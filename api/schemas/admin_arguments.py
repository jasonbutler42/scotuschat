"""Pydantic v2 request/response models for the admin arguments API endpoints.

These schemas back the Phase 11 Argument Metadata Editing routes:
  - ArgumentListItem  — one row in the /admin/arguments list (lead case metadata)
  - ConsolidatedDocket — a single non-lead docket number for read-only display (D-10)
  - ArgumentDetail    — full argument data for the edit form (includes consolidated dockets)
  - ArgumentUpdate    — PATCH body (mass-assignment allow-list: only three editable fields)

Phase 15 additions:
  - ParticipantSideUpdate — PATCH body for argument_participants.side (ROLE-03, T-15-02-MASS)
  - TenureGapWarning      — inline warning when bench argued_date outside all tenures (D-15)
  - ArgumentListItem.status  — explicit lifecycle status
  - ArgumentDetail.tenure_gap_warnings — list of TenureGapWarning per affected bench speaker

Security notes:
  - ArgumentUpdate allow-list is exactly {case_name, docket_number, argued_date} (T-11-MASS).
    published_at is NOT in this schema — it is controlled only by /publish and /unpublish.
    slug and id are also excluded — slug is derived server-side; id is path parameter.
  - ParticipantSideUpdate exposes only ``side`` — no other ArgumentParticipant field is
    writable via this schema (T-15-02-MASS).
"""

import datetime
from typing import Optional

from pydantic import BaseModel

from api.models.models import ArgumentStatusEnum, SideEnum


class ParticipantSideUpdate(BaseModel):
    """PATCH body for argument_participants.side (ROLE-03).

    Mass-assignment guard (T-15-02-MASS): ONLY ``side`` is writable via this
    schema.  No other ArgumentParticipant column can be set.  Service validates
    that BENCH cannot be set (T-15-02-BENCH) — operators set advocate roles only.
    """

    side: SideEnum


class StatusLogEntry(BaseModel):
    """One ArgumentStatusLog row (Phase 26, T-26-03).

    Surfaced on the argument edit page's Status history list, ordered
    oldest-first by get_argument_detail's query (created_at asc, id asc tiebreak).
    """

    status: ArgumentStatusEnum
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class SpeakerRow(BaseModel):
    """One unified bench+advocate row for the argument edit page Speakers section (D-05).

    Replaces the old advocate-only ``participants`` + ``tenure_gap_warnings`` split
    (both retained below for backward compatibility) with a single row shape covering
    every ArgumentParticipant on the argument.

    Bench rows: is_bench=True; bench_role/argument_role come from a CourtTenure
    date-window lookup (_bench_role_and_missing_tenure); missing_tenure=True when no
    tenure covers argued_date; person_edit_href links to the person editor in that
    case. title/title_hint are always None for bench rows — Title is advocate-only
    (PJOB-15 precedent).

    Advocate rows: is_bench=False; argument_role comes from ADVOCATE_LABEL_MAP;
    title and title_hint both source the same ArgumentParticipant.title column
    (D-06 — there is no separate stored "originally extracted" snapshot, unlike
    cover_metadata for argued_date/docket). bench_role is always None and
    missing_tenure is always False for these rows.

    utterance_count is computed via one grouped query keyed on argument_id +
    person_id — never a per-row query (T-26-07, DoS mitigation).
    """

    participant_id: int
    person_id: Optional[int] = None
    full_name: Optional[str] = None
    side: str
    is_bench: bool
    argument_role: Optional[str] = None
    title: Optional[str] = None
    title_hint: Optional[str] = None
    utterance_count: int
    bench_role: Optional[str] = None
    missing_tenure: bool
    person_edit_href: Optional[str] = None

    model_config = {"from_attributes": True}


class TenureGapWarning(BaseModel):
    """A bench speaker whose argued_date falls outside all their CourtTenure rows (D-15).

    Surfaced as an inline warning on the argument edit page.  The ``argued_date``
    field is a serialized "YYYY-MM-DD" string for display.
    """

    person_id: int
    full_name: str
    argued_date: str  # "YYYY-MM-DD"


class ConsolidatedDocket(BaseModel):
    """A non-lead docket number for read-only display (D-10).

    Represents one consolidated case docket linked to the same argument
    but not designated as the lead case.
    """

    docket_number: str


class ArgumentListItem(BaseModel):
    """One row in the /admin/arguments list.

    Returns lead case metadata only — non-lead (consolidated) dockets are
    shown only on the detail page (D-10).
    resolved_at and published_at expose the argument's pipeline / publish state
    so the list page can render status badges without a per-row detail fetch.
    status (Phase 15) is the explicit lifecycle enum value.  The list only
    returns DRAFT and PUBLISHED rows (pipeline-state arguments are excluded, D-02).
    argued_date is Optional[datetime.date] after migration 0011 (D-08 / Phase 19).
    """

    id: int
    argued_date: Optional[datetime.date] = None  # nullable after migration 0011 (D-08)
    case_name: str          # lead case
    docket_number: str      # lead case
    resolved_at: Optional[datetime.datetime] = None
    published_at: Optional[datetime.datetime] = None
    status: ArgumentStatusEnum   # Phase 15 — always DRAFT or PUBLISHED in list results

    model_config = {"from_attributes": True}


