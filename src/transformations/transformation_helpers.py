"""Transformation Helpers

Utility functions for transforming and cleaning extracted table data.
"""

import re
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


def fix_shifted_serial_rows(
    df: pd.DataFrame, serial_col: str = "s/no."
) -> pd.DataFrame:
    """Fix rows where a leading empty cell has shifted the serial number one column right.

    Occurs when the PDF/HTML produces a spurious empty leading cell, so the serial number
    lands in the BILL column and every subsequent value is one position off.

    This must run after column renaming and before merge_spill_rows, because
    merge_spill_rows would incorrectly treat the empty serial column as a spill row.

    Args:
        df: DataFrame with columns already renamed to canonical names.
        serial_col: Column name that should contain serial numbers.

    Returns:
        DataFrame with shifted rows corrected.
    """
    if serial_col not in df.columns:
        log.warning(
            f"fix_shifted_serial_rows: column '{serial_col}' not found, skipping"
        )
        return df

    cols = list(df.columns)
    serial_idx = cols.index(serial_col)
    if serial_idx + 1 >= len(cols):
        return df

    next_col = cols[serial_idx + 1]
    df = df.copy()

    serial_empty = df[serial_col].isna() | (
        df[serial_col].astype(str).str.strip() == ""
    )
    next_is_serial = df[next_col].astype(str).str.strip().str.fullmatch(r"\d+\.?\s*")
    shifted_mask = serial_empty & next_is_serial

    count = int(shifted_mask.sum())
    if count == 0:
        return df

    log.info(f"Fixing {count} shifted serial row(s) in column '{serial_col}'")

    segment = cols[serial_idx:]
    for idx in df[shifted_mask].index:
        vals = df.loc[idx, segment].tolist()
        new_vals = vals[1:] + [""]
        for col, val in zip(segment, new_vals):
            df.loc[idx, col] = val

    return df


def merge_spill_rows(df, serial_col="s/no/"):
    """
    Merge rows that spilled into next row (no serial number).
    Occurs when table cells wrap to multiple lines in PDF.

    Args:
        df: DataFrame with potential spill rows
        serial_col: Column name containing serial numbers

    Returns:
        DataFrame with spill rows merged into previous row
    """
    df = df.copy()

    spill_mask = df[serial_col].isna() | (df[serial_col].astype(str).str.strip() == "")

    for i in df[spill_mask].index:
        prev = i - 1
        if prev in df.index:
            for col in df.columns:
                curr_val = str(df.loc[i, col]).strip()
                if curr_val and curr_val != "nan":
                    prev_val = str(df.loc[prev, col]).strip()
                    df.loc[prev, col] = (
                        (prev_val + " " + curr_val).strip()
                        if prev_val != "nan"
                        else curr_val
                    )

    return df[~spill_mask].reset_index(drop=True)


def merge_duplicate_serial_rows(df, serial_col="", separator=" "):
    """
    Merge rows that share the same serial number into a single row.

    Occurs when a PDF table row spans multiple rows due to cell content wrapping
    across pages or columns. Unlike merge_spill_rows (which handles rows with no
    serial), this handles rows where the serial is explicitly repeated.

    For each group of rows sharing a serial number:
    - Columns with identical values are kept as-is
    - Columns with differing values are concatenated using the separator

    Args:
        df: DataFrame with potential duplicate serial rows
        serial_col: Column name containing serial numbers (default: "s/no/")
        separator: String used to join differing cell values (default: " ")

    Returns:
        pd.DataFrame: DataFrame with duplicate serial rows merged into single rows

    Example:
        >>> df = pd.DataFrame({
        ...     's/no/': ['97.', '97.', '97.'],
        ...     'Bill': ['Bill A', 'Bill A', 'Bill A'],
        ...     'Remarks': ['Note 1', 'Note 2', 'Note 3'],
        ... })
        >>> result = merge_duplicate_serial_rows(df)
        >>> len(result)
        1
        >>> result.loc[0, 'Remarks']
        'Note 1 Note 2 Note 3'
    """
    if df.empty:
        return df

    log.info(f"Merging duplicate serial rows on column: {serial_col}")

    rows_before = len(df)
    merged_rows = []
    serial_to_idx = {}  # serial value -> position in merged_rows

    for _, row in df.iterrows():
        serial = str(row[serial_col]).strip()

        # Skip rows with no serial — use merge_spill_rows for those
        if not serial or serial == "nan":
            merged_rows.append(row.to_dict())
            continue

        if serial in serial_to_idx:
            idx = serial_to_idx[serial]
            for col in df.columns:
                curr = str(row[col]).strip()
                prev = str(merged_rows[idx][col]).strip()

                # Nothing to add
                if not curr or curr == "nan" or curr == prev:
                    continue

                merged_rows[idx][col] = (
                    (prev + separator + curr).strip()
                    if prev and prev != "nan"
                    else curr
                )
        else:
            serial_to_idx[serial] = len(merged_rows)
            merged_rows.append(row.to_dict())

    result = pd.DataFrame(merged_rows).reset_index(drop=True)
    log.info(f"Merged {rows_before} rows into {len(result)} rows")
    return result


