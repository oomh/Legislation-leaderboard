"""
Senate Bill Tracker Builder

Specialized handler for Senate bills tracker table extraction.
Handles rowspan attributes, multi-row entries, and complex formatting.
"""

from pathlib import Path
from bs4 import BeautifulSoup
from loguru import logger as log

# ── Helper Functions ──────────────────────────────────────────────────────────


def parse_senate_bills_markdown(md_file: str) -> list[dict]:
    """
    Parse Senate bills tracker markdown file and extract structured bill data.
    
    Handles:
    - Multiple HTML tables
    - rowspan attributes
    - Multi-row bill entries
    - Complex remarks columns
    
    Args:
        md_file: Path to full.md markdown file
        
    Returns:
        List of dictionaries with bill data
    """
    file_path = Path(md_file)
    
    if not file_path.exists():
        log.warning(f"Markdown file not found: {md_file}")
        return []

    with open(md_file, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")
    # find all tables in the markdown content
    all_tables = soup.find_all("table")

    if not all_tables:
        log.warning(f"No tables found in {md_file}")
        return []
    # list to hold all the bills
    bills = []

    # then we iterate
    for table_idx, table in enumerate(all_tables):
        log.info(f"Processing table {table_idx + 1}/{len(all_tables)}")
        
        # Extract rows from table
        rows = table.find_all("tr")
        
        # Group rows by bill number
        current_bill = None
        
        for row in rows:
            cells = row.find_all("td")
            
            if not cells:
                continue

            # Extract cell text
            cell_data = [cell.get_text(" ", strip=True) for cell in cells]

            # Skip header rows (contain "NO.", "BILL", etc.)
            if len(cell_data) > 0 and cell_data[0] == "NO.":
                continue

            # Check if this is a new bill entry (has a bill number in first column)
            first_cell_text = cell_data[0] if cell_data else ""
            
            if first_cell_text and first_cell_text[0].isdigit():
                # New bill entry
                if current_bill:
                    bills.append(current_bill)

                current_bill = {
                    "bill_number": first_cell_text,
                    "bill_name": cell_data[1] if len(cell_data) > 1 else "",
                    "sponsor": cell_data[2] if len(cell_data) > 2 else "",
                    "gazette_no": cell_data[3] if len(cell_data) > 3 else "",
                    "date_publication": cell_data[4] if len(cell_data) > 4 else "",
                    "maturity": cell_data[5] if len(cell_data) > 5 else "",
                    "date_1st_read": cell_data[6] if len(cell_data) > 6 else "",
                    "sc_committee": cell_data[7] if len(cell_data) > 7 else "",
                    "date_2nd_read": cell_data[8] if len(cell_data) > 8 else "",
                    "cotw_3rd_read": cell_data[9] if len(cell_data) > 9 else "",
                    "date_assent": cell_data[10] if len(cell_data) > 10 else "",
                    "remarks": cell_data[11] if len(cell_data) > 11 else "",
                }

            elif current_bill and first_cell_text:
                # Continuation of previous bill (additional info)
                # This happens when a bill has multiple rows with additional details
                # We'll append to the bill name or remarks
                if len(cell_data) > 0:
                    current_bill["bill_name"] += " " + first_cell_text
                
                # Handle additional remarks
                if len(cell_data) > 11:
                    current_bill["remarks"] += " " + cell_data[11]

        # Don't forget the last bill
        if current_bill:
            bills.append(current_bill)

    log.info(f"Extracted {len(bills)} bills from Senate bill tracker")
    return bills


def validate_and_clean_senate_bills(bills: list[dict]) -> list[dict]:
    """
    Validate and clean extracted bill data.
    
    Args:
        bills: List of bill dictionaries
        
    Returns:
        Cleaned list of bills
    """
    cleaned_bills = []
    
    for bill in bills:
        # Skip if no bill number
        if not bill.get("bill_number"):
            continue

        # Clean up whitespace
        cleaned_bill = {k: v.strip() if isinstance(v, str) else v for k, v in bill.items()}
        cleaned_bills.append(cleaned_bill)

    log.info(f"Cleaned {len(cleaned_bills)} bills")
    return cleaned_bills


# ── Core Functions ────────────────────────────────────────────────────────────


def build_senate_bills_table(md_file: str) -> dict:
    """
    Complete workflow to build Senate bills table.
    
    Args:
        md_file: Path to full.md markdown file
        
    Returns:
        Dictionary with table status and data
    """
    try:
        # Parse markdown
        bills = parse_senate_bills_markdown(md_file)
        
        if not bills:
            log.warning("No bills extracted from Senate bill tracker")
            return {
                "status": "failed",
                "error": "No bills found",
                "data": [],
                "row_count": 0,
            }

        # Validate and clean
        cleaned_bills = validate_and_clean_senate_bills(bills)

        log.info(f"Senate bills table built: {len(cleaned_bills)} bills")
        return {
            "status": "success",
            "data": cleaned_bills,
            "row_count": len(cleaned_bills),
        }

    except Exception as e:
        log.error(f"Failed to build Senate bills table: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "data": [],
            "row_count": 0,
        }
