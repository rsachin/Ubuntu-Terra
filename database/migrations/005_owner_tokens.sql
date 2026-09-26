-- 005_owner_tokens.sql
--
-- Lightweight per-owner access token. This is INTENTIONALLY NOT a full
-- authentication system: there are no passwords, no login/session lifecycle,
-- no token expiry and no rotation. One opaque random token is minted per
-- owner_id and it stays valid indefinitely. The sole purpose is to close the
-- trivial "just type a different owner_id string" gap in the demo.
--
-- A real production version would additionally need:
--   * password-based login (or a real identity provider) to obtain a token,
--   * token expiry + rotation/revocation so a leaked token stops working,
--   * rate limiting on POST /api/owners/register to prevent owner_id
--     enumeration and token-minting abuse,
--   * tokens hashed at rest, and HTTPS-only transport.
--
-- NOTE: this migration only ADDS a table. The fields.owner_id column and the
-- already-seeded demo fields are left untouched.

CREATE TABLE IF NOT EXISTS owner_tokens (
    token TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
