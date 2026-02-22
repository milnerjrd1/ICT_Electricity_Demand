"""Integration tests — full v2 pipeline (study-aligned modules end-to-end)."""

import pytest
import pandas as pd

from src.scenarios.engine import run_scenario_v2, run_all_scenarios_v2
from src.models.schema import REQUIRED_COLUMNS, validate_output
from src.validation.plausibility import check_no_negative_kwh


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gold_tables(
    devices_v2,
    telecom,
    dc_arch,
    grid_ef,
    electricity_prices,
) -> dict:
    return {
        "devices_v2":       devices_v2,
        "telecom_networks": telecom,
        "datacentres_v2":   dc_arch,
        "grid_ef":          grid_ef,
        "electricity_prices": electricity_prices,
    }


# ── Full v2 pipeline ──────────────────────────────────────────────────────────

def test_run_scenario_v2_returns_dict(
    germany_devices_v2_gold,
    germany_telecom_gold,
    germany_dc_arch_gold,
    grid_ef_germany_v2,
    electricity_prices_germany,
    run_id,
):
    tables = _gold_tables(
        germany_devices_v2_gold,
        germany_telecom_gold,
        germany_dc_arch_gold,
        grid_ef_germany_v2,
        electricity_prices_germany,
    )
    result = run_scenario_v2("ai_base", tables, grid_scenario_id="reference", run_id=run_id)
    assert isinstance(result, dict)
    assert "outputs" in result
    assert "report" in result
    assert "run_id" in result
    assert "scenario_id" in result
    assert "grid_scenario_id" in result


def test_run_scenario_v2_outputs_valid_schema(
    germany_devices_v2_gold,
    germany_telecom_gold,
    germany_dc_arch_gold,
    grid_ef_germany_v2,
    electricity_prices_germany,
    run_id,
):
    tables = _gold_tables(
        germany_devices_v2_gold,
        germany_telecom_gold,
        germany_dc_arch_gold,
        grid_ef_germany_v2,
        electricity_prices_germany,
    )
    result = run_scenario_v2("ai_base", tables, grid_scenario_id="reference", run_id=run_id)
    outputs = result["outputs"]
    assert not outputs.empty
    validate_output(outputs, context="integration_v2")


def test_run_scenario_v2_all_segments_present(
    germany_devices_v2_gold,
    germany_telecom_gold,
    germany_dc_arch_gold,
    grid_ef_germany_v2,
    electricity_prices_germany,
    run_id,
):
    tables = _gold_tables(
        germany_devices_v2_gold,
        germany_telecom_gold,
        germany_dc_arch_gold,
        grid_ef_germany_v2,
        electricity_prices_germany,
    )
    result = run_scenario_v2("ai_base", tables, run_id=run_id)
    segments = set(result["outputs"]["segment"].unique())
    assert "devices" in segments
    assert "networks" in segments
    assert "datacentres" in segments


def test_run_scenario_v2_all_application_areas_present(
    germany_devices_v2_gold,
    germany_telecom_gold,
    germany_dc_arch_gold,
    grid_ef_germany_v2,
    electricity_prices_germany,
    run_id,
):
    tables = _gold_tables(
        germany_devices_v2_gold,
        germany_telecom_gold,
        germany_dc_arch_gold,
        grid_ef_germany_v2,
        electricity_prices_germany,
    )
    result = run_scenario_v2("ai_base", tables, run_id=run_id)
    areas = set(result["outputs"]["application_area"].unique())
    assert "households" in areas
    assert "workplace" in areas
    assert "public_spaces" in areas
    assert "telecom_networks" in areas
    assert "datacentres" in areas


def test_run_scenario_v2_no_negative_kwh(
    germany_devices_v2_gold,
    germany_telecom_gold,
    germany_dc_arch_gold,
    grid_ef_germany_v2,
    electricity_prices_germany,
    run_id,
):
    tables = _gold_tables(
        germany_devices_v2_gold,
        germany_telecom_gold,
        germany_dc_arch_gold,
        grid_ef_germany_v2,
        electricity_prices_germany,
    )
    result = run_scenario_v2("ai_base", tables, run_id=run_id)
    violations = check_no_negative_kwh(result["outputs"])
    assert violations == [], f"Negative kWh: {violations}"


