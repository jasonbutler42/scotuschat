"""
Phase 44 Plan 03 — Argument Role dropdown backend proof.

Part 1 (no DB, no gate): parametrised over the four dropdown values, proving
`ResolveRowUpdate` accepts each and coerces `side` to the matching `SideEnum`
member, and that a value outside the enum raises `pydantic.ValidationError`
(T-44-03) — the dropdown's option list is a convenience, the enum is the
enforcement boundary.

Part 2 (DB-gated): a write-then-read round trip through
`update_resolve_row_for_job` + `list_resolve_rows_for_job` for each of the
three real advocate roles (RESOLVE-03), plus a re-assertion at the
round-trip level that a BENCH payload leaves the already-stored descriptor
untouched rather than forcing it to null (RESOLVE-13, superseding PJOB-15's
storage half — see `api/tests/test_admin_jobs_phase25.py`'s inverted bench
test for the canonical version of this assertion).

Following the project pattern (`test_admin_people_phase25.py`,
`test_admin_jobs_phase25.py`):
  - Schema/pure-function tests run without a database.
  - Behavioral tests that need real rows are gated behind a DATABASE_URL
    skipif via a local `_db_configured()` helper.
  - `update_resolve_row_for_job` commits internally, so behavioral tests use
    `AsyncSessionLocal()` directly rather than the shared `db_session`
    fixture (mirrors `test_admin_jobs_phase25.py`'s own round-trip test),
    and clean up their seeded rows manually rather than relying on rollback.
"""

import os

import pytest
from pydantic import ValidationError

from api.schemas.admin_jobs import ResolveRowUpdate


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


# ---------------------------------------------------------------------------
# Part 1 — pure schema, no DB, no gate (T-44-03)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["UNKNOWN", "PETITIONER", "RESPONDENT", "AMICUS"],
)
def test_resolve_row_update_accepts_each_dropdown_value_and_coerces_enum(value: str) -> None:
    from api.models.models import SideEnum

    body = ResolveRowUpdate(participant_id=1, side=value, descriptor=None)
    assert body.side == SideEnum(value)
    assert isinstance(body.side, SideEnum)


def test_resolve_row_update_rejects_out_of_enum_side_value() -> None:
    """T-44-03: a crafted request carrying a side value outside SideEnum is
    rejected by Pydantic before it reaches the ORM — the dropdown's option
    list is a convenience, never the enforcement boundary."""
    with pytest.raises(ValidationError):
        ResolveRowUpdate(participant_id=1, side="ANARCHIST", descriptor=None)


# ---------------------------------------------------------------------------
# Part 2 — DB-gated round trip (RESOLVE-03)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
@pytest.mark.parametrize(
    "side_value,expected_label",
    [
        ("PETITIONER", "Petitioner's Counsel"),
        ("RESPONDENT", "Respondent's Counsel"),
        ("AMICUS", "Amicus Curiae"),
    ],
)
async def test_argument_role_round_trips_for_each_real_advocate_role(
    side_value: str, expected_label: str
) -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Person,
        SideEnum,
    )
    from api.services.admin_jobs import update_resolve_row_for_job
    from api.services.admin_people import list_resolve_rows_for_job

    async with AsyncSessionLocal() as db:
        person = Person(full_name=f"Argument Role Roundtrip {side_value}")
        db.add(person)
        await db.flush()

        arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
        db.add(arg)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label=f"MR. ROUNDTRIP {side_value}",
            side=SideEnum.UNKNOWN,
        )
        db.add(participant)
        await db.flush()

        job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
        db.add(job)
        await db.commit()

        person_id = person.id
        arg_id = arg.id
        participant_id = participant.id
        job_id = job.id

    try:
        # Write: set the row to the real advocate role via the same job-scoped
        # write path ResolveCard.svelte's per-row form submits through.
        advocate_body = ResolveRowUpdate(
            participant_id=participant_id,
            side=SideEnum(side_value),
            descriptor="Counsel of Record",
        )
        async with AsyncSessionLocal() as db:
            updated = await update_resolve_row_for_job(db, job_id, advocate_body)
            assert updated.side == SideEnum(side_value)
            assert updated.descriptor == "Counsel of Record"

        # Read: list_resolve_rows_for_job must project the matching
        # ADVOCATE_LABEL_MAP label in argument_role and the same enum value
        # (as its .value string) in side.
        async with AsyncSessionLocal() as db:
            rows = await list_resolve_rows_for_job(db, job_id)
            row = next(r for r in rows if r["raw_speaker_label"] == f"MR. ROUNDTRIP {side_value}")
            assert row["side"] == side_value
            assert row["argument_role"] == expected_label
            assert row["descriptor"] == "Counsel of Record"

        # RESOLVE-13 re-assertion at the round-trip level: a BENCH payload
        # carrying a different descriptor must NOT overwrite the value the
        # row already has ("Counsel of Record", set above) — the client's
        # bench descriptor is ignored, and the stored value is preserved.
        bench_body = ResolveRowUpdate(
            participant_id=participant_id,
            side=SideEnum.BENCH,
            descriptor="Should not be written",
        )
        async with AsyncSessionLocal() as db:
            updated_bench = await update_resolve_row_for_job(db, job_id, bench_body)
            assert updated_bench.side == SideEnum.BENCH
            assert updated_bench.descriptor == "Counsel of Record"
    finally:
        async with AsyncSessionLocal() as db:
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
