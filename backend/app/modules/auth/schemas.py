"""Auth request/response shapes — DESIGN.md §6.

`email-validator` is not a project dependency (not needed elsewhere), so
email format is validated with a small local regex instead of pydantic's
`EmailStr` — good enough to reject garbage input via the standard
`field_errors` validation-error path without adding a dependency.
"""

import re
import uuid

from pydantic import BaseModel, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(value: str) -> str:
    value = value.strip()
    if not _EMAIL_RE.match(value):
        raise ValueError("invalid email address")
    return value.lower()


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    legal_name: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        return _normalize_email(v)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        return _normalize_email(v)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    seller_id: uuid.UUID
