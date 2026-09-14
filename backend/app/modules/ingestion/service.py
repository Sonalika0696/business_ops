"""Ingestion upload service — DESIGN.md §4/§6/§9 (upload flow + idempotency).

The duplicate-upload check (`(seller_marketplace_account_id, source_file_hash)`)
happens **here**, at upload time — DESIGN.md §9: "Idempotency ... happens at
the upload endpoint ... not inside the task." The Celery task itself
(`app.modules.ingestion.tasks`) is never re-enqueued for a duplicate.

Deviation note: `SettlementReport.period_start`/`period_end` are NOT NULL
columns, but DESIGN.md §6's upload request shape carries only `file` +
`seller_marketplace_account_id` — no explicit period fields, and the §8 file
format carries no report-level period either (only a `posted-date` per
line). We set both to the upload date as a placeholder at creation time, then
the ingestion task (§9 step 3/4) narrows them to the actual
min(posted_date)/max(posted_date) across the parsed rows once parsing
completes, which is the closest reading of "the period this report covers"
available from the data actually on hand.
"""

import hashlib
import logging
import socket
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import MatchStatus, SettlementStatus
from app.modules.ingestion.models import SettlementLineItem, SettlementReport
from app.modules.masters.models import SellerMarketplaceAccount

logger = logging.getLogger(__name__)


class AccountNotFoundError(Exception):
    """Raised when `seller_marketplace_account_id` doesn't exist or isn't owned
    by the current seller — surfaced as 404, not 403 (matches the masters
    module's pattern: don't leak whether the id exists for another seller)."""


class NotFoundError(Exception):
    """Raised when a settlement report doesn't exist or isn't owned by the
    current seller (via their marketplace accounts)."""


def _compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


