"""Ingestion request/response shapes — DESIGN.md §2.8/§2.9, §6."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import AmountCanonical, MatchStatus, SettlementStatus

# ---------------------------------------------------------------------------
# SettlementReport
# ---------------------------------------------------------------------------


class SettlementReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seller_marketplace_account_id: uuid.UUID
    period_start: date
    period_end: date
    total_gross_sales_paise: int | None
    total_fees_paise: int | None
    total_taxes_deducted_paise: int | None
    total_returns_refunds_paise: int | None
    total_reimbursements_paise: int | None
    net_payout_expected_paise: int | None
    net_payout_bank_credited_paise: int | None
    discrepancy_amount_paise: int | None
    file_uploaded_at: datetime
    source_file_hash: str
    original_filename: str
    status: SettlementStatus
    row_count: int | None
    rejected_row_count: int
    error_message: str | None


class SettlementReportListResponse(BaseModel):
    items: list[SettlementReportRead]
    total: int


class SettlementUploadResponse(BaseModel):
    """DESIGN.md §4: `POST /api/settlements/upload` -> 202 { settlement_report_id, status }.

    `duplicate` is `true` only when the upload endpoint recognized the file's
    sha256 hash as already-processed for this account (DESIGN.md §9's
    idempotency rule) and returned the existing report instead of enqueueing
    a new job.
    """

    settlement_report_id: uuid.UUID
    status: SettlementStatus
    duplicate: bool = False


# ---------------------------------------------------------------------------
# SettlementLineItem
# ---------------------------------------------------------------------------


class SettlementLineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    settlement_report_id: uuid.UUID
    order_id: uuid.UUID | None
    amount_description: str
    amount_canonical: AmountCanonical
    amount_value_paise: int
    posted_date: date
    currency: str
    raw_line_data: dict
    match_status: MatchStatus
    expected_amount_paise: int | None
    deviation_paise: int | None
    is_anomaly: bool
    created_at: datetime


class SettlementLineItemListResponse(BaseModel):
    items: list[SettlementLineItemRead]
    total: int


# ---------------------------------------------------------------------------
# Rejected rows
# ---------------------------------------------------------------------------


class RejectedRowDetail(BaseModel):
    row_number: int
    raw_row: dict
    reason: str


class RejectedRowsResponse(BaseModel):
    items: list[RejectedRowDetail]


__all__ = [
    "RejectedRowDetail",
    "RejectedRowsResponse",
    "SettlementLineItemListResponse",
    "SettlementLineItemRead",
    "SettlementReportListResponse",
    "SettlementReportRead",
    "SettlementUploadResponse",
]
