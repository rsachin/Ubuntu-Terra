-- 006_alerts_delivery_status_and_reading_ttl.sql
-- Ubuntu Terra — Phase 2 data-layer hardening
--
-- 1. Track when each (field_id, source) was last refreshed so external APIs are
--    not hit on every request (TTL caching).
-- 2. Persist WhatsApp/SMS alert delivery status, provider message ID, and any
--    provider error so the app has an audit trail of whether an alert was
--    actually delivered or only simulated.

-- Per-source refresh metadata for TTL caching
CREATE TABLE IF NOT EXISTS reading_source_status (
    field_id         INTEGER NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    source           VARCHAR(100) NOT NULL,
    last_refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    cached_value_json JSONB,
    PRIMARY KEY (field_id, source)
);

CREATE INDEX IF NOT EXISTS idx_reading_source_status_field ON reading_source_status(field_id);

-- Add cached_value_json column if the table was created by an earlier version of this migration.
ALTER TABLE reading_source_status
    ADD COLUMN IF NOT EXISTS cached_value_json JSONB;

-- Alert delivery audit columns
ALTER TABLE alerts
    ADD COLUMN IF NOT EXISTS status VARCHAR(20),
    ADD COLUMN IF NOT EXISTS provider_message_id TEXT,
    ADD COLUMN IF NOT EXISTS provider_error TEXT;
