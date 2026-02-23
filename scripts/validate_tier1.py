"""Tier 1 hotspot calibration validation script.

Checks that model output for each Tier 1 DC geo in 2022 is within its
published benchmark tolerance. Extends validate_germany.py to all 8 geos.

Usage:
    uv run python scripts/validate_tier1.py [--parquet PATH] [--fixture] [--geos US GB ...]

Flags:
    --parquet PATH   Path to output parquet (default: data/outputs/baseline_latest.parquet)
    --fixture        Run against hardcoded anchor fixtures (no DuckDB needed, for CI)
    --geos           Subset of Tier 1 geos to check (default: all 8)
    --strict         Exit with code 1 if any primary check fails
"""

import argparse
import logging
import sys
import uuid
from pathlib import Path
from typing import NamedTuple

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("validate_tier1")

CALIBRATION_YEAR = 2022
BASELINE_PATH = Path("data/outputs/baseline_latest.parquet")

# DE benchmark (matches validate_germany.py)
_DE_BENCHMARK = {"target_twh": 18.0, "tolerance": 0.15, "source": "Borderstep 2023"}

ALL_TIER1_GEOS = ["DE", "US", "GB", "IE", "NL", "SG", "JP", "AE"]


class CheckResult(NamedTuple):
    """Result of a single geo calibration check."""

    geo: str
    target_twh: float
    tolerance: float
    model_twh: float
    deviation: float
    passed: bool
    source: str


def get_benchmark(geo: str) -> dict:
    """Return the benchmark dict for a geo.

    Args:
        geo: ISO geo code.

    Returns:
        Dict with target_twh, tolerance, source keys.
    """
    if geo == "DE":
        return _DE_BENCHMARK
    from src.data.loader_tier1 import TIER1_BENCHMARKS
    return TIER1_BENCHMARKS[geo]


def run_fixture_check(geo: str, run_id: str) -> float:
    """Run model against anchor fixture and return TWh for calibration year.

    Args:
        geo: ISO geo code.
        run_id: UUID for this run.

    Returns:
        Total TWh for geo datacentres in CALIBRATION_YEAR.
    """
    from src.models.datacentres import run_datacentres_model

    scenario_params = {
        "scenario_id": "ai_base",
        "pue_improvement_rate": 0.0,
        "utilisation_multiplier": 1.0,
        "ai_growth_rate": 0.0,
    }

    if geo == "DE":
        from src.data.loader_eurostat import load_germany_dc_anchor
        dc_df = load_germany_dc_anchor(run_id=run_id, years=[CALIBRATION_YEAR])
    else:
        from src.data.loader_tier1 import load_tier1_dc_anchor
        dc_df = load_tier1_dc_anchor(geo=geo, run_id=run_id, years=[CALIBRATION_YEAR])

    result_df = run_datacentres_model(dc_df, scenario_params, run_id=run_id)
    mask = (result_df["geo"] == geo) & (result_df["year"] == CALIBRATION_YEAR)
    total_kwh = result_df[mask]["kwh_estimate"].sum()
    return total_kwh / 1e9


def run_parquet_check(geo: str, df: pd.DataFrame) -> float:
    """Extract model TWh for a geo from a loaded parquet DataFrame.

    Args:
        geo: ISO geo code.
        df: Full baseline parquet DataFrame.

    Returns:
        Total TWh for geo datacentres in CALIBRATION_YEAR.

    Raises:
        ValueError: If no matching rows found.
    """
    mask = (
        (df["geo"] == geo)
        & (df["segment"] == "datacentres")
        & (df["year"] == CALIBRATION_YEAR)
    )
    subset = df[mask]
    if subset.empty:
        raise ValueError(
            f"No rows for geo={geo}, segment=datacentres, year={CALIBRATION_YEAR}"
        )
    return subset["kwh_estimate"].sum() / 1e9


