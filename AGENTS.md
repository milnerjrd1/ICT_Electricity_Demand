# ICT Electricity Demand Model — Agent Context

## Project Purpose
A modular Python model + Streamlit decision-support tool that estimates and forecasts ICT-driven
electricity demand globally by geography × segment × product × year. Includes emissions and cost
overlays with explicit uncertainty quantification (P10/P50/P90) and a confidence tier on every
output cell. Focus is on data centres and AI as primary demand drivers.

## Tech Stack
- Python 3.11+ with uv for package management
- DuckDB for local analytical database (no Postgres/cloud DB needed)
- Streamlit for the decision-support UI
- Pandas + NumPy for data manipulation
- SciPy for Monte Carlo / statistical distributions
- Plotly for interactive charts
- pytest for testing
- ruff + mypy for linting and type checking
- GitHub Actions for CI

## Architecture Rules
- All model logic lives in `src/models/` as pure functions (no Streamlit imports)
- All data ingestion lives in `src/data/` with one loader per source
- All scenarios defined as YAML configs in `configs/scenarios/`
- All assumptions stored in `configs/assumptions/` as versioned YAML
- DuckDB is the single source of truth for gold tables (`data/gold/`)
- Streamlit app in `app/` imports from `src/` only
- Every model function must accept and return typed DataFrames conforming to `src/models/schema.py`
- Every output cell must carry `confidence_tier` (1/2/3) and `uncertainty_band`
- Every pipeline run gets a UUID (`run_id`) stored in all outputs

## Output Schema (Canonical — never break this contract)
See `src/models/schema.py`. Key columns:
- geo, segment, product, year
- kwh_estimate, kwh_p10, kwh_p50, kwh_p90
- confidence_tier (1/2/3), uncertainty_band (fractional half-width)
- scenario_id, run_id, source_ids

## Coding Standards
- Type hints on ALL functions
- Docstrings with parameter descriptions on all public functions
- No magic numbers — all constants in `configs/`
- Tests mirror `src/` structure in `tests/`
- Use `logging`, not `print()`
- All imports at top of file
- ruff and mypy must pass before any commit

## Domain Knowledge
- PUE = Power Usage Effectiveness (total facility energy / IT equipment energy)
- Stock-flow model: `installed_base(t) = installed_base(t-1) + shipments(t) - retirements(t)`
- Tier 1 DC/AI hotspots: US, Germany (calibration anchor), UK, Ireland, Netherlands, Singapore, Japan, UAE
- Tier 1 Emerging DC: China, India, Australia, Canada, Sweden/Nordics, Poland
- Tier 2: France, South Korea, Brazil, South Africa, Saudi Arabia, Malaysia
- Tier 3: Regional aggregates (global remainder)
- Germany is the calibration anchor — richest public data (Borderstep, BNetzA, Destatis)
- Confidence tier 1 = official stats / regulator data, >80% coverage, 3+ sources within 15%
- Confidence tier 2 = industry reports, 40-80% coverage, 2 sources within 25%
- Confidence tier 3 = estimates / proxies, <40% coverage or single source

## Key Formulas
### Devices
```
installed_base(t) = installed_base(t-1) + shipments(t) - retirements(t)
annual_kwh = Σ_states [installed_base × hours_per_year(state) × power_draw_W(state)] / 1000
```
### Networks
```
equipment_count = subscribers × equipment_per_sub  OR  base_stations from regulator data
annual_kwh = equipment_count × power_per_unit(t) × utilisation_factor(t)
```
### Data Centres
```
it_power = installed_capacity_MW × utilisation_rate
total_power = it_power × PUE
annual_kwh = total_power × 8760
ai_kwh = ai_compute_demand(t) × kwh_per_compute_unit(t)  [scenario-driven]
```
### Carbon & Cost
```
emissions = kwh × grid_ef(geo, t)   [kgCO2e]
cost = kwh × price(geo, t)          [€/$]
```

## Validation Thresholds
- Germany calibration: model output within ±15% of published total ICT electricity estimates
- Cross-check agreement: alternative methods within ±20% for Tier 1
- Plausibility: no country >25% of total electricity attributed to ICT
- Monte Carlo stability: P50 converges within ±2% across 3 independent runs
- Regression: all output deltas >5% vs previous baseline flagged in release notes

## Windsurf Prompting Tips
- Always use Plan Mode for multi-file architectural changes
- Use @codebase when building modules that need full project context
- Use @file to reference specific files (e.g. @src/models/schema.py) for dependent code
- One module per Cascade session keeps context tight
- Use Turbo Mode for all pipeline/CLI work
