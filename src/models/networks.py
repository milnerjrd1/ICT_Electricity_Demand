"""Networks electricity demand model module.

Equipment inventory approach scaled from regulator data and traffic proxies.
Formula:
    equipment_count(geo, type, t) = subscribers(geo, t) × equipment_per_sub(type)
                                     OR base_stations(geo, t) from regulator data
    annual_kwh(geo, type, t) = equipment_count × power_per_unit(type, t) × utilisation_factor(t)
"""

import logging
import uuid
from typing import Any

import pandas as pd

from src.models.schema import OutputRow, make_stub_output, validate_output

logger = logging.getLogger(__name__)


def run_networks_model(
    gold_df: pd.DataFrame,
    scenario_params: dict[str, Any],
    run_id: str | None = None,
) -> pd.DataFrame:
    """Run the networks electricity demand model.

    Args:
        gold_df: Gold table DataFrame with columns:
            geo, product, year, equipment_count, power_per_unit_w,
            utilisation_factor, confidence_tier, source_ids.
            'product' is the network type (e.g. '5g_base_station', 'fixed_broadband_cpe').
        scenario_params: Dict of scenario overrides (e.g. {'utilisation_multiplier': 1.05}).
        run_id: UUID string for this pipeline run. Generated if not provided.

    Returns:
        DataFrame conforming to OutputSchema with segment='networks'.
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    scenario_id = scenario_params.get("scenario_id", "baseline")
    utilisation_multiplier = float(scenario_params.get("utilisation_multiplier", 1.0))
    power_efficiency_factor = float(scenario_params.get("power_efficiency_factor", 1.0))

    rows: list[OutputRow] = []

    for _, row in gold_df.iterrows():
        effective_power_w = row["power_per_unit_w"] * power_efficiency_factor
        effective_utilisation = min(1.0, row["utilisation_factor"] * utilisation_multiplier)

        annual_kwh = (
            row["equipment_count"]
            * effective_power_w
            * effective_utilisation
            * 8760.0
            / 1000.0
        )

        confidence_tier = int(row.get("confidence_tier", 2))
        uncertainty_band = _tier_to_uncertainty(confidence_tier)

        rows.append(
            make_stub_output(
                geo=str(row["geo"]),
                segment="networks",
                product=str(row["product"]),
                year=int(row["year"]),
                kwh_estimate=annual_kwh,
                confidence_tier=confidence_tier,
                scenario_id=scenario_id,
                run_id=run_id,
                uncertainty_band=uncertainty_band,
                source_ids=list(row.get("source_ids", [])),
            )
        )

    result = pd.DataFrame(rows)
    logger.info("Networks model produced %d rows for run_id=%s", len(result), run_id)
    return validate_output(result, context="networks")


def _tier_to_uncertainty(confidence_tier: int) -> float:
    """Map confidence tier to fractional uncertainty half-width.

    Args:
        confidence_tier: 1, 2, or 3.

    Returns:
        Fractional half-width (e.g. 0.10 = ±10%).
    """
    mapping = {1: 0.10, 2: 0.20, 3: 0.35}
    return mapping.get(confidence_tier, 0.35)
