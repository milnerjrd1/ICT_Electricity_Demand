"""Germany calibration anchor test — Phase 1.

Validates that the data centre model output for Germany is within ±15%
of the Borderstep 2023 benchmark (~18 TWh total DC electricity).

Sources:
  - Hintemann et al. (2023), Rechenzentren in Deutschland, Borderstep Institut
  - EU Code of Conduct for Data Centres 2023
  - Uptime Institute Global Survey 2023

This test uses the calibrated germany_dc_gold fixture from conftest.py,
which mirrors the values in configs/assumptions/germany_dc_anchor.yaml
and src/data/loader_eurostat._DE_DC_ANCHOR.
"""

import pytest
import pandas as pd

from src.data.loader_eurostat import (
    BORDERSTEP_2023_TOTAL_TWH,
    BORDERSTEP_2023_YEAR,
    load_germany_dc_anchor,
)
from src.models.datacentres import run_datacentres_model


# ── Constants ────────────────────────────────────────────────────────────────

CALIBRATION_YEAR = 2022
TOLERANCE_PCT = 15.0
BENCHMARK_TWH = BORDERSTEP_2023_TOTAL_TWH

# Deterministic scenario: no PUE improvement, no utilisation change.
# This isolates the capacity × PUE × utilisation formula from scenario effects.
_DETERMINISTIC_PARAMS: dict = {
    "scenario_id": "calibration_check",
    "pue_improvement_rate": 0.0,
    "utilisation_multiplier": 1.0,
    "ai_growth_rate": 0.0,
}

_RUN_ID = "test-calibration-00000000-0000-0000-0000-000000000001"


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def de_dc_anchor_df() -> pd.DataFrame:
    """Germany DC gold table from loader_eurostat (includes calibration year)."""
    return load_germany_dc_anchor(
        run_id=_RUN_ID,
        years=list(range(2020, 2025)),
    )


@pytest.fixture
def de_dc_model_output(de_dc_anchor_df: pd.DataFrame) -> pd.DataFrame:
    """Run the DC model over the Germany anchor fixture."""
    return run_datacentres_model(
        de_dc_anchor_df,
        _DETERMINISTIC_PARAMS,
        run_id=_RUN_ID,
        monte_carlo_iterations=0,
    )


# ── Calibration tests ─────────────────────────────────────────────────────────

def test_germany_dc_total_within_borderstep_tolerance(de_dc_model_output: pd.DataFrame) -> None:
    """Model total DE DC electricity must be within ±15% of Borderstep 18 TWh.

    This is the primary Phase 1 calibration gate. If this test fails,
    the capacity anchors in loader_eurostat._DE_DC_ANCHOR need adjustment.
    """
    year_df = de_dc_model_output[de_dc_model_output["year"] == CALIBRATION_YEAR]
    assert len(year_df) > 0, f"No model output for calibration year {CALIBRATION_YEAR}"

    total_twh = year_df["kwh_p50"].sum() / 1e9
    deviation_pct = abs(total_twh - BENCHMARK_TWH) / BENCHMARK_TWH * 100

    assert deviation_pct <= TOLERANCE_PCT, (
        f"Germany DC calibration FAILED: model={total_twh:.2f} TWh, "
        f"benchmark={BENCHMARK_TWH} TWh, deviation={deviation_pct:.1f}% "
        f"(tolerance ±{TOLERANCE_PCT}%)"
    )


def test_germany_dc_hyperscale_plausible(de_dc_model_output: pd.DataFrame) -> None:
    """Hyperscale segment should be 4–7 TWh for DE in calibration year.

    Borderstep 2023: hyperscale ~30% of total → ~5.4 TWh.
    Allow wider range (4–7 TWh) to accommodate uncertainty.
    """
    hs = de_dc_model_output[
        (de_dc_model_output["year"] == CALIBRATION_YEAR) &
        (de_dc_model_output["product"] == "hyperscale")
    ]
    assert len(hs) == 1
    twh = hs["kwh_p50"].iloc[0] / 1e9
    assert 4.0 <= twh <= 7.0, f"Hyperscale DE {CALIBRATION_YEAR}: {twh:.2f} TWh outside [4, 7]"


def test_germany_dc_colocation_plausible(de_dc_model_output: pd.DataFrame) -> None:
    """Colocation segment should be 5–10 TWh for DE in calibration year.

    Borderstep 2023: colocation ~38% of total → ~6.8 TWh.
    """
    colo = de_dc_model_output[
        (de_dc_model_output["year"] == CALIBRATION_YEAR) &
        (de_dc_model_output["product"] == "colocation")
    ]
    assert len(colo) == 1
    twh = colo["kwh_p50"].iloc[0] / 1e9
    assert 5.0 <= twh <= 10.0, f"Colocation DE {CALIBRATION_YEAR}: {twh:.2f} TWh outside [5, 10]"


def test_germany_dc_on_premises_plausible(de_dc_model_output: pd.DataFrame) -> None:
    """On-premises segment should be 4–10 TWh for DE in calibration year.

    Borderstep 2023: on-prem ~32% of total → ~5.8 TWh.
    Wider range due to higher uncertainty in enterprise server room data.
    """
    onprem = de_dc_model_output[
        (de_dc_model_output["year"] == CALIBRATION_YEAR) &
        (de_dc_model_output["product"] == "on_premises")
    ]
    assert len(onprem) == 1
    twh = onprem["kwh_p50"].iloc[0] / 1e9
    assert 4.0 <= twh <= 10.0, f"On-premises DE {CALIBRATION_YEAR}: {twh:.2f} TWh outside [4, 10]"


