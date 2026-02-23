"""Tier 1 hotspot ingest script — all 8 Tier 1 DC geographies.

Writes three gold tables to DuckDB for all Tier 1 DC hotspot geos:
  - datacentres  : DC capacity anchors (hyperscale / colo / on-prem)
  - grid_ef      : Grid emission factors 2018-2024
  - electricity_prices : Industrial electricity prices 2018-2024

Covers: DE (Stobbe 2025 anchor) + US, GB, IE, NL, SG, JP, AE (Tier 1 anchors).
Also writes networks and devices gold tables for DE, anchored to Stobbe et al. 2025.

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
        default=list(range(2013, 2036)),
        help="Years to include in DC anchor table (default: 2013-2035)",
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
        # Pass None so the loader uses its own default (2013-2024) regardless of --years.
        # The DC anchor has explicit year-keyed capacity rows; the loader interpolates between them.
        de_df = load_germany_dc_anchor(run_id=run_id, years=None)
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


# Full burn-in range required by the stock-flow model in src/models/devices.py.
# The devices model retires shipments from avg_lifespan_years ago; without pre-history
# the installed base starts at zero and takes lifespan years to reach steady state.
# Networks uses the same range for consistency.
_BURNIN_YEARS: list[int] = list(range(2002, 2036))


# Population ratios vs DE (83.2M) for scaling equipment counts / shipments.
# Sources: World Bank 2023 population estimates.
_POP_RATIO_VS_DE: dict[str, float] = {
    "US": 4.01,   # 334M
    "GB": 0.81,   # 67.3M
    "IE": 0.06,   # 5.1M
    "NL": 0.21,   # 17.6M
    "SG": 0.07,   # 5.9M
    "JP": 1.49,   # 124M
    "AE": 0.11,   # 9.4M
}


def _scale_networks_for_geo(
    de_df: pd.DataFrame, geo: str, run_id: str,
) -> pd.DataFrame:
    """Create proxy networks data for a non-DE geo by scaling DE equipment counts.

    Args:
        de_df: DE networks gold table.
        geo: Target ISO code.
        run_id: UUID string.

    Returns:
        Proxy DataFrame with same columns as de_df.
    """
    ratio = _POP_RATIO_VS_DE.get(geo, 0.5)
    proxy = de_df.copy()
    proxy["geo"] = geo
    proxy["equipment_count"] = (proxy["equipment_count"] * ratio).astype(int)
    proxy["confidence_tier"] = proxy["year"].apply(lambda y: 3 if y > 2024 else 2)
    proxy["source_ids"] = [["proxy_from_de_stobbe_2025"]] * len(proxy)
    proxy["source_id"] = "proxy_from_de_stobbe_2025"
    proxy["run_id"] = run_id
    return proxy


def _scale_devices_for_geo(
    de_df: pd.DataFrame, geo: str, run_id: str,
) -> pd.DataFrame:
    """Create proxy devices data for a non-DE geo by scaling DE shipments.

    Args:
        de_df: DE devices gold table.
        geo: Target ISO code.
        run_id: UUID string.

    Returns:
        Proxy DataFrame with same columns as de_df.
    """
    ratio = _POP_RATIO_VS_DE.get(geo, 0.5)
    proxy = de_df.copy()
    proxy["geo"] = geo
    proxy["shipments"] = (proxy["shipments"] * ratio).astype(int)
    proxy["confidence_tier"] = proxy["year"].apply(lambda y: 3 if y > 2024 else 2)
    proxy["source_ids"] = [["proxy_from_de_stobbe_2025"]] * len(proxy)
    proxy["source_id"] = "proxy_from_de_stobbe_2025"
    proxy["run_id"] = run_id
    return proxy


def build_networks_df(geos: list[str], run_id: str, years: list[int]) -> pd.DataFrame:  # noqa: ARG001
    """Build combined networks DataFrame for all tier-1 geos.

    DE uses Stobbe 2025 anchor. Non-DE geos use population-scaled proxies.
    Always uses the full burn-in + forecast range 2002-2035.

    Args:
        geos: List of geo ISO codes.
        run_id: UUID string for the current pipeline run.
        years: Ignored; kept for API compatibility with build_dc_df.

    Returns:
        Combined DataFrame for all supported geos, or empty DataFrame.
    """
    dfs: list[pd.DataFrame] = []
    de_df: pd.DataFrame | None = None

    if "DE" in geos:
        from src.data.loader_eurostat import load_germany_networks_anchor
        de_df = load_germany_networks_anchor(run_id=run_id, years=_BURNIN_YEARS)
        dfs.append(de_df)

    # Scale DE data for non-DE geos
    if de_df is None:
        from src.data.loader_eurostat import load_germany_networks_anchor
        de_df = load_germany_networks_anchor(run_id=run_id, years=_BURNIN_YEARS)

    for geo in geos:
        if geo != "DE" and geo in _POP_RATIO_VS_DE:
            dfs.append(_scale_networks_for_geo(de_df, geo, run_id))

    combined = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    logger.info("Networks combined: %d geos, %d rows (years 2002-2035)", combined["geo"].nunique() if not combined.empty else 0, len(combined))
    return combined


def build_devices_df(geos: list[str], run_id: str, years: list[int]) -> pd.DataFrame:  # noqa: ARG001
    """Build combined devices DataFrame for all tier-1 geos.

    DE uses Stobbe 2025 anchor. Non-DE geos use population-scaled proxies.
    Always uses the full burn-in + forecast range 2002-2035.

    Args:
        geos: List of geo ISO codes.
        run_id: UUID string for the current pipeline run.
        years: Ignored; kept for API compatibility with build_dc_df.

    Returns:
        Combined DataFrame for all supported geos, or empty DataFrame.
    """
    dfs: list[pd.DataFrame] = []
    de_df: pd.DataFrame | None = None

    if "DE" in geos:
        from src.data.loader_eurostat import load_germany_devices_anchor
        de_df = load_germany_devices_anchor(run_id=run_id, years=_BURNIN_YEARS)
        dfs.append(de_df)

    # Scale DE data for non-DE geos
    if de_df is None:
        from src.data.loader_eurostat import load_germany_devices_anchor
        de_df = load_germany_devices_anchor(run_id=run_id, years=_BURNIN_YEARS)

    for geo in geos:
        if geo != "DE" and geo in _POP_RATIO_VS_DE:
            dfs.append(_scale_devices_for_geo(de_df, geo, run_id))

    combined = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    logger.info("Devices combined: %d geos, %d rows (years 2002-2035)", combined["geo"].nunique() if not combined.empty else 0, len(combined))
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
    networks_df = build_networks_df(args.geos, run_id, args.years)
    devices_df = build_devices_df(args.geos, run_id, args.years)

    if args.dry_run:
        logger.info("DRY RUN — no writes to DuckDB")
        logger.info("Would write datacentres: %d rows", len(dc_df))
        logger.info("Would write grid_ef: %d rows", len(grid_ef_df))
        logger.info("Would write electricity_prices: %d rows", len(prices_df))
        logger.info("Would write networks: %d rows", len(networks_df))
        logger.info("Would write devices: %d rows", len(devices_df))
        print("\n--- datacentres sample (first 5 rows) ---")
        print(dc_df.head(5).to_string())
        print(f"\n--- grid_ef: {len(grid_ef_df)} rows across {dc_df['geo'].nunique() if not dc_df.empty else 0} geos ---")
        print(f"--- electricity_prices: {len(prices_df)} rows ---")
        print(f"--- networks: {len(networks_df)} rows ---")
        print(f"--- devices: {len(devices_df)} rows ---")
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

    if not networks_df.empty:
        write_gold_table(
            df=networks_df,
            table_name="networks",
            source_id="stobbe_fraunhofer_izm_2025",
            version="2025",
            run_id=run_id,
            if_exists=if_exists,
        )

    if not devices_df.empty:
        write_gold_table(
            df=devices_df,
            table_name="devices",
            source_id="stobbe_fraunhofer_izm_2025",
            version="2025",
            run_id=run_id,
            if_exists=if_exists,
        )

    logger.info(
        "Tier 1 ingest complete — datacentres: %d, grid_ef: %d, prices: %d, networks: %d, devices: %d rows",
        len(dc_df), len(grid_ef_df), len(prices_df), len(networks_df), len(devices_df),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
