"""
FastAPI router for argument-related endpoints.

Endpoints:
  GET /arguments/{argument_id}/utterances
    Returns ordered utterances for the given argument, filtered to the latest
    pipeline run, plus argument metadata (case name, docket number, etc.)
    for the UI heading bar.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.schemas.utterance import ArgumentUtterancesResponse
from api.services import arguments as argument_service

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
