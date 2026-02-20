"""Scenario registry — loads and validates all named scenarios from YAML configs.

Scenarios are auto-discovered from configs/scenarios/registry.yaml.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

REGISTRY_PATH = Path("configs/scenarios/registry.yaml")
SCENARIOS_DIR = Path("configs/scenarios")


def load_registry(registry_path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Load the scenario registry YAML file.

    Args:
        registry_path: Path to registry.yaml.

    Returns:
        Dict mapping scenario_id → scenario metadata.

    Raises:
        FileNotFoundError: If registry.yaml does not exist.
    """
    if not registry_path.exists():
        raise FileNotFoundError(f"Scenario registry not found at {registry_path}")

    with open(registry_path) as f:
        registry = yaml.safe_load(f)

    logger.info("Loaded %d scenarios from registry", len(registry.get("scenarios", [])))
    return registry


def load_scenario(scenario_id: str, scenarios_dir: Path = SCENARIOS_DIR) -> dict[str, Any]:
    """Load a single scenario YAML by scenario_id.

    Args:
        scenario_id: Scenario identifier (must match a YAML filename without extension).
        scenarios_dir: Directory containing scenario YAML files.

    Returns:
        Dict of scenario parameters.

    Raises:
        FileNotFoundError: If the scenario YAML file does not exist.
    """
    scenario_path = scenarios_dir / f"{scenario_id}.yaml"
    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {scenario_path}")

    with open(scenario_path) as f:
        params = yaml.safe_load(f)

    params["scenario_id"] = scenario_id
    logger.info("Loaded scenario '%s' from %s", scenario_id, scenario_path)
    return params


def list_scenarios(registry_path: Path = REGISTRY_PATH) -> list[str]:
    """Return list of all registered scenario IDs.

    Args:
        registry_path: Path to registry.yaml.

    Returns:
        List of scenario_id strings.
    """
    registry = load_registry(registry_path)
    return [s["id"] for s in registry.get("scenarios", [])]


def load_all_scenarios(
    registry_path: Path = REGISTRY_PATH,
    scenarios_dir: Path = SCENARIOS_DIR,
) -> dict[str, dict[str, Any]]:
    """Load all registered scenarios.

    Args:
        registry_path: Path to registry.yaml.
        scenarios_dir: Directory containing scenario YAML files.

    Returns:
        Dict mapping scenario_id → scenario params dict.
    """
    scenario_ids = list_scenarios(registry_path)
    return {sid: load_scenario(sid, scenarios_dir) for sid in scenario_ids}
