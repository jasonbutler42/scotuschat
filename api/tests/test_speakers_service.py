"""
Unit tests for tenure date-range role resolution in api/services/speakers.py.

Tests cover (Phase 15, ROLE-01; Phase 37, PEOPLE-08/D-15):
  - _tenure_role_name: empty list returns None
  - _tenure_role_name: argued_date within a window returns that tenure's formal office title
  - _tenure_role_name: open-ended tenure (end_date=None) covers all dates past start
  - _tenure_role_name: argued_date outside all windows returns highest-start_date tenure's
    formal title (D-14)
  - _tenure_role_name: argued_date=None falls back to most-recent tenure (Pitfall 5)
  - _tenure_role_name: valid records always resolve to "Chief Justice"/"Associate Justice",
    never the generic "Justice" fallback (D-15)
  - ADVOCATE_LABEL_MAP: correct label for each SideEnum value

These tests do NOT require a live database — pure Python function tests.
"""

import datetime

import pytest

from api.models.models import OFFICE_ASSOCIATE, OFFICE_CHIEF, SideEnum


# ---------------------------------------------------------------------------
# Module under test
# ---------------------------------------------------------------------------


def _get_helpers():
    """Import the helpers under test (deferred so import errors report clearly)."""
    from api.services.speakers import ADVOCATE_LABEL_MAP, _tenure_role_name

    return _tenure_role_name, ADVOCATE_LABEL_MAP


# ---------------------------------------------------------------------------
# _tenure_role_name tests
# ---------------------------------------------------------------------------


class TestTenureRoleName:
    """Tests for the _tenure_role_name helper."""

    def test_empty_tenures_returns_none(self):
        """_tenure_role_name([], any_date) returns None."""
        _tenure_role_name, _ = _get_helpers()
        assert _tenure_role_name([], datetime.date(2020, 1, 15)) is None

    def test_empty_tenures_none_date_returns_none(self):
        """_tenure_role_name([], None) returns None."""
        _tenure_role_name, _ = _get_helpers()
        assert _tenure_role_name([], None) is None

    def test_argued_date_inside_window_returns_formal_title(self):
        """Returns the formal title whose [start_date, end_date] contains argued_date."""
        _tenure_role_name, _ = _get_helpers()
        tenures = [
            {
                "office": OFFICE_ASSOCIATE,
                "start_date": datetime.date(2010, 8, 7),
                "end_date": datetime.date(2022, 6, 30),
            },
            {
                "office": OFFICE_CHIEF,
                "start_date": datetime.date(2005, 9, 29),
                "end_date": datetime.date(2010, 8, 6),
            },
        ]
        result = _tenure_role_name(tenures, datetime.date(2015, 10, 5))
        assert result == "Associate Justice"

    def test_argued_date_on_start_date_boundary(self):
        """Date exactly on start_date is within the window."""
        _tenure_role_name, _ = _get_helpers()
        tenures = [
            {
                "office": OFFICE_ASSOCIATE,
                "start_date": datetime.date(2020, 1, 1),
                "end_date": datetime.date(2025, 12, 31),
            }
        ]
        result = _tenure_role_name(tenures, datetime.date(2020, 1, 1))
        assert result == "Associate Justice"

    def test_argued_date_on_end_date_boundary(self):
        """Date exactly on end_date is within the window."""
        _tenure_role_name, _ = _get_helpers()
        tenures = [
            {
                "office": OFFICE_ASSOCIATE,
                "start_date": datetime.date(2020, 1, 1),
                "end_date": datetime.date(2025, 12, 31),
            }
        ]
        result = _tenure_role_name(tenures, datetime.date(2025, 12, 31))
        assert result == "Associate Justice"

    def test_open_ended_tenure_end_date_none(self):
        """end_date=None means the tenure is open-ended (currently active)."""
        _tenure_role_name, _ = _get_helpers()
        tenures = [
            {
                "office": OFFICE_ASSOCIATE,
                "start_date": datetime.date(2018, 10, 6),
                "end_date": None,  # open-ended
            }
        ]
        result = _tenure_role_name(tenures, datetime.date(2023, 11, 1))
        assert result == "Associate Justice"

    def test_argued_date_before_all_tenures_uses_fallback(self):
        """D-14: argued_date earlier than all windows returns highest-start_date
        tenure's formal title."""
        _tenure_role_name, _ = _get_helpers()
        tenures = [
            {
                "office": OFFICE_CHIEF,
                "start_date": datetime.date(2005, 9, 29),
                "end_date": datetime.date(2010, 8, 6),
            },
            {
                "office": OFFICE_ASSOCIATE,
                "start_date": datetime.date(2010, 8, 7),
                "end_date": datetime.date(2022, 6, 30),
            },
        ]
        # argued_date is before both tenures
        result = _tenure_role_name(tenures, datetime.date(2000, 1, 1))
        # Fallback: most recent tenure by start_date = the associate tenure
        assert result == "Associate Justice"

    def test_argued_date_after_all_tenures_uses_fallback(self):
        """D-14: argued_date later than all closed windows returns highest-start_date
        tenure's formal title."""
        _tenure_role_name, _ = _get_helpers()
        tenures = [
            {
                "office": OFFICE_CHIEF,
                "start_date": datetime.date(2005, 9, 29),
                "end_date": datetime.date(2010, 8, 6),
            },
        ]
        # argued_date is after the only tenure's end_date
        result = _tenure_role_name(tenures, datetime.date(2015, 5, 1))
        assert result == "Chief Justice"

    def test_argued_date_none_uses_most_recent_tenure(self):
        """Pitfall 5: argued_date=None returns the most-recent tenure's formal title."""
        _tenure_role_name, _ = _get_helpers()
        tenures = [
            {
                "office": OFFICE_ASSOCIATE,
                "start_date": datetime.date(2000, 1, 1),
                "end_date": datetime.date(2010, 6, 30),
            },
            {
                "office": OFFICE_CHIEF,
                "start_date": datetime.date(2015, 9, 1),
                "end_date": None,
            },
        ]
        result = _tenure_role_name(tenures, None)
        assert result == "Chief Justice"

    def test_single_tenure_no_start_date_returns_formal_title(self):
        """A tenure with start_date=None falls back correctly (date.min key)."""
        _tenure_role_name, _ = _get_helpers()
        tenures = [
            {
                "office": OFFICE_ASSOCIATE,
                "start_date": None,
                "end_date": None,
            }
        ]
        result = _tenure_role_name(tenures, None)
        assert result == "Associate Justice"

    def test_valid_records_never_return_generic_justice_fallback(self):
        """D-15: every valid canonical office resolves to its formal title, never
        the bare generic "Justice" wording, regardless of window match or fallback."""
        _tenure_role_name, _ = _get_helpers()
        for office, expected in ((OFFICE_CHIEF, "Chief Justice"), (OFFICE_ASSOCIATE, "Associate Justice")):
            tenures = [
                {
                    "office": office,
                    "start_date": datetime.date(2000, 1, 1),
                    "end_date": None,
                }
            ]
            assert _tenure_role_name(tenures, datetime.date(2001, 1, 1)) == expected
            assert _tenure_role_name(tenures, None) == expected
            assert _tenure_role_name(tenures, datetime.date(1990, 1, 1)) == expected


