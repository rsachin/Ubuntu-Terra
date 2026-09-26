"""
Unit tests for services/weather.py. Fully offline — no live network calls.

Uses httpx's MockTransport to simulate real Open-Meteo / NASA POWER response
shapes, including the fallback path (Open-Meteo down -> NASA POWER used).
"""
import httpx
import pytest

from app.services import weather

# Gamtoos Valley demo field coordinates
LAT, LON = -33.7550, 24.8080


def _open_meteo_success_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "daily": {
                "time": ["2026-09-17", "2026-09-18", "2026-09-19"],
                "precipitation_sum": [0.0, 2.4, 0.0],
                "temperature_2m_mean": [21.3, 20.1, 22.8],
            }
        },
    )


def _open_meteo_failure_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(503, json={"error": True, "reason": "Service unavailable"})


def _nasa_power_success_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "properties": {
                "parameter": {
                    "T2M": {"20260917": 21.0, "20260918": 20.5, "20260919": 22.6},
                    "PRECTOTCORR": {"20260917": 0.0, "20260918": 1.9, "20260919": 0.0},
                }
            }
        },
    )


def _make_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_open_meteo_success_returns_parsed_readings():
    client = _make_client(_open_meteo_success_response)
    readings = weather.get_recent_weather(LAT, LON, days=3, client=client)

    assert len(readings) == 3
    assert all(r.source == "open_meteo" for r in readings)
    assert readings[1].rainfall_mm == 2.4
    assert readings[1].temp_c == 20.1


def test_falls_back_to_nasa_power_when_open_meteo_fails():
    call_count = {"n": 0}

    def router(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if "open-meteo" in str(request.url):
            return _open_meteo_failure_response(request)
        return _nasa_power_success_response(request)

    client = _make_client(router)
    readings = weather.get_recent_weather(LAT, LON, days=3, client=client)

    assert len(readings) == 3
    assert all(r.source == "nasa_power" for r in readings)
    assert call_count["n"] == 2  # tried Open-Meteo, then NASA POWER


def test_falls_back_to_nasa_power_on_network_timeout():
    def router(request: httpx.Request) -> httpx.Response:
        if "open-meteo" in str(request.url):
            raise httpx.ConnectTimeout("simulated timeout", request=request)
        return _nasa_power_success_response(request)

    client = _make_client(router)
    readings = weather.get_recent_weather(LAT, LON, days=3, client=client)

    assert all(r.source == "nasa_power" for r in readings)


def test_nasa_power_cleans_fill_values():
    def router(request: httpx.Request) -> httpx.Response:
        if "power.larc.nasa.gov" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "properties": {
                        "parameter": {
                            "T2M": {"20260917": -999.0, "20260918": 20.5},
                            "PRECTOTCORR": {"20260917": -999.0, "20260918": 1.9},
                        }
                    }
                },
            )
        return _open_meteo_failure_response(request)

    client = _make_client(router)
    readings = weather.get_recent_weather(LAT, LON, days=2, client=client)

    assert readings[0].temp_c is None
    assert readings[0].rainfall_mm is None
    assert readings[1].temp_c == 20.5


def test_raises_nothing_swallowed_if_both_sources_fail():
    def router(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": True})

    client = _make_client(router)
    with pytest.raises(httpx.HTTPStatusError):
        weather.get_recent_weather(LAT, LON, days=3, client=client)
