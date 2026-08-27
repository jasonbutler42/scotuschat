"""
Business logic for admin argument management.

Responsibilities:
  - Directory listing of all arguments with lead case metadata (D-01)
  - Argument detail query with consolidated dockets (D-10)
  - Argument update with slug re-derivation and freeze-on-publish (D-11)
  - Slug and docket collision detection before write (T-11-SLUG, T-11-DOCKET)
  - Publish / Unpublish with resolved_at pre-condition guard (D-07, T-11-PUBGATE)

Critical guards (project-wide pattern from admin_jobs.py):
  - EVERY update() statement includes .execution_options(synchronize_session=False)
  - Date strings parsed with datetime.date.fromisoformat() (V5 Input Validation)
  - Alembic is sole DDL authority (CLAUDE.md) — no direct schema creation calls
  - _derive_slug imported from pipeline.commands.ingest (single source of truth;
    same cross-layer import precedent as admin_jobs.py → pipeline.commands.resolve)
"""

import datetime

from sqlalchemy import and_, delete, exists, func as sqlfunc, not_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from api.models.models import (
    AdminJob,
    Argument,
    ArgumentParticipant,
    ArgumentStatusEnum,
    ArgumentStatusLog,
    Case,
    CaseArgument,
    CourtTenure,
    ImportMethod,
    ImportRun,
    ImportSource,
    Person,
    ReviewState,
    SideEnum,
    Utterance,
    ValueDiscrepancy,
)
from api.domain.authority import WriteDecision
from api.domain.trust import TrustTier
from api.schemas.admin_arguments import ArgumentUpdate, MetadataUpdate
from api.services.admin_people import _bench_role_and_missing_tenure
from api.services.admin_review import apply_participant_value_change, close_open_discrepancies
from api.services.argument_uniqueness import find_argument_by_pair, is_argument_pair_violation
from api.services.speakers import ADVOCATE_LABEL_MAP
from api.services.trust import (
    TrustGateBlocked,
    recompute_argument_tier,
    summarize_tier_blockers,
)
from pipeline.commands.ingest import _derive_slug  # noqa: F401 — re-exported for tests


class DuplicateArgumentError(ValueError):
    """A concrete final metadata pair belongs to another Argument."""

    def __init__(self, conflicting_argument_id: int, docket: str, question: int):
        super().__init__("duplicate_argument")
        self.conflicting_argument_id = conflicting_argument_id
        self.docket = docket
        self.question = question


async def _stamp_operator_provenance(db: AsyncSession, *, model, row_id: int) -> None:
    """
    Unconditionally stamp source=OPERATOR / method=MANUAL on one `Argument`
    or `Case` row (PD-08, Phase 50 plan 50-03).

    `Argument` and `Case` have no `review_state` column — operator
    authority on their five compare-set columns (argued_date,
    question_number, source_docket, case_name, docket_number) can only be
    read off `source == "operator"` (api.domain.authority.authority_rank
    rule 2). This helper is the ONLY place that makes the ladder's
    `operator` rung reachable on these two tables. Deliberately scoped to
    `Argument`/`Case` ONLY — do NOT call this for `ArgumentParticipant` or
    `Person`, whose operator authority is carried by `review_state`
    instead (D-22, Phase 49); stamping source/method there would be a
    second, disagreeing authority mechanism on tables that already have
    one.

    Unconditional — no "if row.source is None" guard, unlike the
    participant backfill precedent at
    api/services/admin_jobs.py:1017-1018 (`resolve_participant_review`).
    These columns describe where the CURRENT value came from, not where
    the value originally came from (the same reasoning D-07, Phase 50,
    gives for the reconcile restamp) — an operator who edits a field a
    second time restamps it a second time.

    Never commits — the caller's own commit covers this write. Uses
    .execution_options(synchronize_session=False) (project-wide critical
    guard, Pitfall 5).
    """
    await db.execute(
        update(model)
        .where(model.id == row_id)
        .values(source=ImportSource.OPERATOR, method=ImportMethod.MANUAL)
        .execution_options(synchronize_session=False)
    )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


async def list_arguments(db: AsyncSession, status: str | None = None) -> list[dict]:
    """Return all Argument rows joined to their lead Case, sorted by argued_date DESC.

    One dict per argument with keys: id, argued_date, case_name, docket_number,
    resolved_at, published_at, status, trust_tier (Phase 48 plan 10 — admin-only,
    consumed only by the /api/admin/arguments router).

    Only joins where CaseArgument.is_lead == True so the result is one row per
    argument regardless of how many consolidated dockets the argument has.

    status (DASH-02, D-05/D-06) is an optional single-value filter narrowing
    the list to one of "draft"/"published"/"unpublished" (the exact
    ArgumentStatusEnum.value strings). It is validated against an allow-list
    of those three values BEFORE ever being passed to ArgumentStatusEnum() —
    any unrecognized value (including "candidate", the born state as of
    Phase 48 D-01 — never a selectable filter, ALIST-02/D-04) or None applies
    no additional filter and the full DRAFT+PUBLISHED+UNPUBLISHED list is
    returned, matching list_people's established "invalid/unrecognized value
    produces no filter" convention.
    """
    q = (
        select(
            Argument.id,
            Argument.argued_date,
            Argument.resolved_at,
            Argument.published_at,
            Argument.status,
            Argument.trust_tier,
            Case.case_name,
            Case.docket_number,
        )
        .join(CaseArgument, CaseArgument.argument_id == Argument.id)
        .join(Case, CaseArgument.case_id == Case.id)
        .where(CaseArgument.is_lead == True)  # noqa: E712
        # D-02: exclude candidate-state arguments from admin list (Pitfall 7);
        # ALIST-02/Phase 48 D-04: DRAFT, PUBLISHED, and UNPUBLISHED are all
        # surfaced — only CANDIDATE-status arguments (the born state as of
        # Phase 48 D-01) are hidden. Candidate visibility is Phase 49's
        # review queue, not this list.
        .where(
            Argument.status.in_(
                [
                    ArgumentStatusEnum.DRAFT,
                    ArgumentStatusEnum.PUBLISHED,
                    ArgumentStatusEnum.UNPUBLISHED,
                ]
            )
        )
    )

    valid_status_values = {
        ArgumentStatusEnum.DRAFT.value,
        ArgumentStatusEnum.PUBLISHED.value,
        ArgumentStatusEnum.UNPUBLISHED.value,
    }
    if status in valid_status_values:
        q = q.where(Argument.status == ArgumentStatusEnum(status))

    q = q.order_by(Argument.argued_date.desc())
    result = await db.execute(q)
    rows = result.all()
    return [
        {
            "id": row.id,
            "argued_date": row.argued_date,
            "case_name": row.case_name,
            "docket_number": row.docket_number,
            "resolved_at": row.resolved_at,
            "published_at": row.published_at,
            "status": row.status,
            "trust_tier": row.trust_tier,
        }
        for row in rows
    ]


