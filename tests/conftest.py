"""Shared pytest fixtures for the ICT electricity demand model test suite.

All tests should use these fixtures rather than hardcoding test data inline.
"""

import uuid
from typing import Any

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def run_id() -> str:
    """Provide a deterministic run_id for tests."""
    return "test-run-00000000-0000-0000-0000-000000000001"


@pytest.fixture
def scenario_baseline() -> dict[str, Any]:
    """Baseline scenario parameters."""
    return {
        "scenario_id": "ai_base",
        "pue_improvement_rate": 0.02,
        "utilisation_multiplier": 1.0,
        "ai_growth_rate": 0.15,
        "avg_lifespan_multiplier": 1.0,
        "utilisation_multiplier": 1.0,
        "power_efficiency_factor": 1.0,
    }


@pytest.fixture
def germany_devices_gold() -> pd.DataFrame:
    """Stub Germany devices gold table for testing.

    Includes 5 warm-up years (2015-2019) before the test window so the
    stock-flow model has a stable installed base by 2020, avoiding large
    YoY jumps caused by building from zero.
    """
    # Warm-up years ensure installed base is stable before 2020
    warmup_years = list(range(2015, 2020))
    test_years = list(range(2020, 2026))
    all_years = warmup_years + test_years
    rows = []
    for year in all_years:
        for product, power_active, power_idle in [
            ("laptop", 15.0, 5.0),
            ("desktop", 80.0, 20.0),
            ("smartphone", 3.0, 0.5),
        ]:
            rows.append({
                "geo": "DE",
                "product": product,
                "year": year,
                "shipments": 5_000_000,
                "avg_lifespan_years": 5.0,
                "power_active_w": power_active,
                "power_idle_w": power_idle,
                "power_sleep_w": 1.0,
                "power_off_w": 0.1,
                "hours_active": 2000.0,
                "hours_idle": 2000.0,
                "hours_sleep": 3000.0,
                "hours_off": 1760.0,
                "confidence_tier": 1,
                "source_ids": ["eurostat_2024", "energy_star"],
            })
    return pd.DataFrame(rows)


@pytest.fixture
def germany_networks_gold() -> pd.DataFrame:
    """Stub Germany networks gold table for testing."""
    years = list(range(2020, 2026))
    rows = []
    for year in years:
        for product, equipment_count, power_w, utilisation in [
            ("5g_base_station", 50_000, 1500.0, 0.6),
            ("4g_base_station", 80_000, 800.0, 0.7),
            ("fixed_broadband_cpe", 35_000_000, 8.0, 0.9),
        ]:
            rows.append({
                "geo": "DE",
                "product": product,
                "year": year,
                "equipment_count": equipment_count,
                "power_per_unit_w": power_w,
                "utilisation_factor": utilisation,
                "confidence_tier": 1,
                "source_ids": ["bnetzA_2024", "itu_2024"],
            })
    return pd.DataFrame(rows)


@pytest.fixture
def germany_dc_gold() -> pd.DataFrame:
    """Stub Germany data centres gold table for testing."""
    years = list(range(2020, 2026))
    rows = []
    for year in years:
        for product, capacity_mw, utilisation, pue, ai_share in [
            ("hyperscale", 800.0, 0.65, 1.15, 0.30),
            ("colocation", 600.0, 0.55, 1.40, 0.10),
            ("on_premises", 400.0, 0.30, 1.70, 0.05),
        ]:
            rows.append({
                "geo": "DE",
                "product": product,
                "year": year,
                "installed_capacity_mw": capacity_mw,
                "utilisation_rate": utilisation,
                "pue": pue,
                "ai_share": ai_share,
                "confidence_tier": 1,
                "source_ids": ["borderstep_2024", "uptime_institute_2024"],
            })
    return pd.DataFrame(rows)


@pytest.fixture
def grid_ef_germany() -> pd.DataFrame:
    """Stub Germany grid emission factors."""
    years = list(range(2020, 2026))
    return pd.DataFrame({
        "geo": ["DE"] * len(years),
        "year": years,
        "grid_ef_kgco2e_per_kwh": [0.366, 0.350, 0.334, 0.320, 0.305, 0.290],
    })


@pytest.fixture
def electricity_prices_germany() -> pd.DataFrame:
    """Stub Germany electricity prices."""
    years = list(range(2020, 2026))
    return pd.DataFrame({
        "geo": ["DE"] * len(years),
        "year": years,
        "price_usd_per_kwh": [0.32, 0.34, 0.38, 0.42, 0.40, 0.38],
    })


@pytest.fixture
def multi_geo_dc_gold() -> pd.DataFrame:
    """Stub multi-geography DC gold table for scale testing."""
    geos = ["US", "DE", "GB", "CN", "JP", "SG"]
    years = [2024, 2025]
    rows = []
    for geo in geos:
        for year in years:
            rows.append({
                "geo": geo,
                "product": "hyperscale",
                "year": year,
                "installed_capacity_mw": 1000.0,
                "utilisation_rate": 0.65,
                "pue": 1.20,
                "ai_share": 0.25,
                "confidence_tier": 1,
                "source_ids": ["stub"],
            })
    return pd.DataFrame(rows)
