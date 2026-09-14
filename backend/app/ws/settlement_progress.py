"""Settlement progress WS route — DESIGN.md §4.

`WS /ws/settlements/{id}?token=<jwt>`: a bearer token in the `Authorization`
header isn't reliably available to browser WebSocket clients, so this one
route takes the JWT as a query parameter instead — a documented, deliberate
exception to the header-auth convention, not a gap. Validated the same way
as `get_current_seller`, via the shared `app.core.deps.authenticate_token`
helper (no duplicated JWT-decoding logic).

On connect, *before* subscribing, the route sends the report's current DB
row (so a client that connects after the job already progressed, or already
finished, isn't left waiting for a transition that already happened) — then
subscribes to the Redis pub/sub channel `settlement:{id}` and forwards
further frames until disconnect.

Redis-failure is fail-open (DESIGN.md §4, ARCHITECTURE.md §11): if the
subscribe/listen fails (Redis down, network blip), the push stream just ends
— logged, connection closed — never raised back to the client. The
`SettlementReport.status` row in Postgres remains the source of truth; a
client that loses the push stream can always re-fetch `GET
/api/settlements/{id}` or reconnect.
"""

import json
import logging
import uuid

from fastapi import WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.core.deps import authenticate_token
from app.core.redis import get_redis
from app.modules.ingestion.models import SettlementReport
from app.modules.masters.models import SellerMarketplaceAccount

logger = logging.getLogger(__name__)


def _progress_frame(report: SettlementReport) -> dict:
    return {
        "status": report.status.value,
        "row_count": report.row_count,
        "rejected_row_count": report.rejected_row_count,
    }


async def settlement_progress_ws(websocket: WebSocket, report_id: uuid.UUID) -> None:
    token = websocket.query_params.get("token")

    async with AsyncSessionLocal() as db:
        seller = await authenticate_token(token, db)
        if seller is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        result = await db.execute(
            select(SettlementReport)
            .join(
                SellerMarketplaceAccount,
                SettlementReport.seller_marketplace_account_id == SellerMarketplaceAccount.id,
            )
            .where(
                SettlementReport.id == report_id,
                SellerMarketplaceAccount.seller_id == seller.id,
            )
        )
        report = result.scalar_one_or_none()
        if report is None:
            # Not owned by this seller (or doesn't exist) — same "404, not
            # 403" posture as the REST routes, translated to a WS close.
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket.accept()
        await websocket.send_json(_progress_frame(report))

    channel = f"settlement:{report_id}"
    pubsub = None
    try:
        pubsub = get_redis().pubsub()
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            await websocket.send_json(json.loads(message["data"]))
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.warning(
            "settlement progress WS: pub/sub failure for report %s (Redis unreachable?)",
            report_id,
            exc_info=True,
        )
    finally:
        if pubsub is not None:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception:
                pass
        try:
            await websocket.close()
        except Exception:
            pass


__all__ = ["settlement_progress_ws"]