def check_geo(geo: str, model_twh: float) -> CheckResult:
    """Run calibration check for a single geo.

    Args:
        geo: ISO geo code.
        model_twh: Model output in TWh.

    Returns:
        CheckResult named tuple.
    """
    bm = get_benchmark(geo)
    dev = (model_twh - bm["target_twh"]) / bm["target_twh"]
    return CheckResult(
        geo=geo,
        target_twh=bm["target_twh"],
        tolerance=bm["tolerance"],
        model_twh=model_twh,
        deviation=dev,
        passed=abs(dev) <= bm["tolerance"],
        source=bm["source"],
    )


def print_results(results: list[CheckResult]) -> None:
    """Print a formatted calibration report table.

    Args:
        results: List of CheckResult objects.
    """
    print()
    print("=" * 80)
    print(f"  Tier 1 DC Calibration Report — year {CALIBRATION_YEAR}")
    print("=" * 80)
    print(f"  {'Geo':<5} {'Target':>9} {'Model':>9} {'Dev':>8} {'Tol':>6}  {'Status':<8}  Source")
    print("  " + "-" * 76)
    for r in results:
        status = "✓ PASS" if r.passed else "✗ FAIL"
        print(
            f"  {r.geo:<5} {r.target_twh:>8.1f}T {r.model_twh:>8.2f}T "
            f"{r.deviation:>+7.1%} {r.tolerance:>5.0%}  {status:<8}  {r.source}"
        )
    print("=" * 80)
    n_pass = sum(1 for r in results if r.passed)
    n_fail = len(results) - n_pass
    print(f"  Summary: {n_pass}/{len(results)} PASS  |  {n_fail} FAIL")
    print("=" * 80)
    print()


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Tier 1 DC calibration validation — checks all 8 Tier 1 geos vs benchmarks"
    )
    parser.add_argument(
        "--parquet",
        type=Path,
        default=BASELINE_PATH,
        help=f"Path to output parquet (default: {BASELINE_PATH})",
    )
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Run against hardcoded anchor fixtures (no DuckDB needed, for CI)",
    )
    parser.add_argument(
        "--geos",
        nargs="+",
        default=ALL_TIER1_GEOS,
        help="Subset of Tier 1 geos to check (default: all 8)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any primary check fails",
    )
    return parser.parse_args()


def main() -> int:
    """Run Tier 1 calibration validation. Returns exit code."""
    args = parse_args()

    invalid = [g for g in args.geos if g not in ALL_TIER1_GEOS]
    if invalid:
        logger.error("Unknown geos: %s. Valid: %s", invalid, ALL_TIER1_GEOS)
        return 1

    logger.info(
        "Tier 1 calibration — year=%d, geos=%s, mode=%s",
        CALIBRATION_YEAR, args.geos, "fixture" if args.fixture else f"parquet({args.parquet})",
    )

    results: list[CheckResult] = []
    run_id = str(uuid.uuid4())

    if args.fixture:
        for geo in args.geos:
            model_twh = run_fixture_check(geo, run_id)
            results.append(check_geo(geo, model_twh))
            logger.info("Fixture %s: %.2f TWh", geo, model_twh)
    else:
        if not args.parquet.exists():
            logger.error(
                "Baseline parquet not found at %s. "
                "Run: uv run python scripts/ingest_tier1.py --replace && "
                "uv run python scripts/run_pipeline.py --engine v1 --skip-diff",
                args.parquet,
            )
            return 1
        df = pd.read_parquet(args.parquet)
        for geo in args.geos:
            try:
                model_twh = run_parquet_check(geo, df)
                results.append(check_geo(geo, model_twh))
                logger.info("Parquet %s: %.2f TWh", geo, model_twh)
            except ValueError as exc:
                logger.warning("Skipping %s: %s", geo, exc)

    print_results(results)

    n_fail = sum(1 for r in results if not r.passed)
    if n_fail > 0:
        logger.error("%d/%d calibration checks FAILED", n_fail, len(results))
        if args.strict:
            return 1
    else:
        logger.info("All %d calibration checks passed ✓", len(results))

    return 0


if __name__ == "__main__":
    sys.exit(main())