# ---------------------------------------------------------------------------
# ADVOCATE_LABEL_MAP tests
# ---------------------------------------------------------------------------


class TestAdvocateLabelMap:
    """Tests for the ADVOCATE_LABEL_MAP constant."""

    def test_petitioner_label(self):
        _, ADVOCATE_LABEL_MAP = _get_helpers()
        assert ADVOCATE_LABEL_MAP[SideEnum.PETITIONER] == "Petitioner's Counsel"

    def test_respondent_label(self):
        _, ADVOCATE_LABEL_MAP = _get_helpers()
        assert ADVOCATE_LABEL_MAP[SideEnum.RESPONDENT] == "Respondent's Counsel"

    def test_amicus_label(self):
        _, ADVOCATE_LABEL_MAP = _get_helpers()
        assert ADVOCATE_LABEL_MAP[SideEnum.AMICUS] == "Amicus Curiae"

    def test_unknown_label(self):
        _, ADVOCATE_LABEL_MAP = _get_helpers()
        assert ADVOCATE_LABEL_MAP[SideEnum.UNKNOWN] == "Counsel"

    def test_advocate_legacy_label(self):
        """SideEnum.ADVOCATE (legacy) must map to 'Counsel' (Pitfall 4)."""
        _, ADVOCATE_LABEL_MAP = _get_helpers()
        assert ADVOCATE_LABEL_MAP[SideEnum.ADVOCATE] == "Counsel"

    def test_bench_not_in_map(self):
        """BENCH is not an advocate — it must NOT appear in ADVOCATE_LABEL_MAP."""
        _, ADVOCATE_LABEL_MAP = _get_helpers()
        assert SideEnum.BENCH not in ADVOCATE_LABEL_MAP
