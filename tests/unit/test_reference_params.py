"""Unit tests for src/models/reference_params.py."""

import pytest
from pathlib import Path

from src.models.reference_params import (
    resolve_reference_year,
    get_params,
    get_all_product_params,
    REFERENCE_YEARS,
)

PARAMS_DIR = Path("configs/assumptions/reference_params")


# ── resolve_reference_year ────────────────────────────────────────────────────

def test_resolve_exact_reference_year():
    assert resolve_reference_year(2022, PARAMS_DIR) == 2022


def test_resolve_year_between_sets():
    # 2023 should resolve to 2022 (most recent ≤ 2023)
    assert resolve_reference_year(2023, PARAMS_DIR) == 2022


def test_resolve_year_2025_to_2022():
    # 2025 should resolve to 2022 (params_2027 not yet applicable)
    result = resolve_reference_year(2025, PARAMS_DIR)
    assert result == 2022


def test_resolve_year_2027():
    assert resolve_reference_year(2027, PARAMS_DIR) == 2027


def test_resolve_year_2030_to_2027():
    assert resolve_reference_year(2030, PARAMS_DIR) == 2027


def test_resolve_year_2032():
    assert resolve_reference_year(2032, PARAMS_DIR) == 2032


def test_resolve_year_2035_to_2032():
    assert resolve_reference_year(2035, PARAMS_DIR) == 2032


def test_resolve_year_before_all_sets():
    # Year before 2007 → use earliest available
    result = resolve_reference_year(2000, PARAMS_DIR)
    assert result == 2007


def test_resolve_year_2017():
    assert resolve_reference_year(2017, PARAMS_DIR) == 2017


def test_resolve_year_2019_to_2017():
    assert resolve_reference_year(2019, PARAMS_DIR) == 2017


def test_resolve_year_2012():
    assert resolve_reference_year(2012, PARAMS_DIR) == 2012


def test_resolve_year_2015_to_2012():
    assert resolve_reference_year(2015, PARAMS_DIR) == 2012


# ── get_params ────────────────────────────────────────────────────────────────

def test_get_params_laptop_hh_2022():
    params = get_params("laptop_hh", 2022, PARAMS_DIR)
    assert isinstance(params, dict)
    assert len(params) > 0
    assert "avg_lifespan_years" in params
    assert "power_active_medium_w" in params


def test_get_params_returns_dict():
    params = get_params("tv_large", 2022, PARAMS_DIR)
    assert isinstance(params, dict)


def test_get_params_unknown_product_returns_empty():
    params = get_params("nonexistent_product_xyz", 2022, PARAMS_DIR)
    assert params == {}


def test_get_params_2022_laptop_lifespan():
    params = get_params("laptop_hh", 2022, PARAMS_DIR)
    assert params["avg_lifespan_years"] == pytest.approx(5.0)


def test_get_params_2017_laptop_higher_power_than_2022():
    """Older reference year should have higher power draw (efficiency trend)."""
    p2017 = get_params("laptop_hh", 2017, PARAMS_DIR)
    p2022 = get_params("laptop_hh", 2022, PARAMS_DIR)
    assert p2017["power_active_medium_w"] > p2022["power_active_medium_w"]


def test_get_params_2027_laptop_lower_power_than_2022():
    """Projected 2027 should have lower power draw than 2022."""
    p2022 = get_params("laptop_hh", 2022, PARAMS_DIR)
    p2027 = get_params("laptop_hh", 2027, PARAMS_DIR)
    assert p2027["power_active_medium_w"] < p2022["power_active_medium_w"]


def test_get_params_year_2023_resolves_to_2022_set():
    p2022 = get_params("laptop_hh", 2022, PARAMS_DIR)
    p2023 = get_params("laptop_hh", 2023, PARAMS_DIR)
    assert p2022 == p2023


def test_get_params_all_reference_years_have_laptop():
    for ry in REFERENCE_YEARS:
        params = get_params("laptop_hh", ry, PARAMS_DIR)
        assert len(params) > 0, f"No params for laptop_hh at reference year {ry}"


# ── get_all_product_params ────────────────────────────────────────────────────

def test_get_all_product_params_2022_returns_dict():
    all_params = get_all_product_params(2022, PARAMS_DIR)
    assert isinstance(all_params, dict)
    assert len(all_params) > 0


def test_get_all_product_params_contains_expected_products():
    all_params = get_all_product_params(2022, PARAMS_DIR)
    expected = {"laptop_hh", "desktop_hh", "smartphone_hh", "tv_large", "home_router"}
    for pg in expected:
        assert pg in all_params, f"Missing product group '{pg}' in 2022 params"


def test_get_all_product_params_values_are_dicts():
    all_params = get_all_product_params(2022, PARAMS_DIR)
    for pg, params in all_params.items():
        assert isinstance(params, dict), f"Params for '{pg}' is not a dict"
