# Phase 6 — Demo Readiness

## Goal

Package the running product into a rehearsed, compelling, <90-second demo with a clear golden path, supporting collateral, and a green CI gate.

## What Is Already Present (from Phase 0)

- A feature-complete app: map, field list, condition panel, trend charts, WhatsApp preview, photo upload, feedback, and disclaimer.
- `README.md`, `planning.md`, `status.md`, and the four `/docs` Phase 0 artifacts.
- A WhatsApp alert pipeline that works in simulated mode without Twilio credentials.

## Scope IN

1. Write a click-by-click `DEMO.md` script.
2. Record or storyboard a <90-second demo video.
3. Add Docker / CI for reproducibility.
4. Add final UX polish and a "demo mode" banner if needed.
5. Verify the golden path end-to-end on the target demo machine.

## Scope OUT

- New product features not required for the demo.
- Business-case slide content (Phase 7).
- Major security refactoring (Phase 5).

## Task List

- [ ] **P6.1** Write `/docs/DEMO.md` with a 90-second click-by-click script including screen captures/transitions and spoken narration cues. (TODO.md Product/Demo #4)
- [ ] **P6.2** Add a `docker-compose.yml` with `postgres:15-postgis`, `backend`, and `frontend` services, and a backend `Dockerfile`. (TODO.md DevEx #1–2)
- [ ] **P6.3** Add a GitHub Actions workflow that runs `pytest` and `npm run build` on every push/PR. (TODO.md DevEx #3)
- [ ] **P6.4** Record the 90-second demo video (or produce a storyboard + timing if recording tools are unavailable). (TODO.md Product/Demo #5)
- [ ] **P6.5** Add a subtle "Hackathon demo — advisory only" banner or tooltip reinforcement so judges immediately understand the product maturity. (TODO.md Product/Demo #2)
- [ ] **P6.6** Configure the real Twilio sandbox Auth Token and webhook URL on the demo machine if live WhatsApp is required; otherwise rehearse the simulated path. (TODO.md Product/Demo #1, Blockers for Human #2)
- [ ] **P6.7** Run the full stack (backend + frontend + DB) from a clean clone and complete the smoke-test checklist on the demo machine. (TODO.md DevEx #5)
- [ ] **P6.8** Add a `CONTRIBUTING.md` with branch conventions and PR checklist for any last-minute team changes. (TODO.md Docs #2)
- [ ] **P6.9** Final update of `status.md`, `TODO.md`, `TECHNICAL_DEBT.md`.

## Definition of Done

1. `docker-compose up` from a clean clone starts PostgreSQL + backend + frontend, and the app is reachable at `http://localhost:5173`.
2. GitHub Actions runs `pytest` and `npm run build` successfully on the repository.
3. `/docs/DEMO.md` exists and contains a 90-second script with exact UI steps and narration.
4. The demo video or storyboard is produced and stored in the repo or linked from `DEMO.md`.
5. The golden path is rehearsed end-to-end on the demo machine with no blocking issues.
6. The simulated WhatsApp alert is demoable without real Twilio credentials; OR the live Twilio path is verified with a real token.
7. No P0/P1 technical-debt items in this phase's scope remain open.

## Deliverables

- `/docs/DEMO.md`.
- `docker-compose.yml` and `backend/Dockerfile`.
- `.github/workflows/ci.yml`.
- 90-second demo video or storyboard.
- `CONTRIBUTING.md`.
- Updated docs and green CI badge in `README.md`.

## Risks / Notes

- Docker on Windows requires WSL2 or Docker Desktop; include a note in `DEMO.md` if the demo machine does not support it.
- Recording a 90-second video can take several attempts; budget time for retakes.
