"""Auth routes — DESIGN.md §6.

POST /api/auth/register -> 201 { seller_id }
POST /api/auth/login    -> 200 { access_token, token_type }
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.modules.auth import service
from app.modules.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_DUPLICATE_EMAIL_DETAIL = {
    "code": "conflict",
    "message": "An account with this email already exists.",
    "field_errors": {"email": "already registered"},
}

_INVALID_CREDENTIALS_DETAIL = {
    "code": "unauthorized",
    "message": "Invalid email or password.",
    "field_errors": None,
}


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> RegisterResponse:
    try:
        seller = await service.register_seller(db, payload)
    except service.DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=_DUPLICATE_EMAIL_DETAIL
        ) from exc
    return RegisterResponse(seller_id=seller.id)


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        seller = await service.authenticate_seller(db, payload)
    except service.InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_CREDENTIALS_DETAIL
        ) from exc
    return service.issue_token(seller)
