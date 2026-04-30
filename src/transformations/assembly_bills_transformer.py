"""Assembly Bills Transformer

Cleans and standardises the raw assembly bill tracker DataFrame extracted by MinerU.

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
    apply_name_parsing,
    strip_cell_punctuation
)

# Canonical column names matching the assembly bill tracker PDF header
ASSEMBLY_BILL_COLUMNS = [
    "s/no.",
    "bill",
    "sponsor",
    "na/sen. bill no.",
    "dated",
    "maturity date",
    "gazette no.",
    "1st read",
    "2nd read",
    "3rd read",
    "remarks",
    "assent",
]

# Strings that identify repeated header rows to be removed from the data
HEADER_ROW_STRINGS = [
    "S/No/",
    "1STREAD",
    "1stREAD",
    "2NDREAD",
]


def rename_assembly_bill_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to the canonical assembly bill tracker header names.

    The raw DataFrame produced by HTML-table conversion has integer column
    names (0, 1, 2, …).  This function maps those to human-readable names,
    handling DataFrames that have fewer columns than the full header.

    Args:
        df: Raw assembly bills DataFrame.

    Returns:
        DataFrame with renamed columns.
    """
    n_cols = len(df.columns)
    col_map = {old: new for old, new in zip(df.columns, ASSEMBLY_BILL_COLUMNS[:n_cols])}
    log.info(f"Renaming {n_cols} assembly bill columns")
    return df.rename(columns=col_map)


def remove_header_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove repeated header rows that MinerU embeds inside the data.

    Uses :func:`create_mask_for_strings` to flag any row whose ``NO.``
    or ``1ST READ`` column contains one of the known header strings, then
    removes it with :func:`apply_mask_to_dataframe`.

    Args:
        df: Assembly bills DataFrame (columns already renamed).

    Returns:
        Cleaned DataFrame with header rows removed.
    """
    search_cols = [c for c in ["no.", "1st read"] if c in df.columns]
    mask = create_mask_for_strings(
        df,
        search_strings=HEADER_ROW_STRINGS,
        columns=search_cols,
        case_sensitive=False,
    )
    return apply_mask_to_dataframe(df, mask)


def transform_assembly_bills(raw_df: pd.DataFrame) -> dict:
    """Apply all transformations to the raw assembly bills DataFrame.

    Pipeline:
        1. Rename columns.
        2. Remove repeated header rows.
        3. Merge spill rows and duplicate serial rows.

    Args:
        raw_df: Raw DataFrame from :func:`src.table_builders.assembly_bills_builder.build_assembly_bills`.

    Returns:
        Dict with keys:
            - ``status`` (str): ``"success"`` or ``"error"``
            - ``data`` (pd.DataFrame): Transformed DataFrame
            - ``row_count`` (int): Number of rows after transformation
            - ``message`` (str): Informational message
    """
    try:
        if raw_df is None or raw_df.empty:
            log.warning("transform_assembly_bills: received empty DataFrame")
            return {
                "status": "success",
                "data": pd.DataFrame(),
                "row_count": 0,
                "message": "No assembly bills data to transform",
            }

        log.info(f"Transforming assembly bills: {len(raw_df)} raw rows")

        df = rename_assembly_bill_columns(raw_df.copy())
        df = remove_header_rows(df)
        
        log.debug(f"columns at this stage: {df.columns.tolist()}")
        
        df = merge_duplicate_serial_rows(df, serial_col="s/no.")
        df = merge_spill_rows(df, serial_col="s/no.")
        
        df["sponsor"] = apply_name_parsing(df, columns=["sponsor"])["sponsor"]
        df = strip_cell_punctuation(df)

        row_count = len(df)
        log.info(f"Assembly bills transformation complete: {row_count} rows retained")

        return {
            "status": "success",
            "data": df,
            "row_count": row_count,
            "message": f"Transformed {row_count} assembly bill records",
        }
    except Exception as e:
        log.error(f"Assembly bills transformation failed: {e}")
        return {
            "status": "error",
            "data": pd.DataFrame(),
            "row_count": 0,
            "message": str(e),
        }
