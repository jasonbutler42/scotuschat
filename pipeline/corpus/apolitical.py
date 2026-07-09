"""
Apolitical allowlist extractors (D-12/D-23 hard constraint).

This module is the ONLY sanctioned translation layer from raw
conversations.json / cases.jsonl source dicts into ORM-bound field
values. Raw corpus dicts must NEVER be passed into ORM constructors or
JSONB columns except through the functions defined here.

Both source files carry outcome/vote fields --
``win_side``/``win_side_detail``/``votes``/``votes_detail``/
``votes_side``/``scdb_docket_id`` -- that must never be persisted
anywhere, including in a JSONB metadata blob (the apolitical framing
hard constraint applies to every speaker/case record, with no
exceptions). Each extractor below builds an explicit, positive
allowlisted dict by pulling named keys off the raw dict -- never
``dict(raw)``/``{**raw}``/a blocklist filter -- so a future field added
to the source data can never silently pass through.
"""

from __future__ import annotations

# Fields that must NEVER appear in a dict returned from this module.
# Exposed for tests/guards that assert these are provably absent.
FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "win_side",
        "win_side_detail",
        "votes",
        "votes_detail",
        "votes_side",
        "scdb_docket_id",
    }
)


def extract_case_fields(raw_case: dict) -> dict:
    """
    Build and return an explicit allowlisted dict of permitted case
    fields from a raw cases.jsonl row.

    Never returns the input dict, a copy of it, or a blocklist-filtered
    view -- only the named fields below are ever read from ``raw_case``.
    """
    return {
        "title": raw_case.get("title"),
        "petitioner": raw_case.get("petitioner"),
        "respondent": raw_case.get("respondent"),
        "docket_no": raw_case.get("docket_no"),
        "decided_date": raw_case.get("decided_date"),
        "citation": raw_case.get("citation"),
        "court": raw_case.get("court"),
        "year": raw_case.get("year"),
        "transcripts": raw_case.get("transcripts"),
        "advocates": raw_case.get("advocates"),
        "case_id": raw_case.get("case_id"),
    }


def extract_conversation_fields(raw_conversation: dict) -> dict:
    """
    Build and return an explicit allowlisted dict of permitted
    conversation fields from a raw conversations.json row.

    Never returns the input dict, a copy of it, or a blocklist-filtered
    view -- only the named fields below are ever read from
    ``raw_conversation``.
    """
    return {
        "conversation_id": raw_conversation.get("conversation_id"),
        "case_id": raw_conversation.get("case_id"),
        "advocates": raw_conversation.get("advocates"),
    }
