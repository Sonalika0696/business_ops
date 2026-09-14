# Progress Tracker — Architect / Supervisor View

> Update this file as phases progress. It is the single place to check "where are we" without re-reading the full plans.
> Tick a phase's status only when **every** exit-criteria checkbox in `backend/PLAN.md` / `frontend/PLAN.md` for that phase is checked.

## Status legend
🔲 Not started · 🟡 In progress · ✅ Complete · ⛔ Blocked

---

## Phase status

| Phase | Backend | Frontend | Blocking issues | Notes |
|---|---|---|---|---|
| 1 — Foundation | ✅ | ✅ | Redis/Celery not resolved on this dev machine (non-blocking — fail-open by design; see Frontend Phase 1 note for how processing was exercised without a worker) | All 10 backend Phase 1 exit criteria independently verified live (see below). Frontend Phase 1's 9 exit criteria also independently verified live 2026-09-15 (see below) — all screens (auth, masters, upload, history, discrepancies) built and working against the real API, not mocks. |
| 2 — Core product | 🟡 In progress | 🟡 In progress | Settlement-upload preview-before-commit has no backing endpoint (see `CROSS-SYSTEM-DEPENDENCIES.md` §6 item 6) | Backend sequencing (locked 2026-09-14): (1) ✅ Flipkart/Meesho parsers — **done 2026-09-14**, (2) ✅ FeeSchedule engine [shared substrate, DEFEND] — **done 2026-09-15**, see below, (3) Reconciliation engine full incl. MAD anomaly detection [DEFEND] — next up, (4) Audit chain, (5) Returns thin slice [DEFEND], (6) TCS/TDS accumulation, (7) Integration gateway (GSTIN/IFSC/PIN, offline-fallback-first), (8) Reporting export. Order follows `SCOPE.md`'s DEFEND priority, not just `backend/PLAN.md`'s listed order. Frontend should treat every Phase-2 screen as **mock-first** per `CROSS-SYSTEM-DEPENDENCIES.md` §2/§3 until this row's Notes say a specific capability is live — check back here rather than assuming. |

**Frontend Phase 1 (done 2026-09-15, independently verified live, not just agent-reported):** All 9 exit criteria in `frontend/PLAN.md` walked end-to-end against the real running backend (Postgres + FastAPI, both started per `backend/DEV_SETUP.md`) in a live browser session: register → auto-login, invalid-login error, logged-out redirect-to-login, marketplace-account CRUD (create + delete-confirm dialog), product CRUD including a real backend duplicate-SKU inline error, seller-profile edit+save, settlement upload via both drag-drop and file-picker, oversized-file client-side rejection, and a partial-failure upload (2 of 3 rows rejected — one bad amount, one unmapped amount-description) rendering the success count, the "Rejected rows" tab, and both reasons correctly. Ingestion history and the discrepancy queue both render real data with working loading/empty/error states.

Two real things found and fixed during this pass:
1. **Celery/Redis isn't running on this dev machine** (see `backend/DEV_SETUP.md`), so uploaded settlements sat at `UPLOADED` forever — not a frontend bug. Unblocked by calling `process_settlement(report_id, session)` directly per report (the same directly-callable escape hatch `scripts/demo_e2e.py` uses), which is the intended dev-without-a-worker path per `tasks.py`'s docstring. A background worker is still needed before this is a real async pipeline — tracked as an open item, not fixed here.
2. **`AnimatePresence mode="wait"` with a keyed sibling-swap (loading ↔ content) silently freezes the DOM on the old branch** even after React's state says it should have moved on — reproduced twice (`AsyncState`, `FileDropzone`) with framer-motion 12.x + React 18 in this stack, no console error either time. Fixed by dropping `AnimatePresence`/`mode="wait"` from both and keeping plain conditional rendering; framer-motion is still used safely elsewhere (single mount/unmount in `Dialog`, `layoutId` shared-element transitions in `Tabs`/`AppShell` nav, `whileTap` on `Button`, `AnimatePresence` in default/"sync" mode for the `Toast` stack). **Avoid the `mode="wait"` + swapped-key pattern in this codebase** unless this is root-caused properly.

**Frontend Phase 2 (in progress, self-tested live 2026-09-15 by the building agent — not yet independently re-verified):** Built against `frontend/PLAN.md` Phase 2's priority order. **Real, against the live backend:** the upload screen now takes multiple files for one period, uploads them sequentially against the real `POST /api/settlements/upload`, tracks per-file status (queued/uploading/done/duplicate/error) with a link to each resulting report, and lets the user remove a file from the queue before committing — verified live by injecting two synthetic files into the page (this browser tooling has no native file-picker) and confirming two distinct `SettlementReport` rows were created. **Mock-first** (fixture data behind hooks shaped like the real ones — see `frontend/src/api/mocks/`, swap-in is a data-source change only) because the backing engines aren't built yet: Reconciliation dashboard (expected-vs-actual by marketplace, functional bar comparison + accessible data-table fallback, anomaly review queue with working accept/dispute mutations verified live — status and pending-count both update correctly), order drill-down (linked from the queue), the un-credited-refunds queue (thin slice, "file claim" mutation verified live), and the TCS/TDS view. Every mock screen carries a visible `MockDataBanner` — a deliberate choice per `ARCHITECTURE.md` §11 ("fail closed on money"): these are money figures, and nothing should look authoritative before the real engine computes it. **Not yet built:** onboarding verification feedback (GSTIN/IFSC/PIN), CSV bulk product import, report export.

