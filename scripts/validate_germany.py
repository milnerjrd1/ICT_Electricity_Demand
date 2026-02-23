"""Germany Phase 1 calibration validation script.

Checks that the model output for Germany data centres in 2022 is within
±15% of the Borderstep 2023 benchmark (18 TWh total DC electricity).

Also cross-checks against:
  - BNetzA Monitoring 2023: ~16.5 TWh (±20% tolerance)
  - IEA Data Centres 2024 proxy: ~19.2 TWh (±20% tolerance)

Usage:
    uv run python scripts/validate_germany.py [--parquet PATH] [--fixture]

Flags:
    --parquet PATH   Path to a specific output parquet to validate.
                     Defaults to data/outputs/baseline_latest.parquet.
    --fixture        Run against the hardcoded anchor fixture (no DuckDB needed).
                     Use this in CI to get a deterministic result.
    --strict         Exit with code 1 if any check fails (default: warn only).
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
logger = logging.getLogger("validate_germany")

# ── Calibration targets ───────────────────────────────────────────────────────
BORDERSTEP_TWH = 18.0
BORDERSTEP_TOLERANCE = 0.15   # ±15%

CROSS_CHECKS = [
    ("BNetzA Monitoring 2023",   16.5, 0.20),
    ("IEA Data Centres 2024",    19.2, 0.20),
]

CALIBRATION_YEAR = 2022
BASELINE_PATH = Path("data/outputs/baseline_latest.parquet")


class CheckResult(NamedTuple):
    """Result of a single calibration check."""

    name: str
    target_twh: float
    tolerance: float
    model_twh: float
    deviation: float
    passed: bool


def run_checks(model_twh: float) -> list[CheckResult]:
    """Run all calibration checks against a model output value.

    Args:
        model_twh: Model output for DE data centres in TWh (2022).

    Returns:
        List of CheckResult named tuples.
    """
    results: list[CheckResult] = []

    # Primary: Borderstep
    dev = (model_twh - BORDERSTEP_TWH) / BORDERSTEP_TWH
    results.append(CheckResult(
        name="Borderstep 2023 (primary)",
        target_twh=BORDERSTEP_TWH,
        tolerance=BORDERSTEP_TOLERANCE,
        model_twh=model_twh,
        deviation=dev,
        passed=abs(dev) <= BORDERSTEP_TOLERANCE,
    ))

    # Cross-checks
    for name, target, tol in CROSS_CHECKS:
        dev = (model_twh - target) / target
        results.append(CheckResult(
            name=name,
            target_twh=target,
            tolerance=tol,
            model_twh=model_twh,
            deviation=dev,
            passed=abs(dev) <= tol,
        ))

    return results


def print_results(results: list[CheckResult], model_twh: float) -> None:
    """Print a formatted calibration report table.

    Args:
        results: List of CheckResult objects.
        model_twh: Model output value in TWh.
    """
    print()
    print("=" * 72)
    print(f"  Germany DC Calibration Report — model output: {model_twh:.2f} TWh (DE, {CALIBRATION_YEAR})")
    print("=" * 72)
    print(f"  {'Check':<35} {'Target':>8} {'Model':>8} {'Dev':>8} {'Tol':>6}  {'Status'}")
    print("  " + "-" * 68)
    for r in results:
        status = "✓ PASS" if r.passed else "✗ FAIL"
        print(
            f"  {r.name:<35} {r.target_twh:>7.1f}T {r.model_twh:>7.2f}T "
            f"{r.deviation:>+7.1%} {r.tolerance:>5.0%}  {status}"
        )
    print("=" * 72)
    all_pass = all(r.passed for r in results)
    primary_pass = results[0].passed if results else False
    print(f"  Primary check (Borderstep): {'PASS ✓' if primary_pass else 'FAIL ✗'}")
    print(f"  All checks:                 {'PASS ✓' if all_pass else 'PARTIAL / FAIL'}")
    print("=" * 72)
    print()


def extract_model_twh_from_parquet(parquet_path: Path) -> float:
    """Read baseline parquet and extract DE DC total TWh for calibration year.

    Args:
        parquet_path: Path to the output parquet file.

    Returns:
        Total kWh estimate for DE data centres in CALIBRATION_YEAR, in TWh.

    Raises:
        FileNotFoundError: If the parquet file does not exist.
        ValueError: If no matching rows are found.
    """
    if not parquet_path.exists():
        raise FileNotFoundError(
            f"Baseline parquet not found at {parquet_path}. "
            "Run: uv run python scripts/ingest_germany.py && "
            "uv run python scripts/run_pipeline.py --engine v1 --scenario ai_base"
        )

    df = pd.read_parquet(parquet_path)
    mask = (
        (df["geo"] == "DE")
        & (df["segment"] == "datacentres")
        & (df["year"] == CALIBRATION_YEAR)
    )
    subset = df[mask]

    if subset.empty:
        raise ValueError(
            f"No rows found for geo=DE, segment=datacentres, year={CALIBRATION_YEAR} "
            f"in {parquet_path}. Available geos: {sorted(df['geo'].unique())}, "
            f"years: {sorted(df['year'].unique())}"
        )

    total_kwh = subset["kwh_estimate"].sum()
    total_twh = total_kwh / 1e9  # kWh → TWh
    logger.info(
        "Extracted from parquet: DE datacentres %d = %.2f TWh (%d rows, scenario(s): %s)",
        CALIBRATION_YEAR, total_twh, len(subset),
        subset["scenario_id"].unique().tolist(),
    )
    return total_twh


def extract_model_twh_from_fixture() -> float:
    """Run the calibration model directly against the hardcoded anchor fixture.

    Uses the same fixture data as conftest.py germany_dc_gold. This is
    deterministic and requires no DuckDB or parquet file — suitable for CI.

    Returns:
        Total kWh estimate for DE data centres in CALIBRATION_YEAR, in TWh.
    """
    from src.data.loader_eurostat import load_germany_dc_anchor
    from src.models.datacentres import run_datacentres_model

    run_id = str(uuid.uuid4())
    dc_df = load_germany_dc_anchor(run_id=run_id, years=[CALIBRATION_YEAR])

    scenario_params = {
        "scenario_id": "ai_base",
        "pue_improvement_rate": 0.0,   # deterministic — no PUE improvement
        "utilisation_multiplier": 1.0,
        "ai_growth_rate": 0.0,
    }

    result_df = run_datacentres_model(dc_df, scenario_params, run_id=run_id)

    de_mask = (
        (result_df["geo"] == "DE")
        & (result_df["year"] == CALIBRATION_YEAR)
    )
    total_kwh = result_df[de_mask]["kwh_estimate"].sum()
    total_twh = total_kwh / 1e9
    logger.info(
        "Fixture run: DE datacentres %d = %.2f TWh (%d output rows)",
        CALIBRATION_YEAR, total_twh, len(result_df[de_mask]),
    )
    return total_twh


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Germany Phase 1 calibration validation — checks DE DC output vs Borderstep 2023"
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
        help="Run against hardcoded anchor fixture (no DuckDB needed, for CI)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if primary (Borderstep) check fails",
    )
    return parser.parse_args()


def main() -> int:
    """Run the Germany calibration validation. Returns exit code."""
    args = parse_args()

    logger.info("Germany calibration validation — year=%d, primary target=%.1f TWh ±%.0f%%",
                CALIBRATION_YEAR, BORDERSTEP_TWH, BORDERSTEP_TOLERANCE * 100)

    if args.fixture:
        logger.info("Mode: fixture (deterministic anchor, no DuckDB required)")
        model_twh = extract_model_twh_from_fixture()
    else:
        logger.info("Mode: parquet (%s)", args.parquet)
        try:
            model_twh = extract_model_twh_from_parquet(args.parquet)
        except (FileNotFoundError, ValueError) as exc:
            logger.error("%s", exc)
            return 1

    results = run_checks(model_twh)
    print_results(results, model_twh)

    primary_passed = results[0].passed
    all_passed = all(r.passed for r in results)

    if not primary_passed:
        logger.error(
            "PRIMARY CALIBRATION FAIL: DE DC %d = %.2f TWh, target %.1f TWh ±%.0f%%",
            CALIBRATION_YEAR, model_twh, BORDERSTEP_TWH, BORDERSTEP_TOLERANCE * 100,
        )
        if args.strict:
            return 1
    elif not all_passed:
        logger.warning("Primary check passed but one or more cross-checks failed — review above")
    else:
        logger.info("All calibration checks passed ✓")

    return 0


if __name__ == "__main__":
    sys.exit(main())
