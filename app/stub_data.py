"""Stub data generator for Phase 0 Streamlit app.

Generates realistic-looking stub data conforming to OutputSchema.
Replace with real model outputs as data loaders and model modules are built.
"""

import uuid

import numpy as np
import pandas as pd

from src.models.schema import REQUIRED_COLUMNS, OutputRow

_STUB_RUN_ID = "00000000-0000-0000-0000-000000000000"

_GEOS = {
    # Tier 1 DC/AI hotspots
    "US": 1, "DE": 1, "GB": 1, "IE": 1, "NL": 1, "SG": 1, "JP": 1, "AE": 1,
    # Tier 1 Emerging DC
    "CN": 1, "IN": 2, "AU": 1, "CA": 1, "SE": 1, "PL": 2,
    # Tier 2
    "FR": 2, "KR": 2, "BR": 2, "ZA": 3, "SA": 2, "MY": 2,
    # Tier 3 aggregates
    "LATAM-REST": 3, "MENA-REST": 3, "SSA-REST": 3, "SEA-REST": 3, "CEE-REST": 3,
}

_SEGMENTS_PRODUCTS = {
    "devices": ["laptop", "desktop", "smartphone", "tablet", "monitor"],
    "networks": ["5g_base_station", "4g_base_station", "fixed_broadband_cpe", "core_network"],
    "datacentres": ["hyperscale", "sovereign", "colocation", "on_premises", "edge"],
}

_SCENARIOS = ["ai_base", "ai_low", "ai_high", "sovereignty_push"]

_YEARS = list(range(2020, 2036))

# Rough scale factors for geo × segment (TWh/year at 2024 baseline)
_GEO_SCALE = {
    "US": 800, "CN": 700, "DE": 90, "JP": 150, "GB": 80, "FR": 70,
    "IN": 120, "CA": 60, "AU": 40, "NL": 30, "IE": 25, "SG": 25,
    "KR": 60, "SE": 20, "BR": 50, "AE": 20, "SA": 25, "PL": 20,
    "MY": 20, "ZA": 15,
    "LATAM-REST": 80, "MENA-REST": 50, "SSA-REST": 30, "SEA-REST": 60, "CEE-REST": 40,
}

_SEGMENT_SHARE = {
    "devices": 0.45,
    "networks": 0.25,
    "datacentres": 0.30,
}

_SCENARIO_MULTIPLIER = {
    "ai_base": 1.0,
    "ai_low": 0.75,
    "ai_high": 1.40,
    "sovereignty_push": 1.15,
}

_DC_PRODUCT_SHARE = {
    "hyperscale": 0.45,
    "sovereign": 0.15,
    "colocation": 0.25,
    "on_premises": 0.10,
    "edge": 0.05,
}

_GROWTH_RATE = {
    "devices": 0.01,
    "networks": 0.03,
    "datacentres": 0.12,
}


def get_stub_dataframe() -> pd.DataFrame:
    """Generate a stub output DataFrame conforming to OutputSchema.

    Returns:
        DataFrame with all REQUIRED_COLUMNS populated with plausible stub values.
    """
    rng = np.random.default_rng(42)
    rows: list[dict] = []

    for scenario_id in _SCENARIOS:
        scenario_mult = _SCENARIO_MULTIPLIER[scenario_id]

        for geo, confidence_tier in _GEOS.items():
            geo_scale_twh = _GEO_SCALE.get(geo, 20)

            for segment, products in _SEGMENTS_PRODUCTS.items():
                seg_share = _SEGMENT_SHARE[segment]
                growth = _GROWTH_RATE[segment]

                for product in products:
                    if segment == "datacentres":
                        product_share = _DC_PRODUCT_SHARE.get(product, 0.2)
                    else:
                        product_share = 1.0 / len(products)

                    base_twh = geo_scale_twh * seg_share * product_share

                    for year in _YEARS:
                        years_from_2024 = year - 2024
                        dc_ai_boost = (
                            1.0 + max(0, years_from_2024) * 0.05
                            if segment == "datacentres"
                            else 1.0
                        )
                        kwh_estimate = (
                            base_twh
                            * 1e9
                            * (1 + growth) ** (year - 2020)
                            * scenario_mult
                            * dc_ai_boost
                            * (1 + rng.normal(0, 0.02))
                        )
                        kwh_estimate = max(0.0, kwh_estimate)

                        uncertainty_band = {1: 0.10, 2: 0.20, 3: 0.35}.get(confidence_tier, 0.20)

                        rows.append(
                            {
                                "geo": geo,
                                "segment": segment,
                                "product": product,
                                "year": year,
                                "kwh_estimate": kwh_estimate,
                                "kwh_p10": kwh_estimate * (1 - uncertainty_band),
                                "kwh_p50": kwh_estimate,
                                "kwh_p90": kwh_estimate * (1 + uncertainty_band),
                                "confidence_tier": confidence_tier,
                                "uncertainty_band": uncertainty_band,
                                "scenario_id": scenario_id,
                                "run_id": _STUB_RUN_ID,
                                "source_ids": ["stub"],
                            }
                        )

    df = pd.DataFrame(rows)
    return df
