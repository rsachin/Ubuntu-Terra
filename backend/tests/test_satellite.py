"""
Unit tests for services/satellite.py. Fully offline — no live network calls,
no real Copernicus credentials needed.

Uses httpx's MockTransport to simulate the real Copernicus token endpoint and
Sentinel Hub Statistical API response shapes.
"""
import datetime as dt

import httpx
import pytest

from app.services import satellite

FIELD_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[
        [24.8065, -33.7565], [24.8095, -33.7565],
        [24.8095, -33.7535], [24.8065, -33.7535], [24.8065, -33.7565],
    ]],
}


@pytest.fixture(autouse=True)
def reset_token_cache():
    # The module-level token cache would otherwise leak state between tests.
    satellite._token_cache = satellite._TokenCache()
    yield


def _token_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={"access_token": "fake-token-123", "expires_in": 300, "token_type": "Bearer"},
    )


def _statistics_success_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "data": [
                {
                    "interval": {"from": "2026-09-10T00:00:00Z", "to": "2026-09-11T00:00:00Z"},
                    "outputs": {
                        "ndvi": {
                            "bands": {
                                "B0": {
                                    "stats": {
                                        "mean": 0.62,
                                        "min": 0.4,
                                        "max": 0.8,
                                        "stDev": 0.05,
                                        "sampleCount": 900,
                                        "noDataCount": 12,
                                    }
                                }
                            }
                        }
                    },
                },
                {
                    "interval": {"from": "2026-09-15T00:00:00Z", "to": "2026-09-16T00:00:00Z"},
                    "outputs": {
                        "ndvi": {
                            "bands": {
                                "B0": {
                                    "stats": {
                                        "mean": 0.55,
                                        "sampleCount": 900,
                                        "noDataCount": 900,  # fully clouded out
                                    }
                                }
                            }
                        }
                    },
                },
            ]
        },
    )


def _make_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_requires_credentials_when_none_available(monkeypatch):
    monkeypatch.delenv("SENTINEL_HUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("SENTINEL_HUB_CLIENT_SECRET", raising=False)

    with pytest.raises(satellite.SatelliteServiceError, match="not set"):
        satellite.get_ndvi_time_series(
            FIELD_GEOJSON, dt.date(2026, 9, 1), dt.date(2026, 9, 20)
        )


def test_returns_parsed_ndvi_readings():
    def router(request: httpx.Request) -> httpx.Response:
        if "identity.dataspace" in str(request.url):
            return _token_response(request)
        return _statistics_success_response(request)

    client = _make_client(router)
    readings = satellite.get_ndvi_time_series(
        FIELD_GEOJSON,
        dt.date(2026, 9, 1),
        dt.date(2026, 9, 20),
        client_id="test-id",
        client_secret="test-secret",
        client=client,
    )

    assert len(readings) == 2
    assert readings[0].date == dt.date(2026, 9, 10)
    assert readings[0].ndvi_mean == 0.62
    assert readings[0].sample_count == 888  # 900 - 12 noData


def test_fully_clouded_interval_returns_none_ndvi():
    def router(request: httpx.Request) -> httpx.Response:
        if "identity.dataspace" in str(request.url):
            return _token_response(request)
        return _statistics_success_response(request)

    client = _make_client(router)
    readings = satellite.get_ndvi_time_series(
        FIELD_GEOJSON,
        dt.date(2026, 9, 1),
        dt.date(2026, 9, 20),
        client_id="test-id",
        client_secret="test-secret",
        client=client,
    )

    clouded = [r for r in readings if r.date == dt.date(2026, 9, 15)][0]
    assert clouded.sample_count == 0
    assert clouded.ndvi_mean is None


def test_token_request_failure_raises():
    def router(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_client"})

    client = _make_client(router)
    with pytest.raises(httpx.HTTPStatusError):
        satellite.get_ndvi_time_series(
            FIELD_GEOJSON,
            dt.date(2026, 9, 1),
            dt.date(2026, 9, 20),
            client_id="bad-id",
            client_secret="bad-secret",
            client=client,
        )


def test_statistics_request_failure_raises():
    def router(request: httpx.Request) -> httpx.Response:
        if "identity.dataspace" in str(request.url):
            return _token_response(request)
        return httpx.Response(400, json={"error": "invalid geometry"})

    client = _make_client(router)
    with pytest.raises(httpx.HTTPStatusError):
        satellite.get_ndvi_time_series(
            FIELD_GEOJSON,
            dt.date(2026, 9, 1),
            dt.date(2026, 9, 20),
            client_id="test-id",
            client_secret="test-secret",
            client=client,
        )


def test_token_is_cached_across_calls():
    call_count = {"token": 0}

    def router(request: httpx.Request) -> httpx.Response:
        if "identity.dataspace" in str(request.url):
            call_count["token"] += 1
            return _token_response(request)
        return _statistics_success_response(request)

    client = _make_client(router)
    satellite.get_ndvi_time_series(
        FIELD_GEOJSON, dt.date(2026, 9, 1), dt.date(2026, 9, 20),
        client_id="test-id", client_secret="test-secret", client=client,
    )
    satellite.get_ndvi_time_series(
        FIELD_GEOJSON, dt.date(2026, 9, 1), dt.date(2026, 9, 20),
        client_id="test-id", client_secret="test-secret", client=client,
    )

    assert call_count["token"] == 1  # second call reused the cached token
