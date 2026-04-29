"""
Scrapes committee leadership and membership data.
"""

import requests
from loguru import logger as log

from .scrape_helpers import get_page, build_url, extract_text_from_element


# ── Core Functions ────────────────────────────────────────────────────────────


def scrape_committee_leadership() -> list[dict]:
    """
    Scrape committee leadership membership documents.

    Extracts PDF links from the committees leadership page.
    Filters for documents containing 'membership' in the title.

    Returns:
        List of dicts with title and url keys.
    """
    log.info("Scraping committee leadership...")

    url = "https://www.parliament.go.ke/committees-leadership"
    session = requests.Session()

    try:
        soup = get_page(session, url)
        committee_docs = _extract_committee_documents(soup, url)

        log.info(f"Extracted {len(committee_docs)} committee leadership documents")
        return committee_docs

    except Exception as e:
        log.error(f"Failed to scrape committee leadership: {e}")
        return []


# ── Helpers ────────────────────────────────────────────────────────────────────


def _extract_committee_documents(soup, page_url: str) -> list[dict]:
    """
    Extract committee documents from the page content.

    Looks for PDF links in the .node__content div and filters for documents
    containing 'membership' in the title.

    Args:
        soup: BeautifulSoup object of the page
        page_url: URL of the page for context

    Returns:
        List of dicts with title and url keys
    """
    found = []

    # Find the main content area
    content_div = soup.find("div", class_="node__content")
    if not content_div:
        log.warning("Committee leadership content area not found on page")
        return []

    # Extract all PDF links from the content area
    for link in content_div.find_all("a", href=True):
        href = link["href"].strip()

        # Resolve relative URLs
        if not href.startswith("http"):
            href = build_url("https://www.parliament.go.ke", href)

        # Extract title from link text
        title = extract_text_from_element(link)

        # Filter for documents containing 'membership' in the title
        if "membership" in title.lower():
            found.append({"title": title, "url": href})
            log.info(f"Added committee document: {title}")

    return found
