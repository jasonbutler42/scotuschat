"""
Tests for pipeline.corpus.apolitical -- the sole sanctioned allowlist
translation layer from raw conversations.json/cases.jsonl dicts into
ORM-bound field values (D-12/D-23 hard apolitical constraint).

Proves two properties for both extractor functions:
    1. Every field in FORBIDDEN_FIELDS is absent from the output, even
       when all of them are present in the input.
    2. The allowlist is POSITIVE: an unrecognized source key never
       leaks into the output (a future field added to the source must
       not silently pass through).
"""

from pipeline.corpus.apolitical import (
    FORBIDDEN_FIELDS,
    extract_case_fields,
    extract_conversation_fields,
)

RAW_CASE_WITH_FORBIDDEN_FIELDS = {
    "title": "Smith v. Jones",
    "petitioner": "Smith",
    "respondent": "Jones",
    "docket_no": "55-71",
    "decided_date": "1956-01-09",
    "citation": "350 U.S. 1",
    "court": "Supreme Court of the United States",
    "year": 1955,
    "transcripts": [{"name": "Oral Argument - November 15, 1955"}],
    "advocates": {"j__earl_warren": {"role": "Chief Justice"}},
    "id": "1955_71",
    # Forbidden outcome/vote fields -- must never appear in the output.
    "win_side": 1,
    "win_side_detail": "affirmed",
    "votes": [1, 0, 1, 1, 0, 1, 1, 0, 1],
    "votes_detail": "6-3",
    "votes_side": 1,
    "scdb_docket_id": "1955-071",
    # An unrecognized future field -- must never leak through.
    "some_future_field_nobody_expects": "surprise",
}

RAW_CONVERSATION_WITH_FORBIDDEN_FIELDS = {
    "conversation_id": "13127",
    "case_id": "1955_71",
    "advocates": {"j__earl_warren": {"side": 3}},
    "win_side": 1,
    "votes_side": 1,
    "some_future_field_nobody_expects": "surprise",
}


class TestForbiddenFieldsConstant:
    def test_forbidden_fields_contains_all_outcome_and_vote_fields(self):
        assert FORBIDDEN_FIELDS == frozenset(
            {
                "win_side",
                "win_side_detail",
                "votes",
                "votes_detail",
                "votes_side",
                "scdb_docket_id",
            }
        )


class TestExtractCaseFields:
    def test_forbidden_fields_never_appear_in_output(self):
        result = extract_case_fields(RAW_CASE_WITH_FORBIDDEN_FIELDS)
        assert set(result.keys()) & FORBIDDEN_FIELDS == set()

    def test_allowlist_is_positive_unexpected_key_does_not_leak(self):
        result = extract_case_fields(RAW_CASE_WITH_FORBIDDEN_FIELDS)
        assert "some_future_field_nobody_expects" not in result

    def test_permitted_fields_are_preserved(self):
        result = extract_case_fields(RAW_CASE_WITH_FORBIDDEN_FIELDS)
        assert result["title"] == "Smith v. Jones"
        assert result["docket_no"] == "55-71"
        assert result["decided_date"] == "1956-01-09"
        assert result["citation"] == "350 U.S. 1"
        assert result["year"] == 1955

    def test_output_is_not_the_input_dict_or_a_shallow_copy(self):
        result = extract_case_fields(RAW_CASE_WITH_FORBIDDEN_FIELDS)
        assert result is not RAW_CASE_WITH_FORBIDDEN_FIELDS


class TestExtractConversationFields:
    def test_forbidden_fields_never_appear_in_output(self):
        result = extract_conversation_fields(RAW_CONVERSATION_WITH_FORBIDDEN_FIELDS)
        assert set(result.keys()) & FORBIDDEN_FIELDS == set()

    def test_allowlist_is_positive_unexpected_key_does_not_leak(self):
        result = extract_conversation_fields(RAW_CONVERSATION_WITH_FORBIDDEN_FIELDS)
        assert "some_future_field_nobody_expects" not in result

    def test_permitted_fields_are_preserved(self):
        result = extract_conversation_fields(RAW_CONVERSATION_WITH_FORBIDDEN_FIELDS)
        assert result["conversation_id"] == "13127"
        assert result["case_id"] == "1955_71"
        assert result["advocates"] == {"j__earl_warren": {"side": 3}}

    def test_output_is_not_the_input_dict_or_a_shallow_copy(self):
        result = extract_conversation_fields(RAW_CONVERSATION_WITH_FORBIDDEN_FIELDS)
        assert result is not RAW_CONVERSATION_WITH_FORBIDDEN_FIELDS
