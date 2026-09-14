"""Reconciliation — DESIGN.md §2.6 (Order) and §2.7 (OrderLineItem).

Phase 1 populates these only via the synthetic generator (scripts/
synth_data_generator.py) — there is no live order-ingestion API yet.
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import OrderStatus, PaymentType, ShippingZone
from app.db_base import Base

if TYPE_CHECKING:
    from app.modules.ingestion.models import SettlementLineItem
    from app.modules.masters.models import SellerMarketplaceAccount
    from app.modules.pricing.models import SKUMarketplaceListing
    from app.modules.returns.models import Return

_GST_RATE_VALUES = (0, 5, 12, 18, 28)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint(
            "seller_marketplace_account_id",
            "marketplace_order_id",
            name="uq_orders_account_marketplace_order_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    seller_marketplace_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_marketplace_accounts.id"), nullable=False
    )
    marketplace_order_id: Mapped[str] = mapped_column(Text, nullable=False)
    buyer_pincode: Mapped[str | None] = mapped_column(Text, nullable=True)
    buyer_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    order_status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    payment_type: Mapped[PaymentType] = mapped_column(
        Enum(
            PaymentType, name="payment_type", values_callable=lambda obj: [e.value for e in obj]
        ),
        nullable=False,
    )
    total_gross_amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_gst_amount_paise: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    total_tcs_deducted_paise: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    total_tds_deducted_paise: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    shipping_zone: Mapped[ShippingZone | None] = mapped_column(
        Enum(
            ShippingZone,
            name="shipping_zone",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    seller_marketplace_account: Mapped["SellerMarketplaceAccount"] = relationship(
        "SellerMarketplaceAccount", back_populates="orders"
    )
    line_items: Mapped[list["OrderLineItem"]] = relationship(
        "OrderLineItem", back_populates="order"
    )
    settlement_line_items: Mapped[list["SettlementLineItem"]] = relationship(
        "SettlementLineItem", back_populates="order"
    )
    returns: Mapped[list["Return"]] = relationship("Return", back_populates="order")


class OrderLineItem(Base):
    __tablename__ = "order_line_items"
    __table_args__ = (
        CheckConstraint(
            f"unit_gst_rate IN {_GST_RATE_VALUES}",
            name="ck_order_line_items_unit_gst_rate_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    # [+] nullable in Phase 1 since listing-sync isn't populated yet — see
    # DESIGN.md §2.7 note: the synthetic generator creates a minimal 1:1
    # SKUMarketplaceListing alongside each Product so this FK chain still
    # holds, rather than adding a Phase-1-only shortcut column.
    sku_marketplace_listing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sku_marketplace_listings.id"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_before_gst_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    unit_gst_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_gst_amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    line_total_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_applied_paise: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    promotion_code_used: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="line_items")
    sku_marketplace_listing: Mapped["SKUMarketplaceListing | None"] = relationship(
        "SKUMarketplaceListing", back_populates="order_line_items"
    )
