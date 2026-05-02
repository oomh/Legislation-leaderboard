"""Application Main Entry Point

Single-page Streamlit app for visualising the pipeline results.
Pipeline logic lives in src/pipeline — this file is view-only.
"""

import pandas as pd
import streamlit as st
from loguru import logger as log

from src.pipeline import PipelineStore, run_full_pipeline
from src.transformations import (
    transform_senate_bills,
    transform_assembly_bills,
    transform_senate_leadership,
    transform_assembly_leadership,
    transform_senate_members,
    transform_assembly_members,
    transform_committees,
)
from src.transformations.merge_transformer import merge_leadership, merge_members


# ── Page config ────────────────────────────────────────────────────────────────


def run_app():
    """Main application entry point."""
    st.set_page_config(
        page_title="Legislation Leaderboard",
        page_icon="📋",
        layout="wide",
    )

    st.title("📋 Legislation Leaderboard")

    # Load or initialise the store once per session
    if "store" not in st.session_state:
        st.session_state.store = PipelineStore.from_disk()
        log.info("PipelineStore loaded into session")

    store: PipelineStore = st.session_state.store

    # ── Run Pipeline button ────────────────────────────────────────────────────
    if st.button("▶ Run Pipeline", type="primary"):
        with st.spinner("Running full pipeline…"):
            store = run_full_pipeline(store)
            st.session_state.store = store
        st.success("Pipeline complete — results updated below.")
        st.rerun()

    st.divider()

    # ── Step 1: Scraping ───────────────────────────────────────────────────────
    st.header("Step 1: Scraping")

    _show_scraping(store)

    st.divider()

    # ── Step 2: MinerU Extraction ──────────────────────────────────────────────
    st.header("Step 2: MinerU Extraction")

    _show_mineru(store)

    st.divider()

    # ── Step 3: Table Building ─────────────────────────────────────────────────
    st.header("Step 3: Table Building")

    _show_table_building(store)

    st.divider()

    # ── Raw tables (before transformation) ────────────────────────────────────
    st.header("Raw Tables")

    _show_raw_tables(store)

    st.divider()

    # ── Transformed tables ─────────────────────────────────────────────────────
    st.header("Transformed Tables")

    _show_transformed_tables(store)

    st.divider()

    # ── Step 4: Merged results ─────────────────────────────────────────────────
    st.header("Step 4: Merged Results")

    _show_merged(store)


# ── Display helpers ────────────────────────────────────────────────────────────


def _df(val) -> pd.DataFrame:
    """Coerce a result dict or DataFrame to a DataFrame."""
    if isinstance(val, pd.DataFrame):
        return val
    if isinstance(val, dict):
        data = val.get("data")
        if isinstance(data, pd.DataFrame):
            return data
        if isinstance(data, list):
            return pd.DataFrame(data)
    return pd.DataFrame()


def _row_badge(df: pd.DataFrame) -> str:
    n = len(df) if isinstance(df, pd.DataFrame) and not df.empty else 0
    return f"**{n} rows**" if n else "_no data_"


def _show_df(df: pd.DataFrame) -> None:
    if isinstance(df, pd.DataFrame) and not df.empty:
        st.dataframe(df, width="stretch")
    else:
        st.info("No data available")


