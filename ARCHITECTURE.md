# Architecture & System Design — Decisions to Make Now

> **Product:** Multi-Marketplace Reconciliation & Pricing Intelligence Platform for micro Indian e-commerce sellers (Amazon India, Flipkart, Meesho).
> **Nature:** Single-tenant, synthetic-data research prototype. Solo build. Zero paid-API budget.
> **This document fixes the structural choices** that are expensive to change later. It does **not** prescribe implementation. It answers *what the system needs and how the pieces relate*.

The guiding constraint is **do not over-engineer the foundation**. Every decision below is deliberately the *simplest structure that does not have to be torn out* when Phase 3+ capabilities arrive.

---

## 1. Topology — the single most important decision

**Decision: a modular monolith backend + single-page frontend. Not microservices.**

- One deployable backend process exposing one API, internally partitioned into modules with hard boundaries (Sellers, Ingestion, Reconciliation, Pricing, Returns, Tax, Dashboard).
- Modules talk to each other through in-process service interfaces, never by reaching into each other's tables directly.
- Background work runs as separate worker processes off the *same* codebase (shared models), not as separate services.

**Why now:** a solo dissertation build cannot afford distributed-systems overhead (service discovery, network contracts, per-service deploys). But module boundaries drawn now mean any single module *could* be extracted later without a rewrite. This is the "solid but not over-built" line.

**Deferred:** service decomposition, message-bus between modules, independent scaling. Explicitly out of scope.

---

## 2. Major system components

| Component | Responsibility | Foundational? |
|---|---|---|
| **Web client (SPA)** | All user interaction; renders state from the API | P0 |
| **API layer** | Request handling, auth, validation, module orchestration | P0 |
| **Domain modules** | Business logic per area (recon, pricing, tax…) behind service interfaces | P0 (recon) → P2/P3 (pricing) |
| **Relational store** | System of record for all 12 entities | P0 |
| **Object/file store** | Raw uploaded settlement files, generated PDFs | P0 |
| **Job queue + workers** | Async parsing, reconciliation, metrics, notifications | P0 (parsing) |
| **Cache / broker** | Job broker + hot-path caching | P0 |
| **Integration gateway** | Adapters for every external API, each with a fallback | P1 |
| **Synthetic data generator** | Reproducible test/eval data — a standalone tool, not part of the running app | P0 |

---

## 3. Frontend / backend boundary

**Decision: thin client, thick server.** The backend owns all business logic and all computation (fee math, matching, anomaly scoring). The frontend renders results and captures input. No business rules duplicated in the browser.

- **Transport:** REST for request/response; **WebSocket** (decided) for one thing only — long-running job progress. Polling is not the fallback path; if a WS connection drops, the client reconnects rather than degrading to poll, keeping one progress mechanism instead of two to maintain.
- **No server-side rendering.** A static SPA served as files is sufficient; there is no SEO or first-paint requirement.
- **The frontend never talks to an external integration directly.** All third-party calls (verification, LLM, comms) are proxied through the backend so keys, fallbacks and rate limits live in one place.

---

## 4. Data flow (the canonical path)

The load-bearing pipeline is **settlement ingestion → reconciliation**. Everything else reads from what it produces.

```
Upload file ──▶ hash + store raw ──▶ create SettlementReport (status: PARSING)
      │                                        │
      │                              enqueue async job
      ▼                                        ▼
  (client polls / WS)              Worker: parse rows ─▶ normalize to canonical enum
                                         ─▶ match line ↔ Order
                                         ─▶ compute expected fee from FeeSchedule
                                         ─▶ deviation ─▶ flag anomaly
                                         ─▶ append AuditEvent (hash-chained)
                                         ─▶ status: RECONCILED
                                        │
                             WS pushes completion ──▶ client refreshes queues
```

**Two contracts must be stable from Phase 1 because everything depends on them:**
1. The **canonical settlement line item** (the 14-enum normalized fee/credit shape).
2. The **job lifecycle** (submit → status → result), which the whole async surface reuses.

---

## 5. APIs & contracts

- **Resource-oriented REST** per module: masters (seller, product, marketplace accounts), settlements/uploads, reconciliation results, discrepancies/anomalies, returns, tax summaries, pricing queries, dashboard aggregates.
- **Async pattern for anything that isn't instant:** the request returns a job handle; status and result are fetched separately. Parsing, reconciliation, metric runs and PDF generation all use this one pattern.
- **Contract-first for the FE/BE seam:** the shapes below are frozen early and mocked so both sides progress in parallel — job lifecycle, settlement-report summary, discrepancy/anomaly item, entity CRUD. (See `CROSS-SYSTEM-DEPENDENCIES.md`.)
- **Versioning:** not needed for a single-tenant prototype; keep one unversioned API. Deferred.

---

## 6. State, persistence & data model

- **Relational database is the single system of record** for all 12 entities (§5 of the design doc). One schema; `seller_id` present on tenant-scoped rows from day one so multi-tenancy is *possible* later without a migration — but multi-tenant enforcement is **not** built now.
- **Semi-structured columns (jsonb) for two deliberate cases:** the preserved raw CSV row (audit) and the FeeSchedule `computation_rule`. These are the config-not-code seams.
- **Append-only / soft-delete only.** No hard deletes anywhere. The `AuditEvent` log is immutable and hash-chained.
- **Time:** store UTC, display IST. Money to paise precision (integer minor units or fixed decimal — decide at runtime, but *never* float for currency).
- **Client state:** ephemeral UI/server-cache state only; the browser is not a source of truth. No offline write model in the foundation.

