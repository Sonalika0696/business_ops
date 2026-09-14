# Scope — Dissertation Core vs. Product Depth

> **This document is the governing lens for prioritization and cuts.** The phase plans (`backend/PLAN.md`, `frontend/PLAN.md`) order work by *dependency* (what must exist before what). This document orders it by *defensibility* (what the examiners actually score). **When the two disagree, this document wins for deciding what to protect and what to cut.**

The execution risk in the design doc is rated 6/10 **specifically because of scope creep**. This file exists to make scope-creep decisions pre-committed rather than improvised at week 10.

---

## The rule everything else serves

**The four novelty claims are the product. Everything else is packaging.** A feature earns its place only if it defends a claim or is a hard dependency of something that does.

| Claim | What defends it | Status |
|---|---|---|
| **#1 — Integrated pricing + reconciliation** | Module E: net-margin per marketplace + price recommendation engine | **DEFEND** |
| **#2 — Benchmarked fee-anomaly detection** | Module C: anomaly detector **with published precision / recall / F1** | **DEFEND** |
| **#3 — Fee-schedules-as-configuration** | FeeSchedule genuinely config-driven, **shared by C and E** (not hardcoded) | **DEFEND** |
| **#4 — Open reproducible dataset** | Synthetic generator with injected known overcharges, clean enough to publish | **DEFEND** |

---

## DEFEND — thesis-critical (protect aggressively)

Cutting any of these weakens a claim. These are non-negotiable.

- **Module C — Reconciliation (core)**
  - Order↔settlement matching; fee-line matching against FeeSchedule
  - **Anomaly detection with published P/R/F1** — Claim #2. *(See refinement below: MAD alone clears this bar.)*
  - Discrepancy queue + anomaly review panel
- **Module E — Pricing Intelligence (core)**
  - Real-time net-margin computation per marketplace
  - Price recommendation engine — Claim #1, the thing no competitor ships
  - Cross-marketplace price parity alerts
- **Fee-schedules-as-configuration** — Claim #3. Must be genuinely config-driven and **shared as the single substrate under both C and E**, or the claim is a design intention, not a contribution.
- **Synthetic dataset generator** — Claim #4. The research artefact. Needs injected known overcharges and must be clean enough to publish.
- **Minimum viable ingestion (Module B)** — Amazon + Flipkart + Meesho parsers (all synthetic). Functional, not polished — it exists to feed the reconciliation engine.
- **Thin slice of Module D** — **return-to-refund matching only.** Un-credited refunds are a major input to the reconciliation story. Everything else in D is product depth.

### Three refinements to the above (decided)

1. **Fees-as-config is the shared substrate, not a standalone deliverable.** The same FeeSchedule config must drive reconciliation's expected-fee math *and* pricing's margin math. It cannot be "ticked off"; it is the thing both engines read.
2. **The protected Claim #2 bar is "a detector *with* rigorous metrics" — MAD alone clears it.** The measured accuracy is the contribution, not the model's sophistication. **MAD + benchmarked P/R/F1 is the load-bearing, protected version.** The ML upgrade is desirable-not-required and is the first thing to drop inside the novelty window if it runs long.
3. **Keep Meesho ingestion.** It is synthetic-only anyway (no API), so a third parser is just one more CSV schema — cheap — and three marketplaces make the cross-marketplace framing of Claims #1/#2 materially stronger than two. It is the *first ingestion cut* only if that specific work overruns, never a pre-emptive drop.

---

## PRODUCT — post-dissertation (cut in this order if time is short)

These make it a sellable product but do not strengthen the academic contribution. The design doc's own "recommended cuts" agree with most. **Cut top-to-bottom.**

1. **All of Section 10 (Minute Features)** — dark mode, keyboard shortcuts, voice notes, offline PWA, "explain like I'm five", undo/redo. **Cut first** if the novelty window (wk 9–11) is threatened. Zero defensibility impact.
2. **Founder Dashboard polish (Module G)** — one summary screen is enough. P&L exports, alert sorting, mobile-specific UX are product features.
3. **Full Tax & Compliance (Module F)** — GSTR-1 helper, e-invoice monitor, composition calculator, reverse-charge tracker. **Keep TCS/TDS tracking only, and only because it feeds the margin math (E) and net-payout reconciliation (C).** The rest is compliance tooling, not reconciliation research.
4. **Full claim-drafting + FBA reimbursement automation** — auto-drafted claim bodies, evidence PDFs, outcome tracking are product depth. RTO cost calculator + trending may stay as a *stretch goal* only.
5. **Live GSTIN / Udyam verification** → static test data (doc already suggests this).
6. **WhatsApp digest / Twilio** → email report is sufficient.
7. **Tally / Zoho export formats** → irrelevant to the thesis.
8. **Volunteer usability testing** → already closed by the Declaration A decision; not in scope.

---

## The protected window (hard rule)

Phase 4 (Novelty Core) is **only weeks 9–11 of 20**. Protect it aggressively.

> **If Phase 3 (Reconciliation, wk 6–8) runs long, cut into Module D and Module F — never into Module C or Module E.**
>
> Order of sacrifice when any phase overruns: Section 10 → Module G polish → Module F (beyond TCS/TDS) → Module D (beyond return-to-refund) → ML anomaly upgrade (MAD stays) → *only then* is the schedule genuinely at risk and the supervisor should be told.

The moment the ML upgrade is the thing under pressure, stop — MAD + metrics already defends Claim #2. Do not let the pursuit of a better model consume the write-up weeks.

---

## Reduced-scope module definitions (as amended)

- **Module D — Returns/RTO** is reduced to **return-to-refund matching + un-credited-refund detection** for the dissertation. Claim drafting, evidence PDFs, FBA reimbursement automation, outcome tracking → PRODUCT.
- **Module F — Tax & Compliance** is reduced to **TCS/TDS accumulation as an input to margin (E) and net-payout (C)**. GSTR-1/3B helpers, threshold monitors, composition/reverse-charge → PRODUCT.
- **Module G — Founder Dashboard** is reduced to **one summary screen** for the dissertation. Polish, exports, mobile UX → PRODUCT (Phase 5).

These reductions are reflected in `backend/PLAN.md` and `frontend/PLAN.md`; this file is the rationale of record.
