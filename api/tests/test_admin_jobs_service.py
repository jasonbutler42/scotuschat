"""
Structural and behavioral tests for admin_jobs service delete_job function (Phase 21 Plan 02).

Scope:
  - Verify delete_job is importable from admin_jobs service.
  - Verify delete_job removes only the admin_job row (not argument/import_run/utterances).
  - Verify delete_job returns False for a non-existent job_id.
  - Structural source assertion: the only table in a delete() call is AdminJob.
  - Structural source assertion: .execution_options(synchronize_session=False) guard present.

DB-touching tests are guarded behind DATABASE_URL skip marker.
No-DB structural assertions run without a live database.

Phase 48 plan 04, Task 3: DB-gated regression coverage locking (a) the
PIPELINE -> CANDIDATE vocabulary swap across approve_job /
update_resolve_row_for_job / list_resolve_rows_for_job, and (b) the
in-transaction recompute_argument_tier wiring in approve_job and
resolve_job. Every test re-reads committed state from a fresh
AsyncSessionLocal() (never asserts against an in-session object) and tears
down its own seeded rows in FK order inside a finally block, mirroring
api/tests/test_trust_recompute.py's seed/assert/teardown shape.
"""

import os

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


# ---------------------------------------------------------------------------
# Import test
# ---------------------------------------------------------------------------


def test_delete_job_importable() -> None:
    """delete_job must be importable from admin_jobs service (ADMIN-02)."""
    from api.services.admin_jobs import delete_job  # noqa: F401


# ---------------------------------------------------------------------------
# Structural guards (no DB required)
# ---------------------------------------------------------------------------


def test_delete_job_only_deletes_admin_jobs() -> None:
    """The delete_job function body must contain a delete() call against AdminJob only.

    No other table (Argument, ImportRun, Utterance, ArgumentParticipant, CaseArgument)
    may appear inside a delete() or update() call within the function (D-10, D-11, Pitfall 6).
    """
    import inspect

    from api.services import admin_jobs

    source = inspect.getsource(admin_jobs)
    func_start = source.find("async def delete_job(")
    assert func_start != -1, "delete_job not found in source"
    # Isolate the function body (up to the next top-level async def)
    next_func = source.find("\nasync def ", func_start + 1)
    if next_func == -1:
        next_func = source.find("\ndef ", func_start + 1)
    func_body = source[func_start:next_func] if next_func != -1 else source[func_start:]

    # The ONLY allowed table in a delete() call is AdminJob
    assert "delete(AdminJob)" in func_body, (
        "delete(AdminJob) not found in delete_job body — function must delete the admin_job row"
    )
    # No other tables may appear in delete() calls
    forbidden_deletes = [
        "delete(Argument)",
        "delete(ImportRun)",
        "delete(Utterance)",
        "delete(ArgumentParticipant)",
        "delete(CaseArgument)",
    ]
    for forbidden in forbidden_deletes:
        assert forbidden not in func_body, (
            f"{forbidden} found in delete_job body — job delete must NOT cascade "
            "into argument or its downstream data (D-10, D-11, Pitfall 6)"
        )


def test_delete_job_has_synchronize_session_false() -> None:
    """The delete(AdminJob) statement in delete_job must include
    .execution_options(synchronize_session=False) (consistent with all other
    bulk-statement guards in the module).
    """
    import inspect

    from api.services import admin_jobs

    source = inspect.getsource(admin_jobs)
    func_start = source.find("async def delete_job(")
    assert func_start != -1, "delete_job not found in source"
    next_func = source.find("\nasync def ", func_start + 1)
    if next_func == -1:
        next_func = source.find("\ndef ", func_start + 1)
    func_body = source[func_start:next_func] if next_func != -1 else source[func_start:]

    assert "synchronize_session=False" in func_body, (
        "delete_job body missing .execution_options(synchronize_session=False) — "
        "required guard for all bulk statements in this module"
    )


