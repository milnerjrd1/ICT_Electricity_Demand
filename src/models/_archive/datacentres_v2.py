"""Data centres electricity demand model — architecture-centric (v2).

Aligned with Fraunhofer Green ICT @ FMD study approach:
  - Inventory represented as CPU units, storage units (HDD/SSD), and port units
  - PUE applied as overhead on total ICT electricity
  - Plausibility cross-checks: rack power density and CPU unit count

Formula:
    ict_kwh(geo, t) = (
        cpu_units   × power_per_cpu_w   × utilisation_cpu
      + hdd_units   × power_per_hdd_w
      + ssd_units   × power_per_ssd_w
      + port_units  × power_per_port_w  × utilisation_port
    ) × 8760 / 1000

    total_kwh(geo, t) = ict_kwh × PUE(t)

The legacy capacity-MW model (datacentres.py) is preserved unchanged.
This module is the new default called by the scenario engine when
gold_tables contains 'datacentres_arch' instead of 'datacentres'.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import pandas as pd

from src.models.schema import OutputRow, make_stub_output, validate_output
from src.models.taxonomy import enrich_with_taxonomy

logger = logging.getLogger(__name__)

HOURS_PER_YEAR = 8760.0

# Default power assumptions (W per unit) — overridden by gold table columns
_DEFAULTS: dict[str, float] = {
    "power_per_cpu_w": 250.0,       # per CPU socket (2-socket server ≈ 500 W IT)
    "power_per_hdd_w": 6.0,         # per HDD unit (3.5" spinning disk)
    "power_per_ssd_w": 2.0,         # per SSD unit (NVMe/SATA)
    "power_per_port_w": 1.5,        # per DC network port (ToR switch port)
    "utilisation_cpu": 0.55,        # CPU utilisation fraction
    "utilisation_port": 0.60,       # port utilisation fraction
    "pue": 1.40,                    # default PUE (overridden by gold table)
}

# Plausibility thresholds
_MAX_RACK_POWER_KW = 30.0           # kW per rack — flag if exceeded
_CPUS_PER_RACK = 40                 # typical 1U servers per 42U rack


def run_datacentres_arch_model(
    gold_df: pd.DataFrame,
    scenario_params: dict[str, Any],
    run_id: str | None = None,
) -> pd.DataFrame:
    """Run the architecture-centric DC electricity demand model.

    Args:
        gold_df: Gold table DataFrame with columns:
            geo, product_group (one of cpu_unit/hdd_unit/ssd_unit/dc_port_unit),
            year, unit_count, power_per_unit_w (optional), utilisation (optional),
            pue (required on cpu_unit rows; ignored on others), confidence_tier, source_ids.
            Rows for different unit types in the same geo/year are summed after
            applying PUE from the cpu_unit row for that geo/year.
        scenario_params: Dict of scenario overrides including:
            pue_improvement_rate, utilisation_multiplier, ai_growth_rate.
        run_id: UUID string for this pipeline run. Generated if not provided.

    Returns:
        DataFrame conforming to OutputSchema with segment='datacentres',
        product_group set to the unit type, application_area='datacentres'.
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    scenario_id = scenario_params.get("scenario_id", "baseline")
    pue_improvement_rate = float(scenario_params.get("pue_improvement_rate", 0.0))
    utilisation_multiplier = float(scenario_params.get("utilisation_multiplier", 1.0))

    rows: list[OutputRow] = []

    # Build PUE lookup: (geo, year) → effective PUE
    # PUE is stored on cpu_unit rows; applied to all unit types in same geo/year
    pue_lookup: dict[tuple[str, int], float] = {}
    base_years: dict[str, int] = {}

    cpu_rows = gold_df[gold_df.get("product_group", gold_df.get("product", "")) == "cpu_unit"] \
        if "product_group" in gold_df.columns \
        else gold_df[gold_df["product"] == "cpu_unit"]

    for geo, geo_group in gold_df.groupby("geo"):
        base_years[str(geo)] = int(geo_group["year"].min())

    for _, row in cpu_rows.iterrows():
        geo = str(row["geo"])
        year = int(row["year"])
        base_year = base_years.get(geo, year)
        years_elapsed = year - base_year
        base_pue = float(row.get("pue", _DEFAULTS["pue"]))
        effective_pue = max(1.01, base_pue * (1 - pue_improvement_rate) ** years_elapsed)
        pue_lookup[(geo, year)] = effective_pue

    for _, row in gold_df.iterrows():
        geo = str(row["geo"])
        year = int(row["year"])
        product_group = str(row.get("product_group", row.get("product", "cpu_unit")))
        confidence_tier = int(row.get("confidence_tier", 2))
        unit_count = float(row.get("unit_count", 0.0))

        base_year = base_years.get(geo, year)
        years_elapsed = year - base_year

        # Power per unit (W)
        if product_group == "cpu_unit":
            power_w = float(row.get("power_per_unit_w", _DEFAULTS["power_per_cpu_w"]))
            utilisation = min(0.95, float(row.get("utilisation", _DEFAULTS["utilisation_cpu"])) * utilisation_multiplier)
            ict_kwh = unit_count * power_w * utilisation * HOURS_PER_YEAR / 1000.0
        elif product_group == "hdd_unit":
            power_w = float(row.get("power_per_unit_w", _DEFAULTS["power_per_hdd_w"]))
            ict_kwh = unit_count * power_w * HOURS_PER_YEAR / 1000.0
        elif product_group == "ssd_unit":
            power_w = float(row.get("power_per_unit_w", _DEFAULTS["power_per_ssd_w"]))
            ict_kwh = unit_count * power_w * HOURS_PER_YEAR / 1000.0
        elif product_group == "dc_port_unit":
            power_w = float(row.get("power_per_unit_w", _DEFAULTS["power_per_port_w"]))
            utilisation = min(1.0, float(row.get("utilisation", _DEFAULTS["utilisation_port"])) * utilisation_multiplier)
            ict_kwh = unit_count * power_w * utilisation * HOURS_PER_YEAR / 1000.0
        else:
            # Unknown unit type — treat as generic device
            power_w = float(row.get("power_per_unit_w", 100.0))
            ict_kwh = unit_count * power_w * HOURS_PER_YEAR / 1000.0

        # Apply PUE (from cpu_unit row for this geo/year, or row's own pue)
        pue = pue_lookup.get((geo, year), float(row.get("pue", _DEFAULTS["pue"])))
        total_kwh = ict_kwh * pue

        uncertainty_band = _tier_to_uncertainty(confidence_tier)

        rows.append(
            make_stub_output(
                geo=geo,
                segment="datacentres",
                product=product_group,
                year=year,
                kwh_estimate=total_kwh,
                confidence_tier=confidence_tier,
                scenario_id=scenario_id,
                run_id=run_id,
                uncertainty_band=uncertainty_band,
                source_ids=list(row.get("source_ids", [])),
            )
        )

    result = pd.DataFrame(rows)
    result = enrich_with_taxonomy(result)
    logger.info("DC arch model produced %d rows for run_id=%s", len(result), run_id)
    return validate_output(result, context="datacentres_arch")


