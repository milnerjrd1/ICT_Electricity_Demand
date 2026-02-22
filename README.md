# ICT Electricity Demand Model

A modular Python model and enterprise React decision-support tool that estimates and forecasts
ICT-driven electricity demand globally by geography × segment × product × year.

## Features

- **7 named scenarios**: AI Low / Base / High / Stress, Sovereignty Push, Grid Constrained, Efficiency Breakthrough
- **Shaped trajectories**: Each scenario has a distinct curve shape (not just a multiplier)
- **Uncertainty quantification**: P10/P50/P90 bands on every output cell
- **Confidence tiering**: Tier 1/2/3 on every cell with explicit methodology
- **Emissions & cost overlays**: Grid emission factors and electricity price by geography
- **Async run pattern**: `POST /runs` → `GET /runs/{id}` polling — handles long Monte Carlo runs
- **Engine abstraction**: Swap synthetic → real pipeline in one line (`backend/api/main.py`)

## Quick Start

### 1. Install Python deps

```bash
uv sync --extra dev
```

### 2. Start the backend (FastAPI)

```bash
source .venv/bin/activate
uvicorn backend.api.main:app --reload --port 8000
# API docs → http://localhost:8000/api/v1/docs
```

### 3. Start the frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
# App → http://localhost:5173
```

### Legacy Streamlit app (fallback only)

```bash
uv run streamlit run app/Home.py
# → http://localhost:8501
```

### Tests & pipeline

```bash
uv run pytest                          # unit + integration tests
uv run ruff check src/ tests/          # lint
uv run mypy src/                       # type check
uv run python scripts/run_pipeline.py  # full nightly pipeline
```

## Repository Structure

```
ict-electricity-demand/
├── backend/                  FastAPI application (see backend/README.md)
│   ├── api/main.py           ← API entrypoint
│   ├── engine/               ScenarioEngine ABC + synthetic/pipeline implementations
│   ├── models.py             Pydantic API contract (source of truth for types)
│   └── synthetic.py          Shaped trajectory generator
├── frontend/                 React 18 + Vite + TypeScript (see frontend/README.md)
│   └── src/
│       ├── pages/            MissionControl · ScenarioBuilder · DemandExplorer · DataQuality · Export
│       ├── api/              TanStack Query hooks + fetch client
│       └── store/            Zustand UI state
├── src/                      Python model logic (black box)
│   ├── data/                 Data loaders + DuckDB gold writer
│   ├── models/               Devices · Networks · Data Centres · Schema
│   ├── scenarios/            Registry + engine
│   └── validation/           Plausibility checks + triangulation
├── app/                      Legacy Streamlit UI (fallback)
├── configs/
│   ├── assumptions/          Versioned YAML assumption sets
│   └── scenarios/            Named scenario configs + registry.yaml
├── tests/                    pytest suite mirroring src/
├── scripts/                  run_pipeline.py · generate_release_notes.py
└── docs/
    ├── cleanup_report.md     Repo janitor audit log
    ├── verification.md       Repeatable health-check commands
    ├── assumptions_register.md
    ├── data_catalogue.md
    ├── limitations_register.md
    └── proxy_rulebook.md
```

## Geography Coverage

- **Tier 1 DC/AI Hotspots**: US, DE (calibration anchor), GB, IE, NL, SG, JP, AE
- **Tier 1 Emerging DC**: CN, IN, AU, CA, SE, PL
- **Tier 2**: FR, KR, BR, ZA, SA, MY
- **Tier 3**: Regional aggregates (LATAM-REST, MENA-REST, SSA-REST, SEA-REST, CEE-REST)

## Validation Thresholds

- Germany calibration: ±15% of published ICT electricity estimates
- Cross-check agreement: ±20% for Tier 1 outputs
- Monte Carlo stability: P50 converges within ±2% across 3 independent runs

## Phase Roadmap

| Phase | Status | Description |
|---|---|---|
| 0 | ✅ Done | Synthetic shaped trajectories, full React/FastAPI app |
| 1 | Planned | Germany calibration anchor (Borderstep, BNetzA, Destatis) |
| 2 | Planned | Tier 1 hotspot real data loaders |
| 3 | Planned | Global coverage + AI compute layer |
| 4 | Planned | Monte Carlo uncertainty (1000 iterations) |
| 5 | Planned | Nightly pipeline + model card artefacts |
