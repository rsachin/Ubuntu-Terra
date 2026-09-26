# Phase 1 — Stabilize & Run

## Goal

Make the repository trustworthy for every subsequent agent and judge: the test suite is green, migrations are reliable, the local Windows setup works end-to-end, and the app starts without manual workarounds.

## What Is Already Present (from Phase 0)

- Full React/Vite frontend and FastAPI backend codebase.
- Five idempotent SQL migrations (`001`–`005`).
- A `.env.example` and a `LOCAL_SETUP_WINDOWS.md` guide.
- Backend dependencies are pinned in `requirements.txt`.

## Scope IN

1. Fix the red test suite.
2. Create a single, ordered migration runner.
3. Verify the local Windows dev stack installs and runs.
4. Add minimal DevEx tooling so the stack is one-command to start.
5. Update living docs (`status.md`, `TODO.md`, `TECHNICAL_DEBT.md`) as work progresses.

## Scope OUT

- New features (caching, real-time alerts, new UI components).
- Security hardening beyond what's needed to run locally (handled in Phase 5).
- Docker/CI/CD full pipelines (started here if quick, but full CI is Phase 6 scope).

## Task List

- [ ] **P1.1** Update `backend/tests/test_risk_engine.py` to use the current `assess_field_risk(ndvi_readings, temp_readings_c, forecast_rainfall_mm)` signature. (TODO.md Bugs #1)
- [ ] **P1.2** Verify all no-DB unit tests pass: `pytest tests/test_health.py tests/test_risk_engine.py tests/test_weather.py tests/test_satellite.py -q`. (TODO.md Bugs #2)
- [ ] **P1.3** Create `database/migrate.py`: apply `001→005` in order, idempotent, with a `--seed` flag that runs `seed_demo_fields.py`. (TODO.md Missing Features #1)
- [ ] **P1.4** Delete `database/apply_migration.py` and `database/apply_migration_005.py`. (TODO.md Missing Features #2)
- [ ] **P1.5** Add `requires-python = ">=3.10,<3.14"` to `backend/pyproject.toml` (or document in `README.md` if no pyproject exists) to formalise the Python 3.10–3.13 support and avoid 3.14 wheel failures. (TODO.md Bugs #3)
- [ ] **P1.6** Add a combined Windows dev script `scripts/dev.ps1` that starts PostgreSQL (if installed locally), applies migrations/seeds, starts the backend, and starts the frontend. (TODO.md DevEx #3)
- [ ] **P1.7** Verify `LOCAL_SETUP_WINDOWS.md` smoke-test checklist passes on a clean Windows environment (or this machine if it's representative). (TODO.md DevEx #5)
- [ ] **P1.8** Add a `.nvmrc` / `.node-version` file pinning Node 20 and document it. (TODO.md DevEx #6)
- [ ] **P1.9** Run the full backend test suite against a seeded local database and close any newly discovered P0/P1 debt. (TODO.md Bugs #5–6)
- [ ] **P1.10** Update `status.md` and `TODO.md` to reflect completed items and any new debt.

## Definition of Done

1. `pytest tests/test_health.py tests/test_risk_engine.py tests/test_weather.py tests/test_satellite.py -q` exits with **0 failures**.
2. `python database/migrate.py --seed` creates the schema and seeds the 3 demo fields without errors on a fresh database.
3. The backend starts with `uvicorn app.main:app --reload --port 8000` and returns `{"status":"ok"}` from `/api/health`.
4. The frontend starts with `npm run dev` and loads the map at `http://localhost:5173` without a backend-connection error banner.
5. The smoke-test checklist in `LOCAL_SETUP_WINDOWS.md` is completed and signed off.
6. No P0 or P1 technical-debt items remain open **within this phase's scope**.
7. All commits reference TODO.md items (e.g. `Fixes TODO Bugs #1: update risk-engine tests to forecast_rainfall_mm`).

## Deliverables

- Updated `backend/tests/test_risk_engine.py`.
- New `database/migrate.py`.
- Deleted ad-hoc migration scripts.
- New `scripts/dev.ps1`.
- Updated `status.md`, `TODO.md`, `TECHNICAL_DEBT.md`.
- Signed-off `LOCAL_SETUP_WINDOWS.md` smoke-test result.

## Risks / Notes

- The Phase 0 environment had no running PostgreSQL, so the database-dependent tests were not exercised here. P1.9 must be done before Phase 2 starts.
- If `psycopg2-binary` fails on another Windows machine, fallback to installing the full PostgreSQL client libraries may be needed; capture that in `LOCAL_SETUP_WINDOWS.md`.
