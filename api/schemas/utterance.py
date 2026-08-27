"""
Pydantic v2 response models for the utterances API endpoint.

These models define the JSON shape returned by GET /arguments/{id}/utterances.
The schema is stable from Phase 1 through Phase 3 — downstream SvelteKit
components depend on this contract.

Key design decisions:
  - UtteranceResponse uses from_attributes=True for ORM → Pydantic serialization.
  - ArgumentMetadataResponse carries the metadata the UI heading bar needs:
    case_name, docket_number, argued_date, question_number.
  - person_id is null at Phase 1; Phase 2 Resolve step populates it.
  - import_run_id is included so callers can confirm which parse run is shown.
"""

import datetime
from typing import Optional

from pydantic import BaseModel


class UtteranceResponse(BaseModel):
    """One spoken utterance or stage direction from the argument transcript."""

    id: int
    sequence: int
    raw_speaker_label: Optional[str] = None
    text: str
    is_stage_direction: bool
    side: str  # "BENCH" | "ADVOCATE" | "UNKNOWN"
    section_hint: Optional[str] = None
    person_id: Optional[int] = None  # null at Phase 1; populated by Resolve step
    import_run_id: int  # which parse run produced this row
    speaker_name: Optional[str] = None   # Resolved from people table
    speaker_role: Optional[str] = None   # Resolved from roles table

    model_config = {"from_attributes": True}


class ArgumentMetadataResponse(BaseModel):
    """Argument-level metadata for the heading bar in the chat view."""

    argument_id: int
    case_name: str
    docket_number: str  # lead docket number (e.g. "14-556")
    # Optional: nullable at the DB layer (Argument.argued_date, models.py:175).
    # Corpus-imported arguments (import_convokit.py _parse_argued_date) can
    # legitimately have no parseable transcript date (CR-01 / gap #13 fix).
    argued_date: datetime.date | None = None
    # Optional: nullable at the DB layer as of migration 0019,
    # mirroring argued_date's nullable-column handling directly above.
    question_number: int | None = None
    oyez_transcript_id: str | None = None  # ConvoKit conversation_id; null for PDF-ingested arguments


class ArgumentUtterancesResponse(BaseModel):
    """
    Full response from GET /arguments/{id}/utterances.

    Combines argument metadata (for the heading bar) with the ordered
    utterances list (for the chat column).
    """

    argument: ArgumentMetadataResponse
    utterances: list[UtteranceResponse]
