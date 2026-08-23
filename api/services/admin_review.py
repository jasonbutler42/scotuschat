"""Business logic for the admin operator review queue (Phase 49, plan 49-01).

Scope of this plan: one thin end-to-end tracer wiring a flagged
`argument_participants` row through to `/admin/review` and an inline
Confirm action. No filters, no tabs, no People queue, no discrepancy
display — those are plans 49-04/49-05.

Public service functions:
  - list_review_queue_arguments — D-05 inclusion query, one row per
    argument, assembled in Python (never a set-combined query per leg).
  - resolve_participant_review — the participant confirm action; follows
    this codebase's real commit convention (see the note below), NOT the
    upstream research docs' "caller commits" claim.

Commit convention (see 49-01-PLAN.md <planner_deviations> item 1): direct
inspection of `api/services/admin_arguments.py` shows the real rule is "one
public service entry point commits exactly once at the end; every helper it
composes must NOT commit" — `publish_argument`, `update_participant_side`,
and `unpublish_argument` each commit their own transaction internally.
`resolve_participant_review` follows that same rule and is this module's
one commit site; `recompute_argument_tier` (api.services.trust) correctly
never commits and stays that way.
"""

from __future__ import annotations

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.trust import TrustTier
from api.models.models import (
    AdminJob,
    Argument,
    ArgumentParticipant,
    Case,
    CaseArgument,
    Person,
    ReviewState,
)
from api.services.trust import recompute_argument_tier


async def list_review_queue_arguments(db: AsyncSession) -> list[dict]:
    """Return every argument needing operator attention, one dict per argument.

    D-05 inclusion predicate — a single OR-composed WHERE over three legs,
    never three separate per-leg queries combined afterward, so an
    argument satisfying more than one leg at once still appears exactly
    once:
      1. a constituent's review_state == NEEDS_REVIEW
      2. a constituent participant row exists whose person_id IS NULL
         (an *existing* unresolved participant row — deliberately guarded
         by `ArgumentParticipant.id.is_not(None)` so an argument with ZERO
         participant rows is not spuriously matched merely because the
         outer join produces NULL columns for it; that argument still
         surfaces via leg 3 whenever its zero-constituent trust_tier is
         genuinely degraded, per floor_tier's own empty-sequence rule)
      3. the argument's own trust_tier is UNCERTAIN or PROVISIONAL

    Unbounded (D-04). Sorted server-side: argued_date ASC NULLS LAST, then
    Argument.id ASC (the tier-rank / published-degraded-first ordering is
    plan 49-05's), THEN ArgumentParticipant.side ASC, then
    ArgumentParticipant.id ASC.

    That trailing pair of keys (tracer feedback gate defect 1) exists so
    that confirming a constituent can never move it within its argument's
    row: PostgreSQL writes an UPDATEd row as a new heap tuple, so without an
    explicit ordering on the participant a sequential scan returns the
    just-confirmed row last, and the confirmed constituent visibly jumps to
    the bottom of the list on the very next load. Ordering by (side, id) —
    both immutable for a given participant — pins every constituent's
    position regardless of write order.

    Only flagged constituent rows are attached to each argument's
    `constituents` list — a participant row that does not itself satisfy
    leg 1 or leg 2 is not included, even when its sibling row on the same
    argument pulled the argument in via leg 3. Full multi-leg constituent
    presentation is plan 49-05's scope.

    attention_count counts constituents whose review_state == needs_review
    OR whose person_id IS NULL.

    Each argument also carries `admin_job_id` — the id of its most
    recently created linked `AdminJob`, or None when the argument has no
    linked job. An argument may legitimately have zero or more than one
    `AdminJob` row; this is a correlated scalar subquery (not a join) so
    picking "most recent by id" never multiplies the outer argument rows
    (tracer feedback gate defect 2b). Used by the frontend to build the
    "Resolve speaker" deep link for an unresolved (person_id IS NULL)
    constituent — see 49-05-PLAN.md's already-decided routing, pulled
    forward here because the tracer would otherwise be a dead end on the
    only unresolved data that exists.
    """
    unresolved_participant_leg = and_(
        ArgumentParticipant.id.is_not(None),
        ArgumentParticipant.person_id.is_(None),
    )
    needs_review_leg = ArgumentParticipant.review_state == ReviewState.NEEDS_REVIEW
    degraded_tier_leg = Argument.trust_tier.in_(
        [TrustTier.UNCERTAIN, TrustTier.PROVISIONAL]
    )

    latest_admin_job_id = (
        select(AdminJob.id)
        .where(AdminJob.argument_id == Argument.id)
        .order_by(AdminJob.id.desc())
        .limit(1)
        .correlate(Argument)
        .scalar_subquery()
    )

    q = (
        select(
            Argument.id,
            Argument.argued_date,
            Argument.status,
            Argument.trust_tier,
            Case.case_name,
            Case.docket_number,
            ArgumentParticipant.id.label("participant_id"),
            ArgumentParticipant.person_id,
            ArgumentParticipant.side,
            ArgumentParticipant.review_state,
            ArgumentParticipant.raw_speaker_label,
            Person.full_name,
            latest_admin_job_id.label("admin_job_id"),
        )
        .join(CaseArgument, CaseArgument.argument_id == Argument.id)
        .join(Case, CaseArgument.case_id == Case.id)
        .outerjoin(ArgumentParticipant, ArgumentParticipant.argument_id == Argument.id)
        .outerjoin(Person, Person.id == ArgumentParticipant.person_id)
        .where(CaseArgument.is_lead == True)  # noqa: E712
        .where(or_(needs_review_leg, unresolved_participant_leg, degraded_tier_leg))
        .order_by(
            Argument.argued_date.asc().nulls_last(),
            Argument.id.asc(),
            ArgumentParticipant.side.asc(),
            ArgumentParticipant.id.asc(),
        )
    )
    rows = (await db.execute(q)).all()

    arguments: dict[int, dict] = {}
    order: list[int] = []
    for row in rows:
        arg_id = row.id
        if arg_id not in arguments:
            arguments[arg_id] = {
                "id": arg_id,
                "case_name": row.case_name,
                "docket_number": row.docket_number,
                "argued_date": row.argued_date.isoformat() if row.argued_date else None,
                "status": row.status.value,
                "trust_tier": row.trust_tier.value,
                "admin_job_id": row.admin_job_id,
                "constituents": [],
            }
            order.append(arg_id)

        if row.participant_id is None:
            continue  # no participant row on this joined line — nothing to list

        is_flagged = (
            row.review_state == ReviewState.NEEDS_REVIEW or row.person_id is None
        )
        if not is_flagged:
            continue

        display_name = row.full_name if row.person_id is not None else row.raw_speaker_label
        arguments[arg_id]["constituents"].append(
            {
                "participant_id": row.participant_id,
                "person_id": row.person_id,
                "display_name": display_name,
                "side": row.side.value,
                "review_state": row.review_state.value,
                "has_open_discrepancy": False,
            }
        )

    items: list[dict] = []
    for arg_id in order:
        arg = arguments[arg_id]
        arg["attention_count"] = len(arg["constituents"])
        items.append(arg)
    return items


