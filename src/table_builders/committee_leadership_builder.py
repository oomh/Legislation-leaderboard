"""Committee Leadership Table Builder

Specialized table builder for committee membership and leadership data.
Extracts committee names and member information from MinerU markdown outputs.
"""

import re
from typing import TypedDict, List, Dict, Any
from loguru import logger as log


class CommitteeMember(TypedDict):
    """Type definition for a committee member record."""

    committee_name: str
    member_number: int
    member_name: str
    honors: str
    position: str


# ── Text Parsing ───────────────────────────────────────────────────────────────


def parse_committee_leadership_markdown(markdown_content: str) -> List[CommitteeMember]:
    """Parse committee membership from markdown text format.
    
    Handles:
    - Committee headers marked with # A., # B., etc.
    - Numbered member lists with positions
    - Honors and designations (CBS, EGH, HSC, etc.)
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
    member_pattern = r"^\d+\.\s+(.+?)(?:\s+[-–]\s+(Chairperson|Vice-Chairperson|Chair|Vice-Chair))?\s*$"

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
            position_match = re.search(r"\s*[-–]\s+(Chairperson|Vice-Chairperson|Chair|Vice-Chair)(?:\s|$)", member_text)
            if position_match:
                position = position_match.group(1).strip()
                # Remove the position from member text
                member_text = member_text[:position_match.start()].strip()

            # Extract honors/designations (patterns like CBS, EGH, HSC, etc.)
            honors = ""
            honors_match = re.search(r",\s*([A-Z]{2,5}(?:\s+[A-Z]{2,5})?)\s*(?:,\s*M\.P\.)?$", member_text)
            if honors_match:
                honors = honors_match.group(1).strip()
                # Remove honors from name
                member_text = member_text[:honors_match.start()].strip()
            
            # Also handle M.P. suffix without honors code
            member_text = re.sub(r"\s*,?\s*M\.P\.?\s*$", "", member_text).strip()

            # Remove common titles from the beginning to get cleaner names
            titles_to_remove = r"^(?:The\s+(?:Rt\.\s+)?Hon\.(?:\s+\(Dr\.\)|\s+\(Prof\.\))?|Dr\.|Prof\.|The Rt\. Hon\.)\s+"
            member_name = re.sub(titles_to_remove, "", member_text).strip()

            if member_name:
                member_record: CommitteeMember = {
                    "committee_name": current_committee,
                    "member_number": len([m for m in all_members if m["committee_name"] == current_committee]) + 1,
                    "member_name": member_name,
                    "honors": honors,
                    "position": position,
                }
                all_members.append(member_record)

    log.info(f"Parsed {len(all_members)} committee members from {len(set(m['committee_name'] for m in all_members))} committees")

    return all_members


# ── Validation ──────────────────────────────────────────────────────────────────


def validate_and_clean_committee_members(
    members: List[CommitteeMember],
) -> List[CommitteeMember]:
    """Validate and clean extracted committee member records.
    
    Args:
        members: List of extracted member records
        
    Returns:
        Cleaned and validated member records
    """

    log.info(f"Validating {len(members)} committee members")

    cleaned_members: List[CommitteeMember] = []

    for member in members:
        # Skip if missing critical fields
        if not member["committee_name"] or not member["member_name"]:
            continue

        # Clean up whitespace
        member["member_name"] = " ".join(member["member_name"].split())
        member["committee_name"] = " ".join(member["committee_name"].split())
        member["honors"] = " ".join(member["honors"].split()) if member["honors"] else ""
        member["position"] = " ".join(member["position"].split()) if member["position"] else ""

        cleaned_members.append(member)

    log.info(f"Validation complete: {len(cleaned_members)} valid members")

    return cleaned_members


# ── Table Organization ──────────────────────────────────────────────────────────


def organize_by_committee(members: List[CommitteeMember]) -> List[Dict[str, Any]]:
    """Organize committee members into tables grouped by committee.
    
    Args:
        members: List of committee member records
        
    Returns:
        List of tables with committee_name and data fields
    """

    log.info("Organizing committee members into tables by committee")

    committees_dict: Dict[str, List[CommitteeMember]] = {}

    # Group members by committee
    for member in members:
        committee_name = member["committee_name"]
        if committee_name not in committees_dict:
            committees_dict[committee_name] = []
        committees_dict[committee_name].append(member)

    # Convert to list of tables
    tables = []
    for committee_name, committee_members in committees_dict.items():
        table_data = [dict(m) for m in committee_members]
        tables.append({
            "committee_name": committee_name,
            "row_count": len(table_data),
            "data": table_data,
        })

    log.info(f"Organized into {len(tables)} committee tables")

    return tables


# ── Main Builder ────────────────────────────────────────────────────────────────


def build_committee_leadership_table(
    mineru_markdown_path: str,
) -> Dict[str, Any]:
    """Complete workflow to extract and build committee leadership table from MinerU markdown output.
    
    Args:
        mineru_markdown_path: Path to MinerU full.md file for committee leadership
        
    Returns:
        Dict with status, table_count, and tables (list of committee tables)
    """

    log.info(f"Starting committee leadership table build from: {mineru_markdown_path}")

    try:
        # Read markdown file
        with open(mineru_markdown_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        # Parse members from markdown
        raw_members = parse_committee_leadership_markdown(markdown_content)

        # Validate and clean
        cleaned_members = validate_and_clean_committee_members(raw_members)

        # Organize into committee tables
        committee_tables = organize_by_committee(cleaned_members)

        log.info(
            f"Committee leadership table build successful: {len(committee_tables)} committees, {len(cleaned_members)} members extracted"
        )

        return {
            "status": "success",
            "table_count": len(committee_tables),
            "member_count": len(cleaned_members),
            "tables": committee_tables,
        }

    except Exception as e:
        log.error(f"Committee leadership table build failed: {e}")
        return {
            "status": "error",
            "table_count": 0,
            "member_count": 0,
            "tables": [],
            "error": str(e),
        }
