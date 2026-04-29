"""Application Main Entry Point

Core application initialization and page orchestration.
"""

import streamlit as st
from loguru import logger as log
from src.config import get_config
from app_py.session_state import initialize_session_state
from app_py.navigation import get_pages, create_navigation_bar


# ── Application Entry Point ────────────────────────────────────────────────────


def configure_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="Legislation Leaderboard",
        page_icon="📋",
        layout="wide",
    )
    log.debug("Page configuration set")


def run_app():
    """Main application entry point."""
    log.info("Starting Legislation Leaderboard application")
    
    configure_page()
    initialize_session_state()

    # Load configuration - validate early
    try:
        config = get_config()
        log.info("Configuration loaded successfully")
    except Exception as e:
        log.error(f"Failed to load configuration: {e}")
        st.error("Failed to load configuration. Check logs for details.")
        st.stop()

    # Get pages and setup navigation
    pages = get_pages()
    current_page = st.navigation(pages=pages, position="hidden")
    
    create_navigation_bar(current_page, pages)
    
    st.title(f"{current_page.icon} {current_page.title}")

    log.info(f"Rendering page: {current_page.title}")
    current_page.run()

    log.debug("Application render cycle complete")
