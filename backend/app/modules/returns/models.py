"""Return — DESIGN.md §2.11. Schema-only in Phase 1; return-to-refund logic is Phase 2."""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, Enum, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    ClaimStatus,
    InventoryDisposition,
    ReturnReason,
    ReturnStatus,
    ReturnType,
)
from app.db_base import Base

if TYPE_CHECKING:
    from app.modules.masters.models import Marketplace
    from app.modules.reconciliation.models import Order


class Return(Base):
    __tablename__ = "returns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    return_marketplace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("marketplaces.id"), nullable=False
    )
    return_reason: Mapped[ReturnReason] = mapped_column(
        Enum(
            ReturnReason, name="return_reason", values_callable=lambda obj: [e.value for e in obj]
        ),
        nullable=False,
    )
    return_type: Mapped[ReturnType] = mapped_column(
        Enum(ReturnType, name="return_type", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    return_status: Mapped[ReturnStatus] = mapped_column(
        Enum(
            ReturnStatus, name="return_status", values_callable=lambda obj: [e.value for e in obj]
        ),
        nullable=False,
        server_default=text("'INITIATED'"),
    )
    initiated_date: Mapped[date] = mapped_column(Date, nullable=False)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    refund_amount_expected_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    refund_amount_credited_paise: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    reimbursement_amount_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    inventory_disposition: Mapped[InventoryDisposition | None] = mapped_column(
        Enum(
            InventoryDisposition,
            name="inventory_disposition",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )
    claim_status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus, name="claim_status", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        server_default=text("'NOT_CLAIMED'"),
    )
    claim_window_expires: Mapped[date | None] = mapped_column(Date, nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="returns")
    return_marketplace: Mapped["Marketplace"] = relationship(
        "Marketplace", back_populates="returns"
    )
