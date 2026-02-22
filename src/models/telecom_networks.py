"""Telecom networks electricity demand model — port-unit channel model.

Aligned with Fraunhofer Green ICT @ FMD study approach:
  - Network split into four layers: mobile_access, fixed_access, aggregation, core_transport
  - Inventory represented as port units per layer
  - Channel model: subscriber connections + traffic → port units per layer
  - Site-specific PUE applied per layer
  - Energy management factor for high-frequency radio (partial operation)

Formula per layer:
    port_units(layer, geo, t) = connections(geo, t) × ports_per_connection(layer)
                                × uplink_multiplier(layer)
    ict_kwh(layer, geo, t)    = port_units × power_per_port_w(layer, t) × 8760 / 1000
    total_kwh(layer, geo, t)  = ict_kwh × site_pue(layer)
                                × energy_mgmt_factor(layer)

The legacy networks model (networks.py) is preserved unchanged.
This module is the new default called by the scenario engine when
gold_tables contains 'telecom_networks' instead of 'networks'.
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

# ── Layer definitions ─────────────────────────────────────────────────────────

# Default channel model coefficients per layer
# ports_per_connection: how many port units are required per subscriber connection
# uplink_multiplier: additional ports for uplink/backhaul (e.g. 1.2 = 20% overhead)
# power_per_port_w: power draw per port unit in watts
# site_pue: power usage effectiveness for the site type
# energy_mgmt_factor: fraction of time equipment is fully active (sleep modes etc.)

LAYER_DEFAULTS: dict[str, dict[str, float]] = {
    "mobile_access": {
        "ports_per_connection": 0.001,   # ~1 port per 1000 mobile subscribers (base station ports)
        "uplink_multiplier": 1.20,
        "power_per_port_w": 800.0,       # W per RAN port (macro cell equivalent)
        "site_pue": 1.50,                # telecom site PUE (shelter + cooling)
        "energy_mgmt_factor": 0.85,      # partial sleep for high-freq small cells
        "annual_improvement": 0.03,      # annual power efficiency improvement
    },
    "fixed_access": {
        "ports_per_connection": 1.0,     # 1 port per fixed-line subscriber (DSL/FTTH port)
        "uplink_multiplier": 1.10,
        "power_per_port_w": 1.2,         # W per DSL/FTTH access port
        "site_pue": 1.20,                # DSLAM/OLT cabinet PUE
        "energy_mgmt_factor": 0.95,
        "annual_improvement": 0.02,
    },
    "aggregation": {
        "ports_per_connection": 0.005,   # ~1 aggregation port per 200 subscribers
        "uplink_multiplier": 1.15,
        "power_per_port_w": 5.0,         # W per aggregation switch port
        "site_pue": 1.30,
        "energy_mgmt_factor": 0.90,
        "annual_improvement": 0.03,
    },
    "core_transport": {
        "ports_per_connection": 0.0002,  # ~1 core port per 5000 subscribers
        "uplink_multiplier": 1.10,
        "power_per_port_w": 20.0,        # W per core/transport port (high-capacity)
        "site_pue": 1.25,
        "energy_mgmt_factor": 0.95,
        "annual_improvement": 0.04,
    },
}

TELECOM_LAYERS: tuple[str, ...] = (
    "mobile_access",
    "fixed_access",
    "aggregation",
    "core_transport",
)

# Map layer → product_group in taxonomy
LAYER_TO_PRODUCT_GROUP: dict[str, str] = {
    "mobile_access":   "mobile_access_port",
    "fixed_access":    "fixed_access_port",
    "aggregation":     "aggregation_port",
    "core_transport":  "core_transport_port",
}


def run_telecom_channel_model(
    gold_df: pd.DataFrame,
    scenario_params: dict[str, Any],
    run_id: str | None = None,
) -> pd.DataFrame:
    """Run the telecom port-unit channel model.

    Args:
        gold_df: Gold table DataFrame. Two supported formats:

          Format A — connection-based (channel model derives port units):
            Columns: geo, year, mobile_subscribers, fixed_subscribers,
            confidence_tier, source_ids.
            Optional per-layer overrides: {layer}_ports_per_connection,
            {layer}_power_per_port_w, {layer}_site_pue, {layer}_energy_mgmt_factor.

          Format B — pre-computed port units (direct input):
            Columns: geo, layer (one of TELECOM_LAYERS), year, port_units,
            power_per_port_w (optional), site_pue (optional),
            energy_mgmt_factor (optional), confidence_tier, source_ids.

        scenario_params: Dict of scenario overrides including:
            power_efficiency_factor (multiplier on power_per_port_w).
        run_id: UUID string for this pipeline run. Generated if not provided.

    Returns:
        DataFrame conforming to OutputSchema with segment='networks',
        product_group set to the layer's port type, application_area='telecom_networks'.
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    scenario_id = scenario_params.get("scenario_id", "baseline")
    power_efficiency_factor = float(scenario_params.get("power_efficiency_factor", 1.0))

    # Detect format
    if "layer" in gold_df.columns and "port_units" in gold_df.columns:
        result = _run_format_b(gold_df, scenario_id, power_efficiency_factor, run_id)
    else:
        result = _run_format_a(gold_df, scenario_id, power_efficiency_factor, run_id)

    if result.empty:
        logger.warning("Telecom channel model produced 0 rows for run_id=%s", run_id)
        return result
    result = enrich_with_taxonomy(result)
    logger.info("Telecom channel model produced %d rows for run_id=%s", len(result), run_id)
    return validate_output(result, context="telecom_networks")


