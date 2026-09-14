"""Shared FastAPI auth dependency.

`get_current_seller` is the guard every router in the app (auth-protected
sellers/masters routes now; ingestion/reconciliation routers later) imports
via `current_seller: Seller = Depends(get_current_seller)`. It decodes the
bearer JWT (app.core.security), loads the corresponding `Seller` row, and
raises the frozen 401 error envelope (DESIGN.md §6) on any failure: missing
token, malformed/expired token, or a seller that no longer exists / has been
soft-deleted.
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import JWTError, decode_access_token
from app.modules.sellers.models import Seller

# tokenUrl is documentation-only here (points Swagger's "Authorize" flow at
# the login endpoint) — token validation itself happens below, not via this
# scheme object. auto_error=False so we can raise our own error-envelope
# shape uniformly instead of FastAPI's default "Not authenticated" detail.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

_UNAUTHORIZED_DETAIL = {
    "code": "unauthorized",
    "message": "Could not validate credentials.",
    "field_errors": None,
}


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_UNAUTHORIZED_DETAIL)


async def authenticate_token(token: str | None, db: AsyncSession) -> Seller | None:
    """Core token -> Seller resolution, shared by header auth (`get_current_seller`,
    below) and query-param auth (the `/ws/settlements/{id}` route, DESIGN.md §4's
    documented exception to header-only auth). Returns `None` on any failure
    (missing/malformed/expired token, unknown or soft-deleted seller) rather
    than raising — callers decide how to surface that (a 401 HTTPException for
    HTTP routes via `get_current_seller`; a WS close code for the WS route,
    which can't return an HTTP response)."""
    if not token:
        return None

    try:
        payload = decode_access_token(token)
    except JWTError:
        return None

    subject = payload.get("sub")
    if not subject:
        return None

    try:
        seller_id = uuid.UUID(str(subject))
    except ValueError:
        return None

    result = await db.execute(
        select(Seller).where(Seller.id == seller_id, Seller.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_current_seller(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Seller:
    seller = await authenticate_token(token, db)
    if seller is None:
        raise _unauthorized()
    return seller


__all__ = ["authenticate_token", "get_current_seller", "oauth2_scheme"]
