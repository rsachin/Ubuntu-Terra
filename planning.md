# Ubuntu Terra — planning.md

Living document. Updated across architecture, scope, and implementation progress.

---

## Problem Statement Summary

South Africa is water-scarce, and agriculture is one of its largest water consumers. Satellite, weather, and soil
data already exist but are scattered, technical, and not packaged for a farmer to act on day to day. Ubuntu Terra turns scattered earth-observation and weather data into an early, explained, actionable signal for South African farmers — starting with water/crop stress.

## Target Users

- Commercial and emerging farmers managing multiple fields.
- Smallholder farmers with limited access to agronomists or soil testing.
- Farm managers responsible for water-use efficiency and yield early warnings.
- Secondary: agri-cooperatives, insurers, water authorities.

## Core Pain Point

Late detection — not knowing where to look, and not knowing why a specific area looks worse than the rest of the field.

## Proposed Solution

A map-based platform where a farmer/judge selects a field and sees: current condition (risk level + plain-language reason), a historical trend (NDVI, rainfall, temperature), and a recommended check — plus an alert preview showing what the farmer would receive off-platform (SMS/WhatsApp-style).

## Features & Implementation Status

### MVP Scope (100% Implemented)
1. [x] **Interactive map** with 3 real South African field boundaries (Patensie Citrus, Hankey Veg, Kirkwood Citrus).
2. [x] **Condition panel**: risk level (Low/Medium/High) + plain-language reason + contributing signals.
3. [x] **Historical trend view**: NDVI, rainfall, temperature inline SVG sparklines over recent weeks.
4. [x] **Rule-based risk engine** combining NDVI trend, rainfall deficit, and temperature anomaly.
5. [x] **Alert/notification preview** (simulated SMS/WhatsApp message).
6. [x] **Backend API + database** storing field boundaries, readings, risk scores, alerts, with caching.
7. [x] **Resilience**: loading states, error states, cached fallback if live external API is down.

## Architecture

```
ubuntu-terra/
├── frontend/          React + Vite + MapLibre GL JS: map view, field selector, risk panel
│   └── src/
│       ├── components/  (FieldMap, RiskBadge, ConditionPanel, TrendChart, AlertPreview, etc.)
│       ├── api/         (client.js, useFieldDashboard.js)
│       └── App.jsx
├── backend/           FastAPI app
│   ├── app/
│   │   ├── routers/   (/fields, /risk, /alerts endpoints)
│   │   ├── services/  (satellite.py, weather.py, risk_engine.py)
│   │   ├── models/    (DB models)
│   │   └── main.py
│   └── tests/         (32/32 unit & integration tests passing)
├── database/
│   ├── migrations/    001_initial_schema.sql
│   └── seed_demo_fields.py
├── planning.md
├── status.md
└── README.md
```

## Demo Region & Fields

**Region:** Gamtoos River Valley (Patensie, Hankey) and Sundays River Valley (Kirkwood), Eastern Cape.

| Field | Location | Water source | Role in demo |
|---|---|---|---|
| Patensie Citrus Block | Patensie, Gamtoos Valley (-33.755, 24.808) | Kouga Dam | Citrus — quota-restricted |
| Hankey Vegetable Field | Hankey, Gamtoos Valley (-33.828, 24.875) | Kouga Dam | Vegetables — quota-restricted |
| Kirkwood Citrus Block | Kirkwood, Sundays River Valley (-33.405, 25.450) | Gariep Dam scheme | Citrus — comparatively secure |

## API Endpoints (Fully Operational)

| Endpoint | Method | Purpose | Status |
|---|---|---|---|
| `/api/health` | GET | Liveness check | Verified (200) |
| `/api/fields` | GET | List all fields for the map | Verified (200) |
| `/api/fields/{id}` | GET | Single field detail | Verified (200) |
| `/api/fields/{id}/readings` | GET | Time series for trend chart | Verified (200) |
| `/api/fields/{id}/risk` | GET | Current risk & explanation | Verified (200) |
| `/api/fields/{id}/alerts` | GET | Alert preview content | Verified (200) |

## Decisions Made

| Date | Decision |
|---|---|
| 2026-09-24 | Stack confirmed: React + MapLibre, FastAPI, PostgreSQL + PostGIS |
| 2026-09-24 | Risk engine rule-based (NDVI trend + rainfall deficit + temp anomaly) for total explainability |
| 2026-09-24 | Auth: single hardcoded demo login for hackathon simplicity |
| 2026-09-24 | Readings cached per-source, merged by date at query time |
| 2026-09-24 | Full frontend + backend end-to-end integration verified |
