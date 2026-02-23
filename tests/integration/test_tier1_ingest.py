"""Integration tests for the Tier 1 hotspot ingest and calibration path.

Tests:
  1. load_tier1_dc_anchor() returns correct schema and row count for each geo
  2. Each geo's DC 2022 output is within its published benchmark tolerance
  3. validate_tier1.py fixture mode passes for all 8 geos
  4. ingest_tier1.py dry-run executes without error
  5. load_all_tier1_dc_anchors() returns correct combined row count
"""

import sys
import uuid

import pandas as pd
import pytest

from src.data.loader_tier1 import (
    TIER1_BENCHMARKS,
    TIER1_GEOS,
    load_all_tier1_dc_anchors,
    load_tier1_dc_anchor,
    load_tier1_electricity_prices,
    load_tier1_grid_ef,
)

CALIBRATION_YEAR = 2022
DEFAULT_YEARS = list(range(2018, 2025))

_REQUIRED_ANCHOR_COLS = {
    "geo", "year", "product",
    "installed_capacity_mw", "utilisation_rate", "pue", "ai_share",
    "confidence_tier", "source_ids", "run_id",
}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def run_id() -> str:
    """Deterministic run_id for Tier 1 integration tests."""
    return "t1-integ-00000000-0000-0000-0000-000000000002"


# ── Schema tests (parametrised over all 7 non-DE geos) ───────────────────────

@pytest.mark.parametrize("geo", TIER1_GEOS)
def test_anchor_schema(geo: str, run_id: str) -> None:
    """load_tier1_dc_anchor() returns all required columns for each geo."""
    df = load_tier1_dc_anchor(geo=geo, run_id=run_id, years=[CALIBRATION_YEAR])
    missing = _REQUIRED_ANCHOR_COLS - set(df.columns)
    assert not missing, f"{geo}: missing columns {missing}"


@pytest.mark.parametrize("geo", TIER1_GEOS)
def test_anchor_row_count_single_year(geo: str, run_id: str) -> None:
    """Each geo anchor for a single year has exactly 3 rows."""
    df = load_tier1_dc_anchor(geo=geo, run_id=run_id, years=[CALIBRATION_YEAR])
    assert len(df) == 3, f"{geo}: expected 3 rows, got {len(df)}"


@pytest.mark.parametrize("geo", TIER1_GEOS)
def test_anchor_geo_column(geo: str, run_id: str) -> None:
    """All rows in anchor have the correct geo value."""
    df = load_tier1_dc_anchor(geo=geo, run_id=run_id, years=[CALIBRATION_YEAR])
    assert (df["geo"] == geo).all(), f"{geo}: unexpected geo values {df['geo'].unique()}"


@pytest.mark.parametrize("geo", TIER1_GEOS)
def test_anchor_products(geo: str, run_id: str) -> None:
    """Each geo anchor contains hyperscale, colocation, and on_premises."""
    df = load_tier1_dc_anchor(geo=geo, run_id=run_id, years=[CALIBRATION_YEAR])
    products = set(df["product"].tolist())
    assert products == {"hyperscale", "colocation", "on_premises"}, (
        f"{geo}: unexpected products {products}"
    )


@pytest.mark.parametrize("geo", TIER1_GEOS)
def test_anchor_positive_values(geo: str, run_id: str) -> None:
    """All capacity, utilisation, and PUE values are positive."""
    df = load_tier1_dc_anchor(geo=geo, run_id=run_id, years=[CALIBRATION_YEAR])
    assert (df["installed_capacity_mw"] > 0).all(), f"{geo}: non-positive capacity"
    assert (df["utilisation_rate"] > 0).all(), f"{geo}: non-positive utilisation"
    assert (df["pue"] >= 1.0).all(), f"{geo}: PUE < 1.0"


@pytest.mark.parametrize("geo", TIER1_GEOS)
def test_anchor_multi_year_row_count(geo: str, run_id: str) -> None:
    """Anchor for 7 years has exactly 21 rows (3 products × 7 years)."""
    df = load_tier1_dc_anchor(geo=geo, run_id=run_id, years=DEFAULT_YEARS)
    assert len(df) == 21, f"{geo}: expected 21 rows for 7 years, got {len(df)}"


def test_load_all_tier1_combined_row_count(run_id: str) -> None:
    """load_all_tier1_dc_anchors() returns 7 geos × 3 products × 7 years = 147 rows."""
    df = load_all_tier1_dc_anchors(run_id=run_id, years=DEFAULT_YEARS)
    assert len(df) == 147, f"Expected 147 rows, got {len(df)}"
    assert set(df["geo"].unique()) == set(TIER1_GEOS)


def test_load_tier1_grid_ef_row_count(run_id: str) -> None:
    """load_tier1_grid_ef() returns 7 geos × 7 years = 49 rows."""
    df = load_tier1_grid_ef(run_id=run_id)
    assert len(df) == 49, f"Expected 49 rows, got {len(df)}"
    assert set(df["geo"].unique()) == set(TIER1_GEOS)


def test_load_tier1_electricity_prices_row_count(run_id: str) -> None:
    """load_tier1_electricity_prices() returns 7 geos × 7 years = 49 rows."""
    df = load_tier1_electricity_prices(run_id=run_id)
    assert len(df) == 49, f"Expected 49 rows, got {len(df)}"
    assert set(df["geo"].unique()) == set(TIER1_GEOS)


def test_invalid_geo_raises() -> None:
    """load_tier1_dc_anchor() raises ValueError for unknown geo."""
    with pytest.raises(ValueError, match="not in TIER1_GEOS"):
        load_tier1_dc_anchor(geo="XX", run_id="test", years=[2022])


# ── Calibration tests (parametrised over all 7 non-DE geos) ──────────────────

