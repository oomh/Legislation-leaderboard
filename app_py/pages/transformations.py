"""Transformations Page

Data transformation of built tables.
"""

import streamlit as st
import pandas as pd
from loguru import logger as log
from src.pipeline import run_transformations_step
from src.transformations import transform_senate_bills


# ── Transformations Page ──────────────────────────────────────────────────────


def page_transformations():
    """Render data transformations page."""
    log.debug("Rendering data transformations page")

    st.markdown("#### Apply Transformations to Built Tables")

    # Check for built tables
    has_tables = bool(st.session_state.get("table_builder_results"))

    if not has_tables:
        st.warning("Build tables first")
        st.info("Navigate to the Build Tables page to build tables from MinerU output")
    else:
        # ── Pre Transformation Section ────────────────────────────────────────────
        st.markdown("### Pre Transformation")
        st.markdown("Review and transform extracted tables below")

        st.divider()

        # ── Bill Trackers Section ─────────────────────────────────────────────────
        st.markdown("#### Bill Trackers")

        tab_senate_bills, tab_assembly_bills = st.tabs(
            ["Senate Bill Tracker", "Assembly Bill Tracker"]
        )

        with tab_senate_bills:
            try:
                # Get senate bills from raw_senate_bills (set by build_tables step)
                senate_result = st.session_state.get("raw_senate_bills", {})
                if (
                    isinstance(senate_result, dict)
                    and senate_result.get("status") == "success"
                ):
                    data = senate_result.get("data")
                    row_count = senate_result.get("row_count", 0)

                    st.success(f"✓ {row_count} records")

                    if data is not None and not data.empty:
                        st.dataframe(data, use_container_width=True)
                    else:
                        st.info("No data available")
                else:
                    st.error(
                        f"✗ Failed: {senate_result.get('message', 'Unknown error')}"
                    )
            except Exception as e:
                log.error(f"Error loading senate bills: {e}")
                st.error(f"Error loading senate bills: {e}")

        with tab_assembly_bills:
            try:
                # Get assembly bills from raw_assembly_bills (set by build_tables step)
                assembly_result = st.session_state.get("raw_assembly_bills", {})
                if (
                    isinstance(assembly_result, dict)
                    and assembly_result.get("status") == "success"
                ):
                    data = assembly_result.get("data")
                    row_count = assembly_result.get("row_count", 0)

                    st.success(f"✓ {row_count} records")

                    if data is not None and not data.empty:
                        st.dataframe(data, use_container_width=True)
                    else:
                        st.info("No data available")
                else:
                    st.error(
                        f"✗ Failed: {assembly_result.get('message', 'Unknown error')}"
                    )
            except Exception as e:
                log.error(f"Error loading assembly bills: {e}")
                st.error(f"Error loading assembly bills: {e}")

        st.divider()

        # ── House Leadership Section ──────────────────────────────────────────────
        st.markdown("#### House Leadership")

        tab_senate_leadership, tab_assembly_leadership = st.tabs(
            ["Senate Leadership", "Assembly Leadership"]
        )

        with tab_senate_leadership:
            try:
                # Get senate leadership from house_leadership (set by scrapers step)
                senate_leadership_data = st.session_state.get(
                    "house_leadership", {}
                ).get("senate")
                log.debug(
                    f"Senate leadership from session: {type(senate_leadership_data)}"
                )

                if senate_leadership_data is not None:
                    if isinstance(senate_leadership_data, pd.DataFrame):
                        df = senate_leadership_data
                    elif isinstance(senate_leadership_data, list) and senate_leadership_data:
                        df = pd.DataFrame(senate_leadership_data)
                    else:
                        df = None

                    if df is not None and not df.empty:
                        st.success(f"✓ {len(df)} records")
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Senate leadership data is empty or invalid format")
                else:
                    st.info("Senate leadership data not yet scraped")
            except Exception as e:
                log.error(f"Error loading senate leadership: {e}")
                st.error(f"Error loading senate leadership data: {e}")

        with tab_assembly_leadership:
            try:
                # Get assembly leadership from house_leadership (set by scrapers step)
                assembly_leadership_data = st.session_state.get(
                    "house_leadership", {}
                ).get("assembly")
                log.debug(
                    f"Assembly leadership from session: {type(assembly_leadership_data)}"
                )

                if assembly_leadership_data is not None:
                    if isinstance(assembly_leadership_data, pd.DataFrame):
                        df = assembly_leadership_data
                    elif isinstance(assembly_leadership_data, list) and assembly_leadership_data:
                        df = pd.DataFrame(assembly_leadership_data)
                    else:
                        df = None

                    if df is not None and not df.empty:
                        st.success(f"✓ {len(df)} records")
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Assembly leadership data is empty or invalid format")
                else:
                    st.info("Assembly leadership data not yet scraped")
            except Exception as e:
                log.error(f"Error loading assembly leadership: {e}")
                st.error(f"Error loading assembly leadership data: {e}")

        st.divider()

        # ── Member Lists Section ──────────────────────────────────────────────────
        st.markdown("#### Member Lists")

        tab_senate_members, tab_assembly_members = st.tabs(
            ["Senate Members", "Assembly Members"]
        )

        with tab_senate_members:
            try:
                # Get senate members from member_lists (set by scrapers step)
                senate_members_data = st.session_state.get("member_lists", {}).get(
                    "senate"
                )
                log.debug(f"Senate members from session: {type(senate_members_data)}")

                if senate_members_data is not None:
                    if isinstance(senate_members_data, pd.DataFrame):
                        df = senate_members_data
                    elif isinstance(senate_members_data, list) and senate_members_data:
                        df = pd.DataFrame(senate_members_data)
                    else:
                        df = None

                    if df is not None and not df.empty:
                        st.success(f"✓ {len(df)} records")
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Senate members data is empty or invalid format")
                else:
                    st.info("Senate members data not yet scraped")
            except Exception as e:
                log.error(f"Error loading senate members: {e}")
                st.error(f"Error loading senate members data: {e}")

        with tab_assembly_members:
            try:
                # Get assembly members from member_lists (set by scrapers step)
                assembly_members_data = st.session_state.get("member_lists", {}).get(
                    "assembly"
                )
                log.debug(
                    f"Assembly members from session: {type(assembly_members_data)}"
                )

                if assembly_members_data is not None:
                    if isinstance(assembly_members_data, pd.DataFrame):
                        df = assembly_members_data
                    elif isinstance(assembly_members_data, list) and assembly_members_data:
                        df = pd.DataFrame(assembly_members_data)
                    else:
                        df = None

                    if df is not None and not df.empty:
                        st.success(f"✓ {len(df)} records")
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Assembly members data is empty or invalid format")
                else:
                    st.info("Assembly members data not yet scraped")
            except Exception as e:
                log.error(f"Error loading assembly members: {e}")
                st.error(f"Error loading assembly members data: {e}")

        st.divider()

        # ── Committees Section ────────────────────────────────────────────────────
        st.markdown("#### Committees")

        try:
            committee_result = st.session_state.get("table_builder_results", {}) or {}
            committee_result = committee_result.get("committee_leadership", {})
            if committee_result.get("status") == "success":
                data = committee_result.get("data")
                row_count = committee_result.get("row_count", 0)

                st.success(f"✓ {row_count} records")

                if data is not None and not data.empty:
                    st.dataframe(data, use_container_width=True)
                else:
                    st.info("No data available")
            else:
                st.error(f"✗ Failed: {committee_result.get('error', 'Unknown error')}")
        except Exception as e:
            log.error(f"Error loading committees: {e}")
            st.error(f"Error loading committees: {e}")

        # ── Post Transformation Section ───────────────────────────────────────────
        st.divider()
        st.markdown("### Post Transformation")
        st.markdown("Apply and review cleaned, standardised tables")

        st.divider()
        st.markdown("#### Senate Bill Tracker — Transformed")

        if st.button("Run Senate Bills Transformation", key="run_senate_transform"):
            senate_result = st.session_state.get("raw_senate_bills", {})
            raw_df = (
                senate_result.get("data")
                if isinstance(senate_result, dict)
                else None
            )
            result = transform_senate_bills(raw_df)
            st.session_state["transformed_senate_bills"] = result
            if result["status"] == "success":
                log.info(
                    f"Senate bills transformation complete: {result['row_count']} rows"
                )
            else:
                log.error(f"Senate bills transformation failed: {result['message']}")

        transformed = st.session_state.get("transformed_senate_bills")
        if transformed:
            if transformed["status"] == "success":
                data = transformed["data"]
                if data is not None and not data.empty:
                    st.success(f"✓ {transformed['row_count']} records after transformation")
                    st.dataframe(data, use_container_width=True)
                else:
                    st.info("Transformation produced no rows")
            else:
                st.error(f"✗ {transformed['message']}")
