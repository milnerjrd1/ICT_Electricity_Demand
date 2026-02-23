"""Germany Phase 1 ingest script.

Writes three gold tables to DuckDB for Germany:
  - datacentres  : Borderstep 2023 capacity anchor (hyperscale / colo / on-prem)
  - grid_ef      : DE grid emission factors 2018-2024 (IEA / Umweltbundesamt)
  - electricity_prices : DE industrial electricity prices 2018-2024 (Eurostat / IEA)

Usage:
    uv run python scripts/ingest_germany.py [--replace]

Flags:
    --replace   Drop and recreate each table instead of appending (default: append)
    --dry-run   Print what would be written without touching DuckDB
"""

import argparse
import logging
import sys
import uuid
from datetime import date
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ingest_germany")

# ── Published DE grid emission factors (kgCO2e/kWh) ──────────────────────────
# Source: IEA CO2 Emissions from Fuel Combustion 2024; Umweltbundesamt (UBA)
# Historical values 2018-2023; 2024 from UBA preliminary estimate.
# Confidence tier 1: 3 independent sources within 5% (IEA, UBA, Destatis).
_DE_GRID_EF: list[dict] = [
    {"year": 2018, "grid_ef_kgco2e_per_kwh": 0.470, "confidence_tier": 1},
    {"year": 2019, "grid_ef_kgco2e_per_kwh": 0.410, "confidence_tier": 1},
    {"year": 2020, "grid_ef_kgco2e_per_kwh": 0.366, "confidence_tier": 1},
    {"year": 2021, "grid_ef_kgco2e_per_kwh": 0.420, "confidence_tier": 1},  # coal rebound
    {"year": 2022, "grid_ef_kgco2e_per_kwh": 0.434, "confidence_tier": 1},  # gas crisis
    {"year": 2023, "grid_ef_kgco2e_per_kwh": 0.380, "confidence_tier": 1},
    {"year": 2024, "grid_ef_kgco2e_per_kwh": 0.350, "confidence_tier": 1},  # UBA preliminary
]

# ── Published DE industrial electricity prices (USD/kWh) ─────────────────────
# Source: Eurostat nrg_pc_205 (industry band IC, taxes included); IEA Energy Prices 2024.
# EUR converted to USD at annual average FX (ECB). Confidence tier 1.
_DE_ELECTRICITY_PRICES: list[dict] = [
    {"year": 2018, "price_usd_per_kwh": 0.185, "sector": "industry", "confidence_tier": 1},
    {"year": 2019, "price_usd_per_kwh": 0.193, "sector": "industry", "confidence_tier": 1},
    {"year": 2020, "price_usd_per_kwh": 0.196, "sector": "industry", "confidence_tier": 1},
    {"year": 2021, "price_usd_per_kwh": 0.210, "sector": "industry", "confidence_tier": 1},
    {"year": 2022, "price_usd_per_kwh": 0.320, "sector": "industry", "confidence_tier": 1},  # energy crisis
    {"year": 2023, "price_usd_per_kwh": 0.280, "sector": "industry", "confidence_tier": 1},
    {"year": 2024, "price_usd_per_kwh": 0.240, "sector": "industry", "confidence_tier": 1},
]


def build_grid_ef_df(run_id: str) -> pd.DataFrame:
    """Build Germany grid emission factor DataFrame.

    Args:
        run_id: UUID string for the current pipeline run.

    Returns:
        DataFrame with columns: geo, year, grid_ef_kgco2e_per_kwh, confidence_tier,
        source_ids, source_id, ingestion_date, version, run_id.
    """
    rows = []
    for entry in _DE_GRID_EF:
        rows.append({
            "geo": "DE",
            "year": entry["year"],
            "grid_ef_kgco2e_per_kwh": entry["grid_ef_kgco2e_per_kwh"],
            "confidence_tier": entry["confidence_tier"],
            "source_ids": ["iea_2024", "umweltbundesamt_2024", "destatis_2024"],
            "run_id": run_id,
        })
    df = pd.DataFrame(rows)
    logger.info("Built grid_ef DataFrame: %d rows for DE", len(df))
    return df


