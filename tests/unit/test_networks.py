"""Unit tests for src/models/networks.py."""

import pytest
import pandas as pd

from src.models.networks import run_networks_model
from src.models.schema import REQUIRED_COLUMNS


def test_networks_model_returns_valid_schema(germany_networks_gold, scenario_baseline, run_id):
    result = run_networks_model(germany_networks_gold, scenario_baseline, run_id=run_id)
    for col in REQUIRED_COLUMNS:
        assert col in result.columns, f"Missing column: {col}"


def test_networks_model_segment_is_networks(germany_networks_gold, scenario_baseline, run_id):
    result = run_networks_model(germany_networks_gold, scenario_baseline, run_id=run_id)
    assert (result["segment"] == "networks").all()


def test_networks_model_no_negative_kwh(germany_networks_gold, scenario_baseline, run_id):
    result = run_networks_model(germany_networks_gold, scenario_baseline, run_id=run_id)
    assert (result["kwh_estimate"] >= 0).all()


def test_networks_model_run_id_propagated(germany_networks_gold, scenario_baseline, run_id):
    result = run_networks_model(germany_networks_gold, scenario_baseline, run_id=run_id)
    assert (result["run_id"] == run_id).all()


def test_networks_model_efficiency_reduces_kwh(germany_networks_gold, scenario_baseline, run_id):
    """Power efficiency factor < 1 should reduce electricity demand."""
    base = run_networks_model(germany_networks_gold, scenario_baseline, run_id=run_id)
    efficient = {**scenario_baseline, "power_efficiency_factor": 0.8}
    result_eff = run_networks_model(germany_networks_gold, efficient, run_id=run_id)
    assert result_eff["kwh_estimate"].sum() < base["kwh_estimate"].sum()


def test_networks_model_p10_le_p90(germany_networks_gold, scenario_baseline, run_id):
    result = run_networks_model(germany_networks_gold, scenario_baseline, run_id=run_id)
    assert (result["kwh_p10"] <= result["kwh_p90"]).all()


def test_networks_model_confidence_tier_preserved(germany_networks_gold, scenario_baseline, run_id):
    result = run_networks_model(germany_networks_gold, scenario_baseline, run_id=run_id)
    assert result["confidence_tier"].isin([1, 2, 3]).all()
