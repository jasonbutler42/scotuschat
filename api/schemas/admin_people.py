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
  - MergeRequest — POST body for POST /api/admin/people/{id}/merge
  - MergePreview — response from GET /api/admin/people/{id}/merge-preview
  - ResolveRow — one Resolve card row for GET /api/admin/jobs/{id}/resolve-rows

Phase 37 (D-01 through D-04, D-11, D-17): court_tenures.office replaces the
free-text `seat` column end to end — there is no `seat` compatibility alias.
TenureWrite and TenureRow are intentionally split: TenureWrite is the STRICT
write contract accepted on PersonUpdate.tenures (office is a required
Literal["chief", "associate"] — blank/null/arbitrary strings fail validation
before reaching the service or the database). TenureRow remains the
legacy-tolerant READ shape returned on PersonDetail.tenures so an invalid
original value can still be displayed for operator correction without
the response schema itself rejecting it. TenureRow is never used to accept a
write.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

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
    remains a free-text field. appointing_president_party is now
    surfaced in the person editor as a curated dropdown (D-16 reversed for
    this field only, 2026-07-09), but at the schema level
    it remains this same Optional[str] free-text-compatible column — the
    API accepts any string, no type/enum constraint is added here.
    Phase 39 addition: reason_left is a strict Literal over the same three
    canonical values as api.models.models.VALID_REASONS_LEFT — a
    hand-crafted tenures JSON carrying an out-of-vocabulary reason is a 422
    before it reaches _replace_tenures or the database CHECK constraint
    (ck_court_tenures_reason_left). Unlike office, reason_left is optional
    on the write side even for an otherwise-valid row — most tenures have
    no recorded reason at all (D-02: only ended tenures ever have one).
    """

    office: Literal["chief", "associate"]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    appointed_by: Optional[str] = None
    appointing_president_party: Optional[str] = None
    reason_left: Optional[Literal["retired", "died", "promoted"]] = None


class TenureRow(BaseModel):
    """A single READ-response court tenure entry — legacy-tolerant shape.

    Returned by GET/PATCH /api/admin/people/{id} (PersonDetail.tenures).
    Unlike TenureWrite, office here is an unconstrained Optional[str] so a
    response can still carry an invalid/original value for operator
    correction without the response schema itself rejecting it. This
    schema must NEVER be used to accept a write — see TenureWrite above.
    Dates are ISO 8601 strings ("YYYY-MM-DD") or None.
    Phase 39 addition: reason_left stays a tolerant Optional[str] here (not
    the TenureWrite Literal) so a pre-existing non-canonical stored value
    remains visible for operator correction, mirroring the office split.
    """

    office: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    appointed_by: Optional[str] = None
    appointing_president_party: Optional[str] = None
    reason_left: Optional[str] = None


class PersonListItem(BaseModel):
    """A single row in the people directory listing.

    missing: list of field labels that are NULL on this person record.
    Possible values: "first name", "last name", "photo", "bio", "birthdate",
    "no tenures", "name review" — the exact vocabulary _missing_fields
    produces. "name review" is included for ANY person
    (bench or advocate) whose `review_state` is `needs_review` (Phase 49
    D-08, carrying Phase 38 D-12 forward unchanged) — unlike the other
    labels it does not indicate a NULL field, but an ambiguous legacy
    `full_name` this row's structured parts could not be confidently
    derived from; it shares the same click-to-filter allow-list mechanism
    (T-27-03 vocabulary) rather than introducing a new UI pattern.
    Phase 18 addition: is_justice for directory badge (D-10 — migration 0010).
    Role_id/role_name removed — the list no longer shows a
    Role column (person-level Role is superseded; role now lives on
    argument_participants). Phase 27 additions: argument_count (Advocate-tab
    column, PDIR-04), tenure_coverage and has_tenure_gap (Bench-tab display
    string and gap indicator, PDIR-03). Phase 49 addition: review_state
    (D-08, D-11) — the unified review status string, mirroring the "name
    review" entry in `missing` for a consumer that prefers an explicit
    field over array membership.
    """

    id: int
    full_name: str
    missing: list[str]
    # Phase 18 addition
    is_justice: bool = False
    # Phase 27 additions
    argument_count: Optional[int] = None
    tenure_coverage: Optional[str] = None
    has_tenure_gap: bool = False
    # Phase 49 addition — migration 0029, replacing Phase 38's
    # name_needs_review boolean
    review_state: str = "unreviewed"

    model_config = {"from_attributes": True}


class PersonProvenanceMetadata(BaseModel):
    """Typed provenance envelope for `Person.provenance_metadata` (Phase 49
    D-08, D-12; carrying Phase 38 D-14/D-18 forward unchanged).

    Mirrors the exact JSONB shape originally written by migration 0022's
    legacy backfill (`source`, `raw`, `confidence`, `reason`,
    `auto_applied` — see alembic/versions/0022_person_name_authority.py),
    carried straight across into `provenance_metadata` by migration 0029,
    and the same shape pipeline/import extraction paths persist for
    freshly-extracted names. This is a whole-record envelope (one decision
    per Person row, not per name part) describing how the current split/
    unsplit state of `full_name` came to be. It is intentionally read-only
    on every request schema — an operator's own edit never clears,
    rewrites, or appends to this value; only a fresh extraction/
    migration pass ever replaces it.
    """

    source: Optional[str] = None
    raw: Optional[str] = None
    confidence: Optional[str] = None
    reason: Optional[str] = None
    auto_applied: Optional[bool] = None

    model_config = {"from_attributes": True}


class PersonDetail(BaseModel):
    """Full person data returned by GET /api/admin/people/{id} and PATCH /api/admin/people/{id}.

    Includes all tenure rows for display in the edit form.
    Phase 9 additions: six structured name and appointment fields (all optional).
    Phase 18 addition: is_justice boolean for the editor toggle (D-11 — migration 0010).
    Role_id/role_name removed — the editor no longer surfaces
    a person-level Role field. Phase 27 addition: birthdate (ISO date string,
    Migration 0016).

    Full_name is a server-derived, read-only
    compatibility value — it is never accepted on PersonCreateRequest or
    PersonUpdate (see below), but it is still returned here so existing
    display/sort/dedup consumers keep working unchanged. Phase 49 additions
    (D-08, D-11, D-12): review_state and provenance_metadata surface the
    People directory's `Name review` attention state and the typed
    provenance envelope for the editor's extracted-value hint, replacing
    Phase 38's name_needs_review/name_extraction_metadata pair outright.
    """

    id: int
    full_name: str
    bio_text: Optional[str] = None
    photo_url: Optional[str] = None
    tenures: list[TenureRow] = []
    # Phase 9 additions
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    name_suffix: Optional[str] = None
    # Appointment columns moved to court_tenures
    # Phase 18 addition
    is_justice: bool = False
    # Phase 27 addition
    birthdate: Optional[str] = None
    # Phase 49 additions — migration 0029, replacing
    # Phase 38's name_needs_review/name_extraction_metadata pair
    review_state: str = "unreviewed"
    provenance_metadata: Optional[PersonProvenanceMetadata] = None
    # Phase 39 addition — migration 0023; mirrors birthdate's exact
    # ISO-date-string shape.
    death_date: Optional[str] = None

    model_config = {"from_attributes": True}


class PersonUpdate(BaseModel):
    """PATCH request body for updating a person record.

    All fields are optional — but the edit form sends all of them.
    tenures=None means "leave existing tenures unchanged".
    tenures=[] means "delete all tenure rows".
    Mass-assignment guard: ONLY explicitly-declared fields are writable, and
    `extra="forbid"` rejects any field this schema does
    not declare — including `full_name`, which is intentionally NOT a field
    here (D-01: Full Name is generated from structured parts and is never
    independently operator-editable; a client that posts `full_name` gets a
    422, not a silently-ignored write).
    Phase 9 extends the allow-list with six structured name and appointment
    fields (T-09-01 — prevents writing arbitrary Person attributes).
    Phase 18 addition: is_justice Optional[bool] — None means leave unchanged.
    Role_id removed from the allow-list entirely — person-level
    Role is superseded (role now lives on argument_participants). Phase 27
    addition: birthdate (ISO date string, PEDIT-02) — added to the mass-
    assignment allow-list following the same T-09-01 explicit-field discipline;
    None means leave unchanged.

    Omitted vs. explicitly-cleared name parts (D-04 partial-PATCH contract):
    a name-part field entirely absent from the request body is left
    unchanged by the service; a name-part field explicitly sent as `null`/
    `""` is treated as an authored clear and merged with the person's other
    stored parts before the first-or-last invariant and full_name derivation
    run — `model_fields_set` (not `is not None`) is what makes this
    distinction possible, mirroring the existing bio_text/photo_url/
    birthdate CR-01 contract in this same schema.

    Phase 39 addition: death_date (ISO date string, migration 0023) follows
    the identical birthdate contract — omission (not `None`) is what means
    "leave unchanged." The service distinguishes the two via
    `model_fields_set`, not a null check, because this field is submitted
    only by the save-form (Identity+Person Type); the separate photo/bio
    form's PATCH body never includes it, and writing it unconditionally
    would silently clear a stored death date on every photo/bio save
    (39-RESEARCH.md Pitfall 5).
    """

    bio_text: Optional[str] = None
    photo_url: Optional[str] = None
    tenures: Optional[list[TenureWrite]] = None
    # Phase 9 additions — mass-assignment allow-list extension
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    name_suffix: Optional[str] = None
    # Appointment columns moved to court_tenures
    # Phase 18 addition — migration 0010 (None = leave unchanged per D-08)
    is_justice: Optional[bool] = None
    # Phase 27 addition — migration 0016 (T-09-01 allow-list discipline)
    birthdate: Optional[str] = None
    # Phase 39 addition — migration 0023 (T-09-01 allow-list discipline);
    # omission means leave unchanged (model_fields_set-guarded in update_person)
    death_date: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class PersonCreateRequest(BaseModel):
    """Request body for POST /api/admin/people.

    `full_name` is NOT a field on this schema —
    Full Name is always derived server-side from structured parts, never
    accepted from the client (`extra="forbid"`, T-38-07, rejects a posted
    `full_name` with 422 rather than silently dropping it). The minimum
    required to create a person is at least ONE of first_name/last_name
    (D-09 — supports incomplete pipeline knowledge and legitimate single-part
    names) plus a Bench/Advocate choice; is_justice remains REQUIRED (unlike
    every Optional field on PersonUpdate). The first-or-last invariant itself
    is enforced by the service layer's shared `prepare_person_name` helper
    (api.domain.person_names), not by this schema, so the same deterministic
    PersonNameError -> 422 contract applies to both create and update. bio,
    photo, tenures, and birthdate remain deferred to the existing PATCH
    /api/admin/people/{id} update flow, not accepted at creation
    time. Does NOT carry the job-scoped fields (raw_speaker_label, side,
    role_name) present on admin_jobs.PersonCreate — this is a standalone
    person-directory create, not a job-linked inline create.
    """

    is_justice: bool
    # Phase 27 Plan 08 additions, still optional at create time (Gap 3
    # closure); Phase 38 makes at least one of first_name/last_name a hard
    # requirement, enforced by prepare_person_name.
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    name_suffix: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


# TODO: orphaned by Phase 27 — person-level roles removed; safe to
# delete once confirmed. Plan 27-05 deletes this schema's only caller (the
# createRole form action); flagged here rather than deleted to avoid
# breaking imports mid-phase.
class RoleCreate(BaseModel):
    """Request body for POST /api/admin/roles (D-10 inline role creation)."""

    name: str


# TODO: orphaned by Phase 27 — person-level roles removed; safe to
# delete once confirmed. See RoleCreate above.
class RoleResponse(BaseModel):
    """Response from POST /api/admin/roles and find-or-create role operation."""

    id: int
    name: str

    model_config = {"from_attributes": True}


class ParticipantItem(BaseModel):
    """A resolved participant in an argument, returned by GET /api/admin/jobs/{id}/participants.

    Only includes participants where person_id IS NOT NULL.
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
    """POST body for POST /api/admin/people/{id}/merge.

    The source person is taken from the URL path parameter; this body
    carries only the target person's id.
    """

    target_id: int


