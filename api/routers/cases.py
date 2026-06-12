"""
FastAPI router for cases endpoints.

Endpoints:
  GET /cases
    Returns all loaded cases with metadata for the case list page.
    Filters by is_lead=True to prevent duplicate rows from consolidated dockets.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.schemas.cases import CaseListResponse
from api.services import cases as cases_service

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=CaseListResponse)
async def get_cases(
    db: AsyncSession = Depends(get_db),
) -> CaseListResponse:
    """
    Return all loaded cases with metadata for the case list page.

    Returns an empty list when no cases are loaded (not 404).
    The is_lead=True filter in the service prevents consolidated dockets
    (e.g. Obergefell 14-556/562/571/574) from producing duplicate rows.
    """
    results = await cases_service.get_cases(db)
    return CaseListResponse(cases=results)
