"""
services/satellite.py

NDVI time series for a field polygon via the Copernicus Data Space Ecosystem
— Sentinel Hub Statistical API. Sentinel-2 L2A imagery, 5-day revisit.

Two-step flow:
    1. OAuth2 client-credentials token exchange (Copernicus identity server).
    2. POST the field polygon + an NDVI evalscript to the Statistical API,
       which returns per-interval mean/stddev NDVI already aggregated
       server-side (no raw imagery download needed for our use case).

Requires SENTINEL_HUB_CLIENT_ID / SENTINEL_HUB_CLIENT_SECRET (see
../.env.example) from a Copernicus Data Space Ecosystem OAuth client —
register at dataspace.copernicus.eu, account approval can take a short
while, so do this early.

This module makes network calls — keep it separate from risk_engine.py,
which must stay pure/offline-testable.
"""
from __future__ import annotations

import datetime as dt
import os
import time
from dataclasses import dataclass

import httpx

TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
)
STATISTICS_URL = "https://sh.dataspace.copernicus.eu/api/v1/statistics"

DEFAULT_TIMEOUT_SECONDS = 20.0

# Cloud-masked NDVI. Returns NaN for cloudy/invalid pixels so they're
# excluded from the server-side mean rather than dragging it down.
NDVI_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04", "B08", "SCL", "dataMask"] }],
    output: [
      { id: "ndvi", bands: 1, sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1 }
    ]
  };
}

function evaluatePixel(sample) {
  // SCL cloud/shadow/snow classes to exclude (Sentinel-2 L2A scene classification)
  const cloudClasses = [3, 8, 9, 10, 11];
  const isValid = sample.dataMask === 1 && cloudClasses.indexOf(sample.SCL) === -1;
  const ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04 + 1e-6);
  return {
    ndvi: [isValid ? ndvi : NaN],
    dataMask: [isValid ? 1 : 0]
  };
}
"""


@dataclass
class NdviReading:
    date: dt.date
    ndvi_mean: float | None
    sample_count: int


class SatelliteServiceError(Exception):
    """Raised when the Copernicus token exchange or statistics call fails."""


class _TokenCache:
    """Simple in-memory token cache so we don't re-authenticate on every call."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0

    def get(self, client: httpx.Client, client_id: str, client_secret: str) -> str:
        if self._token and time.time() < self._expires_at - 30:
            return self._token

        response = client.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        response.raise_for_status()
        payload = response.json()
        self._token = payload["access_token"]
        self._expires_at = time.time() + payload.get("expires_in", 300)
        return self._token


_token_cache = _TokenCache()


def get_ndvi_time_series(
    field_boundary_geojson: dict,
    start_date: dt.date,
    end_date: dt.date,
    client_id: str | None = None,
    client_secret: str | None = None,
    client: httpx.Client | None = None,
) -> list[NdviReading]:
    """
    Return a mean-NDVI-per-Sentinel-2-pass time series for the given field
    polygon (a GeoJSON Polygon geometry dict, as stored in the `fields`
    table) between start_date and end_date.

    `client_id` / `client_secret` default to the SENTINEL_HUB_CLIENT_ID /
    SENTINEL_HUB_CLIENT_SECRET env vars. `client` can be injected for testing.
    """
    client_id = client_id or os.environ.get("SENTINEL_HUB_CLIENT_ID")
    client_secret = client_secret or os.environ.get("SENTINEL_HUB_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise SatelliteServiceError(
            "SENTINEL_HUB_CLIENT_ID / SENTINEL_HUB_CLIENT_SECRET not set. "
            "Register a Copernicus Data Space Ecosystem OAuth client at "
            "dataspace.copernicus.eu and set them in .env."
        )

    owns_client = client is None
    client = client or httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS)
    try:
        token = _token_cache.get(client, client_id, client_secret)
        return _fetch_statistics(
            client, token, field_boundary_geojson, start_date, end_date
        )
    finally:
        if owns_client:
            client.close()


def _fetch_statistics(
    client: httpx.Client,
    token: str,
    field_boundary_geojson: dict,
    start_date: dt.date,
    end_date: dt.date,
) -> list[NdviReading]:
    request_body = {
        "input": {
            "bounds": {
                "geometry": field_boundary_geojson,
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {"maxCloudCoverage": 80},
                }
            ],
        },
        "aggregation": {
            "timeRange": {
                "from": f"{start_date.isoformat()}T00:00:00Z",
                "to": f"{end_date.isoformat()}T23:59:59Z",
            },
            "aggregationInterval": {"of": "P1D"},  # one interval per revisit
            "evalscript": NDVI_EVALSCRIPT,
            "resx": 10,
            "resy": 10,
        },
        "calculations": {"ndvi": {"statistics": {"default": {}}}},
    }

    response = client.post(
        STATISTICS_URL,
        headers={"Authorization": f"Bearer {token}"},
        json=request_body,
    )
    response.raise_for_status()
    payload = response.json()

    readings: list[NdviReading] = []
    for interval_data in payload.get("data", []):
        interval_from = interval_data["interval"]["from"]
        date = dt.datetime.fromisoformat(interval_from.replace("Z", "+00:00")).date()

        outputs = interval_data.get("outputs", {})
        ndvi_stats = outputs.get("ndvi", {}).get("bands", {}).get("B0", {}).get("stats", {})

        sample_count = ndvi_stats.get("sampleCount", 0)
        valid_count = sample_count - ndvi_stats.get("noDataCount", 0)

        readings.append(
            NdviReading(
                date=date,
                ndvi_mean=ndvi_stats.get("mean") if valid_count > 0 else None,
                sample_count=valid_count,
            )
        )

    return sorted(readings, key=lambda r: r.date)


if __name__ == "__main__":
    # Manual smoke test against a real demo field — requires real internet
    # access AND real Copernicus credentials in the environment. Run:
    #   python -m app.services.satellite
    import sys

    # Gamtoos Valley demo field — small square around -33.7550, 24.8080
    field_geojson = {
        "type": "Polygon",
        "coordinates": [[
            [24.8065, -33.7565], [24.8095, -33.7565],
            [24.8095, -33.7535], [24.8065, -33.7535], [24.8065, -33.7565],
        ]],
    }
    end = dt.date.today()
    start = end - dt.timedelta(days=30)
    try:
        readings = get_ndvi_time_series(field_geojson, start, end)
        for r in readings:
            print(r)
    except Exception as exc:  # noqa: BLE001
        print(f"Satellite fetch failed: {exc}", file=sys.stderr)
        raise
