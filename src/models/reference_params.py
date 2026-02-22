"""Reference-year parameter set loader.

The Fraunhofer Green ICT @ FMD study updates technical and usage parameters
in five-year steps (2007, 2012, 2017, 2022, 2027, 2032). Each set applies
to all years until the next reference year.

Resolution rule:
    get_params(product_group, year) → params from the largest reference_year ≤ year.
    If year < earliest reference year, the earliest set is used.

Parameter sets live in:
    configs/assumptions/reference_params/params_{year}.yaml
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

REFERENCE_PARAMS_DIR = Path("configs/assumptions/reference_params")

# Canonical reference years in ascending order
REFERENCE_YEARS: tuple[int, ...] = (2007, 2012, 2017, 2022, 2027, 2032)


@lru_cache(maxsize=16)
def _load_param_set(yaml_path: Path) -> dict[str, Any]:
    """Load and cache a single reference-year YAML file.

    Args:
        yaml_path: Absolute path to the params YAML file.

    Returns:
        Parsed YAML dict.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not yaml_path.exists():
        raise FileNotFoundError(f"Reference param set not found: {yaml_path}")
    with open(yaml_path) as f:
        data: dict[str, Any] = yaml.safe_load(f)
    logger.debug("Loaded reference params from %s", yaml_path)
    return data


def _resolve_reference_year(year: int, params_dir: Path = REFERENCE_PARAMS_DIR) -> int:
    """Find the most recent reference year whose param set exists and is ≤ year.

    Args:
        year: Calendar year to resolve.
        params_dir: Directory containing params_{year}.yaml files.

    Returns:
        The resolved reference year integer.
    """
    available: list[int] = []
    for ry in REFERENCE_YEARS:
        if (params_dir / f"params_{ry}.yaml").exists():
            available.append(ry)

    if not available:
        logger.warning("No reference param sets found in %s — using defaults", params_dir)
        return REFERENCE_YEARS[0]

    candidates = [ry for ry in available if ry <= year]
    if candidates:
        return max(candidates)
    return min(available)  # year is before all available sets → use earliest


def get_params(
    product_group: str,
    year: int,
    params_dir: Path = REFERENCE_PARAMS_DIR,
) -> dict[str, Any]:
    """Get the reference-year parameter set for a product group and calendar year.

    Resolves to the most recent reference year ≤ year. Returns an empty dict
    if the product group is not found in the resolved set (caller should apply
    its own defaults).

    Args:
        product_group: Product group identifier (e.g. 'laptop_hh').
        year: Calendar year for which parameters are needed.
        params_dir: Directory containing params_{year}.yaml files.

    Returns:
        Dict of parameters for the product group, or {} if not found.
    """
    ref_year = _resolve_reference_year(year, params_dir)
    yaml_path = params_dir / f"params_{ref_year}.yaml"

    try:
        data = _load_param_set(yaml_path)
    except FileNotFoundError:
        logger.warning("Param set for reference year %d not found — returning empty", ref_year)
        return {}

    product_groups: dict[str, Any] = data.get("product_groups", {})
    params = product_groups.get(product_group, {})

    if not params:
        logger.debug(
            "No params for product_group='%s' in reference year %d", product_group, ref_year
        )
    return dict(params)


def get_all_product_params(
    year: int,
    params_dir: Path = REFERENCE_PARAMS_DIR,
) -> dict[str, dict[str, Any]]:
    """Get all product group parameters for a given calendar year.

    Args:
        year: Calendar year.
        params_dir: Directory containing params_{year}.yaml files.

    Returns:
        Dict mapping product_group → params dict.
    """
    ref_year = _resolve_reference_year(year, params_dir)
    yaml_path = params_dir / f"params_{ref_year}.yaml"

    try:
        data = _load_param_set(yaml_path)
    except FileNotFoundError:
        return {}

    return {k: dict(v) for k, v in data.get("product_groups", {}).items()}


def resolve_reference_year(year: int, params_dir: Path = REFERENCE_PARAMS_DIR) -> int:
    """Public wrapper for _resolve_reference_year (for testing and inspection).

    Args:
        year: Calendar year to resolve.
        params_dir: Directory containing params_{year}.yaml files.

    Returns:
        The resolved reference year integer.
    """
    return _resolve_reference_year(year, params_dir)
