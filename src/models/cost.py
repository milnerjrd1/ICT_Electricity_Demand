"""Cost overlay module.

Applies electricity price scenarios to electricity outputs.
Formula:
    cost(geo, segment, t) = kwh(geo, segment, t) × price(geo, t)  [€/$]
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def apply_cost_overlay(
    electricity_df: pd.DataFrame,
    price_df: pd.DataFrame,
) -> pd.DataFrame:
    """Apply electricity prices to electricity output DataFrame.

    Args:
        electricity_df: Output DataFrame conforming to OutputSchema (with kwh_estimate etc.).
        price_df: DataFrame with columns: geo, year, price_usd_per_kwh.

    Returns:
        Input DataFrame with additional columns:
            cost_usd, cost_p10_usd, cost_p50_usd, cost_p90_usd.
    """
    # Forward-fill: carry each geo's latest known price into future years
    prices = price_df[["geo", "year", "price_usd_per_kwh"]].copy()
    all_years = electricity_df["year"].unique()
    latest_price = (
        prices.sort_values("year")
        .groupby("geo", as_index=False)
        .last()
        .rename(columns={"year": "_price_year"})
    )
    future_rows: list[pd.DataFrame] = []
    for _, row in latest_price.iterrows():
        future_yrs = [y for y in all_years if y > row["_price_year"]]
        if future_yrs:
            future_rows.append(pd.DataFrame({
                "geo": row["geo"],
                "year": future_yrs,
                "price_usd_per_kwh": row["price_usd_per_kwh"],
            }))
    if future_rows:
        prices = pd.concat([prices, pd.concat(future_rows, ignore_index=True)], ignore_index=True)
        logger.info("Forward-filled electricity prices for %d geo×year combinations", sum(len(f) for f in future_rows))

    merged = electricity_df.merge(prices, on=["geo", "year"], how="left")

    missing_price = merged["price_usd_per_kwh"].isnull().sum()
    if missing_price > 0:
        logger.warning("%d rows missing electricity price — cost will be NaN", missing_price)

    merged["cost_usd"] = merged["kwh_estimate"] * merged["price_usd_per_kwh"]
    merged["cost_p10_usd"] = merged["kwh_p10"] * merged["price_usd_per_kwh"]
    merged["cost_p50_usd"] = merged["kwh_p50"] * merged["price_usd_per_kwh"]
    merged["cost_p90_usd"] = merged["kwh_p90"] * merged["price_usd_per_kwh"]

    merged = merged.drop(columns=["price_usd_per_kwh"])
    logger.info("Cost overlay applied to %d rows", len(merged))
    return merged
