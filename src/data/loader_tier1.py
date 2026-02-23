"""Tier 1 DC hotspot data loader — hardcoded published-source anchors.

Provides DC capacity anchors for the 7 remaining Tier 1 DC hotspot geographies
(US, GB, IE, NL, SG, JP, AE). Germany (DE) is handled by loader_eurostat.py.

All values are derived from published sources cited inline. No raw file
acquisition is required — this is the Phase 2 equivalent of the Borderstep
anchor approach used for Germany in Phase 1.

Primary sources:
  - IEA Data Centres and Data Transmission Networks (2024)
  - Uptime Institute Global Data Center Survey 2023
  - DC Byte Global Data Center Market Report 2023
  - National regulator / grid operator reports (per geo, cited inline)

Confidence tiers:
  - Tier 1: ≥3 independent sources within 15% (IE, NL)
  - Tier 2: 2 sources within 25%, or top-down proxy (US, GB, SG, JP, AE)
"""

import logging
from datetime import date
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

CALIBRATION_YEAR = 2022

# ── DC capacity anchors ───────────────────────────────────────────────────────
# Formula check (deterministic, pue_improvement_rate=0):
#   TWh = installed_capacity_mw × utilisation_rate × pue × 8760h / 1e6

_TIER1_DC_ANCHORS: dict[str, list[dict[str, Any]]] = {
    # US: ~200 TWh (IEA 2024; LBNL 2024). Total modelled: 206.1 TWh (+3.1% ✓)
    "US": [
        {"product": "hyperscale",  "installed_capacity_mw": 13_500.0, "utilisation_rate": 0.65, "pue": 1.15, "ai_share": 0.35, "confidence_tier": 2, "sources": ["iea_2024", "lbnl_2024", "uptime_institute_2023"]},
        {"product": "colocation",  "installed_capacity_mw":  9_000.0, "utilisation_rate": 0.55, "pue": 1.40, "ai_share": 0.10, "confidence_tier": 2, "sources": ["iea_2024", "lbnl_2024", "dc_byte_2023"]},
        {"product": "on_premises", "installed_capacity_mw": 18_000.0, "utilisation_rate": 0.22, "pue": 1.65, "ai_share": 0.03, "confidence_tier": 2, "sources": ["lbnl_2024", "iea_2024"]},
    ],
    # GB: ~12 TWh (IEA 2024; techUK 2023). Total modelled: 12.55 TWh (+4.6% ✓)
    "GB": [
        {"product": "hyperscale",  "installed_capacity_mw":   700.0, "utilisation_rate": 0.65, "pue": 1.15, "ai_share": 0.28, "confidence_tier": 2, "sources": ["iea_2024", "techuk_2023", "uptime_institute_2023"]},
        {"product": "colocation",  "installed_capacity_mw":   700.0, "utilisation_rate": 0.55, "pue": 1.40, "ai_share": 0.08, "confidence_tier": 2, "sources": ["iea_2024", "techuk_2023", "dc_byte_2023"]},
        {"product": "on_premises", "installed_capacity_mw": 1_100.0, "utilisation_rate": 0.20, "pue": 1.70, "ai_share": 0.02, "confidence_tier": 2, "sources": ["iea_2024", "techuk_2023"]},
    ],
    # IE: ~5.8 TWh (EirGrid 2023; CSO Ireland 2022). Total modelled: 5.80 TWh (0.0% ✓)
    "IE": [
        {"product": "hyperscale",  "installed_capacity_mw": 500.0, "utilisation_rate": 0.70, "pue": 1.12, "ai_share": 0.30, "confidence_tier": 1, "sources": ["eirgrid_2023", "cso_ireland_2022", "uptime_institute_2023"]},
        {"product": "colocation",  "installed_capacity_mw": 230.0, "utilisation_rate": 0.60, "pue": 1.35, "ai_share": 0.06, "confidence_tier": 1, "sources": ["eirgrid_2023", "cso_ireland_2022", "dc_byte_2023"]},
        {"product": "on_premises", "installed_capacity_mw": 280.0, "utilisation_rate": 0.18, "pue": 1.65, "ai_share": 0.01, "confidence_tier": 1, "sources": ["eirgrid_2023", "cso_ireland_2022"]},
    ],
    # NL: ~4.0 TWh (CBS Netherlands 2022; DDA 2023). Total modelled: 4.08 TWh (+2.0% ✓)
    "NL": [
        {"product": "hyperscale",  "installed_capacity_mw": 280.0, "utilisation_rate": 0.65, "pue": 1.15, "ai_share": 0.25, "confidence_tier": 1, "sources": ["cbs_netherlands_2022", "dda_2023", "uptime_institute_2023"]},
        {"product": "colocation",  "installed_capacity_mw": 240.0, "utilisation_rate": 0.58, "pue": 1.35, "ai_share": 0.07, "confidence_tier": 1, "sources": ["cbs_netherlands_2022", "dda_2023", "dc_byte_2023"]},
        {"product": "on_premises", "installed_capacity_mw": 290.0, "utilisation_rate": 0.15, "pue": 1.60, "ai_share": 0.01, "confidence_tier": 1, "sources": ["cbs_netherlands_2022", "dda_2023"]},
    ],
    # SG: ~1.7 TWh (EMA Singapore 2023; IEA 2024). Total modelled: 1.75 TWh (+2.9% ✓)
    "SG": [
        {"product": "hyperscale",  "installed_capacity_mw": 115.0, "utilisation_rate": 0.70, "pue": 1.12, "ai_share": 0.30, "confidence_tier": 2, "sources": ["ema_singapore_2023", "iea_2024", "uptime_institute_2023"]},
        {"product": "colocation",  "installed_capacity_mw": 100.0, "utilisation_rate": 0.65, "pue": 1.25, "ai_share": 0.08, "confidence_tier": 2, "sources": ["ema_singapore_2023", "dc_byte_2023"]},
        {"product": "on_premises", "installed_capacity_mw": 155.0, "utilisation_rate": 0.12, "pue": 1.55, "ai_share": 0.01, "confidence_tier": 2, "sources": ["ema_singapore_2023", "iea_2024"]},
    ],
    # JP: ~15 TWh (IEA 2024; METI Japan 2023). Total modelled: 15.08 TWh (+0.5% ✓)
    "JP": [
        {"product": "hyperscale",  "installed_capacity_mw":   800.0, "utilisation_rate": 0.65, "pue": 1.20, "ai_share": 0.25, "confidence_tier": 2, "sources": ["iea_2024", "meti_japan_2023", "uptime_institute_2023"]},
        {"product": "colocation",  "installed_capacity_mw":   850.0, "utilisation_rate": 0.55, "pue": 1.40, "ai_share": 0.07, "confidence_tier": 2, "sources": ["iea_2024", "meti_japan_2023", "dc_byte_2023"]},
        {"product": "on_premises", "installed_capacity_mw": 1_500.0, "utilisation_rate": 0.18, "pue": 1.65, "ai_share": 0.02, "confidence_tier": 2, "sources": ["iea_2024", "meti_japan_2023"]},
    ],
    # AE: ~2.5 TWh (DEWA 2023; IEA proxy). Total modelled: 2.54 TWh (+1.6% ✓)
    "AE": [
        {"product": "hyperscale",  "installed_capacity_mw": 175.0, "utilisation_rate": 0.65, "pue": 1.20, "ai_share": 0.40, "confidence_tier": 2, "sources": ["dewa_2023", "iea_2024", "uptime_institute_2023"]},
        {"product": "colocation",  "installed_capacity_mw": 130.0, "utilisation_rate": 0.60, "pue": 1.35, "ai_share": 0.10, "confidence_tier": 2, "sources": ["dewa_2023", "dc_byte_2023"]},
        {"product": "on_premises", "installed_capacity_mw": 200.0, "utilisation_rate": 0.15, "pue": 1.60, "ai_share": 0.02, "confidence_tier": 2, "sources": ["dewa_2023", "iea_2024"]},
    ],
}

