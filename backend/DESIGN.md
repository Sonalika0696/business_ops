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
- `WS /ws/settlements/{id}` → server pushes `{ status, row_count, rejected_row_count }` on every status transition (Celery task calls `update_state` + publishes to Redis channel `settlement:{id}`; a small FastAPI WS endpoint subscribes and forwards). On disconnect, client reconnects — no polling fallback is maintained, per `../ARCHITECTURE.md` §3.
- Duplicate upload (same `source_file_hash` for the same `seller_marketplace_account_id`) → `200 OK` with the **existing** report and `{ duplicate: true }`, task is not re-enqueued.

---

## 5. Synthetic data generator (Phase 1 minimum — SDD §8.1)

Standalone script, **not** part of the running app: `backend/scripts/synth_data_generator.py`.

Phase 1 scope (grows in Phase 4 per `PLAN.md`):
1. Seed one `Seller`, one `SellerMarketplaceAccount` (Amazon), N `Product` + matching `SKUMarketplaceListing` rows.
2. Generate M synthetic `Order` + `OrderLineItem` rows with known ground-truth totals.
3. Emit an Amazon-Flat-File-V2-*shaped* settlement text file (tab-separated, the columns actually consumed by the parser) covering most of those orders, with a controlled number of intentionally unmatched/adjustment lines — write it to `backend/tests/fixtures/amazon_settlement_sample.txt`.
4. Emit a ground-truth JSON alongside it (`amazon_settlement_sample.ground_truth.json`): expected match count, expected discrepancy count — used by the Phase 1 demo script and later by the Phase 4 evaluation harness.

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
      ingestion/        models.py (SettlementReport, SettlementLineItem), schemas.py, parsers/{base.py, amazon.py}, service.py, router.py, tasks.py
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

## 8. What Phase 1 explicitly does NOT implement (schema exists, logic deferred)

`SKUMarketplaceListing` sync, `FeeSchedule` computation, `Return` matching, fuzzy matching, MAD anomaly detection, LLM classification, Flipkart/Meesho parsers, tax accumulation, reporting export — all Phase 2+ per `PLAN.md`. Phase 1's `SettlementLineItem.match_status` only ever becomes `MATCHED_EXACT` or `UNMATCHED`/`ADJUSTMENT`; `MATCHED_FUZZY` is a defined-but-unused enum value until Phase 2.
