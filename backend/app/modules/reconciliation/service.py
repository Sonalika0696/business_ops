"""Reconciliation v0 — DESIGN.md §9 (exact matching + rollup computation).

This module owns the order-matching and rollup-computation logic that the
ingestion Celery task (`app.modules.ingestion.tasks`) calls — per
`ARCHITECTURE.md` §1's module-boundary rule, reconciliation logic lives here
even though it's only ever invoked from the ingestion job in Phase 1. There
is no REST surface for this module in Phase 1 (DESIGN.md §6 lists none).

Both functions take a **sync** `Session` (`app/core/db_sync.py`) since the
only caller (the Celery task) runs sync per DESIGN.md §9.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AmountCanonical, MatchStatus
from app.modules.ingestion.models import SettlementLineItem
from app.modules.reconciliation.models import Order

# DESIGN.md §9 step 5's five rollup buckets, verbatim.
_FEE_BUCKET: frozenset[AmountCanonical] = frozenset(
    {
        AmountCanonical.REFERRAL_FEE,
        AmountCanonical.CLOSING_FEE,
        AmountCanonical.SHIPPING_FEE,
        AmountCanonical.COLLECTION_FEE,
        AmountCanonical.FBA_FEE,
        AmountCanonical.STORAGE_FEE,
        AmountCanonical.ADVERTISING_FEE,
        AmountCanonical.GST_ON_FEE,
        AmountCanonical.PROMOTION_REBATE,
        AmountCanonical.ADJUSTMENT,
    }
)
_TAX_BUCKET: frozenset[AmountCanonical] = frozenset({AmountCanonical.TCS, AmountCanonical.TDS})


def find_matching_order(
    session: Session, seller_marketplace_account_id: uuid.UUID, marketplace_order_id: str
) -> Order | None:
    """Exact-match lookup: `Order` by `(seller_marketplace_account_id, marketplace_order_id)`
    scoped to the same account as the settlement report (DESIGN.md §9 step 3)."""
    result = session.execute(
        select(Order).where(
            Order.seller_marketplace_account_id == seller_marketplace_account_id,
            Order.marketplace_order_id == marketplace_order_id,
        )
    )
    return result.scalar_one_or_none()


@dataclass(frozen=True)
class SettlementRollups:
    """The five report-level rollups DESIGN.md §9 step 5 computes for a
    settlement report, plus the derived `net_payout_expected_paise`.
    `net_payout_bank_credited_paise` / `discrepancy_amount_paise` are
    deliberately not part of this dataclass — Phase 1 has no bank-statement
    upload, so those two stay NULL and are never computed (DESIGN.md §9)."""

    total_gross_sales_paise: int
    total_fees_paise: int
    total_taxes_deducted_paise: int
    total_returns_refunds_paise: int
    total_reimbursements_paise: int
    net_payout_expected_paise: int


def compute_settlement_rollups(
    session: Session, settlement_report_id: uuid.UUID
) -> SettlementRollups:
    """Compute the five rollup buckets + net payout for a settlement report,
    from its already-inserted `SettlementLineItem` rows — DESIGN.md §9 step 5.

    Straight sums only (Phase 1 has no FeeSchedule-driven expected-vs-actual
    deviation yet); `net_payout_expected_paise` is `total_gross_sales_paise +
    sum(amount_value_paise) over ALL of this report's line items` — a
    straight sum, deliberately **not** the sum of the five bucket totals
    below (per DESIGN.md §9, the straight sum is the source of truth so the
    two never silently drift apart if the bucket definitions ever change).
    """
    line_items = list(
        session.execute(
            select(SettlementLineItem).where(
                SettlementLineItem.settlement_report_id == settlement_report_id
            )
        )
        .scalars()
        .all()
    )

    total_fees_paise = sum(
        li.amount_value_paise for li in line_items if li.amount_canonical in _FEE_BUCKET
    )
    total_taxes_deducted_paise = sum(
        li.amount_value_paise for li in line_items if li.amount_canonical in _TAX_BUCKET
    )
    total_returns_refunds_paise = sum(
        li.amount_value_paise
        for li in line_items
        if li.amount_canonical is AmountCanonical.REFUND
    )
    total_reimbursements_paise = sum(
        li.amount_value_paise
        for li in line_items
        if li.amount_canonical is AmountCanonical.REIMBURSEMENT
    )

    # Distinct orders that received >=1 MATCHED_EXACT line item this report
    # (i.e. orders actually settled this period, not every order that exists).
    matched_order_ids = {
        li.order_id
        for li in line_items
        if li.match_status is MatchStatus.MATCHED_EXACT and li.order_id is not None
    }
    total_gross_sales_paise = 0
    if matched_order_ids:
        orders_result = session.execute(select(Order).where(Order.id.in_(matched_order_ids)))
        total_gross_sales_paise = sum(
            order.total_gross_amount_paise for order in orders_result.scalars().all()
        )

    all_line_items_sum = sum(li.amount_value_paise for li in line_items)
    net_payout_expected_paise = total_gross_sales_paise + all_line_items_sum

    return SettlementRollups(
        total_gross_sales_paise=total_gross_sales_paise,
        total_fees_paise=total_fees_paise,
        total_taxes_deducted_paise=total_taxes_deducted_paise,
        total_returns_refunds_paise=total_returns_refunds_paise,
        total_reimbursements_paise=total_reimbursements_paise,
        net_payout_expected_paise=net_payout_expected_paise,
    )


__all__ = ["SettlementRollups", "compute_settlement_rollups", "find_matching_order"]
