"""Session State Management

Initialize and manage Streamlit session state for all pages.
"""

import streamlit as st
from loguru import logger as log
from app_py.helpers import detect_mineru_extraction_results


# ── Session State ──────────────────────────────────────────────────────────────


def initialize_session_state():
    """Initialize all session state variables for the application."""
    if "bill_tracker_urls" not in st.session_state:
        st.session_state.bill_tracker_urls = {"senate": [], "assembly": []}

    if "bill_trackers_processed" not in st.session_state:
        st.session_state.bill_trackers_processed = {"senate": [], "assembly": []}

    if "house_leadership" not in st.session_state:
        st.session_state.house_leadership = {"senate": [], "assembly": []}

    if "member_lists" not in st.session_state:
        st.session_state.member_lists = {"senate": [], "assembly": []}

    if "committee_leadership" not in st.session_state:
        st.session_state.committee_leadership = []

    if "table_builder_results" not in st.session_state:
        st.session_state.table_builder_results = None

    # Step 3 outputs: Raw extracted tables from MinerU data
    if "raw_senate_bills" not in st.session_state:
        st.session_state.raw_senate_bills = None

    if "raw_assembly_bills" not in st.session_state:
        st.session_state.raw_assembly_bills = None

    if "raw_committee_membership" not in st.session_state:
        st.session_state.raw_committee_membership = None

    if "mineru_extraction_results" not in st.session_state:
        # Try to detect existing MinerU extraction results from disk
        detected_results = detect_mineru_extraction_results()
        if detected_results:
            st.session_state.mineru_extraction_results = detected_results
            log.info("Populated session state with existing MinerU extraction results")
        else:
            st.session_state.mineru_extraction_results = None
