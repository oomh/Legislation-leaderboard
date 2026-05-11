"""Tests for src/transformations/transformation_helpers.py"""

import pandas as pd
import pytest

from src.transformations.transformation_helpers import (
    apply_mask_to_dataframe,
    create_mask_for_strings,
)


class TestCreateMaskForStrings:
    def test_marks_matching_rows_true(self):
        df = pd.DataFrame({"col": ["header", "data", "header"]})
        mask = create_mask_for_strings(df, ["header"])
        assert mask.tolist() == [True, False, True]

    def test_case_insensitive_by_default(self):
        df = pd.DataFrame({"col": ["HEADER", "data"]})
        mask = create_mask_for_strings(df, ["header"])
        assert mask[0] is True or mask[0]
        assert not mask[1]

    def test_case_sensitive_no_match(self):
        df = pd.DataFrame({"col": ["HEADER", "header"]})
        mask = create_mask_for_strings(df, ["header"], case_sensitive=True)
        assert not mask[0]
        assert mask[1]

    def test_empty_dataframe_returns_empty_mask(self):
        df = pd.DataFrame({"col": pd.Series([], dtype=str)})
        mask = create_mask_for_strings(df, ["anything"])
        assert len(mask) == 0

    def test_multiple_search_strings_union(self):
        df = pd.DataFrame({"col": ["bill", "status", "data"]})
        mask = create_mask_for_strings(df, ["bill", "status"])
        assert mask.tolist() == [True, True, False]

    def test_restricts_to_specified_columns(self):
        df = pd.DataFrame({"a": ["header", "data"], "b": ["header", "header"]})
        mask = create_mask_for_strings(df, ["header"], columns=["a"])
        assert mask.tolist() == [True, False]

    def test_unknown_column_skipped_gracefully(self):
        df = pd.DataFrame({"col": ["data"]})
        mask = create_mask_for_strings(df, ["data"], columns=["nonexistent"])
        assert mask.tolist() == [False]


class TestApplyMaskToDataframe:
    def test_removes_rows_where_mask_is_true(self):
        df = pd.DataFrame({"val": [1, 2, 3]})
        mask = pd.Series([False, True, False])
        result = apply_mask_to_dataframe(df, mask)
        assert result["val"].tolist() == [1, 3]

    def test_resets_index(self):
        df = pd.DataFrame({"val": [10, 20, 30]})
        mask = pd.Series([True, False, False])
        result = apply_mask_to_dataframe(df, mask)
        assert result.index.tolist() == [0, 1]

    def test_all_false_mask_returns_full_dataframe(self):
        df = pd.DataFrame({"val": [1, 2, 3]})
        mask = pd.Series([False, False, False])
        result = apply_mask_to_dataframe(df, mask)
        assert len(result) == 3

    def test_all_true_mask_returns_empty_dataframe(self):
        df = pd.DataFrame({"val": [1, 2, 3]})
        mask = pd.Series([True, True, True])
        result = apply_mask_to_dataframe(df, mask)
        assert len(result) == 0
