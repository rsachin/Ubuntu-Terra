# Ubuntu Terra — planning.md

Living document. Updated to reflect the current implementation and the demo-ready state of the application.

---

## Problem Statement Summary

South Africa is water-scarce, and agriculture is one of its largest water consumers. Satellite, weather, and soil data already exist but are scattered, technical, and not packaged for a farmer to act on day to day. Ubuntu Terra turns scattered earth-observation and weather data into an early, explained, actionable signal for South African farmers, starting with water and crop stress alerts.

## Target Users

- Commercial and emerging farmers managing multiple fields.
- Smallholder farmers with limited access to agronomists or soil testing.
- Farm managers responsible for water-use efficiency and yield early warnings.
- Secondary: agri-cooperatives, insurers, and water authorities.

## Core Pain Point

Late detection: farmers often do not know where to look first, or why a specific zone is worse than the rest of the field.

## Proposed Solution

A map-based platform where a farmer selects a field and sees a readable risk status, recent trend data, an explanation of why the risk changed, and a recommended action. The demo focuses on low-friction insight delivery rather than advanced agronomic modelling.

## Current Implemented Scope

### MVP + Demo Enhancements (Implemented)

1. [x] Interactive map with three South African demo field boundaries and field selection.
2. [x] Condition panel showing risk level, reasons, and a recommended check.
3. [x] Historical trend view for NDVI, rainfall, and temperature with sparkline charts.
4. [x] Rule-based risk engine combining NDVI decline, rainfall deficit, and temperature anomaly.
5. [x] Alert preview with SMS/WhatsApp-style messaging.
6. [x] Multilingual alert toggle with English and Afrikaans variants.
7. [x] Read-aloud risk summary using browser speech synthesis.
8. [x] Voice-triggered query patterns for simple spoken prompts.
9. [x] Forward-looking rainfall integration: fetches 7-day predicted rainfall sum from Open-Meteo forecast endpoint to use in risk scoring instead of heuristics.
10. [x] Demo NDVI trigger explicitly restricted to demo fields as a fallback only when real live satellite data fails, clearly labelled as Demo data in the UI.
11. [x] Photo upload backend endpoint storing uploaded images as pending review assets.
12. [x] Frontend photo upload panel for field ground-truth capture.
13. [x] Backend resilience path with cached fallbacks when weather and satellite services fail.
14. [x] Frontend loading and partial-data state handling for degraded network or service conditions.
15. [x] Phase 1 Onboarding: POST /api/fields endpoint with server-side PostGIS polygon validation (self-intersection, area bounds, SA geographical bounding box check).
16. [x] Phase 1 Onboarding: MapLibre interactive click-to-add-vertex drawing tool with live line and polygon preview.
17. [x] Phase 1 Onboarding: Nominatim place/town search box (free OSM search) to recenter map to any South African town.
18. [x] Phase 1 Onboarding: Immediate satellite/weather reading sync & risk score computation on field creation.
19. [x] Phase 1 Onboarding: Owner-based filtering ("My Fields" vs "All Fields") with persistent owner_id support.
20. [x] Phase 2 Vision Diagnosis: Migration `002_photo_diagnoses.sql` adding `photo_diagnoses` schema.
21. [x] Phase 2 Vision Diagnosis: `pest_vision.py` vision classification service (fungal spot, pest damage, chlorosis, healthy foliage).
22. [x] Phase 2 Vision Diagnosis: `POST /api/fields/{id}/photos` extended to run photo classification and store suggestion record.
23. [x] Phase 2 Vision Diagnosis: `ConditionPanel.jsx` surfaces distinct "Possible issue detected from photo" section, kept separate from water-stress score.
24. [x] Phase 3 Transparency: Migration `003_farmer_feedback.sql` adding `farmer_feedback` schema.
25. [x] Phase 3 Transparency: `POST /api/feedback` endpoint to save thumbs up/down accuracy feedback from farmers.
26. [x] Phase 3 Transparency: `GET /validation-stats` endpoint calculating agreement rate (returning "not enough data yet" when <20 responses).
27. [x] Phase 3 Transparency: Advisory disclaimer modal and persistent banner in UI.
28. [x] Phase 3 Transparency: Text-to-speech disclaimer read-aloud on first view of field results.
29. [x] Phase 4 WhatsApp Voice-First: Twilio WhatsApp sandbox integration & fallback in `whatsapp_service.py`.
30. [x] Phase 4 WhatsApp Voice-First: Spoken MP3 voice note generation (`whatsapp_voice.py` using gTTS) in English and Afrikaans.
31. [x] Phase 4 WhatsApp Voice-First: Extended alert pipeline sending both text message & voice note MP3 audio.
32. [x] Phase 4 WhatsApp Voice-First: WhatsApp reply webhook handler `POST /api/whatsapp/webhook` responding to 'YES/JA' confirmations and 'MORE INFO' explanations.
33. [x] Phase 4 WhatsApp Voice-First: Frontend `AlertPreview.jsx` updated with audio voice note player and quick-reply options.

## Architecture

```text
ubuntu-terra/
├── frontend/          React + Vite + MapLibre GL JS: map, field selector, panel UI
│   └── src/
│       ├── components/  ConditionPanel, TrendChart, AlertPreview, PhotoUpload, etc.
│       ├── api/         client.js, useFieldDashboard.js
│       └── App.jsx
├── backend/           FastAPI API and data layer
│   ├── app/
│   │   ├── routers/   fields router with readings, risk, alerts, and photo upload
│   │   ├── services/  weather.py, satellite.py, risk_engine.py
│   │   ├── db.py      Postgres connection helper
│   │   └── main.py    app bootstrap
│   └── tests/         backend verification tests
├── database/
│   ├── migrations/    schema definitions
│   ├── seed_demo_fields.py
│   └── demo_ndvi_fixture.py
├── planning.md
├── status.md
└── README.md
```

