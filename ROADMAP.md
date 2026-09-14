# Consolidated Roadmap — What to Build First, Next, and Later

> This is the single answer to: *what do we build first, what comes next, what can wait, and what must be decided now?*
> Companion documents: `ARCHITECTURE.md` (decide-now structure) · `backend/PLAN.md` · `frontend/PLAN.md` · `CROSS-SYSTEM-DEPENDENCIES.md`.

**Prioritization basis:** dependency → importance → value. **Not** visual impressiveness. The foundation is deliberately minimal; intelligence and polish are layered on top and clearly separated.

**Priority key:** **P0** required foundation · **P1** important next · **P2** useful improvement · **P3** advanced / later.

---

## The shape of the plan

Five macro-phases, but the last two are light — most of the weight is in Phases 1–3.

```
Phase 1  FOUNDATION      ── the loop works end-to-end (one marketplace)
Phase 2  CORE PRODUCT    ── all 3 marketplaces + recovery + compliance = genuinely useful
Phase 3  INTELLIGENCE    ── pricing + benchmarked ML metrics = the dissertation novelty
Phase 4  OPTIMIZATION    ── evaluation, reliability, observability (thin)
Phase 5  POLISH          ── founder dashboard, notifications, styling (thin)
```

> **Build-order ≠ importance.** Phase 3 is late because it *depends* on the foundation, not because it matters less — pricing intelligence and benchmarked anomaly metrics are the graded research contribution. The descope ladder protects them even when convenience features are cut.

---

## Phase 1 — Foundation (P0)

**Everything required to get the core system working; nothing more.**

- **Backend:** 12-entity data model (frozen first) · JWT auth (single seller) · master-data CRUD · ingestion for **one** marketplace (upload, hash, async parse, normalize to canonical) · job/worker tier · reconciliation v0 (exact matching, expected-vs-actual, discrepancy list).
- **Frontend:** login/shell · upload with processing + partial-failure states · ingestion history · read-only discrepancy view · minimal masters forms.
- **Decide now (architecture):** topology (modular monolith + SPA) · canonical line-item & job-lifecycle contracts · config-not-code seam · append-only/soft-delete · money precision · integration-gateway *pattern* (even if unused yet).
- **Defer:** other marketplaces, FeeSchedule engine, fuzzy matching, anomaly detection, all external APIs, pricing, returns, tax, notifications, all styling.
- **Done when:** one synthetic Amazon settlement uploads → parses → matches → discrepancies visible end-to-end.

## Phase 2 — Core product (P1)

**The capabilities that make it genuinely useful.**

