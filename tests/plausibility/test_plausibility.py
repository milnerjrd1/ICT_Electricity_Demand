"""Plausibility tests — run on every pipeline execution. Zero violations in production."""

import pytest
import pandas as pd
import numpy as np

from src.models.schema import make_stub_output
from src.validation.plausibility import (
    check_no_negative_kwh,
    check_yoy_changes,
    check_ict_share_of_total,
    run_all_checks,
    PlausibilityViolation,
)


def _make_clean_df(run_id: str = "test-run") -> pd.DataFrame:
    rows = []
    for year in range(2020, 2026):
        rows.append(make_stub_output("DE", "datacentres", "hyperscale", year, 1e9 * (1.05 ** (year - 2020)), 1, "ai_base", run_id))
        rows.append(make_stub_output("US", "devices", "laptop", year, 5e9 * (1.01 ** (year - 2020)), 1, "ai_base", run_id))
    return pd.DataFrame(rows)


def test_no_negative_kwh_passes_clean_data():
    df = _make_clean_df()
    violations = check_no_negative_kwh(df)
    assert violations == []


def test_no_negative_kwh_catches_negative():
    df = _make_clean_df()
    df.loc[0, "kwh_estimate"] = -100.0
    violations = check_no_negative_kwh(df)
    assert len(violations) == 1
    assert "negative" in violations[0]


def test_no_negative_kwh_strict_raises():
    df = _make_clean_df()
    df.loc[0, "kwh_estimate"] = -1.0
    with pytest.raises(PlausibilityViolation):
        check_no_negative_kwh(df, strict=True)


def test_yoy_changes_passes_gradual_growth():
    df = _make_clean_df()
    violations = check_yoy_changes(df)
    assert violations == []


def test_yoy_changes_catches_large_jump():
    df = _make_clean_df()
    # Inject a 300% jump in one year
    df.loc[(df["geo"] == "DE") & (df["year"] == 2023), "kwh_estimate"] = 1e9 * 4.0
    violations = check_yoy_changes(df)
    assert len(violations) > 0


def test_ict_share_passes_reasonable_share():
    df = _make_clean_df()
    total_elec = pd.DataFrame({
        "geo": ["DE", "US"],
        "year": [2024, 2024],
        "total_kwh": [600e9, 4500e9],  # Germany ~600 TWh, US ~4500 TWh
    })
    df_2024 = df[df["year"] == 2024].copy()
    violations = check_ict_share_of_total(df_2024, total_elec)
    assert violations == []


def test_ict_share_catches_excessive_share():
    df = pd.DataFrame([
        make_stub_output("DE", "datacentres", "hyperscale", 2024, 200e9, 1, "ai_base", "test")
    ])
    total_elec = pd.DataFrame({
        "geo": ["DE"],
        "year": [2024],
        "total_kwh": [300e9],  # ICT = 67% — way over 25% threshold
    })
    violations = check_ict_share_of_total(df, total_elec)
    assert len(violations) == 1
    assert "FAIL" in violations[0]


def test_run_all_checks_returns_dict():
    df = _make_clean_df()
    results = run_all_checks(df)
    assert "no_negative_kwh" in results
    assert "yoy_changes" in results


def test_run_all_checks_clean_data_zero_violations():
    df = _make_clean_df()
    results = run_all_checks(df)
    total = sum(len(v) for v in results.values())
    assert total == 0
