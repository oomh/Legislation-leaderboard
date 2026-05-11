"""PipelineStore

Plain Python data store for the legislation pipeline.
Replaces st.session_state so pipeline steps can run outside Streamlit.

Each pipeline step reads from and writes to its own ``stepN_results`` dict.
All dicts are persisted as individual JSON files in pipeline_data/.

    step1_results          — bill_tracker_urls, house_leadership, member_lists, committee_leadership
    step2_results          — mineru_extraction_results
    step3_results          — senate_bills, assembly_bills, committee_membership
    step4_results          — bill_trackers, leadership, members, committees (individual transforms)
    step5_results          — assembly, senate (normalised bills per sponsor)
    step6_results          — merged_leadership, merged_members
    sponsor_name_corrections — user-supplied manual name overrides; persisted independently
                            of step results so corrections survive pipeline re-runs
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from loguru import logger as log

_PIPELINE_DATA_DIR = Path(__file__).parent / "pipeline_data"

_STEP_KEYS = [
    "step1_results",
    "step2_results",
    "step3_results",
    "step4_results",
    "step5_results",
    "step6_results",
    "sponsor_name_corrections",
]


class PipelineStore:
    """Plain Python data store with one dict per pipeline step."""

    def __init__(self) -> None:
        self.step1_results: dict = {}
        self.step2_results: dict = {}
        self.step3_results: dict = {}
        self.step4_results: dict = {}
        self.step5_results: dict = {}
        self.step6_results: dict = {}
        self.sponsor_name_corrections: dict = {}

    # ── Persistence ────────────────────────────────────────────────────────────

    def save(self) -> None:
        """Persist all step results to src/pipeline/pipeline_data/."""
        _PIPELINE_DATA_DIR.mkdir(parents=True, exist_ok=True)

        for key in _STEP_KEYS:
            val = getattr(self, key, None)
            if not val:
                continue
            try:
                _save_json(val, _PIPELINE_DATA_DIR / f"{key}.json")
            except Exception as e:
                log.warning(f"Could not save {key}: {e}")

        log.info(f"PipelineStore saved to {_PIPELINE_DATA_DIR}")

    @classmethod
    def from_disk(cls) -> "PipelineStore":
        """Reconstruct store from any previously saved step result files."""
        store = cls()

        if not _PIPELINE_DATA_DIR.exists():
            log.info("No pipeline_data directory found — returning empty store")
            return store

        for key in _STEP_KEYS:
            path = _PIPELINE_DATA_DIR / f"{key}.json"
            if path.exists():
                try:
                    setattr(store, key, _load_json(path))
                    log.debug(f"Loaded {key} from disk")
                except Exception as e:
                    log.warning(f"Could not load {key}: {e}")

        log.info(f"PipelineStore loaded from {_PIPELINE_DATA_DIR}")
        return store

    # ── dict-style access (compatibility with st.session_state.get()) ──────────

    def get(self, key: str, default=None):
        return getattr(self, key, default)


# ── Internal helpers ───────────────────────────────────────────────────────────


def _df_to_dict(df: pd.DataFrame) -> dict:
    return df.to_dict(orient="records") if isinstance(df, pd.DataFrame) else {}


def _dict_to_df(d) -> pd.DataFrame:
    if isinstance(d, list):
        return pd.DataFrame(d)
    if isinstance(d, dict):
        return pd.DataFrame(d)
    return pd.DataFrame()


def _serialise_result_dict(val):
    """Recursively serialise result dicts that may contain DataFrames."""
    if isinstance(val, pd.DataFrame):
        return {"__dataframe__": True, "records": val.to_dict(orient="records")}
    if isinstance(val, dict):
        return {k: _serialise_result_dict(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_serialise_result_dict(i) for i in val]
    return val


def _deserialise_result_dict(val):
    """Reconstruct DataFrames from serialised result dicts."""
    if isinstance(val, dict):
        if val.get("__dataframe__"):
            return pd.DataFrame(val.get("records", []))
        return {k: _deserialise_result_dict(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_deserialise_result_dict(i) for i in val]
    return val


def _save_json(val, path: Path) -> None:
    serialised = _serialise_result_dict(val)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(serialised, f, indent=2, default=str)


def _load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return _deserialise_result_dict(raw)
