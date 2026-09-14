"""The settlement parse+reconcile job — DESIGN.md §9 (frozen, 7 steps, exact).

`process_settlement` is the plain, directly-callable function DESIGN.md §4's
testability clause requires — it takes a report id and a **sync** `Session`
and does the actual work; `parse_and_reconcile_settlement` is a thin
`@celery_app.task` wrapper around it, so a running broker/worker is never
required to exercise the real logic (tests, `scripts/demo_e2e.py`).

Every status transition is followed by (a) a commit and (b) a best-effort
Redis publish to `settlement:{report_id}` — publish failures are logged and
swallowed (DESIGN.md §4's fail-open clause: the DB row is the source of
truth, the WS push is UX only) and never abort processing.
"""

import json
import logging
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

# Side-effect import: registers all 12 model classes onto the shared
# declarative registry before this module's first query runs. This is the
# actual entry point a real Celery worker process imports (celery_app's
# `include=[...]`) and the module tests/scripts call `process_settlement`
# from directly — neither necessarily goes through app.main first, so this
# module needs its own guarantee. Without it, SQLAlchemy's lazy mapper
# configuration (triggered on first ORM use) can fail to resolve a
# relationship() string (e.g. Mapped["Order"]) against a model class this
# module never itself imports (this module only imports SettlementReport/
# SettlementLineItem/Order directly, not e.g. Product/FeeSchedule/Return).
import app.all_models  # noqa: E402, F401
from app.canonical.amount_mapping import resolve_amount_canonical
from app.core.celery_app import celery_app
from app.core.db_sync import get_sync_session
from app.core.enums import MatchStatus, SettlementStatus
from app.core.redis import get_redis_sync
from app.modules.ingestion.models import SettlementLineItem, SettlementReport
from app.modules.ingestion.parsers import PARSERS
from app.modules.reconciliation.service import compute_settlement_rollups, find_matching_order

logger = logging.getLogger(__name__)


def _publish_progress(report: SettlementReport) -> None:
    """Best-effort progress push to Redis pub/sub channel `settlement:{id}`.

    DESIGN.md §4: "Redis-publish failures never fail the job" — if this
    raises (Redis down, network blip), log a warning and move on. Never lets
    a WS/progress failure abort or fail settlement processing.
    """
    try:
        payload = json.dumps(
            {
                "status": report.status.value,
                "row_count": report.row_count,
                "rejected_row_count": report.rejected_row_count,
            }
        )
        get_redis_sync().publish(f"settlement:{report.id}", payload)
    except Exception:
        logger.warning(
            "Failed to publish settlement progress for report %s (Redis unreachable?)",
            report.id,
            exc_info=True,
        )


