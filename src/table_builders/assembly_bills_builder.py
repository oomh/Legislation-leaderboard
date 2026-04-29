"""
Specialized table builder for National Assembly (Assembly) bill tracker markdown files.

This module handles extraction and transformation of bill data from MinerU markdown outputs
specifically formatted for National Assembly bills tracker, handling multi-row entries,
repeated headers, and complex formatting.
"""

from bs4 import BeautifulSoup
from loguru import logger
from typing import TypedDict, List, Dict, Any
import re


class BillRecord(TypedDict):
    """Type definition for a bill record extracted from the tracker."""

    bill_number: str
    bill_name: str
    sponsor: str
    na_sen_bill_no: str
    dated: str
    maturity_date: str
    gazette_no: str
    first_read: str
    second_read: str
    third_read: str
    remarks: str
    assent: str


# ----
# Core parsing functions for Assembly bills
# ----


def parse_assembly_bills_markdown(markdown_content: str) -> List[BillRecord]:
    """
    Extract bill records from National Assembly bills tracker markdown.

    Handles:
    - Multiple HTML tables embedded in markdown
    - Repeated header rows throughout document
    - Multi-row bill entries (bill name or remarks spanning rows)
    - Empty cells and irregular formatting
    - Column value continuation across rows

    Args:
        markdown_content: Full markdown content with embedded HTML tables

    Returns:
        List of extracted bill records
    """

    logger.info("Starting Assembly bills markdown parsing")

    soup = BeautifulSoup(markdown_content, "html.parser")
    
    # Find all tables in the markdown content
    tables = soup.find_all("table")

    logger.debug(f"Found {len(tables)} table(s) in markdown")

    # List to hold all extracted bill records
    all_bills: List[BillRecord] = []

    # Then We iterate
    for table_idx, table in enumerate(tables):
        logger.debug(f"Processing table {table_idx + 1}/{len(tables)}")

        rows = table.find_all("tr")

        # Process rows and handle multi-row entries
        current_bill: Dict[str, Any] = {}
        i = 0

        while i < len(rows):
            cells = rows[i].find_all("td")

            if not cells:
                i += 1
                continue

            # Extract cell values
            cell_values = [cell.get_text(strip=False).strip() for cell in cells]

            # Skip if row is empty or header row
            if not any(cell_values) or cell_values[0].upper() == "S/NO/":
                i += 1
                continue

            # Check if first cell is a bill number
            is_new_bill_in_col0 = cell_values[0] and re.match(r"^\d+\.?$", cell_values[0])
            
            # Check if Name column [1] contains a bill number (split entry case)
            is_new_bill_in_col1 = len(cell_values) > 1 and cell_values[1] and re.match(r"^\d+\.?$", cell_values[1]) and not cell_values[0]

            if is_new_bill_in_col0:
                # Save previous bill if exists
                if current_bill:
                    bill_record = _format_bill_record(current_bill)
                    if bill_record:
                        all_bills.append(bill_record)

                # Start new bill from standard column layout
                current_bill = {
                    "bill_number": cell_values[0],
                    "bill_name": cell_values[1] if len(cell_values) > 1 else "",
                    "sponsor": cell_values[2] if len(cell_values) > 2 else "",
                    "na_sen_bill_no": cell_values[3] if len(cell_values) > 3 else "",
                    "dated": cell_values[4] if len(cell_values) > 4 else "",
                    "maturity_date": cell_values[5] if len(cell_values) > 5 else "",
                    "gazette_no": cell_values[6] if len(cell_values) > 6 else "",
                    "first_read": cell_values[7] if len(cell_values) > 7 else "",
                    "second_read": cell_values[8] if len(cell_values) > 8 else "",
                    "third_read": cell_values[9] if len(cell_values) > 9 else "",
                    "remarks": cell_values[10] if len(cell_values) > 10 else "",
                    "assent": cell_values[11] if len(cell_values) > 11 else "",
                }

            elif is_new_bill_in_col1:
                # Save previous bill if exists (continuation from previous row)
                if current_bill:
                    bill_record = _format_bill_record(current_bill)
                    if bill_record:
                        all_bills.append(bill_record)

                # Start new bill with number in column [1] (split entry)
                current_bill = {
                    "bill_number": cell_values[1],
                    "bill_name": cell_values[2] if len(cell_values) > 2 else "",
                    "sponsor": cell_values[3] if len(cell_values) > 3 else "",
                    "na_sen_bill_no": cell_values[4] if len(cell_values) > 4 else "",
                    "dated": cell_values[5] if len(cell_values) > 5 else "",
                    "maturity_date": cell_values[6] if len(cell_values) > 6 else "",
                    "gazette_no": cell_values[7] if len(cell_values) > 7 else "",
                    "first_read": cell_values[8] if len(cell_values) > 8 else "",
                    "second_read": cell_values[9] if len(cell_values) > 9 else "",
                    "third_read": cell_values[10] if len(cell_values) > 10 else "",
                    "remarks": cell_values[11] if len(cell_values) > 11 else "",
                    "assent": cell_values[12] if len(cell_values) > 12 else "",
                }

            else:
                # Continuation row - append to previous bill fields
                if current_bill:

                    # Find which column has the continuation data
                    if cell_values[0] == "" and len(cell_values) > 1 and cell_values[1] != "":
                        # Bill name continuation
                        current_bill["bill_name"] += " " + cell_values[1]

                    if len(cell_values) > 10 and cell_values[10] != "":
                        # Remarks continuation
                        current_bill["remarks"] += " " + cell_values[10]

                    # Handle assent - could be in [11] or [12] depending on number of columns
                    if len(cell_values) > 11 and cell_values[11] and not current_bill["assent"]:
                        current_bill["assent"] = cell_values[11]
                    elif len(cell_values) > 12 and cell_values[12] and not current_bill["assent"]:
                        current_bill["assent"] = cell_values[12]

            i += 1

        # Don't forget last bill
        if current_bill:
            bill_record = _format_bill_record(current_bill)
            if bill_record:
                all_bills.append(bill_record)

    logger.info(f"Parsed {len(all_bills)} bills from Assembly tracker")

    return all_bills


