"""Pricing — DESIGN.md §2.5 (SKUMarketplaceListing) and §2.10 (FeeSchedule).

Both are schema-only in Phase 1: no CRUD/sync logic for listings, no
computation engine for fee schedules (DESIGN.md §8). Migrated now so all 12
entities exist from the start, per the Phase 1 exit criterion.
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import FeeType, ListingStatus
from app.db_base import Base

if TYPE_CHECKING:
    from app.modules.masters.models import Marketplace, Product, SellerMarketplaceAccount
    from app.modules.reconciliation.models import OrderLineItem


class SKUMarketplaceListing(Base):
    __tablename__ = "sku_marketplace_listings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    seller_marketplace_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_marketplace_accounts.id"), nullable=False
    )
    marketplace_sku_id: Mapped[str] = mapped_column(Text, nullable=False)  # ASIN / FSN / Meesho id
    marketplace_category_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    selling_price_current_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # [{price_paise, changed_at}]
    selling_price_history: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    stock_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    listing_status: Mapped[ListingStatus] = mapped_column(
        Enum(
            ListingStatus,
            name="listing_status",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        server_default=text("'ACTIVE'"),
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="listings")
    seller_marketplace_account: Mapped["SellerMarketplaceAccount"] = relationship(
        "SellerMarketplaceAccount", back_populates="listings"
    )
    order_line_items: Mapped[list["OrderLineItem"]] = relationship(
        "OrderLineItem", back_populates="sku_marketplace_listing"
    )


class FeeSchedule(Base):
    """Config-not-code substrate (Claim #3) — schema only in Phase 1."""

    __tablename__ = "fee_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    marketplace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("marketplaces.id"), nullable=False
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    category_pattern: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. "Apparel/*"
    fee_type: Mapped[FeeType] = mapped_column(
        Enum(FeeType, name="fee_type", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    # {type: FLAT|PERCENT|TIERED_BY_PRICE|TIERED_BY_WEIGHT|ZONE_BASED, ...}
    computation_rule: Mapped[dict] = mapped_column(JSONB, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    marketplace: Mapped["Marketplace"] = relationship("Marketplace", back_populates="fee_schedules")
