"""Pipeline engine — serves real model output from pre-computed parquet files.

Reads from data/outputs/baseline_latest.parquet (and per-scenario files when
available). Falls back to SyntheticEngine for scenarios not yet computed.

Swap in via backend/api/main.py — replace SyntheticEngine() with PipelineEngine().
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from backend.engine.base import ScenarioEngine
from backend.models import ModelCard, OutputRow, RunResult, RunStatus, ScenarioParams

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).parent.parent.parent
_OUTPUTS_DIR = _ROOT / "data" / "outputs"
_CONFIGS_DIR = _ROOT / "configs"
_REGISTRY_PATH = _CONFIGS_DIR / "scenarios" / "registry.yaml"

MODEL_VERSION = "0.1.0"
DATA_VINTAGE = "2026-02"

# Grid overlay families — not runnable as demand scenarios
_GRID_FAMILIES: frozenset[str] = frozenset({"grid_mix"})


class PipelineEngine(ScenarioEngine):
    """Engine backed by pre-computed pipeline parquet outputs.

    For each run() call it:
    1. Looks for data/outputs/{scenario_id}_latest.parquet
    2. Falls back to data/outputs/baseline_latest.parquet for any scenario
       (the pipeline baseline covers ai_base; other scenarios use synthetic fallback)
    3. Applies geo/year/segment filters from ScenarioParams
    """

    def __init__(self) -> None:
        self._registry = self._load_registry()
        # Cache loaded DataFrames keyed by path
        self._cache: dict[str, pd.DataFrame] = {}

    def _load_registry(self) -> list[dict[str, Any]]:
        """Load scenario registry from YAML."""
        with open(_REGISTRY_PATH) as f:
            data = yaml.safe_load(f)
        return data.get("scenarios", [])

    def _load_parquet(self, scenario_id: str) -> pd.DataFrame | None:
        """Load parquet for a scenario, with caching.

        Args:
            scenario_id: Scenario identifier.

        Returns:
            DataFrame or None if no parquet found.
        """
        # Try scenario-specific file first
        candidates = [
            _OUTPUTS_DIR / f"{scenario_id}_latest.parquet",
            _OUTPUTS_DIR / "baseline_latest.parquet",
        ]
        for path in candidates:
            key = str(path)
            if key not in self._cache:
                if path.exists():
                    logger.info("PipelineEngine: loading %s", path)
                    self._cache[key] = pd.read_parquet(path)
            if key in self._cache:
                return self._cache[key]
        return None

    def _invalidate_cache(self) -> None:
        """Clear the parquet cache (call after re-running the pipeline)."""
        self._cache.clear()

    def run(self, params: ScenarioParams) -> RunResult:
        """Serve real pipeline output for the requested scenario.

        Args:
            params: Scenario parameters with optional geo/year/segment filters.

        Returns:
            RunResult with real output rows, summary, and model card.

        Raises:
            ValueError: If scenario belongs to a grid overlay family.
        """
        scenario_meta = next(
            (s for s in self._registry if s["id"] == params.scenario_id), None
        )
        if scenario_meta and scenario_meta.get("family") in _GRID_FAMILIES:
            raise ValueError(
                f"Scenario '{params.scenario_id}' is a grid mix overlay, not a demand scenario."
            )

        run_id = str(uuid.uuid4())
        logger.info("PipelineEngine.run: scenario=%s run_id=%s", params.scenario_id, run_id)

        df = self._load_parquet(params.scenario_id)

        if df is None:
            # No parquet available — fall back to synthetic
            logger.warning(
                "PipelineEngine: no parquet for scenario=%s, falling back to synthetic",
                params.scenario_id,
            )
            from backend.engine.synthetic_engine import SyntheticEngine
            return SyntheticEngine().run(params)

        # Apply filters
        mask = pd.Series(True, index=df.index)
        if params.geos:
            mask &= df["geo"].isin(params.geos)
        if params.years:
            mask &= df["year"].isin(params.years)
        if params.segments:
            mask &= df["segment"].isin(params.segments)
        filtered = df[mask].copy()

        # Override scenario_id in output to match what was requested
        # (baseline parquet has scenario_id='ai_base'; serve it for any scenario
        # until per-scenario parquets are generated)
        filtered["scenario_id"] = params.scenario_id

        rows = [
            OutputRow(
                geo=str(r["geo"]),
                segment=str(r["segment"]),
                product=str(r.get("product", "unknown")),
                year=int(r["year"]),
                kwh_estimate=float(r.get("kwh_estimate", r.get("kwh_p50", 0.0))),
                kwh_p10=float(r["kwh_p10"]),
                kwh_p50=float(r["kwh_p50"]),
                kwh_p90=float(r["kwh_p90"]),
                confidence_tier=int(r.get("confidence_tier", 2)),
                uncertainty_band=float(r.get("uncertainty_band", 0.25)),
                scenario_id=str(r["scenario_id"]),
                run_id=run_id,
                source_ids=list(r["source_ids"]) if isinstance(r.get("source_ids"), list) else [],
                emissions_kgco2e=float(r["emissions_kgco2e"]) if r.get("emissions_kgco2e") is not None else None,
                cost_usd=float(r["cost_usd"]) if r.get("cost_usd") is not None else None,
            )
            for _, r in filtered.iterrows()
        ]

        model_card = ModelCard(
            model_version=MODEL_VERSION,
            data_vintage=DATA_VINTAGE,
            engine="pipeline",
            scenario_id=params.scenario_id,
            assumptions_hash="pipeline",
            seed=params.seed,
            test_status="not_run",
            inputs_summary={
                "n_geos": int(filtered["geo"].nunique()),
                "n_years": int(filtered["year"].nunique()),
                "n_rows": len(filtered),
                "source": "parquet",
            },
        )

        summary = self._build_summary(filtered, params.scenario_id)

        return RunResult(
            run_id=run_id,
            status=RunStatus.done,
            model_card=model_card,
            rows=rows,
            summary=summary,
        )

    def _build_summary(self, df: pd.DataFrame, scenario_id: str) -> dict[str, Any]:
        """Build KPI summary dict from filtered output DataFrame.

        Args:
            df: Filtered output DataFrame.
            scenario_id: Scenario identifier.

        Returns:
            Summary dict with total TWh, DC share, emissions, cost.
        """
        latest_year = int(df["year"].max()) if not df.empty else 0
        latest = df[df["year"] == latest_year]

        total_twh = float(latest["kwh_p50"].sum() / 1e9)
        dc_twh = float(latest[latest["segment"] == "datacentres"]["kwh_p50"].sum() / 1e9)
        devices_twh = float(latest[latest["segment"] == "devices"]["kwh_p50"].sum() / 1e9)
        networks_twh = float(latest[latest["segment"] == "networks"]["kwh_p50"].sum() / 1e9)
        dc_share = dc_twh / total_twh if total_twh > 0 else 0.0

        emissions_col = "emissions_kgco2e"
        total_emissions = float(latest[emissions_col].sum()) if emissions_col in latest.columns else 0.0
        cost_col = "cost_usd"
        total_cost = float(latest[cost_col].sum()) if cost_col in latest.columns else 0.0

        tier_dist = latest["confidence_tier"].value_counts().to_dict() if not latest.empty else {}

        return {
            "scenario_id": scenario_id,
            "latest_year": latest_year,
            "total_twh": round(total_twh, 1),
            "dc_twh": round(dc_twh, 1),
            "dc_share": round(dc_share, 4),
            "devices_twh": round(devices_twh, 1),
            "networks_twh": round(networks_twh, 1),
            "total_emissions_mtco2e": round(total_emissions / 1e9, 2),
            "total_cost_usd_bn": round(total_cost / 1e9, 2),
            "n_geos": int(df["geo"].nunique()),
            "confidence_tier_distribution": {str(k): int(v) for k, v in tier_dist.items()},
        }

    def list_scenarios(self) -> list[dict[str, Any]]:
        """Return demand scenario list from registry (grid overlays excluded).

        Returns:
            List of scenario metadata dicts.
        """
        return [s for s in self._registry if s.get("family") not in _GRID_FAMILIES]

    def get_scenario(self, scenario_id: str) -> dict[str, Any] | None:
        """Return single scenario with assumption ranges.

        Args:
            scenario_id: Scenario identifier.

        Returns:
            Scenario metadata dict, or None if not found.
        """
        for s in self._registry:
            if s["id"] == scenario_id:
                result = dict(s)
                scenario_yaml = _CONFIGS_DIR / "scenarios" / f"{scenario_id}.yaml"
                if scenario_yaml.exists():
                    with open(scenario_yaml) as f:
                        result["params"] = yaml.safe_load(f)
                dc_assumptions = _CONFIGS_DIR / "assumptions" / "datacentres.yaml"
                if dc_assumptions.exists():
                    with open(dc_assumptions) as f:
                        result["assumption_ranges"] = yaml.safe_load(f)
                return result
        return None
