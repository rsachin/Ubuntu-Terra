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
import os
import secrets
import uuid
from pathlib import Path

import json
from pydantic import BaseModel

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, Response, UploadFile

from app.db import get_connection
from app.services import satellite as satellite_service
from app.services import weather as weather_service
from app.services.pest_vision import analyze_crop_photo
from app.services.risk_engine import assess_field_risk
from app.services.whatsapp_service import send_whatsapp_alert_and_voice
from app.services.whatsapp_voice import build_spoken_alert_message, generate_spoken_audio

router = APIRouter(prefix="/api/fields", tags=["fields"])

READING_LOOKBACK_DAYS = 14
ALERT_HISTORY_LIMIT = 5
PHOTO_UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"


class FieldCreate(BaseModel):
    name: str
    boundary_geojson: dict
    # Accepted for backwards compatibility with the existing client contract, but
    # IGNORED: ownership is taken from the X-Owner-Token, never from the payload.
    owner_id: str | None = None


class OwnerRegister(BaseModel):
    owner_id: str


class FeedbackCreate(BaseModel):
    field_id: int
    risk_score_id: int | None = None
    photo_diagnosis_id: int | None = None
    was_accurate: bool
    farmer_comment: str | None = None


def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


# --- Owner tokens --------------------------------------------------------
#
# SECURITY SCOPE — read before treating this as real authentication.
# This is deliberately NOT a full authentication system. There are no passwords,
# no login/session lifecycle, no token expiry and no rotation: an owner_id maps
# to exactly one long-lived opaque token that never changes. It exists only to
# close the trivial "just type someone else's owner_id string" gap.
# A production version would need, at minimum:
#   * password-based login (or a real identity provider) to obtain a token,
#   * token expiry + rotation/revocation so a leaked token stops working,
#   * rate limiting on /api/owners/register to stop owner_id enumeration/abuse,
#   * hashing tokens at rest, and transport-only (HTTPS) enforcement.

owners_router = APIRouter(prefix="/api/owners", tags=["owners"])


@owners_router.post("/register", status_code=201)
def register_owner(payload: OwnerRegister, db=Depends(get_db)):
    """
    Issue an opaque access token for a new owner_id (the demo's "sign up" step).

    This is the only unauthenticated endpoint in the owner-token flow — it is how
    a brand-new demo farmer obtains their token for the first time. Registering an
    owner_id that already has a token returns 409 rather than minting a second
    token, which would defeat the point of having one token per owner.
    """
    owner_id = payload.owner_id.strip()
    if not owner_id:
        raise HTTPException(status_code=400, detail="owner_id cannot be empty")

    with db.cursor() as cur:
        cur.execute(
            "SELECT token FROM owner_tokens WHERE owner_id = %s", (owner_id,)
        )
        if cur.fetchone():
            raise HTTPException(
                status_code=409,
                detail="This owner_id already has a token; it cannot be re-issued",
            )

        token = secrets.token_urlsafe(32)
        cur.execute(
            """
            INSERT INTO owner_tokens (token, owner_id)
            VALUES (%s, %s)
            RETURNING token, created_at
            """,
            (token, owner_id),
        )
        row = cur.fetchone()
    db.commit()

    return {
        "owner_id": owner_id,
        "token": row["token"],
        "created_at": row["created_at"].isoformat(),
    }


def require_owner_token(x_owner_token: str = Header(default=""), db=Depends(get_db)) -> str:
    """
    Resolve the caller's owner_id from their opaque X-Owner-Token.

    Returns the owner_id to scope queries by. Endpoints must use this returned
    value as the ownership filter and must NOT trust an owner_id supplied by the
    client. See the SECURITY SCOPE note above: no expiry, no rotation.

    The header defaults to empty rather than being a required parameter so that a
    *missing* token is answered with a 401 (as a bad token is) instead of
    FastAPI's 422 request-validation error.
    """
    if not x_owner_token:
        raise HTTPException(
            status_code=401, detail="Invalid or missing owner token"
        )
    with db.cursor() as cur:
        cur.execute(
            "SELECT owner_id FROM owner_tokens WHERE token = %s", (x_owner_token,)
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=401, detail="Invalid or missing owner token"
        )
    return row["owner_id"]


