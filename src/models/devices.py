"""Devices electricity demand model module.

Stock-flow inventory model with usage profiles and power-state weighting.
Formula:
    installed_base(t) = installed_base(t-1) + shipments(t) - retirements(t)
    retirements(t)    = installed_base(t - avg_lifespan)
    annual_kwh        = Σ_states [installed_base × hours_per_year(state) × power_draw_W(state)] / 1000
"""

import logging
import uuid
from typing import Any

import pandas as pd

from src.models.schema import OutputRow, make_stub_output, validate_output

logger = logging.getLogger(__name__)


def run_devices_model(
    gold_df: pd.DataFrame,
    scenario_params: dict[str, Any],
    run_id: str | None = None,
) -> pd.DataFrame:
    """Run the devices electricity demand model.

    Args:
        gold_df: Gold table DataFrame with columns:
            geo, product, year, shipments, avg_lifespan_years,
            power_active_w, power_idle_w, power_sleep_w, power_off_w,
            hours_active, hours_idle, hours_sleep, hours_off,
            confidence_tier, source_ids.
        scenario_params: Dict of scenario overrides (e.g. {'avg_lifespan_multiplier': 1.1}).
        run_id: UUID string for this pipeline run. Generated if not provided.

    Returns:
        DataFrame conforming to OutputSchema with segment='devices'.
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    scenario_id = scenario_params.get("scenario_id", "baseline")
    lifespan_multiplier = float(scenario_params.get("avg_lifespan_multiplier", 1.0))

    rows: list[OutputRow] = []

    for (geo, product), group in gold_df.groupby(["geo", "product"]):
        group = group.sort_values("year").copy()
        group["avg_lifespan_years"] = group["avg_lifespan_years"] * lifespan_multiplier

        installed_base = 0.0
        base_history: list[float] = []

        for _, row in group.iterrows():
            lifespan = int(round(row["avg_lifespan_years"]))
            retirements = base_history[-lifespan] if len(base_history) >= lifespan else 0.0
            installed_base = installed_base + row["shipments"] - retirements
            installed_base = max(0.0, installed_base)
            base_history.append(installed_base)

            annual_kwh = (
                installed_base
                * (
                    row["hours_active"] * row["power_active_w"]
                    + row["hours_idle"] * row["power_idle_w"]
                    + row["hours_sleep"] * row["power_sleep_w"]
                    + row["hours_off"] * row["power_off_w"]
                )
                / 1000.0
            )

            confidence_tier = int(row.get("confidence_tier", 2))
            uncertainty_band = _tier_to_uncertainty(confidence_tier)

            rows.append(
                make_stub_output(
                    geo=str(geo),
                    segment="devices",
                    product=str(product),
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
    logger.info("Devices model produced %d rows for run_id=%s", len(result), run_id)
    return validate_output(result, context="devices")


def _tier_to_uncertainty(confidence_tier: int) -> float:
    """Map confidence tier to fractional uncertainty half-width.

    Args:
        confidence_tier: 1, 2, or 3.

    Returns:
        Fractional half-width (e.g. 0.10 = ±10%).
    """
    mapping = {1: 0.10, 2: 0.20, 3: 0.35}
    return mapping.get(confidence_tier, 0.35)
