"""Integration tests — full pipeline from gold tables through model outputs."""

import pytest
import pandas as pd

from src.models.devices import run_devices_model
from src.models.networks import run_networks_model
from src.models.datacentres import run_datacentres_model
from src.models.carbon import apply_carbon_overlay
from src.models.cost import apply_cost_overlay
from src.models.schema import REQUIRED_COLUMNS, validate_output
from src.validation.plausibility import run_all_checks, check_no_negative_kwh


def test_full_germany_pipeline(
    germany_devices_gold,
    germany_networks_gold,
    germany_dc_gold,
    grid_ef_germany,
    electricity_prices_germany,
    scenario_baseline,
    run_id,
):
    """Full pipeline: gold tables → model outputs → overlays → plausibility checks."""
    devices = run_devices_model(germany_devices_gold, scenario_baseline, run_id=run_id)
    networks = run_networks_model(germany_networks_gold, scenario_baseline, run_id=run_id)
    dc = run_datacentres_model(germany_dc_gold, scenario_baseline, run_id=run_id)

    combined = pd.concat([devices, networks, dc], ignore_index=True)

    # Schema valid
    validate_output(combined, context="integration_test")

    # Overlays
    combined = apply_carbon_overlay(combined, grid_ef_germany)
    combined = apply_cost_overlay(combined, electricity_prices_germany)

    assert "emissions_kgco2e" in combined.columns
    assert "cost_usd" in combined.columns

    # Plausibility — only check no negative kWh here; YoY checks belong in
    # tests/plausibility/ where fixture data has smooth growth by design.
    neg_violations = check_no_negative_kwh(combined)
    assert neg_violations == [], f"Negative kWh violations: {neg_violations}"


def test_combined_output_has_all_segments(
    germany_devices_gold,
    germany_networks_gold,
    germany_dc_gold,
    scenario_baseline,
    run_id,
):
    devices = run_devices_model(germany_devices_gold, scenario_baseline, run_id=run_id)
    networks = run_networks_model(germany_networks_gold, scenario_baseline, run_id=run_id)
    dc = run_datacentres_model(germany_dc_gold, scenario_baseline, run_id=run_id)
    combined = pd.concat([devices, networks, dc], ignore_index=True)

    assert set(combined["segment"].unique()) == {"devices", "networks", "datacentres"}


def test_run_id_consistent_across_segments(
    germany_devices_gold,
    germany_networks_gold,
    germany_dc_gold,
    scenario_baseline,
    run_id,
):
    devices = run_devices_model(germany_devices_gold, scenario_baseline, run_id=run_id)
    networks = run_networks_model(germany_networks_gold, scenario_baseline, run_id=run_id)
    dc = run_datacentres_model(germany_dc_gold, scenario_baseline, run_id=run_id)
    combined = pd.concat([devices, networks, dc], ignore_index=True)

    assert combined["run_id"].nunique() == 1
    assert combined["run_id"].iloc[0] == run_id


def test_multi_geo_dc_pipeline(multi_geo_dc_gold, scenario_baseline, run_id):
    result = run_datacentres_model(multi_geo_dc_gold, scenario_baseline, run_id=run_id)
    assert result["geo"].nunique() == 6
    validate_output(result, context="multi_geo_dc")
    plausibility = run_all_checks(result)
    assert sum(len(v) for v in plausibility.values()) == 0
