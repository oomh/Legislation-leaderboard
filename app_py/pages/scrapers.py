"""Scrapers Page

Manage and execute various data scrapers for bill trackers, leadership, and members.
"""

import streamlit as st
import pandas as pd
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
from src.scrapers.scrape_committee_members_pdf import scrape_committee_leadership
from app_py.helpers import run_all_scrapers


# ── Scrapers Page ─────────────────────────────────────────────────────────────


def page_scrapers():
    """Render scrapers management page."""
    log.info("Navigating to scrapers page")

    config = get_config()

    with st.expander('Individual Scrapers'):
        st.markdown("You can also run individual scrapers below. Note that some scrapers may take longer to run, especially if they are configured to scrape all pages of data.")
        
        col_bill_tracker, col_leadership, col_members, col_committees  = st.columns(4)
        
        # ── Bill Trackers Button ──────────────────────────────────────────────────────

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
                        
                        
        # ── House Leadership Button ───────────────────────────────────────────────────
        
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
                        
        # ── Member Lists Button ────────────────────────────────────────────────────
        
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
                    
        # ── Committee Leadership Button ────────────────────────────────────────────────
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

    # ── Display All Results ────────────────────────────────────────────────────

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
                    st.dataframe(pd.DataFrame(st.session_state.bill_tracker_urls["senate"]), width='content')
                else:
                    st.info("No Senate bill tracker data")
            
            with tab_assembly:
                if st.session_state.bill_tracker_urls["assembly"]:
                    st.dataframe(pd.DataFrame(st.session_state.bill_tracker_urls["assembly"]), width='content')
                else:
                    st.info("No National Assembly bill tracker data")

        # House Leadership
        if st.session_state.house_leadership["senate"] or st.session_state.house_leadership["assembly"]:
            st.markdown("**House Leadership**")
            tab_senate, tab_assembly = st.tabs(["Senate", "National Assembly"])
            
            with tab_senate:
                if st.session_state.house_leadership["senate"]:
                    st.dataframe(pd.DataFrame(st.session_state.house_leadership["senate"]), width='content')
                else:
                    st.info("No Senate leadership data")
            
            with tab_assembly:
                if st.session_state.house_leadership["assembly"]:
                    st.dataframe(pd.DataFrame(st.session_state.house_leadership["assembly"]), width='content')
                else:
                    st.info("No National Assembly leadership data")

        # Member Lists
        if st.session_state.member_lists["senate"] or st.session_state.member_lists["assembly"]:
            st.markdown("**Member Lists**")
            tab_senate, tab_assembly = st.tabs(["Senate", "National Assembly"])
            
            with tab_senate:
                if st.session_state.member_lists["senate"]:
                    st.dataframe(pd.DataFrame(st.session_state.member_lists["senate"]), width='content')
                else:
                    st.info("No Senate member data")
            
            with tab_assembly:
                if st.session_state.member_lists["assembly"]:
                    st.dataframe(pd.DataFrame(st.session_state.member_lists["assembly"]), width='content')
                else:
                    st.info("No National Assembly member data")

        # Committee Leadership
        if st.session_state.committee_leadership:
            st.markdown("**Committee Leadership**")
            st.dataframe(pd.DataFrame(st.session_state.committee_leadership), width='content')

    # ── Master Control ────────────────────────────────────────────────────────

    st.divider()
    st.markdown("#### Master Control - Run All Scrapers")

    st.info("GitHub Actions runs scrapers automatically on the 1st of each month. Use the button below to run manually.")

    if st.button("Run All Scrapers Now", key="run_all_scrapers", width='content'):
        log.info("Manual scraper run triggered")

        try:
            with st.spinner("Running all scrapers in parallel..."):
                results, errors = run_all_scrapers()

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
