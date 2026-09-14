# Reconciliation & Pricing Platform — Implementation Planning

Foundation-first phased plan for the Multi-Marketplace Reconciliation & Pricing Intelligence Platform (Amazon India · Flipkart · Meesho). Derived from the Software Design Document; single-tenant, synthetic-data research prototype, zero paid-API budget.

## How to read these

| Document | Answers |
|---|---|
| **[ROADMAP.md](ROADMAP.md)** | *Start here.* What to build first / next / later; the 5 macro-phases; P0–P3 priorities; descope ladder; critical path; the decisions that must be made now. |
| **[SCOPE.md](SCOPE.md)** | *The governing lens for cuts.* Dissertation-DEFEND vs. PRODUCT classification tied to the four novelty claims; the protected wk-9–11 window rule; the exact cut order. When priorities conflict, this file wins. |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | The system-level structure fixed up front — components, boundaries, data flow, contracts, persistence, integrations, failure boundaries, security. *What the system needs and how the pieces relate* — not implementation how-to. |
| **[backend/PLAN.md](backend/PLAN.md)** | Phased backend plan — services, data, processing, business logic, integrations, AI/ML — foundational vs. deferred. |
| **[frontend/PLAN.md](frontend/PLAN.md)** | Phased frontend plan — screens, flows, states, frontend architecture, API dependencies. Function before beautification. |
| **[CROSS-SYSTEM-DEPENDENCIES.md](CROSS-SYSTEM-DEPENDENCIES.md)** | How the two tracks depend on each other — contracts to freeze first, what to mock, integration bottlenecks, build sequence. |
| **[TRACKING.md](TRACKING.md)** | *For the supervisor.* Phase-by-phase status board, contract-freeze log, architecture-decision log, descope log, and how to review a phase against its exit criteria. |

## Priority key
**P0** required foundation · **P1** important next · **P2** useful improvement · **P3** advanced / later.

## The one-line summary
Build the **data model → ingestion → reconciliation** spine first (Phase 1–2); layer **pricing intelligence + benchmarked ML metrics** on top (Phase 3, the dissertation novelty); then **measure** (Phase 4) and **polish** (Phase 5). Decide topology, the two core contracts, config-not-code, the integration-gateway pattern, and the synthetic-data posture *now*; leave libraries and layout for runtime.