def build_electricity_prices_df(run_id: str) -> pd.DataFrame:
    """Build Germany electricity prices DataFrame.

    Args:
        run_id: UUID string for the current pipeline run.

    Returns:
        DataFrame with columns: geo, year, price_usd_per_kwh, sector,
        confidence_tier, source_ids, run_id.
    """
    rows = []
    for entry in _DE_ELECTRICITY_PRICES:
        rows.append({
            "geo": "DE",
            "year": entry["year"],
            "price_usd_per_kwh": entry["price_usd_per_kwh"],
            "sector": entry["sector"],
            "confidence_tier": entry["confidence_tier"],
            "source_ids": ["eurostat_nrg_pc_205_2024", "iea_energy_prices_2024"],
            "run_id": run_id,
        })
    df = pd.DataFrame(rows)
    logger.info("Built electricity_prices DataFrame: %d rows for DE", len(df))
    return df


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Germany Phase 1 ingest — writes gold tables to DuckDB")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Drop and recreate each table instead of appending",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be written without touching DuckDB",
    )
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=list(range(2018, 2025)),
        help="Years to include in DC anchor table (default: 2018-2024)",
    )
    return parser.parse_args()


def main() -> int:
    """Run the Germany ingest. Returns exit code (0 = success, 1 = error)."""
    args = parse_args()
    run_id = str(uuid.uuid4())
    if_exists = "replace" if args.replace else "append"

    logger.info("Germany ingest — run_id=%s  if_exists=%s  dry_run=%s", run_id, if_exists, args.dry_run)

    # ── 1. Germany DC anchor ──────────────────────────────────────────────────
    from src.data.loader_eurostat import load_germany_dc_anchor
    dc_df = load_germany_dc_anchor(run_id=run_id, years=args.years)
    logger.info("DC anchor: %d rows, geos=%s, years=%s", len(dc_df), dc_df["geo"].unique().tolist(), sorted(dc_df["year"].unique().tolist()))

    # ── 2. Grid emission factors ──────────────────────────────────────────────
    grid_ef_df = build_grid_ef_df(run_id)

    # ── 3. Electricity prices ─────────────────────────────────────────────────
    prices_df = build_electricity_prices_df(run_id)

    if args.dry_run:
        logger.info("DRY RUN — no writes to DuckDB")
        logger.info("Would write datacentres: %d rows", len(dc_df))
        logger.info("Would write grid_ef: %d rows", len(grid_ef_df))
        logger.info("Would write electricity_prices: %d rows", len(prices_df))
        print("\n--- datacentres sample ---")
        print(dc_df.head(3).to_string())
        print("\n--- grid_ef ---")
        print(grid_ef_df.to_string())
        print("\n--- electricity_prices ---")
        print(prices_df.to_string())
        return 0

    # ── 4. Write to DuckDB ────────────────────────────────────────────────────
    from src.data.gold_writer import write_gold_table

    write_gold_table(
        df=dc_df,
        table_name="datacentres",
        source_id="borderstep_2023",
        version="2023",
        run_id=run_id,
        if_exists=if_exists,
    )

    write_gold_table(
        df=grid_ef_df,
        table_name="grid_ef",
        source_id="iea_2024",
        version="2024",
        run_id=run_id,
        if_exists=if_exists,
    )

    write_gold_table(
        df=prices_df,
        table_name="electricity_prices",
        source_id="eurostat_nrg_pc_205_2024",
        version="2024",
        run_id=run_id,
        if_exists=if_exists,
    )

    logger.info(
        "Ingest complete — datacentres: %d rows, grid_ef: %d rows, electricity_prices: %d rows",
        len(dc_df), len(grid_ef_df), len(prices_df),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
