# ICT Electricity Demand Model

A modular Python model and Streamlit decision-support tool that estimates and forecasts
ICT-driven electricity demand globally by geography × segment × product × year.

## Features

- **Modular model engine**: Devices, Networks, and Data Centres modules with explicit formulas
- **AI/DC scenarios**: Named scenario families (AI Low/Base/High/Stress, Sovereignty, Grid)
- **Uncertainty quantification**: P10/P50/P90 bands via Monte Carlo for Tier 1 DC outputs
- **Confidence tiering**: Every output cell carries a confidence tier (1/2/3)
- **Emissions & cost overlays**: Grid emission factors and electricity price scenarios
- **Streamlit decision-support tool**: Interactive explorer, scenario manager, confidence lens, export
- **Repeat-run CLI**: Automated nightly pipeline with diff reporting

## Quick Start

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --extra dev

# Run the Streamlit app
uv run streamlit run app/Home.py

# Run tests
uv run pytest

# Run the full pipeline
uv run python scripts/run_pipeline.py
```

## Project Structure

```
ict-electricity-demand/
├─ AGENTS.md                  # Windsurf/Cascade context anchor
├─ .windsurfrules             # Persistent coding standards
├─ configs/
│   ├─ assumptions/           # Versioned YAML assumption sets
│   ├─ scenarios/             # Named scenario configs + registry
│   └─ geo_tiers.yaml         # Geography tiering
├─ data/
│   ├─ raw/                   # Downloaded source files (gitignored)
│   ├─ staging/               # Cleaned intermediates
│   └─ gold/                  # DuckDB database files
├─ src/
│   ├─ data/                  # Data loaders + gold writer
│   ├─ models/                # Model modules (pure functions)
│   ├─ scenarios/             # Scenario registry + engine
│   └─ validation/            # Plausibility checks + triangulation
├─ app/                       # Streamlit UI
├─ tests/                     # Mirrors src/ structure
├─ scripts/                   # CLI utilities
└─ docs/                      # Technical appendix, method docs
```

## Geography Coverage

- **Tier 1 DC/AI Hotspots**: US, Germany (calibration anchor), UK, Ireland, Netherlands, Singapore, Japan, UAE
- **Tier 1 Emerging DC**: China, India, Australia, Canada, Sweden/Nordics, Poland
- **Tier 2**: France, South Korea, Brazil, South Africa, Saudi Arabia, Malaysia
- **Tier 3**: Regional aggregates (global remainder)

## Validation Thresholds

- Germany calibration: ±15% of published ICT electricity estimates
- Cross-check agreement: ±20% for Tier 1 outputs
- Monte Carlo stability: P50 converges within ±2% across 3 independent runs

## Development

```bash
# Install pre-commit hooks
uv run pre-commit install

# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/
```