# ── Grid emission factors (kgCO2e/kWh) 2018-2024 ─────────────────────────────
# Source: IEA CO2 Emissions from Fuel Combustion 2024; national grid operators.
_TIER1_GRID_EF: dict[str, list[dict[str, Any]]] = {
    "US": [
        {"year": 2018, "grid_ef_kgco2e_per_kwh": 0.450},
        {"year": 2019, "grid_ef_kgco2e_per_kwh": 0.430},
        {"year": 2020, "grid_ef_kgco2e_per_kwh": 0.410},
        {"year": 2021, "grid_ef_kgco2e_per_kwh": 0.400},
        {"year": 2022, "grid_ef_kgco2e_per_kwh": 0.395},
        {"year": 2023, "grid_ef_kgco2e_per_kwh": 0.385},
        {"year": 2024, "grid_ef_kgco2e_per_kwh": 0.380},
    ],
    "GB": [
        {"year": 2018, "grid_ef_kgco2e_per_kwh": 0.280},
        {"year": 2019, "grid_ef_kgco2e_per_kwh": 0.250},
        {"year": 2020, "grid_ef_kgco2e_per_kwh": 0.230},
        {"year": 2021, "grid_ef_kgco2e_per_kwh": 0.220},
        {"year": 2022, "grid_ef_kgco2e_per_kwh": 0.225},
        {"year": 2023, "grid_ef_kgco2e_per_kwh": 0.215},
        {"year": 2024, "grid_ef_kgco2e_per_kwh": 0.210},
    ],
    "IE": [
        {"year": 2018, "grid_ef_kgco2e_per_kwh": 0.380},
        {"year": 2019, "grid_ef_kgco2e_per_kwh": 0.360},
        {"year": 2020, "grid_ef_kgco2e_per_kwh": 0.340},
        {"year": 2021, "grid_ef_kgco2e_per_kwh": 0.330},
        {"year": 2022, "grid_ef_kgco2e_per_kwh": 0.320},
        {"year": 2023, "grid_ef_kgco2e_per_kwh": 0.305},
        {"year": 2024, "grid_ef_kgco2e_per_kwh": 0.290},
    ],
    "NL": [
        {"year": 2018, "grid_ef_kgco2e_per_kwh": 0.430},
        {"year": 2019, "grid_ef_kgco2e_per_kwh": 0.400},
        {"year": 2020, "grid_ef_kgco2e_per_kwh": 0.370},
        {"year": 2021, "grid_ef_kgco2e_per_kwh": 0.360},
        {"year": 2022, "grid_ef_kgco2e_per_kwh": 0.345},
        {"year": 2023, "grid_ef_kgco2e_per_kwh": 0.330},
        {"year": 2024, "grid_ef_kgco2e_per_kwh": 0.320},
    ],
    "SG": [
        {"year": 2018, "grid_ef_kgco2e_per_kwh": 0.450},
        {"year": 2019, "grid_ef_kgco2e_per_kwh": 0.445},
        {"year": 2020, "grid_ef_kgco2e_per_kwh": 0.435},
        {"year": 2021, "grid_ef_kgco2e_per_kwh": 0.430},
        {"year": 2022, "grid_ef_kgco2e_per_kwh": 0.420},
        {"year": 2023, "grid_ef_kgco2e_per_kwh": 0.415},
        {"year": 2024, "grid_ef_kgco2e_per_kwh": 0.410},
    ],
    "JP": [
        {"year": 2018, "grid_ef_kgco2e_per_kwh": 0.490},
        {"year": 2019, "grid_ef_kgco2e_per_kwh": 0.480},
        {"year": 2020, "grid_ef_kgco2e_per_kwh": 0.470},
        {"year": 2021, "grid_ef_kgco2e_per_kwh": 0.460},
        {"year": 2022, "grid_ef_kgco2e_per_kwh": 0.455},
        {"year": 2023, "grid_ef_kgco2e_per_kwh": 0.448},
        {"year": 2024, "grid_ef_kgco2e_per_kwh": 0.440},
    ],
    "AE": [
        {"year": 2018, "grid_ef_kgco2e_per_kwh": 0.430},
        {"year": 2019, "grid_ef_kgco2e_per_kwh": 0.420},
        {"year": 2020, "grid_ef_kgco2e_per_kwh": 0.410},
        {"year": 2021, "grid_ef_kgco2e_per_kwh": 0.400},
        {"year": 2022, "grid_ef_kgco2e_per_kwh": 0.395},
        {"year": 2023, "grid_ef_kgco2e_per_kwh": 0.390},
        {"year": 2024, "grid_ef_kgco2e_per_kwh": 0.380},
    ],
}

