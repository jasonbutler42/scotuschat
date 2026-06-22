"""Pydantic v2 request/response models for the admin arguments API endpoints.

These schemas back the Phase 11 Argument Metadata Editing routes:
  - ArgumentListItem  — one row in the /admin/arguments list (lead case metadata)
  - ConsolidatedDocket — a single non-lead docket number for read-only display (D-10)
  - ArgumentDetail    — full argument data for the edit form (includes consolidated dockets)
  - ArgumentUpdate    — PATCH body (mass-assignment allow-list: only three editable fields)

Security notes:
  - ArgumentUpdate allow-list is exactly {case_name, docket_number, argued_date} (T-11-MASS).
    published_at is NOT in this schema — it is controlled only by /publish and /unpublish.
    slug and id are also excluded — slug is derived server-side; id is path parameter.
"""

import datetime
from typing import Optional

from pydantic import BaseModel


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
    """

    id: int
    argued_date: datetime.date
    case_name: str          # lead case
    docket_number: str      # lead case
    resolved_at: Optional[datetime.datetime] = None
    published_at: Optional[datetime.datetime] = None

    model_config = {"from_attributes": True}


class ArgumentDetail(BaseModel):
    """Full argument data for the edit form.

    Extends ArgumentListItem with slug and consolidated_dockets (D-10).
    slug is displayed read-only when published_at IS NOT NULL (frozen per D-11).
    """

    id: int
    argued_date: datetime.date
    case_name: str
    docket_number: str
    slug: str
    resolved_at: Optional[datetime.datetime] = None
    published_at: Optional[datetime.datetime] = None
    consolidated_dockets: list[ConsolidatedDocket] = []

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
