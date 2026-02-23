"""Uncertainty quantification utilities.

Provides sensitivity analysis (tornado charts) and Monte Carlo convergence checks.
"""

import logging
from typing import Callable

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def sensitivity_tornado(
    base_params: dict[str, float],
    model_fn: Callable[[dict[str, float]], float],
    swing_fraction: float = 0.20,
) -> pd.DataFrame:
    """Compute one-at-a-time sensitivity for a model function.

    Args:
        base_params: Dict of parameter name → baseline value.
        model_fn: Callable that accepts a params dict and returns a scalar output.
        swing_fraction: Fractional swing applied to each parameter (default ±20%).

    Returns:
        DataFrame with columns: parameter, low_value, high_value, low_output,
        high_output, swing, sorted by abs(swing) descending.
    """
    base_output = model_fn(base_params)
    rows = []

    for param, base_val in base_params.items():
        low_params = {**base_params, param: base_val * (1 - swing_fraction)}
        high_params = {**base_params, param: base_val * (1 + swing_fraction)}

        low_output = model_fn(low_params)
        high_output = model_fn(high_params)

        rows.append(
            {
                "parameter": param,
                "low_value": low_params[param],
                "high_value": high_params[param],
                "low_output": low_output,
                "high_output": high_output,
                "swing": high_output - low_output,
            }
        )

    result = pd.DataFrame(rows).sort_values("swing", key=abs, ascending=False)
    logger.info("Tornado analysis complete: %d parameters evaluated", len(result))
    return result.reset_index(drop=True)


def check_monte_carlo_convergence(
    samples: np.ndarray,
    tolerance: float = 0.02,
    n_splits: int = 3,
) -> dict[str, float | bool]:
    """Check that Monte Carlo P50 converges within tolerance across independent splits.

    Args:
        samples: 1D array of Monte Carlo output samples.
        tolerance: Maximum fractional deviation of split P50s from overall P50 (default 0.02 = ±2%).
        n_splits: Number of equal splits to compare (default 3).

    Returns:
        Dict with keys: overall_p50, split_p50s, max_deviation, converged.
    """
    overall_p50 = float(np.percentile(samples, 50))
    split_size = len(samples) // n_splits
    split_p50s = [
        float(np.percentile(samples[i * split_size : (i + 1) * split_size], 50))
        for i in range(n_splits)
    ]

    deviations = [abs(p - overall_p50) / overall_p50 for p in split_p50s if overall_p50 > 0]
    max_deviation = max(deviations) if deviations else 0.0
    converged = max_deviation <= tolerance

    if not converged:
        logger.warning(
            "Monte Carlo P50 not converged: max deviation=%.3f > tolerance=%.3f",
            max_deviation,
            tolerance,
        )

    return {
        "overall_p50": overall_p50,
        "split_p50s": split_p50s,
        "max_deviation": max_deviation,
        "converged": converged,
    }
