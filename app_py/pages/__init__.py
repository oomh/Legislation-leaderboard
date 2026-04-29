"""Application Pages

Pages module containing all Streamlit page definitions.
"""

from app_py.pages.dashboard import page_dashboard
from app_py.pages.scrapers import page_scrapers
from app_py.pages.mineru_jobs import page_mineru_jobs
from app_py.pages.transformations import page_transformations
from app_py.pages.database import page_database

__all__ = [
    "page_dashboard",
    "page_scrapers",
    "page_mineru_jobs",
    "page_transformations",
    "page_database",
]