# --- Endpoints ---------------------------------------------------------


@router.get("")
def list_fields(
    owner_id: str | None = None,
    db=Depends(get_db),
    token_owner_id: str = Depends(require_owner_token),
):
    """
    List the caller's own fields plus the shared demo fields.

    The owner filter comes from the X-Owner-Token only. A client-supplied
    owner_id query param is rejected rather than ignored, so nobody is left
    guessing which of the two values won.
    """
    if owner_id is not None:
        raise HTTPException(
            status_code=400,
            detail="owner_id is derived from your X-Owner-Token and cannot be supplied as a query parameter",
        )

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, owner_id, is_demo_field, ST_AsGeoJSON(boundary)::json AS boundary
            FROM fields
            WHERE owner_id = %s OR is_demo_field = true
            ORDER BY id
            """,
            (token_owner_id,),
        )
        rows = cur.fetchall()
    return [
        {"id": r["id"], "name": r["name"], "owner_id": r["owner_id"], "is_demo_field": r["is_demo_field"], "boundary": r["boundary"]}
        for r in rows
    ]


@router.post("", status_code=201)
def create_field(
    payload: FieldCreate,
    db=Depends(get_db),
    token_owner_id: str = Depends(require_owner_token),
):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Field name cannot be empty")

    geojson = payload.boundary_geojson
    if isinstance(geojson, dict) and geojson.get("type") == "Feature":
        geojson = geojson.get("geometry", {})

    if not isinstance(geojson, dict) or geojson.get("type") != "Polygon":
        raise HTTPException(status_code=400, detail="Boundary must be a valid GeoJSON Polygon")

    coords = geojson.get("coordinates")
    if not coords or not isinstance(coords, list) or len(coords) == 0:
        raise HTTPException(status_code=400, detail="Polygon coordinates are required")

    outer_ring = coords[0]
    if not isinstance(outer_ring, list) or len(outer_ring) < 3:
        raise HTTPException(status_code=400, detail="Polygon ring must contain at least 3 vertices")

    # Close ring if first and last point are not identical
    if outer_ring[0] != outer_ring[-1]:
        outer_ring = list(outer_ring) + [outer_ring[0]]
        coords[0] = outer_ring
        geojson["coordinates"] = coords

    # Check bounds within South Africa approx: lon 16 to 33, lat -35 to -22
    for pt in outer_ring:
        if not (isinstance(pt, (list, tuple)) and len(pt) >= 2):
            raise HTTPException(status_code=400, detail="Invalid vertex coordinate format")
        lon, lat = float(pt[0]), float(pt[1])
        if not (16.0 <= lon <= 33.0 and -35.0 <= lat <= -22.0):
            raise HTTPException(
                status_code=400,
                detail=f"Field coordinates ({lon:.2f}, {lat:.2f}) must be within South Africa (longitude 16°E-33°E, latitude 22°S-35°S).",
            )

    geojson_str = json.dumps(geojson)

    # Validate PostGIS polygon validity & area bounds
    with db.cursor() as cur:
        try:
            cur.execute(
                """
                SELECT 
                    ST_IsValid(ST_GeomFromGeoJSON(%s)) AS is_valid,
                    ST_IsValidReason(ST_GeomFromGeoJSON(%s)) AS invalid_reason,
                    ST_Area(ST_GeomFromGeoJSON(%s)::geography) AS area_m2
                """,
                (geojson_str, geojson_str, geojson_str),
            )
            val_row = cur.fetchone()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid geometry: {str(e)}")

        if not val_row["is_valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Self-intersecting or invalid polygon boundary: {val_row['invalid_reason']}",
            )

        area_m2 = float(val_row["area_m2"]) if val_row["area_m2"] is not None else 0.0
        if area_m2 < 100:  # < 0.01 hectares (100 m²)
            raise HTTPException(
                status_code=400,
                detail="Field area is too small (minimum 0.01 hectares / 100 m²).",
            )
        if area_m2 > 500_000_000:  # > 50,000 hectares
            raise HTTPException(
                status_code=400,
                detail="Field area is too large (maximum 50,000 hectares).",
            )

        cur.execute(
            """
            INSERT INTO fields (name, owner_id, boundary)
            VALUES (%s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
            RETURNING id, name, owner_id, is_demo_field, ST_AsGeoJSON(boundary)::json AS boundary_geojson, created_at,
                      ST_Y(ST_Centroid(boundary)) AS lat, ST_X(ST_Centroid(boundary)) AS lon
            """,
            (name, token_owner_id, geojson_str),
        )
        row = cur.fetchone()
    db.commit()

    field_dict = {
        "id": row["id"],
        "name": row["name"],
        "owner_id": row["owner_id"],
        "is_demo_field": row["is_demo_field"],
        "boundary_geojson": row["boundary_geojson"],
        "created_at": row["created_at"],
        "lat": float(row["lat"]),
        "lon": float(row["lon"]),
    }

    # Immediately sync readings and compute risk for newly created field
    _sync_readings(field_dict, db)
    _compute_and_cache_risk(row["id"], db)

    return {
        "id": row["id"],
        "name": row["name"],
        "owner_id": row["owner_id"],
        "boundary": row["boundary_geojson"],
        "created_at": row["created_at"].isoformat(),
    }


@router.get("/{field_id}")
def get_field(field_id: int, db=Depends(get_db), token_owner_id: str = Depends(require_owner_token)):
    field = _get_accessible_field_or_403(field_id, db, token_owner_id)
    return {
        "id": field["id"],
        "name": field["name"],
        "is_demo_field": field.get("is_demo_field", False),
        "boundary": field["boundary_geojson"],
        "created_at": field["created_at"].isoformat(),
    }


@router.get("/{field_id}/readings")
def get_readings(field_id: int, db=Depends(get_db), token_owner_id: str = Depends(require_owner_token)):
    field = _get_accessible_field_or_403(field_id, db, token_owner_id)
    _sync_readings(field, db)
    return _fetch_merged_readings(field_id, db)


@router.get("/{field_id}/risk")
def get_risk(field_id: int, db=Depends(get_db), token_owner_id: str = Depends(require_owner_token)):
    field = _get_accessible_field_or_403(field_id, db, token_owner_id)
    _sync_readings(field, db)
    assessment = _compute_and_cache_risk(field_id, db)
    latest_diagnosis = _get_latest_photo_diagnosis(field_id, db)
    
    with db.cursor() as cur:
        cur.execute("SELECT bool_or(source = 'demo_trigger') AS is_demo FROM readings WHERE field_id = %s", (field_id,))
        r = cur.fetchone()
        is_demo_data = r["is_demo"] if r and r["is_demo"] is not None else False
        
    return {
        "score": assessment.score.value,
        "reasons": assessment.reasons,
        "recommended_check": assessment.recommended_check,
        "photo_diagnosis": latest_diagnosis,
        "is_demo_data": is_demo_data,
    }


@router.get("/{field_id}/alerts")
def get_alerts(field_id: int, db=Depends(get_db), token_owner_id: str = Depends(require_owner_token)):
    field = _get_accessible_field_or_403(field_id, db, token_owner_id)
    _sync_readings(field, db)
    assessment = _compute_and_cache_risk(field_id, db)
    message = _build_alert_message(field["name"], assessment)

    # Generate spoken voice note MP3 audio for WhatsApp delivery (Phase 4)
    spoken_text = build_spoken_alert_message(field["name"], assessment.score.value, assessment.reasons)
    audio_url = generate_spoken_audio(spoken_text, lang="en")

    # Dispatch WhatsApp text + voice note via Twilio Sandbox API
    wa_result = send_whatsapp_alert_and_voice(
        to_number=None,
        message_text=message,
        audio_url=audio_url,
    )

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO alerts (field_id, message, channel, status, provider_message_id, provider_error)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                field_id,
                message,
                "whatsapp",
                wa_result.get("status"),
                wa_result.get("sid") or wa_result.get("voice_sid"),
                wa_result.get("error"),
            ),
        )
    db.commit()

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT message, sent_at, channel, status, provider_message_id, provider_error
            FROM alerts
            WHERE field_id = %s ORDER BY sent_at DESC LIMIT %s
            """,
            (field_id, ALERT_HISTORY_LIMIT),
        )
        rows = cur.fetchall()

    return [
        {
            "message": r["message"],
            "created_at": r["sent_at"].isoformat(),
            "channel": r["channel"],
            "status": r["status"],
            "provider_message_id": r["provider_message_id"],
            "provider_error": r["provider_error"],
            "audio_url": audio_url,
            "whatsapp_status": r["status"],
        }
        for r in rows
    ]


