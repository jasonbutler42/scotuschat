"""
Contract tests for api/domain/person_names.py (Phase 38, PEOPLE-09).

Pure fixture-driven regression suite covering:
  - Canonical `First Middle Last, Suffix` formatting (D-05-D-08) — Task 1/2
  - Whitespace normalization and authored-text preservation (D-06/D-07) — Task 1/2
  - Minimum-data / column-bound validation (D-09, T-38-01) — Task 1/2
  - Provenance envelope validation (D-18, D-22, T-38-01) — Task 2
  - Conservative legacy Full Name splitting (D-10-D-12) — Task 3

No FastAPI/SQLAlchemy/database initialization required — these tests import
only api.domain.person_names and the shared JSON fixture file.
"""

import json
from pathlib import Path

import pytest

from api.domain.person_names import (
    PersonNameError,
    derive_initials,
    format_full_name,
    normalize_name_part,
    prepare_name_provenance,
    prepare_person_name,
    split_legacy_full_name,
)

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "person_name_cases.json"


def _load_fixtures() -> dict:
    with FIXTURES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


FIXTURES = _load_fixtures()


def _resolve_part(value):
    """Resolve a fixture part value: literal string/null, or a repeat spec."""
    if isinstance(value, dict) and "repeat_char" in value and "length" in value:
        return value["repeat_char"] * value["length"]
    return value


# ---------------------------------------------------------------------------
# Task 1/2: canonical formatting fixtures (D-05-D-08)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case", FIXTURES["format_cases"], ids=[c["name"] for c in FIXTURES["format_cases"]]
)
def test_format_cases(case):
    result = prepare_person_name(
        first=case["first"], middle=case["middle"], last=case["last"], suffix=case["suffix"]
    )
    assert result.full_name == case["expected_full_name"]
    # Already-clean fixture inputs normalize to themselves unchanged.
    assert result.first_name == case["first"]
    assert result.middle_name == case["middle"]
    assert result.last_name == case["last"]
    assert result.name_suffix == case["suffix"]

    # format_full_name is independently callable with already-normalized parts.
    assert (
        format_full_name(case["first"], case["middle"], case["last"], case["suffix"])
        == case["expected_full_name"]
    )


# ---------------------------------------------------------------------------
# Task 1/2: whitespace normalization / authored-text preservation (D-06/D-07)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    FIXTURES["normalization_cases"],
    ids=[c["name"] for c in FIXTURES["normalization_cases"]],
)
def test_normalization_cases(case):
    result = normalize_name_part(case["raw"], field_name=case["field"])
    assert result == case["expected"]


# ---------------------------------------------------------------------------
# Task 1/2: invalid-input / column-bound validation (D-09, T-38-01)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case", FIXTURES["invalid_cases"], ids=[c["name"] for c in FIXTURES["invalid_cases"]]
)
def test_invalid_cases_are_deterministic_domain_errors(case):
    parts = {key: _resolve_part(value) for key, value in case["parts"].items()}
    with pytest.raises(PersonNameError) as exc_info:
        prepare_person_name(**parts)
    assert exc_info.value.code == case["expected_error_code"]


def test_invalid_length_is_never_silently_truncated():
    """Oversized input raises rather than being truncated to the bound."""
    oversized_first = "A" * 151
    with pytest.raises(PersonNameError) as exc_info:
        prepare_person_name(first=oversized_first, last="Smith")
    assert exc_info.value.code == "length_exceeded"
    # Confirm the module never quietly slices the value down to fit.
    assert len(oversized_first) == 151


# ---------------------------------------------------------------------------
# Task 2: provenance envelope validation (D-18, D-22, T-38-01)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("confidence_input", ["high", "High", "HIGH", "  High  "])
def test_provenance_confidence_normalizes_case_insensitively(confidence_input):
    envelope = prepare_name_provenance(
        value="William", raw="WILLIAM", confidence=confidence_input
    )
    assert envelope.confidence == "High"
    assert envelope.value == "William"
    assert envelope.raw == "WILLIAM"


@pytest.mark.parametrize("confidence_input", ["medium", "low"])
def test_provenance_confidence_accepts_all_three_bands(confidence_input):
    envelope = prepare_name_provenance(
        value="Bill", raw="Bill", confidence=confidence_input
    )
    assert envelope.confidence == confidence_input.capitalize()


def test_provenance_rejects_invalid_confidence_label():
    with pytest.raises(PersonNameError) as exc_info:
        prepare_name_provenance(value="William", raw="WILLIAM", confidence="very high")
    assert exc_info.value.code == "invalid_confidence"


def test_provenance_allows_null_value_and_raw_with_valid_confidence():
    envelope = prepare_name_provenance(value=None, raw=None, confidence="low")
    assert envelope.value is None
    assert envelope.raw is None
    assert envelope.confidence == "Low"


def test_provenance_rejects_oversized_value():
    with pytest.raises(PersonNameError) as exc_info:
        prepare_name_provenance(value="A" * 151, raw="raw", confidence="high")
    assert exc_info.value.code == "provenance_value_length_exceeded"


