"""Admin operator review-queue routes (Phase 49, plan 49-01).

Modeled on `api/routers/admin_dev.py`'s small standalone-router shape:
prefix + router-level `verify_admin_token` dependency (imported from
`api.routers.admin`, the same auth this whole admin family uses) + a
ValueError -> HTTPException mapping at the route body.

Unlike `admin_dev_router`, this router is NOT environment-gated — it is a
real operator-facing feature, always mounted (see api/main.py).

This plan (49-01) ships exactly the two routes needed for the tracer:
GET /arguments (the queue) and PATCH /participants/{participant_id} (the
one confirm action). Plans 49-04/49-05 add the People-tab and stats routes
named in 49-01-PLAN.md's <artifacts_this_phase_produces>.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.routers.admin import verify_admin_token
from api.schemas.admin_review import ReviewActionRequest, ReviewQueueArgumentItem
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


@router.patch("/participants/{participant_id}", response_model=dict)
async def patch_review_participant(
    participant_id: int,
    body: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Advance one participant's review_state (T-49-idor scoped by path id)."""
    try:
        result = await admin_review_service.resolve_participant_review(
            db, participant_id, body.action
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    return result
