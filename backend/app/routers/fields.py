"""
app/routers/fields.py

Exposes the 5 contract endpoints from planning.md:
    GET /api/fields
    GET /api/fields/{id}
    GET /api/fields/{id}/readings
    GET /api/fields/{id}/risk
    GET /api/fields/{id}/alerts

Caching behaviour (per planning.md "Response caching"): each request for
readings/risk/alerts first tries to refresh from the live weather + satellite
services and caches whatever comes back into the `readings` table. If BOTH
live services fail (rate limit, outage, offline demo venue), the endpoint
does not error — it falls back to whatever is already cached, per the
"fall back to the last cached reading rather than showing an error screen"
requirement.
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException

from app.db import get_connection
from app.services import satellite as satellite_service
from app.services import weather as weather_service
from app.services.risk_engine import assess_field_risk

router = APIRouter(prefix="/api/fields", tags=["fields"])

READING_LOOKBACK_DAYS = 14
ALERT_HISTORY_LIMIT = 5


def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


# --- Endpoints ---------------------------------------------------------


@router.get("")
def list_fields(db=Depends(get_db)):
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, name, ST_AsGeoJSON(boundary)::json AS boundary FROM fields ORDER BY id"
        )
        rows = cur.fetchall()
    return [{"id": r["id"], "name": r["name"], "boundary": r["boundary"]} for r in rows]


@router.get("/{field_id}")
def get_field(field_id: int, db=Depends(get_db)):
    field = _get_field_or_404(field_id, db)
    return {
        "id": field["id"],
        "name": field["name"],
        "boundary": field["boundary_geojson"],
        "created_at": field["created_at"].isoformat(),
    }


@router.get("/{field_id}/readings")
def get_readings(field_id: int, db=Depends(get_db)):
    field = _get_field_or_404(field_id, db)
    _sync_readings(field, db)
    return _fetch_merged_readings(field_id, db)


@router.get("/{field_id}/risk")
def get_risk(field_id: int, db=Depends(get_db)):
    field = _get_field_or_404(field_id, db)
    _sync_readings(field, db)
    assessment = _compute_and_cache_risk(field_id, db)
    return {
        "score": assessment.score.value,
        "reasons": assessment.reasons,
        "recommended_check": assessment.recommended_check,
    }


@router.get("/{field_id}/alerts")
def get_alerts(field_id: int, db=Depends(get_db)):
    field = _get_field_or_404(field_id, db)
    _sync_readings(field, db)
    assessment = _compute_and_cache_risk(field_id, db)
    message = _build_alert_message(field["name"], assessment)

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO alerts (field_id, message, channel)
            VALUES (%s, %s, %s)
            """,
            (field_id, message, "whatsapp"),
        )
    db.commit()

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT message, sent_at, channel FROM alerts
            WHERE field_id = %s ORDER BY sent_at DESC LIMIT %s
            """,
            (field_id, ALERT_HISTORY_LIMIT),
        )
        rows = cur.fetchall()

    return [
        {"message": r["message"], "created_at": r["sent_at"].isoformat(), "channel": r["channel"]}
        for r in rows
    ]


# --- Internals -----------------------------------------------------------


def _get_field_or_404(field_id: int, db) -> dict:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, created_at,
                   ST_AsGeoJSON(boundary)::json AS boundary_geojson,
                   ST_Y(ST_Centroid(boundary)) AS lat,
                   ST_X(ST_Centroid(boundary)) AS lon
            FROM fields WHERE id = %s
            """,
            (field_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Field not found")
    return row


def _sync_readings(field: dict, db, days: int = READING_LOOKBACK_DAYS) -> None:
    """
    Best-effort refresh from live services, caching into `readings`. Never
    raises — a failure here just means the endpoint serves whatever's
    already cached, per the "fall back to cached data" requirement.
    """
    end = dt.date.today()
    start = end - dt.timedelta(days=days)

    weather_readings = []
    try:
        weather_readings = weather_service.get_recent_weather(field["lat"], field["lon"], days=days)
    except Exception:
        pass  # live weather unavailable this request — cached data still applies

    ndvi_readings = []
    try:
        ndvi_readings = satellite_service.get_ndvi_time_series(
            field["boundary_geojson"], start, end
        )
    except Exception:
        pass  # live satellite unavailable this request (e.g. no credentials yet)

    if not weather_readings and not ndvi_readings:
        return

    with db.cursor() as cur:
        for w in weather_readings:
            cur.execute(
                """
                INSERT INTO readings (field_id, date, rainfall_mm, temp_c, source)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (field_id, date, source) DO UPDATE SET
                    rainfall_mm = EXCLUDED.rainfall_mm,
                    temp_c = EXCLUDED.temp_c
                """,
                (field["id"], w.date, w.rainfall_mm, w.temp_c, w.source),
            )
        for n in ndvi_readings:
            cur.execute(
                """
                INSERT INTO readings (field_id, date, ndvi_value, source)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (field_id, date, source) DO UPDATE SET
                    ndvi_value = EXCLUDED.ndvi_value
                """,
                (field["id"], n.date, n.ndvi_mean, "sentinel_hub"),
            )
    db.commit()


def _fetch_merged_readings(field_id: int, db) -> list[dict]:
    """
    NDVI and weather are cached as separate rows (different sources) per
    planning.md's schema. Merge them per-date for the trend chart / risk
    engine — MAX() is safe here since each source only ever populates its
    own columns, leaving the others NULL.
    """
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT date,
                   MAX(ndvi_value) AS ndvi_value,
                   MAX(rainfall_mm) AS rainfall_mm,
                   MAX(temp_c) AS temp_c
            FROM readings
            WHERE field_id = %s
            GROUP BY date
            ORDER BY date
            """,
            (field_id,),
        )
        rows = cur.fetchall()

    return [
        {
            "date": r["date"].isoformat(),
            "ndvi": float(r["ndvi_value"]) if r["ndvi_value"] is not None else None,
            "rainfall_mm": float(r["rainfall_mm"]) if r["rainfall_mm"] is not None else None,
            "temp_c": float(r["temp_c"]) if r["temp_c"] is not None else None,
        }
        for r in rows
    ]


def _compute_and_cache_risk(field_id: int, db):
    merged = _fetch_merged_readings(field_id, db)
    ndvi = [r["ndvi"] for r in merged]
    rainfall = [r["rainfall_mm"] for r in merged]
    temp = [r["temp_c"] for r in merged]

    assessment = assess_field_risk(ndvi, rainfall, temp)

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO risk_scores (field_id, date, score, reason_summary)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (field_id, date) DO UPDATE SET
                score = EXCLUDED.score,
                reason_summary = EXCLUDED.reason_summary
            """,
            (field_id, dt.date.today(), assessment.score.value, "; ".join(assessment.reasons)),
        )
    db.commit()

    return assessment


def _build_alert_message(field_name: str, assessment) -> str:
    if assessment.score.value == "Low":
        return f"{field_name}: conditions normal, no action needed."
    reasons_text = "; ".join(assessment.reasons)
    return (
        f"{field_name}: {assessment.score.value} risk — {reasons_text}. "
        f"{assessment.recommended_check}."
    )
