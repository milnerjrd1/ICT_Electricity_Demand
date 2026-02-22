"""Data routes — summary KPIs and paginated demand query."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.engine.base import ScenarioEngine
from backend.models import DataQueryRequest, DemandSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["data"])


def _get_engine() -> ScenarioEngine:
    from backend.api.main import get_engine
    return get_engine()


@router.get("/summary", response_model=DemandSummary)
def get_summary(
    scenario_id: str = Query(..., description="Scenario identifier"),
    year: int = Query(2035, description="Year for KPI snapshot"),
    engine: ScenarioEngine = Depends(_get_engine),
) -> DemandSummary:
    """Return KPI-level aggregates for a scenario and year.

    Args:
        scenario_id: Scenario identifier.
        year: Year for the snapshot.
        engine: Injected scenario engine.

    Returns:
        DemandSummary with total TWh, DC share, emissions, cost.
    """
    from backend.models import ScenarioParams
    params = ScenarioParams(scenario_id=scenario_id, years=[year])
    result = engine.run(params)
    s = result.summary
    return DemandSummary(
        scenario_id=scenario_id,
        year=year,
        total_twh=s.get("total_twh", 0.0),
        dc_twh=s.get("dc_twh", 0.0),
        dc_share=s.get("dc_share", 0.0),
        devices_twh=s.get("devices_twh", 0.0),
        networks_twh=s.get("networks_twh", 0.0),
        total_emissions_mtco2e=s.get("total_emissions_mtco2e", 0.0),
        total_cost_usd_bn=s.get("total_cost_usd_bn", 0.0),
        n_geos=s.get("n_geos", 0),
        confidence_tier_distribution=s.get("confidence_tier_distribution", {}),
    )


@router.post("/query")
def query_demand(
    request: DataQueryRequest,
    engine: ScenarioEngine = Depends(_get_engine),
) -> dict:
    """Query demand data with filters. Returns paginated OutputSchema rows.

    Args:
        request: Filter parameters and pagination.
        engine: Injected scenario engine.

    Returns:
        Paginated dict with rows, total, page, page_size.
    """
    from backend.models import ScenarioParams
    params = ScenarioParams(
        scenario_id=request.scenario_id,
        geos=request.geos,
        years=request.years,
        segments=request.segments,
    )
    result = engine.run(params)

    total = len(result.rows)
    start = (request.page - 1) * request.page_size
    end = start + request.page_size
    page_rows = result.rows[start:end]

    return {
        "total": total,
        "page": request.page,
        "page_size": request.page_size,
        "rows": [r.model_dump() for r in page_rows],
    }
