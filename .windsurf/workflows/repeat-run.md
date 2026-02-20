---
description: Run the full nightly pipeline — ingest, model, validate, diff, release notes
---

## Full pipeline run (all scenarios)

// turbo
```
uv run python scripts/run_pipeline.py --scenario all --mc-iterations 1000
```

## Run a single scenario

// turbo
```
uv run python scripts/run_pipeline.py --scenario ai_base --mc-iterations 1000
```

## Dry run (validate structure only, no models)

// turbo
```
uv run python scripts/run_pipeline.py --dry-run
```

## Run without diff report

// turbo
```
uv run python scripts/run_pipeline.py --skip-diff
```

## Review diff report
After a run with flagged deltas, check `data/outputs/diff_*.csv`.
Approve by tagging the commit:
```
git tag -a release/YYYYMMDD -m "Release: <brief description of changes>"
git push origin release/YYYYMMDD
```

## Run tests only

// turbo
```
uv run pytest tests/ -v --tb=short
```

## Run plausibility checks only

// turbo
```
uv run pytest tests/plausibility/ -v
```
