"""
Tests for pipeline.corpus.stage_directions.detect_stage_direction (D-17).

Covers the positive curated-vocabulary matches (brackets and parens), typo
tolerance, and the explicit negative cases (legal-list markers, the
phonetic-spelling marker, and plain speech) that a blind bracket/paren
regex would have misclassified.
"""

from pipeline.corpus.stage_directions import detect_stage_direction


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
