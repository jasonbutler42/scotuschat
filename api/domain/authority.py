"""
Pure, dependency-light domain contract for the write-acceptance authority
ladder (Phase 49, REVIEW-02, D-31/D-31a/D-31b).

This module has NO FastAPI/SQLAlchemy/Alembic imports. It must remain
importable by API services, pipeline commands, tests, and Alembic
migrations without initializing the app or a database connection —
mirroring api/domain/trust.py's and api/domain/person_names.py's
structural conventions exactly.

This is the ONLY place the write-acceptance ordering exists. Every runtime
that decides whether an incoming value may overwrite a stored one must call
`decide_write` rather than re-implementing any part of this ladder.

`decide_write` answers a DIFFERENT question than `api.domain.trust.derive_tier`
and the two must never be collapsed:
  - `derive_tier` answers "how much do we trust this row" (a TrustTier).
  - `decide_write` answers "may this incoming value overwrite that stored
    one" (a WriteDecision).

Authority order (highest to lowest), from
.planning/notes/provenance-and-trust-model.md § "The authority ladder" and
.planning/ROADMAP.md Phase 50 success criterion 5:

    operator  >  corpus (or seed)  >  pdf_pipeline/rule_based  >  pdf_pipeline/llm_corrective  >  unrecognised

`seed` is ranked with `corpus` because `derive_tier` already treats
`("seed", "direct")` and `("corpus", "direct")` identically (both TRUSTED) —
see 49-04-PLAN.md's flagged assumptions.

D-22: an operator EDIT does NOT rewrite a row's stored `source`/`method` —
the row keeps its original provenance as a durable record of where the
value came from. Operator authority is instead carried entirely by
`review_state ∈ {operator_confirmed, operator_edited}`. `authority_rank`
therefore checks `review_state` FIRST, before `source`, so an
operator-edited row that still carries its original `corpus`/`direct`
provenance columns is nonetheless read as OPERATOR authority.
"""

from __future__ import annotations

import enum


class AuthorityRank(int, enum.Enum):
    """Ordered authority rungs — int enum so comparison IS the ordering
    (mirrors api.domain.trust's `_TIER_ORDER` intent without a parallel
    lookup dict). Higher value == higher authority."""

    UNKNOWN = 0
    PDF_LLM = 1
    PDF_RULE_BASED = 2
    CORPUS = 3
    OPERATOR = 4


class WriteDecision(str, enum.Enum):
    """The three reachable outcomes of `decide_write` (D-31b).

    A `(accepted, should_record)` boolean pair would make `(False, False)`
    — reject silently — expressible, which is exactly the behavior D-16
    forbids (an incoming value that is rejected must ALWAYS leave a
    `value_discrepancy` record). This three-way enum makes that
    combination inexpressible:

      - ACCEPT — the values agree after normalization (or the stored side
        is empty/blank). Write, no record.
      - ACCEPT_AND_RECORD — the incoming value strictly outranks the
        stored one and they differ. Write, and record the discrepancy so
        the overwritten value survives somewhere.
      - REJECT_AND_RECORD — the incoming value ranks equal-or-lower than
        the stored one and they differ. Keep the stored value, record the
        disagreement (D-16, and REVIEW-02's core rule).
    """

    ACCEPT = "accept"
    ACCEPT_AND_RECORD = "accept_and_record"
    REJECT_AND_RECORD = "reject_and_record"


def authority_rank(source: str, method: str, review_state: str) -> AuthorityRank:
    """
    Map one (source, method, review_state) triple to its AuthorityRank.

    Plain strings only, never enum members (same discipline as
    `api.domain.trust.derive_tier`) — callers must pass `.value`, never the
    enum object itself, so this pure module stays free of a models/
    SQLAlchemy import.

    Rules are evaluated in this exact order; the first matching rule wins:

      1. review_state in {"operator_confirmed", "operator_edited"} -> OPERATOR.
         First on purpose: D-22 says an operator edit does NOT rewrite the
         row's stored source/method, so operator authority can ONLY be read
         off review_state.
      2. source == "operator" -> OPERATOR.
      3. source in ("corpus", "seed") -> CORPUS.
      4. (source, method) == ("pdf_pipeline", "rule_based") -> PDF_RULE_BASED.
      5. (source, method) == ("pdf_pipeline", "llm_corrective") -> PDF_LLM.
      6. anything else -> UNKNOWN (fail-closed — an unrecognised source can
         never outrank anything).
    """
    if review_state in ("operator_confirmed", "operator_edited"):
        return AuthorityRank.OPERATOR
    if source == "operator":
        return AuthorityRank.OPERATOR
    if source in ("corpus", "seed"):
        return AuthorityRank.CORPUS
    if (source, method) == ("pdf_pipeline", "rule_based"):
        return AuthorityRank.PDF_RULE_BASED
    if (source, method) == ("pdf_pipeline", "llm_corrective"):
        return AuthorityRank.PDF_LLM
    return AuthorityRank.UNKNOWN


def decide_write(
    *,
    incoming_source: str,
    incoming_method: str,
    incoming_review_state: str,
    existing_source: str,
    existing_method: str,
    existing_review_state: str,
    values_differ: bool,
) -> WriteDecision:
    """
    Decide whether an incoming value may overwrite an existing stored value.

    Keyword-only; every provenance argument is a plain string (never an
    enum member — same discipline as `authority_rank`). `values_differ` is
    computed by the CALLER with a field-appropriate normalizer — this
    module stays field-agnostic and dependency-light on purpose, since
    normalization is field-specific (name parts have their own normalizer;
    `side` and `person_id` do not) and the REVIEW-01/encoding contract
    belongs in one named helper at the call site, not here.

    Logic:
      - `values_differ` is False -> ACCEPT (nothing to write differently,
        nothing to record).
      - `values_differ` is True and the incoming rank is STRICTLY greater
        than the stored rank -> ACCEPT_AND_RECORD.
      - `values_differ` is True and the incoming rank is EQUAL to or LESS
        than the stored rank -> REJECT_AND_RECORD.

    **Equal authority rejects.** This is the boundary the whole requirement
    rests on: a same-rank incoming value (e.g. a fresh corpus re-import
    disagreeing with an existing corpus value) does NOT silently overwrite
    — it is rejected and recorded, exactly like a strictly-lower-authority
    value. Only a STRICTLY higher incoming rank may overwrite a disagreeing
    stored value.
    """
    if not values_differ:
        return WriteDecision.ACCEPT

    incoming_rank = authority_rank(incoming_source, incoming_method, incoming_review_state)
    existing_rank = authority_rank(existing_source, existing_method, existing_review_state)

    if incoming_rank > existing_rank:
        return WriteDecision.ACCEPT_AND_RECORD
    return WriteDecision.REJECT_AND_RECORD
