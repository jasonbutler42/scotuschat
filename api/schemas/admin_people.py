"""Pydantic v2 request/response models for the admin people API endpoints.

These schemas back the Phase 8 People Editor routes, the Phase 12 People Admin
Improvements routes, and the Phase 25 Resolve card contract:
  - PersonListItem  — directory listing row with missing-fields derivation
  - PersonDetail    — full person data for the edit form (includes tenures)
  - PersonUpdate    — PATCH body (all fields optional; tenures=None means keep existing)
  - TenureWrite     — a single SUBMITTED court tenure entry (strict office contract)
  - TenureRow       — a single READ-response court tenure entry (legacy-tolerant office)
  - RoleCreate      — request body for POST /api/admin/roles
  - RoleResponse    — response from POST /api/admin/roles
  - ParticipantItem — one resolved participant for GET /api/admin/jobs/{id}/participants
  - MergeRequest    — POST body for POST /api/admin/people/{id}/merge (PADM-03)
  - MergePreview    — response from GET /api/admin/people/{id}/merge-preview (PADM-04)
  - ResolveRow      — one Resolve card row for GET /api/admin/jobs/{id}/resolve-rows (Phase 25)

Phase 37 (D-01 through D-04, D-11, D-17): court_tenures.office replaces the
free-text `seat` column end to end — there is no `seat` compatibility alias.
TenureWrite and TenureRow are intentionally split: TenureWrite is the STRICT
write contract accepted on PersonUpdate.tenures (office is a required
Literal["chief", "associate"] — blank/null/arbitrary strings fail validation
before reaching the service or the database). TenureRow remains the
legacy-tolerant READ shape returned on PersonDetail.tenures so an invalid
original value can still be displayed for operator correction (D-11) without
the response schema itself rejecting it. TenureRow is never used to accept a
write.
"""

from typing import Literal, Optional

from pydantic import BaseModel

from api.models.models import SideEnum


class TenureWrite(BaseModel):
    """A single SUBMITTED court tenure entry — the strict write contract.

    office is REQUIRED and constrained to exactly the two canonical values
    (D-01, D-03, D-04, D-17) — Pydantic rejects blank strings, null, and any
    other free-text value (legacy numbered seats, formal titles like
    "Chief Justice") before this row ever reaches _replace_tenures or the
    database. Dates are ISO 8601 strings ("YYYY-MM-DD") or None.
    Phase 27 additions: appointed_by and appointing_president_party are
    per-row appointment fields — each tenure row carries its own appointing
    president/party rather than a single person-level value. appointed_by
    remains a free-text field (D-16). appointing_president_party is now
    surfaced in the person editor as a curated dropdown (D-16 reversed for
    this field only, per Phase 27 UAT, 2026-07-09), but at the schema level
    it remains this same Optional[str] free-text-compatible column — the
    API accepts any string, no type/enum constraint is added here.
    """

    office: Literal["chief", "associate"]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    appointed_by: Optional[str] = None
    appointing_president_party: Optional[str] = None


class TenureRow(BaseModel):
    """A single READ-response court tenure entry — legacy-tolerant shape.

    Returned by GET/PATCH /api/admin/people/{id} (PersonDetail.tenures).
    Unlike TenureWrite, office here is an unconstrained Optional[str] so a
    response can still carry an invalid/original value for operator
    correction (D-11) without the response schema itself rejecting it. This
    schema must NEVER be used to accept a write — see TenureWrite above.
    Dates are ISO 8601 strings ("YYYY-MM-DD") or None.
    """

    office: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    appointed_by: Optional[str] = None
    appointing_president_party: Optional[str] = None


