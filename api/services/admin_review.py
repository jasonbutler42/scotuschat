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

import enum

from sqlalchemy import and_, case, or_, select, update
from sqlalchemy import func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.authority import WriteDecision, decide_write
from api.domain.person_names import normalize_name_part
from api.domain.trust import TrustTier
from api.models.models import (
    AdminJob,
    Argument,
    ArgumentParticipant,
    ArgumentStatusEnum,
    Case,
    CaseArgument,
    ImportMethod,
    ImportSource,
    Person,
    ReviewState,
    ValueDiscrepancy,
)
from api.services.trust import recompute_argument_tier, summarize_tier_blockers

# Four name-part fields route through the shared normalize_name_part
# contract (REVIEW-01/encoding); every other field routes through a
# generic strip-and-blank-to-None normalization.
_NAME_PART_FIELDS = frozenset({"first_name", "middle_name", "last_name", "name_suffix"})


def _stringify(value) -> str | None:
    """Stringify a value for value_discrepancy storage. None stays None;
    an enum member is stored as its `.value`, never its repr."""
    if value is None:
        return None
    if isinstance(value, enum.Enum):
        return value.value
    return str(value)


def _normalize_generic(value) -> str | None:
    """Non-name-part normalization: str(...).strip(), with None/"" (and an
    enum's blank .value) collapsing to None on both sides."""
    if value is None:
        return None
    if isinstance(value, enum.Enum):
        value = value.value
    stripped = str(value).strip()
    return stripped if stripped else None


def _values_differ(field: str, incoming, existing) -> bool:
    """
    The single named home of the REVIEW-01/encoding normalization contract.

    The four name-part fields route through
    `api.domain.person_names.normalize_name_part` on BOTH sides; every
    other field routes through `str(...).strip()` with None/"" collapsing
    to None on both sides. The two normalized values are compared with
    plain Python `==` — case-sensitive, punctuation-preserving, with no
    Unicode NFC folding. A pure-whitespace difference is NOT a
    disagreement; a letter-case difference IS.
    """
    if field in _NAME_PART_FIELDS:
        norm_incoming = normalize_name_part(incoming, field_name=field) if incoming else None
        norm_existing = normalize_name_part(existing, field_name=field) if existing else None
    else:
        norm_incoming = _normalize_generic(incoming)
        norm_existing = _normalize_generic(existing)
    return norm_incoming != norm_existing


async def record_value_discrepancy(
    db: AsyncSession,
    *,
    target_type: str,
    target_id: int,
    field: str,
    import_run_id: int | None,
    incoming_value,
    existing_value,
    incoming_source: str,
    incoming_method: str,
    existing_source: str | None,
    existing_method: str | None,
) -> ValueDiscrepancy:
    """
    Record one open (unresolved) value_discrepancy row. Never commits — the
    caller (a public service entry point) owns the transaction boundary.

    Both values are stringified for storage (Text columns); an enum member
    is stored as its `.value`. Provenance strings are converted to their
    ImportSource/ImportMethod enum members when non-blank, else NULL — the
    column type is the PG enum, not free text, and a blank string (e.g. an
    ArgumentParticipant with source=NULL) is never a valid enum member.
    """
    discrepancy = ValueDiscrepancy(
        target_type=target_type,
        target_id=target_id,
        field=field,
        import_run_id=import_run_id,
        incoming_value=_stringify(incoming_value),
        existing_value=_stringify(existing_value),
        incoming_source=ImportSource(incoming_source) if incoming_source else None,
        incoming_method=ImportMethod(incoming_method) if incoming_method else None,
        existing_source=ImportSource(existing_source) if existing_source else None,
        existing_method=ImportMethod(existing_method) if existing_method else None,
    )
    db.add(discrepancy)
    return discrepancy