class MergePreview(BaseModel):
    """Response from GET /api/admin/people/{id}/merge-preview.

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
    """A single Resolve card row, returned by GET /api/admin/jobs/{id}/resolve-rows.

    One row per ArgumentParticipant on the job's linked argument — including
    rows where person_id IS NULL, so raw_speaker_label is always preserved even
    before the pipeline resolves a speaker. This is a superset of
    ParticipantItem: ParticipantItem only covers resolved rows for the older
    participants list; ResolveRow covers every row and adds the locked column
    contract for the restructured Resolve card.

    Column contract (locked order): raw_speaker_label, resolved-as (person_id/
    full_name/photo_url), side (Bench/Advocate), argument_role, descriptor
    (advocate-only), then the frontend Action column derives from the fields
    above (no separate schema field needed).

    Bench rows (side == BENCH): argument_role/bench_role carry the formal
    office title (Chief Justice/Associate Justice) for the tenure covering
    Argument.argued_date when one exists; when none covers the date,
    both are null, missing_tenure is true, and person_edit_href points at the
    person editor. descriptor/descriptor_hint are always
    null — the Descriptor column is advocate-only.

    Non-bench rows: argument_role is the side's advocate label (e.g. "Petitioner's
    Counsel"); descriptor/descriptor_hint carry ArgumentParticipant.descriptor.
    bench_role, missing_tenure, and person_edit_href are always null/false for
    these rows.

    editable is false once the linked argument has left the 'candidate' status —
    the Resolve card renders every row read-only in that state.
    """

    participant_id: int
    raw_speaker_label: str
    person_id: Optional[int] = None
    full_name: Optional[str] = None
    photo_url: Optional[str] = None
    side: SideEnum
    argument_role: Optional[str] = None
    descriptor: Optional[str] = None
    descriptor_hint: Optional[str] = None
    bench_role: Optional[str] = None
    missing_tenure: bool = False
    person_edit_href: Optional[str] = None
    editable: bool = True


class BenchRolePreview(BaseModel):
    """Response from GET /api/admin/jobs/{job_id}/people/{person_id}/bench-role-preview
    (Plan 44-09 tenure-preview follow-up, RESOLVE-15/16 remediation).

    Previews the tenure-derived bench role for a person the operator has
    picked for a BENCH row but not yet committed via the Resolve card's batch
    ?/resolve submit — ArgumentParticipant.person_id is two-phase (client-side
    pick, then batch commit), so ResolveRow.bench_role/missing_tenure stay
    null/false for that row until the commit lands. This mirrors
    _bench_role_and_missing_tenure's own (bench_role, missing_tenure) shape
    exactly, computed against the same person and the same argument's
    argued_date the eventual committed row would use.
    """

    bench_role: Optional[str] = None
    missing_tenure: bool = False

    model_config = {"from_attributes": True}
