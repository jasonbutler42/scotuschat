"""
FastAPI router for people endpoints.

Endpoints:
  GET /people/{person_id}
    Returns a person record with resolved name and role.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.schemas.people import PersonResponse
from api.services import people as people_service

router = APIRouter(prefix="/people", tags=["people"])


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: int,
    db: AsyncSession = Depends(get_db),
) -> PersonResponse:
    """
    Return person metadata by ID.

    Path parameter `person_id` is validated as int by FastAPI — non-integer
    values produce a 422 Unprocessable Entity response without reaching the
    service layer (T-03-01 SQL injection mitigation).

    Returns 404 if the person ID is not found.
    """
    result = await people_service.get_person_by_id(db, person_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return result
