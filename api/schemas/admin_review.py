"""Pydantic v2 request/response models for the admin review-queue API (Phase 49).

Scope of this plan (49-01): one thin end-to-end tracer — a flagged
`argument_participants` row surfacing on `/admin/review` and being confirmed
inline. Plans 49-04/49-05 widen this module (People tab, discrepancy
detail, "confirm as unattributable", "re-flag for review") — this file is
deliberately a subset, not the full 49-UI-SPEC.md contract.

Security notes:
  - ReviewActionRequest exposes ONLY ``action: Literal["confirm"]`` — no id,
    no target scope, no column name is accepted in the body (T-49-massassign).
    Scope is derived from the URL path, mirroring
    ``api/schemas/admin_arguments.py::ParticipantSideUpdate``'s established
    mass-assignment-guard discipline. Plans 49-04/49-05 widen the literal.
  - These schemas are referenced only by ``api/routers/admin_review.py`` —
    never imported by the public routers (cases/arguments/people) — so trust
    and review-state data can never reach a public response (T-49-leak).
"""

from typing import Literal, Optional

from pydantic import BaseModel


class ReviewQueueConstituent(BaseModel):
    """One flagged participant on a review-queue argument row.

    ``has_open_discrepancy`` defaults False in this plan — no discrepancy
    data is populated or displayed yet (plan 49-04's scope); the field
    exists now so plan 49-04 does not have to touch this schema's shape.
    """

    participant_id: int
    person_id: Optional[int] = None
    display_name: str
    side: str
    review_state: str
    has_open_discrepancy: bool = False


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


class ReviewActionRequest(BaseModel):
    """PATCH body for `/api/admin/review/participants/{participant_id}`.

    Mass-assignment guard (T-49-massassign): ONLY ``action`` is writable via
    this schema. No id, no target scope, and no column name is accepted in
    the body — scope comes entirely from the URL path, per
    ``ParticipantSideUpdate``'s established pattern. This plan (49-01) ships
    exactly one action; plans 49-04/49-05 widen this literal to add
    "confirm_unattributable" and "reflag".
    """

    action: Literal["confirm"]
