"""Merge Transformer

Combines senate and assembly transformed DataFrames into unified tables.
"""

import pandas as pd
from loguru import logger as log

from src.transformations.transformation_helpers import (
    more_name_parsing_comma_split_rearrange,
)


def merge_leadership(senate_df: pd.DataFrame, assembly_df: pd.DataFrame) -> dict:
    """Merge transformed senate and assembly leadership into a single table.

    Adds a ``chamber`` column (``'senate'`` / ``'assembly'``) to identify the source.

    Args:
        senate_df: Transformed senate leadership DataFrame.
        assembly_df: Transformed assembly leadership DataFrame.

    Returns:
        Dict with keys:
            - ``status`` (str): ``"success"`` or ``"error"``
            - ``data`` (pd.DataFrame): Merged DataFrame
            - ``row_count`` (int): Number of rows after merge
            - ``message`` (str): Informational message
    """
    try:
        frames = []

        if senate_df is not None and not senate_df.empty:
            senate_copy = senate_df.copy()
            senate_copy.insert(0, "chamber", "senate")
            frames.append(senate_copy)
            log.info(f"merge_leadership: adding {len(senate_copy)} senate rows")
        else:
            log.warning("merge_leadership: senate leadership DataFrame is empty")

        if assembly_df is not None and not assembly_df.empty:
            assembly_copy = assembly_df.copy()
            assembly_copy.insert(0, "chamber", "assembly")
            frames.append(assembly_copy)
            log.info(f"merge_leadership: adding {len(assembly_copy)} assembly rows")
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
    """Merge transformed senate and assembly members into a single table.

    Adds a ``chamber`` column (``'senate'`` / ``'assembly'``) to identify the source.

    Args:
        senate_df: Transformed senate members DataFrame.
        assembly_df: Transformed assembly members DataFrame.

    Returns:
        Dict with keys:
            - ``status`` (str): ``"success"`` or ``"error"``
            - ``data`` (pd.DataFrame): Merged DataFrame
            - ``row_count`` (int): Number of rows after merge
            - ``message`` (str): Informational message
    """
    try:
        frames = []

        if senate_df is not None and not senate_df.empty:
            senate_copy = senate_df.copy()
            senate_copy.insert(0, "chamber", "senate")
            frames.append(senate_copy)
            log.info(f"merge_members: adding {len(senate_copy)} senate rows")
        else:
            log.warning("merge_members: senate members DataFrame is empty")

        if assembly_df is not None and not assembly_df.empty:
            assembly_copy = assembly_df.copy()
            assembly_copy.insert(0, "chamber", "assembly")
            frames.append(assembly_copy)
            log.info(f"merge_members: adding {len(assembly_copy)} assembly rows")
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
