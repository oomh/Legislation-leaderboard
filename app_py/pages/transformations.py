"""Transformations Page

Data transformation and table building from MinerU extraction output.
"""

import streamlit as st
import pandas as pd
from loguru import logger as log
from src.table_builders import build_tables_from_mineru_output


# ── Transformations Page ──────────────────────────────────────────────────────


def page_transformations():
    """Render data transformation page."""
    log.debug("Rendering data transformations page")

    # Check for MinerU extraction results
    has_mineru_results = bool(st.session_state.mineru_extraction_results)

    st.markdown("#### Table Builder - Build from MinerU Output")

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
                        # Get directories from session state if available, otherwise use defaults
                        bill_tracker_senate_dir = results.get("bill_tracker_senate", {}).get("extract_dir", "./data/mineru_output_bill_tracker_senate")
                        bill_tracker_assembly_dir = results.get("bill_tracker_assembly", {}).get("extract_dir", "./data/mineru_output_bill_tracker_assembly")
                        committee_leadership_dir = results.get("committee_leadership", {}).get("extract_dir", "./data/mineru_output_committee_leadership")

                        table_results = build_tables_from_mineru_output(
                            bill_tracker_senate_dir=bill_tracker_senate_dir,
                            bill_tracker_assembly_dir=bill_tracker_assembly_dir,
                            committee_leadership_dir=committee_leadership_dir,
                        )

                    st.session_state.table_builder_results = table_results

                    # Count successful tables
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
                data = result.get("data", [])
                
                st.success(f"✓ {row_count} bills extracted")
                
                if data:
                    st.dataframe(pd.DataFrame(data), width='content')
                    
                    # Export option
                    csv_data = pd.DataFrame(data).to_csv(index=False)
                    st.download_button(
                        label="Download as CSV",
                        data=csv_data,
                        file_name="senate_bills.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("No bills data available")
            else:
                st.error(f"✗ Failed: {result.get('error', 'Unknown error')}")

        with tab_assembly:
            result = results.get("bill_tracker_assembly", {})
            if result.get("status") == "success":
                row_count = result.get("row_count", 0)
                data = result.get("data", [])
                
                st.success(f"✓ {row_count} bills extracted")
                
                if data:
                    st.dataframe(pd.DataFrame(data), width='content')
                    
                    # Export option
                    csv_data = pd.DataFrame(data).to_csv(index=False)
                    st.download_button(
                        label="Download as CSV",
                        data=csv_data,
                        file_name="assembly_bills.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("No bills data available")
            else:
                st.error(f"✗ Failed: {result.get('error', 'Unknown error')}")

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
        st.info("Build tables above to populate results")
