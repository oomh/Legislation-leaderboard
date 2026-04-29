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
from src.scrapers.scrape_members import (
    scrape_senate_members,
    scrape_national_assembly_members,
)
from src.scrapers.scrape_committee_members_pdf import (
    scrape_committee_leadership,
)
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    
def _run_all_scrapers():
    """Run all scrapers in parallel using ThreadPoolExecutor."""
    scraper_tasks = {
        "Senate Bill Tracker": lambda: scrape_bill_tracker_senate(page_only=True),
        "Assembly Bill Tracker": lambda: scrape_bill_tracker_national_assembly(page_only=True),
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
            executor.submit(task): name 
            for name, task in scraper_tasks.items()
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


def page_scrapers():
    """Render scrapers management page."""
    log.info("Navigating to scrapers page")

    config = get_config()

    if "bill_tracker_urls" not in st.session_state:
        st.session_state.bill_tracker_urls = {"senate": [], "assembly": []}
    
    if "house_leadership" not in st.session_state:
        st.session_state.house_leadership = {"senate": [], "assembly": []}
    
    if "member_lists" not in st.session_state:
        st.session_state.member_lists = {"senate": [], "assembly": []}
    
    if "committee_leadership" not in st.session_state:
        st.session_state.committee_leadership = []


    with st.expander('Individual Scrapers'):
        st.markdown("You can also run individual scrapers below. Note that some scrapers may take longer to run, especially if they are configured to scrape all pages of data.")
        
        col_bill_tracker, col_leadership, col_members, col_committees  = st.columns(4)
        
        # ── Bill Trackers button ──────────────────────────────────────────────────────────

        with col_bill_tracker:
                if st.button("Scrape Both Bill Trackers", key="scrape_both", width='content'):
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
                        
                        
        # ── House Leadership button ──────────────────────────────────────────────────────────
        
        with col_leadership:
            with col_leadership:
                if st.button("Scrape House Leadership", key="scrape_leadership", width='content'):
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
                        
        # ── Member Lists button ──────────────────────────────────────────────────────────
        
        with col_members:
            if st.button("Scrape Both Member Lists", key="scrape_members", width='content'):
                log.info("Starting both member list scrapers (page 1 only)")

                try:
                    with st.spinner("Scraping both member lists..."):
                        senate_members = scrape_senate_members(page_only=False)
                        assembly_members = scrape_national_assembly_members(page_only=False)

                        st.session_state.member_lists = {
                            "senate": senate_members,
                            "assembly": assembly_members,
                        }

                        log.info(f"Both member scrapers complete: Senate={len(senate_members)}, Assembly={len(assembly_members)}")

                    st.success(f"✓ Senate: {len(senate_members)} members | Assembly: {len(assembly_members)} members")

                except Exception as e:
                    log.error(f"Member list scrapers failed: {e}")
                    st.error(f"Scraping failed: {e}")
                    
        # ── Committee Leadership button ──────────────────────────────────────────────────────────
        with col_committees:
            if st.button("Scrape Committee Leadership", key="scrape_committees", width='content'):
                log.info("Starting committee leadership scraper")

                try:
                    with st.spinner("Scraping committee leadership..."):
                        committee_docs = scrape_committee_leadership()

                        st.session_state.committee_leadership = committee_docs

                        log.info(f"Committee leadership scrape complete: {len(committee_docs)} documents")

                    st.success(f"✓ {len(committee_docs)} committee document(s) scraped")

                except Exception as e:
                    log.error(f"Committee leadership scraper failed: {e}")
                    st.error(f"Scraping failed: {e}")

    # ── Display All Results ────────────────────────────────────────────────────────

    st.divider()
    st.markdown("#### Scraper Results")

    has_results = any([
        st.session_state.bill_tracker_urls["senate"],
        st.session_state.bill_tracker_urls["assembly"],
        st.session_state.house_leadership["senate"],
        st.session_state.house_leadership["assembly"],
        st.session_state.member_lists["senate"],
        st.session_state.member_lists["assembly"],
        st.session_state.committee_leadership,
    ])

    if not has_results:
        st.warning("No scraper results yet. Run scrapers above to populate results.")
    else:
        # Bill Trackers
        if st.session_state.bill_tracker_urls["senate"] or st.session_state.bill_tracker_urls["assembly"]:
            st.markdown("**Bill Trackers**")
            tab_senate, tab_assembly = st.tabs(["Senate", "National Assembly"])
            
            with tab_senate:
                if st.session_state.bill_tracker_urls["senate"]:
                    st.dataframe(pd.DataFrame(st.session_state.bill_tracker_urls["senate"]), use_container_width=True)
                else:
                    st.info("No Senate bill tracker data")
            
            with tab_assembly:
                if st.session_state.bill_tracker_urls["assembly"]:
                    st.dataframe(pd.DataFrame(st.session_state.bill_tracker_urls["assembly"]), use_container_width=True)
                else:
                    st.info("No National Assembly bill tracker data")

        # House Leadership
        if st.session_state.house_leadership["senate"] or st.session_state.house_leadership["assembly"]:
            st.markdown("**House Leadership**")
            tab_senate, tab_assembly = st.tabs(["Senate", "National Assembly"])
            
            with tab_senate:
                if st.session_state.house_leadership["senate"]:
                    st.dataframe(pd.DataFrame(st.session_state.house_leadership["senate"]), use_container_width=True)
                else:
                    st.info("No Senate leadership data")
            
            with tab_assembly:
                if st.session_state.house_leadership["assembly"]:
                    st.dataframe(pd.DataFrame(st.session_state.house_leadership["assembly"]), use_container_width=True)
                else:
                    st.info("No National Assembly leadership data")

        # Member Lists
        if st.session_state.member_lists["senate"] or st.session_state.member_lists["assembly"]:
            st.markdown("**Member Lists**")
            tab_senate, tab_assembly = st.tabs(["Senate", "National Assembly"])
            
            with tab_senate:
                if st.session_state.member_lists["senate"]:
                    st.dataframe(pd.DataFrame(st.session_state.member_lists["senate"]), use_container_width=True)
                else:
                    st.info("No Senate member data")
            
            with tab_assembly:
                if st.session_state.member_lists["assembly"]:
                    st.dataframe(pd.DataFrame(st.session_state.member_lists["assembly"]), use_container_width=True)
                else:
                    st.info("No National Assembly member data")

        # Committee Leadership
        if st.session_state.committee_leadership:
            st.markdown("**Committee Leadership**")
            st.dataframe(pd.DataFrame(st.session_state.committee_leadership), use_container_width=True)

    # ── Master Control ────────────────────────────────────────────────────────

    st.divider()
    st.markdown("#### Master Control - Run All Scrapers")

    st.info("GitHub Actions runs scrapers automatically on the 1st of each month. Use the button below to run manually.")

    if st.button("Run All Scrapers Now", key="run_all_scrapers", width='content'):
        log.info("Manual scraper run triggered")

        try:
            with st.spinner("Running all scrapers in parallel..."):
                results, errors = _run_all_scrapers()

            st.session_state.bill_tracker_urls["senate"] = results.get("Senate Bill Tracker", [])
            st.session_state.bill_tracker_urls["assembly"] = results.get("Assembly Bill Tracker", [])
            st.session_state.house_leadership["senate"] = results.get("Senate Leadership", [])
            st.session_state.house_leadership["assembly"] = results.get("Assembly Leadership", [])
            st.session_state.member_lists["senate"] = results.get("Senate Members", [])
            st.session_state.member_lists["assembly"] = results.get("Assembly Members", [])
            st.session_state.committee_leadership = results.get("Committee Leadership", [])

            success_count = len(results)
            error_count = len(errors)
            st.success(f"Scraping complete: {success_count} successful, {error_count} failed")

            if errors:
                with st.expander("View Errors"):
                    for name, error in errors.items():
                        st.error(f"{name}: {error}")

        except Exception as e:
            log.error(f"Parallel scraping failed: {e}")
            st.error(f"Scraping failed: {e}")


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