class PersonListItem(BaseModel):
    """A single row in the people directory listing.

    missing: list of field labels that are NULL on this person record.
    Possible values: "first name", "last name", "photo", "bio", "birthdate",
    "no tenures" — the exact vocabulary _missing_fields produces (see D-04, D-06).
    Phase 18 addition: is_justice for directory badge (D-10 — migration 0010).
    Phase 27 (D-10): role_id/role_name removed — the list no longer shows a
    Role column (person-level Role is superseded; role now lives on
    argument_participants). Phase 27 additions: argument_count (Advocate-tab
    column, PDIR-04), tenure_coverage and has_tenure_gap (Bench-tab display
    string and gap indicator, PDIR-03).
    """

    id: int
    full_name: str
    missing: list[str]
    # Phase 18 addition — migration 0010
    is_justice: bool = False
    # Phase 27 additions
    argument_count: Optional[int] = None
    tenure_coverage: Optional[str] = None
    has_tenure_gap: bool = False

    model_config = {"from_attributes": True}


class PersonDetail(BaseModel):
    """Full person data returned by GET /api/admin/people/{id} and PATCH /api/admin/people/{id}.

    Includes all tenure rows for display in the edit form (D-07, D-08).
    Phase 9 additions: six structured name and appointment fields (all optional).
    Phase 18 addition: is_justice boolean for the editor toggle (D-11 — migration 0010).
    Phase 27 (D-10): role_id/role_name removed — the editor no longer surfaces
    a person-level Role field. Phase 27 addition: birthdate (ISO date string,
    PEDIT-02 — migration 0016).
    """

    id: int
    full_name: str
    bio_text: Optional[str] = None
    photo_url: Optional[str] = None
    tenures: list[TenureRow] = []
    # Phase 9 additions — migration 0006
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    name_suffix: Optional[str] = None
    # Phase 22 — migration 0013: appointment columns moved to court_tenures (PEDIT-10)
    # Phase 18 addition — migration 0010
    is_justice: bool = False
    # Phase 27 addition — migration 0016
    birthdate: Optional[str] = None

    model_config = {"from_attributes": True}


class PersonUpdate(BaseModel):
    """PATCH request body for updating a person record.

    All fields are optional — but the edit form sends all of them.
    tenures=None means "leave existing tenures unchanged".
    tenures=[] means "delete all tenure rows".
    Mass-assignment guard: ONLY explicitly-declared fields are writable.
    Phase 9 extends the allow-list with six structured name and appointment
    fields (T-09-01 — prevents writing arbitrary Person attributes).
    Phase 18 addition: is_justice Optional[bool] — None means leave unchanged (D-08, D-11).
    Phase 27 (D-10): role_id removed from the allow-list entirely — person-level
    Role is superseded (role now lives on argument_participants). Phase 27
    addition: birthdate (ISO date string, PEDIT-02) — added to the mass-
    assignment allow-list following the same T-09-01 explicit-field discipline;
    None means leave unchanged.
    """

    full_name: Optional[str] = None
    bio_text: Optional[str] = None
    photo_url: Optional[str] = None
    tenures: Optional[list[TenureWrite]] = None
    # Phase 9 additions — mass-assignment allow-list extension (T-09-01)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    name_suffix: Optional[str] = None
    # Phase 22 — migration 0013: appointment columns moved to court_tenures (PEDIT-10)
    # Phase 18 addition — migration 0010 (None = leave unchanged per D-08)
    is_justice: Optional[bool] = None
    # Phase 27 addition — migration 0016 (T-09-01 allow-list discipline)
    birthdate: Optional[str] = None


class PersonCreateRequest(BaseModel):
    """Request body for POST /api/admin/people (D-08, PEDIT-09).

    The minimum required to create a person is a full name plus a Bench/
    Advocate choice — both full_name and is_justice are REQUIRED (unlike
    every field on PersonUpdate, which is Optional). The four structured
    name-part fields (first_name/middle_name/last_name/name_suffix) are now
    also accepted (all Optional) at create time to match the [id] editor's
    save behavior, per Phase 27 UAT gap closure (Gap 3, 2026-07-09) — omitting
    them still succeeds and leaves those columns NULL. bio, photo, tenures,
    and birthdate remain deferred to the existing PATCH /api/admin/people/{id}
    update flow (D-08), not accepted at creation time. Does NOT carry the
    job-scoped fields (raw_speaker_label, side, role_name) present on
    admin_jobs.PersonCreate — this is a standalone person-directory create,
    not a job-linked inline create.
    """

    full_name: str
    is_justice: bool
    # Phase 27 Plan 08 additions (UAT Gap 3 closure) — mirrors PersonUpdate's
    # allow-list discipline (T-09-01); optional, None/omitted leaves NULL.
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    name_suffix: Optional[str] = None


