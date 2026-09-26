# Ubuntu Terra — Technical Debt Register

This file captures known technical debt discovered during the onboarding review. Items are ranked P0 (blocks demo/judging) → P3 (nice to have). Items marked **Hackathon-acceptable** are conscious compromises for the deadline; items marked **Must fix before usable** should be addressed before the app is presented as production-ready.

---

## Prioritised Debt Table

| Priority | Item | Location | Why it's debt | Risk if unaddressed | Suggested fix |
|----------|------|----------|---------------|---------------------|---------------|
| ~~P0~~ ✅ | Stale risk-engine tests fixed | `backend/tests/test_risk_engine.py` | Updated to use the `forecast_rainfall_mm` signature; all no-DB tests now pass. | — | Closed in Phase 1. |
| ~~P0~~ ✅ | Single ordered migration runner created | `database/migrate.py` | Applies `001→005` in order and supports `--seed` / `--reset`. Ad-hoc scripts deleted. | — | Closed in Phase 1. |
| ~~P0~~ ✅ | Docker / local deployment config added | repo root | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `.dockerignore` added. Provides a one-command PostGIS + backend + frontend stack. | GitHub Actions CI is still pending (Phase 6). | Closed in Phase 1. |
| **P1** | Live WhatsApp demo blocked without token | `.env.example:20`, `backend/app/services/whatsapp_service.py:24–26`, `backend/app/routers/fields.py:405–423` | `TWILIO_AUTH_TOKEN` and `TWILIO_ACCOUNT_SID` are empty by default. Webhooks fail closed (500); outbound sends are `simulated`. | The most impressive feature is dead in the demo unless the real token is present and the webhook URL matches exactly. | Add the real Twilio Auth Token to `.env` on the demo machine, set the sandbox webhook URL, and re-verify end-to-end. |
| **P1** | Native Windows smoke test blocked by missing PostGIS | local PostgreSQL 17 on review machine | `database/migrate.py --seed` fails at `CREATE EXTENSION postgis;` because PostGIS is not installed in the local PostgreSQL. | Native Windows setup cannot be fully verified on this machine. | Use the Docker Compose path (`docker compose up --build`) on this machine, or install PostGIS via Stack Builder/OSGeo4W for native setup. |
| ~~P1~~ ✅ | Python dependency pins may fail on 3.14 | `backend/requirements.txt`, `backend/pyproject.toml` | `requires-python = ">=3.10,<3.14"` added to `pyproject.toml`; pins remain explicit. | Future environment upgrades break the install if someone tries 3.14. | Document the supported range and consider bumping pins post-hackathon. |
| **P1** | Owner-token auth is demo-grade | `backend/app/routers/fields.py:75–159`, `frontend/src/api/client.js:13–69` | No passwords, sessions, expiry, rotation, or rate limiting; token stored in `localStorage`; `owner_id` enumeration is trivial. | Data isolation relies on an easily leakable, never-expiring token. Not acceptable for real farm data. | For the hackathon: document the limitation. Post-hackathon: add password login, httpOnly cookies, token expiry/rotation, and rate limiting on `/api/owners/register`. |
| ~~P1~~ ✅ | Backend entrypoint / combined dev script | `scripts/dev.ps1` | Single PowerShell script starts PostgreSQL (if installed as a service), applies migrations/seeds, and launches backend + frontend in new windows. | macOS/Linux Makefile still pending. | Closed in Phase 1. |
| **P2** | No rate limiting | `backend/app/routers/fields.py` | Public endpoints such as `/api/owners/register`, `/api/validation-stats`, and the webhook have no rate limits. | Abuse/DoS risk; `owner_id` enumeration on registration is trivial. | Add FastAPI middleware or dependency-based rate limiting (e.g. `slowapi`) for registration and webhook endpoints. |
| **P2** | No file-size / upload quotas | `backend/app/routers/fields.py:482–540` | Photo uploads accept any size image; `backend/uploads/` grows without bound. | Disk exhaustion; slow uploads; potential abuse. | Add a `UploadFile` size limit, image resize/compression, and periodic cleanup or S3-backed storage. |
| **P2** | Per-request external API calls | `backend/app/routers/fields.py:724–770` | Every `/readings`, `/risk`, `/alerts` call re-fetches weather and attempts NDVI. | External service rate limits, slow response times, unnecessary load. | Cache readings with a TTL (e.g. only refresh if older than 6 hours) and add a background refresh scheduler. |
| **P2** | No input sanitisation on owner_id / field names | `backend/app/routers/fields.py:101, 207` | `owner_id` and `name` are stripped but otherwise stored verbatim. | Potential for stored abuse strings; no XSS filter. | Add length limits and basic sanitisation; escape output in frontend. |
| **P2** | Photo classifier is heuristic-only | `backend/app/services/pest_vision.py` | Uses filename keywords + simple pixel colour ratios, not a trained model. | Misleading "AI" claims; low accuracy on real crop photos. | Replace with a real plant-health model (e.g. TensorFlow/PyTorch) or clearly label the feature as a heuristic demo in UI/slides. |
| **P2** | `alerts` table does not store delivery status | `database/migrations/001_initial_schema.sql:47–54` | The Twilio/simulated result from `whatsapp_service.py` is returned to the caller but never persisted. | Cannot tell whether an alert was actually delivered; no audit trail. | Add `status`, `provider_message_id`, `error` columns to `alerts` and persist the `wa_result` dict. |
| **P2** | Validation stats threshold unreachable in demo | `backend/app/routers/fields.py:618–650`, `frontend/src/components/DisclaimerModal.jsx` | Agreement rate is hidden until 20 feedback responses; a judge will never see a validated state. | Demo gives the impression the tool has no real-world validation. | Show a provisional/early-stage badge below the threshold and explain why. |
| **P2** | Unhandled shadowed route | `backend/app/routers/fields.py:315, 618` | `GET /api/fields/validation-stats` is shadowed by `GET /api/fields/{field_id}` because of declaration order. | A documented/expected path returns a field instead of stats. | Remove the shadowed route or reorder routers so `/validation-stats` is the only alias. |
| **P3** | No structured logging / observability | entire backend | Only `logger.warning` in WhatsApp service; no request IDs, metrics, or tracing. | Hard to debug failures in production or during demo. | Add a structured logger (e.g. `structlog`) and basic request/response middleware. |
| **P3** | No HTTPS redirect / HSTS | `backend/app/main.py` | CORS is set, but no middleware forces HTTPS or sets security headers. | Token and webhook traffic can be downgraded to HTTP. | Add `HTTPSRedirectMiddleware` and security headers behind an environment flag. |
| **P3** | No dependency vulnerability audit | `backend/requirements.txt`, `frontend/package.json` | Pins are fixed but not continuously checked. | Unknown CVE exposure. | Run `pip-audit` / `npm audit` and document a cadence; consider Dependabot. |
| **P3** | Frontend has no tests | `frontend/` | No unit, component, or e2e tests. | UI regressions go undetected. | Add at least a smoke test with Vitest + React Testing Library, plus an e2e test for the demo path. |
| **P3** | Hardcoded strings / demo region assumptions | `backend/app/services/whatsapp_voice.py:42`, `frontend/src/components/FieldMap.jsx:67`, `frontend/src/components/AlertPreview.jsx` | Placeholder "Patensie" in voice message; initial map center is Eastern Cape. | Not reusable for other regions without code changes. | Make defaults configurable via env vars or user profile. |
| **P3** | No data retention / rollup policy | `backend/app/routers/fields.py:724–770` | Readings and risk_scores accumulate indefinitely. | Database bloat over a growing season. | Add a cleanup job that archives or aggregates readings older than one season. |

