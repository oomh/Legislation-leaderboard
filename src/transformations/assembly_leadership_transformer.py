"""Assembly Leadership Transformer

Cleans and standardises the assembly leadership DataFrame scraped from parliament.go.ke.

Steps:
1. Parse the ``person`` column to remove titles and post-nominal letters.
"""

import pandas as pd
from loguru import logger as log

from src.transformations.transformation_helpers import (
    apply_name_parsing,
    strip_cell_punctuation,
)


def transform_assembly_leadership(raw_df: pd.DataFrame) -> dict:
    """Apply all transformations to the raw assembly leadership DataFrame.

    Pipeline:
        1. Parse names in the ``person`` column.

    Args:
        raw_df: Raw DataFrame from the assembly leadership scraper.

    Returns:
        Dict with keys:
            - ``status`` (str): ``"success"`` or ``"error"``
            - ``data`` (pd.DataFrame): Transformed DataFrame
            - ``row_count`` (int): Number of rows after transformation
            - ``message`` (str): Informational message
    """
    try:
        if raw_df is None or raw_df.empty:
            log.warning("transform_assembly_leadership: received empty DataFrame")
            return {
                "status": "success",
                "data": pd.DataFrame(),
                "row_count": 0,
                "message": "No assembly leadership data to transform",
            }

        log.info(f"Transforming assembly leadership: {len(raw_df)} rows")

        df = apply_name_parsing(raw_df.copy(), ["person"])
        df = strip_cell_punctuation(df)

        row_count = len(df)
        log.info(f"Assembly leadership transformation complete: {row_count} rows")

        return {
            "status": "success",
            "data": df,
            "row_count": row_count,
            "message": f"Transformed {row_count} assembly leadership records",
        }
    except Exception as e:
        log.error(f"Assembly leadership transformation failed: {e}")
        return {
            "status": "error",
            "data": pd.DataFrame(),
            "row_count": 0,
            "message": str(e),
        }
