"""Pydantic v2 response models for the people API endpoint."""

from typing import Optional

from pydantic import BaseModel


class PersonResponse(BaseModel):
    """A resolved speaker — Justice or counsel."""

    id: int
    full_name: str
    role_name: Optional[str] = None  # None if person has no role assigned

    model_config = {"from_attributes": True}
