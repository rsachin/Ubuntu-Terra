"""
Tests for routers/fields.py — run against the REAL local PostGIS database
(requires the migration applied + demo fields seeded, same as
test_database.py). The external weather/satellite calls are monkeypatched
so these tests don't depend on live network or Copernicus credentials —
only the DB layer and the endpoint wiring itself are under test here.
"""
import datetime as dt
import os

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


@pytest.fixture
def test_field():
    """Creates an isolated test field so these tests don't pollute the real
    seeded demo fields' reading history. Cleaned up after each test
    (readings/risk_scores/alerts cascade-delete via the FK)."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    with conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fields (name, owner_id, boundary)
            VALUES (%s, %s, ST_GeomFromText(%s, 4326))
            RETURNING id
            """,
            (
                "Test Field — Router Tests",
                "test",
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


def test_list_fields_includes_seeded_demo_fields():
    response = client.get("/api/fields")
    assert response.status_code == 200
    names = [f["name"] for f in response.json()]
    assert "Patensie Citrus Block — Gamtoos Valley" in names
    assert "Hankey Vegetable Field — Gamtoos Valley" in names
    assert "Kirkwood Citrus Block — Sundays River Valley" in names


def test_get_field_detail(test_field):
    response = client.get(f"/api/fields/{test_field}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == test_field
    assert body["boundary"]["type"] == "Polygon"
    assert "created_at" in body


def test_get_field_404_for_unknown_id():
    response = client.get("/api/fields/999999")
    assert response.status_code == 404


def test_readings_endpoint_merges_weather_and_ndvi_by_date(test_field, monkeypatch):
    fake_weather = [
        DailyWeather(date=dt.date(2026, 9, 20), rainfall_mm=5.0, temp_c=22.0, source="open_meteo"),
        DailyWeather(date=dt.date(2026, 9, 21), rainfall_mm=0.0, temp_c=24.0, source="open_meteo"),
    ]
    fake_ndvi = [
        NdviReading(date=dt.date(2026, 9, 20), ndvi_mean=0.55, sample_count=800),
        NdviReading(date=dt.date(2026, 9, 21), ndvi_mean=0.50, sample_count=800),
    ]
    monkeypatch.setattr(weather_service, "get_recent_weather", lambda *a, **k: fake_weather)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", lambda *a, **k: fake_ndvi)

    response = client.get(f"/api/fields/{test_field}/readings")
    assert response.status_code == 200
    body = response.json()
    dates = {r["date"] for r in body}
    assert {"2026-09-20", "2026-09-21"}.issubset(dates)

    day1 = next(r for r in body if r["date"] == "2026-09-20")
    assert day1["ndvi"] == 0.55
    assert day1["rainfall_mm"] == 5.0
    assert day1["temp_c"] == 22.0


def test_risk_endpoint_flags_declining_field(test_field, monkeypatch):
    fake_weather = [
        DailyWeather(date=dt.date(2026, 9, 18), rainfall_mm=25.0, temp_c=21.0, source="open_meteo"),
        DailyWeather(date=dt.date(2026, 9, 19), rainfall_mm=22.0, temp_c=21.2, source="open_meteo"),
        DailyWeather(date=dt.date(2026, 9, 20), rainfall_mm=5.0, temp_c=25.0, source="open_meteo"),
    ]
    fake_ndvi = [
        NdviReading(date=dt.date(2026, 9, 18), ndvi_mean=0.60, sample_count=800),
        NdviReading(date=dt.date(2026, 9, 19), ndvi_mean=0.58, sample_count=800),
        NdviReading(date=dt.date(2026, 9, 20), ndvi_mean=0.48, sample_count=800),
    ]
    monkeypatch.setattr(weather_service, "get_recent_weather", lambda *a, **k: fake_weather)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", lambda *a, **k: fake_ndvi)

    response = client.get(f"/api/fields/{test_field}/risk")
    assert response.status_code == 200
    body = response.json()
    assert body["score"] in ("Medium", "High")
    assert body["reasons"]
    assert "irrigation" in body["recommended_check"].lower()


def test_risk_endpoint_healthy_field_is_low(test_field, monkeypatch):
    fake_weather = [
        DailyWeather(date=dt.date(2026, 9, 18), rainfall_mm=18.0, temp_c=21.0, source="open_meteo"),
        DailyWeather(date=dt.date(2026, 9, 19), rainfall_mm=19.0, temp_c=21.2, source="open_meteo"),
    ]
    fake_ndvi = [
        NdviReading(date=dt.date(2026, 9, 18), ndvi_mean=0.58, sample_count=800),
        NdviReading(date=dt.date(2026, 9, 19), ndvi_mean=0.60, sample_count=800),
    ]
    monkeypatch.setattr(weather_service, "get_recent_weather", lambda *a, **k: fake_weather)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", lambda *a, **k: fake_ndvi)

    response = client.get(f"/api/fields/{test_field}/risk")
    assert response.status_code == 200
    assert response.json()["score"] == "Low"


def test_alerts_message_matches_current_risk_score(test_field, monkeypatch):
    # Needs a real trend (2+ points) for the risk engine to flag anything —
    # a single reading has no baseline to compare against and is correctly
    # always Low. Use the same declining-field shape as the risk test above.
    fake_weather = [
        DailyWeather(date=dt.date(2026, 9, 21), rainfall_mm=20.0, temp_c=21.0, source="open_meteo"),
        DailyWeather(date=dt.date(2026, 9, 22), rainfall_mm=1.0, temp_c=26.0, source="open_meteo"),
    ]
    fake_ndvi = [
        NdviReading(date=dt.date(2026, 9, 21), ndvi_mean=0.60, sample_count=800),
        NdviReading(date=dt.date(2026, 9, 22), ndvi_mean=0.40, sample_count=800),
    ]
    monkeypatch.setattr(weather_service, "get_recent_weather", lambda *a, **k: fake_weather)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", lambda *a, **k: fake_ndvi)

    risk_score = client.get(f"/api/fields/{test_field}/risk").json()["score"]
    alerts = client.get(f"/api/fields/{test_field}/alerts").json()

    assert risk_score in ("Medium", "High")  # sanity check this scenario actually flags
    assert len(alerts) >= 1
    assert risk_score in alerts[0]["message"]


def test_readings_fall_back_to_cache_when_both_external_services_fail(test_field, monkeypatch):
    # First call: both services succeed, data gets cached.
    fake_weather = [DailyWeather(date=dt.date(2026, 9, 22), rainfall_mm=1.0, temp_c=26.0, source="open_meteo")]
    fake_ndvi = [NdviReading(date=dt.date(2026, 9, 22), ndvi_mean=0.4, sample_count=800)]
    monkeypatch.setattr(weather_service, "get_recent_weather", lambda *a, **k: fake_weather)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", lambda *a, **k: fake_ndvi)

    first = client.get(f"/api/fields/{test_field}/readings")
    assert first.status_code == 200
    assert len(first.json()) == 1

    # Second call: simulate both live services being down. Endpoint must
    # NOT error — it should serve the cached reading from the first call.
    def raise_error(*args, **kwargs):
        raise Exception("simulated external API outage")

    monkeypatch.setattr(weather_service, "get_recent_weather", raise_error)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", raise_error)

    second = client.get(f"/api/fields/{test_field}/readings")
    assert second.status_code == 200
    assert len(second.json()) == 1
    assert second.json()[0]["ndvi"] == 0.4  # cached value, not lost
