"""Tier 1 hotspot ingest script — all 8 Tier 1 DC geographies.

Writes three gold tables to DuckDB for all Tier 1 DC hotspot geos:
  - datacentres  : DC capacity anchors (hyperscale / colo / on-prem)
  - grid_ef      : Grid emission factors 2018-2024
  - electricity_prices : Industrial electricity prices 2018-2024

Covers: DE (Borderstep anchor) + US, GB, IE, NL, SG, JP, AE (Tier 1 anchors).

Usage:
    uv run python scripts/ingest_tier1.py [--geos US GB ...] [--replace] [--dry-run]

Flags:
    --geos       Subset of geos to ingest (default: all 8 Tier 1)
    --replace    Drop and recreate each table instead of appending
    --dry-run    Print what would be written without touching DuckDB
    --years      Years to include in DC anchor (default: 2018-2024)
"""

import argparse
import logging
import sys
import uuid

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ingest_tier1")

ALL_TIER1_GEOS = ["DE", "US", "GB", "IE", "NL", "SG", "JP", "AE"]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Tier 1 hotspot ingest — writes DC anchor + grid EF + prices to DuckDB"
    )
    parser.add_argument(
        "--geos",
        nargs="+",
        default=ALL_TIER1_GEOS,
        help=f"Geos to ingest (default: all {len(ALL_TIER1_GEOS)})",
    )
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


def build_dc_df(geos: list[str], run_id: str, years: list[int]) -> pd.DataFrame:
    """Build combined DC anchor DataFrame for all requested geos.

    Args:
        geos: List of geo ISO codes.
        run_id: UUID string for the current pipeline run.
        years: Calendar years to include.

    Returns:
        Combined DataFrame for all geos.
    """
    dfs: list[pd.DataFrame] = []

    if "DE" in geos:
        from src.data.loader_eurostat import load_germany_dc_anchor
        de_df = load_germany_dc_anchor(run_id=run_id, years=years)
        dfs.append(de_df)

    tier1_geos = [g for g in geos if g != "DE"]
    if tier1_geos:
        from src.data.loader_tier1 import load_all_tier1_dc_anchors
        t1_df = load_all_tier1_dc_anchors(run_id=run_id, geos=tier1_geos, years=years)
        dfs.append(t1_df)

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)
    logger.info(
        "DC anchors combined: %d geos, %d rows, years=%s",
        len(geos), len(combined), sorted(combined["year"].unique().tolist()),
    )
    return combined


def build_grid_ef_df(geos: list[str], run_id: str) -> pd.DataFrame:
    """Build combined grid EF DataFrame for all requested geos.

    Args:
        geos: List of geo ISO codes.
        run_id: UUID string for the current pipeline run.

    Returns:
        Combined DataFrame for all geos.
    """
    from src.data.loader_tier1 import load_tier1_grid_ef

    # DE grid EF is hardcoded in ingest_germany.py; replicate here for completeness
    _DE_GRID_EF = [
        {"year": 2018, "grid_ef_kgco2e_per_kwh": 0.470},
        {"year": 2019, "grid_ef_kgco2e_per_kwh": 0.410},
        {"year": 2020, "grid_ef_kgco2e_per_kwh": 0.366},
        {"year": 2021, "grid_ef_kgco2e_per_kwh": 0.420},
        {"year": 2022, "grid_ef_kgco2e_per_kwh": 0.434},
        {"year": 2023, "grid_ef_kgco2e_per_kwh": 0.380},
        {"year": 2024, "grid_ef_kgco2e_per_kwh": 0.350},
    ]

    dfs: list[pd.DataFrame] = []

    if "DE" in geos:
        de_rows = [
            {
                "geo": "DE",
                "year": e["year"],
                "grid_ef_kgco2e_per_kwh": e["grid_ef_kgco2e_per_kwh"],
                "confidence_tier": 1,
                "source_ids": ["iea_2024", "umweltbundesamt_2024"],
                "run_id": run_id,
            }
            for e in _DE_GRID_EF
        ]
        dfs.append(pd.DataFrame(de_rows))

    tier1_geos = [g for g in geos if g != "DE"]
    if tier1_geos:
        dfs.append(load_tier1_grid_ef(run_id=run_id, geos=tier1_geos))

    combined = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    logger.info("Grid EF combined: %d geos, %d rows", len(geos), len(combined))
    return combined