def check_rack_power_plausibility(
    gold_df: pd.DataFrame,
    max_rack_power_kw: float = _MAX_RACK_POWER_KW,
    cpus_per_rack: int = _CPUS_PER_RACK,
) -> list[str]:
    """Check that implied rack power density is within plausible bounds.

    Cross-check: cpu_units / cpus_per_rack × power_per_cpu_w × 2 sockets
    should not exceed max_rack_power_kw per rack.

    Args:
        gold_df: Gold table with cpu_unit rows.
        max_rack_power_kw: Maximum plausible rack power in kW.
        cpus_per_rack: Assumed CPU sockets per rack.

    Returns:
        List of warning strings (empty if all pass).
    """
    warnings: list[str] = []
    cpu_rows = gold_df[
        gold_df.get("product_group", gold_df.get("product", "")) == "cpu_unit"
    ] if "product_group" in gold_df.columns else gold_df[gold_df.get("product", "") == "cpu_unit"]

    for _, row in cpu_rows.iterrows():
        power_w = float(row.get("power_per_unit_w", _DEFAULTS["power_per_cpu_w"]))
        rack_power_kw = (cpus_per_rack * power_w) / 1000.0
        if rack_power_kw > max_rack_power_kw:
            msg = (
                f"PLAUSIBILITY WARN DC: {row['geo']} {row['year']} "
                f"implied rack power = {rack_power_kw:.1f} kW > {max_rack_power_kw} kW threshold "
                f"(power_per_cpu_w={power_w} W, cpus_per_rack={cpus_per_rack})"
            )
            warnings.append(msg)
            logger.warning(msg)

    return warnings


def check_cpu_unit_count_plausibility(
    gold_df: pd.DataFrame,
    server_count_proxy_df: pd.DataFrame | None = None,
    tolerance: float = 0.30,
) -> list[str]:
    """Cross-check CPU unit counts against an external server count proxy.

    Args:
        gold_df: Gold table with cpu_unit rows (columns: geo, year, unit_count).
        server_count_proxy_df: Optional DataFrame with columns: geo, year,
            server_count_proxy. If None, only logs a warning that no proxy is available.
        tolerance: Maximum fractional deviation before flagging (default 30%).

    Returns:
        List of warning strings (empty if all pass).
    """
    warnings: list[str] = []

    if server_count_proxy_df is None:
        logger.info("DC CPU unit plausibility: no server count proxy provided — skipping cross-check")
        return warnings

    cpu_rows = gold_df[
        gold_df.get("product_group", gold_df.get("product", "")) == "cpu_unit"
    ] if "product_group" in gold_df.columns else gold_df[gold_df.get("product", "") == "cpu_unit"]

    merged = cpu_rows.merge(
        server_count_proxy_df[["geo", "year", "server_count_proxy"]],
        on=["geo", "year"],
        how="inner",
    )

    for _, row in merged.iterrows():
        model_units = float(row["unit_count"])
        proxy_units = float(row["server_count_proxy"])
        if proxy_units <= 0:
            continue
        deviation = abs(model_units - proxy_units) / proxy_units
        if deviation > tolerance:
            msg = (
                f"PLAUSIBILITY WARN DC: {row['geo']} {row['year']} "
                f"CPU units model={model_units:,.0f} vs proxy={proxy_units:,.0f} "
                f"deviation={deviation:.1%} > {tolerance:.0%} tolerance"
            )
            warnings.append(msg)
            logger.warning(msg)

    return warnings


def _tier_to_uncertainty(confidence_tier: int) -> float:
    """Map confidence tier to fractional uncertainty half-width.

    Args:
        confidence_tier: 1, 2, or 3.

    Returns:
        Fractional half-width (e.g. 0.10 = ±10%).
    """
    mapping = {1: 0.10, 2: 0.25, 3: 0.40}
    return mapping.get(confidence_tier, 0.40)
