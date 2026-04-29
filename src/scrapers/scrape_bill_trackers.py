"""
Scrapes bill tracking data for both senate and national assembly bills.
"""

import time
import requests
from loguru import logger as log

from .scrape_helpers import get_page, extract_pdf_links, get_total_pages


# ── Core Functions ────────────────────────────────────────────────────────────


def scrape_bill_tracker_national_assembly(delay: float = 0.5, page_only: bool = False) -> list[dict]:
    """
    Scrape bill tracker data for National Assembly bills.

    Args:
        delay: Delay in seconds between page requests.
        page_only: If True, only scrape the first page.

    Returns:
        List of bill tracker data dicts with title and url keys.
    """
    log.info("Scraping National Assembly bill tracker...")

    url = "https://www.parliament.go.ke/the-national-assembly/house-business/bill-tracker"
    session = requests.Session()

    try:
        soup = get_page(session, url)
        total_pages = get_total_pages(soup)
        log.info(f"Found {total_pages} pages in National Assembly bill tracker")

        all_pdfs = []

        # Only scrape first page if page_only is True
        pages_to_scrape = 1 if page_only else total_pages

        for page in range(pages_to_scrape):
            page_url = f"{url}?page={page}"
            log.info(f"Fetching National Assembly page {page + 1}/{pages_to_scrape}")

            soup = get_page(session, page_url)
            pdfs = extract_pdf_links(soup, page_url)
            all_pdfs.extend(pdfs)

            if page < pages_to_scrape - 1:
                time.sleep(delay)

        log.info(f"Extracted {len(all_pdfs)} bill tracker links from National Assembly")
        return all_pdfs

    except Exception as e:
        log.error(f"Failed to scrape National Assembly bill tracker: {e}")
        return []


def scrape_bill_tracker_senate(delay: float = 0.5, page_only: bool = False) -> list[dict]:
    """
    Scrape bill tracker data for Senate bills.

    Args:
        delay: Delay in seconds between page requests.
        page_only: If True, only scrape the first page.

    Returns:
        List of bill tracker data dicts with title and url keys.
    """
    log.info("Scraping Senate bill tracker...")

    url = "https://www.parliament.go.ke/the-senate/house-business/bills-tracker"
    session = requests.Session()

    try:
        soup = get_page(session, url)
        total_pages = get_total_pages(soup)
        log.info(f"Found {total_pages} pages in Senate bill tracker")

        all_pdfs = []

        # Only scrape first page if page_only is True
        pages_to_scrape = 1 if page_only else total_pages

        for page in range(pages_to_scrape):
            page_url = f"{url}?page={page}"
            log.info(f"Fetching Senate page {page + 1}/{pages_to_scrape}")

            soup = get_page(session, page_url)
            pdfs = extract_pdf_links(soup, page_url)
            all_pdfs.extend(pdfs)

            if page < pages_to_scrape - 1:
                time.sleep(delay)

        log.info(f"Extracted {len(all_pdfs)} bill tracker links from Senate")
        return all_pdfs

    except Exception as e:
        log.error(f"Failed to scrape Senate bill tracker: {e}")
        return []
