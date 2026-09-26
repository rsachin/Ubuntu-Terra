"""
Tests for routers/fields.py — run against the REAL local PostGIS database
(requires the migration applied + demo fields seeded, same as
test_database.py). The external weather/satellite calls are monkeypatched
so these tests don't depend on live network or Copernicus credentials —
only the DB layer and the endpoint wiring itself are under test here.
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


# --- Owner-token helpers -------------------------------------------------
# Owner-scoped endpoints require an X-Owner-Token. Tests that need to act as a
# specific owner register one via the real /api/owners/register endpoint, so the
# tests exercise the same path the frontend uses.

TEST_OWNER = "test"


@pytest.fixture(scope="module")
def owner_headers():
    """
    Auth headers for the shared 'test' owner that owns the test_field rows.

    The token is written directly rather than via /api/owners/register, which
    returns 409 for an owner_id that already has a token — that would make this
    fixture fail the second time it ran against the same database. Upserting on
    owner_id keeps it idempotent across runs.
    """
    token = "test-owner-token-fixture"
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
def owner():
    """A freshly registered owner with a valid token and ready-to-use headers."""
    owner_id = f"test_owner_{uuid.uuid4().hex[:12]}"
    res = client.post("/api/owners/register", json={"owner_id": owner_id})
    assert res.status_code == 201, res.text
    token = res.json()["token"]

    yield {
        "owner_id": owner_id,
        "token": token,
        "headers": {"X-Owner-Token": token},
    }

    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    with conn, conn.cursor() as cur:
        cur.execute("DELETE FROM owner_tokens WHERE owner_id = %s", (owner_id,))
    conn.close()


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


def _delete_field(field_id):
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    with conn, conn.cursor() as cur:
        cur.execute("DELETE FROM fields WHERE id = %s", (field_id,))
    conn.close()


VALID_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [24.80, -33.75],
            [24.81, -33.75],
            [24.81, -33.76],
            [24.80, -33.76],
            [24.80, -33.75],
        ]
    ],
}


def _demo_field_ids():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    with conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM fields WHERE is_demo_field = true ORDER BY id")
        ids = [r["id"] for r in cur.fetchall()]
    conn.close()
    return ids


# --- Owner token enforcement --------------------------------------------


def test_protected_endpoint_without_token_returns_401():
    """No X-Owner-Token header must be a 401, not a 422 or a silent success."""
    for method, url in [
        ("get", "/api/fields"),
        ("get", "/api/fields/1"),
        ("get", "/api/fields/1/readings"),
        ("get", "/api/fields/1/risk"),
        ("get", "/api/fields/1/alerts"),
        ("get", "/api/fields/1/photos"),
    ]:
        response = getattr(client, method)(url)
        assert response.status_code == 401, url
        assert response.json()["detail"] == "Invalid or missing owner token", url


def test_protected_endpoint_with_unknown_token_returns_401():
    response = client.get("/api/fields", headers={"X-Owner-Token": "not-a-real-token"})
    assert response.status_code == 401


def test_token_cannot_read_another_owners_field(test_field, owner_headers, owner):
    """
    A valid token for owner A must not reach owner B's field by guessing or
    incrementing the field_id in the URL.
    """
    assert client.get(f"/api/fields/{test_field}", headers=owner_headers).status_code == 200

    # `owner` is a different, freshly registered owner with a valid token.
    assert client.get(f"/api/fields/{test_field}", headers=owner["headers"]).status_code == 403
    assert client.get(f"/api/fields/{test_field}/readings", headers=owner["headers"]).status_code == 403
    assert client.get(f"/api/fields/{test_field}/photos", headers=owner["headers"]).status_code == 403


def test_token_cannot_write_to_another_owners_field(test_field, owner):
    """Owner B must not be able to attach feedback to owner A's field."""
    res = client.post(
        "/api/feedback",
        headers=owner["headers"],
        json={"field_id": test_field, "was_accurate": True, "farmer_comment": "not mine"},
    )
    assert res.status_code == 403


def test_any_valid_token_can_read_the_seeded_demo_fields(owner):
    """
    Demo fields stay readable by every valid token so the 3 seeded fields keep
    working for any judge/tester without registering field data of their own.
    """
    demo_ids = _demo_field_ids()
    assert len(demo_ids) == 3, "expected the 3 seeded demo fields"

    listed = client.get("/api/fields", headers=owner["headers"])
    assert listed.status_code == 200
    listed_ids = {f["id"] for f in listed.json()}
    assert set(demo_ids).issubset(listed_ids)

    for field_id in demo_ids:
        assert client.get(f"/api/fields/{field_id}", headers=owner["headers"]).status_code == 200
        assert client.get(f"/api/fields/{field_id}/readings", headers=owner["headers"]).status_code == 200
        assert client.get(f"/api/fields/{field_id}/photos", headers=owner["headers"]).status_code == 200


