"""Masters: GET /api/marketplaces (seeded reference rows), marketplace-account
CRUD (marketplace_code resolution + soft delete), and product CRUD (pagination,
soft-delete-excluded-from-list, duplicate-SKU 409, field_errors validation).
"""

import uuid

from httpx import AsyncClient


def _unique_email() -> str:
    return f"seller-{uuid.uuid4().hex[:12]}@example.test"


def _unique_sku() -> str:
    return f"SKU-{uuid.uuid4().hex[:10]}"


async def _auth_headers(client: AsyncClient) -> dict:
    email = _unique_email()
    payload = {"email": email, "password": "correct-horse-1", "legal_name": "Acme Traders"}
    await client.post("/api/auth/register", json=payload)
    login_resp = await client.post(
        "/api/auth/login", json={"email": email, "password": "correct-horse-1"}
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Marketplace (reference data)
# ---------------------------------------------------------------------------


async def test_list_marketplaces_returns_seeded_rows(
    client: AsyncClient, seed_marketplaces: None
) -> None:
    resp = await client.get("/api/marketplaces")
    assert resp.status_code == 200
    body = resp.json()
    codes = {item["code"] for item in body["items"]}
    assert {"AMAZON_IN", "FLIPKART", "MEESHO"} <= codes


# ---------------------------------------------------------------------------
# SellerMarketplaceAccount
# ---------------------------------------------------------------------------


async def test_marketplace_account_create_resolves_code(
    client: AsyncClient, seed_marketplaces: None
) -> None:
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/marketplace-accounts",
        json={
            "marketplace_code": "AMAZON_IN",
            "merchant_id_on_platform": "MERCHANT-1",
            "fulfillment_type": "SELF_SHIP",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["merchant_id_on_platform"] == "MERCHANT-1"
    assert body["marketplace_id"]  # resolved server-side, not echoed from the request

    get_resp = await client.get(f"/api/marketplace-accounts/{body['id']}", headers=headers)
    assert get_resp.status_code == 200

    list_resp = await client.get("/api/marketplace-accounts", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1


async def test_marketplace_account_unknown_code_rejected(client: AsyncClient) -> None:
    """`marketplace_code` is a closed enum (DESIGN.md §2.2) — a value outside
    AMAZON_IN/FLIPKART/MEESHO fails request validation before it ever reaches
    the marketplace lookup."""
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/marketplace-accounts",
        json={
            "marketplace_code": "SNAPDEAL",
            "merchant_id_on_platform": "MERCHANT-1",
            "fulfillment_type": "SELF_SHIP",
        },
        headers=headers,
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "validation_error"
    assert "marketplace_code" in body["error"]["field_errors"]


async def test_marketplace_account_update_and_soft_delete(
    client: AsyncClient, seed_marketplaces: None
) -> None:
    headers = await _auth_headers(client)
    create_resp = await client.post(
        "/api/marketplace-accounts",
        json={
            "marketplace_code": "FLIPKART",
            "merchant_id_on_platform": "MERCHANT-2",
            "fulfillment_type": "FLIPKART_ADVANTAGE",
        },
        headers=headers,
    )
    account_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/marketplace-accounts/{account_id}",
        json={"warehouse_pincode": "400001"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["warehouse_pincode"] == "400001"

    delete_resp = await client.delete(f"/api/marketplace-accounts/{account_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_after_delete = await client.get(
        f"/api/marketplace-accounts/{account_id}", headers=headers
    )
    assert get_after_delete.status_code == 404

    list_after_delete = await client.get("/api/marketplace-accounts", headers=headers)
    assert all(a["id"] != account_id for a in list_after_delete.json()["items"])


async def test_marketplace_account_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/marketplace-accounts")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------


async def test_product_crud_and_soft_delete(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    sku = _unique_sku()

    create_resp = await client.post(
        "/api/products",
        json={
            "internal_sku": sku,
            "product_name": "Blue Widget",
            "mrp_paise": 99900,
            "cost_price_paise": 50000,
            "gst_rate": 18,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    product = create_resp.json()
    product_id = product["id"]
    assert product["internal_sku"] == sku

    get_resp = await client.get(f"/api/products/{product_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["internal_sku"] == sku

    patch_resp = await client.patch(
        f"/api/products/{product_id}", json={"product_name": "Blue Widget v2"}, headers=headers
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["product_name"] == "Blue Widget v2"
    # untouched fields survive the partial update
    assert patch_resp.json()["internal_sku"] == sku

    list_resp = await client.get("/api/products", headers=headers)
    assert list_resp.status_code == 200
    assert any(p["id"] == product_id for p in list_resp.json()["items"])

    delete_resp = await client.delete(f"/api/products/{product_id}", headers=headers)
    assert delete_resp.status_code == 204

    # Soft-deleted products are excluded from list...
    list_after_delete = await client.get("/api/products", headers=headers)
    assert all(p["id"] != product_id for p in list_after_delete.json()["items"])

    # ...and from get (404, not a raw 500 / silent success).
    get_after_delete = await client.get(f"/api/products/{product_id}", headers=headers)
    assert get_after_delete.status_code == 404
    assert get_after_delete.json()["error"]["code"] == "not_found"


async def test_product_duplicate_sku_rejected(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    sku = _unique_sku()
    payload = {
        "internal_sku": sku,
        "product_name": "Red Widget",
        "mrp_paise": 49900,
        "cost_price_paise": 20000,
        "gst_rate": 5,
    }
    first = await client.post("/api/products", json=payload, headers=headers)
    assert first.status_code == 201

    second = await client.post("/api/products", json=payload, headers=headers)
    assert second.status_code == 409
    body = second.json()
    assert body["error"]["code"] == "conflict"
    assert "internal_sku" in (body["error"]["field_errors"] or {})


async def test_product_sku_reusable_after_soft_delete(client: AsyncClient) -> None:
    """unique(seller_id, internal_sku) WHERE deleted_at IS NULL — DESIGN.md §2.4:
    a soft-deleted SKU must not block re-creating the same internal_sku."""
    headers = await _auth_headers(client)
    sku = _unique_sku()
    payload = {
        "internal_sku": sku,
        "product_name": "Green Widget",
        "mrp_paise": 10000,
        "cost_price_paise": 5000,
        "gst_rate": 0,
    }
    first = await client.post("/api/products", json=payload, headers=headers)
    assert first.status_code == 201
    await client.delete(f"/api/products/{first.json()['id']}", headers=headers)

    second = await client.post("/api/products", json=payload, headers=headers)
    assert second.status_code == 201


async def test_product_validation_errors_use_field_errors_shape(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/products",
        json={
            "internal_sku": _unique_sku(),
            "product_name": "Bad GST",
            "mrp_paise": -100,
            "cost_price_paise": 100,
            "gst_rate": 7,
        },
        headers=headers,
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "validation_error"
    assert "mrp_paise" in body["error"]["field_errors"]
    assert "gst_rate" in body["error"]["field_errors"]


async def test_product_pagination(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    for _ in range(3):
        await client.post(
            "/api/products",
            json={
                "internal_sku": _unique_sku(),
                "product_name": "Paginated Widget",
                "mrp_paise": 1000,
                "cost_price_paise": 500,
                "gst_rate": 0,
            },
            headers=headers,
        )

    page1 = await client.get("/api/products?page=1&page_size=2", headers=headers)
    assert page1.status_code == 200
    body1 = page1.json()
    assert len(body1["items"]) == 2
    assert body1["total"] == 3

    page2 = await client.get("/api/products?page=2&page_size=2", headers=headers)
    body2 = page2.json()
    assert len(body2["items"]) == 1

    too_big = await client.get("/api/products?page_size=101", headers=headers)
    assert too_big.status_code == 422


async def test_product_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/products")
    assert resp.status_code == 401


async def test_product_scoped_to_owning_seller(client: AsyncClient) -> None:
    headers_a = await _auth_headers(client)
    headers_b = await _auth_headers(client)

    create_resp = await client.post(
        "/api/products",
        json={
            "internal_sku": _unique_sku(),
            "product_name": "Seller A's Widget",
            "mrp_paise": 1000,
            "cost_price_paise": 500,
            "gst_rate": 0,
        },
        headers=headers_a,
    )
    product_id = create_resp.json()["id"]

    # Seller B cannot see or touch seller A's product.
    get_resp = await client.get(f"/api/products/{product_id}", headers=headers_b)
    assert get_resp.status_code == 404

    list_resp = await client.get("/api/products", headers=headers_b)
    assert all(p["id"] != product_id for p in list_resp.json()["items"])
