"""Carbon emissions overlay — grid scenario dispatch (v2).

Extends carbon.py with three grid mix scenarios from 2025 onward:
  - reference: moderate decarbonisation (current policy)
  - ambitious: accelerated decarbonisation (1.5°C-aligned)
  - fossil: slow decarbonisation (fossil persistence)

Historical emission factors (≤ 2024) are fixed regardless of scenario.
From 2025 onward, the scenario applies an annual EF reduction rate
multiplicatively to the 2024 baseline.

Usage:
    from src.models.carbon_v2 import apply_carbon_overlay_v2
    result = apply_carbon_overlay_v2(electricity_df, grid_ef_df, grid_scenario_id='reference')
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

logger = logging.getLogger(__name__)

SCENARIOS_DIR = Path("configs/scenarios")
HISTORICAL_ANCHOR_YEAR = 2024

# Fallback global rates if scenario YAML not found
_FALLBACK_RATES: dict[str, float] = {
    "reference": 0.030,
    "ambitious": 0.060,
    "fossil":    0.010,
}


def _load_grid_scenario(grid_scenario_id: str) -> dict[str, Any]:
    """Load grid mix scenario YAML by grid_scenario_id.

    Args:
        grid_scenario_id: One of 'reference', 'ambitious', 'fossil'.

    Returns:
        Parsed YAML dict, or minimal fallback dict if file not found.
    """
    path = SCENARIOS_DIR / f"grid_mix_{grid_scenario_id}.yaml"
    if not path.exists():
        logger.warning("Grid scenario file not found: %s — using fallback rate", path)
        return {
            "grid_scenario_id": grid_scenario_id,
            "historical_anchor_year": HISTORICAL_ANCHOR_YEAR,
            "annual_ef_reduction_rate": _FALLBACK_RATES.get(grid_scenario_id, 0.030),
            "geo_overrides": {},
        }
    with open(path) as f:
        return yaml.safe_load(f)


def _compute_ef(
    base_ef: float,
    year: int,
    anchor_year: int,
    annual_rate: float,
) -> float:
    """Compute emission factor for a given year using exponential decay from anchor.

    Args:
        base_ef: Emission factor at anchor_year (kgCO2e/kWh).
        year: Target year.
        anchor_year: Year from which the scenario rate applies.
        annual_rate: Annual fractional reduction rate (e.g. 0.03 = 3%/yr).

    Returns:
        Emission factor for the target year (kgCO2e/kWh), floored at 0.005.
    """
    if year <= anchor_year:
        return base_ef
    years_ahead = year - anchor_year
    ef = base_ef * (1.0 - annual_rate) ** years_ahead
    return max(0.005, ef)


def build_grid_ef_scenario(
    grid_ef_df: pd.DataFrame,
    grid_scenario_id: str = "reference",
    years: list[int] | None = None,
) -> pd.DataFrame:
    """Build a grid emission factor DataFrame for all geo/year combinations.

    Historical years (≤ anchor_year) use the values from grid_ef_df directly.
    Future years (> anchor_year) apply the scenario decay rate.

    Args:
        grid_ef_df: DataFrame with columns: geo, year, grid_ef_kgco2e_per_kwh.
            Must contain at least the anchor year (2024) for each geo.
        grid_scenario_id: Grid scenario identifier ('reference', 'ambitious', 'fossil').
        years: List of years to generate. Defaults to 2010–2036.

    Returns:
        DataFrame with columns: geo, year, grid_ef_kgco2e_per_kwh, grid_scenario_id.
    """
    if years is None:
        years = list(range(2010, 2037))

    scenario = _load_grid_scenario(grid_scenario_id)
    anchor_year = int(scenario.get("historical_anchor_year", HISTORICAL_ANCHOR_YEAR))
    global_rate = float(scenario.get("annual_ef_reduction_rate", 0.030))
    geo_overrides: dict[str, dict[str, float]] = scenario.get("geo_overrides", {}) or {}

    # Build anchor EF lookup: geo → ef at anchor_year
    anchor_ef: dict[str, float] = {}
    for _, row in grid_ef_df.iterrows():
        if int(row["year"]) == anchor_year:
            anchor_ef[str(row["geo"])] = float(row["grid_ef_kgco2e_per_kwh"])

    # Historical lookup: (geo, year) → ef
    historical: dict[tuple[str, int], float] = {
        (str(r["geo"]), int(r["year"])): float(r["grid_ef_kgco2e_per_kwh"])
        for _, r in grid_ef_df.iterrows()
    }

    rows: list[dict[str, Any]] = []
    geos = grid_ef_df["geo"].unique()

    for geo in geos:
        geo_str = str(geo)
        rate = float(geo_overrides.get(geo_str, {}).get("annual_ef_reduction_rate", global_rate))
        base_ef = anchor_ef.get(geo_str)

        for year in years:
            hist_ef = historical.get((geo_str, year))
            if year <= anchor_year and hist_ef is not None:
                ef = hist_ef
            elif base_ef is not None:
                ef = _compute_ef(base_ef, year, anchor_year, rate)
            elif hist_ef is not None:
                ef = hist_ef
            else:
                # No data at all — skip
                continue

            rows.append({
                "geo": geo_str,
                "year": year,
                "grid_ef_kgco2e_per_kwh": ef,
                "grid_scenario_id": grid_scenario_id,
            })

    df = pd.DataFrame(rows)
    logger.info(
        "Grid EF scenario '%s' built: %d geo×year combinations",
        grid_scenario_id, len(df),
    )
    return df


def apply_carbon_overlay_v2(
    electricity_df: pd.DataFrame,
    grid_ef_df: pd.DataFrame,
    grid_scenario_id: str = "reference",
) -> pd.DataFrame:
    """Apply grid emission factors with scenario dispatch to electricity output.

    Historical years (≤ 2024) use fixed EFs. From 2025 onward, the selected
    grid scenario's decay rate is applied.

    Args:
        electricity_df: Output DataFrame conforming to OutputSchema.
        grid_ef_df: DataFrame with columns: geo, year, grid_ef_kgco2e_per_kwh.
            Must cover at least the anchor year (2024) for each geo.
        grid_scenario_id: Grid scenario ('reference', 'ambitious', 'fossil').

    Returns:
        Input DataFrame with additional columns:
            emissions_kgco2e, emissions_p10_kgco2e, emissions_p50_kgco2e,
            emissions_p90_kgco2e, grid_scenario_id.
    """
    years_needed = sorted(electricity_df["year"].unique().tolist())
    scenario_ef_df = build_grid_ef_scenario(
        grid_ef_df,
        grid_scenario_id=grid_scenario_id,
        years=years_needed,
    )

    merged = electricity_df.merge(
        scenario_ef_df[["geo", "year", "grid_ef_kgco2e_per_kwh"]],
        on=["geo", "year"],
        how="left",
    )

    missing = merged["grid_ef_kgco2e_per_kwh"].isnull().sum()
    if missing > 0:
        logger.warning("%d rows missing grid EF for scenario '%s'", missing, grid_scenario_id)

    merged["emissions_kgco2e"] = merged["kwh_estimate"] * merged["grid_ef_kgco2e_per_kwh"]
    merged["emissions_p10_kgco2e"] = merged["kwh_p10"] * merged["grid_ef_kgco2e_per_kwh"]
    merged["emissions_p50_kgco2e"] = merged["kwh_p50"] * merged["grid_ef_kgco2e_per_kwh"]
    merged["emissions_p90_kgco2e"] = merged["kwh_p90"] * merged["grid_ef_kgco2e_per_kwh"]
    merged["grid_scenario_id"] = grid_scenario_id
    merged = merged.drop(columns=["grid_ef_kgco2e_per_kwh"])

    logger.info(
        "Carbon overlay v2 applied: %d rows, grid_scenario='%s'",
        len(merged), grid_scenario_id,
    )
    return merged
