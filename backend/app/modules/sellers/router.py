"""Seller profile routes — DESIGN.md §6.

GET   /api/sellers/me -> 200 Seller
PATCH /api/sellers/me -> 200 Seller

Both behind `get_current_seller`.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_seller
from app.modules.sellers import service
from app.modules.sellers.models import Seller
from app.modules.sellers.schemas import SellerRead, SellerUpdate

router = APIRouter(prefix="/api/sellers", tags=["sellers"])


@router.get("/me", response_model=SellerRead)
async def get_me(current_seller: Seller = Depends(get_current_seller)) -> Seller:
    return current_seller


@router.patch("/me", response_model=SellerRead)
async def update_me(
    payload: SellerUpdate,
    current_seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> Seller:
    return await service.update_seller(db, current_seller, payload)