async def whatsapp_webhook(request: Request, db):
    """
    Lightweight WhatsApp reply handler for incoming farmer messages (Twilio Webhook).
    Replies with confirmation for 'yes/ja/yebo' or detailed explanation for 'more info/help'.

    Signature verification lives here (rather than in main.py's two route aliases) so
    /whatsapp/webhook and /api/whatsapp/webhook are protected by the same check.
    """
    from twilio.request_validator import RequestValidator

    auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    if not auth_token:
        # Fail closed: without the token we cannot verify anything, so the message
        # must not be processed. Surfaced as a 500 (not a 403) because this is a
        # server misconfiguration, not a bad request from Twilio.
        raise HTTPException(
            status_code=500,
            detail="TWILIO_AUTH_TOKEN is not configured; cannot validate webhook signature",
        )

    validator = RequestValidator(auth_token)

    # Reconstruct the exact public URL Twilio signed against. Twilio signs the URL
    # it actually called, which is HTTPS in production / behind an ngrok tunnel, so
    # trust X-Forwarded-Proto when present (the proxy may terminate TLS before the
    # request reaches FastAPI). NOTE: this does not fix a mismatched *host* header
    # behind a proxy that rewrites it — the tunnel URL must be what's registered in
    # the Twilio console, trailing slash included.
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    public_url = str(request.url).replace(request.url.scheme, forwarded_proto, 1)

    signature = request.headers.get("x-twilio-signature", "")
    form = await request.form()

    if not validator.validate(public_url, dict(form), signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    # Only now — post-validation — do we read the message itself. Parsing the body
    # before this point would let a malformed payload skip verification entirely.
    body_text = str(form.get("Body") or "").strip().lower()
    media_url = form.get("MediaUrl0") or ""

    if any(k in body_text for k in ("yes", "ja", "yebo", "ee", "ok", "confirm", "seen")) or media_url:
        reply_msg = "Siyabonga! / Dankie! / Re a leboga! We have confirmed your alert receipt. We will continue monitoring your field."
    elif any(k in body_text for k in ("more", "info", "help", "explain", "verduidelik", "why", "lusisi", "ncedisa", "tshedisa", "ka lebaka")):
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT f.name, r.score, r.reason_summary
                FROM risk_scores r
                JOIN fields f ON f.id = r.field_id
                ORDER BY r.created_at DESC LIMIT 1
                """
            )
            r_row = cur.fetchone()

        if r_row:
            reply_msg = (
                f"{r_row['name']} risk explanation: Risk score is {r_row['score']}. "
                f"Reasons: {r_row['reason_summary']}. Please inspect irrigation valves and soil moisture today."
            )
        else:
            reply_msg = (
                "Ubuntu Terra risk explanation: Field stress risk is calculated from satellite NDVI vegetation decline, "
                "rainfall deficit, and temperature anomalies. Current demo fields show normal moisture levels."
            )
    else:
        reply_msg = (
            "Ubuntu Terra Assistant: Reply YES (or JA / YEBO / EE) to confirm alert receipt, "
            "or reply MORE INFO for a detailed explanation of your field's stress condition."
        )

    twiml_content = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{reply_msg}</Message></Response>'
    return Response(content=twiml_content, media_type="application/xml")



@router.post("/{field_id}/photos")
async def upload_field_photo(
    field_id: int,
    file: UploadFile = File(...),
    db=Depends(get_db),
    token_owner_id: str = Depends(require_owner_token),
):
    field = _get_accessible_field_or_403(field_id, db, token_owner_id)
    if not file.filename:
        raise HTTPException(status_code=400, detail="A file name is required")

    PHOTO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_bytes = await file.read()

    file_ext = os.path.splitext(file.filename)[1] or ".jpg"
    safe_name = f"field_{field_id}_{dt.datetime.now(dt.UTC).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}{file_ext}"
    destination = PHOTO_UPLOAD_DIR / safe_name

    with destination.open("wb") as uploaded:
        uploaded.write(file_bytes)

    # Analyze image for disease/pest issues (Phase 2)
    diag_data = analyze_crop_photo(file_bytes, file.filename)

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO photo_diagnoses (field_id, filename, category, confidence, description, model_name)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, category, confidence, description, model_name, created_at
            """,
            (
                field["id"],
                safe_name,
                diag_data["category"],
                diag_data["confidence"],
                diag_data["description"],
                diag_data["model_name"],
            ),
        )
        diag_row = cur.fetchone()
    db.commit()

    return {
        "id": uuid.uuid4().hex,
        "field_id": field["id"],
        "filename": safe_name,
        "status": "pending_review",
        "stored_path": str(destination),
        "uploaded_at": dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
        "diagnosis": {
            "id": diag_row["id"],
            "category": diag_row["category"],
            "confidence": float(diag_row["confidence"]),
            "description": diag_row["description"],
            "model_name": diag_row["model_name"],
            "created_at": diag_row["created_at"].isoformat(),
        },
    }


