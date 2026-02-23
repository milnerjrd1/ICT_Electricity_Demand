# Cleanup Report

**Branch:** `chore/debloat-and-docs`  
**Date:** 2026-02-23 (pass 2)  
**Engineer:** Cascade (automated repo janitor)

This report covers both the original cleanup pass (2026-02-22) and the second pass (2026-02-23).

---

## Repo Map (post-cleanup)

```
ict-electricity-demand/
├── backend/                  FastAPI application
│   ├── api/
│   │   ├── main.py           ← entrypoint: uvicorn backend.api.main:app
│   │   └── routes/           runs.py · scenarios.py · data.py · config.py
│   ├── engine/
│   │   ├── base.py           ScenarioEngine ABC
│   │   └── synthetic_engine.py  Phase 0 implementation
│   ├── models.py             Pydantic API contract
│   └── synthetic.py          Shaped trajectory generator
├── frontend/                 React 19 + Vite 7 + TypeScript
│   ├── index.html            ← entrypoint: /src/main.tsx
│   ├── src/
│   │   ├── main.tsx          React root mount
│   │   ├── App.tsx           Router + QueryClientProvider
│   │   ├── api/              client.ts · hooks.ts (TanStack Query)
│   │   ├── components/
│   │   │   ├── charts/       ChoroplethMap.tsx (lazy-loaded Plotly)
│   │   │   ├── layout/       Shell · TopBar · Sidebar
│   │   │   └── ui/           Card · Badge · Button · PageHeader
│   │   ├── pages/            MissionControl · ScenarioBuilder · DemandExplorer
│   │   │                     DataQuality · Export · ScenarioGuide · Methodology
│   │   ├── store/            scenarioStore.ts (Zustand)
│   │   └── types/            schema.ts (mirrors backend Pydantic models)
│   └── vite.config.ts        Tailwind v4 plugin + /api proxy → :8000
├── src/                      Python model logic (black box — do not modify)
│   ├── data/                 Data loaders + gold writer
│   ├── models/               Devices · Networks · Data Centres · Schema
│   ├── scenarios/            Registry + engine
│   └── validation/           Plausibility + triangulation
├── configs/                  YAML assumptions + scenario registry
├── scripts/                  run_pipeline.py · generate_release_notes.py
├── tests/                    pytest suite mirroring src/
└── docs/                     This file + assumptions_register · data_catalogue · etc.
```

**Build tools:** `uv` (Python), `npm` (Node)  
**Backend entrypoint:** `backend/api/main.py` → `uvicorn backend.api.main:app`  
**Frontend entrypoint:** `frontend/index.html` → `frontend/src/main.tsx`  
**API client:** `frontend/src/api/client.ts`

---

## Deleted Files

### Pass 1 (2026-02-22)

| File | Reason |
|---|---|
| `frontend/src/assets/react.svg` | Vite scaffold boilerplate. Zero imports in any `.tsx`/`.ts` file. |
| `frontend/src/App.css` | Vite scaffold boilerplate. Not imported anywhere. |
| `frontend/src/components/charts/DemandFanChart.tsx` | Never imported by any page or component. Superseded by inline chart logic in `MissionControl.tsx`. |
| `frontend/public/vite.svg` | Vite scaffold favicon. Replaced by inline SVG data URI in `index.html`. |
| `ICT_Electricity_Demand_Programme_Plan_v2.docx` | Binary Word document at repo root. Not referenced anywhere. |

### Pass 2 (2026-02-23)

| File | Reason |
|---|---|
| `app/Home.py` | Legacy Streamlit UI — deleted entirely (user decision). Recoverable from git. |
| `app/pages/1_Explorer.py` | Part of deleted Streamlit app. |
| `app/pages/2_Scenarios.py` | Part of deleted Streamlit app. |
| `app/pages/3_Confidence.py` | Part of deleted Streamlit app. |
| `app/pages/4_Export.py` | Part of deleted Streamlit app. |
| `app/pages/5_Application_Areas.py` | Part of deleted Streamlit app. |
| `app/pages/6_Appendix_Export.py` | Part of deleted Streamlit app. |
| `app/stub_data.py` | Part of deleted Streamlit app. |
| `app/theme.py` | Part of deleted Streamlit app. |
| `.streamlit/config.toml` | Only used by the deleted Streamlit app. |
| `backend/engine/pipeline_engine.py` | 40-line stub raising `NotImplementedError`. Never imported outside its own file. Recoverable from git. |
| `frontend/src/assets/` (empty dir) | Empty directory, never contained tracked files. |

### Pass 2 — Dead code removed from existing files

| File | What was removed | Evidence |
|---|---|---|
| `frontend/src/api/hooks.ts` | `useScenario()` hook | Exported but never imported in any `.tsx` file (0 hits via ripgrep). |
| `frontend/src/api/hooks.ts` | `useAssumptions()` hook | Exported but never imported in any `.tsx` file (0 hits). |
| `frontend/src/types/schema.ts` | `DemandSummary` interface | Only defined, never imported (0 hits outside schema.ts). |
| `frontend/src/types/schema.ts` | `RunResponse` interface | Only defined, never imported (0 hits outside schema.ts). |
| `frontend/src/types/schema.ts` | `ScenarioDetail` interface | Only imported by the deleted `useScenario` hook. |

---

## Dependency Changes

### Node (`frontend/package.json`)

Pass 1 removed `@types/node` (devDep). Pass 2 found no further unused Node dependencies — all current deps are actively imported.

### Python (`pyproject.toml`)

| Package | Action | Reason |
|---|---|---|
| `streamlit>=1.35.0` | Moved to `[project.optional-dependencies.streamlit]` | Not imported by `src/`, `backend/`, `scripts/`, or `tests/`. Only used by deleted `app/`. |
| `plotly>=5.22.0` | Moved to `[project.optional-dependencies.streamlit]` | Same — only used by deleted `app/`. |

Install with `uv sync --extra streamlit` if needed.

---

## Items Retained

| Item | Why retained |
|---|---|
| `CHANGELOG.md` | Referenced by `.windsurf/workflows/release.md`. |
| `frontend/src/components/charts/ChoroplethMap.tsx` | Actively used (lazy-loaded in `DemandExplorer.tsx`). |
| `configs/scenarios/grid_mix_*.yaml` (3 files) | Referenced by `carbon_v2.py` grid scenario logic. Not listed to users but used internally. |
| `src/models/*_v2.py` files | Active v2 model modules used by `src/scenarios/engine.py`. Not duplicates of v1 — different implementations. |

---

## Documentation Updated

| File | Changes |
|---|---|
| `README.md` | React 19, Open Sans font, added ScenarioGuide + Methodology pages, removed Streamlit section, updated structure tree. |
| `frontend/README.md` | Light theme design system, new pages, removed stale `VITE_API_BASE` env var, added font entries. |
| `backend/README.md` | Removed `pipeline_engine.py` from architecture tree, updated engine swap docs. |
| `docs/verification.md` | Refreshed with current pages, light theme, accurate commands. |
| `docs/cleanup_report.md` | This file — updated with pass 2 changes. |

---

## What Was NOT Changed

- No changes to `src/` (Python model logic — treated as black box)
- No changes to `configs/` (YAML assumptions and scenario registry)
- No changes to `tests/` (existing pytest suite)
- No changes to `scripts/` (pipeline + release notes scripts)
- No auto-formatting of existing files
- No new libraries introduced
