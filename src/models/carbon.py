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
    # Forward-fill: carry each geo's latest known EF into future years
    ef = grid_ef_df[["geo", "year", "grid_ef_kgco2e_per_kwh"]].copy()
    all_years = electricity_df["year"].unique()
    latest_ef = (
        ef.sort_values("year")
        .groupby("geo", as_index=False)
        .last()
        .rename(columns={"year": "_ef_year"})
    )
    future_rows: list[pd.DataFrame] = []
    for _, row in latest_ef.iterrows():
        future_yrs = [y for y in all_years if y > row["_ef_year"]]
        if future_yrs:
            future_rows.append(pd.DataFrame({
                "geo": row["geo"],
                "year": future_yrs,
                "grid_ef_kgco2e_per_kwh": row["grid_ef_kgco2e_per_kwh"],
            }))
    if future_rows:
        ef = pd.concat([ef, pd.concat(future_rows, ignore_index=True)], ignore_index=True)
        logger.info("Forward-filled grid EF for %d geo×year combinations", sum(len(f) for f in future_rows))

    merged = electricity_df.merge(ef, on=["geo", "year"], how="left")

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
