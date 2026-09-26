"""
services/risk_engine.py

Pure rule-based risk scoring. NO network calls here, deliberately — this
module must be fully testable offline and must never be blocked by a flaky
external API. Services (weather.py, satellite.py) fetch data; this module
only reasons over data already fetched.

Rule (v1, from planning.md):
    Flag Medium/High when NDVI is trending down over the recent window AND
    at least one of (rainfall below recent average, temperature above
    recent average) is also true. The reason string names which signals
    triggered the flag.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskScore(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


@dataclass
class RiskAssessment:
    score: RiskScore
    reasons: list[str]
    recommended_check: str


# --- Thresholds (tune these as real data comes in; keep them named and
# in one place so they're easy to defend in Q&A and easy to adjust). ---

# NDVI is considered "trending down" if the most recent reading is at least
# this many percentage points below the average of the earlier readings.
NDVI_DECLINE_THRESHOLD_PCT = 8.0

# Rainfall is considered low if the 7-day forecast predicts less than this amount.
LOW_FORECAST_RAINFALL_MM = 10.0

# Temperature is "anomalously high" if the most recent reading is at least
# this many degrees C above the average of the earlier readings.
TEMP_ANOMALY_THRESHOLD_C = 2.0

# NDVI decline that severe (%) with BOTH other signals also triggered -> High
# instead of Medium.
HIGH_RISK_NDVI_DECLINE_PCT = 15.0


def assess_field_risk(
    ndvi_readings: list[float],
    temp_readings_c: list[float],
    forecast_rainfall_mm: float | None = None,
) -> RiskAssessment:
    """
    Combine NDVI trend + low forecast rainfall + temperature anomaly into a
    score and a plain-language reason.

    Each `*_readings` list is ordered oldest -> newest. The last reading in
    each list is treated as "current"; everything before it is the recent
    baseline it's compared against. Missing/empty data for a signal means
    that signal simply can't contribute to a flag (never assumed to be bad).
    """
    ndvi_decline_pct = _percent_decline(ndvi_readings)
    temp_anomaly_c = _anomaly(temp_readings_c)

    ndvi_declining = ndvi_decline_pct is not None and ndvi_decline_pct >= NDVI_DECLINE_THRESHOLD_PCT
    rainfall_deficit = (
        forecast_rainfall_mm is not None and forecast_rainfall_mm < LOW_FORECAST_RAINFALL_MM
    )
    temp_anomaly = temp_anomaly_c is not None and temp_anomaly_c >= TEMP_ANOMALY_THRESHOLD_C

    reasons: list[str] = []
    if ndvi_declining:
        reasons.append(f"NDVI down {ndvi_decline_pct:.0f}% over the last {len(ndvi_readings)} readings")
    if rainfall_deficit:
        reasons.append(f"Forecast predicts low rainfall (~{forecast_rainfall_mm:.0f}mm) over the next 7 days")
    if temp_anomaly:
        reasons.append(f"Temperature {temp_anomaly_c:.1f}\u00b0C above the recent average")

    contributing_factor = rainfall_deficit or temp_anomaly

    if not ndvi_declining or not contributing_factor:
        return RiskAssessment(
            score=RiskScore.LOW,
            reasons=reasons or ["No significant decline detected in vegetation, rainfall, or temperature"],
            recommended_check="No action needed — continue routine monitoring",
        )

    # ndvi_declining AND contributing_factor are both true from here on.
    is_high = ndvi_decline_pct >= HIGH_RISK_NDVI_DECLINE_PCT and rainfall_deficit and temp_anomaly

    return RiskAssessment(
        score=RiskScore.HIGH if is_high else RiskScore.MEDIUM,
        reasons=reasons,
        recommended_check=_recommended_check(rainfall_deficit, temp_anomaly),
    )


def _percent_decline(readings: list[float]) -> float | None:
    """
    % by which the most recent reading is below the average of the earlier
    readings. Positive = decline. None if there isn't enough data to compare.
    """
    valid = [r for r in readings if r is not None]
    if len(valid) < 2:
        return None
    *earlier, current = valid
    baseline = sum(earlier) / len(earlier)
    if baseline == 0:
        return None
    return ((baseline - current) / baseline) * 100


def _anomaly(readings: list[float]) -> float | None:
    """
    Degrees by which the most recent reading is above the average of the
    earlier readings. Positive = hotter than recent baseline. None if there
    isn't enough data to compare.
    """
    valid = [r for r in readings if r is not None]
    if len(valid) < 2:
        return None
    *earlier, current = valid
    baseline = sum(earlier) / len(earlier)
    return current - baseline


def _recommended_check(rainfall_deficit: bool, temp_anomaly: bool) -> str:
    if rainfall_deficit and temp_anomaly:
        return "Check the irrigation system — low rainfall and rising heat are compounding"
    if rainfall_deficit:
        return "Check the irrigation system for reduced water delivery"
    return "Check for heat stress — consider shade netting or adjusted irrigation timing"
