"""
Business logic for admin job orchestration.

Responsibilities:
  - CRUD for AdminJob rows (create, get, list)
  - Atomic step-advance guards (rowcount check, no RETURNING)
  - Run-id lookup for resumable re-spawn (PIPE-17)
  - Resolve job: validate person_ids, upsert SpeakerAlias, UPDATE utterances +
    argument_participants, complete job
  - Inline person/role creation (D-13)

Critical guards (mirroring pipeline/commands/resolve.py):
  - EVERY update() call includes .execution_options(synchronize_session=False)
  - try_advance_* guards use rowcount == 1, never RETURNING (Pattern 3)
  - resolve_job validates all person_ids BEFORE any alias/utterance write (Pitfall 5)
  - normalize_label imported from pipeline.commands.resolve (single source of truth)
"""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func

from api.models.models import (
    AdminJob,
    AdminJobStatus,
    AdminJobStep,
    Argument,
    ArgumentParticipant,
    Person,
    PipelineRun,
    Role,
    SpeakerAlias,
    Utterance,
)
from api.schemas.admin_jobs import PersonCreate, ResolveMatch
from pipeline.commands.resolve import normalize_label


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------


async def create_job(
    db: AsyncSession,
    *,
    pdf_url: str | None = None,
    spaces_key: str | None = None,
) -> AdminJob:
    """Insert a new AdminJob row and return it.

    Status starts as PENDING; current_step starts as INGEST.
    The caller (router) is responsible for spawning the pipeline subprocess
    after this returns.
    """
    job = AdminJob(
        status=AdminJobStatus.PENDING,
        current_step=AdminJobStep.INGEST,
        pdf_url=pdf_url,
        spaces_key=spaces_key,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: int) -> AdminJob | None:
    """Load a single AdminJob by primary key."""
    result = await db.execute(
        select(AdminJob).where(AdminJob.id == job_id)
    )
    return result.scalar_one_or_none()


