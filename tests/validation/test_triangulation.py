"""Tests for src/validation/triangulation.py."""

import pytest
import pandas as pd

from src.models.schema import make_stub_output
from src.validation.triangulation import (
    check_germany_calibration,
    check_crosscheck_agreement,
    build_validation_report,
)


def _make_germany_df(kwh_total: float, year: int = 2024) -> pd.DataFrame:
    return pd.DataFrame([
        make_stub_output("DE", "datacentres", "hyperscale", year, kwh_total * 0.4, 1, "ai_base", "test"),
        make_stub_output("DE", "devices", "laptop", year, kwh_total * 0.35, 1, "ai_base", "test"),
        make_stub_output("DE", "networks", "5g_base_station", year, kwh_total * 0.25, 1, "ai_base", "test"),
    ])


def test_germany_calibration_passes_within_tolerance():
    # Model = 62 TWh, benchmark = 60 TWh → deviation ~3.3% < 15%
    df = _make_germany_df(kwh_total=62e9)
    result = check_germany_calibration(df, benchmark_twh=60.0, year=2024)
    assert result["passed"] == True


def test_germany_calibration_fails_outside_tolerance():
    # Model = 80 TWh, benchmark = 60 TWh → deviation ~33% > 15%
    df = _make_germany_df(kwh_total=80e9)
    result = check_germany_calibration(df, benchmark_twh=60.0, year=2024)
    assert result["passed"] == False


def test_germany_calibration_no_data_returns_fail():
    df = _make_germany_df(kwh_total=60e9, year=2023)
    result = check_germany_calibration(df, benchmark_twh=60.0, year=2024)
    assert result["passed"] == False


def test_crosscheck_passes_within_tolerance():
    result = check_crosscheck_agreement(
        primary_kwh=60e9, alternative_kwh=65e9, geo="DE", year=2024
    )
    assert result["passed"] == True  # ~7.7% deviation < 20%


def test_crosscheck_fails_outside_tolerance():
    result = check_crosscheck_agreement(
        primary_kwh=60e9, alternative_kwh=90e9, geo="DE", year=2024
    )
    assert result["passed"] == False  # ~33% deviation > 20%


def test_build_validation_report_structure():
    cal = [check_germany_calibration(_make_germany_df(60e9), 60.0, 2024)]
    cc = [check_crosscheck_agreement(60e9, 62e9, "DE", 2024)]
    report = build_validation_report(cal, cc)
    assert "check_type" in report.columns
    assert "passed" in report.columns
    assert len(report) == 2
