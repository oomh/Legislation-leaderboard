"""
Scrapers for acquiring member lists (MPs/Senators) from parliament.go.ke.
"""

import time
from loguru import logger as log

from src.config import get_config
from .scrape_helpers import (
    create_session,
    get_page,
    get_total_pages,
    build_url,
    extract_text_from_element,
    clean_text,
)

# ── Imports & Constants ────────────────────────────────────────────────────────

config = get_config()
BASE_URL = config["base_url"]

# ── Helpers ────────────────────────────────────────────────────────────────────


def _extract_member_from_row(row, page_url: str, chamber: str = "senate") -> dict | None:
    """
    Extract member details from a single table row (tr).
    Returns dict with: name, county, party, status, profile_url
    Returns None if extraction fails.
    
    Args:
        row: BeautifulSoup tr element
        page_url: URL of the page for context
        chamber: "senate" or "assembly" to handle different table structures
    """
    try:
        cells = row.find_all("td")
        
        if chamber == "senate":
            # Senate structure: name, image, county, party, status, more_link
            if len(cells) < 6:
                return None
            
            name = clean_text(cells[0].get_text(strip=True))
            county = clean_text(cells[2].get_text(strip=True))
            party = clean_text(cells[3].get_text(strip=True))
            status = clean_text(cells[4].get_text(strip=True))
            more_link = cells[5].find("a")
        
        else:  # assembly
            # Assembly structure: name, image, county, constituency, party, status, more_link
            if len(cells) < 7:
                return None
            
            name = clean_text(cells[0].get_text(strip=True))
            county = clean_text(cells[2].get_text(strip=True))
            party = clean_text(cells[4].get_text(strip=True))
            status = clean_text(cells[5].get_text(strip=True))
            more_link = cells[6].find("a")
        
        # Extract profile URL from link
        profile_url = ""
        if more_link and more_link.get("href"):
            profile_url = build_url(BASE_URL, more_link["href"])

        if name:
            return {
                "name": name,
                "county": county,
                "party": party,
                "status": status,
                "profile_url": profile_url,
            }
        return None

    except Exception as e:
        log.info(f"Error extracting member from row: {e}")
        return None


# ── Core Functions ────────────────────────────────────────────────────────────


def scrape_senate_members(delay: float = 0.5, page_only: bool = False) -> list[dict]:
    """
    Scrape all Senate members from paginated list.
    Returns list of dicts with: name, county, party, status, profile_url

    Args:
        delay: Delay between page requests in seconds
        page_only: If True, only scrape first page (for testing)
    """
    url = f"{BASE_URL}/the-senate/senators"
    log.info(f"Scraping Senate members from {url}")

    session = create_session()
    all_members: list[dict] = []

    soup = get_page(session, url)

    total_pages = get_total_pages(soup)
    log.info(f"Found {total_pages} pages in Senate members list")

    for page_num in range(0, total_pages):
        if page_only and page_num > 0:
            break

        paginated_url = f"{url}?page={page_num}" if page_num > 0 else url
        log.info(f"Fetching Senate page {page_num + 1}/{total_pages}")

        try:
            soup = get_page(session, paginated_url)
        except RuntimeError as e:
            log.info(f"Skipping page {page_num + 1}: {e}")
            continue

        # Extract members from table rows (find table with 6+ columns)
        tbody_found = False
        for table in soup.find_all("table"):
            tbody = table.find("tbody")
            if not tbody:
                continue
            
            # Check if this table has the right structure (6 columns for members table)
            first_row = tbody.find("tr")
            if first_row and len(first_row.find_all("td")) >= 6:
                rows = tbody.find_all("tr")
                log.info(f"Found {len(rows)} members on page {page_num + 1}")
                
                for row in rows:
                    member = _extract_member_from_row(row, paginated_url, chamber="senate")
                    if member:
                        all_members.append(member)
                        log.info(f"Added Senator: {member['name']} ({member['county']})")
                
                tbody_found = True
                break
        
        if not tbody_found:
            log.info(f"No members table found on page {page_num + 1}")

        if not page_only and page_num < total_pages - 1:
            time.sleep(delay)

    log.info(f"Senate member scraping complete: {len(all_members)} total members collected")
    return all_members


def scrape_national_assembly_members(
    delay: float = 0.5, page_only: bool = False
) -> list[dict]:
    """
    Scrape all National Assembly members from paginated list.
    Returns list of dicts with: name, county, party, status, profile_url

    Args:
        delay: Delay between page requests in seconds
        page_only: If True, only scrape first page (for testing)
    """
    url = f"{BASE_URL}/the-national-assembly/mps"
    log.info(f"Scraping National Assembly members from {url}")

    session = create_session()
    all_members: list[dict] = []

    soup = get_page(session, url)

    total_pages = get_total_pages(soup)
    log.info(f"Found {total_pages} pages in National Assembly members list")

    for page_num in range(0, total_pages):
        if page_only and page_num > 0:
            break

        paginated_url = f"{url}?page={page_num}" if page_num > 0 else url
        log.info(f"Fetching National Assembly page {page_num + 1}/{total_pages}")

        try:
            soup = get_page(session, paginated_url)
        except RuntimeError as e:
            log.info(f"Skipping page {page_num + 1}: {e}")
            continue

        # Extract members from table rows (find table with 6+ columns)
        tbody_found = False
        for table in soup.find_all("table"):
            tbody = table.find("tbody")
            if not tbody:
                continue
            
            # Check if this table has the right structure (6 columns for members table)
            first_row = tbody.find("tr")
            if first_row and len(first_row.find_all("td")) >= 6:
                rows = tbody.find_all("tr")
                log.info(f"Found {len(rows)} members on page {page_num + 1}")
                
                for row in rows:
                    member = _extract_member_from_row(row, paginated_url, chamber="assembly")
                    if member:
                        all_members.append(member)
                        log.debug(f"Added MP: {member['name']} ({member['county']})")
                
                tbody_found = True
                break
        
        if not tbody_found:
            log.info(f"No members table found on page {page_num + 1}")

        if not page_only and page_num < total_pages - 1:
            time.sleep(delay)

    log.info(f"National Assembly member scraping complete: {len(all_members)} total members collected")
    return all_members


def scrape_all_members(
    delay: float = 0.5, page_only: bool = False
) -> dict:
    """
    Scrape all members from both chambers.
    Returns dict with 'senate' and 'national_assembly' keys.
    """
    log.info("Starting member scraping for both chambers")

    return {
        "senate": scrape_senate_members(delay=delay, page_only=page_only),
        "national_assembly": scrape_national_assembly_members(
            delay=delay, page_only=page_only
        ),
    }
