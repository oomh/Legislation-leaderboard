"""
Helper functions for building and processing legislative tables.

This module contains utility functions for extracting, filtering, and processing
table data from JSON files and other sources used in the table builders.
"""

import json
import logging
from io import StringIO
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)


def extract_tables_from_json(json_file_path: str) -> List[Dict[str, Any]]:
    """
    Extract table objects from a JSON file based on specific filtering criteria.

    This function loads a JSON file, scans for table objects, and filters them based on:
    - type equals 'table'
    - image_source.path length greater than 'image/' (length > 7)
    - html content length greater than 0

    Args:
        json_file_path (str): Path to the JSON file to process.

    Returns:
        List[Dict[str, Any]]: List of filtered table objects that meet the criteria.

    Raises:
        FileNotFoundError: If the specified JSON file does not exist.
        json.JSONDecodeError: If the JSON file is invalid or cannot be parsed.

    Example:
        >>> tables = extract_tables_from_json('data/mineru_output_bill_tracker_senate/content_list_v2.json')
        >>> print(f"Found {len(tables)} tables")
    """
    try:
        json_path = Path(json_file_path)

        if not json_path.exists():
            logger.error(f"JSON file not found: {json_file_path}")
            raise FileNotFoundError(f"JSON file not found: {json_file_path}")

        # Load the JSON file
        with open(json_path, "r") as f:
            data = json.load(f)

        logger.info(
            f"Loaded JSON file with {len(data)} top-level items from {json_file_path}"
        )

        # Flatten the nested list structure
        all_items = []
        for item_list in data:
            if isinstance(item_list, list):
                all_items.extend(item_list)
            else:
                all_items.append(item_list)

        logger.info(f"Flattened data contains {len(all_items)} total items")

        # Filter tables based on criteria
        filtered_tables = []
        min_path_length = len("image/")

        for item in all_items:
            if item.get("type") == "table":
                content = item.get("content", {})
                image_source = content.get("image_source", {})
                image_path = image_source.get("path", "")
                html_content = content.get("html", "")

                # Apply filters
                if len(image_path) > min_path_length and len(html_content) > 0:
                    filtered_tables.append(item)

        logger.info(
            f"Filtered and found {len(filtered_tables)} tables matching criteria"
        )

        return filtered_tables

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON file {json_file_path}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error processing JSON file {json_file_path}: {str(e)}")
        raise


def convert_html_tables_to_dataframes(
    table_objects: List[Dict[str, Any]],
    min_columns: int | None = None,
) -> List[pd.DataFrame]:
    """
    Convert HTML content from table objects to pandas DataFrames.

    This function takes a list of table objects (extracted from JSON) and converts
    the HTML content of each table into one or more pandas DataFrames using pd.read_html().

    Args:
        table_objects (List[Dict[str, Any]]): List of table objects containing HTML content.
            Each object should have a 'content' key with an 'html' key containing the HTML string.
        min_columns (int | None): If provided, DataFrames with fewer columns than this
            value are discarded. Useful for filtering out spurious small tables that
            MinerU extracts alongside the main bill tracker table.

    Returns:
        List[pd.DataFrame]: List of DataFrames converted from the HTML tables.
            Note: A single HTML may contain multiple tables, so the returned list
            may have more DataFrames than input table objects.

    Example:
        >>> tables = extract_tables_from_json('data/mineru_output_bill_tracker_senate/content_list_v2.json')
        >>> dataframes = convert_html_tables_to_dataframes(tables, min_columns=11)
        >>> print(f"Converted {len(dataframes)} dataframes from {len(tables)} HTML tables")
    """
    dataframes = []
    conversion_errors = []

    for i, table_obj in enumerate(table_objects):
        try:
            html_content = table_obj.get("content", {}).get("html", "")

            if not html_content:
                logger.warning(f"Table {i+1}: Empty HTML content, skipping")
                continue

            # Use StringIO to pass HTML string to pd.read_html
            dfs = pd.read_html(StringIO(html_content))

            kept = [
                df
                for df in dfs
                if min_columns is None or len(df.columns) >= min_columns
            ]
            for df in dfs:
                if min_columns is not None and len(df.columns) < min_columns:
                    logger.info(
                        f"Table {i+1}: Skipping DataFrame with {len(df.columns)} columns "
                        f"(min_columns={min_columns})"
                    )

            if kept:
                dataframes.extend(kept)
                logger.info(
                    f"Table {i+1}: Kept {len(kept)}/{len(dfs)} DataFrame(s) "
                    f"with shapes: {[df.shape for df in kept]}"
                )
            else:
                logger.warning(f"Table {i+1}: No tables passed column filter")

        except Exception as e:
            error_msg = str(e)[:100]
            logger.error(f"Table {i+1}: Error converting HTML - {error_msg}")
            conversion_errors.append({"table_index": i + 1, "error": error_msg})

    logger.info(
        f"Conversion complete: {len(dataframes)} DataFrames created "
        f"from {len(table_objects)} table objects "
        f"({len(conversion_errors)} errors)"
    )

    return dataframes


def merge_spill_rows(df: pd.DataFrame, serial_col: str = "s/no/") -> pd.DataFrame:
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

    # Identify spill rows (rows with empty/NaN serial number)
    spill_mask = df[serial_col].isna() | (df[serial_col].astype(str).str.strip() == "")

    # Merge spill rows into previous row
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

    # Remove spill rows and reset index
    return df[~spill_mask].reset_index(drop=True)


def validate_records(records: list[dict], key_col: str | None = None) -> list[dict]:
    """
    Validate and clean records: filter empty key column, collapse whitespace.

    Args:
        records: List of record dictionaries
        key_col: Column name to check for emptiness. If None, uses first dict key.

    Returns:
        Cleaned and validated record list
    """
    if not records:
        return []

    cleaned = []
    for record in records:
        if not record:
            continue

        # Determine key column if not provided
        if key_col is None:
            key_col = next(iter(record.keys())) if record else None
            if not key_col:
                continue

        # Skip if key column is empty
        if not record.get(key_col):
            continue

        # Collapse whitespace on all string values
        cleaned_record = {}
        for k, v in record.items():
            if isinstance(v, str):
                cleaned_record[k] = " ".join(v.split())
            else:
                cleaned_record[k] = v

        cleaned.append(cleaned_record)

    return cleaned
