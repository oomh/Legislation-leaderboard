"""Helper Functions

Utility functions for managing scrapers and data processing.
"""

import os
import streamlit as st
from loguru import logger as log
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
from concurrent.futures import ThreadPoolExecutor, as_completed


# ── MinerU Detection ───────────────────────────────────────────────────────────


def detect_mineru_extraction_results():
    """Detect existing MinerU extraction results in data folder.

    Returns dict with extraction results in session state format, or None if not found.
    """
    data_dir = "./data"

    extractions = {
        "bill_tracker_senate": {
            "extract_dir": os.path.join(data_dir, "mineru_output_bill_tracker_senate"),
        },
        "bill_tracker_assembly": {
            "extract_dir": os.path.join(
                data_dir, "mineru_output_bill_tracker_assembly"
            ),
        },
        "committee_leadership": {
            "extract_dir": os.path.join(data_dir, "mineru_output_committee_leadership"),
        },
    }

    all_found = True
    results = {}

    for key, extraction_info in extractions.items():
        extract_dir = extraction_info["extract_dir"]
        full_md_path = os.path.join(extract_dir, "full.md")

        if os.path.exists(full_md_path):
            results[key] = {
                "status": "success",
                "extract_dir": extract_dir,
                "result": {
                    "file_list": [
                        f
                        for f in os.listdir(extract_dir)
                        if os.path.isfile(os.path.join(extract_dir, f))
                    ]
                },
            }
            log.info(f"Found existing MinerU extraction: {key}")
        else:
            all_found = False

    if all_found and results:
        log.info("All MinerU extraction results detected from disk")
        return results

    return None


# ── Scraper Orchestration ─────────────────────────────────────────────────────


def run_all_scrapers():
    """Run all scrapers in parallel using ThreadPoolExecutor."""
    scraper_tasks = {
        "Senate Bill Tracker": lambda: scrape_bill_tracker_senate(page_only=True),
        "Assembly Bill Tracker": lambda: scrape_bill_tracker_national_assembly(
            page_only=True
        ),
        "Senate Leadership": lambda: scrape_house_leadership_senate(),
        "Assembly Leadership": lambda: scrape_house_leadership_national_assembly(),
        "Senate Members": lambda: scrape_senate_members(page_only=False),
        "Assembly Members": lambda: scrape_national_assembly_members(page_only=False),
        "Committee Leadership": lambda: scrape_committee_leadership(),
    }

    results = {}
    errors = {}

    # Execute all scrapers in parallel (max 4 concurrent threads)
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all tasks
        future_to_name = {
            executor.submit(task): name for name, task in scraper_tasks.items()
        }

        log.info(f"Started {len(future_to_name)} scrapers in parallel")

        # Collect results as they complete
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                result = future.result()
                results[name] = result
                log.info(f"Completed: {name} - {len(result)} records")
            except Exception as e:
                errors[name] = str(e)
                log.error(f"Failed: {name} - {e}")

    return results, errors