async def get_argument_stats(db: AsyncSession) -> dict:
    """Aggregate stat-card counts for the Arguments card (DASH-01).

    One grouped COUNT query keyed on Argument.status, restricted to
    DRAFT/PUBLISHED/UNPUBLISHED (ALIST-02 parity — CANDIDATE-status rows,
    the born state as of Phase 48 D-01, are excluded from total, matching
    list_arguments' existing status filter). Missing statuses default to 0
    (e.g. an empty table returns all zeros).
    """
    q = (
        select(Argument.status, sqlfunc.count())
        .where(
            Argument.status.in_(
                [
                    ArgumentStatusEnum.DRAFT,
                    ArgumentStatusEnum.PUBLISHED,
                    ArgumentStatusEnum.UNPUBLISHED,
                ]
            )
        )
        .group_by(Argument.status)
    )
    result = await db.execute(q)
    counts_by_status = dict(result.all())

    published = counts_by_status.get(ArgumentStatusEnum.PUBLISHED, 0)
    draft = counts_by_status.get(ArgumentStatusEnum.DRAFT, 0)
    unpublished = counts_by_status.get(ArgumentStatusEnum.UNPUBLISHED, 0)
    return {
        "total": published + draft + unpublished,
        "published": published,
        "draft": draft,
        "unpublished": unpublished,
    }


async def get_recent_drafts(db: AsyncSession, limit: int = 5) -> list[dict]:
    """Top-``limit`` most recently created DRAFT arguments (DASH-03, Needs Attention).

    Ordered by Argument.id DESC (Pitfall 3 — Argument has no created_at column;
    resolved_at is not a reliable proxy for insertion order). D-03: no age
    threshold — every DRAFT argument is eligible regardless of age. D-01: caps
    at ``limit`` (default 5).
    """
    q = (
        select(Argument.id, Case.case_name, Case.docket_number)
        .join(CaseArgument, CaseArgument.argument_id == Argument.id)
        .join(Case, CaseArgument.case_id == Case.id)
        .where(
            CaseArgument.is_lead == True,  # noqa: E712
            Argument.status == ArgumentStatusEnum.DRAFT,
        )
        .order_by(Argument.id.desc())
        .limit(limit)
    )
    result = await db.execute(q)
    rows = result.all()
    return [
        {"id": row.id, "case_name": row.case_name, "docket_number": row.docket_number}
        for row in rows
    ]


async def get_utterance_count(db: AsyncSession) -> int:
    """Total count of every Utterance row, regardless of parent argument status (DASH-01, A3).

    Counts utterances under PIPELINE/DRAFT/PUBLISHED/UNPUBLISHED arguments alike —
    this is a raw table-wide count, not scoped to the admin-visible argument set.
    """
    result = await db.execute(select(sqlfunc.count()).select_from(Utterance))
    return result.scalar_one()


async def list_argument_speakers(db: AsyncSession, argument_id: int) -> list[dict]:
    """Return a unified bench+advocate speaker row per ArgumentParticipant (D-05).

    Mirrors admin_people.list_resolve_rows_for_job's per-participant row-building
    shape (advocate vs. bench branching, tenure prefetch avoiding N+1), but keyed
    on argument_id directly rather than job_id — this helper backs the argument
    edit page's Speakers section (Phase 26 Plan 04), not the pipeline-job Resolve
    card.

    Bench rows: bench_role/argument_role and missing_tenure come from
    _bench_role_and_missing_tenure against a CourtTenure date-window lookup
    (descriptor/descriptor_hint always None — Descriptor is advocate-only,
    PJOB-15 precedent). An unresolved bench row (person_id IS NULL) reports
    missing_tenure=False — there is no person to flag as missing tenure data,
    mirroring list_resolve_rows_for_job's identical unresolved-row handling.

    Advocate rows: argument_role from ADVOCATE_LABEL_MAP; descriptor and
    descriptor_hint both source ArgumentParticipant.descriptor (D-06 — no
    separate stored "originally extracted" snapshot exists for advocate
    descriptor).

    utterance_count is computed via ONE grouped query over Utterance rows scoped
    to this argument (T-26-07 — avoids an N+1 per-participant count query).

    Returns [] if the argument does not exist.
    """
    arg_result = await db.execute(select(Argument).where(Argument.id == argument_id))
    argument = arg_result.scalar_one_or_none()
    if argument is None:
        return []

    participants_result = await db.execute(
        select(ArgumentParticipant, Person.full_name)
        .outerjoin(Person, ArgumentParticipant.person_id == Person.id)
        .where(ArgumentParticipant.argument_id == argument_id)
        .order_by(ArgumentParticipant.id.asc())
    )
    participant_rows = participants_result.all()

    # Pre-fetch tenures for every BENCH person_id in one query (avoids N+1).
    bench_person_ids = [
        p.person_id
        for p, _full_name in participant_rows
        if p.side == SideEnum.BENCH and p.person_id is not None
    ]
    tenures_by_person: dict[int, list[CourtTenure]] = {}
    if bench_person_ids:
        tenures_result = await db.execute(
            select(CourtTenure).where(CourtTenure.person_id.in_(bench_person_ids))
        )
        for t in tenures_result.scalars().all():
            tenures_by_person.setdefault(t.person_id, []).append(t)

    # Compute utterance counts in ONE grouped query (T-26-07 — no per-row count).
    counts_result = await db.execute(
        select(Utterance.person_id, sqlfunc.count())
        .where(
            Utterance.argument_id == argument_id,
            Utterance.person_id.isnot(None),
        )
        .group_by(Utterance.person_id)
    )
    utterance_counts: dict[int, int] = {row[0]: row[1] for row in counts_result.all()}

    rows: list[dict] = []
    for participant, full_name in participant_rows:
        utterance_count = (
            utterance_counts.get(participant.person_id, 0)
            if participant.person_id is not None
            else 0
        )
        if participant.side == SideEnum.BENCH:
            bench_role, missing_tenure = (
                _bench_role_and_missing_tenure(
                    tenures_by_person.get(participant.person_id, []),
                    argument.argued_date,
                )
                if participant.person_id is not None
                else (None, False)
            )
            person_edit_href = (
                f"/admin/people/{participant.person_id}"
                if missing_tenure and participant.person_id is not None
                else None
            )
            rows.append(
                {
                    "participant_id": participant.id,
                    "person_id": participant.person_id,
                    "full_name": full_name,
                    "side": participant.side.value,
                    "is_bench": True,
                    "argument_role": bench_role,
                    "descriptor": None,
                    "descriptor_hint": None,
                    "utterance_count": utterance_count,
                    "bench_role": bench_role,
                    "missing_tenure": missing_tenure,
                    "person_edit_href": person_edit_href,
                }
            )
        else:
            rows.append(
                {
                    "participant_id": participant.id,
                    "person_id": participant.person_id,
                    "full_name": full_name,
                    "side": participant.side.value,
                    "is_bench": False,
                    "argument_role": ADVOCATE_LABEL_MAP.get(participant.side),
                    "descriptor": participant.descriptor,
                    "descriptor_hint": participant.descriptor,
                    "utterance_count": utterance_count,
                    "bench_role": None,
                    "missing_tenure": False,
                    "person_edit_href": None,
                }
            )
    return rows