class AdvocateParticipant(BaseModel):
    """An advocate participant in an argument with their current role assignment.

    Used on the argument edit page (D-12) to render the per-advocate role dropdown.
    participant_id is the ArgumentParticipant.id — used to PATCH the side field.
    person_id links to the people directory for the "Edit person" navigation.
    side is one of PETITIONER, RESPONDENT, AMICUS, UNKNOWN (never BENCH).
    """

    participant_id: int
    person_id: int
    full_name: str
    side: str  # SideEnum value as string


class ArgumentDetail(BaseModel):
    """Full argument data for the edit form.

    Extends ArgumentListItem with slug and consolidated_dockets (D-10).
    slug is displayed read-only when published_at IS NOT NULL (frozen per D-11).
    tenure_gap_warnings (Phase 15, D-15): list of bench speakers whose
    argued_date falls outside all their CourtTenure rows.
    participants (Phase 15, D-12): list of resolved advocate participants for
    the per-argument role editor — excludes BENCH participants.
    source_docket (Phase 19, D-01): new column; exposed for job detail metadata card.
    cover_metadata (Phase 19, D-07): raw cover extractor output; exposed for hint text.
    """

    id: int
    argued_date: Optional[datetime.date] = None  # nullable after migration 0011 (D-08)
    case_name: str
    docket_number: str
    slug: str
    resolved_at: Optional[datetime.datetime] = None
    published_at: Optional[datetime.datetime] = None
    status: ArgumentStatusEnum = ArgumentStatusEnum.DRAFT  # Phase 15
    consolidated_dockets: list[ConsolidatedDocket] = []
    tenure_gap_warnings: list[TenureGapWarning] = []       # Phase 15
    participants: list[AdvocateParticipant] = []           # Phase 15 D-12
    source_docket: Optional[str] = None                   # Phase 19 D-01
    source_dockets: list[str] = []                        # Phase 23 D-MULTI-DOCKET
    cover_metadata: Optional[dict] = None                 # Phase 19 D-07
    question_number: Optional[int] = None                 # Phase 23 PJOB-07

    model_config = {"from_attributes": True}


class ArgumentUpdate(BaseModel):
    """PATCH request body for updating an argument record.

    Mass-assignment guard (T-11-MASS): ONLY case_name, docket_number, and
    argued_date are writable via PATCH.

    Explicitly excluded fields (must never appear here):
      - published_at: controlled only by POST /publish and POST /unpublish
      - slug: derived server-side from case_name; never client-writable
      - id: path parameter, never a body field
      - resolved_at: pipeline-managed, never operator-writable

    argued_date is accepted as an ISO 8601 string ("YYYY-MM-DD") and parsed
    by the service layer with datetime.date.fromisoformat() (V5 Input Validation).
    """

    case_name: Optional[str] = None
    docket_number: Optional[str] = None
    argued_date: Optional[str] = None  # ISO date string "YYYY-MM-DD"


class MetadataUpdate(BaseModel):
    """PATCH body for argument metadata from job detail page (D-15, Phase 19).

    Mass-assignment guard (T-19-03-01, extended Phase 23 T-23-01, T-23-07):
    ONLY case_name, source_docket, source_dockets, argued_date, and question_number
    are writable via this schema.  No other Argument or Case field can be set here.

    argued_date is accepted as an ISO 8601 string "YYYY-MM-DD"; parsed by the
    service layer with datetime.date.fromisoformat() (V5 Input Validation pattern).
    source_docket is the primary docket string (e.g. "14-556") from the pipeline
    start form or cover extractor — stored on Argument.source_docket (D-01).
    source_dockets is the full ordered docket list for consolidated cases (D-MULTI-DOCKET);
    when provided, the service writes both source_dockets (normalized) and source_docket
    (= first element, the canonical dedup key). Prefer sending source_dockets; the service
    falls back to source_docket for older callers that omit source_dockets.
    question_number is accepted as free text (PJOB-06); the service parses to int
    via a guarded int() call, skipping silently on ValueError (T-23-02).
    """

    case_name: Optional[str] = None
    source_docket: Optional[str] = None
    source_dockets: Optional[list[str]] = None  # Phase 23 D-MULTI-DOCKET
    argued_date: Optional[str] = None   # ISO date string "YYYY-MM-DD"
    question_number: Optional[str] = None  # free text; parsed to int in service (PJOB-06)
