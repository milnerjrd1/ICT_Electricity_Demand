"""Unit tests for src/models/datacentres_v2.py."""

import pytest
import pandas as pd

from src.models.datacentres_v2 import (
    run_datacentres_arch_model,
    check_rack_power_plausibility,
    check_cpu_unit_count_plausibility,
)
from src.models.schema import REQUIRED_COLUMNS

_RUN_ID = "test-dc-v2-00000000-0000-0000-0000-000000000001"
_SCENARIO = {"scenario_id": "ai_base", "pue_improvement_rate": 0.0, "utilisation_multiplier": 1.0}


def _make_dc_arch_gold(years: list[int] | None = None) -> pd.DataFrame:
    if years is None:
        years = [2022]
    rows = []
    for year in years:
        rows.extend([
            {
                "geo": "DE", "product_group": "cpu_unit", "year": year,
                "unit_count": 500_000.0,
                "power_per_unit_w": 250.0,
                "utilisation": 0.55,
                "pue": 1.40,
                "confidence_tier": 1,
                "source_ids": ["borderstep_2023"],
            },
            {
                "geo": "DE", "product_group": "hdd_unit", "year": year,
                "unit_count": 2_000_000.0,
                "power_per_unit_w": 6.0,
                "confidence_tier": 2,
                "source_ids": ["borderstep_2023"],
            },
            {
                "geo": "DE", "product_group": "ssd_unit", "year": year,
                "unit_count": 1_000_000.0,
                "power_per_unit_w": 2.0,
                "confidence_tier": 2,
                "source_ids": ["borderstep_2023"],
            },
            {
                "geo": "DE", "product_group": "dc_port_unit", "year": year,
                "unit_count": 3_000_000.0,
                "power_per_unit_w": 1.5,
                "utilisation": 0.60,
                "confidence_tier": 2,
                "source_ids": ["borderstep_2023"],
            },
        ])
    return pd.DataFrame(rows)


def test_dc_arch_model_returns_valid_schema():
    gold = _make_dc_arch_gold()
    result = run_datacentres_arch_model(gold, _SCENARIO, run_id=_RUN_ID)
    for col in REQUIRED_COLUMNS:
        assert col in result.columns, f"Missing column: {col}"


def test_dc_arch_model_segment_is_datacentres():
    gold = _make_dc_arch_gold()
    result = run_datacentres_arch_model(gold, _SCENARIO, run_id=_RUN_ID)
    assert (result["segment"] == "datacentres").all()


def test_dc_arch_model_no_negative_kwh():
    gold = _make_dc_arch_gold()
    result = run_datacentres_arch_model(gold, _SCENARIO, run_id=_RUN_ID)
    assert (result["kwh_estimate"] >= 0).all()


def test_dc_arch_model_run_id_propagated():
    gold = _make_dc_arch_gold()
    result = run_datacentres_arch_model(gold, _SCENARIO, run_id=_RUN_ID)
    assert (result["run_id"] == _RUN_ID).all()


def test_dc_arch_model_all_unit_types_present():
    gold = _make_dc_arch_gold()
    result = run_datacentres_arch_model(gold, _SCENARIO, run_id=_RUN_ID)
    products = set(result["product"].unique())
    assert "cpu_unit" in products
    assert "hdd_unit" in products
    assert "ssd_unit" in products
    assert "dc_port_unit" in products


def test_dc_arch_model_cpu_kwh_formula():
    """cpu_units × power_w × utilisation × PUE × 8760 / 1000."""
    gold = pd.DataFrame([{
        "geo": "DE", "product_group": "cpu_unit", "year": 2022,
        "unit_count": 1_000.0,
        "power_per_unit_w": 250.0,
        "utilisation": 0.55,
        "pue": 1.40,
        "confidence_tier": 1,
        "source_ids": [],
    }])
    result = run_datacentres_arch_model(gold, _SCENARIO, run_id=_RUN_ID)
    expected = 1_000.0 * 250.0 * 0.55 * 1.40 * 8760.0 / 1000.0
    actual = result[result["product"] == "cpu_unit"]["kwh_estimate"].iloc[0]
    assert abs(actual - expected) / expected < 0.01


def test_dc_arch_model_pue_improvement_reduces_kwh():
    gold = _make_dc_arch_gold(years=[2022, 2027])
    improved = {**_SCENARIO, "pue_improvement_rate": 0.05}
    result = run_datacentres_arch_model(gold, improved, run_id=_RUN_ID)
    cpu_2022 = result[(result["product"] == "cpu_unit") & (result["year"] == 2022)]["kwh_estimate"].iloc[0]
    cpu_2027 = result[(result["product"] == "cpu_unit") & (result["year"] == 2027)]["kwh_estimate"].iloc[0]
    assert cpu_2027 < cpu_2022


def test_dc_arch_model_adds_application_area():
    gold = _make_dc_arch_gold()
    result = run_datacentres_arch_model(gold, _SCENARIO, run_id=_RUN_ID)
    assert "application_area" in result.columns
    assert (result["application_area"] == "datacentres").all()


# ── Plausibility checks ───────────────────────────────────────────────────────

def test_rack_power_plausibility_no_warnings_normal():
    gold = _make_dc_arch_gold()
    warnings = check_rack_power_plausibility(gold)
    assert warnings == []


def test_rack_power_plausibility_warns_on_high_power():
    gold = pd.DataFrame([{
        "geo": "DE", "product_group": "cpu_unit", "year": 2022,
        "unit_count": 1_000.0,
        "power_per_unit_w": 2000.0,  # 2000W per CPU × 40 per rack = 80 kW >> 30 kW threshold
        "utilisation": 0.55, "pue": 1.40,
        "confidence_tier": 1, "source_ids": [],
    }])
    warnings = check_rack_power_plausibility(gold)
    assert len(warnings) > 0
    assert "PLAUSIBILITY WARN DC" in warnings[0]


def test_cpu_unit_count_plausibility_no_proxy():
    gold = _make_dc_arch_gold()
    warnings = check_cpu_unit_count_plausibility(gold, server_count_proxy_df=None)
    assert warnings == []


def test_cpu_unit_count_plausibility_within_tolerance():
    gold = _make_dc_arch_gold()
    proxy = pd.DataFrame([{"geo": "DE", "year": 2022, "server_count_proxy": 490_000.0}])
    warnings = check_cpu_unit_count_plausibility(gold, server_count_proxy_df=proxy, tolerance=0.30)
    assert warnings == []  # 500k vs 490k = 2% deviation < 30%


def test_cpu_unit_count_plausibility_outside_tolerance():
    gold = _make_dc_arch_gold()
    proxy = pd.DataFrame([{"geo": "DE", "year": 2022, "server_count_proxy": 200_000.0}])
    warnings = check_cpu_unit_count_plausibility(gold, server_count_proxy_df=proxy, tolerance=0.30)
    assert len(warnings) > 0
    assert "PLAUSIBILITY WARN DC" in warnings[0]
