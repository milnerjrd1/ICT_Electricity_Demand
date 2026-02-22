"""Synthetic scenario engine — Phase 0 implementation of ScenarioEngine.

Uses shaped trajectory generator from backend/synthetic.py.
Swapped for PipelineEngine in Phase 1+ via dependency injection.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

import yaml

from backend.engine.base import ScenarioEngine
from backend.models import (
    DemandSummary,
    ModelCard,
    OutputRow,
    RunResult,
    RunStatus,
    ScenarioParams,
)
from backend.synthetic import assumptions_hash, generate

logger = logging.getLogger(__name__)

_CONFIGS_DIR = Path(__file__).parent.parent.parent / "configs"
_REGISTRY_PATH = _CONFIGS_DIR / "scenarios" / "registry.yaml"
_ASSUMPTIONS_DIR = _CONFIGS_DIR / "assumptions"

MODEL_VERSION = "0.1.0"
DATA_VINTAGE = "2026-02"


class SyntheticEngine(ScenarioEngine):
    """Phase 0 engine — generates shaped synthetic trajectories."""

    def __init__(self) -> None:
        self._registry = self._load_registry()

    def _load_registry(self) -> list[dict[str, Any]]:
        """Load scenario registry from YAML."""
        with open(_REGISTRY_PATH) as f:
            data = yaml.safe_load(f)
        return data.get("scenarios", [])

    def run(self, params: ScenarioParams) -> RunResult:
        """Run synthetic scenario and return structured results.

        Args:
            params: Scenario parameters with overrides.

        Returns:
            RunResult with output rows, summary, and model card.
        """
        run_id = str(uuid.uuid4())
        logger.info("SyntheticEngine.run: scenario=%s run_id=%s", params.scenario_id, run_id)

        df = generate(
            scenario_id=params.scenario_id,
            geos=params.geos,
            years=params.years,
            segments=params.segments,
            seed=params.seed,
            run_id=run_id,
        )

        rows = [
            OutputRow(
                geo=str(r["geo"]),
                segment=str(r["segment"]),
                product=str(r["product"]),
                year=int(r["year"]),
                kwh_estimate=float(r["kwh_estimate"]),
                kwh_p10=float(r["kwh_p10"]),
                kwh_p50=float(r["kwh_p50"]),
                kwh_p90=float(r["kwh_p90"]),
                confidence_tier=int(r["confidence_tier"]),
                uncertainty_band=float(r["uncertainty_band"]),
                scenario_id=str(r["scenario_id"]),
                run_id=str(r["run_id"]),
                source_ids=list(r["source_ids"]),
                emissions_kgco2e=float(r["emissions_kgco2e"]) if r.get("emissions_kgco2e") is not None else None,
                cost_usd=float(r["cost_usd"]) if r.get("cost_usd") is not None else None,
            )
            for _, r in df.iterrows()
        ]

        params_dict = params.model_dump()
        model_card = ModelCard(
            model_version=MODEL_VERSION,
            data_vintage=DATA_VINTAGE,
            engine="synthetic",
            scenario_id=params.scenario_id,
            assumptions_hash=assumptions_hash(params_dict),
            seed=params.seed,
            test_status="not_run",
            inputs_summary={
                "n_geos": df["geo"].nunique(),
                "n_years": df["year"].nunique(),
                "n_rows": len(df),
            },
        )

        summary = self._build_summary(df, params.scenario_id)

        return RunResult(
            run_id=run_id,
            status=RunStatus.done,
            model_card=model_card,
            rows=rows,
            summary=summary,
        )

    def _build_summary(self, df: Any, scenario_id: str) -> dict[str, Any]:
        """Build KPI summary dict from output DataFrame."""
        import pandas as pd

        latest_year = int(df["year"].max())
        latest = df[df["year"] == latest_year]

        total_twh = float(latest["kwh_estimate"].sum() / 1e9)
        dc_twh = float(latest[latest["segment"] == "datacentres"]["kwh_estimate"].sum() / 1e9)
        devices_twh = float(latest[latest["segment"] == "devices"]["kwh_estimate"].sum() / 1e9)
        networks_twh = float(latest[latest["segment"] == "networks"]["kwh_estimate"].sum() / 1e9)
        dc_share = dc_twh / total_twh if total_twh > 0 else 0.0

        emissions_col = "emissions_kgco2e"
        total_emissions = float(latest[emissions_col].sum()) if emissions_col in latest.columns else 0.0
        cost_col = "cost_usd"
        total_cost = float(latest[cost_col].sum()) if cost_col in latest.columns else 0.0

        tier_dist = latest["confidence_tier"].value_counts().to_dict()

        return {
            "scenario_id": scenario_id,
            "latest_year": latest_year,
            "total_twh": round(total_twh, 1),
            "dc_twh": round(dc_twh, 1),
            "dc_share": round(dc_share, 4),
            "devices_twh": round(devices_twh, 1),
            "networks_twh": round(networks_twh, 1),
            "total_emissions_mtco2e": round(total_emissions, 2),
            "total_cost_usd_bn": round(total_cost, 2),
            "n_geos": int(df["geo"].nunique()),
            "confidence_tier_distribution": {str(k): int(v) for k, v in tier_dist.items()},
        }

    def list_scenarios(self) -> list[dict[str, Any]]:
        """Return scenario list from registry."""
        return self._registry

    def get_scenario(self, scenario_id: str) -> dict[str, Any] | None:
        """Return single scenario with assumption ranges."""
        for s in self._registry:
            if s["id"] == scenario_id:
                result = dict(s)
                scenario_yaml = _CONFIGS_DIR / "scenarios" / f"{scenario_id}.yaml"
                if scenario_yaml.exists():
                    with open(scenario_yaml) as f:
                        result["params"] = yaml.safe_load(f)
                dc_assumptions = _ASSUMPTIONS_DIR / "datacentres.yaml"
                if dc_assumptions.exists():
                    with open(dc_assumptions) as f:
                        result["assumption_ranges"] = yaml.safe_load(f)
                return result
        return None
