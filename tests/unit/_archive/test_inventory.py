"""Unit tests for src/models/inventory.py."""

import numpy as np
import pandas as pd
import pytest

from src.models.inventory import (
    _triangular_retirement_weights,
    compute_stock_flow,
    build_stock_series,
)


# ── _triangular_retirement_weights ────────────────────────────────────────────

def test_weights_sum_to_one_deterministic():
    w = _triangular_retirement_weights(5.0, lifespan_std=0.0)
    assert abs(w.sum() - 1.0) < 1e-9


def test_weights_sum_to_one_distribution():
    w = _triangular_retirement_weights(5.0, lifespan_std=1.5)
    assert abs(w.sum() - 1.0) < 1e-9


def test_deterministic_weight_at_correct_index():
    w = _triangular_retirement_weights(5.0, lifespan_std=0.0)
    # All weight at age 5 → index 4 (0-indexed)
    assert w[4] == pytest.approx(1.0)
    assert w[:4].sum() == pytest.approx(0.0)
    assert w[5:].sum() == pytest.approx(0.0)


def test_distribution_weights_spread_around_mean():
    w = _triangular_retirement_weights(5.0, lifespan_std=1.5)
    # Weight at mode (index 4) should be the largest
    assert w[4] == w.max()
    # Weights should be non-zero around the mode
    assert w[2] > 0
    assert w[6] > 0


def test_weights_non_negative():
    for std in [0.0, 0.5, 1.0, 2.0]:
        w = _triangular_retirement_weights(5.0, lifespan_std=std)
        assert (w >= 0).all()


# ── compute_stock_flow ────────────────────────────────────────────────────────

def test_stock_flow_zero_shipments():
    stock = compute_stock_flow([0.0] * 5, lifespan_mean=3.0)
    assert (stock == 0.0).all()


def test_stock_flow_grows_with_shipments():
    shipments = [100.0] * 10
    stock = compute_stock_flow(shipments, lifespan_mean=5.0)
    # Stock should grow initially
    assert stock[4] > stock[0]


def test_stock_flow_stabilises_at_steady_state():
    """With constant shipments and long enough horizon, stock should stabilise."""
    shipments = [1000.0] * 20
    stock = compute_stock_flow(shipments, lifespan_mean=5.0, lifespan_std=0.0)
    # After lifespan years, retirements = shipments → stock constant
    assert abs(stock[-1] - stock[-2]) / stock[-1] < 0.01


def test_stock_flow_non_negative():
    shipments = [1000.0, 500.0, 200.0, 100.0, 50.0]
    stock = compute_stock_flow(shipments, lifespan_mean=3.0)
    assert (stock >= 0).all()


def test_stock_flow_deterministic_vs_distribution():
    """Distribution model should produce smoother retirements than deterministic."""
    shipments = [1000.0] * 15
    stock_det = compute_stock_flow(shipments, lifespan_mean=5.0, lifespan_std=0.0)
    stock_dist = compute_stock_flow(shipments, lifespan_mean=5.0, lifespan_std=1.5)
    # Both should converge to similar steady-state
    assert abs(stock_det[-1] - stock_dist[-1]) / stock_det[-1] < 0.15


def test_stock_flow_with_initial_stock():
    shipments = [0.0] * 5
    stock = compute_stock_flow(shipments, lifespan_mean=10.0, initial_stock=500.0)
    # With no shipments and long lifespan, initial stock persists
    assert stock[0] == pytest.approx(500.0)


def test_stock_flow_length_matches_shipments():
    shipments = [100.0] * 7
    stock = compute_stock_flow(shipments, lifespan_mean=3.0)
    assert len(stock) == 7


# ── build_stock_series ────────────────────────────────────────────────────────

def _make_device_gold(n_years: int = 5) -> pd.DataFrame:
    years = list(range(2020, 2020 + n_years))
    rows = []
    for year in years:
        rows.append({
            "geo": "DE",
            "product_group": "laptop_hh",
            "year": year,
            "shipments": 1_000_000.0,
            "avg_lifespan_years": 5.0,
            "lifespan_std_years": 1.0,
        })
    return pd.DataFrame(rows)


def test_build_stock_series_adds_active_stock():
    df = _make_device_gold()
    result = build_stock_series(df)
    assert "active_stock" in result.columns


def test_build_stock_series_non_negative():
    df = _make_device_gold()
    result = build_stock_series(df)
    assert (result["active_stock"] >= 0).all()


def test_build_stock_series_multiple_products():
    rows = []
    for product in ["laptop_hh", "smartphone_hh"]:
        for year in range(2020, 2025):
            rows.append({
                "geo": "DE",
                "product_group": product,
                "year": year,
                "shipments": 500_000.0,
                "avg_lifespan_years": 4.0,
            })
    df = pd.DataFrame(rows)
    result = build_stock_series(df)
    assert len(result) == 10  # 2 products × 5 years
    assert result["active_stock"].notna().all()


def test_build_stock_series_multiple_geos():
    rows = []
    for geo in ["DE", "GB"]:
        for year in range(2020, 2023):
            rows.append({
                "geo": geo,
                "product_group": "laptop_hh",
                "year": year,
                "shipments": 1_000_000.0,
                "avg_lifespan_years": 5.0,
            })
    df = pd.DataFrame(rows)
    result = build_stock_series(df)
    assert len(result) == 6
    de_stock = result[result["geo"] == "DE"]["active_stock"].tolist()
    gb_stock = result[result["geo"] == "GB"]["active_stock"].tolist()
    assert de_stock == pytest.approx(gb_stock)


def test_build_stock_series_without_std_col():
    """Should work without lifespan_std_years column (defaults to 0)."""
    df = _make_device_gold()
    df = df.drop(columns=["lifespan_std_years"])
    result = build_stock_series(df, lifespan_std_col=None)
    assert "active_stock" in result.columns
    assert (result["active_stock"] >= 0).all()
