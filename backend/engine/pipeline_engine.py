"""Pipeline scenario engine — Phase 1+ implementation stub.

Implements the same ScenarioEngine interface as SyntheticEngine.
Will be wired to real data loaders and model modules in Phase 1.
Swap = one dependency injection change in backend/api/main.py.
"""

from __future__ import annotations

from typing import Any

from backend.engine.base import ScenarioEngine
from backend.models import RunResult, ScenarioParams


class PipelineEngine(ScenarioEngine):
    """Phase 1+ engine — real data loaders + model pipeline. Stub for now."""

    def run(self, params: ScenarioParams) -> RunResult:
        """Run real pipeline. Not yet implemented.

        Args:
            params: Scenario parameters.

        Returns:
            RunResult from real model pipeline.

        Raises:
            NotImplementedError: Until Phase 1 is complete.
        """
        raise NotImplementedError("PipelineEngine not yet implemented — use SyntheticEngine")

    def list_scenarios(self) -> list[dict[str, Any]]:
        """Return available scenarios. Not yet implemented."""
        raise NotImplementedError

    def get_scenario(self, scenario_id: str) -> dict[str, Any] | None:
        """Return single scenario. Not yet implemented."""
        raise NotImplementedError
