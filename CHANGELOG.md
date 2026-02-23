# Changelog

All notable changes to the ICT Electricity Demand Model are documented here.
Format: `## [YYYY-MM-DD] — description`

---

## [2026-02-23] — Phase 2: Tier 1 hotspot data loaders

- `src/data/loader_tier1.py`: DC capacity anchors + grid EF + electricity prices for US, GB, IE, NL, SG, JP, AE (hardcoded from IEA 2024, Uptime Institute 2023, national regulators)
- `scripts/ingest_tier1.py`: multi-geo Tier 1 ingest (all 8 geos, supports `--geos`, `--replace`, `--dry-run`)
- `scripts/validate_tier1.py`: calibration check for all 8 Tier 1 geos; fixture + parquet modes
- `tests/integration/test_tier1_ingest.py`: 64 tests covering schema, calibration tolerance, sanity bounds, dry-run
- `.github/workflows/ci.yml`: extended calibration job to run `validate_tier1.py --fixture --strict`
- `fix(datacentres)`: clamp triangular MC bounds so `left <= mode <= right` (was crashing with `pue_improvement_rate > 0`)
- Calibration result (fixture, deterministic): 8/8 PASS — all geos within published benchmark tolerances
- Calibration result (real pipeline, ai_base scenario): 8/8 PASS

---

## [2026-02-23] — Phase 1: Germany calibration anchor

- `scripts/ingest_germany.py`: writes DE datacentres (Borderstep 2023 anchor), grid EF, and electricity prices to DuckDB gold tables
- `scripts/validate_germany.py`: calibration check — DE DC 2022 output vs Borderstep 2023 (18 TWh ±15%); all 3 checks pass (18.60 TWh, +3.3%)
- `scripts/run_pipeline.py`: added `--engine v1|v2` flag and `--grid-scenario` flag; `load_gold_tables_v2()` and `run_models_v2()` functions
- `tests/integration/test_germany_ingest.py`: 14 tests covering anchor schema, calibration tolerance, output schema, and dry-run
- `.github/workflows/ci.yml`: added `calibration` job running `validate_germany.py --fixture --strict`
- Calibration result: DE DC 2022 = 18.60 TWh (+3.3% vs Borderstep, within ±15% ✓)

---

## [2026-02-20] — Phase 0 scaffold

- Initial project scaffold: full repo structure, AGENTS.md, .windsurfrules, pyproject.toml
- Output schema locked: `src/models/schema.py`
- Model module stubs: devices, networks, datacentres, carbon, cost, uncertainty
- Data loader stubs: IEA, ITU, UN Comtrade, DC Byte, Eurostat
- Scenario engine + registry: 7 named scenarios across 4 families
- Assumption configs: datacentres, devices, networks, grid emissions
- Geography tiering: 25 geographies across Tier 1/2/3
- Streamlit app: Home, Explorer, Scenarios, Confidence, Export pages (stub data)
- Test suite: unit, integration, plausibility, validation tests
- CLI pipeline: `scripts/run_pipeline.py` + `scripts/generate_release_notes.py`
- Windsurf workflows: scaffold, repeat-run, release
- Status: stub data only — real model outputs pending data ingestion (Phase 1)