def test_run_scenario_v2_run_id_consistent(
    germany_devices_v2_gold,
    germany_telecom_gold,
    germany_dc_arch_gold,
    grid_ef_germany_v2,
    electricity_prices_germany,
    run_id,
):
    tables = _gold_tables(
        germany_devices_v2_gold,
        germany_telecom_gold,
        germany_dc_arch_gold,
        grid_ef_germany_v2,
        electricity_prices_germany,
    )
    result = run_scenario_v2("ai_base", tables, run_id=run_id)
    assert result["run_id"] == run_id
    assert result["outputs"]["run_id"].nunique() == 1
    assert result["outputs"]["run_id"].iloc[0] == run_id


def test_run_scenario_v2_carbon_overlay_applied(
    germany_devices_v2_gold,
    germany_telecom_gold,
    germany_dc_arch_gold,
    grid_ef_germany_v2,
    electricity_prices_germany,
    run_id,
):
    tables = _gold_tables(
        germany_devices_v2_gold,
        germany_telecom_gold,
        germany_dc_arch_gold,
        grid_ef_germany_v2,
        electricity_prices_germany,
    )
    result = run_scenario_v2("ai_base", tables, grid_scenario_id="reference", run_id=run_id)
    assert "emissions_kgco2e" in result["outputs"].columns
    assert "grid_scenario_id" in result["outputs"].columns
    assert (result["outputs"]["grid_scenario_id"] == "reference").all()


def test_run_scenario_v2_cost_overlay_applied(
    germany_devices_v2_gold,
    germany_telecom_gold,
    germany_dc_arch_gold,
    grid_ef_germany_v2,
    electricity_prices_germany,
    run_id,
):
    tables = _gold_tables(
        germany_devices_v2_gold,
        germany_telecom_gold,
        germany_dc_arch_gold,
        grid_ef_germany_v2,
        electricity_prices_germany,
    )
    result = run_scenario_v2("ai_base", tables, run_id=run_id)
    assert "cost_usd" in result["outputs"].columns


def test_run_scenario_v2_report_has_all_keys(
    germany_devices_v2_gold,
    germany_telecom_gold,
    germany_dc_arch_gold,
    grid_ef_germany_v2,
    electricity_prices_germany,
    run_id,
):
    tables = _gold_tables(
        germany_devices_v2_gold,
        germany_telecom_gold,
        germany_dc_arch_gold,
        grid_ef_germany_v2,
        electricity_prices_germany,
    )
    result = run_scenario_v2(
        "ai_base", tables, run_id=run_id,
        report_reference_years=[2022, 2025],
    )
    report = result["report"]
    assert "appendix_table" in report
    assert "by_application_area" in report
    assert "total_ict" in report


def test_run_scenario_v2_report_non_empty(
    germany_devices_v2_gold,
    germany_telecom_gold,
    germany_dc_arch_gold,
    grid_ef_germany_v2,
    electricity_prices_germany,
    run_id,
):
    tables = _gold_tables(
        germany_devices_v2_gold,
        germany_telecom_gold,
        germany_dc_arch_gold,
        grid_ef_germany_v2,
        electricity_prices_germany,
    )
    result = run_scenario_v2(
        "ai_base", tables, run_id=run_id,
        report_reference_years=[2022, 2025],
    )
    for key, df in result["report"].items():
        assert isinstance(df, pd.DataFrame), f"report['{key}'] is not a DataFrame"
        assert len(df) > 0, f"report['{key}'] is empty"


# ── Grid scenario differentiation ────────────────────────────────────────────

def test_ambitious_grid_lower_emissions_than_reference(
    germany_devices_v2_gold,
    germany_telecom_gold,
    germany_dc_arch_gold,
    grid_ef_germany_v2,
    electricity_prices_germany,
    run_id,
):
    """Ambitious grid should produce lower total emissions than reference for future years."""
    tables = _gold_tables(
        germany_devices_v2_gold,
        germany_telecom_gold,
        germany_dc_arch_gold,
        grid_ef_germany_v2,
        electricity_prices_germany,
    )
    ref = run_scenario_v2("ai_base", tables, grid_scenario_id="reference", run_id=run_id)
    amb = run_scenario_v2("ai_base", tables, grid_scenario_id="ambitious", run_id=run_id)

    ref_em = ref["outputs"][ref["outputs"]["year"] == 2025]["emissions_kgco2e"].sum()
    amb_em = amb["outputs"][amb["outputs"]["year"] == 2025]["emissions_kgco2e"].sum()
    assert amb_em < ref_em