def test_demo_fields_visible_to_two_different_tokens():
    """Demo readability must not depend on which owner is asking."""
    first = client.post("/api/owners/register", json={"owner_id": f"demo_visor_{uuid.uuid4().hex[:10]}"})
    second = client.post("/api/owners/register", json={"owner_id": f"demo_visor_{uuid.uuid4().hex[:10]}"})
    assert first.status_code == 201 and second.status_code == 201
    h1 = {"X-Owner-Token": first.json()["token"]}
    h2 = {"X-Owner-Token": second.json()["token"]}

    demo_ids = set(_demo_field_ids())
    try:
        a = {f["id"] for f in client.get("/api/fields", headers=h1).json()}
        b = {f["id"] for f in client.get("/api/fields", headers=h2).json()}
        assert demo_ids.issubset(a)
        assert demo_ids.issubset(b)
    finally:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        with conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM owner_tokens WHERE owner_id LIKE 'demo_visor_%'"
            )
        conn.close()


def test_register_issues_a_token_once_per_owner():
    owner_id = f"register_once_{uuid.uuid4().hex[:10]}"
    try:
        first = client.post("/api/owners/register", json={"owner_id": owner_id})
        assert first.status_code == 201
        token = first.json()["token"]
        assert first.json()["owner_id"] == owner_id
        assert len(token) >= 32

        # Re-registering must not mint a second token for the same owner.
        second = client.post("/api/owners/register", json={"owner_id": owner_id})
        assert second.status_code == 409

        # ...and the original token still works.
        assert client.get("/api/fields", headers={"X-Owner-Token": token}).status_code == 200
    finally:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        with conn, conn.cursor() as cur:
            cur.execute("DELETE FROM owner_tokens WHERE owner_id = %s", (owner_id,))
        conn.close()


def test_create_field_takes_owner_id_from_token_not_payload(owner):
    """A spoofed owner_id in the body must be ignored in favour of the token's."""
    res = client.post(
        "/api/fields",
        headers=owner["headers"],
        json={
            "name": "Spoof Attempt",
            "owner_id": "somebody_else",
            "boundary_geojson": VALID_POLYGON,
        },
    )
    assert res.status_code == 201
    field_id = res.json()["id"]
    try:
        assert res.json()["owner_id"] == owner["owner_id"]
        assert res.json()["owner_id"] != "somebody_else"
    finally:
        _delete_field(field_id)


def test_list_fields_rejects_client_supplied_owner_id_query_param(owner):
    """
    The owner filter is derived from the token only. Rather than silently
    ignoring a client-supplied owner_id, it is rejected so it is unambiguous
    which value would have been used.
    """
    res = client.get("/api/fields?owner_id=somebody_else", headers=owner["headers"])
    assert res.status_code == 400
    assert "X-Owner-Token" in res.json()["detail"]


def test_list_fields_shows_only_own_fields_plus_demo_fields(owner):
    """A brand-new owner sees the demo fields and nothing else."""
    listed = client.get("/api/fields", headers=owner["headers"]).json()
    assert {f["id"] for f in listed} == set(_demo_field_ids())

    created = client.post(
        "/api/fields",
        headers=owner["headers"],
        json={"name": "Scoped Field", "boundary_geojson": VALID_POLYGON},
    )
    field_id = created.json()["id"]
    try:
        listed = client.get("/api/fields", headers=owner["headers"]).json()
        ids = {f["id"] for f in listed}
        assert field_id in ids
        assert set(_demo_field_ids()).issubset(ids)
        # No other owner's non-demo field leaks in.
        assert all(f["owner_id"] in (owner["owner_id"], "demo") for f in listed)
    finally:
        _delete_field(field_id)


# --- Existing endpoint tests (now owner-token scoped) --------------------


def test_list_fields_includes_seeded_demo_fields(owner):
    response = client.get("/api/fields", headers=owner["headers"])
    assert response.status_code == 200
    names = [f["name"] for f in response.json()]
    assert "Patensie Citrus Block — Gamtoos Valley" in names
    assert "Hankey Vegetable Field — Gamtoos Valley" in names
    assert "Kirkwood Citrus Block — Sundays River Valley" in names