async def get_argument_detail(db: AsyncSession, argument_id: int) -> dict | None:
    """Return full argument data including consolidated dockets.

    Returns None if the argument does not exist (router → 404 IDOR guard T-11-IDOR).
    consolidated_dockets: list of {docket_number} for non-lead cases on the same argument.
    """
    # Load the argument row
    arg_result = await db.execute(
        select(Argument).where(Argument.id == argument_id)
    )
    argument = arg_result.scalar_one_or_none()
    if argument is None:
        return None

    # Load lead case via CaseArgument.is_lead == True
    lead_result = await db.execute(
        select(Case)
        .join(CaseArgument, CaseArgument.case_id == Case.id)
        .where(
            CaseArgument.argument_id == argument_id,
            CaseArgument.is_lead == True,  # noqa: E712
        )
    )
    lead_case = lead_result.scalar_one_or_none()
    if lead_case is None:
        # Argument exists but has no lead case — data integrity issue; return partial
        return None

    # Load consolidated (non-lead) dockets
    consolidated_result = await db.execute(
        select(Case.docket_number)
        .join(CaseArgument, CaseArgument.case_id == Case.id)
        .where(
            CaseArgument.argument_id == argument_id,
            CaseArgument.is_lead == False,  # noqa: E712
        )
        .order_by(Case.docket_number)
    )
    consolidated_rows = consolidated_result.all()

    # Compute tenure gap warnings (D-15): bench participants whose argued_date
    # is not covered by any of their CourtTenure rows.
    tenure_gap_warnings: list[dict] = []
    if argument.argued_date is not None:
        bench_result = await db.execute(
            select(ArgumentParticipant.person_id, Person.full_name)
            .join(Person, Person.id == ArgumentParticipant.person_id)
            .where(
                ArgumentParticipant.argument_id == argument_id,
                ArgumentParticipant.side == SideEnum.BENCH,
                ArgumentParticipant.person_id.isnot(None),
            )
        )
        bench_rows = bench_result.all()

        for person_id, full_name in bench_rows:
            # Check if any CourtTenure covers the argued_date for this person
            covering = exists(
                select(CourtTenure.id).where(
                    and_(
                        CourtTenure.person_id == person_id,
                        CourtTenure.start_date <= argument.argued_date,
                        or_(
                            CourtTenure.end_date.is_(None),
                            CourtTenure.end_date >= argument.argued_date,
                        ),
                    )
                )
            )
            has_covering = (await db.execute(select(covering))).scalar()
            if not has_covering:
                tenure_gap_warnings.append(
                    {
                        "person_id": person_id,
                        "full_name": full_name,
                        "argued_date": str(argument.argued_date),
                    }
                )

    # Load resolved advocate participants (D-12): non-BENCH ArgumentParticipant rows
    # where person_id IS NOT NULL (unresolved participants cannot be role-assigned).
    advocate_result = await db.execute(
        select(
            ArgumentParticipant.id,
            ArgumentParticipant.person_id,
            ArgumentParticipant.side,
            Person.full_name,
        )
        .join(Person, Person.id == ArgumentParticipant.person_id)
        .where(
            ArgumentParticipant.argument_id == argument_id,
            ArgumentParticipant.side != SideEnum.BENCH,
            ArgumentParticipant.person_id.isnot(None),
        )
        .order_by(Person.full_name)
    )
    advocate_rows = advocate_result.all()
    participants = [
        {
            "participant_id": row.id,
            "person_id": row.person_id,
            "full_name": row.full_name,
            "side": row.side.value if row.side else SideEnum.UNKNOWN.value,
        }
        for row in advocate_rows
    ]

    # Load the full status log, oldest first (T-26-03 — Status history list).
    #
    # Phase 48 finding (48-09-EVIDENCE.md Finding 2): `id` must be the
    # PRIMARY sort key for an append-only audit trail, not `created_at`.
    # `created_at` uses `server_default=func.now()`, and PostgreSQL's
    # `now()` returns the enclosing TRANSACTION's start time, not
    # per-statement wall-clock time. Any writer that batches more than one
    # status-log INSERT into a single transaction that was opened earlier
    # by an unrelated read (e.g. `reset_to_fixture`'s long-lived
    # verification-loop session) can produce a `created_at` value that is
    # *older* than a row inserted before it. `id` is monotonic by
    # construction (auto-increment primary key) and is unaffected by
    # transaction timing, so it is the only key that reliably preserves
    # insertion order for this table.
    status_log_result = await db.execute(
        select(ArgumentStatusLog)
        .where(ArgumentStatusLog.argument_id == argument_id)
        .order_by(ArgumentStatusLog.id.asc())
    )
    status_log = [
        {
            "status": row.status,
            "created_at": row.created_at,
            "override_reason": row.override_reason,  # Phase 48 D-15/D-20
            "trust_tier_at_transition": row.trust_tier_at_transition,  # Phase 48 D-15/D-20
        }
        for row in status_log_result.scalars().all()
    ]

    # Unified bench+advocate speakers list (D-05, replaces participants +
    # tenure_gap_warnings for the rebuilt edit page — both retained above for
    # backward compatibility).
    speakers = await list_argument_speakers(db, argument_id)

    return {
        "id": argument.id,
        "argued_date": argument.argued_date,
        "case_name": lead_case.case_name,
        "docket_number": lead_case.docket_number,
        "slug": lead_case.slug,
        "resolved_at": argument.resolved_at,
        "published_at": argument.published_at,
        "status": argument.status,
        "trust_tier": argument.trust_tier,  # Phase 48 D-20 — admin-only, never public
        "consolidated_dockets": [
            {"docket_number": row.docket_number} for row in consolidated_rows
        ],
        "tenure_gap_warnings": tenure_gap_warnings,
        "participants": participants,
        "source_docket": argument.source_docket,          # Phase 19 D-01
        "source_dockets": argument.source_dockets or [],  # Phase 23 D-MULTI-DOCKET
        "cover_metadata": argument.cover_metadata,        # Phase 19 D-07
        "question_number": argument.question_number,  # Phase 23 PJOB-07
        "status_log": status_log,                          # Phase 26 D-05
        "speakers": speakers,                              # Phase 26 D-05
    }


