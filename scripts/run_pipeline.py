"""End-to-end pipeline script.

Usage:
    uv run python scripts/run_pipeline.py [--scenario all|<scenario_id>] [--mc-iterations 1000]

Runs: ingest → model → validate → diff vs previous baseline → export release notes.
Every run gets a UUID run_id. Outputs written to data/gold/.
"""

import argparse
import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("pipeline")

OUTPUTS_DIR = Path("data/outputs")
BASELINE_PATH = OUTPUTS_DIR / "baseline_latest.parquet"
RUN_LOG_PATH = OUTPUTS_DIR / "run_log.jsonl"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="ICT Electricity Demand Pipeline")
    parser.add_argument(
        "--scenario",
        default="all",
        help="Scenario ID to run, or 'all' to run all registered scenarios (default: all)",
    )
    parser.add_argument(
        "--mc-iterations",
        type=int,
        default=1000,
        help="Monte Carlo iterations for Tier 1 DC outputs (default: 1000)",
    )
    parser.add_argument(
        "--skip-diff",
        action="store_true",
        help="Skip diff report against previous baseline",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate pipeline structure without running models",
    )
    parser.add_argument(
        "--engine",
        choices=["v1", "v2"],
        default="v1",
        help="Model engine: v1 (legacy capacity-MW) or v2 (study-aligned, default: v1)",
    )
    parser.add_argument(
        "--grid-scenario",
        nargs="+",
        default=["reference", "ambitious", "fossil"],
        help="Grid mix scenarios for v2 engine (default: reference ambitious fossil)",
    )
    return parser.parse_args()


def load_gold_tables() -> dict[str, pd.DataFrame]:
    """Load all available gold tables from DuckDB (v1 engine keys).

    Returns:
        Dict mapping table name → DataFrame. Empty DataFrames for missing tables.
    """
    from src.data.gold_writer import list_gold_tables, read_gold_table

    available = list_gold_tables()
    logger.info("Available gold tables: %s", available)

    tables: dict[str, pd.DataFrame] = {}
    for name in ["devices", "networks", "datacentres", "grid_ef", "electricity_prices"]:
        if name in available:
            tables[name] = read_gold_table(name)
            logger.info("Loaded gold table '%s': %d rows", name, len(tables[name]))
        else:
            logger.warning("Gold table '%s' not found — skipping", name)
            tables[name] = pd.DataFrame()

    return tables


def load_gold_tables_v2() -> dict[str, pd.DataFrame]:
    """Load gold tables for the v2 study-aligned engine.

    Loads v2-specific keys (devices_v2, telecom_networks, datacentres_v2) when
    available, falling back to legacy keys so Phase 1 data (written under
    'datacentres', 'grid_ef', 'electricity_prices') is picked up automatically.

    Returns:
        Dict mapping table name → DataFrame. Empty DataFrames for missing tables.
    """
    from src.data.gold_writer import list_gold_tables, read_gold_table

    available = list_gold_tables()
    logger.info("Available gold tables (v2 load): %s", available)

    tables: dict[str, pd.DataFrame] = {}

    # v2-specific keys (preferred)
    for name in ["devices_v2", "telecom_networks", "datacentres_v2"]:
        if name in available:
            tables[name] = read_gold_table(name)
            logger.info("Loaded v2 gold table '%s': %d rows", name, len(tables[name]))
        else:
            tables[name] = pd.DataFrame()

    # Legacy keys — used as fallback when v2-specific tables are absent
    for name in ["devices", "networks", "datacentres", "grid_ef", "electricity_prices"]:
        if name in available:
            tables[name] = read_gold_table(name)
            logger.info("Loaded legacy gold table '%s': %d rows", name, len(tables[name]))
        else:
            tables[name] = pd.DataFrame()

    return tables


def run_models(
    gold_tables: dict[str, pd.DataFrame],
    scenario_ids: list[str],
    run_id: str,
    mc_iterations: int,
) -> dict[str, pd.DataFrame]:
    """Run all model modules for each scenario (v1 engine).

    Args:
        gold_tables: Dict of gold table DataFrames.
        scenario_ids: List of scenario IDs to run.
        run_id: UUID for this pipeline run.
        mc_iterations: Monte Carlo iterations for Tier 1 DC.

    Returns:
        Dict mapping scenario_id → output DataFrame.
    """
    from src.scenarios.engine import run_all_scenarios

    return run_all_scenarios(
        scenario_ids=scenario_ids,
        gold_tables=gold_tables,
        run_id=run_id,
        monte_carlo_iterations=mc_iterations,
    )


