# Frontend — ICT Electricity Demand

React 19 + Vite 7 + TypeScript enterprise UI for the ICT Electricity Demand scenario modelling tool.

## Quick Start

```bash
# Requires the backend running on :8000 (see backend/README.md)
npm install
npm run dev
# → http://localhost:5173
```

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start Vite dev server with HMR (proxies `/api` → `localhost:8000`) |
| `npm run build` | TypeScript check + production bundle → `dist/` |
| `npm run lint` | ESLint with react-hooks + react-refresh rules |
| `npm run preview` | Serve the production `dist/` build locally |

## Stack

| Library | Version | Purpose |
|---|---|---|
| React | 19 | UI framework |
| Vite | 7 | Build tool + dev server |
| TypeScript | 5.9 | Type safety |
| Tailwind CSS | 4 | Utility CSS (via `@tailwindcss/vite` plugin) |
| React Router | 7 | Client-side routing |
| TanStack Query | 5 | Server state: API calls, caching, polling |
| Zustand | 5 | UI state: active scenario, saved scenarios, selections |
| Recharts | 3 | Line/area/bar charts |
| react-plotly.js | 2 | Choropleth world map (lazy-loaded on Explorer page) |
| Lucide React | 0.575 | Icons |
| Open Sans | — | Body font (loaded via Google Fonts) |
| JetBrains Mono | — | Monospace font for data values, badges, code |

## Structure

```
src/
├── main.tsx              React root mount
├── App.tsx               Router + QueryClientProvider
├── index.css             Global theme (CSS variables, @keyframes, scrollbar)
├── api/
│   ├── client.ts         Fetch wrapper with request IDs + error handling
│   └── hooks.ts          TanStack Query hooks (useScenarios, useCreateRun, useRunStatus, …)
├── components/
│   ├── charts/
│   │   └── ChoroplethMap.tsx   Plotly choropleth (lazy-loaded)
│   ├── layout/
│   │   ├── Shell.tsx     Page wrapper (TopBar + Sidebar + Outlet)
│   │   ├── TopBar.tsx    Fixed header with engine/version status
│   │   └── Sidebar.tsx   Navigation links
│   └── ui/
│       ├── Card.tsx      Card + KpiCard
│       ├── Badge.tsx     Inline status badge
│       ├── Button.tsx    Primary / secondary / danger / ghost variants
│       └── PageHeader.tsx  Page title + subtitle + actions slot
├── pages/
│   ├── MissionControl.tsx   All-scenario fan chart + KPI strip
│   ├── ScenarioBuilder.tsx  Assumption sliders + RUN button + results panel
│   ├── DemandExplorer.tsx   Choropleth map + by-segment/geo/product tabs
│   ├── DataQuality.tsx      Confidence tier cards + heatmap + geo ranking
│   ├── Export.tsx           CSV download + paginated data preview
│   ├── ScenarioGuide.tsx    Interactive scenario family browser
│   └── Methodology.tsx      SVG process flow with pan/zoom + flow highlighting
├── store/
│   └── scenarioStore.ts  Zustand store (active params, saved scenarios)
└── types/
    └── schema.ts         TypeScript types mirroring backend Pydantic models
```

## Environment Variables

No environment variables are required for development. The Vite dev server proxies all `/api` requests to `http://localhost:8000` (configured in `vite.config.ts`). The API base path `/api/v1` is hardcoded in `src/api/client.ts`.

## API Wiring

- Base path: `/api/v1` (defined in `src/api/client.ts`)
- Proxy target: `http://localhost:8000` (defined in `vite.config.ts`)
- All API types live in `src/types/schema.ts` and mirror `backend/models.py`

## Design System

Light-theme design with CSS custom properties defined in `src/index.css`:

| Token | Value | Usage |
|---|---|---|
| `--bg-base` | `#F6F7F9` | Page background |
| `--bg-surface` | `#FFFFFF` | Cards, sidebar |
| `--bg-elevated` | `#FBFBFC` | Inputs, table rows |
| `--accent` | `#86BC24` | Primary accent (brand green) |
| `--accent-amber` | `#ED8B00` | Warning / Tier 2 |
| `--accent-red` | `#DA291C` | Alert / Tier 3 |
| `--font-mono` | JetBrains Mono | Data values, badges |
| `--font-sans` | Open Sans | Body text |
