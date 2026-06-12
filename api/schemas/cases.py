"""Pydantic v2 response models for the cases API endpoint."""

import datetime

from pydantic import BaseModel


class CaseItem(BaseModel):
    """A loaded case with metadata for the case list page."""

    id: int
    slug: str
    case_name: str
    docket_number: str
    term_year: int
    argued_date: datetime.date
    argument_id: int
    question_number: int

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    """Wrapper response containing a list of cases."""

    cases: list[CaseItem]