# TODO(D-10): orphaned by Phase 27 — person-level roles removed; safe to
# delete once confirmed. Plan 27-05 deletes this schema's only caller (the
# createRole form action); flagged here rather than deleted to avoid
# breaking imports mid-phase.
class RoleCreate(BaseModel):
    """Request body for POST /api/admin/roles (D-10 inline role creation)."""

    name: str


# TODO(D-10): orphaned by Phase 27 — person-level roles removed; safe to
# delete once confirmed. See RoleCreate above.
class RoleResponse(BaseModel):
    """Response from POST /api/admin/roles and find-or-create role operation."""

    id: int
    name: str

    model_config = {"from_attributes": True}


class ParticipantItem(BaseModel):
    """A resolved participant in an argument, returned by GET /api/admin/jobs/{id}/participants.

    Only includes participants where person_id IS NOT NULL (D-02).
    Phase 15 adds participant_id (ArgumentParticipant.id) and side for the advocate
    role dropdowns on the pipeline job detail page.
    """

    participant_id: int
    person_id: int
    full_name: str
    role_name: Optional[str] = None
    side: Optional[str] = None

    model_config = {"from_attributes": True}


class MergeRequest(BaseModel):
    """POST body for POST /api/admin/people/{id}/merge (PADM-03).

    The source person is taken from the URL path parameter; this body
    carries only the target person's id.
    """

    target_id: int


class MergePreview(BaseModel):
    """Response from GET /api/admin/people/{id}/merge-preview (PADM-04).

    Returns the count of each FK table row that will transfer from source to target
    when a merge is executed. Used to show the operator a summary before confirming.
    """

    utterances: int
    aliases: int
    appearances: int
    argument_participants: int
    tenures: int

    model_config = {"from_attributes": True}


class ResolveRow(BaseModel):
    """A single Resolve card row, returned by GET /api/admin/jobs/{id}/resolve-rows (Phase 25).

    One row per ArgumentParticipant on the job's linked argument — including
    rows where person_id IS NULL, so raw_speaker_label is always preserved even
    before the pipeline resolves a speaker (D-10, D-11). This is a superset of
    ParticipantItem: ParticipantItem only covers resolved rows for the older
    participants list; ResolveRow covers every row and adds the locked column
    contract for the restructured Resolve card (25-UI-SPEC.md, PJOB-14/15/16).

    Column contract (locked order): raw_speaker_label, resolved-as (person_id/
    full_name/photo_url), side (Bench/Advocate), argument_role, title
    (advocate-only), then the frontend Action column derives from the fields
    above (no separate schema field needed).

    Bench rows (side == BENCH): argument_role/bench_role carry the formal
    office title (Chief Justice/Associate Justice) for the tenure covering
    Argument.argued_date when one exists; when none covers the date,
    both are null, missing_tenure is true, and person_edit_href points at the
    person editor (D-15, D-16, PJOB-16). title/title_hint are always null —
    the Title column is advocate-only (PJOB-15).

    Non-bench rows: argument_role is the side's advocate label (e.g. "Petitioner's
    Counsel"); title/title_hint carry ArgumentParticipant.title. bench_role,
    missing_tenure, and person_edit_href are always null/false for these rows.

    editable is false once the linked argument has left the 'pipeline' status —
    the Resolve card renders every row read-only in that state (D-18, D-19).
    """

    participant_id: int
    raw_speaker_label: str
    person_id: Optional[int] = None
    full_name: Optional[str] = None
    photo_url: Optional[str] = None
    side: SideEnum
    argument_role: Optional[str] = None
    title: Optional[str] = None
    title_hint: Optional[str] = None
    bench_role: Optional[str] = None
    missing_tenure: bool = False
    person_edit_href: Optional[str] = None
    editable: bool = True

    model_config = {"from_attributes": True}
