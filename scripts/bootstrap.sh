#!/usr/bin/env bash
set -euo pipefail

# ICT Electricity Demand Model — Bootstrap Script
# Installs all dependencies, populates DuckDB gold tables, and runs the full pipeline.
#
# Usage:
#   ./scripts/bootstrap.sh           # full setup (deps + ingest + pipeline)
#   ./scripts/bootstrap.sh --quick   # deps only (use committed parquet as-is)

QUICK=false
for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=true ;;
  esac
done

echo "==> Installing Python dependencies..."
uv sync --extra dev

echo "==> Installing frontend dependencies..."
(cd frontend && npm install)

if [ "$QUICK" = true ]; then
  if [ -f data/outputs/baseline_latest.parquet ]; then
    echo ""
    echo "✅ Quick bootstrap complete (using committed parquet)."
    echo "   Parquet:  data/outputs/baseline_latest.parquet"
  else
    echo ""
    echo "⚠️  No committed parquet found — running full pipeline instead."
    QUICK=false
  fi
fi

if [ "$QUICK" = false ]; then
  echo "==> Ingesting Tier 1 gold data into DuckDB..."
  uv run python scripts/ingest_tier1.py --replace

  echo "==> Running full pipeline (all scenarios)..."
  uv run python scripts/run_pipeline.py

  echo ""
  echo "✅ Bootstrap complete."
  echo "   Parquet:  data/outputs/baseline_latest.parquet"
  echo "   DuckDB:   data/gold/ict_demand.duckdb"
fi

echo ""
echo "Start the app:"
echo "  Terminal 1:  uv run uvicorn backend.api.main:app --reload --port 8000"
echo "  Terminal 2:  cd frontend && npm run dev"
echo "  Open:        http://localhost:5173"
