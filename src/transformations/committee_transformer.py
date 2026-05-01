"""Committee Transformer

Cleans and standardises the committee leadership DataFrame extracted by MinerU.

Steps:
1. Parse the ``member_name`` column to remove titles and post-nominal letters.
"""

import pandas as pd
from loguru import logger as log

from src.transformations.transformation_helpers import (
    apply_name_parsing,
    strip_cell_punctuation,
)


def transform_committees(raw_df: pd.DataFrame) -> dict:
    """Apply all transformations to the raw committee leadership DataFrame.

    Pipeline:
        1. Parse names in the ``member_name`` column.

    Args:
        raw_df: Raw DataFrame from the committee leadership table builder.

    Returns:
        Dict with keys:
            - ``status`` (str): ``"success"`` or ``"error"``
            - ``data`` (pd.DataFrame): Transformed DataFrame
            - ``row_count`` (int): Number of rows after transformation
            - ``message`` (str): Informational message
    """
    try:
        if raw_df is None or raw_df.empty:
            log.warning("transform_committees: received empty DataFrame")
            return {
                "status": "success",
                "data": pd.DataFrame(),
                "row_count": 0,
                "message": "No committee data to transform",
            }

        log.info(f"Transforming committees: {len(raw_df)} rows")

        df = apply_name_parsing(raw_df.copy(), ["member_name"])
        df = strip_cell_punctuation(df)

        row_count = len(df)
        log.info(f"Committee transformation complete: {row_count} rows")

        return {
            "status": "success",
            "data": df,
            "row_count": row_count,
            "message": f"Transformed {row_count} committee records",
        }
    except Exception as e:
        log.error(f"Committee transformation failed: {e}")
        return {
            "status": "error",
            "data": pd.DataFrame(),
            "row_count": 0,
            "message": str(e),
        }
