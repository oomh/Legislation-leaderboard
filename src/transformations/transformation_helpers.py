"""Transformation Helpers

Utility functions for transforming and cleaning extracted table data.
"""

import pandas as pd
from typing import List
from loguru import logger as log


def create_mask_for_strings(
    df: pd.DataFrame,
    search_strings: List[str],
    columns: List[str] | None = None,
    case_sensitive: bool = False,
) -> pd.Series:
    """Create a boolean mask for rows containing specified strings.

    Creates a mask where True indicates a row should be removed (contains search strings),
    and False indicates a row should be kept.

    Args:
        df: Input DataFrame to analyze
        search_strings: List of strings to search for
        columns: Specific columns to search in. If None, searches all columns.
        case_sensitive: Whether to perform case-sensitive matching (default: False)

    Returns:
        pd.Series: Boolean mask where True = remove row, False = keep row

    Example:
        >>> df = pd.DataFrame({
        ...     'Bill': ['HB 1', 'Bill', 'HB 2'],
        ...     'Status': ['Passed', 'Status', 'Failed']
        ... })
        >>> mask = create_mask_for_strings(df, ['Bill', 'Status'])
        >>> mask
        0    False
        1     True
        2    False
    """
    if df.empty:
        log.warning("Cannot create mask on empty DataFrame")
        return pd.Series([False] * len(df), index=df.index)

    log.info(f"Creating mask for rows containing strings: {search_strings}")

    # Determine which columns to search
    cols_to_search = columns if columns else df.columns.tolist()

    # Start with all False (no rows to remove)
    mask = pd.Series([False] * len(df), index=df.index)

    # For each search string, mark rows that contain it
    for search_str in search_strings:
        for col in cols_to_search:
            if col not in df.columns:
                log.warning(f"Column {col} not found in DataFrame")
                continue

            # Convert column to string for comparison
            col_str = df[col].astype(str)

            if case_sensitive:
                matches = col_str.str.contains(search_str, na=False, regex=False)
            else:
                matches = col_str.str.lower().str.contains(
                    search_str.lower(), na=False, regex=False
                )

            # Update mask: mark matching rows as True (to be removed)
            mask = mask | matches

    return mask


def apply_mask_to_dataframe(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    """Delete rows where mask is True.

    Args:
        df: Input DataFrame
        mask: Boolean mask where True = remove row, False = keep row

    Returns:
        pd.DataFrame: DataFrame with masked rows removed

    Example:
        >>> df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        >>> mask = pd.Series([False, True, False])
        >>> result = apply_mask_to_dataframe(df, mask)
        >>> len(result)
        2
    """
    rows_removed = mask.sum()
    rows_kept = (~mask).sum()

    log.info(f"Applying mask: removing {rows_removed} rows, keeping {rows_kept} rows")

    return df[~mask].reset_index(drop=True)


def remove_duplicate_header_rows(
    df: pd.DataFrame,
    header_indicators: List[str],
    columns: List[str] | None = None,
) -> pd.DataFrame:
    """Remove rows that match header indicator strings.

    Args:
        df: Input DataFrame
        header_indicators: List of strings that indicate a header row to be removed (required)
        columns: Specific columns to search in. If None, searches all columns.

    Returns:
        pd.DataFrame: DataFrame with header-like rows removed

    Example:
        >>> df = pd.DataFrame({
        ...     'Bill': ['HB 1', 'Bill', 'HB 2'],
        ...     'Status': ['Passed', 'Status', 'Failed']
        ... })
        >>> result = remove_duplicate_header_rows(df, ['Bill', 'Status'])
        >>> len(result)
        2
    """
    if df.empty:
        return df

    log.info(f"Removing duplicate header rows with indicators: {header_indicators}")

    mask = create_mask_for_strings(
        df, header_indicators, columns=columns, case_sensitive=False
    )
    return apply_mask_to_dataframe(df, mask)