async def resolve_participant_review(
    db: AsyncSession, participant_id: int, action: str
) -> dict | None:
    """Advance one participant's review_state and recompute the argument's tier.

    Scoped select-then-update (T-49-idor) — a missing participant_id
    returns None (router -> 404), never a silent no-op.

    This plan (49-01) implements exactly one action, "confirm" — advances
    review_state to OPERATOR_CONFIRMED. The schema-level
    ``ReviewActionRequest.action: Literal["confirm"]`` already restricts
    callers to this value; the guard below is defense-in-depth against any
    future caller that bypasses the schema.

    Unresolved-speaker guard (tracer feedback gate defect 2a): raises
    ValueError when the participant's person_id IS NULL. Confirm only
    advances review_state — it never touches person_id — so confirming an
    unresolved speaker would be a permanent no-op that silently pretends to
    succeed while never clearing the row from the queue. Mirrors
    ``api/services/admin_arguments.py::update_participant_side``'s
    established unresolved-row rejection idiom (raise ValueError, router
    maps to 422). Clearing an unresolved row is plan 49-04's
    "confirm-as-unattributable" action (D-17 floor lift) — NOT this one;
    the real fix for an unresolved speaker is the person-search/assign
    flow at `/admin/pipeline/{admin_job_id}` (see
    ``list_review_queue_arguments``'s docstring).

    This is the module's single public commit entry point (see module
    docstring) — recompute_argument_tier never commits; this function
    commits exactly once, as the last statement before refresh+return.
    """
    if action != "confirm":
        raise ValueError(f"unsupported review action: {action!r}")

    result = await db.execute(
        select(ArgumentParticipant).where(ArgumentParticipant.id == participant_id)
    )
    participant = result.scalar_one_or_none()
    if participant is None:
        return None  # router -> 404

    if participant.person_id is None:
        raise ValueError(
            "Cannot confirm a participant whose speaker is unresolved; "
            "resolve the speaker first"
        )

    await db.execute(
        update(ArgumentParticipant)
        .where(ArgumentParticipant.id == participant_id)
        .values(review_state=ReviewState.OPERATOR_CONFIRMED)
        .execution_options(synchronize_session=False)
    )
    await recompute_argument_tier(db, participant.argument_id)
    await db.commit()
    await db.refresh(participant)

    return {
        "id": participant.id,
        "argument_id": participant.argument_id,
        "review_state": participant.review_state.value,
    }
