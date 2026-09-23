"""
Tests for api.domain.content_digest (Phase 50, plan 50-01, Task 2).

Pure unit tests, no database — mirrors api/tests/test_authority_matrix.py's
Section 1 (pure unit matrix over api.domain.authority) convention. This
module must collect and pass with NO DATABASE_URL/TEST_DATABASE_URL set at
all, proving compute_utterance_digest needs no database.

Covers every <behavior> bullet in 50-01-PLAN.md Task 2:
    - Determinism: two calls over the same row list return the same digest.
    - Shape: 64 lowercase hex characters, matching hashlib.sha256 of the
      documented serialization.
    - Sensitivity: a one-character text change, an is_stage_direction flip,
      and a None-vs-"" raw_speaker_label distinction each change the digest.
    - Order sensitivity: reordering two rows changes the digest.
    - Empty input: a stable, non-empty 64-character digest, distinct from
      the digest of a one-row list.
    - Strict ascending sequence validation: a mis-ordered sequence raises
      ValueError rather than silently hashing a mis-ordered set.
    - Field allow-list: extra keys on a row are ignored by the digest.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from api.domain.content_digest import DIGEST_VERSION, compute_utterance_digest


def _row(sequence: int, raw_speaker_label, text: str, is_stage_direction: bool) -> dict:
    return {
        "sequence": sequence,
        "raw_speaker_label": raw_speaker_label,
        "text": text,
        "is_stage_direction": is_stage_direction,
    }


_ROWS = [
    _row(1, "Jane Roe", "May it please the Court.", False),
    _row(2, None, "(Laughter)", True),
    _row(3, "Test Justice Bench", "Counsel, what about the statute's plain text?", False),
]


def test_digest_version_is_frozen_at_1():
    assert DIGEST_VERSION == 1


def test_two_calls_over_same_rows_are_deterministic():
    assert compute_utterance_digest(_ROWS) == compute_utterance_digest(_ROWS)


def test_digest_is_64_char_lowercase_hex_matching_documented_serialization():
    digest = compute_utterance_digest(_ROWS)
    assert len(digest) == 64
    assert digest == digest.lower()
    assert all(c in "0123456789abcdef" for c in digest)

    expected_payload = [
        [1, "Jane Roe", "May it please the Court.", False],
        [2, None, "(Laughter)", True],
        [3, "Test Justice Bench", "Counsel, what about the statute's plain text?", False],
    ]
    expected_blob = json.dumps(
        expected_payload, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    assert digest == hashlib.sha256(expected_blob).hexdigest()


def test_changing_one_character_of_text_changes_digest():
    changed = [
        _row(1, "Jane Roe", "May it please the Courts.", False),
        _row(2, None, "(Laughter)", True),
        _row(3, "Test Justice Bench", "Counsel, what about the statute's plain text?", False),
    ]
    assert compute_utterance_digest(changed) != compute_utterance_digest(_ROWS)


def test_changing_is_stage_direction_changes_digest():
    changed = [
        _row(1, "Jane Roe", "May it please the Court.", False),
        _row(2, None, "(Laughter)", False),
        _row(3, "Test Justice Bench", "Counsel, what about the statute's plain text?", False),
    ]
    assert compute_utterance_digest(changed) != compute_utterance_digest(_ROWS)


def test_raw_speaker_label_none_vs_empty_string_are_distinct():
    none_rows = [_row(1, None, "Text.", False)]
    empty_rows = [_row(1, "", "Text.", False)]
    assert compute_utterance_digest(none_rows) != compute_utterance_digest(empty_rows)


def test_reordering_two_rows_changes_digest():
    reordered = [
        _row(1, None, "(Laughter)", True),
        _row(2, "Jane Roe", "May it please the Court.", False),
        _row(3, "Test Justice Bench", "Counsel, what about the statute's plain text?", False),
    ]
    assert compute_utterance_digest(reordered) != compute_utterance_digest(_ROWS)


def test_empty_row_list_returns_stable_nonempty_digest_distinct_from_one_row():
    empty_digest = compute_utterance_digest([])
    assert len(empty_digest) == 64
    assert empty_digest != ""
    assert empty_digest == compute_utterance_digest([])

    one_row_digest = compute_utterance_digest([_row(1, "Jane Roe", "Hi.", False)])
    assert empty_digest != one_row_digest


def test_non_ascending_sequence_raises_value_error():
    bad_rows = [
        _row(1, "Jane Roe", "May it please the Court.", False),
        _row(3, None, "(Laughter)", True),  # skips 2 -- not strictly ascending
    ]
    with pytest.raises(ValueError):
        compute_utterance_digest(bad_rows)


def test_sequence_not_starting_at_1_raises_value_error():
    bad_rows = [_row(0, "Jane Roe", "May it please the Court.", False)]
    with pytest.raises(ValueError):
        compute_utterance_digest(bad_rows)


def test_never_resorts_mis_ordered_input_raises_rather_than_silently_hashing():
    """A descending sequence must raise, not be silently sorted into an
    ascending run and hashed anyway."""
    bad_rows = [
        _row(2, "Jane Roe", "May it please the Court.", False),
        _row(1, None, "(Laughter)", True),
    ]
    with pytest.raises(ValueError):
        compute_utterance_digest(bad_rows)


def test_extra_keys_outside_the_frozen_field_list_are_ignored():
    rows_with_extra = [
        {
            "sequence": 1,
            "raw_speaker_label": "Jane Roe",
            "text": "May it please the Court.",
            "is_stage_direction": False,
            "person_id": 42,
            "side": "PETITIONER",
            "section_hint": "petitioner",
            "id": 99,
            "argument_id": 7,
            "import_run_id": 12,
        }
    ]
    plain_rows = [_row(1, "Jane Roe", "May it please the Court.", False)]
    assert compute_utterance_digest(rows_with_extra) == compute_utterance_digest(plain_rows)
