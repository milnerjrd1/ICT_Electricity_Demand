"""Scenario engine — applies scenario parameters to model inputs.

Loads scenario YAML configs and provides a unified interface for running
all model modules under a given scenario.
"""

import logging
import uuid
from typing import Any

import pandas as pd

from src.models.carbon import apply_carbon_overlay
from src.models.carbon_v2 import apply_carbon_overlay_v2
from src.models.cost import apply_cost_overlay
from src.models.datacentres import run_datacentres_model
from src.models.datacentres_v2 import run_datacentres_arch_model
from src.models.devices import run_devices_model
from src.models.devices_v2 import run_devices_v2_model
from src.models.networks import run_networks_model
from src.models.reporting import build_full_report
from src.models.schema import validate_output
from src.models.telecom_networks import run_telecom_channel_model
from src.scenarios.registry import load_scenario

logger = logging.getLogger(__name__)


def run_scenario(
    scenario_id: str,
    gold_tables: dict[str, pd.DataFrame],
    run_id: str | None = None,
    monte_carlo_iterations: int = 1000,
) -> pd.DataFrame:
    """Run all model modules under a named scenario and return combined outputs.

    Args:
        scenario_id: Scenario identifier (must exist in configs/scenarios/).
        gold_tables: Dict mapping table name → DataFrame. Expected keys:
            'devices', 'networks', 'datacentres', 'grid_ef', 'electricity_prices'.
        run_id: UUID string for this pipeline run. Generated if not provided.
        monte_carlo_iterations: MC iterations for Tier 1 DC outputs.

    Returns:
        Combined DataFrame of all segment outputs conforming to OutputSchema,
        with emissions and cost overlays applied.
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    scenario_params = load_scenario(scenario_id)
    scenario_params["scenario_id"] = scenario_id

    logger.info("Running scenario '%s' with run_id=%s", scenario_id, run_id)

    segment_dfs: list[pd.DataFrame] = []

    if "devices" in gold_tables and not gold_tables["devices"].empty:
        devices_df = run_devices_model(gold_tables["devices"], scenario_params, run_id=run_id)
        segment_dfs.append(devices_df)
        logger.info("Devices: %d rows", len(devices_df))

    if "networks" in gold_tables and not gold_tables["networks"].empty:
        networks_df = run_networks_model(gold_tables["networks"], scenario_params, run_id=run_id)
        segment_dfs.append(networks_df)
        logger.info("Networks: %d rows", len(networks_df))

    if "datacentres" in gold_tables and not gold_tables["datacentres"].empty:
        dc_df = run_datacentres_model(
            gold_tables["datacentres"],
            scenario_params,
            run_id=run_id,
            monte_carlo_iterations=monte_carlo_iterations,
        )
        segment_dfs.append(dc_df)
        logger.info("Datacentres: %d rows", len(dc_df))

    if not segment_dfs:
        logger.warning("No segment data available for scenario '%s'", scenario_id)
        return pd.DataFrame()

    combined = pd.concat(segment_dfs, ignore_index=True)

    if "grid_ef" in gold_tables and not gold_tables["grid_ef"].empty:
        combined = apply_carbon_overlay(combined, gold_tables["grid_ef"])

    if "electricity_prices" in gold_tables and not gold_tables["electricity_prices"].empty:
        combined = apply_cost_overlay(combined, gold_tables["electricity_prices"])

    logger.info(
        "Scenario '%s' complete: %d total rows, run_id=%s",
        scenario_id,
        len(combined),
        run_id,
    )
    return combined


def run_all_scenarios(
    scenario_ids: list[str],
    gold_tables: dict[str, pd.DataFrame],
    run_id: str | None = None,
    monte_carlo_iterations: int = 1000,
) -> dict[str, pd.DataFrame]:
    """Run multiple scenarios and return results keyed by scenario_id.

    Args:
        scenario_ids: List of scenario identifiers to run.
        gold_tables: Dict mapping table name → DataFrame.
        run_id: UUID string shared across all scenarios in this run.
        monte_carlo_iterations: MC iterations for Tier 1 DC outputs.

    Returns:
        Dict mapping scenario_id → output DataFrame.
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    results: dict[str, pd.DataFrame] = {}
    for scenario_id in scenario_ids:
        try:
            results[scenario_id] = run_scenario(
                scenario_id,
                gold_tables,
                run_id=run_id,
                monte_carlo_iterations=monte_carlo_iterations,
            )
        except Exception:
            logger.exception("Scenario '%s' failed", scenario_id)
            results[scenario_id] = pd.DataFrame()

    return results


