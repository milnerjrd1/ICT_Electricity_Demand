"""Scenarios routes — list and retrieve scenario definitions."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.engine.base import ScenarioEngine
from backend.models import ScenarioDetail, ScenarioMeta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


def _get_engine() -> ScenarioEngine:
    from backend.api.main import get_engine
    return get_engine()


@router.get("", response_model=list[ScenarioMeta])
def list_scenarios(engine: ScenarioEngine = Depends(_get_engine)) -> list[ScenarioMeta]:
    """List all available scenarios from the registry.

    Args:
        engine: Injected scenario engine.

    Returns:
        List of scenario metadata.
    """
    raw = engine.list_scenarios()
    return [ScenarioMeta(**s) for s in raw]


@router.get("/{scenario_id}", response_model=ScenarioDetail)
def get_scenario(
    scenario_id: str,
    engine: ScenarioEngine = Depends(_get_engine),
) -> ScenarioDetail:
    """Retrieve a single scenario with assumption ranges.

    Args:
        scenario_id: Scenario identifier.
        engine: Injected scenario engine.

    Returns:
        ScenarioDetail with params and assumption ranges.
    """
    raw = engine.get_scenario(scenario_id)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    return ScenarioDetail(
        id=raw["id"],
        family=raw["family"],
        label=raw["label"],
        description=raw["description"],
        color=raw["color"],
        params=raw.get("params", {}),
        assumption_ranges=raw.get("assumption_ranges", {}),
    )