# ── Electricity prices (USD/kWh, industrial) 2018-2024 ───────────────────────
# Source: IEA Energy Prices 2024; Eurostat (GB, IE, NL); EMA (SG); METI (JP); DEWA (AE).
_TIER1_ELECTRICITY_PRICES: dict[str, list[dict[str, Any]]] = {
    "US": [
        {"year": 2018, "price_usd_per_kwh": 0.068},
        {"year": 2019, "price_usd_per_kwh": 0.068},
        {"year": 2020, "price_usd_per_kwh": 0.067},
        {"year": 2021, "price_usd_per_kwh": 0.072},
        {"year": 2022, "price_usd_per_kwh": 0.082},
        {"year": 2023, "price_usd_per_kwh": 0.085},
        {"year": 2024, "price_usd_per_kwh": 0.086},
    ],
    "GB": [
        {"year": 2018, "price_usd_per_kwh": 0.145},
        {"year": 2019, "price_usd_per_kwh": 0.148},
        {"year": 2020, "price_usd_per_kwh": 0.142},
        {"year": 2021, "price_usd_per_kwh": 0.175},
        {"year": 2022, "price_usd_per_kwh": 0.310},
        {"year": 2023, "price_usd_per_kwh": 0.260},
        {"year": 2024, "price_usd_per_kwh": 0.220},
    ],
    "IE": [
        {"year": 2018, "price_usd_per_kwh": 0.155},
        {"year": 2019, "price_usd_per_kwh": 0.158},
        {"year": 2020, "price_usd_per_kwh": 0.152},
        {"year": 2021, "price_usd_per_kwh": 0.180},
        {"year": 2022, "price_usd_per_kwh": 0.320},
        {"year": 2023, "price_usd_per_kwh": 0.270},
        {"year": 2024, "price_usd_per_kwh": 0.230},
    ],
    "NL": [
        {"year": 2018, "price_usd_per_kwh": 0.090},
        {"year": 2019, "price_usd_per_kwh": 0.095},
        {"year": 2020, "price_usd_per_kwh": 0.088},
        {"year": 2021, "price_usd_per_kwh": 0.120},
        {"year": 2022, "price_usd_per_kwh": 0.280},
        {"year": 2023, "price_usd_per_kwh": 0.220},
        {"year": 2024, "price_usd_per_kwh": 0.185},
    ],
    "SG": [
        {"year": 2018, "price_usd_per_kwh": 0.115},
        {"year": 2019, "price_usd_per_kwh": 0.118},
        {"year": 2020, "price_usd_per_kwh": 0.112},
        {"year": 2021, "price_usd_per_kwh": 0.120},
        {"year": 2022, "price_usd_per_kwh": 0.145},
        {"year": 2023, "price_usd_per_kwh": 0.155},
        {"year": 2024, "price_usd_per_kwh": 0.150},
    ],
    "JP": [
        {"year": 2018, "price_usd_per_kwh": 0.155},
        {"year": 2019, "price_usd_per_kwh": 0.148},
        {"year": 2020, "price_usd_per_kwh": 0.142},
        {"year": 2021, "price_usd_per_kwh": 0.148},
        {"year": 2022, "price_usd_per_kwh": 0.175},
        {"year": 2023, "price_usd_per_kwh": 0.185},
        {"year": 2024, "price_usd_per_kwh": 0.180},
    ],
    "AE": [
        {"year": 2018, "price_usd_per_kwh": 0.075},
        {"year": 2019, "price_usd_per_kwh": 0.075},
        {"year": 2020, "price_usd_per_kwh": 0.073},
        {"year": 2021, "price_usd_per_kwh": 0.074},
        {"year": 2022, "price_usd_per_kwh": 0.078},
        {"year": 2023, "price_usd_per_kwh": 0.080},
        {"year": 2024, "price_usd_per_kwh": 0.080},
    ],
}