async def list_jobs(
    db: AsyncSession, limit: int = 10, incomplete: bool = False
) -> list[AdminJob]:
    """Return the most recent `limit` AdminJob rows, newest first.

    Args:
        db: Async database session.
        limit: Maximum number of rows to return (default 10).
        incomplete: When True, filter to only PAUSED and FAILED jobs (D-10 / PIPE-20).
                    When False (default), return all jobs regardless of status.
    """
    query = select(AdminJob)
    if incomplete:
        query = query.where(
            AdminJob.status.in_([AdminJobStatus.PAUSED, AdminJobStatus.FAILED])
        )
    query = query.order_by(AdminJob.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Atomic step-advance guards (Pattern 3 — rowcount, no RETURNING)
# ---------------------------------------------------------------------------


async def try_advance_ingest_to_parse(db: AsyncSession, job_id: int) -> bool:
    """Atomically transition INGEST/COMPLETED → PARSE/RUNNING.

    Returns True if exactly one row was updated (this caller wins the race),
    False if the row was already advanced or does not match the expected state.

    Design notes (Pattern 3):
      - WHERE clause enforces both current_step AND status so a double-spawn
        (Pitfall 4) cannot advance a job twice.
      - NEVER use RETURNING — it nullifies rowcount on some PG driver versions.
      - .execution_options(synchronize_session=False) is mandatory for UPDATE.
    """
    result = await db.execute(
        update(AdminJob)
        .where(
            AdminJob.id == job_id,
            AdminJob.current_step == AdminJobStep.INGEST,
            AdminJob.status == AdminJobStatus.COMPLETED,
        )
        .values(status=AdminJobStatus.RUNNING, current_step=AdminJobStep.PARSE)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return result.rowcount == 1


async def try_advance_parse_to_resolve(db: AsyncSession, job_id: int) -> bool:
    """Atomically transition PARSE/COMPLETED → RESOLVE/RUNNING.

    Returns True if exactly one row was updated, False otherwise.
    Same rowcount-guard pattern as try_advance_ingest_to_parse.
    """
    result = await db.execute(
        update(AdminJob)
        .where(
            AdminJob.id == job_id,
            AdminJob.current_step == AdminJobStep.PARSE,
            AdminJob.status == AdminJobStatus.COMPLETED,
        )
        .values(status=AdminJobStatus.RUNNING, current_step=AdminJobStep.RESOLVE)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return result.rowcount == 1


# ---------------------------------------------------------------------------
# Run-id lookup (PIPE-17 — resumable re-spawn)
# ---------------------------------------------------------------------------


async def get_run_id_for_step(
    db: AsyncSession, job_id: int, step: str
) -> int | None:
    """Return the most recent pipeline_run.id for (argument_id, step).

    This enables resumable re-spawn: when the poll endpoint needs to pass
    `--run-id` to the next subprocess, it calls this with the INPUT step
    (the step whose run feeds the next command).

    Examples:
        get_run_id_for_step(db, job_id, "ingest") → run-id parse consumes
        get_run_id_for_step(db, job_id, "parse")  → run-id resolve consumes

    Returns None if the job has no argument_id yet (ingest not yet finished)
    or if no pipeline_run exists for the given (argument_id, step).

    No admin_jobs columns are added — the run-id is always re-derivable from
    pipeline_runs by (argument_id, step), so a re-entrant poll after the
    operator closed and reopened the browser re-derives the correct run-id.
    """
    job = await get_job(db, job_id)
    if job is None or job.argument_id is None:
        return None

    result = await db.execute(
        select(PipelineRun.id)
        .where(
            PipelineRun.argument_id == job.argument_id,
            PipelineRun.step == step,
        )
        .order_by(PipelineRun.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Resolve job
# ---------------------------------------------------------------------------


async def resolve_job(
    db: AsyncSession,
    job_id: int,
    matches: list[ResolveMatch],
) -> AdminJob:
    """Apply operator-confirmed speaker-label mappings to a paused job.

    Order (Pitfall 5 — validate FIRST, mutate never):
      1. Validate every person_id exists — raise ValueError if any is missing.
      2. For each match:
         a. Upsert SpeakerAlias keyed on normalize_label(raw_speaker_label).
         b. UPDATE Utterance.person_id for (argument_id, parse_run_id, raw_label).
         c. UPDATE ArgumentParticipant.person_id for (argument_id, raw_label).
      3. Set job.status = COMPLETED; commit.
    """
    # Step 1: Load job
    job = await get_job(db, job_id)
    if job is None:
        raise ValueError(f"AdminJob {job_id} not found")

    # Step 1a: Guard against double-submit or wrong-state calls.
    # resolve_job may only be applied to a PAUSED job — a second POST on an
    # already-COMPLETED job would re-apply alias writes and overwrite resolved_at.
    if job.status != AdminJobStatus.PAUSED:
        raise ValueError(
            f"AdminJob {job_id} is not PAUSED (current status: {job.status.value!r}); "
            "resolve can only be applied to a paused job."
        )

    # Step 1b: Validate all person_ids BEFORE any alias/utterance write
    for match in matches:
        person_result = await db.execute(
            select(Person).where(Person.id == match.person_id)
        )
        if person_result.scalar_one_or_none() is None:
            raise ValueError(
                f"Person id={match.person_id} does not exist "
                f"(referenced by raw_speaker_label={match.raw_speaker_label!r})"
            )

    # Step 1c: Derive the parse run-id so we can scope the Utterance UPDATE.
    # WR-05: treat a missing parse_run_id as an error — a None would broaden the
    # Utterance UPDATE to all parse runs for the argument, corrupting prior runs.
    parse_run_id = await get_run_id_for_step(db, job_id, "parse")
    if parse_run_id is None:
        raise ValueError(
            f"No parse pipeline_run found for AdminJob {job_id}. "
            "Cannot scope utterance updates without a parse run id."
        )

    # Step 2: Apply each match
    for match in matches:
        normalized = normalize_label(match.raw_speaker_label)

        # Step 2a: Upsert SpeakerAlias (normalized_label is UNIQUE)
        existing_alias_result = await db.execute(
            select(SpeakerAlias).where(SpeakerAlias.normalized_label == normalized)
        )
        existing_alias = existing_alias_result.scalar_one_or_none()

        if existing_alias is None:
            alias = SpeakerAlias(
                normalized_label=normalized,
                person_id=match.person_id,
            )
            db.add(alias)
            await db.flush()
        else:
            await db.execute(
                update(SpeakerAlias)
                .where(SpeakerAlias.normalized_label == normalized)
                .values(person_id=match.person_id)
                .execution_options(synchronize_session=False)
            )

        # Step 2b: UPDATE Utterance.person_id (scope by argument + parse run)
        # parse_run_id is guaranteed non-None here (checked at step 1c above)
        if job.argument_id is not None:
            await db.execute(
                update(Utterance)
                .where(
                    Utterance.argument_id == job.argument_id,
                    Utterance.raw_speaker_label == match.raw_speaker_label,
                    Utterance.pipeline_run_id == parse_run_id,
                )
                .values(person_id=match.person_id)
                .execution_options(synchronize_session=False)
            )

            # Step 2c: UPDATE ArgumentParticipant.person_id
            await db.execute(
                update(ArgumentParticipant)
                .where(
                    ArgumentParticipant.argument_id == job.argument_id,
                    ArgumentParticipant.raw_speaker_label == match.raw_speaker_label,
                )
                .values(person_id=match.person_id)
                .execution_options(synchronize_session=False)
            )

    # Step 3: Mark job COMPLETED and stamp arguments.resolved_at
    await db.execute(
        update(AdminJob)
        .where(AdminJob.id == job_id)
        .values(status=AdminJobStatus.COMPLETED)
        .execution_options(synchronize_session=False)
    )
    # Stamp resolved_at so the argument becomes visible in /cases/ (Gap 3 gate)
    if job.argument_id is not None:
        await db.execute(
            update(Argument)
            .where(Argument.id == job.argument_id)
            .values(resolved_at=func.now())
            .execution_options(synchronize_session=False)
        )
    await db.commit()

    # Reload and return the updated job
    updated = await get_job(db, job_id)
    return updated  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# People list (typeahead for discrepancy review)
# ---------------------------------------------------------------------------


async def list_people(
    db: AsyncSession,
) -> list[dict]:
    """Return all Person rows joined with their Role name, sorted by full_name.

    Used by the discrepancy review typeahead so operators can correct wrong
    auto-matches against the full roster (Gap 1b fix, Plan 07-07).

    Returns a list of dicts with keys: id, full_name, role_name (may be None).
    The same join/order used by pipeline/commands/resolve.py lines 185-189.
    """
    result = await db.execute(
        select(Person, Role.name.label("role_name"))
        .outerjoin(Role, Person.role_id == Role.id)
        .order_by(Person.full_name)
    )
    rows = result.all()
    return [
        {
            "id": person.id,
            "full_name": person.full_name,
            "role_name": role_name,
        }
        for person, role_name in rows
    ]


# ---------------------------------------------------------------------------
# Inline person/role creation (D-13)
# ---------------------------------------------------------------------------


async def create_person_for_job(
    db: AsyncSession,
    job_id: int,
    body: PersonCreate,
) -> Person:
    """Create a new Person (and optionally a new Role) for the given job.

    If body.role_name is set and body.role_id is None, find-or-create a Role
    by name first, then use its id for the new Person.

    WR-02: validates that the AdminJob exists and is PAUSED before creating
    the Person — prevents phantom person rows from spurious or wrong-state POSTs.

    Bio, photo, and tenure fields are Phase 8 (D-13 deferred).
    """
    job = await get_job(db, job_id)
    if job is None:
        raise ValueError(f"AdminJob {job_id} not found")
    if job.status != AdminJobStatus.PAUSED:
        raise ValueError(
            f"AdminJob {job_id} is not PAUSED (status: {job.status.value!r}); "
            "people can only be created for a paused job."
        )

    role_id = body.role_id

    if body.role_name and role_id is None:
        # Find-or-create role by name
        role_result = await db.execute(
            select(Role).where(Role.name == body.role_name)
        )
        role = role_result.scalar_one_or_none()
        if role is None:
            role = Role(name=body.role_name)
            db.add(role)
            await db.flush()
        role_id = role.id

    person = Person(full_name=body.full_name, role_id=role_id)
    db.add(person)
    await db.flush()
    await db.commit()
    await db.refresh(person)
    return person
