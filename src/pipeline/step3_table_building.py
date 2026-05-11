"""Step 3: Table Building Pipeline

Orchestrates table building from MinerU output and stores results in session state.
Inputs: mineru_extraction_results
Outputs: raw_senate_bills, raw_assembly_bills, raw_committee_membership
"""

from pathlib import Path

from loguru import logger as log
from src.pipeline.store import PipelineStore
from src.table_builders.assembly_bills_builder import build_assembly_bills
from src.table_builders.senate_bills_builder import build_senate_bills
from src.table_builders.committee_leadership_builder import (
    build_committee_leadership_table,
)


def _find_content_list_v2(extract_dir: str) -> str:
    """Find the content_list_v2 JSON file in a MinerU extract directory.

    MinerU prefixes the filename with a UUID (e.g. ``{uuid}_content_list_v2.json``).
    Falls back to the bare ``content_list_v2.json`` name if no prefixed file exists.

    Args:
        extract_dir: Path to the MinerU extraction output directory.

    Returns:
        Absolute path string to the content_list_v2 JSON file.
    """
    directory = Path(extract_dir)
    matches = sorted(directory.glob("*_content_list_v2.json"))
    if matches:
        return str(matches[0])
    return str(directory / "content_list_v2.json")


def run_table_building_step(store: PipelineStore | None = None) -> dict:
    """Orchestrate table building step.

    Returns:
        Dict with status and build results
    """
    log.info("Starting Step 3: Table Building")
    if store is None:
        store = PipelineStore()

    # Check for required inputs
    step2 = store.step2_results or {}
    results = step2.get("mineru_extraction_results", {})
    has_mineru_results = bool(results)

    if not has_mineru_results:
        log.warning("MinerU extraction results not found")
        return {
            "status": "error",
            "message": "Run MinerU extraction first to build tables",
        }

    # Check if all extractions were successful
    all_success = all(r.get("status") == "success" for r in results.values())

    if not all_success:
        log.warning("Some MinerU extractions failed")
        return {
            "status": "error",
            "message": "Some MinerU extractions failed. Check MinerU Jobs page for details",
        }

    try:
        log.info("Building tables from MinerU output...")

        # Get JSON/markdown paths from session state
        senate_json = _find_content_list_v2(
            results.get("bill_tracker_senate", {}).get(
                "extract_dir", "data/mineru_output_bill_tracker_senate"
            )
        )
        assembly_json = _find_content_list_v2(
            results.get("bill_tracker_assembly", {}).get(
                "extract_dir", "data/mineru_output_bill_tracker_assembly"
            )
        )
        committee_md = (
            results.get("committee_leadership", {}).get(
                "extract_dir", "data/mineru_output_committee_leadership"
            )
            + "/full.md"
        )

        # Build all tables
        senate_result = build_senate_bills(senate_json)
        assembly_result = build_assembly_bills(assembly_json)
        committee_result = build_committee_leadership_table(committee_md)

        # Store results in step3_results
        store.step3_results = {
            "senate_bills": senate_result,
            "assembly_bills": assembly_result,
            "committee_membership": committee_result,
        }

        # Count successful builders
        success_count = sum(
            1
            for r in store.step3_results.values()
            if r.get("status") == "success"
        )
        total_count = len(store.step3_results)

        log.info(f"Table building complete: {success_count}/{total_count} successful")

        return {
            "status": "success",
            "message": f"Table building complete: {success_count}/{total_count} successful",
            "successful": success_count,
            "total": total_count,
        }
    except Exception as e:
        log.error(f"Table building failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }
