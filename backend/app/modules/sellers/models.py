"""Seller — DESIGN.md §2.1 (single-tenant for the prototype)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import MsmeClassification
from app.db_base import Base

if TYPE_CHECKING:
    from app.modules.masters.models import Product, SellerMarketplaceAccount


class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    legal_name: Mapped[str] = mapped_column(Text, nullable=False)
    trade_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    # [+] auth identity (DESIGN.md §2.1 / SDD §9: "JWT simple email/password")
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)  # [+]

    gstin: Mapped[str | None] = mapped_column(Text, nullable=True)
    pan: Mapped[str | None] = mapped_column(Text, nullable=True)
    udyam_registration_number: Mapped[str | None] = mapped_column(Text, nullable=True)

    msme_classification: Mapped[MsmeClassification] = mapped_column(
        Enum(
            MsmeClassification,
            name="msme_classification",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        server_default=text("'NONE'"),
    )

    primary_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_pincode: Mapped[str | None] = mapped_column(Text, nullable=True)
    principal_place_of_business: Mapped[str | None] = mapped_column(Text, nullable=True)

    bank_account_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    bank_ifsc: Mapped[str | None] = mapped_column(Text, nullable=True)
    bank_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=text("now()"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # [+] soft delete

    marketplace_accounts: Mapped[list["SellerMarketplaceAccount"]] = relationship(
        "SellerMarketplaceAccount", back_populates="seller"
    )
    products: Mapped[list["Product"]] = relationship("Product", back_populates="seller")
