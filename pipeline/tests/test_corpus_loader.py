"""
Tests for pipeline.corpus.loader against small temporary fixtures (never
the real 900MB utterances.jsonl file, D-18).
"""

import inspect
import json

from pipeline.corpus.loader import (
    load_cases,
    load_conversation_by_id,
    load_conversations_for_term,
    load_speakers,
    stream_utterances_for_conversation_ids,
)


class TestStreamUtterancesForConversationIds:
    def test_is_a_generator(self):
        assert inspect.isgeneratorfunction(stream_utterances_for_conversation_ids)

    def test_yields_only_wanted_conversation_ids(self, tmp_path):
        fixture = tmp_path / "utterances.jsonl"
        fixture.write_text(
            "\n".join(
                json.dumps(row)
                for row in [
                    {"id": "u1", "conversation_id": "1955_71", "text": "wanted"},
                    {"id": "u2", "conversation_id": "1955_99", "text": "not wanted"},
                    {"id": "u3", "conversation_id": "1956_12", "text": "not wanted"},
                    {"id": "u4", "conversation_id": "1955_71", "text": "also wanted"},
                ]
            ),
            encoding="utf-8",
        )

        result = list(
            stream_utterances_for_conversation_ids(fixture, {"1955_71"})
        )

        assert [row["id"] for row in result] == ["u1", "u4"]

    def test_skips_blank_lines(self, tmp_path):
        fixture = tmp_path / "utterances_with_blanks.jsonl"
        fixture.write_text(
            "\n".join(
                [
                    json.dumps({"id": "u1", "conversation_id": "1955_71"}),
                    "",
                    "   ",
                    json.dumps({"id": "u2", "conversation_id": "1955_71"}),
                ]
            ),
            encoding="utf-8",
        )

        result = list(
            stream_utterances_for_conversation_ids(fixture, {"1955_71"})
        )

        assert [row["id"] for row in result] == ["u1", "u2"]


class TestLoadConversationsForTerm:
    def test_returns_only_prefix_matching_case_ids(self, tmp_path):
        fixture = tmp_path / "conversations.json"
        fixture.write_text(
            json.dumps(
                {
                    "1955_71": {"case_id": "1955_71", "advocates": {}},
                    "1955_99": {"case_id": "1955_99", "advocates": {}},
                    "1956_12": {"case_id": "1956_12", "advocates": {}},
                }
            ),
            encoding="utf-8",
        )

        result = load_conversations_for_term(fixture, 1955)

        assert set(result.keys()) == {"1955_71", "1955_99"}


class TestLoadConversationById:
    def test_returns_the_record_for_a_present_id(self, tmp_path):
        fixture = tmp_path / "conversations.json"
        fixture.write_text(
            json.dumps(
                {
                    "15169": {"case_id": "1966_642", "advocates": {}},
                    "1955_99": {"case_id": "1955_99", "advocates": {}},
                }
            ),
            encoding="utf-8",
        )

        result = load_conversation_by_id(fixture, "15169")

        assert result == {"case_id": "1966_642", "advocates": {}}

    def test_returns_none_for_an_absent_id(self, tmp_path):
        fixture = tmp_path / "conversations.json"
        fixture.write_text(
            json.dumps({"15169": {"case_id": "1966_642", "advocates": {}}}),
            encoding="utf-8",
        )

        result = load_conversation_by_id(fixture, "99999999")

        assert result is None


class TestLoadSpeakers:
    def test_loads_speakers_fully(self, tmp_path):
        fixture = tmp_path / "speakers.json"
        fixture.write_text(
            json.dumps({"j__earl_warren": {"name": "Earl Warren"}}),
            encoding="utf-8",
        )

        result = load_speakers(fixture)

        assert result == {"j__earl_warren": {"name": "Earl Warren"}}


class TestLoadCases:
    def test_indexes_by_id_not_docket_number(self, tmp_path):
        fixture = tmp_path / "cases.jsonl"
        fixture.write_text(
            "\n".join(
                [
                    json.dumps(
                        {"id": "1955_71", "docket_no": "71", "title": "Smith v. Jones"}
                    ),
                    "",
                    json.dumps(
                        {"id": "1955_99", "docket_no": "99", "title": "Doe v. Roe"}
                    ),
                ]
            ),
            encoding="utf-8",
        )

        result = load_cases(fixture)

        assert result["1955_71"]["title"] == "Smith v. Jones"
        assert result["1955_99"]["title"] == "Doe v. Roe"
        assert len(result) == 2

    def test_recycled_docket_number_across_terms_does_not_collide(self, tmp_path):
        """Historical docket numbers repeat across terms (docket "71" is a
        different case in 1955 and 1956) -- indexing by "id" must keep both,
        not silently overwrite one with the other."""
        fixture = tmp_path / "cases.jsonl"
        fixture.write_text(
            "\n".join(
                [
                    json.dumps(
                        {"id": "1955_71", "docket_no": "71", "title": "1955 Case"}
                    ),
                    json.dumps(
                        {"id": "1956_71", "docket_no": "71", "title": "1956 Case"}
                    ),
                ]
            ),
            encoding="utf-8",
        )

        result = load_cases(fixture)

        assert len(result) == 2
        assert result["1955_71"]["title"] == "1955 Case"
        assert result["1956_71"]["title"] == "1956 Case"


def test_stream_prefilter_matches_only_the_real_conversation_id_key(tmp_path):
    """The scan skips unwanted rows by regex before json.loads. A look-alike
    key inside utterance text is escaped in JSON, so it must never be taken
    for the real key -- whichever order the fields appear in, and with or
    without whitespace after the colon."""
    rows = [
        # Real id wanted; text (placed first) mentions an unwanted id.
        {"text": 'he said "conversation_id": "999"', "conversation_id": "1"},
        # Real id unwanted; text mentions a wanted id.
        {"text": 'see "conversation_id": "1"', "conversation_id": "999"},
        {"conversation_id": "2", "text": "plain"},
    ]
    path = tmp_path / "utterances.jsonl"
    lines = [json.dumps(rows[0]), json.dumps(rows[1]), json.dumps(rows[2], separators=(",", ":"))]
    path.write_text("\n".join(lines) + "\n\n", encoding="utf-8")

    got = list(stream_utterances_for_conversation_ids(path, {"1", "2"}))

    assert [r["conversation_id"] for r in got] == ["1", "2"]
