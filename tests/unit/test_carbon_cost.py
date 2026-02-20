"""Unit tests for src/models/carbon.py and src/models/cost.py."""

import pytest
import pandas as pd

from src.models.carbon import apply_carbon_overlay
from src.models.cost import apply_cost_overlay
from src.models.schema import make_stub_output


def _make_electricity_df(run_id: str = "test-run") -> pd.DataFrame:
    rows = [
        make_stub_output("DE", "datacentres", "hyperscale", 2024, 1e9, 1, "ai_base", run_id),
        make_stub_output("US", "datacentres", "hyperscale", 2024, 2e9, 1, "ai_base", run_id),
    ]
    return pd.DataFrame(rows)


def _make_grid_ef_df() -> pd.DataFrame:
    return pd.DataFrame({
        "geo": ["DE", "US"],
        "year": [2024, 2024],
        "grid_ef_kgco2e_per_kwh": [0.350, 0.380],
    })


def _make_price_df() -> pd.DataFrame:
    return pd.DataFrame({
        "geo": ["DE", "US"],
        "year": [2024, 2024],
        "price_usd_per_kwh": [0.38, 0.12],
    })


def test_carbon_overlay_adds_emissions_columns():
    elec = _make_electricity_df()
    grid_ef = _make_grid_ef_df()
    result = apply_carbon_overlay(elec, grid_ef)
    assert "emissions_kgco2e" in result.columns
    assert "emissions_p10_kgco2e" in result.columns
    assert "emissions_p90_kgco2e" in result.columns


def test_carbon_overlay_correct_values():
    elec = _make_electricity_df()
    grid_ef = _make_grid_ef_df()
    result = apply_carbon_overlay(elec, grid_ef)
    de_row = result[result["geo"] == "DE"].iloc[0]
    assert de_row["emissions_kgco2e"] == pytest.approx(1e9 * 0.350)


def test_carbon_overlay_preserves_row_count():
    elec = _make_electricity_df()
    result = apply_carbon_overlay(elec, _make_grid_ef_df())
    assert len(result) == len(elec)


def test_cost_overlay_adds_cost_columns():
    elec = _make_electricity_df()
    result = apply_cost_overlay(elec, _make_price_df())
    assert "cost_usd" in result.columns
    assert "cost_p10_usd" in result.columns
    assert "cost_p90_usd" in result.columns


def test_cost_overlay_correct_values():
    elec = _make_electricity_df()
    result = apply_cost_overlay(elec, _make_price_df())
    us_row = result[result["geo"] == "US"].iloc[0]
    assert us_row["cost_usd"] == pytest.approx(2e9 * 0.12)


def test_cost_overlay_preserves_row_count():
    elec = _make_electricity_df()
    result = apply_cost_overlay(elec, _make_price_df())
    assert len(result) == len(elec)