async def _get_owned_account(
    db: AsyncSession, seller_id: uuid.UUID, account_id: uuid.UUID
) -> SellerMarketplaceAccount:
    result = await db.execute(
        select(SellerMarketplaceAccount).where(
            SellerMarketplaceAccount.id == account_id,
            SellerMarketplaceAccount.seller_id == seller_id,
            SellerMarketplaceAccount.deleted_at.is_(None),
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise AccountNotFoundError
    return account


async def upload_settlement_file(
    db: AsyncSession,
    seller_id: uuid.UUID,
    seller_marketplace_account_id: uuid.UUID,
    original_filename: str,
    content: bytes,
) -> tuple[SettlementReport, bool]:
    """Handle a settlement file upload. Returns `(report, duplicate)`.

    `duplicate=True` means an identical file (same sha256) was already
    uploaded for this account — the existing report is returned unchanged
    and no new Celery task is enqueued (DESIGN.md §9's idempotency rule).
    """
    await _get_owned_account(db, seller_id, seller_marketplace_account_id)

    file_hash = _compute_sha256(content)

    existing_result = await db.execute(
        select(SettlementReport).where(
            SettlementReport.seller_marketplace_account_id == seller_marketplace_account_id,
            SettlementReport.source_file_hash == file_hash,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        return existing, True

    settings = get_settings()
    storage_dir = Path(settings.storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = storage_dir / file_hash
    storage_path.write_bytes(content)

    upload_date: date = datetime.now(UTC).date()
    report = SettlementReport(
        id=uuid.uuid4(),
        seller_marketplace_account_id=seller_marketplace_account_id,
        period_start=upload_date,  # placeholder — see module docstring
        period_end=upload_date,
        source_file_hash=file_hash,
        original_filename=original_filename,
        storage_path=str(storage_path),
        status=SettlementStatus.UPLOADED,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    _enqueue_processing(report.id)

    return report, False


def _enqueue_processing(settlement_report_id: uuid.UUID) -> None:
    """Enqueue the Celery task. Wrapped in try/except: a broker that is down
    (Redis unreachable) must not 500 the upload request — the report row
    (status=UPLOADED) is already durably committed, and a later retry /
    manual re-trigger / worker restart can pick it up. This mirrors
    ARCHITECTURE.md §11's "fail open on convenience" posture for the
    dispatch step specifically; it does not affect the task's own
    fail-closed-on-money behavior once it does run (DESIGN.md §9 step 7).
    """
    if not _broker_reachable():
        # A raw TCP pre-check, not just a try/except around `.delay()`:
        # Celery/kombu's own connection machinery does NOT reliably honor a
        # short timeout on every code path when the broker is down (observed
        # multi-second-to-indefinite hangs in practice on this stack), which
        # would defeat DESIGN.md §4's fail-open intent — a down broker must
        # not make the upload request itself slow or hang. A cheap raw
        # socket check first keeps this fast in the common "broker is just
        # not running" case; `.delay()` is only attempted when a TCP
        # connection to the broker host:port actually succeeds.
        logger.warning(
            "Redis broker unreachable — skipping enqueue of "
            "parse_and_reconcile_settlement for report %s; report remains "
            "UPLOADED for later retry.",
            settlement_report_id,
        )
        return

    try:
        from app.modules.ingestion.tasks import parse_and_reconcile_settlement

        parse_and_reconcile_settlement.delay(str(settlement_report_id))
    except Exception:
        logger.warning(
            "Failed to enqueue parse_and_reconcile_settlement for report %s "
            "(broker unreachable?) — report remains UPLOADED for later retry.",
            settlement_report_id,
            exc_info=True,
        )


def _broker_reachable(timeout_seconds: float = 0.5) -> bool:
    """Fast raw-TCP reachability check for the Redis broker host:port."""
    settings = get_settings()
    parsed = urlparse(settings.redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


async def get_settlement_report(
    db: AsyncSession, seller_id: uuid.UUID, report_id: uuid.UUID
) -> SettlementReport:
    result = await db.execute(
        select(SettlementReport)
        .join(
            SellerMarketplaceAccount,
            SettlementReport.seller_marketplace_account_id == SellerMarketplaceAccount.id,
        )
        .where(
            SettlementReport.id == report_id,
            SellerMarketplaceAccount.seller_id == seller_id,
        )
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise NotFoundError
    return report


async def list_settlement_reports(
    db: AsyncSession, seller_id: uuid.UUID, page: int, page_size: int
) -> tuple[list[SettlementReport], int]:
    base = (
        select(SettlementReport)
        .join(
            SellerMarketplaceAccount,
            SettlementReport.seller_marketplace_account_id == SellerMarketplaceAccount.id,
        )
        .where(SellerMarketplaceAccount.seller_id == seller_id)
    )
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    items_stmt = (
        base.order_by(SettlementReport.file_uploaded_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(items_stmt)).scalars().all()
    return list(items), total


async def list_settlement_line_items(
    db: AsyncSession,
    seller_id: uuid.UUID,
    report_id: uuid.UUID,
    match_status: MatchStatus | None,
    page: int,
    page_size: int,
) -> tuple[list[SettlementLineItem], int]:
    """Line items for a report, seller-scoped via the report's owning account.

    Raises `NotFoundError` if the report doesn't exist / isn't owned by
    `seller_id` — a settlement report belonging to another seller's account
    must 404, matching the masters module's pattern, not leak via an empty list.
    """
    await get_settlement_report(db, seller_id, report_id)  # ownership check, raises NotFoundError

    base = select(SettlementLineItem).where(
        SettlementLineItem.settlement_report_id == report_id
    )
    if match_status is not None:
        base = base.where(SettlementLineItem.match_status == match_status)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    items_stmt = (
        base.order_by(SettlementLineItem.created_at)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(items_stmt)).scalars().all()
    return list(items), total


async def get_rejected_rows(
    db: AsyncSession, seller_id: uuid.UUID, report_id: uuid.UUID
) -> list[dict]:
    """`rejected_rows_detail` for a report — `[{row_number, raw_row, reason}]`."""
    report = await get_settlement_report(db, seller_id, report_id)
    return list(report.rejected_rows_detail or [])


__all__ = [
    "AccountNotFoundError",
    "NotFoundError",
    "get_rejected_rows",
    "get_settlement_report",
    "list_settlement_line_items",
    "list_settlement_reports",
    "upload_settlement_file",
]