async def update_argument(
    db: AsyncSession, argument_id: int, body: ArgumentUpdate
) -> dict | None:
    """Update an argument's argued_date and its lead case's case_name / docket_number.

    Returns None if the argument does not exist (router → 404 IDOR guard T-11-IDOR).

    Published guard (D-35, D-35a, operator, 2026-08-24): raises ValueError when
    the owning argument's status is PUBLISHED. D-35a is the operator's
    whole-argument answer to the scope question D-35's first half (plan
    49-09) left open in deferred-items.md — "lock everything," not just
    participant data. The predicate is published-only, so CANDIDATE, DRAFT,
    and UNPUBLISHED all remain editable. The check runs immediately after
    step 1's load, BEFORE step 2's lead-Case load, so a refusal performs no
    further work and leaves no attribute assignments on the session. This
    supersedes the pre-existing partial treatment below, in which this
    function froze only the slug on a published argument while
    argued_date, case_name, and docket_number all stayed writable on live
    public data — that gap is what this guard closes.

    Slug logic (D-11, ALIST-01):
      - When body.case_name is provided AND argument.status == DRAFT:
        re-derive slug from new case_name and write to lead_case.slug.
        Pre-write collision check: if another Case has the same slug, raise
        ValueError("slug_collision") → router returns 422 (T-11-SLUG).
      - When argument.status is UNPUBLISHED: slug is frozen — only
        lead_case.case_name is updated; lead_case.slug is NOT touched
        (Pitfall 3). The PUBLISHED half of this branch is now unreachable —
        the published guard above raises before this logic ever runs for a
        published argument; the UNPUBLISHED case remains live and this
        sentence stays true for it.

    Docket collision (T-11-DOCKET):
      - If body.docket_number differs from current and another Case already has
        that docket_number, raise ValueError("docket_collision") → 422.

    Date validation (T-11-VALID):
      - body.argued_date is parsed with datetime.date.fromisoformat(); a malformed
        ISO string raises ValueError with a descriptive message → 422.

    EVERY update() statement uses .execution_options(synchronize_session=False)
    (Pitfall 5 — project-wide critical guard).
    """
    # 1. Load argument row
    arg_result = await db.execute(
        select(Argument).where(Argument.id == argument_id)
    )
    argument = arg_result.scalar_one_or_none()
    if argument is None:
        return None
    if argument.status == ArgumentStatusEnum.PUBLISHED:
        raise ValueError(
            f"Argument {argument.id} is published (current status: "
            f"{argument.status.value!r}); the argument's data is read-only "
            "once it has been published (D-35/D-35a, operator, 2026-08-24)."
        )

    # 2. Load lead case
    lead_result = await db.execute(
        select(Case)
        .join(CaseArgument, CaseArgument.case_id == Case.id)
        .where(
            CaseArgument.argument_id == argument_id,
            CaseArgument.is_lead == True,  # noqa: E712
        )
    )
    lead_case = lead_result.scalar_one_or_none()
    if lead_case is None:
        raise ValueError("No lead case found for this argument")

    # 3. Apply argued_date (T-11-VALID)
    case_provenance_dirty = False
    if body.argued_date is not None:
        try:
            argument.argued_date = datetime.date.fromisoformat(body.argued_date)
        except ValueError:
            raise ValueError("invalid_date_format")
        # PD-08: stamp operator provenance on the argument row's own write
        # (Phase 50 plan 50-03) — the only way authority_rank can ever
        # read this column as OPERATOR (Argument has no review_state).
        await _stamp_operator_provenance(db, model=Argument, row_id=argument.id)

    # 4. Apply docket_number with collision check (T-11-DOCKET)
    if body.docket_number is not None:
        new_docket = body.docket_number
        if new_docket != lead_case.docket_number:
            collision = await db.execute(
                select(Case).where(
                    Case.docket_number == new_docket,
                    Case.id != lead_case.id,
                )
            )
            if collision.scalar_one_or_none() is not None:
                raise ValueError("docket_collision")
            lead_case.docket_number = new_docket
            # docket_number_norm: same normalization as ingest (strip leading zeros, etc.)
            # The norm column is a project field — keep it consistent with ingest.
            # ingest.py does not export a normalizer for docket_number_norm, so we
            # set it to the same stripped value (operator-entered dockets are already
            # in canonical form; the norm column is used for duplicate detection at
            # ingest time, not for display).
            lead_case.docket_number_norm = new_docket
            case_provenance_dirty = True

    # 5. Apply case_name with slug logic (D-11, Pitfall 2, Pitfall 3)
    if body.case_name is not None:
        lead_case.case_name = body.case_name
        case_provenance_dirty = True
        if argument.status == ArgumentStatusEnum.DRAFT:
            # DRAFT: re-derive slug from new case_name
            new_slug = _derive_slug(lead_case.case_name)
            # Pre-write collision check (T-11-SLUG)
            slug_collision = await db.execute(
                select(Case).where(
                    Case.slug == new_slug,
                    Case.id != lead_case.id,
                )
            )
            if slug_collision.scalar_one_or_none() is not None:
                raise ValueError("slug_collision")
            lead_case.slug = new_slug
        # else: PUBLISHED or UNPUBLISHED — slug is frozen; only case_name
        # display updates (Pitfall 3, ALIST-01)

    # PD-08: stamp operator provenance on the lead Case row — a case-only
    # edit (case_name and/or docket_number) touches ONLY the Case row's
    # provenance, never the Argument row's (Phase 50 plan 50-03).
    if case_provenance_dirty:
        await _stamp_operator_provenance(db, model=Case, row_id=lead_case.id)

    await db.commit()
    return await get_argument_detail(db, argument_id)


async def approve_argument(db: AsyncSession, argument_id: int) -> dict | None:
    """Transition an argument from CANDIDATE to DRAFT (Phase 50, D-14).

    This is the argument-scoped peer of `api.services.admin_jobs.approve_job`
    (PATTERNS.md rates that function an exact analog) with the job legs
    removed — no `AdminJob` is read, written, or required. `approve_job`
    remains the PDF path's job-scoped wrapper; this function is what a
    corpus argument (which never has an `AdminJob` as of this phase, D-14/
    D-19) calls instead. `reset_to_fixture` calls this function directly
    for its Draft/Published fixtures (replacing its two `approve_job`
    calls).

    This is the ONLY writer of `resolved_at` for a jobless corpus argument
    — without it, `publish_argument`'s non-overridable `resolved_at IS
    NULL` refusal would make such an argument permanently unpublishable.

    Sets `status = DRAFT` and `resolved_at = now()`.

    Returns None if the argument does not exist (router → 404 T-11-IDOR
    precedent — never trust a client-supplied id without a matching row).
    Raises ValueError naming the argument's current status when it is not
    CANDIDATE (the same double-approve guard `approve_job` enforces).

    Writes one ArgumentStatusLog row (status=DRAFT) — the "Created"
    transition record (D-08 precedent) — in the same transaction as the
    Argument update.

    Recomputes and stores arguments.trust_tier in the same transaction,
    before this function's own commit (D-07, 48-RESEARCH.md Pitfall 2).

    Uses .execution_options(synchronize_session=False) (project-wide
    critical guard, Pitfall 5).
    """
    result = await db.execute(select(Argument).where(Argument.id == argument_id))
    argument = result.scalar_one_or_none()
    if argument is None:
        return None

    if argument.status != ArgumentStatusEnum.CANDIDATE:
        raise ValueError(
            f"Argument is already in '{argument.status.value}' state; cannot approve again."
        )

    await db.execute(
        update(Argument)
        .where(Argument.id == argument_id)
        .values(status=ArgumentStatusEnum.DRAFT, resolved_at=sqlfunc.now())
        .execution_options(synchronize_session=False)
    )
    db.add(ArgumentStatusLog(argument_id=argument_id, status=ArgumentStatusEnum.DRAFT))
    # D-07: not itself a constituent change, but every writer recomputes
    # (48-RESEARCH.md writer #4) — one bounded per-argument query guarantees
    # the tier is truthful the moment the argument becomes operator-visible.
    await recompute_argument_tier(db, argument_id)
    await db.commit()
    # Phase 31 fix: the bulk update() above uses synchronize_session=False,
    # so the already-loaded `argument` object never syncs to the new status
    # in this session's identity map. Refresh it before the caller's own
    # re-read (same db.refresh() precedent unpublish_argument/publish_
    # argument already use after their own bulk updates).
    await db.refresh(argument)
    return await get_argument_detail(db, argument_id)


