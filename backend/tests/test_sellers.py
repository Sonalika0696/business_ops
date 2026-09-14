"""GET/PATCH /api/sellers/me — profile read + partial update, both behind auth."""

import uuid

from httpx import AsyncClient


def _unique_email() -> str:
    return f"seller-{uuid.uuid4().hex[:12]}@example.test"


async def _register_and_login(client: AsyncClient) -> tuple[str, str]:
    email = _unique_email()
    payload = {"email": email, "password": "correct-horse-1", "legal_name": "Acme Traders"}
    register_resp = await client.post("/api/auth/register", json=payload)
    assert register_resp.status_code == 201
    seller_id = register_resp.json()["seller_id"]

    login_resp = await client.post(
        "/api/auth/login", json={"email": email, "password": "correct-horse-1"}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    return seller_id, token


async def test_get_me(client: AsyncClient) -> None:
    seller_id, token = await _register_and_login(client)
    resp = await client.get("/api/sellers/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == seller_id
    assert body["legal_name"] == "Acme Traders"
    assert "hashed_password" not in body
    assert "password" not in body


async def test_get_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/sellers/me")
    assert resp.status_code == 401


async def test_patch_me_partial_update(client: AsyncClient) -> None:
    _, token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.patch(
        "/api/sellers/me",
        json={"trade_name": "Acme Fast Traders", "primary_state": "Maharashtra"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["trade_name"] == "Acme Fast Traders"
    assert body["primary_state"] == "Maharashtra"

    # Fields not sent in the PATCH are left untouched.
    get_resp = await client.get("/api/sellers/me", headers=headers)
    assert get_resp.json()["legal_name"] == "Acme Traders"


async def test_patch_me_rejects_bad_msme_classification(client: AsyncClient) -> None:
    _, token = await _register_and_login(client)
    resp = await client.patch(
        "/api/sellers/me",
        json={"msme_classification": "NOT_A_REAL_VALUE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "validation_error"
    assert "msme_classification" in body["error"]["field_errors"]