def run_models_v2(
    gold_tables: dict[str, pd.DataFrame],
    scenario_ids: list[str],
    run_id: str,
    grid_scenario_ids: list[str],
) -> dict[str, pd.DataFrame]:
    """Run all model modules for each scenario using the v2 study-aligned engine.

    Flattens the nested demand × grid result dict into a single DataFrame per
    demand scenario (concatenating across grid scenarios) so the rest of the
    pipeline (validation, diff, save) works unchanged.

    Args:
        gold_tables: Dict of gold table DataFrames (v2 + legacy keys).
        scenario_ids: List of demand scenario IDs to run.
        run_id: UUID for this pipeline run.
        grid_scenario_ids: Grid mix scenarios to cross with each demand scenario.

    Returns:
        Dict mapping scenario_id → combined output DataFrame (all grid scenarios).
    """
    from src.scenarios.engine import run_all_scenarios_v2

    nested = run_all_scenarios_v2(
        scenario_ids=scenario_ids,
        gold_tables=gold_tables,
        grid_scenario_ids=grid_scenario_ids,
        run_id=run_id,
    )

    # Flatten: for each demand scenario, concat outputs across all grid scenarios
    flat: dict[str, pd.DataFrame] = {}
    for demand_id, grid_results in nested.items():
        dfs = [
            result["outputs"]
            for result in grid_results.values()
            if not result["outputs"].empty
        ]
        flat[demand_id] = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
        logger.info(
            "v2 engine: demand='%s' → %d rows across %d grid scenarios",
            demand_id, len(flat[demand_id]), len(grid_results),
        )

    return flat


def run_validation(results: dict[str, pd.DataFrame]) -> dict[str, list[str]]:
    """Run plausibility checks on all scenario outputs.

    Args:
        results: Dict mapping scenario_id → output DataFrame.

    Returns:
        Dict mapping scenario_id → list of violation messages.
    """
    from src.validation.plausibility import run_all_checks

    all_violations: dict[str, list[str]] = {}
    for scenario_id, df in results.items():
        if df.empty:
            continue
        violations = run_all_checks(df)
        flat = [msg for msgs in violations.values() for msg in msgs]
        all_violations[scenario_id] = flat
        if flat:
            logger.warning("Scenario '%s': %d plausibility violations", scenario_id, len(flat))
        else:
            logger.info("Scenario '%s': all plausibility checks passed", scenario_id)

    return all_violations


def compute_diff(
    current: pd.DataFrame,
    previous: pd.DataFrame,
    threshold: float = 0.05,
) -> pd.DataFrame:
    """Compute diff between current and previous baseline outputs.

    Args:
        current: Current run output DataFrame.
        previous: Previous baseline output DataFrame.
        threshold: Flag rows where abs delta > this fraction (default 0.05 = 5%).

    Returns:
        DataFrame of flagged rows with delta columns.
    """
    keys = ["geo", "segment", "product", "year", "scenario_id"]
    merged = current.merge(
        previous[keys + ["kwh_estimate"]].rename(columns={"kwh_estimate": "kwh_prev"}),
        on=keys,
        how="left",
    )
    merged["delta_pct"] = (merged["kwh_estimate"] - merged["kwh_prev"]) / merged["kwh_prev"].abs()
    flagged = merged[merged["delta_pct"].abs() > threshold].copy()
    logger.info(
        "Diff report: %d rows flagged with >%.0f%% delta vs previous baseline",
        len(flagged),
        threshold * 100,
    )
    return flagged


def save_outputs(
    results: dict[str, pd.DataFrame],
    run_id: str,
    run_timestamp: str,
) -> Path:
    """Save combined outputs to parquet.

    Args:
        results: Dict mapping scenario_id → output DataFrame.
        run_id: UUID for this pipeline run.
        run_timestamp: ISO timestamp string.

    Returns:
        Path to the saved output file.
    """
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    non_empty = {k: v for k, v in results.items() if not v.empty}
    if not non_empty:
        logger.warning("No outputs to save")
        return OUTPUTS_DIR

    combined = pd.concat(non_empty.values(), ignore_index=True)
    out_path = OUTPUTS_DIR / f"run_{run_timestamp}_{run_id[:8]}.parquet"
    combined.to_parquet(out_path, index=False)
    logger.info("Saved %d rows to %s", len(combined), out_path)

    # Update latest baseline
    combined.to_parquet(BASELINE_PATH, index=False)
    logger.info("Updated baseline at %s", BASELINE_PATH)

    return out_path