---

## Conscious Hackathon Limitations (Acceptable for 27 Sep Demo)

These are deliberate shortcuts agreed in `planning.md` and `status.md`. They should be flagged in the slide deck/demo narrative, not silently fixed before submission.

| Limitation | Why it is acceptable | How to present it |
|------------|----------------------|-------------------|
| Owner-token auth instead of real login | Real auth (passwords, sessions, cookies) is too much for a 48-hour hackathon and not a judging gate. | Call it "demo-grade access control" and note the production roadmap in the security slide. |
| Hand-drawn demo field boundaries | Real cadastral boundaries are private; auto-detection needs ML training data. | State that boundaries are representative rectangles around real towns for demo purposes. |
| Photo diagnosis uses heuristics | A real vision model needs training data + GPU infra beyond the hackathon. | Label it "vision prototype" and explain the planned upgrade to a trained plant-health model. |
| Validation stats threshold of 20 | Prevents meaningless percentages with tiny sample sizes. | Show the provisional "Early Stage" badge and explain the threshold. |
| Simulated WhatsApp without live token | Twilio sandbox setup requires a private token and public URL. | Demo the generated message, MP3, and webhook verification locally; explain live send needs the token. |
| Docker / CI not fully proven in CI | Docker Compose is provided and runs locally, but no GitHub Actions gate exists yet. | Provide the `LOCAL_SETUP_WINDOWS.md` and Docker paths; mention CI is the next step. |

---

## Must Fix Before It Is Presented as Usable

These items must be resolved before the app is marketed or operated with real farmer data.

1. **Replace owner-token auth** with password-based login, token expiry/rotation, httpOnly cookies, and rate limiting on registration.
2. **Add HTTPS-only transport** with HSTS and secure cookie flags.
3. **Persist alert delivery status** and add retry logic for Twilio failures.
4. **Replace the heuristic photo classifier** with a validated agronomic vision model and an admin review queue.
5. **Add file-size limits, image compression, and virus scanning** for uploads.
6. **Implement request-level rate limiting** and abuse detection.
7. **Add structured logging, monitoring, and paging** for service health and data-pipeline failures.
8. **Audit dependencies** for CVEs and set up automated updates.
9. **Add real field-boundary auto-detection** from satellite imagery (e.g. OneSoil-style workflow).
10. **Add a data-retention and privacy policy**, including farmer consent and geospatial data handling.
