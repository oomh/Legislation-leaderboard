"""Dashboard Page

Main dashboard showing pipeline status and recent activity.
"""

import streamlit as st
from loguru import logger as log


# ── Dashboard Page ────────────────────────────────────────────────────────────


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
