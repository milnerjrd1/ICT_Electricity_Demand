"""Integration tests for the Germany Phase 1 ingest and calibration path.

Tests:
  1. load_germany_dc_anchor() returns correct schema and row count
  2. run_datacentres_model() with anchor data produces DE DC output within
     ±15% of the Borderstep 2023 benchmark (18 TWh for 2022)
  3. validate_germany.py fixture mode passes the primary calibration check
  4. ingest_germany.py dry-run executes without error
"""

import uuid
from pathlib import Path

import pandas as pd
import pytest

BORDERSTEP_TWH = 18.0
BORDERSTEP_TOLERANCE = 0.15
CALIBRATION_YEAR = 2022

# Required columns in the DC anchor gold table
_ANCHOR_REQUIRED_COLS = {
    "geo", "year", "product",
    "installed_capacity_mw", "utilisation_rate", "pue", "ai_share",
    "confidence_tier", "source_ids", "run_id",
}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def run_id() -> str:
    """Deterministic run_id for integration tests."""
    return "integ-run-00000000-0000-0000-0000-000000000001"


@pytest.fixture
def anchor_df(run_id: str) -> pd.DataFrame:
    """Germany DC anchor DataFrame for calibration year only."""
    from src.data.loader_eurostat import load_germany_dc_anchor
    return load_germany_dc_anchor(run_id=run_id, years=[CALIBRATION_YEAR])


@pytest.fixture
def anchor_df_multi_year(run_id: str) -> pd.DataFrame:
    """Germany DC anchor DataFrame for 2020-2024."""
    from src.data.loader_eurostat import load_germany_dc_anchor
    return load_germany_dc_anchor(run_id=run_id, years=list(range(2020, 2025)))


# ── Schema tests ──────────────────────────────────────────────────────────────

def test_anchor_schema(anchor_df: pd.DataFrame) -> None:
    """load_germany_dc_anchor() returns all required columns."""
    missing = _ANCHOR_REQUIRED_COLS - set(anchor_df.columns)
    assert not missing, f"Missing columns in anchor DataFrame: {missing}"


def test_anchor_row_count(anchor_df: pd.DataFrame) -> None:
    """Anchor for a single year has exactly 3 rows (hyperscale, colo, on-prem)."""
    assert len(anchor_df) == 3, f"Expected 3 rows, got {len(anchor_df)}"


def test_anchor_geo(anchor_df: pd.DataFrame) -> None:
    """All anchor rows are for Germany (DE)."""
    assert (anchor_df["geo"] == "DE").all(), "Expected all rows to have geo='DE'"


def test_anchor_products(anchor_df: pd.DataFrame) -> None:
    """Anchor contains hyperscale, colocation, and on_premises products."""
    products = set(anchor_df["product"].tolist())
    assert products == {"hyperscale", "colocation", "on_premises"}, (
        f"Unexpected products: {products}"
    )


def test_anchor_confidence_tier(anchor_df: pd.DataFrame) -> None:
    """All anchor rows have confidence_tier = 1 (Borderstep primary source)."""
    assert (anchor_df["confidence_tier"] == 1).all(), (
        "Expected all anchor rows to have confidence_tier=1"
    )


def test_anchor_multi_year_row_count(anchor_df_multi_year: pd.DataFrame) -> None:
    """Anchor for 5 years has exactly 15 rows (3 products × 5 years)."""
    assert len(anchor_df_multi_year) == 15, (
        f"Expected 15 rows for 5 years × 3 products, got {len(anchor_df_multi_year)}"
    )


def test_anchor_positive_capacity(anchor_df: pd.DataFrame) -> None:
    """All capacity and utilisation values are positive."""
    assert (anchor_df["installed_capacity_mw"] > 0).all()
    assert (anchor_df["utilisation_rate"] > 0).all()
    assert (anchor_df["pue"] >= 1.0).all()


# ── Calibration tests ─────────────────────────────────────────────────────────

def test_de_dc_2022_within_borderstep_tolerance(anchor_df: pd.DataFrame, run_id: str) -> None:
    """run_datacentres_model() with anchor data produces DE DC output within ±15% of 18 TWh.

    This is the primary Phase 1 calibration gate. The model must output
    between 15.3 TWh and 20.7 TWh for Germany data centres in 2022.
    """
    from src.models.datacentres import run_datacentres_model

    scenario_params = {
        "scenario_id": "ai_base",
        "pue_improvement_rate": 0.0,   # deterministic — no improvement applied
        "utilisation_multiplier": 1.0,
        "ai_growth_rate": 0.0,
    }

    result_df = run_datacentres_model(anchor_df, scenario_params, run_id=run_id)

    assert not result_df.empty, "run_datacentres_model() returned empty DataFrame"

    de_mask = (result_df["geo"] == "DE") & (result_df["year"] == CALIBRATION_YEAR)
    de_rows = result_df[de_mask]
    assert not de_rows.empty, (
        f"No DE rows for year={CALIBRATION_YEAR} in model output. "
        f"Available: geos={result_df['geo'].unique()}, years={result_df['year'].unique()}"
    )

    total_kwh = de_rows["kwh_estimate"].sum()
    total_twh = total_kwh / 1e9

    lower = BORDERSTEP_TWH * (1 - BORDERSTEP_TOLERANCE)
    upper = BORDERSTEP_TWH * (1 + BORDERSTEP_TOLERANCE)

    assert lower <= total_twh <= upper, (
        f"DE DC 2022 = {total_twh:.2f} TWh — outside Borderstep ±{BORDERSTEP_TOLERANCE:.0%} "
        f"tolerance [{lower:.1f}, {upper:.1f}] TWh. "
        f"Deviation: {(total_twh - BORDERSTEP_TWH) / BORDERSTEP_TWH:+.1%}"
    )


