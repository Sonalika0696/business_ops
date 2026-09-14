"""Ingestion — DESIGN.md §2.8 (SettlementReport) and §2.9 (SettlementLineItem).

`SettlementReport.status` is the frozen Phase 1 job-lifecycle contract
(DESIGN.md §4): UPLOADED -> PARSING -> PARSED -> RECONCILING -> RECONCILED,
or -> FAILED with `error_message` set. `SettlementLineItem` rows are
strictly append-only (ARCHITECTURE.md §6) — no `deleted_at` column here.
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AmountCanonical, MatchStatus, SettlementStatus
from app.db_base import Base

if TYPE_CHECKING:
    from app.modules.masters.models import SellerMarketplaceAccount
    from app.modules.reconciliation.models import Order


class SettlementReport(Base):
    __tablename__ = "settlement_reports"
    __table_args__ = (
        UniqueConstraint(
            "seller_marketplace_account_id",
            "source_file_hash",
            name="uq_settlement_reports_account_file_hash",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    seller_marketplace_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_marketplace_accounts.id"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    total_gross_sales_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_fees_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_taxes_deducted_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_returns_refunds_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_reimbursements_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    net_payout_expected_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    net_payout_bank_credited_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    discrepancy_amount_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    file_uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    source_file_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)  # sha256 hex
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)  # [+]
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)  # [+]
    status: Mapped[SettlementStatus] = mapped_column(
        Enum(
            SettlementStatus,
            name="settlement_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        server_default=text("'UPLOADED'"),
    )  # [+] this *is* the Phase-1 job-lifecycle state (DESIGN.md §4)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # [+]
    rejected_row_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )  # [+]
    rejected_rows_detail: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )  # [+] [{row_number, raw_row, reason}], see DESIGN.md §9
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)  # [+]

    seller_marketplace_account: Mapped["SellerMarketplaceAccount"] = relationship(
        "SellerMarketplaceAccount", back_populates="settlement_reports"
    )
    line_items: Mapped[list["SettlementLineItem"]] = relationship(
        "SettlementLineItem", back_populates="settlement_report"
    )


class SettlementLineItem(Base):
    """The canonical line item (DESIGN.md §3). Append-only — no delete column."""

    __tablename__ = "settlement_line_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    settlement_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("settlement_reports.id"), nullable=False
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True
    )  # null until matched, or for pure adjustments
    amount_description: Mapped[str] = mapped_column(Text, nullable=False)  # raw marketplace string
    amount_canonical: Mapped[AmountCanonical] = mapped_column(
        Enum(
            AmountCanonical,
            name="amount_canonical",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    # signed: fees negative, credits positive (DESIGN.md §3 sign convention)
    amount_value_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    posted_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'INR'"))
    raw_line_data: Mapped[dict] = mapped_column(JSONB, nullable=False)  # original CSV row, audit

    match_status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus, name="match_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        server_default=text("'UNMATCHED'"),
    )  # [+]
    expected_amount_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # [+]
    deviation_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # [+]
    is_anomaly: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )  # [+]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    settlement_report: Mapped["SettlementReport"] = relationship(
        "SettlementReport", back_populates="line_items"
    )
    order: Mapped["Order | None"] = relationship("Order", back_populates="settlement_line_items")
