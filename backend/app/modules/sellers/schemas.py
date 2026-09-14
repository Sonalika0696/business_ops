"""Seller response/update shapes — DESIGN.md §2.1 / §6.

`SellerRead` intentionally omits `hashed_password` (never exposed via the
API). `SellerUpdate` covers the mutable profile fields only — `id`, `email`,
`created_at`, `updated_at`, `deleted_at` are excluded (email is the auth
identity and immutable via this endpoint; DESIGN.md doesn't define an
email-change flow for Phase 1).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import MsmeClassification


class SellerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    legal_name: str
    trade_name: str | None
    email: str
    gstin: str | None
    pan: str | None
    udyam_registration_number: str | None
    msme_classification: MsmeClassification
    primary_state: str | None
    primary_pincode: str | None
    principal_place_of_business: str | None
    bank_account_number: str | None
    bank_ifsc: str | None
    bank_name: str | None
    created_at: datetime
    updated_at: datetime


class SellerUpdate(BaseModel):
    legal_name: str | None = None
    trade_name: str | None = None
    gstin: str | None = None
    pan: str | None = None
    udyam_registration_number: str | None = None
    msme_classification: MsmeClassification | None = None
    primary_state: str | None = None
    primary_pincode: str | None = None
    principal_place_of_business: str | None = None
    bank_account_number: str | None = None
    bank_ifsc: str | None = None
    bank_name: str | None = None
