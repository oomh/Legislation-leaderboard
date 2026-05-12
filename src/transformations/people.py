"""People Transformers and Mergers

Transforms leadership, members, and committee DataFrames, and merges
the per-chamber results into combined DataFrames.

Public API
----------
Transformers:
    transform_senate_leadership(raw_df)   -> result dict
    transform_assembly_leadership(raw_df) -> result dict
    transform_senate_members(raw_df)      -> result dict
    transform_assembly_members(raw_df)    -> result dict
    transform_committees(raw_df)          -> result dict

Mergers:
    merge_leadership(senate_df, assembly_df) -> result dict
    merge_members(senate_df, assembly_df)    -> result dict
"""

import re

import pandas as pd
from loguru import logger as log

from src.transformations.transformation_helpers import (
    apply_name_parsing,
    more_name_parsing_comma_split_rearrange,
    strip_cell_punctuation,
)

# ── Private helpers ────────────────────────────────────────────────────────────

# Strips trailing role suffixes such as "- Vice-Chairperson, Finance" that OCR
# sometimes attaches to the member_name column.
_ROLE_SUFFIX_RE = re.compile(
    r",?\s*[-\u2013]?\s*(?:vice[-\s]chairperson|chairperson|vice[-\s]chair|chair)\b.*$",
    re.IGNORECASE,
)


def _strip_role_from_member_name(df: pd.DataFrame) -> pd.DataFrame:
    if "member_name" not in df.columns:
        return df
    df = df.copy()
    before = df["member_name"].copy()
    df["member_name"] = df["member_name"].apply(
        lambda v: (
            _ROLE_SUFFIX_RE.sub("", v).strip().strip(",").strip()
            if isinstance(v, str)
            else v
        )
    )
    changed = (df["member_name"] != before).sum()
    if changed:
        log.info(f"Stripped residual role suffixes from {changed} member_name value(s)")
    return df


# ── Transformers ───────────────────────────────────────────────────────────────


def transform_senate_leadership(raw_df: pd.DataFrame) -> dict:
    """Transform the raw senate leadership DataFrame.

    Returns:
        Dict with keys: status, data (pd.DataFrame), row_count, message.
    """
    try:
        if raw_df is None or raw_df.empty:
            log.warning("transform_senate_leadership: received empty DataFrame")
            return {
                "status": "success",
                "data": pd.DataFrame(),
                "row_count": 0,
                "message": "No senate leadership data to transform",
            }
        log.info(f"Transforming senate leadership: {len(raw_df)} rows")
        df = apply_name_parsing(raw_df.copy(), ["person"])
        df = strip_cell_punctuation(df)
        row_count = len(df)
        log.info(f"Senate leadership transformation complete: {row_count} rows")
        return {
            "status": "success",
            "data": df,
            "row_count": row_count,
            "message": f"Transformed {row_count} senate leadership records",
        }
    except Exception as e:
        log.error(f"Senate leadership transformation failed: {e}")
        return {
            "status": "error",
            "data": pd.DataFrame(),
            "row_count": 0,
            "message": str(e),
        }


def transform_assembly_leadership(raw_df: pd.DataFrame) -> dict:
    """Transform the raw assembly leadership DataFrame.

    Returns:
        Dict with keys: status, data (pd.DataFrame), row_count, message.
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


def transform_senate_members(raw_df: pd.DataFrame) -> dict:
    """Transform the raw senate members DataFrame.

    Returns:
        Dict with keys: status, data (pd.DataFrame), row_count, message.
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


def transform_assembly_members(raw_df: pd.DataFrame) -> dict:
    """Transform the raw assembly members DataFrame.

    Returns:
        Dict with keys: status, data (pd.DataFrame), row_count, message.
    """
    try:
        if raw_df is None or raw_df.empty:
            log.warning("transform_assembly_members: received empty DataFrame")
            return {
                "status": "success",
                "data": pd.DataFrame(),
                "row_count": 0,
                "message": "No assembly members data to transform",
            }
        log.info(f"Transforming assembly members: {len(raw_df)} rows")
        df = apply_name_parsing(raw_df.copy(), ["name"])
        df = strip_cell_punctuation(df)
        df["name"] = df["name"].apply(more_name_parsing_comma_split_rearrange)
        row_count = len(df)
        log.info(f"Assembly members transformation complete: {row_count} rows")
        return {
            "status": "success",
            "data": df,
            "row_count": row_count,
            "message": f"Transformed {row_count} assembly member records",
        }
    except Exception as e:
        log.error(f"Assembly members transformation failed: {e}")
        return {
            "status": "error",
            "data": pd.DataFrame(),
            "row_count": 0,
            "message": str(e),
        }


