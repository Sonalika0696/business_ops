"""Auth service — register/login business logic (DESIGN.md §6).

Errors are raised as small domain exceptions here and translated to the
frozen error envelope in `router.py` — keeps this module HTTP-agnostic.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.modules.sellers.models import Seller


class DuplicateEmailError(Exception):
    """Raised when registering with an email that already exists."""


class InvalidCredentialsError(Exception):
    """Raised on login with a wrong email/password (or a soft-deleted seller)."""


async def register_seller(db: AsyncSession, payload: RegisterRequest) -> Seller:
    existing = await db.execute(select(Seller).where(Seller.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise DuplicateEmailError

    seller = Seller(
        id=uuid.uuid4(),
        legal_name=payload.legal_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(seller)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateEmailError from exc
    await db.refresh(seller)
    return seller


async def authenticate_seller(db: AsyncSession, payload: LoginRequest) -> Seller:
    result = await db.execute(
        select(Seller).where(Seller.email == payload.email, Seller.deleted_at.is_(None))
    )
    seller = result.scalar_one_or_none()
    if seller is None or not verify_password(payload.password, seller.hashed_password):
        raise InvalidCredentialsError
    return seller


def issue_token(seller: Seller) -> TokenResponse:
    token = create_access_token(subject=str(seller.id))
    return TokenResponse(access_token=token, token_type="bearer")


__all__ = [
    "DuplicateEmailError",
    "InvalidCredentialsError",
    "authenticate_seller",
    "issue_token",
    "register_seller",
]