# ── Calibration benchmarks ────────────────────────────────────────────────────
TIER1_BENCHMARKS: dict[str, dict[str, Any]] = {
    "US": {"target_twh": 200.0, "tolerance": 0.20, "year": 2022, "source": "IEA 2024; LBNL 2024"},
    "GB": {"target_twh":  12.0, "tolerance": 0.20, "year": 2022, "source": "IEA 2024; techUK 2023"},
    "IE": {"target_twh":   5.8, "tolerance": 0.15, "year": 2022, "source": "EirGrid 2023; CSO Ireland 2022"},
    "NL": {"target_twh":   4.0, "tolerance": 0.20, "year": 2022, "source": "CBS Netherlands 2022; DDA 2023"},
    "SG": {"target_twh":   1.7, "tolerance": 0.20, "year": 2022, "source": "EMA Singapore 2023; IEA 2024"},
    "JP": {"target_twh":  15.0, "tolerance": 0.20, "year": 2022, "source": "IEA 2024; METI Japan 2023"},
    "AE": {"target_twh":   2.5, "tolerance": 0.25, "year": 2022, "source": "DEWA 2023; IEA proxy"},
}

TIER1_GEOS = list(_TIER1_DC_ANCHORS.keys())


# ── Public loader functions ───────────────────────────────────────────────────

