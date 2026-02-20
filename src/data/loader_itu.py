"""ITU data loader.

Loads ITU ICT statistics for network infrastructure modelling.
Sources:
  - ITU World Telecommunication/ICT Indicators Database
    (subscribers, base stations, broadband penetration)
  - URL: https://www.itu.int/en/ITU-D/Statistics/Pages/stat/default.aspx
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

SOURCE_ID = "itu"
RAW_DIR = Path("data/raw/itu")


def load_network_subscribers(
    raw_path: Path,
    run_id: str,
    version: str,
) -> pd.DataFrame:
    """Load and clean ITU subscriber and base station data.

    Args:
        raw_path: Path to the raw ITU indicators CSV/Excel file.
        run_id: UUID string for the current pipeline run.
        version: Version string for this data snapshot (e.g. '2024').

    Returns:
        Cleaned DataFrame with columns: geo, year, mobile_subscribers,
        fixed_broadband_subscribers, base_stations_4g, base_stations_5g,
        source_id, ingestion_date, version, run_id.
    """
    logger.info("Loading ITU network subscriber data from %s", raw_path)

    # TODO: Replace with actual ITU file parsing once data is acquired.
    # Expected format: ITU Excel export with country × indicator × year structure
    raise NotImplementedError(
        "ITU subscriber loader not yet implemented. "
        "Acquire data from https://www.itu.int/en/ITU-D/Statistics and implement parsing."
    )
