"""Unit tests for src/models/devices.py."""

import pytest
import pandas as pd

from src.models.devices import run_devices_model
from src.models.schema import REQUIRED_COLUMNS


def test_devices_model_returns_valid_schema(germany_devices_gold, scenario_baseline, run_id):
    result = run_devices_model(germany_devices_gold, scenario_baseline, run_id=run_id)
    for col in REQUIRED_COLUMNS:
        assert col in result.columns, f"Missing column: {col}"


def test_devices_model_segment_is_devices(germany_devices_gold, scenario_baseline, run_id):
    result = run_devices_model(germany_devices_gold, scenario_baseline, run_id=run_id)
    assert (result["segment"] == "devices").all()


def test_devices_model_no_negative_kwh(germany_devices_gold, scenario_baseline, run_id):
    result = run_devices_model(germany_devices_gold, scenario_baseline, run_id=run_id)
    assert (result["kwh_estimate"] >= 0).all()


def test_devices_model_run_id_propagated(germany_devices_gold, scenario_baseline, run_id):
    result = run_devices_model(germany_devices_gold, scenario_baseline, run_id=run_id)
    assert (result["run_id"] == run_id).all()


def test_devices_model_lifespan_multiplier_increases_kwh(germany_devices_gold, scenario_baseline, run_id):
    """Longer lifespan → larger installed base → higher electricity."""
    base = run_devices_model(germany_devices_gold, scenario_baseline, run_id=run_id)
    long_life = {**scenario_baseline, "avg_lifespan_multiplier": 2.0}
    result_long = run_devices_model(germany_devices_gold, long_life, run_id=run_id)
    # Longer lifespan means fewer retirements → larger base → more kWh
    assert result_long["kwh_estimate"].sum() >= base["kwh_estimate"].sum()


def test_devices_model_geo_preserved(germany_devices_gold, scenario_baseline, run_id):
    result = run_devices_model(germany_devices_gold, scenario_baseline, run_id=run_id)
    assert (result["geo"] == "DE").all()


def test_devices_model_p10_le_p90(germany_devices_gold, scenario_baseline, run_id):
    result = run_devices_model(germany_devices_gold, scenario_baseline, run_id=run_id)
    assert (result["kwh_p10"] <= result["kwh_p90"]).all()
