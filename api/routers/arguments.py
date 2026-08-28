"""
FastAPI router for argument-related endpoints.

Endpoints:
  GET /arguments/{argument_id}/utterances
    Returns ordered utterances for the given argument, filtered to the latest
    pipeline run, plus argument metadata (case name, docket number, etc.)
    for the UI heading bar.

  GET /arguments/{argument_id}/speakers
    Returns speaker popover data for all resolved speakers in an argument.
    Empty list when no utterances have been resolved (person_id IS NULL).

  GET /arguments/by-slug/{slug}/utterances
  GET /arguments/by-slug/{slug}/speakers
    Phase 51 plan 51-02 (D-10/D-12): the public-URL peers of the two routes
    above, resolving a slug to an argument id first. Four-segment paths —
    they cannot collide with the three-segment {argument_id} routes above,
    so no declaration-order dependency is introduced between them.
"""

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.schemas.speakers import SpeakerPopoverEntry
from api.schemas.utterance import ArgumentUtterancesResponse
from api.services import arguments as argument_service
from api.services import speakers as speakers_service

router = APIRouter(prefix="/arguments", tags=["arguments"])

# T-51-02-01: a slug is untrusted input reaching a database query. Rejecting
# anything outside lowercase-alphanumeric-hyphen with a 422 before the
# service layer runs closes a path-traversal / injection primitive (e.g. a
# URL-encoded "../etc/passwd" segment) the same way the integer routes'
# ge/le bounds close theirs.
_SLUG_PATH = Path(..., min_length=1, max_length=200, pattern=r"^[a-z0-9-]+$")


@router.get("/{argument_id}/utterances", response_model=ArgumentUtterancesResponse)
async def get_utterances(
    argument_id: int = Path(..., ge=1, le=2_147_483_647),
    db: AsyncSession = Depends(get_db),
) -> ArgumentUtterancesResponse:
    """
    Return ordered utterances for an argument.

    Path parameter `argument_id` is validated as int by FastAPI — non-integer
    values produce a 422 Unprocessable Entity response without reaching the
    service layer (T-05-01 SQL injection mitigation). The ge/le bounds match
    the `Integer` (int4) DB column's range so an out-of-range ID 422s cleanly
    instead of raising an unhandled driver error and 500ing.

    Returns 404 if the argument ID is not found or has no linked cases.
    """
    result = await argument_service.get_argument_with_utterances(db, argument_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Argument not found")
    return result


@router.get("/{argument_id}/speakers", response_model=list[SpeakerPopoverEntry])
async def get_speakers(
    argument_id: int = Path(..., ge=1, le=2_147_483_647),
    db: AsyncSession = Depends(get_db),
) -> list[SpeakerPopoverEntry]:
    """
    Return speaker popover data for all resolved speakers in an argument.

    Returns 404 if the argument ID is not found or is not published —
    identical detail string to get_utterances's 404. Returns an empty list
    (not 404) when the argument is published but no utterances have been resolved
    (person_id IS NULL).
    argument_id validated as int by FastAPI — non-integer path values produce 422
    without reaching the service layer (T-14-01 SQL injection mitigation, same as T-05-01).
    The ge/le bounds match the `Integer` (int4) DB column's range so an out-of-range
    ID 422s cleanly instead of raising an unhandled driver error and 500ing.
    """
    result = await speakers_service.get_argument_speakers(db, argument_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Argument not found")
    return result


@router.get("/by-slug/{slug}/utterances", response_model=ArgumentUtterancesResponse)
async def get_utterances_by_slug(
    slug: str = _SLUG_PATH,
    db: AsyncSession = Depends(get_db),
) -> ArgumentUtterancesResponse:
    """
    The public-URL peer of `GET /{argument_id}/utterances` (D-10, D-12):
    resolves `slug` to an argument id under the published gate, then
    delegates to the exact same service call the integer route uses — no
    second query-shape to keep in sync.

    Returns 404 (same detail string as the integer route) when the slug
    does not resolve to a published argument.
    """
    argument_id = await argument_service.get_argument_by_slug(db, slug)
    if argument_id is None:
        raise HTTPException(status_code=404, detail="Argument not found")
    result = await argument_service.get_argument_with_utterances(db, argument_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Argument not found")
    return result


@router.get("/by-slug/{slug}/speakers", response_model=list[SpeakerPopoverEntry])
async def get_speakers_by_slug(
    slug: str = _SLUG_PATH,
    db: AsyncSession = Depends(get_db),
) -> list[SpeakerPopoverEntry]:
    """
    The public-URL peer of `GET /{argument_id}/speakers` (D-10, D-12).
    Returns 404 (same detail string as the integer route) when the slug
    does not resolve to a published argument. Returns an empty list (not
    404) when the argument is published but no utterances have been
    resolved (person_id IS NULL) — identical to the integer route.
    """
    argument_id = await argument_service.get_argument_by_slug(db, slug)
    if argument_id is None:
        raise HTTPException(status_code=404, detail="Argument not found")
    result = await speakers_service.get_argument_speakers(db, argument_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Argument not found")
    return result
