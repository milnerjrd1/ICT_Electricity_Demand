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
    """Germany data centres gold table anchored to Borderstep 2023.

    Capacity values calibrated so run_datacentres_model() produces ~18.6 TWh
    for DE in 2022, within the ±15% tolerance of the Borderstep benchmark
    (Hintemann et al. 2023: ~18 TWh total DC electricity for Germany).

    Breakdown (deterministic, pue_improvement_rate=0):
      hyperscale : 750 MW × 0.65 × 1.15 × 8760h = 4.91 TWh
      colocation  : 1000 MW × 0.55 × 1.45 × 8760h = 6.98 TWh
      on_premises : 1800 MW × 0.25 × 1.70 × 8760h = 6.70 TWh
      Total                                         = 18.59 TWh  (+3.3% vs 18 TWh ✓)
    """
    years = list(range(2020, 2026))
    rows = []
    for year in years:
        for product, capacity_mw, utilisation, pue, ai_share in [
            ("hyperscale", 750.0,  0.65, 1.15, 0.25),
            ("colocation",  1000.0, 0.55, 1.45, 0.08),
            ("on_premises", 1800.0, 0.25, 1.70, 0.02),
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
                "source_ids": ["borderstep_2023", "uptime_institute_2023", "eu_coc_2023"],
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


# ── Study-aligned v2 fixtures ─────────────────────────────────────────────────

@pytest.fixture
def germany_devices_v2_gold() -> pd.DataFrame:
    """Germany devices gold table for the study-aligned v2 model.

    Uses four-state power profile and application_area column.
    Includes warm-up years 2015-2019 for stable stock-flow.
    """
    warmup_years = list(range(2015, 2020))
    test_years = list(range(2020, 2026))
    all_years = warmup_years + test_years
    rows = []
    for year in all_years:
        for product_group, area, power_off, power_ready, power_med, power_high, h_off, h_ready, h_med, h_high, lifespan in [
            ("laptop_hh",    "households",   0.1,  5.0, 15.0, 35.0, 1760, 3000, 2500,  500, 5.0),
            ("desktop_hh",   "households",   0.5, 20.0, 80.0, 120.0, 2000, 2500, 2500, 1760, 6.0),
            ("smartphone_hh","households",   0.0,  0.5,  3.0,   5.0, 4000, 2000, 1500, 1260, 3.0),
            ("pc_notebook_wp","workplace",   0.1,  5.0, 15.0,  35.0,  760, 2000, 3000, 3000, 4.0),
            ("pos_terminal", "public_spaces",0.1,  2.0,  8.0,  12.0, 1760, 2000, 3000, 2000, 5.0),
        ]:
            rows.append({
                "geo": "DE",
                "product_group": product_group,
                "application_area": area,
                "year": year,
                "shipments": 3_000_000.0,
                "avg_lifespan_years": lifespan,
                "lifespan_std_years": lifespan * 0.2,
                "power_off_w": power_off,
                "power_ready_w": power_ready,
                "power_active_medium_w": power_med,
                "power_active_high_w": power_high,
                "hours_off": float(h_off),
                "hours_ready": float(h_ready),
                "hours_active_medium": float(h_med),
                "hours_active_high": float(h_high),
                "confidence_tier": 1,
                "source_ids": ["eurostat_2024", "energy_star"],
            })
    return pd.DataFrame(rows)


@pytest.fixture
def germany_telecom_gold() -> pd.DataFrame:
    """Germany telecom networks gold table for the port-unit channel model (Format A)."""
    years = list(range(2020, 2026))
    rows = []
    for year in years:
        rows.append({
            "geo": "DE",
            "year": year,
            "mobile_subscribers": 80_000_000.0,
            "fixed_subscribers": 35_000_000.0,
            "confidence_tier": 1,
            "source_ids": ["bnetzA_2024", "itu_2024"],
        })
    return pd.DataFrame(rows)


@pytest.fixture
def germany_dc_arch_gold() -> pd.DataFrame:
    """Germany data centres gold table for the architecture-centric v2 model.

    Uses CPU/storage/port unit counts rather than installed_capacity_mw.
    """
    years = list(range(2020, 2026))
    rows = []
    for year in years:
        rows.extend([
            {
                "geo": "DE", "product_group": "cpu_unit", "year": year,
                "unit_count": 500_000.0, "power_per_unit_w": 250.0,
                "utilisation": 0.55, "pue": 1.40,
                "confidence_tier": 1, "source_ids": ["borderstep_2023"],
            },
            {
                "geo": "DE", "product_group": "hdd_unit", "year": year,
                "unit_count": 2_000_000.0, "power_per_unit_w": 6.0,
                "confidence_tier": 2, "source_ids": ["borderstep_2023"],
            },
            {
                "geo": "DE", "product_group": "ssd_unit", "year": year,
                "unit_count": 1_000_000.0, "power_per_unit_w": 2.0,
                "confidence_tier": 2, "source_ids": ["borderstep_2023"],
            },
            {
                "geo": "DE", "product_group": "dc_port_unit", "year": year,
                "unit_count": 3_000_000.0, "power_per_unit_w": 1.5,
                "utilisation": 0.60,
                "confidence_tier": 2, "source_ids": ["borderstep_2023"],
            },
        ])
    return pd.DataFrame(rows)


@pytest.fixture
def grid_ef_germany_v2() -> pd.DataFrame:
    """Germany grid EF table with 2024 anchor year for carbon_v2 dispatch."""
    years = list(range(2020, 2026))
    efs   = [0.400, 0.385, 0.370, 0.360, 0.350, 0.340]
    return pd.DataFrame({
        "geo": ["DE"] * len(years),
        "year": years,
        "grid_ef_kgco2e_per_kwh": efs,
    })


@pytest.fixture
def scenario_v2_params() -> dict:
    """Scenario params compatible with all v2 model modules."""
    return {
        "scenario_id": "ai_base",
        "pue_improvement_rate": 0.02,
        "utilisation_multiplier": 1.0,
        "avg_lifespan_multiplier": 1.0,
        "power_efficiency_factor": 1.0,
        "ai_growth_rate": 0.15,
    }


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