# ── Study-aligned v2 engine ───────────────────────────────────────────────────

def run_scenario_v2(
    scenario_id: str,
    gold_tables: dict[str, pd.DataFrame],
    grid_scenario_id: str = "reference",
    run_id: str | None = None,
    report_reference_years: list[int] | None = None,
) -> dict[str, Any]:
    """Run all study-aligned model modules under a named scenario.

    Routes new gold table keys to the Fraunhofer-aligned modules:
      - 'devices_v2'       → run_devices_v2_model (inventory + load_profile)
      - 'telecom_networks' → run_telecom_channel_model (port-unit channel)
      - 'datacentres_v2'   → run_datacentres_arch_model (CPU/storage/port)

    Legacy keys ('devices', 'networks', 'datacentres') are also accepted and
    routed to the original modules for backward compatibility.

    Carbon overlay uses apply_carbon_overlay_v2 with the selected grid scenario
    (historical EFs fixed ≤ 2024; scenario decay from 2025 onward).

    Args:
        scenario_id: Demand scenario identifier (e.g. 'ai_base', 'ai_high').
        gold_tables: Dict mapping table name → DataFrame. Recognised keys:
            'devices_v2', 'telecom_networks', 'datacentres_v2',
            'devices', 'networks', 'datacentres',
            'grid_ef', 'electricity_prices'.
        grid_scenario_id: Grid mix scenario ('reference', 'ambitious', 'fossil').
        run_id: UUID string for this pipeline run. Generated if not provided.
        report_reference_years: Years for appendix tables (default [2015, 2025, 2035]).

    Returns:
        Dict with keys:
          'outputs'    — combined OutputSchema DataFrame (all segments)
          'report'     — dict of appendix DataFrames from build_full_report()
          'run_id'     — run UUID string
          'scenario_id'      — demand scenario used
          'grid_scenario_id' — grid scenario used
    """
    if run_id is None:
        run_id = str(uuid.uuid4())
    if report_reference_years is None:
        report_reference_years = [2015, 2025, 2035]

    scenario_params = load_scenario(scenario_id)
    scenario_params["scenario_id"] = scenario_id

    logger.info(
        "run_scenario_v2: demand='%s' grid='%s' run_id=%s",
        scenario_id, grid_scenario_id, run_id,
    )

    segment_dfs: list[pd.DataFrame] = []

    # ── New study-aligned modules ─────────────────────────────────────────────
    if "devices_v2" in gold_tables and not gold_tables["devices_v2"].empty:
        df = run_devices_v2_model(gold_tables["devices_v2"], scenario_params, run_id=run_id)
        segment_dfs.append(df)
        logger.info("devices_v2: %d rows", len(df))

    if "telecom_networks" in gold_tables and not gold_tables["telecom_networks"].empty:
        df = run_telecom_channel_model(
            gold_tables["telecom_networks"], scenario_params, run_id=run_id
        )
        if not df.empty:
            segment_dfs.append(df)
        logger.info("telecom_networks: %d rows", len(df))

    if "datacentres_v2" in gold_tables and not gold_tables["datacentres_v2"].empty:
        df = run_datacentres_arch_model(
            gold_tables["datacentres_v2"], scenario_params, run_id=run_id
        )
        segment_dfs.append(df)
        logger.info("datacentres_v2: %d rows", len(df))

    # ── Legacy modules (backward-compatible pass-through) ─────────────────────
    if "devices" in gold_tables and not gold_tables["devices"].empty:
        df = run_devices_model(gold_tables["devices"], scenario_params, run_id=run_id)
        segment_dfs.append(df)
        logger.info("devices (legacy): %d rows", len(df))

    if "networks" in gold_tables and not gold_tables["networks"].empty:
        df = run_networks_model(gold_tables["networks"], scenario_params, run_id=run_id)
        segment_dfs.append(df)
        logger.info("networks (legacy): %d rows", len(df))

    if "datacentres" in gold_tables and not gold_tables["datacentres"].empty:
        df = run_datacentres_model(gold_tables["datacentres"], scenario_params, run_id=run_id)
        segment_dfs.append(df)
        logger.info("datacentres (legacy): %d rows", len(df))

    if not segment_dfs:
        logger.warning("run_scenario_v2: no segment data for scenario '%s'", scenario_id)
        return {
            "outputs": pd.DataFrame(),
            "report": {},
            "run_id": run_id,
            "scenario_id": scenario_id,
            "grid_scenario_id": grid_scenario_id,
        }

    combined = pd.concat(segment_dfs, ignore_index=True)

    # ── Carbon overlay (v2 with grid scenario dispatch) ───────────────────────
    if "grid_ef" in gold_tables and not gold_tables["grid_ef"].empty:
        combined = apply_carbon_overlay_v2(
            combined,
            gold_tables["grid_ef"],
            grid_scenario_id=grid_scenario_id,
        )

    # ── Cost overlay ──────────────────────────────────────────────────────────
    if "electricity_prices" in gold_tables and not gold_tables["electricity_prices"].empty:
        combined = apply_cost_overlay(combined, gold_tables["electricity_prices"])

    # ── Appendix report ───────────────────────────────────────────────────────
    report = build_full_report(combined, reference_years=report_reference_years)

    logger.info(
        "run_scenario_v2 complete: %d rows, demand='%s', grid='%s', run_id=%s",
        len(combined), scenario_id, grid_scenario_id, run_id,
    )

    return {
        "outputs": combined,
        "report": report,
        "run_id": run_id,
        "scenario_id": scenario_id,
        "grid_scenario_id": grid_scenario_id,
    }


