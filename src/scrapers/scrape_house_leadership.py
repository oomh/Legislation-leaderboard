"""
Scrapes house leadership data for both Senate and National Assembly.
"""

import requests
from loguru import logger as log

from .scrape_helpers import get_page, clean_text


# ── Helpers ────────────────────────────────────────────────────────────────────


def parse_leadership_title(full_text: str) -> dict[str, str]:
    """
    Parse leadership position text into office and person.

    Handles two formats:
    - Senate: "Speaker of the Senate - Rt. Hon. Amason Jeffah Kingi, EGH, MP."
    - National Assembly: "Rt. Hon. (Dr.) Moses M. Wetang'ula, EGH, MP, Speaker of the National Assembly"

    Args:
        full_text: The full text from the leadership position element.

    Returns:
        Dict with 'office' and 'person' keys.
    """
    # Handle Senate format: Office - Person
    if " - " in full_text:
        parts = full_text.split(" - ", 1)
        return {
            "office": clean_text(parts[0]),
            "person": clean_text(parts[1]),
        }

    # Handle National Assembly format: Person, Office
    # Sort patterns by length (longest first) to match more specific patterns
    office_patterns = [
        "Deputy Speaker of the National Assembly",
        "Speaker of the National Assembly",
        "Leader of the Majority Party",
        "Leader of the Minority Party",
        "Majority Party Whip",
        "Minority Party Whip",
        "Clerk of the National Assembly",
    ]

    for pattern in office_patterns:
        if pattern in full_text:
            # Find the last occurrence of the pattern
            office_start = full_text.rfind(pattern)
            # Extract office and clean up
            office = full_text[office_start:].strip().rstrip(".")
            person = full_text[:office_start].strip().rstrip(",")

            return {
                "office": clean_text(office),
                "person": clean_text(person),
            }

    # Fallback if no recognized pattern is found
    return {"office": full_text, "person": ""}


def extract_leadership_from_page(soup) -> list[dict]:
    """
    Extract all leadership positions from the page HTML.

    Looks for positions within the .isotope-items.view-portfolio container.

    Args:
        soup: BeautifulSoup object of the page.

    Returns:
        List of dicts with 'office' and 'person' keys.
    """
    leadership_data = []

    # Find the portfolio container
    portfolio = soup.find("div", class_="isotope-items view-portfolio")

    if not portfolio:
        log.warning("Portfolio container not found on page")
        return []

    # Extract all leadership positions
    position_elements = portfolio.find_all("div", class_="post-title")

    for position in position_elements:
        link = position.find("a")
        if not link:
            continue

        title_text = clean_text(link.get_text(strip=True))
        parsed = parse_leadership_title(title_text)

        leadership_data.append(parsed)

    return leadership_data


# ── Core Functions ────────────────────────────────────────────────────────────


def scrape_house_leadership_senate() -> list[dict]:
    """
    Scrape Senate house leadership positions.

    Returns:
        List of dicts with 'office' and 'person' keys.
    """
    log.info("Scraping Senate house leadership...")

    url = "https://www.parliament.go.ke/the-senate"
    session = requests.Session()

    try:
        soup = get_page(session, url)
        leadership_data = extract_leadership_from_page(soup)

        log.info(f"Extracted {len(leadership_data)} Senate leadership positions")
        return leadership_data

    except Exception as e:
        log.error(f"Failed to scrape Senate house leadership: {e}")
        return []


def scrape_house_leadership_national_assembly() -> list[dict]:
    """
    Scrape National Assembly house leadership positions.

    Returns:
        List of dicts with 'office' and 'person' keys.
    """
    log.info("Scraping National Assembly house leadership...")

    url = "https://www.parliament.go.ke/the-national-assembly"
    session = requests.Session()

    try:
        soup = get_page(session, url)
        leadership_data = extract_leadership_from_page(soup)

        log.info(f"Extracted {len(leadership_data)} National Assembly leadership positions")
        return leadership_data

    except Exception as e:
        log.error(f"Failed to scrape National Assembly house leadership: {e}")
        return []


def scrape_all_house_leadership() -> dict:
    """
    Scrape house leadership for both chambers.

    Returns:
        Dict with 'senate' and 'national_assembly' keys containing leadership lists.
    """
    log.info("Starting house leadership scrape for both chambers")

    senate_data = scrape_house_leadership_senate()
    na_data = scrape_house_leadership_national_assembly()

    result = {
        "senate": senate_data,
        "national_assembly": na_data,
    }

    log.info(f"House leadership scrape complete: {len(senate_data)} Senate positions, {len(na_data)} Assembly positions")
    return result
