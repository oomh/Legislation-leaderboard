"""
Markdown Parser for MinerU Output

Extracts HTML tables from MinerU's full.md markdown files
and converts them to structured data.
"""

from pathlib import Path
from bs4 import BeautifulSoup
from loguru import logger as log

# ── Helper Functions ──────────────────────────────────────────────────────────


def extract_table_from_markdown(md_file: str) -> list[dict] | list[list]:
    """
    Extract all HTML tables from a markdown file.
    
    Args:
        md_file: Path to markdown file containing HTML tables
        
    Returns:
        If multiple tables: list of dicts with table_index and rows
        If single table: list of lists (rows)
        Empty list if no tables found
    """
    file_path = Path(md_file)
    
    if not file_path.exists():
        log.warning(f"Markdown file not found: {md_file}")
        return []

    with open(md_file, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")

    all_tables = []
    
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if cells:
                rows.append(cells)

        if rows:
            all_tables.append(rows)

    if not all_tables:
        log.warning(f"No tables found in {md_file}")
        return []

    if len(all_tables) > 1:
        log.info(f"Found {len(all_tables)} tables in {md_file}")
        return [{"table_index": idx, "rows": table} for idx, table in enumerate(all_tables)]
    
    log.info(f"Found 1 table in {md_file}")
    return all_tables


def extract_headers_and_rows(table_data: list) -> tuple[list, list]:
    """
    Separate table headers from data rows.
    
    Args:
        table_data: List of rows from extracted table
        
    Returns:
        Tuple of (headers list, data rows list)
    """
    if not table_data:
        return [], []

    headers = table_data[0] if table_data else []
    rows = table_data[1:] if len(table_data) > 1 else []
    
    return headers, rows


def convert_rows_to_dicts(headers: list, rows: list) -> list[dict]:
    """
    Convert table rows to list of dictionaries.
    
    Args:
        headers: Column header names
        rows: List of data rows
        
    Returns:
        List of dictionaries with headers as keys
    """
    if not headers or not rows:
        return []

    result = []
    for row in rows:
        row_dict = {}
        for idx, header in enumerate(headers):
            row_dict[header] = row[idx] if idx < len(row) else None
        result.append(row_dict)
    
    return result


# ── Core Functions ────────────────────────────────────────────────────────────


def parse_mineru_markdown(md_file: str) -> dict:
    """
    Complete workflow to parse MinerU markdown file.
    
    Args:
        md_file: Path to full.md file from MinerU output
        
    Returns:
        Dictionary with table data converted to list of dicts
    """
    try:
        # Extract all tables
        tables = extract_table_from_markdown(md_file)
        
        if not tables:
            log.warning(f"No tables extracted from {md_file}")
            return {"status": "no_tables", "tables": []}

        # Handle multiple tables
        if isinstance(tables[0], dict):
            parsed_tables = []
            for table_info in tables:
                table_index = table_info["table_index"]
                raw_rows = table_info["rows"]
                headers, data_rows = extract_headers_and_rows(raw_rows)
                table_dict = convert_rows_to_dicts(headers, data_rows)
                
                parsed_tables.append({
                    "table_index": table_index,
                    "headers": headers,
                    "row_count": len(table_dict),
                    "data": table_dict,
                })
            
            log.info(f"Parsed {len(parsed_tables)} tables from {md_file}")
            return {"status": "success", "tables": parsed_tables}
        
        # Handle single table
        else:
            headers, data_rows = extract_headers_and_rows(tables[0])
            table_dict = convert_rows_to_dicts(headers, data_rows)
            
            log.info(f"Parsed 1 table with {len(table_dict)} rows from {md_file}")
            return {
                "status": "success",
                "tables": [{
                    "table_index": 0,
                    "headers": headers,
                    "row_count": len(table_dict),
                    "data": table_dict,
                }],
            }

    except Exception as e:
        log.error(f"Failed to parse markdown file {md_file}: {e}")
        return {"status": "failed", "error": str(e), "tables": []}
