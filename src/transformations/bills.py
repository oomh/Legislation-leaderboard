"""Bills Transformers and Sponsor Splitters

Transforms raw bill tracker DataFrames extracted by MinerU and normalises
sponsor columns so that each row has exactly one sponsor.

Public API
----------
Transformers:
    transform_senate_bills(raw_df)   -> result dict
    transform_assembly_bills(raw_df) -> result dict

Assembly sponsor splitter (same names as the old assembly_bills_sponsor_splitter module):
    partition_assembly_bills, extract_office_sponsored_bills,
    extract_multi_sponsored_bills, extract_residue_bills,
    split_office_sponsors, split_multi_sponsors, rebuild_assembly_bills

Senate sponsor splitter:
    partition_senate_bills, extract_senate_office_sponsored_bills,
    extract_senate_multi_sponsored_bills, extract_senate_residue_bills,
    split_senate_office_sponsors, split_senate_multi_sponsors, rebuild_senate_bills
"""

import re

import pandas as pd
from loguru import logger as log

from src.transformations.transformation_helpers import (
    apply_mask_to_dataframe,
    apply_name_parsing,
    create_mask_for_strings,
    fix_shifted_serial_rows,
    merge_duplicate_serial_rows,
    merge_spill_rows,
    strip_cell_punctuation,
)

# ── Column constants ───────────────────────────────────────────────────────────

SENATE_BILL_COLUMNS: list[str] = [
    "no.",
    "bill",
    "sponsor",
    "gazette no.",
    "date of publication",
    "maturity",
    "date 1st read",
    "sc committee referred to",
    "date 2nd read",
    "cotw/ 3rd read",
    "date of assent",
    "remarks",
]

ASSEMBLY_BILL_COLUMNS: list[str] = [
    "s/no.",
    "bill",
    "sponsor",
    "na/sen. bill no.",
    "dated",
    "maturity date",
    "gazette no.",
    "1st read",
    "2nd read",
    "3rd read",
    "remarks",
    "assent",
]

# ── Header-removal constants (per chamber) ────────────────────────────────────

_SENATE_HEADER_STRINGS: list[str] = [
    "no.",
    "sc committee referred to",
]
_SENATE_HEADER_SEARCH_COLS: list[str] = ["no.", "sc committee referred to"]

_ASSEMBLY_HEADER_STRINGS: list[str] = [
    "S/No/",
    "MATURITY DATE",
    "GAZETTE NO",
]
_ASSEMBLY_HEADER_SEARCH_COLS: list[str] = ["MATURITY DATE"]

# ── Sponsor-splitter constants (per chamber) ──────────────────────────────────

_SENATE_OFFICE_KEYWORDS: list[str] = [
    "leader",
    "chairperson",
    "the chairperson",
    "majority",
    "minority",
]
_ASSEMBLY_OFFICE_KEYWORDS: list[str] = [
    "leader",
    "chairperson",
    "the chairperson",
    "majority",
    "minority",
    "speaker",
]

_SENATE_OFFICE_PATTERN = re.compile("|".join(_SENATE_OFFICE_KEYWORDS), re.IGNORECASE)
_ASSEMBLY_OFFICE_PATTERN = re.compile(
    "|".join(_ASSEMBLY_OFFICE_KEYWORDS), re.IGNORECASE
)

_AND_PATTERN = re.compile(r"\s+and\s+", re.IGNORECASE)
# Match ', And ', ', & ', ', ', ' and ', ' & ' as single separator tokens.
_COMMA_AND_PATTERN = re.compile(r",\s*(?:(?:and|&)\s+)?|\s+(?:and|&)\s+", re.IGNORECASE)

# Senate also matches "The Chairperson ..."
_SENATE_CHAIRPERSON_PATTERN = re.compile(r"^\s*(?:the\s*)?chairperson", re.IGNORECASE)
_ASSEMBLY_CHAIRPERSON_PATTERN = re.compile(r"^\s*chairperson", re.IGNORECASE)


# ── Shared private: bill transformation pipeline ──────────────────────────────


