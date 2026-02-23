"""Unit tests for src/models/carbon_v2.py."""

import pytest
import pandas as pd

from src.models.carbon_v2 import (
    _compute_ef,
    build_grid_ef_scenario,
    apply_carbon_overlay_v2,
)


def _make_grid_ef_df() -> pd.DataFrame:
    """Minimal grid EF DataFrame with 2024 anchor values for DE and GB."""
    return pd.DataFrame([
        {"geo": "DE", "year": 2020, "grid_ef_kgco2e_per_kwh": 0.400},
        {"geo": "DE", "year": 2021, "grid_ef_kgco2e_per_kwh": 0.385},
        {"geo": "DE", "year": 2022, "grid_ef_kgco2e_per_kwh": 0.370},
        {"geo": "DE", "year": 2023, "grid_ef_kgco2e_per_kwh": 0.360},
        {"geo": "DE", "year": 2024, "grid_ef_kgco2e_per_kwh": 0.350},
        {"geo": "GB", "year": 2024, "grid_ef_kgco2e_per_kwh": 0.210},
    ])


def _make_electricity_df() -> pd.DataFrame:
    from src.models.schema import make_stub_output
    rows = [
        make_stub_output("DE", "datacentres", "cpu_unit", yr, 1e9, 1, "ai_base", "test-run")
        for yr in [2022, 2025, 2030]
    ]
    return pd.DataFrame(rows)


# ── _compute_ef ───────────────────────────────────────────────────────────────

def test_compute_ef_historical_year_unchanged():
    ef = _compute_ef(0.35, year=2024, anchor_year=2024, annual_rate=0.03)
    assert ef == pytest.approx(0.35)


def test_compute_ef_past_year_unchanged():
    ef = _compute_ef(0.35, year=2020, anchor_year=2024, annual_rate=0.03)
    assert ef == pytest.approx(0.35)


def test_compute_ef_future_year_decreases():
    ef = _compute_ef(0.35, year=2025, anchor_year=2024, annual_rate=0.03)
    assert ef < 0.35
    assert ef == pytest.approx(0.35 * 0.97, rel=1e-6)


def test_compute_ef_floored_at_minimum():
    # Very aggressive rate over many years should floor at 0.005
    ef = _compute_ef(0.35, year=2100, anchor_year=2024, annual_rate=0.20)
    assert ef == pytest.approx(0.005)


def test_compute_ef_monotonically_decreasing():
    efs = [_compute_ef(0.35, yr, 2024, 0.03) for yr in range(2024, 2036)]
    for i in range(len(efs) - 1):
        assert efs[i] >= efs[i + 1]


# ── build_grid_ef_scenario ────────────────────────────────────────────────────

def test_build_grid_ef_scenario_returns_dataframe():
    df = _make_grid_ef_df()
    result = build_grid_ef_scenario(df, "reference", years=[2022, 2025, 2030])
    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0


def test_build_grid_ef_scenario_has_required_columns():
    df = _make_grid_ef_df()
    result = build_grid_ef_scenario(df, "reference", years=[2022, 2025])
    assert "geo" in result.columns
    assert "year" in result.columns
    assert "grid_ef_kgco2e_per_kwh" in result.columns
    assert "grid_scenario_id" in result.columns


def test_build_grid_ef_scenario_historical_year_fixed():
    """EF for 2022 should match the historical value regardless of scenario."""
    df = _make_grid_ef_df()
    for scenario in ["reference", "ambitious", "fossil"]:
        result = build_grid_ef_scenario(df, scenario, years=[2022])
        de_2022 = result[(result["geo"] == "DE") & (result["year"] == 2022)]
        assert len(de_2022) == 1
        assert de_2022["grid_ef_kgco2e_per_kwh"].iloc[0] == pytest.approx(0.370)


def test_build_grid_ef_scenario_ambitious_lower_than_reference_2030():
    df = _make_grid_ef_df()
    ref = build_grid_ef_scenario(df, "reference", years=[2030])
    amb = build_grid_ef_scenario(df, "ambitious", years=[2030])
    ref_de = ref[ref["geo"] == "DE"]["grid_ef_kgco2e_per_kwh"].iloc[0]
    amb_de = amb[amb["geo"] == "DE"]["grid_ef_kgco2e_per_kwh"].iloc[0]
    assert amb_de < ref_de


