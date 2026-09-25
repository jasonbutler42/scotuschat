"""Pydantic v2 response models for the dev-only "Reset to Fixture" endpoint.

Phase 43. This schema locks the FULL response
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
    # Replaces the retired AdminJob-status
    # field -- there is no AdminJob for a corpus fixture anymore. The step
    # of the fixture argument's highest-id ImportRun, which together with
    # argument_status keeps all four reference states distinguishable:
    # Complexity = candidate/parse, Draft = draft/parse, Published =
    # published/parse, Mid-pipeline = candidate/reconcile.
    latest_import_run_step: str


class ResetToFixtureResponse(BaseModel):
    fixtures: list[ResetFixtureItem]


class SeedUnresolvedSpeakerResponse(BaseModel):
    """Phase 49. Mirrors ResetToFixtureResponse's plain-BaseModel,
    hand-built-dict convention -- no from_attributes, no ORM row."""

    argument_id: int
    participant_id: int
    raw_speaker_label: str
    trust_tier: str
    already_seeded: bool


class FixtureStateItem(BaseModel):
    """Phase 52-05 (D-14). One FIXTURE_SET conversation's landing state, as
    re-read by api.services.admin_dev.get_fixture_state -- never written by
    the reset itself. `present` is False and the three nullable fields are
    None when no Argument row exists yet for this conversation."""

    conversation_id: str
    case_name: str
    role: str
    present: bool
    argument_id: int | None
    status: str | None
    latest_import_run_step: str | None


class ResetProgress(BaseModel):
    """Phase 52-05 (D-15). `step` is a short machine token
    ("seeding_justices" | "reseeding_fixture_N") -- the frontend owns the
    Copywriting Contract's rendered literal strings and maps this token to
    them, never the other way around."""

    step: str
    completed: int
    total: int


class FixtureStateResponse(BaseModel):
    """Phase 52-05 (D-14/D-15). `progress` is None when no reset is
    currently in flight."""

    fixtures: list[FixtureStateItem]
    progress: ResetProgress | None
