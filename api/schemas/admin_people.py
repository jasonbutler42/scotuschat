"""Pydantic v2 request/response models for the admin people API endpoints.

These schemas back the Phase 8 People Editor routes:
  - PersonListItem  — directory listing row with missing-fields derivation
  - PersonDetail    — full person data for the edit form (includes tenures)
  - PersonUpdate    — PATCH body (all fields optional; tenures=None means keep existing)
  - TenureRow       — a single court tenure entry (seat, start_date, end_date as ISO strings)
  - RoleCreate      — request body for POST /api/admin/roles
  - RoleResponse    — response from POST /api/admin/roles
  - ParticipantItem — one resolved participant for GET /api/admin/jobs/{id}/participants
"""

from typing import Optional

from pydantic import BaseModel


class TenureRow(BaseModel):
    """A single court tenure entry.

    Dates are ISO 8601 strings ("YYYY-MM-DD") or None.
    All fields are Optional so the frontend can send partially-filled rows;
    the service filters out rows where both seat and start_date are falsy.
    """

    seat: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class PersonListItem(BaseModel):
    """A single row in the people directory listing.

    missing: list of field labels that are NULL on this person record.
    Possible values: "role", "bio", "photo" (see D-04, D-06).
    """

    id: int
    full_name: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    missing: list[str]

    model_config = {"from_attributes": True}


class PersonDetail(BaseModel):
    """Full person data returned by GET /api/admin/people/{id} and PATCH /api/admin/people/{id}.

    Includes all tenure rows for display in the edit form (D-07, D-08).
    Phase 9 additions: six structured name and appointment fields (all optional).
    """

    id: int
    full_name: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    bio_text: Optional[str] = None
    photo_url: Optional[str] = None
    tenures: list[TenureRow] = []
    # Phase 9 additions — migration 0006
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    name_suffix: Optional[str] = None
    appointing_president: Optional[str] = None
    appointing_president_party: Optional[str] = None

    model_config = {"from_attributes": True}


class PersonUpdate(BaseModel):
    """PATCH request body for updating a person record.

    All fields are optional — but the edit form sends all of them.
    tenures=None means "leave existing tenures unchanged".
    tenures=[] means "delete all tenure rows".
    Mass-assignment guard: ONLY explicitly-declared fields are writable.
    Phase 9 extends the allow-list with six structured name and appointment
    fields (T-09-01 — prevents writing arbitrary Person attributes).
    """

    full_name: Optional[str] = None
    role_id: Optional[int] = None
    bio_text: Optional[str] = None
    photo_url: Optional[str] = None
    tenures: Optional[list[TenureRow]] = None
    # Phase 9 additions — mass-assignment allow-list extension (T-09-01)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    name_suffix: Optional[str] = None
    appointing_president: Optional[str] = None
    appointing_president_party: Optional[str] = None


class RoleCreate(BaseModel):
    """Request body for POST /api/admin/roles (D-10 inline role creation)."""

    name: str


class RoleResponse(BaseModel):
    """Response from POST /api/admin/roles and find-or-create role operation."""

    id: int
    name: str

    model_config = {"from_attributes": True}


class ParticipantItem(BaseModel):
    """A resolved participant in an argument, returned by GET /api/admin/jobs/{id}/participants.

    Only includes participants where person_id IS NOT NULL (D-02).
    """

    person_id: int
    full_name: str
    role_name: Optional[str] = None

    model_config = {"from_attributes": True}
