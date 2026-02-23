"""Unit tests for src/models/reporting.py."""

import pytest
import pandas as pd

from src.models.reporting import (
    build_appendix_table,
    aggregate_by_application_area,
    aggregate_total_ict,
    build_full_report,
)
from src.models.schema import make_stub_output


def _make_results_df(years: list[int] | None = None) -> pd.DataFrame:
    """Build a minimal results DataFrame covering all application areas."""
    if years is None:
        years = [2015, 2025, 2035]
    rows = []
    combos = [
        ("DE", "devices",     "laptop",          "households",       "laptop_hh"),
        ("DE", "devices",     "pc_notebook_wp",  "workplace",        "pc_notebook_wp"),
        ("DE", "networks",    "5g_base_station",  "telecom_networks", "mobile_access_port"),
        ("DE", "datacentres", "cpu_unit",         "datacentres",      "cpu_unit"),
        ("DE", "devices",     "pos_terminal",     "public_spaces",    "pos_terminal"),
    ]
    for year in years:
        for geo, seg, prod, area, pg in combos:
            row = make_stub_output(geo, seg, prod, year, 1e9, 1, "ai_base", "test-run")
            row["application_area"] = area
            row["product_group"] = pg
            rows.append(row)
    df = pd.DataFrame(rows)
    df["emissions_kgco2e"] = df["kwh_estimate"] * 0.35
    return df


# ── build_appendix_table ──────────────────────────────────────────────────────

def test_build_appendix_table_returns_dataframe():
    df = _make_results_df()
    result = build_appendix_table(df)
    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0


def test_build_appendix_table_has_required_columns():
    df = _make_results_df()
    result = build_appendix_table(df)
    assert "application_area" in result.columns
    assert "product_group" in result.columns
    assert "metric" in result.columns
    assert "2015" in result.columns
    assert "2025" in result.columns
    assert "2035" in result.columns


def test_build_appendix_table_metrics_present():
    df = _make_results_df()
    result = build_appendix_table(df)
    metrics = set(result["metric"].unique())
    assert "kwh_twh" in metrics
    assert "emissions_mtco2e" in metrics


def test_build_appendix_table_kwh_twh_correct_units():
    """1e9 kWh = 1 TWh."""
    df = _make_results_df()
    result = build_appendix_table(df)
    kwh_rows = result[result["metric"] == "kwh_twh"]
    vals = kwh_rows["2025"].dropna()
    assert len(vals) > 0
    assert ((vals - 1.0).abs() < 1e-3).all()


def test_build_appendix_table_all_areas_present():
    df = _make_results_df()
    result = build_appendix_table(df)
    areas = set(result["application_area"].unique())
    expected = {"households", "workplace", "telecom_networks", "datacentres", "public_spaces"}
    assert expected.issubset(areas)


def test_build_appendix_table_no_data_returns_empty():
    df = _make_results_df(years=[2020])  # no reference years
    result = build_appendix_table(df, reference_years=[2015, 2025, 2035])
    assert result.empty


def test_build_appendix_table_custom_reference_years():
    df = _make_results_df(years=[2020, 2030])
    result = build_appendix_table(df, reference_years=[2020, 2030])
    assert "2020" in result.columns
    assert "2030" in result.columns
    assert "2025" not in result.columns


def test_build_appendix_table_sorted_by_area_and_product():
    df = _make_results_df()
    result = build_appendix_table(df)
    areas = result["application_area"].tolist()
    # Should be sorted
    assert areas == sorted(areas)


# ── aggregate_by_application_area ────────────────────────────────────────────

def test_aggregate_by_application_area_returns_dataframe():
    df = _make_results_df()
    result = aggregate_by_application_area(df)
    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0


def test_aggregate_by_application_area_has_required_columns():
    df = _make_results_df()
    result = aggregate_by_application_area(df)
    assert "application_area" in result.columns
    assert "year" in result.columns
    assert "kwh_twh" in result.columns
    assert "kwh_p10_twh" in result.columns
    assert "kwh_p90_twh" in result.columns


def test_aggregate_by_application_area_all_areas_present():
    df = _make_results_df()
    result = aggregate_by_application_area(df)
    areas = set(result["application_area"].unique())
    expected = {"households", "workplace", "telecom_networks", "datacentres", "public_spaces"}
    assert expected.issubset(areas)


def test_aggregate_by_application_area_kwh_positive():
    df = _make_results_df()
    result = aggregate_by_application_area(df)
    assert (result["kwh_twh"] > 0).all()


def test_aggregate_by_application_area_p10_le_p90():
    df = _make_results_df()
    result = aggregate_by_application_area(df)
    assert (result["kwh_p10_twh"] <= result["kwh_p90_twh"]).all()


def test_aggregate_by_application_area_emissions_present():
    df = _make_results_df()
    result = aggregate_by_application_area(df)
    assert "emissions_mtco2e" in result.columns
    assert (result["emissions_mtco2e"] > 0).all()


# ── aggregate_total_ict ───────────────────────────────────────────────────────

def test_aggregate_total_ict_returns_dataframe():
    df = _make_results_df()
    result = aggregate_total_ict(df)
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3  # 3 reference years


def test_aggregate_total_ict_has_required_columns():
    df = _make_results_df()
    result = aggregate_total_ict(df)
    assert "year" in result.columns
    assert "kwh_twh" in result.columns


def test_aggregate_total_ict_equals_sum_of_areas():
    df = _make_results_df()
    by_area = aggregate_by_application_area(df)
    total = aggregate_total_ict(df)
    for yr in [2015, 2025, 2035]:
        area_sum = by_area[by_area["year"] == yr]["kwh_twh"].sum()
        total_val = total[total["year"] == yr]["kwh_twh"].iloc[0]
        assert total_val == pytest.approx(area_sum, rel=1e-6)


def test_aggregate_total_ict_sorted_by_year():
    df = _make_results_df()
    result = aggregate_total_ict(df)
    assert list(result["year"]) == sorted(result["year"].tolist())


# ── build_full_report ─────────────────────────────────────────────────────────

def test_build_full_report_returns_dict():
    df = _make_results_df()
    report = build_full_report(df)
    assert isinstance(report, dict)


def test_build_full_report_has_all_keys():
    df = _make_results_df()
    report = build_full_report(df)
    assert "appendix_table" in report
    assert "by_application_area" in report
    assert "total_ict" in report


def test_build_full_report_all_values_are_dataframes():
    df = _make_results_df()
    report = build_full_report(df)
    for key, val in report.items():
        assert isinstance(val, pd.DataFrame), f"report['{key}'] is not a DataFrame"


def test_build_full_report_non_empty():
    df = _make_results_df()
    report = build_full_report(df)
    for key, val in report.items():
        assert len(val) > 0, f"report['{key}'] is empty"
