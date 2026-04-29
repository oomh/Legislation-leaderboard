"""
Table Builder Orchestration

Coordinates extraction of tables from all MinerU output directories.
Processes markdown files using specialized builders for different document types.
"""

from pathlib import Path
from loguru import logger as log
from src.table_builders.markdown_parser import parse_mineru_markdown
from src.table_builders.senate_bills_builder import build_senate_bills_table
from src.table_builders.assembly_bills_builder import build_assembly_bills_table
from src.table_builders.committee_leadership_builder import build_committee_leadership_table

# ── Core Functions ────────────────────────────────────────────────────────────


def build_tables_from_mineru_output(
    bill_tracker_senate_dir: str = "./data/mineru_output_bill_tracker_senate",
    bill_tracker_assembly_dir: str = "./data/mineru_output_bill_tracker_assembly",
    committee_leadership_dir: str = "./data/mineru_output_committee_leadership",
) -> dict:
    """
    Extract and build tables from all MinerU extraction output directories.
    
    Uses specialized builders for each document type:
    - Senate bills: Handles rowspan, multi-row entries
    - Assembly bills: Generic parser (pending specialization)
    - Committee leadership: Generic parser (pending specialization)
    
    Args:
        bill_tracker_senate_dir: Senate bill tracker extraction directory
        bill_tracker_assembly_dir: Assembly bill tracker extraction directory
        committee_leadership_dir: Committee leadership extraction directory
        
    Returns:
        Dictionary with table extraction results for each document type
    """
    log.info("Starting table builder workflow from MinerU outputs")

    results = {}

    # Extract Senate bill tracker using specialized builder
    senate_md_path = Path(bill_tracker_senate_dir) / "full.md"
    log.info(f"Building Senate bills table from: {senate_md_path}")
    
    senate_result = build_senate_bills_table(str(senate_md_path))
    results["bill_tracker_senate"] = {
        "status": senate_result.get("status"),
        "row_count": senate_result.get("row_count"),
        "data": senate_result.get("data", []),
    }
    
    if senate_result.get("status") == "success":
        log.info(f"Senate bills: {senate_result['row_count']} bills extracted")
    else:
        log.warning(f"Senate bills extraction failed: {senate_result.get('error', 'Unknown error')}")

    # Extract Assembly bill tracker using specialized builder
    assembly_md_path = Path(bill_tracker_assembly_dir) / "full.md"
    log.info(f"Building Assembly bills table from: {assembly_md_path}")
    
    assembly_result = build_assembly_bills_table(str(assembly_md_path))
    results["bill_tracker_assembly"] = {
        "status": assembly_result.get("status"),
        "row_count": assembly_result.get("row_count"),
        "data": assembly_result.get("data", []),
    }
    
    if assembly_result.get("status") == "success":
        log.info(f"Assembly bills: {assembly_result['row_count']} bills extracted")
    else:
        log.warning(f"Assembly bills extraction failed: {assembly_result.get('error', 'Unknown error')}")

    # Extract committee leadership using specialized builder
    committee_md_path = Path(committee_leadership_dir) / "full.md"
    log.info(f"Building committee leadership table from: {committee_md_path}")
    
    committee_result = build_committee_leadership_table(str(committee_md_path))
    results["committee_leadership"] = {
        "status": committee_result.get("status"),
        "table_count": committee_result.get("table_count"),
        "member_count": committee_result.get("member_count"),
        "tables": committee_result.get("tables", []),
    }
    
    if committee_result.get("status") == "success":
        log.info(f"Committee leadership: {committee_result['table_count']} committees, {committee_result['member_count']} members extracted")
    else:
        log.warning(f"Committee leadership extraction failed: {committee_result.get('error', 'Unknown error')}")

    log.info("Table builder workflow complete")

    return results
