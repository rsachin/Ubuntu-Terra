"""
Unit tests for services/risk_engine.py — pure logic, no network, no
external API dependency of any kind. Hand-picked input/output cases,
including edge cases (flat data, missing data, only-one-signal-bad).
"""
from app.services.risk_engine import RiskScore, assess_field_risk


def test_all_signals_good_is_low_risk():
    # Healthy field: NDVI flat/improving, rainfall on par, temp on par.
    result = assess_field_risk(
        ndvi_readings=[0.55, 0.56, 0.58],
        rainfall_readings_mm=[20.0, 18.0, 19.0],
        temp_readings_c=[22.0, 22.5, 22.2],
    )
    assert result.score == RiskScore.LOW
    assert "No action needed" in result.recommended_check


def test_clear_decline_all_three_signals_bad_is_medium_or_high():
    # NDVI down substantially, rainfall well below average, temp well above.
    result = assess_field_risk(
        ndvi_readings=[0.60, 0.58, 0.50],   # ~13.8% decline vs avg of first two
        rainfall_readings_mm=[25.0, 22.0, 8.0],  # well below avg (23.5 -> 8.0)
        temp_readings_c=[21.0, 21.5, 25.0],  # +3.75C above avg
    )
    assert result.score in (RiskScore.MEDIUM, RiskScore.HIGH)
    assert any("NDVI down" in r for r in result.reasons)
    assert any("Rainfall" in r for r in result.reasons)
    assert any("Temperature" in r for r in result.reasons)
    assert "irrigation" in result.recommended_check.lower()


def test_severe_decline_with_both_contributing_factors_is_high():
    result = assess_field_risk(
        ndvi_readings=[0.70, 0.68, 0.40],   # ~42% decline — clearly severe
        rainfall_readings_mm=[30.0, 28.0, 5.0],
        temp_readings_c=[20.0, 20.0, 26.0],
    )
    assert result.score == RiskScore.HIGH


def test_ndvi_declining_but_no_contributing_factor_is_low():
    # NDVI down, but rainfall and temp both normal — could be harvest,
    # pest damage, or natural senescence, not necessarily water stress.
    # The engine should NOT flag this as Medium/High on NDVI alone.
    result = assess_field_risk(
        ndvi_readings=[0.60, 0.58, 0.48],  # ~17% decline
        rainfall_readings_mm=[20.0, 21.0, 20.5],  # normal
        temp_readings_c=[22.0, 22.1, 22.3],  # normal
    )
    assert result.score == RiskScore.LOW


def test_rainfall_deficit_alone_without_ndvi_decline_is_low():
    # Rainfall down, but vegetation hasn't responded yet — not flagged yet.
    result = assess_field_risk(
        ndvi_readings=[0.55, 0.56, 0.57],  # improving
        rainfall_readings_mm=[25.0, 24.0, 5.0],  # sharp drop
        temp_readings_c=[21.0, 21.0, 21.0],
    )
    assert result.score == RiskScore.LOW


def test_flat_ndvi_is_low_risk():
    # Edge case: perfectly flat NDVI (no baseline decline to compute).
    result = assess_field_risk(
        ndvi_readings=[0.5, 0.5, 0.5],
        rainfall_readings_mm=[10.0, 10.0, 2.0],
        temp_readings_c=[20.0, 20.0, 25.0],
    )
    assert result.score == RiskScore.LOW


def test_missing_ndvi_data_does_not_crash_and_is_low_risk():
    # Edge case: fewer than 2 valid NDVI readings (e.g. cloud cover gaps) —
    # can't compute a trend, so NDVI must not contribute to a flag.
    result = assess_field_risk(
        ndvi_readings=[0.55],
        rainfall_readings_mm=[25.0, 5.0],
        temp_readings_c=[20.0, 26.0],
    )
    assert result.score == RiskScore.LOW


def test_missing_ndvi_data_with_none_values_does_not_crash():
    # Edge case: explicit None entries mixed into the readings (cloud-masked
    # satellite pass, matching what satellite.py returns for fully-clouded
    # intervals).
    result = assess_field_risk(
        ndvi_readings=[0.6, None, 0.5],
        rainfall_readings_mm=[25.0, 20.0, 5.0],
        temp_readings_c=[20.0, 20.0, 26.0],
    )
    # Only 2 valid NDVI points remain (0.6, 0.5) -> ~16.7% decline, still
    # computable and should still flag given the other two signals.
    assert result.score in (RiskScore.MEDIUM, RiskScore.HIGH)


def test_empty_readings_do_not_crash_and_are_low_risk():
    result = assess_field_risk(
        ndvi_readings=[],
        rainfall_readings_mm=[],
        temp_readings_c=[],
    )
    assert result.score == RiskScore.LOW
    assert result.reasons  # should still return a human-readable reason, not blow up


def test_reason_strings_name_the_triggering_signals_only():
    # Only rainfall is a contributing factor (temp is normal) — the reason
    # list should mention rainfall but not fabricate a temperature reason.
    result = assess_field_risk(
        ndvi_readings=[0.60, 0.58, 0.50],
        rainfall_readings_mm=[25.0, 22.0, 8.0],
        temp_readings_c=[21.0, 21.2, 21.1],  # normal
    )
    assert result.score == RiskScore.MEDIUM
    assert any("Rainfall" in r for r in result.reasons)
    assert not any("Temperature" in r for r in result.reasons)