async def close_open_discrepancies(db: AsyncSession, *, target_type: str, target_id: int) -> int:
    """
    Close every currently-open value_discrepancy row for one target in ONE
    UPDATE statement — a single shared `resolved_at` timestamp across every
    closed row, so the close order is unobservable (edge REVIEW-04/
    ordering). Never commits.
    """
    result = await db.execute(
        update(ValueDiscrepancy)
        .where(
            ValueDiscrepancy.target_type == target_type,
            ValueDiscrepancy.target_id == target_id,
            ValueDiscrepancy.resolved_at.is_(None),
        )
        .values(resolved_at=sqlfunc.now())
        .execution_options(synchronize_session=False)
    )
    return result.rowcount


async def apply_participant_value_change(
    db: AsyncSession,
    *,
    participant: ArgumentParticipant,
    field: str,
    incoming_value,
    incoming_source: str,
    incoming_method: str,
    import_run_id: int | None = None,
) -> WriteDecision:
    """
    The ONE authority gate for `argument_participants` (D-31/D-31a). Every
    write to a value-bearing column on this table must go through this
    function — no second, ungated write path may survive.

    Reads the stored authority off `participant.review_state.value` plus
    `participant.source`/`.method` (`.value` when present, `""` when NULL —
    the same Pitfall 1 `.value` rule `derive_tier` callers already follow).
    Never commits, never recomputes the trust tier — the caller (a public
    service entry point) owns both.
    """
    existing_value = getattr(participant, field)
    values_differ = _values_differ(field, incoming_value, existing_value)

    existing_source_value = participant.source.value if participant.source else ""
    existing_method_value = participant.method.value if participant.method else ""
    existing_review_state_value = participant.review_state.value

    decision = decide_write(
        incoming_source=incoming_source,
        incoming_method=incoming_method,
        # The incoming write is not itself review-stated — its authority is
        # fully determined by incoming_source (rule 2/3 of authority_rank),
        # so an empty review_state here never changes the outcome.
        incoming_review_state="",
        existing_source=existing_source_value,
        existing_method=existing_method_value,
        existing_review_state=existing_review_state_value,
        values_differ=values_differ,
    )

    if decision in (WriteDecision.ACCEPT, WriteDecision.ACCEPT_AND_RECORD):
        await db.execute(
            update(ArgumentParticipant)
            .where(
                ArgumentParticipant.id == participant.id,
                ArgumentParticipant.argument_id == participant.argument_id,
            )
            .values(**{field: incoming_value})
            .execution_options(synchronize_session=False)
        )

    if decision in (WriteDecision.ACCEPT_AND_RECORD, WriteDecision.REJECT_AND_RECORD):
        await record_value_discrepancy(
            db,
            target_type="argument_participant",
            target_id=participant.id,
            field=field,
            import_run_id=import_run_id,
            incoming_value=incoming_value,
            existing_value=existing_value,
            incoming_source=incoming_source,
            incoming_method=incoming_method,
            existing_source=existing_source_value or None,
            existing_method=existing_method_value or None,
        )

    return decision


async def apply_person_value_change(
    db: AsyncSession,
    *,
    person: Person,
    field: str,
    incoming_value,
    incoming_source: str,
    incoming_method: str,
    import_run_id: int | None = None,
) -> WriteDecision:
    """
    The same authority gate, shaped for `people` (D-31/D-31a). `Person` has
    no `source`/`method` columns at all (D-08's fold left the person-level
    authority record entirely on `review_state`) — so the existing
    provenance passed to `decide_write` is always `("", "")`, and existing
    authority is OPERATOR only when `review_state` is already
    operator_confirmed/operator_edited, else UNKNOWN. `Person` has no
    parent scope, so the scoped-SELECT guard is the primary-key lookup the
    caller already performed. Never commits.
    """
    existing_value = getattr(person, field)
    values_differ = _values_differ(field, incoming_value, existing_value)

    existing_review_state_value = person.review_state.value

    decision = decide_write(
        incoming_source=incoming_source,
        incoming_method=incoming_method,
        incoming_review_state="",
        existing_source="",
        existing_method="",
        existing_review_state=existing_review_state_value,
        values_differ=values_differ,
    )

    if decision in (WriteDecision.ACCEPT, WriteDecision.ACCEPT_AND_RECORD):
        await db.execute(
            update(Person)
            .where(Person.id == person.id)
            .values(**{field: incoming_value})
            .execution_options(synchronize_session=False)
        )

    if decision in (WriteDecision.ACCEPT_AND_RECORD, WriteDecision.REJECT_AND_RECORD):
        await record_value_discrepancy(
            db,
            target_type="person",
            target_id=person.id,
            field=field,
            import_run_id=import_run_id,
            incoming_value=incoming_value,
            existing_value=existing_value,
            incoming_source=incoming_source,
            incoming_method=incoming_method,
            existing_source=None,
            existing_method=None,
        )

    return decision


