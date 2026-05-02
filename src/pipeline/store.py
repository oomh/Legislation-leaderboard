"""PipelineStore

Plain Python data store for the legislation pipeline.
Replaces st.session_state so pipeline steps can run outside Streamlit.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from loguru import logger as log

_PIPELINE_DATA_DIR = Path(__file__).parent / "pipeline_data"

# Keys whose values are plain dicts/lists (serialised as JSON)
_JSON_KEYS = {
    "bill_tracker_urls",
    "bill_trackers_processed",
    "house_leadership",
    "member_lists",
    "committee_leadership",
    "mineru_extraction_results",
    "table_builder_results",
    "raw_senate_bills",
    "raw_assembly_bills",
    "raw_committee_membership",
}

# Keys that may contain nested DataFrames inside a result dict
_RESULT_DICT_KEYS = {
    "table_builder_results",
    "raw_senate_bills",
    "raw_assembly_bills",
    "raw_committee_membership",
}


class PipelineStore:
    """Plain Python data store mirroring all st.session_state pipeline keys."""

    def __init__(self) -> None:
        self.bill_tracker_urls: dict = {"senate": [], "assembly": []}
        self.bill_trackers_processed: dict = {"senate": [], "assembly": []}
        self.house_leadership: dict = {"senate": [], "assembly": []}
        self.member_lists: dict = {"senate": [], "assembly": []}
        self.committee_leadership: list = []
        self.mineru_extraction_results: dict | None = None
        self.table_builder_results: dict | None = None
        self.raw_senate_bills: dict | None = None
        self.raw_assembly_bills: dict | None = None
        self.raw_committee_membership: dict | None = None
        self.transformed_data: dict | None = None

    # ── Persistence ────────────────────────────────────────────────────────────

    def save(self) -> None:
        """Persist all store data to src/pipeline/pipeline_data/."""
        _PIPELINE_DATA_DIR.mkdir(parents=True, exist_ok=True)

        for key in _JSON_KEYS:
            val = getattr(self, key, None)
            if val is None:
                continue
            try:
                _save_json(val, _PIPELINE_DATA_DIR / f"{key}.json")
            except Exception as e:
                log.warning(f"Could not save {key} as JSON: {e}")

        # transformed_data may contain nested DataFrames — save separately
        if self.transformed_data is not None:
            try:
                _save_transformed_data(self.transformed_data, _PIPELINE_DATA_DIR)
            except Exception as e:
                log.warning(f"Could not save transformed_data: {e}")

        log.info(f"PipelineStore saved to {_PIPELINE_DATA_DIR}")

    @classmethod
    def from_disk(cls) -> "PipelineStore":
        """Reconstruct store from any previously saved files in pipeline_data/."""
        store = cls()

        if not _PIPELINE_DATA_DIR.exists():
            log.info("No pipeline_data directory found — returning empty store")
            return store

        for key in _JSON_KEYS:
            path = _PIPELINE_DATA_DIR / f"{key}.json"
            if path.exists():
                try:
                    setattr(store, key, _load_json(path))
                    log.debug(f"Loaded {key} from disk")
                except Exception as e:
                    log.warning(f"Could not load {key}: {e}")

        # Restore transformed_data with DataFrames from parquet
        transformed_path = _PIPELINE_DATA_DIR / "transformed_data"
        if transformed_path.exists():
            try:
                store.transformed_data = _load_transformed_data(transformed_path)
                log.debug("Loaded transformed_data from disk")
            except Exception as e:
                log.warning(f"Could not load transformed_data: {e}")

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


def _save_transformed_data(data: dict, base: Path) -> None:
    """Save transformed_data — nested dicts with DataFrames — as parquet + JSON."""
    td_dir = base / "transformed_data"
    td_dir.mkdir(exist_ok=True)
    serialised = _serialise_result_dict(data)
    with open(td_dir / "transformed_data.json", "w", encoding="utf-8") as f:
        json.dump(serialised, f, indent=2, default=str)


def _load_transformed_data(path: Path) -> dict:
    json_path = path / "transformed_data.json"
    with open(json_path, encoding="utf-8") as f:
        raw = json.load(f)
    return _deserialise_result_dict(raw)
