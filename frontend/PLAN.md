# Frontend — Phased Plan

> Scope: screens, flows, interactions, frontend architecture, API dependencies, and the loading/error/empty/processing states needed for a genuinely usable product.
> Read alongside `../ARCHITECTURE.md` and `../CROSS-SYSTEM-DEPENDENCIES.md`.
> Priority key: **P0** required foundation · **P1** important next · **P2** useful improvement · **P3** advanced / later.

**Governing principle for now: determine *what UI must exist for the product to work*, not how it should look.** Visual beautification, animation, and design refinement are deferred to Phase 5. Every state a real workflow can land in (loading, error, empty, processing, partial) is treated as required functionality, not polish.

> **Prioritization is governed by [`../SCOPE.md`](../SCOPE.md).** The UI that surfaces the four novelty claims — reconciliation/anomaly review (Claim #2) and pricing/parity (Claim #1) — is **[DEFEND]**. Screens for full Returns/RTO, full Tax/Compliance, and the founder dashboard beyond one summary screen are **[PRODUCT]** and follow the cut order in SCOPE.md.

---

## Frontend architecture (decided up front)

- **Single-page app, thin client.** No business logic in the browser; the UI renders backend state and captures input. All fee math, matching and scoring happen server-side.
- **Server state vs. UI state are separated:** server data is fetched/cached through a data-fetching layer (query + invalidation on job completion); local UI state (form drafts, filters, selected rows) is kept separate and ephemeral.
- **One async-job UX pattern, reused everywhere:** submit → show processing state → subscribe to progress (WebSocket) or poll → render result / partial-failure. Parsing, reconciliation runs, metric runs and report generation all use it.
- **The client never calls an external service directly** — only the backend API.
- **Routing mirrors the module map** (masters, upload, reconciliation, returns, tax, pricing, dashboard) so screens map to backend boundaries.

---

## Phase 1 — Foundation (P0)

*Goal: a user can log in, set up minimal masters, upload one settlement file, watch it process, and see discrepancies. This is the minimum usable loop.*

**Screens & flows (priority-ordered)**
1. **Auth (P0)** — login; authenticated shell/layout; route guarding.
2. **Settlement upload (P0)** — file picker/drag-drop; submit; **processing state with live progress**; success + **partial-failure** (parsed vs. rejected rows) views.
3. **Ingestion history (P0)** — list of past uploads with status.
4. **Discrepancy view (P0)** — read-only list of what didn't match for a processed report.
5. **Minimal masters (P0)** — seller profile + product/SKU CRUD forms (plain, validated).

**Required frontend functionality**
- The four canonical async states rendered honestly: **loading, empty, error, processing** (+ partial success).
- Form validation surfacing backend field errors.
- Job-progress subscription (the reusable pattern).

**API dependencies:** auth, master CRUD, upload + job-status/WS, discrepancy read. (All must be contract-stable or mocked — see cross-system doc.)

**Explicitly deferred:** dashboards, charts, multi-marketplace UI niceties, any styling beyond legible defaults.

**Exit criteria checklist**
- [ ] Login works end-to-end against the real auth API; invalid credentials show a real error
- [ ] Authenticated routes redirect to login when the token is missing/expired
- [ ] Seller profile and product/SKU forms create/edit real records, with backend validation errors shown inline
- [ ] File upload works via drag-drop and picker; large/invalid files handled gracefully
- [ ] Upload shows a live processing state (not a static spinner) reflecting real job progress
- [ ] A partially-failed upload (some rows rejected) renders both the success count and the rejected rows with reasons
- [ ] Ingestion history lists past uploads with accurate status
- [ ] Discrepancy list renders real backend data with loading/empty/error states all verified (not just the happy path)
- [ ] A new team member can run the full loop (login → upload → see discrepancies) with zero backend/DB knowledge

---

## Phase 2 — Core product (P1)

*Goal: the screens that make all three marketplaces, reconciliation, returns and tax actually operable.*

**Screens & flows (priority-ordered)**
1. **Reconciliation dashboard (P1) [DEFEND — Claim #2]** — this-period expected vs. actual vs. bank; discrepancy queue; anomaly review panel with accept/dispute actions.
2. **Order-level drill-down (P1) [DEFEND]** — what a specific order actually earned.
3. **Full upload UX (P1) [DEFEND]** — per-marketplace file typing; multi-file for one period; **preview-before-commit** with reject; parsing-errors panel.
4. **Onboarding flow (P1)** — masters with external verification feedback (GSTIN valid/invalid, IFSC autofill, PIN→state, Udyam), CSV bulk product import with row-level errors. *(Live-verification UI is a nicety; static/offline feedback is an acceptable dissertation substitute.)*
5. **Un-credited-refund queue (P1) [DEFEND — thin slice]** — the one Returns screen the reconciliation story needs. *(Full open-returns dashboard, RTO tracker, claim workspace → [PRODUCT], Phase 5.)*
6. **TCS/TDS view (P1) [DEFEND-adjacent]** — only what shows the deductions feeding margin/net-payout. *(GSTR-1 helper, compliance calendar, threshold warnings → [PRODUCT], Phase 5.)*
7. **Report export (P2)** — trigger + download reconciliation reports.

**Required frontend functionality**
- Tabular data with sorting/filtering and bookmarkable filters.
- Functional (not beautiful) charts for the reconciliation dashboard.
- Action affordances (accept / dispute / mark-claimed) wired to backend state transitions.
- Consistent handling of "backend returned partial / degraded (e.g. LLM unavailable → manual-review)" states.

**API dependencies:** full ingestion, reconciliation results, returns, tax summaries, FeeSchedule (read-only viewer).

**Explicitly deferred:** pricing UI (Phase 3); full Returns/RTO + full Tax/Compliance screens, founder mobile dashboard, notifications UI, visual design system (all [PRODUCT], Phase 5).

**Exit criteria checklist**
- [ ] Reconciliation dashboard shows this-period expected vs. actual vs. bank with real numbers
- [ ] Anomaly review panel supports accept/dispute actions that persist to the backend
- [ ] Order drill-down shows real per-order earnings breakdown
- [ ] All three marketplaces selectable in upload UI; multi-file upload for one period works
- [ ] Preview-before-commit lets the user inspect and reject a bad upload before it's processed
- [ ] Parsing-errors panel shows real rejected rows with reasons
- [ ] Onboarding shows live verification feedback (GSTIN valid/invalid, IFSC autofill, PIN→state) and degrades sensibly when the service is unavailable
- [ ] CSV bulk product import shows row-level validation errors
- [ ] Un-credited-refund queue renders real data (thin slice; full RTO tracker/claim workspace are [PRODUCT], Phase 5)
- [ ] TCS/TDS view shows correct real figures feeding margin/net-payout (full GSTR-1/calendar are [PRODUCT], Phase 5)
- [ ] Reconciliation report downloads successfully from the UI

---

## Phase 3 — Intelligence / advanced UI (P2 → P3)

*Goal: surface the novelty features.*

**Screens & flows**
1. **Pricing intelligence screens (P2) [DEFEND — Claim #1]** — cross-marketplace parity view; per-SKU profitability calculator; price recommendation with margin curve; fee-simulation "what-if" tool.
2. **Anomaly-metrics / evaluation view (P2) [DEFEND — Claim #2]** — present benchmarked P/R/F1 (primarily for the dissertation; can be a simple results screen or exported figures).
3. **Claim drafting UI (P3) [PRODUCT]** — assemble evidence packet, review drafted claim, one-click "mark as claimed".
4. **"Correct me" affordances (P3) [PRODUCT]** — let a user fix an AI classification.

**Required frontend functionality**
- Interactive parameter inputs feeding backend computation (what-if, target margin).
- Charts that carry real analytical meaning (margin curves, threshold sweeps) — functional first, styled in Phase 5.

**API dependencies:** pricing service, ML/metrics endpoints, LLM-classification results, claim-drafting service.

**Exit criteria checklist**
- [ ] Price recommendation screen returns a real recommended price with margin curve for a test SKU
- [ ] Fee-simulation "what-if" tool updates results live as inputs change
- [ ] Cross-marketplace parity view flags a genuine mismatch visually
- [ ] Anomaly-metrics view displays real P/R/F1 figures across thresholds (not placeholder numbers)
- [ ] Claim drafting UI shows an assembled evidence packet and lets the user review/edit before submission
- [ ] "Correct me" affordance on an AI classification actually persists the correction

---

## Phase 4 — (mostly backend) — frontend items only

*The optimization phase is largely backend. Frontend contributions are limited to:*
- **Reliability UX (P2):** clear surfacing of job failures/retries; never leave the user on an indefinite spinner (timeouts + retry affordance).
- **Empty/error-state completeness audit (P2):** confirm every list/detail screen handles no-data and failure gracefully.

**Exit criteria checklist**
- [ ] Every async action has a timeout + visible retry affordance (no indefinite spinners)
- [ ] Every list/detail screen audited and confirmed to handle empty and error states correctly

---

## Phase 5 — Polish (P3)

*Goal: product-feel and beautification — deliberately last.*

**Priority-ordered**
1. **Founder mobile dashboard (P3)** — one-page cash/receivables/alerts/this-week view, marketplace P&L side-by-side, fee-leakage counter, notifications inbox. *(Functional data already exists from Phase 2; this is the polished consumer surface.)*
2. **Visual design system (P3)** — typography, spacing, color, component styling, status badges.
3. **Minute UX touches (P3)** — dark mode, Indian number formatting (1,00,000), ₹/paise precision display, tooltips for jargon (TCS, SAFE-T, MRP), keyboard shortcuts, onboarding checklist, empty-state illustrations.
4. **Notification-preferences UI (P3)** — WhatsApp/email/push settings.
5. **Reliability niceties (P3)** — offline PWA cache for the reconciliation report viewer, auto-save on forms, undo/redo on price changes.
6. **Animations & transitions (P3)** — last, and only where they aid comprehension.

**Dependencies on earlier phases:** all functional screens from Phases 1–3 (polish decorates working flows; it never precedes them).

**Exit criteria checklist**
- [ ] Founder mobile dashboard renders correctly on a real phone-width viewport with live aggregated data
- [ ] Design system tokens (type, spacing, color, status badges) applied consistently across all screens
- [ ] Dark mode toggle works across every screen without contrast/legibility issues
- [ ] Indian number formatting and paise-precision amounts display correctly throughout
- [ ] Tooltips present on all identified jargon terms (TCS, SAFE-T, MRP, etc.)
- [ ] Notification preferences save and are respected by the backend notification engine
- [ ] Offline PWA cache serves the reconciliation report viewer without a network connection

---

## Frontend cross-cutting (upheld throughout)
- Every screen renders the four states: loading, empty, error, processing.
- No screen assumes a backend call succeeds; degraded/partial responses have a defined UI.
- Server state and UI state stay separated; job-completion invalidates cached queries.
- Accessibility basics (focus states, labels) are built in from Phase 1 — cheaper than retrofitting.
