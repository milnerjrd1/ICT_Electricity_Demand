"""IEA data loader.

Loads IEA electricity statistics, emission factors, and energy prices.
Sources:
  - IEA World Energy Statistics (electricity generation, consumption)
  - IEA CO2 Emissions from Fuel Combustion (grid emission factors)
  - IEA Energy Prices (retail/wholesale electricity prices)
"""

import logging
from pathlib import Path

import pandas as pd

from src.data.gold_writer import write_gold_table

logger = logging.getLogger(__name__)

SOURCE_ID = "iea"
RAW_DIR = Path("data/raw/iea")


def load_grid_emission_factors(
    raw_path: Path,
    run_id: str,
    version: str,
) -> pd.DataFrame:
    """Load and clean IEA grid emission factors into the gold table.

    Args:
        raw_path: Path to the raw IEA emission factors CSV/Excel file.
        run_id: UUID string for the current pipeline run.
        version: Version string for this data snapshot (e.g. '2024').

    Returns:
        Cleaned DataFrame with columns: geo, year, grid_ef_kgco2e_per_kwh,
        source_id, ingestion_date, version, run_id.
    """
    logger.info("Loading IEA grid emission factors from %s", raw_path)

    # TODO: Replace with actual IEA file parsing once data is acquired.
    # Expected columns in raw file: Country, Year, Value (kgCO2/kWh)
    raise NotImplementedError(
        "IEA grid emission factor loader not yet implemented. "
        "Acquire data from https://www.iea.org/data-and-statistics and implement parsing."
    )


def load_electricity_prices(
    raw_path: Path,
    run_id: str,
    version: str,
) -> pd.DataFrame:
    """Load and clean IEA electricity prices into the gold table.

    Args:
        raw_path: Path to the raw IEA energy prices CSV/Excel file.
        run_id: UUID string for the current pipeline run.
        version: Version string for this data snapshot (e.g. '2024').

    Returns:
        Cleaned DataFrame with columns: geo, year, price_usd_per_kwh,
        sector (industry/residential), source_id, ingestion_date, version, run_id.
    """
    logger.info("Loading IEA electricity prices from %s", raw_path)

    # TODO: Replace with actual IEA file parsing once data is acquired.
    raise NotImplementedError(
        "IEA electricity price loader not yet implemented. "
        "Acquire data from https://www.iea.org/data-and-statistics and implement parsing."
    )