# ---------------------------------------------------------------------------
# DB-guarded behavioral tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_job_returns_false_for_missing_id() -> None:
    """delete_job must return False when job_id does not exist (no row deleted)."""
    from api.core.database import AsyncSessionLocal
    from api.services.admin_jobs import delete_job

    async with AsyncSessionLocal() as db:
        result = await delete_job(db, 999999)
    assert result is False


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_delete_job_removes_only_admin_job_row() -> None:
    """delete_job removes the admin_job row and returns True.

    The linked argument, its ImportRun step rows, and its Utterance rows
    must all survive the delete (D-10, D-11).
    """
    import datetime

    from sqlalchemy import select

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentStatusEnum,
        ImportMethod,
        ImportRun,
        ImportRunStatus,
        ImportSource,
        Utterance,
    )
    from api.services.admin_jobs import delete_job

    async with AsyncSessionLocal() as db:
        # --- seed: argument ---
        arg = Argument(
            status=ArgumentStatusEnum.PIPELINE,
            resolved_at=None,
        )
        db.add(arg)
        await db.flush()

        # --- seed: import run (ingest) ---
        run = ImportRun(
            argument_id=arg.id,
            step="ingest",
            status=ImportRunStatus.COMPLETED,
            source=ImportSource.PDF_PIPELINE,
            method=ImportMethod.NORMALIZED,
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(run)
        await db.flush()

        # --- seed: utterance (linked to argument + import run) ---
        # Utterance has no `raw_text` column — the field is `text` (stale test
        # assumption). Provenance now lives on the parent ImportRun row, not
        # on Utterance.
        utt = Utterance(
            argument_id=arg.id,
            import_run_id=run.id,
            sequence=1,
            raw_speaker_label="CHIEF JUSTICE ROBERTS",
            text="We'll hear argument next in this case.",
        )
        db.add(utt)
        await db.flush()

        # --- seed: admin_job linked to the argument ---
        job = AdminJob(
            status=AdminJobStatus.COMPLETED,
            current_step=AdminJobStep.INGEST,
            argument_id=arg.id,
        )
        db.add(job)
        await db.commit()

        job_id = job.id
        arg_id = arg.id
        run_id = run.id
        utt_id = utt.id

    # --- act: delete the job ---
    async with AsyncSessionLocal() as db:
        result = await delete_job(db, job_id)

    assert result is True, "delete_job must return True when the job row is deleted"

    # --- assert: admin_job is gone ---
    async with AsyncSessionLocal() as db:
        deleted_job = await db.get(AdminJob, job_id)
        assert deleted_job is None, "AdminJob row must be removed by delete_job"

        # --- assert: argument, import_run, utterance all survive ---
        surviving_arg = await db.get(Argument, arg_id)
        assert surviving_arg is not None, (
            "Argument must NOT be deleted by delete_job (D-10, D-11)"
        )

        surviving_run = await db.get(ImportRun, run_id)
        assert surviving_run is not None, (
            "ImportRun must NOT be deleted by delete_job (D-10, D-11)"
        )

        surviving_utt = await db.get(Utterance, utt_id)
        assert surviving_utt is not None, (
            "Utterance must NOT be deleted by delete_job (D-10, D-11)"
        )

        # --- cleanup: remove seeded data ---
        # No relationship() is configured between these models (Core-style FK
        # columns only), so the ORM unit-of-work cannot auto-derive delete
        # order from FK dependencies — an explicit flush() after each delete
        # forces FK-safe ordering (utterances -> import_run -> arguments),
        # matching the manual-ordering convention used elsewhere in this
        # codebase (e.g. admin_arguments.delete_argument's Pitfall 2 comment).
        await db.delete(surviving_utt)
        await db.flush()
        await db.delete(surviving_run)
        await db.flush()
        await db.delete(surviving_arg)
        await db.commit()


# ---------------------------------------------------------------------------
# approve_job — ArgumentStatusLog "Created" audit row (Phase 26 Plan 01, D-08)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_approve_job_writes_one_draft_log_row() -> None:
    """approve_job on a CANDIDATE argument sets status=DRAFT, resolved_at=now(),
    completes the job, and writes exactly one ArgumentStatusLog row with
    status=DRAFT for that argument_id (the "Created" transition, D-08).
    """
    from sqlalchemy import select

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentStatusEnum,
        ArgumentStatusLog,
    )
    from api.services.admin_jobs import approve_job

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.CANDIDATE, resolved_at=None)
        db.add(arg)
        await db.flush()

        job = AdminJob(
            status=AdminJobStatus.PAUSED,
            current_step=AdminJobStep.RESOLVE,
            argument_id=arg.id,
        )
        db.add(job)
        await db.commit()

        arg_id = arg.id
        job_id = job.id

    async with AsyncSessionLocal() as db:
        updated_job = await approve_job(db, job_id)

    assert updated_job.status == AdminJobStatus.COMPLETED

    async with AsyncSessionLocal() as db:
        arg = await db.get(Argument, arg_id)
        assert arg.status == ArgumentStatusEnum.DRAFT
        assert arg.resolved_at is not None

        log_result = await db.execute(
            select(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == arg_id)
        )
        log_rows = log_result.scalars().all()
        assert len(log_rows) == 1
        assert log_rows[0].status == ArgumentStatusEnum.DRAFT

        # --- cleanup --- (explicit flush() forces FK-safe delete order — no
        # relationship() is configured between these models)
        job = await db.get(AdminJob, job_id)
        for row in log_rows:
            await db.delete(row)
        await db.delete(job)
        await db.flush()
        await db.delete(arg)
        await db.commit()


