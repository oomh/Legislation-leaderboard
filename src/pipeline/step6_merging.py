"""Step 6: Merging & Final Table Cleaning

Merges the individually-transformed leadership and member datasets produced by Step 4
into single combined DataFrames (one per entity type across both chambers).

Also takes the sponsor-normalised bill DataFrames from Step 5 and produces
Neon-ready final tables: assembly_bills_final and senate_bills_final.

Inputs:  step4_results — leadership, members
        step5_results — assembly, senate (normalised bills)
Outputs: step6_results — {
            merged_leadership,
            merged_members,
            assembly_bills_final,
            senate_bills_final,
        }
"""

import pandas as pd
from loguru import logger as log

from src.pipeline.store import PipelineStore
from src.transformations import merge_leadership, merge_members

# ── Final column order ─────────────────────────────────────────────────────────

_ASSEMBLY_FINAL_COLS = [
    "serial_number",
    "bill_name",
    "sponsor",
    "bill_number",
    "gazette_number",
    "dated",
    "maturity_date",
    "first_reading",
    "assent_date",
    "gazette_period",
    "assent_period",
]

_SENATE_FINAL_COLS = [
    "serial_number",
    "bill_name",
    "sponsor",
    "gazette_number",
    "dated",
    "maturity_date",
    "first_reading",
    "assent_date",
    "gazette_period",
    "assent_period",
]


# ── Private helpers ────────────────────────────────────────────────────────────


def _result_to_df(result: dict) -> pd.DataFrame:
    """Extract a DataFrame from a transformer result dict."""
    if isinstance(result, dict):
        data = result.get("data")
        if isinstance(data, pd.DataFrame):
            return data
    return pd.DataFrame()


def _parse_date_col(series: pd.Series) -> pd.Series:
    """Coerce a series of date strings to datetime64.

    Replaces empty strings with NaN first, then parses with format="mixed"
    and dayfirst=True so both dd/mm/yy and dd/mm/yyyy variants are handled
    without emitting UserWarnings about format inference.
    """
    cleaned = series.replace("", pd.NA)
    return pd.to_datetime(cleaned, format="mixed", dayfirst=True, errors="coerce")


def _calc_period(date_a: pd.Series, date_b: pd.Series) -> pd.Series:
    """Return (date_b - date_a).days formatted as 'X days', or pd.NA when either is NaT."""
    delta = (date_b - date_a).dt.days
    return delta.apply(lambda d: f"{int(d)} days" if pd.notna(d) else pd.NA)


def _clean_text_col(series: pd.Series) -> pd.Series:
    """Strip whitespace, convert empty strings to NaN."""
    return series.astype(str).str.strip().replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA})


def _finalize_assembly_bills(df: pd.DataFrame) -> dict:
    """Produce the Neon-ready assembly_bills table from a Step 5 normalised DataFrame.

    Source columns:
        s/no., bill, sponsor, na/sen. bill no., gazette no.,
        dated, maturity date, 1st read, assent
    Drops: 2nd read, 3rd read, remarks
    """
    try:
        out = pd.DataFrame()

        out["serial_number"] = pd.to_numeric(df.get("s/no."), errors="coerce").astype("Int64")
        out["bill_name"] = _clean_text_col(df.get("bill", pd.Series(dtype=str)))
        out["sponsor"] = _clean_text_col(df.get("sponsor", pd.Series(dtype=str)))
        out["bill_number"] = _clean_text_col(df.get("na/sen. bill no.", pd.Series(dtype=str)))
        out["gazette_number"] = pd.to_numeric(df.get("gazette no."), errors="coerce").astype("Int64")

        out["dated"] = _parse_date_col(df.get("dated", pd.Series(dtype=str)))
        out["maturity_date"] = _parse_date_col(df.get("maturity date", pd.Series(dtype=str)))
        out["first_reading"] = _parse_date_col(df.get("1st read", pd.Series(dtype=str)))
        out["assent_date"] = _parse_date_col(df.get("assent", pd.Series(dtype=str)))

        out["gazette_period"] = _calc_period(out["dated"], out["maturity_date"])
        out["assent_period"] = _calc_period(out["first_reading"], out["assent_date"])

        out = out[_ASSEMBLY_FINAL_COLS]

        row_count = len(out)
        log.info(f"assembly_bills_final: {row_count} rows")
        return {"status": "success", "data": out, "row_count": row_count, "message": f"{row_count} assembly bills finalised"}

    except Exception as e:
        log.error(f"_finalize_assembly_bills failed: {e}")
        return {"status": "error", "data": pd.DataFrame(), "row_count": 0, "message": str(e)}


