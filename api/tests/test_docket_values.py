"""
Unit tests for api/domain/docket_values.py (Phase 38 gap closure G-38-6/T-38-20).

Drives every case in api/tests/fixtures/docket_value_cases.json through
normalize_docket_value, plus two constructed length-boundary tests derived
directly from DOCKET_VALUE_MAX_LENGTH (never hand-counted into the fixture,
so the boundary can never drift from the module constant).

No DB, no ASGI client, no network — this file passes with no DATABASE_URL
set, like api/tests/test_docket_arg_safety.py does.

Run with:
    pytest api/tests/test_docket_values.py -x -q
"""

import json
import pathlib

import pytest

from api.domain.docket_values import (
    DOCKET_VALUE_ECHO_LIMIT,
    DOCKET_VALUE_MAX_LENGTH,
    DOCKET_VALUE_PATTERN,
    DocketValueError,
    normalize_docket_value,
)

# A generous bound on the total raised-message length: the bounded-echo
# budget plus the ellipsis character plus room for the surrounding
# static wording. If _bounded_echo ever stopped truncating, this would
# catch it long before a multi-kilobyte value could inflate a 422 body or
# admin_jobs.error_message column.
_MAX_MESSAGE_LENGTH = 200


def _fixture_path() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "fixtures" / "docket_value_cases.json"


def _load_fixture() -> dict:
    with open(_fixture_path(), encoding="utf-8") as f:
        return json.load(f)


_FIXTURE = _load_fixture()


# ---------------------------------------------------------------------------
# Fixture <-> module agreement (T-38-25: fixture proves it agrees with the
# canonical module rather than silently carrying a weaker/divergent copy)
# ---------------------------------------------------------------------------


def test_fixture_pattern_matches_module_constant():
    assert _FIXTURE["metadata"]["pattern"] == DOCKET_VALUE_PATTERN


def test_fixture_max_length_matches_module_constant():
    assert _FIXTURE["metadata"]["max_length"] == DOCKET_VALUE_MAX_LENGTH


# ---------------------------------------------------------------------------
# Valid cases — every real docket shape normalizes unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    _FIXTURE["valid_cases"],
    ids=[c["name"] for c in _FIXTURE["valid_cases"]],
)
def test_valid_cases_normalize_as_expected(case):
    assert normalize_docket_value(case["value"]) == case["normalized"]


# ---------------------------------------------------------------------------
# Invalid cases — every path-hazard, over-length, and blank case raises the
# documented code
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    _FIXTURE["invalid_cases"],
    ids=[c["name"] for c in _FIXTURE["invalid_cases"]],
)
def test_invalid_cases_raise_expected_code(case):
    with pytest.raises(DocketValueError) as exc_info:
        normalize_docket_value(case["value"])
    assert exc_info.value.code == case["code"]


# ---------------------------------------------------------------------------
# Constructed length-boundary tests — derived from DOCKET_VALUE_MAX_LENGTH so
# the boundary can never drift from the module constant (never hand-counted
# into the fixture)
# ---------------------------------------------------------------------------


def test_max_length_value_is_accepted():
    value = "a" * DOCKET_VALUE_MAX_LENGTH
    assert normalize_docket_value(value) == value


def test_one_over_max_length_value_raises_length_exceeded():
    value = "a" * (DOCKET_VALUE_MAX_LENGTH + 1)
    with pytest.raises(DocketValueError) as exc_info:
        normalize_docket_value(value)
    assert exc_info.value.code == "length_exceeded"


# ---------------------------------------------------------------------------
# Bounded-echo enforcement — every raised message stays small even for a
# multi-kilobyte submitted value
# ---------------------------------------------------------------------------


def test_error_messages_are_bounded():
    long_invalid_value = "!" + ("x" * 5000)  # invalid leading char, huge length
    with pytest.raises(DocketValueError) as exc_info:
        normalize_docket_value(long_invalid_value)
    assert len(str(exc_info.value)) <= _MAX_MESSAGE_LENGTH


def test_error_messages_are_bounded_for_over_length_value():
    long_value = "a" * 5000
    with pytest.raises(DocketValueError) as exc_info:
        normalize_docket_value(long_value)
    assert exc_info.value.code == "length_exceeded"
    assert len(str(exc_info.value)) <= _MAX_MESSAGE_LENGTH


def test_bounded_echo_limit_is_smaller_than_max_message_length():
    # Sanity check on the test's own bound relative to the module constant.
    assert DOCKET_VALUE_ECHO_LIMIT < _MAX_MESSAGE_LENGTH