def run_all_scenarios_v2(
    scenario_ids: list[str],
    gold_tables: dict[str, pd.DataFrame],
    grid_scenario_ids: list[str] | None = None,
    run_id: str | None = None,
    report_reference_years: list[int] | None = None,
) -> dict[str, dict[str, Any]]:
    """Run multiple demand × grid scenario combinations using the v2 engine.

    Args:
        scenario_ids: List of demand scenario identifiers.
        gold_tables: Dict mapping table name → DataFrame.
        grid_scenario_ids: Grid scenarios to cross with each demand scenario.
            Defaults to ['reference', 'ambitious', 'fossil'].
        run_id: UUID string shared across all runs.
        report_reference_years: Years for appendix tables.

    Returns:
        Nested dict: {demand_scenario_id: {grid_scenario_id: result_dict}}.
    """
    if run_id is None:
        run_id = str(uuid.uuid4())
    if grid_scenario_ids is None:
        grid_scenario_ids = ["reference", "ambitious", "fossil"]

    results: dict[str, dict[str, Any]] = {}
    for scenario_id in scenario_ids:
        results[scenario_id] = {}
        for grid_id in grid_scenario_ids:
            try:
                results[scenario_id][grid_id] = run_scenario_v2(
                    scenario_id,
                    gold_tables,
                    grid_scenario_id=grid_id,
                    run_id=run_id,
                    report_reference_years=report_reference_years,
                )
            except Exception:
                logger.exception(
                    "run_all_scenarios_v2 failed: demand='%s' grid='%s'",
                    scenario_id, grid_id,
                )
                results[scenario_id][grid_id] = {
                    "outputs": pd.DataFrame(),
                    "report": {},
                    "run_id": run_id,
                    "scenario_id": scenario_id,
                    "grid_scenario_id": grid_id,
                }

    return results
