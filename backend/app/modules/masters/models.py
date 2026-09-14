"""Masters — DESIGN.md §2.2 (Marketplace), §2.3 (SellerMarketplaceAccount), §2.4 (Product)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import FulfillmentType, MarketplaceCode
from app.db_base import Base

if TYPE_CHECKING:
    from app.modules.audit.models import AuditEvent  # noqa: F401
    from app.modules.ingestion.models import SettlementReport
    from app.modules.pricing.models import FeeSchedule, SKUMarketplaceListing
    from app.modules.reconciliation.models import Order
    from app.modules.returns.models import Return
    from app.modules.sellers.models import Seller

# GST rate is modeled as a restricted SMALLINT domain (CHECK constraint)
# rather than a native Postgres ENUM: the legal values (0, 5, 12, 18, 28)
# are GST percentages that later phases do arithmetic with (fee/tax
# computation), so keeping the column an integer is more useful than a
# string-labeled enum type while still exactly matching DESIGN.md's
# "enum(0, 5, 12, 18, 28)" value set. The `GstRate` IntEnum in
# app.core.enums is the application-level representation of this same set.
_GST_RATE_VALUES = (0, 5, 12, 18, 28)


class Marketplace(Base):
    """Reference/seed data — not seller-scoped. Seeded via scripts/seed_reference_data.py."""

    __tablename__ = "marketplaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    code: Mapped[MarketplaceCode] = mapped_column(
        Enum(
            MarketplaceCode,
            name="marketplace_code",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        unique=True,
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    settlement_frequency_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    payout_split_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("1")
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    seller_accounts: Mapped[list["SellerMarketplaceAccount"]] = relationship(
        "SellerMarketplaceAccount", back_populates="marketplace"
    )
    fee_schedules: Mapped[list["FeeSchedule"]] = relationship(
        "FeeSchedule", back_populates="marketplace"
    )
    returns: Mapped[list["Return"]] = relationship(
        "Return", back_populates="return_marketplace"
    )


class SellerMarketplaceAccount(Base):
    __tablename__ = "seller_marketplace_accounts"
    __table_args__ = (
        UniqueConstraint(
            "seller_id",
            "marketplace_id",
            "merchant_id_on_platform",
            name="uq_seller_marketplace_account_seller_marketplace_merchant",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sellers.id"), nullable=False
    )
    marketplace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("marketplaces.id"), nullable=False
    )
    merchant_id_on_platform: Mapped[str] = mapped_column(Text, nullable=False)
    warehouse_pincode: Mapped[str | None] = mapped_column(Text, nullable=True)
    fulfillment_type: Mapped[FulfillmentType] = mapped_column(
        Enum(
            FulfillmentType,
            name="fulfillment_type",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    activated_on: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=text("current_date")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="marketplace_accounts")
    marketplace: Mapped["Marketplace"] = relationship(
        "Marketplace", back_populates="seller_accounts"
    )
    listings: Mapped[list["SKUMarketplaceListing"]] = relationship(
        "SKUMarketplaceListing", back_populates="seller_marketplace_account"
    )
    orders: Mapped[list["Order"]] = relationship(
        "Order", back_populates="seller_marketplace_account"
    )
    settlement_reports: Mapped[list["SettlementReport"]] = relationship(
        "SettlementReport", back_populates="seller_marketplace_account"
    )


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            f"gst_rate IN {_GST_RATE_VALUES}",
            name="ck_products_gst_rate_valid",
        ),
        # unique(seller_id, internal_sku) WHERE deleted_at IS NULL — a partial
        # unique index, since a soft-deleted SKU must not block re-creating
        # the same internal_sku for the same seller. Postgres only supports
        # partial uniqueness via a partial unique INDEX, not a table-level
        # UniqueConstraint (which cannot carry a WHERE clause).
        Index(
            "uq_products_seller_internal_sku",
            "seller_id",
            "internal_sku",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sellers.id"), nullable=False
    )
    internal_sku: Mapped[str] = mapped_column(Text, nullable=False)
    product_name: Mapped[str] = mapped_column(Text, nullable=False)
    hsn_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_primary: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_sub: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dimensions_cm_length: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    dimensions_cm_width: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    dimensions_cm_height: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    mrp_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cost_price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    gst_rate: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="products")
    listings: Mapped[list["SKUMarketplaceListing"]] = relationship(
        "SKUMarketplaceListing", back_populates="product"
    )
