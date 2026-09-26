# Ubuntu Terra — Implementation Phases Plan

This plan takes Ubuntu Terra from its **current Phase 0 state** (onboarding review complete, four `/docs` artifacts written) to a **hackathon-ready, demoable, genuinely usable product** aligned with the judging criteria and the "Build for Use" theme.

## Phase 0 Recap: What We Found

- **Frontend:** React 19 + Vite 8 + MapLibre GL 6. Feature-complete for onboarding, map, condition panel, trend charts, WhatsApp alert preview, and photo upload. No frontend tests.
- **Backend:** FastAPI 0.115 + Uvicorn + psycopg2. Core endpoints, risk engine, weather/satellite services, WhatsApp integration, and webhook verification are implemented.
- **Database:** PostgreSQL + PostGIS with five idempotent migrations (`001`–`005`). No single ordered runner; demo fields seed correctly.
- **Tests:** 52 passing, 10 failing (all in `test_risk_engine.py` — stale signature). No frontend tests. Integration tests need a live seeded DB.
- **DevEx:** No Docker, no CI/CD, no combined dev script.
- **Security:** Demo-grade owner-token auth, explicit CORS allow-list, verified Twilio signatures, parameterized SQL. No rate limiting, no HTTPS enforcement, no token hashing.

## Sequencing Principles

1. **Foundational before feature:** fix the red test suite and migration runner before adding new capabilities.
2. **Feature before polish:** harden the data pipeline and API before UX refinements.
3. **Polish before demo-readiness:** the app must be runnable and demoable at the end of every phase.
4. **Security is not a finishing coat:** a dedicated security pass happens after core features are stable, with artifacts feeding the SSDLC submission.
5. **Business alignment is the final gate:** the running product must visibly support the Lean Business Canvas and the 90-second pitch.

## Judging Criteria Mapping

| Judging Criterion | Weight | Primary Phase | How it is addressed |
|-------------------|--------|---------------|---------------------|
| Innovation & Creativity | 15% | 2, 3, 4 | Explainable risk engine, satellite + weather fusion, WhatsApp voice, photo diagnosis |
| Technical Implementation | 15% | 1, 2, 3, 5 | Green test suite, working data pipeline, validated API, security hardening |
| Usability & Design | 10% | 4, 6 | Responsive UI, plain-language explanations, seeded demo, demo script |
| Security & Ethics | 10% | 5 | SSDLC artifacts, auth audit, input validation, data-privacy notes |
| Business & Presentation | 15% | 7 | Lean Canvas alignment, impact metrics, demo video/story |
| Bonus: Quantum Tech | 5% | — | Not applicable; no quantum component is part of this product. |

## Phase Overview

| Phase | Goal | Main TODO.md References | Exit Gate |
|-------|------|------------------------|-----------|
| **Phase 1 — Stabilize & Run** | Fix broken tests, create a single migration runner, verify the local Windows setup end-to-end | TODO Bugs #1–3, DevEx #1–5 | All backend unit tests pass; `LOCAL_SETUP_WINDOWS.md` smoke test completes successfully |
| **Phase 2 — Core Data Layer** | Harden schema, seed data, ingestion, and alert persistence | TODO Missing Features #1–3, Tests #4–5 | Demo fields seed cleanly; weather/NDVI real data path works; alert delivery status persisted |
| **Phase 3 — Core API Hardening** | Validate and tighten field/risk/feedback endpoints; fix shadowed route | TODO Bugs #4, Missing Features #4, Tests #3 | `test_fields_router.py` green; input validation audited; all API tests pass |
| **Phase 4 — Map & Farmer UI** | Responsive/robust frontend, seeded demo narrative, UX polish | TODO Tests #1–2, Product/Demo #1–3 | Frontend build passes; map + panel demoable; no console errors on golden path |
| **Phase 5 — Security & Ethics** | Auth/validation/privacy hardening mapped to SSDLC | TODO Security #1–7, Docs #3 | Rate limiting on registration; security runbook; SSDLC submission draft |
| **Phase 6 — Demo Readiness** | Rehearsed golden-path demo, <90s video plan, final docs | TODO Product/Demo #4–7, Tests #2 | 90-second demo script exists; video recorded; all P0/P1 debt in scope closed |
| **Phase 7 — Business Alignment** | Lean Canvas / pitch alignment and impact measurement | TODO Product/Demo #8, Blockers for Human #1–4 | Business slide deck and Canvas reflect the running product |

## Gating Rules

- A phase may **not** start until the previous phase's Definition of Done is verified and the human confirms go-ahead.
- Any new technical debt discovered during a phase must be logged in `/docs/TECHNICAL_DEBT.md` and either resolved in the current phase or explicitly accepted and moved to the "Hackathon-acceptable" section.
- The app must start locally and the core demo path must work at every phase boundary.
- Every code change references at least one TODO.md item in its commit message or PR description.

## Cross-Phase Dependencies

- Phase 2 depends on Phase 1 because the migration runner and green tests are prerequisites for trustworthy data-layer changes.
- Phase 3 depends on Phase 2 because API tests assert against real/seeded data.
- Phase 4 depends on Phase 3 because the UI consumes hardened endpoints.
- Phase 5 (security) can run in parallel with Phase 4 (UI polish) once Phase 3 is complete, but its **deliverables** must be finalized after Phase 3.
- Phase 6 and 7 are sequential and must happen last.

---

## Individual Phase Files

Each phase is detailed in its own file so an agent can be handed a single document and work independently:

- [`phase-1.md`](phase-1.md) — Stabilize & Run
- [`phase-2.md`](phase-2.md) — Core Data Layer
- [`phase-3.md`](phase-3.md) — Core API Hardening
- [`phase-4.md`](phase-4.md) — Map & Farmer UI
- [`phase-5.md`](phase-5.md) — Security & Ethics Hardening
- [`phase-6.md`](phase-6.md) — Demo Readiness
- [`phase-7.md`](phase-7.md) — Business Alignment