def log_run(
    run_id: str,
    run_timestamp: str,
    scenario_ids: list[str],
    row_counts: dict[str, int],
    violations: dict[str, list[str]],
    flagged_deltas: int,
    output_path: str,
) -> None:
    """Append run metadata to the run log JSONL file."""
    RUN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "run_id": run_id,
        "timestamp": run_timestamp,
        "scenarios": scenario_ids,
        "row_counts": row_counts,
        "total_violations": sum(len(v) for v in violations.values()),
        "flagged_deltas": flagged_deltas,
        "output_path": output_path,
    }
    with open(RUN_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    logger.info("Run logged to %s", RUN_LOG_PATH)


def main() -> int:
    """Run the full pipeline. Returns exit code (0 = success, 1 = violations)."""
    args = parse_args()
    run_id = str(uuid.uuid4())
    run_timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")

    logger.info("=" * 60)
    logger.info("ICT Electricity Demand Pipeline")
    logger.info("run_id=%s  timestamp=%s  engine=%s", run_id, run_timestamp, args.engine)
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("Dry run — validating pipeline structure only")
        from src.scenarios.registry import list_scenarios
        scenarios = list_scenarios()
        logger.info("Registered scenarios: %s", scenarios)
        logger.info("Dry run complete")
        return 0

    # Load scenario list
    from src.scenarios.registry import list_scenarios
    if args.scenario == "all":
        scenario_ids = list_scenarios()
    else:
        scenario_ids = [args.scenario]
    logger.info("Running scenarios: %s", scenario_ids)

    # Load gold tables (v2 loader also picks up legacy keys as fallback)
    if args.engine == "v2":
        gold_tables = load_gold_tables_v2()
    else:
        gold_tables = load_gold_tables()

    all_empty = all(v.empty for v in gold_tables.values())
    if all_empty:
        logger.warning("All gold tables are empty — no real data to model. Exiting.")
        logger.info("Run ingest first: uv run python scripts/ingest_germany.py")
        return 0

    # Run models
    if args.engine == "v2":
        results = run_models_v2(gold_tables, scenario_ids, run_id, args.grid_scenario)
    else:
        results = run_models(gold_tables, scenario_ids, run_id, args.mc_iterations)
    row_counts = {k: len(v) for k, v in results.items()}
    logger.info("Model outputs: %s", row_counts)

    # Validate
    violations = run_validation(results)

    # Diff vs previous baseline
    flagged_deltas = 0
    if not args.skip_diff and BASELINE_PATH.exists():
        previous = pd.read_parquet(BASELINE_PATH)
        baseline_scenario = results.get("ai_base", pd.DataFrame())
        if not baseline_scenario.empty:
            diff_df = compute_diff(baseline_scenario, previous[previous["scenario_id"] == "ai_base"])
            flagged_deltas = len(diff_df)
            if flagged_deltas > 0:
                diff_path = OUTPUTS_DIR / f"diff_{run_timestamp}_{run_id[:8]}.csv"
                diff_df.to_csv(diff_path, index=False)
                logger.warning("Diff report saved to %s — REVIEW BEFORE PUBLISHING", diff_path)

    # Save outputs
    out_path = save_outputs(results, run_id, run_timestamp)

    # Log run
    log_run(run_id, run_timestamp, scenario_ids, row_counts, violations, flagged_deltas, str(out_path))

    # Generate release notes
    from scripts.generate_release_notes import generate_release_notes
    notes_path = generate_release_notes(run_id, run_timestamp, row_counts, violations, flagged_deltas)
    logger.info("Release notes: %s", notes_path)

    total_violations = sum(len(v) for v in violations.values())
    if total_violations > 0:
        logger.error("Pipeline complete with %d plausibility violations — DO NOT PUBLISH", total_violations)
        return 1

    logger.info("Pipeline complete — %d total output rows, 0 violations", sum(row_counts.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
