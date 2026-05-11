"""Application Main Entry Point

Single-page Streamlit app for visualising the pipeline results.
Pipeline logic lives in src/pipeline — this file is view-only.
"""

import pandas as pd
import streamlit as st
from loguru import logger as log

from src.pipeline import (
    PipelineStore,
    run_full_pipeline,
    run_scraping_step,
    run_mineru_extraction_step,
    run_table_building_step,
    run_transformations_step,
    run_sponsor_normalisation_step,
)
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

    # ── Step 4: Transformations ───────────────────────────────────────────────
    st.header("Step 4: Transformations")

    _show_step4(store)

    st.divider()

    # ── Step 5: Sponsor Normalisation ─────────────────────────────────────────
    st.header("Step 5: Sponsor Normalisation")

    _show_step5(store)

    st.divider()

    # ── Step 5.5: Manual Sponsor Name Corrections ─────────────────────────────
    st.header("Step 5.5: Manual Sponsor Name Corrections (optional)")

    _show_step5_5(store)


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


def _has_data(d: dict) -> bool:
    """Return True if any value in the dict is a non-empty DataFrame or truthy value."""
    return any(
        (not v.empty) if isinstance(v, pd.DataFrame) else bool(v)
        for v in d.values()
    )


def _show_scraping(store: PipelineStore) -> None:
    col_run, col_status = st.columns([1, 4])
    with col_run:
        if st.button("Run Step 1", key="run_step1"):
            with st.spinner("Scraping data…"):
                result = run_scraping_step(store=store)
                st.session_state.store = store
            if result.get("status") in ("success", "partial"):
                store.save()
                st.success(result.get("message", "Step 1 complete"))
                st.rerun()
            else:
                st.error(result.get("message", "Step 1 failed"))
    with col_status:
        has_data = bool(store.bill_tracker_urls or store.house_leadership or store.member_lists)
        st.caption("Data loaded" if has_data else "Not run yet — click Run Step 1 or run the full pipeline.")

    tabs = st.tabs(
        [
            "Bill Tracker URLs (Senate)",
            "Bill Tracker URLs (Assembly)",
            "House Leadership (Senate)",
            "House Leadership (Assembly)",
            "Members (Senate)",
            "Members (Assembly)",
            "Committee Leadership",
        ]
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

    committee = (
        pd.DataFrame(store.committee_leadership)
        if store.committee_leadership
        else pd.DataFrame()
    )
    with tabs[6]:
        st.caption(_row_badge(committee))
        _show_df(committee)


def _show_mineru(store: PipelineStore) -> None:
    col_run, col_status = st.columns([1, 4])
    with col_run:
        if st.button("Run Step 2", key="run_step2"):
            with st.spinner("Running MinerU extraction…"):
                result = run_mineru_extraction_step(store=store)
                st.session_state.store = store
            if result.get("status") in ("success", "partial"):
                store.save()
                st.success(result.get("message", "Step 2 complete"))
                st.rerun()
            else:
                st.error(result.get("message", "Step 2 failed"))
    with col_status:
        results = store.mineru_extraction_results or {}
        if results:
            statuses = ", ".join(f"{k}: **{v.get('status', '?')}**" for k, v in results.items() if isinstance(v, dict))
            st.caption(statuses)
        else:
            st.caption("Not run yet — click Run Step 2 or run the full pipeline.")

    results = store.mineru_extraction_results or {}
    if not results:
        return

    tabs = st.tabs(list(results.keys()))
    for tab, (key, val) in zip(tabs, results.items()):
        with tab:
            status = (
                val.get("status", "unknown") if isinstance(val, dict) else "unknown"
            )
            st.caption(
                f"Status: **{status}** | Dir: `{val.get('extract_dir', '')}` "
                if isinstance(val, dict)
                else ""
            )


def _show_table_building(store: PipelineStore) -> None:
    col_run, col_status = st.columns([1, 4])
    with col_run:
        if st.button("Run Step 3", key="run_step3"):
            with st.spinner("Building tables…"):
                result = run_table_building_step(store=store)
                st.session_state.store = store
            if result.get("status") in ("success", "partial"):
                store.save()
                st.success(result.get("message", "Step 3 complete"))
                st.rerun()
            else:
                st.error(result.get("message", "Step 3 failed"))
    with col_status:
        tb = store.table_builder_results or {}
        if tb:
            statuses = ", ".join(f"{k}: **{v.get('status', '?')}**" for k, v in tb.items() if isinstance(v, dict))
            st.caption(statuses)
        else:
            st.caption("Not run yet — click Run Step 3 or run the full pipeline.")

    tb = store.table_builder_results or {}
    if not tb:
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

    if not tb and not _has_data(hl) and not _has_data(ml):
        st.warning("No raw tables loaded yet — run the pipeline first.")
        return

    tabs = st.tabs(
        [
            "Senate Bills",
            "Assembly Bills",
            "Committee Leadership",
            "Senate Leadership",
            "Assembly Leadership",
            "Senate Members",
            "Assembly Members",
        ]
    )

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

    tabs = st.tabs(
        [
            "Senate Bills",
            "Assembly Bills",
            "Committee",
            "Senate Leadership",
            "Assembly Leadership",
            "Senate Members",
            "Assembly Members",
        ]
    )

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


def _show_step4(store: PipelineStore) -> None:
    col_run, col_status = st.columns([1, 4])
    with col_run:
        if st.button("Run Step 4", key="run_step4"):
            with st.spinner("Running transformations…"):
                result = run_transformations_step(store=store)
                st.session_state.store = store
            if result.get("status") in ("success", "partial"):
                store.save()
                st.success(result.get("message", "Step 4 complete"))
                st.rerun()
            else:
                st.error(result.get("message", "Step 4 failed"))
    with col_status:
        td = store.transformed_data or {}
        if td:
            bt = td.get("bill_trackers", {})
            parts = []
            for k, v in bt.items():
                if isinstance(v, dict):
                    parts.append(f"{k}: **{v.get('status', '?')}** ({v.get('row_count', 0)} rows)")
            st.caption(" | ".join(parts) if parts else "Data available")
        else:
            st.caption("Not run yet — click Run Step 4 or run the full pipeline.")

    _show_merged(store)


def _show_merged(store: PipelineStore) -> None:
    tb = store.table_builder_results or {}
    hl = store.house_leadership or {}
    ml = store.member_lists or {}

    has_data = bool(tb) or _has_data(hl) or _has_data(ml)
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
        assembly_lead_df = _df(
            transform_assembly_leadership(_to_df(hl.get("assembly")))
        )
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


def _show_step5_5(store: PipelineStore) -> None:
    """Optional step: manually correct sponsor names in normalised bill data."""
    assembly_result = getattr(store, "normalised_assembly_bills", None)
    senate_result = getattr(store, "normalised_senate_bills", None)

    if not assembly_result and not senate_result:
        st.info("No normalised bill data yet — run Step 5 first.")
        return

    # Persist the replacement queue across reruns
    if "sponsor_replacements" not in st.session_state:
        st.session_state["sponsor_replacements"] = {}

    replacements: dict = st.session_state["sponsor_replacements"]

    st.caption(
        "Add one or more sponsor name corrections below, then click **Apply**. Leave both fields empty to skip this step. Since this is mostly used to clean up naming structure, Copy Paste the current name and the updated name directly from the bill tables to ensure an exact match."
    )

    col_from, col_to, col_add = st.columns([3, 3, 1])
    with col_from:
        current_name = st.text_input("Current sponsor name", key="sponsor_current", label_visibility="collapsed", placeholder="Current sponsor name")
    with col_to:
        new_name = st.text_input("Replacement name", key="sponsor_new", label_visibility="collapsed", placeholder="Replacement name")
    with col_add:
        if st.button("Add", key="sponsor_add"):
            if current_name.strip() and new_name.strip():
                replacements[current_name.strip()] = new_name.strip()
                st.session_state["sponsor_replacements"] = replacements
                st.rerun()
            else:
                st.warning("Both fields must be filled to add a replacement.")

    if replacements:
        st.write("**Pending replacements:**")
        st.dataframe(
            pd.DataFrame(
                [{"Current": k, "Replace with": v} for k, v in replacements.items()]
            ),
            width="stretch",
            hide_index=True,
        )

        col_apply, col_clear = st.columns([1, 1])
        with col_apply:
            if st.button("Apply Replacements", key="sponsor_apply", type="primary"):
                sponsor_cols = ["sponsor", "sponsor_normalised", "bill_sponsor"]

                def _apply_to_result(result):
                    if not result:
                        return result
                    df = _df(result)
                    if df.empty:
                        return result
                    cols_present = [c for c in sponsor_cols if c in df.columns]
                    for col in cols_present:
                        df[col] = df[col].replace(replacements)
                    updated = dict(result)
                    updated["data"] = df
                    return updated

                store.normalised_assembly_bills = _apply_to_result(assembly_result)
                store.normalised_senate_bills = _apply_to_result(senate_result)
                store.save()
                st.session_state.store = store
                st.session_state["sponsor_replacements"] = {}
                st.success(f"Applied {len(replacements)} replacement(s) and saved.")
                st.rerun()
        with col_clear:
            if st.button("Clear all", key="sponsor_clear"):
                st.session_state["sponsor_replacements"] = {}
                st.rerun()
    else:
        st.caption("_No pending replacements — step will be skipped._")


def _show_step5(store: PipelineStore) -> None:
    assembly_result = getattr(store, "normalised_assembly_bills", None)
    senate_result = getattr(store, "normalised_senate_bills", None)

    col_run, col_status = st.columns([1, 4])
    with col_run:
        if st.button("Run Step 5", key="run_step5"):
            with st.spinner("Normalising bill sponsors..."):
                result = run_sponsor_normalisation_step(store=store)
                assembly_result = store.normalised_assembly_bills
                senate_result = store.normalised_senate_bills
                st.session_state.store = store
            if result.get("status") in ("success", "partial"):
                store.save()
                st.success(result["message"])
                st.rerun()
            else:
                st.error(result.get("message", "Step 5 failed"))

    with col_status:
        parts = []
        if assembly_result:
            parts.append(f"Assembly: **{assembly_result.get('status')}** ({assembly_result.get('row_count', 0)} rows)")
        if senate_result:
            parts.append(f"Senate: **{senate_result.get('status')}** ({senate_result.get('row_count', 0)} rows)")
        if parts:
            st.caption(" | ".join(parts))
        else:
            st.caption("Not run yet — click Run Step 5 or run the full pipeline.")

    tab_assembly, tab_senate = st.tabs(["Assembly Bills", "Senate Bills"])

    with tab_assembly:
        df = _df(assembly_result) if assembly_result else pd.DataFrame()
        st.caption(_row_badge(df))
        _show_df(df)

    with tab_senate:
        df = _df(senate_result) if senate_result else pd.DataFrame()
        st.caption(_row_badge(df))
        _show_df(df)