def _transform_bills(
    raw_df: pd.DataFrame,
    columns: list[str],
    header_strings: list[str],
    header_search_cols: list[str],
    serial_col: str,
    chamber_name: str,
    spill_before_duplicate: bool = True,
) -> dict:
    """Shared bill transformation pipeline used by both chamber wrappers.

    Steps:
    1. Rename generic integer column indices to canonical names.
    2. Drop any leftover integer-named columns.
    3. Remove embedded header rows.
    4. Fix shifted serial rows.
    5. Merge spill rows and duplicate serial rows (order controlled by
        spill_before_duplicate).
    6. Parse sponsor names and strip cell punctuation.
    """
    try:
        if raw_df is None or raw_df.empty:
            log.warning(
                f"_transform_bills: received empty DataFrame for {chamber_name}"
            )
            return {
                "status": "success",
                "data": pd.DataFrame(),
                "row_count": 0,
                "message": f"No {chamber_name} bills data to transform",
            }

        log.info(f"Transforming {chamber_name} bills: {len(raw_df)} raw rows")

        n_cols = len(raw_df.columns)
        col_map = {old: new for old, new in zip(raw_df.columns, columns[:n_cols])}
        df = raw_df.copy().rename(columns=col_map)
        extra_cols = [c for c in df.columns if isinstance(c, int)]
        if extra_cols:
            df = df.drop(columns=extra_cols)
        log.info(f"Renamed {n_cols} {chamber_name} bill columns")

        active_search_cols = [c for c in header_search_cols if c in df.columns]
        mask = create_mask_for_strings(
            df,
            search_strings=header_strings,
            columns=active_search_cols,
            case_sensitive=False,
        )
        df = apply_mask_to_dataframe(df, mask)

        log.debug(f"columns after header removal: {df.columns.tolist()}")

        df = fix_shifted_serial_rows(df, serial_col=serial_col)
        
        if spill_before_duplicate:
            df = merge_spill_rows(df, serial_col=serial_col)
            df = merge_duplicate_serial_rows(df, serial_col=serial_col)
        else:
            df = merge_duplicate_serial_rows(df, serial_col=serial_col)
            df = merge_spill_rows(df, serial_col=serial_col)

        df["sponsor"] = apply_name_parsing(df, columns=["sponsor"])["sponsor"]
        df = strip_cell_punctuation(df)

        row_count = len(df)
        log.info(
            f"{chamber_name.title()} bills transformation complete: {row_count} rows retained"
        )

        return {
            "status": "success",
            "data": df,
            "row_count": row_count,
            "message": f"Transformed {row_count} {chamber_name} bill records",
        }
    except Exception as e:
        log.error(f"{chamber_name.title()} bills transformation failed: {e}")
        return {
            "status": "error",
            "data": pd.DataFrame(),
            "row_count": 0,
            "message": str(e),
        }


# ── Public transformers ────────────────────────────────────────────────────────


def transform_senate_bills(raw_df: pd.DataFrame) -> dict:
    """Transform the raw senate bills DataFrame.

    Returns:
        Dict with keys: status, data (pd.DataFrame), row_count, message.
    """
    return _transform_bills(
        raw_df,
        columns=SENATE_BILL_COLUMNS,
        header_strings=_SENATE_HEADER_STRINGS,
        header_search_cols=_SENATE_HEADER_SEARCH_COLS,
        serial_col="no.",
        chamber_name="senate",
        spill_before_duplicate=True,
    )


def transform_assembly_bills(raw_df: pd.DataFrame) -> dict:
    """Transform the raw assembly bills DataFrame.

    Returns:
        Dict with keys: status, data (pd.DataFrame), row_count, message.
    """
    return _transform_bills(
        raw_df,
        columns=ASSEMBLY_BILL_COLUMNS,
        header_strings=_ASSEMBLY_HEADER_STRINGS,
        header_search_cols=_ASSEMBLY_HEADER_SEARCH_COLS,
        serial_col="s/no.",
        chamber_name="assembly",
        spill_before_duplicate=False,
    )


# ── Shared private: sponsor splitter helpers ──────────────────────────────────


def _has_multiple_names(sponsor: str) -> bool:
    return bool(_COMMA_AND_PATTERN.search(str(sponsor)))


def _extract_office_bills(df: pd.DataFrame, office_pattern: re.Pattern) -> pd.DataFrame:
    mask = df["sponsor"].apply(lambda s: bool(office_pattern.search(str(s))))
    result = df[mask].copy()
    log.info(f"Office-sponsored bills extracted: {len(result)} rows")
    return result


def _extract_multi_bills(df: pd.DataFrame) -> pd.DataFrame:
    mask = df["sponsor"].apply(_has_multiple_names)
    result = df[mask].copy()
    log.info(f"Multi-sponsored bills extracted: {len(result)} rows")
    return result


def _extract_residue_bills(df: pd.DataFrame) -> pd.DataFrame:
    mask = ~df["sponsor"].apply(_has_multiple_names)
    result = df[mask].copy()
    log.info(f"Residue (single-sponsor) bills extracted: {len(result)} rows")
    return result


