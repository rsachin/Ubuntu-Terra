# Phase 5 — Security & Ethics Hardening

## Goal

Strengthen the security and ethical posture of the app to meet the hackathon's Security & Ethics judging criterion and produce the artifacts needed for the SSDLC submission.

## What Is Already Present (from Phase 0)

- `.env` and `backend/uploads/` are gitignored; no secrets in the repo.
- CORS restricted to an explicit `ALLOWED_ORIGINS` allow-list.
- Parameterised SQL queries in all database access.
- Twilio webhook signature verification.
- Demo-grade owner-token auth with ownership enforcement.

## Scope IN

1. Rate limiting on public/abusable endpoints.
2. Request logging with redaction.
3. Token hashing at rest.
4. HTTPS/security headers for production deployments.
5. Input validation audit and documentation.
6. Privacy/data-handling notes for farm location data.
7. SSDLC submission draft.

## Scope OUT

- Full password-based login replacement (too large for the hackathon deadline; document the post-hackathon roadmap instead).
- Penetration testing by an external party.
- Production infrastructure hardening (firewalls, WAF) — document, don't implement.

## Task List

- [ ] **P5.1** Add rate limiting to `POST /api/owners/register` (e.g. 5 attempts per IP per hour) using `slowapi` or a custom in-memory store. (TODO.md Security #1)
- [ ] **P5.2** Add rate limiting to `POST /api/whatsapp/webhook` to prevent signature-verification CPU abuse. (TODO.md Security #2)
- [ ] **P5.3** Hash `owner_tokens.token` at rest with a slow hash (e.g. `bcrypt`) and update token lookup to hash the incoming header before comparison. (TODO.md Security #7)
- [ ] **P5.4** Add FastAPI middleware for request logging: method, path, status, duration, with `X-Owner-Token` and `TWILIO_AUTH_TOKEN` redacted. (TODO.md Security #3)
- [ ] **P5.5** Add `HTTPSRedirectMiddleware` and security headers (HSTS, CSP, X-Content-Type-Options) behind an `ENVIRONMENT=production` flag so local dev is unaffected. (TODO.md Security #4)
- [ ] **P5.6** Audit every `POST`/`PUT`/`GET` endpoint for input validation and document findings in `/docs/SECURITY_AUDIT.md`. (TODO.md Security #6)
- [ ] **P5.7** Write `/docs/PRIVACY.md` covering: what farm data is collected, why, retention, who can access it, and how farmers can request deletion. (TODO.md Docs #3)
- [ ] **P5.8** Run `pip-audit` on backend dependencies and `npm audit` on frontend dependencies; triage and document findings. (TODO.md Security #8)
- [ ] **P5.9** Draft the SSDLC submission: threat model, security controls list, dependency audit summary, privacy notes, and incident response outline. (TODO.md Product/Demo #8)
- [ ] **P5.10** Update `status.md`, `TODO.md`, `TECHNICAL_DEBT.md`.

## Definition of Done

1. `POST /api/owners/register` returns HTTP 429 after exceeding the configured rate limit.
2. `owner_tokens.token` is stored as a hash; plaintext tokens cannot be recovered from the DB.
3. A request log line is emitted for every API call with tokens redacted.
4. With `ENVIRONMENT=production`, HTTP requests are redirected to HTTPS and security headers are present.
5. `/docs/SECURITY_AUDIT.md` and `/docs/PRIVACY.md` exist and are accurate to the current code.
6. `pip-audit` and `npm audit` findings are documented with mitigation status; no unmitigated critical vulnerabilities in runtime dependencies.
7. SSDLC submission draft is complete and ready for human review.
8. The app still starts locally in development mode and the demo path works.
9. No P0/P1 technical-debt items in this phase's scope remain open.

## Deliverables

- Updated `backend/app/routers/fields.py`, `backend/app/main.py`, `backend/app/db.py`.
- New security middleware/logging code.
- New/updated tests for rate limiting, token hashing, and HTTPS headers.
- `/docs/SECURITY_AUDIT.md` and `/docs/PRIVACY.md`.
- SSDLC submission draft.
- Updated docs.

## Risks / Notes

- Hashing tokens will break existing seeded/demo tokens in local DBs; include a migration/reset step or a command to re-register tokens.
- Do not enable HTTPS redirect in local dev or tests will fail.
