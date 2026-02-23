"""Scenario engine — applies scenario parameters to model inputs.

Loads scenario YAML configs and provides a unified interface for running
all model modules under a given scenario.
"""

import logging
import uuid
from typing import Any

import pandas as pd

from src.models.carbon import apply_carbon_overlay
from src.models.cost import apply_cost_overlay
from src.models.datacentres import run_datacentres_model
from src.models.devices import run_devices_model
from src.models.networks import run_networks_model
from src.models.schema import validate_output
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
