# Ubuntu Terra — status.md

**Read this file first in any new session, before touching code.** Keep it accurate and aligned with the current implementation.

---

## Current Phase

**Phase 1 (Stabilize & Run) and Phase 2 (Core Data Layer) are complete.**
Phase 3 (Core API Hardening) is next.

## Current Objective

Tighten and test the FastAPI endpoints: fix the shadowed route, strengthen input validation, add upload size limits, and ensure the full backend test suite stays green.

---

## What is working (verified)

Verified by running the code in this environment, not by inspection.

### End-to-end demo flow — passes

| Step | Result |
| --- | --- |
| Register an owner token | 201, 43-char token |
| Duplicate registration | 409 (no second token issued) |
| Request with no token | 401 |
| Create a field | 201, `owner_id` taken from the token, payload `owner_id` ignored |
| List fields | Own fields + 3 shared demo fields |
| Read a seeded demo field | 200 (readings 15 points, risk `Medium`, demo data labelled) |
| Cross-owner read of another owner's field | 403 (readings, risk, alerts, photos, feedback) |
| WhatsApp alert | Alert row + MP3 voice note generated; `simulated` send without Twilio creds |
| WhatsApp alert delivery status persisted | `alerts.status` = `simulated`, `provider_message_id` stored |
| External API TTL caching | Second `/readings` call within 6 hours does not re-hit weather/NDVI APIs |
| Demo NDVI fallback scoping | Synthetic NDVI only seeded for `is_demo_field = true` fields |
| WhatsApp "yes" reply with a real Twilio signature | 200 + TwiML confirmation, on both webhook paths |
| Unsigned / garbage / wrong-token / wrong-URL signature | 403, message not processed |
| CORS preflight from `http://localhost:5173` | 200, `X-Owner-Token` in `allow-headers` |
| CORS preflight from any other origin | Rejected |
| Frontend production build | Succeeds |

### Test suite

- **66 tests collected — 66 passing, 0 failing** (verified inside Docker with a seeded PostGIS database).
- The 10 previously stale `test_risk_engine.py` tests were updated to the `forecast_rainfall_mm` signature in Phase 1.
- Phase 2 added `test_data_pipeline.py` covering TTL caching, alert delivery persistence, and demo-NDVI scoping.
- No previously-passing test regressed during Phase 2.

### Live data sources (confirmed reachable / keyless)

| Source | Used for | Key required |
| --- | --- | --- |
| Open-Meteo | Weather + 7-day forecast | No |
| NASA POWER | Weather fallback | No |
| Esri World Imagery | Satellite basemap tiles | No |
| OpenStreetMap Nominatim | Place search | No |
| Copernicus Data Space (Sentinel Hub) | NDVI time series | **Yes** — falls back to labelled demo NDVI for demo fields |

---

## Features added

### Phase 1 — Onboarding
- `POST /api/fields` with server-side PostGIS validation (self-intersection, 0.01–50,000 ha area bounds, South Africa bounding box).
- MapLibre click-to-draw polygon tool with live preview.
- Nominatim place search (country-restricted to ZA).
- Immediate reading sync + risk computation on field creation.
- Owner-based "My Fields" vs "All Fields" filtering.

### Phase 2 — Vision diagnosis
- Migration `002_photo_diagnoses.sql`.
- `pest_vision.py` classification (fungal spot, pest damage, chlorosis, healthy foliage).
- `POST /api/fields/{id}/photos` runs classification and stores a suggestion record.
- Surfaced in `ConditionPanel.jsx` as a section **separate** from the water-stress score.

### Phase 3 — Transparency
- Migration `003_farmer_feedback.sql`.
- `POST /api/feedback` accuracy feedback.
- `GET /validation-stats` agreement rate, gated at 20 responses ("not enough data yet" below that).
- Advisory disclaimer banner + modal, TTS read-aloud on first view.