@router.get("/{field_id}/photos")
def list_field_photos(field_id: int, db=Depends(get_db), token_owner_id: str = Depends(require_owner_token)):
    _get_accessible_field_or_403(field_id, db, token_owner_id)
    PHOTO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    photos = []
    for file_path in sorted(PHOTO_UPLOAD_DIR.glob(f"field_{field_id}_*")):
        photos.append(
            {
                "field_id": field_id,
                "filename": file_path.name,
                "status": "pending_review",
                "stored_path": str(file_path),
                "uploaded_at": dt.datetime.fromtimestamp(file_path.stat().st_mtime).isoformat() + "Z",
            }
        )
    return photos


@router.get("/{field_id}/photos/diagnoses")
def list_photo_diagnoses(field_id: int, db=Depends(get_db), token_owner_id: str = Depends(require_owner_token)):
    _get_accessible_field_or_403(field_id, db, token_owner_id)
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, field_id, filename, category, confidence, description, model_name, created_at
            FROM photo_diagnoses
            WHERE field_id = %s
            ORDER BY created_at DESC
            """,
            (field_id,),
        )
        rows = cur.fetchall()
    return [
        {
            "id": r["id"],
            "field_id": r["field_id"],
            "filename": r["filename"],
            "category": r["category"],
            "confidence": float(r["confidence"]),
            "description": r["description"],
            "model_name": r["model_name"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


@router.post("/feedback", status_code=201)
def submit_feedback(
    payload: FeedbackCreate,
    db=Depends(get_db),
    token_owner_id: str = Depends(require_owner_token),
):
    _get_accessible_field_or_403(payload.field_id, db, token_owner_id)
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO farmer_feedback (field_id, risk_score_id, photo_diagnosis_id, was_accurate, farmer_comment)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, created_at
            """,
            (
                payload.field_id,
                payload.risk_score_id,
                payload.photo_diagnosis_id,
                payload.was_accurate,
                payload.farmer_comment,
            ),
        )
        row = cur.fetchone()
    db.commit()
    return {"id": row["id"], "status": "saved", "created_at": row["created_at"].isoformat()}


