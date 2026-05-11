"""Committee Transformer

Cleans and standardises the committee leadership DataFrame extracted by MinerU.

Steps:
1. Parse the ``member_name`` column to remove titles and post-nominal letters.
"""

import re

import pandas as pd
from loguru import logger as log

from src.transformations.transformation_helpers import (
    apply_name_parsing,
    more_name_parsing_comma_split_rearrange,
    strip_cell_punctuation,
)

# Matches any leftover role text that survived name parsing, e.g. ", -chairperson"
# or "- vice-chairperson". The leading comma, dash and surrounding spaces are
# all optional because they appear in different combinations in the raw data.
_ROLE_SUFFIX_RE = re.compile(
    r",?\s*[-\u2013]?\s*(?:vice[-\s]chairperson|chairperson|vice[-\s]chair|chair)\b.*$",
    re.IGNORECASE,
)


def _strip_role_from_member_name(df: pd.DataFrame) -> pd.DataFrame:
    """Remove any lingering chairperson/vice-chairperson suffixes from member_name.

    This is a fallback for rows where the position extractor in the table builder
    could not detect the role (e.g. inconsistent hyphen spacing in the source PDF).

    Args:
        df: DataFrame containing a ``member_name`` column.

    Returns:
        Copy of the DataFrame with role suffixes removed from ``member_name``.
    """
    if "member_name" not in df.columns:
        return df

    df = df.copy()
    before = df["member_name"].copy()
    df["member_name"] = df["member_name"].apply(
        lambda v: _ROLE_SUFFIX_RE.sub("", v).strip().strip(",").strip()
        if isinstance(v, str)
        else v
    )
    changed = (df["member_name"] != before).sum()
    if changed:
        log.info(f"Stripped residual role suffixes from {changed} member_name value(s)")
    return df


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
        df = _strip_role_from_member_name(df)
        df["member_name"] = df["member_name"].apply(more_name_parsing_comma_split_rearrange)
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
