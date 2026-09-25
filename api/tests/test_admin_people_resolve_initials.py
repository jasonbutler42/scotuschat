"""
Phase 52 Plan 06 — ResolveRow.initials, sourced from the one existing
derive_initials implementation (D-12/D-13, JUSTICE-06).

Converges the last surviving client-side initials splitter
(app/src/lib/admin/ResolveCard.svelte's getInitials, found during 52-02's
structural ban sweep) onto api.domain.person_names.derive_initials, the same
function 52-02 wired into SpeakerPopoverEntry.initials and
UtteranceResponse.speaker_initials.

Covers the four <behavior> bullets from 52-06-PLAN.md Task 1:
  1. Structured name parts -> derive_initials over those parts, suffix ignored.
  2. full_name only (no structured parts) -> derive_initials's D-13 fallback.
  3. Unresolved row (person_id is None) -> initials is None.
  4. initials is read-only (absent from every write schema on this surface).

Asserts against list_resolve_rows_for_job's real output — never by re-calling
derive_initials in the test and comparing it to itself (per the plan's
explicit instruction).
"""

import os

import pytest


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


# ---------------------------------------------------------------------------
# Schema test (no DB required)
# ---------------------------------------------------------------------------


def test_resolve_row_schema_carries_initials_field() -> None:
    """ResolveRow exposes initials: Optional[str], accepting both a populated
    value and the unresolved-row default of None."""
    from api.models.models import SideEnum
    from api.schemas.admin_people import ResolveRow

    resolved = ResolveRow(
        participant_id=1,
        raw_speaker_label="MR. HARLAN",
        person_id=5,
        full_name="John Marshall Harlan, II",
        side=SideEnum.BENCH,
        initials="JH",
    )
    assert resolved.initials == "JH"

    unresolved = ResolveRow(
        participant_id=2,
        raw_speaker_label="UNKNOWN SPEAKER",
        side=SideEnum.UNKNOWN,
    )
    assert unresolved.initials is None


def test_resolve_row_update_schema_has_no_initials_field() -> None:
    """initials must never be writable — it is not on the request schema for
    this surface (there is no ResolveRow write schema; ResolveRowUpdate is
    the write path and must not gain this field)."""
    from api.schemas.admin_jobs import ResolveRowUpdate

    assert "initials" not in ResolveRowUpdate.model_fields


# ---------------------------------------------------------------------------
# DB-guarded behavioral tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_initials_from_structured_parts_ignores_suffix(db_session) -> None:
    """Behavior bullet 1: a suffixed person (structured parts present) yields
    first-initial + surname-initial — JH for John Marshall Harlan, II, not JI
    (name_suffix is accepted by derive_initials and deliberately ignored)."""
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
    from api.services.admin_people import list_resolve_rows_for_job

    person = Person(
        full_name="John Marshall Harlan, II",
        first_name="John",
        middle_name="Marshall",
        last_name="Harlan",
        name_suffix="II",
    )
    db_session.add(person)
    await db_session.flush()

    arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
    db_session.add(arg)
    await db_session.flush()

    participant = ArgumentParticipant(
        argument_id=arg.id,
        person_id=person.id,
        raw_speaker_label="JUSTICE HARLAN",
        side=SideEnum.BENCH,
    )
    db_session.add(participant)
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
    db_session.add(job)
    await db_session.flush()

    rows = await list_resolve_rows_for_job(db_session, job.id)

    assert len(rows) == 1
    assert rows[0]["initials"] == "JH"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_initials_from_full_name_when_no_structured_parts(db_session) -> None:
    """Behavior bullet 2: a person with only a full_name (no structured parts)
    still renders correctly via derive_initials's D-13 legacy fallback — this
    surface must not regress anyone who renders correctly today."""
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
    from api.services.admin_people import list_resolve_rows_for_job

    person = Person(full_name="Jane Q. Advocate")
    db_session.add(person)
    await db_session.flush()

    arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
    db_session.add(arg)
    await db_session.flush()

    participant = ArgumentParticipant(
        argument_id=arg.id,
        person_id=person.id,
        raw_speaker_label="MS. ADVOCATE",
        side=SideEnum.PETITIONER,
    )
    db_session.add(participant)
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
    db_session.add(job)
    await db_session.flush()

    rows = await list_resolve_rows_for_job(db_session, job.id)

    assert len(rows) == 1
    assert rows[0]["initials"] == "JA"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_initials_null_for_unresolved_row(db_session) -> None:
    """Behavior bullet 3: an unresolved row (person_id is None) yields a null
    initials — no fabricated glyph for a row that has no committed person."""
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        SideEnum,
    )
    from api.services.admin_people import list_resolve_rows_for_job

    arg = Argument(status=ArgumentStatusEnum.PIPELINE, question_number=1)
    db_session.add(arg)
    await db_session.flush()

    participant = ArgumentParticipant(
        argument_id=arg.id,
        person_id=None,
        raw_speaker_label="UNRESOLVED SPEAKER",
        side=SideEnum.UNKNOWN,
    )
    db_session.add(participant)
    await db_session.flush()

    job = AdminJob(status=AdminJobStatus.PAUSED, current_step=AdminJobStep.RESOLVE, argument_id=arg.id)
    db_session.add(job)
    await db_session.flush()

    rows = await list_resolve_rows_for_job(db_session, job.id)

    assert len(rows) == 1
    assert rows[0]["person_id"] is None
    assert rows[0]["initials"] is None
