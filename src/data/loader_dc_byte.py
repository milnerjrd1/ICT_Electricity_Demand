"""DC Byte / Uptime Institute data loader.

Loads data centre capacity and PUE benchmark data.
Sources:
  - DC Byte (colocation and hyperscale capacity by geography)
  - Uptime Institute Annual Global Data Center Survey (PUE benchmarks)
  - Hyperscaler sustainability reports (Google, Microsoft, Amazon, Meta)
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

SOURCE_ID = "dc_byte_uptime"
RAW_DIR = Path("data/raw/dc_capacity")


def load_dc_capacity(
    raw_path: Path,
    run_id: str,
    version: str,
) -> pd.DataFrame:
    """Load and clean data centre capacity data.

    Args:
        raw_path: Path to the raw DC capacity CSV/Excel file.
        run_id: UUID string for the current pipeline run.
        version: Version string for this data snapshot (e.g. '2024').

    Returns:
        Cleaned DataFrame with columns: geo, product (dc_type), year,
        installed_capacity_mw, utilisation_rate, pue, ai_share,
        confidence_tier, source_ids, source_id, ingestion_date, version, run_id.
        dc_type is one of: hyperscale, sovereign, colocation, on_premises, edge.
    """
    logger.info("Loading DC capacity data from %s", raw_path)

    # TODO: Replace with actual DC Byte / Uptime file parsing once data is acquired.
    raise NotImplementedError(
        "DC capacity loader not yet implemented. "
        "Acquire data from DC Byte (https://www.dc-byte.com/) and "
        "Uptime Institute (https://uptimeinstitute.com/) and implement parsing."
    )


def load_pue_benchmarks(
    raw_path: Path,
    run_id: str,
    version: str,
) -> pd.DataFrame:
    """Load and clean PUE benchmark data by DC type and geography.

    Args:
        raw_path: Path to the raw PUE benchmark file.
        run_id: UUID string for the current pipeline run.
        version: Version string for this data snapshot (e.g. '2024').

    Returns:
        Cleaned DataFrame with columns: geo, product (dc_type), year,
        pue_mean, pue_p25, pue_p75, source_id, ingestion_date, version, run_id.
    """
    logger.info("Loading PUE benchmark data from %s", raw_path)

    # TODO: Replace with actual Uptime Institute survey parsing once data is acquired.
    raise NotImplementedError(
        "PUE benchmark loader not yet implemented. "
        "Acquire data from Uptime Institute Annual Survey and implement parsing."
    )