@router.get("/validation-stats")
def get_validation_stats(db=Depends(get_db)):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT 
                COUNT(*) AS total,
                SUM(CASE WHEN was_accurate THEN 1 ELSE 0 END) AS accurate_count
            FROM farmer_feedback
            """
        )
        row = cur.fetchone()

    total = row["total"] or 0
    accurate_count = row["accurate_count"] or 0

    if total < 20:
        return {
            "status": "not_enough_data",
            "response_count": total,
            "threshold": 20,
            "message": "not enough data yet",
            "detail": f"Only {total} feedback response(s) recorded. At least 20 responses are required before reporting an agreement rate.",
        }

    agreement_rate = round((accurate_count / total) * 100, 1)
    return {
        "status": "validated",
        "response_count": total,
        "accurate_count": accurate_count,
        "agreement_rate": agreement_rate,
        "message": f"{agreement_rate}% agreement across {total} farmer feedback responses.",
    }



def _get_latest_photo_diagnosis(field_id: int, db) -> dict | None:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, filename, category, confidence, description, model_name, created_at
            FROM photo_diagnoses
            WHERE field_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (field_id,),
        )
        r = cur.fetchone()
    if not r:
        return None
    return {
        "id": r["id"],
        "filename": r["filename"],
        "category": r["category"],
        "confidence": float(r["confidence"]),
        "description": r["description"],
        "model_name": r["model_name"],
        "created_at": r["created_at"].isoformat(),
    }


# --- Internals -----------------------------------------------------------


def _get_field_or_404(field_id: int, db) -> dict:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, created_at, owner_id, is_demo_field,
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


def _get_accessible_field_or_403(field_id: int, db, token_owner_id: str) -> dict:
    """
    Load a field and enforce ownership.

    Guards the per-field URL endpoints (readings/risk/alerts/photos/feedback)
    against a token holder enumerating field_id values to reach another
    owner's field — a separate hole from the owner_id query-param one, since
    incrementing an integer in the path never touches the ownership filter.

    Demo fields (is_demo_field = true) stay readable by any valid token so the
    seeded demo data keeps working for every judge/tester without registering
    field data of their own.
    """
    field = _get_field_or_404(field_id, db)
    if field.get("is_demo_field"):
        return field
    if field.get("owner_id") != token_owner_id:
        raise HTTPException(
            status_code=403, detail="You do not have access to this field"
        )
    return field


READING_CACHE_TTL_SECONDS = int(os.environ.get("READING_CACHE_TTL_SECONDS", "21600"))  # 6 hours default


def _is_source_fresh(field_id: int, source: str, db, ttl_seconds: int = READING_CACHE_TTL_SECONDS) -> bool:
    """Return True if we have a reading_source_status row newer than the TTL."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT last_refreshed_at FROM reading_source_status
            WHERE field_id = %s AND source = %s
            """,
            (field_id, source),
        )
        row = cur.fetchone()
    if not row:
        return False
    age_seconds = (dt.datetime.now(dt.timezone.utc) - row["last_refreshed_at"]).total_seconds()
    return age_seconds < ttl_seconds


def _touch_source_refresh(field_id: int, source: str, db, cached_value=None) -> None:
    """Upsert the last-refreshed timestamp for a (field_id, source) pair.

    For scalar sources such as the rainfall forecast, store the fetched value
    in cached_value_json so it can be reused within the TTL window.
    """
    import json

    value_json = json.dumps(cached_value) if cached_value is not None else None
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO reading_source_status (field_id, source, last_refreshed_at, cached_value_json)
            VALUES (%s, %s, now(), %s::jsonb)
            ON CONFLICT (field_id, source) DO UPDATE SET
                last_refreshed_at = EXCLUDED.last_refreshed_at,
                cached_value_json = COALESCE(EXCLUDED.cached_value_json, reading_source_status.cached_value_json)
            """,
            (field_id, source, value_json),
        )
    db.commit()


