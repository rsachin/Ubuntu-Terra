-- 001_initial_schema.sql
-- Ubuntu Terra — initial schema
-- Applied once, never edited after being applied. Schema changes go in a new numbered file.

CREATE EXTENSION IF NOT EXISTS postgis;

-- Farmer's field boundaries
CREATE TABLE IF NOT EXISTS fields (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    owner_id    VARCHAR(255),                      -- kept simple for the hackathon demo login
    boundary    GEOMETRY(POLYGON, 4326) NOT NULL,   -- WGS84 lat/lon polygon
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fields_boundary ON fields USING GIST (boundary);

-- One row per data pull per field per date, from satellite/weather services
CREATE TABLE IF NOT EXISTS readings (
    id           SERIAL PRIMARY KEY,
    field_id     INTEGER NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    date         DATE NOT NULL,
    ndvi_value   NUMERIC(4, 3),                     -- typically -1.0 to 1.0
    rainfall_mm  NUMERIC(6, 2),
    temp_c       NUMERIC(5, 2),
    source       VARCHAR(100) NOT NULL,              -- e.g. 'sentinel_hub', 'open_meteo', 'nasa_power'
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (field_id, date, source)                  -- avoid duplicate pulls for the same field/day/source
);

CREATE INDEX IF NOT EXISTS idx_readings_field_date ON readings (field_id, date);

-- Output of the risk engine, kept as history for the trend view
CREATE TABLE IF NOT EXISTS risk_scores (
    id              SERIAL PRIMARY KEY,
    field_id        INTEGER NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    score           VARCHAR(10) NOT NULL CHECK (score IN ('Low', 'Medium', 'High')),
    reason_summary  TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (field_id, date)
);

CREATE INDEX IF NOT EXISTS idx_risk_scores_field_date ON risk_scores (field_id, date);

-- Generated notification text and (simulated or real) delivery record
CREATE TABLE IF NOT EXISTS alerts (
    id            SERIAL PRIMARY KEY,
    field_id      INTEGER NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
    risk_score_id INTEGER REFERENCES risk_scores(id) ON DELETE SET NULL,
    message       TEXT NOT NULL,
    channel       VARCHAR(50) NOT NULL DEFAULT 'sms',  -- 'sms' | 'whatsapp' (simulated for the demo)
    sent_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_alerts_field ON alerts (field_id);