# ---------------------------------------------------------------------------
# Phase 48 plan 04, Task 3: candidate/CANDIDATE vocabulary swap +
# recompute_argument_tier wiring regression coverage.
# ---------------------------------------------------------------------------


async def _teardown_rows(
    argument_id=None,
    admin_job_id=None,
    status_log_ids=(),
    participant_ids=(),
    utterance_ids=(),
    import_run_ids=(),
    person_ids=(),
):
    """Delete every seeded row in FK order: ArgumentStatusLog, Utterance,
    ArgumentParticipant, AdminJob, ImportRun, Argument, Person — a `finally`
    block callers use so a failed assertion mid-test still leaves the shared
    scotus_test database clean for the rootdir conftest.py row-count
    tripwire.

    ArgumentStatusLog rows are deleted by querying argument_id, not by
    explicit id, because approve_job writes one as a side effect the caller
    never captures an id for (D-22's FK — argument_status_log.argument_id —
    must be clear before the Argument row itself can be deleted).
    """
    from sqlalchemy import delete as _delete
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        Argument,
        ArgumentParticipant,
        ArgumentStatusLog,
        ImportRun,
        Person,
        Utterance,
        ValueDiscrepancy,
    )

    async with AsyncSessionLocal() as db:
        for log_id in status_log_ids:
            row = await db.get(ArgumentStatusLog, log_id)
            if row is not None:
                await db.delete(row)
        if argument_id is not None:
            await db.execute(
                _delete(ArgumentStatusLog).where(
                    ArgumentStatusLog.argument_id == argument_id
                )
            )
        for utterance_id in utterance_ids:
            row = await db.get(Utterance, utterance_id)
            if row is not None:
                await db.delete(row)
        # Phase 49 (D-31/D-31a): the authority-gated writer may have
        # recorded a value_discrepancy for a participant this test touched
        # via update_resolve_row_for_job/apply_participant_value_change —
        # value_discrepancy.target_id has no real FK to
        # argument_participants.id, so it would otherwise leak past the
        # participant's own delete below.
        if participant_ids:
            await db.execute(
                _delete(ValueDiscrepancy).where(
                    ValueDiscrepancy.target_type == "argument_participant",
                    ValueDiscrepancy.target_id.in_(list(participant_ids)),
                )
            )
        for participant_id in participant_ids:
            row = await db.get(ArgumentParticipant, participant_id)
            if row is not None:
                await db.delete(row)
        if admin_job_id is not None:
            row = await db.get(AdminJob, admin_job_id)
            if row is not None:
                await db.delete(row)
        await db.flush()
        for import_run_id in import_run_ids:
            row = await db.get(ImportRun, import_run_id)
            if row is not None:
                await db.delete(row)
        if argument_id is not None:
            row = await db.get(Argument, argument_id)
            if row is not None:
                await db.delete(row)
        for person_id in person_ids:
            row = await db.get(Person, person_id)
            if row is not None:
                await db.delete(row)
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_approve_job_accepts_freshly_created_candidate_and_rejects_second_call() -> None:
    """approve_job succeeds on a freshly-created (CANDIDATE) argument and
    raises ValueError naming the already-DRAFT state on a second call
    (T-48-DOUBLEAPPROVE)."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep, Argument, ArgumentStatusEnum
    from api.services.admin_jobs import approve_job

    argument_id = None
    admin_job_id = None
    try:
        async with AsyncSessionLocal() as db:
            arg = Argument(status=ArgumentStatusEnum.CANDIDATE, resolved_at=None)
            db.add(arg)
            await db.flush()
            job = AdminJob(
                status=AdminJobStatus.PAUSED,
                current_step=AdminJobStep.RESOLVE,
                argument_id=arg.id,
            )
            db.add(job)
            await db.commit()
            argument_id = arg.id
            admin_job_id = job.id

        async with AsyncSessionLocal() as db:
            updated_job = await approve_job(db, admin_job_id)
        assert updated_job.status == AdminJobStatus.COMPLETED

        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, argument_id)
            assert arg.status == ArgumentStatusEnum.DRAFT

        with pytest.raises(ValueError, match="already in 'draft' state"):
            async with AsyncSessionLocal() as db:
                await approve_job(db, admin_job_id)
    finally:
        await _teardown_rows(
            argument_id=argument_id,
            admin_job_id=admin_job_id,
        )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_resolve_row_accepts_candidate_draft_and_rejects_published() -> None:
    """update_resolve_row_for_job accepts an edit pre-approval (CANDIDATE),
    STILL accepts it once the argument has moved to DRAFT (Phase 49 folded
    todo: 2026-08-21-widen-participant-editability-to-all-unpublished-
    states — supersedes the prior CANDIDATE-only T-48-GUARD), and only
    rejects once the argument is PUBLISHED, naming 'published' in the
    error."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        SideEnum,
    )
    from api.schemas.admin_jobs import ResolveRowUpdate
    from api.services.admin_jobs import approve_job, update_resolve_row_for_job

    argument_id = None
    admin_job_id = None
    participant_id = None
    try:
        async with AsyncSessionLocal() as db:
            arg = Argument(status=ArgumentStatusEnum.CANDIDATE, resolved_at=None)
            db.add(arg)
            await db.flush()
            participant = ArgumentParticipant(
                argument_id=arg.id,
                raw_speaker_label="MR. TEST",
                side=SideEnum.PETITIONER,
            )
            db.add(participant)
            await db.flush()
            job = AdminJob(
                status=AdminJobStatus.PAUSED,
                current_step=AdminJobStep.RESOLVE,
                argument_id=arg.id,
            )
            db.add(job)
            await db.commit()
            argument_id = arg.id
            admin_job_id = job.id
            participant_id = participant.id

        # Pre-approval: the edit succeeds.
        async with AsyncSessionLocal() as db:
            updated = await update_resolve_row_for_job(
                db,
                admin_job_id,
                ResolveRowUpdate(
                    participant_id=participant_id,
                    side=SideEnum.PETITIONER,
                    descriptor="Counsel for Petitioner",
                ),
            )
        assert updated.descriptor == "Counsel for Petitioner"

        async with AsyncSessionLocal() as db:
            await approve_job(db, admin_job_id)

        # Post-approval (DRAFT): the edit STILL succeeds under the widened
        # editability rule.
        async with AsyncSessionLocal() as db:
            updated = await update_resolve_row_for_job(
                db,
                admin_job_id,
                ResolveRowUpdate(
                    participant_id=participant_id,
                    side=SideEnum.RESPONDENT,
                    descriptor="Counsel for Respondent",
                ),
            )
        assert updated.descriptor == "Counsel for Respondent"

        # Once PUBLISHED, the same edit is rejected, naming 'published'.
        async with AsyncSessionLocal() as db:
            from sqlalchemy import update as sa_update

            await db.execute(
                sa_update(Argument)
                .where(Argument.id == argument_id)
                .values(status=ArgumentStatusEnum.PUBLISHED)
            )
            await db.commit()

        with pytest.raises(ValueError) as exc_info:
            async with AsyncSessionLocal() as db:
                await update_resolve_row_for_job(
                    db,
                    admin_job_id,
                    ResolveRowUpdate(
                        participant_id=participant_id,
                        side=SideEnum.PETITIONER,
                        descriptor="Should not persist",
                    ),
                )
        assert "published" in str(exc_info.value)
    finally:
        await _teardown_rows(
            argument_id=argument_id,
            admin_job_id=admin_job_id,
            participant_ids=[participant_id] if participant_id is not None else [],
        )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_resolve_rows_editable_flag_tracks_published_state() -> None:
    """list_resolve_rows_for_job reports editable=True pre-approval AND
    post-approval (DRAFT) under the widened editability rule (Phase 49
    folded todo), and editable=False only once the argument is PUBLISHED."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        SideEnum,
    )
    from api.services.admin_jobs import approve_job
    from api.services.admin_people import list_resolve_rows_for_job

    argument_id = None
    admin_job_id = None
    participant_id = None
    try:
        async with AsyncSessionLocal() as db:
            arg = Argument(status=ArgumentStatusEnum.CANDIDATE, resolved_at=None)
            db.add(arg)
            await db.flush()
            participant = ArgumentParticipant(
                argument_id=arg.id,
                raw_speaker_label="MR. TEST",
                side=SideEnum.PETITIONER,
            )
            db.add(participant)
            await db.flush()
            job = AdminJob(
                status=AdminJobStatus.PAUSED,
                current_step=AdminJobStep.RESOLVE,
                argument_id=arg.id,
            )
            db.add(job)
            await db.commit()
            argument_id = arg.id
            admin_job_id = job.id
            participant_id = participant.id

        async with AsyncSessionLocal() as db:
            rows = await list_resolve_rows_for_job(db, admin_job_id)
        assert len(rows) == 1
        assert rows[0]["editable"] is True

        async with AsyncSessionLocal() as db:
            await approve_job(db, admin_job_id)

        # Post-approval (DRAFT): still editable under the widened rule.
        async with AsyncSessionLocal() as db:
            rows = await list_resolve_rows_for_job(db, admin_job_id)
        assert len(rows) == 1
        assert rows[0]["editable"] is True

        # PUBLISHED: read-only.
        async with AsyncSessionLocal() as db:
            from sqlalchemy import update as sa_update

            await db.execute(
                sa_update(Argument)
                .where(Argument.id == argument_id)
                .values(status=ArgumentStatusEnum.PUBLISHED)
            )
            await db.commit()

        async with AsyncSessionLocal() as db:
            rows = await list_resolve_rows_for_job(db, admin_job_id)
        assert len(rows) == 1
        assert rows[0]["editable"] is False
    finally:
        await _teardown_rows(
            argument_id=argument_id,
            admin_job_id=admin_job_id,
            participant_ids=[participant_id] if participant_id is not None else [],
        )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_approve_job_stamps_trust_tier() -> None:
    """approve_job on a fully-resolved corpus/direct argument stores
    trust_tier='trusted' — not the 'uncertain' server default — proving the
    in-transaction recompute call is live, not a no-op (D-07)."""
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentStatusEnum,
        ImportMethod,
        ImportRun,
        ImportSource,
        Person,
        SideEnum,
        Utterance,
    )
    from api.services.admin_jobs import approve_job

    argument_id = None
    admin_job_id = None
    import_run_id = None
    utterance_id = None
    person_id = None
    try:
        async with AsyncSessionLocal() as db:
            arg = Argument(status=ArgumentStatusEnum.CANDIDATE, resolved_at=None)
            db.add(arg)
            await db.flush()
            run = ImportRun(
                argument_id=arg.id,
                step="parse",
                source=ImportSource.CORPUS,
                method=ImportMethod.DIRECT,
            )
            db.add(run)
            await db.flush()
            person = Person(full_name="Trust Wiring Test Person")
            db.add(person)
            await db.flush()
            utt = Utterance(
                argument_id=arg.id,
                import_run_id=run.id,
                sequence=1,
                raw_speaker_label="MR. TEST",
                text="Test utterance.",
                side=SideEnum.PETITIONER,
                person_id=person.id,
            )
            db.add(utt)
            await db.flush()
            job = AdminJob(
                status=AdminJobStatus.PAUSED,
                current_step=AdminJobStep.RESOLVE,
                argument_id=arg.id,
            )
            db.add(job)
            await db.commit()
            argument_id = arg.id
            admin_job_id = job.id
            import_run_id = run.id
            utterance_id = utt.id
            person_id = person.id

        # Assert the fail-closed default BEFORE approve_job runs.
        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, argument_id)
            assert arg.trust_tier is TrustTier.UNCERTAIN

        async with AsyncSessionLocal() as db:
            await approve_job(db, admin_job_id)

        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, argument_id)
            assert arg.trust_tier is TrustTier.TRUSTED
            assert arg.trust_tier is not TrustTier.UNCERTAIN
    finally:
        await _teardown_rows(
            argument_id=argument_id,
            admin_job_id=admin_job_id,
            utterance_ids=[utterance_id] if utterance_id is not None else [],
            import_run_ids=[import_run_id] if import_run_id is not None else [],
            person_ids=[person_id] if person_id is not None else [],
        )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_resolve_job_recomputes_tier_when_last_speaker_resolves() -> None:
    """resolve_job filling the last NULL person_id moves the stored tier
    from 'uncertain' to 'trusted' in the same transaction as the person_id
    writes (D-07, D-11)."""
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        ImportMethod,
        ImportRun,
        ImportSource,
        Person,
        SideEnum,
        Utterance,
    )
    from api.schemas.admin_jobs import ResolveMatch
    from api.services.admin_jobs import resolve_job

    argument_id = None
    admin_job_id = None
    import_run_id = None
    utterance_id = None
    participant_id = None
    person_id = None
    try:
        async with AsyncSessionLocal() as db:
            arg = Argument(status=ArgumentStatusEnum.CANDIDATE, resolved_at=None)
            db.add(arg)
            await db.flush()
            run = ImportRun(
                argument_id=arg.id,
                step="parse",
                source=ImportSource.CORPUS,
                method=ImportMethod.DIRECT,
            )
            db.add(run)
            await db.flush()
            utt = Utterance(
                argument_id=arg.id,
                import_run_id=run.id,
                sequence=1,
                raw_speaker_label="MR. TEST",
                text="Test utterance.",
                side=SideEnum.PETITIONER,
                person_id=None,
            )
            db.add(utt)
            participant = ArgumentParticipant(
                argument_id=arg.id,
                raw_speaker_label="MR. TEST",
                side=SideEnum.PETITIONER,
                person_id=None,
            )
            db.add(participant)
            await db.flush()
            job = AdminJob(
                status=AdminJobStatus.PAUSED,
                current_step=AdminJobStep.RESOLVE,
                argument_id=arg.id,
            )
            db.add(job)
            await db.commit()
            argument_id = arg.id
            admin_job_id = job.id
            import_run_id = run.id
            utterance_id = utt.id
            participant_id = participant.id

        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, argument_id)
            assert arg.trust_tier is TrustTier.UNCERTAIN

        async with AsyncSessionLocal() as db:
            person = Person(full_name="Resolve Recompute Test Person")
            db.add(person)
            await db.flush()
            await db.commit()
            person_id = person.id

        async with AsyncSessionLocal() as db:
            await resolve_job(
                db,
                admin_job_id,
                [ResolveMatch(raw_speaker_label="MR. TEST", person_id=person_id)],
            )

        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, argument_id)
            assert arg.trust_tier is TrustTier.TRUSTED
    finally:
        # resolve_job also upserts a SpeakerAlias keyed on the normalized
        # label, which FKs to Person — delete it BEFORE _teardown_rows
        # deletes the Person row below, or the Person delete violates
        # speaker_alias_person_id_fkey.
        from api.models.models import SpeakerAlias
        from pipeline.commands.resolve import normalize_label
        from sqlalchemy import select as _select

        async with AsyncSessionLocal() as db:
            alias_result = await db.execute(
                _select(SpeakerAlias).where(
                    SpeakerAlias.normalized_label == normalize_label("MR. TEST")
                )
            )
            alias = alias_result.scalar_one_or_none()
            if alias is not None:
                await db.delete(alias)
                await db.commit()

        await _teardown_rows(
            argument_id=argument_id,
            admin_job_id=admin_job_id,
            utterance_ids=[utterance_id] if utterance_id is not None else [],
            participant_ids=[participant_id] if participant_id is not None else [],
            import_run_ids=[import_run_id] if import_run_id is not None else [],
            person_ids=[person_id] if person_id is not None else [],
        )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_repeated_writer_call_leaves_tier_unchanged() -> None:
    """Calling update_resolve_row_for_job twice with the same body, with no
    intervening constituent change, leaves the stored tier identical after
    both calls — the recompute is idempotent under an unchanged constituent
    set (adjacency edge)."""
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        ImportMethod,
        ImportRun,
        ImportSource,
        Person,
        SideEnum,
        Utterance,
    )
    from api.schemas.admin_jobs import ResolveRowUpdate
    from api.services.admin_jobs import update_resolve_row_for_job

    argument_id = None
    admin_job_id = None
    import_run_id = None
    utterance_id = None
    participant_id = None
    person_id = None
    try:
        async with AsyncSessionLocal() as db:
            arg = Argument(status=ArgumentStatusEnum.CANDIDATE, resolved_at=None)
            db.add(arg)
            await db.flush()
            run = ImportRun(
                argument_id=arg.id,
                step="parse",
                source=ImportSource.CORPUS,
                method=ImportMethod.DIRECT,
            )
            db.add(run)
            await db.flush()
            person = Person(full_name="Idempotence Test Person")
            db.add(person)
            await db.flush()
            utt = Utterance(
                argument_id=arg.id,
                import_run_id=run.id,
                sequence=1,
                raw_speaker_label="MR. TEST",
                text="Test utterance.",
                side=SideEnum.PETITIONER,
                person_id=person.id,
            )
            db.add(utt)
            participant = ArgumentParticipant(
                argument_id=arg.id,
                raw_speaker_label="MR. TEST",
                side=SideEnum.PETITIONER,
                person_id=person.id,
            )
            db.add(participant)
            await db.flush()
            job = AdminJob(
                status=AdminJobStatus.PAUSED,
                current_step=AdminJobStep.RESOLVE,
                argument_id=arg.id,
            )
            db.add(job)
            await db.commit()
            argument_id = arg.id
            admin_job_id = job.id
            import_run_id = run.id
            utterance_id = utt.id
            participant_id = participant.id
            person_id = person.id

        body = ResolveRowUpdate(
            participant_id=participant_id,
            side=SideEnum.PETITIONER,
            descriptor="Counsel for Petitioner",
        )

        async with AsyncSessionLocal() as db:
            await update_resolve_row_for_job(db, admin_job_id, body)
        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, argument_id)
            tier_after_first_call = arg.trust_tier
        assert tier_after_first_call is TrustTier.TRUSTED

        async with AsyncSessionLocal() as db:
            await update_resolve_row_for_job(db, admin_job_id, body)
        async with AsyncSessionLocal() as db:
            arg = await db.get(Argument, argument_id)
            tier_after_second_call = arg.trust_tier

        assert tier_after_second_call is tier_after_first_call
    finally:
        await _teardown_rows(
            argument_id=argument_id,
            admin_job_id=admin_job_id,
            utterance_ids=[utterance_id] if utterance_id is not None else [],
            participant_ids=[participant_id] if participant_id is not None else [],
            import_run_ids=[import_run_id] if import_run_id is not None else [],
            person_ids=[person_id] if person_id is not None else [],
        )
