"""Config routes — expose assumption YAML files as JSON."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])

_ASSUMPTIONS_DIR = Path(__file__).parent.parent.parent.parent / "configs" / "assumptions"


@router.get("/assumptions")
def get_assumptions() -> dict:
    """Return datacentres and grid emissions assumptions as JSON.

    Returns:
        Dict with 'datacentres' and 'grid_emissions' keys.
    """
    result: dict = {}
    for name in ("datacentres", "grid_emissions", "devices", "networks"):
        path = _ASSUMPTIONS_DIR / f"{name}.yaml"
        if path.exists():
            with open(path) as f:
                result[name] = yaml.safe_load(f)
        else:
            logger.warning("Assumptions file not found: %s", path)
    return result
