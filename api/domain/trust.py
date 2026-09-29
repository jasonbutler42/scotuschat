"""
Pure, dependency-light domain contract for trust-tier derivation.

This module has NO FastAPI/SQLAlchemy/Alembic imports. It must remain
importable by API services, pipeline commands, tests, and Alembic
migrations without initializing the app or a database connection —
mirroring api/domain/person_names.py's structural conventions exactly.

Trust means transcription/attribution accuracy, never content judgment
(.planning/notes/provenance-and-trust-model.md § "Trust tiers (derived)").
This module never reads utterance text, speaker names, case names, or any
content field — it is handed only the plain string values of an import
unit's declared provenance (`source`, `method`) plus a `review_state`
string, and it returns one of four ordered TrustTier values.

Derivation order (TRUST-01/D-07, first match wins — see derive_tier()):
  1. review_state in {operator_confirmed, operator_edited} -> VERIFIED
  2. review_state == needs_review -> UNCERTAIN
  3. source == operator and method == manual -> VERIFIED
  4. (source, method) in {(corpus, direct), (seed, direct)} -> TRUSTED
  5. method == normalized -> PROVISIONAL
  6. (source, method) == (pdf_pipeline, rule_based) -> PROVISIONAL
  7. anything else (including (pdf_pipeline, llm_corrective) and any
     unrecognised source/method/review_state) -> UNCERTAIN (fail-closed)

Rule 3 was originally a planner assumption, not stated verbatim in
provenance-and-trust-model.md's tier table (which keys VERIFIED strictly on
review_state and never states what an operator-sourced, unreviewed row
derives). It was flagged in .planning/phases/48-trust-lifecycle/48-01-
PLAN.md's <flagged_assumptions> section pending operator confirmation, and
was CONFIRMED by the operator on 2026-08-21 at the plan 48-09 sign-off
checkpoint — this is now an operator-confirmed
derivation rule, not an outstanding assumption. The rationale stands
unchanged: mapping an operator-authored value to VERIFIED follows the
authority ladder (operator ranks highest) and the note's own worked
example, and is necessary so an operator-created argument is not
unpublishable-without-override by construction — the fail-closed
fallthrough (rule 7) would otherwise apply, which would contradict
operator-final-authority. No production code writes ImportSource.OPERATOR
today, so this rule remains currently unreachable; it exists so the
mapping is total.
"""

from __future__ import annotations

import enum
from typing import Sequence


class TrustTier(str, enum.Enum):
    VERIFIED = "verified"
    TRUSTED = "trusted"
    PROVISIONAL = "provisional"
    UNCERTAIN = "uncertain"


# Least-trusted first, so min() over this ordering is the floor.
_TIER_ORDER: dict[TrustTier, int] = {
    TrustTier.UNCERTAIN: 0,
    TrustTier.PROVISIONAL: 1,
    TrustTier.TRUSTED: 2,
    TrustTier.VERIFIED: 3,
}

# Every Phase 48 caller passes this literal as review_state — no
# per-argument-participant review signal exists yet (ArgumentParticipant has
# no review_state/method column today). Phase 49 will supply a real
# per-participant value in its place; derive_tier's three-argument signature
# does not change when that lands.
UNREVIEWED = "unreviewed"


