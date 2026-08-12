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
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.schemas.speakers import SpeakerPopoverEntry
from api.schemas.utterance import ArgumentUtterancesResponse
from api.services import arguments as argument_service
from api.services import speakers as speakers_service

router = APIRouter(prefix="/arguments", tags=["arguments"])


@router.get("/{argument_id}/utterances", response_model=ArgumentUtterancesResponse)
async def get_utterances(
    argument_id: int,
    db: AsyncSession = Depends(get_db),
) -> ArgumentUtterancesResponse:
    """
    Return ordered utterances for an argument.

    Path parameter `argument_id` is validated as int by FastAPI — non-integer
    values produce a 422 Unprocessable Entity response without reaching the
    service layer (T-05-01 SQL injection mitigation).

    Returns 404 if the argument ID is not found or has no linked cases.
    """
    result = await argument_service.get_argument_with_utterances(db, argument_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Argument not found")
    return result


@router.get("/{argument_id}/speakers", response_model=list[SpeakerPopoverEntry])
async def get_speakers(
    argument_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[SpeakerPopoverEntry]:
    """
    Return speaker popover data for all resolved speakers in an argument.

    Returns 404 if the argument ID is not found or is not published (BUG-01/D-02) —
    identical detail string to get_utterances's 404 (D-01). Returns an empty list
    (not 404) when the argument is published but no utterances have been resolved
    (person_id IS NULL).
    argument_id validated as int by FastAPI — non-integer path values produce 422
    without reaching the service layer (T-14-01 SQL injection mitigation, same as T-05-01).
    """
    result = await speakers_service.get_argument_speakers(db, argument_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Argument not found")
    return result
