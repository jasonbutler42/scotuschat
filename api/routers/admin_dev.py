"""
Dev-only admin router — "Reset to Fixture" (Phase 43, DEVTOOL-01/DEVTOOL-02)
and "Seed unresolved speaker" (Phase 49, D-33a).

This router is ONLY mounted on the FastAPI app (api/main.py) when
settings.environment == "development" (D-07). In every other environment it
is genuinely absent — a request to it 404s because the route was never
registered, not because a handler refused it with a 403.

A brand-new, separate APIRouter (RESEARCH.md Pattern 1) — never added to
api/routers/admin.py's existing flat router. Gating that router would also
404 login, people-editing, and every other admin feature in production.

Prefix: /api/admin/dev (a sub-prefix of the existing /api/admin family).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.routers.admin import verify_admin_token
from api.schemas.admin_dev import ResetToFixtureResponse, SeedUnresolvedSpeakerResponse
from api.services import admin_dev as admin_dev_service
from api.services.admin_dev import (
    CorpusUnavailableError,
    FixtureNotSeededError,
    ResetIncompleteError,
)

router = APIRouter(
    prefix="/api/admin/dev",
    tags=["admin-dev"],
    dependencies=[Depends(verify_admin_token)],
)


@router.post("/reset-to-fixture", response_model=ResetToFixtureResponse)
async def reset_to_fixture(db: AsyncSession = Depends(get_db)):
    """
    Wipe the D-01 table set and reseed the fixture set through the real
    import-convokit path.

    Auth inherited from router-level verify_admin_token dependency. This
    route is only reachable at all when the environment is development
    (D-07) — see api/main.py's guarded include_router call.

    Takes no request body, query parameter, or header of its own — the
    fixture set is a hardcoded constant (api.services.admin_dev.FIXTURE_SET).
    The admin token value is never included in any error detail below.
    """
    try:
        result = await admin_dev_service.reset_to_fixture(db)
    except CorpusUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ResetIncompleteError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result


@router.post("/seed-unresolved-speaker", response_model=SeedUnresolvedSpeakerResponse)
async def seed_unresolved_speaker(db: AsyncSession = Depends(get_db)):
    """
    Null the person_id of one advocate-side participant on the Complexity
    fixture argument, so the unresolved-speaker case can be produced on
    demand in a browser (D-33a). See
    api.services.admin_dev.seed_unresolved_speaker_fixture's docstring for
    why this exists and why it is dev-only.

    Auth inherited from router-level verify_admin_token dependency. This
    route is only reachable at all when the environment is development
    (D-07) — see api/main.py's guarded include_router call, the same gate
    reset-to-fixture uses. There is no handler-level environment check
    here: a 403 would confirm to a prober that the endpoint exists at all.

    Takes no request body, query parameter, or header of its own — the
    target conversation is the service's own default constant, never a
    request surface.
    """
    try:
        result = await admin_dev_service.seed_unresolved_speaker_fixture(db)
    except FixtureNotSeededError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result
