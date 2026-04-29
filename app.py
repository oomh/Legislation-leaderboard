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

# ============================================================================
# Initialization & Configuration
# ============================================================================

log.info("Starting Legislation Leaderboard application")

st.set_page_config(
    page_title="Legislation Leaderboard",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

log.debug("Page configuration set")


# ============================================================================
# Page Renderers
# ============================================================================

def _render_dashboard():
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


def _render_scrapers_page(config):
    """Render scrapers management page."""
    log.info("Navigating to scrapers page")

    # ── Initialize session state ──────────────────────────────────────────────

    if "bill_tracker_urls" not in st.session_state:
        st.session_state.bill_tracker_urls = {"senate": [], "assembly": []}
    
    if "house_leadership" not in st.session_state:
        st.session_state.house_leadership = {"senate": [], "assembly": []}

    st.markdown("### Scraper Management")

    # ── Bill Trackers ──────────────────────────────────────────────────────────

    st.markdown("#### Bill Trackers")

    # Scrape both button
    col_both = st.columns(1)[0]
    with col_both:
        if st.button("Scrape Both (Page 1 Only)", key="scrape_both", use_container_width=True):
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

    # Individual scrapers
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Senate Bill Tracker**")
        if st.button("Run Senate Scraper", key="scrape_senate"):
            log.info("Starting Senate bill tracker scrape (page 1 only)")
            try:
                with st.spinner("Scraping Senate bill tracker..."):
                    pdfs = scrape_bill_tracker_senate(page_only=True)
                    st.session_state.bill_tracker_urls["senate"] = pdfs
                    log.info(f"Senate scrape complete: {len(pdfs)} PDFs found")

                st.success(f"Found {len(pdfs)} Senate bill tracker PDFs")
                if pdfs:
                    with st.expander("View Senate PDFs"):
                        for pdf in pdfs:
                            st.write(f"- {pdf['title']}")
                            st.write(f"  URL: {pdf['url']}")
            except Exception as e:
                log.error(f"Senate scraper failed: {e}")
                st.error(f"Scraping failed: {e}")

    with col2:
        st.write("**National Assembly Bill Tracker**")
        if st.button("Run Assembly Scraper", key="scrape_assembly"):
            log.info("Starting National Assembly bill tracker scrape (page 1 only)")
            try:
                with st.spinner("Scraping National Assembly bill tracker..."):
                    pdfs = scrape_bill_tracker_national_assembly(page_only=True)
                    st.session_state.bill_tracker_urls["assembly"] = pdfs
                    log.info(f"Assembly scrape complete: {len(pdfs)} PDFs found")

                st.success(f"Found {len(pdfs)} National Assembly bill tracker PDFs")
                if pdfs:
                    with st.expander("View Assembly PDFs"):
                        for pdf in pdfs:
                            st.write(f"- {pdf['title']}")
                            st.write(f"  URL: {pdf['url']}")
            except Exception as e:
                log.error(f"Assembly scraper failed: {e}")
                st.error(f"Scraping failed: {e}")

    # ── Stored URLs Summary ────────────────────────────────────────────────────

    st.divider()
    st.markdown("#### Latest Scraped URLs (for MinerU)")

    if st.session_state.bill_tracker_urls["senate"] or st.session_state.bill_tracker_urls["assembly"]:
        col_senate, col_assembly = st.columns(2)

        with col_senate:
            if st.session_state.bill_tracker_urls["senate"]:
                st.write(f"**Senate:** {len(st.session_state.bill_tracker_urls['senate'])} URLs")
                with st.expander("View Senate URLs"):
                    for url in st.session_state.bill_tracker_urls["senate"]:
                        st.write(f"- {url['title']}: {url['url']}")

        with col_assembly:
            if st.session_state.bill_tracker_urls["assembly"]:
                st.write(f"**Assembly:** {len(st.session_state.bill_tracker_urls['assembly'])} URLs")
                with st.expander("View Assembly URLs"):
                    for url in st.session_state.bill_tracker_urls["assembly"]:
                        st.write(f"- {url['title']}: {url['url']}")
    else:
        st.info("No URLs scraped yet. Click 'Scrape Both' or run individual scrapers.")

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


def _render_mineru_page(config):
    """Render MinerU extraction jobs page."""
    log.debug("Rendering MinerU extraction jobs page")

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


def _render_transformations_page():
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


def _render_database_page(config):
    """Render database management page."""
    log.debug("Rendering database management page")

    st.markdown("### Database Management")

    if config.get("neon_database_url"):
        log.debug("Database connection is configured")
        st.success("✓ Database connected")
    else:
        log.warning("Database URL is not configured in secrets")
        st.error("✗ Database URL not configured in secrets")

    st.markdown("#### Tables")
    st.info("Database schema will appear here once initialized")


# ============================================================================
# Main Application
# ============================================================================

def main():
    """Main application entry point."""
    log.info("Initializing main application")

    st.title("📋 Legislation Leaderboard")
    st.subheader("Data Pipeline Orchestrator")

    # Load configuration
    try:
        config = get_config()
        log.info("Configuration loaded successfully")
    except Exception as e:
        log.error(f"Failed to load configuration: {e}")
        st.error("Failed to load configuration. Check logs for details.")
        return

    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Select Page",
            ["Dashboard", "Scrapers", "MinerU Jobs", "Transformations", "Database"],
        )

    log.debug(f"User selected page: {page}")

    # Page routing
    if page == "Dashboard":
        _render_dashboard()
    elif page == "Scrapers":
        _render_scrapers_page(config)
    elif page == "MinerU Jobs":
        _render_mineru_page(config)
    elif page == "Transformations":
        _render_transformations_page()
    elif page == "Database":
        _render_database_page(config)


if __name__ == "__main__":
    log.info("Application started")
    main()
    log.debug("Application render cycle complete")

