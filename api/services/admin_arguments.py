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

from api.models.models import (
    AdminJob,
    Argument,
    ArgumentParticipant,
    ArgumentStatusEnum,
    Case,
    CaseArgument,
    CourtTenure,
    Person,
    PipelineRun,
    SideEnum,
    Utterance,
)
from api.schemas.admin_arguments import ArgumentUpdate, MetadataUpdate
from pipeline.commands.ingest import _derive_slug  # noqa: F401 — re-exported for tests


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


async def list_arguments(db: AsyncSession) -> list[dict]:
    """Return all Argument rows joined to their lead Case, sorted by argued_date DESC.

    One dict per argument with keys: id, argued_date, case_name, docket_number,
    resolved_at, published_at.

    Only joins where CaseArgument.is_lead == True so the result is one row per
    argument regardless of how many consolidated dockets the argument has.
    """
    q = (
        select(
            Argument.id,
            Argument.argued_date,
            Argument.resolved_at,
            Argument.published_at,
            Argument.status,
            Case.case_name,
            Case.docket_number,
        )
        .join(CaseArgument, CaseArgument.argument_id == Argument.id)
        .join(Case, CaseArgument.case_id == Case.id)
        .where(CaseArgument.is_lead == True)  # noqa: E712
        # D-02: exclude pipeline-state arguments from admin list (Pitfall 7)
        .where(Argument.status.in_([ArgumentStatusEnum.DRAFT, ArgumentStatusEnum.PUBLISHED]))
        .order_by(Argument.argued_date.desc())
    )
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
        }
        for row in rows
    ]


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

    return {
        "id": argument.id,
        "argued_date": argument.argued_date,
        "case_name": lead_case.case_name,
        "docket_number": lead_case.docket_number,
        "slug": lead_case.slug,
        "resolved_at": argument.resolved_at,
        "published_at": argument.published_at,
        "status": argument.status,
        "consolidated_dockets": [
            {"docket_number": row.docket_number} for row in consolidated_rows
        ],
        "tenure_gap_warnings": tenure_gap_warnings,
        "participants": participants,
        "source_docket": argument.source_docket,    # Phase 19 D-01
        "cover_metadata": argument.cover_metadata,  # Phase 19 D-07
        "question_number": argument.question_number,  # Phase 23 PJOB-07
    }


