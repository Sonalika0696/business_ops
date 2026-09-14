"""Masters routes — DESIGN.md §6.

    GET    /api/marketplaces                      -> 200 { items }
    GET    /api/marketplace-accounts               -> 200 { items, total }
    POST   /api/marketplace-accounts                -> 201
    GET    /api/marketplace-accounts/{id}            -> 200
    PATCH  /api/marketplace-accounts/{id}            -> 200
    DELETE /api/marketplace-accounts/{id}            -> 204
    GET    /api/products                            -> 200 { items, total }
    POST   /api/products                             -> 201
    GET    /api/products/{id}                        -> 200
    PATCH  /api/products/{id}                        -> 200
    DELETE /api/products/{id}                        -> 204

One router covers all three resources (they share the module's service
layer); prefixes differ per resource so paths are declared explicitly
rather than via a single `APIRouter(prefix=...)`.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_seller
from app.modules.masters import service
from app.modules.masters.schemas import (
    MarketplaceListResponse,
    ProductCreate,
    ProductListResponse,
    ProductRead,
    ProductUpdate,
    SellerMarketplaceAccountCreate,
    SellerMarketplaceAccountListResponse,
    SellerMarketplaceAccountRead,
    SellerMarketplaceAccountUpdate,
)
from app.modules.sellers.models import Seller

router = APIRouter(tags=["masters"])

_NOT_FOUND_DETAIL = {"code": "not_found", "message": "Resource not found.", "field_errors": None}
_UNKNOWN_MARKETPLACE_DETAIL = {
    "code": "validation_error",
    "message": "Unknown marketplace_code.",
    "field_errors": {"marketplace_code": "does not match a known marketplace"},
}


def _duplicate_detail(message: str, field: str | None = None) -> dict:
    return {
        "code": "conflict",
        "message": message,
        "field_errors": {field: "already exists"} if field else None,
    }


def _pagination(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> tuple[int, int]:
    return page, page_size


# ---------------------------------------------------------------------------
# Marketplace (read-only reference data — no auth-scoping needed)
# ---------------------------------------------------------------------------


@router.get("/api/marketplaces", response_model=MarketplaceListResponse)
async def list_marketplaces(db: AsyncSession = Depends(get_db)) -> MarketplaceListResponse:
    marketplaces = await service.list_marketplaces(db)
    return MarketplaceListResponse(items=marketplaces)


# ---------------------------------------------------------------------------
# SellerMarketplaceAccount
# ---------------------------------------------------------------------------


@router.get("/api/marketplace-accounts", response_model=SellerMarketplaceAccountListResponse)
async def list_marketplace_accounts(
    pagination: tuple[int, int] = Depends(_pagination),
    current_seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> SellerMarketplaceAccountListResponse:
    page, page_size = pagination
    items, total = await service.list_marketplace_accounts(
        db, current_seller.id, page, page_size
    )
    return SellerMarketplaceAccountListResponse(items=items, total=total)


@router.post(
    "/api/marketplace-accounts",
    response_model=SellerMarketplaceAccountRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_marketplace_account(
    payload: SellerMarketplaceAccountCreate,
    current_seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> SellerMarketplaceAccountRead:
    try:
        account = await service.create_marketplace_account(db, current_seller.id, payload)
    except service.UnknownMarketplaceCodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_UNKNOWN_MARKETPLACE_DETAIL,
        ) from exc
    except service.DuplicateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_duplicate_detail(
                "An account with this marketplace and merchant id already exists."
            ),
        ) from exc
    return account


@router.get("/api/marketplace-accounts/{account_id}", response_model=SellerMarketplaceAccountRead)
async def get_marketplace_account(
    account_id: uuid.UUID,
    current_seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> SellerMarketplaceAccountRead:
    try:
        return await service.get_marketplace_account(db, current_seller.id, account_id)
    except service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL
        ) from exc


@router.patch(
    "/api/marketplace-accounts/{account_id}", response_model=SellerMarketplaceAccountRead
)
async def update_marketplace_account(
    account_id: uuid.UUID,
    payload: SellerMarketplaceAccountUpdate,
    current_seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> SellerMarketplaceAccountRead:
    try:
        return await service.update_marketplace_account(
            db, current_seller.id, account_id, payload
        )
    except service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL
        ) from exc
    except service.DuplicateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_duplicate_detail(
                "An account with this marketplace and merchant id already exists."
            ),
        ) from exc


@router.delete("/api/marketplace-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_marketplace_account(
    account_id: uuid.UUID,
    current_seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await service.delete_marketplace_account(db, current_seller.id, account_id)
    except service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL
        ) from exc


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------


@router.get("/api/products", response_model=ProductListResponse)
async def list_products(
    pagination: tuple[int, int] = Depends(_pagination),
    current_seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> ProductListResponse:
    page, page_size = pagination
    items, total = await service.list_products(db, current_seller.id, page, page_size)
    return ProductListResponse(items=items, total=total)


@router.post("/api/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    current_seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> ProductRead:
    try:
        return await service.create_product(db, current_seller.id, payload)
    except service.DuplicateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_duplicate_detail(
                "A product with this internal_sku already exists.", "internal_sku"
            ),
        ) from exc


@router.get("/api/products/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: uuid.UUID,
    current_seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> ProductRead:
    try:
        return await service.get_product(db, current_seller.id, product_id)
    except service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL
        ) from exc


@router.patch("/api/products/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    current_seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> ProductRead:
    try:
        return await service.update_product(db, current_seller.id, product_id, payload)
    except service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL
        ) from exc
    except service.DuplicateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_duplicate_detail(
                "A product with this internal_sku already exists.", "internal_sku"
            ),
        ) from exc


@router.delete("/api/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: uuid.UUID,
    current_seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> None:
    try:
        await service.delete_product(db, current_seller.id, product_id)
    except service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND_DETAIL
        ) from exc
