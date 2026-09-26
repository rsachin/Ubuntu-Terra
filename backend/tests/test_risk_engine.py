"""
Unit tests for services/risk_engine.py — pure logic, no network, no
external API dependency of any kind. Hand-picked input/output cases,
including edge cases (flat data, missing data, only-one-signal-bad).
"""
from app.services.risk_engine import RiskScore, assess_field_risk


def test_all_signals_good_is_low_risk():
    # Healthy field: NDVI flat/improving, forecast rainfall adequate, temp on par.
    result = assess_field_risk(
        ndvi_readings=[0.55, 0.56, 0.58],
        temp_readings_c=[22.0, 22.5, 22.2],
        forecast_rainfall_mm=20.0,
    )
    assert result.score == RiskScore.LOW
    assert "No action needed" in result.recommended_check


def test_clear_decline_all_three_signals_bad_is_medium_or_high():
    # NDVI down substantially, forecast rainfall below the low-rain threshold, temp well above.
    result = assess_field_risk(
        ndvi_readings=[0.60, 0.58, 0.50],   # ~13.8% decline vs avg of first two
        temp_readings_c=[21.0, 21.5, 25.0],  # +3.75C above avg
        forecast_rainfall_mm=8.0,            # below 10 mm low-rain threshold
    )
    assert result.score in (RiskScore.MEDIUM, RiskScore.HIGH)
    assert any("NDVI down" in r for r in result.reasons)
    assert any("rainfall" in r.lower() for r in result.reasons)
    assert any("temperature" in r.lower() for r in result.reasons)
    assert "irrigation" in result.recommended_check.lower()


def test_severe_decline_with_both_contributing_factors_is_high():
    result = assess_field_risk(
        ndvi_readings=[0.70, 0.68, 0.40],   # ~42% decline — clearly severe
        temp_readings_c=[20.0, 20.0, 26.0],  # +6C above avg
        forecast_rainfall_mm=5.0,           # well below low-rain threshold
    )
    assert result.score == RiskScore.HIGH


def test_ndvi_declining_but_no_contributing_factor_is_low():
    # NDVI down, but forecast rainfall is adequate and temp is normal — could be harvest,
    # pest damage, or natural senescence, not necessarily water stress.
    # The engine should NOT flag this as Medium/High on NDVI alone.
    result = assess_field_risk(
        ndvi_readings=[0.60, 0.58, 0.48],  # ~17% decline
        temp_readings_c=[22.0, 22.1, 22.3],  # normal
        forecast_rainfall_mm=20.0,          # adequate forecast rain
    )
    assert result.score == RiskScore.LOW


def test_rainfall_deficit_alone_without_ndvi_decline_is_low():
    # Forecast rain is low, but vegetation hasn't responded yet — not flagged yet.
    result = assess_field_risk(
        ndvi_readings=[0.55, 0.56, 0.57],  # improving
        temp_readings_c=[21.0, 21.0, 21.0],  # flat
        forecast_rainfall_mm=5.0,           # sharp drop
    )
    assert result.score == RiskScore.LOW


def test_flat_ndvi_is_low_risk():
    # Edge case: perfectly flat NDVI (no meaningful decline to compute).
    result = assess_field_risk(
        ndvi_readings=[0.5, 0.5, 0.5],
        temp_readings_c=[20.0, 20.0, 25.0],  # hot anomaly
        forecast_rainfall_mm=2.0,              # low forecast rain
    )
    assert result.score == RiskScore.LOW


def test_missing_ndvi_data_does_not_crash_and_is_low_risk():
    # Edge case: fewer than 2 valid NDVI readings (e.g. cloud cover gaps) —
    # can't compute a trend, so NDVI must not contribute to a flag.
    result = assess_field_risk(
        ndvi_readings=[0.55],
        temp_readings_c=[20.0, 26.0],  # hot anomaly
        forecast_rainfall_mm=5.0,      # low forecast rain
    )
    assert result.score == RiskScore.LOW


def test_missing_ndvi_data_with_none_values_does_not_crash():
    # Edge case: explicit None entries mixed into the readings (cloud-masked
    # satellite pass, matching what satellite.py returns for fully-clouded
    # intervals).
    result = assess_field_risk(
        ndvi_readings=[0.6, None, 0.5],
        temp_readings_c=[20.0, 20.0, 26.0],  # +6C anomaly
        forecast_rainfall_mm=5.0,            # low forecast rain
    )
    # Only 2 valid NDVI points remain (0.6, 0.5) -> ~16.7% decline, still
    # computable and should still flag given the other two signals.
    assert result.score in (RiskScore.MEDIUM, RiskScore.HIGH)


def test_empty_readings_do_not_crash_and_are_low_risk():
    result = assess_field_risk(
        ndvi_readings=[],
        temp_readings_c=[],
        forecast_rainfall_mm=None,
    )
    assert result.score == RiskScore.LOW
    assert result.reasons  # should still return a human-readable reason, not blow up


def test_reason_strings_name_the_triggering_signals_only():
    # Only forecast rainfall is a contributing factor (temp is normal) — the reason
    # list should mention rainfall but not fabricate a temperature reason.
    result = assess_field_risk(
        ndvi_readings=[0.60, 0.58, 0.50],
        temp_readings_c=[21.0, 21.2, 21.1],  # normal
        forecast_rainfall_mm=8.0,             # low forecast rain
    )
    assert result.score == RiskScore.MEDIUM
    assert any("rainfall" in r.lower() for r in result.reasons)
    assert not any("temperature" in r.lower() for r in result.reasons)
