# Phase 4 — Map & Farmer UI

## Goal

Make the frontend robust, responsive, and demo-ready: it handles errors gracefully, presents the demo narrative clearly, and supports the core farmer workflow on desktop and mobile.

## What Is Already Present (from Phase 0)

- `frontend/src/App.jsx` with field list, map, condition panel, trend chart, alert preview, and photo upload.
- `FieldMap.jsx` with click-to-draw, Nominatim search, geolocation, and custom risk pins.
- `ConditionPanel.jsx` with risk badge, signal states, voice read-aloud, language toggle, feedback buttons, and photo diagnosis display.
- `useFieldDashboard.js` for partial-data resilience.
- Dark glassmorphic styling in `index.css`.

## Scope IN

1. Fix responsive layout issues on smaller screens.
2. Add frontend unit/component tests.
3. Improve demo-data labelling and the provisional validation-stats UI.
4. Add a "last refreshed" indicator for readings.
5. Ensure the golden-path UI has no console errors or broken interactions.

## Scope OUT

- Complete visual redesign.
- New major UI features (dashboard, admin panel, settings page).
- PWA/offline service worker.

## Task List

- [ ] **P4.1** Fix the mobile responsive layout: ensure the map and panels stack correctly at widths ≤ 860 px, touch targets are ≥ 44 px, and text remains readable. (TODO.md Tests #2)
- [ ] **P4.2** Add Vitest + React Testing Library to the frontend and write unit tests for `RiskBadge`, `TrendChart`, and the `api/client.js` token flow. (TODO.md Tests #1)
- [ ] **P4.3** Add a frontend e2e smoke test (Playwright or Cypress) for: map loads, demo field polygon visible, condition panel shows a risk score. (TODO.md Tests #2)
- [ ] **P4.4** Add a "last refreshed" indicator in `ConditionPanel` using the new `last_refreshed_at` data from Phase 2. (TODO.md Missing Features #6)
- [ ] **P4.5** Display a provisional/early-stage badge in `DisclaimerModal` when validation stats are below 20 responses. (TODO.md Missing Features #5)
- [ ] **P4.6** Ensure the `[Demo data]` label is prominent and consistent across the condition panel and alert preview. (TODO.md Product/Demo #2)
- [ ] **P4.7** Add a friendly empty state for when no fields exist and guide the user to draw a field. (TODO.md Tests #2)
- [ ] **P4.8** Run `npm run build` and `npm run lint` with zero errors. (TODO.md DevEx #5)
- [ ] **P4.9** Update `frontend/README.md` with test commands and the production build process. (TODO.md Docs #1)
- [ ] **P4.10** Update `status.md`, `TODO.md`, `TECHNICAL_DEBT.md`.

## Definition of Done

1. `npm run build` succeeds with no errors and `npm run lint` reports no blocking issues.
2. Frontend unit tests for `RiskBadge`, `TrendChart`, and `api/client.js` pass (`npm test` or equivalent).
3. The e2e smoke test passes: map loads, a demo field polygon is visible, the condition panel shows `Low`/`Medium`/`High`.
4. The UI is usable at 375 px viewport width (no horizontal overflow, reachable buttons).
5. `[Demo data]` is clearly shown for demo fields; the disclaimer modal shows an "Early Stage" badge when feedback count < 20.
6. No console errors on the golden path.
7. The app starts locally and the demo path works.
8. No P0/P1 technical-debt items in this phase's scope remain open.

## Deliverables

- Updated frontend components and CSS.
- New `frontend/src/__tests__/` or equivalent unit tests.
- New e2e test configuration and spec.
- Updated `frontend/package.json` scripts if new test commands are added.
- Updated docs.

## Risks / Notes

- Adding Playwright/Cypress may require additional setup time; if bandwidth is tight, fall back to a Vitest-based smoke test that renders the full app with a mocked backend.
- MapLibre WebGL can fail in headless CI; ensure tests handle that gracefully.
