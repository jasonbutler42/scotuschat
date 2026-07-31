"""Pydantic v2 response models for the dev-only "Reset to Fixture" endpoint.

Phase 43 (DEVTOOL-01, DEVTOOL-02). This schema locks the FULL response
contract now, even though Plan 43-01 only populates one entry (the Complexity
fixture, conversation 15169) — Plan 43-03 (frontend) codes against this shape
in parallel with Plan 43-02 (service expansion to all four fixtures).

Plain BaseModel classes (no from_attributes) — reset_to_fixture returns a
hand-built dict, not an ORM row, mirroring api/schemas/admin_dashboard.py's
convention for non-ORM response shapes.

Apolitical constraint: these schemas carry only identifying/lifecycle
metadata (conversation id, case name, role label, argument id, status
strings) — no derived-insight, outcome, or vote-margin field appears here.
"""

from pydantic import BaseModel


class ResetFixtureItem(BaseModel):
    conversation_id: str
    case_name: str
    role: str
    argument_id: int
    argument_status: str
    admin_job_status: str


class ResetToFixtureResponse(BaseModel):
    fixtures: list[ResetFixtureItem]
