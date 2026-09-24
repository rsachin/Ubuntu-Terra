"""
Ubuntu Terra backend — FastAPI entrypoint.

Routers are added here as they're built (fields, readings, risk, alerts).
Keep this file thin: wiring only, no business logic.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import fields

app = FastAPI(
    title="Ubuntu Terra API",
    description="Geo-spatial water & crop stress monitoring for South African farmers",
    version="0.1.0",
)

# Wide-open CORS for hackathon demo purposes — tighten before any real deployment
# beyond the hackathon.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fields.router)


@app.get("/api/health")
def health_check():
    """Liveness check so Sachin (and CI) can confirm the backend is alive."""
    return {"status": "ok"}