def test_de_dc_2022_output_schema(anchor_df: pd.DataFrame, run_id: str) -> None:
    """run_datacentres_model() output conforms to OutputSchema required columns."""
    from src.models.datacentres import run_datacentres_model
    from src.models.schema import REQUIRED_COLUMNS

    scenario_params = {
        "scenario_id": "ai_base",
        "pue_improvement_rate": 0.0,
        "utilisation_multiplier": 1.0,
        "ai_growth_rate": 0.0,
    }

    result_df = run_datacentres_model(anchor_df, scenario_params, run_id=run_id)
    missing = set(REQUIRED_COLUMNS) - set(result_df.columns)
    assert not missing, f"Output missing required schema columns: {missing}"


def test_de_dc_no_negative_kwh(anchor_df: pd.DataFrame, run_id: str) -> None:
    """No negative kWh estimates in DE DC output."""
    from src.models.datacentres import run_datacentres_model

    scenario_params = {
        "scenario_id": "ai_base",
        "pue_improvement_rate": 0.0,
        "utilisation_multiplier": 1.0,
        "ai_growth_rate": 0.0,
    }

    result_df = run_datacentres_model(anchor_df, scenario_params, run_id=run_id)
    assert (result_df["kwh_estimate"] >= 0).all(), "Negative kwh_estimate values found"


def test_de_dc_confidence_tier_preserved(anchor_df: pd.DataFrame, run_id: str) -> None:
    """Confidence tier 1 from anchor is preserved in model output."""
    from src.models.datacentres import run_datacentres_model

    scenario_params = {
        "scenario_id": "ai_base",
        "pue_improvement_rate": 0.0,
        "utilisation_multiplier": 1.0,
        "ai_growth_rate": 0.0,
    }

    result_df = run_datacentres_model(anchor_df, scenario_params, run_id=run_id)
    assert (result_df["confidence_tier"] == 1).all(), (
        "Expected all output rows to have confidence_tier=1 (from Borderstep anchor)"
    )


# ── validate_germany.py fixture mode ─────────────────────────────────────────

def test_validate_germany_fixture_passes() -> None:
    """validate_germany.py fixture mode passes the primary Borderstep check."""
    from scripts.validate_germany import extract_model_twh_from_fixture, run_checks

    model_twh = extract_model_twh_from_fixture()
    results = run_checks(model_twh)

    primary = results[0]
    assert primary.passed, (
        f"Primary calibration check failed: model={model_twh:.2f} TWh, "
        f"target={primary.target_twh:.1f} TWh, deviation={primary.deviation:+.1%}, "
        f"tolerance=±{primary.tolerance:.0%}"
    )


def test_validate_germany_model_twh_in_range() -> None:
    """Fixture model TWh is between 15 and 22 TWh (sanity bounds)."""
    from scripts.validate_germany import extract_model_twh_from_fixture

    model_twh = extract_model_twh_from_fixture()
    assert 15.0 <= model_twh <= 22.0, (
        f"Model TWh {model_twh:.2f} is outside sanity bounds [15, 22] TWh"
    )


# ── ingest_germany.py dry-run ─────────────────────────────────────────────────

def test_ingest_germany_dry_run(capsys: pytest.CaptureFixture) -> None:
    """ingest_germany.py dry-run executes without error and prints expected tables."""
    import sys

    # Simulate --dry-run by calling main() with patched argv
    import scripts.ingest_germany as ingest_mod

    original_argv = sys.argv
    try:
        sys.argv = ["ingest_germany.py", "--dry-run", "--years", "2022"]
        exit_code = ingest_mod.main()
    finally:
        sys.argv = original_argv

    assert exit_code == 0, f"ingest_germany.py --dry-run returned exit code {exit_code}"

    captured = capsys.readouterr()
    assert "datacentres" in captured.out, "Expected 'datacentres' in dry-run output"
    assert "grid_ef" in captured.out, "Expected 'grid_ef' in dry-run output"
    assert "electricity_prices" in captured.out, "Expected 'electricity_prices' in dry-run output"
