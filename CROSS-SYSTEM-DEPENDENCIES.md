# Cross-System Dependencies (Frontend ↔ Backend)

> Purpose: keep the two tracks from becoming isolated. This maps which backend capability each frontend feature needs, which contracts must be frozen first, what can be mocked, and where integration bottlenecks lurk.

---

## 1. Contracts to freeze first (before parallel work begins)

These are the seams both sides code against. Freeze and mock them at the start of Phase 1 so frontend and backend proceed independently.

| Contract | Why it's first | Consumed by |
|---|---|---|
| **Job lifecycle** (submit → status → result, + progress events) | Every async surface reuses it | Upload, recon runs, metrics, report export |
| **Canonical settlement line item** (14-enum normalized shape) | The unit all reconciliation UI displays | Discrepancy view, drill-down, reports |
| **Discrepancy / anomaly item** shape | Core of the main working screen | Reconciliation dashboard, review panel |
| **Auth token + error envelope** | Guards every route; standard error rendering | All screens |
| **Entity CRUD shapes** (seller, product) | Masters forms | Onboarding, product master |

**Rule:** these five are agreed as schemas before either side builds against them. Changing them later is the most expensive kind of rework.

---

## 2. Feature → required backend capability

| Frontend feature (phase) | Requires backend | Can start against a mock? |
|---|---|---|
| Login / shell (P1) | Auth service | Yes → real early |
| Settlement upload + progress (P1) | Ingestion + job tier + WS | **Mock job lifecycle first**, wire real when parser lands |
| Discrepancy view (P1) | Recon v0 output | Yes (fixture data) |
| Masters forms (P1) | Master CRUD | Yes |
| Reconciliation dashboard (P2) | Full recon engine + FeeSchedule | Mock aggregate shape; real after engine |
| Onboarding verification feedback (P2) | Integration gateway (GSTIN/IFSC/PIN) | Mock responses; real after gateway |
| Returns / RTO screens (P2) | Returns service | Yes (fixtures) |
| Tax screens (P2) | Tax service | Yes (fixtures) |
| Pricing screens (P3) | Pricing service | Mock margin curves; real after service |
| Anomaly-metrics view (P3) | ML metrics endpoint | Real (it's the research output) |
| Claim drafting (P3) | Claim-drafting + PDF | Mock draft; real after service |
| Founder dashboard (P5) | Dashboard aggregates (exist by P2) | Real data available; polish only |

---

## 3. What can be mocked initially

- **The entire async-job surface** can run against a mock lifecycle from day one — this is what lets the upload UX be built before any real parser exists.
- **External-integration responses** (GSTIN valid/invalid, IFSC autofill, LLM classification) — mock at the gateway boundary so onboarding UI and degraded-state UI are built without live keys.
- **Reconciliation aggregates and pricing curves** — fixture payloads matching the frozen shapes.

## 4. What must be real early (cannot be meaningfully mocked)

- The **data model** — everything derives from it; freeze in Phase 1.
- The **FeeSchedule engine** — its output shape drives both reconciliation and pricing; the *rule schema* must be real before P2 UI relies on it.
- The **ML anomaly metrics** — the dissertation result itself; no mock substitutes.

---

## 5. Architectural decisions that affect both sides

| Decision | Frontend impact | Backend impact |
|---|---|---|
| Async-job pattern (not inline) | Must build processing/progress UX, not just request/response | Must build queue + status + WS |
| Partial-success is first-class | Must render "980 parsed / 20 rejected" | Must return partial results + reasons |
| No external call on recon critical path | Must render "LLM unavailable → manual review" degraded state | Must implement the fallback path |
| Config-not-code (FeeSchedule) | Read-only fee-schedule viewer screen | jsonb rule engine |
| Money to paise, UTC-store/IST-display | Display formatting rules | Storage/precision rules |
| Soft-delete / append-only | "Deleted" items may still be shown as inactive | No hard-delete endpoints |

---

## 6. Integration bottlenecks to watch

1. **The job lifecycle is the highest-traffic seam** — if its contract churns, every async screen breaks. Freeze it hardest.
2. **FeeSchedule rule shape** couples reconciliation *and* pricing to the same jsonb structure; a late change ripples across two modules and their UIs.
3. **The upload/parse partial-failure shape** is easy to under-specify; agree the rejected-row error format early or the errors panel gets reworked.
4. **External verification during onboarding** can block the onboarding flow if the fallback isn't ready — build the mock/offline path *with* the happy path, not after.
5. **WebSocket vs. polling** for progress — pick one transport in Phase 1; supporting both later is wasted effort.

---

## 7. Recommended build sequence to avoid blocking

1. Freeze the five Phase-1 contracts (§1).
2. Backend builds data model + auth + job tier; frontend builds auth + upload UX against the **mock** job lifecycle in parallel.
3. Backend lands the first real parser → frontend swaps mock for real with no UI change (that's the payoff of contract-first).
4. Repeat per module: agree shape → mock on frontend → build real backend → swap.
