-- 003_farmer_feedback.sql
-- Ubuntu Terra — farmer feedback and validation tracking schema for Phase 3

CREATE TABLE IF NOT EXISTS farmer_feedback (
    id                 SERIAL PRIMARY KEY,
    field_id           INTEGER NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    risk_score_id      INTEGER REFERENCES risk_scores(id) ON DELETE CASCADE,
    photo_diagnosis_id INTEGER REFERENCES photo_diagnoses(id) ON DELETE CASCADE,
    was_accurate       BOOLEAN NOT NULL,
    farmer_comment     TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_farmer_feedback_field ON farmer_feedback(field_id);