def build_prices_df(geos: list[str], run_id: str) -> pd.DataFrame:
    """Build combined electricity prices DataFrame for all requested geos.

    Args:
        geos: List of geo ISO codes.
        run_id: UUID string for the current pipeline run.

    Returns:
        Combined DataFrame for all geos.
    """
    from src.data.loader_tier1 import load_tier1_electricity_prices

    _DE_PRICES = [
        {"year": 2018, "price_usd_per_kwh": 0.185},
        {"year": 2019, "price_usd_per_kwh": 0.193},
        {"year": 2020, "price_usd_per_kwh": 0.196},
        {"year": 2021, "price_usd_per_kwh": 0.210},
        {"year": 2022, "price_usd_per_kwh": 0.320},
        {"year": 2023, "price_usd_per_kwh": 0.280},
        {"year": 2024, "price_usd_per_kwh": 0.240},
    ]

    dfs: list[pd.DataFrame] = []

    if "DE" in geos:
        de_rows = [
            {
                "geo": "DE",
                "year": e["year"],
                "price_usd_per_kwh": e["price_usd_per_kwh"],
                "sector": "industry",
                "confidence_tier": 1,
                "source_ids": ["eurostat_nrg_pc_205_2024", "iea_energy_prices_2024"],
                "run_id": run_id,
            }
            for e in _DE_PRICES
        ]
        dfs.append(pd.DataFrame(de_rows))

    tier1_geos = [g for g in geos if g != "DE"]
    if tier1_geos:
        dfs.append(load_tier1_electricity_prices(run_id=run_id, geos=tier1_geos))

    combined = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    logger.info("Electricity prices combined: %d geos, %d rows", len(geos), len(combined))
    return combined


def main() -> int:
    """Run the Tier 1 ingest. Returns exit code (0 = success, 1 = error)."""
    args = parse_args()
    run_id = str(uuid.uuid4())
    if_exists = "replace" if args.replace else "append"

    # Validate geos
    invalid = [g for g in args.geos if g not in ALL_TIER1_GEOS]
    if invalid:
        logger.error("Unknown geos: %s. Valid: %s", invalid, ALL_TIER1_GEOS)
        return 1

    logger.info(
        "Tier 1 ingest — run_id=%s  geos=%s  if_exists=%s  dry_run=%s",
        run_id, args.geos, if_exists, args.dry_run,
    )

    dc_df = build_dc_df(args.geos, run_id, args.years)
    grid_ef_df = build_grid_ef_df(args.geos, run_id)
    prices_df = build_prices_df(args.geos, run_id)

    if args.dry_run:
        logger.info("DRY RUN — no writes to DuckDB")
        logger.info("Would write datacentres: %d rows", len(dc_df))
        logger.info("Would write grid_ef: %d rows", len(grid_ef_df))
        logger.info("Would write electricity_prices: %d rows", len(prices_df))
        print("\n--- datacentres sample (first 5 rows) ---")
        print(dc_df.head(5).to_string())
        print(f"\n--- grid_ef: {len(grid_ef_df)} rows across {dc_df['geo'].nunique() if not dc_df.empty else 0} geos ---")
        print(f"--- electricity_prices: {len(prices_df)} rows ---")
        return 0

    from src.data.gold_writer import write_gold_table

    write_gold_table(
        df=dc_df,
        table_name="datacentres",
        source_id="tier1_anchor_2024",
        version="2024",
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
        source_id="iea_energy_prices_2024",
        version="2024",
        run_id=run_id,
        if_exists=if_exists,
    )

    logger.info(
        "Tier 1 ingest complete — datacentres: %d rows, grid_ef: %d rows, electricity_prices: %d rows",
        len(dc_df), len(grid_ef_df), len(prices_df),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
