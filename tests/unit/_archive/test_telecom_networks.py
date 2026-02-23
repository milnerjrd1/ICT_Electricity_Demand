"""Unit tests for src/models/telecom_networks.py."""

import pytest
import pandas as pd

from src.models.telecom_networks import (
    run_telecom_channel_model,
    derive_port_units,
    check_port_unit_layer_shares,
    LAYER_DEFAULTS,
    TELECOM_LAYERS,
    LAYER_TO_PRODUCT_GROUP,
)
from src.models.schema import REQUIRED_COLUMNS

_RUN_ID = "test-telecom-00000000-0000-0000-0000-000000000001"
_SCENARIO = {"scenario_id": "ai_base", "power_efficiency_factor": 1.0}


def _make_subscriber_gold(years: list[int] | None = None) -> pd.DataFrame:
    if years is None:
        years = [2022]
    rows = []
    for year in years:
        rows.append({
            "geo": "DE",
            "year": year,
            "mobile_subscribers": 80_000_000.0,
            "fixed_subscribers": 35_000_000.0,
            "confidence_tier": 1,
            "source_ids": ["bnetzA_2023", "itu_2023"],
        })
    return pd.DataFrame(rows)


def _make_port_unit_gold() -> pd.DataFrame:
    rows = []
    for layer in TELECOM_LAYERS:
        rows.append({
            "geo": "DE",
            "year": 2022,
            "layer": layer,
            "port_units": 100_000.0,
            "confidence_tier": 2,
            "source_ids": ["bnetzA_2023"],
        })
    return pd.DataFrame(rows)


# ── Format A (subscriber-based) ───────────────────────────────────────────────

def test_telecom_format_a_returns_valid_schema():
    gold = _make_subscriber_gold()
    result = run_telecom_channel_model(gold, _SCENARIO, run_id=_RUN_ID)
    for col in REQUIRED_COLUMNS:
        assert col in result.columns, f"Missing column: {col}"


def test_telecom_format_a_segment_is_networks():
    gold = _make_subscriber_gold()
    result = run_telecom_channel_model(gold, _SCENARIO, run_id=_RUN_ID)
    assert (result["segment"] == "networks").all()


def test_telecom_format_a_all_layers_present():
    gold = _make_subscriber_gold()
    result = run_telecom_channel_model(gold, _SCENARIO, run_id=_RUN_ID)
    products = set(result["product"].unique())
    for layer in TELECOM_LAYERS:
        expected_pg = LAYER_TO_PRODUCT_GROUP[layer]
        assert expected_pg in products, f"Missing layer product group: {expected_pg}"


def test_telecom_format_a_no_negative_kwh():
    gold = _make_subscriber_gold()
    result = run_telecom_channel_model(gold, _SCENARIO, run_id=_RUN_ID)
    assert (result["kwh_estimate"] >= 0).all()


def test_telecom_format_a_run_id_propagated():
    gold = _make_subscriber_gold()
    result = run_telecom_channel_model(gold, _SCENARIO, run_id=_RUN_ID)
    assert (result["run_id"] == _RUN_ID).all()


def test_telecom_format_a_adds_application_area():
    gold = _make_subscriber_gold()
    result = run_telecom_channel_model(gold, _SCENARIO, run_id=_RUN_ID)
    assert "application_area" in result.columns
    assert (result["application_area"] == "telecom_networks").all()


def test_telecom_format_a_power_efficiency_reduces_kwh():
    gold = _make_subscriber_gold()
    base = run_telecom_channel_model(gold, _SCENARIO, run_id=_RUN_ID)
    efficient = run_telecom_channel_model(
        gold, {**_SCENARIO, "power_efficiency_factor": 0.5}, run_id=_RUN_ID
    )
    assert efficient["kwh_estimate"].sum() < base["kwh_estimate"].sum()


def test_telecom_format_a_mobile_access_larger_than_core():
    """Mobile access should dominate over core/transport for typical subscriber counts."""
    gold = _make_subscriber_gold()
    result = run_telecom_channel_model(gold, _SCENARIO, run_id=_RUN_ID)
    mobile_kwh = result[result["product"] == "mobile_access_port"]["kwh_estimate"].sum()
    core_kwh = result[result["product"] == "core_transport_port"]["kwh_estimate"].sum()
    assert mobile_kwh > core_kwh


