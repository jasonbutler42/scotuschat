"""Pydantic v2 request/response models for the admin jobs API endpoints."""

import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from api.models.models import AdminJobStatus, AdminJobStep, SideEnum


class AdminJobCreateURL(BaseModel):
    """Request body for creating a new pipeline job via PDF URL (PIPE-12)."""

    pdf_url: str


class ParseStats(BaseModel):
    """Parse step stats embedded in AdminJobResponse.

    Assembled from scalar COUNT query results at render time — not an ORM row.
    No from_attributes config needed (constructed from plain dicts, not ORM objects).

    Phase 23 expansion (PJOB-10/11/12):
      speaker_count retained for backward compat with polling TS interface.
      bench_count / advocate_count / total_speaker_count: speaker breakdown.
      case_name / argued_date / primary_docket: cover_metadata pass-through.
      question_number: from Argument.question_number integer column (NOT cover_metadata).
    """

    utterance_count: int
    speaker_count: int  # retained for backward compat; equals total_speaker_count
    # Phase 23 — speaker breakdown (PJOB-10)
    bench_count: Optional[int] = None
    advocate_count: Optional[int] = None
    total_speaker_count: Optional[int] = None
    # Phase 23 — cover_metadata pass-through (PJOB-10/12)
    case_name: Optional[str] = None
    argued_date: Optional[str] = None      # ISO date string "YYYY-MM-DD"
    primary_docket: Optional[str] = None
    question_number: Optional[int] = None  # from Argument.question_number column


class AdminJobResponse(BaseModel):
    """Full admin job row returned by the poll endpoint and job creation."""

    id: int
    status: AdminJobStatus
    current_step: Optional[AdminJobStep] = None
    argument_id: Optional[int] = None
    pdf_url: Optional[str] = None
    spaces_key: Optional[str] = None
    original_filename: Optional[str] = None
    source_dockets: Optional[list[str]] = None
    parse_stats: Optional[ParseStats] = None
    discrepancies: Optional[list[dict]] = None
    error_message: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    # Phase 26 gap closure (PLIST-05): true when the job's linked argument has
    # already been created (its status is no longer PIPELINE), mirroring the
    # already_created state RunReadiness reports for the detail page. Defaults
    # to False for get_job (single-job path derives its archived signal from
    # the readiness endpoint instead) and is populated for real by list_jobs
    # via an Argument outerjoin.
    is_archived: bool = False
    # Phase 30: "pdf" for jobs created via the ingest pipeline, "corpus" for
    # jobs created directly by import-convokit (Phase 30, D-01). Derived via
    # an exists() subquery on PipelineRun.strategy == "convokit_import" in
    # both list_jobs() and get_job() — see api/services/admin_jobs.py.
    source: Literal["pdf", "corpus"] = "pdf"

    model_config = {"from_attributes": True}


class ResolveMatch(BaseModel):
    """A single confirmed speaker-label-to-person mapping submitted by the operator."""

    raw_speaker_label: str
    person_id: int


class ResolveRequest(BaseModel):
    """Request body for POST /api/admin/jobs/{id}/resolve."""

    matches: list[ResolveMatch]


class PersonCreate(BaseModel):
    """Request body for creating a new person inline during discrepancy review (D-12, D-13).

    Phase 25 (PJOB-19): raw_speaker_label + side make this a job-scoped mini
    create-person request. When both are present, create_person_for_job sets
    Person.is_justice from side == BENCH and updates the matching job-owned
    ArgumentParticipant row (identified by raw_speaker_label) with the new
    person_id and side in the same transaction (D-12). full_name, role_id, and
    role_name remain backward-compatible for callers that do not use the mini
    popover (raw_speaker_label/side omitted).
    """

    full_name: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None  # create a new Role inline if role_id is None
    raw_speaker_label: Optional[str] = None
    side: Optional[SideEnum] = None


class PersonResponse(BaseModel):
    """Minimal person record returned after inline person creation."""

    id: int
    full_name: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Phase 25: Run readiness and failed-step recovery (D-01 through D-08, D-18, D-20)
# ---------------------------------------------------------------------------


class ReadinessBlocker(BaseModel):
    """A single reason Create Argument is not yet available (D-02).

    code is a stable machine-readable identifier for the blocker; message is
    the operator-facing copy shown in the run status card blocker checklist.
    """

    code: str
    message: str


class RunReadiness(BaseModel):
    """Backend-derived Create Argument readiness for the run status card (D-01 through D-04).

    state is one of:
      not_ready       — one or more strict blockers exist (D-02); blockers is non-empty.
      ready           — no blockers remain; the Create Argument CTA is enabled (D-03).
      already_created — the linked argument has left the pipeline lifecycle state;
                         the page becomes read-only provenance (D-04, D-18, D-20).

    argument_edit_href is only set for the already_created state (D-04) — it links
    to the argument editor, never to a rerun action.
    """

    state: Literal["not_ready", "ready", "already_created"]
    blockers: list[ReadinessBlocker] = []
    argument_edit_href: Optional[str] = None


class FailedStepRecovery(BaseModel):
    """Step-specific failed-run guidance, kept separate from the raw technical error.

    guidance is short, human, step-specific copy shown first (D-06, D-07, D-08).
    raw_error is the unedited AdminJob.error_message, meant for an expandable
    technical details block — never merged into guidance (T-25-03).
    href always points at the pipeline list page so the operator starts a
    corrected new run rather than retrying the same source (D-05, D-06, PJOB-22
    superseded by 25-UI-SPEC.md — no same-source rerun is offered here).
    """

    step: Optional[str] = None
    guidance: str
    href: str
    raw_error: Optional[str] = None


# ---------------------------------------------------------------------------
# Phase 25: Job-scoped resolve-row mutation (D-14, D-18, PJOB-14, PJOB-18)
# ---------------------------------------------------------------------------


class ResolveRowUpdate(BaseModel):
    """Request body for the job-scoped resolve-row side/title mutation.

    Mass-assignment guard (T-25-15): ONLY side and title are writable via this
    schema. participant_id identifies the target row; ownership is re-verified
    server-side against the job's linked argument before any mutation (T-25-14
    IDOR guard) — this schema does not accept argument_id.

    Unlike ParticipantSideUpdate (api/schemas/admin_arguments.py), side here MAY
    be BENCH — this is the resolve-scoped write path, not the advocate-only
    argument-editor path. title is ignored (forced to null) server-side whenever
    side == BENCH (PJOB-15).

    WR-03: title is capped at 500 characters to match
    ArgumentParticipant.title (String(500)) — without this, an over-length
    title would raise an unhandled asyncpg DataError (500) instead of the
    422 validation-error pattern used everywhere else in this file.
    """

    participant_id: int
    side: SideEnum
    title: Optional[str] = Field(default=None, max_length=500)