def _argument_attention_predicate():
    """
    The D-05 OR-composed inclusion predicate for the Arguments tab — a
    single expression covering all four legs, never combined afterward
    from separate per-leg queries, so an argument satisfying more than
    one leg at once still appears exactly once:
      1. a constituent's review_state == NEEDS_REVIEW
      2. a constituent participant row exists whose person_id IS NULL
         (an *existing* unresolved participant row — deliberately guarded
         by `ArgumentParticipant.id.is_not(None)` so an argument with ZERO
         participant rows is not spuriously matched merely because the
         outer join produces NULL columns for it; that argument still
         surfaces via leg 3 whenever its zero-constituent trust_tier is
         genuinely degraded, per floor_tier's own empty-sequence rule)
      3. the argument's own trust_tier is UNCERTAIN or PROVISIONAL
      4. a constituent participant has an open value_discrepancy row
         (Phase 49 plan 49-06 fix — this leg was missing from the
         original three, even though `_person_attention_predicate` below
         already has its own discrepancy leg and this function's own
         docstring calls that "the same inclusion philosophy at the
         person level." Verified against the live dev DB during D-32's
         walkthrough: an operator-edited, already-resolved participant
         that a lower-authority re-import disagrees with satisfies NONE
         of legs 1-3 — its review_state is operator_edited, not
         needs_review; person_id is NOT NULL; and this single edit does
         not necessarily move the argument's own trust_tier — so the
         exact scenario D-32 exists to surface (equal-or-lower-authority
         disagreement records a discrepancy, operator value survives)
         was invisible in the queue entirely. This is REVIEW-02/REVIEW-04
         must_haves' central claim, not a peripheral case.)

    Factored out (plan 49-05) so list_review_queue_arguments and
    get_review_queue_stats share the IDENTICAL expression — the dashboard
    card's count and the screen's own list can never disagree (D-30).
    """
    unresolved_participant_leg = and_(
        ArgumentParticipant.id.is_not(None),
        ArgumentParticipant.person_id.is_(None),
    )
    needs_review_leg = ArgumentParticipant.review_state == ReviewState.NEEDS_REVIEW
    degraded_tier_leg = Argument.trust_tier.in_(
        [TrustTier.UNCERTAIN, TrustTier.PROVISIONAL]
    )
    discrepant_participant_ids_subq = (
        select(ValueDiscrepancy.target_id)
        .where(
            ValueDiscrepancy.target_type == "argument_participant",
            ValueDiscrepancy.resolved_at.is_(None),
        )
        .distinct()
    )
    discrepant_participant_leg = and_(
        ArgumentParticipant.id.is_not(None),
        ArgumentParticipant.id.in_(discrepant_participant_ids_subq),
    )
    return or_(
        needs_review_leg,
        unresolved_participant_leg,
        degraded_tier_leg,
        discrepant_participant_leg,
    )


def _person_attention_predicate():
    """
    The People-tab inclusion predicate: review_state IN (needs_review,
    unreviewed) OR an open value_discrepancy row exists for this person.
    Factored out (plan 49-05) for the same reason as
    _argument_attention_predicate above — shared verbatim between
    list_review_queue_people and get_review_queue_stats.
    """
    discrepant_person_ids_subq = (
        select(ValueDiscrepancy.target_id)
        .where(
            ValueDiscrepancy.target_type == "person",
            ValueDiscrepancy.resolved_at.is_(None),
        )
        .distinct()
    )
    return or_(
        Person.review_state.in_([ReviewState.NEEDS_REVIEW, ReviewState.UNREVIEWED]),
        Person.id.in_(discrepant_person_ids_subq),
    )