def test_get_field_detail(test_field, owner_headers):
    response = client.get(f"/api/fields/{test_field}", headers=owner_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == test_field
    assert body["boundary"]["type"] == "Polygon"
    assert "created_at" in body


def test_get_field_404_for_unknown_id(owner):
    response = client.get("/api/fields/999999", headers=owner["headers"])
    assert response.status_code == 404


def test_readings_endpoint_merges_weather_and_ndvi_by_date(test_field, owner_headers, monkeypatch):
    fake_weather = [
        DailyWeather(date=dt.date(2026, 9, 20), rainfall_mm=5.0, temp_c=22.0, source="open_meteo"),
        DailyWeather(date=dt.date(2026, 9, 21), rainfall_mm=0.0, temp_c=24.0, source="open_meteo"),
    ]
    fake_ndvi = [
        NdviReading(date=dt.date(2026, 9, 20), ndvi_mean=0.55, sample_count=800),
        NdviReading(date=dt.date(2026, 9, 21), ndvi_mean=0.50, sample_count=800),
    ]
    monkeypatch.setattr(weather_service, "get_recent_weather", lambda *a, **k: fake_weather)
    monkeypatch.setattr(weather_service, "get_forecast_rainfall", lambda *a, **k: 5.0)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", lambda *a, **k: fake_ndvi)

    response = client.get(f"/api/fields/{test_field}/readings", headers=owner_headers)
    assert response.status_code == 200
    body = response.json()
    dates = {r["date"] for r in body}
    assert {"2026-09-20", "2026-09-21"}.issubset(dates)

    day1 = next(r for r in body if r["date"] == "2026-09-20")
    assert day1["ndvi"] == 0.55
    assert day1["rainfall_mm"] == 5.0
    assert day1["temp_c"] == 22.0


def test_risk_endpoint_flags_declining_field(test_field, owner_headers, monkeypatch):
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
    monkeypatch.setattr(weather_service, "get_forecast_rainfall", lambda *a, **k: 5.0)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", lambda *a, **k: fake_ndvi)

    response = client.get(f"/api/fields/{test_field}/risk", headers=owner_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["score"] in ("Medium", "High")
    assert body["reasons"]
    assert "irrigation" in body["recommended_check"].lower()


def test_risk_endpoint_healthy_field_is_low(test_field, owner_headers, monkeypatch):
    fake_weather = [
        DailyWeather(date=dt.date(2026, 9, 18), rainfall_mm=18.0, temp_c=21.0, source="open_meteo"),
        DailyWeather(date=dt.date(2026, 9, 19), rainfall_mm=19.0, temp_c=21.2, source="open_meteo"),
    ]
    fake_ndvi = [
        NdviReading(date=dt.date(2026, 9, 18), ndvi_mean=0.58, sample_count=800),
        NdviReading(date=dt.date(2026, 9, 19), ndvi_mean=0.60, sample_count=800),
    ]
    monkeypatch.setattr(weather_service, "get_recent_weather", lambda *a, **k: fake_weather)
    monkeypatch.setattr(weather_service, "get_forecast_rainfall", lambda *a, **k: 5.0)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", lambda *a, **k: fake_ndvi)

    response = client.get(f"/api/fields/{test_field}/risk", headers=owner_headers)
    assert response.status_code == 200
    assert response.json()["score"] == "Low"


def test_alerts_message_matches_current_risk_score(test_field, owner_headers, monkeypatch):
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
    monkeypatch.setattr(weather_service, "get_forecast_rainfall", lambda *a, **k: 5.0)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", lambda *a, **k: fake_ndvi)

    risk_score = client.get(f"/api/fields/{test_field}/risk", headers=owner_headers).json()["score"]
    alerts = client.get(f"/api/fields/{test_field}/alerts", headers=owner_headers).json()

    assert risk_score in ("Medium", "High")  # sanity check this scenario actually flags
    assert len(alerts) >= 1
    assert risk_score in alerts[0]["message"]


def test_readings_fall_back_to_cache_when_both_external_services_fail(test_field, owner_headers, monkeypatch):
    # First call: both services succeed, data gets cached.
    fake_weather = [DailyWeather(date=dt.date(2026, 9, 22), rainfall_mm=1.0, temp_c=26.0, source="open_meteo")]
    fake_ndvi = [NdviReading(date=dt.date(2026, 9, 22), ndvi_mean=0.4, sample_count=800)]
    monkeypatch.setattr(weather_service, "get_recent_weather", lambda *a, **k: fake_weather)
    monkeypatch.setattr(weather_service, "get_forecast_rainfall", lambda *a, **k: 5.0)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", lambda *a, **k: fake_ndvi)

    first = client.get(f"/api/fields/{test_field}/readings", headers=owner_headers)
    assert first.status_code == 200
    assert len(first.json()) == 1

    # Second call: simulate both live services being down. Endpoint must
    # NOT error — it should serve the cached reading from the first call.
    def raise_error(*args, **kwargs):
        raise Exception("simulated external API outage")

    monkeypatch.setattr(weather_service, "get_recent_weather", raise_error)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", raise_error)

    second = client.get(f"/api/fields/{test_field}/readings", headers=owner_headers)
    assert second.status_code == 200
    assert len(second.json()) == 1
    assert second.json()[0]["ndvi"] == 0.4  # cached value, not lost


def test_photo_upload_endpoint_accepts_image_and_marks_pending_review(test_field, owner_headers):
    response = client.post(
        f"/api/fields/{test_field}/photos",
        headers=owner_headers,
        files={"file": ("ground-truth.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["field_id"] == test_field
    assert body["status"] == "pending_review"
    assert body["filename"].endswith(".jpg")
    assert body["stored_path"]
    assert "diagnosis" in body
    assert body["diagnosis"]["category"]


def test_photo_upload_disease_detection(test_field, owner_headers):
    response = client.post(
        f"/api/fields/{test_field}/photos",
        headers=owner_headers,
        files={"file": ("diseased_leaf_spot.jpg", b"fake-diseased-image", "image/jpeg")},
    )
    assert response.status_code == 200
    diag = response.json().get("diagnosis")
    assert diag is not None
    assert "Fungal" in diag["category"] or "Spot" in diag["category"]
    assert diag["confidence"] > 0.7
    assert diag["description"]

    # Verify risk endpoint surfaces this photo_diagnosis separately
    risk_res = client.get(f"/api/fields/{test_field}/risk", headers=owner_headers)
    assert risk_res.status_code == 200
    risk_body = risk_res.json()
    assert "photo_diagnosis" in risk_body
    assert risk_body["photo_diagnosis"]["category"] == diag["category"]

    # Verify diagnoses listing endpoint
    diag_list_res = client.get(f"/api/fields/{test_field}/photos/diagnoses", headers=owner_headers)
    assert diag_list_res.status_code == 200
    assert len(diag_list_res.json()) >= 1


def test_photo_upload_healthy_foliage_detection(test_field, owner_headers):
    response = client.post(
        f"/api/fields/{test_field}/photos",
        headers=owner_headers,
        files={"file": ("healthy_crop_field.jpg", b"fake-healthy-image", "image/jpeg")},
    )
    assert response.status_code == 200
    diag = response.json().get("diagnosis")
    assert diag is not None
    assert diag["category"] == "Healthy Foliage"
    assert "No obvious visual signs" in diag["description"]



def test_create_field_success_and_immediate_risk(owner):
    payload = {
        "name": "New Farmer Field — Ceres Apple Farm",
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [
                [
                    [19.31, -33.36],
                    [19.32, -33.36],
                    [19.32, -33.37],
                    [19.31, -33.37],
                    [19.31, -33.36],
                ]
            ],
        },
    }
    res = client.post("/api/fields", headers=owner["headers"], json=payload)
    assert res.status_code == 201
    data = res.json()
    field_id = data["id"]
    assert data["name"] == "New Farmer Field — Ceres Apple Farm"
    # Ownership is assigned from the token, not from anything the client sends.
    assert data["owner_id"] == owner["owner_id"]

    try:
        # Verify risk endpoint returns immediate score for newly created field
        risk_res = client.get(f"/api/fields/{field_id}/risk", headers=owner["headers"])
        assert risk_res.status_code == 200
        assert risk_res.json()["score"] in ("Low", "Medium", "High")
    finally:
        _delete_field(field_id)



def test_create_field_requires_token():
    payload = {"name": "No Token Field", "boundary_geojson": VALID_POLYGON}
    res = client.post("/api/fields", json=payload)
    assert res.status_code == 401


def test_create_field_rejects_outside_south_africa(owner):
    payload = {
        "name": "Field in Europe",
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [
                [
                    [10.0, 50.0],
                    [10.1, 50.0],
                    [10.1, 50.1],
                    [10.0, 50.1],
                    [10.0, 50.0],
                ]
            ],
        },
    }
    res = client.post("/api/fields", headers=owner["headers"], json=payload)
    assert res.status_code == 400
    assert "within South Africa" in res.json()["detail"]


def test_create_field_rejects_self_intersecting_polygon(owner):
    payload = {
        "name": "Bowtie Polygon",
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [
                [
                    [24.80, -33.75],
                    [24.81, -33.76],
                    [24.81, -33.75],
                    [24.80, -33.76],
                    [24.80, -33.75],
                ]
            ],
        },
    }
    res = client.post("/api/fields", headers=owner["headers"], json=payload)
    assert res.status_code == 400
    assert "Self-intersecting" in res.json()["detail"] or "invalid" in res.json()["detail"]


def test_list_fields_scoped_to_token_owner(owner):
    """
    Ownership scoping: a field created with one owner's token must not appear in
    another owner's field list (demo fields are intentionally shared).
    """
    create_res = client.post(
        "/api/fields",
        headers=owner["headers"],
        json={"name": "Owner Scoped Field", "boundary_geojson": VALID_POLYGON},
    )
    assert create_res.status_code == 201
    field_id = create_res.json()["id"]

    try:
        mine = client.get("/api/fields", headers=owner["headers"]).json()
        assert [f["id"] for f in mine].count(field_id) == 1

        # A second, unrelated owner must not see it.
        other_id = f"other_owner_{uuid.uuid4().hex[:10]}"
        other = client.post("/api/owners/register", json={"owner_id": other_id})
        assert other.status_code == 201
        other_headers = {"X-Owner-Token": other.json()["token"]}
        try:
            theirs = client.get("/api/fields", headers=other_headers).json()
            assert field_id not in [f["id"] for f in theirs]
        finally:
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            with conn, conn.cursor() as cur:
                cur.execute("DELETE FROM owner_tokens WHERE owner_id = %s", (other_id,))
            conn.close()
    finally:
        _delete_field(field_id)


def test_submit_farmer_feedback(test_field, owner_headers):
    payload = {
        "field_id": test_field,
        "was_accurate": True,
        "farmer_comment": "Water stress indication was accurate on the east block.",
    }
    res = client.post("/api/feedback", headers=owner_headers, json=payload)
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "saved"
    assert "id" in body


def test_validation_stats_reports_not_enough_data_yet():
    # Clean table for controlled test
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    with conn, conn.cursor() as cur:
        cur.execute("DELETE FROM farmer_feedback")
    conn.close()

    res = client.get("/validation-stats")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "not_enough_data"
    assert "not enough data yet" in data["message"].lower()
    assert data["response_count"] < 20


def test_validation_stats_reports_percentage_when_threshold_reached(test_field):
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    with conn, conn.cursor() as cur:
        cur.execute("DELETE FROM farmer_feedback")
        for i in range(25):
            accurate = i < 20  # 20 accurate out of 25 -> 80.0%
            cur.execute(
                """
                INSERT INTO farmer_feedback (field_id, was_accurate, farmer_comment)
                VALUES (%s, %s, %s)
                """,
                (test_field, accurate, f"Feedback #{i}"),
            )
    conn.close()

    try:
        res = client.get("/validation-stats")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "validated"
        assert data["response_count"] == 25
        assert data["agreement_rate"] == 80.0
        assert "80" in data["message"]
    finally:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        with conn, conn.cursor() as cur:
            cur.execute("DELETE FROM farmer_feedback")
        conn.close()


def test_whatsapp_alert_generation_creates_audio(test_field, owner_headers, monkeypatch):
    fake_weather = [
        DailyWeather(date=dt.date(2026, 9, 21), rainfall_mm=20.0, temp_c=21.0, source="open_meteo"),
        DailyWeather(date=dt.date(2026, 9, 22), rainfall_mm=1.0, temp_c=28.0, source="open_meteo"),
    ]
    fake_ndvi = [
        NdviReading(date=dt.date(2026, 9, 21), ndvi_mean=0.60, sample_count=800),
        NdviReading(date=dt.date(2026, 9, 22), ndvi_mean=0.40, sample_count=800),
    ]
    monkeypatch.setattr(weather_service, "get_recent_weather", lambda *a, **k: fake_weather)
    monkeypatch.setattr(weather_service, "get_forecast_rainfall", lambda *a, **k: 5.0)
    monkeypatch.setattr(satellite_service, "get_ndvi_time_series", lambda *a, **k: fake_ndvi)

    res = client.get(f"/api/fields/{test_field}/alerts", headers=owner_headers)
    assert res.status_code == 200
    alerts = res.json()
    assert len(alerts) >= 1
    first = alerts[0]
    assert first["channel"] == "whatsapp"
    assert "audio_url" in first
    assert first["audio_url"].endswith(".mp3")




