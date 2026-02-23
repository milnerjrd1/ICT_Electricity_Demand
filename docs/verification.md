# Verification Checklist

Run these commands after any significant change to confirm the repo is healthy.  
All commands assume you are in the repo root.

---

## 1. Python — syntax + imports

```bash
source .venv/bin/activate
python -m compileall backend/ src/ scripts/ -q
```

Expected: no output (silent = pass).

---

## 2. Backend — start + smoke test

```bash
# Terminal 1: start the API
source .venv/bin/activate
uvicorn backend.api.main:app --port 8000

# Terminal 2: smoke test all required endpoints
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
# Expected: {"status": "ok", "model_version": "0.1.0", "data_vintage": "2026-02", "engine": "synthetic"}

curl -s http://localhost:8000/api/v1/scenarios | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'OK: {len(d)} scenarios')"
# Expected: OK: 7 scenarios

curl -s http://localhost:8000/api/v1/scenarios/ai_base | python3 -c "import json,sys; d=json.load(sys.stdin); print('OK:', d['id'], d['label'])"
# Expected: OK: ai_base AI Base

# POST a run and poll for result
RUN_ID=$(curl -s -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "ai_base", "seed": 42}' | python3 -c "import json,sys; print(json.load(sys.stdin)['run_id'])")
echo "Run ID: $RUN_ID"
sleep 3
curl -s "http://localhost:8000/api/v1/runs/$RUN_ID" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('status:', d['status'])
print('rows:', len(d.get('result', {}).get('rows', [])))
print('summary total_twh:', d.get('result', {}).get('summary', {}).get('total_twh'))
"
# Expected: status: done, rows: 5600, total_twh: ~4683

curl -s -X POST http://localhost:8000/api/v1/data/query \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "ai_base", "years": [2035], "segments": ["datacentres"]}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'OK: {d[\"total\"]} rows, page {d[\"page\"]}')"
# Expected: OK: N rows, page 1

curl -s http://localhost:8000/api/v1/config/assumptions | python3 -c "import json,sys; d=json.load(sys.stdin); print('OK: keys =', list(d.keys()))"
# Expected: OK: keys = ['datacentres', 'grid_emissions', ...]
```

---

## 3. Frontend — typecheck + build

```bash
cd frontend

# Install deps (idempotent)
npm install

# TypeScript typecheck (zero errors expected)
npx tsc --noEmit

# Production build (zero TS errors expected; Plotly chunk size warning is acceptable)
npm run build
# Expected: ✓ built in ~35s, zero errors
```

---

## 4. Frontend — dev smoke test

```bash
# With backend running on :8000, start frontend dev server
cd frontend
npm run dev
# → http://localhost:5173
```

Manual checks:
- [ ] App loads — light background (`#F6F7F9`), TopBar with green accent visible
- [ ] Mission Control: spinner then fan chart + KPI strip appear
- [ ] Scenario Builder: select a scenario, move a slider, click **▶ RUN SCENARIO** — results panel populates
- [ ] Demand Explorer: area chart loads, switching scenarios updates data
- [ ] Data Quality: tier cards and heatmap render
- [ ] Export: KPI cards show, Download CSV buttons are enabled
- [ ] Scenario Guide: family filter and scenario cards render
- [ ] Methodology: SVG flow diagram with pan/zoom and flow presets
- [ ] No red console errors on any page (Plotly chunk warning is acceptable)

---

## 5. Python tests

```bash
source .venv/bin/activate
pytest tests/ -q
# Expected: all tests pass (or known-failing tests match the baseline)
```

---

## 6. Integration — frontend ↔ backend wiring

```bash
# Confirm the Vite proxy is configured correctly
grep -A5 "proxy" frontend/vite.config.ts
# Expected: target: 'http://localhost:8000'

# Confirm the API base path in the client
grep "BASE" frontend/src/api/client.ts
# Expected: const BASE = '/api/v1';

# Confirm all backend route prefixes match
grep "prefix=" backend/api/main.py
# Expected: /api/v1 on all routers
```

---

## 7. API docs

With backend running:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc
- OpenAPI JSON: http://localhost:8000/api/v1/openapi.json

---

## 8. Phase 1 — Germany calibration

```bash
source .venv/bin/activate

# Fixture mode (deterministic, no DuckDB needed — used in CI)
uv run python scripts/validate_germany.py --fixture --strict
# Expected: 18.60 TWh, all 3 checks PASS ✓

# Full ingest + pipeline + calibration (requires DuckDB write access)
uv run python scripts/ingest_germany.py --replace
uv run python scripts/run_pipeline.py --engine v1 --scenario ai_base --skip-diff
uv run python scripts/validate_germany.py --strict
# Expected: DE DC 2022 within ±15% of 18 TWh

# v2 engine (study-aligned, all demand × grid scenario combinations)
uv run python scripts/run_pipeline.py --engine v2 --scenario ai_base --skip-diff
```

Calibration targets:

| Check | Target | Tolerance | Result |
|---|---|---|---|
| Borderstep 2023 (primary) | 18.0 TWh | ±15% | 18.60 TWh (+3.3%) ✓ |
| BNetzA Monitoring 2023 | 16.5 TWh | ±20% | 18.60 TWh (+12.7%) ✓ |
| IEA Data Centres 2024 | 19.2 TWh | ±20% | 18.60 TWh (−3.1%) ✓ |

---

## 9. Phase 2 — Tier 1 hotspot calibration

```bash
# Fixture mode (deterministic, no DuckDB needed — used in CI)
uv run python scripts/validate_tier1.py --fixture --strict
# Expected: 8/8 PASS ✓

# Full ingest + pipeline + calibration
uv run python scripts/ingest_tier1.py --replace
uv run python scripts/run_pipeline.py --engine v1 --scenario ai_base --skip-diff
uv run python scripts/validate_tier1.py --strict
# Expected: all 8 Tier 1 geos within benchmark tolerances

# Ingest a subset of geos
uv run python scripts/ingest_tier1.py --geos US GB IE --replace
```

Calibration targets (fixture, deterministic):

| Geo | Target | Tolerance | Source | Fixture result |
|---|---|---|---|---|
| DE | 18.0 TWh | ±15% | Borderstep 2023 | 18.60 TWh (+3.3%) ✓ |
| US | 200.0 TWh | ±20% | IEA 2024; LBNL 2024 | 206.3 TWh (+3.2%) ✓ |
| GB | 12.0 TWh | ±20% | IEA 2024; techUK 2023 | 12.58 TWh (+4.8%) ✓ |
| IE | 5.8 TWh | ±15% | EirGrid 2023; CSO Ireland | 5.79 TWh (−0.1%) ✓ |
| NL | 4.0 TWh | ±20% | CBS Netherlands; DDA 2023 | 4.09 TWh (+2.2%) ✓ |
| SG | 1.7 TWh | ±20% | EMA Singapore 2023 | 1.75 TWh (+3.2%) ✓ |
| JP | 15.0 TWh | ±20% | IEA 2024; METI Japan | 15.10 TWh (+0.7%) ✓ |
| AE | 2.5 TWh | ±25% | DEWA 2023; IEA proxy | 2.54 TWh (+1.5%) ✓ |
