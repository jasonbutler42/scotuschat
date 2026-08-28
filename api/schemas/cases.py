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
    # Optional: nullable at the DB layer (Argument.argued_date, models.py:175),
    # identical non-optional-over-nullable-column pattern as
    # ArgumentMetadataResponse (see api/schemas/utterance.py). Not reachable
    # today because get_cases() filters WHERE Argument.published_at.isnot(None)
    # (drafts excluded), but fixed now so a corpus-imported draft with a null
    # argued_date doesn't 500 the public case list the moment it is published.
    argued_date: datetime.date | None = None
    argument_id: int
    # Optional: nullable at the DB layer as of migration 0019,
    # mirroring argued_date's nullable-column handling directly above.
    question_number: int | None = None
    # The argument's public URL slug (Phase 51 plan 51-02, D-10/D-12) — the
    # href target on each row of the /arguments listing. Optional because
    # migration 0031 adds Argument.slug nullable, no backfill (reseed-not-
    # migrate); a pre-existing row reseeded through the real import path
    # always has one, but the type stays honest about the DB contract.
    argument_slug: str | None = None

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    """Wrapper response containing a list of cases."""

    cases: list[CaseItem]
