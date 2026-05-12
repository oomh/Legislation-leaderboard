"""
Configuration management for the legislation leaderboard pipeline.

Loads settings from Streamlit secrets or environment variables.
"""

import json
import os
import streamlit as st
from loguru import logger as log


def _secret(key: str, default=None):
    """Read a value from Streamlit secrets, falling back to os.environ."""
    try:
        value = st.secrets.get(key, None)
    except Exception:
        value = None
        
    if value is None:
        # Env fallback
        from dotenv import load_dotenv
        load_dotenv()  
        value = os.environ.get(key, default)
    return value


def get_config():
    """
    Load configuration from Streamlit secrets or environment variables.

    Returns:
        dict: Configuration dictionary with BASE_URL, SCRAPE_HEADERS, EXCLUDED_TITLES
    """
    config = {
        "base_url": _secret("BASE_URL", "https://www.parliament.go.ke"),
        "scrape_headers": _parse_headers(_secret("SCRAPE_HEADERS", "")),
        "excluded_titles": _secret("EXCLUDED_TITLES", []),
        "neon_database_url": _secret("NEON_DATABASE_URL"),
        "mineru_api_key": _secret("MINERU_API_KEY"),
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