def _run_format_a(
    gold_df: pd.DataFrame,
    scenario_id: str,
    power_efficiency_factor: float,
    run_id: str,
) -> pd.DataFrame:
    """Run channel model from subscriber connection counts (Format A)."""
    rows: list[OutputRow] = []

    for _, row in gold_df.iterrows():
        geo = str(row["geo"])
        year = int(row["year"])
        confidence_tier = int(row.get("confidence_tier", 2))
        source_ids = list(row.get("source_ids", []))

        mobile_subs = float(row.get("mobile_subscribers", 0.0))
        fixed_subs = float(row.get("fixed_subscribers", 0.0))

        # Connections per layer
        layer_connections: dict[str, float] = {
            "mobile_access": mobile_subs,
            "fixed_access": fixed_subs,
            "aggregation": mobile_subs + fixed_subs,
            "core_transport": mobile_subs + fixed_subs,
        }

        for layer in TELECOM_LAYERS:
            defaults = LAYER_DEFAULTS[layer]
            connections = layer_connections[layer]

            ports_per_conn = float(row.get(f"{layer}_ports_per_connection", defaults["ports_per_connection"]))
            uplink_mult = float(defaults["uplink_multiplier"])
            port_units = connections * ports_per_conn * uplink_mult

            power_w = float(row.get(f"{layer}_power_per_port_w", defaults["power_per_port_w"]))
            power_w *= power_efficiency_factor
            site_pue = float(row.get(f"{layer}_site_pue", defaults["site_pue"]))
            energy_mgmt = float(row.get(f"{layer}_energy_mgmt_factor", defaults["energy_mgmt_factor"]))

            ict_kwh = port_units * power_w * energy_mgmt * HOURS_PER_YEAR / 1000.0
            total_kwh = ict_kwh * site_pue

            uncertainty_band = _tier_to_uncertainty(confidence_tier)
            product_group = LAYER_TO_PRODUCT_GROUP[layer]

            rows.append(
                make_stub_output(
                    geo=geo,
                    segment="networks",
                    product=product_group,
                    year=year,
                    kwh_estimate=total_kwh,
                    confidence_tier=confidence_tier,
                    scenario_id=scenario_id,
                    run_id=run_id,
                    uncertainty_band=uncertainty_band,
                    source_ids=source_ids,
                )
            )

    return pd.DataFrame(rows)


