"""
Direct exhaustiveness + KeyError regression test for reason_left_title()
(Phase 39 D-01, D-02, D-15).

office_title() has no equivalent direct test today — this one exists because
this phase intentionally reverses a documented information-disclosure
exclusion (T-14-02) and a non-canonical value reaching the popover would
otherwise only be caught in production (39-RESEARCH.md Wave 0 Gaps).

Pure Python — no database required.
"""

import pytest

from api.models.models import (
    Person,
    REASON_DIED,
    REASON_LEFT_TITLES,
    REASON_PROMOTED,
    REASON_RETIRED,
    VALID_REASONS_LEFT,
    reason_left_title,
)


class TestReasonLeftTitleExhaustiveness:
    """reason_left_title() returns exactly the three canonical display titles
    and raises KeyError for anything else (D-15)."""

    def test_retired_returns_retired(self):
        assert reason_left_title(REASON_RETIRED) == "Retired"
        assert reason_left_title("retired") == "Retired"

    def test_died_returns_died_in_office(self):
        assert reason_left_title(REASON_DIED) == "Died in office"
        assert reason_left_title("died") == "Died in office"

    def test_promoted_returns_promoted(self):
        assert reason_left_title(REASON_PROMOTED) == "Promoted"
        assert reason_left_title("promoted") == "Promoted"

    def test_unrecognized_value_raises_key_error(self):
        """'resigned' is not one of the three canonical values — never coerced,
        never falls back to a generic label."""
        with pytest.raises(KeyError):
            reason_left_title("resigned")

    def test_empty_string_raises_key_error(self):
        with pytest.raises(KeyError):
            reason_left_title("")

    def test_wrong_case_raises_key_error(self):
        """'Retired' (capitalized, matching the raw CSV vocabulary) is not the
        canonical lowercase value — no case-normalization/coercion."""
        with pytest.raises(KeyError):
            reason_left_title("Retired")


class TestValidReasonsLeftExhaustiveness:
    """VALID_REASONS_LEFT and REASON_LEFT_TITLES' key set must always match,
    so the mapping can never drift out of exhaustiveness."""

    def test_valid_reasons_left_matches_titles_keys(self):
        assert set(VALID_REASONS_LEFT) == set(REASON_LEFT_TITLES.keys())

    def test_exactly_three_canonical_values(self):
        assert len(VALID_REASONS_LEFT) == 3
        assert set(VALID_REASONS_LEFT) == {"retired", "died", "promoted"}


class TestPersonDeathDate:
    """Person.death_date is a nullable Date column (Phase 39 D-04)."""

    def test_death_date_column_is_nullable(self):
        assert Person.__table__.c.death_date.nullable is True

    def test_fresh_person_death_date_is_none(self):
        person = Person(full_name="Example Person")
        assert person.death_date is None
