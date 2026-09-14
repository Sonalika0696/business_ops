"""Masters request/response shapes — DESIGN.md §2.2/§2.3/§2.4, §6.

Note on `SellerMarketplaceAccount`: the DESIGN.md §2.3 entity shape carries
`marketplace_id` (the FK), not `marketplace_code` — the client only ever
sends `marketplace_code` on create (§6), which the service resolves to
`marketplace_id` server-side. The read/list responses below mirror the
entity as specified, i.e. `marketplace_id`.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import FulfillmentType, MarketplaceCode

_ALLOWED_GST_RATES = (0, 5, 12, 18, 28)


# ---------------------------------------------------------------------------
# Marketplace (read-only reference data)
# ---------------------------------------------------------------------------


class MarketplaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: MarketplaceCode
    display_name: str
    settlement_frequency_days: int
    payout_split_count: int
    active: bool


class MarketplaceListResponse(BaseModel):
    items: list[MarketplaceRead]


# ---------------------------------------------------------------------------
# SellerMarketplaceAccount
# ---------------------------------------------------------------------------


class SellerMarketplaceAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seller_id: uuid.UUID
    marketplace_id: uuid.UUID
    merchant_id_on_platform: str
    warehouse_pincode: str | None
    fulfillment_type: FulfillmentType
    activated_on: date
    deleted_at: datetime | None


class SellerMarketplaceAccountListResponse(BaseModel):
    items: list[SellerMarketplaceAccountRead]
    total: int


class SellerMarketplaceAccountCreate(BaseModel):
    marketplace_code: MarketplaceCode
    merchant_id_on_platform: str = Field(min_length=1)
    warehouse_pincode: str | None = None
    fulfillment_type: FulfillmentType


class SellerMarketplaceAccountUpdate(BaseModel):
    """Partial update — only `warehouse_pincode`/`fulfillment_type` are mutable
    (DESIGN.md §6: `marketplace_code`/`merchant_id` are immutable post-create)."""

    warehouse_pincode: str | None = None
    fulfillment_type: FulfillmentType | None = None


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seller_id: uuid.UUID
    internal_sku: str
    product_name: str
    hsn_code: str | None
    category_primary: str | None
    category_sub: str | None
    weight_grams: int | None
    dimensions_cm_length: Decimal | None
    dimensions_cm_width: Decimal | None
    dimensions_cm_height: Decimal | None
    mrp_paise: int
    cost_price_paise: int
    gst_rate: int
    created_at: datetime
    deleted_at: datetime | None


class ProductListResponse(BaseModel):
    items: list[ProductRead]
    total: int


class ProductCreate(BaseModel):
    internal_sku: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    hsn_code: str | None = None
    category_primary: str | None = None
    category_sub: str | None = None
    weight_grams: int | None = Field(default=None, ge=0)
    dimensions_cm_length: Decimal | None = Field(default=None, ge=0)
    dimensions_cm_width: Decimal | None = Field(default=None, ge=0)
    dimensions_cm_height: Decimal | None = Field(default=None, ge=0)
    mrp_paise: int = Field(ge=0)
    cost_price_paise: int = Field(ge=0)
    gst_rate: int

    @field_validator("gst_rate")
    @classmethod
    def _validate_gst_rate(cls, v: int) -> int:
        if v not in _ALLOWED_GST_RATES:
            raise ValueError(f"gst_rate must be one of {_ALLOWED_GST_RATES}")
        return v


class ProductUpdate(BaseModel):
    internal_sku: str | None = Field(default=None, min_length=1)
    product_name: str | None = Field(default=None, min_length=1)
    hsn_code: str | None = None
    category_primary: str | None = None
    category_sub: str | None = None
    weight_grams: int | None = Field(default=None, ge=0)
    dimensions_cm_length: Decimal | None = Field(default=None, ge=0)
    dimensions_cm_width: Decimal | None = Field(default=None, ge=0)
    dimensions_cm_height: Decimal | None = Field(default=None, ge=0)
    mrp_paise: int | None = Field(default=None, ge=0)
    cost_price_paise: int | None = Field(default=None, ge=0)
    gst_rate: int | None = None

    @field_validator("gst_rate")
    @classmethod
    def _validate_gst_rate(cls, v: int | None) -> int | None:
        if v is not None and v not in _ALLOWED_GST_RATES:
            raise ValueError(f"gst_rate must be one of {_ALLOWED_GST_RATES}")
        return v
