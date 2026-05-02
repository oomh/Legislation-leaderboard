"""Step 4: Transformations Pipeline

Consolidates data from Steps 1 and 3 for final output.
Inputs: house_leadership, member_lists (Step 1) + raw_senate_bills, raw_assembly_bills, raw_committee_membership (Step 3)
Outputs: Consolidated transformed datasets ready for database
"""

import pandas as pd
from loguru import logger as log
from src.pipeline.store import PipelineStore
from src.transformations import merge_leadership, merge_members


def prepare_transformation_data(store: PipelineStore | None = None) -> dict:
    """Prepare and consolidate data for final transformation.

    Returns:
        Dict with all consolidated datasets ready for output
    """
    log.info("Starting Step 4: Transformations")
    if store is None:
        store = PipelineStore()

    try:
        # Check for table builder results
        has_tables = bool(store.table_builder_results)

        if not has_tables:
            log.warning("Table builder results not found")
            return {
                "status": "error",
                "message": "Build tables first",
            }

        # Prepare consolidated data
        transformed_data = {
            "bill_trackers": prepare_bill_trackers(store),
            "leadership": prepare_leadership_data(store),
            "members": prepare_member_data(store),
            "committees": prepare_committee_data(store),
            "merged_leadership": prepare_merged_leadership(store),
            "merged_members": prepare_merged_members(store),
        }

        # Store consolidated results
        store.transformed_data = transformed_data

        log.info("Step 4 Complete: Data consolidated and ready for output")

        return {
            "status": "success",
            "data": transformed_data,
        }
    except Exception as e:
        log.error(f"Transformation preparation failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


def prepare_bill_trackers(store: PipelineStore) -> dict:
    """Prepare consolidated bill tracker data.

    Returns:
        Dict with senate and assembly bills
    """
    try:
        senate_bills = store.raw_senate_bills or {}
        assembly_bills = store.raw_assembly_bills or {}

        return {
            "senate": {
                "data": (
                    senate_bills.get("data")
                    if isinstance(senate_bills, dict)
                    else senate_bills
                ),
                "row_count": (
                    len(senate_bills.get("data", []))
                    if isinstance(senate_bills, dict)
                    else (
                        len(senate_bills)
                        if isinstance(senate_bills, pd.DataFrame)
                        else 0
                    )
                ),
            },
            "assembly": {
                "data": (
                    assembly_bills.get("data")
                    if isinstance(assembly_bills, dict)
                    else assembly_bills
                ),
                "row_count": (
                    len(assembly_bills.get("data", []))
                    if isinstance(assembly_bills, dict)
                    else (
                        len(assembly_bills)
                        if isinstance(assembly_bills, pd.DataFrame)
                        else 0
                    )
                ),
            },
        }
    except Exception as e:
        log.error(f"Error preparing bill trackers: {e}")
        return {"senate": {}, "assembly": {}}


def prepare_leadership_data(store: PipelineStore) -> dict:
    """Prepare consolidated house leadership data.

    Returns:
        Dict with senate and assembly leadership
    """
    try:
        house_leadership = store.house_leadership or {}

        senate_leadership = house_leadership.get("senate", pd.DataFrame())
        assembly_leadership = house_leadership.get("assembly", pd.DataFrame())

        return {
            "senate": {
                "data": senate_leadership,
                "row_count": (
                    len(senate_leadership)
                    if isinstance(senate_leadership, pd.DataFrame)
                    else 0
                ),
            },
            "assembly": {
                "data": assembly_leadership,
                "row_count": (
                    len(assembly_leadership)
                    if isinstance(assembly_leadership, pd.DataFrame)
                    else 0
                ),
            },
        }
    except Exception as e:
        log.error(f"Error preparing leadership data: {e}")
        return {"senate": {}, "assembly": {}}


def prepare_member_data(store: PipelineStore) -> dict:
    """Prepare consolidated member lists data.

    Returns:
        Dict with senate and assembly members
    """
    try:
        member_lists = store.member_lists or {}

        senate_members = member_lists.get("senate", pd.DataFrame())
        assembly_members = member_lists.get("assembly", pd.DataFrame())

        return {
            "senate": {
                "data": senate_members,
                "row_count": (
                    len(senate_members)
                    if isinstance(senate_members, pd.DataFrame)
                    else 0
                ),
            },
            "assembly": {
                "data": assembly_members,
                "row_count": (
                    len(assembly_members)
                    if isinstance(assembly_members, pd.DataFrame)
                    else 0
                ),
            },
        }
    except Exception as e:
        log.error(f"Error preparing member data: {e}")
        return {"senate": {}, "assembly": {}}


def prepare_committee_data(store: PipelineStore) -> dict:
    """Prepare consolidated committee data.

    Returns:
        Dict with committee membership
    """
    try:
        committee_result = store.raw_committee_membership or {}

        if isinstance(committee_result, dict):
            committee_data = committee_result.get("data", pd.DataFrame())
            row_count = committee_result.get("row_count", 0)
        else:
            committee_data = (
                committee_result
                if isinstance(committee_result, pd.DataFrame)
                else pd.DataFrame()
            )
            row_count = (
                len(committee_data) if isinstance(committee_data, pd.DataFrame) else 0
            )

        return {
            "data": committee_data,
            "row_count": row_count,
        }
    except Exception as e:
        log.error(f"Error preparing committee data: {e}")
        return {}


def prepare_merged_leadership(store: PipelineStore) -> dict:
    """Merge transformed senate and assembly leadership into a single table.

    Reads already-transformed results from session state if available, otherwise
    falls back to the raw leadership data.

    Returns:
        Dict with merged leadership data from merge_leadership().
    """
    try:
        senate_result = (store.transformed_data or {}).get("leadership", {}).get("senate", {})
        assembly_result = (store.transformed_data or {}).get("leadership", {}).get("assembly", {})

        senate_df = (
            senate_result.get("data")
            if isinstance(senate_result, dict)
            else senate_result
        )
        assembly_df = (
            assembly_result.get("data")
            if isinstance(assembly_result, dict)
            else assembly_result
        )

        if not isinstance(senate_df, pd.DataFrame):
            senate_df = pd.DataFrame()
        if not isinstance(assembly_df, pd.DataFrame):
            assembly_df = pd.DataFrame()

        result = merge_leadership(senate_df, assembly_df)
        return result
    except Exception as e:
        log.error(f"Error preparing merged leadership: {e}")
        return {"status": "error", "message": str(e)}


def prepare_merged_members(store: PipelineStore) -> dict:
    """Merge transformed senate and assembly members into a single table.

    Reads already-transformed results from session state if available, otherwise
    falls back to the raw member data.

    Returns:
        Dict with merged members data from merge_members().
    """
    try:
        senate_result = (store.transformed_data or {}).get("members", {}).get("senate", {})
        assembly_result = (store.transformed_data or {}).get("members", {}).get("assembly", {})

        senate_df = (
            senate_result.get("data")
            if isinstance(senate_result, dict)
            else senate_result
        )
        assembly_df = (
            assembly_result.get("data")
            if isinstance(assembly_result, dict)
            else assembly_result
        )

        if not isinstance(senate_df, pd.DataFrame):
            senate_df = pd.DataFrame()
        if not isinstance(assembly_df, pd.DataFrame):
            assembly_df = pd.DataFrame()

        result = merge_members(senate_df, assembly_df)
        return result
    except Exception as e:
        log.error(f"Error preparing merged members: {e}")
        return {"status": "error", "message": str(e)}


def run_transformations_step(store: PipelineStore | None = None) -> dict:
    """Orchestrate complete transformations step.

    Returns:
        Dict with transformation status and consolidated data
    """
    return prepare_transformation_data(store)