def _person_provenance_note(metadata: dict | None) -> str:
    """
    Render `Person.provenance_metadata` as a short, plain-text note for the
    People-tab "Provenance note" column.

    Plan 49-05's action text specifies the format `"{Source} · {method}"`,
    but `Person` has no `method` field anywhere in its
    `provenance_metadata` JSONB shape — verified against every writer:
    `pipeline/commands/import_convokit.py`,
    `pipeline/commands/import_justices_csv.py`, and
    `alembic/versions/0022_person_name_authority.py`'s legacy backfill all
    write exactly `{source, raw, confidence, reason, auto_applied}`, never
    `method` (that field exists only on `ArgumentParticipant`, which DOES
    have `source`/`method` columns — Person's D-08 fold deliberately left
    person-level authority entirely on `review_state` instead). `confidence`
    (a short, controlled "High"/"Medium"/"Low" vocabulary) is the closest
    verified analog to a compact second field; `reason` is a full sentence
    and is not used here. Source wins over spec prose — same precedent as
    this plan's own `<planner_decisions>` for the StatCard grid and the
    Edit deep-link target.
    """
    metadata = metadata or {}
    source = metadata.get("source")
    confidence = metadata.get("confidence")
    if not source and not confidence:
        return "—"
    source_display = source.replace("_", " ").title() if source else None
    if source_display and confidence:
        return f"{source_display} · {confidence}"
    return source_display or confidence


