# Verification Checklist

Run these commands after any significant change to confirm the repo is healthy.  
All commands assume you are in the repo root: `/Users/jamesmilner/ict-electricity-demand/`

---

## 1. Python — syntax + imports

```bash
# Compile-check all Python files (catches syntax errors and bad imports)
source .venv/bin/activate
python -m compileall backend/ src/ app/ scripts/ -q
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
- [ ] App loads at `http://localhost:5173` — dark navy background, TopBar visible
- [ ] Mission Control: spinner shows `0/7 scenarios loaded...`, then charts appear
- [ ] Scenario Builder: select a scenario, move a slider, click **▶ RUN SCENARIO** — results panel populates
- [ ] Demand Explorer: loads map tab, switches to segment/geo/product tabs
- [ ] Data Quality: tier cards and heatmap render
- [ ] Export: KPI cards show, Download CSV buttons are enabled
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

## 8. Legacy Streamlit (fallback only)

```bash
source .venv/bin/activate
streamlit run app/Home.py
# → http://localhost:8501
```

Expected: Matrix-themed dashboard loads with stub data.
