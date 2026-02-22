"""Runs routes — async job pattern for scenario execution.

POST /runs   → queues a run, returns run_id immediately
GET  /runs/{run_id} → polls status + result
DELETE /runs/{run_id} → cancel (marks as failed)
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.engine.base import ScenarioEngine
from backend.models import RunResponse, RunResult, RunStatus, RunStatusResponse, ScenarioParams

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs", tags=["runs"])

# In-memory run store (replaced by DB/Redis in production)
_runs: dict[str, RunStatusResponse] = {}
_lock = threading.Lock()


def _get_engine() -> ScenarioEngine:
    """Dependency injection — returns the active engine."""
    from backend.api.main import get_engine
    return get_engine()


def _execute_run(run_id: str, params: ScenarioParams, engine: ScenarioEngine) -> None:
    """Execute a run in a background thread and update the run store."""
    with _lock:
        _runs[run_id].status = RunStatus.running
        _runs[run_id].progress = 0.1

    try:
        result = engine.run(params)
        result.run_id = run_id
        with _lock:
            _runs[run_id].status = RunStatus.done
            _runs[run_id].progress = 1.0
            _runs[run_id].result = result
        logger.info("Run completed: run_id=%s", run_id)
    except Exception as exc:
        with _lock:
            _runs[run_id].status = RunStatus.failed
            _runs[run_id].error = str(exc)
        logger.exception("Run failed: run_id=%s error=%s", run_id, exc)


@router.post("", response_model=RunResponse, status_code=202)
def create_run(
    params: ScenarioParams,
    engine: ScenarioEngine = Depends(_get_engine),
) -> RunResponse:
    """Queue a scenario run.

    Args:
        params: Scenario parameters and overrides.
        engine: Injected scenario engine.

    Returns:
        RunResponse with run_id and initial status.
    """
    run_id = str(uuid.uuid4())
    entry = RunStatusResponse(run_id=run_id, status=RunStatus.queued, progress=0.0)
    with _lock:
        _runs[run_id] = entry

    thread = threading.Thread(target=_execute_run, args=(run_id, params, engine), daemon=True)
    thread.start()

    logger.info("Run queued: run_id=%s scenario=%s", run_id, params.scenario_id)
    return RunResponse(run_id=run_id, status=RunStatus.queued)


@router.get("/{run_id}", response_model=RunStatusResponse)
def get_run_status(run_id: str) -> RunStatusResponse:
    """Poll run status and retrieve result when done.

    Args:
        run_id: UUID of the run to check.

    Returns:
        RunStatusResponse with status, progress, and result if done.
    """
    with _lock:
        entry = _runs.get(run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return entry


@router.delete("/{run_id}", status_code=204)
def cancel_run(run_id: str) -> None:
    """Cancel a queued or running run.

    Args:
        run_id: UUID of the run to cancel.
    """
    with _lock:
        entry = _runs.get(run_id)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        if entry.status in (RunStatus.queued, RunStatus.running):
            entry.status = RunStatus.failed
            entry.error = "Cancelled by user"
    logger.info("Run cancelled: run_id=%s", run_id)
