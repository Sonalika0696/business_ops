# Backend — Phase 1 Technical Design (frozen)

> Derived from `Software_Design_Document.docx` (§5 Data Model, §7 Integration Architecture, §9 Tech Stack) plus
> `../ARCHITECTURE.md`, `../ROADMAP.md`, `../SCOPE.md`, `PLAN.md`.
> This document is the concrete, buildable spec for Phase 1. Once implementation starts against it, the schema and
> contracts below are **frozen** per `../ARCHITECTURE.md` §4 — changes go through `../TRACKING.md`'s contract-freeze
> log, not silent drift in code.

---

## 1. Tech stack (confirmed)

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.12 | |
| Backend framework | FastAPI | async, auto OpenAPI docs, native WebSocket |
| Package/dependency manager | `uv` | pyproject.toml + uv.lock |
| ORM | SQLAlchemy 2.0 (async, `asyncpg` driver) | |
| Migrations | Alembic | one linear history, no branching |
| Database | PostgreSQL 16 | jsonb for `raw_line_data`, `computation_rule`, snapshots |
| Cache / broker | Redis 7 | Celery broker + result backend, WS pub/sub bridge |
| Async workers | Celery | matches SDD §9 exactly |
| Object storage | Local filesystem (`storage/uploads/<sha256>`) | MinIO deferred, zero-budget posture |
| Auth | JWT (python-jose or PyJWT) + passlib/bcrypt | single seller, email/password |
| Testing | pytest, pytest-asyncio, httpx.AsyncClient | |
| Lint/format | ruff | |
| Local orchestration | `docker-compose.yml` (postgres, redis only — app runs via uvicorn locally) | |

**Money:** integer paise (`BigInteger`), never float. **Time:** `TIMESTAMPTZ`, stored UTC; IST display is a frontend concern. **Deletes:** soft-delete (`deleted_at` nullable) on mutable masters; `AuditEvent` and `SettlementLineItem` raw data are strictly append-only, no delete column at all.

---

## 2. The 12 core entities (verbatim from SDD §5, extended only where Phase 1 functionality requires a column the SDD didn't spell out — each extension is flagged `[+]`)

### 2.1 `Seller` (single-tenant for the prototype)
```
id                              uuid, pk
legal_name                      text, not null
trade_name                      text, nullable
email                           citext, unique, not null        [+] auth identity (SDD §9: "JWT simple email/password")
hashed_password                 text, not null                  [+]
gstin                           text, nullable
pan                             text, nullable
udyam_registration_number       text, nullable
msme_classification             enum(MICRO, SMALL, MEDIUM, NONE), default NONE
primary_state                   text, nullable
primary_pincode                 text, nullable
principal_place_of_business     text, nullable
bank_account_number             text, nullable
bank_ifsc                       text, nullable
bank_name                       text, nullable
created_at                      timestamptz, not null, default now()
updated_at                      timestamptz, not null, default now()
deleted_at                      timestamptz, nullable            [+] soft delete
```

### 2.2 `Marketplace` (reference/seed data — not seller-scoped)
```
id                       uuid, pk
code                     enum(AMAZON_IN, FLIPKART, MEESHO), unique, not null
display_name             text, not null
settlement_frequency_days smallint, not null
payout_split_count       smallint, not null default 1
active                   boolean, not null default true
```
Seeded once via `scripts/seed_reference_data.py` (Amazon=1 split/14d, Flipkart=2 splits/7d, Meesho=1 split/15d — placeholder cadences, adjust from real docs if found later).

### 2.3 `SellerMarketplaceAccount`
```
id                          uuid, pk
seller_id                   uuid, fk -> Seller, not null
marketplace_id               uuid, fk -> Marketplace, not null
merchant_id_on_platform      text, not null
warehouse_pincode            text, nullable
fulfillment_type             enum(SELF_SHIP, FBA, FLIPKART_ADVANTAGE, MEESHO_SUPPLIER), not null
activated_on                 date, not null default today
deleted_at                   timestamptz, nullable
unique(seller_id, marketplace_id, merchant_id_on_platform)
```

### 2.4 `Product` (SKU)
```
id                    uuid, pk
seller_id              uuid, fk -> Seller, not null
internal_sku           text, not null
product_name           text, not null
hsn_code                text, nullable
category_primary        text, nullable
category_sub            text, nullable
weight_grams            integer, nullable
dimensions_cm_length     numeric(8,2), nullable
dimensions_cm_width      numeric(8,2), nullable
dimensions_cm_height     numeric(8,2), nullable
mrp_paise                bigint, not null
cost_price_paise         bigint, not null
gst_rate                 enum(0, 5, 12, 18, 28), not null
created_at               timestamptz, not null, default now()
deleted_at               timestamptz, nullable
unique(seller_id, internal_sku) where deleted_at is null
```

