"""UN Comtrade trade data loader.

Loads device shipment proxies from UN Comtrade HS code trade data.
Sources:
  - UN Comtrade Database (HS codes for ICT equipment)
    HS 8471: Computers; HS 8517: Phones; HS 8443: Printers
  - URL: https://comtradeplus.un.org/
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

SOURCE_ID = "un_comtrade"
RAW_DIR = Path("data/raw/comtrade")

HS_CODES = {
    "8471": "computers_and_peripherals",
    "8517": "mobile_phones",
    "8443": "printers",
    "8528": "monitors_and_displays",
}


def load_device_shipments(
    raw_path: Path,
    run_id: str,
    version: str,
) -> pd.DataFrame:
    """Load and clean UN Comtrade device shipment proxies.

    Args:
        raw_path: Path to the raw Comtrade CSV export file.
        run_id: UUID string for the current pipeline run.
        version: Version string for this data snapshot (e.g. '2024-Q1').

    Returns:
        Cleaned DataFrame with columns: geo, product, year, shipments_units,
        trade_value_usd, hs_code, source_id, ingestion_date, version, run_id.
    """
    logger.info("Loading UN Comtrade device shipment data from %s", raw_path)

    # TODO: Replace with actual Comtrade file parsing once data is acquired.
    # Expected format: Comtrade bulk download CSV with columns:
    #   ReporterISO, CmdCode, Period, TradeValue, Qty
    raise NotImplementedError(
        "UN Comtrade loader not yet implemented. "
        "Acquire data from https://comtradeplus.un.org/ and implement parsing."
    )