One real bug caught and fixed during this pass: `UploadPage`'s post-upload-loop summary read the `pendingFiles` state variable directly after several `setPendingFiles` calls inside the same function — since React state updates are async/batched, that closure still held pre-loop values, so the failure count and file count in the toast/redirect logic would have been wrong under real usage. Fixed by tracking `failureCount`/`totalCount` as plain local variables through the loop instead of re-deriving them from React state. Also found: the mock fixture generator picked `amount_description` and `amount_canonical` independently, producing incoherent pairs (e.g. "Shipping fee" labeled as a Closing fee) — fixed by pairing them in one lookup table.

**Phase 2, slice 1 — Flipkart + Meesho parsers (done 2026-09-14, independently verified live):** `backend/DESIGN.md` §11 is the frozen spec. Canonical-mapping lookup is now marketplace-aware (`resolve_amount_canonical(raw_description, marketplace_code)`, one CSV per marketplace under `seed_data/`); new pure parsers `flipkart.py`/`meesho.py` mirror `amazon.py`'s structure exactly, both column-drift tolerant (lookup by header name) and BOM-tolerant (Meesho's fixture is written with a UTF-8 BOM to genuinely exercise this); a `PARSERS` dispatch table in `app/modules/ingestion/parsers/__init__.py` replaces the old hardcoded-Amazon call in `tasks.py`. Synthetic generator now seeds all 3 marketplace accounts (15 shared products, 50 orders each) and emits 3 fixtures + ground truths; `demo_e2e.py` processes all 3 in one run. Verified myself, not just agent-reported: `uv run pytest` → 51/51 passed, `uv run ruff check .` → clean, `uv run python scripts/demo_e2e.py` → `=== PASS ===`, all 3 marketplaces RECONCILED with 0 rejected rows. One real bug caught during the build: the original `meesho_amount_mapping.csv` I wrote was missing an `FBA_FEE` row (13/14 enum coverage, violating §11.1's own coverage requirement) — fixed by adding `Fulfillment charge,FBA_FEE,negative`. No changes to any of the 5 frozen Phase-1 contracts. `backend/PLAN.md` Phase 2 checklist: first 3 of 12 items now ticked.

**Phase 2, slice 2 — FeeSchedule engine (done 2026-09-15, independently verified live):** `backend/DESIGN.md` §12 is the frozen spec. New pure module `app/modules/pricing/fee_engine.py`: `compute_fee_amount` implements all 5 `computation_rule` shapes (FLAT, PERCENT [Decimal/ROUND_HALF_UP], TIERED_BY_PRICE, TIERED_BY_WEIGHT, ZONE_BASED) — malformed config raises `ValueError`, legitimately-missing context (e.g. no product weight) returns `None`, never guessed; `resolve_fee_schedule` does effective-dated, category-pattern (`fnmatch`) schedule lookup with a most-specific-pattern-wins tie-break; `compute_expected_fee` orchestrates across an order's line items and returns a signed (negative) expected-fee total, or `None` if nothing was computable. Deliberately **not** wired into the settlement pipeline yet — that's slice 3 (Reconciliation engine full)'s job; this slice hands it a proven engine to call. New idempotent seed script `scripts/seed_fee_schedules.py` seeds 18 `FeeSchedule` rows (one of each rule type × 3 marketplaces, plus a category-specific `Electronics/*` REFERRAL override to exercise the specificity tie-break with real data) — re-running it inserts 0 new rows, confirmed twice myself. Verified myself: `uv run pytest` → 75/75 passed (44 new), `uv run ruff check .` → clean, seed script idempotency confirmed live. One legitimate improvement the building agent caught and flagged (not a bug, a correctness fix): used `fnmatch.fnmatchcase` instead of `fnmatch.fnmatch` — the latter case-normalizes via `os.path.normcase` on Windows, which would have made category-pattern matching silently case-insensitive in Windows dev but case-sensitive on Linux CI, a platform-dependent bug waiting to happen. Also noted: this dev DB (shared, no test rollback, same pattern as `test_reconciliation.py`) has some harmless leftover `FeeSchedule` rows from the agent's own earlier test iterations before it added per-run-unique category patterns — checked myself, they're either content-identical to the real seed rows or fall outside any realistic order's effective-date window, so they don't affect resolution correctness; cosmetic only, not cleaned up since deleting shared dev-DB rows wasn't asked for. No changes to `tasks.py`, `demo_e2e.py`, `synth_data_generator.py`, any frozen Phase-1 contract, or the slice-1 parser files. `backend/PLAN.md` Phase 2 checklist: first 5 of 12 items now ticked.
| 3 — Intelligence | 🔲 | 🔲 | — | |
| 4 — Optimization | 🔲 | 🔲 | — | |
| 5 — Polish | 🔲 | 🔲 | — | |

*(Edit the emoji + notes columns directly as work lands. Link a PR/commit in Notes when a phase closes.)*

---

## Contract freeze log

Per `CROSS-SYSTEM-DEPENDENCIES.md` §1 — the five contracts that must be frozen before parallel FE/BE work. Record the date each was frozen and whether it has changed since (a change after freeze is a signal to re-check downstream screens/services).

| Contract | Frozen on | Changed since? | Notes |
|---|---|---|---|
| Job lifecycle (submit/status/result/progress) | 2026-09-14 | No | `SettlementReport.status` enum IS the job state (no separate Job table — see `backend/DESIGN.md` §4). Verified live: upload → PARSING → PARSED → RECONCILING → RECONCILED, plus the FAILED path, all exercised by tests + the demo script. |
| Canonical settlement line item | 2026-09-14 | No | 14-enum `amount_canonical` (DESIGN.md §3), verified live against the seed mapping table (`backend/seed_data/amazon_amount_mapping.csv`) and the synthetic fixture (216 line items, 0 rejected). |
| Discrepancy / anomaly item shape | 2026-09-14 | No | No separate table — `SettlementLineItem.match_status` + `GET /api/settlements/{id}/line-items?match_status=UNMATCHED` is the discrepancy queue (DESIGN.md §2.9 design note). Verified live via real HTTP call: returned exactly the 4 orphan lines the synthetic generator injected. |
| Auth token + error envelope | 2026-09-14 | No | JWT bearer + `{"error": {"code", "message", "field_errors"}}` envelope (DESIGN.md §6). Verified live across auth/masters/ingestion routes, including the WS route's query-param-token exception (DESIGN.md §4). |
| Entity CRUD shapes (seller, product) | 2026-09-14 | No | Seller profile + Product + SellerMarketplaceAccount CRUD, all verified live incl. soft-delete and partial-unique-index (duplicate SKU) behavior. |

---

## Architecture decisions log

Record any decision made *during* runtime that deviates from or extends `ARCHITECTURE.md`. This is how you catch scope/architecture drift as supervisor without reading every commit.

| Date | Decision | Reason | Approved by |
|---|---|---|---|
| 2026-09-14 | WebSocket (not polling) for job progress; no polling fallback maintained | One progress mechanism instead of two | Project owner |
| 2026-09-14 | Declaration A locked — no volunteer usability study, no real seller data ever | Simplifies ethics/compliance; matches zero-budget constraint | Project owner |
| 2026-09-14 | Synthetic-first standing policy: any resource that turns paid mid-project falls back to synthetic/offline rather than upgrading to a paid tier | Zero-budget constraint holds for the life of the build, not just at launch | Project owner |
| 2026-09-14 | Second developer may join later but is not relied upon; plan sequenced to work solo end-to-end | Avoid blocking on an unconfirmed resource | Project owner |
| 2026-09-14 | Adopted defensibility-first scope (see SCOPE.md): DEFEND = Modules C+E cores, fees-as-config, synth generator, min ingestion, return-to-refund slice. Module D/F reduced to thesis slices; rest → PRODUCT/Phase 5 | Execution risk is scope creep (6/10); protect the wk-9–11 novelty window | Project owner |
| 2026-09-14 | MAD + published P/R/F1 is the protected Claim-#2 bar; ML anomaly model is an expendable upgrade, first to drop inside the novelty window | De-risk the graded contribution; measurement is the contribution, not model sophistication | Project owner |
| 2026-09-14 | Keep Meesho synthetic ingestion (3 marketplaces); first ingestion cut only if that work overruns | Cheap (synthetic-only) and strengthens cross-marketplace framing of Claims #1/#2 | Project owner |

---

## Descope actions taken

If the timeline slips and a cut from `ROADMAP.md`'s descope ladder is exercised, log it here so the final writeup accurately reflects what was actually built.

| Date | Cut taken | Time saved (est.) | Reversible later? |
|---|---|---|---|
| | | | |

---

## How to review a phase as supervisor

1. Open `backend/PLAN.md` and `frontend/PLAN.md`, find the phase, check its **Exit criteria checklist**.
2. Ask for a live demo against the checklist, not a code walkthrough — the checklist is written as observable behavior, not implementation detail.
3. Confirm nothing from a *later* phase leaked in early (e.g. styling work during Phase 1, pricing logic during Phase 2) — that's the main risk this plan is designed to prevent.
4. If a criterion can't be demonstrated, the phase isn't done — move it back to 🟡 and note what's missing.
5. Update the **Contract freeze log** the first time each contract is actually used by both sides; flag here if it changed after freeze (this is where FE/BE drift usually starts).
