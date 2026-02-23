"""Unit tests for src/models/uncertainty.py."""

import numpy as np
import pytest

from src.models.uncertainty import check_monte_carlo_convergence, sensitivity_tornado


def _simple_model(params: dict) -> float:
    return params["a"] * 2.0 + params["b"] * 3.0


def test_tornado_returns_correct_columns():
    base = {"a": 10.0, "b": 5.0}
    result = sensitivity_tornado(base, _simple_model)
    assert "parameter" in result.columns
    assert "swing" in result.columns
    assert len(result) == 2


def test_tornado_sorted_by_abs_swing():
    base = {"a": 10.0, "b": 5.0}
    result = sensitivity_tornado(base, _simple_model)
    swings = result["swing"].abs().tolist()
    assert swings == sorted(swings, reverse=True)


def test_tornado_b_has_larger_swing():
    """b has coefficient 3 vs a coefficient 2 — b should dominate."""
    base = {"a": 10.0, "b": 10.0}
    result = sensitivity_tornado(base, _simple_model)
    assert result.iloc[0]["parameter"] == "b"


def test_mc_convergence_passes_stable_samples():
    rng = np.random.default_rng(42)
    samples = rng.normal(loc=1000.0, scale=10.0, size=3000)
    result = check_monte_carlo_convergence(samples, tolerance=0.02)
    assert result["converged"] is True


def test_mc_convergence_fails_unstable_samples():
    """Highly skewed samples should fail convergence."""
    samples = np.array([1.0] * 100 + [1_000_000.0] * 100 + [1.0] * 100)
    result = check_monte_carlo_convergence(samples, tolerance=0.02, n_splits=3)
    assert result["converged"] is False


def test_mc_convergence_returns_expected_keys():
    samples = np.random.default_rng(0).normal(500.0, 5.0, 300)
    result = check_monte_carlo_convergence(samples)
    assert "overall_p50" in result
    assert "split_p50s" in result
    assert "max_deviation" in result
    assert "converged" in result
