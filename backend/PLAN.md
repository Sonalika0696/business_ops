# Backend — Phased Plan

> Scope: services, APIs, data, processing, business logic, integrations, AI/ML.
> Read alongside `../ARCHITECTURE.md` (structural decisions) and `../ROADMAP.md` (consolidated phasing).
> Priority key: **P0** required foundation · **P1** important next · **P2** useful improvement · **P3** advanced / later.

The backend is the thick side of the system — it owns all computation and business rules. Foundation work is deliberately narrow: the data model, one ingestion path, and enough reconciliation to prove the loop end-to-end. Everything sophisticated (pricing, ML, claims) is layered on top and is intentionally deferred.

> **Prioritization is governed by [`../SCOPE.md`](../SCOPE.md).** This file orders work by *build dependency*; SCOPE.md orders it by *dissertation defensibility* and decides what gets cut. Items tagged **[DEFEND]** protect a novelty claim and are non-negotiable; items tagged **[PRODUCT]** are post-dissertation depth and are cut first. Where the two views disagree on what to protect, SCOPE.md wins.

---

## Phase 1 — Foundation (P0)

*Goal: a single settlement file can be uploaded, parsed, stored, matched, and its discrepancies read back. The system works end-to-end for one marketplace.*

**Core services (priority-ordered)**
1. **Data model & persistence** — all 12 entities defined; migrations; `seller_id` scoping seam. *Gating: nothing else starts until this is frozen.*
2. **Auth service** — JWT email/password, single seller.
3. **Master-data service** — seller, product/SKU, marketplace-account CRUD (no external verification yet).
4. **Ingestion service (one marketplace)** — file upload, SHA-256 hash + raw store, async parse job, normalize to the **canonical line-item** shape.
5. **Job/worker tier** — queue + one worker; job lifecycle (submit → status → result); idempotency by file hash.
6. **Reconciliation v0** — exact order↔settlement matching; expected-vs-actual at the report level; discrepancy list.

**Architectural / system-design decisions locked here**
- The canonical line-item contract and the job-lifecycle contract (both reused everywhere).
- Append-only audit + soft-delete conventions.
- Money precision rule; UTC-store/IST-display.
- Module-boundary interfaces (even with only recon populated).

**Dependencies on earlier phases:** none (this *is* the foundation).

**Explicitly deferred:** other marketplaces, FeeSchedule engine, fuzzy matching, anomaly detection, any external API, pricing, returns, tax, notifications.

**Exit criteria checklist**
- [x] All 12 entities migrated; schema reviewed and frozen (no breaking changes expected downstream)
- [x] Seller can register/login and receive a valid JWT
- [x] Seller + product/SKU CRUD works with validation errors surfaced
- [x] A synthetic Amazon settlement file uploads, is hashed (SHA-256), and is stored raw
- [x] Upload triggers an async job; job status is queryable end-to-end (queued → processing → done/failed)
- [x] Parsed rows are normalized into the canonical line-item shape and persisted
- [x] Re-uploading the same file (same hash) is detected as a duplicate, not re-processed
- [x] Exact order↔settlement matching runs and produces a discrepancy list
- [x] Discrepancy list is readable via API with no manual DB inspection required
- [x] One demo script/test runs the full loop (upload → parse → match → discrepancies) unattended

---

## Phase 2 — Core product (P1)

*Goal: all three marketplaces, real fee logic, and the loss-recovery + compliance layers that make the tool genuinely useful to a seller.*