def test_germany_dc_confidence_tier_all_one(de_dc_model_output: pd.DataFrame) -> None:
    """All DE DC rows from the anchor fixture must be confidence tier 1.

    Tier 1 requires: official/survey data, >80% coverage, 3+ sources within 15%.
    The Borderstep anchor meets this bar for Germany.
    """
    assert (de_dc_model_output["confidence_tier"] == 1).all(), (
        "Expected all DE DC anchor rows to be confidence_tier=1"
    )


def test_germany_dc_source_ids_propagated(de_dc_model_output: pd.DataFrame) -> None:
    """source_ids must be non-empty on all DE DC rows."""
    assert de_dc_model_output["source_ids"].apply(lambda x: len(x) > 0).all(), (
        "source_ids must not be empty on any DE DC row"
    )


def test_germany_dc_p10_p50_p90_ordering(de_dc_model_output: pd.DataFrame) -> None:
    """P10 ≤ P50 ≤ P90 must hold for all rows."""
    assert (de_dc_model_output["kwh_p10"] <= de_dc_model_output["kwh_p50"]).all()
    assert (de_dc_model_output["kwh_p50"] <= de_dc_model_output["kwh_p90"]).all()


# ── Loader unit tests ─────────────────────────────────────────────────────────

def test_load_germany_dc_anchor_returns_expected_shape() -> None:
    """Loader should return 3 DC types × 5 years = 15 rows by default."""
    df = load_germany_dc_anchor(run_id=_RUN_ID)
    assert len(df) == 15, f"Expected 15 rows (3 types × 5 years), got {len(df)}"
    assert set(df["product"].unique()) == {"hyperscale", "colocation", "on_premises"}
    assert set(df["geo"].unique()) == {"DE"}


def test_load_germany_dc_anchor_custom_years() -> None:
    """Loader should respect custom years argument."""
    df = load_germany_dc_anchor(run_id=_RUN_ID, years=[2022, 2023])
    assert len(df) == 6  # 3 types × 2 years
    assert set(df["year"].unique()) == {2022, 2023}


def test_load_germany_dc_anchor_has_lineage_columns() -> None:
    """Loader output must include gold table lineage columns."""
    df = load_germany_dc_anchor(run_id=_RUN_ID)
    for col in ("source_id", "ingestion_date", "version", "run_id"):
        assert col in df.columns, f"Missing lineage column: {col}"
    assert (df["run_id"] == _RUN_ID).all()
    assert (df["source_id"] == "borderstep_2023").all()


def test_load_germany_dc_anchor_modelled_twh_matches_expected() -> None:
    """Verify the anchor fixture produces ~18.59 TWh when run through the model.

    This is a regression guard: if _DE_DC_ANCHOR values change, this test
    will catch the drift before it silently breaks the calibration gate.
    """
    df = load_germany_dc_anchor(run_id=_RUN_ID, years=[CALIBRATION_YEAR])
    result = run_datacentres_model(df, _DETERMINISTIC_PARAMS, run_id=_RUN_ID)
    total_twh = result["kwh_p50"].sum() / 1e9

    # Expected: 4.91 + 6.98 + 6.70 = 18.59 TWh
    expected_twh = 18.59
    assert abs(total_twh - expected_twh) / expected_twh < 0.01, (
        f"Anchor fixture regression: expected ~{expected_twh} TWh, got {total_twh:.3f} TWh"
    )


# ── Cross-check tests ─────────────────────────────────────────────────────────

def test_germany_dc_crosscheck_bnetza(de_dc_model_output: pd.DataFrame) -> None:
    """Cross-check: model output within ±20% of BNetzA sector estimate (16.5 TWh).

    BNetzA Monitoring 2023 reports ~16.5 TWh for ICT services electricity.
    This is a lower bound (includes some non-DC ICT), so we allow ±20%.
    """
    year_df = de_dc_model_output[de_dc_model_output["year"] == CALIBRATION_YEAR]
    total_twh = year_df["kwh_p50"].sum() / 1e9
    bnetza_twh = 16.5
    deviation_pct = abs(total_twh - bnetza_twh) / bnetza_twh * 100
    assert deviation_pct <= 20.0, (
        f"BNetzA cross-check FAILED: model={total_twh:.2f} TWh, "
        f"BNetzA={bnetza_twh} TWh, deviation={deviation_pct:.1f}% (tolerance ±20%)"
    )


def test_germany_dc_crosscheck_iea(de_dc_model_output: pd.DataFrame) -> None:
    """Cross-check: model output within ±20% of IEA proxy estimate (19.2 TWh).

    IEA Data Centres 2024 uses a top-down GDP-adjusted proxy for Germany.
    """
    year_df = de_dc_model_output[de_dc_model_output["year"] == CALIBRATION_YEAR]
    total_twh = year_df["kwh_p50"].sum() / 1e9
    iea_twh = 19.2
    deviation_pct = abs(total_twh - iea_twh) / iea_twh * 100
    assert deviation_pct <= 20.0, (
        f"IEA cross-check FAILED: model={total_twh:.2f} TWh, "
        f"IEA={iea_twh} TWh, deviation={deviation_pct:.1f}% (tolerance ±20%)"
    )
