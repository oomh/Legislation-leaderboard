"""Step 7 — Neon Database Push

Pushes the four Step 6 output tables to Neon PostgreSQL.

For each table the step:
    1. Reads the corresponding ``src/database/sql/<table>.sql`` file and executes it
        to ensure the table exists (CREATE TABLE IF NOT EXISTS).
    2. Truncates the table so the push is always a full refresh.
    3. Batch-inserts all rows using ``executemany``.

Tables pushed (from ``store.step6_results``):
  - senate_bills        <- senate_bills_final
  - assembly_bills      <- assembly_bills_final
  - leadership          <- merged_leadership
  - members             <- merged_members
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger as log

from src.database import get_cursor

_SQL_DIR = Path(__file__).parent.parent / "database" / "sql"

# Maps store key -> (sql_file_stem, table_name, expected_columns)
_TABLE_CONFIG: list[tuple[str, str, list[str] | None]] = [
    (
        "senate_bills_final",
        "senate_bills",
        [
            "serial_number", "bill_name", "sponsor",
            "bill_house", "bill_number", "bill_year",
            "gazette_number", "dated", "maturity_date",
            "first_reading", "assent_date", "gazette_period", "assent_period",
        ],
    ),
    (
        "assembly_bills_final",
        "assembly_bills",
        [
            "serial_number", "bill_name", "sponsor",
            "bill_house", "bill_number", "bill_year",
            "gazette_number", "dated", "maturity_date",
            "first_reading", "assent_date", "gazette_period", "assent_period",
        ],
    ),
    ("merged_leadership", "leadership", ["chamber", "office", "person"]),
    ("merged_members", "members", ["chamber", "name", "county", "constituency", "party", "status", "profile_url"]),
]


# ── Private helpers ────────────────────────────────────────────────────────────


def _load_sql(table_name: str) -> str:
    """Read the DDL file for a table from src/database/sql/."""
    path = _SQL_DIR / f"{table_name}.sql"
    return path.read_text(encoding="utf-8")


def _df_to_rows(df: pd.DataFrame, columns: list[str]) -> list[tuple]:
    """
    Select ``columns`` from ``df`` and convert each row to a plain Python tuple.

    pandas NA/NaT values become None so psycopg can map them to SQL NULL.
    """
    subset = df.reindex(columns=columns)
    clean = subset.where(subset.notna(), other=None)
    return [tuple(row) for row in clean.itertuples(index=False, name=None)]


def _push_table(cursor, store_result: dict, table_name: str, columns: list[str]) -> dict:
    """
    Create, truncate, and populate a single table.

    Returns:
        dict with keys: status, row_count, message.
    """
    df: pd.DataFrame = store_result.get("data", pd.DataFrame())
    if df is None or df.empty:
        log.warning(f"step7: skipping {table_name} — no data available")
        return {"status": "skipped", "row_count": 0, "message": "No data to push"}

    ddl = _load_sql(table_name)
    cursor.execute(ddl)
    log.info(f"step7: ensured table {table_name} exists")

    cursor.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY")
    log.info(f"step7: truncated {table_name}")

    rows = _df_to_rows(df, columns)
    cols_sql = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    insert_sql = f"INSERT INTO {table_name} ({cols_sql}) VALUES ({placeholders})"

    cursor.executemany(insert_sql, rows)
    row_count = len(rows)
    log.info(f"step7: inserted {row_count} rows into {table_name}")

    return {
        "status": "success",
        "row_count": row_count,
        "message": f"Inserted {row_count} rows into {table_name}",
    }


# ── Public API ─────────────────────────────────────────────────────────────────


def run_neon_push(store) -> dict:
    """
    Push all Step 6 output tables to Neon PostgreSQL.

    Args:
        store: PipelineStore instance with ``step6_results`` populated.

    Returns:
        dict with keys: status, tables (per-table result dicts), message.
    """
    step6 = store.step6_results
    if not step6:
        log.warning("step7: step6_results is empty — nothing to push")
        return {
            "status": "error",
            "tables": {},
            "message": "Step 6 results are empty. Run Step 6 first.",
        }

    table_results: dict[str, dict] = {}
    failed: list[str] = []

    try:
        with get_cursor() as cursor:
            for store_key, table_name, columns in _TABLE_CONFIG:
                store_result = step6.get(store_key, {})
                result = _push_table(cursor, store_result, table_name, columns)
                table_results[table_name] = result
                if result["status"] == "error":
                    failed.append(table_name)

    except Exception as e:
        log.error(f"step7: database push failed: {e}")
        return {
            "status": "error",
            "tables": table_results,
            "message": str(e),
        }

    if failed:
        message = f"Push completed with errors on: {', '.join(failed)}"
        status = "partial"
    else:
        pushed = [t for t, r in table_results.items() if r["status"] == "success"]
        message = f"Successfully pushed {len(pushed)} table(s): {', '.join(pushed)}"
        status = "success"

    log.info(f"step7: {message}")
    return {
        "status": status,
        "tables": table_results,
        "message": message,
    }
