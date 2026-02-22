# Cleanup Report

**Branch:** `chore/debloat-and-docs`  
**Date:** 2026-02-22  
**Engineer:** Cascade (automated repo janitor pass)

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
│   │   ├── synthetic_engine.py  Phase 0 implementation
│   │   └── pipeline_engine.py   Phase 1+ stub
│   ├── models.py             Pydantic API contract
│   └── synthetic.py          Shaped trajectory generator
├── frontend/                 React 18 + Vite + TypeScript
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
│   │   │                     DataQuality · Export
│   │   ├── store/            scenarioStore.ts (Zustand)
│   │   └── types/            schema.ts (mirrors backend Pydantic models)
│   └── vite.config.ts        Tailwind v4 plugin + /api proxy → :8000
├── src/                      Python model logic (black box — do not modify)
│   ├── data/                 Data loaders + gold writer
│   ├── models/               Devices · Networks · Data Centres · Schema
│   ├── scenarios/            Registry + engine
│   └── validation/           Plausibility + triangulation
├── app/                      Legacy Streamlit UI (retained as fallback)
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

| File | Reason |
|---|---|
| `frontend/src/assets/react.svg` | Vite scaffold boilerplate. Zero imports in any `.tsx`/`.ts` file (confirmed with ripgrep). |
| `frontend/src/App.css` | Vite scaffold boilerplate. Not imported anywhere — `App.tsx` does not contain `import './App.css'`. All styling is in `index.css`. |
| `frontend/src/components/charts/DemandFanChart.tsx` | Defined and exported but never imported by any page or component (ripgrep: zero hits for `import.*DemandFanChart`). Superseded by inline chart logic in `MissionControl.tsx`. |
| `frontend/public/vite.svg` | Vite scaffold favicon. Replaced by inline SVG data URI in `index.html` (a cyan lightning bolt matching the app theme). |
| `ICT_Electricity_Demand_Programme_Plan_v2.docx` | Binary Word document at repo root. Not referenced in any source file, script, or CI config. Likely an early planning artefact. |

---

## Moved / Renamed Files

None. All remaining files are in their correct locations.

---

## Unused Dependencies Removed

### Node (`frontend/package.json`)

| Package | Evidence of non-use | Action |
|---|---|---|
| `@types/node` (devDep) | No `process.env`, no `node:` imports, no `path`/`fs` usage anywhere in `frontend/src/`. Confirmed with ripgrep. | **Removed** |

### Python (`pyproject.toml`)

No Python dependencies were removed. All declared packages are either:
- Directly imported in `src/`, `backend/`, `app/`, or `scripts/`
- Transitive dependencies of the above (e.g. `pyarrow` used by DuckDB/pandas interop)

---

## Deprecations Retained

| Item | Why retained |
|---|---|
| `app/` (Streamlit UI) | Explicitly required as legacy fallback per cleanup constraints. `app/Home.py`, `app/pages/`, `app/stub_data.py`, `app/theme.py` are all internally consistent and self-contained. Not wired to the new React/FastAPI stack. |
| `CHANGELOG.md` | Referenced by `.windsurf/workflows/release.md` release workflow. |
| `frontend/src/components/charts/` directory | Retained — `ChoroplethMap.tsx` is actively used (lazy-loaded in `DemandExplorer.tsx`). |
| `backend/engine/pipeline_engine.py` | Phase 1+ stub. Intentionally raises `NotImplementedError`. Retained as the documented swap point for the real engine. |

---

## Other Fixes Applied

| Change | Rationale |
|---|---|
| `frontend/index.html` title: `"frontend"` → `"ICT Electricity Demand"` | Vite scaffold default title was never updated. |
| `frontend/index.html` favicon: `vite.svg` → inline SVG data URI | Removes dependency on deleted `public/vite.svg`; uses a cyan lightning bolt matching the app theme. |

---

## What Was NOT Changed

- No changes to `src/` (Python model logic — treated as black box)
- No changes to `configs/` (YAML assumptions and scenario registry)
- No changes to `tests/` (existing pytest suite)
- No changes to `scripts/` (pipeline + release notes scripts)
- No auto-formatting of existing files
- No new libraries introduced
