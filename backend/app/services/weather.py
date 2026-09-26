"""
services/weather.py

Pulls recent daily rainfall + temperature for a field centroid.

Primary source: Open-Meteo (no API key). Falls back to NASA POWER (no API
key either) if Open-Meteo fails or times out. Two independent free sources
so the demo doesn't die if one is rate-limited or briefly down.

This module makes network calls — keep it separate from risk_engine.py,
which must stay pure/offline-testable.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import httpx

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_LOOKBACK_DAYS = 14


@dataclass
class DailyWeather:
    date: dt.date
    rainfall_mm: float | None
    temp_c: float | None
    source: str  # "open_meteo" | "nasa_power"


class WeatherServiceError(Exception):
    """Raised when both Open-Meteo and NASA POWER fail."""


def get_recent_weather(
    latitude: float,
    longitude: float,
    days: int = DEFAULT_LOOKBACK_DAYS,
    client: httpx.Client | None = None,
) -> list[DailyWeather]:
    """
    Return daily rainfall + temperature for the last `days` days at the given
    coordinates. Tries Open-Meteo first; falls back to NASA POWER on any
    request error, timeout, or non-2xx response.

    `client` can be injected for testing (see tests/test_weather.py).
    """
    owns_client = client is None
    client = client or httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS)
    try:
        try:
            return _fetch_open_meteo(latitude, longitude, days, client)
        except (httpx.HTTPError, WeatherServiceError, KeyError, ValueError):
            return _fetch_nasa_power(latitude, longitude, days, client)
    finally:
        if owns_client:
            client.close()


def get_forecast_rainfall(
    latitude: float,
    longitude: float,
    client: httpx.Client | None = None,
) -> float | None:
    """
    Return the 7-day predicted rainfall sum for the given coordinates from Open-Meteo.
    """
    owns_client = client is None
    client = client or httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS)
    try:
        response = client.get(
            OPEN_METEO_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "daily": "precipitation_sum",
                "forecast_days": 7,
                "past_days": 0,
                "timezone": "auto",
            },
        )
        response.raise_for_status()
        payload = response.json()
        daily = payload.get("daily", {})
        precipitation = daily.get("precipitation_sum", [])
        
        valid_precip = [p for p in precipitation if p is not None]
        if not valid_precip:
            return None
        return sum(valid_precip)
    except Exception:
        return None
    finally:
        if owns_client:
            client.close()


def _fetch_open_meteo(
    latitude: float, longitude: float, days: int, client: httpx.Client
) -> list[DailyWeather]:
    response = client.get(
        OPEN_METEO_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "daily": "precipitation_sum,temperature_2m_mean",
            "past_days": days,
            "forecast_days": 1,  # we only care about the recent past here
            "timezone": "auto",
        },
    )
    response.raise_for_status()
    payload = response.json()

    daily = payload["daily"]
    dates = daily["time"]
    rainfall = daily["precipitation_sum"]
    temps = daily["temperature_2m_mean"]

    if not (len(dates) == len(rainfall) == len(temps)):
        raise WeatherServiceError("Open-Meteo returned mismatched array lengths")

    return [
        DailyWeather(
            date=dt.date.fromisoformat(d),
            rainfall_mm=rainfall[i],
            temp_c=temps[i],
            source="open_meteo",
        )
        for i, d in enumerate(dates)
    ]


def _fetch_nasa_power(
    latitude: float, longitude: float, days: int, client: httpx.Client
) -> list[DailyWeather]:
    end = dt.date.today()
    start = end - dt.timedelta(days=days)

    response = client.get(
        NASA_POWER_URL,
        params={
            "parameters": "T2M,PRECTOTCORR",
            "community": "AG",
            "longitude": longitude,
            "latitude": latitude,
            "start": start.strftime("%Y%m%d"),
            "end": end.strftime("%Y%m%d"),
            "format": "JSON",
        },
    )
    response.raise_for_status()
    payload = response.json()

    params = payload["properties"]["parameter"]
    temps_by_date = params["T2M"]
    rain_by_date = params["PRECTOTCORR"]

    # NASA POWER uses -999 (or similar) as a fill value for missing data.
    def clean(value: float) -> float | None:
        return None if value is not None and value <= -900 else value

    readings = []
    for date_str in sorted(temps_by_date.keys()):
        readings.append(
            DailyWeather(
                date=dt.datetime.strptime(date_str, "%Y%m%d").date(),
                rainfall_mm=clean(rain_by_date.get(date_str)),
                temp_c=clean(temps_by_date.get(date_str)),
                source="nasa_power",
            )
        )
    return readings


if __name__ == "__main__":
    # Manual smoke test against a real demo field — requires real internet
    # access (this will fail in network-restricted sandboxes). Run directly:
    #   python -m app.services.weather
    import sys

    # Gamtoos Valley demo field coordinates (Patensie area)
    lat, lon = -33.7550, 24.8080
    try:
        readings = get_recent_weather(lat, lon, days=7)
        for r in readings:
            print(r)
    except Exception as exc:  # noqa: BLE001
        print(f"Weather fetch failed: {exc}", file=sys.stderr)
        raise
