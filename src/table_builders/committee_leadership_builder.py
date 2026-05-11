"""Committee Leadership Table Builder

Specialized table builder for committee membership and leadership data.
Extracts committee names and member information from MinerU markdown outputs.
"""

import re
import pandas as pd
from typing import TypedDict, List, Dict, Any
from loguru import logger as log
from .helper_functions import validate_records


class CommitteeMember(TypedDict):
    """Type definition for a committee member record."""

    committee_name: str
    member_name: str
    position: str


# ── Text Parsing ───────────────────────────────────────────────────────────────


def parse_committee_leadership_markdown(markdown_content: str) -> List[CommitteeMember]:
    """Parse committee membership from markdown text format.

    Handles:
    - Committee headers marked with # A., # B., etc.
    - Numbered member lists with positions
    - Chairperson and Vice-Chairperson roles

    Args:
        markdown_content: Full markdown content with committee information

    Returns:
        List of extracted committee member records
    """

    log.info("Starting committee leadership markdown parsing")

    all_members: List[CommitteeMember] = []
    lines = markdown_content.split("\n")

    current_committee = ""
    committee_pattern = r"^#\s+[A-Z]+\.\s+(.+)$"

    for line in lines:
        line = line.strip()

        if not line:
            continue

        # Check if this is a committee header
        committee_match = re.match(committee_pattern, line)
        if committee_match:
            current_committee = committee_match.group(1).strip()
            log.debug(f"Found committee: {current_committee}")
            continue

        # Check if this is a member line
        if current_committee and re.match(r"^\d+\.\s+", line):
            # Remove the number prefix
            member_text = re.sub(r"^\d+\.\s+", "", line).strip()

            # Extract position (Chairperson, Vice-Chairperson) marked with dash
            position = ""
            position_match = re.search(
                r"\s*[-–]\s*(Chairperson|Vice-Chairperson|Chair|Vice-Chair)(?:\s|$)",
                member_text,
                re.IGNORECASE,
            )
            if position_match:
                position = position_match.group(1).strip()
                # Remove the position from member text
                member_text = member_text[: position_match.start()].strip()

            member_name = member_text.strip()

            if member_name:
                member_record: CommitteeMember = {
                    "committee_name": current_committee,
                    "member_name": member_name,
                    "position": position if position else "",
                }
                all_members.append(member_record)

    log.info(
        f"Parsed {len(all_members)} committee members from {len(set(m['committee_name'] for m in all_members))} committees"
    )

    return all_members


# ── Table Organization ──────────────────────────────────────────────────────────


def build_single_committee_table(members: List[CommitteeMember]) -> Dict[str, Any]:
    """Build a single table with all committee members.

    Args:
        members: List of committee member records

    Returns:
        Dict with row_count and data fields
    """

    table_data = []
    for member in members:
        # Ensure all values are strings for proper serialization
        table_data.append(
            {
                "committee_name": str(member.get("committee_name", "")),
                "member_name": str(member.get("member_name", "")),
                "position": str(member.get("position", "")),
            }
        )

    log.info(f"Created single table with {len(table_data)} members")

    # Convert to DataFrame for consistency with bill builders
    committee_df = (
        pd.DataFrame(table_data)
        if table_data
        else pd.DataFrame(columns=["committee_name", "member_name", "position"])
    )

    return {
        "row_count": len(committee_df),
        "data": committee_df,
    }


# ── Main Builder ────────────────────────────────────────────────────────────────


def build_committee_leadership_table(
    mineru_markdown_path: str = "data/mineru_output_committee_leadership/full.md",
) -> Dict[str, Any]:
    """Complete workflow to extract and build committee leadership table from MinerU markdown output.

    Args:
        mineru_markdown_path: Path to MinerU full.md file for committee leadership

    Returns:
        Dict with status, row_count, and table data
    """

    log.info(f"Starting committee leadership table build from: {mineru_markdown_path}")

    try:
        # Read markdown file
        with open(mineru_markdown_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        # Parse members from markdown
        raw_members = parse_committee_leadership_markdown(markdown_content)

        # Validate and clean using shared validator
        members_list = [dict(m) for m in raw_members]
        cleaned_members = validate_records(members_list, key_col="member_name")

        # Build single table with all members
        table = build_single_committee_table(
            [CommitteeMember(**m) for m in cleaned_members]
        )

        log.info(
            f"Committee leadership table build successful: {len(cleaned_members)} members extracted"
        )

        return {
            "status": "success",
            "row_count": table["row_count"],
            "data": table["data"],  # Now returns DataFrame, not list
        }

    except Exception as e:
        log.error(f"Committee leadership table build failed: {e}")
        return {
            "status": "error",
            "row_count": 0,
            "data": pd.DataFrame(columns=["committee_name", "member_name", "position"]),
            "error": str(e),
        }