def _show_scraping(store: PipelineStore) -> None:
    tabs = st.tabs(
        ["Bill Tracker URLs (Senate)", "Bill Tracker URLs (Assembly)",
        "House Leadership (Senate)", "House Leadership (Assembly)",
        "Members (Senate)", "Members (Assembly)",
        "Committee Leadership"]
    )

    senate_urls = store.bill_tracker_urls.get("senate", [])
    assembly_urls = store.bill_tracker_urls.get("assembly", [])

    with tabs[0]:
        st.caption(_row_badge(pd.DataFrame(senate_urls)))
        _show_df(pd.DataFrame(senate_urls))
    with tabs[1]:
        st.caption(_row_badge(pd.DataFrame(assembly_urls)))
        _show_df(pd.DataFrame(assembly_urls))

    senate_lead = store.house_leadership.get("senate", pd.DataFrame())
    assembly_lead = store.house_leadership.get("assembly", pd.DataFrame())
    if isinstance(senate_lead, list):
        senate_lead = pd.DataFrame(senate_lead)
    if isinstance(assembly_lead, list):
        assembly_lead = pd.DataFrame(assembly_lead)

    with tabs[2]:
        st.caption(_row_badge(senate_lead))
        _show_df(senate_lead)
    with tabs[3]:
        st.caption(_row_badge(assembly_lead))
        _show_df(assembly_lead)

    senate_mem = store.member_lists.get("senate", pd.DataFrame())
    assembly_mem = store.member_lists.get("assembly", pd.DataFrame())
    if isinstance(senate_mem, list):
        senate_mem = pd.DataFrame(senate_mem)
    if isinstance(assembly_mem, list):
        assembly_mem = pd.DataFrame(assembly_mem)

    with tabs[4]:
        st.caption(_row_badge(senate_mem))
        _show_df(senate_mem)
    with tabs[5]:
        st.caption(_row_badge(assembly_mem))
        _show_df(assembly_mem)

    committee = pd.DataFrame(store.committee_leadership) if store.committee_leadership else pd.DataFrame()
    with tabs[6]:
        st.caption(_row_badge(committee))
        _show_df(committee)


def _show_mineru(store: PipelineStore) -> None:
    results = store.mineru_extraction_results or {}
    if not results:
        st.info("No MinerU extraction results — run the pipeline first.")
        return

    tabs = st.tabs(list(results.keys()))
    for tab, (key, val) in zip(tabs, results.items()):
        with tab:
            status = val.get("status", "unknown") if isinstance(val, dict) else "unknown"
            st.caption(f"Status: **{status}** | Dir: `{val.get('extract_dir', '')}` " if isinstance(val, dict) else "")


def _show_table_building(store: PipelineStore) -> None:
    tb = store.table_builder_results or {}
    if not tb:
        st.info("No table building results — run the pipeline first.")
        return

    tab_senate, tab_assembly, tab_committee = st.tabs(
        ["Senate Bills (raw)", "Assembly Bills (raw)", "Committee Leadership (raw)"]
    )

    with tab_senate:
        df = _df(tb.get("bill_tracker_senate", {}))
        st.caption(_row_badge(df))
        _show_df(df)
    with tab_assembly:
        df = _df(tb.get("bill_tracker_assembly", {}))
        st.caption(_row_badge(df))
        _show_df(df)
    with tab_committee:
        df = _df(tb.get("committee_leadership", {}))
        st.caption(_row_badge(df))
        _show_df(df)


def _show_raw_tables(store: PipelineStore) -> None:
    tb = store.table_builder_results or {}
    hl = store.house_leadership or {}
    ml = store.member_lists or {}

    if not tb and not any(hl.values()) and not any(ml.values()):
        st.info("No raw tables yet — run the pipeline first.")
        return

    tabs = st.tabs([
        "Senate Bills", "Assembly Bills", "Committee Leadership",
        "Senate Leadership", "Assembly Leadership",
        "Senate Members", "Assembly Members",
    ])

    with tabs[0]:
        df = _df(tb.get("bill_tracker_senate", {}))
        st.caption(_row_badge(df))
        _show_df(df)
    with tabs[1]:
        df = _df(tb.get("bill_tracker_assembly", {}))
        st.caption(_row_badge(df))
        _show_df(df)
    with tabs[2]:
        df = _df(tb.get("committee_leadership", {}))
        st.caption(_row_badge(df))
        _show_df(df)

    def _to_df(val):
        if isinstance(val, pd.DataFrame):
            return val
        if isinstance(val, list):
            return pd.DataFrame(val)
        return pd.DataFrame()

    with tabs[3]:
        df = _to_df(hl.get("senate"))
        st.caption(_row_badge(df))
        _show_df(df)
    with tabs[4]:
        df = _to_df(hl.get("assembly"))
        st.caption(_row_badge(df))
        _show_df(df)
    with tabs[5]:
        df = _to_df(ml.get("senate"))
        st.caption(_row_badge(df))
        _show_df(df)
    with tabs[6]:
        df = _to_df(ml.get("assembly"))
        st.caption(_row_badge(df))
        _show_df(df)


