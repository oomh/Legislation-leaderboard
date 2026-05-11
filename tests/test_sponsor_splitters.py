"""Tests for assembly and senate sponsor splitter logic."""

import pandas as pd
import pytest

from src.transformations.bills import (
    _has_multiple_names,
    _ASSEMBLY_OFFICE_PATTERN,
    extract_multi_sponsored_bills,
    extract_office_sponsored_bills,
    extract_residue_bills,
    partition_assembly_bills,
)


def _is_office_sponsor(sponsor: str) -> bool:
    return bool(_ASSEMBLY_OFFICE_PATTERN.search(str(sponsor)))


def _df(sponsors):
    return pd.DataFrame({"sponsor": sponsors, "bill": range(len(sponsors))})


class TestIsOfficeSponsor:
    def test_leader_keyword(self):
        assert _is_office_sponsor("Majority Leader") is True

    def test_speaker_keyword(self):
        assert _is_office_sponsor("The Speaker") is True

    def test_chairperson_keyword(self):
        assert _is_office_sponsor("Chairperson, Agriculture Committee") is True

    def test_regular_name_is_false(self):
        assert _is_office_sponsor("John Doe") is False

    def test_case_insensitive(self):
        assert _is_office_sponsor("MINORITY WHIP") is True


class TestHasMultipleNames:
    def test_comma_separated(self):
        assert _has_multiple_names("Alice Wanjiku, Bob Kamau") is True

    def test_and_separated(self):
        assert _has_multiple_names("Alice Wanjiku and Bob Kamau") is True

    def test_single_name_is_false(self):
        assert _has_multiple_names("Alice Wanjiku") is False

    def test_ampersand_separated(self):
        assert _has_multiple_names("Alice & Bob") is True


class TestPartition:
    def setup_method(self):
        self.df = _df([
            "Majority Leader",          # office
            "Alice Wanjiku and Bob",    # multi
            "Jane Muthoni",             # residue
            "Minority Whip",            # office
            "Carol, Dave",              # multi
        ])

    def test_office_count(self):
        office, multi, residue = partition_assembly_bills(self.df)
        assert len(office) == 2

    def test_multi_count(self):
        office, multi, residue = partition_assembly_bills(self.df)
        assert len(multi) == 2

    def test_residue_count(self):
        office, multi, residue = partition_assembly_bills(self.df)
        assert len(residue) == 1

    def test_partitions_are_non_overlapping(self):
        office, multi, residue = partition_assembly_bills(self.df)
        all_idx = list(office.index) + list(multi.index) + list(residue.index)
        assert len(all_idx) == len(set(all_idx)), "Partitions overlap"

    def test_partitions_cover_all_rows(self):
        office, multi, residue = partition_assembly_bills(self.df)
        assert len(office) + len(multi) + len(residue) == len(self.df)