def load_tier1_dc_anchor(
    geo: str,
    run_id: str,
    years: list[int] | None = None,
) -> pd.DataFrame:
    """Return the DC capacity gold fixture for a Tier 1 geo.

    Args:
        geo: ISO 3166-1 alpha-2 code. Must be one of TIER1_GEOS.
        run_id: UUID string for the current pipeline run.
        years: Calendar years to include. Defaults to 2018-2024.

    Returns:
        DataFrame with columns: geo, product, year, installed_capacity_mw,
        utilisation_rate, pue, ai_share, confidence_tier, source_ids,
        source_id, ingestion_date, version, run_id.

    Raises:
        ValueError: If geo is not in TIER1_GEOS.
    """
    if geo not in _TIER1_DC_ANCHORS:
        raise ValueError(f"geo '{geo}' not in TIER1_GEOS. Available: {TIER1_GEOS}")

    if years is None:
        years = list(range(2018, 2025))

    anchor = _TIER1_DC_ANCHORS[geo]
    rows: list[dict[str, Any]] = []
    for year in years:
        for dc in anchor:
            rows.append({
                "geo": geo,
                "year": year,
                "product": dc["product"],
                "installed_capacity_mw": dc["installed_capacity_mw"],
                "utilisation_rate": dc["utilisation_rate"],
                "pue": dc["pue"],
                "ai_share": dc["ai_share"],
                "confidence_tier": dc["confidence_tier"],
                "source_ids": dc["sources"],
                "source_id": dc["sources"][0],
                "ingestion_date": date.today().isoformat(),
                "version": "2024",
                "run_id": run_id,
            })

    df = pd.DataFrame(rows)
    logger.info("Tier 1 DC anchor loaded: geo=%s %d rows, %d years", geo, len(df), len(years))
    return df


def load_all_tier1_dc_anchors(
    run_id: str,
    geos: list[str] | None = None,
    years: list[int] | None = None,
) -> pd.DataFrame:
    """Return DC capacity gold fixtures for all (or selected) Tier 1 geos.

    Args:
        run_id: UUID string for the current pipeline run.
        geos: Subset of TIER1_GEOS to load. Defaults to all 7.
        years: Calendar years to include. Defaults to 2018-2024.

    Returns:
        Combined DataFrame for all requested geos.
    """
    target_geos = geos if geos is not None else TIER1_GEOS
    dfs = [load_tier1_dc_anchor(geo, run_id, years) for geo in target_geos]
    combined = pd.concat(dfs, ignore_index=True)
    logger.info(
        "All Tier 1 DC anchors loaded: %d geos, %d rows",
        len(target_geos), len(combined),
    )
    return combined


def load_tier1_grid_ef(
    run_id: str,
    geos: list[str] | None = None,
) -> pd.DataFrame:
    """Return grid emission factors for all (or selected) Tier 1 geos.

    Args:
        run_id: UUID string for the current pipeline run.
        geos: Subset of TIER1_GEOS to load. Defaults to all 7.

    Returns:
        DataFrame with columns: geo, year, grid_ef_kgco2e_per_kwh,
        confidence_tier, source_ids, run_id.
    """
    target_geos = geos if geos is not None else TIER1_GEOS
    rows: list[dict[str, Any]] = []
    for geo in target_geos:
        for entry in _TIER1_GRID_EF[geo]:
            rows.append({
                "geo": geo,
                "year": entry["year"],
                "grid_ef_kgco2e_per_kwh": entry["grid_ef_kgco2e_per_kwh"],
                "confidence_tier": 1,
                "source_ids": ["iea_2024"],
                "run_id": run_id,
            })
    df = pd.DataFrame(rows)
    logger.info("Tier 1 grid EF loaded: %d geos, %d rows", len(target_geos), len(df))
    return df


def load_tier1_electricity_prices(
    run_id: str,
    geos: list[str] | None = None,
) -> pd.DataFrame:
    """Return electricity prices for all (or selected) Tier 1 geos.

    Args:
        run_id: UUID string for the current pipeline run.
        geos: Subset of TIER1_GEOS to load. Defaults to all 7.

    Returns:
        DataFrame with columns: geo, year, price_usd_per_kwh, sector,
        confidence_tier, source_ids, run_id.
    """
    target_geos = geos if geos is not None else TIER1_GEOS
    rows: list[dict[str, Any]] = []
    for geo in target_geos:
        for entry in _TIER1_ELECTRICITY_PRICES[geo]:
            rows.append({
                "geo": geo,
                "year": entry["year"],
                "price_usd_per_kwh": entry["price_usd_per_kwh"],
                "sector": "industry",
                "confidence_tier": 1,
                "source_ids": ["iea_energy_prices_2024"],
                "run_id": run_id,
            })
    df = pd.DataFrame(rows)
    logger.info("Tier 1 electricity prices loaded: %d geos, %d rows", len(target_geos), len(df))
    return df
