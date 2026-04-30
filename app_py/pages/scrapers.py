"""Scrapers Page

Manage and execute various data scrapers for bill trackers, leadership, and members.
"""

import streamlit as st
import pandas as pd
from loguru import logger as log
from src.config import get_config
from src.pipeline import (
    run_bill_trackers_scraping,
    run_house_leadership_scraping,
    run_member_lists_scraping,
    run_committee_leadership_scraping,
)
from app_py.helpers import run_all_scrapers


# ── Scrapers Page ─────────────────────────────────────────────────────────────


def _is_nonempty(val) -> bool:
    """Return True if val is a non-empty list, dict, or DataFrame."""
    if isinstance(val, pd.DataFrame):
        return not val.empty
    return bool(val)


def page_scrapers():
    """Render scrapers management page."""
    log.info("Navigating to scrapers page")

    config = get_config()

    with st.expander("Individual Scrapers"):
        st.markdown(
            "You can also run individual scrapers below. Note that some scrapers may take longer to run, especially if they are configured to scrape all pages of data."
        )

        col_bill_tracker, col_leadership, col_members, col_committees = st.columns(4)

        # ── Bill Trackers Button ──────────────────────────────────────────────────────

        with col_bill_tracker:
            if st.button(
                "Scrape Both Bill Trackers", key="scrape_both", width="content"
            ):
                with st.spinner("Scraping both bill trackers..."):
                    result = run_bill_trackers_scraping(page_only=True)

                if result["status"] == "success":
                    st.success(
                        f"✓ Senate: {result['senate_count']} PDFs | Assembly: {result['assembly_count']} PDFs"
                    )
                else:
                    st.error(
                        f"Scraping failed: {result.get('message', 'Unknown error')}"
                    )

        # ── House Leadership Button ───────────────────────────────────────────────────

        with col_leadership:
            with col_leadership:
                if st.button(
                    "Scrape House Leadership", key="scrape_leadership", width="content"
                ):
                    with st.spinner("Scraping house leadership..."):
                        result = run_house_leadership_scraping()

                    if result["status"] == "success":
                        st.success(
                            f"✓ Senate: {result['senate_count']} roles | Assembly: {result['assembly_count']} roles"
                        )
                    else:
                        st.error(
                            f"Scraping failed: {result.get('message', 'Unknown error')}"
                        )

        # ── Member Lists Button ────────────────────────────────────────────────────

        with col_members:
            if st.button(
                "Scrape Both Member Lists", key="scrape_members", width="content"
            ):
                with st.spinner("Scraping both member lists..."):
                    result = run_member_lists_scraping(page_only=False)

                if result["status"] == "success":
                    st.success(
                        f"✓ Senate: {result['senate_count']} members | Assembly: {result['assembly_count']} members"
                    )
                else:
                    st.error(
                        f"Scraping failed: {result.get('message', 'Unknown error')}"
                    )

        with col_committees:
            if st.button(
                "Scrape Committee Leadership", key="scrape_committees", width="content"
            ):
                with st.spinner("Scraping committee leadership..."):
                    result = run_committee_leadership_scraping()

                if result["status"] == "success":
                    st.success(f"✓ {result['count']} committee document(s) scraped")
                else:
                    st.error(
                        f"Scraping failed: {result.get('message', 'Unknown error')}"
                    )

    # ── Display All Results ────────────────────────────────────────────────────

    st.divider()
    st.markdown("#### Scraper Results")

    has_results = any(
        [
            _is_nonempty(st.session_state.bill_tracker_urls["senate"]),
            _is_nonempty(st.session_state.bill_tracker_urls["assembly"]),
            _is_nonempty(st.session_state.house_leadership["senate"]),
            _is_nonempty(st.session_state.house_leadership["assembly"]),
            _is_nonempty(st.session_state.member_lists["senate"]),
            _is_nonempty(st.session_state.member_lists["assembly"]),
            _is_nonempty(st.session_state.committee_leadership),
        ]
    )

    if not has_results:
        st.warning("No scraper results yet. Run scrapers above to populate results.")
    else:
        # Bill Trackers
        if _is_nonempty(st.session_state.bill_tracker_urls["senate"]) or _is_nonempty(
            st.session_state.bill_tracker_urls["assembly"]
        ):
            st.markdown("**Bill Trackers**")
            tab_senate, tab_assembly = st.tabs(["Senate", "National Assembly"])

            with tab_senate:
                if _is_nonempty(st.session_state.bill_tracker_urls["senate"]):
                    st.dataframe(
                        pd.DataFrame(st.session_state.bill_tracker_urls["senate"]),
                        width="content",
                    )
                else:
                    st.info("No Senate bill tracker data")

            with tab_assembly:
                if _is_nonempty(st.session_state.bill_tracker_urls["assembly"]):
                    st.dataframe(
                        pd.DataFrame(st.session_state.bill_tracker_urls["assembly"]),
                        width="content",
                    )
                else:
                    st.info("No National Assembly bill tracker data")

        # House Leadership
        if _is_nonempty(st.session_state.house_leadership["senate"]) or _is_nonempty(
            st.session_state.house_leadership["assembly"]
        ):
            st.markdown("**House Leadership**")
            tab_senate, tab_assembly = st.tabs(["Senate", "National Assembly"])

            with tab_senate:
                if _is_nonempty(st.session_state.house_leadership["senate"]):
                    st.dataframe(
                        pd.DataFrame(st.session_state.house_leadership["senate"]),
                        width="content",
                    )
                else:
                    st.info("No Senate leadership data")

            with tab_assembly:
                if _is_nonempty(st.session_state.house_leadership["assembly"]):
                    st.dataframe(
                        pd.DataFrame(st.session_state.house_leadership["assembly"]),
                        width="content",
                    )
                else:
                    st.info("No National Assembly leadership data")

        # Member Lists
        if _is_nonempty(st.session_state.member_lists["senate"]) or _is_nonempty(
            st.session_state.member_lists["assembly"]
        ):
            st.markdown("**Member Lists**")
            tab_senate, tab_assembly = st.tabs(["Senate", "National Assembly"])

            with tab_senate:
                if _is_nonempty(st.session_state.member_lists["senate"]):
                    st.dataframe(
                        pd.DataFrame(st.session_state.member_lists["senate"]),
                        width="content",
                    )
                else:
                    st.info("No Senate member data")

            with tab_assembly:
                if _is_nonempty(st.session_state.member_lists["assembly"]):
                    st.dataframe(
                        pd.DataFrame(st.session_state.member_lists["assembly"]),
                        width="content",
                    )
                else:
                    st.info("No National Assembly member data")

        # Committee Leadership
        if _is_nonempty(st.session_state.committee_leadership):
            st.markdown("**Committee Leadership**")
            st.dataframe(
                pd.DataFrame(st.session_state.committee_leadership), width="content"
            )

    # ── Master Control ────────────────────────────────────────────────────────

    st.divider()
    st.markdown("#### Master Control - Run All Scrapers")

    st.info(
        "GitHub Actions runs scrapers automatically on the 1st of each month. Use the button below to run manually."
    )

    if st.button("Run All Scrapers Now", key="run_all_scrapers", width="content"):
        log.info("Manual scraper run triggered")

        try:
            with st.spinner("Running all scrapers in parallel..."):
                results, errors = run_all_scrapers()

            st.session_state.bill_tracker_urls["senate"] = results.get(
                "Senate Bill Tracker", []
            )
            st.session_state.bill_tracker_urls["assembly"] = results.get(
                "Assembly Bill Tracker", []
            )
            st.session_state.house_leadership["senate"] = results.get(
                "Senate Leadership", []
            )
            st.session_state.house_leadership["assembly"] = results.get(
                "Assembly Leadership", []
            )
            st.session_state.member_lists["senate"] = results.get("Senate Members", [])
            st.session_state.member_lists["assembly"] = results.get(
                "Assembly Members", []
            )
            st.session_state.committee_leadership = results.get(
                "Committee Leadership", []
            )

            success_count = len(results)
            error_count = len(errors)
            st.success(
                f"Scraping complete: {success_count} successful, {error_count} failed"
            )

            if errors:
                with st.expander("View Errors"):
                    for name, error in errors.items():
                        st.error(f"{name}: {error}")

        except Exception as e:
            log.error(f"Parallel scraping failed: {e}")
            st.error(f"Scraping failed: {e}")