## Demo Region & Fields

**Region:** Gamtoos River Valley (Patensie, Hankey) and Sundays River Valley (Kirkwood), Eastern Cape.

| Field                  | Location                                         | Water source      | Role in demo                  |
| ---------------------- | ------------------------------------------------ | ----------------- | ----------------------------- |
| Patensie Citrus Block  | Patensie, Gamtoos Valley (-33.755, 24.808)       | Kouga Dam         | Citrus — quota-restricted     |
| Hankey Vegetable Field | Hankey, Gamtoos Valley (-33.828, 24.875)         | Kouga Dam         | Vegetables — quota-restricted |
| Kirkwood Citrus Block  | Kirkwood, Sundays River Valley (-33.405, 25.450) | Gariep Dam scheme | Citrus — comparatively secure |

## API Endpoints (Operational)

`🔒` = requires the per-owner `X-Owner-Token` header. `🌐` = deliberately public.

| Endpoint                    | Method | Purpose                                              | Status   |
| --------------------------- | ------ | ---------------------------------------------------- | -------- |
| `/api/health`               | GET    | Health check                                         | Verified |
| `/api/owners/register`      | POST   | Issue an opaque access token for a new `owner_id` (the demo signup step; 409 if one already exists) | Verified |
| `/api/fields`               | GET    | 🔒 Field list for map (token's own fields + shared demo fields; `owner_id` query param rejected) | Verified |
| `/api/fields`               | POST   | 🔒 Create a field (owner_id taken from the token, payload owner_id ignored) | Verified |
| `/api/fields/{id}`          | GET    | 🔒 Single field detail (403 for another owner's field; demo fields open) | Verified |
| `/api/fields/{id}/readings` | GET    | 🔒 Trend data and merged readings                    | Verified |
| `/api/fields/{id}/risk`     | GET    | 🔒 Risk score, reasons, recommended check            | Verified |
| `/api/fields/{id}/alerts`   | GET    | 🔒 Alert history for preview                         | Verified |
| `/api/fields/{id}/photos`   | POST   | 🔒 Upload ground-truth photo with pending_review status | Verified |
| `/api/fields/{id}/photos`   | GET    | 🔒 List uploaded photos for a field                  | Verified |
| `/api/fields/feedback`      | POST   | 🔒 Farmer feedback for a field (403 across owners)  | Verified |
| `/api/feedback`             | POST   | 🔒 Top-level alias of the above                      | Verified |
| `/whatsapp/webhook`         | POST   | 🌐 Twilio inbound message handler — `X-Twilio-Signature` verified, 403 when invalid | Verified |
| `/api/whatsapp/webhook`     | POST   | 🌐 Alias of the above (same verification)            | Verified |
| `/api/validation-stats`     | GET    | 🌐 Aggregate feedback statistics (no owner-specific data) | Verified |

### Security scope (deliberately not full auth)

Owner access uses a per-owner opaque token, **not** a password/session system. What is
enforced: the token's `owner_id` is the only ownership filter, client-supplied `owner_id`
is ignored, and per-field endpoints 403 across owners. Explicitly **out of scope**: no
passwords, no sessions, **no token expiry or rotation**, and no rate limiting on
`/api/owners/register` (owner_id enumeration/abuse remains possible). A production
version needs password login, expiry/rotation, rate limiting, and httpOnly cookies or
short-lived tokens instead of `localStorage`.

## Decisions Made

| Date       | Decision                                                                                                                                     |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-09-24 | Stack confirmed: React + MapLibre, FastAPI, PostgreSQL + PostGIS                                                                             |
| 2026-09-24 | Risk engine rule-based (NDVI trend + rainfall deficit + temperature anomaly) for explainability                                              |
| 2026-09-24 | Demo mode strictly prefers live Sentinel Hub NDVI first; synthetic NDVI is restricted to flagged demo fields when live services fail and is labelled. |
| 2026-09-24 | Photos are stored locally with a pending review status, without AI processing                                                                |
| 2026-09-24 | Frontend uses browser speech synthesis for reading risk details aloud                                                                        |
| 2026-09-24 | Readings are cached per source and merged by date, with graceful fallback if external services fail                                          |
| 2026-09-24 | Product direction includes automatically detected field boundaries as a future real-world deployment step, following OneSoil-style workflows |
| 2026-09-24 | Forward-looking rainfall uses actual 7-day forecast data from Open-Meteo to drive risk-scoring instead of heuristics.                        |
| 2026-09-26 | CORS restricted to an explicit `ALLOWED_ORIGINS` allow-list (no wildcard); the deployed frontend URL is added by env var, not a code change.   |
| 2026-09-26 | Twilio webhook signatures verified inside `fields.whatsapp_webhook` so both webhook aliases share one check; fails closed with 500 if the auth token is unset. |
| 2026-09-26 | Owner identity is a per-owner opaque token (`X-Owner-Token`), scoped deliberately short of real auth: no passwords, sessions, expiry or rotation yet. Demo fields stay readable by any valid token. |

## Product Positioning Notes

- Real deployment would replace manually-placed boundaries with satellite auto-detection, following the same approach OneSoil uses at scale: algorithms trained on large field datasets detect field outlines automatically rather than requiring a farmer to draw them by hand.
- The app integrates real forward-looking forecast data from Open-Meteo (e.g. 7-day rainfall predictions) alongside historical satellite observations to provide proactive rather than purely reactive monitoring.
- The current demo remains intentionally explainable and lightweight, prioritising trust, speed, and clear action guidance over complex agronomic prediction models.
