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
  - Phase 53 (D-07/D-10): speaker_undetermined and is_inaudible_marker are
    rendering facts, not trust facts — safe to expose publicly. The raw
    source form of a canonicalised marker row is deliberately NOT added
    here; D-10 keeps that column in the database only, so a leak-ban grep
    for its name never needs to touch this file. Public and admin both
    read the canonical `text`.
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
    # D-12: server-computed from structured name parts (api.domain.person_names
    # .derive_initials) — the client no longer parses a name string for the
    # avatar glyph. Nullable because speaker_name itself is nullable when
    # person_id is null.
    speaker_initials: Optional[str] = None
    # D-05/D-12 (Phase 53): a rendering fact, not a trust fact — whether
    # this row's speaker is the source's own "no identifiable speaker"
    # sentinel. A legacy row (written before migration 0033, NULL in the
    # DB) serialises as False, matching pre-Phase-53 rendering exactly.
    speaker_undetermined: bool = False
    # D-04/D-12/D-15 (Phase 53): a rendering fact — whether this row's
    # whole turn is the canonical Inaudible marker (a known or undetermined
    # speaker's words were lost, not a room event). NULL reads as False.
    is_inaudible_marker: bool = False

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
