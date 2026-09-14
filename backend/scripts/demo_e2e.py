"""Phase 1/2 exit-criteria demo — DESIGN.md §7 + §11.6, run unattended.

Runs the whole ingestion + reconciliation-v0 loop end to end for all 3
marketplaces (Amazon, Flipkart, Meesho) in one run, with no external
services beyond Postgres (no live Celery worker or Redis needed, per
DESIGN.md §4's testability clause):

  1. Run the synthetic data generator (`scripts/synth_data_generator.py`,
     default fixed seed) — this script does NOT assume the generator has
     already been run; it calls it itself, so a single `uv run python
     scripts/demo_e2e.py` is enough for an unattended demo. The generator now
     emits one settlement fixture + ground truth per marketplace
     (DESIGN.md §11.5).
  2. For each marketplace, upload its generated settlement fixture through
     the real service layer (`app.modules.ingestion.service.upload_settlement_file`
     called directly, not over HTTP — faster and avoids needing a running
     uvicorn process for what is otherwise a pure DB-and-filesystem flow).
  3. Run `process_settlement` directly (the plain function, not the Celery
     task wrapper) against each resulting `SettlementReport` — this is what
     exercises the marketplace-aware parser dispatch (DESIGN.md §11.3) end
     to end, including Meesho's BOM-tolerance path.
  4. Assert each resulting `SettlementReport`/`SettlementLineItem` rows match
     that marketplace's own `*_settlement_sample.ground_truth.json` (row
     counts, matched vs. unmatched/orphan counts). Exits non-zero with a
     clear message on the first mismatch found (across any marketplace);
     prints a clean pass summary for all 3 on success.

Usage:
    uv run python scripts/demo_e2e.py
"""

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

# Side-effect import: registers all 12 model classes before this script's
# first query — see the matching comment in scripts/synth_data_generator.py
# and app/modules/ingestion/tasks.py for why this is needed independently in
# every standalone entry point.
import app.all_models  # noqa: E402, F401
from app.core.db import AsyncSessionLocal  # noqa: E402
from app.core.db_sync import get_sync_session  # noqa: E402
from app.core.enums import MarketplaceCode, MatchStatus, SettlementStatus  # noqa: E402
from app.modules.ingestion import service as ingestion_service  # noqa: E402
from app.modules.ingestion.models import SettlementLineItem, SettlementReport  # noqa: E402
from app.modules.ingestion.tasks import process_settlement  # noqa: E402
from app.modules.masters.models import Marketplace, SellerMarketplaceAccount  # noqa: E402
from app.modules.sellers.models import Seller  # noqa: E402
from scripts.synth_data_generator import (  # noqa: E402
    DEMO_SELLER_EMAIL,
    FLIPKART_SETTLEMENT_FIXTURE_PATH,
    MEESHO_SETTLEMENT_FIXTURE_PATH,
    SETTLEMENT_FIXTURE_PATH,
    generate,
)

# DESIGN.md §11.6: one run, all 3 marketplace accounts, each asserted against
# its own ground truth.
_MARKETPLACES: list[tuple[str, MarketplaceCode, Path]] = [
    ("amazon", MarketplaceCode.AMAZON_IN, SETTLEMENT_FIXTURE_PATH),
    ("flipkart", MarketplaceCode.FLIPKART, FLIPKART_SETTLEMENT_FIXTURE_PATH),
    ("meesho", MarketplaceCode.MEESHO, MEESHO_SETTLEMENT_FIXTURE_PATH),
]


def _fail(message: str) -> None:
    print(f"\nDEMO FAILED: {message}")
    sys.exit(1)


async def _fetch_and_upload_all() -> dict[str, uuid.UUID]:
    """Fetch the demo seller + all 3 marketplace accounts and upload each
    one's fixture, all inside ONE event loop (a single `asyncio.run()` call
    from `main()` — see below for why this matters). Returns
    `{label: settlement_report_id}`.

    `app.core.db.engine` is a module-level singleton whose asyncpg
    connections are bound to whichever event loop was active when they were
    first acquired; calling `asyncio.run()` more than once for work that
    shares that engine reuses a pooled connection across a *closed* loop and
    corrupts it (`RuntimeError: Event loop is closed` / `AttributeError:
    'NoneType' object has no attribute 'send'`) — the exact same class of bug
    the test suite hit against pytest-asyncio's per-function loops, fixed
    there via `asyncio_default_test_loop_scope = "session"` in
    pyproject.toml. DESIGN.md §11.6 extends this script to 3 marketplaces in
    one run, so all 3 uploads must happen inside this single coroutine
    (looped, not called via 3 separate `asyncio.run()`s) to stay inside one
    event loop end to end.
    """
    report_ids: dict[str, uuid.UUID] = {}
    async with AsyncSessionLocal() as db:
        seller = (
            await db.execute(select(Seller).where(Seller.email == DEMO_SELLER_EMAIL))
        ).scalar_one()

        for label, marketplace_code, fixture_path in _MARKETPLACES:
            account = (
                await db.execute(
                    select(SellerMarketplaceAccount)
                    .join(
                        Marketplace, SellerMarketplaceAccount.marketplace_id == Marketplace.id
                    )
                    .where(
                        SellerMarketplaceAccount.seller_id == seller.id,
                        Marketplace.code == marketplace_code,
                    )
                )
            ).scalar_one()
            print(f"  [{label}] seller={seller.id} account={account.id}")

            content = fixture_path.read_bytes()
            report, duplicate = await ingestion_service.upload_settlement_file(
                db, seller.id, account.id, fixture_path.name, content
            )
            print(f"  [{label}] uploaded -> report {report.id} (duplicate={duplicate})")
            report_ids[label] = report.id

    return report_ids


