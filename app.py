"""
Legislation Leaderboard - Data Pipeline Orchestrator

Main Streamlit application for monitoring and managing the data pipeline.
Coordinates scraping, MinerU extraction, and database population.
"""

import streamlit as st
from loguru import logger as log
from src.config import get_config
from src.scrapers.scrape_bill_trackers import (
    scrape_bill_tracker_senate,
    scrape_bill_tracker_national_assembly,
)
from src.scrapers.scrape_house_leadership import (
    scrape_house_leadership_national_assembly,
    scrape_house_leadership_senate,
)
import pandas as pd

# ── Imports & Configuration ────────────────────────────────────────────────────

log.info("Starting Legislation Leaderboard application")

st.set_page_config(
    page_title="Legislation Leaderboard",
    page_icon="📋",
    layout="wide",
)

log.debug("Page configuration set")


# ── Page Definitions ──────────────────────────────────────────────────────────

def page_dashboard():
    """Render main dashboard page."""
    log.debug("Rendering dashboard page")

    st.markdown("### Pipeline Status")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Scraped Records", "0", "Pending")
    with col2:
        st.metric("Processing Jobs", "0", "In Queue")
    with col3:
        st.metric("Transformed Records", "0", "Ready")
    with col4:
        st.metric("Database Loaded", "0", "Synced")

    st.markdown("### Recent Activity")
    st.info("No recent activity. Start a scraping job to begin.")


def page_scrapers():
    """Render scrapers management page."""
    log.info("Navigating to scrapers page")

    config = get_config()

    if "bill_tracker_urls" not in st.session_state:
        st.session_state.bill_tracker_urls = {"senate": [], "assembly": []}
    
    if "house_leadership" not in st.session_state:
        st.session_state.house_leadership = {"senate": [], "assembly": []}

    st.markdown("### Scraper Management")

    # ── Bill Trackers ──────────────────────────────────────────────────────────

    st.markdown("#### Bill Trackers")

    col_both = st.columns(1)[0]
    with col_both:
        if st.button("Scrape Both Bill Trackers", key="scrape_both", use_container_width=True):
            log.info("Starting both bill tracker scrapers (page 1 only)")

            try:
                with st.spinner("Scraping both bill trackers..."):
                    senate_pdfs = scrape_bill_tracker_senate(page_only=True)
                    assembly_pdfs = scrape_bill_tracker_national_assembly(page_only=True)

                    st.session_state.bill_tracker_urls = {
                        "senate": senate_pdfs,
                        "assembly": assembly_pdfs,
                    }

                    log.info(f"Both scrapers complete: Senate={len(senate_pdfs)}, Assembly={len(assembly_pdfs)}")

                st.success(f"✓ Senate: {len(senate_pdfs)} PDFs | Assembly: {len(assembly_pdfs)} PDFs")

            except Exception as e:
                log.error(f"Both scrapers failed: {e}")
                st.error(f"Scraping failed: {e}")

    st.divider()

    # Display bill tracker data
    if st.session_state.bill_tracker_urls["senate"] or st.session_state.bill_tracker_urls["assembly"]:
        st.markdown("#### Bill Tracker Results")

        tab_senate, tab_assembly = st.tabs(["Senate Bill Trackers", "National Assembly Bill Trackers"])

        with tab_senate:
            if st.session_state.bill_tracker_urls["senate"]:
                senate_df = pd.DataFrame(st.session_state.bill_tracker_urls["senate"])
                st.dataframe(senate_df, use_container_width=True)
            else:
                st.info("No Senate bill tracker data scraped yet")

        with tab_assembly:
            if st.session_state.bill_tracker_urls["assembly"]:
                assembly_df = pd.DataFrame(st.session_state.bill_tracker_urls["assembly"])
                st.dataframe(assembly_df, use_container_width=True)
            else:
                st.info("No National Assembly bill tracker data scraped yet")

    # ── House Leadership ──────────────────────────────────────────────────────

    st.divider()
    st.markdown("#### House Leadership")

    col_leadership = st.columns(1)[0]
    with col_leadership:
        if st.button("Scrape House Leadership", key="scrape_leadership", use_container_width=True):
            log.info("Starting house leadership scrapers")

            try:
                with st.spinner("Scraping house leadership..."):
                    senate_leadership = scrape_house_leadership_senate()
                    assembly_leadership = scrape_house_leadership_national_assembly()

                    st.session_state.house_leadership = {
                        "senate": senate_leadership,
                        "assembly": assembly_leadership,
                    }

                    log.info(f"Leadership scrape complete: Senate={len(senate_leadership)}, Assembly={len(assembly_leadership)}")

                st.success(f"✓ Senate: {len(senate_leadership)} roles | Assembly: {len(assembly_leadership)} roles")

            except Exception as e:
                log.error(f"House leadership scrapers failed: {e}")
                st.error(f"Scraping failed: {e}")

    st.divider()

    # Display leadership data
    if st.session_state.house_leadership["senate"] or st.session_state.house_leadership["assembly"]:
        st.markdown("#### Leadership Positions")

        tab_senate, tab_assembly = st.tabs(["Senate Leadership", "Assembly Leadership"])

        with tab_senate:
            if st.session_state.house_leadership["senate"]:
                senate_df = pd.DataFrame(st.session_state.house_leadership["senate"])
                st.dataframe(senate_df, use_container_width=True)
            else:
                st.info("No Senate leadership data scraped yet")

        with tab_assembly:
            if st.session_state.house_leadership["assembly"]:
                assembly_df = pd.DataFrame(st.session_state.house_leadership["assembly"])
                st.dataframe(assembly_df, use_container_width=True)
            else:
                st.info("No Assembly leadership data scraped yet")

    # ── Other Scrapers ────────────────────────────────────────────────────────

    st.divider()
    st.markdown("#### Other Scrapers")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Member Lists**")
        if st.button("Run", key="scrape_members"):
            log.info("Member list scraper triggered (not yet implemented)")
            st.info("Member list scraper - coming soon")

    with col2:
        st.write("**Committee Leadership**")
        if st.button("Run", key="scrape_committee"):
            log.info("Committee leadership scraper triggered (not yet implemented)")
            st.info("Committee leadership scraper - coming soon")

    # ── Configuration ──────────────────────────────────────────────────────────

    st.markdown("#### Configuration")
    st.code(f"Base URL: {config['base_url']}", language="text")


