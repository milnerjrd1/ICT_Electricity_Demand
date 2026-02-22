# Backend — ICT Electricity Demand API

FastAPI application exposing the scenario model engine over a JSON REST API.

## Quick Start

```bash
# From repo root
source .venv/bin/activate
uvicorn backend.api.main:app --reload --port 8000
```

API is available at **http://localhost:8000**  
Interactive docs: **http://localhost:8000/api/v1/docs**

---

## Architecture

```
backend/
├── api/
│   ├── main.py           App factory: CORS, request-ID middleware, route registration
│   └── routes/
│       ├── runs.py       POST /runs · GET /runs/{id} · DELETE /runs/{id}
│       ├── scenarios.py  GET /scenarios · GET /scenarios/{id}
│       ├── data.py       GET /data/summary · POST /data/query
│       └── config.py     GET /config/assumptions
├── engine/
│   ├── base.py           ScenarioEngine ABC (stable interface)
│   ├── synthetic_engine.py  Phase 0: shaped synthetic trajectories
│   └── pipeline_engine.py   Phase 1+ stub (raises NotImplementedError)
├── models.py             Pydantic request/response models (API contract source of truth)
└── synthetic.py          Trajectory generator: 7 scenario curve shapes + emissions + cost
```

**Engine swap (Phase 1):** Change one line in `backend/api/main.py`:
```python
# Phase 0 (current)
_engine: ScenarioEngine = SyntheticEngine()

# Phase 1 (when real data loaders are ready)
_engine: ScenarioEngine = PipelineEngine()
```

---

## Endpoints

All routes are prefixed `/api/v1`.

### Health

```
GET /api/v1/health
```
```json
{"status": "ok", "model_version": "0.1.0", "data_vintage": "2026-02", "engine": "synthetic"}
```

### Scenarios

```
GET /api/v1/scenarios
```
Returns list of `ScenarioMeta` objects from `configs/scenarios/registry.yaml`.

```
GET /api/v1/scenarios/{scenario_id}
```
Returns `ScenarioDetail` with params and assumption ranges.

**Example:**
```bash
curl http://localhost:8000/api/v1/scenarios/ai_base
```
```json
{
  "id": "ai_base",
  "family": "ai_dc",
  "label": "AI Base",
  "description": "Central AI compute growth trajectory...",
  "color": "#3B82F6",
  "params": {...},
  "assumption_ranges": {...}
}
```

### Runs (async job pattern)

```
POST /api/v1/runs          → 202 {run_id, status: "queued"}
GET  /api/v1/runs/{run_id} → {run_id, status, progress, result?}
DELETE /api/v1/runs/{run_id} → 204 (cancel)
```

`status` values: `queued` → `running` → `done` | `failed`  
`progress`: 0.0–1.0 float

**Minimal run payload:**
```bash
curl -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "ai_base", "seed": 42}'
```
```json
{"run_id": "abc123...", "status": "queued"}
```

**Poll for result:**
```bash
curl http://localhost:8000/api/v1/runs/abc123...
```
```json
{
  "run_id": "abc123...",
  "status": "done",
  "progress": 1.0,
  "result": {
    "run_id": "abc123...",
    "model_card": {"model_version": "0.1.0", "engine": "synthetic", ...},
    "rows": [...],
    "summary": {
      "total_twh": 4683.5,
      "dc_twh": 2388.1,
      "dc_share": 0.51,
      ...
    }
  }
}
```

**Full `ScenarioParams` schema** (all fields optional except `scenario_id`):

| Field | Type | Default | Description |
|---|---|---|---|
| `scenario_id` | string | required | Base scenario from registry |
| `pue_improvement_rate` | float | 0.02 | Annual PUE improvement (0–0.20) |
| `utilisation_multiplier` | float | 1.0 | DC utilisation multiplier (0.5–2.0) |
| `ai_growth_rate` | float | 0.20 | Annual AI compute growth (0–1.0) |
| `hyperscale_share` | float | 0.45 | Fraction of DC workload in hyperscale |
| `avg_lifespan_multiplier` | float | 1.0 | Device lifespan multiplier |
| `device_shipment_growth` | float | 0.01 | Annual device shipment growth |
| `power_efficiency_factor` | float | 1.0 | Network equipment efficiency factor |
| `geos` | list[str] | null (all) | Filter to specific geographies |
| `years` | list[int] | null (2020–2035) | Filter to specific years |
| `segments` | list[str] | null (all) | Filter to specific segments |
| `seed` | int | 42 | Random seed for reproducibility |

### Data

```
GET  /api/v1/data/summary?scenario_id=ai_base&year=2035
POST /api/v1/data/query
```

**Query body:**
```json
{
  "scenario_id": "ai_base",
  "geos": ["US", "DE"],
  "years": [2030, 2035],
  "segments": ["datacentres"],
  "page": 1,
  "page_size": 500
}
```

### Config

```
GET /api/v1/config/assumptions
```
Returns datacentres, grid_emissions, devices, networks assumption YAML files as JSON.

---

## Non-functional

- **Request IDs:** Every response includes `X-Request-ID` header
- **Structured logging:** JSON-formatted log lines with `time`, `level`, `logger`, `msg`
- **CORS:** Allows `localhost:5173` and `localhost:3000` (Vite dev servers)
- **Reproducibility:** All synthetic runs are deterministic via `seed` parameter

---

## Environment Variables

None required for Phase 0. Future additions:

| Variable | Default | Description |
|---|---|---|
| `ENGINE` | `synthetic` | `synthetic` or `pipeline` |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
