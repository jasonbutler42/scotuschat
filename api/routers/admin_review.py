"""Admin operator review-queue routes (Phase 49).

Modeled on `api/routers/admin_dev.py`'s small standalone-router shape:
prefix + router-level `verify_admin_token` dependency (imported from
`api.routers.admin`, the same auth this whole admin family uses, and the
ONLY auth surface here — no second check is layered on top) + a
ValueError -> HTTPException mapping at the route body.

Unlike `admin_dev_router`, this router is NOT environment-gated — it is a
real operator-facing feature, always mounted (see api/main.py).

Plan 49-01 shipped the tracer's two routes (GET /arguments, PATCH
/participants/{id}, confirm-only). Plan 49-04 adds the People-tab routes
and widens the participant action set to the full three-action resolve
set (confirm, confirm_unattributable, reflag).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.routers.admin import verify_admin_token
from api.schemas.admin_review import (
    ReviewActionRequest,
    ReviewQueueArgumentItem,
    ReviewQueuePersonItem,
)
from api.services import admin_review as admin_review_service

router = APIRouter(
    prefix="/api/admin/review",
    tags=["admin-review"],
    dependencies=[Depends(verify_admin_token)],
)


@router.get("/arguments", response_model=list[ReviewQueueArgumentItem])
async def get_review_queue_arguments(db: AsyncSession = Depends(get_db)):
    """Return every argument needing operator attention (D-05).

    Returns an empty list (never 404) when nothing currently needs review.
    """
    return await admin_review_service.list_review_queue_arguments(db)


@router.get("/people", response_model=list[ReviewQueuePersonItem])
async def get_review_queue_people(db: AsyncSession = Depends(get_db)):
    """Return every Person needing operator attention (D-02).

    Returns an empty list (never 404) when nothing currently needs review.
    """
    return await admin_review_service.list_review_queue_people(db)


@router.patch("/participants/{participant_id}", response_model=dict)
async def patch_review_participant(
    participant_id: int,
    body: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Advance one participant's review_state (T-49-idor scoped by path id).

    Tagged ValueErrors from resolve_participant_review (e.g.
    "unresolved_requires_unattributable", "participant_is_resolved",
    "row_not_yet_reviewed") map to 422 with the tag as the detail, matching
    update_participant_side/update_resolve_row's established convention.
    """
    try:
        result = await admin_review_service.resolve_participant_review(
            db, participant_id, body.action
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    return result


@router.patch("/people/{person_id}", response_model=dict)
async def patch_review_person(
    person_id: int,
    body: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Advance one Person's review_state (T-49-idor scoped by path id).

    Tagged ValueErrors (e.g. "row_not_yet_reviewed",
    "confirm_unattributable_not_applicable_to_person") map to 422 with the
    tag as the detail, matching the participant route's convention.
    """
    try:
        result = await admin_review_service.resolve_person_review(
            db, person_id, body.action
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return result
