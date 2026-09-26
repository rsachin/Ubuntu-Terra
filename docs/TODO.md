# Ubuntu Terra — Actionable Backlog

This is the living task list discovered during the onboarding review. Items are intentionally **ungrouped by phase**; future sessions can sequence them into sprints. Check items off as they are completed.

## Bugs

- [x] Fix 10 stale tests in `backend/tests/test_risk_engine.py` — update calls to use `forecast_rainfall_mm=` instead of `rainfall_readings_mm=`.
- [x] Verify the fixed risk-engine tests pass: `../venv/Scripts/python -m pytest tests/test_risk_engine.py -q`.
- [x] Investigate and resolve the Python 3.14 wheel issue for `pydantic==2.9.2` / `psycopg2-binary==2.9.9` (bump pins or document `requires-python` range).
- [ ] Remove or reorder the shadowed route `GET /api/fields/validation-stats` so it is not swallowed by `GET /api/fields/{field_id}`.
- [ ] Confirm `test_whatsapp_webhook.py` passes against a running PostGIS database (currently fails because `get_db` dependency cannot connect).
- [ ] Confirm `test_fields_router.py` and `test_database.py` pass against a seeded database.

## Missing Features

- [x] Create a single ordered migration runner (`database/migrate.py`) that applies `001→005` and optionally seeds demo fields.
- [x] Delete the ad-hoc `database/apply_migration.py` and `database/apply_migration_005.py` once the runner exists.
- [x] Persist WhatsApp delivery result in the `alerts` table (status, Twilio SID, error).
- [ ] Add file-size and image-dimension limits to `POST /api/fields/{id}/photos`.
- [ ] Add a provisional/early-stage badge in the UI when validation stats are below 20 responses.
- [ ] Add a "last refreshed" indicator for readings in the condition panel so farmers know how current the data is.
- [x] Cache external API results with a TTL (e.g. only refresh weather/NDVI if older than 6 hours) instead of re-fetching on every request.

## DevEx / Reproducibility

- [x] Add `docker-compose.yml` with services: `postgres:15-postgis`, `backend`, `frontend`.
- [x] Add a backend `Dockerfile`.
- [ ] Add a minimal GitHub Actions workflow: run backend unit tests, run frontend build.
- [x] Add a combined dev script for Windows (`scripts/dev.ps1`) that starts backend + frontend and seeds the DB.
- [ ] Add a `Makefile` or cross-platform equivalent for macOS/Linux users.
- [x] Pin or document the exact Node.js version required (currently `package.json` says Vite 8, Node 20+ recommended).
- [ ] Verify the frontend installs and builds on a clean Windows machine with the documented Node version.

## Security Hardening

- [ ] Add rate limiting to `POST /api/owners/register` to prevent `owner_id` enumeration and token-minting abuse.
- [ ] Add rate limiting to the Twilio webhook endpoint.
- [ ] Add HTTPS redirect middleware and security headers for production deployments.
- [ ] Add request logging with a stable request ID and redaction of tokens.
- [ ] Hash `owner_tokens.token` at rest (currently stored plaintext).
- [ ] Evaluate and document a post-hackathon migration path from owner tokens to password login + httpOnly cookies.
- [ ] Run `pip-audit` and `npm audit`; address or document any high/critical findings.

## Tests

- [ ] Add frontend unit/component tests (Vitest + React Testing Library) for `RiskBadge`, `TrendChart`, and the main app render.
- [ ] Add a frontend e2e smoke test (e.g. Playwright) for: map loads, at least one demo field polygon is visible, condition panel shows a risk score.
- [x] Add an integration test for the full demo data flow: create field → seed readings → compute risk → generate alert.
- [x] Add a test that verifies demo NDVI is only used for `is_demo_field = true` fields.
- [x] Add a test that verifies non-demo fields do not get synthetic data when Sentinel Hub fails.

## Documentation

- [ ] Keep `README.md`, `planning.md`, `status.md`, and `/docs` in sync as code changes.
- [ ] Update `status.md` after each fix (test count, verified-working table, missing-items list).
- [ ] Add a `CONTRIBUTING.md` with branch/PR conventions if multiple agents continue work.
- [ ] Add a security runbook: how to rotate `TWILIO_AUTH_TOKEN`, how to revoke an owner token.

## Product / Demo Polish

- [ ] Add the real `TWILIO_AUTH_TOKEN` and `TWILIO_ACCOUNT_SID` to the demo `.env` and verify end-to-end WhatsApp send + reply.
- [ ] Configure the Twilio sandbox webhook URL to match the public HTTPS URL + `/api/whatsapp/webhook`.
- [ ] Decide how to present the heuristic photo classifier in the slide deck ("vision prototype").
- [ ] Add a short `DEMO.md` script with exact click-by-click steps for a 90-second demo video.
- [ ] Record the 90-second demo video.
- [ ] Finalise Lean Business Canvas and final slide deck.
- [ ] Complete SSDLC submission.

## Known Blockers for the Human

- [ ] Confirm the demo machine will have Python 3.11–3.13 or accept 3.10.
- [ ] Confirm whether live WhatsApp is required for judging or if the simulated fallback is sufficient.
- [ ] Confirm the PostgreSQL/PostGIS install path on the demo machine (Stack Builder vs OSGeo4W vs Docker).
- [ ] Confirm if any dependency updates are allowed before the final submission deadline.
