# Phase 2 Completion Report — Core Data Layer

## Status

**Phase 2 completed.** All deliverables are implemented, the backend test suite is green, and the full stack was verified end-to-end via Docker Compose.

## What Was Completed

| Task | Result |
|------|--------|
| Verify PostGIS schema reproducibility | ✅ Done — `database/migrate.py --seed` on a fresh Docker PostGIS DB creates all tables through migration 006 and seeds the 3 demo fields |
| Add TTL cache metadata table | ✅ Done — migration `006_alerts_delivery_status_and_reading_ttl.sql` adds `reading_source_status(field_id, source, last_refreshed_at, cached_value_json)` |
| Skip external fetches when cache is fresh | ✅ Done — `_sync_readings()` in `routers/fields.py` checks `_is_source_fresh()` before calling weather/NDVI services; default TTL is 6 hours |
| Cache 7-day rainfall forecast scalar | ✅ Done — `_compute_and_cache_risk()` stores the forecast sum in `reading_source_status` so risk scores stay deterministic within the TTL |
| Add alert delivery-status columns | ✅ Done — migration 006 adds `status`, `provider_message_id`, `provider_error` to `alerts` |
| Persist WhatsApp delivery result | ✅ Done — `get_alerts()` stores the stable result dict returned by `send_whatsapp_alert_and_voice()`; simulated path records `status='simulated'` |
| Integration test for full data pipeline | ✅ Done — `backend/tests/test_data_pipeline.py` covers create field → fetch readings → compute risk → generate alert |
| Tests for demo-NDVI scoping | ✅ Done — `test_demo_ndvi_only_for_demo_fields` and `test_non_demo_field_no_synthetic_ndvi` pass |
| Stable WhatsApp result contract | ✅ Done — `whatsapp_service.py` returns `{status, sid, voice_sid, error, simulated}` for both live and simulated paths |
| Update documentation | ✅ Done — `README.md`, `planning.md`, `status.md`, `TODO.md`, `TECHNICAL_DEBT.md` updated |

## Verification

### Test suite (inside Docker with seeded PostGIS)

```text
66 passed, 2 warnings in 32.27s
```

Run with:

```bash
docker compose up --build -d
docker compose exec backend python -m pytest tests -q
```

### End-to-end smoke test (Docker)

| Step | Result |
| --- | --- |
| `docker compose up --build` | ✅ Stack starts: postgres, backend, frontend |
| Frontend at http://localhost:5173 | ✅ Serves |
| Backend health at `/api/health` | ✅ 200 |
| `GET /api/fields` with a valid token | ✅ Returns 3 demo fields |
| `GET /api/fields/{demo_id}/readings` twice within TTL | ✅ External APIs called once, second request served from cache |
| `GET /api/fields/{demo_id}/alerts` | ✅ Alert row created with `status = 'simulated'` |

## What Was Already Solid

- `weather.py` (Open-Meteo + NASA POWER fallback) and `satellite.py` (Sentinel Hub) required no service-level changes for TTL caching; the cache layer was added at the router level.
- `seed_demo_fields.py` and `demo_ndvi_fixture.py` already produced reproducible demo data; Phase 2 only narrowed the synthetic NDVI fallback to `is_demo_field = true` fields.

## How to Verify Phase 2 on a Correctly Provisioned Machine

### Path A — Docker (recommended)

```bash
cd <repo-root>
docker compose up --build
# in another shell:
docker compose exec backend python -m pytest tests -q
```

Open http://localhost:5173 and select a demo field to confirm readings load and a risk score appears.

### Path B — Native Windows with PostGIS

1. Ensure PostgreSQL 15+ with PostGIS is running.
2. Copy `.env.example` → `.env` and set `DATABASE_URL`.
3. Run `cd database && python migrate.py --seed`.
4. Start backend and frontend as documented in `README.md`.
5. Run `cd backend && python -m pytest tests -q`.

## Definition of Done Assessment

| DoD Item | Met | Notes |
|----------|-----|-------|
| `migrate.py --seed` works on fresh DB | ✅ Yes | Verified inside Docker; PostGIS 15-3.4 image used |
| `GET /api/fields/{demo_id}/readings` does not call external APIs twice within TTL | ✅ Yes | `test_ttl_cache_skips_second_api_call` asserts mock call count = 1 |
| `GET /api/fields/{id}/alerts` inserts row with `status = 'simulated'` when Twilio absent | ✅ Yes | Verified in integration test |
| Synthetic-data scoping tests pass | ✅ Yes | Both demo-NDVI tests pass |
| App starts and map shows demo fields | ✅ Yes | Docker smoke test confirms |
| No P0/P1 debt left in this phase's scope | ✅ Yes | TTL caching and alert delivery audit were the P1/P2 scoped items |

## New / Updated Files

- `database/migrations/006_alerts_delivery_status_and_reading_ttl.sql`
- `backend/tests/test_data_pipeline.py`
- `backend/app/routers/fields.py` (TTL caching helpers + alert persistence)
- `backend/app/services/whatsapp_service.py` (stable result dict)
- `backend/Dockerfile`
- `database/migrate.py`
- `docker-compose.yml`
- `README.md`, `planning.md`, `status.md`, `docs/TODO.md`, `docs/TECHNICAL_DEBT.md`

## Decision Required

Phase 3 (Core API Hardening) is ready to start. It will focus on:

- Removing/reordering the shadowed `GET /api/fields/validation-stats` route.
- Strengthening input validation on all endpoints.
- Adding upload size limits to `POST /api/fields/{id}/photos`.
- Confirming the full backend test suite stays green.

**Recommendation:** proceed to Phase 3. Phase 2's gates are met and the data layer is now stable and auditable.
