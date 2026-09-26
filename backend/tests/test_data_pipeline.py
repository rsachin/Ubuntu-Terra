"""
Integration tests for the core data pipeline and TTL caching in Phase 2.

Runs against the REAL local PostGIS database with migrations 001–006 applied
and demo fields seeded. External weather/satellite calls are monkeypatched
so these tests need no network or Copernicus credentials.
"""
import datetime as dt
import os
import uuid

import psycopg2
import pytest
from fastapi.testclient import TestClient
from psycopg2.extras import RealDictCursor

from app.main import app
from app.services import satellite as satellite_service
from app.services import weather as weather_service
from app.services.satellite import NdviReading
from app.services.weather import DailyWeather

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ubuntu_terra"
)

client = TestClient(app)

TEST_OWNER = "test_pipeline"


@pytest.fixture(scope="module")
def owner_headers():
    """Auth headers for the shared test owner."""
    token = "test-pipeline-owner-token"
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    with conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO owner_tokens (token, owner_id) VALUES (%s, %s)
            ON CONFLICT (owner_id) DO UPDATE SET token = EXCLUDED.token
            """,
            (token, TEST_OWNER),
        )
    conn.close()
    yield {"X-Owner-Token": token}


@pytest.fixture
def test_field(owner_headers):
    """Creates an isolated non-demo test field and cleans it up after the test."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    with conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fields (name, owner_id, boundary)
            VALUES (%s, %s, ST_GeomFromText(%s, 4326))
            RETURNING id
            """,
            (
                "Pipeline Test Field",
                TEST_OWNER,
                "POLYGON((24.80 -33.75, 24.81 -33.75, 24.81 -33.76, 24.80 -33.76, 24.80 -33.75))",
            ),
        )
        field_id = cur.fetchone()["id"]
    conn.close()

    yield field_id

    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    with conn, conn.cursor() as cur:
        cur.execute("DELETE FROM fields WHERE id = %s", (field_id,))
    conn.close()


@pytest.fixture
def demo_field_id(owner_headers):
    """Return the first seeded demo field id."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    with conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM fields WHERE is_demo_field = true ORDER BY id LIMIT 1")
        row = cur.fetchone()
    conn.close()
    assert row, "expected at least one demo field to be seeded"
    return row["id"]


