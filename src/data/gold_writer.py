"""DuckDB gold table writer.

All gold table writes must go through this module.
Every gold table gets: source_id, ingestion_date, version, run_id columns.
"""

import logging
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

GOLD_DB_PATH = Path("data/gold/ict_demand.duckdb")

REQUIRED_LINEAGE_COLUMNS = {"source_id", "ingestion_date", "version"}


def write_gold_table(
    df: pd.DataFrame,
    table_name: str,
    source_id: str,
    version: str,
    run_id: str,
    db_path: Path = GOLD_DB_PATH,
    if_exists: str = "append",
) -> None:
    """Write a DataFrame to a DuckDB gold table with lineage columns.

    Args:
        df: DataFrame to write.
        table_name: Target table name in DuckDB.
        source_id: Identifier for the data source (e.g. 'iea_2024', 'borderstep_2023').
        version: Version string for this data snapshot (e.g. '2024-01').
        run_id: UUID string for the current pipeline run.
        db_path: Path to the DuckDB database file.
        if_exists: 'append' or 'replace'. Default 'append'.

    Raises:
        ValueError: If df is empty or if_exists is invalid.
    """
    if df.empty:
        raise ValueError(f"Cannot write empty DataFrame to gold table '{table_name}'")
    if if_exists not in ("append", "replace"):
        raise ValueError(f"if_exists must be 'append' or 'replace', got '{if_exists}'")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    enriched = df.copy()
    enriched["source_id"] = source_id
    enriched["ingestion_date"] = date.today().isoformat()
    enriched["version"] = version
    enriched["run_id"] = run_id

    con = duckdb.connect(str(db_path))
    try:
        if if_exists == "replace":
            con.execute(f"DROP TABLE IF EXISTS {table_name}")

        con.execute(
            f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM enriched LIMIT 0"
        )
        con.execute(f"INSERT INTO {table_name} SELECT * FROM enriched")
        row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        logger.info(
            "Wrote %d rows to gold table '%s' (total rows now: %d)",
            len(enriched),
            table_name,
            row_count,
        )
    finally:
        con.close()


def read_gold_table(
    table_name: str,
    db_path: Path = GOLD_DB_PATH,
    filters: dict[str, str | int | float] | None = None,
) -> pd.DataFrame:
    """Read a gold table from DuckDB with optional filters.

    Args:
        table_name: Table name to read.
        db_path: Path to the DuckDB database file.
        filters: Optional dict of column → value equality filters.

    Returns:
        DataFrame with all columns from the gold table.

    Raises:
        FileNotFoundError: If the database file does not exist.
        ValueError: If the table does not exist.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Gold database not found at {db_path}")

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
        if table_name not in tables:
            raise ValueError(f"Table '{table_name}' not found in {db_path}. Available: {tables}")

        query = f"SELECT * FROM {table_name}"
        if filters:
            conditions = " AND ".join(
                f"{col} = '{val}'" if isinstance(val, str) else f"{col} = {val}"
                for col, val in filters.items()
            )
            query += f" WHERE {conditions}"

        df = con.execute(query).df()
        logger.info("Read %d rows from gold table '%s'", len(df), table_name)
        return df
    finally:
        con.close()


def list_gold_tables(db_path: Path = GOLD_DB_PATH) -> list[str]:
    """List all tables in the gold DuckDB database.

    Args:
        db_path: Path to the DuckDB database file.

    Returns:
        List of table names.
    """
    if not db_path.exists():
        return []
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        return [row[0] for row in con.execute("SHOW TABLES").fetchall()]
    finally:
        con.close()
