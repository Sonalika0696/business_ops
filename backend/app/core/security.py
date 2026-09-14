"""Password hashing and JWT helpers.

JWT library choice: `python-jose[cryptography]` (not PyJWT) — chosen because
it ships HS256/RS256 support and a JWTError hierarchy that's convenient to
catch in the exception handlers (app/core/errors.py) without pulling in a
second crypto backend. Documented here per DESIGN.md §1's "JWT (python-jose
or PyJWT)" — this is the decided branch.

No auth business logic lives here yet (Phase 1 scaffolding only) — these are
just the primitive helpers later `modules/auth/service.py` will call.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a signed JWT for `subject` (typically the seller id), expiring per settings."""
    settings = get_settings()
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "iat": now, "exp": expires_at}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT, raising `jose.JWTError` on any invalid/expired token."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


__all__ = [
    "JWTError",
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "verify_password",
]
