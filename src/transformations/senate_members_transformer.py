"""Senate Members Transformer

Cleans and standardises the senate members DataFrame scraped from parliament.go.ke.

Steps:
1. Parse the ``name`` column to remove titles and post-nominal letters.
"""

import pandas as pd
from loguru import logger as log

from src.transformations.transformation_helpers import apply_name_parsing, strip_cell_punctuation


def transform_senate_members(raw_df: pd.DataFrame) -> dict:
    """Apply all transformations to the raw senate members DataFrame.

    Pipeline:
        1. Parse names in the ``name`` column.

    Args:
        raw_df: Raw DataFrame from the senate members scraper.

    Returns:
        Dict with keys:
            - ``status`` (str): ``"success"`` or ``"error"``
            - ``data`` (pd.DataFrame): Transformed DataFrame
            - ``row_count`` (int): Number of rows after transformation
            - ``message`` (str): Informational message
    """
    try:
        if raw_df is None or raw_df.empty:
            log.warning("transform_senate_members: received empty DataFrame")
            return {
                "status": "success",
                "data": pd.DataFrame(),
                "row_count": 0,
                "message": "No senate members data to transform",
            }

        log.info(f"Transforming senate members: {len(raw_df)} rows")

        df = apply_name_parsing(raw_df.copy(), ["name"])
        df = strip_cell_punctuation(df)

        row_count = len(df)
        log.info(f"Senate members transformation complete: {row_count} rows")

        return {
            "status": "success",
            "data": df,
            "row_count": row_count,
            "message": f"Transformed {row_count} senate member records",
        }
    except Exception as e:
        log.error(f"Senate members transformation failed: {e}")
        return {
            "status": "error",
            "data": pd.DataFrame(),
            "row_count": 0,
            "message": str(e),
        }