### 2.5 `SKUMarketplaceListing`
```
id                              uuid, pk
product_id                       uuid, fk -> Product, not null
seller_marketplace_account_id     uuid, fk -> SellerMarketplaceAccount, not null
marketplace_sku_id                text, not null   -- ASIN / FSN / Meesho id
marketplace_category_id           text, nullable
selling_price_current_paise        bigint, nullable
selling_price_history              jsonb, not null default '[]'   -- [{price_paise, changed_at}]
stock_available                    integer, nullable
listing_status                     enum(ACTIVE, INACTIVE, SUPPRESSED), default ACTIVE
last_synced_at                     timestamptz, nullable
```
*(Schema-only in Phase 1 — no CRUD logic until pricing/listing sync work lands, per `PLAN.md`'s "module boundary interfaces even with only recon populated".)*

### 2.6 `Order`
```
id                              uuid, pk
seller_marketplace_account_id    uuid, fk -> SellerMarketplaceAccount, not null
marketplace_order_id             text, not null
buyer_pincode                    text, nullable
buyer_state                      text, nullable
order_date                       date, not null
order_status                     enum(PLACED, SHIPPED, DELIVERED, CANCELLED, RETURNED, RTO), not null
payment_type                     enum(PREPAID, COD), not null
total_gross_amount_paise          bigint, not null
total_gst_amount_paise            bigint, not null default 0
total_tcs_deducted_paise          bigint, not null default 0
total_tds_deducted_paise          bigint, not null default 0
shipping_zone                    enum(LOCAL, REGIONAL, NATIONAL), nullable
created_at                       timestamptz, not null, default now()
unique(seller_marketplace_account_id, marketplace_order_id)
```
Populated in Phase 1 only via the synthetic generator (§5) — there is no live order-ingestion API yet.

### 2.7 `OrderLineItem`
```
id                                uuid, pk
order_id                           uuid, fk -> Order, not null
sku_marketplace_listing_id          uuid, fk -> SKUMarketplaceListing, nullable   [+] nullable in Phase 1 since listings aren't populated yet; synthetic generator links directly to Product via a Phase-1-only product_id column instead — see note below
quantity                            integer, not null
unit_price_before_gst_paise          bigint, not null
unit_gst_rate                       enum(0, 5, 12, 18, 28), not null
unit_gst_amount_paise                bigint, not null
line_total_paise                     bigint, not null
discount_applied_paise               bigint, not null default 0
promotion_code_used                  text, nullable
```
**Note:** SDD ties `OrderLineItem` to `SKUMarketplaceListing`, which itself needs a `Product`. Since Phase 1 doesn't build listing-sync, the synthetic generator creates a minimal `SKUMarketplaceListing` row alongside each `Product` it seeds (1:1, `marketplace_sku_id = internal_sku`) purely so the FK chain holds — no listing *logic* is exercised, only the row's existence. This keeps the schema exactly as specified without inventing a shortcut FK.

### 2.8 `SettlementReport`
```
id                                  uuid, pk
seller_marketplace_account_id        uuid, fk -> SellerMarketplaceAccount, not null
period_start                        date, not null
period_end                          date, not null
total_gross_sales_paise              bigint, nullable   -- filled after parse
total_fees_paise                     bigint, nullable
total_taxes_deducted_paise           bigint, nullable
total_returns_refunds_paise          bigint, nullable
total_reimbursements_paise           bigint, nullable
net_payout_expected_paise            bigint, nullable
net_payout_bank_credited_paise       bigint, nullable
discrepancy_amount_paise             bigint, nullable   -- computed
file_uploaded_at                     timestamptz, not null, default now()
source_file_hash                     char(64), not null   -- sha256 hex
original_filename                    text, not null        [+]
storage_path                         text, not null        [+]
status                               enum(UPLOADED, PARSING, PARSED, RECONCILING, RECONCILED, FAILED), not null, default UPLOADED   [+] — this *is* the Phase-1 job-lifecycle state for the settlement pipeline (see §4)
row_count                           integer, nullable      [+]
rejected_row_count                   integer, not null default 0   [+]
rejected_rows_detail                 jsonb, not null default '[]'   [+] -- [{row_number, raw_row, reason}], see §9
error_message                        text, nullable         [+]
unique(seller_marketplace_account_id, source_file_hash)   -- idempotency: same file for the same account is a no-op
```

### 2.9 `SettlementLineItem` (the canonical line item — §3 below)
```
id                       uuid, pk
settlement_report_id      uuid, fk -> SettlementReport, not null
order_id                  uuid, fk -> Order, nullable   -- null until matched, or for pure adjustments
amount_description         text, not null    -- raw marketplace string, e.g. "Referral fee – Apparel"
amount_canonical            enum(14 values — §3), not null
amount_value_paise           bigint, not null   -- signed: fees negative, credits positive (sign convention fixed here)
posted_date                 date, not null
currency                    char(3), not null default 'INR'
raw_line_data                jsonb, not null   -- original CSV row, audit
match_status                enum(UNMATCHED, MATCHED_EXACT, MATCHED_FUZZY, ADJUSTMENT), not null default UNMATCHED   [+]
expected_amount_paise        bigint, nullable   [+] — from FeeSchedule once the engine exists (Phase 2); null in Phase 1
deviation_paise              bigint, nullable   [+]
is_anomaly                  boolean, not null default false   [+]
created_at                  timestamptz, not null, default now()
```
**Design note:** there is no separate `Discrepancy`/`Anomaly` table — the SDD's 12 entities do not include one. "Discrepancy queue" and "anomaly review panel" (Module C) are **views over `SettlementLineItem`** (filtered by `match_status`/`is_anomaly`) joined with the matching `AuditEvent` rows written at flag-time (SDD §7.2 step h: *"Insert AuditEvent for every anomaly with hash chain"*). Phase 1 only populates `match_status` (exact matching); `expected_amount_paise`/`deviation_paise`/`is_anomaly` stay null/false until the FeeSchedule engine (Phase 2).

### 2.10 `FeeSchedule` (config-not-code substrate — Claim #3)
```
id                    uuid, pk
marketplace_id         uuid, fk -> Marketplace, not null
effective_from         date, not null
effective_to           date, nullable
category_pattern        text, not null   -- e.g. "Apparel/*"
fee_type                enum(REFERRAL, CLOSING, SHIPPING, FBA, COLLECTION), not null
computation_rule         jsonb, not null   -- {type: FLAT|PERCENT|TIERED_BY_PRICE|TIERED_BY_WEIGHT|ZONE_BASED, ...}
notes                   text, nullable
```
*(Migrated now per the Phase 1 "all 12 entities" exit criterion; no read/write logic until Phase 2's FeeSchedule engine.)*

### 2.11 `Return`
```
id                          uuid, pk
order_id                     uuid, fk -> Order, not null
return_marketplace_id         uuid, fk -> Marketplace, not null
return_reason                enum(DAMAGED, WRONG_ITEM, NOT_AS_DESCRIBED, CHANGE_OF_MIND, DEFECTIVE, RTO_UNDELIVERED), not null
return_type                  enum(CUSTOMER_RETURN, RTO), not null
return_status                enum(INITIATED, IN_TRANSIT, RECEIVED, INSPECTED, REFUNDED, REIMBURSED, DISPUTED), not null default INITIATED
initiated_date                date, not null
received_date                 date, nullable
refund_amount_expected_paise    bigint, not null
refund_amount_credited_paise    bigint, not null default 0
reimbursement_amount_paise      bigint, nullable
inventory_disposition           enum(RESTOCKED, DAMAGED, LOST, DISPOSED, NOT_YET_RETURNED), nullable
claim_status                    enum(NOT_CLAIMED, CLAIMED, APPROVED, REJECTED), not null default NOT_CLAIMED
claim_window_expires             date, nullable
```
*(Schema-only in Phase 1; return-to-refund logic is Phase 2.)*

### 2.12 `AuditEvent` (hash-chained, append-only, tamper-evident)
```
id                     uuid, pk
entity_type             text, not null   -- 'SETTLEMENT_REPORT' | 'ORDER' | 'RETURN' | 'PRICING_CHANGE' | ...
entity_id               uuid, not null
event_type              text, not null   -- 'CREATED' | 'UPDATED' | 'ANOMALY_FLAGGED' | 'DISPUTE_RAISED' | 'RECONCILED'
actor                   text, not null   -- 'system' or seller id/email
before_snapshot          jsonb, nullable
after_snapshot           jsonb, nullable
previous_event_hash       char(64), nullable   -- null only for the very first event ever
this_event_hash           char(64), not null   -- sha256(previous_event_hash + canonical_json(payload))
created_at               timestamptz, not null, default now()
```
Hash chain is global (one chain across all entities, ordered by `created_at`/insertion), not per-entity — simplest tamper-evidence that still lets a single verifier walk the whole log. Insert-only service function `append_audit_event(...)` is the *only* way rows are created; no direct inserts elsewhere.

---

## 3. Canonical settlement line-item contract (frozen — SDD §5.9, §6.B)

`amount_canonical` enum, exactly 14 values:
```
REFERRAL_FEE, CLOSING_FEE, SHIPPING_FEE, COLLECTION_FEE, FBA_FEE, STORAGE_FEE,
ADVERTISING_FEE, PROMOTION_REBATE, TCS, TDS, REFUND, REIMBURSEMENT, ADJUSTMENT, GST_ON_FEE
```
Sign convention: fee/deduction types (`REFERRAL_FEE`, `CLOSING_FEE`, `SHIPPING_FEE`, `COLLECTION_FEE`, `FBA_FEE`, `STORAGE_FEE`, `ADVERTISING_FEE`, `TCS`, `TDS`, `GST_ON_FEE`) are stored **negative**; credit types (`REFUND`, `REIMBURSEMENT`, `PROMOTION_REBATE`, `ADJUSTMENT`) are stored with their **natural sign** (adjustment can be either). This lets a settlement's net payout be a straight `sum(amount_value_paise)`.

The raw-description → canonical mapping (Phase 1 needs only the Amazon subset actually present in the synthetic fixture; Phase 2 fills in the full 40+ table) lives as **data**, not code: `backend/app/canonical/amount_mapping.py` exposes a `dict[str, AmountCanonical]` seeded from a `seed_data/amazon_amount_mapping.csv` file (raw_description → canonical enum), loaded at startup and cached — this is the config-not-code seam the SDD calls out, kept as an editable table from day one even though Phase 1 only needs a handful of rows.

---

## 4. Job-lifecycle contract (frozen)

There is **no dedicated `Job` table** — it is not one of the 12 entities. Phase 1 has exactly one job type (settlement parse+match), and its lifecycle is the `SettlementReport.status` enum itself (`UPLOADED → PARSING → PARSED → RECONCILING → RECONCILED`, or `→ FAILED` with `error_message` set). This *is* the frozen job-lifecycle contract for Phase 1; Phase 2+ job types (metrics runs, PDF export) reuse the same shape — a resource whose own status field is the job state — rather than a generic polymorphic job table, per SDD's actual data model.

**API surface:**
- `POST /api/settlements/upload` → `202 Accepted`, body `{ settlement_report_id, status: "UPLOADED" }`. Enqueues a Celery task `parse_and_reconcile_settlement(settlement_report_id)`.
- `GET /api/settlements/{id}` → current `SettlementReport` row including `status`, `row_count`, `rejected_row_count`, `error_message`.
- `WS /ws/settlements/{id}` → server pushes `{ status, row_count, rejected_row_count }` on every status transition (Celery task calls `update_state` + publishes to Redis channel `settlement:{id}`; a small FastAPI WS endpoint subscribes and forwards). On disconnect, client reconnects — no polling fallback is maintained, per `../ARCHITECTURE.md` §3. **On connect**, before subscribing, the endpoint immediately sends the report's *current* row from the DB (so a client that connects after the job has already progressed, or after it already finished, isn't left waiting for a transition that already happened) — then subscribes for further pushes. **Auth:** a bearer token in the `Authorization` header isn't reliably available to browser WebSocket clients, so this one route takes the JWT as a query parameter instead — `wss://.../ws/settlements/{id}?token=<jwt>` — validated the same way as `get_current_seller`, just read from the query string rather than the header; this is a documented, deliberate exception to the header-auth convention, not a gap. **Redis-publish failures never fail the job**: per `../ARCHITECTURE.md` §11 ("fail open on convenience"), the progress push is UX only — the `SettlementReport.status` row in Postgres is the source of truth. If a Redis publish raises (Redis down, network blip), the task logs a warning and continues; it never lets a WS/progress failure abort or fail the settlement processing itself. **Testability:** the actual row-by-row processing logic must live in a plain function callable directly (not only reachable via the Celery broker), so tests can exercise it without a running Celery worker or Redis — the Celery `@task`-decorated function should be a thin wrapper around that plain function.
- Duplicate upload (same `source_file_hash` for the same `seller_marketplace_account_id`) → `200 OK` with the **existing** report and `{ duplicate: true }`, task is not re-enqueued.

---

## 5. Synthetic data generator (Phase 1 minimum — SDD §8.1)

Standalone script, **not** part of the running app: `backend/scripts/synth_data_generator.py`. Deterministic given a `--seed` argument (default fixed seed for reproducible CI/demo runs).

1. Seed one `Seller` (fixed test identity, e.g. `demo@seller.test`), one `SellerMarketplaceAccount` (Amazon), N=15 `Product` rows spanning a few GST rates/categories, and one `SKUMarketplaceListing` per product (see §2.7 note).
2. Generate M=50 `Order` + one `OrderLineItem` each, spread over a period (e.g. one calendar month), with realistic gross amounts derived from each product's `mrp_paise`.
3. Emit `backend/tests/fixtures/amazon_settlement_sample.txt` in the §9 shape: for ~45 of the 50 orders, emit 3-6 fee/tax lines each (referral + closing + shipping + TCS + TDS + occasional GST_ON_FEE/advertising/storage/promotion/reimbursement), all drawn from the mapping table in §9 with plausible amounts (a simple percentage of the order's gross amount, not the real FeeSchedule math — that engine doesn't exist until Phase 2). The remaining ~5 orders are deliberately left with **no** settlement lines (they'll show up as "expected but not settled" — a discrepancy) and 3-4 extra lines reference an `order-id` that doesn't exist in the `Order` table at all (unmatched/orphan lines — the other discrepancy shape Phase 1 must surface).
4. Emit `backend/tests/fixtures/amazon_settlement_sample.ground_truth.json`: `{"total_orders": 50, "orders_with_settlement_lines": 45, "orders_without_settlement_lines": 5, "orphan_line_count": <n>, "total_line_count": <n>}` — consumed by `scripts/demo_e2e.py` and later the Phase 4 evaluation harness.

This is intentionally thin in Phase 1 (fixed seed, one profile) — configurable profiles/mix/injection-rate is Phase 4's "generator v2".

---

## 6. Phase 1 REST surface (contract-first, frozen shapes only — full OpenAPI grows in code)

```
POST   /api/auth/register            { email, password, legal_name }        -> 201 { seller_id }
POST   /api/auth/login               { email, password }                    -> 200 { access_token, token_type }
GET    /api/sellers/me                                                       -> 200 Seller
PATCH  /api/sellers/me               partial Seller fields                   -> 200 Seller

GET    /api/products                 ?page=&page_size=                       -> 200 { items: Product[], total }
POST   /api/products                 Product create shape                    -> 201 Product
GET    /api/products/{id}                                                     -> 200 Product
PATCH  /api/products/{id}                                                     -> 200 Product
DELETE /api/products/{id}            soft delete                              -> 204

GET    /api/marketplaces                                                      -> 200 { items: Marketplace[] }   -- read-only, the 3 seeded reference rows
GET    /api/marketplace-accounts                                              -> 200 { items: SellerMarketplaceAccount[], total }
POST   /api/marketplace-accounts     { marketplace_code, merchant_id_on_platform, warehouse_pincode?, fulfillment_type } -> 201 SellerMarketplaceAccount
GET    /api/marketplace-accounts/{id}                                          -> 200 SellerMarketplaceAccount
PATCH  /api/marketplace-accounts/{id}  partial (warehouse_pincode, fulfillment_type only — marketplace_code/merchant_id are immutable post-create) -> 200 SellerMarketplaceAccount
DELETE /api/marketplace-accounts/{id}  soft delete                             -> 204

POST   /api/settlements/upload       multipart file + seller_marketplace_account_id -> 202 { settlement_report_id, status }
GET    /api/settlements                                                       -> 200 { items: SettlementReport[], total }
GET    /api/settlements/{id}                                                  -> 200 SettlementReport
WS     /ws/settlements/{id}          progress push                            -> frames { status, row_count, rejected_row_count }

GET    /api/settlements/{id}/line-items   ?match_status=                      -> 200 { items: SettlementLineItem[], total }   -- doubles as the "discrepancy list" (filter match_status=UNMATCHED)
GET    /api/settlements/{id}/rejected-rows                                     -> 200 { items: [{row_number, raw_row, reason}] }
```

Error envelope (all 4xx/5xx): `{ "error": { "code": "string", "message": "string", "field_errors": {"field": "message"} | null } }`. Auth: `Authorization: Bearer <jwt>`; missing/expired → `401 { error: { code: "unauthorized", ... } }`.

---

## 7. Folder structure

```
backend/
  app/
    main.py                    # FastAPI app factory
    core/
      config.py                # pydantic-settings
      db.py                    # async engine/session
      redis.py
      security.py               # JWT + password hashing
      errors.py                 # exception handlers -> error envelope
      enums.py                  # shared enums (money-adjacent, status, etc.)
    canonical/
      amount_mapping.py          # loads seed_data/amazon_amount_mapping.csv
    modules/
      sellers/        models.py, schemas.py, service.py, router.py
      auth/            service.py, router.py
      masters/          (Product, SellerMarketplaceAccount, Marketplace) models.py, schemas.py, service.py, router.py
      ingestion/        models.py (SettlementReport, SettlementLineItem), schemas.py, parsers/{base.py, amazon.py, flipkart.py, meesho.py, __init__.py (dispatch)}, service.py, router.py, tasks.py
      reconciliation/    models.py (Order, OrderLineItem), schemas.py, service.py (exact matcher), router.py
      returns/          models.py (Return)          # schema only, Phase 1
      pricing/          models.py (FeeSchedule, SKUMarketplaceListing)  # schema only, Phase 1
      audit/            models.py (AuditEvent), service.py (append_audit_event, hash chain)
    ws/
      settlement_progress.py
  alembic/
    env.py
    versions/
  seed_data/
    amazon_amount_mapping.csv
    flipkart_amount_mapping.csv
    meesho_amount_mapping.csv
    reference_marketplaces.csv
  scripts/
    synth_data_generator.py
    seed_reference_data.py
    demo_e2e.py                 # Phase 1 exit-criteria demo, run unattended
  tests/
    conftest.py
    fixtures/
    test_auth.py
    test_masters.py
    test_ingestion.py
    test_reconciliation.py
  storage/uploads/               # gitignored
  pyproject.toml
  docker-compose.yml
  alembic.ini
  .env.example
```

---

## 8. Phase 1 Amazon settlement file format + canonical mapping table (frozen)

The SDD's "Amazon Flat File V2" is a real, complex, non-public export format. Byte-exact replication isn't required (SDD §4.1: "realistic synthetic data generation... matching documented schemas" is about plausibility, not certification) — Phase 1 defines its own tractable tab-separated shape, realistic in content, that the synthetic generator emits and the parser consumes. Both must agree on this exact shape; changing it after Phase 1 goes through the same freeze process as everything else here.

**File shape** (`.txt`, tab-separated, UTF-8, header row required):
```
order-id	transaction-type	amount-description	amount	posted-date
```
- `order-id` — matches `Order.marketplace_order_id` for the same `seller_marketplace_account_id`; may be blank for report-level adjustments not tied to an order.
- `transaction-type` — free text from the marketplace (`Order`, `Refund`, `FBA Inventory Fee`, `Service Fee`, ...) — informational only, not parsed into a column; carried into `raw_line_data`.
- `amount-description` — the raw string mapped to a canonical enum via the table below.
- `amount` — decimal rupees (e.g. `-50.00`), parser converts to signed integer paise.
- `posted-date` — `YYYY-MM-DD`.

**Note on "Principal"/sale-value lines:** the 14 canonical enums are exhaustively fee/tax/credit types — there is no "sale value" enum. The base order sale amount lives on `Order.total_gross_amount_paise` (already populated by the synthetic generator) and on `SettlementReport.total_gross_sales_paise` (a report-level rollup, computed by the parser as the sum of matched orders' gross amounts, not from a line item). `SettlementLineItem` rows in Phase 1 therefore represent **only** the fee/tax/credit adjustments layered on top of a sale — real Amazon settlement exports do carry a "Product Charges"/principal line too, but modeling it would require a 15th canonical value the SDD doesn't define, so it's deliberately excluded; reconciliation compares `Order.total_gross_amount_paise + sum(that order's SettlementLineItem.amount_value_paise)` against the report's bank-credited total.

**Canonical mapping table** (`backend/seed_data/amazon_amount_mapping.csv`, columns `raw_description,canonical,sign_hint`) — Phase 1's subset, realistic Amazon India wording, covering all 14 enums at least once:

| raw_description | canonical | stored sign |
|---|---|---|
| Referral fee | REFERRAL_FEE | negative |
| Variable closing fee | CLOSING_FEE | negative |
| Fixed closing fee | CLOSING_FEE | negative |
| Shipping fee | SHIPPING_FEE | negative |
| FBA pick & pack fee | FBA_FEE | negative |
| FBA weight handling fee | FBA_FEE | negative |
| Collection fee | COLLECTION_FEE | negative |
| Monthly storage fee | STORAGE_FEE | negative |
| Sponsored Products charge | ADVERTISING_FEE | negative |
| Coupon redemption fee | PROMOTION_REBATE | negative |
| Promotional rebate | PROMOTION_REBATE | positive |
| TCS-IGST | TCS | negative |
| TCS-CGST | TCS | negative |
| TCS-SGST | TCS | negative |
| TDS Section 194-O | TDS | negative |
| Refund | REFUND | positive (credited back to seller's ledger as a reversal — see note) |
| FBA inventory reimbursement | REIMBURSEMENT | positive |
| CGST on selling fees | GST_ON_FEE | negative |
| SGST on selling fees | GST_ON_FEE | negative |
| IGST on selling fees | GST_ON_FEE | negative |
| Adjustment | ADJUSTMENT | either (from file) |

*(`REFUND`'s sign models the settlement-ledger view — a customer refund is itself a deduction from what the seller nets on that order, so `Refund` rows in the raw file typically arrive as negative amounts in real exports; the generator emits the actual signed rupee amount and the parser trusts the file's sign rather than forcing one, except it raises a rejected-row warning if a row's sign contradicts the "stored sign" hint above by a wide margin — a light sanity check, not a hard rule.)*

`app/canonical/amount_mapping.py` loads this CSV once at startup into a `dict[str, AmountCanonical]` (raw description → enum), case-insensitive exact match. An unmapped description in Phase 1 (no LLM fallback yet — that's Phase 3) is a **rejected row**: logged with reason `"unmapped amount_description: <value>"`, counted in `rejected_row_count` and appended to `rejected_rows_detail` (`{row_number, raw_row, reason}`), never silently dropped or guessed.

---

## 9. Job execution & reconciliation v0 (frozen — the Celery task's exact behavior)

One Celery task, `app.modules.ingestion.tasks.parse_and_reconcile_settlement(settlement_report_id: str)`, drives the entire §4 job lifecycle for a given `SettlementReport`. It uses a **sync** SQLAlchemy session (`app/core/db_sync.py`, built from `Settings.database_url_sync` — the same psycopg DSN Alembic uses) since Celery's default worker model is sync; the async engine (`app/core/db.py`) is for the FastAPI process only. After every status transition it (a) commits the `SettlementReport.status` update and (b) publishes `{"status": ..., "row_count": ..., "rejected_row_count": ...}` as JSON to the Redis pub/sub channel `settlement:{settlement_report_id}` — this publish *is* the WS-push mechanism in §4, not an optional extra.

**Steps:**
1. `status = PARSING`, commit + publish.
2. Open the file at `SettlementReport.storage_path`, parse as the §8 tab-separated shape (header row required, columns `order-id`, `transaction-type`, `amount-description`, `amount`, `posted-date`).
3. For each data row (1-indexed row number for error reporting):
   - Resolve `amount-description` via `resolve_amount_canonical()`. **Miss → rejected row** (reason `"unmapped amount_description: <value>"`), skip to next row — never inserted as a line item.
   - Parse `amount` as `Decimal`, convert to integer paise via `round(Decimal(amount) * 100)` (never `float`). Malformed amount/date → rejected row (reason names the bad field), skip.
   - If `order-id` is blank → insert `SettlementLineItem` with `order_id=None`, `match_status=ADJUSTMENT`.
   - If `order-id` is present → look up `Order` by `(seller_marketplace_account_id, marketplace_order_id=order-id)` (the same account as the report). Found → `order_id=<that order>`, `match_status=MATCHED_EXACT`. Not found → `order_id=None`, `match_status=UNMATCHED` (an orphan line — **this is the Phase-1 discrepancy signal**, surfaced via `GET /api/settlements/{id}/line-items?match_status=UNMATCHED`, no separate table needed per §2.9's design note).
   - `raw_line_data` = the full raw row as a dict (all 5 columns, unparsed strings) — audit trail.
   - Insert the `SettlementLineItem` (append-only, no update-in-place).
4. `row_count` = count of data rows processed (rejected + inserted); `rejected_row_count` / `rejected_rows_detail` as accumulated above. `status = PARSED`, commit + publish.
5. `status = RECONCILING`, commit + publish. Compute report-level rollups (Phase 1 exact-matching only — no FeeSchedule yet, so these are straight sums, not expected-vs-actual deviation):
   - `total_gross_sales_paise` = `sum(Order.total_gross_amount_paise)` over the **distinct orders that received at least one `MATCHED_EXACT` line item** in this report (i.e. orders actually settled this period, not every order that exists).
   - `total_fees_paise` = `sum(amount_value_paise)` over this report's line items where `amount_canonical` is one of `REFERRAL_FEE, CLOSING_FEE, SHIPPING_FEE, COLLECTION_FEE, FBA_FEE, STORAGE_FEE, ADVERTISING_FEE, GST_ON_FEE, PROMOTION_REBATE, ADJUSTMENT` (every fee/adjustment-shaped bucket except tax and refund/reimbursement — kept as one bucket in Phase 1 rather than the finer breakdown a FeeSchedule-aware Phase 2 view would want).
   - `total_taxes_deducted_paise` = `sum(amount_value_paise)` where canonical in `{TCS, TDS}`.
   - `total_returns_refunds_paise` = `sum(amount_value_paise)` where canonical = `REFUND`.
   - `total_reimbursements_paise` = `sum(amount_value_paise)` where canonical = `REIMBURSEMENT`.
   - `net_payout_expected_paise` = `total_gross_sales_paise + sum(amount_value_paise over ALL of this report's line items)` — a straight sum since every line item is already correctly signed; deliberately **not** the sum of the five bucket totals above (which double-count nothing today but would if the bucket definitions ever drift — the straight sum is the source of truth, the buckets are a display breakdown).
   - `net_payout_bank_credited_paise` and `discrepancy_amount_paise` stay `NULL` in Phase 1 — there is no bank-statement upload yet (SDD's "optional" feature), so there is nothing to diff the expected figure against. Do not fabricate a value for either.
6. `status = RECONCILED`, commit + publish (final frame).
7. On any unhandled exception at any step: `status = FAILED`, `error_message = str(exception)`, commit + publish, re-raise (so Celery's own retry/failure bookkeeping still sees it) — matches `ARCHITECTURE.md` §11 "fail closed on money".

**Idempotency** (duplicate-upload detection) happens at the **upload endpoint**, before this task is ever enqueued — not inside the task. `POST /api/settlements/upload` checks for an existing `SettlementReport` with the same `(seller_marketplace_account_id, source_file_hash)`; if found, returns that existing report with `{"duplicate": true}` and does not enqueue a new task.

---

## 10. What Phase 1 explicitly does NOT implement (schema exists, logic deferred)

`SKUMarketplaceListing` sync, `FeeSchedule` computation, `Return` matching, fuzzy matching, MAD anomaly detection, LLM classification, Flipkart/Meesho parsers, tax accumulation, reporting export — all Phase 2+ per `PLAN.md`. Phase 1's `SettlementLineItem.match_status` only ever becomes `MATCHED_EXACT` or `UNMATCHED`/`ADJUSTMENT`; `MATCHED_FUZZY` is a defined-but-unused enum value until Phase 2.

---

## 11. Phase 2, slice 1 — Flipkart + Meesho settlement parsers (frozen)

Extends §8/§9 to three marketplaces. None of the 5 frozen Phase-1 API/job contracts (`../TRACKING.md`'s freeze log) change — this is purely internal: a new file shape per marketplace, a marketplace-aware canonical-mapping lookup, and a parser-dispatch seam in the ingestion task. `SettlementReport`/`SettlementLineItem` schemas, the REST surface (§6), and the job lifecycle (§4) are untouched.

### 11.1 Marketplace-aware canonical mapping (breaking internal change, not an API change)

Phase 1's `resolve_amount_canonical(raw_description: str) -> AmountCanonical | None` assumed one global mapping table. Different marketplaces use different vocabulary for the same fee concept (e.g. Amazon's "Referral fee" vs. Flipkart/Meesho's "Commission" both mean `REFERRAL_FEE`), so the signature becomes marketplace-aware:

```python
def resolve_amount_canonical(
    raw_description: str, marketplace_code: MarketplaceCode
) -> AmountCanonical | None: ...
```

`load_amount_mapping()` becomes `load_amount_mapping(marketplace_code: MarketplaceCode) -> dict[str, AmountCanonical]`, `@lru_cache`d per marketplace code (the enum is hashable, so this works unchanged), each reading its own CSV:
- `seed_data/amazon_amount_mapping.csv` (existing, 21 rows, unchanged)
- `seed_data/flipkart_amount_mapping.csv` (new, 18 rows)
- `seed_data/meesho_amount_mapping.csv` (new, 17 rows)

Combined, 56 raw descriptions map to the 14 canonical enums — clears PLAN.md's Phase 2 "40+ raw amount-descriptions" exit criterion. Every table independently covers all 14 enum values at least once (verify this the same way Phase 1's Amazon table was verified — load each table and check `set(mapping.values()) == set(AmountCanonical)`).

The only caller of `resolve_amount_canonical` is `app/modules/ingestion/tasks.py` step 3 — it now needs the report's marketplace code before resolving, see §11.3.

### 11.2 File shapes (both new, tractable, not byte-exact replicas — same posture as §8's Amazon note)

**Flipkart** (`.csv`, comma-separated, UTF-8, header row required):
```
Order ID,Event Type,Amount Head,Amount,Event Date
```
- `Order ID` — matches `Order.marketplace_order_id`; blank for report-level adjustments.
- `Event Type` — free text (`Sale`, `Return`, `Adjustment`, ...), carried into `raw_line_data` only, not parsed into a column (mirrors Amazon's `transaction-type`).
- `Amount Head` — raw string resolved via `flipkart_amount_mapping.csv`.
- `Amount` — decimal rupees, signed.
- `Event Date` — `YYYY-MM-DD`.

**Meesho** (`.csv`, comma-separated, **UTF-8 with a leading BOM** — deliberately, to exercise BOM tolerance per `backend/PLAN.md`'s "encoding/BOM/column-drift tolerance" exit criterion):
```
Sub Order No,Reason,Description,Value,Date
```
- `Sub Order No` — matches `Order.marketplace_order_id`; blank allowed.
- `Reason` — free text, `raw_line_data` only.
- `Description` — raw string resolved via `meesho_amount_mapping.csv`.
- `Value` — decimal rupees, signed.
- `Date` — `YYYY-MM-DD`.

**Column-drift tolerance**: both new parsers must look up fields by header *name* (`dict(zip(header, raw_fields))`, exactly as `amazon.py` already does), not by fixed position — a reordered header row must still parse correctly. This is already true of `amazon.py`'s implementation; the new parsers must follow the same pattern, not a positional one.

**BOM tolerance**: the ingestion task must open every settlement file with `encoding="utf-8-sig"` instead of `"utf-8"` (a safe superset — strips a leading BOM if present, behaves identically to plain UTF-8 if not, so this is safe to apply uniformly to all three marketplaces, not just Meesho). In addition, each parser's header-parsing step must itself strip a leading `'﻿'` from the first header cell if present, as a defensive second layer — this matters because unit tests call parser functions directly with a raw string (bypassing the task's file-open step), so BOM handling must not depend solely on how the caller opened the file.

### 11.3 Parser dispatch

A new mapping from `MarketplaceCode` to parser function (natural home: `app/modules/ingestion/parsers/__init__.py`):

```python
PARSERS: dict[MarketplaceCode, Callable[[Iterable[str] | str], ParseResult]] = {
    MarketplaceCode.AMAZON_IN: parse_amazon_settlement_file,
    MarketplaceCode.FLIPKART: parse_flipkart_settlement_file,
    MarketplaceCode.MEESHO: parse_meesho_settlement_file,
}
```

`app/modules/ingestion/tasks.py` step 2 (§9) currently hardcodes `parse_amazon_settlement_file`. It now must: (a) load the report's `SellerMarketplaceAccount.marketplace.code` (the relationship already exists on `SellerMarketplaceAccount`), (b) look up the matching parser via the dispatch table above, (c) call `resolve_amount_canonical(description, marketplace_code)` in step 3 with that same code. An unregistered marketplace code is a programming error (all 3 seeded marketplaces have parsers) — raise, don't silently skip.

### 11.4 Canonical-mapping table for reference

**Flipkart** (`backend/seed_data/flipkart_amount_mapping.csv`):

| raw_description | canonical | stored sign |
|---|---|---|
| Commission | REFERRAL_FEE | negative |
| Fixed fee | CLOSING_FEE | negative |
| Collection fee | COLLECTION_FEE | negative |
| Shipping fee | SHIPPING_FEE | negative |
| Reverse shipping fee | SHIPPING_FEE | negative |
| Pick and pack fee | FBA_FEE | negative |
| Storage fee | STORAGE_FEE | negative |
| Sponsored ads fee | ADVERTISING_FEE | negative |
| Coupon fee | PROMOTION_REBATE | negative |
| Seller promotion reimbursement | PROMOTION_REBATE | positive |
| TCS collected | TCS | negative |
| TDS deducted | TDS | negative |
| Customer refund | REFUND | positive |
| Return premium reimbursement | REIMBURSEMENT | positive |
| CGST on fees | GST_ON_FEE | negative |
| SGST on fees | GST_ON_FEE | negative |
| IGST on fees | GST_ON_FEE | negative |
| Miscellaneous adjustment | ADJUSTMENT | either |

**Meesho** (`backend/seed_data/meesho_amount_mapping.csv`):

| raw_description | canonical | stored sign |
|---|---|---|
| Commission | REFERRAL_FEE | negative |
| Fixed fee | CLOSING_FEE | negative |
| Shipping charge | SHIPPING_FEE | negative |
| Return shipping charge | SHIPPING_FEE | negative |
| Reverse pickup charge | COLLECTION_FEE | negative |
| Warehousing charge | STORAGE_FEE | negative |
| Ads charge | ADVERTISING_FEE | negative |
| Discount reimbursement | PROMOTION_REBATE | positive |
| Marketing fee | PROMOTION_REBATE | negative |
| TCS | TCS | negative |
| TDS | TDS | negative |
| Refund to customer | REFUND | positive |
| Compensation | REIMBURSEMENT | positive |
| CGST on charges | GST_ON_FEE | negative |
| SGST on charges | GST_ON_FEE | negative |
| IGST on charges | GST_ON_FEE | negative |
| Other adjustment | ADJUSTMENT | either |

`FBA_FEE`'s name is Amazon-flavored (legacy from Phase 1) but is reused across marketplaces as the generic "fulfillment fee" bucket — not renamed, since the 14-enum contract is frozen (§3) and this is exactly the kind of cross-marketplace reuse the canonical contract exists for. Note this in code as a comment where Flipkart's "Pick and pack fee" maps to it, so it doesn't read as a copy-paste mistake.

### 11.5 Synthetic generator extension

`scripts/synth_data_generator.py`'s existing Amazon path (seller, products, listings, 50 orders, fixture) is already verified end-to-end against Phase 1 — **do not refactor it**. Add two new, parallel functions (`_generate_flipkart_fixture`, `_generate_meesho_fixture`, or similarly named) that follow the *same shape* per marketplace: one additional `SellerMarketplaceAccount` (FLIPKART / MEESHO) for the same demo seller, its own 50 `Order`+`OrderLineItem` set (orders are scoped to one `seller_marketplace_account_id`, so each marketplace needs its own order set — they cannot share Amazon's), and its own settlement fixture + ground truth, using each marketplace's own mapping-table vocabulary and file shape (§11.2). Emit:
- `tests/fixtures/flipkart_settlement_sample.csv` + `.ground_truth.json`
- `tests/fixtures/meesho_settlement_sample.csv` + `.ground_truth.json` (write this one with a UTF-8 BOM — `encoding="utf-8-sig"` on the write side too, so the fixture genuinely exercises the BOM-tolerance path end-to-end, not just in a unit test)

Same ~45/5 matched/unmatched-order split and 3-4 orphan lines per marketplace as the Amazon fixture (§5 step 3), reusing that same ratio rather than inventing a new one. `_wipe_existing_demo_data` must be extended to also clean up the two new accounts' orders/reports on a re-run (same idempotency requirement as the existing Amazon path).

### 11.6 Demo script extension

`scripts/demo_e2e.py` currently asserts against one marketplace. Extend it to upload + process all three marketplace accounts' fixtures and assert each against its own ground truth — the exit criterion is "Flipkart and Meesho settlement files parse successfully **alongside** Amazon," i.e. all three in one run, not three separate scripts.

### 11.7 What this slice explicitly does not cover

Preview-before-commit, and full encoding-tolerance beyond BOM (e.g. non-UTF-8 legacy encodings) are separate, later sub-items of `PLAN.md`'s "Full ingestion" line — not in scope for this slice. FeeSchedule computation, fuzzy matching, and MAD anomaly detection remain Phase 2 items not yet started (§10 still applies to them).