def _partition_bills(
    df: pd.DataFrame,
    office_pattern: re.Pattern,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    
    office = _extract_office_bills(df, office_pattern)
    remainder = df[~df.index.isin(office.index)]
    multi = _extract_multi_bills(remainder)
    residue = _extract_residue_bills(remainder)
    log.info(
        f"Partition complete: {len(office)} office, {len(multi)} multi, {len(residue)} residue"
        f" (total {len(office) + len(multi) + len(residue)} / {len(df)})"
    )
    return office, multi, residue


def _split_office_on_and(
    df: pd.DataFrame,
    chairperson_pattern: re.Pattern,
    chamber_name: str,
) -> pd.DataFrame:
    
    def _split(sponsor: str) -> list[str]:
        if chairperson_pattern.match(str(sponsor)):
            return [sponsor.strip()]
        parts = _AND_PATTERN.split(str(sponsor))
        return [
            p.strip().strip(",").strip() for p in parts if p.strip().strip(",").strip()
        ]

    expanded = df.copy()
    expanded["sponsor"] = expanded["sponsor"].apply(_split)
    result = expanded.explode("sponsor").reset_index(drop=True)
    log.info(f"Office bills after splitting: {len(result)} rows (was {len(df)})")
    return result


def _split_multi_on_comma_and(df: pd.DataFrame) -> pd.DataFrame:
    def _split(sponsor: str) -> list[str]:
        parts = _COMMA_AND_PATTERN.split(str(sponsor))
        return [
            p.strip().strip(",").strip() for p in parts if p.strip().strip(",").strip()
        ]

    expanded = df.copy()
    expanded["sponsor"] = expanded["sponsor"].apply(_split)
    result = expanded.explode("sponsor").reset_index(drop=True)
    log.info(f"Multi-sponsor bills after splitting: {len(result)} rows (was {len(df)})")
    return result


def _rebuild_bills(
    office_bills: pd.DataFrame,
    multi_bills: pd.DataFrame,
    residue_bills: pd.DataFrame,
    chamber_name: str,
    include_office: bool = True,
    include_multi: bool = True,
    include_residue: bool = True,
) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    if include_office:
        parts.append(office_bills)
    if include_multi:
        parts.append(multi_bills)
    if include_residue:
        parts.append(residue_bills)
    if not parts:
        log.warning(
            f"No subsets selected for {chamber_name} rebuild — returning empty DataFrame"
        )
        return pd.DataFrame()
    result = pd.concat(parts, ignore_index=True)
    log.info(f"Rebuilt {chamber_name} bills: {len(result)} rows total")
    return result


# ── Assembly sponsor splitter (public) ────────────────────────────────────────


def extract_office_sponsored_bills(df: pd.DataFrame) -> pd.DataFrame:
    """Return assembly rows whose sponsor contains an office-role keyword."""
    return _extract_office_bills(df, _ASSEMBLY_OFFICE_PATTERN)


def extract_multi_sponsored_bills(df: pd.DataFrame) -> pd.DataFrame:
    """Return assembly rows whose sponsor names more than one individual."""
    return _extract_multi_bills(df)


def extract_residue_bills(df: pd.DataFrame) -> pd.DataFrame:
    """Return assembly rows that already have exactly one individual sponsor."""
    return _extract_residue_bills(df)


def partition_assembly_bills(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split assembly bills into (office_bills, multi_bills, residue_bills)."""
    return _partition_bills(df, _ASSEMBLY_OFFICE_PATTERN)


def split_office_sponsors(df: pd.DataFrame) -> pd.DataFrame:
    """Explode assembly office-sponsored rows on ' and '."""
    return _split_office_on_and(df, _ASSEMBLY_CHAIRPERSON_PATTERN, "assembly")


def split_multi_sponsors(df: pd.DataFrame) -> pd.DataFrame:
    """Explode assembly multi-sponsored rows on commas and ' and '."""
    return _split_multi_on_comma_and(df)


def rebuild_assembly_bills(
    office_bills: pd.DataFrame,
    multi_bills: pd.DataFrame,
    residue_bills: pd.DataFrame,
    include_office: bool = True,
    include_multi: bool = True,
    include_residue: bool = True,
) -> pd.DataFrame:
    """Reassemble the three assembly bill subsets into one DataFrame."""
    return _rebuild_bills(
        office_bills,
        multi_bills,
        residue_bills,
        "assembly",
        include_office,
        include_multi,
        include_residue,
    )


# ── Senate sponsor splitter (public) ──────────────────────────────────────────


def extract_senate_office_sponsored_bills(df: pd.DataFrame) -> pd.DataFrame:
    """Return senate rows whose sponsor contains an office-role keyword."""
    return _extract_office_bills(df, _SENATE_OFFICE_PATTERN)


def extract_senate_multi_sponsored_bills(df: pd.DataFrame) -> pd.DataFrame:
    """Return senate rows whose sponsor names more than one individual."""
    return _extract_multi_bills(df)


def extract_senate_residue_bills(df: pd.DataFrame) -> pd.DataFrame:
    """Return senate rows that already have exactly one individual sponsor."""
    return _extract_residue_bills(df)


def partition_senate_bills(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split senate bills into (office_bills, multi_bills, residue_bills)."""
    return _partition_bills(df, _SENATE_OFFICE_PATTERN)


def split_senate_office_sponsors(df: pd.DataFrame) -> pd.DataFrame:
    """Explode senate office-sponsored rows on ' and '."""
    return _split_office_on_and(df, _SENATE_CHAIRPERSON_PATTERN, "senate")


def split_senate_multi_sponsors(df: pd.DataFrame) -> pd.DataFrame:
    """Explode senate multi-sponsored rows on commas and ' and '."""
    return _split_multi_on_comma_and(df)


def rebuild_senate_bills(
    office_bills: pd.DataFrame,
    multi_bills: pd.DataFrame,
    residue_bills: pd.DataFrame,
    include_office: bool = True,
    include_multi: bool = True,
    include_residue: bool = True,
) -> pd.DataFrame:
    """Reassemble the three senate bill subsets into one DataFrame."""
    return _rebuild_bills(
        office_bills,
        multi_bills,
        residue_bills,
        "senate",
        include_office,
        include_multi,
        include_residue,
    )
