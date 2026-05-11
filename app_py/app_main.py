"""Application Main Entry Point

Single-page Streamlit app — one Run button and tabbed DataFrame display per pipeline step.
Pipeline logic lives in src/pipeline — this file is view-only.
"""

import pandas as pd
import streamlit as st

from src.pipeline.store import PipelineStore
from src.pipeline.step1_scraping import run_scraping_step
from src.pipeline.step2_mineru_extraction import run_mineru_extraction_step
from src.pipeline.step3_table_building import run_table_building_step
from src.pipeline.step4_transformations import run_transformations_step
from src.pipeline.step5_sponsor_normalisation import run_sponsor_normalisation_step
from src.pipeline.step6_merging import run_merging_step
from src.pipeline.orchestrator import run_full_pipeline


# ── Helpers ────────────────────────────────────────────────────────────────────


def _to_df(val) -> pd.DataFrame:
    """Best-effort conversion of a store value to a DataFrame."""
    if isinstance(val, pd.DataFrame):
        return val
    if isinstance(val, dict) and "data" in val:
        return _to_df(val["data"])
    if isinstance(val, list):
        try:
            return pd.DataFrame(val)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def _display_value(val, depth: int = 0) -> None:
    """Recursively display a store value.

    - DataFrames and transformer result dicts (with a "data" key) are shown as st.dataframe.
    - Plain dicts become nested st.tabs (up to 2 levels deep).
    - Lists are converted to DataFrames.
    """
    if isinstance(val, pd.DataFrame):
        st.dataframe(val, width="stretch")
        return

    if isinstance(val, dict) and "data" in val:
        df = _to_df(val)
        status = val.get("status", "")
        rows = val.get("row_count", len(df))
        if status:
            st.caption(f"{status} — {rows} rows")
        st.dataframe(df, width="stretch")
        return

    if isinstance(val, dict) and depth < 3:
        keys = list(val.keys())
        if keys:
            tabs = st.tabs([k.replace("_", " ").title() for k in keys])
            for tab, k in zip(tabs, keys):
                with tab:
                    _display_value(val[k], depth + 1)
        return

    if isinstance(val, list):
        st.dataframe(_to_df(val), width="stretch")
        return

    st.write(val)


def _show_step(
    n: int,
    name: str,
    run_fn,
    results_attr: str,
    store: PipelineStore,
) -> None:
    """Render a single pipeline step: header, run button, and tabbed results."""
    st.subheader(f"Step {n}: {name}")

    results = getattr(store, results_attr, {}) or {}

    col_btn, col_status = st.columns([1, 5])
    with col_btn:
        if st.button(f"Run Step {n}", key=f"run_step{n}"):
            with st.spinner(f"Running Step {n}: {name}..."):
                result = run_fn(store=store)
            store.save()
            st.session_state.store = store
            status = result.get("status", "unknown")
            msg = result.get("message", "")
            if status in ("success", "partial"):
                st.success(msg or f"Step {n} complete")
            else:
                st.error(msg or f"Step {n} failed")
            st.rerun()
    with col_status:
        if results:
            st.caption(f"{len(results)} key(s) in store")
        else:
            st.caption("Not run yet")

    if results:
        _display_value(results)


# ── App entry point ────────────────────────────────────────────────────────────


def run_app() -> None:
    st.set_page_config(page_title="Legislation Leaderboard", layout="wide")
    st.title("Legislation Leaderboard")

    if "store" not in st.session_state:
        st.session_state.store = PipelineStore.from_disk()

    store: PipelineStore = st.session_state.store
    
    st.button("Run Full Pipeline", on_click=run_full_pipeline, args=(store,), type="primary")

    _show_step(1, "Scraping", run_scraping_step, "step1_results", store)
    st.divider()
    _show_step(2, "MinerU Extraction", run_mineru_extraction_step, "step2_results", store)
    st.divider()
    _show_step(3, "Table Building", run_table_building_step, "step3_results", store)
    st.divider()
    _show_step(4, "Transformations", run_transformations_step, "step4_results", store)
    st.divider()
    _show_step(5, "Sponsor Normalisation", run_sponsor_normalisation_step, "step5_results", store)
    st.divider()
    _show_step(6, "Merging", run_merging_step, "step6_results", store)
