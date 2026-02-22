"""ScenarioEngine abstract base class.

All engine implementations (synthetic, pipeline) must implement this interface.
Swapping engines = one dependency injection change in the API routes.
"""

from abc import ABC, abstractmethod
from typing import Any

from backend.models import RunResult, ScenarioParams


class ScenarioEngine(ABC):
    """Abstract scenario engine — stable run interface across all implementations."""

    @abstractmethod
    def run(self, params: ScenarioParams) -> RunResult:
        """Execute a scenario run and return structured results.

        Args:
            params: Scenario parameters including overrides, geos, and year range.

        Returns:
            RunResult containing output rows, metadata, and model card.
        """
        ...

    @abstractmethod
    def list_scenarios(self) -> list[dict[str, Any]]:
        """Return available scenario definitions from the registry.

        Returns:
            List of scenario metadata dicts (id, label, family, description, color).
        """
        ...

    @abstractmethod
    def get_scenario(self, scenario_id: str) -> dict[str, Any] | None:
        """Return a single scenario definition with assumption ranges.

        Args:
            scenario_id: Scenario identifier string.

        Returns:
            Scenario metadata dict, or None if not found.
        """
        ...
