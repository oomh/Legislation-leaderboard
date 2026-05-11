"""Step 2: MinerU Extraction Pipeline

Orchestrates MinerU extraction and stores results in session state.
Inputs: bill_tracker_urls, committee_leadership
Outputs: mineru_extraction_results
"""

from loguru import logger as log
from src.config import get_config
from src.pipeline.store import PipelineStore
from src.minerU_extractors import extract_bill_trackers_and_committee


def run_mineru_extraction_step(store: PipelineStore | None = None) -> dict:
    """Orchestrate MinerU extraction step.

    Returns:
        Dict with status and extraction results
    """
    log.info("Starting Step 2: MinerU Extraction")
    if store is None:
        store = PipelineStore()

    # Check for required inputs
    has_bill_tracker_senate = bool(store.bill_tracker_urls.get("senate"))
    has_bill_tracker_assembly = bool(store.bill_tracker_urls.get("assembly"))
    has_committee_leadership = bool(store.committee_leadership)

    if not (
        has_bill_tracker_senate
        and has_bill_tracker_assembly
        and has_committee_leadership
    ):
        log.warning("Missing required scraping data for MinerU extraction")
        return {
            "status": "error",
            "message": "Run scrapers first to populate bill trackers and committee leadership data",
        }

    # Get config
    config = get_config()
    if not config.get("mineru_api_key"):
        log.error("MinerU API key not configured")
        return {
            "status": "error",
            "message": "MinerU API key not configured in secrets",
        }

    try:
        # Get URLs from store (0th index)
        senate_bill_url = (
            store.bill_tracker_urls["senate"][0].get("url")
            if store.bill_tracker_urls["senate"]
            else None
        )
        assembly_bill_url = (
            store.bill_tracker_urls["assembly"][0].get("url")
            if store.bill_tracker_urls["assembly"]
            else None
        )
        committee_url = (
            store.committee_leadership[0].get("url")
            if store.committee_leadership
            else None
        )

        if not (senate_bill_url and assembly_bill_url and committee_url):
            log.error("Missing URL data in scraped results")
            return {
                "status": "error",
                "message": "Missing URL data in scraped results",
            }

        log.info(f"Extracting documents with MinerU...")

        # Run MinerU extraction
        results = extract_bill_trackers_and_committee(
            bill_tracker_senate_url=senate_bill_url,
            bill_tracker_assembly_url=assembly_bill_url,
            committee_leadership_url=committee_url,
            api_key=config.get("mineru_api_key"),
        )

        # Store results
        store.mineru_extraction_results = results

        # Count successes
        success_count = sum(1 for r in results.values() if r.get("status") == "success")
        total_count = len(results)

        log.info(
            f"MinerU extraction complete: {success_count}/{total_count} successful"
        )

        return {
            "status": "success",
            "message": f"MinerU extraction complete: {success_count}/{total_count} successful",
            "successful": success_count,
            "total": total_count,
            "results": results,
        }
    except Exception as e:
        log.error(f"MinerU extraction failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }
