"""Unit tests for src/models/schema.py."""

import pytest
import pandas as pd

from src.models.schema import validate_output, make_stub_output, REQUIRED_COLUMNS


def _make_valid_df(n: int = 3, run_id: str = "test-run-id") -> pd.DataFrame:
    rows = [
        make_stub_output(
            geo="DE",
            segment="datacentres",
            product="hyperscale",
            year=2024 + i,
            kwh_estimate=1e9,
            confidence_tier=1,
            scenario_id="ai_base",
            run_id=run_id,
        )
        for i in range(n)
    ]
    return pd.DataFrame(rows)


def test_validate_output_passes_valid_df() -> None:
    df = _make_valid_df()
    result = validate_output(df)
    assert len(result) == 3


def test_validate_output_raises_on_missing_columns() -> None:
    df = _make_valid_df().drop(columns=["confidence_tier"])
    with pytest.raises(ValueError, match="Missing required columns"):
        validate_output(df)


def test_validate_output_raises_on_null_confidence_tier() -> None:
    df = _make_valid_df()
    df.loc[0, "confidence_tier"] = None
    with pytest.raises(ValueError, match="confidence_tier must not be null"):
        validate_output(df)


def test_validate_output_raises_on_invalid_confidence_tier() -> None:
    df = _make_valid_df()
    df.loc[0, "confidence_tier"] = 4
    with pytest.raises(ValueError, match="confidence_tier must be 1, 2, or 3"):
        validate_output(df)


def test_validate_output_raises_on_null_run_id() -> None:
    df = _make_valid_df()
    df.loc[0, "run_id"] = ""
    with pytest.raises(ValueError, match="run_id must not be null or empty"):
        validate_output(df)


def test_validate_output_raises_on_negative_kwh() -> None:
    df = _make_valid_df()
    df.loc[0, "kwh_estimate"] = -1.0
    with pytest.raises(ValueError, match="kwh_estimate must not be negative"):
        validate_output(df)


def test_validate_output_raises_on_p10_gt_p90() -> None:
    df = _make_valid_df()
    df.loc[0, "kwh_p10"] = 2e9
    df.loc[0, "kwh_p90"] = 1e9
    with pytest.raises(ValueError, match="kwh_p10 must be <= kwh_p90"):
        validate_output(df)


def test_make_stub_output_default_bands() -> None:
    row = make_stub_output(
        geo="US",
        segment="devices",
        product="laptop",
        year=2025,
        kwh_estimate=5e8,
        confidence_tier=2,
        scenario_id="ai_base",
        run_id="test-run",
    )
    assert row["kwh_p10"] == pytest.approx(5e8 * 0.8)
    assert row["kwh_p90"] == pytest.approx(5e8 * 1.2)
    assert row["confidence_tier"] == 2


def test_required_columns_complete() -> None:
    df = _make_valid_df()
    for col in REQUIRED_COLUMNS:
        assert col in df.columns, f"Missing required column: {col}"