### Phase 4 — WhatsApp voice-first
- Twilio sandbox integration with graceful `simulated` fallback (`whatsapp_service.py`).
- gTTS spoken MP3 voice notes in **English and Afrikaans** (`whatsapp_voice.py`); Zulu and Sepedi text alerts are supported with English voice fallback because gTTS 2.5.4 does not include those voices.
- Alert pipeline sending both text and voice note.
- Inbound webhook handling `YES`/`JA`/`YEBO`/`EE` confirmations and `MORE INFO`/`LUSISI`/`NCEDISA`/`TSHEDISA` explanations.
- Frontend voice-note player and quick-reply tags.

### Backend enhancements (Part B)
- Open-Meteo 7-day forecast integrated into the risk engine, replacing heuristics.
- Synthetic demo NDVI restricted to flagged demo fields, used only as a fallback, labelled in the UI.

### Phase 2 implementation — Core Data Layer
- Migration `006_alerts_delivery_status_and_reading_ttl.sql` adds `reading_source_status` (TTL cache metadata) and delivery-status columns to `alerts`.
- TTL caching for Open-Meteo, NASA POWER, Sentinel Hub, and the 7-day rainfall forecast (default 6 hours, configurable via `READING_CACHE_TTL_SECONDS`).
- `get_alerts()` persists WhatsApp delivery result (`status`, `provider_message_id`, `provider_error`).
- Integration tests verify the full pipeline, TTL cache behavior, and that synthetic demo NDVI is scoped to demo fields only.

### Security hardening pass
- CORS restricted to an explicit `ALLOWED_ORIGINS` allow-list (no wildcard), with whitespace-stripping so a malformed value cannot silently break the browser.
- Twilio webhook signature verification inside `fields.whatsapp_webhook`, so both `/whatsapp/webhook` and `/api/whatsapp/webhook` share one check. Fails closed with 500 if the token is unset.
- Per-owner opaque token: `POST /api/owners/register`, `require_owner_token` dependency, ownership enforcement on every owner-scoped endpoint, 403 on cross-owner field access, demo fields readable by any valid token.

---

## What is missing

Ordered by what blocks someone else from running or judging the project.

### 1. Blocking for a live WhatsApp demo — `TWILIO_AUTH_TOKEN` is empty
The real `.env` has `TWILIO_AUTH_TOKEN=` and `TWILIO_ACCOUNT_SID=` blank.
Consequences: inbound webhooks fail closed with **500** (no message processed),
and outbound alerts are recorded as `simulated` rather than sent. Only the
project owner can paste the sandbox Auth Token. The sandbox webhook URL must
also byte-match the public HTTPS URL.

### 2. Blocking for reproducibility — CI/CD
`docker-compose.yml` and Dockerfiles exist and the full stack runs with
`docker compose up --build`. A GitHub Actions workflow is still needed to run
`pytest` and `npm run build` automatically on every push/PR.

### 3. Completed in Phase 1 — single migration runner
`database/migrate.py` now applies 001→006 in order and supports `--seed` / `--reset`.
Ad-hoc `apply_migration*.py` scripts deleted.

### 4. Completed in Phase 1 — Docker / local deployment config
`docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, and `.dockerignore`
are present. The stack starts with one command.

### 5. Completed in Phase 1 — build/release scripts
`scripts/dev.ps1` provides a one-command Windows dev launcher. A cross-platform
`Makefile` is still pending.

### 6. Completed in Phase 2 — `.gitignore` excludes uploads
`backend/uploads/` and `.postgres/` are now ignored.

### 7. Completed in Phase 1 — dependency pins / Python version range
`backend/pyproject.toml` now declares `requires-python = ">=3.10,<3.14"`.
Python 3.14 is explicitly out of scope.

### 8. Out of scope for now — aggregate endpoint unauthenticated
`GET /api/validation-stats` and `/validation-stats` require no token because
they return aggregate counts rather than one owner's data. Defensible, but it
should be a conscious decision rather than an omission.

### 9. Minor pre-existing — unreachable route
`GET /api/fields/validation-stats` is shadowed by `GET /api/fields/{field_id}`
because of declaration order. The top-level `/validation-stats` and
`/api/validation-stats` aliases work correctly, so nothing depends on the
shadowed path.

---

## How to run the project

Full instructions are in **`README.md`**. Short version:

**Prerequisites:** Python 3.11–3.13, Node.js 20+, PostgreSQL 15+ with PostGIS.

```bash
# 1. Environment
cp .env.example .env          # then set DATABASE_URL

