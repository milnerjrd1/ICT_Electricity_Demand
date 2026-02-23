"""Pydantic models for the ICT Electricity Demand API.

These are the source of truth for the API contract.
TypeScript types are generated from the OpenAPI schema produced by FastAPI.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────


class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


class SegmentEnum(str, Enum):
    devices = "devices"
    networks = "networks"
    datacentres = "datacentres"


# ── Request models ─────────────────────────────────────────────────────────────


class ScenarioParams(BaseModel):
    """Parameters for a scenario run — overrides on top of a base scenario."""

    scenario_id: str = Field(..., description="Base scenario identifier (from registry)")
    label: str | None = Field(None, description="Optional custom label for this run")

    # Data centre overrides (None = use scenario YAML default)
    pue_improvement_rate: float | None = Field(None, ge=0.0, le=0.20, description="Annual PUE improvement rate")
    utilisation_multiplier: float | None = Field(None, ge=0.5, le=2.0, description="DC utilisation multiplier")
    ai_growth_rate: float | None = Field(None, ge=0.0, le=1.0, description="Annual AI compute demand growth rate")
    hyperscale_share: float | None = Field(None, ge=0.0, le=1.0, description="Fraction of DC workload in hyperscale")

    # Device overrides (None = use scenario YAML default)
    avg_lifespan_multiplier: float | None = Field(None, ge=0.5, le=2.0, description="Device lifespan multiplier")
    device_shipment_growth: float | None = Field(None, ge=-0.10, le=0.20, description="Annual device shipment growth rate")

    # Network overrides (None = use scenario YAML default)
    power_efficiency_factor: float | None = Field(None, ge=0.5, le=1.5, description="Network equipment power efficiency factor")

    # Grid overrides
    grid_carbon_2035_target: float | None = Field(None, ge=0.0, le=1.0, description="Override grid carbon intensity 2035 target (kgCO2e/kWh)")

    # Scope
    geos: list[str] | None = Field(None, description="Geographies to include (None = all)")
    years: list[int] | None = Field(None, description="Years to include (None = 2020-2035)")
    segments: list[str] | None = Field(None, description="Segments to include (None = all)")

    # Reproducibility
    seed: int = Field(42, description="Random seed for deterministic results")


class DataQueryRequest(BaseModel):
    """Request body for POST /data/query."""

    scenario_id: str
    geos: list[str] | None = None
    years: list[int] | None = None
    segments: list[str] | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(500, ge=1, le=5000)


# ── Output row ─────────────────────────────────────────────────────────────────


class OutputRow(BaseModel):
    """Single output row — mirrors src/models/schema.py OutputRow."""

    geo: str
    segment: str
    product: str
    year: int
    kwh_estimate: float
    kwh_p10: float
    kwh_p50: float
    kwh_p90: float
    confidence_tier: int = Field(..., ge=1, le=3)
    uncertainty_band: float
    scenario_id: str
    run_id: str
    source_ids: list[str]
    emissions_kgco2e: float | None = None
    cost_usd: float | None = None


class ProvenanceRecord(BaseModel):
    """Source provenance for a data point."""

    metric: str
    geo: str
    segment: str
    year_range: str
    source_name: str
    source_type: str = Field(..., description="IEA | Eurostat | vendor | proxy | synthetic")
    retrieved_on: str | None = None
    license: str | None = None
    link: str | None = None
    confidence_tier: int = Field(..., ge=1, le=3)
    notes: str | None = None


# ── Model card ─────────────────────────────────────────────────────────────────


class ModelCard(BaseModel):
    """Metadata attached to every run result."""

    model_version: str
    data_vintage: str
    engine: str
    scenario_id: str
    assumptions_hash: str
    seed: int
    test_status: str = "not_run"
    inputs_summary: dict[str, Any] = Field(default_factory=dict)


# ── Run models ─────────────────────────────────────────────────────────────────


class RunResult(BaseModel):
    """Full result of a completed scenario run."""

    run_id: str
    status: RunStatus = RunStatus.done
    model_card: ModelCard
    rows: list[OutputRow]
    summary: dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    """Response for POST /runs — immediate acknowledgement."""

    run_id: str
    status: RunStatus = RunStatus.queued


class RunStatusResponse(BaseModel):
    """Response for GET /runs/{run_id}."""

    run_id: str
    status: RunStatus
    progress: float = Field(0.0, ge=0.0, le=1.0, description="0.0–1.0 completion fraction")
    result: RunResult | None = None
    error: str | None = None


# ── API envelope ───────────────────────────────────────────────────────────────


class ApiEnvelope(BaseModel):
    """Standard response envelope for all API responses."""

    api_version: str = "v1"
    run_id: str | None = None
    model_version: str
    data_vintage: str
    units: dict[str, str] = Field(
        default_factory=lambda: {"energy": "TWh", "emissions": "MtCO2e", "cost": "USD"}
    )
    data: Any


# ── Scenario registry ──────────────────────────────────────────────────────────


class ScenarioMeta(BaseModel):
    """Scenario metadata from registry.yaml."""

    id: str
    family: str
    label: str
    description: str
    color: str


class ScenarioDetail(ScenarioMeta):
    """Full scenario detail including assumption ranges."""

    params: dict[str, Any] = Field(default_factory=dict)
    assumption_ranges: dict[str, Any] = Field(default_factory=dict)


# ── Summary / KPI ──────────────────────────────────────────────────────────────


class DemandSummary(BaseModel):
    """KPI-level aggregates for a scenario + year."""

    scenario_id: str
    year: int
    total_twh: float
    dc_twh: float
    dc_share: float
    devices_twh: float
    networks_twh: float
    total_emissions_mtco2e: float
    total_cost_usd_bn: float
    n_geos: int
    confidence_tier_distribution: dict[str, int]
