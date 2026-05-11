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
from src.pipeline.step5_5_manual_corrections import (
    load_manual_corrections,
    run_manual_corrections_step,
    save_manual_corrections,
)
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


def _show_step_5_5(store: PipelineStore) -> None:
    """Render the Step 5.5 manual corrections section."""
    st.subheader("Step 5.5: Manual Corrections")

    results = store.step5_5_results or {}

    # ── Run button + status ────────────────────────────────────────────────────
    col_btn, col_status = st.columns([1, 5])
    with col_btn:
        if st.button("Run Step 5.5", key="run_step5_5"):
            with st.spinner("Running Step 5.5: Manual Corrections..."):
                result = run_manual_corrections_step(store=store)
            store.save()
            st.session_state.store = store
            status = result.get("status", "unknown")
            msg = result.get("message", "")
            if status in ("success", "partial", "skipped"):
                st.success(msg or "Step 5.5 complete")
            else:
                st.error(msg or "Step 5.5 failed")
            st.rerun()
    with col_status:
        if results:
            total = results.get("total_corrections", 0)
            st.caption(f"{total} correction(s) applied — status: {results.get('status', '')}")
        else:
            st.caption("Not run yet")

    # ── Saved corrections panel ────────────────────────────────────────────────
    corrections = load_manual_corrections()

    with st.expander("Saved Corrections", expanded=True):
        # Flatten the nested dict into rows for display
        flat_rows = [
            {"dataset": ds, "column": col, "from": frm, "to": to}
            for ds, col_map in corrections.items()
            if isinstance(col_map, dict)
            for col, replacements in col_map.items()
            if isinstance(replacements, dict)
            for frm, to in replacements.items()
        ]

        if flat_rows:
            for i, row in enumerate(flat_rows):
                c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 3, 1])
                c1.write(row["dataset"])
                c2.write(row["column"])
                c3.write(row["from"])
                c4.write(row["to"])
                if c5.button("✕", key=f"del_correction_{i}"):
                    # Remove this entry from the corrections dict
                    ds, col, frm = row["dataset"], row["column"], row["from"]
                    del corrections[ds][col][frm]
                    if not corrections[ds][col]:
                        del corrections[ds][col]
                    if not corrections[ds]:
                        del corrections[ds]
                    save_manual_corrections(corrections)
                    st.rerun()
        else:
            st.caption("No corrections saved yet.")

    # ── Add correction form ────────────────────────────────────────────────────
    st.markdown("**Add a correction**")

    # These selectors live outside the form so each change triggers a rerun and
    # the dependent dropdowns (column list, value list) refresh immediately.
    dataset_options = [k for k in store.step5_results if store.step5_results]
    if not dataset_options:
        dataset_options = ["assembly", "senate"]

    selected_dataset = st.selectbox("Dataset", options=dataset_options, key="form_dataset")

    col_options: list[str] = []
    step5_entry = store.step5_results.get(selected_dataset) if store.step5_results else None
    if isinstance(step5_entry, dict):
        df_preview = step5_entry.get("data")
        if isinstance(df_preview, pd.DataFrame) and not df_preview.empty:
            col_options = list(df_preview.columns)

    selected_column = st.selectbox(
        "Column",
        options=col_options if col_options else ["(run step 5 first)"],
        key="form_column",
    )

    val_options: list[str] = []
    if col_options and selected_column in col_options:
        df_col = store.step5_results[selected_dataset]["data"][selected_column]
        val_options = sorted(
            str(v)
            for v in df_col.dropna().unique()
            if str(v) not in ("", "nan")
        )

    current_value = st.selectbox(
        "Current value",
        options=val_options if val_options else ["(no values available)"],
        key="form_current",
    )

    with st.form("add_correction", clear_on_submit=True):
        new_value = st.text_input("New value", key="form_new")
        submitted = st.form_submit_button("Add correction")
        if submitted:
            if not new_value.strip():
                st.warning("New value cannot be empty.")
            elif not col_options or selected_column not in col_options:
                st.warning("Please run Step 5 before adding corrections.")
            elif not val_options or current_value == "(no values available)":
                st.warning("No valid current value selected.")
            else:
                corrections.setdefault(selected_dataset, {}).setdefault(selected_column, {})
                corrections[selected_dataset][selected_column][current_value] = new_value.strip()
                save_manual_corrections(corrections)
                st.success(
                    f"Correction added: [{selected_dataset}].{selected_column}: "
                    f"'{current_value}' → '{new_value.strip()}'"
                )
                st.rerun()

    # ── Applied corrections log ────────────────────────────────────────────────
    if results:
        with st.expander("Applied corrections log", expanded=True):
            applied = results.get("applied", [])
            if applied:
                st.dataframe(pd.DataFrame(applied), width="stretch")
            else:
                st.caption(results.get("message", "No corrections were applied."))


# ── App entry point ────────────────────────────────────────────────────────────


def run_app() -> None:
    st.set_page_config(page_title="Legislation Leaderboard", layout="wide")
    st.title("Legislation Leaderboard")

    if "store" not in st.session_state:
        st.session_state.store = PipelineStore.from_disk()

    store: PipelineStore = st.session_state.store
    
    def _run_full_pipeline():
        run_full_pipeline(store)
    
    st.button("Run Full Pipeline", on_click=_run_full_pipeline, type="primary")

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
    _show_step_5_5(store)
    st.divider()
    _show_step(6, "Merging", run_merging_step, "step6_results", store)
