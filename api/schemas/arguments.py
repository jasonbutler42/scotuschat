"""Pydantic v2 response models for the public term-grouped arguments listing.

Phase 51 plan 51-04 (D-14/D-15): `GET /cases` returns every row with no
limit, offset, filter, or grouping. These models back the term-grouped
replacement — an index of October Terms with published-argument counts
(`TermIndexResponse`), and a term-scoped list of that term's arguments
(`TermArgumentsResponse`).

Apolitical binding (P-01, P-02, P-04): every field here is identification
only — case name, docket, date, term, a published-record count. No
per-speaker or per-argument derived statistic (utterance count, speaking
time, duration, ranking, sentiment), no editorial-prominence flag, and no
operator-facing trust/review-state/provenance vocabulary. `argument_count`
is a count of published records, not a measure of any speaker's behavior.

D-16 (51-DESIGN-DECISIONS.md, "Term-row variant"): the operator selected
Variant A — the minimal row. `ArgumentListItem` therefore carries no
`advocates` field; the `argument_participants` -> `people` join Variant B
would have required is deferred, not built.
"""

import datetime

from pydantic import BaseModel


class TermSummary(BaseModel):
    """One October Term with its published-argument count."""

    term_year: int
    argument_count: int

    model_config = {"from_attributes": True}


class TermIndexResponse(BaseModel):
    """Wrapper response containing the list of terms with published arguments."""

    terms: list[TermSummary]


class ArgumentListItem(BaseModel):
    """One published argument on a term-detail listing page."""

    argument_id: int
    slug: str | None = None
    case_name: str
    docket_number: str
    term_year: int
    argued_date: datetime.date | None = None
    question_number: int | None = None

    model_config = {"from_attributes": True}


class TermArgumentsResponse(BaseModel):
    """Wrapper response containing a term's published arguments."""

    term_year: int
    arguments: list[ArgumentListItem]
