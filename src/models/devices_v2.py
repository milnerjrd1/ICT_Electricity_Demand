"""Devices electricity demand model — study-aligned v2.

Aligned with Fraunhofer Green ICT @ FMD study approach:
  - Uses lifespan-distribution stock-flow (inventory.py)
  - Uses four-state load profile (load_profile.py)
  - Supports reference-year parameter sets (reference_params.py)
  - Adds application_area + product_group dimensions (taxonomy.py)
  - Covers households, workplace, and public_spaces application areas

The legacy devices model (devices.py) is preserved unchanged.
This module is the new default called by the scenario engine when
gold_tables contains 'devices_v2' instead of 'devices'.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import pandas as pd

from src.models.inventory import build_stock_series
from src.models.load_profile import apply_load_profile
from src.models.reference_params import get_params
from src.models.schema import OutputRow, make_stub_output, validate_output
from src.models.taxonomy import enrich_with_taxonomy

logger = logging.getLogger(__name__)


def run_devices_v2_model(
    gold_df: pd.DataFrame,
    scenario_params: dict[str, Any],
    run_id: str | None = None,
    use_reference_params: bool = True,
) -> pd.DataFrame:
    """Run the study-aligned devices electricity demand model.

    Args:
        gold_df: Gold table DataFrame with columns:
            geo, product_group (or product), application_area (optional),
            year, shipments, avg_lifespan_years, lifespan_std_years (optional),
            power_off_w / power_ready_w / power_active_medium_w / power_active_high_w
            (or legacy: power_active_w / power_idle_w / power_sleep_w / power_off_w),
            hours_off / hours_ready / hours_active_medium / hours_active_high
            (or legacy: hours_active / hours_idle / hours_sleep / hours_off),
            confidence_tier, source_ids.
        scenario_params: Dict of scenario overrides including:
            avg_lifespan_multiplier, scenario_id.
        run_id: UUID string for this pipeline run. Generated if not provided.
        use_reference_params: If True, overlay reference-year parameters from
            configs/assumptions/reference_params/ for each product_group × year.
            Gold table values take precedence over reference params.

    Returns:
        DataFrame conforming to OutputSchema with segment='devices',
        application_area and product_group columns added.
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    scenario_id = scenario_params.get("scenario_id", "baseline")
    lifespan_multiplier = float(scenario_params.get("avg_lifespan_multiplier", 1.0))

    # Normalise product_group column
    df = gold_df.copy()
    if "product_group" not in df.columns and "product" in df.columns:
        df["product_group"] = df["product"]

    # Apply reference-year parameter overlays if requested
    if use_reference_params:
        df = _apply_reference_params(df)

    # Apply lifespan multiplier
    df["avg_lifespan_years"] = df["avg_lifespan_years"] * lifespan_multiplier

    # Compute active stock via lifespan-distribution stock-flow
    df = build_stock_series(
        df,
        lifespan_mean_col="avg_lifespan_years",
        lifespan_std_col="lifespan_std_years" if "lifespan_std_years" in df.columns else None,
        shipments_col="shipments",
    )

    # Compute annual kWh via load profile
    df = apply_load_profile(df)

    # Build output rows
    rows: list[OutputRow] = []
    for _, row in df.iterrows():
        confidence_tier = int(row.get("confidence_tier", 2))
        uncertainty_band = _tier_to_uncertainty(confidence_tier)

        rows.append(
            make_stub_output(
                geo=str(row["geo"]),
                segment="devices",
                product=str(row["product_group"]),
                year=int(row["year"]),
                kwh_estimate=float(row["annual_kwh"]),
                confidence_tier=confidence_tier,
                scenario_id=scenario_id,
                run_id=run_id,
                uncertainty_band=uncertainty_band,
                source_ids=list(row.get("source_ids", [])),
            )
        )

    result = pd.DataFrame(rows)
    result = enrich_with_taxonomy(result)

    # Preserve application_area from gold table if present
    if "application_area" in df.columns:
        area_map = df.set_index(["geo", "product_group", "year"])["application_area"].to_dict()
        result["application_area"] = [
            area_map.get((row["geo"], row["product"], row["year"]), row["application_area"])
            for _, row in result.iterrows()
        ]

    logger.info("Devices v2 model produced %d rows for run_id=%s", len(result), run_id)
    return validate_output(result, context="devices_v2")


def _apply_reference_params(df: pd.DataFrame) -> pd.DataFrame:
    """Overlay reference-year parameters onto the gold DataFrame.

    Reference params fill in missing columns only — gold table values
    (non-null) take precedence.

    Args:
        df: Gold table DataFrame with product_group and year columns.

    Returns:
        DataFrame with reference-year parameter columns filled in.
    """
    out = df.copy()

    param_cols = [
        "avg_lifespan_years", "lifespan_std_years",
        "power_off_w", "power_ready_w", "power_active_medium_w", "power_active_high_w",
        "hours_off", "hours_ready", "hours_active_medium", "hours_active_high",
    ]

    for idx, row in out.iterrows():
        product_group = str(row.get("product_group", row.get("product", "")))
        year = int(row["year"])
        ref = get_params(product_group, year)
        if not ref:
            continue
        for col in param_cols:
            if col in ref and (col not in out.columns or pd.isna(out.at[idx, col])):
                out.at[idx, col] = ref[col]

    return out


def _tier_to_uncertainty(confidence_tier: int) -> float:
    """Map confidence tier to fractional uncertainty half-width."""
    mapping = {1: 0.10, 2: 0.20, 3: 0.35}
    return mapping.get(confidence_tier, 0.35)
