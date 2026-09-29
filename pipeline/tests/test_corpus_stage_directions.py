"""
Tests for pipeline.corpus.stage_directions.detect_stage_direction (D-17).

Covers the positive curated-vocabulary matches (brackets and parens), typo
tolerance, and the explicit negative cases (legal-list markers, the
phonetic-spelling marker, and plain speech) that a blind bracket/paren
regex would have misclassified.

Phase 53 plan 53-02 adds: trailing-period tolerance (D-08, the fix noted
in CONTEXT.md's Claude's Discretion), canonical_marker_text (D-08), and
the INAUDIBLE_LABEL / ROOM_EVENT_LABELS vocabulary split (D-03/D-04).
"""

import pytest

from pipeline.corpus.stage_directions import (
    CURATED_MARKERS,
    INAUDIBLE_LABEL,
    ROOM_EVENT_LABELS,
    canonical_marker_text,
    detect_stage_direction,
)


class TestPositiveMatches:
    def test_inaudible_in_parens(self):
        assert detect_stage_direction("(Inaudible)") == "Inaudible"

    def test_laughter_in_brackets(self):
        assert detect_stage_direction("[Laughter]") == "Laughter"

    def test_laughs_in_brackets(self):
        assert detect_stage_direction("[Laughs]") == "Laughter"

    def test_laughter_in_parens(self):
        assert detect_stage_direction("(Laughter)") == "Laughter"

    def test_voice_overlap_in_parens(self):
        assert detect_stage_direction("(Voice Overlap)") == "Voice Overlap"

    def test_recess_in_parens(self):
        assert detect_stage_direction("(Recess)") == "Recess"

    def test_luncheon_recess_in_parens(self):
        assert detect_stage_direction("(Luncheon Recess)") == "Luncheon Recess"

    def test_cross_talk_in_parens(self):
        assert detect_stage_direction("(Cross Talk)") == "Cross Talk"


class TestTypoTolerance:
    def test_luaghter_typo(self):
        assert detect_stage_direction("(Luaghter)") == "Laughter"

    def test_inaudibel_typo(self):
        assert detect_stage_direction("[Inaudibel]") == "Inaudible"


class TestNegativeCases:
    """The explicit anti-cases: a blind paren regex would misclassify these."""

    def test_legal_list_marker_a(self):
        assert detect_stage_direction("(a)") is None

    def test_legal_list_marker_b(self):
        assert detect_stage_direction("(b)") is None

    def test_legal_list_marker_1(self):
        assert detect_stage_direction("(1)") is None

    def test_legal_list_marker_2(self):
        assert detect_stage_direction("(2)") is None

    def test_phonetic_marker_ph(self):
        assert detect_stage_direction("(ph)") is None

    def test_plain_sentence_no_marker(self):
        assert (
            detect_stage_direction(
                "Counsel, would you please address the question presented?"
            )
            is None
        )

    def test_plain_sentence_with_parenthetical_citation(self):
        assert (
            detect_stage_direction(
                "The statute is governed by section (a) of the code."
            )
            is None
        )


class TestTrailingPeriodTolerance:
    """D-08: "(Inaudible)." / "[Inaudible]." must be detected -- the
    trailing-period fix flagged in Phase 53 CONTEXT.md's Claude's
    Discretion. The legal-list/phonetic anti-cases must still be rejected
    with a trailing period too."""

    def test_inaudible_paren_trailing_period(self):
        assert detect_stage_direction("(Inaudible).") == "Inaudible"

    def test_inaudible_bracket_trailing_period(self):
        assert detect_stage_direction("[Inaudible].") == "Inaudible"

    def test_inaudible_inner_period_still_matches(self):
        """Pre-existing behavior (inner period, not trailing) must not
        regress."""
        assert detect_stage_direction("(Inaudible.)") == "Inaudible"

    def test_legal_list_marker_a_trailing_period_still_rejected(self):
        assert detect_stage_direction("(a).") is None

    def test_legal_list_marker_1_trailing_period_still_rejected(self):
        assert detect_stage_direction("(1).") is None


class TestCanonicalMarkerText:
    """D-08: canonical_marker_text is the one place that wraps a curated
    label in the display form; it must refuse anything not curated."""

    def test_wraps_curated_label_in_round_parens(self):
        assert canonical_marker_text("Voice Overlap") == "(Voice Overlap)"

    def test_rejects_uncurated_label(self):
        with pytest.raises(ValueError):
            canonical_marker_text("Nonsense")


class TestVocabularySplit:
    """D-03/D-04: Inaudible is the one transcription failure; every other
    curated label is a room event."""

    def test_inaudible_label_constant(self):
        assert INAUDIBLE_LABEL == "Inaudible"

    def test_room_event_labels_excludes_inaudible(self):
        assert ROOM_EVENT_LABELS == frozenset(
            {"Laughter", "Voice Overlap", "Recess", "Luncheon Recess", "Cross Talk"}
        )
        assert INAUDIBLE_LABEL not in ROOM_EVENT_LABELS

    def test_room_event_labels_is_curated_minus_inaudible(self):
        assert ROOM_EVENT_LABELS == CURATED_MARKERS - {INAUDIBLE_LABEL}
