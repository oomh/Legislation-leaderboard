"""Assembly Bills Sponsor Splitter

Normalises assembly bill tracker rows so that each row has exactly one sponsor.

Bills are first partitioned into three non-overlapping subsets:
    1. Office-sponsored bills  — sponsor contains a role keyword (leader, chairperson majority, minority, speaker)
    2. Multi-sponsored bills   — sponsor names more than one individual (no role keyword)
    3. Residue bills           — already have exactly one individual sponsor

Each subset is then processed independently before being reassembled via
``rebuild_assembly_bills``.

Pipeline role: Step 5 — sponsor normalisation before member matching.
"""

import re

import pandas as pd
from loguru import logger as log


OFFICE_KEYWORDS: list[str] = [
    "leader",
    "chairperson",
    "the chairperson",
    "majority",
    "minority",
    "speaker",
]

_OFFICE_PATTERN = re.compile("|".join(OFFICE_KEYWORDS), re.IGNORECASE)
_AND_PATTERN = re.compile(r"\s+and\s+", re.IGNORECASE)
# Match ', And ', ', & ', ', ', ' and ', ' & ' all as single separator tokens.
# The optional (?:(?:and|&)\s+) after the comma ensures ', And ' is consumed
# in one pass so that 'And Y' fragments are never left behind.
_COMMA_AND_PATTERN = re.compile(r",\s*(?:(?:and|&)\s+)?|\s+(?:and|&)\s+", re.IGNORECASE)


# ── Predicate helpers ──────────────────────────────────────────────────────


def _is_office_sponsor(sponsor: str) -> bool:
    """Return True if the sponsor string contains an office-role keyword."""
    return bool(_OFFICE_PATTERN.search(str(sponsor)))


def _has_multiple_names(sponsor: str) -> bool:
    """Return True if the sponsor string appears to name more than one person.

    Detects commas or the word ' and ' as separators.
    """
    return bool(_COMMA_AND_PATTERN.search(str(sponsor)))


# ── Partition functions ────────────────────────────────────────────────────────


