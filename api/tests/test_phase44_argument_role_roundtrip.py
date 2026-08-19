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

Part 3 (DB-gated, added by 44-09's Task 4 second checkpoint remediation,
item 9): an immediate three-step Advocate -> Bench -> Advocate round trip in
one session (no manual page reload) proving the server-side half of the
confirmed descriptor data-loss fix — the client-side half
(`lastDescriptorValue` in ResolveCard.svelte) is covered by a static source
contract in `test_phase44_resolve_table_contract.py`.

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
    # Resolve SideEnum from ResolveRowUpdate's OWN field annotation rather than via
    # a fresh `from api.models.models import SideEnum`. This is the same hazard
    # `pipeline/tests/test_resolve.py` documents for ImportRun (Phase 31, T-31-19):
    # `tests/test_admin_router.py::test_api_main_imports_without_error` deletes every
    # `api.*` entry from sys.modules and re-imports `api.main`, so a fresh import here
    # yields a NEW SideEnum class object while `ResolveRowUpdate` — bound at this
    # module's own import time, above — still carries the OLD one. The values stay
    # equal (str-enum equality is by value) but `isinstance` returns False, which is
    # exactly how this test failed in full-suite order while passing in isolation.
    # `model_fields[...].annotation` is the class the model actually coerces to, so
    # both assertions hold regardless of any mid-session re-import.
    side_enum = ResolveRowUpdate.model_fields["side"].annotation
    assert side_enum is not None

    body = ResolveRowUpdate(participant_id=1, side=value, descriptor=None)
    assert body.side == side_enum(value)
    assert isinstance(body.side, side_enum)


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

        arg = Argument(status=ArgumentStatusEnum.CANDIDATE, question_number=1)
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


# ---------------------------------------------------------------------------
# Part 3 — 44-09 Task 4 checkpoint remediation (item 9): immediate
# Advocate -> Bench -> Advocate round trip, no manual reload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_descriptor_and_specific_role_survive_an_immediate_bench_then_back_toggle() -> None:
    """Confirmed root cause (ResolveCard.svelte descriptorCell): while a row
    is on BENCH, `list_resolve_rows_for_job` correctly reports
    descriptor: null (44-06, by design). Without a client-side memory that
    survives that null read, toggling Advocate -> Bench -> Advocate can
    submit an empty string over an already-saved descriptor in the SAME
    request as the side change (the toggle's own submitRow() flushes and
    submits synchronously, before the operator ever blurs the field).

    This is a backend round-trip proof, not a browser test — this executor
    has no browser/vision tool. It proves the *server* side of the fix: given
    the payloads a correctly-behaving client (one that resubmits its
    memorized descriptor, exactly as ResolveCard.svelte's `lastDescriptorValue`
    now does) would send for each of the three steps, immediately and in one
    session (no manual page reload), the full sequence round-trips both the
    descriptor and the specific advocate role with no data loss. The client
    fix itself — `lastDescriptorValue` preferred over the nullable
    `row.descriptor` prop, captured via oninput so a synchronous toggle-
    triggered submit cannot race ahead of a blur — is covered by the static
    source contract in api/tests/test_phase44_resolve_table_contract.py
    (`test_descriptor_input_uses_a_client_memory_that_survives_side_toggles`);
    together the two tests cover what a live browser session would otherwise
    be needed to prove."""
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
        person = Person(full_name="Immediate Toggle Roundtrip")
        db.add(person)
        await db.flush()

        arg = Argument(status=ArgumentStatusEnum.CANDIDATE, question_number=1)
        db.add(arg)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label="MR. IMMEDIATE TOGGLE",
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
        # Step (a): while Advocate, pick a specific Argument Role and type a
        # Descriptor — mirrors the operator typing "Attorney" while Advocate,
        # then blurring (which saves it).
        step_a = ResolveRowUpdate(
            participant_id=participant_id,
            side=SideEnum.PETITIONER,
            descriptor="Attorney",
        )
        async with AsyncSessionLocal() as db:
            updated_a = await update_resolve_row_for_job(db, job_id, step_a)
            assert updated_a.side == SideEnum.PETITIONER
            assert updated_a.descriptor == "Attorney"

        async with AsyncSessionLocal() as db:
            rows = await list_resolve_rows_for_job(db, job_id)
            row_a = next(r for r in rows if r["raw_speaker_label"] == "MR. IMMEDIATE TOGGLE")
            assert row_a["side"] == "PETITIONER"
            assert row_a["argument_role"] == "Petitioner's Counsel"
            assert row_a["descriptor"] == "Attorney"

        # Step (b): toggle to Bench. The client's own descriptor input still
        # shows "Attorney" at the instant of this submit (the null read-back
        # only happens on the NEXT read), but it does not matter either way —
        # the server drops a client-supplied descriptor whenever side==BENCH
        # (44-06/RESOLVE-13), so the stored "Attorney" survives regardless of
        # what the client sends here.
        step_b = ResolveRowUpdate(
            participant_id=participant_id,
            side=SideEnum.BENCH,
            descriptor="Attorney",
        )
        async with AsyncSessionLocal() as db:
            updated_b = await update_resolve_row_for_job(db, job_id, step_b)
            assert updated_b.side == SideEnum.BENCH
            assert updated_b.descriptor == "Attorney"

        async with AsyncSessionLocal() as db:
            rows = await list_resolve_rows_for_job(db, job_id)
            row_b = next(r for r in rows if r["raw_speaker_label"] == "MR. IMMEDIATE TOGGLE")
            assert row_b["side"] == "BENCH"
            # 44-06/RESOLVE-13: the read path reports descriptor: null while
            # BENCH by design ("hidden, not shown") — this is exactly the
            # null read-back the client-side fix (lastDescriptorValue) exists
            # to survive.
            assert row_b["descriptor"] is None

        # Step (c): toggle back to Advocate, immediately (same session, no
        # manual reload). A client with the fixed `lastDescriptorValue`
        # memory resubmits "Attorney" (its last-known value) in the SAME
        # request as the side change, rather than the empty string the
        # now-null `row.descriptor` prop would otherwise have bound the
        # reappearing <input> to.
        step_c = ResolveRowUpdate(
            participant_id=participant_id,
            side=SideEnum.PETITIONER,
            descriptor="Attorney",
        )
        async with AsyncSessionLocal() as db:
            updated_c = await update_resolve_row_for_job(db, job_id, step_c)
            assert updated_c.side == SideEnum.PETITIONER
            assert updated_c.descriptor == "Attorney"

        async with AsyncSessionLocal() as db:
            rows = await list_resolve_rows_for_job(db, job_id)
            row_c = next(r for r in rows if r["raw_speaker_label"] == "MR. IMMEDIATE TOGGLE")
            # Both halves of item 9 verified in one immediate round trip: the
            # specific advocate role (a pure client-memory restore,
            # lastAdvocateRole, already correct pre-remediation) and the
            # descriptor (the confirmed data-loss bug, now fixed) both
            # survive Bench -> Advocate with no manual reload.
            assert row_c["side"] == "PETITIONER"
            assert row_c["argument_role"] == "Petitioner's Counsel"
            assert row_c["descriptor"] == "Attorney"
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
