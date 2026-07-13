"""
Tests for the Phase 28 dashboard aggregation service functions (DASH-01, DASH-03).

Covers the seven new service functions:
  - admin_arguments.get_argument_stats / get_recent_drafts / get_utterance_count
  - admin_jobs.get_pipeline_stats
  - admin_people.get_people_stats / get_incomplete_people / get_tenure_gap_justices

Fixture-scoping rule (the DB holds ~7,800 real corpus-imported Argument/Utterance
rows from Phases 29/30, plus ~328 real Person rows from Phase 27/29-03 in these
same tables):
  - Whole-table aggregates (get_argument_stats, get_utterance_count,
    get_pipeline_stats.recent_count, get_people_stats) are asserted via
    AFTER-minus-BEFORE deltas against a baseline captured before seeding —
    never a raw absolute count.
  - Top-5 list functions (get_recent_drafts, get_incomplete_people,
    get_tenure_gap_justices) tag every seeded fixture with a unique,
    run-scoped marker token and filter the returned rows to that marker
    before asserting count/order/cap. Marker rows use a full_name/docket_number
    prefix ("0" + token) chosen to sort before every existing ambient row
    under list_people's/get_recent_drafts' ascending ordering (verified: no
    ambient row's sort key currently precedes "A", so a "0"-prefixed marker
    always sorts first and is guaranteed to land inside a top-5 window).

DB-gated: every test below is skipped when DATABASE_URL is not configured.
"""