def page_mineru_jobs():
    """Render MinerU extraction jobs page."""
    log.debug("Rendering MinerU extraction jobs page")

    config = get_config()

    st.markdown("### MinerU Extraction Jobs")

    st.markdown("#### Active Jobs")
    st.info("No active jobs. Upload data or start a scraper to process.")

    st.markdown("#### Job Configuration")
    if st.checkbox("Show MinerU API Configuration"):
        if config.get("mineru_api_key"):
            log.debug("MinerU API key is configured")
            st.success("MinerU API Key configured")
        else:
            log.warning("MinerU API key is not configured")
            st.warning("MinerU API Key not configured in secrets")


def page_transformations():
    """Render data transformation page."""
    log.debug("Rendering data transformations page")

    st.markdown("### Data Transformations")

    transformations = [
        "bill_trackers_builder",
        "member_lists_builder",
        "committee_leadership_builder",
        "house_leadership_builder",
    ]

    for transform in transformations:
        st.markdown(f"**{transform}**")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Pending Records", "0")
        with col2:
            st.metric("Processed", "0")


def page_database():
    """Render database management page."""
    log.debug("Rendering database management page")

    config = get_config()

    st.markdown("### Database Management")

    if config.get("neon_database_url"):
        log.debug("Database connection is configured")
        st.success("✓ Database connected")
    else:
        log.warning("Database URL is not configured in secrets")
        st.error("✗ Database URL not configured in secrets")

    st.markdown("#### Tables")
    st.info("Database schema will appear here once initialized")


# ── Navigation & Main ──────────────────────────────────────────────────────────


# Load configuration - validate early
try:
    config = get_config()
    log.info("Configuration loaded successfully")
except Exception as e:
    log.error(f"Failed to load configuration: {e}")
    st.error("Failed to load configuration. Check logs for details.")
    st.stop()


# Define pages
pages = [
    st.Page(page_dashboard, icon=":material/home:", title="Dashboard"),
    st.Page(page_scrapers, icon=":material/settings:", title="Scrapers"),
    st.Page(page_mineru_jobs, icon=":material/cloud_queue:", title="MinerU Jobs"),
    st.Page(page_transformations, icon=":material/transform:", title="Transformations"),
    st.Page(page_database, icon=":material/database:", title="Database"),
]

current_page = st.navigation(pages=pages, position="hidden")

# Create custom navigation bar
num_cols = max(len(pages) + 1, 6)
columns = st.columns(num_cols, vertical_alignment="bottom")

columns[0].write("**Legislation Leaderboard**")

for col, page in zip(columns[1:], pages):
    col.page_link(page, icon=page.icon)

st.title(f"{current_page.icon} {current_page.title}")

log.info(f"Rendering page: {current_page.title}")
current_page.run()

log.debug("Application render cycle complete")

