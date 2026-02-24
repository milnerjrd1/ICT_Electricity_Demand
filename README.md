# ICT Electricity Demand Model

A modular Python model and React decision-support tool that estimates and forecasts ICT-driven
electricity demand globally by geography × segment × product × year. Calibrated against
Stobbe et al. 2025 (Fraunhofer IZM) for Germany across data centres, telecom networks, and
household devices.

## Features

- **3 modelled segments**: Data centres · Telecom networks · Household devices
- **7 named scenarios**: AI Low / Base / High / Stress, Sovereignty Push, Grid Constrained, Efficiency Breakthrough
- **Uncertainty quantification**: P10/P50/P90 bands on every output cell
- **Confidence tiering**: Tier 1/2/3 on every cell with explicit methodology
- **Emissions & cost overlays**: Grid emission factors and electricity price by geography
- **Benchmark comparison**: Model vs Stobbe et al. 2025 (Fraunhofer IZM) segment-by-segment
- **Async run pattern**: `POST /runs` → `GET /runs/{id}` polling

---

## Prerequisites

| Tool | Minimum version | Install |
|---|---|---|
| Python | 3.11 | [python.org](https://www.python.org/downloads/) |
| [uv](https://docs.astral.sh/uv/) | 0.4+ | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 18 | [nodejs.org](https://nodejs.org/) |
| npm | 9 | Bundled with Node.js |
| Git | any | [git-scm.com](https://git-scm.com/) |

> **macOS shortcut:** `brew install python@3.11 node` then install `uv` via the curl above.

---

## Setup (first time)

### 1. Clone the repository

```bash
git clone https://github.com/milnerjrd1/ICT_Electricity_Demand.git
cd ICT_Electricity_Demand
```

### 2. Quick start (recommended)

The pre-computed baseline parquet is committed to the repo, so you can be up and running
with a single command:

```bash
./scripts/bootstrap.sh --quick
```

This installs Python and frontend dependencies, and uses the committed
`data/outputs/baseline_latest.parquet` so the app works immediately.

To **regenerate all data from scratch** (ingest gold tables + run all 7 scenarios), omit
the flag:

```bash
./scripts/bootstrap.sh
```

### 2b. Manual setup (alternative)

If you prefer to run each step yourself:

```bash
# Install Python dependencies
uv sync --extra dev

# Install frontend dependencies
cd frontend && npm install && cd ..

# Ingest gold data into DuckDB (only needed if regenerating data)
uv run python scripts/ingest_tier1.py --replace

# Run the full pipeline — all 7 scenarios (only needed if regenerating data)
uv run python scripts/run_pipeline.py
```

> **Note:** The committed `baseline_latest.parquet` means the app works without running the
> pipeline. Only re-run if you change model code, assumptions, or anchor data.

---

## Running the application

You need **two terminal windows** — one for the backend, one for the frontend.

### Terminal 1 — Backend (FastAPI)

```bash
uv run uvicorn backend.api.main:app --reload --port 8000
```

The API is now available at:
- **Base URL:** `http://localhost:8000/api/v1`
- **Interactive docs:** `http://localhost:8000/api/v1/docs`
- **Health check:** `http://localhost:8000/api/v1/health`

### Terminal 2 — Frontend (React + Vite)

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

> The Vite dev server automatically proxies all `/api` requests to `http://localhost:8000`,
> so no environment variables or CORS configuration is needed for local development.

---

## Tests & code quality

```bash
# Run the full test suite
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Lint (ruff)
uv run ruff check src/ tests/ scripts/

# Type check (mypy)
uv run mypy src/

# Format check
uv run ruff format --check src/ tests/
```

---

## Re-ingesting data after anchor changes

If you modify any anchor data in `src/data/loader_eurostat.py` or `src/data/loader_tier1.py`,
re-run the ingest and pipeline:

```bash
uv run python scripts/ingest_tier1.py --replace
uv run python scripts/run_pipeline.py --scenario ai_base --skip-diff
```

---

## Repository structure

```
ICT_Electricity_Demand/
├── backend/                  FastAPI application
│   ├── api/
│   │   ├── main.py           App factory, CORS, middleware, route registration
│   │   └── routes/           runs · scenarios · data · config endpoints
│   ├── engine/               ScenarioEngine ABC + SyntheticEngine
│   ├── models.py             Pydantic API contract (source of truth for types)
│   └── synthetic.py          Shaped trajectory generator (7 scenario curves)
│
├── frontend/                 React 19 + Vite 7 + TypeScript UI
│   └── src/
│       ├── pages/            MissionControl · ScenarioBuilder · DemandExplorer
│       │                     DataQuality · Export · BenchmarkComparison
│       │                     ScenarioGuide · Methodology
│       ├── api/              TanStack Query hooks + fetch client
│       ├── components/       Layout shell, charts, UI primitives
│       └── store/            Zustand UI state
│
├── src/                      Python model logic
│   ├── data/
│   │   ├── loader_eurostat.py   Germany anchors (Stobbe 2025, Borderstep)
│   │   ├── loader_tier1.py      Tier 1 geo anchors (US, GB, IE, NL, SG, JP, AE)
│   │   └── gold_writer.py       DuckDB write helper (enforces schema contract)
│   ├── models/
│   │   ├── datacentres.py    DC model: capacity × utilisation × PUE × 8760
│   │   ├── networks.py       Network model: equipment_count × power × utilisation
│   │   ├── devices.py        Stock-flow model: shipments → installed_base → kWh
│   │   └── schema.py         OutputRow TypedDict (canonical column contract)
│   ├── scenarios/
│   │   ├── engine.py         run_scenario_v2: orchestrates all three models
│   │   └── registry.py       Loads scenario configs from configs/scenarios/
│   └── validation/           Plausibility checks + triangulation
│
├── configs/
│   ├── assumptions/          Versioned YAML assumption sets (DC, networks, devices)
│   └── scenarios/            Named scenario YAML files + registry.yaml
│
├── scripts/
│   ├── bootstrap.sh          One-command setup (deps + ingest + pipeline)
│   ├── ingest_tier1.py       Populate DuckDB gold tables from loaders
│   ├── run_pipeline.py       Full model pipeline (ingest → model → validate → output)
│   └── generate_release_notes.py
│
├── tests/                    pytest suite mirroring src/ structure
├── data/
│   ├── gold/                 DuckDB database (git-ignored, created by ingest)
│   └── outputs/              Pipeline parquet outputs + run log
│       └── baseline_latest.parquet  ← committed (app works out of the box)
└── docs/                     Methodology docs, assumptions register, data catalogue
```

---

## Geography coverage

| Tier | Geographies |
|---|---|
| **Tier 1 — DC/AI hotspots** | US, DE *(calibration anchor)*, GB, IE, NL, SG, JP, AE |
| **Tier 1 — Emerging DC** | CN, IN, AU, CA, SE, PL |
| **Tier 2** | FR, KR, BR, ZA, SA, MY |
| **Tier 3** | LATAM-REST, MENA-REST, SSA-REST, SEA-REST, CEE-REST |

Germany (DE) is the primary calibration anchor — it has the richest public data (Stobbe et al.
2025, Borderstep, BNetzA, Destatis) and is used to validate the model methodology.

---

## Calibration targets (Germany, Stobbe et al. 2025)

| Segment | 2018 | 2022 | 2023 | Model 2023 | Δ |
|---|---|---|---|---|---|
| Data centres | 11.0 TWh | 14.0 TWh | 15.0 TWh | 14.4 TWh | −4% |
| Telecom networks | 6.8 TWh | 8.0 TWh | 8.4 TWh | 8.1 TWh | −4% |
| Household devices | 15.5 TWh | 13.5 TWh | 13.0 TWh | 13.4 TWh | +3% |

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'src'`**
Run all Python commands from the repo root with `uv run python ...`, not `python ...`.

**`duckdb.CatalogException: Table ... does not exist`**
The gold database hasn't been populated. Run `uv run python scripts/ingest_tier1.py --replace`.

**Frontend shows "Failed to fetch" or blank data**
The backend is not running. Start it in a separate terminal:
`uv run uvicorn backend.api.main:app --reload --port 8000`

**`npm install` fails with peer dependency errors**
Use `npm install --legacy-peer-deps` or upgrade to Node.js 20+.

**Pipeline exits with "N plausibility violations — DO NOT PUBLISH"**
This is expected for non-DE geographies where anchor data is sparse. The model still produces
output; violations are logged to `data/outputs/run_log.jsonl` for review.

**Mission Control shows 0 / stale data after pulling latest code**
The committed `baseline_latest.parquet` should work immediately. If you see zeros, regenerate:
`./scripts/bootstrap.sh`

---

## Scenario reference

| ID | Label | PUE improvement | AI growth | Character |
|---|---|---|---|---|
| `ai_base` | AI Base | 2%/yr | 20%/yr | Central trajectory |
| `ai_low` | AI Low | 4%/yr | 10%/yr | Efficiency-led |
| `ai_high` | AI High | 1%/yr | 30%/yr | Demand-led |
| `ai_stress` | AI Stress | 0.5%/yr | 50%/yr | Extreme demand |
| `sovereignty_push` | Sovereignty Push | 1.5%/yr | 25%/yr | Fragmented infra |
| `grid_constrained` | Grid Constrained | 2.5%/yr | 15%/yr | Supply-limited |
| `efficiency_breakthrough` | Efficiency Breakthrough | 6%/yr | 20%/yr | Tech optimism |
