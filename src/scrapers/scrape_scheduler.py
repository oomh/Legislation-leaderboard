"""
Scheduling and timestamp management for scrapers.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger as log

# ── Constants ──────────────────────────────────────────────────────────────────

SCHEDULE_FILE = Path(__file__).parent.parent.parent / "scraper_schedule.json"


# ── Core Functions ────────────────────────────────────────────────────────────


def get_last_run_time() -> datetime | None:
    """
    Get the timestamp of the last successful scraper run.

    Returns:
        datetime object or None if never run
    """
    if not SCHEDULE_FILE.exists():
        return None

    try:
        with open(SCHEDULE_FILE, "r") as f:
            data = json.load(f)
        timestamp = data.get("last_run")
        if timestamp:
            return datetime.fromisoformat(timestamp)
    except Exception as e:
        log.warning(f"Error reading schedule file: {e}")

    return None


def update_last_run_time() -> None:
    """
    Update the last scraper run timestamp to now.
    """
    try:
        data = {"last_run": datetime.now().isoformat()}
        with open(SCHEDULE_FILE, "w") as f:
            json.dump(data, f, indent=2)
        log.info("Updated last scraper run timestamp")
    except Exception as e:
        log.error(f"Failed to update schedule file: {e}")


def days_until_next_run(days_interval: int = 30) -> int:
    """
    Calculate days until next scheduled run.

    Args:
        days_interval: Number of days between runs (default 30 for monthly)

    Returns:
        Number of days until next run (negative if overdue)
    """
    last_run = get_last_run_time()
    if last_run is None:
        return 0

    next_run = last_run + timedelta(days=days_interval)
    days_left = (next_run - datetime.now()).days
    return days_left


def is_scheduled_run_due(days_interval: int = 30) -> bool:
    """
    Check if a scheduled run is due (monthly check).

    Args:
        days_interval: Number of days between runs

    Returns:
        True if overdue for run
    """
    return days_until_next_run(days_interval) <= 0
