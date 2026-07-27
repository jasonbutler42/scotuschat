"""
Phase 31 Plan 07 — success-criterion-3 regression guard.

`create_person_for_job` (api/services/admin_jobs.py) commits internally
(`await db.commit()`) rather than participating in a caller-managed
transaction that a test fixture could roll back. Before this phase, that
inner commit landed in the shared dev DB — every invocation of this service
function from a test left a real Person row behind. Phase 31's fix (D-01)
is environmental: TEST_DATABASE_URL redirects DATABASE_URL for the whole
suite (see tests/conftest.py), so the inner commit now lands in the isolated
`scotus_test` database instead.

This test does NOT itself assert anything about the shared dev DB — that
no-leak assertion is enforced globally, for every test in the suite, by the
`pytest_sessionstart`/`pytest_sessionfinish` hook in tests/conftest.py
(T-31-17: delegating the check to an always-on hook means it can't be
forgotten by a future per-test assertion). What THIS test proves is the
other half: that the inner commit actually took effect somewhere queryable
(scotus_test), not that it silently vanished. Together, the two constitute
the criterion-3 demonstration: the commit landed in scotus_test, and NOT in
the shared dev DB.

Does not modify api/services/admin_jobs.py or its commit semantics — this
phase's fix is purely environmental (D-01).
"""

import os

import pytest


def _db_configured() -> bool:
    """Same placeholder guard every DB-gated test in this suite uses."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_create_person_for_job_inner_commit_is_queryable_after_return() -> None:
    """
    create_person_for_job's internal `await db.commit()` (admin_jobs.py:957)
    must be durably visible to a fresh session once the call returns —
    demonstrating the commit landed in scotus_test (via the TEST_DATABASE_URL
    redirect), not lost, not rolled back, and not written to the shared dev
    DB (enforced separately by the sessionfinish leak hook).

    Uses AsyncSessionLocal() directly, not the shared db_session fixture —
    create_person_for_job commits internally, which raises "Can't operate on
    closed transaction" when nested inside db_session's outer
    session.begin() wrapper (same reasoning as
    test_admin_jobs_phase25.py::test_create_person_for_job_bench_sets_is_justice_and_participant_side).
    """
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentStatusEnum,
        Person,
    )
    from api.schemas.admin_jobs import PersonCreate
    from api.services.admin_jobs import create_person_for_job

    # Arrange: a PAUSED job is required by create_person_for_job's WR-02 guard.
    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
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

    body = PersonCreate(last_name="Isolation Regression Test Person")

    # Act: invoke the production service function that commits internally.
    async with AsyncSessionLocal() as db:
        person = await create_person_for_job(db, job_id, body)
        person_id = person.id

    # Assert: a BRAND NEW session (no connection/transaction shared with the
    # call above) can see the row — proving the commit is durable, not just
    # visible within the same in-flight transaction.
    async with AsyncSessionLocal() as db:
        reloaded = await db.get(Person, person_id)
        assert reloaded is not None, (
            "create_person_for_job's internal commit did not durably persist "
            "the Person row — isolation mechanism is not surviving inner "
            "commits (success criterion 3 failed)"
        )
        assert reloaded.last_name == "Isolation Regression Test Person"
        assert reloaded.full_name == "Isolation Regression Test Person"

        # Cleanup — create_person_for_job commits internally, so nothing here
        # is protected by a rollback; must delete explicitly.
        await db.delete(reloaded)
        job = await db.get(AdminJob, job_id)
        if job is not None:
            await db.delete(job)
        arg = await db.get(Argument, arg_id)
        if arg is not None:
            await db.delete(arg)
        await db.commit()
