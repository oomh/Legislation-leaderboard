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

    if "house_leadership" not in st.session_state:
        st.session_state.house_leadership = {"senate": [], "assembly": []}

    if "member_lists" not in st.session_state:
        st.session_state.member_lists = {"senate": [], "assembly": []}

    if "committee_leadership" not in st.session_state:
        st.session_state.committee_leadership = []

    if "table_builder_results" not in st.session_state:
        st.session_state.table_builder_results = None

    if "mineru_extraction_results" not in st.session_state:
        # Try to detect existing MinerU extraction results from disk
        detected_results = detect_mineru_extraction_results()
        if detected_results:
            st.session_state.mineru_extraction_results = detected_results
            log.info("Populated session state with existing MinerU extraction results")
        else:
            st.session_state.mineru_extraction_results = None