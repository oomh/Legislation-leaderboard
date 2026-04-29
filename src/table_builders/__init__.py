"""
Table Builders Package

Extracts HTML tables from MinerU markdown outputs and converts them to structured data.
Includes specialized builders for different document types.
"""

from src.table_builders.markdown_parser import parse_mineru_markdown, extract_table_from_markdown
from src.table_builders.senate_bills_builder import build_senate_bills_table
from src.table_builders.assembly_bills_builder import build_assembly_bills_table
from src.table_builders.orchestration import build_tables_from_mineru_output

__all__ = [
    "parse_mineru_markdown",
    "extract_table_from_markdown",
    "build_senate_bills_table",
    "build_tables_from_mineru_output",
]
