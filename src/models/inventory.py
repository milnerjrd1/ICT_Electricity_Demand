"""Inventory (stock-flow) model with lifespan distribution.

Implements the sales → active stock calculation used for device-centric
application areas (households, workplace, public_spaces).

The study uses a lifespan distribution rather than a single average lifespan
so that retirements are spread across multiple years, producing smoother
inventory curves and more realistic year-on-year fluctuations.

Formula:
    retirement_weight(age) = triangular_pdf(age; min, mode, max)
    retirements(t) = Σ_age [ shipments(t - age) × retirement_weight(age) ]
    stock(t) = stock(t-1) + shipments(t) - retirements(t)
    stock(t) = max(0, stock(t))
"""

from __future__ import annotations

import logging
from typing import Sequence

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Maximum lifespan considered (years). Weights beyond this are negligible.
_MAX_LIFESPAN_YEARS = 20


def _triangular_retirement_weights(
    lifespan_mean: float,
    lifespan_std: float = 0.0,
) -> np.ndarray:
    """Compute normalised retirement weight vector for a triangular lifespan distribution.

    When lifespan_std=0 the distribution degenerates to a point mass at
    round(lifespan_mean), reproducing the legacy single-lifespan behaviour.

    Args:
        lifespan_mean: Mean lifespan in years (mode of the triangular distribution).
        lifespan_std: Standard deviation proxy; sets the half-width of the
            triangular distribution as std × √6. Set to 0 for deterministic.

    Returns:
        1-D numpy array of length _MAX_LIFESPAN_YEARS. weights[i] is the
        fraction of a cohort retired at age i+1 years. Sums to 1.0.
    """
    if lifespan_std <= 0.0:
        # Degenerate: all retirements at integer-rounded mean lifespan
        weights = np.zeros(_MAX_LIFESPAN_YEARS)
        idx = max(0, min(int(round(lifespan_mean)) - 1, _MAX_LIFESPAN_YEARS - 1))
        weights[idx] = 1.0
        return weights

    # Triangular distribution: left = mean - half_width, right = mean + half_width
    # half_width derived from std: Var(triangular) = (b-a)^2/24 → b-a = std × sqrt(24)
    half_width = lifespan_std * np.sqrt(6.0)
    left = max(0.5, lifespan_mean - half_width)
    right = lifespan_mean + half_width
    mode = lifespan_mean

    ages = np.arange(1, _MAX_LIFESPAN_YEARS + 1, dtype=float)

    # Triangular PDF evaluated at each integer age
    pdf = np.zeros_like(ages)
    for i, age in enumerate(ages):
        if age < left or age > right:
            pdf[i] = 0.0
        elif age <= mode:
            pdf[i] = 2.0 * (age - left) / ((right - left) * (mode - left))
        else:
            pdf[i] = 2.0 * (right - age) / ((right - left) * (right - mode))

    total = pdf.sum()
    if total > 0:
        pdf /= total
    else:
        # Fallback to point mass
        idx = max(0, min(int(round(lifespan_mean)) - 1, _MAX_LIFESPAN_YEARS - 1))
        pdf[idx] = 1.0

    return pdf


def compute_stock_flow(
    shipments: Sequence[float],
    lifespan_mean: float,
    lifespan_std: float = 0.0,
    initial_stock: float = 0.0,
) -> np.ndarray:
    """Compute active device stock for each year using a lifespan distribution.

    Args:
        shipments: Annual shipment (sales) counts, ordered oldest to newest.
        lifespan_mean: Mean device lifespan in years.
        lifespan_std: Lifespan standard deviation (0 = deterministic single lifespan).
        initial_stock: Starting stock before the first shipment year.

    Returns:
        1-D numpy array of active stock values, same length as shipments.
    """
    weights = _triangular_retirement_weights(lifespan_mean, lifespan_std)
    n = len(shipments)
    ships = np.asarray(shipments, dtype=float)
    stock = np.zeros(n)
    current_stock = float(initial_stock)

    for t in range(n):
        # Retirements: weighted sum of past shipments by age
        retirements = 0.0
        for age_idx, w in enumerate(weights):
            if w == 0.0:
                continue
            past_t = t - (age_idx + 1)
            if past_t >= 0:
                retirements += ships[past_t] * w
            # Shipments before the series are assumed zero (no pre-history)

        current_stock = max(0.0, current_stock + ships[t] - retirements)
        stock[t] = current_stock

    return stock


def build_stock_series(
    gold_df: pd.DataFrame,
    lifespan_mean_col: str = "avg_lifespan_years",
    lifespan_std_col: str | None = "lifespan_std_years",
    shipments_col: str = "shipments",
) -> pd.DataFrame:
    """Apply compute_stock_flow to each (geo, product_group) group in a gold DataFrame.

    Args:
        gold_df: DataFrame with columns: geo, product_group (or product), year,
            shipments, avg_lifespan_years, and optionally lifespan_std_years.
        lifespan_mean_col: Column name for mean lifespan.
        lifespan_std_col: Column name for lifespan std dev. If None or absent,
            defaults to 0 (deterministic).
        shipments_col: Column name for annual shipments.

    Returns:
        Input DataFrame with an additional 'active_stock' column.
    """
    group_col = "product_group" if "product_group" in gold_df.columns else "product"
    result_parts: list[pd.DataFrame] = []

    for (geo, product), group in gold_df.groupby(["geo", group_col]):
        group = group.sort_values("year").copy()

        lifespan_mean = float(group[lifespan_mean_col].iloc[0])
        lifespan_std = 0.0
        if lifespan_std_col and lifespan_std_col in group.columns:
            lifespan_std = float(group[lifespan_std_col].iloc[0])

        stock = compute_stock_flow(
            shipments=group[shipments_col].tolist(),
            lifespan_mean=lifespan_mean,
            lifespan_std=lifespan_std,
        )
        group["active_stock"] = stock
        result_parts.append(group)

    if not result_parts:
        out = gold_df.copy()
        out["active_stock"] = 0.0
        return out

    result = pd.concat(result_parts, ignore_index=True)
    logger.info(
        "Stock-flow computed: %d rows, %d geo×product groups",
        len(result),
        len(result.groupby(["geo", group_col])),
    )
    return result
