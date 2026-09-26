# Phase 3 — Core API Hardening

## Goal

Validate, tighten, and test the FastAPI endpoints so the field/risk/feedback API is robust, correctly authorised, and free of routing or input-validation gaps.

## What Is Already Present (from Phase 0)

- `backend/app/routers/fields.py` with CRUD, readings, risk, alerts, photo upload, feedback, and validation-stats endpoints.
- Owner-token dependency `require_owner_token` and ownership enforcement in `_get_accessible_field_or_403`.
- Twilio webhook signature verification in `whatsapp_webhook`.
- Pydantic models for `FieldCreate`, `OwnerRegister`, `FeedbackCreate`.

## Scope IN

1. Fix the shadowed `/api/fields/validation-stats` route.
2. Audit and strengthen input validation on all write endpoints.
3. Add file-size and image-dimension limits to photo upload.
4. Ensure all owner-scoped endpoints reject client-supplied `owner_id`.
5. Make `test_fields_router.py` and `test_whatsapp_webhook.py` green.
6. Add API-level tests for edge cases (invalid GeoJSON, out-of-bounds polygons, missing tokens).

## Scope OUT

- Replacing owner-token auth with real login (Phase 5).
- Adding background workers or message queues.
- New endpoint creation beyond what's needed to close gaps.

## Task List

- [ ] **P3.1** Remove or reorder `GET /api/fields/validation-stats` so it is not shadowed by `GET /api/fields/{field_id}`. The top-level `/validation-stats` aliases are sufficient. (TODO.md Bugs #4)
- [ ] **P3.2** Add stricter validation in `FieldCreate`: `name` max length 120 chars, reject empty/whitespace-only names, strip control characters. (TODO.md Security #5)
- [ ] **P3.3** Add a `MAX_UPLOAD_SIZE_MB` environment variable (default 5) and reject oversized photo uploads with HTTP 413. (TODO.md Missing Features #4)
- [ ] **P3.4** Validate uploaded image dimensions and reject non-image content types before running `pest_vision` analysis. (TODO.md Missing Features #4)
- [ ] **P3.5** Confirm `POST /api/fields` ignores any `owner_id` in the body and that `GET /api/fields?owner_id=...` returns 400. Add regression tests. (TODO.md Security #5)
- [ ] **P3.6** Add rate-limiting dependency scaffolding (actual limits configured in Phase 5) so endpoints can opt-in without code changes. (TODO.md Security #1)
- [ ] **P3.7** Run the full backend test suite against a seeded database and fix any failures in `test_fields_router.py` and `test_whatsapp_webhook.py`. (TODO.md Bugs #5–6)
- [ ] **P3.8** Add a test for each HTTP 400/401/403/404 path in the fields router to lock in the security behaviour. (TODO.md Tests #3)
- [ ] **P3.9** Update `README.md` API endpoint table with the corrected routes and validation behaviour. (TODO.md Docs #1)
- [ ] **P3.10** Update `status.md`, `TODO.md`, `TECHNICAL_DEBT.md`.

## Definition of Done

1. `pytest tests/ -q` runs with **0 failures** against a local seeded PostGIS database.
2. `GET /api/fields/validation-stats` no longer exists as a shadowed path; only `/api/validation-stats` and `/api/fields/{id}` remain.
3. Uploading a file larger than `MAX_UPLOAD_SIZE_MB` returns HTTP 413.
4. Uploading a non-image file returns HTTP 400.
5. All auth/authz tests pass: missing token → 401, wrong token → 401, cross-owner access → 403, client-supplied `owner_id` query param → 400.
6. The app starts locally; the golden path (register token → create field → get readings → get risk → get alerts) works end-to-end.
7. No P0/P1 technical-debt items in this phase's scope remain open.

## Deliverables

- Updated `backend/app/routers/fields.py`.
- Updated `backend/app/services/pest_vision.py` (input validation hooks if needed).
- New/updated tests in `backend/tests/`.
- Updated `README.md`, `status.md`, `TODO.md`, `TECHNICAL_DEBT.md`.

## Risks / Notes

- `test_whatsapp_webhook.py` needs the Twilio token set; ensure the test fixture monkeypatches it correctly so it does not depend on `.env`.
- Avoid breaking the existing frontend contract when changing routes.
