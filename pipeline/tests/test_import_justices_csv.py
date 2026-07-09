"""
Tests for pipeline.commands.import_justices_csv.

Covers:
    - Task 1: reconstruct_full_name() byte-for-byte reproduction of all 13
      existing seed_aliases.py Person.full_name literals from CSV-shaped
      name parts (CORPUS-01; guards Pitfall 1 — a mismatch here means a
      silent duplicate Person row at dedup time).

Task 2 adds run_import_justices_csv() DB-integration tests to this file.
"""

import pytest

from pipeline.commands.import_justices_csv import reconstruct_full_name

# ===========================================================================
# Task 1: reconstruct_full_name() — no DB required
# ===========================================================================

# (first, middle, last, suffix, expected seed_aliases.py literal)
# Values taken directly from the real justices tenure CSV rows for these
# 13 people, cross-checked against pipeline/commands/seed_aliases.py's
# _JUSTICES literal names.
_SEEDED_JUSTICE_CASES = [
    ("John", "G.", "Roberts", "Jr.", "John G. Roberts, Jr."),
    ("Clarence", "", "Thomas", "", "Clarence Thomas"),
    ("Samuel", "A.", "Alito", "Jr.", "Samuel A. Alito, Jr."),
    ("Sonia", "", "Sotomayor", "", "Sonia Sotomayor"),
    ("Elena", "", "Kagan", "", "Elena Kagan"),
    ("Neil", "M.", "Gorsuch", "", "Neil M. Gorsuch"),
    ("Brett", "M.", "Kavanaugh", "", "Brett M. Kavanaugh"),
    ("Amy", "Coney", "Barrett", "", "Amy Coney Barrett"),
    ("Ketanji", "Brown", "Jackson", "", "Ketanji Brown Jackson"),
    ("Antonin", "", "Scalia", "", "Antonin Scalia"),
    ("Anthony", "M.", "Kennedy", "", "Anthony M. Kennedy"),
    ("Ruth", "Bader", "Ginsburg", "", "Ruth Bader Ginsburg"),
    ("Stephen", "G.", "Breyer", "", "Stephen G. Breyer"),
]


@pytest.mark.parametrize(
    "first,middle,last,suffix,expected",
    _SEEDED_JUSTICE_CASES,
    ids=[case[4] for case in _SEEDED_JUSTICE_CASES],
)
def test_reconstruct_full_name_matches_seed_aliases_literal(
    first, middle, last, suffix, expected
):
    """Each of the 13 seeded justices must reconstruct byte-identically."""
    assert reconstruct_full_name(first, middle, last, suffix) == expected


def test_reconstruct_full_name_no_middle_name_no_double_space():
    result = reconstruct_full_name("Clarence", "", "Thomas", "")
    assert "  " not in result
    assert result == "Clarence Thomas"


def test_reconstruct_full_name_no_suffix_no_trailing_comma():
    result = reconstruct_full_name("Elena", "", "Kagan", "")
    assert not result.endswith(",")
    assert "," not in result


def test_reconstruct_full_name_with_suffix_matches_exact_seed_form():
    result = reconstruct_full_name("John", "G.", "Roberts", "Jr.")
    assert result == "John G. Roberts, Jr."


def test_reconstruct_full_name_all_13_seeded_justices_reproduced():
    """
    Guards Pitfall 1 directly: every one of the 13 seed_aliases.py literals
    must be reproduced exactly (or via an explicit MANUAL_NAME_OVERRIDES
    entry), or D-02's exact-match dedup silently creates duplicate Person
    rows instead of upgrading the existing seeded row.
    """
    for first, middle, last, suffix, expected in _SEEDED_JUSTICE_CASES:
        assert reconstruct_full_name(first, middle, last, suffix) == expected