async def publish_argument(
    db: AsyncSession, argument_id: int, override_reason: str | None = None
) -> dict | None:
    """Stamp published_at = now() and status = PUBLISHED, making the argument
    publicly visible. Re-publish from UNPUBLISHED is allowed (D-02 / AEDIT-08).

    Two distinct gates, evaluated in this order (Phase 48 D-14):
      1. `resolved_at IS NULL` — a non-overridable completeness precondition
         (T-11-PUBGATE, Pitfall 1). An argument whose resolve step never ran
         is incomplete, not a trust judgment call; `override_reason` is never
         consulted before this guard.
      2. Already-PUBLISHED — unchanged, non-overridable.
      3. The trust gate: the tier is recomputed fresh (so the gate reads the
         row's current constituents, never a possibly stale stored value) and,
         if it is `TrustTier.UNCERTAIN`, publishing is blocked unless a
         non-blank `override_reason` is supplied. This is the only overridable
         gate. The override authorizes exactly this publish attempt — it is
         never sticky (D-16): an unpublish then republish while still
         UNCERTAIN is blocked again and requires a fresh reason.

    A blank/whitespace-only `override_reason` (after `.strip()`) is rejected
    server-side with a distinct tagged `ValueError("blank_override_reason")`
    — this check is authoritative regardless of what the UI does (D-17); a
    disabled client button is defense-in-depth only.

    Returns None if the argument does not exist (router → 404 T-11-IDOR).
    Raises ValueError("Cannot publish: resolve step not yet complete") if
    resolved_at IS NULL.
    Raises ValueError("Already published") if already published.
    Raises TrustGateBlocked (api.services.trust) if the tier is UNCERTAIN and
    no reason (or only a None) was supplied — carries the tier and the
    blocker breakdown (D-19/D-20) for the caller to render "why blocked".
    Raises ValueError("blank_override_reason") if a reason was supplied but
    is empty after stripping.

    Writes one ArgumentStatusLog row (status=PUBLISHED) in the same
    transaction as the Argument update (T-26-03 — audit trail, D-09). When
    the trust gate was overridden, that row also carries the stripped
    `override_reason` and the `trust_tier_at_transition` (D-15); a normal,
    non-blocked publish leaves both of those columns NULL — the override
    path is not accidentally mandatory (D-16 edge).

    Uses .execution_options(synchronize_session=False) (Pitfall 5).
    """
    result = await db.execute(
        select(Argument).where(Argument.id == argument_id)
    )
    argument = result.scalar_one_or_none()
    if argument is None:
        return None

    # D-07 / T-11-PUBGATE: backend must enforce this independently of the UI.
    # D-14: this gate is non-overridable — evaluated before override_reason
    # is ever consulted.
    if argument.resolved_at is None:
        raise ValueError("Cannot publish: resolve step not yet complete")
    # D-02: guard keys on status (not published_at) so re-publish from
    # UNPUBLISHED succeeds; only an already-PUBLISHED argument is rejected.
    if argument.status == ArgumentStatusEnum.PUBLISHED:
        raise ValueError("Already published")

    # Phase 48 D-14/D-20: recompute before judging, so the trust gate reads a
    # tier consistent with the row's current constituents (writer row 7).
    current_tier = await recompute_argument_tier(db, argument_id)
    override_reason_to_log: str | None = None
    tier_at_transition: TrustTier | None = None
    if current_tier is TrustTier.UNCERTAIN:
        reason = (override_reason or "").strip()
        if not reason:
            if override_reason is not None:
                # A reason was supplied but was blank/whitespace-only — a
                # distinguishable failure from "no reason was given at all"
                # (D-17 flagged assumption), so the operator sees their
                # submission did not count rather than a silently re-shown
                # block.
                raise ValueError("blank_override_reason")
            blockers = await summarize_tier_blockers(db, argument_id)
            raise TrustGateBlocked(current_tier, blockers)
        # D-16: the override authorizes exactly this publish attempt; nothing
        # persistent is written to carry it forward to a future attempt.
        override_reason_to_log = reason
        tier_at_transition = current_tier
    # else: the tier is not UNCERTAIN — override_reason (if any) is simply
    # unused; the log row's override columns stay NULL (D-16 edge case).

    await db.execute(
        update(Argument)
        .where(Argument.id == argument_id)
        .values(status=ArgumentStatusEnum.PUBLISHED, published_at=sqlfunc.now())
        .execution_options(synchronize_session=False)
    )
    db.add(
        ArgumentStatusLog(
            argument_id=argument_id,
            status=ArgumentStatusEnum.PUBLISHED,
            override_reason=override_reason_to_log,
            trust_tier_at_transition=tier_at_transition,
        )
    )
    await db.commit()
    # Phase 31 fix: the bulk update() above uses synchronize_session=False, so
    # the `argument` object already loaded into this session's identity map
    # (via the select() at the top of this function) is never synced to the
    # new column values. get_argument_detail()'s own select() for the same
    # argument_id would otherwise return that same stale in-memory object
    # (status still the pre-publish value) instead of the committed row.
    # Refreshing here fixes it in place for every subsequent read in this
    # session (matches the db.refresh() pattern already used after commit in
    # create_person_for_job / update_resolve_row_for_job).
    await db.refresh(argument)
    return await get_argument_detail(db, argument_id)


