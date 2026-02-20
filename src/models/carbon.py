"""Carbon emissions overlay module.

Applies grid emission factors to electricity outputs.
Formula:
    emissions(geo, segment, t) = kwh(geo, segment, t) × grid_ef(geo, t)  [kgCO2e]
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def apply_carbon_overlay(
    electricity_df: pd.DataFrame,
    grid_ef_df: pd.DataFrame,
) -> pd.DataFrame:
    """Apply grid emission factors to electricity output DataFrame.

    Args:
        electricity_df: Output DataFrame conforming to OutputSchema (with kwh_estimate etc.).
        grid_ef_df: DataFrame with columns: geo, year, grid_ef_kgco2e_per_kwh.

    Returns:
        Input DataFrame with additional columns:
            emissions_kgco2e, emissions_p10_kgco2e, emissions_p50_kgco2e, emissions_p90_kgco2e.
    """
    merged = electricity_df.merge(grid_ef_df[["geo", "year", "grid_ef_kgco2e_per_kwh"]], on=["geo", "year"], how="left")

    missing_ef = merged["grid_ef_kgco2e_per_kwh"].isnull().sum()
    if missing_ef > 0:
        logger.warning("%d rows missing grid emission factor — emissions will be NaN", missing_ef)

    merged["emissions_kgco2e"] = merged["kwh_estimate"] * merged["grid_ef_kgco2e_per_kwh"]
    merged["emissions_p10_kgco2e"] = merged["kwh_p10"] * merged["grid_ef_kgco2e_per_kwh"]
    merged["emissions_p50_kgco2e"] = merged["kwh_p50"] * merged["grid_ef_kgco2e_per_kwh"]
    merged["emissions_p90_kgco2e"] = merged["kwh_p90"] * merged["grid_ef_kgco2e_per_kwh"]

    merged = merged.drop(columns=["grid_ef_kgco2e_per_kwh"])
    logger.info("Carbon overlay applied to %d rows", len(merged))
    return merged
