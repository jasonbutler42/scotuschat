"""
Public speaker popover schemas.

appointing_president_party is intentionally excluded — admin-only field per
apolitical framing constraint (REQUIREMENTS.md Out of Scope). This schema is
used exclusively by the public GET /arguments/{id}/speakers endpoint.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class TenureEntry(BaseModel):
    """One continuous service period on the Court.

    office carries the canonical storage value ("chief"/"associate", Phase 37
    D-15/D-17) — projection to the formal "Chief Justice"/"Associate Justice"
    display title happens at the render boundary (SpeakerPopover.svelte), not
    here. There is no `seat` compatibility alias.
    """

    office: Optional[str] = None
    start_date: Optional[str] = None  # DB Date serialized as "YYYY-MM-DD"
    end_date: Optional[str] = None    # None = currently active Justice
    # Phase 39 (D-01/D-15): the raw canonical reason_left value
    # ("retired"/"died"/"promoted") is carried end to end; projection to the
    # formal display title ("Retired"/"Died in office"/"Promoted") happens
    # at the render boundary (SpeakerPopover.svelte), not here — same
    # precedent as `office` above. None when the tenure has no recorded
    # reason (open tenure, or unknown historical row — D-02).
    reason_left: Optional[str] = None


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
    side: Optional[str] = None        # raw SideEnum value for isBench rendering logic (Phase 15)

    model_config = ConfigDict(from_attributes=True)
