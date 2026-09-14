"""Masters service — Marketplace (read-only), SellerMarketplaceAccount, Product.

DESIGN.md §6 endpoint behaviors:
  - marketplace-accounts and products are always scoped to the current
    seller (`seller_id`); list/get exclude soft-deleted rows.
  - POST for marketplace-accounts takes `marketplace_code` and resolves it
    to `marketplace_id` server-side — the client never sends a raw id.
  - DELETE is a soft delete (`deleted_at = now()`), never a hard delete
    (ARCHITECTURE.md §6).
  - Product creation must translate a unique-constraint violation on
    `(seller_id, internal_sku) WHERE deleted_at IS NULL` into a clean 409,
    not a raw 500.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.masters.models import Marketplace, Product, SellerMarketplaceAccount
from app.modules.masters.schemas import (
    ProductCreate,
    ProductUpdate,
    SellerMarketplaceAccountCreate,
    SellerMarketplaceAccountUpdate,
)


class NotFoundError(Exception):
    """Raised when a seller-scoped resource doesn't exist (or belongs to another seller)."""


class DuplicateError(Exception):
    """Raised when a create/update violates a unique constraint."""


class UnknownMarketplaceCodeError(Exception):
    """Raised when `marketplace_code` doesn't match a seeded `Marketplace` row."""


# ---------------------------------------------------------------------------
# Marketplace (reference data, read-only, not seller-scoped)
# ---------------------------------------------------------------------------


async def list_marketplaces(db: AsyncSession) -> list[Marketplace]:
    result = await db.execute(select(Marketplace).order_by(Marketplace.code))
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# SellerMarketplaceAccount
# ---------------------------------------------------------------------------


async def list_marketplace_accounts(
    db: AsyncSession, seller_id: uuid.UUID, page: int, page_size: int
) -> tuple[list[SellerMarketplaceAccount], int]:
    base = select(SellerMarketplaceAccount).where(
        SellerMarketplaceAccount.seller_id == seller_id,
        SellerMarketplaceAccount.deleted_at.is_(None),
    )
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    items_stmt = (
        base.order_by(SellerMarketplaceAccount.activated_on.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(items_stmt)).scalars().all()
    return list(items), total


async def get_marketplace_account(
    db: AsyncSession, seller_id: uuid.UUID, account_id: uuid.UUID
) -> SellerMarketplaceAccount:
    result = await db.execute(
        select(SellerMarketplaceAccount).where(
            SellerMarketplaceAccount.id == account_id,
            SellerMarketplaceAccount.seller_id == seller_id,
            SellerMarketplaceAccount.deleted_at.is_(None),
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise NotFoundError
    return account


async def create_marketplace_account(
    db: AsyncSession, seller_id: uuid.UUID, payload: SellerMarketplaceAccountCreate
) -> SellerMarketplaceAccount:
    marketplace_result = await db.execute(
        select(Marketplace).where(Marketplace.code == payload.marketplace_code)
    )
    marketplace = marketplace_result.scalar_one_or_none()
    if marketplace is None:
        raise UnknownMarketplaceCodeError

    account = SellerMarketplaceAccount(
        id=uuid.uuid4(),
        seller_id=seller_id,
        marketplace_id=marketplace.id,
        merchant_id_on_platform=payload.merchant_id_on_platform,
        warehouse_pincode=payload.warehouse_pincode,
        fulfillment_type=payload.fulfillment_type,
    )
    db.add(account)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateError from exc
    await db.refresh(account)
    return account


async def update_marketplace_account(
    db: AsyncSession,
    seller_id: uuid.UUID,
    account_id: uuid.UUID,
    payload: SellerMarketplaceAccountUpdate,
) -> SellerMarketplaceAccount:
    account = await get_marketplace_account(db, seller_id, account_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateError from exc
    await db.refresh(account)
    return account


async def delete_marketplace_account(
    db: AsyncSession, seller_id: uuid.UUID, account_id: uuid.UUID
) -> None:
    account = await get_marketplace_account(db, seller_id, account_id)
    account.deleted_at = datetime.now(UTC)
    await db.commit()


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------


async def list_products(
    db: AsyncSession, seller_id: uuid.UUID, page: int, page_size: int
) -> tuple[list[Product], int]:
    base = select(Product).where(Product.seller_id == seller_id, Product.deleted_at.is_(None))
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    items_stmt = (
        base.order_by(Product.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = (await db.execute(items_stmt)).scalars().all()
    return list(items), total


async def get_product(db: AsyncSession, seller_id: uuid.UUID, product_id: uuid.UUID) -> Product:
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.seller_id == seller_id,
            Product.deleted_at.is_(None),
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise NotFoundError
    return product


async def create_product(
    db: AsyncSession, seller_id: uuid.UUID, payload: ProductCreate
) -> Product:
    product = Product(id=uuid.uuid4(), seller_id=seller_id, **payload.model_dump())
    db.add(product)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateError from exc
    await db.refresh(product)
    return product


async def update_product(
    db: AsyncSession, seller_id: uuid.UUID, product_id: uuid.UUID, payload: ProductUpdate
) -> Product:
    product = await get_product(db, seller_id, product_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateError from exc
    await db.refresh(product)
    return product


async def delete_product(db: AsyncSession, seller_id: uuid.UUID, product_id: uuid.UUID) -> None:
    product = await get_product(db, seller_id, product_id)
    product.deleted_at = datetime.now(UTC)
    await db.commit()


__all__ = [
    "DuplicateError",
    "NotFoundError",
    "UnknownMarketplaceCodeError",
    "create_marketplace_account",
    "create_product",
    "delete_marketplace_account",
    "delete_product",
    "get_marketplace_account",
    "get_product",
    "list_marketplace_accounts",
    "list_marketplaces",
    "list_products",
    "update_marketplace_account",
    "update_product",
]
