"""Transformations Page

Data transformation of built tables.
"""

import streamlit as st
import pandas as pd
from loguru import logger as log
from src.pipeline import run_transformations_step
from src.transformations import (
    transform_senate_bills,
    transform_assembly_bills,
    transform_senate_leadership,
    transform_assembly_leadership,
    transform_senate_members,
    transform_assembly_members,
    transform_committees,
    merge_leadership,
    merge_members,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _df_from_result(key: str) -> pd.DataFrame | None:
    """Return DataFrame from a session state key that may be a result dict or DataFrame."""
    val = st.session_state.get(key)
    if isinstance(val, dict):
        return val.get("data")
    if isinstance(val, pd.DataFrame):
        return val
    return None


def _nested_df(key: str, subkey: str) -> pd.DataFrame | None:
    """Return DataFrame from a nested session state key."""
    val = st.session_state.get(key, {})
    sub = val.get(subkey) if isinstance(val, dict) else None
    if isinstance(sub, pd.DataFrame):
        return sub
    if isinstance(sub, list) and sub:
        return pd.DataFrame(sub)
    return None


def _show_df(df: pd.DataFrame | None) -> None:
    if df is not None and not df.empty:
        st.dataframe(df, width="stretch")
    else:
        st.info("No data available")


def _show_transformed(key: str) -> None:
    result = st.session_state.get(key)
    if result is None:
        st.info("Not yet transformed")
        return
    if result.get("status") == "success":
        st.success(f"✓ {result.get('row_count', 0)} records")
        _show_df(result.get("data"))
    else:
        st.error(f"✗ {result.get('message', 'Unknown error')}")


# ── Transformations Page ──────────────────────────────────────────────────────


def page_transformations():
    """Render data transformations page."""
    log.debug("Rendering data transformations page")

    st.markdown("#### Transformations")

    if not st.session_state.get("table_builder_results"):
        st.warning("Build tables first")
        st.info("Navigate to the Build Tables page to build tables from MinerU output")
        return

    # ── 1. Raw Tables ─────────────────────────────────────────────────────────
    st.markdown("### Raw Tables")

    (
        tab_raw_senate,
        tab_raw_assembly,
        tab_raw_sen_lead,
        tab_raw_asm_lead,
        tab_raw_sen_mem,
        tab_raw_asm_mem,
        tab_raw_comm,
    ) = st.tabs(
        [
            "Senate Bills",
            "Assembly Bills",
            "Senate Leadership",
            "Assembly Leadership",
            "Senate Members",
            "Assembly Members",
            "Committees",
        ]
    )

    with tab_raw_senate:
        _show_df(_df_from_result("raw_senate_bills"))

    with tab_raw_assembly:
        _show_df(_df_from_result("raw_assembly_bills"))

    with tab_raw_sen_lead:
        _show_df(_nested_df("house_leadership", "senate"))

    with tab_raw_asm_lead:
        _show_df(_nested_df("house_leadership", "assembly"))

    with tab_raw_sen_mem:
        _show_df(_nested_df("member_lists", "senate"))

    with tab_raw_asm_mem:
        _show_df(_nested_df("member_lists", "assembly"))

    with tab_raw_comm:
        comm = (st.session_state.get("table_builder_results") or {}).get(
            "committee_leadership", {}
        )
        _show_df(comm.get("data") if isinstance(comm, dict) else None)

    st.divider()

    # ── 2. Transform Buttons ──────────────────────────────────────────────────
    st.markdown("### Transform")

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

    with c1:
        if st.button("Senate Bills", width="stretch", key="btn_t_senate"):
            raw = _df_from_result("raw_senate_bills")
            if raw is None:
                raw = pd.DataFrame()
            st.session_state["transformed_senate_bills"] = transform_senate_bills(raw)

    with c2:
        if st.button("Assembly Bills", width="stretch", key="btn_t_assembly"):
            raw = _df_from_result("raw_assembly_bills")
            if raw is None:
                raw = pd.DataFrame()
            st.session_state["transformed_assembly_bills"] = transform_assembly_bills(
                raw
            )

    with c3:
        if st.button("Senate Leadership", width="stretch", key="btn_t_sen_lead"):
            df = _nested_df("house_leadership", "senate")
            if df is None:
                df = pd.DataFrame()
            st.session_state["transformed_senate_leadership"] = (
                transform_senate_leadership(df)
            )

    with c4:
        if st.button("Assembly Leadership", width="stretch", key="btn_t_asm_lead"):
            df = _nested_df("house_leadership", "assembly")
            if df is None:
                df = pd.DataFrame()
            st.session_state["transformed_assembly_leadership"] = (
                transform_assembly_leadership(df)
            )

    with c5:
        if st.button("Senate Members", width="stretch", key="btn_t_sen_mem"):
            df = _nested_df("member_lists", "senate")
            if df is None:
                df = pd.DataFrame()
            st.session_state["transformed_senate_members"] = transform_senate_members(
                df
            )

    with c6:
        if st.button("Assembly Members", width="stretch", key="btn_t_asm_mem"):
            df = _nested_df("member_lists", "assembly")
            if df is None:
                df = pd.DataFrame()
            st.session_state["transformed_assembly_members"] = (
                transform_assembly_members(df)
            )

    with c7:
        if st.button("Committees", width="stretch", key="btn_t_comm"):
            comm = (st.session_state.get("table_builder_results") or {}).get(
                "committee_leadership", {}
            )
            raw_comm = comm.get("data") if isinstance(comm, dict) else None
            if raw_comm is None:
                raw_comm = pd.DataFrame()
            st.session_state["transformed_committees"] = transform_committees(raw_comm)

    if st.button(
        "Run All Transformations",
        type="primary",
        width="stretch",
        key="btn_run_all",
    ):
        result = run_transformations_step()
        if result.get("status") == "success":
            st.success("All transformations complete")
        else:
            st.error(f"Transformation failed: {result.get('message')}")

    st.divider()

    # ── 2b. Merge ─────────────────────────────────────────────────────────────
    st.markdown("### Merge")

    mc1, mc2 = st.columns(2)

    with mc1:
        if st.button("Merge Leadership", width="stretch", key="btn_merge_lead"):
            senate_lead = _df_from_result("transformed_senate_leadership")
            assembly_lead = _df_from_result("transformed_assembly_leadership")
            if senate_lead is None:
                senate_lead = pd.DataFrame()
            if assembly_lead is None:
                assembly_lead = pd.DataFrame()
            st.session_state["merged_leadership"] = merge_leadership(
                senate_lead, assembly_lead
            )

    with mc2:
        if st.button("Merge Members", width="stretch", key="btn_merge_mem"):
            senate_mem = _df_from_result("transformed_senate_members")
            assembly_mem = _df_from_result("transformed_assembly_members")
            if senate_mem is None:
                senate_mem = pd.DataFrame()
            if assembly_mem is None:
                assembly_mem = pd.DataFrame()
            st.session_state["merged_members"] = merge_members(senate_mem, assembly_mem)

    st.divider()

    # ── 3. Transformed Tables ─────────────────────────────────────────────────
    st.markdown("### Transformed Tables")

    (
        tab_t_senate,
        tab_t_assembly,
        tab_t_sen_lead,
        tab_t_asm_lead,
        tab_t_sen_mem,
        tab_t_asm_mem,
        tab_t_comm,
        tab_t_merged_lead,
        tab_t_merged_mem,
    ) = st.tabs(
        [
            "Senate Bills",
            "Assembly Bills",
            "Senate Leadership",
            "Assembly Leadership",
            "Senate Members",
            "Assembly Members",
            "Committees",
            "Merged Leadership",
            "Merged Members",
        ]
    )

    with tab_t_senate:
        _show_transformed("transformed_senate_bills")

    with tab_t_assembly:
        _show_transformed("transformed_assembly_bills")

    with tab_t_sen_lead:
        _show_transformed("transformed_senate_leadership")

    with tab_t_asm_lead:
        _show_transformed("transformed_assembly_leadership")

    with tab_t_sen_mem:
        _show_transformed("transformed_senate_members")

    with tab_t_asm_mem:
        _show_transformed("transformed_assembly_members")

    with tab_t_comm:
        _show_transformed("transformed_committees")

    with tab_t_merged_lead:
        _show_transformed("merged_leadership")

    with tab_t_merged_mem:
        _show_transformed("merged_members")