async def update_argument(
    db: AsyncSession, argument_id: int, body: ArgumentUpdate
) -> dict | None:
    """Update an argument's argued_date and its lead case's case_name / docket_number.

    Returns None if the argument does not exist (router → 404 IDOR guard T-11-IDOR).

    Slug logic (D-11):
      - When body.case_name is provided AND argument.published_at IS NULL:
        re-derive slug from new case_name and write to lead_case.slug.
        Pre-write collision check: if another Case has the same slug, raise
        ValueError("slug_collision") → router returns 422 (T-11-SLUG).
      - When argument.published_at IS NOT NULL: slug is frozen — only
        lead_case.case_name is updated; lead_case.slug is NOT touched (Pitfall 3).

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
    if body.argued_date is not None:
        try:
            argument.argued_date = datetime.date.fromisoformat(body.argued_date)
        except ValueError:
            raise ValueError("invalid_date_format")

    # 4. Apply docket_number with collision check (T-11-DOCKET)
    if body.docket_number is not None:
        new_docket = body.docket_number.strip()
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

    # 5. Apply case_name with slug logic (D-11, Pitfall 2, Pitfall 3)
    if body.case_name is not None:
        lead_case.case_name = body.case_name.strip()
        if argument.published_at is None:
            # Unpublished: re-derive slug from new case_name
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
        # else: published — slug is frozen; only case_name display updates (Pitfall 3)

    await db.commit()
    return await get_argument_detail(db, argument_id)


async def publish_argument(db: AsyncSession, argument_id: int) -> dict | None:
    """Stamp published_at = now() on an argument, making it publicly visible.

    Returns None if the argument does not exist (router → 404 T-11-IDOR).
    Raises ValueError if resolved_at IS NULL (publish gate — T-11-PUBGATE, Pitfall 1).
    Raises ValueError if already published.

    Uses .execution_options(synchronize_session=False) (Pitfall 5).
    """
    result = await db.execute(
        select(Argument).where(Argument.id == argument_id)
    )
    argument = result.scalar_one_or_none()
    if argument is None:
        return None

    # D-07 / T-11-PUBGATE: backend must enforce this independently of the UI
    if argument.resolved_at is None:
        raise ValueError("Cannot publish: resolve step not yet complete")
    if argument.published_at is not None:
        raise ValueError("Already published")

    await db.execute(
        update(Argument)
        .where(Argument.id == argument_id)
        .values(published_at=sqlfunc.now())
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return await get_argument_detail(db, argument_id)


async def update_participant_side(
    db: AsyncSession,
    argument_id: int,
    participant_id: int,
    side: SideEnum,
) -> dict | None:
    """Update argument_participants.side for a specific participant in a specific argument.

    IDOR guard (T-15-02-IDOR): the SELECT and UPDATE are both scoped by BOTH
    argument_id AND participant_id — a participant that belongs to a different
    argument will return None → router returns 404.

    Mass-assignment guard (T-15-02-MASS): only ``side`` is writable via this function.

    BENCH guard (T-15-02-BENCH): raises ValueError when side == BENCH — operators
    cannot demote or re-classify bench participants.

    Returns:
        dict with ``id`` and ``side`` on success.
        None if the participant does not exist under this argument_id (→ 404).
    """
    if side == SideEnum.BENCH:
        raise ValueError("BENCH cannot be set via participant side update")

    result = await db.execute(
        select(ArgumentParticipant).where(
            ArgumentParticipant.id == participant_id,
            ArgumentParticipant.argument_id == argument_id,
        )
    )
    participant = result.scalar_one_or_none()
    if participant is None:
        return None  # router → 404

    await db.execute(
        update(ArgumentParticipant)
        .where(
            ArgumentParticipant.id == participant_id,
            ArgumentParticipant.argument_id == argument_id,
        )
        .values(side=side)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return {"id": participant_id, "side": side.value}


async def unpublish_argument(db: AsyncSession, argument_id: int) -> dict | None:
    """Clear published_at on an argument, hiding it from the public site.

    Returns None if the argument does not exist (router → 404 T-11-IDOR).
    Raises ValueError if the argument is not currently published.

    Uses .execution_options(synchronize_session=False) (Pitfall 5).
    """
    result = await db.execute(
        select(Argument).where(Argument.id == argument_id)
    )
    argument = result.scalar_one_or_none()
    if argument is None:
        return None

    if argument.published_at is None:
        raise ValueError("Not currently published")

    await db.execute(
        update(Argument)
        .where(Argument.id == argument_id)
        .values(published_at=None)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return await get_argument_detail(db, argument_id)


async def check_duplicate_argument(db: AsyncSession, docket: str, question: int) -> dict:
    """Check if an argument with (source_docket, question_number) already exists.

    Returns dict with keys 'exists' (bool) and 'argument_id' (int | None).
    Called by the JS preflight endpoint (D-04, Phase 19).

    No 404 — absence of a match is a valid 200 response.
    Uses parameterized query (T-19-03-03: no string interpolation, SQLAlchemy bind params).
    """
    result = await db.execute(
        select(Argument.id).where(
            Argument.source_docket == docket,
            Argument.question_number == question,
        )
    )
    row = result.scalar_one_or_none()
    return {"exists": row is not None, "argument_id": row}


async def delete_argument(db: AsyncSession, argument_id: int) -> bool | None:
    """Delete an argument and all dependent data (ADMIN-01).

    Returns True on success, False if argument is published (→ router 409),
    None if argument not found (→ router 404).

    FK-ordered cascade (no ORM relationship cascades exist — manual only):
      1. Utterances (references both pipeline_runs.id AND arguments.id — must go first)
      2. PipelineRuns (references arguments.id — after utterances)
      3. ArgumentParticipants (references arguments.id)
      4. CaseArguments (references arguments.id)
      5. AdminJob.argument_id NULLed (FK nullable, no ondelete — Pitfall 1: RESTRICT default)
      6. Argument (last — all children cleared)

    All delete() and update() statements use .execution_options(synchronize_session=False)
    (Pitfall 3 — project-wide critical guard for async SQLAlchemy).

    Critical ordering note (Pitfall 2): Utterance.pipeline_run_id FK references
    pipeline_runs.id — deleting pipeline_runs before utterances raises ForeignKeyViolation.
    Utterances MUST be deleted before pipeline_runs.

    Published arguments are blocked server-side (T-21-01-PUB) — client disabled state
    is defense-in-depth only.
    """
    result = await db.execute(select(Argument).where(Argument.id == argument_id))
    argument = result.scalar_one_or_none()
    if argument is None:
        return None
    if argument.published_at is not None:
        return False

    # Step 1: Delete utterances referencing this argument (must be before pipeline_runs)
    await db.execute(
        delete(Utterance)
        .where(Utterance.argument_id == argument_id)
        .execution_options(synchronize_session=False)
    )
    # Step 2: Delete pipeline_run rows for this argument (after utterances)
    await db.execute(
        delete(PipelineRun)
        .where(PipelineRun.argument_id == argument_id)
        .execution_options(synchronize_session=False)
    )
    # Step 3: Delete argument_participants
    await db.execute(
        delete(ArgumentParticipant)
        .where(ArgumentParticipant.argument_id == argument_id)
        .execution_options(synchronize_session=False)
    )
    # Step 4: Delete case_arguments join rows
    await db.execute(
        delete(CaseArgument)
        .where(CaseArgument.argument_id == argument_id)
        .execution_options(synchronize_session=False)
    )
    # Step 5: NULL out AdminJob.argument_id — FK is nullable but has no ondelete clause;
    # PostgreSQL default RESTRICT will raise ForeignKeyViolation if not NULLed first (Pitfall 1)
    await db.execute(
        update(AdminJob)
        .where(AdminJob.argument_id == argument_id)
        .values(argument_id=None)
        .execution_options(synchronize_session=False)
    )
    # Step 6: Delete the argument itself
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

    # b. Parse argued_date from ISO string if provided
    parsed_date: datetime.date | None = (
        datetime.date.fromisoformat(body.argued_date)
        if body.argued_date
        else None
    )

    # c. Update Argument row — only write fields that were explicitly provided.
    # WR-01: always writing source_docket=body.source_docket would NULL an existing
    # docket when the operator saves the form with that field left blank.
    values_to_set: dict = {}
    if parsed_date is not None:
        values_to_set["argued_date"] = parsed_date
    if body.source_docket is not None:
        values_to_set["source_docket"] = body.source_docket or None
    # Phase 23 (PJOB-07 / T-23-02): parse question_number from free-text string.
    # Non-numeric input is silently skipped (never raises 500 per T-23-02).
    if body.question_number is not None and body.question_number.strip():
        try:
            values_to_set["question_number"] = int(body.question_number)
        except ValueError:
            pass  # Non-numeric value — skip silently per T-23-02
    if values_to_set:
        await db.execute(
            update(Argument)
            .where(Argument.id == argument_id)
            .values(**values_to_set)
            .execution_options(synchronize_session=False)
        )

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

    await db.commit()
    return True