def transform_committees(raw_df: pd.DataFrame) -> dict:
    """Transform the raw committee membership DataFrame.

    Returns:
        Dict with keys: status, data (pd.DataFrame), row_count, message.
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
        df["member_name"] = df["member_name"].apply(
            more_name_parsing_comma_split_rearrange
        )
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


# ── Mergers ────────────────────────────────────────────────────────────────────


def merge_leadership(senate_df: pd.DataFrame, assembly_df: pd.DataFrame) -> dict:
    """Concatenate senate and assembly leadership DataFrames with a 'chamber' column.

    Returns:
        Dict with keys: status, data (pd.DataFrame), row_count, message.
    """
    try:
        frames: list[pd.DataFrame] = []
        if senate_df is not None and not senate_df.empty:
            s = senate_df.copy()
            s.insert(0, "chamber", "senate")
            frames.append(s)
            log.info(f"merge_leadership: adding {len(s)} senate rows")
        else:
            log.warning("merge_leadership: senate leadership DataFrame is empty")

        if assembly_df is not None and not assembly_df.empty:
            a = assembly_df.copy()
            a.insert(0, "chamber", "assembly")
            frames.append(a)
            log.info(f"merge_leadership: adding {len(a)} assembly rows")
        else:
            log.warning("merge_leadership: assembly leadership DataFrame is empty")

        if not frames:
            return {
                "status": "success",
                "data": pd.DataFrame(),
                "row_count": 0,
                "message": "No leadership data to merge",
            }

        merged = pd.concat(frames, ignore_index=True)
        row_count = len(merged)
        log.info(f"Leadership merge complete: {row_count} rows")
        return {
            "status": "success",
            "data": merged,
            "row_count": row_count,
            "message": f"Merged {row_count} leadership records",
        }
    except Exception as e:
        log.error(f"Leadership merge failed: {e}")
        return {
            "status": "error",
            "data": pd.DataFrame(),
            "row_count": 0,
            "message": str(e),
        }


def merge_members(senate_df: pd.DataFrame, assembly_df: pd.DataFrame) -> dict:
    """Concatenate senate and assembly member DataFrames with a 'chamber' column.

    Returns:
        Dict with keys: status, data (pd.DataFrame), row_count, message.
    """
    try:
        frames: list[pd.DataFrame] = []
        if senate_df is not None and not senate_df.empty:
            s = senate_df.copy()
            s.insert(0, "chamber", "senate")
            frames.append(s)
            log.info(f"merge_members: adding {len(s)} senate rows")
        else:
            log.warning("merge_members: senate members DataFrame is empty")

        if assembly_df is not None and not assembly_df.empty:
            a = assembly_df.copy()
            a.insert(0, "chamber", "assembly")
            frames.append(a)
            log.info(f"merge_members: adding {len(a)} assembly rows")
        else:
            log.warning("merge_members: assembly members DataFrame is empty")

        if not frames:
            return {
                "status": "success",
                "data": pd.DataFrame(),
                "row_count": 0,
                "message": "No members data to merge",
            }

        merged = pd.concat(frames, ignore_index=True)
        merged["name"] = merged["name"].apply(more_name_parsing_comma_split_rearrange)
        row_count = len(merged)
        log.info(f"Members merge complete: {row_count} rows")
        return {
            "status": "success",
            "data": merged,
            "row_count": row_count,
            "message": f"Merged {row_count} member records",
        }
    except Exception as e:
        log.error(f"Members merge failed: {e}")
        return {
            "status": "error",
            "data": pd.DataFrame(),
            "row_count": 0,
            "message": str(e),
        }
