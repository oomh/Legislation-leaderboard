"""
Senate Bills Table Builder

Builds and processes legislative tables from MinerU-extracted senate bill tracker JSON.
"""

import logging
from typing import Dict, Any

import pandas as pd

from src.table_builders.helper_functions import (
    extract_tables_from_json,
    convert_html_tables_to_dataframes
    )

logger = logging.getLogger(__name__)


def build_senate_bills(
    json_file_path: str = "data/mineru_output_bill_tracker_senate/content_list_v2.json",
) -> Dict[str, Any]:
    """
    Build senate bill tables from MinerU-extracted JSON.

    This function:
    1. Extracts table objects from the senate bill tracker JSON file
    2. Converts HTML content to DataFrames
    3. Concatenates all DataFrames into a single combined DataFrame

    Args:
        json_file_path (str): Path to the JSON file containing extracted senate bills.

    Returns:
        Dict[str, Any]: Result dictionary containing:
            - status (str): 'success' or 'error'
            - data (pd.DataFrame): Combined DataFrame with all bill data
            - row_count (int): Number of rows in the result
            - message (str): Status message
    """
    try:
        logger.info(f"Building senate bills tables from {json_file_path}")

        # Step 1: Extract tables from JSON
        tables = extract_tables_from_json(json_file_path)

        if not tables:
            warning_msg = "No tables found in senate bills JSON"
            logger.warning(warning_msg)
            return {
                "status": "success",
                "data": pd.DataFrame(),
                "row_count": 0,
                "message": warning_msg,
            }

        # Step 2: Convert HTML tables to DataFrames
        dataframes = convert_html_tables_to_dataframes(tables)

        if not dataframes:
            warning_msg = "No DataFrames created from HTML conversion"
            logger.warning(warning_msg)
            
            return {
                "status": "success",
                "data": pd.DataFrame(),
                "row_count": 0,
                "message": warning_msg,
            }

        # Step 3: Concatenate all DataFrames into one
        combined_df = pd.concat(dataframes, ignore_index=True) if dataframes else pd.DataFrame()

        # Step 4: Convert all data to strings and handle missing values for Arrow compatibility
        if not combined_df.empty:
            # Convert all columns to string type and replace NaN with empty strings
            combined_df = combined_df.astype(str).replace('nan', '')
            
        row_count = len(combined_df)

        logger.info(f"Successfully built senate bills: {row_count} rows")

        return {
            "status": "success",
            "data": combined_df,
            "row_count": row_count,
            "message": f"Successfully extracted {row_count} bill records",
        }

    except Exception as e:
        error_msg = f"Error building senate bills: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "data": pd.DataFrame(),
            "row_count": 0,
            "message": error_msg,
        }
