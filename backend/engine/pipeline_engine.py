"""Pipeline engine — serves real model output from pre-computed parquet files,
or runs the live model when custom scenario parameters are provided.

For pre-computed (default) runs: reads from data/outputs/baseline_latest.parquet.
For custom runs (slider overrides): loads gold tables from DuckDB and runs the
scenario engine with the merged params, returning a live result.
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

    def _load_scenario_defaults(self, scenario_id: str) -> dict[str, Any]:
        """Load scenario YAML defaults for comparison with request params.

        Args:
            scenario_id: Scenario identifier.

        Returns:
            Dict of default param values from the scenario YAML.
        """
        scenario_yaml = _CONFIGS_DIR / "scenarios" / f"{scenario_id}.yaml"
        if scenario_yaml.exists():
            with open(scenario_yaml) as f:
                return yaml.safe_load(f) or {}
        return {}

    def _is_custom_run(self, params: ScenarioParams) -> bool:
        """Return True if any slider param differs from the scenario's YAML defaults.

        Args:
            params: Incoming scenario parameters.

        Returns:
            True if the user has customised any parameter.
        """
        defaults = self._load_scenario_defaults(params.scenario_id)
        _PARAM_KEYS = [
            "pue_improvement_rate",
            "utilisation_multiplier",
            "ai_growth_rate",
            "avg_lifespan_multiplier",
            "device_shipment_growth",
            "power_efficiency_factor",
        ]
        for key in _PARAM_KEYS:
            user_val = getattr(params, key, None)
            default_val = defaults.get(key)
            if user_val is not None and default_val is not None:
                if abs(float(user_val) - float(default_val)) > 1e-6:
                    logger.info(
                        "PipelineEngine: custom param %s=%s (default=%s) → live run",
                        key, user_val, default_val,
                    )
                    return True
        return False

    def _run_live_model(self, params: ScenarioParams, run_id: str) -> RunResult:
        """Run the live scenario engine with merged params (YAML defaults + overrides).

        Args:
            params: Scenario parameters including user overrides.
            run_id: UUID for this run.

        Returns:
            RunResult from the live model execution.
        """
        from src.data.gold_writer import list_gold_tables, read_gold_table

        # Load gold tables from DuckDB
        available = list_gold_tables()
        gold_tables: dict[str, pd.DataFrame] = {}
        for tbl in ["datacentres", "networks", "devices", "grid_ef", "electricity_prices"]:
            if tbl in available:
                gold_tables[tbl] = read_gold_table(tbl)

        # Merge YAML defaults with user overrides
        scenario_params = self._load_scenario_defaults(params.scenario_id)
        scenario_params["scenario_id"] = params.scenario_id
        override_keys = [
            "pue_improvement_rate", "utilisation_multiplier", "ai_growth_rate",
            "avg_lifespan_multiplier", "device_shipment_growth", "power_efficiency_factor",
        ]
        for key in override_keys:
            val = getattr(params, key, None)
            if val is not None:
                scenario_params[key] = val

        logger.info(
            "PipelineEngine._run_live_model: scenario=%s params=%s",
            params.scenario_id,
            {k: scenario_params.get(k) for k in override_keys},
        )

        from src.models.datacentres import run_datacentres_model
        from src.models.devices import run_devices_model
        from src.models.networks import run_networks_model
        from src.models.carbon import apply_carbon_overlay
        from src.models.cost import apply_cost_overlay

        segment_dfs: list[pd.DataFrame] = []
        if "devices" in gold_tables and not gold_tables["devices"].empty:
            segment_dfs.append(run_devices_model(gold_tables["devices"], scenario_params, run_id=run_id))
        if "networks" in gold_tables and not gold_tables["networks"].empty:
            segment_dfs.append(run_networks_model(gold_tables["networks"], scenario_params, run_id=run_id))
        if "datacentres" in gold_tables and not gold_tables["datacentres"].empty:
            segment_dfs.append(run_datacentres_model(gold_tables["datacentres"], scenario_params, run_id=run_id, monte_carlo_iterations=0))

        if not segment_dfs:
            raise RuntimeError("No segment data available for live run")

        df = pd.concat(segment_dfs, ignore_index=True)

        if "grid_ef" in gold_tables and not gold_tables["grid_ef"].empty:
            df = apply_carbon_overlay(df, gold_tables["grid_ef"])
        if "electricity_prices" in gold_tables and not gold_tables["electricity_prices"].empty:
            df = apply_cost_overlay(df, gold_tables["electricity_prices"])

        # Apply year >= 2013 filter
        df = df[df["year"] >= 2013].copy()

        # Apply scope filters
        if params.geos:
            df = df[df["geo"].isin(params.geos)]
        if params.years:
            df = df[df["year"].isin(params.years)]
        if params.segments:
            df = df[df["segment"].isin(params.segments)]

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
                scenario_id=str(r.get("scenario_id", params.scenario_id)),
                run_id=run_id,
                source_ids=list(r["source_ids"]) if isinstance(r.get("source_ids"), list) else [],
                emissions_kgco2e=float(r["emissions_kgco2e"]) if r.get("emissions_kgco2e") is not None else None,
                cost_usd=float(r["cost_usd"]) if r.get("cost_usd") is not None else None,
            )
            for _, r in df.iterrows()
        ]

        model_card = ModelCard(
            model_version=MODEL_VERSION,
            data_vintage=DATA_VINTAGE,
            engine="pipeline-live",
            scenario_id=params.scenario_id,
            assumptions_hash="custom",
            seed=params.seed,
            test_status="not_run",
            inputs_summary={
                "n_geos": int(df["geo"].nunique()),
                "n_years": int(df["year"].nunique()),
                "n_rows": len(df),
                "source": "live",
                "overrides": {k: scenario_params.get(k) for k in override_keys},
            },
        )

        return RunResult(
            run_id=run_id,
            status=RunStatus.done,
            model_card=model_card,
            rows=rows,
            summary=self._build_summary(df, params.scenario_id),
        )

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

        # If the user has customised any slider param, run the live model
        if self._is_custom_run(params):
            return self._run_live_model(params, run_id)

        df = self._load_parquet(params.scenario_id)

        if df is None:
            # No parquet available — fall back to synthetic
            logger.warning(
                "PipelineEngine: no parquet for scenario=%s, falling back to synthetic",
                params.scenario_id,
            )
            from backend.engine.synthetic_engine import SyntheticEngine
            return SyntheticEngine().run(params)

        # Filter to the requested scenario's rows (parquet may contain all scenarios)
        if "scenario_id" in df.columns and params.scenario_id in df["scenario_id"].values:
            df = df[df["scenario_id"] == params.scenario_id].copy()
        elif "scenario_id" in df.columns:
            # Scenario not in parquet — fall back to synthetic
            logger.warning(
                "PipelineEngine: scenario=%s not in parquet, falling back to synthetic",
                params.scenario_id,
            )
            from backend.engine.synthetic_engine import SyntheticEngine
            return SyntheticEngine().run(params)

        # Apply filters — always exclude burn-in years (pre-2013) from API output
        mask = df["year"] >= 2013
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
