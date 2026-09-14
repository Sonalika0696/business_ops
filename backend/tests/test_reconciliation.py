"""Reconciliation v0 — DESIGN.md §9 step 3 (exact matching) and step 5 (rollups).

Exercises `app.modules.reconciliation.service` directly against a small
hand-seeded dataset, via the **sync** session (`app/core/db_sync.py`) — the
same driver the real ingestion task and this service module run against.
There is no REST surface for Order/reconciliation in Phase 1 (DESIGN.md §6),
so these are plain sync tests, not routed through the HTTP client.
"""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db_sync import get_sync_session
from app.core.enums import (
    AmountCanonical,
    FulfillmentType,
    MarketplaceCode,
    MatchStatus,
    OrderStatus,
    PaymentType,
)
from app.core.security import hash_password
from app.modules.ingestion.models import SettlementLineItem, SettlementReport
from app.modules.masters.models import Marketplace, SellerMarketplaceAccount
from app.modules.reconciliation.models import Order
from app.modules.reconciliation.service import compute_settlement_rollups, find_matching_order
from app.modules.sellers.models import Seller


def _seed_account(session: Session) -> uuid.UUID:
    marketplace = session.execute(
        select(Marketplace).where(Marketplace.code == MarketplaceCode.AMAZON_IN)
    ).scalar_one_or_none()
    if marketplace is None:
        marketplace = Marketplace(
            id=uuid.uuid4(),
            code=MarketplaceCode.AMAZON_IN,
            display_name="Amazon India",
            settlement_frequency_days=14,
            payout_split_count=1,
            active=True,
        )
        session.add(marketplace)
        session.flush()

    seller = Seller(
        id=uuid.uuid4(),
        legal_name="Recon Test Seller",
        email=f"recon-{uuid.uuid4().hex[:10]}@example.test",
        hashed_password=hash_password("x"),
    )
    session.add(seller)
    session.flush()

    account = SellerMarketplaceAccount(
        id=uuid.uuid4(),
        seller_id=seller.id,
        marketplace_id=marketplace.id,
        merchant_id_on_platform=f"M-{uuid.uuid4().hex[:8]}",
        fulfillment_type=FulfillmentType.SELF_SHIP,
    )
    session.add(account)
    session.commit()
    return account.id


def test_find_matching_order_hit_and_miss() -> None:
    with get_sync_session() as session:
        account_id = _seed_account(session)
        order = Order(
            id=uuid.uuid4(),
            seller_marketplace_account_id=account_id,
            marketplace_order_id="ORD-ABC",
            order_date=date(2026, 8, 1),
            order_status=OrderStatus.DELIVERED,
            payment_type=PaymentType.PREPAID,
            total_gross_amount_paise=10_000,
        )
        session.add(order)
        session.commit()

        found = find_matching_order(session, account_id, "ORD-ABC")
        assert found is not None
        assert found.id == order.id

        missing = find_matching_order(session, account_id, "ORD-DOES-NOT-EXIST")
        assert missing is None

        # Scoping: the same marketplace_order_id under a different account
        # must never match — matching is always (account, marketplace_order_id).
        other_account_id = _seed_account(session)
        cross_account_miss = find_matching_order(session, other_account_id, "ORD-ABC")
        assert cross_account_miss is None


def test_compute_settlement_rollups_exact_math() -> None:
    """DESIGN.md §9 step 5's five buckets + net payout, hand-calculated:

    gross_sales = 200_000 (only the order with a MATCHED_EXACT line counts)
    fees        = -20_000 (REFERRAL_FEE only)
    taxes       = -2_000  (TCS only)
    refunds     = -5_000
    reimbursements = 3_000
    net_payout  = gross_sales + sum(ALL line items)
                = 200_000 + (-20_000 - 2_000 - 5_000 + 3_000) = 176_000
    """
    with get_sync_session() as session:
        account_id = _seed_account(session)

        order_matched = Order(
            id=uuid.uuid4(),
            seller_marketplace_account_id=account_id,
            marketplace_order_id="ORD-1",
            order_date=date(2026, 8, 1),
            order_status=OrderStatus.DELIVERED,
            payment_type=PaymentType.PREPAID,
            total_gross_amount_paise=200_000,
        )
        # Exists, but never referenced by a MATCHED_EXACT line item below —
        # must NOT contribute to total_gross_sales_paise.
        order_unsettled = Order(
            id=uuid.uuid4(),
            seller_marketplace_account_id=account_id,
            marketplace_order_id="ORD-2",
            order_date=date(2026, 8, 1),
            order_status=OrderStatus.DELIVERED,
            payment_type=PaymentType.PREPAID,
            total_gross_amount_paise=999_999,
        )
        session.add_all([order_matched, order_unsettled])
        session.commit()

        report = SettlementReport(
            id=uuid.uuid4(),
            seller_marketplace_account_id=account_id,
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 30),
            source_file_hash=uuid.uuid4().hex + uuid.uuid4().hex,
            original_filename="f.txt",
            storage_path="/tmp/f.txt",
        )
        session.add(report)
        session.commit()

        session.add_all(
            [
                SettlementLineItem(
                    id=uuid.uuid4(),
                    settlement_report_id=report.id,
                    order_id=order_matched.id,
                    amount_description="Referral fee",
                    amount_canonical=AmountCanonical.REFERRAL_FEE,
                    amount_value_paise=-20_000,
                    posted_date=date(2026, 8, 2),
                    raw_line_data={},
                    match_status=MatchStatus.MATCHED_EXACT,
                ),
                SettlementLineItem(
                    id=uuid.uuid4(),
                    settlement_report_id=report.id,
                    order_id=order_matched.id,
                    amount_description="TCS-IGST",
                    amount_canonical=AmountCanonical.TCS,
                    amount_value_paise=-2_000,
                    posted_date=date(2026, 8, 2),
                    raw_line_data={},
                    match_status=MatchStatus.MATCHED_EXACT,
                ),
                SettlementLineItem(
                    id=uuid.uuid4(),
                    settlement_report_id=report.id,
                    order_id=None,
                    amount_description="Refund",
                    amount_canonical=AmountCanonical.REFUND,
                    amount_value_paise=-5_000,
                    posted_date=date(2026, 8, 3),
                    raw_line_data={},
                    match_status=MatchStatus.UNMATCHED,
                ),
                SettlementLineItem(
                    id=uuid.uuid4(),
                    settlement_report_id=report.id,
                    order_id=None,
                    amount_description="FBA inventory reimbursement",
                    amount_canonical=AmountCanonical.REIMBURSEMENT,
                    amount_value_paise=3_000,
                    posted_date=date(2026, 8, 3),
                    raw_line_data={},
                    match_status=MatchStatus.ADJUSTMENT,
                ),
            ]
        )
        session.commit()

        rollups = compute_settlement_rollups(session, report.id)

        assert rollups.total_gross_sales_paise == 200_000
        assert rollups.total_fees_paise == -20_000
        assert rollups.total_taxes_deducted_paise == -2_000
        assert rollups.total_returns_refunds_paise == -5_000
        assert rollups.total_reimbursements_paise == 3_000
        assert rollups.net_payout_expected_paise == 176_000
