"""Database Page

Database management and schema configuration.
"""

import streamlit as st
from loguru import logger as log
from src.config import get_config


# ── Database Page ─────────────────────────────────────────────────────────────


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