- **Backend:** Flipkart + Meesho parsers + 14-enum mapping table · **FeeSchedule engine (shared substrate — Claim #3)** · full reconciliation (fuzzy match, date-awareness, deviation thresholds, MAD anomalies **+ this is where Claim #2's metrics bar is met**, UTR matching, roll-forward) · hash-chained audit · integration gateway · **return-to-refund thin slice** · **TCS/TDS-as-input only** · report export.
- **Frontend:** reconciliation dashboard + anomaly review · order drill-down · full upload UX · onboarding with verification feedback + bulk import · un-credited-refund queue · TCS/TDS view · report download.
- **Defer to Phase 5 [PRODUCT]:** full Returns/RTO (RTO calc, claims), full Tax/Compliance (GSTR helpers, monitors, splits), pricing UI/logic (→ Phase 3), notifications, founder polish, design system.
- **Done when:** a seller can reconcile all three marketplaces, see and action discrepancies, and see un-credited refunds + TCS/TDS feeding the numbers — on synthetic data. *(Claim #2's metrics are met here with MAD; the ML upgrade is Phase 3 and optional.)*

## Phase 3 — Intelligence / advanced capabilities (P2 → P3)

**The novelty, built on the foundation.**

- **Backend:** pricing intelligence — net-margin, recommendation, parity, what-if `P2` **[DEFEND — Claim #1]** · ML anomaly detection with benchmarked P/R/F1 `P2` **(upgrade — MAD+metrics from Phase 2 is the protected bar; drop this first if the window slips)** · LLM classification `P3` **[PRODUCT]** · claim auto-drafting `P3` **[PRODUCT]** · advanced pricing `P3` **[PRODUCT]**.
- **Frontend:** pricing screens + margin curves `P2` **[DEFEND]** · anomaly-metrics/results view `P2` **[DEFEND]** · claim drafting UI `P3` **[PRODUCT]** · "correct me" `P3` **[PRODUCT]**.
- **Defer:** anything beyond three-marketplace scope; streaming/real-time inference.
- **Done when:** price recommendations return with fee breakdown (Claim #1), and the anomaly results view presents benchmarked metrics across thresholds (Claim #2). The ML upgrade is a bonus over the MAD baseline, not a gate.

## Phase 4 — Optimization & measurement (P2, thin)

**Measured, reproducible, operationally sound.**

- **Backend:** evaluation harness (parsing/matching/anomaly/recon/fee/price metrics) `P2` · synthetic generator v2 + packaged open dataset `P2` · job reliability hardening `P2` · structured logging/observability `P2` · performance tuning `P3` *(only if measured necessary — small data makes it unlikely)*.
- **Frontend:** job-failure/retry surfacing `P2` · empty/error-state completeness audit `P2`.
- **Defer:** load/throughput scaling, distributed workers, tracing/APM.
- **Done when:** metrics tables/plots exist for the results chapter and the open dataset is released.

> For the dissertation, Phases 3–4 carry the assessed contribution. They sit late in *build order* but high in *value* — do not treat "Phase 4" as skippable.

## Phase 5 — Polish (P3, thin)

**Product-feel and conveniences — deliberately last.**

- **Backend:** notification engine (WhatsApp/push/weekly-PDF, scheduled reminders) · invoice-mailbox IMAP · Tally/Zoho exports · plain-English summaries.
- **Frontend:** founder mobile dashboard · visual design system · minute UX touches (dark mode, Indian number format, tooltips, shortcuts) · notification-preferences · offline PWA/auto-save/undo · animations.
- **Done when:** the tool reads as a product, not a prototype — but every underlying flow already worked before this phase began.

---

## Descope ladder (if time is short — cut top-to-bottom)

*Governed by [`SCOPE.md`](SCOPE.md). Ordered by defensibility: the least claim-relevant thing goes first. Declaration B was never in scope.*

1. **All of Section 10 (minute features)** — dark mode, shortcuts, PWA, undo/redo. **Cut first** if the novelty window (wk 9–11) is threatened.
2. **Founder dashboard polish** — keep one summary screen.
3. **Full Tax/Compliance (Module F)** beyond TCS/TDS-as-input.
4. **Full Returns/RTO (Module D)** beyond return-to-refund matching.
5. **ML anomaly upgrade** — MAD + metrics already defends Claim #2, so the ML model is expendable.
6. Live GSTIN verification → static data · Tally/Zoho export · WhatsApp digest → email.

**Protected core (never cut):** ingestion (Amazon+Flipkart+Meesho synthetic), the reconciliation engine, pricing recommendation (Claim #1), fee-schedules-as-config (Claim #3), the synthetic dataset generator (Claim #4), and **anomaly detection with published P/R/F1 (Claim #2)**.

### The protected window (hard rule)
Phase 4 (Novelty Core) is only **weeks 9–11 of 20**. **If Phase 3 (Reconciliation, wk 6–8) overruns, cut into Modules D and F — never into C or E.** The order of sacrifice is exactly the ladder above. The moment the *ML upgrade* is what's under pressure, stop and keep MAD — do not let a better model eat the write-up weeks.

---

## Critical path (cannot be parallelised)

```
Data model ▶ Ingestion ▶ Reconciliation engine ▶ Anomaly metrics ▶ Evaluation ▶ Write-up
```

**Pricing (Claim #1) also sits on the critical line** even though it comes after reconciliation — it is a graded contribution, not a branch. The Returns/Tax *thin slices* branch off and can be trimmed without breaking the path; their *full* versions are [PRODUCT] and off it entirely. Anomaly metrics (Claim #2) stay on the line because they are the primary research result — but note the protected bar is MAD+metrics, not the ML upgrade.

---

## The decisions — all now made

1. **Modular monolith + thin SPA** (not microservices, not a thick client).
2. **Two frozen contracts** — canonical line item + job lifecycle — before parallel FE/BE work.
3. **Config-not-code** for fees/tax/thresholds/mappings.
4. **Integration-gateway pattern** with fallbacks; **no external call on the reconciliation critical path**.
5. **Synthetic-data-only** posture — **Declaration A**, decided. No volunteer usability study; no real seller data at any point.
6. **WebSocket** (decided) for job progress — no polling fallback path to maintain; on disconnect, the client reconnects.
7. **Synthetic-first standing policy** (decided) — any external resource that turns paid mid-project (rate limit exhausted, trial ends) falls back to its synthetic/offline path rather than the project adopting a paid tier, for the life of the build.

Everything else (libraries, folder layout, exact schemas, endpoint names, tooling) is a runtime decision and is intentionally left open.

## Team assumption

Solo build, with a **possible but unconfirmed** second developer. The plan does not depend on them joining:
- Phase 1's contract-freeze step (canonical line item + job lifecycle) is written to hold regardless of team size — if the second developer joins later, those contracts are already stable enough to parallelize against immediately, per `CROSS-SYSTEM-DEPENDENCIES.md` §7.
- No task in `backend/PLAN.md` or `frontend/PLAN.md` assumes concurrent FE/BE work; sequencing is safe to run solo end-to-end.
- If the second developer joins, the natural split is exactly the backend/frontend folder boundary already drawn — no replanning needed, just start them on the frontend track against the frozen contracts (mocked where the backend isn't there yet).
