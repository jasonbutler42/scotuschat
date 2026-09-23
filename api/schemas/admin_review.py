"""Pydantic v2 request/response models for the admin review-queue API.

Plan 49-01 shipped a thin end-to-end tracer (Arguments queue, one Confirm
action). Plan 49-04 widens this module: the full three-action resolve set
(confirm, confirm_unattributable, reflag — "edit" is a deep link, D-23, not
a fourth PATCH), discrepancy detail on each constituent, and the People
queue's own item shape.

Security notes:
  - ReviewActionRequest exposes ONLY ``action`` (a closed three-value
    Literal) — no id, no target scope, no column name is accepted in the
    body (T-49-massassign). Scope is derived from the URL path, mirroring
    ``api/schemas/admin_arguments.py::ParticipantSideUpdate``'s established
    mass-assignment-guard discipline.
  - These schemas are referenced only by ``api/routers/admin_review.py`` —
    never imported by the public routers (cases/arguments/people) — so trust
    and review-state data can never reach a public response (T-49-leak,
    D-34).
"""

from typing import Literal, Optional

from pydantic import BaseModel


class DiscrepancyDetail(BaseModel):
    """One value_discrepancy row, admin-only (D-34's extended leak ban
    covers every field name here). Ordered by ``id`` ASC by the service
    (edge REVIEW-04/ordering) for a stable, repeatable render."""

    id: int
    field: str
    existing_value: Optional[str] = None
    existing_source: Optional[str] = None
    existing_method: Optional[str] = None
    incoming_value: Optional[str] = None
    incoming_source: Optional[str] = None
    incoming_method: Optional[str] = None
    created_at: str


class ReviewQueueConstituent(BaseModel):
    """One flagged participant on a review-queue argument row.

    ``has_open_discrepancy`` and ``discrepancies`` are populated from
    ``list_review_queue_arguments``'s open-discrepancy attachment (plan
    49-04's scope; plan 49-01 always shipped ``has_open_discrepancy=False``
    and an empty list since no discrepancy existed yet).
    """

    participant_id: int
    person_id: Optional[int] = None
    display_name: str
    side: str
    review_state: str
    has_open_discrepancy: bool = False
    discrepancies: list[DiscrepancyDetail] = []


class ReviewQueueArgumentItem(BaseModel):
    """One row in the `/admin/review` Arguments-tab queue.

    ``attention_count`` counts constituents whose review_state is
    ``needs_review`` OR whose ``person_id IS NULL`` — see
    ``api/services/admin_review.py::list_review_queue_arguments``.

    ``admin_job_id`` is the argument's most recently linked ``AdminJob``
    id, or None when no job is linked. It exists so the frontend can build
    the "Resolve speaker" deep link (`/admin/pipeline/{admin_job_id}`) for
    an unresolved (person_id IS NULL) constituent, since Confirm cannot
    clear that leg (tracer feedback gate defect 2).
    """

    id: int
    case_name: str
    docket_number: str
    argued_date: Optional[str] = None
    status: str
    trust_tier: str
    attention_count: int
    admin_job_id: Optional[int] = None
    constituents: list[ReviewQueueConstituent]
    # The summarize_tier_blockers breakdown for this argument
    # (list of {"code": str, "count": int} dicts) — populated even when
    # constituents is empty, so a row queued solely via the degraded-tier
    # leg still has something real to show in the expanded panel.
    blockers: list[dict] = []
    # Phase 50 plan 50-02: open value_discrepancy rows recorded
    # directly against THIS argument's own value columns
    # (target_type="argument") or against its LEAD case's columns
    # (target_type="case") — distinct from `constituents[].discrepancies`,
    # which cover only argument_participant-level rows. Reuses
    # DiscrepancyDetail verbatim (no parallel schema class).
    argument_discrepancies: list[DiscrepancyDetail] = []


class ReviewQueuePersonItem(BaseModel):
    """One row in the `/admin/review` People-tab queue."""

    id: int
    full_name: str
    review_state: str
    provenance_note: str
    has_open_discrepancy: bool = False
    discrepancies: list[DiscrepancyDetail] = []


class ReviewQueueStats(BaseModel):
    """Summary counts for the dashboard StatCard — plan 49-05.

    Backed by ``get_review_queue_stats``'s two dedicated COUNT queries,
    which share the exact inclusion predicates the list endpoints use, so
    this can never disagree with what the screen itself would show.
    """

    arguments: int
    people: int
    total: int


class ReviewActionRequest(BaseModel):
    """PATCH body for `/api/admin/review/participants/{participant_id}` and
    `/api/admin/review/people/{person_id}`.

    Mass-assignment guard (T-49-massassign): ONLY ``action`` is writable via
    this schema — a closed three-value ``Literal``. No id, no target scope,
    and no column value is accepted in the body — scope comes entirely from
    the URL path, and the field being written is chosen server-side by the
    action verb, per ``ParticipantSideUpdate``'s established pattern.

    "edit" deliberately has no literal here: editing a value is a
    deep link into the existing editors (update_participant_side,
    update_resolve_row_for_job, update_person), whose writes already route
    through the Task 2 authority gate — there is no fourth PATCH to build.
    """

    action: Literal["confirm", "confirm_unattributable", "reflag"]
