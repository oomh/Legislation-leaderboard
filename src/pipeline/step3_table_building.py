"""Step 3: Table Building Pipeline

Orchestrates table building from MinerU output and stores results in session state.
Inputs: mineru_extraction_results
Outputs: raw_senate_bills, raw_assembly_bills, raw_committee_membership
"""

from loguru import logger as log
from src.pipeline.store import PipelineStore
from src.table_builders.assembly_bills_builder import build_assembly_bills
from src.table_builders.senate_bills_builder import build_senate_bills
from src.table_builders.committee_leadership_builder import (
    build_committee_leadership_table,
)


def run_table_building_step(store: PipelineStore | None = None) -> dict:
    """Orchestrate table building step.

    Returns:
        Dict with status and build results
    """
    log.info("Starting Step 3: Table Building")
    if store is None:
        store = PipelineStore()

    # Check for required inputs
    has_mineru_results = bool(store.mineru_extraction_results)

    if not has_mineru_results:
        log.warning("MinerU extraction results not found")
        return {
            "status": "error",
            "message": "Run MinerU extraction first to build tables",
        }

    results = store.mineru_extraction_results

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
        senate_json = (
            results.get("bill_tracker_senate", {}).get(
                "extract_dir", "data/mineru_output_bill_tracker_senate"
            )
            + "/content_list_v2.json"
        )
        assembly_json = (
            results.get("bill_tracker_assembly", {}).get(
                "extract_dir", "data/mineru_output_bill_tracker_assembly"
            )
            + "/content_list_v2.json"
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

        table_results = {
            "bill_tracker_senate": senate_result,
            "bill_tracker_assembly": assembly_result,
            "committee_leadership": committee_result,
        }

        # Store results
        store.table_builder_results = table_results

        store.raw_senate_bills = senate_result
        store.raw_assembly_bills = assembly_result
        store.raw_committee_membership = committee_result

        # Count successful builders
        success_count = sum(
            1 for r in table_results.values() if r.get("status") == "success"
        )
        total_count = len(table_results)

        log.info(f"Table building complete: {success_count}/{total_count} successful")

        return {
            "status": "success",
            "message": f"Table building complete: {success_count}/{total_count} successful",
            "successful": success_count,
            "total": total_count,
            "results": table_results,
        }
    except Exception as e:
        log.error(f"Table building failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }
