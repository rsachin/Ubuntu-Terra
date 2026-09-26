"""
Ubuntu Terra backend — FastAPI entrypoint.

Routers are added here as they're built (fields, readings, risk, alerts).
Keep this file thin: wiring only, no business logic.
"""
from dotenv import load_dotenv
load_dotenv()



from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import fields

app = FastAPI(
    title="Ubuntu Terra API",
    description="Geo-spatial water & crop stress monitoring for South African farmers",
    version="0.1.0",
)

# Mount static directory for audio voice note files and photo uploads
uploads_dir = Path(__file__).resolve().parents[1] / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
(uploads_dir / "audio").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(uploads_dir)), name="static")
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

import os

# Explicit origin allow-list. A wildcard ("*") here would let any website
# issue credentialed requests against the API from a farmer's browser, so the
# deployed frontend URL is added via ALLOWED_ORIGINS rather than in code.
# Entries are stripped/emptied-out because a stray space ("a, b") would
# otherwise produce an origin string that never matches and silently break
# every browser request.
allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "ALLOWED_ORIGINS", "http://localhost:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Owner-Token"],
)

app.include_router(fields.router)
app.include_router(fields.owners_router)


@app.get("/api/health")
def health_check():
    """Liveness check so Sachin (and CI) can confirm the backend is alive."""
    return {"status": "ok"}


@app.get("/validation-stats")
@app.get("/api/validation-stats")
def validation_stats_alias(db=fields.Depends(fields.get_db)):
    """Admin/internal endpoint returning farmer feedback agreement statistics."""
    return fields.get_validation_stats(db=db)


@app.post("/api/feedback", status_code=201)
def submit_feedback_alias(
    payload: fields.FeedbackCreate,
    db=fields.Depends(fields.get_db),
    token_owner_id: str = fields.Depends(fields.require_owner_token),
):
    """Top-level feedback submission endpoint."""
    return fields.submit_feedback(payload=payload, db=db, token_owner_id=token_owner_id)


@app.post("/whatsapp/webhook")
@app.post("/api/whatsapp/webhook")
async def whatsapp_webhook_alias(request: Request, db=fields.Depends(fields.get_db)):
    """Lightweight WhatsApp reply handler (webhook for Twilio inbound messages)."""
    return await fields.whatsapp_webhook(request=request, db=db)


