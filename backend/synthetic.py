"""Shaped synthetic trajectory generator for Phase 0.

Each scenario has a distinct curve shape, not just a multiplier.
Adds emissions_kgco2e and cost_usd columns using grid_emissions.yaml values.
All runs are deterministic via seed.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

_CONFIGS_DIR = Path(__file__).parent.parent / "configs"
_ASSUMPTIONS_DIR = _CONFIGS_DIR / "assumptions"

_YEARS = list(range(2020, 2036))

_GEOS: dict[str, int] = {
    "US": 1, "DE": 1, "GB": 1, "IE": 1, "NL": 1, "SG": 1, "JP": 1, "AE": 1,
    "CN": 1, "IN": 2, "AU": 1, "CA": 1, "SE": 1, "PL": 2,
    "FR": 2, "KR": 2, "BR": 2, "ZA": 3, "SA": 2, "MY": 2,
    "LATAM-REST": 3, "MENA-REST": 3, "SSA-REST": 3, "SEA-REST": 3, "CEE-REST": 3,
}

_GEO_SCALE_TWH: dict[str, float] = {
    "US": 800, "CN": 700, "DE": 90, "JP": 150, "GB": 80, "FR": 70,
    "IN": 120, "CA": 60, "AU": 40, "NL": 30, "IE": 25, "SG": 25,
    "KR": 60, "SE": 20, "BR": 50, "AE": 20, "SA": 25, "PL": 20,
    "MY": 20, "ZA": 15,
    "LATAM-REST": 80, "MENA-REST": 50, "SSA-REST": 30, "SEA-REST": 60, "CEE-REST": 40,
}

_SEGMENT_SHARE: dict[str, float] = {
    "devices": 0.45,
    "networks": 0.25,
    "datacentres": 0.30,
}

_SEGMENTS_PRODUCTS: dict[str, list[str]] = {
    "devices": ["laptop", "desktop", "smartphone", "tablet", "monitor"],
    "networks": ["5g_base_station", "4g_base_station", "fixed_broadband_cpe", "core_network"],
    "datacentres": ["hyperscale", "sovereign", "colocation", "on_premises", "edge"],
}

_DC_PRODUCT_SHARE: dict[str, float] = {
    "hyperscale": 0.45,
    "sovereign": 0.15,
    "colocation": 0.25,
    "on_premises": 0.10,
    "edge": 0.05,
}

# Electricity prices USD/kWh (2024 approximate)
_ELECTRICITY_PRICE: dict[str, float] = {
    "US": 0.12, "DE": 0.32, "GB": 0.28, "IE": 0.26, "NL": 0.25,
    "SG": 0.18, "JP": 0.22, "AE": 0.09, "CN": 0.08, "IN": 0.08,
    "AU": 0.20, "CA": 0.10, "SE": 0.12, "PL": 0.18, "FR": 0.20,
    "KR": 0.11, "BR": 0.13, "ZA": 0.10, "SA": 0.05, "MY": 0.08,
    "LATAM-REST": 0.12, "MENA-REST": 0.07, "SSA-REST": 0.15,
    "SEA-REST": 0.10, "CEE-REST": 0.15,
}


def _load_grid_ef() -> dict[str, float]:
    """Load 2024 grid emission factors from grid_emissions.yaml."""
    path = _ASSUMPTIONS_DIR / "grid_emissions.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)
    return {geo: vals["ef_2024"] for geo, vals in data.get("geographies", {}).items()}


def _dc_trajectory(scenario_id: str, year: int, base: float) -> float:
    """Return a shaped DC electricity multiplier for a given scenario and year.

    Each scenario has a distinct curve, not just a flat multiplier.
    Base year is 2024.
    """
    t = year - 2024  # years from base

    if scenario_id == "ai_base":
        # Exponential 2024–2030, plateau 2030–2035
        if t <= 0:
            return base
        if year <= 2030:
            return base * (1.18 ** t)
        return base * (1.18 ** 6) * (1.02 ** (year - 2030))

    elif scenario_id == "ai_high":
        # Steeper exponential, no plateau
        if t <= 0:
            return base
        return base * (1.30 ** t)

    elif scenario_id == "ai_low":
        # Linear slow growth
        if t <= 0:
            return base
        return base * (1 + 0.04 * t)

    elif scenario_id == "ai_stress":
        # Hockey stick post-2026
        if t <= 0:
            return base
        if year <= 2026:
            return base * (1.10 ** t)
        return base * (1.10 ** 2) * (1.45 ** (year - 2026))

    elif scenario_id == "sovereignty_push":
        # Distributed growth — hyperscale grows slower, edge/sovereign faster
        # Net effect: moderate growth, different product mix
        if t <= 0:
            return base
        return base * (1.12 ** t)

    elif scenario_id == "grid_constrained":
        # Capped post-2027
        if t <= 0:
            return base
        if year <= 2027:
            return base * (1.15 ** t)
        cap = base * (1.15 ** 3)
        return cap * (1.01 ** (year - 2027))

    elif scenario_id == "efficiency_breakthrough":
        # Compute up, kWh down — decoupled
        if t <= 0:
            return base
        return base * (1 + 0.02 * t)

    # Fallback
    return base * (1.10 ** max(0, t))


def _device_trajectory(scenario_id: str, year: int, base: float) -> float:
    """Return shaped device electricity for a given scenario and year."""
    t = year - 2024
    if t <= 0:
        return base * (1.01 ** (year - 2020))

    rates = {
        "ai_base": 0.00,
        "ai_high": 0.00,
        "ai_low": -0.01,
        "ai_stress": 0.00,
        "sovereignty_push": 0.00,
        "grid_constrained": 0.00,
        "efficiency_breakthrough": -0.02,
    }
    r = rates.get(scenario_id, 0.0)
    base_2024 = base * (1.01 ** 4)
    return base_2024 * ((1 + r) ** t)


def _network_trajectory(scenario_id: str, year: int, base: float) -> float:
    """Return shaped network electricity for a given scenario and year."""
    t = year - 2024
    if t <= 0:
        return base * (1.03 ** (year - 2020))

    rates = {
        "ai_base": 0.03,
        "ai_high": 0.05,
        "ai_low": 0.01,
        "ai_stress": 0.08,
        "sovereignty_push": 0.04,
        "grid_constrained": 0.01,
        "efficiency_breakthrough": -0.01,
    }
    r = rates.get(scenario_id, 0.03)
    base_2024 = base * (1.03 ** 4)
    return base_2024 * ((1 + r) ** t)


def generate(
    scenario_id: str,
    geos: list[str] | None = None,
    years: list[int] | None = None,
    segments: list[str] | None = None,
    seed: int = 42,
    run_id: str = "00000000-0000-0000-0000-000000000000",
) -> pd.DataFrame:
    """Generate shaped synthetic output DataFrame for a single scenario.

    Args:
        scenario_id: Scenario identifier.
        geos: Geographies to include (None = all).
        years: Years to include (None = 2020–2035).
        segments: Segments to include (None = all).
        seed: Random seed for deterministic noise.
        run_id: UUID for this run.

    Returns:
        DataFrame conforming to OutputSchema with emissions and cost columns.
    """
    rng = np.random.default_rng(seed)
    grid_ef = _load_grid_ef()

    active_geos = {g: t for g, t in _GEOS.items() if geos is None or g in geos}
    active_years = [y for y in _YEARS if years is None or y in years]
    active_segments = [s for s in _SEGMENTS_PRODUCTS if segments is None or s in segments]

    rows: list[dict] = []

    for geo, confidence_tier in active_geos.items():
        geo_scale = _GEO_SCALE_TWH.get(geo, 20.0)
        ef = grid_ef.get(geo, 0.40)
        price = _ELECTRICITY_PRICE.get(geo, 0.12)

        for segment in active_segments:
            seg_share = _SEGMENT_SHARE[segment]
            products = _SEGMENTS_PRODUCTS[segment]

            for product in products:
                if segment == "datacentres":
                    product_share = _DC_PRODUCT_SHARE.get(product, 0.2)
                else:
                    product_share = 1.0 / len(products)

                base_twh = geo_scale * seg_share * product_share

                for year in active_years:
                    noise = 1.0 + rng.normal(0, 0.015)

                    if segment == "datacentres":
                        twh = _dc_trajectory(scenario_id, year, base_twh) * noise
                    elif segment == "devices":
                        twh = _device_trajectory(scenario_id, year, base_twh) * noise
                    else:
                        twh = _network_trajectory(scenario_id, year, base_twh) * noise

                    twh = max(0.0, twh)
                    kwh = twh * 1e9

                    uncertainty_band = {1: 0.10, 2: 0.20, 3: 0.35}.get(confidence_tier, 0.20)

                    emissions = kwh * ef / 1e9  # MtCO2e (kwh * kgCO2e/kWh / 1e9)
                    cost = kwh * price / 1e9  # USD billions

                    rows.append({
                        "geo": geo,
                        "segment": segment,
                        "product": product,
                        "year": year,
                        "kwh_estimate": kwh,
                        "kwh_p10": kwh * (1 - uncertainty_band),
                        "kwh_p50": kwh,
                        "kwh_p90": kwh * (1 + uncertainty_band),
                        "confidence_tier": confidence_tier,
                        "uncertainty_band": uncertainty_band,
                        "scenario_id": scenario_id,
                        "run_id": run_id,
                        "source_ids": ["synthetic"],
                        "emissions_kgco2e": emissions,
                        "cost_usd": cost,
                    })

    df = pd.DataFrame(rows)
    logger.info(
        "Synthetic data generated: scenario=%s rows=%d seed=%d",
        scenario_id, len(df), seed,
    )
    return df


def assumptions_hash(params: dict) -> str:
    """Return a short hash of scenario params for reproducibility tracking."""
    content = str(sorted(params.items())).encode()
    return hashlib.sha256(content).hexdigest()[:12]