def _run_format_b(
    gold_df: pd.DataFrame,
    scenario_id: str,
    power_efficiency_factor: float,
    run_id: str,
) -> pd.DataFrame:
    """Run channel model from pre-computed port unit counts (Format B)."""
    rows: list[OutputRow] = []

    for _, row in gold_df.iterrows():
        geo = str(row["geo"])
        year = int(row["year"])
        layer = str(row["layer"])
        confidence_tier = int(row.get("confidence_tier", 2))
        source_ids = list(row.get("source_ids", []))

        if layer not in LAYER_DEFAULTS:
            logger.warning("Unknown telecom layer '%s' — skipping row", layer)
            continue

        defaults = LAYER_DEFAULTS[layer]
        port_units = float(row["port_units"])
        power_w = float(row.get("power_per_port_w", defaults["power_per_port_w"])) * power_efficiency_factor
        site_pue = float(row.get("site_pue", defaults["site_pue"]))
        energy_mgmt = float(row.get("energy_mgmt_factor", defaults["energy_mgmt_factor"]))

        ict_kwh = port_units * power_w * energy_mgmt * HOURS_PER_YEAR / 1000.0
        total_kwh = ict_kwh * site_pue

        uncertainty_band = _tier_to_uncertainty(confidence_tier)
        product_group = LAYER_TO_PRODUCT_GROUP.get(layer, layer)

        rows.append(
            make_stub_output(
                geo=geo,
                segment="networks",
                product=product_group,
                year=year,
                kwh_estimate=total_kwh,
                confidence_tier=confidence_tier,
                scenario_id=scenario_id,
                run_id=run_id,
                uncertainty_band=uncertainty_band,
                source_ids=source_ids,
            )
        )

    return pd.DataFrame(rows)


def derive_port_units(
    connections: float,
    layer: str,
    ports_per_connection_override: float | None = None,
) -> float:
    """Derive port unit count from subscriber connections for a given layer.

    Args:
        connections: Number of subscriber connections (mobile or fixed).
        layer: Telecom layer name (one of TELECOM_LAYERS).
        ports_per_connection_override: Override for ports_per_connection coefficient.

    Returns:
        Estimated port unit count.
    """
    defaults = LAYER_DEFAULTS.get(layer, {})
    ports_per_conn = ports_per_connection_override or defaults.get("ports_per_connection", 0.001)
    uplink_mult = defaults.get("uplink_multiplier", 1.0)
    return connections * ports_per_conn * uplink_mult


def check_port_unit_layer_shares(
    result_df: pd.DataFrame,
    geo: str,
    year: int,
) -> list[str]:
    """Check that port unit layer shares sum to a plausible total.

    Warns if any single layer accounts for >80% of total telecom electricity
    for a given geo/year (suggests a misconfigured coefficient).

    Args:
        result_df: Output DataFrame from run_telecom_channel_model.
        geo: Geography to check.
        year: Year to check.

    Returns:
        List of warning strings (empty if all pass).
    """
    warnings: list[str] = []
    subset = result_df[
        (result_df["geo"] == geo)
        & (result_df["year"] == year)
        & (result_df["segment"] == "networks")
    ]

    if subset.empty:
        return warnings

    total_kwh = subset["kwh_estimate"].sum()
    if total_kwh <= 0:
        return warnings

    for _, row in subset.iterrows():
        share = row["kwh_estimate"] / total_kwh
        if share > 0.80:
            msg = (
                f"PLAUSIBILITY WARN TELECOM: {geo} {year} layer '{row['product']}' "
                f"accounts for {share:.1%} of total telecom electricity "
                f"(threshold >80% — check channel model coefficients)"
            )
            warnings.append(msg)
            logger.warning(msg)

    return warnings


def _tier_to_uncertainty(confidence_tier: int) -> float:
    """Map confidence tier to fractional uncertainty half-width."""
    mapping = {1: 0.10, 2: 0.25, 3: 0.40}
    return mapping.get(confidence_tier, 0.40)
