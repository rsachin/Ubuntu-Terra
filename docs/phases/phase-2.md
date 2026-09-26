# Phase 2 — Core Data Layer

## Goal

Harden the data layer so the app reliably ingests, stores, and reports real geospatial and weather data, with trustworthy demo fallback data and a persistent alert audit trail.

## What Is Already Present (from Phase 0)

- `fields`, `readings`, `risk_scores`, `alerts`, `photo_diagnoses`, `farmer_feedback`, `owner_tokens` tables.
- Idempotent migrations and a (now Phase 1) migration runner.
- `seed_demo_fields.py` inserts 3 demo fields and a synthetic NDVI trigger for Patensie.
- `weather.py` (Open-Meteo + NASA POWER fallback) and `satellite.py` (Sentinel Hub) services.
- `_sync_readings()` and `_seed_demo_ndvi_trigger()` in `routers/fields.py`.

## Scope IN

1. Verify and harden the PostGIS schema.
2. Ensure demo seed data is reproducible and clearly labelled.
3. Add a time-to-live (TTL) cache for external API calls.
4. Persist WhatsApp delivery status in the `alerts` table.
5. Add integration tests for the full data pipeline.

## Scope OUT

- New external data sources beyond Open-Meteo, NASA POWER, and Sentinel Hub.
- Background job scheduler (e.g. Celery) — keep it simple with request-time TTL caching.
- Alert retry logic (Phase 3 scope).

## Task List

- [ ] **P2.1** Run `database/migrate.py --seed` on a fresh database and verify all 7 tables exist, PostGIS is enabled, and 3 demo fields are inserted with valid `GEOMETRY(POLYGON, 4326)`. (TODO.md Tests #3, #4)
- [ ] **P2.2** Add a `last_refreshed_at` column or a `reading_metadata` table to track when each `(field_id, source)` was last refreshed. (TODO.md Missing Features #6)
- [ ] **P2.3** Modify `_sync_readings()` to skip external fetches if cached data for a source is newer than a configurable TTL (default 6 hours). (TODO.md Missing Features #7)
- [ ] **P2.4** Update `backend/app/services/weather.py` and `satellite.py` to expose a `fetch_if_stale` helper used by `_sync_readings()`.
- [ ] **P2.5** Add columns to `alerts` for delivery tracking: `status VARCHAR(20)`, `provider_message_id TEXT`, `provider_error TEXT`. Update migration `001_initial_schema.sql` or add `006_alerts_delivery_status.sql`. (TODO.md Missing Features #3)
- [ ] **P2.6** Update `send_whatsapp_alert_and_voice()` to return a stable result dict and update `get_alerts()` to persist that result in the new `alerts` columns. (TODO.md Missing Features #3)
- [ ] **P2.7** Add an integration test that runs: create field → fetch weather/NDVI → compute risk → generate alert → assert alert row exists with status `simulated` or `sent`. (TODO.md Tests #3)
- [ ] **P2.8** Add tests that verify synthetic NDVI is **only** seeded for `is_demo_field = true` fields and that non-demo fields do not get demo data when Sentinel Hub fails. (TODO.md Tests #4, #5)
- [ ] **P2.9** Document the data-pipeline TTL and fallback behaviour in `README.md` and `planning.md`. (TODO.md Docs #1)
- [ ] **P2.10** Update `status.md`, `TODO.md`, `TECHNICAL_DEBT.md`.

## Definition of Done

1. `database/migrate.py --seed` on a fresh DB produces a schema that passes `test_database.py`.
2. `GET /api/fields/{demo_id}/readings` returns data without calling external APIs twice within the TTL window (verify with mocked service call counts).
3. `GET /api/fields/{id}/alerts` inserts an `alerts` row with `status = 'simulated'` when Twilio credentials are absent, and `status = 'sent'` with a Twilio SID when credentials are present (use a mocked Twilio client for tests).
4. The two synthetic-data tests (P2.8) pass.
5. The app still starts locally and the map shows at least one demo field polygon.
6. No P0/P1 technical-debt items in this phase's scope remain open.

## Deliverables

- Schema update (migration `006` or amended `001`).
- Updated `backend/app/routers/fields.py` with TTL caching.
- Updated `backend/app/services/whatsapp_service.py` and `routers/fields.py:get_alerts`.
- New integration tests in `backend/tests/`.
- Updated docs.

## Risks / Notes

- Sentinel Hub requires a real OAuth client; without credentials the demo depends on the synthetic trigger. Make sure the UI still labels demo data clearly.
- TTL caching must not break the integration tests; use a short TTL or inject the clock in tests.