async def list_review_queue_arguments(
    db: AsyncSession,
    *,
    status: str | None = None,
    tier: str | None = None,
    review_state: str | None = None,
) -> list[dict]:
    """Return every argument needing operator attention, one dict per argument.

    D-05 inclusion is `_argument_attention_predicate()` above (unaffected
    by the filters below — filters narrow WITHIN the attention-worthy set,
    they do not widen it).

    Filters (D-07) — each an allow-list dict mirroring
    `api/services/admin_people.py::missing_filters`'s named-predicate-dict
    idiom: an unrecognised value applies NO additional filter, matching
    `list_arguments`'/`list_people`'s established "invalid/unrecognized
    value produces no filter" convention.
      - `status`: candidate/draft/published/unpublished — deliberately
        wider than `list_arguments`' three-value allow-list (D-07/D-28);
        the two allow-lists are independent and `list_arguments` is
        untouched by this plan.
      - `tier`: uncertain/provisional/trusted/verified.
      - `review_state`: unreviewed/needs_review/operator_confirmed/
        operator_edited — narrows to arguments HAVING AT LEAST ONE
        constituent in that exact state (a correlated `IN` over argument
        ids, not a row-level `WHERE`, so an argument's OTHER flagged
        constituents — flagged via a different leg — are still returned
        once the argument itself qualifies).

    Sort (D-03, plan 49-05), in this exact key order:
      1. published-but-degraded floats to the very top: 0 when
         `status == PUBLISHED` AND `trust_tier IN (UNCERTAIN, PROVISIONAL)`,
         else 1 — regardless of date or anything else.
      2. tier rank: uncertain=0, provisional=1, trusted=2, verified=3.
      3. `argued_date` ASC, NULLS LAST.
      4. `Argument.id` ASC — the deterministic tie-break. `Argument` has NO
         `created_at` column, and
         `.planning/todos/pending/2026-08-20-reset-to-fixture-stale-created-at-timestamps.md`
         documents that stored timestamps are unreliable on reset
         fixtures anyway (this is exactly what produced Phase 48's
         display-ordering bug) — the primary key is the only safe,
         always-present, monotonic tie-break.
      5/6. `ArgumentParticipant.side` ASC, `ArgumentParticipant.id` ASC —
         UNCHANGED from plan 49-01's tracer feedback gate fix (defect 1):
         pins each constituent's position within its argument's row
         regardless of write order (a just-confirmed row must not jump).

    Unbounded (D-04) — known tension, recorded deliberately: this is the
    one screen guaranteed to be large on a real corpus; paging is
    deliberately deferred.

    Only flagged constituent rows are attached to each argument's
    `constituents` list — a participant row that does not itself satisfy
    leg 1, leg 2, or leg 4 (has an open discrepancy) is not included, even
    when its sibling row on the same argument pulled the argument in via
    leg 3.

    attention_count counts constituents whose review_state == needs_review,
    OR whose person_id IS NULL, OR who carry an open discrepancy.

    Each argument also carries `admin_job_id` — the id of its most
    recently created linked `AdminJob`, or None when the argument has no
    linked job. An argument may legitimately have zero or more than one
    `AdminJob` row; this is a correlated scalar subquery (not a join) so
    picking "most recent by id" never multiplies the outer argument rows
    (tracer feedback gate defect 2b). Used by the frontend to build the
    "Resolve speaker" deep link for an unresolved (person_id IS NULL)
    constituent.

    Each argument also carries `blockers` — the `summarize_tier_blockers`
    breakdown for that argument, so an argument queued solely via the
    degraded-tier leg (zero flagged constituents) has something real to
    show in the expanded panel (49-05 `<planner_decisions>` E5 empty).
    """
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
        .where(_argument_attention_predicate())
    )

    # D-07 filters — allow-list dicts, unrecognised value applies no filter.
    status_filters = {
        "candidate": ArgumentStatusEnum.CANDIDATE,
        "draft": ArgumentStatusEnum.DRAFT,
        "published": ArgumentStatusEnum.PUBLISHED,
        "unpublished": ArgumentStatusEnum.UNPUBLISHED,
    }
    if status in status_filters:
        q = q.where(Argument.status == status_filters[status])

    tier_filters = {
        "uncertain": TrustTier.UNCERTAIN,
        "provisional": TrustTier.PROVISIONAL,
        "trusted": TrustTier.TRUSTED,
        "verified": TrustTier.VERIFIED,
    }
    if tier in tier_filters:
        q = q.where(Argument.trust_tier == tier_filters[tier])

    review_state_filters = {
        "unreviewed": ReviewState.UNREVIEWED,
        "needs_review": ReviewState.NEEDS_REVIEW,
        "operator_confirmed": ReviewState.OPERATOR_CONFIRMED,
        "operator_edited": ReviewState.OPERATOR_EDITED,
    }
    if review_state in review_state_filters:
        matching_argument_ids = select(ArgumentParticipant.argument_id).where(
            ArgumentParticipant.review_state == review_state_filters[review_state]
        )
        q = q.where(Argument.id.in_(matching_argument_ids))

    # D-03/plan 49-05 sort — see docstring for the exact key order and why
    # Argument.id (never created_at, which does not exist on this table)
    # is the deterministic tie-break.
    published_degraded_rank = case(
        (
            and_(
                Argument.status == ArgumentStatusEnum.PUBLISHED,
                Argument.trust_tier.in_([TrustTier.UNCERTAIN, TrustTier.PROVISIONAL]),
            ),
            0,
        ),
        else_=1,
    )
    tier_rank = case(
        (Argument.trust_tier == TrustTier.UNCERTAIN, 0),
        (Argument.trust_tier == TrustTier.PROVISIONAL, 1),
        (Argument.trust_tier == TrustTier.TRUSTED, 2),
        (Argument.trust_tier == TrustTier.VERIFIED, 3),
        else_=4,
    )

    q = q.order_by(
        published_degraded_rank,
        tier_rank,
        Argument.argued_date.asc().nulls_last(),
        Argument.id.asc(),
        ArgumentParticipant.side.asc(),
        ArgumentParticipant.id.asc(),
    )
    rows = (await db.execute(q)).all()

    # Pre-fetch the set of participant ids carrying an open discrepancy
    # (Phase 49 plan 49-06 fix) — a constituent must be listed whenever it
    # has one, mirroring _argument_attention_predicate's new leg 4 above.
    # Fetched once, before the row loop, rather than per-row.
    discrepant_participant_ids: set[int] = set(
        (
            await db.execute(
                select(ValueDiscrepancy.target_id).where(
                    ValueDiscrepancy.target_type == "argument_participant",
                    ValueDiscrepancy.resolved_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )

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
            row.review_state == ReviewState.NEEDS_REVIEW
            or row.person_id is None
            or row.participant_id in discrepant_participant_ids
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
                "discrepancies": [],
            }
        )

    # Attach each constituent's open discrepancies (plan 49-04) — one query
    # over every flagged participant id already collected above, never a
    # per-row query. Ordered by id ASC (edge REVIEW-04/ordering) for a
    # stable, repeatable render regardless of the close order.
    all_participant_ids = [
        constituent["participant_id"]
        for arg in arguments.values()
        for constituent in arg["constituents"]
    ]
    discrepancies_by_participant: dict[int, list[dict]] = {}
    if all_participant_ids:
        disc_rows = (
            await db.execute(
                select(ValueDiscrepancy)
                .where(
                    ValueDiscrepancy.target_type == "argument_participant",
                    ValueDiscrepancy.target_id.in_(all_participant_ids),
                    ValueDiscrepancy.resolved_at.is_(None),
                )
                .order_by(ValueDiscrepancy.id.asc())
            )
        ).scalars().all()
        for d in disc_rows:
            discrepancies_by_participant.setdefault(d.target_id, []).append(
                {
                    "id": d.id,
                    "field": d.field,
                    "existing_value": d.existing_value,
                    "existing_source": d.existing_source.value if d.existing_source else None,
                    "existing_method": d.existing_method.value if d.existing_method else None,
                    "incoming_value": d.incoming_value,
                    "incoming_source": d.incoming_source.value if d.incoming_source else None,
                    "incoming_method": d.incoming_method.value if d.incoming_method else None,
                    "created_at": d.created_at.isoformat(),
                }
            )

    items: list[dict] = []
    for arg_id in order:
        arg = arguments[arg_id]
        for constituent in arg["constituents"]:
            open_discs = discrepancies_by_participant.get(constituent["participant_id"], [])
            constituent["discrepancies"] = open_discs
            constituent["has_open_discrepancy"] = len(open_discs) > 0
        arg["attention_count"] = len(arg["constituents"])
        arg["blockers"] = await summarize_tier_blockers(db, arg_id)
        items.append(arg)
    return items


async def list_review_queue_people(db: AsyncSession, *, review_state: str | None = None) -> list[dict]:
    """
    Return every Person needing operator attention (D-02's People tab).

    D-05-style inclusion is `_person_attention_predicate()` above:
    `review_state IN (needs_review, unreviewed)` OR having an open
    `value_discrepancy` row — matching `list_review_queue_arguments`'s
    inclusion philosophy at the person level. Unbounded (D-04).

    `review_state` (D-07) is an optional allow-list filter narrowing
    WITHIN that inclusion set — an unrecognised value applies no filter,
    same convention as the Arguments query.

    Sort (plan 49-05): a CASE ranking needs_review=0, unreviewed=1,
    everything else=2 (matches the People tab's own Screen Contract, since
    a Person can carry any of the four review_state values even though
    only needs_review/unreviewed drive base inclusion), then `full_name`
    ASC, then `people.id` ASC — the deterministic tie-break (mirrors the
    Arguments query's own reasoning for why a primary key, not a
    timestamp, is the safe tie-break).
    """
    q = select(Person).where(_person_attention_predicate())

    review_state_filters = {
        "unreviewed": ReviewState.UNREVIEWED,
        "needs_review": ReviewState.NEEDS_REVIEW,
        "operator_confirmed": ReviewState.OPERATOR_CONFIRMED,
        "operator_edited": ReviewState.OPERATOR_EDITED,
    }
    if review_state in review_state_filters:
        q = q.where(Person.review_state == review_state_filters[review_state])

    review_state_rank = case(
        (Person.review_state == ReviewState.NEEDS_REVIEW, 0),
        (Person.review_state == ReviewState.UNREVIEWED, 1),
        else_=2,
    )
    q = q.order_by(review_state_rank, Person.full_name.asc(), Person.id.asc())
    people = (await db.execute(q)).scalars().all()
    if not people:
        return []

    person_ids = [p.id for p in people]
    disc_rows = (
        await db.execute(
            select(ValueDiscrepancy)
            .where(
                ValueDiscrepancy.target_type == "person",
                ValueDiscrepancy.target_id.in_(person_ids),
                ValueDiscrepancy.resolved_at.is_(None),
            )
            .order_by(ValueDiscrepancy.id.asc())
        )
    ).scalars().all()
    discrepancies_by_person: dict[int, list[dict]] = {}
    for d in disc_rows:
        discrepancies_by_person.setdefault(d.target_id, []).append(
            {
                "id": d.id,
                "field": d.field,
                "existing_value": d.existing_value,
                "existing_source": d.existing_source.value if d.existing_source else None,
                "existing_method": d.existing_method.value if d.existing_method else None,
                "incoming_value": d.incoming_value,
                "incoming_source": d.incoming_source.value if d.incoming_source else None,
                "incoming_method": d.incoming_method.value if d.incoming_method else None,
                "created_at": d.created_at.isoformat(),
            }
        )

    items: list[dict] = []
    for person in people:
        open_discs = discrepancies_by_person.get(person.id, [])
        items.append(
            {
                "id": person.id,
                "full_name": person.full_name,
                "review_state": person.review_state.value,
                "provenance_note": _person_provenance_note(person.provenance_metadata),
                "has_open_discrepancy": len(open_discs) > 0,
                "discrepancies": open_discs,
            }
        )
    return items


async def get_review_queue_stats(db: AsyncSession) -> dict:
    """
    Summary counts for the dashboard StatCard (D-30) — `{"arguments": int,
    "people": int, "total": int}`, derived from two dedicated COUNT
    queries that reuse the EXACT SAME inclusion predicates as
    `list_review_queue_arguments`/`list_review_queue_people`
    (`_argument_attention_predicate`/`_person_attention_predicate`), never
    by fetching either unbounded list just to produce a number — D-04's
    unbounded lean makes that expensive, and sharing the predicate is what
    guarantees the card's count and the screen's own list can never
    disagree.
    """
    arguments_count_q = (
        select(sqlfunc.count(sqlfunc.distinct(Argument.id)))
        .select_from(Argument)
        .join(CaseArgument, CaseArgument.argument_id == Argument.id)
        .outerjoin(ArgumentParticipant, ArgumentParticipant.argument_id == Argument.id)
        .where(CaseArgument.is_lead == True)  # noqa: E712
        .where(_argument_attention_predicate())
    )
    arguments_count = (await db.execute(arguments_count_q)).scalar_one()

    people_count_q = (
        select(sqlfunc.count(sqlfunc.distinct(Person.id)))
        .select_from(Person)
        .where(_person_attention_predicate())
    )
    people_count = (await db.execute(people_count_q)).scalar_one()

    return {
        "arguments": arguments_count,
        "people": people_count,
        "total": arguments_count + people_count,
    }


async def resolve_participant_review(
    db: AsyncSession, participant_id: int, action: str
) -> dict | None:
    """Advance one participant's review_state and recompute the argument's tier.

    Scoped select-then-update (T-49-idor) — a missing participant_id
    returns None (router -> 404), never a silent no-op.

    Three actions (plan 49-04; "edit" is a deep link, D-23, not a fourth
    action here — see api/schemas/admin_review.py::ReviewActionRequest):

      - "confirm": advances review_state to OPERATOR_CONFIRMED on an
        already-resolved participant (person_id IS NOT NULL). Raises a
        tagged ValueError("unresolved_requires_unattributable") when
        person_id IS NULL (tracer feedback gate defect 2a) — an ordinary
        confirm never lifts the D-11 unresolved-speaker floor as a side
        effect (D-17); the real fix for an unresolved speaker is either
        the person-search/assign flow at `/admin/pipeline/{admin_job_id}`
        or "confirm_unattributable" below.
      - "confirm_unattributable": advances review_state to
        OPERATOR_CONFIRMED on an UNRESOLVED participant (person_id IS
        NULL) — the operator's explicit judgment that no further speaker
        resolution is possible. Raises a tagged
        ValueError("participant_is_resolved") when person_id IS NOT NULL
        (this is not the action for an already-resolved row). Lifts the
        D-11 floor via api.services.trust._load_constituents' D-17
        qualification.
      - "reflag": sets review_state back to NEEDS_REVIEW on an
        operator_confirmed or operator_edited row. Raises a tagged
        ValueError("row_not_yet_reviewed") when the row is still
        UNREVIEWED — reflag is the only backward transition (D-25); no
        action here ever writes UNREVIEWED.

    Every action closes this participant's open discrepancies (D-15: same
    transaction as the state advance and the trust recompute — one shared
    resolved_at across every closed row, see close_open_discrepancies) and
    recomputes the argument's tier before this function's single commit
    (the module's one public commit entry point — see module docstring).
    """
    result = await db.execute(
        select(ArgumentParticipant).where(ArgumentParticipant.id == participant_id)
    )
    participant = result.scalar_one_or_none()
    if participant is None:
        return None  # router -> 404

    if action == "confirm":
        if participant.person_id is None:
            raise ValueError("unresolved_requires_unattributable")
        new_review_state = ReviewState.OPERATOR_CONFIRMED
    elif action == "confirm_unattributable":
        if participant.person_id is not None:
            raise ValueError("participant_is_resolved")
        new_review_state = ReviewState.OPERATOR_CONFIRMED
    elif action == "reflag":
        if participant.review_state == ReviewState.UNREVIEWED:
            raise ValueError("row_not_yet_reviewed")
        new_review_state = ReviewState.NEEDS_REVIEW
    else:
        raise ValueError(f"unsupported review action: {action!r}")

    # D-25: no action above ever assigns ReviewState.UNREVIEWED — the only
    # backward transition is reflag, which lands on NEEDS_REVIEW.
    await db.execute(
        update(ArgumentParticipant)
        .where(ArgumentParticipant.id == participant_id)
        .values(review_state=new_review_state)
        .execution_options(synchronize_session=False)
    )
    await close_open_discrepancies(db, target_type="argument_participant", target_id=participant_id)
    await recompute_argument_tier(db, participant.argument_id)
    await db.commit()
    await db.refresh(participant)

    return {
        "id": participant.id,
        "argument_id": participant.argument_id,
        "review_state": participant.review_state.value,
    }


async def resolve_person_review(db: AsyncSession, person_id: int, action: str) -> dict | None:
    """Advance one Person's review_state (D-02's People-tab resolve action).

    Same shape as resolve_participant_review, minus
    "confirm_unattributable" (D-17 is an ArgumentParticipant-only concept —
    a bare Person has no unattributable state) and minus any recompute
    call (Phase 48 D-10's no-fan-out rule: a person-level review never
    reaches an argument's trust floor).

    Scoped select-then-update (T-49-idor) — a missing person_id returns
    None (router -> 404).
    """
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if person is None:
        return None  # router -> 404

    if action == "confirm":
        new_review_state = ReviewState.OPERATOR_CONFIRMED
    elif action == "reflag":
        if person.review_state == ReviewState.UNREVIEWED:
            raise ValueError("row_not_yet_reviewed")
        new_review_state = ReviewState.NEEDS_REVIEW
    elif action == "confirm_unattributable":
        raise ValueError("confirm_unattributable_not_applicable_to_person")
    else:
        raise ValueError(f"unsupported review action: {action!r}")

    # D-25: no action above ever assigns ReviewState.UNREVIEWED.
    await db.execute(
        update(Person)
        .where(Person.id == person_id)
        .values(review_state=new_review_state)
        .execution_options(synchronize_session=False)
    )
    await close_open_discrepancies(db, target_type="person", target_id=person_id)
    await db.commit()
    await db.refresh(person)

    return {
        "id": person.id,
        "review_state": person.review_state.value,
    }
