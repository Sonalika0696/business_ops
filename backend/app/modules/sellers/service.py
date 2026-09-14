"""Seller profile service — DESIGN.md §6 (`GET/PATCH /api/sellers/me`)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sellers.models import Seller
from app.modules.sellers.schemas import SellerUpdate


async def update_seller(db: AsyncSession, seller: Seller, payload: SellerUpdate) -> Seller:
    """Apply only the fields the client actually sent (partial update)."""
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(seller, field, value)
    await db.commit()
    await db.refresh(seller)
    return seller


__all__ = ["update_seller"]
