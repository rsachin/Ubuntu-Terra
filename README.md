# Ubuntu Terra

**Geo-spatial water & crop stress monitoring for South African farmers.**

Farmers in water-stressed regions like the Gamtoos and Sundays River valleys
don't lack data — they lack *time*. Irrigation quotas, dam levels and crop
stress are communicated through WhatsApp groups and advice from extension
officers, days after the damage is done. Ubuntu Terra turns satellite and
weather data into a plain-language warning a farmer can act on the same day,
in English or Afrikaans, with a voice note for people who would rather listen
than read.

---

## Table of contents

- [Problem statement](#problem-statement)
- [The solution](#the-solution)
- [Features](#features)
- [Tech stack](#tech-stack)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [How to use the application](#how-to-use-the-application)
- [WhatsApp (Twilio) setup](#whatsapp-twilio-setup)
- [Running the tests](#running-the-tests)
- [Project structure](#project-structure)
- [Known limitations](#known-limitations)

---

## Problem statement

Smallholder and commercial farmers in South Africa's Eastern Cape face
recurring, quantified water stress:

- The **Kouga Dam** supply (Patensie, Hankey) has repeatedly imposed
  irrigation quotas as low as **40% of full allocation** in drought years.
- Crop stress from water deficit and heat is visible in satellite data
  **days before** it is obvious in the field.
- Existing tools are either enterprise agronomy platforms (too costly, too
  complex) or raw data feeds (UFC codes, NDVI rasters) that a farmer cannot
  act on directly.
- Alerting is fragmented: WhatsApp groups, radio, and extension officers.
  There is no confirmation loop, so nobody knows whether a farmer saw a warning.

## The solution

Ubuntu Terra is a field-scoped monitoring app that:

1. Lets a farmer **draw their field boundary** on a satellite map (or search
   for their town).
2. **Pulls real data** for that exact polygon — Sentinel Hub NDVI vegetation
   index plus Open-Meteo / NASA POWER weather.
3. Runs an **explainable rule-based risk engine** over the trend and returns
   `Low` / `Medium` / `High` with *reasons* and a *recommended check*, in
   plain language rather than a score with no explanation.
4. **Delivers the warning over WhatsApp** as text *and* a spoken voice note
   (English / Afrikaans), and handles replies back (`YES` to confirm, `MORE
   INFO` for an explanation).
5. **Closes the loop** with photo diagnosis, farmer accuracy feedback, and an
   agreement rate that is only reported once 20 responses exist.

Every risk verdict is explainable: the app tells you *which* signal triggered
it, so a farmer can trust it and an agronomist can audit it.

## Features

| Area | Capability |
| --- | --- |
| **Onboarding** | Click-to-draw field polygons with live preview; SA-wide place search (Nominatim); server-side PostGIS validation (self-intersection, min/max area, SA bounding box) |
| **Data** | Sentinel Hub NDVI time series; Open-Meteo + NASA POWER weather; 7-day forward rainfall forecast; per-source caching with graceful degradation when services fail |
| **Risk** | Explainable rule engine (NDVI trend + rainfall deficit + temperature anomaly) with recommended checks; demo NDVI fallback restricted to flagged demo fields and labelled `[Demo data]` in the UI |
| **Field view** | Satellite basemap (Esri World Imagery), field list, condition panel, trend charts, voice read-aloud of the risk summary |
| **WhatsApp** | Text + gTTS MP3 voice note (English/Afrikaans); inbound webhook with YES/JA/YEBO confirmation and MORE INFO explanation; Twilio signature verification |
| **Vision** | Ground-truth photo upload with plant-health classification (fungal spot, pest damage, chlorosis, healthy foliage), surfaced separately from the water-stress score |
| **Transparency** | Advisory disclaimer banner + modal, TTS read-aloud on first view, thumbs up/down accuracy feedback, agreement-rate stats gated at 20 responses |
| **Resilience** | Cached-reading fallback when live services are down; partial-data and loading states in the UI |
| **Security** | CORS allow-list; verified Twilio webhook signatures; per-owner opaque access token with ownership enforcement on every owner-scoped endpoint |

## Tech stack

| Layer | Choice |
| --- | --- |
| Frontend | React 19, Vite 8, MapLibre GL 6 |
| Backend | FastAPI 0.115, Uvicorn |
| Database | PostgreSQL + PostGIS |
| Data libs | `psycopg2` (no ORM, deliberately), `httpx` |
| Satellite | Copernicus Data Space Ecosystem (Sentinel Hub) |
| Weather | Open-Meteo, NASA POWER (both keyless) |
| Voice | gTTS |
| WhatsApp | Twilio SDK |

External services used at runtime: Esri World Imagery tiles, OpenStreetMap
Nominatim (place search), Open-Meteo, NASA POWER, Copernicus Data Space.

---

## Quick start

### Prerequisites

| Requirement | Notes |
| --- | --- |
| Python 3.11–3.13 | **Avoid 3.14 for now** — see [Known limitations](#known-limitations) |
| Node.js 20+ | For the Vite frontend |
| PostgreSQL 15+ **with PostGIS** | `CREATE EXTENSION postgis` is required by migration 001 |
| A database named `ubuntu_terra` | Or set `DATABASE_URL` to your own |

### 1. Get the code and environment file

```bash
git clone <your-repo-url> ubuntu-terra
cd ubuntu-terra
cp .env.example .env
```

Edit `.env` and fill in at least `DATABASE_URL`. Everything else has a working
default or is optional for local development (see [Configuration](#configuration)).

### 2. Create the database

```bash
createdb ubuntu_terra
psql -d ubuntu_terra -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

### 3. Apply migrations (run in order)

**Option A — the migration runner (recommended):**

```bash
cd database
python migrate.py          # applies 001→006
python migrate.py --seed   # applies migrations + seeds 3 demo fields
cd ..
```

**Option B — the documented `psql` loop:**

```bash
for f in database/migrations/0*.sql; do
  echo "Applying $f"
  psql "$DATABASE_URL" -f "$f"
done
```

This creates `fields`, `readings`, `risk_scores`, `alerts`, `photo_diagnoses`,
`farmer_feedback`, `owner_tokens`, and `reading_source_status` (for TTL cache
metadata). Migrations now run through `006`.
All migrations are idempotent (`IF NOT EXISTS`), so re-running is safe.

### 4. Seed the demo fields (optional but recommended)

If you used `migrate.py --seed` above, this step is already done.

```bash
cd database
python seed_demo_fields.py
cd ..
```

This inserts the three demo fields (Patensie, Hankey, Kirkwood) with
`is_demo_field = true`. They are readable by every owner and are what the demo
walkthrough uses. The boundaries are small representative rectangles centred on
real farming towns — **not** surveyed cadastral boundaries of any real farm.

### 5. Start the backend

```bash
cd backend
python -m venv ../venv            # first time only
../venv/Scripts/pip install -r requirements.txt   # Windows
# source ../venv/bin/activate && pip install -r backend/requirements.txt   # macOS/Linux

../venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

The API is now on **http://localhost:8000** — interactive docs at
**http://localhost:8000/docs**, health check at `/api/health`.

### 6. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The app is now on **http://localhost:5173**.

> The frontend calls the backend directly at `http://localhost:8000` by
> default, so that origin must be in `ALLOWED_ORIGINS` (it is by default).
> To point at a deployed backend instead, set `VITE_API_BASE_URL` in
> `frontend/.env`.

### Build for production

```bash
cd frontend
npm run build      # -> frontend/dist
npm run preview    # serve the production build locally
npm run lint       # oxlint
```

A ready-to-use `docker-compose.yml` is provided — see [Quick start](#quick-start).

---

## Configuration

All variables live in `.env` at the repo root. Only `DATABASE_URL` is
mandatory for local development.

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | **Yes** | PostgreSQL connection string, must point at a PostGIS-enabled DB |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS allow-list. Default `http://localhost:5173`. Add your deployed frontend URL here — no code change needed |
| `SENTINEL_HUB_CLIENT_ID` | For live NDVI | Copernicus Data Space OAuth client id. Without it, NDVI falls back (see below) |
| `SENTINEL_HUB_CLIENT_SECRET` | For live NDVI | Copernicus Data Space OAuth client secret |
| `TWILIO_AUTH_TOKEN` | For WhatsApp | **Must match the Twilio console exactly.** Inbound webhooks return 403 with a wrong token and fail closed with a 500 when unset |
| `TWILIO_ACCOUNT_SID` | For live WhatsApp send | With it, alerts send for real; without it, delivery is recorded as `simulated` |
| `TWILIO_WHATSAPP_NUMBER` | No | Your Twilio sandbox sender. Default `whatsapp:+14155238886` |
| `RECIPIENT_WHATSAPP_NUMBER` | No | Destination for outbound alerts |

### Graceful degradation

The app is designed to stay demo-able when the network or credentials fail:

| Missing | Behaviour |
| --- | --- |
| Sentinel Hub credentials / NDVI fetch fails | For **demo fields only**, a synthetic declining NDVI series is seeded as a fallback and labelled `[Demo data]` in the UI. Non-demo fields just show less data |
| Both weather services fail | Cached readings from the last successful pull are served instead of an error screen |
| Twilio credentials | Outbound alerts are recorded as `simulated`; the alert still appears in the UI and in the `alerts` table |

---

## How to use the application

### 1. Add your field

On the map, click each corner of your field to draw the boundary, then close
the polygon. A live preview follows your cursor. You can also search for your
town in the search box to jump to that area. Give the field a name and save.

The server validates before accepting: the polygon must be valid (no
self-intersections), within South Africa's bounding box, and between 0.01 and
50,000 hectares. Readings and a first risk score are computed immediately.

### 2. Read the risk

Selecting a field opens the condition panel showing:

- **Risk level** — `Low`, `Medium`, or `High`
- **Reasons** — the specific signals that triggered it
- **Recommended check** — the concrete field action to take
- **Trend chart** — NDVI, rainfall, and temperature over the last 14 days
- **Possible issue detected from photo** — if a photo has been uploaded

Tap the speaker icon to hear the summary read aloud.

Use the **My Fields / All Fields** toggle to switch between your own fields
and the shared demo fields.

### 3. Upload a ground-truth photo

Use the photo panel to capture or upload a picture of the crop. It is analysed
for plant-health issues (fungal spot, pest damage, chlorosis, healthy foliage)
and reported as a **separate** section from the water-stress score, because a
disease and a water deficit need different actions.

### 4. Send and confirm a WhatsApp alert

Opening the alert preview composes the WhatsApp message and generates a spoken
voice note. With Twilio configured, the alert is delivered to your registered
number as text plus an MP3.

Replying **YES** (or JA / YEBO) confirms you saw it. Replying **MORE INFO**
returns a plain-language explanation of the risk and what to inspect. Replies
arrive at the webhook, which verifies the Twilio signature before processing.

### 5. Rate the accuracy

Thumbs up / thumbs down on whether the risk call was accurate feeds the
agreement-rate statistic. The rate is only published once **20** responses
exist — below that it honestly reports "not enough data yet" rather than
publishing a meaningless percentage.

---

## WhatsApp (Twilio) setup

1. In the [Twilio Console](https://console.twilio.com), open the **Messaging →
   Try it Out** sandbox and note the **Auth Token**.
2. Put it in `.env` as `TWILIO_AUTH_TOKEN`, plus `TWILIO_ACCOUNT_SID` and
   `TWILIO_WHATSAPP_NUMBER`.
3. Set the sandbox's **"When a message comes in"** webhook to your public HTTPS
   URL + `/api/whatsapp/webhook` (for local testing use a tunnel, e.g.
   `ngrok http 8000`).
4. Join the sandbox from your own phone using the code Twilio gives you.

**The URL must match exactly** what you register — scheme, host, and trailing
slash. Twilio signs the URL it called, so a mismatch (e.g. registering
`http://` while serving `https://`, or a stale ngrok URL) makes every genuine
webhook return `403 Invalid Twilio signature` even with a correct token. The
app honours `X-Forwarded-Proto` for TLS-terminating proxies, but a proxy that
also rewrites the **host** header will still break validation.

Verify it locally without Twilio by generating a real signature:

```python
from twilio.request_validator import RequestValidator
sig = RequestValidator(token).compute_signature(url, {"Body": "YES"})
# POST to url with header  x-twilio-signature: <sig>
```

---

## Running the tests

```bash
cd backend
../venv/Scripts/python -m pytest tests -q
```

The suite runs against a **real local PostGIS database** (the same one the app
uses) so it verifies real SQL and PostGIS geometry handling. The external
weather and satellite calls are monkeypatched, so tests need no network and no
API credentials. Seed the demo fields first — several tests assert on them.

Current state: **66 passing, 0 failing** (includes Phase 2 integration tests for
TTL caching, alert delivery persistence, and demo-NDVI scoping).

---

## Project structure

```
backend/
  app/
    main.py              FastAPI entrypoint, CORS, static mounts, route aliases
    db.py                psycopg2 connection helper (no ORM)
    routers/fields.py    All field/owner/feedback endpoints + WhatsApp webhook
    services/
      risk_engine.py     Explainable rule-based risk scoring
      satellite.py       Copernicus Data Space NDVI
      weather.py         Open-Meteo + NASA POWER
      pest_vision.py     Plant-health classification
      whatsapp_service.py  Twilio delivery
      whatsapp_voice.py    gTTS voice notes (en/af)
  tests/                 pytest suite
  uploads/               Local photo + audio storage (gitignored)
database/
  migrations/            001..006, applied in order, idempotent
  seed_demo_fields.py    Seeds the 3 demo fields
frontend/
  src/api/client.js      API client + owner-token store
  src/components/        Map, condition panel, charts, photo upload, alerts
docs: planning.md        Scope, architecture, decisions
      status.md          What works, what is missing, recommendations
```

## Known limitations

- **Python 3.14 is not supported by the pinned dependencies.**
  `pydantic==2.9.2` and `psycopg2-binary==2.9.9` have no 3.14 wheels and
  require a Rust/PostgreSQL toolchain to build from source. Use Python 3.11–3.13.
- **Owner access is a per-owner opaque token, not real authentication.** No
  passwords, sessions, expiry, or rotation; the token is stored in
  `localStorage`; `POST /api/owners/register` has no rate limiting, so
  `owner_id` enumeration is still possible. See `status.md`.
- **Field boundaries are hand-drawn** and, for the demo fields, representative
  rectangles rather than surveyed boundaries. Real deployment would use
  satellite auto-detection.
- **Photo storage is local disk** with a `pending_review` status and no admin
  review queue.
- **No CI/CD yet.** `docker-compose.yml` works locally; a GitHub Actions
  workflow is still pending (Phase 6).
- **No upload size limits.** `POST /api/fields/{id}/photos` accepts any image
  size; production needs a cap plus resize/virus scanning.
- **`GET /api/fields/validation-stats` is shadowed** by `GET /api/fields/{field_id}`
  because of route declaration order. The top-level `/validation-stats` and
  `/api/validation-stats` aliases work correctly.