# ----
# Helper functions
# ----


def _format_bill_record(bill_dict: Dict[str, Any]) -> BillRecord | None:
    """
    Validate and format a bill record dict into BillRecord type.

    Args:
        bill_dict: Raw bill dict from parsing

    Returns:
        Formatted BillRecord or None if invalid
    """

    # Require at least bill number and name
    if not bill_dict.get("bill_number") or not bill_dict.get("bill_name"):
        return None

    return BillRecord(
        bill_number=bill_dict.get("bill_number", "").strip(),
        bill_name=bill_dict.get("bill_name", "").strip(),
        sponsor=bill_dict.get("sponsor", "").strip(),
        na_sen_bill_no=bill_dict.get("na_sen_bill_no", "").strip(),
        dated=bill_dict.get("dated", "").strip(),
        maturity_date=bill_dict.get("maturity_date", "").strip(),
        gazette_no=bill_dict.get("gazette_no", "").strip(),
        first_read=bill_dict.get("first_read", "").strip(),
        second_read=bill_dict.get("second_read", "").strip(),
        third_read=bill_dict.get("third_read", "").strip(),
        remarks=bill_dict.get("remarks", "").strip(),
        assent=bill_dict.get("assent", "").strip(),
    )


def validate_and_clean_assembly_bills(bills: List[BillRecord]) -> List[BillRecord]:
    """
    Validate and clean extracted bill records.

    Args:
        bills: List of extracted bill records

    Returns:
        Cleaned and validated bill records
    """

    logger.info(f"Validating {len(bills)} Assembly bills")

    cleaned_bills: List[BillRecord] = []

    for bill in bills:
        # Skip bills missing critical fields
        if not bill["bill_number"] or not bill["bill_name"]:
            continue

        # Clean up bill names (remove extra whitespace)
        bill["bill_name"] = " ".join(bill["bill_name"].split())
        bill["remarks"] = " ".join(bill["remarks"].split())

        cleaned_bills.append(bill)

    logger.info(f"Validation complete: {len(cleaned_bills)} valid bills")

    return cleaned_bills


def build_assembly_bills_table(
    mineru_markdown_path: str,
) -> Dict[str, Any]:
    """
    Complete workflow to extract and build Assembly bills table from MinerU markdown output.

    Args:
        mineru_markdown_path: Path to MinerU full.md file for Assembly tracker

    Returns:
        Dict with status, row_count, and data (list of bill records)
    """

    logger.info(f"Starting Assembly bills table build from: {mineru_markdown_path}")

    try:

        # Read markdown file
        with open(mineru_markdown_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        # Parse bills from markdown
        raw_bills = parse_assembly_bills_markdown(markdown_content)

        # Validate and clean
        cleaned_bills = validate_and_clean_assembly_bills(raw_bills)

        # Convert to dict format for output
        bills_data = [dict(bill) for bill in cleaned_bills]

        logger.info(
            f"Assembly bills table build successful: {len(bills_data)} bills extracted"
        )

        return {
            "status": "success",
            "row_count": len(bills_data),
            "data": bills_data,
        }

    except Exception as e:

        logger.error(f"Assembly bills table build failed: {str(e)}")

        return {
            "status": "failed",
            "row_count": 0,
            "data": [],
            "error": str(e),
        }
