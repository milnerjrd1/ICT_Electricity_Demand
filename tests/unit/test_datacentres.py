"""Unit tests for src/models/datacentres.py."""

import pytest
import pandas as pd

from src.models.datacentres import run_datacentres_model
from src.models.schema import REQUIRED_COLUMNS


def test_dc_model_returns_valid_schema(germany_dc_gold, scenario_baseline, run_id):
    result = run_datacentres_model(germany_dc_gold, scenario_baseline, run_id=run_id)
    for col in REQUIRED_COLUMNS:
        assert col in result.columns, f"Missing column: {col}"


def test_dc_model_segment_is_datacentres(germany_dc_gold, scenario_baseline, run_id):
    result = run_datacentres_model(germany_dc_gold, scenario_baseline, run_id=run_id)
    assert (result["segment"] == "datacentres").all()


def test_dc_model_no_negative_kwh(germany_dc_gold, scenario_baseline, run_id):
    result = run_datacentres_model(germany_dc_gold, scenario_baseline, run_id=run_id)
    assert (result["kwh_estimate"] >= 0).all()


def test_dc_model_run_id_propagated(germany_dc_gold, scenario_baseline, run_id):
    result = run_datacentres_model(germany_dc_gold, scenario_baseline, run_id=run_id)
    assert (result["run_id"] == run_id).all()


def test_dc_model_p10_le_p90(germany_dc_gold, scenario_baseline, run_id):
    result = run_datacentres_model(germany_dc_gold, scenario_baseline, run_id=run_id)
    assert (result["kwh_p10"] <= result["kwh_p90"]).all()


def test_dc_model_pue_improvement_reduces_kwh(germany_dc_gold, scenario_baseline, run_id):
    """Higher PUE improvement rate should reduce total electricity over time."""
    base = run_datacentres_model(germany_dc_gold, scenario_baseline, run_id=run_id)
    improved = {**scenario_baseline, "pue_improvement_rate": 0.10}
    result_improved = run_datacentres_model(germany_dc_gold, improved, run_id=run_id)
    assert result_improved["kwh_estimate"].sum() <= base["kwh_estimate"].sum()


def test_dc_model_monte_carlo_produces_bands(germany_dc_gold, scenario_baseline, run_id):
    """Monte Carlo should produce P10 < P50 < P90 for Tier 1 rows."""
    result = run_datacentres_model(
        germany_dc_gold, scenario_baseline, run_id=run_id, monte_carlo_iterations=200
    )
    tier1 = result[result["confidence_tier"] == 1]
    assert len(tier1) > 0
    assert (tier1["kwh_p10"] < tier1["kwh_p50"]).all()
    assert (tier1["kwh_p50"] < tier1["kwh_p90"]).all()


def test_dc_model_kwh_formula_plausible(germany_dc_gold, scenario_baseline, run_id):
    """Spot-check: 750 MW × 0.65 utilisation × 1.15 PUE × 8760h × 1000 ≈ 4.91 TWh.

    Fixture updated to Borderstep 2023 calibrated values (750 MW hyperscale).
    scenario_baseline has pue_improvement_rate=0.02; year 2020 is the base year
    so years_elapsed=0 and effective_pue = 1.15 × (1-0.02)^0 = 1.15 exactly.
    """
    result = run_datacentres_model(germany_dc_gold, scenario_baseline, run_id=run_id)
    hyperscale_2020 = result[(result["product"] == "hyperscale") & (result["year"] == 2020)]
    assert len(hyperscale_2020) == 1
    expected_kwh = 750.0 * 0.65 * 1.15 * 8760.0 * 1000.0
    actual_kwh = hyperscale_2020["kwh_estimate"].iloc[0]
    assert abs(actual_kwh - expected_kwh) / expected_kwh < 0.01