def _show_transformed_tables(store: PipelineStore) -> None:
    tb = store.table_builder_results or {}
    hl = store.house_leadership or {}
    ml = store.member_lists or {}

    has_bills = tb.get("bill_tracker_senate") or tb.get("bill_tracker_assembly")
    if not has_bills:
        st.info("No raw tables available to transform — run the pipeline first.")
        return

    def _raw_df(result_dict) -> pd.DataFrame:
        return _df(result_dict) if result_dict else pd.DataFrame()

    def _to_df(val) -> pd.DataFrame:
        if isinstance(val, pd.DataFrame):
            return val
        if isinstance(val, list):
            return pd.DataFrame(val)
        return pd.DataFrame()

    tabs = st.tabs([
        "Senate Bills", "Assembly Bills", "Committee",
        "Senate Leadership", "Assembly Leadership",
        "Senate Members", "Assembly Members",
    ])

    with tabs[0]:
        result = transform_senate_bills(_raw_df(tb.get("bill_tracker_senate", {})))
        df = _df(result)
        st.caption(_row_badge(df))
        _show_df(df)
    with tabs[1]:
        result = transform_assembly_bills(_raw_df(tb.get("bill_tracker_assembly", {})))
        df = _df(result)
        st.caption(_row_badge(df))
        _show_df(df)
    with tabs[2]:
        result = transform_committees(_raw_df(tb.get("committee_leadership", {})))
        df = _df(result)
        st.caption(_row_badge(df))
        _show_df(df)
    with tabs[3]:
        result = transform_senate_leadership(_to_df(hl.get("senate")))
        df = _df(result)
        st.caption(_row_badge(df))
        _show_df(df)
    with tabs[4]:
        result = transform_assembly_leadership(_to_df(hl.get("assembly")))
        df = _df(result)
        st.caption(_row_badge(df))
        _show_df(df)
    with tabs[5]:
        result = transform_senate_members(_to_df(ml.get("senate")))
        df = _df(result)
        st.caption(_row_badge(df))
        _show_df(df)
    with tabs[6]:
        result = transform_assembly_members(_to_df(ml.get("assembly")))
        df = _df(result)
        st.caption(_row_badge(df))
        _show_df(df)


def _show_merged(store: PipelineStore) -> None:
    tb = store.table_builder_results or {}
    hl = store.house_leadership or {}
    ml = store.member_lists or {}

    has_data = tb or any(hl.values()) or any(ml.values())
    if not has_data:
        st.info("No data to merge — run the pipeline first.")
        return

    def _raw_df(result_dict) -> pd.DataFrame:
        return _df(result_dict) if result_dict else pd.DataFrame()

    def _to_df(val) -> pd.DataFrame:
        if isinstance(val, pd.DataFrame):
            return val
        if isinstance(val, list):
            return pd.DataFrame(val)
        return pd.DataFrame()

    tab_lead, tab_mem = st.tabs(["Merged Leadership", "Merged Members"])

    with tab_lead:
        senate_lead_df = _df(transform_senate_leadership(_to_df(hl.get("senate"))))
        assembly_lead_df = _df(transform_assembly_leadership(_to_df(hl.get("assembly"))))
        result = merge_leadership(senate_lead_df, assembly_lead_df)
        df = _df(result)
        st.caption(_row_badge(df))
        _show_df(df)

    with tab_mem:
        senate_mem_df = _df(transform_senate_members(_to_df(ml.get("senate"))))
        assembly_mem_df = _df(transform_assembly_members(_to_df(ml.get("assembly"))))
        result = merge_members(senate_mem_df, assembly_mem_df)
        df = _df(result)
        st.caption(_row_badge(df))
        _show_df(df)


def _show_transformations(store: PipelineStore) -> None:
    """Legacy — kept for compatibility. New layout uses _show_raw_tables / _show_transformed_tables / _show_merged."""
    _show_merged(store)