def _get_cached_scalar(field_id: int, source: str, db, ttl_seconds: int = READING_CACHE_TTL_SECONDS):
    """Return a cached scalar value if it exists and is still fresh, else None."""
    if not _is_source_fresh(field_id, source, db, ttl_seconds):
        return None
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT cached_value_json FROM reading_source_status
            WHERE field_id = %s AND source = %s
            """,
            (field_id, source),
        )
        row = cur.fetchone()
    if not row or row["cached_value_json"] is None:
        return None

    # psycopg2 already deserialises JSONB into native Python objects.
    value = row["cached_value_json"]
    if isinstance(value, str):
        import json
        return json.loads(value)
    return value


def _sync_readings(field: dict, db, days: int = READING_LOOKBACK_DAYS) -> None:
    end = dt.date.today()
    start = end - dt.timedelta(days=days)

    # Only hit external weather APIs if our cached data is stale or absent.
    weather_readings = []
    if not _is_source_fresh(field["id"], "open_meteo", db):
        try:
            weather_readings = weather_service.get_recent_weather(field["lat"], field["lon"], days=days)
            if weather_readings:
                # Record the actual source that returned data (open_meteo or nasa_power fallback).
                _touch_source_refresh(field["id"], weather_readings[0].source, db)
        except Exception:
            pass

    # Only hit Sentinel Hub if our cached NDVI is stale or absent.
    ndvi_readings = []
    if not _is_source_fresh(field["id"], "sentinel_hub", db):
        try:
            ndvi_readings = satellite_service.get_ndvi_time_series(
                field["boundary_geojson"], start, end
            )
            if ndvi_readings:
                _touch_source_refresh(field["id"], "sentinel_hub", db)
        except Exception:
            pass

    # Demo NDVI fallback is restricted to demo fields and only seeded when stale.
    if field.get("is_demo_field") and not ndvi_readings and not _is_source_fresh(field["id"], "demo_trigger", db):
        _seed_demo_ndvi_trigger(field, db)
        _touch_source_refresh(field["id"], "demo_trigger", db)

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


def _seed_demo_ndvi_trigger(field: dict, db) -> None:
    base_date = dt.date.today()
    demo_rows = [
        (base_date - dt.timedelta(days=4), 0.68, 18.0, 22.0),
        (base_date - dt.timedelta(days=3), 0.62, 16.0, 23.5),
        (base_date - dt.timedelta(days=2), 0.54, 9.0, 25.5),
        (base_date - dt.timedelta(days=1), 0.47, 4.0, 27.5),
        (base_date, 0.39, 1.0, 29.0),
    ]

    with db.cursor() as cur:
        for row_date, ndvi, rainfall, temp in demo_rows:
            cur.execute(
                """
                INSERT INTO readings (field_id, date, ndvi_value, rainfall_mm, temp_c, source)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (field_id, date, source) DO UPDATE SET
                    ndvi_value = EXCLUDED.ndvi_value,
                    rainfall_mm = EXCLUDED.rainfall_mm,
                    temp_c = EXCLUDED.temp_c
                """,
                (field["id"], row_date, ndvi, rainfall, temp, "demo_trigger"),
            )
    db.commit()


def _fetch_merged_readings(field_id: int, db) -> list[dict]:
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
    temp = [r["temp_c"] for r in merged]

    field = _get_field_or_404(field_id, db)

    # Cache the 7-day rainfall forecast with the same TTL as readings.
    forecast_rainfall_mm = _get_cached_scalar(field_id, "forecast", db)
    if forecast_rainfall_mm is None:
        try:
            forecast_rainfall_mm = weather_service.get_forecast_rainfall(field["lat"], field["lon"])
            _touch_source_refresh(field_id, "forecast", db, cached_value=forecast_rainfall_mm)
        except Exception:
            pass

    assessment = assess_field_risk(ndvi, temp, forecast_rainfall_mm=forecast_rainfall_mm)

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