def _finalize_senate_bills(df: pd.DataFrame) -> dict:
    """Produce the Neon-ready senate_bills table from a Step 5 normalised DataFrame.

    Source columns:
        no., bill, sponsor, gazette no., date of publication,
        maturity, date 1st read, date of assent
    Drops: sc committee referred to, date 2nd read, cotw/ 3rd read, remarks
    Note:  senate table has no bill_number column.
    """
    try:
        out = pd.DataFrame()

        out["serial_number"] = pd.to_numeric(df.get("no."), errors="coerce").astype("Int64")
        out["bill_name"] = _clean_text_col(df.get("bill", pd.Series(dtype=str)))
        out["sponsor"] = _clean_text_col(df.get("sponsor", pd.Series(dtype=str)))
        out["gazette_number"] = pd.to_numeric(df.get("gazette no."), errors="coerce").astype("Int64")

        out["dated"] = _parse_date_col(df.get("date of publication", pd.Series(dtype=str)))
        out["maturity_date"] = _parse_date_col(df.get("maturity", pd.Series(dtype=str)))
        out["first_reading"] = _parse_date_col(df.get("date 1st read", pd.Series(dtype=str)))
        out["assent_date"] = _parse_date_col(df.get("date of assent", pd.Series(dtype=str)))

        out["gazette_period"] = _calc_period(out["dated"], out["maturity_date"])
        out["assent_period"] = _calc_period(out["first_reading"], out["assent_date"])

        out = out[_SENATE_FINAL_COLS]

        row_count = len(out)
        log.info(f"senate_bills_final: {row_count} rows")
        return {"status": "success", "data": out, "row_count": row_count, "message": f"{row_count} senate bills finalised"}

    except Exception as e:
        log.error(f"_finalize_senate_bills failed: {e}")
        return {"status": "error", "data": pd.DataFrame(), "row_count": 0, "message": str(e)}


def run_merging_step(store: PipelineStore | None = None) -> dict:
    """Merge senate and assembly leadership/member datasets and finalise bill tables.

    Reads individually-transformed DataFrames from Step 4 and merges each
    chamber pair into a single combined DataFrame. Also takes the
    sponsor-normalised bills from Step 5 and produces Neon-ready final tables.

    Args:
        store: PipelineStore populated through at least Steps 4 and 5.

    Returns:
        Dict with keys: status, message.
    """
    log.info("Starting Step 6: Merging & Final Table Cleaning")

    if store is None:
        store = PipelineStore()

    step4 = store.step4_results or {}
    transformed_data = step4.get("transformed_data", {})

    if not transformed_data:
        msg = "No transformation data found — run Step 4 first"
        log.error(msg)
        return {"status": "error", "message": msg}

    step5 = store.step5_results or {}

    try:
        # ── Leadership & Members merge ─────────────────────────────────────────
        leadership = transformed_data.get("leadership", {})
        members = transformed_data.get("members", {})

        senate_lead_df = _result_to_df(leadership.get("senate", {}))
        assembly_lead_df = _result_to_df(leadership.get("assembly", {}))
        senate_mem_df = _result_to_df(members.get("senate", {}))
        assembly_mem_df = _result_to_df(members.get("assembly", {}))

        merged_leadership = merge_leadership(senate_lead_df, assembly_lead_df)
        merged_members = merge_members(senate_mem_df, assembly_mem_df)

        lead_count = len(_result_to_df(merged_leadership))
        mem_count = len(_result_to_df(merged_members))

        # ── Bill tracker final cleaning ────────────────────────────────────────
        assembly_raw = _result_to_df(step5.get("assembly", {}))
        senate_raw = _result_to_df(step5.get("senate", {}))

        if assembly_raw.empty:
            log.warning("No assembly bills in Step 5 results — run Step 5 first")
        if senate_raw.empty:
            log.warning("No senate bills in Step 5 results — run Step 5 first")

        assembly_final = _finalize_assembly_bills(assembly_raw) if not assembly_raw.empty else {
            "status": "error", "data": pd.DataFrame(), "row_count": 0,
            "message": "No assembly bills — run Step 5 first",
        }
        senate_final = _finalize_senate_bills(senate_raw) if not senate_raw.empty else {
            "status": "error", "data": pd.DataFrame(), "row_count": 0,
            "message": "No senate bills — run Step 5 first",
        }

        store.step6_results = {
            "merged_leadership": merged_leadership,
            "merged_members": merged_members,
            "assembly_bills_final": assembly_final,
            "senate_bills_final": senate_final,
        }

        asm_count = assembly_final.get("row_count", 0)
        sen_count = senate_final.get("row_count", 0)

        log.info(
            f"Step 6 complete: {lead_count} leadership rows, {mem_count} member rows, "
            f"{asm_count} assembly bills, {sen_count} senate bills"
        )

        return {
            "status": "success",
            "message": (
                f"Merging complete: {lead_count} leadership rows, {mem_count} member rows, "
                f"{asm_count} assembly bills finalised, {sen_count} senate bills finalised"
            ),
        }

    except Exception as e:
        log.error(f"Merging step failed: {e}")
        return {"status": "error", "message": str(e)}
