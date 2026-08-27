"""
Public speaker popover schemas.

appointing_president_party is included on each tenure entry. Phase 14
 originally kept this field out of the public schema on apolitical
grounds; Phase 39 (39-CONTEXT.md D-11/D-12) reverses that decision because the
value describes the *appointing president's* party affiliation — a partisan
officeholder by definition, and factual historical record — not the Justice's,
who has no party. It is serialised identically for every tenure entry, with
no aggregation and no differential framing, so the apolitical constraint on
how Justices themselves are treated is preserved. This schema is used
exclusively by the public GET /arguments/{id}/speakers endpoint.
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
    # The raw canonical reason_left value
    # ("retired"/"died"/"promoted") is carried end to end; projection to the
    # formal display title ("Retired"/"Died in office"/"Promoted") happens
    # at the render boundary (SpeakerPopover.svelte), not here — same
    # precedent as `office` above. None when the tenure has no recorded
    # reason (open tenure, or unknown historical row — D-02).
    reason_left: Optional[str] = None
    # Phase 39 (D-13, promote not add-alongside): the per-tenure appointing
    # president, replacing the retired top-level `appointing_president` field
    # below — a Justice can hold more than one tenure with a different
    # appointing president each (e.g. Rehnquist: Nixon, then Reagan), which a
    # single person-level value cannot represent.
    appointed_by: Optional[str] = None
    # Phase 39 (D-11/D-12, reverses T-14-02): the appointing president's party
    # affiliation — factual historical record about the president, not the
    # Justice. Serialised identically for every entry.
    appointing_president_party: Optional[str] = None


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
    photo_url: Optional[str] = None   # raw DB value; URL reconstructed in +page.server.ts
    # The top-level `appointing_president` field that lived
    # here (hardcoded null since Phase 22) is retired. The concept moved onto
    # each `TenureEntry` as `appointed_by` (see above) — do not re-add a
    # top-level field.
    birthdate: Optional[str] = None   # DB Date serialized as "YYYY-MM-DD"; None when unknown
    death_date: Optional[str] = None  # DB Date serialized as "YYYY-MM-DD"; None when living/unknown
    bio_text: Optional[str] = None    # None when no bio is on file
    tenure: list[TenureEntry] = []
    side: Optional[str] = None        # raw SideEnum value for isBench rendering logic

    model_config = ConfigDict(from_attributes=True)