async def update_participant_side(
    db: AsyncSession,
    argument_id: int,
    participant_id: int,
    side: SideEnum,
    descriptor: str | None = None,
) -> dict | None:
    """Update argument_participants.side (and optionally descriptor) for a specific
    participant in a specific argument (ROLE-03, Phase 26 D-06).

    IDOR guard (T-15-02-IDOR): the SELECT and UPDATE are both scoped by BOTH
    argument_id AND participant_id — a participant that belongs to a different
    argument will return None → router returns 404.

    Mass-assignment guard (T-26-04): only ``side`` and ``descriptor`` are writable
    via this function.

    T-15-02-BENCH — RETIRED AS SATISFIED, NOT RELAXED (D-35, 2026-08-24, operator,
    Phase 49 gap-closure execution, plan 49-10). This function used to raise
    ValueError when side == BENCH. The threat's real concern was never "bench must
    never be settable" — the Resolve card (api/services/admin_jobs.py::
    update_resolve_row_for_job) has set it every day since Phase 25 — its concern
    was "bench must not be settable WITHOUT THE RECONCILIATION the Resolve card
    performs." Under D-35 ("converge both surfaces") that concern is met at this
    call site by four compensating controls, so the guard is OBSOLETE rather than
    relaxed:
      1. An explicit two-step confirmation on the calling surface before a
         boundary crossing (the argument-detail Speakers card, plan 49-10 Task 3) —
         serving the same purpose as ResolveCard.svelte's needsSideGate/confirmSide.
      2. No fabricated bench role: the read path derives bench_role from a
         CourtTenure date-window lookup with NO fallback
         (_bench_role_and_missing_tenure, D-15) and reports "Missing tenure"
         otherwise — a reclassified advocate cannot acquire a Justice title by
         being reclassified; it acquires a visible warning.
      3. No silent carry of a mismatched person link: the same read path turns a
         non-Justice person on a bench row into the Missing-tenure affordance plus
         a link to the person editor — RESOLVE-09's disjoint-pool concern answered
         by the read path, because this surface has no person picker to clear.
      4. The published lock below (D-35's first half, plan 49-09) — the strongest
         control: a reclassification from this surface can never mutate live
         public data.
    Still in force under this same threat id: the unresolved-side rejection below
    and the two-field (side/descriptor) mass-assignment boundary. Honest boundary
    of this argument: the retirement is strictly stronger on published data and
    deliberately permissive on unpublished data — that is the authority D-35
    grants the operator, not a claim that it is stronger everywhere.

    Unresolved-side guard (T-26-14, CLAUDE.md no-silent-inference constraint):
    raises ValueError when side == UNKNOWN or the legacy side == ADVOCATE —
    an advocate's side must be authoritatively resolved to PETITIONER,
    RESPONDENT, or AMICUS before it can be persisted. This is the backend's
    authoritative rejection; the edit-page UI additionally disables Save while
    the row is unresolved as defense-in-depth.

    descriptor is written ONLY when the caller passes a non-None value AND side
    is not BENCH — omitting descriptor (or setting side to BENCH) leaves the
    existing ArgumentParticipant.descriptor unchanged (does not clobber it),
    mirroring the "only write provided fields" pattern used by
    update_argument_metadata. RESOLVE-13 (copied from update_resolve_row_for_job,
    api/services/admin_jobs.py): a BENCH write never touches the descriptor
    column at all — the stored value is preserved, not overwritten with null, and
    a client-supplied bench descriptor is ignored rather than written. This is
    what makes the advocate -> bench -> advocate round trip lossless: the read
    path reports a bench row's descriptor as null (RESOLVE-13's "hidden, not
    shown, not cleared"), so a naive write on the way back out would otherwise
    submit an empty string and clobber the value this guard protects.

    Published guard (D-35, D-31a): raises ValueError when the owning argument's
    status is PUBLISHED — participant data is read-only once an argument has
    been published. The predicate is published-only (CANDIDATE, DRAFT, and
    UNPUBLISHED all remain editable), matching the folded todo `2026-08-21-
    widen-participant-editability-to-all-unpublished-states`, which is what
    this function's sibling `update_resolve_row_for_job`
    (api/services/admin_jobs.py) already implements. This function deliberately
    mirrors that writer so the two participant-value writers read identically
    on the published question — D-31a itself recorded that this writer had
    "no status guard today." The check runs before the participant SELECT and
    therefore before either `apply_participant_value_change` call below,
    because that call records a `value_discrepancy` as part of deciding a
    write (D-16) — a refusal placed after it would leave a discrepancy row and
    a `review_state` advance behind for a write that never happened.

    Returns:
        dict with ``id``, ``side``, and ``descriptor`` on success.
        None if the participant does not exist under this argument_id (→ 404).
    """
    # Pure-input guard (T-26-14) — validates the incoming `side` value alone
    # and must raise before the session is ever touched
    # (test_update_participant_side_rejects_unresolved_side calls this
    # function with a sentinel `None` session to prove exactly that). The
    # sibling BENCH guard (T-15-02-BENCH) that used to sit here is retired —
    # see the docstring above.
    if side in (SideEnum.UNKNOWN, SideEnum.ADVOCATE):
        raise ValueError(
            "An advocate's side must be resolved to Petitioner, Respondent, or Amicus"
        )

    argument_result = await db.execute(
        select(Argument).where(Argument.id == argument_id)
    )
    argument = argument_result.scalar_one_or_none()
    if argument is None:
        return None  # router → 404, same as a missing participant
    if argument.status == ArgumentStatusEnum.PUBLISHED:
        raise ValueError(
            f"Argument {argument.id} is published (current status: "
            f"{argument.status.value!r}); participant data is read-only once "
            "an argument has been published (Phase 49 folded todo: "
            "2026-08-21-widen-participant-editability-to-all-unpublished-states)."
        )

    result = await db.execute(
        select(ArgumentParticipant).where(
            ArgumentParticipant.id == participant_id,
            ArgumentParticipant.argument_id == argument_id,
        )
    )
    participant = result.scalar_one_or_none()
    if participant is None:
        return None  # router → 404

    # Phase 49 (D-31/D-31a): every value write to this table routes through
    # the ONE authority-gated writer — no second, ungated write path
    # survives. incoming_source/incoming_method are always "operator"/
    # "manual" here: this function is an operator-facing edit path.
    side_decision = await apply_participant_value_change(
        db,
        participant=participant,
        field="side",
        incoming_value=side,
        incoming_source="operator",
        incoming_method="manual",
    )
    descriptor_decision: WriteDecision | None = None
    # RESOLVE-13 (copied from api/services/admin_jobs.py::
    # update_resolve_row_for_job): the descriptor gate is applied ONLY when
    # the side is not BENCH, so a BENCH write never touches that column at
    # all — the stored value is preserved, not overwritten with null, and a
    # client-supplied bench descriptor is ignored rather than written.
    if descriptor is not None and side != SideEnum.BENCH:
        descriptor_decision = await apply_participant_value_change(
            db,
            participant=participant,
            field="descriptor",
            incoming_value=descriptor,
            incoming_source="operator",
            incoming_method="manual",
        )

    # An operator write through this path is an edit (D-11's rule applied
    # to participants) — advance review_state to OPERATOR_EDITED. Per D-22,
    # source/method are NOT written: the row keeps its original provenance,
    # and its operator authority is carried entirely by review_state.
    await db.execute(
        update(ArgumentParticipant)
        .where(
            ArgumentParticipant.id == participant_id,
            ArgumentParticipant.argument_id == argument_id,
        )
        .values(review_state=ReviewState.OPERATOR_EDITED)
        .execution_options(synchronize_session=False)
    )
    await close_open_discrepancies(db, target_type="argument_participant", target_id=participant_id)
    # Phase 48 D-10/48-RESEARCH.md Open Question 1: side/descriptor do not
    # feed the tier derivation under D-10's current scope, but recompute is
    # called anyway — Phase 49 adds `review_state` to this exact
    # ArgumentParticipant row, and this call site is where that signal will
    # first become live.
    await recompute_argument_tier(db, argument_id)
    await db.commit()

    # persisted_descriptor must not claim a write that did not happen: on a
    # BENCH write the descriptor gate above is never reached, so the return
    # value reports the row's EXISTING (unchanged) descriptor rather than an
    # ignored incoming one (RESOLVE-13).
    persisted_descriptor = (
        descriptor if descriptor is not None and side != SideEnum.BENCH else participant.descriptor
    )
    return {
        "id": participant_id,
        "side": side.value,
        "descriptor": persisted_descriptor,
        "write_decision": side_decision.value,
        "descriptor_write_decision": descriptor_decision.value if descriptor_decision else None,
    }


async def unpublish_argument(db: AsyncSession, argument_id: int) -> dict | None:
    """Set status = UNPUBLISHED on an argument, hiding it from the public site.

    published_at is intentionally LEFT UNCHANGED (D-02) so the Status card can
    still show the argument's most recent publish date.

    Returns None if the argument does not exist (router → 404 T-11-IDOR).
    Raises ValueError if the argument is not currently published (guard keys
    on status, not published_at).

    Writes one ArgumentStatusLog row (status=UNPUBLISHED) in the same
    transaction as the Argument update (T-26-03 — audit trail, D-09).

    Uses .execution_options(synchronize_session=False) (Pitfall 5).
    """
    result = await db.execute(
        select(Argument).where(Argument.id == argument_id)
    )
    argument = result.scalar_one_or_none()
    if argument is None:
        return None

    if argument.status != ArgumentStatusEnum.PUBLISHED:
        raise ValueError("Not currently published")

    await db.execute(
        update(Argument)
        .where(Argument.id == argument_id)
        .values(status=ArgumentStatusEnum.UNPUBLISHED)
        .execution_options(synchronize_session=False)
    )
    db.add(ArgumentStatusLog(argument_id=argument_id, status=ArgumentStatusEnum.UNPUBLISHED))
    # Phase 48 D-08: the tier stays live after unpublish too — recompute here
    # so the stored value never goes stale, though nothing about unpublishing
    # itself changes the tier's inputs.
    await recompute_argument_tier(db, argument_id)
    await db.commit()
    # Phase 31 fix: same stale-identity-map issue as publish_argument above —
    # refresh the already-loaded `argument` object so get_argument_detail()'s
    # re-select in this same session reflects the committed UNPUBLISHED status.
    await db.refresh(argument)
    return await get_argument_detail(db, argument_id)


