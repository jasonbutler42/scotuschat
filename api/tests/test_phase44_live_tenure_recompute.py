"""
Phase 44 Plan 06 Task 3 — live tenure-derived bench role regression lock (RESOLVE-11).

This file locks RESOLVE-11's already-correct live derivation so a future
change cannot silently introduce a snapshot column or a cache: both read
paths (`list_resolve_rows_for_job` for the job-scoped Resolve card,
`list_argument_speakers` for the argument-scoped Speakers section) issue a
fresh `court_tenures` query on every call and share the identical
`_bench_role_and_missing_tenure` helper, with no snapshot sitting between the
table and the response. See `44-05-RESEARCH.md` Pattern 2.

These tests assert behaviour; they do not drive a fix. They are expected to
be green on their first run against unmodified service code.

Following the project pattern (`test_phase44_argument_role_roundtrip.py`):
  - A local `_db_configured()` helper gates every test behind DATABASE_URL.
  - Every test creates its own fixtures inside `AsyncSessionLocal()` directly
    (both services under test commit internally) and deletes them in an
    explicit cleanup block, in child-before-parent order: CourtTenure,
    ArgumentParticipant, AdminJob, Argument, Person.
"""

import datetime
import os

import pytest

from api.models.models import office_title


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


# Fixed argued date: 1966, before any tenure below with a start_date after it,
# and covered once that tenure's start_date is widened to precede it — the
# coverage relationship is unambiguous throughout.
ARGUED_DATE = datetime.date(1966, 3, 1)
NOT_COVERING_START = datetime.date(1967, 1, 1)  # after ARGUED_DATE — does not cover
COVERING_START = datetime.date(1960, 1, 1)  # before ARGUED_DATE — covers


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_resolve_rows_bench_role_recomputes_after_tenure_correction() -> None:
    """RESOLVE-11: a tenure correction reaches list_resolve_rows_for_job on the
    very next call — no restart, no cache invalidation, no resolve-step re-run."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        CourtTenure,
        OFFICE_ASSOCIATE,
        Person,
        SideEnum,
    )
    from api.services.admin_people import list_resolve_rows_for_job

    async with AsyncSessionLocal() as db:
        person = Person(full_name="Justice Recompute", is_justice=True)
        db.add(person)
        await db.flush()

        arg = Argument(
            status=ArgumentStatusEnum.PIPELINE,
            question_number=1,
            argued_date=ARGUED_DATE,
        )
        db.add(arg)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label="JUSTICE RECOMPUTE",
            side=SideEnum.BENCH,
        )
        db.add(participant)
        await db.flush()

        job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
        db.add(job)
        await db.flush()

        # Tenure window does NOT cover the argued date.
        tenure = CourtTenure(person_id=person.id, office=OFFICE_ASSOCIATE, start_date=NOT_COVERING_START)
        db.add(tenure)
        await db.commit()

        person_id = person.id
        arg_id = arg.id
        participant_id = participant.id
        job_id = job.id
        tenure_id = tenure.id

    try:
        async with AsyncSessionLocal() as db:
            rows = await list_resolve_rows_for_job(db, job_id)
            row = next(r for r in rows if r["participant_id"] == participant_id)
            assert row["missing_tenure"] is True
            assert row["bench_role"] is None
            assert row["person_edit_href"] == f"/admin/people/{person_id}"

        # Widen the tenure to cover the argued date, in a separate session.
        async with AsyncSessionLocal() as db:
            t = await db.get(CourtTenure, tenure_id)
            t.start_date = COVERING_START
            await db.commit()

        # Third read, no restart / cache clear / resolve re-run in between.
        async with AsyncSessionLocal() as db:
            rows = await list_resolve_rows_for_job(db, job_id)
            row = next(r for r in rows if r["participant_id"] == participant_id)
            assert row["missing_tenure"] is False
            assert row["bench_role"] == office_title(OFFICE_ASSOCIATE)
            assert row["person_edit_href"] is None
    finally:
        async with AsyncSessionLocal() as db:
            seeded_tenure = await db.get(CourtTenure, tenure_id)
            if seeded_tenure is not None:
                await db.delete(seeded_tenure)
            seeded_participant = await db.get(ArgumentParticipant, participant_id)
            if seeded_participant is not None:
                await db.delete(seeded_participant)
            seeded_job = await db.get(AdminJob, job_id)
            if seeded_job is not None:
                await db.delete(seeded_job)
            seeded_arg = await db.get(Argument, arg_id)
            if seeded_arg is not None:
                await db.delete(seeded_arg)
            seeded_person = await db.get(Person, person_id)
            if seeded_person is not None:
                await db.delete(seeded_person)
            await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_argument_speakers_bench_role_recomputes_after_tenure_correction() -> None:
    """RESOLVE-11: the same before/after tenure-correction sequence against
    list_argument_speakers (the argument-scoped, read-only Speakers section)."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        CourtTenure,
        OFFICE_CHIEF,
        Person,
        SideEnum,
    )
    from api.services.admin_arguments import list_argument_speakers

    async with AsyncSessionLocal() as db:
        person = Person(full_name="Justice Speakers Recompute", is_justice=True)
        db.add(person)
        await db.flush()

        arg = Argument(
            status=ArgumentStatusEnum.PIPELINE,
            question_number=1,
            argued_date=ARGUED_DATE,
        )
        db.add(arg)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label="JUSTICE SPEAKERS RECOMPUTE",
            side=SideEnum.BENCH,
        )
        db.add(participant)
        await db.flush()

        tenure = CourtTenure(person_id=person.id, office=OFFICE_CHIEF, start_date=NOT_COVERING_START)
        db.add(tenure)
        await db.commit()

        person_id = person.id
        arg_id = arg.id
        participant_id = participant.id
        tenure_id = tenure.id

    try:
        async with AsyncSessionLocal() as db:
            rows = await list_argument_speakers(db, arg_id)
            row = next(r for r in rows if r["participant_id"] == participant_id)
            assert row["missing_tenure"] is True
            assert row["bench_role"] is None
            assert row["person_edit_href"] == f"/admin/people/{person_id}"

        async with AsyncSessionLocal() as db:
            t = await db.get(CourtTenure, tenure_id)
            t.start_date = COVERING_START
            await db.commit()

        async with AsyncSessionLocal() as db:
            rows = await list_argument_speakers(db, arg_id)
            row = next(r for r in rows if r["participant_id"] == participant_id)
            assert row["missing_tenure"] is False
            assert row["bench_role"] == office_title(OFFICE_CHIEF)
            assert row["person_edit_href"] is None
    finally:
        async with AsyncSessionLocal() as db:
            seeded_tenure = await db.get(CourtTenure, tenure_id)
            if seeded_tenure is not None:
                await db.delete(seeded_tenure)
            seeded_participant = await db.get(ArgumentParticipant, participant_id)
            if seeded_participant is not None:
                await db.delete(seeded_participant)
            seeded_arg = await db.get(Argument, arg_id)
            if seeded_arg is not None:
                await db.delete(seeded_arg)
            seeded_person = await db.get(Person, person_id)
            if seeded_person is not None:
                await db.delete(seeded_person)
            await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_both_read_paths_agree_on_bench_role_and_missing_tenure() -> None:
    """RESOLVE-11 'rendered identically in editable and read-only': for the same
    person/tenure/argued-date, the job-scoped and argument-scoped paths return
    the same bench_role and the same missing_tenure — before AND after a
    tenure-state flip, all within one session."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        CourtTenure,
        OFFICE_ASSOCIATE,
        Person,
        SideEnum,
    )
    from api.services.admin_arguments import list_argument_speakers
    from api.services.admin_people import list_resolve_rows_for_job

    async with AsyncSessionLocal() as db:
        person = Person(full_name="Justice Agreement Check", is_justice=True)
        db.add(person)
        await db.flush()

        arg = Argument(
            status=ArgumentStatusEnum.PIPELINE,
            question_number=1,
            argued_date=ARGUED_DATE,
        )
        db.add(arg)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label="JUSTICE AGREEMENT CHECK",
            side=SideEnum.BENCH,
        )
        db.add(participant)
        await db.flush()

        job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
        db.add(job)
        await db.flush()

        # Tenure covers the argued date from the start.
        tenure = CourtTenure(person_id=person.id, office=OFFICE_ASSOCIATE, start_date=COVERING_START)
        db.add(tenure)
        await db.commit()

        person_id = person.id
        arg_id = arg.id
        participant_id = participant.id
        job_id = job.id
        tenure_id = tenure.id

    try:
        async with AsyncSessionLocal() as db:
            resolve_rows = await list_resolve_rows_for_job(db, job_id)
            speaker_rows = await list_argument_speakers(db, arg_id)
            resolve_row = next(r for r in resolve_rows if r["participant_id"] == participant_id)
            speaker_row = next(r for r in speaker_rows if r["participant_id"] == participant_id)
            assert resolve_row["bench_role"] == speaker_row["bench_role"] == office_title(OFFICE_ASSOCIATE)
            assert resolve_row["missing_tenure"] == speaker_row["missing_tenure"] is False

        # Flip to a non-covering tenure — both paths must agree again.
        async with AsyncSessionLocal() as db:
            t = await db.get(CourtTenure, tenure_id)
            t.start_date = NOT_COVERING_START
            await db.commit()

        async with AsyncSessionLocal() as db:
            resolve_rows = await list_resolve_rows_for_job(db, job_id)
            speaker_rows = await list_argument_speakers(db, arg_id)
            resolve_row = next(r for r in resolve_rows if r["participant_id"] == participant_id)
            speaker_row = next(r for r in speaker_rows if r["participant_id"] == participant_id)
            assert resolve_row["bench_role"] == speaker_row["bench_role"] is None
            assert resolve_row["missing_tenure"] == speaker_row["missing_tenure"] is True
    finally:
        async with AsyncSessionLocal() as db:
            seeded_tenure = await db.get(CourtTenure, tenure_id)
            if seeded_tenure is not None:
                await db.delete(seeded_tenure)
            seeded_participant = await db.get(ArgumentParticipant, participant_id)
            if seeded_participant is not None:
                await db.delete(seeded_participant)
            seeded_job = await db.get(AdminJob, job_id)
            if seeded_job is not None:
                await db.delete(seeded_job)
            seeded_arg = await db.get(Argument, arg_id)
            if seeded_arg is not None:
                await db.delete(seeded_arg)
            seeded_person = await db.get(Person, person_id)
            if seeded_person is not None:
                await db.delete(seeded_person)
            await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_published_argument_bench_role_recomputes_after_tenure_correction() -> None:
    """RESOLVE-11's largest correctness item: leaving the pipeline lifecycle
    state must not freeze the derived bench role. A PUBLISHED argument's
    editable flag stays False throughout, but its bench_role/missing_tenure
    still recompute live after a post-publication tenure correction."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        CourtTenure,
        OFFICE_ASSOCIATE,
        Person,
        SideEnum,
    )
    from api.services.admin_people import list_resolve_rows_for_job

    async with AsyncSessionLocal() as db:
        person = Person(full_name="Justice Published Recompute", is_justice=True)
        db.add(person)
        await db.flush()

        arg = Argument(
            status=ArgumentStatusEnum.PUBLISHED,
            question_number=1,
            argued_date=ARGUED_DATE,
        )
        db.add(arg)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label="JUSTICE PUBLISHED RECOMPUTE",
            side=SideEnum.BENCH,
        )
        db.add(participant)
        await db.flush()

        job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
        db.add(job)
        await db.flush()

        tenure = CourtTenure(person_id=person.id, office=OFFICE_ASSOCIATE, start_date=NOT_COVERING_START)
        db.add(tenure)
        await db.commit()

        person_id = person.id
        arg_id = arg.id
        participant_id = participant.id
        job_id = job.id
        tenure_id = tenure.id

    try:
        async with AsyncSessionLocal() as db:
            rows = await list_resolve_rows_for_job(db, job_id)
            row = next(r for r in rows if r["participant_id"] == participant_id)
            assert row["editable"] is False
            assert row["missing_tenure"] is True
            assert row["bench_role"] is None

        # Correct the tenure in a separate session, after publication.
        async with AsyncSessionLocal() as db:
            t = await db.get(CourtTenure, tenure_id)
            t.start_date = COVERING_START
            await db.commit()

        async with AsyncSessionLocal() as db:
            rows = await list_resolve_rows_for_job(db, job_id)
            row = next(r for r in rows if r["participant_id"] == participant_id)
            assert row["editable"] is False
            assert row["missing_tenure"] is False
            assert row["bench_role"] == office_title(OFFICE_ASSOCIATE)
    finally:
        async with AsyncSessionLocal() as db:
            seeded_tenure = await db.get(CourtTenure, tenure_id)
            if seeded_tenure is not None:
                await db.delete(seeded_tenure)
            seeded_participant = await db.get(ArgumentParticipant, participant_id)
            if seeded_participant is not None:
                await db.delete(seeded_participant)
            seeded_job = await db.get(AdminJob, job_id)
            if seeded_job is not None:
                await db.delete(seeded_job)
            seeded_arg = await db.get(Argument, arg_id)
            if seeded_arg is not None:
                await db.delete(seeded_arg)
            seeded_person = await db.get(Person, person_id)
            if seeded_person is not None:
                await db.delete(seeded_person)
            await db.commit()
