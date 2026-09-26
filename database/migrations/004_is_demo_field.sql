-- 004_is_demo_field.sql
-- Flags the seeded demo fields so synthetic NDVI can be restricted to them
-- instead of being used for any farmer-created field.
--
-- IF NOT EXISTS keeps this re-runnable, matching every other migration.
ALTER TABLE fields
    ADD COLUMN IF NOT EXISTS is_demo_field BOOLEAN NOT NULL DEFAULT FALSE;