async def check_duplicate_argument(db: AsyncSession, docket: str, question: int) -> dict:
    """Check if an argument with (source_docket, question_number) already exists.

    Returns dict with keys 'exists' (bool) and 'argument_id' (int | None).
    Called by the JS preflight endpoint (D-04, Phase 19).

    No 404 — absence of a match is a valid 200 response.
    Uses parameterized query (T-19-03-03: no string interpolation, SQLAlchemy bind params).
    """
    row = await find_argument_by_pair(db, docket, question)
    return {"exists": row is not None, "argument_id": row}


async def delete_argument(db: AsyncSession, argument_id: int) -> bool | None:
    """Delete an argument and all dependent data (ADMIN-01, D-25/PD-11, Phase 50).

    Returns True on success, False when the current status is PUBLISHED
    (→ router 409), None if argument not found (→ router 404).

    Deletable in every state except published (D-25/PD-11): CANDIDATE,
    DRAFT, and UNPUBLISHED all delete. Delete is the strongest edit there
    is, so this is D-35a's published-only doctrine (Phase 49) applied
    consistently to the delete gate — the most useful shape under a
    reseed-heavy workflow. The prior gate blocked CANDIDATE on the theory
    that an active AdminJob might still reference it; that reasoning no
    longer holds — corpus arguments carry no AdminJob at all as of this
    phase (D-14/D-19), and a PDF job's argument_id is NULLed by cascade
    step 7 below regardless of the argument's status.

    FK-ordered cascade (no ORM relationship cascades exist — manual only):
      1. value_discrepancy rows scoped to this argument, its lead case
         (ONLY when no OTHER argument also leads that case — Case is
         shared, so its discrepancy rows are not this argument's to
         delete otherwise), and its participants (D-26) — MUST run before
         ImportRun rows are deleted: value_discrepancy.import_run_id is a
         hard FK to import_run.id (migration 0028). The participant leg
         is captured BEFORE step 4 deletes those rows, because
         value_discrepancy.target_id is a SOFT reference with no FK to
         catch the orphan otherwise. target_type == "person" rows are
         NEVER touched — a Person is shared across every argument they
         appear in, and deleting a person-scoped discrepancy here would
         destroy another argument's review item.
      1b. Any SURVIVING value_discrepancy row whose import_run_id still
          points at one of THIS argument's own ImportRun rows has that
          reference NULLed (import_run_id is nullable) — a person-scoped
          or other-argument-participant-scoped row can legitimately be
          attributed to this argument's own import/reconcile run.
      2. Utterances (references both import_run.id AND arguments.id — must go first)
      3. ImportRuns (references arguments.id — after utterances)
      4. ArgumentParticipants (references arguments.id)
      5. CaseArguments (references arguments.id)
      6. ArgumentStatusLog (the argument_status_log table; references
         arguments.id, NOT NULL FK with no ondelete — Phase 48 D-22: every
         argument carries at least one status-log row from birth (D-03),
         so this step is required, not defensive; PostgreSQL applies
         RESTRICT without it)
      7. AdminJob.argument_id NULLed (FK nullable, no ondelete — Pitfall 1: RESTRICT default)
      8. Argument (last — all children cleared)

    All delete() and update() statements use .execution_options(synchronize_session=False)
    (Pitfall 3 — project-wide critical guard for async SQLAlchemy).

    Critical ordering note (Pitfall 2): Utterance.import_run_id FK references
    import_run.id — deleting import_run rows before utterances raises ForeignKeyViolation.
    Utterances MUST be deleted before import_run rows.

    Client disabled state is defense-in-depth only; this server-side gate is
    authoritative.
    """
    result = await db.execute(select(Argument).where(Argument.id == argument_id))
    argument = result.scalar_one_or_none()
    if argument is None:
        return None
    # D-25/PD-11: delete gate is a single positive condition keyed on
    # status == PUBLISHED — every OTHER status (CANDIDATE, DRAFT,
    # UNPUBLISHED, and the retired PIPELINE value) is deletable.
    if argument.status == ArgumentStatusEnum.PUBLISHED:
        return False

    # Step 1 (D-26): delete value_discrepancy rows scoped to this argument,
    # captured BEFORE any of their referenced rows (participants, the
    # argument itself) are deleted below — see the docstring's three-scope
    # breakdown.
    participant_ids_result = await db.execute(
        select(ArgumentParticipant.id).where(ArgumentParticipant.argument_id == argument_id)
    )
    participant_ids = [row[0] for row in participant_ids_result.all()]

    lead_case_ids_result = await db.execute(
        select(CaseArgument.case_id).where(
            CaseArgument.argument_id == argument_id,
            CaseArgument.is_lead == True,  # noqa: E712
        )
    )
    lead_case_ids = [row[0] for row in lead_case_ids_result.all()]
    exclusive_lead_case_ids: list[int] = []
    for case_id in lead_case_ids:
        other_lead_result = await db.execute(
            select(CaseArgument.argument_id).where(
                CaseArgument.case_id == case_id,
                CaseArgument.is_lead == True,  # noqa: E712
                CaseArgument.argument_id != argument_id,
            )
        )
        if other_lead_result.first() is None:
            exclusive_lead_case_ids.append(case_id)

    discrepancy_scope_conditions = [
        and_(ValueDiscrepancy.target_type == "argument", ValueDiscrepancy.target_id == argument_id),
    ]
    if exclusive_lead_case_ids:
        discrepancy_scope_conditions.append(
            and_(
                ValueDiscrepancy.target_type == "case",
                ValueDiscrepancy.target_id.in_(exclusive_lead_case_ids),
            )
        )
    if participant_ids:
        discrepancy_scope_conditions.append(
            and_(
                ValueDiscrepancy.target_type == "argument_participant",
                ValueDiscrepancy.target_id.in_(participant_ids),
            )
        )
    await db.execute(
        delete(ValueDiscrepancy)
        .where(or_(*discrepancy_scope_conditions))
        .execution_options(synchronize_session=False)
    )
    # Step 1b (D-26 follow-up): a SURVIVING value_discrepancy row (e.g.
    # target_type="person", or a different argument's participant) can
    # still reference one of THIS argument's own ImportRun rows as its
    # import_run_id — Person is shared and a discrepancy on it can be
    # attributed to any argument's reconcile/resolve pass, including this
    # one. Every row this cascade should delete was already removed in
    # step 1 above; anything still referencing one of this argument's
    # import_run ids at this point is, by construction, a row that must
    # NOT be deleted. import_run_id is a nullable FK
    # (mirrors the AdminJob.argument_id NULL-out precedent in step 7
    # below) — clear the reference rather than let ImportRun deletion in
    # step 3 raise ForeignKeyViolation against a row this function must
    # preserve.
    own_import_run_ids_result = await db.execute(
        select(ImportRun.id).where(ImportRun.argument_id == argument_id)
    )
    own_import_run_ids = [row[0] for row in own_import_run_ids_result.all()]
    if own_import_run_ids:
        await db.execute(
            update(ValueDiscrepancy)
            .where(ValueDiscrepancy.import_run_id.in_(own_import_run_ids))
            .values(import_run_id=None)
            .execution_options(synchronize_session=False)
        )
    # Step 2: Delete utterances referencing this argument (must be before import_run rows)
    await db.execute(
        delete(Utterance)
        .where(Utterance.argument_id == argument_id)
        .execution_options(synchronize_session=False)
    )
    # Step 3: Delete import_run rows for this argument (after utterances)
    await db.execute(
        delete(ImportRun)
        .where(ImportRun.argument_id == argument_id)
        .execution_options(synchronize_session=False)
    )
    # Step 4: Delete argument_participants
    await db.execute(
        delete(ArgumentParticipant)
        .where(ArgumentParticipant.argument_id == argument_id)
        .execution_options(synchronize_session=False)
    )
    # Step 5: Delete case_arguments join rows
    await db.execute(
        delete(CaseArgument)
        .where(CaseArgument.argument_id == argument_id)
        .execution_options(synchronize_session=False)
    )
    # Step 6: Delete argument_status_log rows — FK is NOT NULL with no ondelete
    # clause, so PostgreSQL applies RESTRICT (Phase 48 D-22). Every argument
    # carries at least one status-log row from birth (D-03), so this step is
    # required for every delete, not a defensive edge case.
    await db.execute(
        delete(ArgumentStatusLog)
        .where(ArgumentStatusLog.argument_id == argument_id)
        .execution_options(synchronize_session=False)
    )
    # Step 7: NULL out AdminJob.argument_id — FK is nullable but has no ondelete clause;
    # PostgreSQL default RESTRICT will raise ForeignKeyViolation if not NULLed first (Pitfall 1)
    await db.execute(
        update(AdminJob)
        .where(AdminJob.argument_id == argument_id)
        .values(argument_id=None)
        .execution_options(synchronize_session=False)
    )
    # Step 8: Delete the argument itself
    await db.execute(
        delete(Argument)
        .where(Argument.id == argument_id)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return True


async def update_argument_metadata(
    db: AsyncSession, argument_id: int, body: MetadataUpdate
) -> bool:
    """Update Argument.argued_date, Argument.source_docket, and lead Case.case_name
    from the job detail metadata card (D-15, Phase 19).

    Returns False if argument_id not found (router converts to 404 — T-19-03-02).

    Mass-assignment guard (T-19-03-01): ONLY argued_date, source_docket on Argument
    and case_name on the lead Case are writable via this function.

    Published guard (D-35, D-35a, operator, 2026-08-24): raises ValueError when
    the owning argument's status is PUBLISHED. This function had NO status
    check at any layer before D-35a — not the service, not the router, not
    the SvelteKit action — and it writes argued_date, source_docket,
    source_dockets, question_number, and the lead Case.case_name, all of
    which are live public data on a published argument. The predicate is
    published-only (CANDIDATE, DRAFT, and UNPUBLISHED all remain editable).
    The check deliberately reuses the row loaded at step a immediately
    below — never a second SELECT of the Argument row — so this
    function's db.execute call sequence is unchanged (three
    AsyncMock-driven tests in test_admin_arguments_service.py depend on
    that exact sequence).

    Critical: every UPDATE statement uses .execution_options(synchronize_session=False)
    (Pitfall 5 — project-wide critical guard).
    """
    # a. Fetch Argument by id
    result = await db.execute(
        select(Argument).where(Argument.id == argument_id)
    )
    argument = result.scalar_one_or_none()
    if argument is None:
        return False
    if argument.status == ArgumentStatusEnum.PUBLISHED:
        raise ValueError(
            f"Argument {argument.id} is published (current status: "
            f"{argument.status.value!r}); the argument's data is read-only "
            "once it has been published (D-35/D-35a, operator, 2026-08-24)."
        )

    # b. Parse argued_date from ISO string if provided
    parsed_date: datetime.date | None = None
    if body.argued_date:
        try:
            parsed_date = datetime.date.fromisoformat(body.argued_date)
        except ValueError:
            raise ValueError("invalid_date_format")

    # c. Update Argument row — only write fields that were explicitly provided.
    # WR-01: always writing source_docket=body.source_docket would NULL an existing
    # docket when the operator saves the form with that field left blank.
    # Distinguish "field omitted from the request" (model_fields_set) from "field
    # present but empty/null" — the latter is an explicit clear and must write NULL,
    # not silently no-op (WR-01, 30.1-REVIEW.md).
    values_to_set: dict = {}
    if "argued_date" in body.model_fields_set:
        values_to_set["argued_date"] = parsed_date
    if body.source_dockets is not None:
        # The schema supplies the canonical trimmed, de-duplicated non-empty list.
        values_to_set["source_dockets"] = body.source_dockets
        values_to_set["source_docket"] = body.source_dockets[0]
    elif body.source_docket is not None:
        values_to_set["source_docket"] = body.source_docket
    # Phase 23 (PJOB-07 / T-23-02): parse question_number from free-text string.
    # Non-numeric input is silently skipped (never raises 500 per T-23-02) — but an
    # explicitly-cleared value (empty/null) must NULL the column, not no-op (WR-01).
    if "question_number" in body.model_fields_set:
        if body.question_number is not None and body.question_number.strip():
            try:
                values_to_set["question_number"] = int(body.question_number)
            except ValueError:
                pass  # Non-numeric value — skip silently per T-23-02
        else:
            values_to_set["question_number"] = None
    final_docket = values_to_set.get("source_docket", argument.source_docket)
    final_question = values_to_set.get("question_number", argument.question_number)
    conflicting_id = await find_argument_by_pair(
        db, final_docket, final_question, exclude_argument_id=argument_id
    )
    if conflicting_id is not None:
        raise DuplicateArgumentError(conflicting_id, final_docket, final_question)
    if values_to_set:
        await db.execute(
            update(Argument)
            .where(Argument.id == argument_id)
            .values(**values_to_set)
            .execution_options(synchronize_session=False)
        )
        # PD-08: stamp operator provenance on the argument row when
        # question_number or source_docket was written (Phase 50 plan
        # 50-03) — the only way authority_rank can ever read either
        # column as OPERATOR (Argument has no review_state). argued_date
        # is deliberately NOT stamped here — this call site is scoped to
        # exactly the two fields named by this task.
        if "question_number" in values_to_set or "source_docket" in values_to_set:
            await _stamp_operator_provenance(db, model=Argument, row_id=argument_id)

    # d. Update lead Case.case_name if provided
    if body.case_name is not None:
        lead_result = await db.execute(
            select(CaseArgument).where(
                CaseArgument.argument_id == argument_id,
                CaseArgument.is_lead == True,  # noqa: E712
            )
        )
        lead_ca = lead_result.scalar_one_or_none()
        if lead_ca is not None:
            await db.execute(
                update(Case)
                .where(Case.id == lead_ca.case_id)
                .values(case_name=body.case_name)
                .execution_options(synchronize_session=False)
            )
            # PD-08 / G-50-2a: stamp operator provenance on the lead Case,
            # exactly as `update_argument`'s own case_name write does. Both
            # functions are operator-facing routes onto the SAME column, so
            # both must reach the same rung of the ladder. Without this the
            # edit stayed at CORPUS authority (Case has no `review_state`;
            # `source` is the only carrier), and a disagreeing corpus
            # re-import was rejected only by the equal-rank tie rather than
            # by operator authority — with `value_discrepancy` then
            # attributing the operator's own value to `corpus`, which is
            # what /admin/review rendered back to them. Found by the D-09
            # live walkthrough, 2026-08-26.
            await _stamp_operator_provenance(db, model=Case, row_id=lead_ca.case_id)

    try:
        await db.commit()
    except IntegrityError as exc:
        # Preserve the submitted final pair across the router's required rollback;
        # the rolled-back row contains the old values and cannot reconstruct it.
        exc.argument_pair = (final_docket, final_question)
        raise
    return True
