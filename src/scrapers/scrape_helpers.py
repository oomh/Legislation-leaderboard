"""
Helpers used by all the individual scrapers.
"""

import time
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from loguru import logger as log
import requests
from bs4 import BeautifulSoup

from src.config import get_config

# ── Imports & Constants ────────────────────────────────────────────────────────

config = get_config()
BASE_URL = config["base_url"]
headers = config["scrape_headers"]
excluded_titles = config["excluded_titles"]

log.info(f"Base URL: {BASE_URL}")
log.info(f"Excluded titles: {excluded_titles}")
log.info(f"Headers configured: {bool(headers)}")
log.info(f"User agent: {headers.get('User-Agent', 'Not set')}")

# ── Helpers ────────────────────────────────────────────────────────────────────


def create_session() -> requests.Session:
    """Create a requests session with default headers."""
    session = requests.Session()
    session.headers.update(headers)
    return session


def clean_text(text: str) -> str:
    """Clean and normalize text by removing extra whitespace."""
    if not text:
        return ""
    return " ".join(text.split())


def extract_text_from_element(element, separator: str = " ") -> str:
    """Extract and clean text content from a BeautifulSoup element."""
    if not element:
        return ""
    return clean_text(element.get_text(separator=separator, strip=True))


def get_element_attribute(element, attr: str, default: str = "") -> str:
    """Safely get an attribute from a BeautifulSoup element."""
    if not element:
        return default
    value = element.get(attr)
    return clean_text(value) if value else default


def build_url(base: str, relative: str) -> str:
    """Resolve a relative URL to an absolute URL."""
    if not relative:
        return ""
    if relative.startswith("http"):
        return relative
    return urljoin(base, relative)


def is_pdf_url(url: str) -> bool:
    """Check if a URL points to a PDF."""
    return url.lower().endswith(".pdf")


def is_document_path(url: str) -> bool:
    """Check if URL contains common document store path patterns."""
    return bool(re.search(r"/sites/default/files/", url, re.I))


def extract_page_number(href: str) -> int | None:
    """Extract page number from pagination URL parameter."""
    match = re.search(r"page=(\d+)", str(href))
    return int(match.group(1)) if match else None


# ── Core Fetching Functions ────────────────────────────────────────────────────


def get_page(session: requests.Session, url: str, retries: int = 3) -> BeautifulSoup:
    """Fetch a URL and return a BeautifulSoup object. Retries on failure."""
    log.info(f"Fetching page: {url}")

    for attempt in range(1, retries + 1):
        try:
            response = session.get(url=url, timeout=30)
            response.raise_for_status()
            log.info(f"Successfully fetched {url}")
            return BeautifulSoup(response.text, "html.parser")

        except requests.RequestException as exc:
            log.info(f"Attempt {attempt}/{retries} failed for {url}: {exc}")
            if attempt < retries:
                time.sleep(3 * attempt)

    log.info(f"Failed to fetch {url} after {retries} attempts")
    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts.")


def get_page_content(url: str, retries: int = 3) -> BeautifulSoup:
    """Convenience function to fetch a page without managing a session."""
    log.info(f"Getting page content from {url}")
    session = create_session()
    return get_page(session, url, retries=retries)


# ── Pagination Detection ────────────────────────────────────────────────────────


def get_total_pages(soup: BeautifulSoup) -> int:
    """
    Detect the last page number from Drupal's pager widget.
    Falls back to 1 (single page) if no pager is found.

    Drupal pager: <li class="pager-last last"><a href="?page=N">last »</a></li>
    """
    last = soup.select_one("li.pager-last a, li.pager__item--last a")
    if last and last.get("href"):
        page_num = extract_page_number(last["href"])
        if page_num is not None:
            return page_num + 1

    # Alternative: collect all page= numbers and take the maximum
    page_nums = []
    for a in soup.select("li.pager-item a, li.pager__item a"):
        href = a.get("href", "")
        if href:
            href = href if isinstance(href, str) else " ".join(href)
            page_num = extract_page_number(href)
            if page_num is not None:
                page_nums.append(page_num)

    return max(page_nums) + 1 if page_nums else 1


# ── Link Extraction ────────────────────────────────────────────────────────────