---

## 7. Config-not-code (a first-class architectural decision)

**Decide now:** marketplace fee rules, tax rates, thresholds and enum mappings live as **data**, not as branching logic in code.

- `FeeSchedule` rows carry effective-dated, category/weight/zone-aware computation rules.
- The 40+ raw amount-descriptions → 14 canonical enums mapping is a table, not a switch statement.
- Tax rates (TCS, TDS, GST slabs) and filing thresholds are reference data.

**Why now:** this pattern is one of the four dissertation novelty claims, and retrofitting it later means rewriting the reconciliation core. It costs little to establish up front.

---

## 8. Processing & background jobs

- **A queue + worker tier is foundational** (parsing cannot run inline within a request). Establish it in Phase 1 even though only one job type exists at first.
- Jobs must be **idempotent** (re-running an upload with the same file hash is a no-op + warning) and **retriable**.
- **Scheduled jobs** (filing reminders, digests) arrive later (Phase 5) and reuse the same worker tier — no new infrastructure.

---

## 9. External integrations

**Decision: every external service sits behind an adapter with a declared fallback, and the core depends on the *interface*, never the vendor.**

| Concern | Primary (free) | Fallback | Isolation rule |
|---|---|---|---|
| GSTIN / PAN / Udyam | gstinapi.in / Decentro | self-hosted / static test data | onboarding must work fully offline |
| Bank / PIN lookup | Razorpay IFSC, postalpincode.in | India Post / static | keyless; cache aggressively |
| LLM classification | Groq / Gemini free tier | local model / "route to manual review" | **must degrade to a rules path**, never block reconciliation |
| Notifications | WhatsApp / Twilio trial | email (SMTP) | best-effort, never on the critical path |
| FX display | exchangerate-api | ExchangeRate.host | display-only |

**Rule:** no external call is ever on the reconciliation critical path. If Groq is down, unknown fee codes route to a manual-review queue; the run still completes.

**Standing policy (decided): synthetic-first for any resource that turns paid.** The "free tier" column above is a snapshot, not a guarantee — free tiers get throttled, revoked, or paywalled. Whenever a listed service would require payment to keep using (rate-limit exhausted, trial expired, tier downgraded), the adapter falls to its synthetic/offline path rather than the project adopting a paid plan. This applies for the life of the prototype, not just at launch — if gstinapi.in's free 100/month is exhausted mid-development, onboarding runs on static test data for the rest of that month rather than upgrading. Each adapter's fallback (§9 table) must therefore stay exercised and working, not just written once and left to bit-rot.

---

## 10. Observability

Lightweight, proportionate to a prototype — **not** a full APM stack.

- **Structured logs** with a correlation id per job.
- **Job status is first-class** and user-visible (parsing progress, failures).
- **Rejected rows are logged with a reason and never silently dropped** — this is both an observability and a data-integrity requirement.
- **The audit log doubles as the domain event trail.**

Deferred: metrics dashboards, tracing, alerting infrastructure.

---

## 11. Error handling & failure boundaries

- **Ingestion is the untrusted boundary.** Treat every uploaded file as hostile/malformed: validate, tolerate encoding/whitespace/column drift, preview before commit, and let the user reject a bad upload.
- **Partial success is a first-class outcome:** a settlement may parse 980/1000 rows; the 20 go to an errors panel, the 980 proceed.
- **Fail closed on money, fail open on convenience:** never fabricate a fee match to force a reconciliation; do let a notification silently fail.
- **Idempotency via file hash** guards against double-processing.

---

## 12. Scalability

**Explicit decision: scale is not a design driver.** The target user runs <1,000 orders/month; a single tenant; datasets are small. Designing for throughput here *is* over-engineering.

- Keep the API stateless and workers queue-fed so horizontal scale is *available* if ever needed — that falls out of the architecture for free.
- Do not build sharding, read replicas, caching tiers, or autoscaling. Deferred indefinitely.

---

## 13. Security boundaries

**Decided: Declaration A.** No volunteer usability study, no real seller data at any point — the synthetic-data decision collapses most of the security surface:

- **No real seller PII or financial data is ever handled** (Declaration A). This removes the hardest compliance and breach-risk obligations by design. No ethics-approval lead time is needed for a Declaration B study — that path is closed, not just deferred.
- **Secrets** (API keys, JWT signing) live in environment configuration, never in the repo.
- **Auth** is JWT email/password for a single seller. Authorization is trivial today; the `seller_id` scoping is the seam for later.
- **Uploaded files** are validated and treated as untrusted input (see §11).
- **The public repo publishes code + synthetic data only** — never credentials or real datasets.

Deferred: RBAC, multi-tenant isolation, secret rotation, pen-testing.

---

## 14. What must be decided now vs. at runtime

**Decide now (this document):** topology, module boundaries, the canonical line-item and job-lifecycle contracts, config-not-code, the integration-gateway pattern, append-only/soft-delete, synthetic-data-only security posture, "no external call on the recon critical path."

**Leave for runtime:** specific libraries, folder structure, exact schema column types, ORM patterns, endpoint naming, PDF/templating tooling, test framework layout, deployment target details. These do not constrain the architecture and should not be pre-decided.