# ── Format B (pre-computed port units) ───────────────────────────────────────

def test_telecom_format_b_returns_valid_schema():
    gold = _make_port_unit_gold()
    result = run_telecom_channel_model(gold, _SCENARIO, run_id=_RUN_ID)
    for col in REQUIRED_COLUMNS:
        assert col in result.columns, f"Missing column: {col}"


def test_telecom_format_b_all_layers_present():
    gold = _make_port_unit_gold()
    result = run_telecom_channel_model(gold, _SCENARIO, run_id=_RUN_ID)
    assert len(result) == len(TELECOM_LAYERS)


def test_telecom_format_b_kwh_formula():
    """port_units × power_w × energy_mgmt × PUE × 8760 / 1000."""
    layer = "fixed_access"
    defaults = LAYER_DEFAULTS[layer]
    gold = pd.DataFrame([{
        "geo": "DE", "year": 2022, "layer": layer,
        "port_units": 1_000.0,
        "confidence_tier": 2, "source_ids": [],
    }])
    result = run_telecom_channel_model(gold, _SCENARIO, run_id=_RUN_ID)
    expected = (
        1_000.0
        * defaults["power_per_port_w"]
        * defaults["energy_mgmt_factor"]
        * defaults["site_pue"]
        * 8760.0 / 1000.0
    )
    actual = result["kwh_estimate"].iloc[0]
    assert abs(actual - expected) / expected < 0.01


def test_telecom_format_b_unknown_layer_skipped():
    gold = pd.DataFrame([{
        "geo": "DE", "year": 2022, "layer": "unknown_layer",
        "port_units": 100_000.0,
        "confidence_tier": 2, "source_ids": [],
    }])
    result = run_telecom_channel_model(gold, _SCENARIO, run_id=_RUN_ID)
    assert len(result) == 0


# ── derive_port_units ─────────────────────────────────────────────────────────

def test_derive_port_units_mobile_access():
    ports = derive_port_units(80_000_000.0, "mobile_access")
    defaults = LAYER_DEFAULTS["mobile_access"]
    expected = 80_000_000.0 * defaults["ports_per_connection"] * defaults["uplink_multiplier"]
    assert ports == pytest.approx(expected)


def test_derive_port_units_with_override():
    ports = derive_port_units(1_000_000.0, "fixed_access", ports_per_connection_override=2.0)
    defaults = LAYER_DEFAULTS["fixed_access"]
    expected = 1_000_000.0 * 2.0 * defaults["uplink_multiplier"]
    assert ports == pytest.approx(expected)


def test_derive_port_units_zero_connections():
    assert derive_port_units(0.0, "mobile_access") == pytest.approx(0.0)


# ── check_port_unit_layer_shares ──────────────────────────────────────────────

def test_port_unit_layer_shares_no_warnings_balanced():
    gold = _make_subscriber_gold()
    result = run_telecom_channel_model(gold, _SCENARIO, run_id=_RUN_ID)
    warnings = check_port_unit_layer_shares(result, "DE", 2022)
    # Balanced subscriber counts should not trigger >80% share warning
    assert warnings == []


def test_port_unit_layer_shares_warns_on_dominant_layer():
    """Manually construct a result where one layer has >80% share."""
    result = pd.DataFrame([
        {"geo": "DE", "year": 2022, "segment": "networks",
         "product": "mobile_access_port", "kwh_estimate": 900.0},
        {"geo": "DE", "year": 2022, "segment": "networks",
         "product": "fixed_access_port", "kwh_estimate": 50.0},
        {"geo": "DE", "year": 2022, "segment": "networks",
         "product": "aggregation_port", "kwh_estimate": 30.0},
        {"geo": "DE", "year": 2022, "segment": "networks",
         "product": "core_transport_port", "kwh_estimate": 20.0},
    ])
    warnings = check_port_unit_layer_shares(result, "DE", 2022)
    assert len(warnings) > 0
    assert "PLAUSIBILITY WARN TELECOM" in warnings[0]


def test_port_unit_layer_shares_empty_for_wrong_geo():
    gold = _make_subscriber_gold()
    result = run_telecom_channel_model(gold, _SCENARIO, run_id=_RUN_ID)
    warnings = check_port_unit_layer_shares(result, "US", 2022)
    assert warnings == []
