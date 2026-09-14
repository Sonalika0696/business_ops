"""Auth: register/login happy path + duplicate-email rejection, and
`get_current_seller`'s rejection of missing/garbage/expired tokens.
"""

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from jose import jwt

from app.core.config import get_settings


def _unique_email() -> str:
    return f"seller-{uuid.uuid4().hex[:12]}@example.test"


async def test_register_and_login_happy_path(client: AsyncClient) -> None:
    email = _unique_email()
    register_resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "correct-horse-1", "legal_name": "Acme Traders"},
    )
    assert register_resp.status_code == 201
    body = register_resp.json()
    assert "seller_id" in body
    uuid.UUID(body["seller_id"])  # valid uuid

    login_resp = await client.post(
        "/api/auth/login", json={"email": email, "password": "correct-horse-1"}
    )
    assert login_resp.status_code == 200
    login_body = login_resp.json()
    assert login_body["token_type"] == "bearer"
    assert login_body["access_token"]


async def test_register_duplicate_email_rejected(client: AsyncClient) -> None:
    email = _unique_email()
    payload = {"email": email, "password": "correct-horse-1", "legal_name": "Acme Traders"}

    first = await client.post("/api/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/auth/register", json=payload)
    assert second.status_code == 409
    body = second.json()
    assert body["error"]["code"] == "conflict"
    assert body["error"]["field_errors"] == {"email": "already registered"}


async def test_register_duplicate_email_case_insensitive(client: AsyncClient) -> None:
    """Seller.email is CITEXT (case-insensitive unique) per DESIGN.md §2.1."""
    email = _unique_email()
    payload = {"email": email, "password": "correct-horse-1", "legal_name": "Acme Traders"}
    first = await client.post("/api/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post(
        "/api/auth/register", json={**payload, "email": email.upper()}
    )
    assert second.status_code == 409


async def test_login_wrong_password_rejected(client: AsyncClient) -> None:
    email = _unique_email()
    payload = {"email": email, "password": "correct-horse-1", "legal_name": "Acme Traders"}
    await client.post("/api/auth/register", json=payload)

    resp = await client.post("/api/auth/login", json={"email": email, "password": "wrong-pass"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


async def test_login_unknown_email_rejected(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/login", json={"email": _unique_email(), "password": "whatever1"}
    )
    assert resp.status_code == 401


async def test_get_current_seller_rejects_missing_token(client: AsyncClient) -> None:
    resp = await client.get("/api/sellers/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


async def test_get_current_seller_rejects_garbage_token(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/sellers/me", headers={"Authorization": "Bearer not-a-real-jwt"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


async def test_get_current_seller_rejects_expired_token(client: AsyncClient) -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    expired_payload = {
        "sub": str(uuid.uuid4()),
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }
    token = jwt.encode(expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    resp = await client.get("/api/sellers/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


async def test_get_current_seller_rejects_deleted_seller_subject(client: AsyncClient) -> None:
    """A well-formed, unexpired token for a seller id that doesn't exist -> 401."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": str(uuid.uuid4()), "iat": now, "exp": now + timedelta(hours=1)}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    resp = await client.get("/api/sellers/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
