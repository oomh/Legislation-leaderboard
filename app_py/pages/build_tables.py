"""Build Tables Page

Table building from MinerU extraction output.
"""

import streamlit as st
import pandas as pd
from loguru import logger as log
from src.table_builders.assembly_bills_builder import build_assembly_bills
from src.table_builders.senate_bills_builder import build_senate_bills
from src.table_builders.committee_leadership_builder import build_committee_leadership_table


# ── Build Tables Page ─────────────────────────────────────────────────────────


def page_build_tables():
    """Render table building page."""
    log.debug("Rendering build tables page")

    st.markdown("#### Build Tables from MinerU Output")

    # Check for MinerU extraction results
    has_mineru_results = bool(st.session_state.mineru_extraction_results)

    if not has_mineru_results:
        st.warning("Run MinerU extraction first to build tables")
        st.info("Navigate to MinerU Jobs page to extract bill trackers and committee leadership documents")
    else:
        results = st.session_state.mineru_extraction_results

        # Check if all extractions were successful
        all_success = all(r.get("status") == "success" for r in results.values())

        if not all_success:
            st.error("Some MinerU extractions failed. Check MinerU Jobs page for details")
        else:
            # Display source documents
            st.markdown("**Input Documents:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                senate_status = results.get("bill_tracker_senate", {}).get("status")
                st.caption(f"Senate Bill Tracker: {'✓' if senate_status == 'success' else '✗'}")
            
            with col2:
                assembly_status = results.get("bill_tracker_assembly", {}).get("status")
                st.caption(f"Assembly Bill Tracker: {'✓' if assembly_status == 'success' else '✗'}")
            
            with col3:
                committee_status = results.get("committee_leadership", {}).get("status")
                st.caption(f"Committee Leadership: {'✓' if committee_status == 'success' else '✗'}")

            st.divider()

            # Build tables button
            if st.button("Build Tables from MinerU Output", key="build_tables", width='content'):
                log.info("Starting table building from MinerU extraction directories")
                
                try:
                    with st.spinner("Building tables from extracted markdown files..."):
                        # Get JSON/markdown paths from session state
                        senate_json = results.get("bill_tracker_senate", {}).get("extract_dir", "data/mineru_output_bill_tracker_senate") + "/content_list_v2.json"
                        assembly_json = results.get("bill_tracker_assembly", {}).get("extract_dir", "data/mineru_output_bill_tracker_assembly") + "/content_list_v2.json"
                        committee_md = results.get("committee_leadership", {}).get("extract_dir", "data/mineru_output_committee_leadership") + "/full.md"

                        # Build all tables
                        senate_result = build_senate_bills(senate_json)
                        assembly_result = build_assembly_bills(assembly_json)
                        committee_result = build_committee_leadership_table(committee_md)

                        table_results = {
                            "bill_tracker_senate": senate_result,
                            "bill_tracker_assembly": assembly_result,
                            "committee_leadership": committee_result,
                        }

                    st.session_state.table_builder_results = table_results

                    # Count successful builders
                    success_count = sum(1 for r in table_results.values() if r.get("status") == "success")
                    total_count = len(table_results)

                    st.success(f"Table building complete: {success_count}/{total_count} documents processed")

                    log.info(f"Table building complete: {success_count} successful, {total_count - success_count} failed")

                except Exception as e:
                    log.error(f"Table building failed: {e}")
                    st.error(f"Table building failed: {e}")

    # Display table builder results
    st.divider()
    st.markdown("#### Built Tables")

    if st.session_state.table_builder_results:
        results = st.session_state.table_builder_results

        tab_senate, tab_assembly, tab_committee = st.tabs(["Senate Bill Tracker", "Assembly Bill Tracker", "Committee Leadership"])

        with tab_senate:
            result = results.get("bill_tracker_senate", {})
            if result.get("status") == "success":
                row_count = result.get("row_count", 0)
                data = result.get("data")
                
                st.success(f"✓ {row_count} bills extracted")
                
                if data is not None and not data.empty:
                    st.dataframe(data, width='content')
                else:
                    st.info("No bills data available")
            else:
                st.error(f"✗ Failed: {result.get('message', 'Unknown error')}")

        with tab_assembly:
            result = results.get("bill_tracker_assembly", {})
            if result.get("status") == "success":
                row_count = result.get("row_count", 0)
                data = result.get("data")
                
                st.success(f"✓ {row_count} bills extracted")
                
                if data is not None and not data.empty:
                    st.dataframe(data, width='content')
                else:
                    st.info("No bills data available")
            else:
                st.error(f"✗ Failed: {result.get('message', 'Unknown error')}")

        with tab_committee:
            result = results.get("committee_leadership", {})
            if result.get("status") == "success":
                st.success(f"✓ {result.get('table_count')} table(s) built")
                
                for table_info in result.get("tables", []):
                    table_idx = table_info.get("table_index", 0)
                    row_count = table_info.get("row_count", 0)
                    data = table_info.get("data", [])
                    
                    st.subheader(f"Table {table_idx} - {row_count} rows")
                    if data:
                        st.dataframe(pd.DataFrame(data), width='content')
                    else:
                        st.info("No data in this table")
            else:
                st.error(f"✗ Failed: {result.get('error', 'Unknown error')}")
    else:
        st.info("Build tables above to populate results")
