"""Pydantic v2 request/response models for the admin jobs API endpoints."""

import datetime
from typing import Optional

from pydantic import BaseModel

from api.models.models import AdminJobStatus, AdminJobStep


class AdminJobCreateURL(BaseModel):
    """Request body for creating a new pipeline job via PDF URL (PIPE-12)."""

    pdf_url: str


class ParseStats(BaseModel):
    """Parse step stats embedded in AdminJobResponse.

    Assembled from scalar COUNT query results at render time — not an ORM row.
    No from_attributes config needed (constructed from plain dicts, not ORM objects).
    """

    utterance_count: int
    speaker_count: int


class AdminJobResponse(BaseModel):
    """Full admin job row returned by the poll endpoint and job creation."""

    id: int
    status: AdminJobStatus
    current_step: Optional[AdminJobStep] = None
    argument_id: Optional[int] = None
    pdf_url: Optional[str] = None
    spaces_key: Optional[str] = None
    original_filename: Optional[str] = None
    parse_stats: Optional[ParseStats] = None
    discrepancies: Optional[list[dict]] = None
    error_message: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class ResolveMatch(BaseModel):
    """A single confirmed speaker-label-to-person mapping submitted by the operator."""

    raw_speaker_label: str
    person_id: int


class ResolveRequest(BaseModel):
    """Request body for POST /api/admin/jobs/{id}/resolve."""

    matches: list[ResolveMatch]


class PersonCreate(BaseModel):
    """Request body for creating a new person inline during discrepancy review (D-13)."""

    full_name: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None  # create a new Role inline if role_id is None


class PersonResponse(BaseModel):
    """Minimal person record returned after inline person creation."""

    id: int
    full_name: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None

    model_config = {"from_attributes": True}