def test_build_grid_ef_scenario_fossil_higher_than_reference_2030():
    df = _make_grid_ef_df()
    ref = build_grid_ef_scenario(df, "reference", years=[2030])
    fossil = build_grid_ef_scenario(df, "fossil", years=[2030])
    ref_de = ref[ref["geo"] == "DE"]["grid_ef_kgco2e_per_kwh"].iloc[0]
    fossil_de = fossil[fossil["geo"] == "DE"]["grid_ef_kgco2e_per_kwh"].iloc[0]
    assert fossil_de > ref_de


def test_build_grid_ef_scenario_all_ef_positive():
    df = _make_grid_ef_df()
    for scenario in ["reference", "ambitious", "fossil"]:
        result = build_grid_ef_scenario(df, scenario, years=list(range(2020, 2036)))
        assert (result["grid_ef_kgco2e_per_kwh"] > 0).all()


def test_build_grid_ef_scenario_scenario_id_column():
    df = _make_grid_ef_df()
    result = build_grid_ef_scenario(df, "ambitious", years=[2025])
    assert (result["grid_scenario_id"] == "ambitious").all()


# ── apply_carbon_overlay_v2 ───────────────────────────────────────────────────

def test_apply_carbon_overlay_v2_adds_emissions_columns():
    elec = _make_electricity_df()
    grid = _make_grid_ef_df()
    result = apply_carbon_overlay_v2(elec, grid, grid_scenario_id="reference")
    assert "emissions_kgco2e" in result.columns
    assert "emissions_p10_kgco2e" in result.columns
    assert "emissions_p50_kgco2e" in result.columns
    assert "emissions_p90_kgco2e" in result.columns
    assert "grid_scenario_id" in result.columns


def test_apply_carbon_overlay_v2_scenario_id_propagated():
    elec = _make_electricity_df()
    grid = _make_grid_ef_df()
    result = apply_carbon_overlay_v2(elec, grid, grid_scenario_id="ambitious")
    assert (result["grid_scenario_id"] == "ambitious").all()


def test_apply_carbon_overlay_v2_ambitious_lower_emissions_2030():
    """Ambitious scenario should produce lower emissions in 2030 than reference."""
    elec = _make_electricity_df()
    grid = _make_grid_ef_df()
    ref = apply_carbon_overlay_v2(elec, grid, "reference")
    amb = apply_carbon_overlay_v2(elec, grid, "ambitious")
    ref_2030 = ref[ref["year"] == 2030]["emissions_kgco2e"].sum()
    amb_2030 = amb[amb["year"] == 2030]["emissions_kgco2e"].sum()
    assert amb_2030 < ref_2030


def test_apply_carbon_overlay_v2_historical_year_same_across_scenarios():
    """2022 emissions should be identical regardless of grid scenario."""
    elec = _make_electricity_df()
    grid = _make_grid_ef_df()
    ref = apply_carbon_overlay_v2(elec, grid, "reference")
    amb = apply_carbon_overlay_v2(elec, grid, "ambitious")
    fossil = apply_carbon_overlay_v2(elec, grid, "fossil")
    ref_2022 = ref[ref["year"] == 2022]["emissions_kgco2e"].sum()
    amb_2022 = amb[amb["year"] == 2022]["emissions_kgco2e"].sum()
    fossil_2022 = fossil[fossil["year"] == 2022]["emissions_kgco2e"].sum()
    assert ref_2022 == pytest.approx(amb_2022, rel=1e-6)
    assert ref_2022 == pytest.approx(fossil_2022, rel=1e-6)


def test_apply_carbon_overlay_v2_no_negative_emissions():
    elec = _make_electricity_df()
    grid = _make_grid_ef_df()
    result = apply_carbon_overlay_v2(elec, grid, "reference")
    assert (result["emissions_kgco2e"].dropna() >= 0).all()
