# Progress Tracker — Architect / Supervisor View

> Update this file as phases progress. It is the single place to check "where are we" without re-reading the full plans.
> Tick a phase's status only when **every** exit-criteria checkbox in `backend/PLAN.md` / `frontend/PLAN.md` for that phase is checked.

## Status legend
🔲 Not started · 🟡 In progress · ✅ Complete · ⛔ Blocked

---

## Phase status

| Phase | Backend | Frontend | Blocking issues | Notes |
|---|---|---|---|---|
| 1 — Foundation | 🔲 | 🔲 | — | |
| 2 — Core product | 🔲 | 🔲 | — | |
| 3 — Intelligence | 🔲 | 🔲 | — | |
| 4 — Optimization | 🔲 | 🔲 | — | |
| 5 — Polish | 🔲 | 🔲 | — | |

*(Edit the emoji + notes columns directly as work lands. Link a PR/commit in Notes when a phase closes.)*

---

## Contract freeze log

Per `CROSS-SYSTEM-DEPENDENCIES.md` §1 — the five contracts that must be frozen before parallel FE/BE work. Record the date each was frozen and whether it has changed since (a change after freeze is a signal to re-check downstream screens/services).

| Contract | Frozen on | Changed since? | Notes |
|---|---|---|---|
| Job lifecycle (submit/status/result/progress) | — | — | |
| Canonical settlement line item | — | — | |
| Discrepancy / anomaly item shape | — | — | |
| Auth token + error envelope | — | — | |
| Entity CRUD shapes (seller, product) | — | — | |

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
