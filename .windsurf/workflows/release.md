---
description: Tag a release after reviewing and approving pipeline outputs
---

## 1. Review the diff report
Check `data/outputs/diff_*.csv` for any rows with >5% delta vs previous baseline.
Investigate any unexpected changes before proceeding.

## 2. Review release notes
Check `docs/release_notes/release_*.md` for the latest run.

## 3. Run the full test suite
// turbo
```
uv run pytest tests/ -v --tb=short
```

## 4. Lint and type check
// turbo
```
uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/
```

## 5. Tag the release
```
git add -A
git commit -m "release: <YYYYMMDD> — <brief description>"
git tag -a release/YYYYMMDD -m "Release YYYYMMDD: <description>"
git push origin main --tags
```

## 6. Update CHANGELOG.md
Add an entry at the top of `CHANGELOG.md`:
```
## [YYYY-MM-DD] — <description>
- Scenarios run: <list>
- Key changes: <what changed vs previous baseline>
- Violations: 0
- Diff flags: <N>
```