def _process_and_assert(label: str, report_id: uuid.UUID, ground_truth: dict) -> None:
    """Run `process_settlement` for one report, then assert its resulting
    rows match that marketplace's ground truth (DESIGN.md §11.6)."""
    with get_sync_session() as session:
        try:
            process_settlement(report_id, session)
        except Exception as exc:  # noqa: BLE001 — surfaced via _fail below
            _fail(f"[{label}] process_settlement raised: {exc!r}")

    with get_sync_session() as session:
        report = session.get(SettlementReport, report_id)
        if report is None:
            _fail(f"[{label}] SettlementReport row disappeared after processing")
        if report.status != SettlementStatus.RECONCILED:
            _fail(
                f"[{label}] expected status=RECONCILED, got {report.status} "
                f"(error_message={report.error_message!r})"
            )

        line_items = list(
            session.execute(
                select(SettlementLineItem).where(
                    SettlementLineItem.settlement_report_id == report_id
                )
            )
            .scalars()
            .all()
        )

        matched_order_ids = {
            li.order_id
            for li in line_items
            if li.match_status is MatchStatus.MATCHED_EXACT and li.order_id is not None
        }
        unmatched_count = sum(1 for li in line_items if li.match_status is MatchStatus.UNMATCHED)
        adjustment_count = sum(
            1 for li in line_items if li.match_status is MatchStatus.ADJUSTMENT
        )

        errors: list[str] = []
        if report.rejected_row_count != 0:
            errors.append(
                f"rejected_row_count={report.rejected_row_count}, expected 0 "
                f"(the synthetic fixture only emits mapped descriptions/valid rows)"
            )
        if report.row_count != ground_truth["total_line_count"]:
            errors.append(
                f"row_count={report.row_count} != expected total_line_count="
                f"{ground_truth['total_line_count']}"
            )
        if len(matched_order_ids) != ground_truth["orders_with_settlement_lines"]:
            errors.append(
                f"distinct matched orders={len(matched_order_ids)} != expected "
                f"orders_with_settlement_lines={ground_truth['orders_with_settlement_lines']}"
            )
        if unmatched_count != ground_truth["orphan_line_count"]:
            errors.append(
                f"UNMATCHED (orphan) line count={unmatched_count} != expected "
                f"orphan_line_count={ground_truth['orphan_line_count']}"
            )

        if errors:
            print()
            for e in errors:
                print(f"  [{label}] MISMATCH: {e}")
            _fail(f"[{label}] ground-truth assertions failed (see MISMATCH lines above)")

        print(f"\n  [{label}] PASS — SettlementReport {report_id}: status={report.status.value}")
        print(f"    row_count={report.row_count} rejected_row_count={report.rejected_row_count}")
        print(
            f"    matched distinct orders={len(matched_order_ids)} "
            f"unmatched(orphan)={unmatched_count} adjustment={adjustment_count}"
        )
        print(f"    total_gross_sales_paise={report.total_gross_sales_paise}")
        print(f"    total_fees_paise={report.total_fees_paise}")
        print(f"    total_taxes_deducted_paise={report.total_taxes_deducted_paise}")
        print(f"    net_payout_expected_paise={report.net_payout_expected_paise}")


def main() -> None:
    print("=== Phase 2 end-to-end demo (Amazon + Flipkart + Meesho) ===\n")

    print("Step 1: generating synthetic data + settlement fixtures for all 3 marketplaces...")
    ground_truths = generate()

    print("\nStep 2: uploading all 3 marketplaces' fixtures (one event loop)...")
    report_ids = asyncio.run(_fetch_and_upload_all())

    for label, _marketplace_code, fixture_path in _MARKETPLACES:
        print(f"\nStep 3 [{label}]: processing {fixture_path.name}...")
        _process_and_assert(label, report_ids[label], ground_truths[label])

    print("\n=== PASS ===")
    print("All 3 marketplaces (Amazon, Flipkart, Meesho) parsed + reconciled successfully.")


if __name__ == "__main__":
    main()
