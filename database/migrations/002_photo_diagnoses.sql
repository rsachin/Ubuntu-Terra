-- 002_photo_diagnoses.sql
-- Ubuntu Terra — photo diagnoses schema for Phase 2

CREATE TABLE IF NOT EXISTS photo_diagnoses (
    id          SERIAL PRIMARY KEY,
    field_id    INTEGER NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    filename    VARCHAR(255) NOT NULL,
    category    VARCHAR(100) NOT NULL,
    confidence  NUMERIC(4, 3) NOT NULL,
    description TEXT NOT NULL,
    model_name  VARCHAR(100) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_photo_diagnoses_field ON photo_diagnoses(field_id);