_PUNCT_STRIP = re.compile(r"^[\s,;.\-/|]+|[\s,;.\-/|]+$")


def strip_cell_punctuation(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading/trailing punctuation and whitespace from all string cells.

    Removes characters in the set ``[ , ; . - / | ]`` from the start and end
    of every string-valued cell. Non-string values are left untouched.

    Args:
        df: Input DataFrame.

    Returns:
        Copy of DataFrame with cells cleaned.
    """

    def _clean(val):
        if not isinstance(val, str):
            return val
        return _PUNCT_STRIP.sub("", val).strip()

    return df.map(_clean)


_NAME_STRIP_PARTS = [
    "the rt.",
    "rt. hon.",
    "the hon.",
    "the hon",
    "rt. hon",
    "hon.",
    "hon ",
    "(amb.)",
    "(amb)",
    "the hon. ",
    "the hon ",
    "hon.",
    "sen. ",
    "sen.",
    "m.p.",
    ", m.p.",
    ",m.p",
    " m.p",
    " mp,",
    " mp",
    ",mp",
    ", mp",
    " cbs",
    ", cbs",
    ",cbs",
    ", egh",
    ", mgh",
    ", ebs",
    " cs",
    "cs",
    ", cs",
    "gk",
    ", sc",
    "(dr)",
    "(dr.)",
    "(eng)",
    "(eng.)",
    "(cpa)",
    "(cpa.)",
    "(prof)",
    "(prof.)",
    "prof.",
    "(rtd)",
    "(rtd.)",
    "(co-sponsor)",
    "co-sponsor",
    "hsc",
    "capt.",
    "dsm",
    "1",
    "(",
    ")",
    ";",
    ":",
    ", ogw",
    ",ogw",
]


def apply_name_parsing(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """Strip legislative titles and post-nominals from name columns, then title-case.

    Args:
        df: Input DataFrame.
        columns: Column names to clean. Missing columns are skipped.

    Returns:
        Copy of DataFrame with specified columns cleaned.
    """

    def _clean(name: str) -> str:
        if not isinstance(name, str):
            return name
        result = name.lower().strip()
        for part in _NAME_STRIP_PARTS:
            result = result.replace(part, " ")
        return re.sub(r"\s+", " ", result).strip().strip(",").strip().title()

    df = df.copy()
    for col in columns:
        if col not in df.columns:
            log.warning(f"apply_name_parsing: column '{col}' not found, skipping")
            continue
        log.info(f"Parsing names in column '{col}'")
        df[col] = df[col].apply(_clean)
    return df


def more_name_parsing_comma_split_rearrange(name: str) -> str:
    """Handle names in "Last, First" format by splitting on comma and rearranging.

    NOTE TO SELF: use after apply_name_parsing, which already handles titles and post-nominals. while merging the senate and assembly members.

    If the name contains a comma, assumes format is "Last, First" and rearranges
    to "First Last". If no comma is present, returns the name unchanged.

    Args:
        name: Input name string.
    Returns:
        Cleaned name string with "Last, First" rearranged to "First Last".
    """
    if not isinstance(name, str):
        return name
    if "," in name:
        parts = [part.strip() for part in name.split(",")]
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}"
    return name.strip()
