"""
Database connection helpers for the Neon PostgreSQL database.

Uses psycopg (v3) with the connection URL stored in Streamlit secrets
or the NEON_DATABASE_URL environment variable.
"""

from contextlib import contextmanager

import psycopg
from loguru import logger as log

from src.config import get_config


def _get_url() -> str:
    url = get_config().get("neon_database_url")
    if not url:
        raise RuntimeError(
            "NEON_DATABASE_URL is not configured. "
            "Add it to .streamlit/secrets.toml or set the environment variable."
        )
    return url


def get_connection() -> psycopg.Connection:
    """Return an open psycopg connection to the Neon database.

    The caller is responsible for closing the connection.
    Prefer get_cursor() for transactional work.
    """
    url = _get_url()
    log.info("Connecting to Neon database.")
    return psycopg.connect(url)


@contextmanager
def get_cursor():
    """Context manager that yields a psycopg cursor inside a transaction.

    Commits on success, rolls back on exception, and always closes the
    connection.

    Usage::

        with get_cursor() as cur:
            cur.execute("SELECT 1")
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
