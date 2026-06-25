"""
Public speaker popover schemas.

appointing_president_party is intentionally excluded — admin-only field per
apolitical framing constraint (REQUIREMENTS.md Out of Scope). This schema is
used exclusively by the public GET /arguments/{id}/speakers endpoint.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class TenureEntry(BaseModel):
    """One continuous service period on the Court."""

    seat: Optional[str] = None
    start_date: Optional[str] = None  # DB Date serialized as "YYYY-MM-DD"
    end_date: Optional[str] = None    # None = currently active Justice


class SpeakerPopoverEntry(BaseModel):
    """
    Speaker details for the popover card on the public argument page.

    Contains everything the SvelteKit +page.server.ts needs to render the
    popover without a second API call.  photo_url is the raw DB value;
    full URL reconstruction happens in +page.server.ts (D-03 in CONTEXT.md).
    """

    person_id: int
    full_name: str
    role_name: Optional[str] = None
    photo_url: Optional[str] = None   # raw DB value; URL reconstructed in +page.server.ts (D-03)
    appointing_president: Optional[str] = None
    tenure: list[TenureEntry] = []

    model_config = ConfigDict(from_attributes=True)
