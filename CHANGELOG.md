# Changelog

All notable changes to the ICT Electricity Demand Model are documented here.
Format: `## [YYYY-MM-DD] — description`

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
