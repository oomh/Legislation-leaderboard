"""Step 1: Scraping Pipeline

Orchestrates all scraping operations and stores results in session state.
Outputs: bill_tracker_urls, house_leadership, member_lists, committee_leadership
"""

import pandas as pd
from loguru import logger as log
from src.pipeline.store import PipelineStore
from src.scrapers.scrape_bill_trackers import (
    scrape_bill_tracker_senate,
    scrape_bill_tracker_national_assembly,
)
from src.scrapers.scrape_house_leadership import (
    scrape_house_leadership_national_assembly,
    scrape_house_leadership_senate,
)
from src.scrapers.scrape_members import (
    scrape_senate_members,
    scrape_national_assembly_members,
)
from src.scrapers.scrape_committee_members_pdf import scrape_committee_leadership


def run_bill_trackers_scraping(
    page_only: bool = True, store: PipelineStore | None = None
) -> dict:
    """Run bill tracker scrapers.

    Args:
        page_only: If True, scrape only first page

    Returns:
        Dict with status and counts
    """
    log.info("Starting bill tracker scrapers")
    if store is None:
        store = PipelineStore()

    try:
        senate_pdfs = scrape_bill_tracker_senate(page_only=page_only)
        assembly_pdfs = scrape_bill_tracker_national_assembly(page_only=page_only)

        step1 = store.step1_results or {}
        step1["bill_tracker_urls"] = {"senate": senate_pdfs, "assembly": assembly_pdfs}
        store.step1_results = step1

        log.info(
            f"Bill tracker scraping complete: Senate={len(senate_pdfs)}, Assembly={len(assembly_pdfs)}"
        )

        return {
            "status": "success",
            "senate_count": len(senate_pdfs),
            "assembly_count": len(assembly_pdfs),
        }
    except Exception as e:
        log.error(f"Bill tracker scraping failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


def run_house_leadership_scraping(store: PipelineStore | None = None) -> dict:
    """Run house leadership scrapers.

    Returns:
        Dict with status and counts
    """
    log.info("Starting house leadership scrapers")
    if store is None:
        store = PipelineStore()

    try:
        senate_leadership = scrape_house_leadership_senate()
        assembly_leadership = scrape_house_leadership_national_assembly()

        # Convert to DataFrames for consistency
        step1 = store.step1_results or {}
        step1["house_leadership"] = {
            "senate": (
                pd.DataFrame(senate_leadership).to_dict(orient="records")
                if senate_leadership
                else []
            ),
            "assembly": (
                pd.DataFrame(assembly_leadership).to_dict(orient="records")
                if assembly_leadership
                else []
            ),
        }
        store.step1_results = step1

        log.info(
            f"House leadership scraping complete: Senate={len(senate_leadership)}, Assembly={len(assembly_leadership)}"
        )

        return {
            "status": "success",
            "senate_count": len(senate_leadership),
            "assembly_count": len(assembly_leadership),
        }
    except Exception as e:
        log.error(f"House leadership scraping failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


def run_member_lists_scraping(
    page_only: bool = False, store: PipelineStore | None = None
) -> dict:
    """Run member list scrapers.

    Args:
        page_only: If True, scrape only first page

    Returns:
        Dict with status and counts
    """
    log.info("Starting member list scrapers")
    if store is None:
        store = PipelineStore()

    try:
        senate_members = scrape_senate_members(page_only=page_only)
        assembly_members = scrape_national_assembly_members(page_only=page_only)

        # Convert to DataFrames for consistency
        step1 = store.step1_results or {}
        step1["member_lists"] = {
            "senate": (
                pd.DataFrame(senate_members).to_dict(orient="records")
                if senate_members
                else []
            ),
            "assembly": (
                pd.DataFrame(assembly_members).to_dict(orient="records")
                if assembly_members
                else []
            ),
        }
        store.step1_results = step1

        log.info(
            f"Member list scraping complete: Senate={len(senate_members)}, Assembly={len(assembly_members)}"
        )

        return {
            "status": "success",
            "senate_count": len(senate_members),
            "assembly_count": len(assembly_members),
        }
    except Exception as e:
        log.error(f"Member list scraping failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


def run_committee_leadership_scraping(store: PipelineStore | None = None) -> dict:
    """Run committee leadership scraper.

    Returns:
        Dict with status and count
    """
    log.info("Starting committee leadership scraper")
    if store is None:
        store = PipelineStore()

    try:
        committee_docs = scrape_committee_leadership()

        step1 = store.step1_results or {}
        step1["committee_leadership"] = committee_docs
        store.step1_results = step1

        log.info(
            f"Committee leadership scraping complete: {len(committee_docs)} documents"
        )

        return {
            "status": "success",
            "count": len(committee_docs),
        }
    except Exception as e:
        log.error(f"Committee leadership scraping failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


def run_scraping_step(
    run_bill_trackers: bool = True,
    run_leadership: bool = True,
    run_members: bool = True,
    run_committee: bool = True,
    store: PipelineStore | None = None,
) -> dict:
    """Orchestrate complete scraping step.

    Args:
        run_bill_trackers: Run bill tracker scrapers
        run_leadership: Run house leadership scrapers
        run_members: Run member list scrapers
        run_committee: Run committee leadership scraper

    Returns:
        Dict with overall status and individual results
    """
    log.info("Starting Step 1: Scraping")
    if store is None:
        store = PipelineStore()

    results = {
        "bill_trackers": None,
        "leadership": None,
        "members": None,
        "committee": None,
    }

    if run_bill_trackers:
        results["bill_trackers"] = run_bill_trackers_scraping(store=store)

    if run_leadership:
        results["leadership"] = run_house_leadership_scraping(store=store)

    if run_members:
        results["members"] = run_member_lists_scraping(store=store)

    if run_committee:
        results["committee"] = run_committee_leadership_scraping(store=store)

    # Check overall success
    all_success = all(
        r is None or r.get("status") == "success" for r in results.values()
    )

    log.info(f"Step 1 Complete: {'Success' if all_success else 'Partial failures'}")

    run_count = sum(1 for r in results.values() if r is not None)
    success_count = sum(
        1 for r in results.values() if r is not None and r.get("status") == "success"
    )

    return {
        "status": "success" if all_success else "partial",
        "message": f"Scraping complete: {success_count}/{run_count} scrapers succeeded",
        "results": results,
    }