# 2. Database + PostGIS
createdb ubuntu_terra
psql -d ubuntu_terra -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# 3. Migrations + demo seed (one command)
cd database && python migrate.py --seed && cd ..

# 4. Backend  -> http://localhost:8000  (docs at /docs)
cd backend
python -m venv ../venv
../venv/Scripts/pip install -r requirements.txt
../venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

# 5. Frontend -> http://localhost:5173   (second terminal)
cd frontend && npm install && npm run dev
```

**Build for production:** `cd frontend && npm run build` → `frontend/dist`.

---

## Recommendations

**Before any demo or judging session**

1. **Add the real `TWILIO_AUTH_TOKEN`** to `.env` and re-verify the webhook
   end-to-end. The WhatsApp leg is the most impressive feature and it is
   currently dead without a token.
2. **Add a provisional badge** in the UI when validation stats are below 20
   responses so the demo does not look like the tool has no validation.

**To make it reproducible for anyone else**

4. **Add a minimal GitHub Actions workflow**: run `pytest` and `npm run build`
   on every push/PR. This is the highest-leverage follow-up after Phase 2.
5. **Add a cross-platform dev launcher** (`Makefile` or npm script) so
   macOS/Linux users have the same one-command experience as `scripts/dev.ps1`.

**Security, if this ever handles real farm data**

6. Replace the owner token with real authentication: password login, token
   expiry and rotation, httpOnly cookies instead of `localStorage`, and rate
   limiting on `POST /api/owners/register` (owner_id enumeration is currently
   trivial).
7. Add an admin review queue for `pending_review` photos instead of local disk.
8. Serve map tiles / data sources through a cache or CDN if usage grows.

**Product**

9. **Field auto-detection from satellite imagery** instead of hand-drawing
   boundaries — the single biggest fidelity gap versus a real product
   (OneSoil does this at scale).
10. Persist the owner token with an expiry so a shared demo machine does not
    leak the previous demo farmer's access.
11. The validation-stats threshold (20 responses) is never reachable in a
    demo; consider a clearly-labelled provisional mode for judging.

---

## Decisions

See planning.md for the full decisions table and product positioning notes.
Recent additions:

| Date | Decision |
| --- | --- |
| 2026-09-26 | CORS restricted to an explicit `ALLOWED_ORIGINS` allow-list; deployed frontend URL added by env var, not code |
| 2026-09-26 | Twilio webhook signatures verified inside `fields.whatsapp_webhook` so both aliases share one check; fails closed with 500 if the token is unset |
| 2026-09-26 | Owner identity is a per-owner opaque token (`X-Owner-Token`), deliberately short of real auth; demo fields stay readable by any valid token |
| 2026-09-27 | External weather/NDVI readings cached per source in `reading_source_status` with a 6-hour TTL (`READING_CACHE_TTL_SECONDS`) instead of re-fetching on every request |
| 2026-09-27 | WhatsApp alert delivery result persisted in `alerts` (`status`, `provider_message_id`, `provider_error`) for audit and simulated/live path debugging |

---

## Last Updated

2026-09-27 — Phase 2 Core Data Layer complete. 66 tests passing (0 failures).
Added `reading_source_status` TTL cache, migration 006, alert delivery audit
columns, and integration tests. Updated docs (`README.md`, `planning.md`,
`status.md`, `TODO.md`, `TECHNICAL_DEBT.md`). Remaining blockers: live Twilio
token for real WhatsApp send, CI/CD workflow, and Phase 3 API hardening.