def extract_pdf_links(soup: BeautifulSoup, page_url: str) -> list[dict]:
    """
    Return a list of dicts with keys: title, url.
    Looks for <a> tags whose href ends in .pdf (case-insensitive),
    or whose href contains common parliament document path patterns.
    Filters out titles matching excluded_titles from config.
    """
    found = []
    seen_urls = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()

        # Resolve relative URLs
        if not href.startswith("http"):
            href = urljoin(BASE_URL, href)

        # Extract title from link text or filename
        raw_title = a.get_text(separator=" ", strip=True)
        if not raw_title:
            raw_title = (
                Path(urlparse(href).path).stem.replace("_", " ").replace("-", " ")
            )

        # Skip known non-document link titles - check if title starts with excluded phrase
        if any(raw_title.lower().startswith(phrase.lower()) for phrase in excluded_titles):
            log.info(f"Filtered out: {raw_title}")
            continue

        # Filter: must be a PDF or a /sites/default/files/ document
        is_pdf = href.lower().endswith(".pdf")
        is_doc_path = bool(re.search(r"/sites/default/files/", href, re.I))

        if (is_pdf or is_doc_path) and href not in seen_urls:
            seen_urls.add(href)
            found.append({"title": raw_title, "url": href})
            log.info(f"Added to results: {raw_title}")

    return found


def extract_links_by_selector(soup: BeautifulSoup, selector: str) -> list[dict]:
    """Extract all links matching a CSS selector. Returns dicts with title and url."""
    found = []
    for element in soup.select(selector):
        href = build_url(BASE_URL, element.get("href", ""))
        if href:
            title = extract_text_from_element(element)
            found.append({"title": title, "url": href})
    return found


def extract_text_by_selector(soup: BeautifulSoup, selector: str) -> list[dict]:
    """Extract text content from elements matching a CSS selector."""
    found = []
    for element in soup.select(selector):
        text = extract_text_from_element(element)
        if text:
            found.append({"text": text})
    return found


# ── Pagination Scraping ────────────────────────────────────────────────────────


def scrape_all_pdfs(
    URL: str,
    delay: float = 1.5,
) -> list[dict]:
    """
    Iterate through all paginated pages and collect every PDF link.
    Returns a de-duplicated list of dicts: {title, url}.
    """
    log.info(f"Starting PDF scraping from {URL}")

    session = create_session()
    all_pdfs: list[dict] = []
    seen_urls: set[str] = set()

    soup = get_page(session, URL)

    total_pages = get_total_pages(soup)
    log.info(f"Detected {total_pages} total page(s)")

    for link in extract_pdf_links(soup, URL):
        if link["url"] not in seen_urls:
            seen_urls.add(link["url"])
            all_pdfs.append(link)

    for page_num in range(1, total_pages):
        url = f"{URL}?page={page_num}"
        log.info(f"Fetching page {page_num + 1}/{total_pages}")
        time.sleep(1.5)

        try:
            soup = get_page(session, url)
        except RuntimeError as e:
            log.info(f"Skipping page {page_num + 1}: {e}")
            continue

        for link in extract_pdf_links(soup, url):
            if link["url"] not in seen_urls:
                seen_urls.add(link["url"])
                all_pdfs.append(link)

    log.info(f"PDF scraping complete: {len(all_pdfs)} total PDFs collected")
    return all_pdfs


def scrape_paginated_links(
    url: str,
    selector: str,
    delay: float = 1.5,
) -> list[dict]:
    """
    Iterate through all paginated pages and collect links matching a selector.
    Returns a de-duplicated list of dicts: {title, url}.
    """
    log.info(f"Starting paginated link scraping from {url}")

    session = create_session()
    all_links: list[dict] = []
    seen_urls: set[str] = set()

    soup = get_page(session, url)

    total_pages = get_total_pages(soup)
    log.info(f"Detected {total_pages} total page(s)")

    for link in extract_links_by_selector(soup, selector):
        if link["url"] not in seen_urls:
            seen_urls.add(link["url"])
            all_links.append(link)

    for page_num in range(1, total_pages):
        paginated_url = f"{url}?page={page_num}"
        log.info(f"Fetching page {page_num + 1}/{total_pages}")
        time.sleep(delay)

        try:
            soup = get_page(session, paginated_url)
        except RuntimeError as e:
            log.info(f"Skipping page {page_num + 1}: {e}")
            continue

        for link in extract_links_by_selector(soup, selector):
            if link["url"] not in seen_urls:
                seen_urls.add(link["url"])
                all_links.append(link)

    log.info(f"Link scraping complete: {len(all_links)} total links collected")
    return all_links
