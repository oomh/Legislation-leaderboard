"""
MinerU Orchestration

Coordinates extraction of multiple documents through the MinerU pipeline.
Sends scraped documents to MinerU for structured data extraction.
"""

from loguru import logger as log
from src.minerU_extractors.mineru import mineru_workflow

# ── Core Functions ────────────────────────────────────────────────────────────


def extract_bill_trackers_and_committee(
    bill_tracker_senate_url: str,
    bill_tracker_assembly_url: str,
    committee_leadership_url: str,
    api_key: str,
    bill_tracker_senate_dir: str = "./data/mineru_output_bill_tracker_senate",
    bill_tracker_assembly_dir: str = "./data/mineru_output_bill_tracker_assembly",
    committee_leadership_dir: str = "./data/mineru_output_committee_leadership",
):
    """
    Extract bill trackers and committee leadership documents through MinerU.

    Args:
        bill_tracker_senate_url: Senate bill tracker PDF URL
        bill_tracker_assembly_url: National Assembly bill tracker PDF URL
        committee_leadership_url: Committee leadership membership PDF URL
        api_key: MinerU API key for authentication
        bill_tracker_senate_dir: Directory to extract Senate bill tracker
        bill_tracker_assembly_dir: Directory to extract Assembly bill tracker
        committee_leadership_dir: Directory to extract committee leadership

    Returns:
        Dictionary with extraction results for all three documents
    """
    log.info(
        "Starting MinerU extraction workflow for bill trackers and committee leadership"
    )

    results = {}

    # Extract Senate bill tracker
    log.info(f"Extracting Senate bill tracker from {bill_tracker_senate_url}")
    senate_result = mineru_workflow(
        bill_tracker_senate_url, api_key, bill_tracker_senate_dir
    )

    results["bill_tracker_senate"] = {
        "status": "success" if senate_result else "failed",
        "extract_dir": bill_tracker_senate_dir,
        "result": senate_result,
    }

    if senate_result:
        log.info(
            f"Senate bill tracker extraction complete: {len(senate_result['file_list'])} files"
        )
    else:
        log.warning("Senate bill tracker extraction failed")

    # Extract Assembly bill tracker
    log.info(f"Extracting Assembly bill tracker from {bill_tracker_assembly_url}")
    assembly_result = mineru_workflow(
        bill_tracker_assembly_url, api_key, bill_tracker_assembly_dir
    )

    results["bill_tracker_assembly"] = {
        "status": "success" if assembly_result else "failed",
        "extract_dir": bill_tracker_assembly_dir,
        "result": assembly_result,
    }

    if assembly_result:
        log.info(
            f"Assembly bill tracker extraction complete: {len(assembly_result['file_list'])} files"
        )
    else:
        log.warning("Assembly bill tracker extraction failed")

    # Extract committee leadership
    log.info(f"Extracting committee leadership from {committee_leadership_url}")
    committee_result = mineru_workflow(
        committee_leadership_url, api_key, committee_leadership_dir
    )

    results["committee_leadership"] = {
        "status": "success" if committee_result else "failed",
        "extract_dir": committee_leadership_dir,
        "result": committee_result,
    }

    if committee_result:
        log.info(
            f"Committee leadership extraction complete: {len(committee_result['file_list'])} files"
        )
    else:
        log.warning("Committee leadership extraction failed")

    log.info("MinerU extraction workflow complete")

    return results
