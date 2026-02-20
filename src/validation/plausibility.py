"""Automated plausibility checks for model outputs.

These checks run on every pipeline execution. Zero violations in production.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)

MAX_ICT_SHARE_OF_TOTAL_ELECTRICITY = 0.25
MAX_YOY_CHANGE = 0.15


class PlausibilityViolation(Exception):
    """Raised when a plausibility check fails in strict mode."""


def check_no_negative_kwh(df: pd.DataFrame, strict: bool = False) -> list[str]:
    """Check that no kWh estimates are negative.

    Args:
        df: Output DataFrame conforming to OutputSchema.
        strict: If True, raise PlausibilityViolation on failure.

    Returns:
        List of violation message strings (empty if all pass).
    """
    violations = []
    for col in ["kwh_estimate", "kwh_p10", "kwh_p50", "kwh_p90"]:
        if col in df.columns and (df[col] < 0).any():
            n = (df[col] < 0).sum()
            msg = f"PLAUSIBILITY FAIL: {n} rows have negative {col}"
            violations.append(msg)
            logger.error(msg)

    if strict and violations:
        raise PlausibilityViolation("\n".join(violations))
    return violations


def check_ict_share_of_total(
    ict_df: pd.DataFrame,
    total_electricity_df: pd.DataFrame,
    strict: bool = False,
) -> list[str]:
    """Check that no country's ICT share exceeds 25% of total electricity.

    Args:
        ict_df: ICT output DataFrame with columns: geo, year, kwh_estimate.
        total_electricity_df: DataFrame with columns: geo, year, total_kwh.
        strict: If True, raise PlausibilityViolation on failure.

    Returns:
        List of violation message strings (empty if all pass).
    """
    violations = []

    ict_agg = ict_df.groupby(["geo", "year"])["kwh_estimate"].sum().reset_index()
    merged = ict_agg.merge(total_electricity_df[["geo", "year", "total_kwh"]], on=["geo", "year"], how="inner")

    if merged.empty:
        logger.warning("No matching geo/year pairs for ICT share check — skipping")
        return violations

    merged["ict_share"] = merged["kwh_estimate"] / merged["total_kwh"]
    flagged = merged[merged["ict_share"] > MAX_ICT_SHARE_OF_TOTAL_ELECTRICITY]

    for _, row in flagged.iterrows():
        msg = (
            f"PLAUSIBILITY FAIL: {row['geo']} {row['year']} ICT share = "
            f"{row['ict_share']:.1%} > {MAX_ICT_SHARE_OF_TOTAL_ELECTRICITY:.0%} threshold"
        )
        violations.append(msg)
        logger.error(msg)

    if strict and violations:
        raise PlausibilityViolation("\n".join(violations))
    return violations


def check_yoy_changes(
    df: pd.DataFrame,
    max_change: float = MAX_YOY_CHANGE,
    strict: bool = False,
) -> list[str]:
    """Check that year-on-year changes are within explainable bounds.

    Args:
        df: Output DataFrame with columns: geo, segment, product, year, kwh_estimate.
        max_change: Maximum fractional YoY change before flagging (default 0.15 = 15%).
        strict: If True, raise PlausibilityViolation on failure.

    Returns:
        List of violation message strings (empty if all pass).
    """
    violations = []

    df_sorted = df.sort_values(["geo", "segment", "product", "year"])
    df_sorted = df_sorted.copy()
    df_sorted["kwh_prev"] = df_sorted.groupby(["geo", "segment", "product"])["kwh_estimate"].shift(1)
    df_sorted["yoy_change"] = (df_sorted["kwh_estimate"] - df_sorted["kwh_prev"]) / df_sorted["kwh_prev"].abs()

    # Only flag rows where a prior year exists (shift produces NaN for first year per group)
    flagged = df_sorted[
        df_sorted["yoy_change"].abs() > max_change
    ].dropna(subset=["kwh_prev", "yoy_change"])

    for _, row in flagged.iterrows():
        msg = (
            f"PLAUSIBILITY WARN: {row['geo']} {row['segment']} {row['product']} "
            f"{int(row['year'])}: YoY change = {row['yoy_change']:.1%} > {max_change:.0%} threshold"
        )
        violations.append(msg)
        logger.warning(msg)

    if strict and violations:
        raise PlausibilityViolation("\n".join(violations))
    return violations


def run_all_checks(
    df: pd.DataFrame,
    total_electricity_df: pd.DataFrame | None = None,
    strict: bool = False,
) -> dict[str, list[str]]:
    """Run all plausibility checks and return a summary.

    Args:
        df: Output DataFrame conforming to OutputSchema.
        total_electricity_df: Optional DataFrame for ICT share check.
        strict: If True, raise PlausibilityViolation on first failure.

    Returns:
        Dict mapping check name → list of violation messages.
    """
    results: dict[str, list[str]] = {}

    results["no_negative_kwh"] = check_no_negative_kwh(df, strict=strict)
    results["yoy_changes"] = check_yoy_changes(df, strict=strict)

    if total_electricity_df is not None:
        results["ict_share"] = check_ict_share_of_total(df, total_electricity_df, strict=strict)

    total_violations = sum(len(v) for v in results.values())
    if total_violations == 0:
        logger.info("All plausibility checks passed")
    else:
        logger.warning("Plausibility checks: %d violations found", total_violations)

    return results