def extract_office_sponsored_bills(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows where the sponsor contains an office-role keyword.

    Args:
        df: Assembly bills DataFrame with a 'sponsor' column.

    Returns:
        Subset of rows whose sponsor contains an office-role keyword.
    """
    mask = df["sponsor"].apply(_is_office_sponsor)
    result = df[mask].copy()
    log.info(f"Office-sponsored bills extracted: {len(result)} rows")
    return result


def extract_multi_sponsored_bills(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows whose sponsor names more than one individual.

    Office-role rows must already be excluded before calling this function.

    Args:
        df: Assembly bills DataFrame with office-sponsored rows removed.

    Returns:
        Subset of rows with multiple individual sponsors.
    """
    mask = df["sponsor"].apply(_has_multiple_names)
    result = df[mask].copy()
    log.info(f"Multi-sponsored bills extracted: {len(result)} rows")
    return result


def extract_residue_bills(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows that already carry exactly one clean individual sponsor.

    Office-role rows must already be excluded before calling this function.

    Args:
        df: Assembly bills DataFrame with office-sponsored rows removed.

    Returns:
        Residue rows — each already has a single sponsor.
    """
    mask = ~df["sponsor"].apply(_has_multiple_names)
    result = df[mask].copy()
    log.info(f"Residue (single-sponsor) bills extracted: {len(result)} rows")
    return result


def partition_assembly_bills(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split assembly bills into three non-overlapping subsets.

    Partition order:
    1. Office-sponsored bills  (sponsor contains a role keyword)
    2. Multi-sponsored bills   (multiple individual names, no role keyword)
    3. Residue bills           (exactly one individual sponsor)

    Args:
        df: Transformed assembly bills DataFrame with a 'sponsor' column.

    Returns:
        Tuple of (office_bills, multi_bills, residue_bills).
    """
    office = extract_office_sponsored_bills(df)
    remainder = df[~df.index.isin(office.index)]
    multi = extract_multi_sponsored_bills(remainder)
    residue = extract_residue_bills(remainder)
    log.info(
        f"Partition complete: {len(office)} office, {len(multi)} multi, {len(residue)} residue"
        f" (total {len(office) + len(multi) + len(residue)} / {len(df)})"
    )
    return office, multi, residue


# ── Split / explode functions ──────────────────────────────────────────────────


_CHAIRPERSON_PATTERN = re.compile(r"^\s*chairperson", re.IGNORECASE)


def split_office_sponsors(df: pd.DataFrame) -> pd.DataFrame:
    """Explode office-sponsored rows on ' and ' when multiple entries are present.

    Rows whose sponsor starts with 'Chairperson' are kept as-is because their
    committee names often contain ' and ' (e.g. 'Chairperson, Committee on
    Agriculture and Livestock'), which would produce false splits.

    # TODO: Research and implement proper splitting for chairperson-sponsored bills.
    #       Options include: splitting only on ' and ' that is followed by a
    #       capitalised word not part of a known committee pattern, or maintaining
    #       a lookup of committee names to exclude from splitting.

    Rows whose sponsor does not contain ' and ' are kept as a single-element list
    and therefore remain unchanged after the explode.

    Args:
        df: Office-sponsored bills DataFrame.

    Returns:
        DataFrame where each row has a single sponsor entry.
    """

    def _split_on_and(sponsor: str) -> list[str]:
        # Chairperson sponsors are returned as-is to avoid splitting committee names
        if _CHAIRPERSON_PATTERN.match(str(sponsor)):
            return [sponsor.strip()]
        parts = _AND_PATTERN.split(str(sponsor))
        # Strip trailing commas left when ', And ' was the original separator
        return [p.strip().strip(",").strip() for p in parts if p.strip().strip(",").strip()]

    expanded = df.copy()
    expanded["sponsor"] = expanded["sponsor"].apply(_split_on_and)
    result = expanded.explode("sponsor").reset_index(drop=True)
    log.info(f"Office bills after splitting: {len(result)} rows (was {len(df)})")
    return result


def split_multi_sponsors(df: pd.DataFrame) -> pd.DataFrame:
    """Explode multi-sponsored rows by splitting on commas and ' and '.

    Args:
        df: Multi-sponsored bills DataFrame.

    Returns:
        DataFrame where each row has a single sponsor entry.
    """

    def _split_on_comma_and(sponsor: str) -> list[str]:
        parts = _COMMA_AND_PATTERN.split(str(sponsor))
        # Strip stray leading/trailing commas or whitespace from each piece
        return [p.strip().strip(",").strip() for p in parts if p.strip().strip(",").strip()]

    expanded = df.copy()
    expanded["sponsor"] = expanded["sponsor"].apply(_split_on_comma_and)
    result = expanded.explode("sponsor").reset_index(drop=True)
    
    log.info(f"Multi-sponsor bills after splitting: {len(result)} rows (was {len(df)})")
    return result


# ── Rebuild ────────────────────────────────────────────────────────────────────


def rebuild_assembly_bills(
    office_bills: pd.DataFrame,
    multi_bills: pd.DataFrame,
    residue_bills: pd.DataFrame,
    include_office: bool = True,
    include_multi: bool = True,
    include_residue: bool = True,
) -> pd.DataFrame:
    """Reassemble the three processed bill subsets into one unified DataFrame.

    Pass ``include_*=False`` to exclude a subset from the rebuild.

    Args:
        office_bills: Processed office-sponsored bills (already split).
        multi_bills: Processed multi-sponsored bills (already split).
        residue_bills: Residue bills (already single-sponsor, taken as-is).
        include_office: Include office-sponsored bills in the output.
        include_multi: Include multi-sponsored bills in the output.
        include_residue: Include residue bills in the output.

    Returns:
        Concatenated DataFrame with one sponsor per row and a reset index.
    """
    parts: list[pd.DataFrame] = []

    if include_office:
        parts.append(office_bills)
    if include_multi:
        parts.append(multi_bills)
    if include_residue:
        parts.append(residue_bills)

    if not parts:
        log.warning("No subsets selected for rebuild — returning empty DataFrame")
        return pd.DataFrame()

    result = pd.concat(parts, ignore_index=True)
    log.info(f"Rebuilt assembly bills: {len(result)} rows total")
    return result