**Core services (priority-ordered)**
1. **Full ingestion (P1) [DEFEND]** — Flipkart + Meesho parsers; 40+ codes → 14 canonical enums as a mapping table; encoding/BOM/column-drift tolerance; rejected-row logging; preview-before-commit; duplicate detection. *(Meesho is the first ingestion cut if this overruns — see SCOPE.md; do not drop it pre-emptively.)*
2. **FeeSchedule engine (P1) [DEFEND — Claim #3]** — config-not-code fee computation (flat / percent / tiered / zone), effective-dated. **This is the single shared substrate under both reconciliation *and* pricing** — the same config must drive expected-fee math (C) and margin math (E), or Claim #3 is only a design intention.
3. **Reconciliation engine, full (P1) [DEFEND — Claim #2]** — fuzzy matching for truncated IDs; posted-date vs order-date awareness; per-line expected-fee compute; configurable deviation thresholds; **rules-based anomaly detection** (median-absolute-deviation); bank-UTR matching; roll-forward of unresolved items. *(MAD + published metrics is the protected Claim-#2 bar; the ML upgrade in Phase 3 is desirable-not-required.)*
4. **Audit chain (P1)** — hash-chained `AuditEvent` on every anomaly / state change.
5. **Integration gateway (P1)** — adapter layer; wire onboarding verifications (GSTIN, IFSC, PIN, Udyam) with offline fallbacks. *(Live verification is a PRODUCT nicety — static test data is an acceptable dissertation substitute; build the fallback path first.)*
6. **Returns — thin slice (P1) [DEFEND]** — **return-to-refund matching + un-credited-refund detection only.** Un-credited refunds feed the reconciliation story.
7. **TCS/TDS accumulation (P1) [DEFEND-adjacent]** — only as an **input to margin (E) and net-payout reconciliation (C)**. Not the full tax module.
8. **Reporting (P2)** — reconciliation report export (PDF / spreadsheet).

**[PRODUCT] — deferred out of the dissertation core (moved to Phase 5 / cut list, see SCOPE.md):** full Returns/RTO (RTO cost calc + trending as optional stretch), claim-window tracking; full Tax & Compliance (GSTR-8 recon, GSTR-1/3B helpers, e-invoice/e-way-bill monitors, IGST/CGST/SGST split, composition, reverse-charge).

**Architectural decisions locked here**
- Integration-gateway interface + the "no external call on the recon critical path" rule (LLM-absent path routes unknowns to manual review).
- FeeSchedule rule schema (the jsonb `computation_rule` shape).

**Dependencies on earlier phases:** Phase 1 data model, canonical line item, job tier, recon v0.

**Explicitly deferred:** pricing intelligence, ML anomaly model, LLM classification, auto-drafted claims, evaluation harness.

**Exit criteria checklist**
- [x] Flipkart and Meesho settlement files parse successfully alongside Amazon
- [x] 40+ raw amount-descriptions map to the 14 canonical enums via a table (not conditional code)
- [x] Malformed/unmappable rows are rejected with a logged reason, never silently dropped
- [ ] FeeSchedule engine computes expected fees for at least one flat, one percent, one tiered, and one zone-based rule
- [ ] A fee-schedule change (e.g. new rate) takes effect via config update with zero code deploy
- [ ] Fuzzy matching resolves truncated/malformed order IDs above an agreed accuracy bar
- [ ] Rules-based (MAD) anomaly detection flags at least the known-injected anomalies in synthetic test data
- [ ] Every anomaly/state change writes a verifiable, hash-chained AuditEvent
- [ ] GSTIN/IFSC/PIN/Udyam verification works live, and falls back cleanly to offline/static mode when the external service is unavailable
- [ ] Return-to-refund matching runs on synthetic data; un-credited refunds are correctly detected (thin slice — full RTO/claims are [PRODUCT])
- [ ] TCS/TDS accumulate correctly against a hand-calculated reference month (as an input to margin + net-payout; not the full tax module)
- [ ] Reconciliation report exports to PDF/spreadsheet with correct totals

---

## Phase 3 — Intelligence / advanced capabilities (P2 → P3)

*Goal: the dissertation's defensible novelty. Build-order-late, but grade-critical — see note.*

**Core services (priority-ordered)**
1. **Pricing intelligence service (P2) [DEFEND — Claim #1]** — real-time net-margin per marketplace from the shared FeeSchedule; target-margin price recommendation (the thing no competitor ships); cross-marketplace parity + alerts; negative-margin warnings; marketplace ranking by take-home; fee-simulation "what-if".
2. **ML anomaly detection (P2 — upgrade, not load-bearing)** — supervised/unsupervised model upgrading the MAD rules, with benchmarked P/R/F1. **The protected Claim-#2 deliverable is MAD + metrics (Phase 2); this ML upgrade is the *first thing to drop* inside the novelty window if it runs long.** Do not let a better model consume the write-up weeks.
3. **LLM-assisted classification (P3) [PRODUCT]** — Groq/Gemini fallback for unmapped fee codes, behind the gateway with a rules/manual fallback.
4. **Claim auto-drafting (P3) [PRODUCT]** — evidence-packet assembly + drafted claim body. Product depth, not research depth.
5. **Advanced pricing (P3) [PRODUCT]** — ad-cost integration, volume-discount modelling, cross-marketplace optimizer.

> **Priority note:** items 1–2 sit late on the *dependency/build-order* axis (they need the Phase 1–2 foundation) but are the **highest** on the defensibility axis — pricing (Claim #1) and benchmarked anomaly metrics (Claim #2) are what the examiners score. `../SCOPE.md` protects them; the ML *upgrade* is expendable, the metrics are not.

**Dependencies on earlier phases:** FeeSchedule engine + reconciliation outputs (feature/label source), full ingestion.

**Explicitly deferred:** anything beyond the three-marketplace scope; real-time/streaming inference.

**Exit criteria checklist**
- [ ] Price recommendation returns a specific price for a target margin, with full fee breakdown shown
- [ ] Negative-margin warning triggers correctly when a set price would lose money after fees
- [ ] Cross-marketplace parity view correctly flags a genuine price mismatch on a test SKU
- [ ] ML anomaly model trained and evaluated against the synthetic ground-truth-with-injected-overcharges dataset
- [ ] Precision, recall, F1 computed and recorded at multiple threshold values (this is the primary quantitative result — do not skip)
- [ ] ML model outperforms (or is honestly compared against) the Phase-2 MAD rules baseline
- [ ] LLM classification handles at least one previously-unmapped fee code correctly, and degrades to manual-review when the LLM call fails
- [ ] Claim auto-draft produces a coherent, evidence-backed draft for at least one return scenario

---

## Phase 4 — Optimization & measurement (P2)

*Goal: turn the working system into measured, reproducible research + operationally sound.*

**Priority-ordered**
1. **Evaluation harness (P2)** — automated tests of parsing accuracy, matching P/R/F1, anomaly P/R/F1 at thresholds, recon totals vs ground truth, FeeSchedule vs hand-calc, price-rec correctness. *(For the dissertation this is high-value, not optional.)*
2. **Synthetic data generator v2 (P2)** — configurable profiles/mix/injection; ground-truth JSON; packaged as the open dataset.
3. **Reliability (P2)** — job retry/backoff hardening; partial-failure recovery; idempotency audit.
4. **Observability (P2)** — structured logging with correlation ids; job-failure surfacing; rejected-row analytics.
5. **Performance (P3)** — query/index review, caching hot dashboard aggregates. *Only if measured to be needed — small datasets make this unlikely.*

**Dependencies on earlier phases:** all functional modules (Phases 1–3).

**Explicitly deferred:** load/throughput scaling, distributed workers, APM/tracing.

**Exit criteria checklist**
- [ ] Evaluation harness runs unattended and produces a results table/report for every metric (parsing, matching, anomaly, recon totals, fee accuracy, price-rec correctness)
- [ ] Synthetic generator v2 supports configurable seller profile, marketplace mix, and injected anomaly rate
- [ ] Generated dataset + ground truth published (versioned release) as the open research artefact
- [ ] Every job type has retry/backoff behavior verified under simulated failure
- [ ] Correlation IDs trace a request through upload → job → result in logs
- [ ] Rejected-row rate and reasons are queryable, not just logged to a file

---

## Phase 5 — Polish & product depth (P3) [all PRODUCT]

*Goal: product-feel and operational conveniences. Non-essential to correctness or to any novelty claim. This is where the scope deferred out of the dissertation core lands — build only if the DEFEND set is complete and time remains.*

**Priority-ordered**
1. **Full Returns/RTO (P3)** — RTO cost calculator + trending, claim-window tracking (beyond the Phase-2 return-to-refund thin slice).
2. **Full Tax & Compliance (P3)** — GSTR-8 reconciliation, GSTR-1 Table 8 / GSTR-3B helpers, e-invoice & e-way-bill monitors, IGST/CGST/SGST split, composition & reverse-charge (beyond the Phase-2 TCS/TDS input).
3. **Notification engine (P3)** — WhatsApp daily digest, critical push alerts, weekly PDF email; scheduled jobs for reminders. *Best-effort, off critical path.*
4. **Invoice mailbox ingestion (P3)** — IMAP intake of a dedicated inbox.
5. **Export conveniences (P3)** — Tally (XML) / Zoho (CSV) formats; statement-of-account, vendor-payment-advice PDFs.
6. **FX display, plain-English summaries (P3)** — LLM-generated report narration.

**Dependencies on earlier phases:** aggregated data from Phases 2–3; comms integrations.

**Exit criteria checklist**
- [ ] Daily WhatsApp digest sends successfully to a test number with correct figures
- [ ] Weekly PDF email report generates and sends via SMTP
- [ ] Invoice mailbox (IMAP) correctly ingests at least one test email
- [ ] Tally XML export and Zoho CSV export both round-trip without data loss on a test dataset
- [ ] Plain-English LLM summary reads correctly on at least one complex report

---

## Backend cross-cutting (established Phase 1, upheld throughout)
- Config-not-code for all fee/tax/threshold/mapping data.
- Append-only audit + soft-delete; no hard deletes.
- Idempotent, retriable jobs.
- Every external dependency behind an adapter with a fallback.
- Synthetic-data-only security posture; secrets in env.
