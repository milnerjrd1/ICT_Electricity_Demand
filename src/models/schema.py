"""Canonical output schema for the ICT electricity demand model.

This schema is locked. Never change column names or types without a migration.
All model functions must return DataFrames validated against OutputSchema.
"""

from typing import get_args

import pandas as pd
from typing_extensions import TypedDict


class OutputRow(TypedDict):
    """Single output row — every model module returns DataFrames of these."""

    geo: str
    segment: str
    product: str
    year: int
    kwh_estimate: float
    kwh_p10: float
    kwh_p50: float
    kwh_p90: float
    confidence_tier: int
    uncertainty_band: float
    scenario_id: str
    run_id: str
    source_ids: list[str]


REQUIRED_COLUMNS: list[str] = list(OutputRow.__annotations__.keys())

SEGMENT_VALUES: tuple[str, ...] = ("devices", "networks", "datacentres")
CONFIDENCE_TIER_VALUES: tuple[int, ...] = (1, 2, 3)


def validate_output(df: pd.DataFrame, context: str = "") -> pd.DataFrame:
    """Validate a DataFrame conforms to OutputSchema.

    Args:
        df: DataFrame to validate.
        context: Optional label for error messages (e.g. module name).

    Returns:
        The input DataFrame if valid.

    Raises:
        ValueError: If any schema constraint is violated.
    """
    prefix = f"[{context}] " if context else ""

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{prefix}Missing required columns: {missing}")

    if df["confidence_tier"].isnull().any():
        raise ValueError(f"{prefix}confidence_tier must not be null")
    invalid_tiers = df.loc[~df["confidence_tier"].isin(CONFIDENCE_TIER_VALUES), "confidence_tier"].unique()
    if len(invalid_tiers) > 0:
        raise ValueError(f"{prefix}confidence_tier must be 1, 2, or 3. Found: {invalid_tiers}")

    if df["run_id"].isnull().any() or (df["run_id"] == "").any():
        raise ValueError(f"{prefix}run_id must not be null or empty")

    if (df["kwh_estimate"] < 0).any():
        raise ValueError(f"{prefix}kwh_estimate must not be negative")

    if (df["kwh_p10"] > df["kwh_p90"]).any():
        raise ValueError(f"{prefix}kwh_p10 must be <= kwh_p90")

    return df


def make_stub_output(
    geo: str,
    segment: str,
    product: str,
    year: int,
    kwh_estimate: float,
    confidence_tier: int,
    scenario_id: str,
    run_id: str,
    uncertainty_band: float = 0.2,
    source_ids: list[str] | None = None,
) -> OutputRow:
    """Create a single OutputRow with sensible defaults for P10/P50/P90.

    Args:
        geo: ISO 3166-1 alpha-2 country code or regional aggregate.
        segment: One of 'devices', 'networks', 'datacentres'.
        product: Product sub-type (e.g. 'laptop', 'hyperscale').
        year: Calendar year.
        kwh_estimate: Central kWh estimate.
        confidence_tier: 1, 2, or 3.
        scenario_id: Scenario identifier string.
        run_id: UUID string for this pipeline run.
        uncertainty_band: Fractional half-width for P10/P90 (default 0.2 = ±20%).
        source_ids: List of source identifiers contributing to this estimate.

    Returns:
        A populated OutputRow TypedDict.
    """
    return OutputRow(
        geo=geo,
        segment=segment,
        product=product,
        year=year,
        kwh_estimate=kwh_estimate,
        kwh_p10=kwh_estimate * (1 - uncertainty_band),
        kwh_p50=kwh_estimate,
        kwh_p90=kwh_estimate * (1 + uncertainty_band),
        confidence_tier=confidence_tier,
        uncertainty_band=uncertainty_band,
        scenario_id=scenario_id,
        run_id=run_id,
        source_ids=source_ids or [],
    )