def process_settlement(report_id: uuid.UUID, session: Session) -> None:
    """DESIGN.md §9's 7 steps, exactly. Raises on failure (after recording
    FAILED + error_message) so Celery's own retry/failure bookkeeping still
    sees it — callers that need the row-level exception (tests, demo script)
    should call this directly and catch it themselves if desired.
    """
    report = session.get(SettlementReport, report_id)
    if report is None:
        raise ValueError(f"SettlementReport {report_id} not found")

    try:
        # --- Step 1: PARSING -------------------------------------------------
        report.status = SettlementStatus.PARSING
        session.commit()
        _publish_progress(report)

        # --- Step 2: open + parse the marketplace-appropriate file shape ------
        # DESIGN.md §11.2/§11.3: "utf-8-sig" is a safe superset of "utf-8" —
        # it strips a leading BOM if present (Meesho) and behaves identically
        # to plain UTF-8 if not (Amazon/Flipkart), so it's applied uniformly.
        marketplace_code = report.seller_marketplace_account.marketplace.code
        parse_file = PARSERS[marketplace_code]
        with Path(report.storage_path).open("r", encoding="utf-8-sig", newline="") as f:
            parse_result = parse_file(f)

        # --- Step 3: resolve canonical + match, per row -----------------------
        rejected_rows_detail: list[dict] = list(report.rejected_rows_detail or [])
        row_count = 0

        # Rows the parser already rejected structurally (bad amount/date/columns).
        for rejected in parse_result.rejected_rows:
            row_count += 1
            rejected_rows_detail.append(
                {
                    "row_number": rejected.row_number,
                    "raw_row": rejected.raw_row,
                    "reason": rejected.reason,
                }
            )

        for parsed in parse_result.parsed_rows:
            row_count += 1

            canonical = resolve_amount_canonical(parsed.amount_description, marketplace_code)
            if canonical is None:
                rejected_rows_detail.append(
                    {
                        "row_number": parsed.row_number,
                        "raw_row": parsed.raw_row,
                        "reason": f"unmapped amount_description: {parsed.amount_description}",
                    }
                )
                continue

            amount_value_paise = int(round(parsed.amount * 100))

            if parsed.order_id is None:
                order_id = None
                match_status = MatchStatus.ADJUSTMENT
            else:
                order = find_matching_order(
                    session, report.seller_marketplace_account_id, parsed.order_id
                )
                if order is not None:
                    order_id = order.id
                    match_status = MatchStatus.MATCHED_EXACT
                else:
                    order_id = None
                    match_status = MatchStatus.UNMATCHED

            session.add(
                SettlementLineItem(
                    id=uuid.uuid4(),
                    settlement_report_id=report.id,
                    order_id=order_id,
                    amount_description=parsed.amount_description,
                    amount_canonical=canonical,
                    amount_value_paise=amount_value_paise,
                    posted_date=parsed.posted_date,
                    raw_line_data=parsed.raw_row,
                    match_status=match_status,
                )
            )

        # Narrow period_start/period_end to the actual data span, if any rows
        # parsed (see ingestion/service.py's module docstring for why these
        # start as upload-date placeholders).
        if parse_result.parsed_rows:
            posted_dates = [row.posted_date for row in parse_result.parsed_rows]
            report.period_start = min(posted_dates)
            report.period_end = max(posted_dates)

        # --- Step 4: PARSED ----------------------------------------------------
        report.row_count = row_count
        report.rejected_row_count = len(rejected_rows_detail)
        report.rejected_rows_detail = rejected_rows_detail
        report.status = SettlementStatus.PARSED
        session.commit()
        _publish_progress(report)

        # --- Step 5: RECONCILING + rollups --------------------------------------
        report.status = SettlementStatus.RECONCILING
        session.commit()
        _publish_progress(report)

        rollups = compute_settlement_rollups(session, report.id)
        report.total_gross_sales_paise = rollups.total_gross_sales_paise
        report.total_fees_paise = rollups.total_fees_paise
        report.total_taxes_deducted_paise = rollups.total_taxes_deducted_paise
        report.total_returns_refunds_paise = rollups.total_returns_refunds_paise
        report.total_reimbursements_paise = rollups.total_reimbursements_paise
        report.net_payout_expected_paise = rollups.net_payout_expected_paise
        # net_payout_bank_credited_paise / discrepancy_amount_paise stay NULL —
        # no bank-statement upload exists in Phase 1 (DESIGN.md §9 step 5).

        # --- Step 6: RECONCILED (final frame) -----------------------------------
        report.status = SettlementStatus.RECONCILED
        session.commit()
        _publish_progress(report)

    except Exception as exc:
        # --- Step 7: FAILED, fail closed on money -------------------------------
        session.rollback()
        report = session.get(SettlementReport, report_id)
        report.status = SettlementStatus.FAILED
        report.error_message = str(exc)
        session.commit()
        _publish_progress(report)
        raise


@celery_app.task(name="app.modules.ingestion.tasks.parse_and_reconcile_settlement")
def parse_and_reconcile_settlement(settlement_report_id: str) -> None:
    """Thin Celery wrapper around `process_settlement` (DESIGN.md §4's
    testability clause) — opens its own sync session since Celery tasks run
    outside any request-scoped session."""
    report_uuid = uuid.UUID(settlement_report_id)
    with get_sync_session() as session:
        process_settlement(report_uuid, session)


__all__ = ["parse_and_reconcile_settlement", "process_settlement"]