def _clear_source_status(field_id: int):
    """Helper to reset TTL metadata for a field so the next request re-fetches."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    with conn, conn.cursor() as cur:
        cur.execute("DELETE FROM reading_source_status WHERE field_id = %s", (field_id,))
    conn.close()


def test_full_pipeline_creates_alert_with_simulated_status(
    test_field, owner_headers, monkeypatch
):
    """
    End-to-end: readings sync -> risk compute -> alert generation.
    Without Twilio credentials the alert is persisted with status='simulated'.
    """
    fake_weather = [
        DailyWeather(date=dt.date(2026, 9, 20), rainfall_mm=20.0, temp_c=21.0, source="open_meteo"),
        DailyWeather(date=dt.date(2026, 9, 21), rainfall_mm=1.0, temp_c=28.0, source="open_meteo"),
    ]
    fake_ndvi = [
        NdviReading(date=dt.date(2026, 9, 20), ndvi_mean=0.60, sample_count=800),
        NdviReading(date=dt.date(2026, 9, 21), ndvi_mean=0.40, sample_count=800),
    ]
    monkeypatch.setattr(weather_service, "get_recent_weather", lambda *a, **k: fake_weather)
    monkeypatch.setattr(weather_service, "get_forecast_rainfall", lambda *a, **k: 5.0)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", lambda *a, **k: fake_ndvi)

    res = client.get(f"/api/fields/{test_field}/alerts", headers=owner_headers)
    assert res.status_code == 200, res.text
    alerts = res.json()
    assert len(alerts) >= 1
    first = alerts[0]
    assert first["status"] == "simulated"
    assert first["channel"] == "whatsapp"
    assert first["audio_url"].endswith(".mp3")

    # Verify the alert row in the DB carries the persisted status.
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    with conn, conn.cursor() as cur:
        cur.execute(
            "SELECT status, provider_message_id, provider_error FROM alerts WHERE field_id = %s",
            (test_field,),
        )
        row = cur.fetchone()
    conn.close()
    assert row["status"] == "simulated"
    assert row["provider_error"] is None


def test_ttl_cache_skips_external_api_on_second_readings_call(
    test_field, owner_headers, monkeypatch
):
    """
    The first /readings call fetches and caches weather/NDVI. The second call
    within the TTL window must not re-invoke the external services.
    """
    call_counts = {"weather": 0, "ndvi": 0}

    def fake_weather(*args, **kwargs):
        call_counts["weather"] += 1
        return [
            DailyWeather(date=dt.date(2026, 9, 22), rainfall_mm=5.0, temp_c=22.0, source="open_meteo"),
        ]

    def fake_ndvi(*args, **kwargs):
        call_counts["ndvi"] += 1
        return [
            NdviReading(date=dt.date(2026, 9, 22), ndvi_mean=0.55, sample_count=800),
        ]

    monkeypatch.setattr(weather_service, "get_recent_weather", fake_weather)
    monkeypatch.setattr(weather_service, "get_forecast_rainfall", lambda *a, **k: 10.0)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", fake_ndvi)

    # First call: should hit external services.
    first = client.get(f"/api/fields/{test_field}/readings", headers=owner_headers)
    assert first.status_code == 200
    assert call_counts["weather"] == 1
    assert call_counts["ndvi"] == 1

    # Second call within TTL: should reuse cached data.
    second = client.get(f"/api/fields/{test_field}/readings", headers=owner_headers)
    assert second.status_code == 200
    assert call_counts["weather"] == 1, "weather service should not be called again within TTL"
    assert call_counts["ndvi"] == 1, "satellite service should not be called again within TTL"


def test_demo_field_gets_demo_ndvi_when_live_satellite_fails(
    demo_field_id, owner_headers, monkeypatch
):
    """
    When Sentinel Hub fails for a demo field, the demo NDVI trigger is seeded
    and the readings endpoint returns data labelled as demo_trigger.
    """
    _clear_source_status(demo_field_id)

    def failing_ndvi(*args, **kwargs):
        raise RuntimeError("simulated Sentinel Hub outage")

    monkeypatch.setattr(weather_service, "get_recent_weather", lambda *a, **k: [])
    monkeypatch.setattr(weather_service, "get_forecast_rainfall", lambda *a, **k: None)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", failing_ndvi)

    res = client.get(f"/api/fields/{demo_field_id}/readings", headers=owner_headers)
    assert res.status_code == 200, res.text
    readings = res.json()
    sources = {r["source"] for r in readings if "source" in r}
    # The endpoint merges readings and does not return source directly, so check DB.

    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    with conn, conn.cursor() as cur:
        cur.execute(
            "SELECT source FROM readings WHERE field_id = %s AND source = 'demo_trigger'",
            (demo_field_id,),
        )
        demo_rows = cur.fetchall()
    conn.close()
    assert len(demo_rows) > 0, "demo field should have demo_trigger readings after satellite failure"


def test_non_demo_field_does_not_get_demo_ndvi_when_satellite_fails(
    test_field, owner_headers, monkeypatch
):
    """
    Non-demo fields must never receive synthetic demo NDVI, even when Sentinel
    Hub is unavailable.
    """
    _clear_source_status(test_field)

    def failing_ndvi(*args, **kwargs):
        raise RuntimeError("simulated Sentinel Hub outage")

    monkeypatch.setattr(weather_service, "get_recent_weather", lambda *a, **k: [])
    monkeypatch.setattr(weather_service, "get_forecast_rainfall", lambda *a, **k: None)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", failing_ndvi)

    res = client.get(f"/api/fields/{test_field}/readings", headers=owner_headers)
    assert res.status_code == 200, res.text

    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    with conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM readings WHERE field_id = %s AND source = 'demo_trigger'",
            (test_field,),
        )
        demo_rows = cur.fetchall()
    conn.close()
    assert len(demo_rows) == 0, "non-demo field must not have demo_trigger readings"