def derive_tier(source: str, method: str, review_state: str) -> TrustTier:
    """
    Map one (source, method, review_state) triple to exactly one TrustTier.

    This is the ONLY place this mapping exists — every
    runtime (API service layer, offline pipeline CLI, Alembic migrations,
    tests) must call this function rather than re-implementing any part of
    the vocabulary below.

    Accepts the plain string values of ImportSource/ImportMethod
    ("operator", "corpus", "pdf_pipeline", "seed"; "manual", "direct",
    "normalized", "rule_based", "llm_corrective") and of the four
    review_state values ("unreviewed", "needs_review", "operator_confirmed",
    "operator_edited") — never the enum objects themselves, so this pure
    module stays free of a models/SQLAlchemy import.

    Rules are evaluated in this exact precedence order; the first matching
    rule wins (edge case: a triple satisfying more than one rule always
    resolves via the earliest one, never ambiguously):

      1. review_state in {"operator_confirmed", "operator_edited"} -> VERIFIED
      2. review_state == "needs_review" -> UNCERTAIN
      3. source == "operator" and method == "manual" -> VERIFIED
      4. (source, method) in {("corpus", "direct"), ("seed", "direct")} -> TRUSTED
      5. method == "normalized" -> PROVISIONAL
      6. (source, method) == ("pdf_pipeline", "rule_based") -> PROVISIONAL
      7. anything else, including ("pdf_pipeline", "llm_corrective") and any
         unrecognised source/method/review_state -> UNCERTAIN (fail-closed)

    See this module's docstring for the source of each rule and rule 3's
    operator-confirmed rationale (confirmed 2026-08-21, plan 48-09).
    """
    if review_state in ("operator_confirmed", "operator_edited"):
        return TrustTier.VERIFIED
    if review_state == "needs_review":
        return TrustTier.UNCERTAIN
    if source == "operator" and method == "manual":
        return TrustTier.VERIFIED
    if (source, method) in (("corpus", "direct"), ("seed", "direct")):
        return TrustTier.TRUSTED
    if method == "normalized":
        return TrustTier.PROVISIONAL
    if (source, method) == ("pdf_pipeline", "rule_based"):
        return TrustTier.PROVISIONAL
    return TrustTier.UNCERTAIN


def floor_tier(tiers: Sequence[TrustTier]) -> TrustTier:
    """
    Return the floor (least-trusted / minimum) tier over a sequence of
    constituent tiers (TRUST-02's rollup rule).

    Zero-constituent base case (Zero-Utterance Tier Decision,
    48-RESEARCH.md § "Zero-Utterance Tier Decision", Pitfall 3): an empty
    sequence returns TrustTier.UNCERTAIN via an explicit early return —
    NEVER a bare min() over an empty iterable, which would raise
    ValueError. An argument with zero utterances and zero participants has
    the maximal attribution risk (no evidence at all), not a free pass, so
    it must read identically to the column's own fail-closed default.

    Ordering/adjacency guarantee: returns the same TrustTier for any
    permutation of the same constituent list (min() over a fixed per-tier
    rank is permutation-invariant by construction), and returns that tier
    unchanged when every entry is equal.
    """
    if not tiers:
        return TrustTier.UNCERTAIN
    return min(tiers, key=lambda t: _TIER_ORDER[t])


def exceeds_undetermined_majority(undetermined: int, total: int) -> bool:
    """
    D-06/SPEAKER-05: True when strictly more than half of `total`
    non-stage-direction utterances are source-undetermined
    (`speaker_undetermined is True`).

    Integer arithmetic only — `2 * undetermined > total` compares the
    EXACT ratio, never a float or a rounded percentage. An argument at
    50.2% undetermined is held; one at 49.8% is not; exactly half (2 of 4)
    is NOT held (strictly greater than half, not "at least half"). A zero
    total (no non-stage-direction utterances at all) returns False — there
    is nothing to hold a majority over.
    """
    return total > 0 and 2 * undetermined > total


def undetermined_share_percent(undetermined: int, total: int) -> int:
    """
    Display-only half-up integer rounding of `undetermined / total` as a
    percentage (D-18; rounding choice is Claude's discretion per
    53-CONTEXT.md). Raises ValueError when `total <= 0` — there is no
    percentage of zero constituents to display.

    `(200 * undetermined + total) // (2 * total)` is the half-up integer
    rounding of `100 * undetermined / total` computed entirely in
    integers: 101/200 -> 51 (not banker's 50), 134/267 -> 50, 68/100 -> 68,
    3/5 -> 60.

    This function is NEVER used by exceeds_undetermined_majority's own
    gate comparison — it reads the exact ratio. Consequence: an argument
    at 50.2% undetermined displays "50%" (the rounded number) while still
    being held, because the gate compares the exact ratio and the
    blocker's accompanying sentence ("more than half") carries the fact
    the rounded number alone cannot.
    """
    if total <= 0:
        raise ValueError("undetermined_share_percent: total must be > 0")
    return (200 * undetermined + total) // (2 * total)
