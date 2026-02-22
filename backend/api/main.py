"""FastAPI application entry point.

All routes under /api/v1.
Includes CORS, request ID middleware, structured logging.
Engine is injected via get_engine() — swap SyntheticEngine for PipelineEngine in Phase 1.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.engine.base import ScenarioEngine
from backend.engine.synthetic_engine import SyntheticEngine

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "msg": "%(message)s"}',
)
logger = logging.getLogger(__name__)

# ── Engine (swap here for Phase 1) ────────────────────────────────────────────

_engine: ScenarioEngine = SyntheticEngine()


def get_engine() -> ScenarioEngine:
    """Return the active scenario engine (dependency injection target)."""
    return _engine


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ICT Electricity Demand API",
    description="Scenario modelling API for global ICT electricity demand forecasting.",
    version="0.1.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request ID middleware ─────────────────────────────────────────────────────


@app.middleware("http")
async def request_id_middleware(request: Request, call_next: Any) -> Response:
    """Attach a unique request ID to every request and log duration."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()

    response: Response = await call_next(request)

    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request method=%s path=%s status=%d duration_ms=%s request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response


# ── Routes ────────────────────────────────────────────────────────────────────

from backend.api.routes import config, data, runs, scenarios  # noqa: E402

app.include_router(runs.router, prefix="/api/v1")
app.include_router(scenarios.router, prefix="/api/v1")
app.include_router(data.router, prefix="/api/v1")
app.include_router(config.router, prefix="/api/v1")


# ── Health ────────────────────────────────────────────────────────────────────


@app.get("/api/v1/health", tags=["health"])
def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Dict with status, model_version, and data_vintage.
    """
    return {
        "status": "ok",
        "model_version": "0.1.0",
        "data_vintage": "2026-02",
        "engine": "synthetic",
    }
