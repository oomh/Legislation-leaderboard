"""Senate Bills Transformer

Cleans and standardises the raw senate bill tracker DataFrame extracted by MinerU.

Steps:
1. Rename generic numeric columns to proper header names.
2. Mask and remove repeated header rows embedded in the data.
3. Drop rows that are entirely empty after cleaning.
"""

import pandas as pd
from loguru import logger as log

from src.transformations.transformation_helpers import (
    apply_mask_to_dataframe,
    create_mask_for_strings,
    merge_spill_rows,
    merge_duplicate_serial_rows,
    strip_cell_punctuation,
    apply_name_parsing,
)

# Canonical column names matching the senate bill tracker PDF header
SENATE_BILL_COLUMNS = [
    "no.",
    "bill",
    "sponsor",
    "gazette no.",
    "date of publication",
    "maturity",
    "date 1st read",
    "sc committee referred to",
    "date 2nd read",
    "cotw/ 3rd read",
    "date of assent",
    "remarks",
]

# Strings that identify repeated header rows to be removed from the data
HEADER_ROW_STRINGS = [
    "no.",
    # "bill",
    # "sponsor",
    # "gazette no.",
    # "date of publication",
    # "maturity",
    # "date 1st read",
    "sc committee referred to",
    # "date 2nd read",
    # "date of assent",
    # "remarks",
]


def rename_senate_bill_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to the canonical senate bill tracker header names.

    The raw DataFrame produced by HTML-table conversion has integer column
    names (0, 1, 2, …).  This function maps those to human-readable names,
    handling DataFrames that have fewer columns than the full header.

    Args:
        df: Raw senate bills DataFrame.

    Returns:
        DataFrame with renamed columns.
    """
    n_cols = len(df.columns)
    col_map = {old: new for old, new in zip(df.columns, SENATE_BILL_COLUMNS[:n_cols])}
    log.info(f"Renaming {n_cols} senate bill columns")
    return df.rename(columns=col_map)


def remove_header_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove repeated header rows that MinerU embeds inside the data.

    Uses :func:`create_mask_for_strings` to flag any row whose ``NO.``
    column contains one of the known header strings, then removes it with
    :func:`apply_mask_to_dataframe`.

    Args:
        df: Senate bills DataFrame (columns already renamed).

    Returns:
        Cleaned DataFrame with header rows removed.
    """
    # Search only the first two columns so we don't accidentally drop real data
    search_cols = [c for c in ["no.", "sc committee referred to"] if c in df.columns]
    mask = create_mask_for_strings(
        df,
        search_strings=HEADER_ROW_STRINGS,
        columns=search_cols,
        case_sensitive=False,
    )
    return apply_mask_to_dataframe(df, mask)


def transform_senate_bills(raw_df: pd.DataFrame) -> dict:
    """Apply all transformations to the raw senate bills DataFrame.

    Pipeline:
        1. Rename columns.
        2. Remove repeated header rows.
        3. Drop fully-empty rows.

    Args:
        raw_df: Raw DataFrame from :func:`src.table_builders.senate_bills_builder.build_senate_bills`.

    Returns:
        Dict with keys:
            - ``status`` (str): ``"success"`` or ``"error"``
            - ``data`` (pd.DataFrame): Transformed DataFrame
            - ``row_count`` (int): Number of rows after transformation
            - ``message`` (str): Informational message
    """
    try:
        if raw_df is None or raw_df.empty:
            log.warning("transform_senate_bills: received empty DataFrame")
            return {
                "status": "success",
                "data": pd.DataFrame(),
                "row_count": 0,
                "message": "No senate bills data to transform",
            }

        log.info(f"Transforming senate bills: {len(raw_df)} raw rows")

        df = rename_senate_bill_columns(raw_df.copy())
        df = remove_header_rows(df)
        df = merge_spill_rows(
            df,
            serial_col="no.",
        )
        df = merge_duplicate_serial_rows(df, serial_col="no.")
        df["sponsor"] = apply_name_parsing(df, columns=["sponsor"])["sponsor"]
        df = strip_cell_punctuation(df)

        row_count = len(df)

        log.info(f"Senate bills transformation complete: {row_count} rows retained")

        return {
            "status": "success",
            "data": df,
            "row_count": row_count,
            "message": f"Transformed {row_count} senate bill records",
        }
    except Exception as e:
        log.error(f"Senate bills transformation failed: {e}")
        return {
            "status": "error",
            "data": pd.DataFrame(),
            "row_count": 0,
            "message": str(e),
        }
