"""Unit tests for src/models/load_profile.py."""

import pytest
import pandas as pd

from src.models.load_profile import (
    PowerStateProfile,
    annual_kwh_per_unit,
    profile_from_legacy,
    apply_load_profile,
)


# ── annual_kwh_per_unit ───────────────────────────────────────────────────────

def test_annual_kwh_all_zero():
    profile = PowerStateProfile(
        power_off_w=0.0, power_ready_w=0.0,
        power_active_medium_w=0.0, power_active_high_w=0.0,
        hours_off=8760.0, hours_ready=0.0,
        hours_active_medium=0.0, hours_active_high=0.0,
    )
    assert annual_kwh_per_unit(profile) == pytest.approx(0.0)


def test_annual_kwh_simple_calculation():
    # 100 W active for 1000 h = 100 kWh
    profile = PowerStateProfile(
        power_off_w=0.0, power_ready_w=0.0,
        power_active_medium_w=100.0, power_active_high_w=0.0,
        hours_off=0.0, hours_ready=0.0,
        hours_active_medium=1000.0, hours_active_high=0.0,
    )
    assert annual_kwh_per_unit(profile) == pytest.approx(100.0)


def test_annual_kwh_all_states():
    profile = PowerStateProfile(
        power_off_w=0.1, power_ready_w=5.0,
        power_active_medium_w=15.0, power_active_high_w=35.0,
        hours_off=1760.0, hours_ready=3000.0,
        hours_active_medium=2500.0, hours_active_high=500.0,
    )
    expected = (1760 * 0.1 + 3000 * 5.0 + 2500 * 15.0 + 500 * 35.0) / 1000.0
    assert annual_kwh_per_unit(profile) == pytest.approx(expected)


def test_annual_kwh_non_negative():
    profile = PowerStateProfile(
        power_off_w=-1.0, power_ready_w=0.0,
        power_active_medium_w=0.0, power_active_high_w=0.0,
        hours_off=8760.0, hours_ready=0.0,
        hours_active_medium=0.0, hours_active_high=0.0,
    )
    # Negative power should be floored to 0
    assert annual_kwh_per_unit(profile) >= 0.0


# ── profile_from_legacy ───────────────────────────────────────────────────────

def test_profile_from_legacy_active_maps_to_medium():
    p = profile_from_legacy(
        power_active_w=15.0, power_idle_w=5.0,
        power_sleep_w=1.0, power_off_w=0.1,
        hours_active=2000, hours_idle=2000,
        hours_sleep=3000, hours_off=1760,
    )
    assert p["power_active_medium_w"] == pytest.approx(15.0)
    assert p["power_ready_w"] == pytest.approx(5.0)
    assert p["hours_active_medium"] == pytest.approx(2000.0)
    assert p["hours_ready"] == pytest.approx(2000.0)


def test_profile_from_legacy_sleep_merged_into_off():
    p = profile_from_legacy(
        power_active_w=15.0, power_idle_w=5.0,
        power_sleep_w=1.0, power_off_w=0.1,
        hours_active=2000, hours_idle=2000,
        hours_sleep=3000, hours_off=1760,
    )
    # Total off hours = sleep + off
    assert p["hours_off"] == pytest.approx(3000.0 + 1760.0)
    # Effective off power = weighted average
    expected_off_w = (3000 * 1.0 + 1760 * 0.1) / (3000 + 1760)
    assert p["power_off_w"] == pytest.approx(expected_off_w)


def test_profile_from_legacy_active_high_zero():
    p = profile_from_legacy(
        power_active_w=15.0, power_idle_w=5.0,
        power_sleep_w=1.0, power_off_w=0.1,
        hours_active=2000, hours_idle=2000,
        hours_sleep=3000, hours_off=1760,
    )
    assert p["hours_active_high"] == pytest.approx(0.0)


def test_profile_from_legacy_energy_conservation():
    """Legacy and new-style profiles should give same kWh for equivalent inputs."""
    legacy_p = profile_from_legacy(
        power_active_w=15.0, power_idle_w=5.0,
        power_sleep_w=0.0, power_off_w=0.0,
        hours_active=2000, hours_idle=2000,
        hours_sleep=0, hours_off=4760,
    )
    legacy_kwh = annual_kwh_per_unit(legacy_p)
    # Direct calculation: 2000h × 15W + 2000h × 5W = 40 kWh
    assert legacy_kwh == pytest.approx(40.0)


# ── apply_load_profile ────────────────────────────────────────────────────────

def _make_stock_df(new_style: bool = True) -> pd.DataFrame:
    if new_style:
        return pd.DataFrame([{
            "geo": "DE", "product_group": "laptop_hh", "year": 2022,
            "active_stock": 10_000_000.0,
            "power_off_w": 0.1, "power_ready_w": 5.0,
            "power_active_medium_w": 15.0, "power_active_high_w": 35.0,
            "hours_off": 1760.0, "hours_ready": 3000.0,
            "hours_active_medium": 2500.0, "hours_active_high": 500.0,
        }])
    else:
        return pd.DataFrame([{
            "geo": "DE", "product_group": "laptop_hh", "year": 2022,
            "active_stock": 10_000_000.0,
            "power_active_w": 15.0, "power_idle_w": 5.0,
            "power_sleep_w": 1.0, "power_off_w": 0.1,
            "hours_active": 2000.0, "hours_idle": 2000.0,
            "hours_sleep": 3000.0, "hours_off": 1760.0,
        }])


def test_apply_load_profile_adds_kwh_columns():
    df = _make_stock_df(new_style=True)
    result = apply_load_profile(df)
    assert "kwh_per_unit" in result.columns
    assert "annual_kwh" in result.columns


def test_apply_load_profile_annual_kwh_positive():
    df = _make_stock_df(new_style=True)
    result = apply_load_profile(df)
    assert result["annual_kwh"].iloc[0] > 0


def test_apply_load_profile_annual_kwh_equals_stock_times_per_unit():
    df = _make_stock_df(new_style=True)
    result = apply_load_profile(df)
    assert result["annual_kwh"].iloc[0] == pytest.approx(
        result["active_stock"].iloc[0] * result["kwh_per_unit"].iloc[0]
    )


def test_apply_load_profile_legacy_style():
    df = _make_stock_df(new_style=False)
    result = apply_load_profile(df)
    assert "annual_kwh" in result.columns
    assert result["annual_kwh"].iloc[0] > 0


def test_apply_load_profile_zero_stock_gives_zero_kwh():
    df = _make_stock_df(new_style=True)
    df["active_stock"] = 0.0
    result = apply_load_profile(df)
    assert result["annual_kwh"].iloc[0] == pytest.approx(0.0)