def test_fossil_grid_higher_emissions_than_reference(
    germany_devices_v2_gold,
    germany_telecom_gold,
    germany_dc_arch_gold,
    grid_ef_germany_v2,
    electricity_prices_germany,
    run_id,
):
    tables = _gold_tables(
        germany_devices_v2_gold,
        germany_telecom_gold,
        germany_dc_arch_gold,
        grid_ef_germany_v2,
        electricity_prices_germany,
    )
    ref    = run_scenario_v2("ai_base", tables, grid_scenario_id="reference", run_id=run_id)
    fossil = run_scenario_v2("ai_base", tables, grid_scenario_id="fossil",    run_id=run_id)

    ref_em    = ref["outputs"][ref["outputs"]["year"] == 2025]["emissions_kgco2e"].sum()
    fossil_em = fossil["outputs"][fossil["outputs"]["year"] == 2025]["emissions_kgco2e"].sum()
    assert fossil_em > ref_em


# ── run_all_scenarios_v2 ──────────────────────────────────────────────────────

def test_run_all_scenarios_v2_returns_nested_dict(
    germany_devices_v2_gold,
    germany_telecom_gold,
    germany_dc_arch_gold,
    grid_ef_germany_v2,
    electricity_prices_germany,
    run_id,
):
    tables = _gold_tables(
        germany_devices_v2_gold,
        germany_telecom_gold,
        germany_dc_arch_gold,
        grid_ef_germany_v2,
        electricity_prices_germany,
    )
    results = run_all_scenarios_v2(
        ["ai_base", "ai_low"],
        tables,
        grid_scenario_ids=["reference", "ambitious"],
        run_id=run_id,
    )
    assert set(results.keys()) == {"ai_base", "ai_low"}
    for demand_id, grid_results in results.items():
        assert set(grid_results.keys()) == {"reference", "ambitious"}
        for grid_id, result in grid_results.items():
            assert "outputs" in result
            assert not result["outputs"].empty, (
                f"Empty outputs for demand='{demand_id}' grid='{grid_id}'"
            )


# ── Backward-compat: legacy gold tables still work through v2 engine ──────────

def test_run_scenario_v2_accepts_legacy_gold_tables(
    germany_devices_gold,
    germany_networks_gold,
    germany_dc_gold,
    grid_ef_germany_v2,
    electricity_prices_germany,
    run_id,
):
    """Legacy gold table keys should still work via the v2 engine."""
    tables = {
        "devices":            germany_devices_gold,
        "networks":           germany_networks_gold,
        "datacentres":        germany_dc_gold,
        "grid_ef":            grid_ef_germany_v2,
        "electricity_prices": electricity_prices_germany,
    }
    result = run_scenario_v2("ai_base", tables, run_id=run_id)
    assert not result["outputs"].empty
    segments = set(result["outputs"]["segment"].unique())
    assert "devices" in segments
    assert "networks" in segments
    assert "datacentres" in segments


def test_run_scenario_v2_mixed_legacy_and_v2_gold_tables(
    germany_devices_v2_gold,
    germany_networks_gold,
    germany_dc_arch_gold,
    grid_ef_germany_v2,
    electricity_prices_germany,
    run_id,
):
    """Mixing v2 and legacy gold tables should produce combined outputs."""
    tables = {
        "devices_v2":         germany_devices_v2_gold,
        "networks":           germany_networks_gold,
        "datacentres_v2":     germany_dc_arch_gold,
        "grid_ef":            grid_ef_germany_v2,
        "electricity_prices": electricity_prices_germany,
    }
    result = run_scenario_v2("ai_base", tables, run_id=run_id)
    assert not result["outputs"].empty
    segments = set(result["outputs"]["segment"].unique())
    assert "devices" in segments
    assert "networks" in segments
    assert "datacentres" in segments


def test_run_scenario_v2_empty_gold_tables_returns_empty(run_id):
    result = run_scenario_v2("ai_base", {}, run_id=run_id)
    assert result["outputs"].empty
    assert result["report"] == {}