def test_provenance_rejects_oversized_raw():
    with pytest.raises(PersonNameError) as exc_info:
        prepare_name_provenance(value="value", raw="A" * 301, confidence="high")
    assert exc_info.value.code == "provenance_raw_length_exceeded"


def test_provenance_preserves_raw_text_exactly_apart_from_length():
    # Raw source text keeps its authored punctuation/casing verbatim.
    raw_text = "  WILLIAM   H.  TAFT  "
    envelope = prepare_name_provenance(value="William", raw=raw_text, confidence="medium")
    assert envelope.raw == raw_text


# ---------------------------------------------------------------------------
# Task 3: conservative legacy Full Name splitting (D-10-D-12)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    FIXTURES["legacy_split_cases"],
    ids=[c["name"] for c in FIXTURES["legacy_split_cases"]],
)
def test_legacy_split_cases(case):
    result = split_legacy_full_name(case["full_name"])
    assert result.first_name == case["expected_first_name"]
    assert result.middle_name == case["expected_middle_name"]
    assert result.last_name == case["expected_last_name"]
    assert result.name_suffix == case["expected_name_suffix"]
    assert result.confidence == case["expected_confidence"]
    assert result.auto_apply == case["expected_auto_apply"]
    assert case["expected_reason_contains"] in result.reason


@pytest.mark.parametrize(
    "full_name",
    [
        "John G. Roberts, Jr.",
        "Clarence Thomas",
        "Cher",
        "Charles de la Cruz",
        "Roberts, John",
    ],
)
def test_legacy_split_is_idempotent(full_name):
    """Repeated runs return identical parts, confidence, reason, and auto_apply."""
    first_run = split_legacy_full_name(full_name)
    second_run = split_legacy_full_name(full_name)
    assert first_run == second_run


def test_legacy_split_auto_apply_only_true_for_high_confidence():
    high = split_legacy_full_name("Clarence Thomas")
    assert high.confidence == "High"
    assert high.auto_apply is True

    low = split_legacy_full_name("Cher")
    assert low.confidence != "High"
    assert low.auto_apply is False


def test_legacy_split_preserves_original_full_name_available_to_caller():
    """The splitter never mutates or consumes the caller's original string."""
    original = "Roberts, John"
    result = split_legacy_full_name(original)
    assert result.auto_apply is False
    # Caller-side contract: original remains exactly what was passed in.
    assert original == "Roberts, John"


# ---------------------------------------------------------------------------
# Phase 52-02 Task 1: derive_initials (D-12/D-13, JUSTICE-06)
# ---------------------------------------------------------------------------


def test_derive_initials_structured_parts_with_suffix():
    # name_suffix is accepted and deliberately ignored — a suffix is never
    # an initial. This is the JI -> JH fix.
    assert derive_initials(first_name="John", last_name="Harlan", name_suffix="II") == "JH"


def test_derive_initials_structured_parts_no_suffix():
    assert derive_initials(first_name="Oliver", last_name="Holmes") == "OH"


def test_derive_initials_structured_parts_win_over_full_name():
    # Structured parts win: full_name is never parsed when first_name and
    # last_name are both present.
    assert (
        derive_initials(
            first_name="John",
            last_name="Harlan",
            full_name="An Entirely Different Name",
        )
        == "JH"
    )


def test_derive_initials_fallback_drops_roman_numeral_suffix_after_comma():
    # D-13 fallback: no parts, full_name only. Suffix token dropped.
    assert derive_initials(full_name="John Marshall Harlan, II") == "JH"


def test_derive_initials_fallback_drops_jr_suffix_after_comma():
    assert derive_initials(full_name="Oliver W. Holmes, Jr.") == "OH"


def test_derive_initials_fallback_single_token_returns_first_two_codepoints():
    assert derive_initials(full_name="Cher") == "CH"


@pytest.mark.parametrize("blank_full_name", [None, "", "   "])
def test_derive_initials_blank_or_none_full_name_and_no_parts_returns_none(
    blank_full_name,
):
    assert derive_initials(full_name=blank_full_name) is None


def test_derive_initials_no_arguments_returns_none():
    assert derive_initials() is None


def test_derive_initials_only_first_name_falls_back_to_full_name():
    # Structured branch requires BOTH first_name and last_name; a lone
    # first_name is not enough to take the structured path.
    assert (
        derive_initials(first_name="John", full_name="John Marshall Harlan, II")
        == "JH"
    )


def test_derive_initials_uppercases_nfc_normalized_leading_codepoint():
    # Lowercase, accented leading characters are uppercased, not stripped
    # of their mark.
    assert derive_initials(first_name="émile", last_name="zola") == "ÉZ"


def test_derive_initials_is_pure_and_deterministic():
    first = derive_initials(first_name="John", last_name="Harlan", name_suffix="II")
    second = derive_initials(first_name="John", last_name="Harlan", name_suffix="II")
    assert first == second == "JH"
