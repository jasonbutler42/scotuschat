"""
Trust-tier recompute service.

Thin DB-touching layer over the pure api.domain.trust module: reads exactly
one argument's constituent rows (utterances + argument_participants),
derives a tier per constituent via derive_tier(), takes the floor, and
stores it on Argument.trust_tier — in the SAME transaction as the caller's
own mutation (48-RESEARCH.md Pitfall 2). Every writer path in this phase
(corpus import birth, PDF ingest birth, approve_job, resolve-row edits,
participant edits, publish, unpublish, the offline recompute-trust CLI)
calls recompute_argument_tier before its own commit.

Reads only per-argument `utterances` and `argument_participants` rows
scoped to exactly one argument_id — it never queries the `people` table.
A NULL person_id (unresolved speaker/participant) contributes
TrustTier.UNCERTAIN to the floor — QUALIFIED by Phase 49 D-17: an
ArgumentParticipant with person_id IS NULL AND review_state ==
operator_confirmed (the "confirm as unattributable" resolve action)
contributes VERIFIED instead, lifting this floor. An ORDINARY confirm (on
an already-resolved participant) never touches this NULL-person_id branch,
so it can never trigger the lift as a side effect. D-12:
is_stage_direction=true utterance rows are excluded from the floor
entirely (no speaker to attribute); this is NOT extended to side=UNKNOWN
rows, which still contribute normally.
Every utterance constituent's review_state is still supplied as the
literal api.domain.trust.UNREVIEWED — no per-utterance review signal
exists. Phase 49 fills this module's own participant-branch slot:
`_load_constituents` now reads each ArgumentParticipant's real
`(source, method, review_state)` triple and calls derive_tier() with it,
in place of the Phase 48 placeholder that contributed nothing for a
resolved participant. derive_tier's three-argument signature is unchanged.
"""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.trust import UNREVIEWED, TrustTier, derive_tier, floor_tier
from api.models.models import Argument, ArgumentParticipant, ImportRun, ReviewState, Utterance


class TrustGateBlocked(ValueError):
    """
    Raised by publish_argument when the UNCERTAIN publish gate
    blocks a publish attempt with no (or a blank) override_reason.

    Carries the structured tier + blocker breakdown so the router/SvelteKit
    layer can render "why blocked" rather than a bare string.
    Calling super().__init__("uncertain_tier_blocked") keeps this
    compatible with the codebase's existing `except ValueError as exc:
    ...detail=str(exc)` router pattern (update_argument's
    "slug_collision"/"docket_collision" tagged-error shape).
    """

    code = "uncertain_tier_blocked"

    def __init__(self, tier: TrustTier, blockers: list[dict]) -> None:
        self.tier = tier
        self.blockers = blockers
        super().__init__("uncertain_tier_blocked")


async def _load_constituents(
    db: AsyncSession, argument_id: int
) -> tuple[list[TrustTier], list[dict]]:
    """
    Load and derive a TrustTier for every constituent row of one argument,
    plus a parallel list of blocker-code dicts describing what dragged the
    floor down (used by summarize_tier_blockers / the blocked-publish
    response, D-20).

    Returns (tiers, blockers) where blockers is a list of
    {"code": str, "count": int} dicts with zero-count codes omitted.
    """
    utterance_rows = (
        await db.execute(
            select(
                Utterance.person_id,
                Utterance.is_stage_direction,
                ImportRun.source,
                ImportRun.method,
            )
            .join(ImportRun, Utterance.import_run_id == ImportRun.id)
            .where(Utterance.argument_id == argument_id)
        )
    ).all()
    participant_rows = (
        await db.execute(
            select(
                ArgumentParticipant.person_id,
                ArgumentParticipant.review_state,
                ArgumentParticipant.source,
                ArgumentParticipant.method,
            ).where(ArgumentParticipant.argument_id == argument_id)
        )
    ).all()

    tiers: list[TrustTier] = []
    blocker_counts: dict[str, int] = {}

    def _bump(code: str) -> None:
        blocker_counts[code] = blocker_counts.get(code, 0) + 1

    for person_id, is_stage_direction, source, method in utterance_rows:
        if is_stage_direction:  # No speaker to attribute, no risk
            continue
        if person_id is None:  # Unresolved speaker floors to UNCERTAIN
            tiers.append(TrustTier.UNCERTAIN)
            _bump("unresolved_utterance_speaker")
            continue
        tier = derive_tier(source.value, method.value, UNREVIEWED)
        tiers.append(tier)
        if tier is TrustTier.UNCERTAIN:
            _bump("llm_corrective_utterance")

    for person_id, review_state, source, method in participant_rows:
        if person_id is None:
            # An unresolved speaker (person_id IS NULL) still floors
            # to UNCERTAIN by default — EXCEPT when the operator has
            # explicitly confirmed this participant as unattributable
            # (review_state == operator_confirmed via
            # resolve_participant_review's "confirm_unattributable"
            # action). That is a deliberate human judgment that no further
            # speaker resolution is possible or needed for this row, and it
            # lifts the D-11 floor — derive_tier's rule 1 already returns
            # VERIFIED for operator_confirmed; this branch is what lets
            # that rule apply on the previously short-circuited NULL-
            # person_id path. An ORDINARY confirm (on a resolved
            # participant) never reaches this branch at all, so it can
            # never lift this floor as a side effect.
            if review_state == ReviewState.OPERATOR_CONFIRMED:
                tiers.append(TrustTier.VERIFIED)
            else:
                tiers.append(TrustTier.UNCERTAIN)
                _bump("unresolved_participant")
            continue
        # A resolved participant now contributes a real tier —
        # Pitfall 1: pass .value for every enum-typed column, mirroring the
        # utterance branch above. source/method are nullable; review_state
        # is NOT NULL (always present) as of migration 0028.
        tier = derive_tier(
            source.value if source else "",
            method.value if method else "",
            review_state.value,
        )
        tiers.append(tier)
        if tier is TrustTier.UNCERTAIN:
            _bump("uncertain_participant")

    if not utterance_rows and not participant_rows:
        _bump("no_constituents")

    blockers = [{"code": code, "count": count} for code, count in blocker_counts.items()]
    return tiers, blockers


async def recompute_argument_tier(db: AsyncSession, argument_id: int) -> TrustTier:
    """
    Recompute and store the floor trust_tier for exactly one argument.

    Reads only utterances/argument_participants scoped to argument_id
    (D-10 — never queries `people`). Issues its UPDATE with
    .execution_options(synchronize_session=False) (project-wide critical
    guard, Pitfall 4) and does NOT commit — the calling writer's own
    commit call persists this value in the same transaction (D-07,
    48-RESEARCH.md Pitfall 2). Callers that re-read the same Argument
    object in the same session afterward must refresh it.
    """
    tiers, _blockers = await _load_constituents(db, argument_id)
    result = floor_tier(tiers)
    await db.execute(
        update(Argument)
        .where(Argument.id == argument_id)
        .values(trust_tier=result)
        .execution_options(synchronize_session=False)
    )
    return result


async def summarize_tier_blockers(db: AsyncSession, argument_id: int) -> list[dict]:
    """
    Return the blocker-code breakdown for one argument without writing
    anything (used by plan 48-06's blocked-publish response, D-20).
    """
    _tiers, blockers = await _load_constituents(db, argument_id)
    return blockers
