"""MinerU Jobs Page

Manage MinerU extraction jobs for document processing.
"""

import streamlit as st
from loguru import logger as log
from src.config import get_config
from src.pipeline import run_mineru_extraction_step


# ── MinerU Jobs Page ──────────────────────────────────────────────────────────


def page_mineru_jobs():
    """Render MinerU extraction jobs page."""
    log.debug("Rendering MinerU extraction jobs page")

    config = get_config()

    st.markdown("### MinerU Extraction Jobs")

    # Check for required data
    has_bill_tracker_senate = bool(st.session_state.bill_tracker_urls.get("senate"))
    has_bill_tracker_assembly = bool(st.session_state.bill_tracker_urls.get("assembly"))
    has_committee_leadership = bool(st.session_state.committee_leadership)

    # Display configuration
    st.markdown("#### Configuration")

    if config.get("mineru_api_key"):
        log.debug("MinerU API key is configured")
        st.success("✓ MinerU API Key configured")
    else:
        log.warning("MinerU API key is not configured")
        st.error("✗ MinerU API Key not configured in secrets")

    st.divider()

    # Extraction controls
    st.markdown("#### Extract Documents")

    if (
        not has_bill_tracker_senate
        or not has_bill_tracker_assembly
        or not has_committee_leadership
    ):
        st.warning(
            "Run scrapers first to populate bill trackers and committee leadership data"
        )
        st.info(
            f"Senate bill tracker: {'✓ Available' if has_bill_tracker_senate else '✗ Missing'}"
        )
        st.info(
            f"Assembly bill tracker: {'✓ Available' if has_bill_tracker_assembly else '✗ Missing'}"
        )
        st.info(
            f"Committee leadership: {'✓ Available' if has_committee_leadership else '✗ Missing'}"
        )
    else:
        # Get URLs from session state (0th index)
        senate_bill_url = (
            st.session_state.bill_tracker_urls["senate"][0].get("url")
            if st.session_state.bill_tracker_urls["senate"]
            else None
        )
        assembly_bill_url = (
            st.session_state.bill_tracker_urls["assembly"][0].get("url")
            if st.session_state.bill_tracker_urls["assembly"]
            else None
        )
        committee_url = (
            st.session_state.committee_leadership[0].get("url")
            if st.session_state.committee_leadership
            else None
        )

        if not senate_bill_url or not assembly_bill_url or not committee_url:
            st.error("Missing URL data in scraped results")
        else:
            # Display documents to extract
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**Senate Bill Tracker**")
                st.caption(senate_bill_url[-50:])

            with col2:
                st.markdown("**Assembly Bill Tracker**")
                st.caption(assembly_bill_url[-50:])

            with col3:
                st.markdown("**Committee Leadership**")
                st.caption(committee_url[-50:])

            st.divider()

            # Extract button
            if st.button(
                "Start MinerU Extraction",
                key="start_mineru_extraction",
                width="content",
            ):
                with st.spinner("Extracting documents with MinerU..."):
                    result = run_mineru_extraction_step()

                if result["status"] == "success":
                    st.success(
                        f"Extraction complete: {result['successful']}/{result['total']} documents processed"
                    )
                else:
                    st.error(
                        f"Extraction failed: {result.get('message', 'Unknown error')}"
                    )

    # Display results
    st.divider()
    st.markdown("#### Extraction Results")

    if st.session_state.mineru_extraction_results:
        results = st.session_state.mineru_extraction_results

        tab_senate, tab_assembly, tab_committee = st.tabs(
            ["Senate Bill Tracker", "Assembly Bill Tracker", "Committee Leadership"]
        )

        with tab_senate:
            result = results.get("bill_tracker_senate", {})
            if result.get("status") == "success":
                st.success(f"✓ Extracted {len(result['result']['file_list'])} files")
                st.caption(f"Location: {result['extract_dir']}")
                with st.expander("View extracted files"):
                    st.text("\n".join(result["result"]["file_list"]))
            else:
                st.error("✗ Extraction failed")

        with tab_assembly:
            result = results.get("bill_tracker_assembly", {})
            if result.get("status") == "success":
                st.success(f"✓ Extracted {len(result['result']['file_list'])} files")
                st.caption(f"Location: {result['extract_dir']}")
                with st.expander("View extracted files"):
                    st.text("\n".join(result["result"]["file_list"]))
            else:
                st.error("✗ Extraction failed")

        with tab_committee:
            result = results.get("committee_leadership", {})
            if result.get("status") == "success":
                st.success(f"✓ Extracted {len(result['result']['file_list'])} files")
                st.caption(f"Location: {result['extract_dir']}")
                with st.expander("View extracted files"):
                    st.text("\n".join(result["result"]["file_list"]))
            else:
                st.error("✗ Extraction failed")
    else:
        st.info("Run extraction above to populate results")
