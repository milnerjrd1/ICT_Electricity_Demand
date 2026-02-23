"""Data centres electricity demand model module.

Capacity-based approach with explicit AI workload separation and PUE trajectories.
Formula:
    it_power(geo, dc_type, t)    = installed_capacity_MW × utilisation_rate(dc_type, t)
    total_power(geo, dc_type, t) = it_power × PUE(dc_type, t)
    annual_kwh                   = total_power × 8760
    ai_kwh(geo, t)               = ai_compute_demand(t) × kwh_per_compute_unit(t)

Placement shares (hyperscale / sovereign / colo / on-prem / edge) applied per scenario.
Monte Carlo uncertainty applied to PUE, utilisation, and AI growth rate for Tier 1.
"""

import logging
import uuid
from typing import Any

import numpy as np
import pandas as pd

from src.models.schema import OutputRow, make_stub_output, validate_output

logger = logging.getLogger(__name__)

HOURS_PER_YEAR = 8760.0

DC_TYPES = ("hyperscale", "sovereign", "colocation", "on_premises", "edge")


def run_datacentres_model(
    gold_df: pd.DataFrame,
    scenario_params: dict[str, Any],
    run_id: str | None = None,
    monte_carlo_iterations: int = 0,
) -> pd.DataFrame:
    """Run the data centres electricity demand model.

    Args:
        gold_df: Gold table DataFrame with columns:
            geo, product (dc_type), year, installed_capacity_mw,
            utilisation_rate, pue, ai_share, confidence_tier, source_ids.
        scenario_params: Dict of scenario overrides including:
            scenario_id, pue_improvement_rate, utilisation_multiplier,
            ai_growth_rate, ai_kwh_per_eflop.
        run_id: UUID string for this pipeline run. Generated if not provided.
        monte_carlo_iterations: Number of MC iterations for Tier 1 geos (0 = deterministic).

    Returns:
        DataFrame conforming to OutputSchema with segment='datacentres'.
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    scenario_id = scenario_params.get("scenario_id", "baseline")
    pue_improvement_rate = float(scenario_params.get("pue_improvement_rate", 0.0))
    utilisation_multiplier = float(scenario_params.get("utilisation_multiplier", 1.0))
    ai_growth_rate = float(scenario_params.get("ai_growth_rate", 0.0))

    rows: list[OutputRow] = []

    # Use the last calibrated (non-forecast) year as the PUE improvement base.
    # Anchor PUEs are already calibrated per year; improvement should only compound
    # beyond the last historical anchor, not from the start of the time series.
    calibrated_mask = gold_df["confidence_tier"].isin([1, 2])
    base_year = int(gold_df.loc[calibrated_mask, "year"].max()) if calibrated_mask.any() else int(gold_df["year"].min())

    # Map ai_growth_rate → 2035 DC output multiplier vs 2024 anchor.
    # All multipliers >= 1.0: even conservative scenarios see DC demand grow
    # due to ongoing digitisation — just slower than baseline.
    # DE trajectory already has built-in growth via Stobbe anchor; this
    # multiplier primarily drives non-DE geos (which have flat 2022 anchors).
    #   0.05 (ai_low)              → 1.05x  (very slow growth, efficiency offsets)
    #   0.10 (efficiency_brkthru)  → 1.10x  (efficiency gains limit growth)
    #   0.12 (grid_constrained)    → 1.15x  (grid limits cap expansion)
    #   0.20 (ai_base)             → 1.30x  (moderate baseline growth)
    #   0.45 (ai_high)             → 2.00x  (aggressive AI build-out)
    #   0.80 (ai_stress)           → 3.00x  (extreme AI, near physical limits)
    _RATE_TO_2035_MULT: list[tuple[float, float]] = [
        (0.00, 1.00),
        (0.05, 1.05),
        (0.10, 1.10),
        (0.12, 1.15),
        (0.20, 1.30),
        (0.45, 2.00),
        (0.80, 3.00),
        (1.00, 3.50),
    ]

    def _rate_to_mult(rate: float) -> float:
        """Linearly interpolate ai_growth_rate → 2035 multiplier."""
        for i in range(len(_RATE_TO_2035_MULT) - 1):
            r0, m0 = _RATE_TO_2035_MULT[i]
            r1, m1 = _RATE_TO_2035_MULT[i + 1]
            if r0 <= rate <= r1:
                t = (rate - r0) / (r1 - r0)
                return m0 + t * (m1 - m0)
        return _RATE_TO_2035_MULT[-1][1]

    mult_2035 = _rate_to_mult(ai_growth_rate)
    FORECAST_HORIZON = 11  # 2024 → 2035

    for _, row in gold_df.iterrows():
        confidence_tier = int(row.get("confidence_tier", 2))
        years_elapsed = max(0, int(row["year"]) - base_year)

        # PUE: use anchor value directly for all geos.
        # - DE: anchor PUE is already calibrated year-by-year to produce correct TWh.
        # - Non-DE: anchor is a static 2022 snapshot; capacity_scaler encodes scenario.
        # pue_improvement_rate affects the Monte Carlo uncertainty band width only.
        effective_pue = float(row["pue"])

        effective_utilisation = min(0.95, row["utilisation_rate"] * utilisation_multiplier)

        # For forecast years (tier 3) of non-DE geos, linearly interpolate from
        # 1.0 (at base_year) to mult_2035 (at 2035). DE has a year-by-year
        # calibrated Stobbe trajectory — applying the scaler would double-count.
        geo = str(row.get("geo", ""))
        if confidence_tier == 3 and years_elapsed > 0 and geo != "DE":
            t = min(1.0, years_elapsed / FORECAST_HORIZON)
            capacity_scaler = 1.0 + t * (mult_2035 - 1.0)
        else:
            capacity_scaler = 1.0

        effective_capacity_mw = row["installed_capacity_mw"] * capacity_scaler
        it_power_mw = effective_capacity_mw * effective_utilisation
        total_power_mw = it_power_mw * effective_pue
        annual_kwh = total_power_mw * HOURS_PER_YEAR * 1000.0

        if monte_carlo_iterations > 0 and confidence_tier == 1:
            kwh_p10, kwh_p50, kwh_p90, uncertainty_band = _monte_carlo(
                installed_capacity_mw=effective_capacity_mw,
                base_pue=row["pue"],
                base_utilisation=row["utilisation_rate"],
                pue_improvement_rate=pue_improvement_rate,
                utilisation_multiplier=utilisation_multiplier,
                years_elapsed=years_elapsed,
                iterations=monte_carlo_iterations,
            )
        else:
            uncertainty_band = _tier_to_uncertainty(confidence_tier)
            kwh_p10 = annual_kwh * (1 - uncertainty_band)
            kwh_p50 = annual_kwh
            kwh_p90 = annual_kwh * (1 + uncertainty_band)

        rows.append(
            OutputRow(
                geo=str(row["geo"]),
                segment="datacentres",
                product=str(row["product"]),
                year=int(row["year"]),
                kwh_estimate=annual_kwh,
                kwh_p10=kwh_p10,
                kwh_p50=kwh_p50,
                kwh_p90=kwh_p90,
                confidence_tier=confidence_tier,
                uncertainty_band=uncertainty_band,
                scenario_id=scenario_id,
                run_id=run_id,
                source_ids=list(row.get("source_ids", [])),
            )
        )

    result = pd.DataFrame(rows)
    logger.info("DC model produced %d rows for run_id=%s", len(result), run_id)
    return validate_output(result, context="datacentres")


def _monte_carlo(
    installed_capacity_mw: float,
    base_pue: float,
    base_utilisation: float,
    pue_improvement_rate: float,
    utilisation_multiplier: float,
    years_elapsed: int,
    iterations: int = 1000,
) -> tuple[float, float, float, float]:
    """Run Monte Carlo simulation for DC electricity demand uncertainty.

    Args:
        installed_capacity_mw: Installed IT capacity in MW.
        base_pue: Baseline PUE value.
        base_utilisation: Baseline utilisation rate (0–1).
        pue_improvement_rate: Annual PUE improvement rate.
        utilisation_multiplier: Scenario utilisation multiplier.
        years_elapsed: Years since base year.
        iterations: Number of Monte Carlo iterations.

    Returns:
        Tuple of (kwh_p10, kwh_p50, kwh_p90, uncertainty_band).
    """
    rng = np.random.default_rng()

    pue_mode = max(1.01, base_pue * (1 - pue_improvement_rate) ** years_elapsed)
    pue_left = min(base_pue * 0.90, pue_mode)
    pue_right = max(base_pue * 1.10, pue_mode)
    pue_samples = rng.triangular(left=pue_left, mode=pue_mode, right=pue_right, size=iterations)
    pue_samples = np.maximum(1.01, pue_samples)

    util_mode = min(0.95, base_utilisation * utilisation_multiplier)
    util_left = min(base_utilisation * 0.80, util_mode)
    util_right = max(min(0.98, base_utilisation * 1.20), util_mode)
    util_samples = rng.triangular(left=util_left, mode=util_mode, right=util_right, size=iterations)

    kwh_samples = installed_capacity_mw * util_samples * pue_samples * HOURS_PER_YEAR * 1000.0

    p10 = float(np.percentile(kwh_samples, 10))
    p50 = float(np.percentile(kwh_samples, 50))
    p90 = float(np.percentile(kwh_samples, 90))
    uncertainty_band = (p90 - p10) / (2.0 * p50) if p50 > 0 else 0.20

    return p10, p50, p90, uncertainty_band


def _tier_to_uncertainty(confidence_tier: int) -> float:
    """Map confidence tier to fractional uncertainty half-width.

    Args:
        confidence_tier: 1, 2, or 3.

    Returns:
        Fractional half-width (e.g. 0.10 = ±10%).
    """
    mapping = {1: 0.10, 2: 0.25, 3: 0.40}
    return mapping.get(confidence_tier, 0.40)
