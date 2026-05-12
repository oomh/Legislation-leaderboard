"""Step 5.5 — Manual Corrections

Applies user-defined find-and-replace edits to the Step 5 results (normalised
bill DataFrames) before they are passed to Step 6.  Corrections are persisted
in a JSON file so they only need to be entered once.

Corrections file format
-----------------------
``data/transformations_memory/manual_corrections.json``

.. code-block:: json

    {
    "assembly": {
        "sponsor": {
        "John Doe": "Hon. John Doe"
        }
    },
    "senate": {
        "sponsor": {
        "J. Smith": "Sen. Jane Smith"
        }
    }
    }

Top-level key   = dataset name (must match a key in ``store.step5_results``).
Second-level key = column name in that dataset's DataFrame.
Third-level key  = current (find) value  →  value = replacement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from loguru import logger as log

from src.pipeline.store import PipelineStore

_CORRECTIONS_PATH = Path("data/transformations_memory/manual_corrections.json")


# ── Public helpers (used by the Streamlit app) ─────────────────────────────────


def load_manual_corrections() -> dict:
    """Return the saved corrections dict, or ``{}`` if the file is missing or empty."""
    if not _CORRECTIONS_PATH.exists():
        return {}
    try:
        with open(_CORRECTIONS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        log.warning(f"Could not read manual corrections: {e}")
        return {}


def save_manual_corrections(corrections: dict) -> None:
    """Persist *corrections* to the corrections JSON file."""
    _CORRECTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CORRECTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(corrections, f, indent=2, ensure_ascii=False)
    log.info(f"Manual corrections saved to {_CORRECTIONS_PATH}")


# ── Pipeline step ──────────────────────────────────────────────────────────────


def run_manual_corrections_step(store: PipelineStore | None = None) -> dict:
    """Apply manual corrections to ``store.step5_results``.

    Returns a standard ``{status, message}`` dict.  Status is ``"skipped"``
    when the corrections file is empty — this is treated as success by the
    orchestrator and does *not* stop the pipeline.
    """
    if store is None:
        store = PipelineStore()

    corrections = load_manual_corrections()

    if not corrections:
        result = {
            "applied": [],
            "total_corrections": 0,
            "status": "skipped",
            "message": "No corrections defined — step skipped",
        }
        store.step5_5_results = result
        return {"status": "skipped", "message": result["message"]}

    applied: list[dict] = []
    errors: list[str] = []

    for dataset, column_map in corrections.items():
        if not isinstance(column_map, dict):
            errors.append(f"Skipped '{dataset}': expected a dict of column mappings")
            continue

        step5_entry = store.step5_results.get(dataset)
        if step5_entry is None:
            errors.append(f"Dataset '{dataset}' not found in step5_results — skipped")
            continue

        df: pd.DataFrame = (
            step5_entry.get("data") if isinstance(step5_entry, dict) else None
        )
        if not isinstance(df, pd.DataFrame):
            errors.append(f"Dataset '{dataset}' has no 'data' DataFrame — skipped")
            continue

        for column, replacements in column_map.items():
            if not isinstance(replacements, dict):
                errors.append(
                    f"Skipped '{dataset}.{column}': expected a dict of {{from: to}} replacements"
                )
                continue

            if column not in df.columns:
                errors.append(
                    f"Column '{column}' not found in dataset '{dataset}' — skipped"
                )
                continue

            before = df[column].copy()
            df[column] = df[column].replace(replacements)
            rows_affected = int((df[column] != before).sum())

            for from_val, to_val in replacements.items():
                applied.append(
                    {
                        "dataset": dataset,
                        "column": column,
                        "from": from_val,
                        "to": to_val,
                        "rows_affected": rows_affected,
                    }
                )
                log.debug(
                    f"Correction applied: [{dataset}].{column} "
                    f"'{from_val}' → '{to_val}' ({rows_affected} rows)"
                )

        # Write modified DataFrame back into step5_results
        if isinstance(step5_entry, dict):
            step5_entry["data"] = df
        else:
            store.step5_results[dataset] = df

    total = len(applied)
    status = "success" if not errors else "partial"
    message = (
        f"Applied {total} correction(s) across "
        f"{len({e['dataset'] for e in applied})} dataset(s)"
        if applied
        else "Corrections defined but none matched any rows"
    )
    if errors:
        message += f"; {len(errors)} warning(s): " + "; ".join(errors)

    store.step5_5_results = {
        "applied": applied,
        "total_corrections": total,
        "status": status,
        "message": message,
    }

    log.info(f"Step 5.5: {message}")
    return {"status": status, "message": message}