@pytest.mark.parametrize("geo", TIER1_GEOS)
def test_dc_2022_within_benchmark_tolerance(geo: str, run_id: str) -> None:
    """run_datacentres_model() with anchor data is within each geo's benchmark tolerance.

    This is the primary Phase 2 calibration gate for all Tier 1 geos.
    """
    from src.models.datacentres import run_datacentres_model

    if geo == "DE":
        from src.data.loader_eurostat import load_germany_dc_anchor
        dc_df = load_germany_dc_anchor(run_id=run_id, years=[CALIBRATION_YEAR])
        target_twh = 18.0
        tolerance = 0.15
    else:
        dc_df = load_tier1_dc_anchor(geo=geo, run_id=run_id, years=[CALIBRATION_YEAR])
        bm = TIER1_BENCHMARKS[geo]
        target_twh = bm["target_twh"]
        tolerance = bm["tolerance"]

    scenario_params = {
        "scenario_id": "ai_base",
        "pue_improvement_rate": 0.0,
        "utilisation_multiplier": 1.0,
        "ai_growth_rate": 0.0,
    }

    result_df = run_datacentres_model(dc_df, scenario_params, run_id=run_id)
    mask = (result_df["geo"] == geo) & (result_df["year"] == CALIBRATION_YEAR)
    total_twh = result_df[mask]["kwh_estimate"].sum() / 1e9

    lower = target_twh * (1 - tolerance)
    upper = target_twh * (1 + tolerance)

    assert lower <= total_twh <= upper, (
        f"{geo}: {total_twh:.2f} TWh outside [{lower:.1f}, {upper:.1f}] TWh "
        f"(target={target_twh} TWh ±{tolerance:.0%}, "
        f"deviation={(total_twh - target_twh) / target_twh:+.1%})"
    )


@pytest.mark.parametrize("geo", TIER1_GEOS)
def test_dc_no_negative_kwh(geo: str, run_id: str) -> None:
    """No negative kWh estimates for any Tier 1 geo."""
    from src.models.datacentres import run_datacentres_model

    if geo == "DE":
        from src.data.loader_eurostat import load_germany_dc_anchor
        dc_df = load_germany_dc_anchor(run_id=run_id, years=[CALIBRATION_YEAR])
    else:
        dc_df = load_tier1_dc_anchor(geo=geo, run_id=run_id, years=[CALIBRATION_YEAR])

    scenario_params = {
        "scenario_id": "ai_base",
        "pue_improvement_rate": 0.0,
        "utilisation_multiplier": 1.0,
        "ai_growth_rate": 0.0,
    }
    result_df = run_datacentres_model(dc_df, scenario_params, run_id=run_id)
    assert (result_df["kwh_estimate"] >= 0).all(), f"{geo}: negative kwh_estimate found"


# ── validate_tier1.py fixture mode ───────────────────────────────────────────

def test_validate_tier1_fixture_all_pass() -> None:
    """validate_tier1.py fixture mode passes all 8 Tier 1 geo checks."""
    from scripts.validate_tier1 import ALL_TIER1_GEOS, check_geo, run_fixture_check

    run_id = str(uuid.uuid4())
    failures = []
    for geo in ALL_TIER1_GEOS:
        model_twh = run_fixture_check(geo, run_id)
        result = check_geo(geo, model_twh)
        if not result.passed:
            failures.append(
                f"{geo}: {model_twh:.2f} TWh, target={result.target_twh:.1f} TWh, "
                f"dev={result.deviation:+.1%}, tol=±{result.tolerance:.0%}"
            )

    assert not failures, "Fixture calibration failures:\n" + "\n".join(failures)


def test_validate_tier1_model_twh_sanity() -> None:
    """All Tier 1 fixture TWh values are within broad sanity bounds."""
    from scripts.validate_tier1 import run_fixture_check

    sanity_bounds = {
        "DE": (10.0, 30.0),
        "US": (100.0, 350.0),
        "GB": (6.0, 25.0),
        "IE": (2.0, 12.0),
        "NL": (1.5, 10.0),
        "SG": (0.5, 5.0),
        "JP": (7.0, 30.0),
        "AE": (0.8, 8.0),
    }
    run_id = str(uuid.uuid4())
    for geo, (lo, hi) in sanity_bounds.items():
        model_twh = run_fixture_check(geo, run_id)
        assert lo <= model_twh <= hi, (
            f"{geo}: {model_twh:.2f} TWh outside sanity bounds [{lo}, {hi}]"
        )


# ── ingest_tier1.py dry-run ───────────────────────────────────────────────────

def test_ingest_tier1_dry_run(capsys: pytest.CaptureFixture) -> None:
    """ingest_tier1.py --dry-run executes without error."""
    import scripts.ingest_tier1 as ingest_mod

    original_argv = sys.argv
    try:
        sys.argv = ["ingest_tier1.py", "--dry-run", "--years", "2022", "--geos", "DE", "US", "GB"]
        exit_code = ingest_mod.main()
    finally:
        sys.argv = original_argv

    assert exit_code == 0, f"ingest_tier1.py --dry-run returned exit code {exit_code}"

    captured = capsys.readouterr()
    assert "datacentres" in captured.out
    assert "grid_ef" in captured.out
    assert "electricity_prices" in captured.out


def test_ingest_tier1_invalid_geo() -> None:
    """ingest_tier1.py returns exit code 1 for unknown geo."""
    import scripts.ingest_tier1 as ingest_mod

    original_argv = sys.argv
    try:
        sys.argv = ["ingest_tier1.py", "--dry-run", "--geos", "XX"]
        exit_code = ingest_mod.main()
    finally:
        sys.argv = original_argv

    assert exit_code == 1
