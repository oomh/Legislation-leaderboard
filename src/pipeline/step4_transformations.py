"""Step 4: Transformations Pipeline

Applies individual transformations to each dataset from Steps 1 and 3.
Merging of leadership and members is handled by Step 6.

Inputs:  step1_results (house_leadership, member_lists)
         step3_results (senate_bills, assembly_bills, committee_membership)
Outputs: step4_results — { bill_trackers, leadership, members, committees }
"""

import pandas as pd
from loguru import logger as log
from src.pipeline.store import PipelineStore
from src.transformations import (
    transform_senate_bills,
    transform_assembly_bills,
    transform_senate_leadership,
    transform_assembly_leadership,
    transform_senate_members,
    transform_assembly_members,
    transform_committees,
)


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
        step3 = store.step3_results or {}
        has_tables = bool(step3)

        if not has_tables:
            log.warning("Table builder results not found")
            return {
                "status": "error",
                "message": "Build tables first",
            }

        # Apply individual transformations
        bill_trackers = prepare_bill_trackers(store)
        leadership = prepare_leadership_data(store)
        members = prepare_member_data(store)
        committees = prepare_committee_data(store)

        transformed_data = {
            "bill_trackers": bill_trackers,
            "leadership": leadership,
            "members": members,
            "committees": committees,
        }

        # Store consolidated results
        store.step4_results = {"transformed_data": transformed_data}

        log.info("Step 4 Complete: Data consolidated and ready for output")

        return {
            "status": "success",
            "message": "Transformations complete",
            "data": transformed_data,
        }
    except Exception as e:
        log.error(f"Transformation preparation failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


def _to_df(val) -> pd.DataFrame:
    """Coerce a raw store value (DataFrame, list, or dict) to a DataFrame."""
    if isinstance(val, pd.DataFrame):
        return val
    if isinstance(val, list):
        return pd.DataFrame(val)
    return pd.DataFrame()


def _result_to_df(result: dict) -> pd.DataFrame:
    """Extract a DataFrame from a transformer result dict."""
    if isinstance(result, dict):
        data = result.get("data")
        if isinstance(data, pd.DataFrame):
            return data
    return pd.DataFrame()


def prepare_bill_trackers(store: PipelineStore) -> dict:
    """Transform senate and assembly bills.

    Returns:
        Dict with senate and assembly transformed bills.
    """
    try:
        step3 = store.step3_results or {}
        senate_raw = step3.get("senate_bills", {})
        assembly_raw = step3.get("assembly_bills", {})

        senate_raw_df = senate_raw.get("data") if isinstance(senate_raw, dict) else senate_raw
        assembly_raw_df = assembly_raw.get("data") if isinstance(assembly_raw, dict) else assembly_raw

        senate_result = transform_senate_bills(senate_raw_df) if isinstance(senate_raw_df, pd.DataFrame) else {}
        assembly_result = transform_assembly_bills(assembly_raw_df) if isinstance(assembly_raw_df, pd.DataFrame) else {}

        senate_df = senate_result.get("data", pd.DataFrame()) if isinstance(senate_result, dict) else pd.DataFrame()
        assembly_df = assembly_result.get("data", pd.DataFrame()) if isinstance(assembly_result, dict) else pd.DataFrame()

        return {
            "senate": {"data": senate_df, "row_count": len(senate_df)},
            "assembly": {"data": assembly_df, "row_count": len(assembly_df)},
        }
    except Exception as e:
        log.error(f"Error preparing bill trackers: {e}")
        return {"senate": {}, "assembly": {}}


def prepare_leadership_data(store: PipelineStore) -> dict:
    """Apply leadership transformations and return results.

    Returns:
        Dict with transformed senate and assembly leadership DataFrames.
    """
    try:
        step1 = store.step1_results or {}
        house_leadership = step1.get("house_leadership", {})

        senate_raw = _to_df(house_leadership.get("senate"))
        assembly_raw = _to_df(house_leadership.get("assembly"))

        senate_result = transform_senate_leadership(senate_raw)
        assembly_result = transform_assembly_leadership(assembly_raw)

        senate_df = _result_to_df(senate_result)
        assembly_df = _result_to_df(assembly_result)

        return {
            "senate": {"data": senate_df, "row_count": len(senate_df)},
            "assembly": {"data": assembly_df, "row_count": len(assembly_df)},
        }
    except Exception as e:
        log.error(f"Error preparing leadership data: {e}")
        return {"senate": {}, "assembly": {}}


def prepare_member_data(store: PipelineStore) -> dict:
    """Apply member transformations and return results.

    Returns:
        Dict with transformed senate and assembly member DataFrames.
    """
    try:
        step1 = store.step1_results or {}
        member_lists = step1.get("member_lists", {})

        senate_raw = _to_df(member_lists.get("senate"))
        assembly_raw = _to_df(member_lists.get("assembly"))

        senate_result = transform_senate_members(senate_raw)
        assembly_result = transform_assembly_members(assembly_raw)

        senate_df = _result_to_df(senate_result)
        assembly_df = _result_to_df(assembly_result)

        return {
            "senate": {"data": senate_df, "row_count": len(senate_df)},
            "assembly": {"data": assembly_df, "row_count": len(assembly_df)},
        }
    except Exception as e:
        log.error(f"Error preparing member data: {e}")
        return {"senate": {}, "assembly": {}}


def prepare_committee_data(store: PipelineStore) -> dict:
    """Apply committee transformation and return result.

    Returns:
        Dict with transformed committee DataFrame.
    """
    try:
        step3 = store.step3_results or {}
        committee_result = step3.get("committee_membership", {})

        if isinstance(committee_result, dict):
            raw_df = committee_result.get("data", pd.DataFrame())
        else:
            raw_df = committee_result if isinstance(committee_result, pd.DataFrame) else pd.DataFrame()

        result = transform_committees(raw_df)
        df = _result_to_df(result)

        return {"data": df, "row_count": len(df)}
    except Exception as e:
        log.error(f"Error preparing committee data: {e}")
        return {}


def run_transformations_step(store: PipelineStore | None = None) -> dict:
    """Orchestrate complete transformations step.

    Returns:
        Dict with transformation status and consolidated data
    """
    return prepare_transformation_data(store)
