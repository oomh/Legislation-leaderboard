"""
Configuration management for the legislation leaderboard pipeline.

Loads settings from Streamlit secrets or environment variables.
"""

import json
import streamlit as st
from loguru import logger as log


def get_config():
    """
    Load configuration from Streamlit secrets.

    Returns:
        dict: Configuration dictionary with BASE_URL, SCRAPE_HEADERS, EXCLUDED_TITLES
    """
    config = {
        "base_url": st.secrets.get("BASE_URL", "https://www.parliament.go.ke"),
        "scrape_headers": _parse_headers(st.secrets.get("SCRAPE_HEADERS", "")),
        "excluded_titles": st.secrets.get("EXCLUDED_TITLES", []),
        "neon_database_url": st.secrets.get("NEON_DATABASE_URL"),
        "mineru_api_key": st.secrets.get("MINERU_API_KEY"),
    }
    return config


def _parse_headers(headers_str):
    """
    Parse JSON headers string into dictionary.

    Args:
        headers_str: JSON string of headers

    Returns:
        dict: Parsed headers dictionary
    """
    if isinstance(headers_str, dict):
        return headers_str
    try:
        return json.loads(headers_str)
    except (json.JSONDecodeError, TypeError):
        return {}
