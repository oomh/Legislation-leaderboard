"""Step 5: Sponsor Normalisation

Splits assembly and senate bill tracker rows so that each row has exactly one sponsor.

Inputs:  store.transformed_data["bill_trackers"] — transformed DataFrames from Step 4
         Raises an error if Step 4 has not been run yet.
Outputs: store.normalised_assembly_bills — dict with keys:
            status, data (pd.DataFrame), row_count, message
         store.normalised_senate_bills   — same structure
"""

import pandas as pd
from loguru import logger as log

from src.pipeline.store import PipelineStore
from src.transformations.assembly_bills_sponsor_splitter import (
    partition_assembly_bills,
    split_office_sponsors as split_assembly_office_sponsors,
    split_multi_sponsors as split_assembly_multi_sponsors,
    rebuild_assembly_bills,
)
from src.transformations.senate_bills_sponsor_splitter import (
    partition_senate_bills,
    split_office_sponsors as split_senate_office_sponsors,
    split_multi_sponsors as split_senate_multi_sponsors,
    rebuild_senate_bills,
)


def run_sponsor_normalisation_step(store: PipelineStore | None = None) -> dict:
    """Normalise assembly and senate bill sponsors so every row has exactly one sponsor.

    Reads already-transformed bills from Step 4 (``store.transformed_data``).
    Raises a descriptive error if Step 4 has not been run.

    Args:
        store: PipelineStore populated through at least Step 4.

    Returns:
        Dict with keys: status, assembly, senate, message.
        ``assembly`` and ``senate`` are each dicts with status/data/row_count/message.
    """
    log.info("Starting Step 5: Sponsor Normalisation")

    if store is None:
        store = PipelineStore()

    transformed = store.transformed_data
    if not transformed:
        msg = "No transformed data found — run Step 4 first"
        log.error(msg)
        return {"status": "error", "assembly": {}, "senate": {}, "message": msg}

    bill_trackers = transformed.get("bill_trackers", {})
    if not bill_trackers:
        msg = "No bill tracker data in Step 4 results — re-run Step 4"
        log.error(msg)
        return {"status": "error", "assembly": {}, "senate": {}, "message": msg}

    overall_status = "success"
    results: dict = {}

    for chamber, store_attr in [
        ("assembly", "normalised_assembly_bills"),
        ("senate", "normalised_senate_bills"),
    ]:
        chamber_entry = bill_trackers.get(chamber, {})
        bills = chamber_entry.get("data") if isinstance(chamber_entry, dict) else None

        if bills is None or (isinstance(bills, pd.DataFrame) and bills.empty):
            msg = f"No transformed {chamber} bills in Step 4 results — re-run Step 4"
            log.error(msg)
            chamber_result = {"status": "error", "data": pd.DataFrame(), "row_count": 0, "message": msg}
            results[chamber] = chamber_result
            setattr(store, store_attr, chamber_result)
            overall_status = "partial"
            continue

        try:
            log.info(f"{chamber.title()} bills from Step 4: {len(bills)} rows")

            if chamber == "assembly":
                office, multi, residue = partition_assembly_bills(bills)
                office_split = split_assembly_office_sponsors(office)
                multi_split = split_assembly_multi_sponsors(multi)
                normalized = rebuild_assembly_bills(
                    office_split, multi_split, residue,
                    include_office=True, include_multi=True, include_residue=True,
                )
            else:
                office, multi, residue = partition_senate_bills(bills)
                office_split = split_senate_office_sponsors(office)
                multi_split = split_senate_multi_sponsors(multi)
                normalized = rebuild_senate_bills(
                    office_split, multi_split, residue,
                    include_office=True, include_multi=True, include_residue=True,
                )

            for col in ("s/no.", "no."):
                if col in normalized.columns:
                    normalized[col] = normalized[col].astype(int)
                    break

            row_count = len(normalized)
            msg = f"Normalized {row_count} {chamber} bill records (one sponsor per row)"
            log.info(f"Step 5 {chamber} complete: {msg}")

            chamber_result = {"status": "success", "data": normalized, "row_count": row_count, "message": msg}
            results[chamber] = chamber_result
            setattr(store, store_attr, chamber_result)

        except Exception as e:
            log.error(f"Step 5 {chamber} normalisation failed: {e}")
            chamber_result = {"status": "error", "data": pd.DataFrame(), "row_count": 0, "message": str(e)}
            results[chamber] = chamber_result
            setattr(store, store_attr, chamber_result)
            overall_status = "partial"

    total = sum(r.get("row_count", 0) for r in results.values())
    return {
        "status": overall_status,
        "assembly": results.get("assembly", {}),
        "senate": results.get("senate", {}),
        "message": f"Normalised {total} bill records across both chambers",
    }