import os
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db_configured() -> bool:
    """Same guard every api/tests DB-gated fixture uses."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


def _token() -> str:
    """Short unique run-scoped marker (fits String(50) docket_number columns)."""
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# admin_arguments.get_argument_stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_argument_stats_delta_and_pipeline_exclusion(db_session: AsyncSession) -> None:
    """Seeding 3 draft + 8 published + 2 unpublished + 2 pipeline rows moves
    total/published/draft/unpublished by exactly the non-pipeline delta; the
    2 pipeline rows change none of the four fields (ALIST-02, DASH-01)."""
    from api.models.models import Argument, ArgumentStatusEnum
    from api.services.admin_arguments import get_argument_stats

    baseline = await get_argument_stats(db_session)

    for _ in range(3):
        db_session.add(Argument(status=ArgumentStatusEnum.DRAFT))
    for _ in range(8):
        db_session.add(Argument(status=ArgumentStatusEnum.PUBLISHED))
    for _ in range(2):
        db_session.add(Argument(status=ArgumentStatusEnum.UNPUBLISHED))
    for _ in range(2):
        db_session.add(Argument(status=ArgumentStatusEnum.PIPELINE))
    await db_session.flush()

    after = await get_argument_stats(db_session)

    assert after["draft"] == baseline["draft"] + 3
    assert after["published"] == baseline["published"] + 8
    assert after["unpublished"] == baseline["unpublished"] + 2
    # PIPELINE rows must not appear in total (ALIST-02 parity)
    assert after["total"] == baseline["total"] + 13


# ---------------------------------------------------------------------------
# admin_arguments.get_recent_drafts
# ---------------------------------------------------------------------------


async def _seed_lead_case_argument(
    db_session: AsyncSession, *, docket_number: str, status
):
    """Create a bare Argument + lead Case + CaseArgument row, return the Argument."""
    from api.models.models import Argument, Case, CaseArgument

    arg = Argument(status=status)
    db_session.add(arg)
    await db_session.flush()

    case = Case(
        docket_number=docket_number,
        docket_number_norm=docket_number.lower(),
        case_name=f"Synthetic Case {docket_number}",
        term_year=2026,
        slug=f"synthetic-case-{docket_number.lower()}",
    )
    db_session.add(case)
    await db_session.flush()

    db_session.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))
    await db_session.flush()
    return arg


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_recent_drafts_caps_at_five_ordered_by_id_desc(
    db_session: AsyncSession,
) -> None:
    """7 marker-tagged DRAFT arguments seeded -> exactly 5 marked rows returned,
    highest id first (Pitfall 3: ordered by Argument.id DESC, not resolved_at)."""
    from api.models.models import ArgumentStatusEnum
    from api.services.admin_arguments import get_recent_drafts

    token = _token()
    seeded_ids: list[int] = []
    for i in range(7):
        arg = await _seed_lead_case_argument(
            db_session,
            docket_number=f"0{token}-{i}",
            status=ArgumentStatusEnum.DRAFT,
        )
        seeded_ids.append(arg.id)

    rows = await get_recent_drafts(db_session, limit=5)
    marked = [r for r in rows if r["docket_number"].startswith(f"0{token}")]

    assert len(marked) == 5, (
        f"Expected 5 marker-tagged rows in the top-5 window, got {len(marked)}"
    )
    expected_top5 = sorted(seeded_ids, reverse=True)[:5]
    assert [r["id"] for r in marked] == expected_top5, (
        "Marked rows must be ordered by Argument.id DESC and limited to the "
        "5 highest-id seeded drafts"
    )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_recent_drafts_no_marker_rows_when_none_seeded(
    db_session: AsyncSession,
) -> None:
    """No drafts seeded under this token -> no marker-tagged rows appear (D-03: no
    age threshold does not mean an empty result set given ambient corpus drafts)."""
    from api.services.admin_arguments import get_recent_drafts

    token = _token()
    rows = await get_recent_drafts(db_session, limit=5)
    marked = [r for r in rows if r["docket_number"].startswith(f"0{token}")]
    assert marked == []


# ---------------------------------------------------------------------------
# admin_arguments.get_utterance_count
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_utterance_count_counts_every_status(db_session: AsyncSession) -> None:
    """Utterances under a PIPELINE argument and an UNPUBLISHED argument both count
    toward the total (A3, DASH-01) — the function never filters by argument status."""
    from api.models.models import Argument, ArgumentStatusEnum, PipelineRun, Utterance
    from api.services.admin_arguments import get_utterance_count

    baseline = await get_utterance_count(db_session)

    pipeline_arg = Argument(status=ArgumentStatusEnum.PIPELINE)
    db_session.add(pipeline_arg)
    await db_session.flush()
    pipeline_run = PipelineRun(argument_id=pipeline_arg.id, step="parse")
    db_session.add(pipeline_run)
    await db_session.flush()
    for i in range(3):
        db_session.add(
            Utterance(
                argument_id=pipeline_arg.id,
                pipeline_run_id=pipeline_run.id,
                sequence=i,
                text=f"Pipeline utterance {i}",
                strategy="rule_based",
            )
        )

    unpub_arg = Argument(status=ArgumentStatusEnum.UNPUBLISHED)
    db_session.add(unpub_arg)
    await db_session.flush()
    unpub_run = PipelineRun(argument_id=unpub_arg.id, step="parse")
    db_session.add(unpub_run)
    await db_session.flush()
    for i in range(2):
        db_session.add(
            Utterance(
                argument_id=unpub_arg.id,
                pipeline_run_id=unpub_run.id,
                sequence=i,
                text=f"Unpublished utterance {i}",
                strategy="rule_based",
            )
        )
    await db_session.flush()

    after = await get_utterance_count(db_session)
    assert after == baseline + 5


# ---------------------------------------------------------------------------
# admin_jobs.get_pipeline_stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_pipeline_stats_30_day_window_and_last_activity(
    db_session: AsyncSession,
) -> None:
    """A job created within 30 days increments recent_count and becomes the new
    last_activity_at MAX; a job created 40 days ago is excluded from recent_count
    but does not corrupt the MAX (A1)."""
    from api.models.models import AdminJob, AdminJobStatus, AdminJobStep
    from api.services.admin_jobs import get_pipeline_stats

    baseline = await get_pipeline_stats(db_session)

    now = datetime.now(timezone.utc)
    # Sentinel far in the future so this row is unambiguously the new global MAX
    # regardless of any ambient admin_jobs row's updated_at.
    future_activity = now + timedelta(days=3650)

    recent_job = AdminJob(
        status=AdminJobStatus.PENDING,
        current_step=AdminJobStep.INGEST,
        updated_at=future_activity,
    )
    db_session.add(recent_job)

    old_job = AdminJob(
        status=AdminJobStatus.PENDING,
        current_step=AdminJobStep.INGEST,
        created_at=now - timedelta(days=40),
        updated_at=now - timedelta(days=40),
    )
    db_session.add(old_job)
    await db_session.flush()

    after = await get_pipeline_stats(db_session)

    # Only recent_job (created "now", server_default) falls inside the 30-day window.
    assert after["recent_count"] == baseline["recent_count"] + 1
    assert after["last_activity_at"] == future_activity


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_pipeline_stats_empty_delta_when_nothing_seeded(
    db_session: AsyncSession,
) -> None:
    """Calling get_pipeline_stats twice with no seeding in between returns an
    identical result (no hidden mutation, no drift from the empty-table contract)."""
    from api.services.admin_jobs import get_pipeline_stats

    first = await get_pipeline_stats(db_session)
    second = await get_pipeline_stats(db_session)
    assert first == second


# ---------------------------------------------------------------------------
# admin_people.get_people_stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_people_stats_delta(db_session: AsyncSession) -> None:
    """Seeding 10 people (4 incomplete, 6 fully complete) moves total by 10 and
    incomplete by exactly 4 (DASH-01)."""
    from api.models.models import Person
    from api.services.admin_people import get_people_stats

    token = _token()
    baseline = await get_people_stats(db_session)

    for i in range(4):
        db_session.add(
            Person(
                full_name=f"0{token}-Incomplete-{i}",
                is_justice=False,
                first_name=None,
                last_name=None,
                photo_url=None,
                bio_text=None,
            )
        )
    for i in range(6):
        db_session.add(
            Person(
                full_name=f"0{token}-Complete-{i}",
                first_name="Test",
                last_name=f"Complete{i}",
                is_justice=False,
                photo_url="https://example.test/photo.jpg",
                bio_text="Bio text.",
            )
        )
    await db_session.flush()

    after = await get_people_stats(db_session)
    assert after["total"] == baseline["total"] + 10
    assert after["incomplete"] == baseline["incomplete"] + 4


# ---------------------------------------------------------------------------
# admin_people.get_incomplete_people
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_incomplete_people_combined_top_five(db_session: AsyncSession) -> None:
    """8 incomplete people seeded across both tabs -> exactly 5 marker-tagged rows
    returned, combined (not split by tab, D-02). Marker full_names are prefixed
    with a digit so they sort before every ambient row under list_people's
    ascending COALESCE(last_name, full_name) ordering."""
    from api.models.models import Person
    from api.services.admin_people import get_incomplete_people

    token = _token()
    for i in range(4):
        db_session.add(
            Person(
                full_name=f"0{token}-Bench-{i}",
                is_justice=True,
                first_name=None,
                last_name=None,
                photo_url=None,
                bio_text=None,
            )
        )
    for i in range(4):
        db_session.add(
            Person(
                full_name=f"0{token}-Advocate-{i}",
                is_justice=False,
                first_name=None,
                last_name=None,
                photo_url=None,
                bio_text=None,
            )
        )
    await db_session.flush()

    rows = await get_incomplete_people(db_session, limit=5)
    marked = [r for r in rows if r["full_name"].startswith(f"0{token}")]

    assert len(marked) == 5, f"Expected 5 marker-tagged rows, got {len(marked)}"
    tabs_present = {r["is_justice"] for r in marked}
    assert tabs_present == {True, False}, (
        "Combined People sub-list must include both tabs, not just one (D-02)"
    )


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_incomplete_people_no_marker_when_all_complete(
    db_session: AsyncSession,
) -> None:
    """Marker-tagged people that are fully complete never appear in the
    incomplete sub-list, regardless of the top-5 window."""
    from api.models.models import Person
    from api.services.admin_people import get_incomplete_people

    token = _token()
    for i in range(3):
        db_session.add(
            Person(
                full_name=f"0{token}-Complete-{i}",
                first_name="Test",
                last_name=f"Complete{i}",
                is_justice=False,
                photo_url="https://example.test/photo.jpg",
                bio_text="Bio text.",
            )
        )
    await db_session.flush()

    rows = await get_incomplete_people(db_session, limit=5)
    marked = [r for r in rows if r["full_name"].startswith(f"0{token}")]
    assert marked == []


# ---------------------------------------------------------------------------
# admin_people.get_tenure_gap_justices
# ---------------------------------------------------------------------------


async def _seed_tenure_gap_justice(db_session: AsyncSession, *, full_name: str):
    """Seed a Justice Person with a CourtTenure that does NOT cover an
    ArgumentParticipant's argued_date, producing a tenure gap (D-15/D-06)."""
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        CourtTenure,
        Person,
        SideEnum,
    )

    person = Person(full_name=full_name, is_justice=True)
    db_session.add(person)
    await db_session.flush()

    # Tenure covers 2000-2010; argued_date below (2015) falls outside it.
    db_session.add(
        CourtTenure(
            person_id=person.id,
            seat="Associate Justice",
            start_date=date(2000, 1, 1),
            end_date=date(2010, 1, 1),
        )
    )
    arg = Argument(status=ArgumentStatusEnum.DRAFT, argued_date=date(2015, 1, 1))
    db_session.add(arg)
    await db_session.flush()
    db_session.add(
        ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label=full_name,
            side=SideEnum.BENCH,
        )
    )
    await db_session.flush()
    return person


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_tenure_gap_justices_combined_top_five(db_session: AsyncSession) -> None:
    """6 tenure-gap justices seeded -> exactly 5 marker-tagged rows returned;
    no advocates ever appear (D-06 delegates to list_people(is_justice=True,
    tenure_gaps=True))."""
    from api.services.admin_people import get_tenure_gap_justices

    token = _token()
    for i in range(6):
        await _seed_tenure_gap_justice(db_session, full_name=f"0{token}-Gap-{i}")

    rows = await get_tenure_gap_justices(db_session, limit=5)
    marked = [r for r in rows if r["full_name"].startswith(f"0{token}")]

    assert len(marked) == 5, f"Expected 5 marker-tagged rows, got {len(marked)}"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_tenure_gap_justices_no_marker_when_tenure_covers_argued_date(
    db_session: AsyncSession,
) -> None:
    """A justice whose tenure fully covers their argued_date has no gap and
    never appears in the tenure-gap sub-list."""
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        CourtTenure,
        Person,
        SideEnum,
    )
    from api.services.admin_people import get_tenure_gap_justices

    token = _token()
    person = Person(full_name=f"0{token}-NoGap", is_justice=True)
    db_session.add(person)
    await db_session.flush()

    db_session.add(
        CourtTenure(
            person_id=person.id,
            seat="Associate Justice",
            start_date=date(2000, 1, 1),
            end_date=None,  # currently active — covers any argued_date after 2000
        )
    )
    arg = Argument(status=ArgumentStatusEnum.DRAFT, argued_date=date(2015, 1, 1))
    db_session.add(arg)
    await db_session.flush()
    db_session.add(
        ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label=f"0{token}-NoGap",
            side=SideEnum.BENCH,
        )
    )
    await db_session.flush()

    rows = await get_tenure_gap_justices(db_session, limit=5)
    marked = [r for r in rows if r["full_name"].startswith(f"0{token}")]
    assert marked == []
