"""Navigation Setup

Configure navigation between application pages.
"""

import streamlit as st
from loguru import logger as log
from app_py.pages import (
    page_build_tables,
    page_scrapers,
    page_mineru_jobs,
    page_transformations,
    page_database,
)


# ── Navigation Setup ──────────────────────────────────────────────────────────


def get_pages():
    """Get list of all application pages."""
    pages = [
        st.Page(page_build_tables, icon=":material/build:", title="Build Tables"),
        st.Page(page_scrapers, icon=":material/settings:", title="Scrapers"),
        st.Page(page_mineru_jobs, icon=":material/cloud_queue:", title="MinerU Jobs"),
        st.Page(page_transformations, icon=":material/transform:", title="Transformations"),
        st.Page(page_database, icon=":material/database:", title="Database"),
    ]
    return pages


def create_navigation_bar(current_page, pages):
    """Create custom navigation bar."""
    num_cols = max(len(pages) + 1, 6)
    columns = st.columns(num_cols, vertical_alignment="bottom")

    columns[0].write("**Legislation Leaderboard**")

    for col, page in zip(columns[1:], pages):
        col.page_link(page, icon=page.icon)
