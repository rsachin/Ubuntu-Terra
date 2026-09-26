# Ubuntu Terra — status.md

**Read this file first in any new session, before touching code.** Keep it accurate and aligned with the current implementation.

---

## Current Phase

Feature work (Phases 1–4) and the security hardening pass are **complete**. The project is functionally demo-ready when run from source with seeded demo fields. What remains is **reproducibility and deployment polish** — see [What is missing](#what-is-missing).

## Current Objective

Make the project reproducible for someone who has never seen it: one documented install path, a green test suite, and an optional containerised/CI build.

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
| WhatsApp "yes" reply with a real Twilio signature | 200 + TwiML confirmation, on both webhook paths |
| Unsigned / garbage / wrong-token / wrong-URL signature | 403, message not processed |
| CORS preflight from `http://localhost:5173` | 200, `X-Owner-Token` in `allow-headers` |
| CORS preflight from any other origin | Rejected |
| Frontend production build | Succeeds |

### Test suite

- **62 tests collected — 52 passing, 10 failing.**
- All 10 failures are in `backend/tests/test_risk_engine.py` and are **stale
  tests, not broken code**: they call
  `assess_field_risk(rainfall_readings_mm=...)` from before the Part B refactor
  to forward-looking `forecast_rainfall_mm`. The engine implements the newer,
  intended design. The fix is to update the tests, **not** to revert
  `risk_engine.py`.
- No previously-passing test regressed during the security pass.

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
- gTTS spoken MP3 voice notes in **English and Afrikaans** (`whatsapp_voice.py`).
- Alert pipeline sending both text and voice note.
- Inbound webhook handling `YES`/`JA`/`YEBO` confirmations and `MORE INFO` explanations.
- Frontend voice-note player and quick-reply tags.

### Backend enhancements (Part B)
- Open-Meteo 7-day forecast integrated into the risk engine, replacing heuristics.
- Synthetic demo NDVI restricted to flagged demo fields, used only as a fallback, labelled in the UI.

### Security hardening pass
- CORS restricted to an explicit `ALLOWED_ORIGINS` allow-list (no wildcard), with whitespace-stripping so a malformed value cannot silently break the browser.
- Twilio webhook signature verification inside `fields.whatsapp_webhook`, so both `/whatsapp/webhook` and `/api/whatsapp/webhook` share one check. Fails closed with 500 if the token is unset.
- Per-owner opaque token: `POST /api/owners/register`, `require_owner_token` dependency, ownership enforcement on every owner-scoped endpoint, 403 on cross-owner field access, demo fields readable by any valid token.

---

## What is missing

Ordered by what blocks someone else from running or judging the project.

### 1. Blocking — red test suite (10 failures)
`test_risk_engine.py` targets a pre-Part-B signature. The suite should be green
before any demo. Fix: update the 10 tests to pass `forecast_rainfall_mm`.

### 2. Blocking for a live WhatsApp demo — `TWILIO_AUTH_TOKEN` is empty
The real `.env` has `TWILIO_AUTH_TOKEN=` and `TWILIO_ACCOUNT_SID=` blank.
Consequences: inbound webhooks fail closed with **500** (no message processed),
and outbound alerts are recorded as `simulated` rather than sent. Only the
project owner can paste the sandbox Auth Token. The sandbox webhook URL must
also byte-match the public HTTPS URL.

### 3. Blocking for reproducibility — no single migration runner
`database/apply_migration.py` hardcodes `004_is_demo_field.sql`,
`apply_migration_005.py` hardcodes `005`, and **001–003 have no runner at all**.
A fresh clone has no reliable way to build the schema. The README documents a
`for` loop over `database/migrations/0*.sql` as the workaround, but a single
ordered runner should exist.

> **Fixed in this pass:** `004_is_demo_field.sql` was the one non-idempotent
> migration (a bare `ADD COLUMN`, no `IF NOT EXISTS`), so re-running the loop
> against an already-migrated database aborted with
> `column "is_demo_field" of relation "fields" already exists`. It now uses
> `ADD COLUMN IF NOT EXISTS`; all five migrations re-run cleanly (verified).

### 4. Missing — Docker / CI-CD / deployment config
There is **no** `Dockerfile`, `docker-compose.yml`, `render.yaml`, `Procfile`,
or any CI workflow. Consequences:
- The app can only be run from source; no reproducible runtime image.
- `frontend/src/api/client.js` and the CORS allow-list both assume a deployed
  frontend URL that has no infrastructure behind it.
- No automated test run on commit or PR.

### 5. Missing — build/release scripts
`frontend/package.json` has `dev`, `build`, `preview`, and `lint`, which is
adequate for the frontend. There is **no** backend entrypoint script, no
combined "run everything" script, and no seed-and-migrate command. A
`Makefile` or a small `scripts/dev.ps1` would remove the multi-terminal,
multi-command setup from the README.

### 6. Housekeeping — `.gitignore` does not exclude uploads
`backend/uploads/` is untracked-but-not-ignored and currently holds **65 files**
(farmer photos and generated MP3s). It needs an ignore rule, otherwise demo
artefacts get committed.

### 7. Housekeeping — dependency pins fail on Python 3.14
`pydantic==2.9.2` and `psycopg2-binary==2.9.9` have no Python 3.14 wheels and
need a Rust / PostgreSQL toolchain to build from source (this was hit while
verifying the security pass). The project targets Python 3.11–3.13. The pins
should be bumped to versions with modern wheels, or the supported version range
declared explicitly.

### 8. Known-but-unfixed — `owner_tokens` migration is not committed
`database/migrations/005_owner_tokens.sql` and its runner are still untracked,
along with all of Phase 2–4. **Nothing from this project has been committed** —
the working tree holds 20+ untracked files.

### 9. Out of scope for now — aggregate endpoint unauthenticated
`GET /api/validation-stats` and `/validation-stats` require no token because
they return aggregate counts rather than one owner's data. Defensible, but it
should be a conscious decision rather than an omission.

### 10. Minor pre-existing — unreachable route
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

# 3. Migrations, in order (all idempotent)
for f in database/migrations/0*.sql; do psql "$DATABASE_URL" -f "$f"; done

# 4. Seed the 3 demo fields
cd database && python seed_demo_fields.py && cd ..

# 5. Backend  -> http://localhost:8000  (docs at /docs)
cd backend
python -m venv ../venv
../venv/Scripts/pip install -r requirements.txt
../venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

# 6. Frontend -> http://localhost:5173   (second terminal)
cd frontend && npm install && npm run dev
```

**Build for production:** `cd frontend && npm run build` → `frontend/dist`.

---

## Recommendations

**Before any demo or judging session**

1. **Fix the 10 failing tests.** A red suite is the first thing a judge sees
   and it undermines claims that the risk engine is verified. ~15 minutes.
2. **Add the real `TWILIO_AUTH_TOKEN`** to `.env` and re-verify the webhook
   end-to-end. The WhatsApp leg is the most impressive feature and it is
   currently dead without a token.
3. **Commit everything.** 20+ untracked files including all of Phase 2–4, the
   owner-token migration, and the new tests. Uncommitted work is invisible work.
4. **Add `backend/uploads/` to `.gitignore`** before committing.

**To make it reproducible for anyone else**

5. **Write one ordered migration runner** (`database/migrate.py`) that applies
   001→005 and optionally seeds. Delete the two ad-hoc scripts.
6. **Write the `README.md`** — done in this pass.
7. **Add a `Dockerfile`** (backend) and a `docker-compose.yml` wiring
   `postgres+postgis` → backend → frontend. This is the single highest-leverage
   item for "a judge can run it".
8. **Add a minimal GitHub Actions workflow**: `pytest` on push, `npm run build`
   on push. Catches the red-suite class of problem automatically.

**Security, if this ever handles real farm data**

9. Replace the owner token with real authentication: password login, token
   expiry and rotation, httpOnly cookies instead of `localStorage`, and rate
   limiting on `POST /api/owners/register` (owner_id enumeration is currently
   trivial).
10. Add an admin review queue for `pending_review` photos instead of local disk.
11. Serve map tiles / data sources through a cache or CDN if usage grows; the
    NDVI and weather calls are currently made per request.

**Product**

12. **Field auto-detection from satellite imagery** instead of hand-drawing
    boundaries — the single biggest fidelity gap versus a real product
    (OneSoil does this at scale).
13. Persist the owner token with an expiry so a shared demo machine does not
    leak the previous demo farmer's access.
14. The validation-stats threshold (20 responses) is never reachable in a
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

---

## Last Updated

2026-09-26 — Security hardening pass complete. Added verified-working-state
table, feature inventory, prioritised "what is missing" list (test suite,
Twilio token, migration runner, Docker/CI-CD, build scripts), run instructions,
and a prioritised recommendation list. `README.md` created. Also made
`004_is_demo_field.sql` idempotent so the documented migration loop is re-runnable.
