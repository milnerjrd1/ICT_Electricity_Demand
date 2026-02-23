"""Appendix-style reporting module.

Produces study-aligned output tables:
  - Per product group: inventory, kWh, emissions for reference years 2015/2025/2035
  - Aggregated totals by application area
  - Overall ICT-in-scope totals

All functions accept the standard OutputSchema DataFrame (with optional
application_area / product_group columns added by enrich_with_taxonomy).
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from src.models.taxonomy import APPLICATION_AREAS, enrich_with_taxonomy

logger = logging.getLogger(__name__)

DEFAULT_REFERENCE_YEARS: list[int] = [2015, 2025, 2035]


def build_appendix_table(
    results_df: pd.DataFrame,
    reference_years: list[int] = DEFAULT_REFERENCE_YEARS,
    include_emissions: bool = True,
    include_inventory: bool = True,
) -> pd.DataFrame:
    """Build an appendix-style wide-format results table per product group.

    Columns: application_area, product_group, metric, {year_1}, {year_2}, {year_3}, ...
    Metrics: kwh_twh, emissions_mtco2e (if include_emissions), inventory_units (if include_inventory).

    Args:
        results_df: Combined output DataFrame conforming to OutputSchema,
            with application_area and product_group columns (added automatically
            if absent via enrich_with_taxonomy).
        reference_years: Calendar years to include as columns (default [2015, 2025, 2035]).
        include_emissions: Include emissions rows (requires emissions_kgco2e column).
        include_inventory: Include inventory rows (requires active_stock column, optional).

    Returns:
        Wide-format DataFrame with one row per (product_group, metric).
    """
    df = enrich_with_taxonomy(results_df)

    # Filter to reference years only
    df_ref = df[df["year"].isin(reference_years)].copy()

    if df_ref.empty:
        logger.warning("No data for reference years %s — returning empty appendix table", reference_years)
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []

    group_cols = ["application_area", "product_group", "year"]
    agg: dict[str, str] = {"kwh_p50": "sum"}
    if include_emissions and "emissions_kgco2e" in df_ref.columns:
        agg["emissions_kgco2e"] = "sum"
    if include_inventory and "active_stock" in df_ref.columns:
        agg["active_stock"] = "sum"

    grouped = df_ref.groupby(group_cols).agg(agg).reset_index()

    for (area, pg), pg_group in grouped.groupby(["application_area", "product_group"]):
        # kWh row (TWh)
        kwh_row: dict[str, Any] = {
            "application_area": area,
            "product_group": pg,
            "metric": "kwh_twh",
        }
        for yr in reference_years:
            yr_data = pg_group[pg_group["year"] == yr]
            kwh_row[str(yr)] = round(float(yr_data["kwh_p50"].sum()) / 1e9, 4) if not yr_data.empty else None
        rows.append(kwh_row)

        # Emissions row (MtCO2e)
        if include_emissions and "emissions_kgco2e" in grouped.columns:
            em_row: dict[str, Any] = {
                "application_area": area,
                "product_group": pg,
                "metric": "emissions_mtco2e",
            }
            for yr in reference_years:
                yr_data = pg_group[pg_group["year"] == yr]
                em_row[str(yr)] = round(float(yr_data["emissions_kgco2e"].sum()) / 1e12, 6) if not yr_data.empty else None
            rows.append(em_row)

        # Inventory row (millions of units)
        if include_inventory and "active_stock" in grouped.columns:
            inv_row: dict[str, Any] = {
                "application_area": area,
                "product_group": pg,
                "metric": "inventory_munits",
            }
            for yr in reference_years:
                yr_data = pg_group[pg_group["year"] == yr]
                inv_row[str(yr)] = round(float(yr_data["active_stock"].sum()) / 1e6, 3) if not yr_data.empty else None
            rows.append(inv_row)

    result = pd.DataFrame(rows)
    result = result.sort_values(["application_area", "product_group", "metric"]).reset_index(drop=True)
    logger.info(
        "Appendix table built: %d rows, %d product groups, reference years=%s",
        len(result),
        result["product_group"].nunique() if not result.empty else 0,
        reference_years,
    )
    return result


def aggregate_by_application_area(
    results_df: pd.DataFrame,
    reference_years: list[int] = DEFAULT_REFERENCE_YEARS,
) -> pd.DataFrame:
    """Aggregate electricity and emissions by application area for reference years.

    Args:
        results_df: Combined output DataFrame with application_area column.
        reference_years: Calendar years to include.

    Returns:
        DataFrame with columns: application_area, year, kwh_twh,
        kwh_p10_twh, kwh_p90_twh, emissions_mtco2e (if available).
    """
    df = enrich_with_taxonomy(results_df)
    df_ref = df[df["year"].isin(reference_years)].copy()

    if df_ref.empty:
        return pd.DataFrame()

    agg_cols: dict[str, str] = {
        "kwh_p50": "sum",
        "kwh_p10": "sum",
        "kwh_p90": "sum",
    }
    if "emissions_kgco2e" in df_ref.columns:
        agg_cols["emissions_kgco2e"] = "sum"

    grouped = df_ref.groupby(["application_area", "year"]).agg(agg_cols).reset_index()
    grouped["kwh_twh"] = grouped["kwh_p50"] / 1e9
    grouped["kwh_p10_twh"] = grouped["kwh_p10"] / 1e9
    grouped["kwh_p90_twh"] = grouped["kwh_p90"] / 1e9
    if "emissions_kgco2e" in grouped.columns:
        grouped["emissions_mtco2e"] = grouped["emissions_kgco2e"] / 1e12

    drop_cols = [c for c in ["kwh_p50", "kwh_p10", "kwh_p90", "emissions_kgco2e"] if c in grouped.columns]
    grouped = grouped.drop(columns=drop_cols)

    logger.info("Application area aggregation: %d rows", len(grouped))
    return grouped.sort_values(["application_area", "year"]).reset_index(drop=True)


def aggregate_total_ict(
    results_df: pd.DataFrame,
    reference_years: list[int] = DEFAULT_REFERENCE_YEARS,
) -> pd.DataFrame:
    """Aggregate total ICT-in-scope electricity and emissions for reference years.

    Args:
        results_df: Combined output DataFrame.
        reference_years: Calendar years to include.

    Returns:
        DataFrame with columns: year, kwh_twh, kwh_p10_twh, kwh_p90_twh,
        emissions_mtco2e (if available).
    """
    df = results_df[results_df["year"].isin(reference_years)].copy()

    if df.empty:
        return pd.DataFrame()

    agg_cols: dict[str, str] = {
        "kwh_p50": "sum",
        "kwh_p10": "sum",
        "kwh_p90": "sum",
    }
    if "emissions_kgco2e" in df.columns:
        agg_cols["emissions_kgco2e"] = "sum"

    grouped = df.groupby("year").agg(agg_cols).reset_index()
    grouped["kwh_twh"] = grouped["kwh_p50"] / 1e9
    grouped["kwh_p10_twh"] = grouped["kwh_p10"] / 1e9
    grouped["kwh_p90_twh"] = grouped["kwh_p90"] / 1e9
    if "emissions_kgco2e" in grouped.columns:
        grouped["emissions_mtco2e"] = grouped["emissions_kgco2e"] / 1e12

    drop_cols = [c for c in ["kwh_p50", "kwh_p10", "kwh_p90", "emissions_kgco2e"] if c in grouped.columns]
    grouped = grouped.drop(columns=drop_cols)

    logger.info("Total ICT aggregation: %d reference years", len(grouped))
    return grouped.sort_values("year").reset_index(drop=True)


def build_full_report(
    results_df: pd.DataFrame,
    reference_years: list[int] = DEFAULT_REFERENCE_YEARS,
) -> dict[str, pd.DataFrame]:
    """Build the complete study-aligned report as a dict of DataFrames.

    Args:
        results_df: Combined output DataFrame.
        reference_years: Reference years for appendix tables.

    Returns:
        Dict with keys:
          'appendix_table'       — per product group × metric × year
          'by_application_area'  — totals per application area × year
          'total_ict'            — overall ICT totals × year
    """
    return {
        "appendix_table": build_appendix_table(results_df, reference_years),
        "by_application_area": aggregate_by_application_area(results_df, reference_years),
        "total_ict": aggregate_total_ict(results_df, reference_years),
    }


def export_appendix_csv(
    results_df: pd.DataFrame,
    output_path: str,
    reference_years: list[int] = DEFAULT_REFERENCE_YEARS,
) -> None:
    """Export the appendix table to a CSV file.

    Args:
        results_df: Combined output DataFrame.
        output_path: Path to write the CSV file.
        reference_years: Reference years to include.
    """
    table = build_appendix_table(results_df, reference_years)
    table.to_csv(output_path, index=False)
    logger.info("Appendix table exported to %s (%d rows)", output_path, len(table))
