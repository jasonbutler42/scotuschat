"""
End-to-end integration test for the Phase 49 review-queue tracer (plan 49-01).

Covers the plan's six `<behavior>` bullets:
  1. GET /api/admin/review/arguments returns a CANDIDATE argument carrying a
     needs_review participant exactly once, with that participant listed as
     a constituent.
  2. PATCH /api/admin/review/participants/{id} with {"action": "confirm"}
     sets review_state='operator_confirmed' and returns 200.
  3. After that PATCH, the owning arguments.trust_tier reflects a fresh
     recompute in the same transaction (derive_tier's rule 1: an
     operator_confirmed review_state floors to VERIFIED regardless of
     source/method).
  4. A participant id that does not exist -> PATCH returns 404.
  5. An argument with zero utterances and zero participants -> recompute
     stores UNCERTAIN (floor_tier([])'s explicit early return), never an
     exception.
  6. Given nothing flagged, the list endpoint returns 200 (never 404) and
     excludes a healthy (trusted, fully resolved, unflagged) argument.

Also covers the two defects found at the Task 1 tracer feedback gate
(human browser test of /admin/review):
  - Defect 1: constituent order is stable across a write to one row (a
    deterministic ordering on ArgumentParticipant.side/id, not physical
    write order).
  - Defect 2a: Confirm is rejected (422) on a participant whose person_id
    IS NULL — it can never clear that leg, so allowing it would be a
    permanent no-op.
  - Defect 2b: the queue payload carries admin_job_id (nullable, and never
    a row-multiplying join) so the frontend can route an unresolved
    speaker to the real resolve flow.

Follows this repo's established DB-gated integration pattern
(api/tests/test_admin_arguments_routes.py's publish-route tests): seed via
a bare AsyncSessionLocal (uncommitted state is invisible to the app's own
request-scoped sessions), exercise the real router through an ASGI
TestClient (so the router's own dependency/error-mapping code runs, not a
mock), then tear down explicitly. `resolve_participant_review` commits
internally (see api/services/admin_review.py's module docstring) — that is
exactly why this file uses raw AsyncSessionLocal rather than the
`db_session` fixture's begin()/rollback() wrapper, mirroring why
test_admin_arguments_service.py's publish_argument tests do the same.
"""

import os

import pytest
import pytest_asyncio


def _db_configured() -> bool:
    """Same guard every DB-gated api/tests module uses (WR-04)."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


def _admin_headers() -> dict:
    from api.core.config import settings

    return {"X-Admin-Token": settings.admin_token}


# ---------------------------------------------------------------------------
# Seed / teardown helpers
# ---------------------------------------------------------------------------


async def _seed_needs_review_participant():
    """One CANDIDATE argument, a lead Case, a resolved Person, and one
    ArgumentParticipant flagged review_state=NEEDS_REVIEW. Zero utterances —
    the participant is this argument's only constituent, so the argument's
    stored trust_tier (server_default) is already UNCERTAIN, matching what
    derive_tier would compute for a needs_review participant anyway."""
    import uuid as _uuid

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Case,
        CaseArgument,
        Person,
        ReviewState,
        SideEnum,
    )

    suffix = _uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.CANDIDATE)
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number=f"RV-01-{suffix}",
            docket_number_norm=f"rv-01-{suffix}",
            case_name="Review Fixture v. Needs Review",
            term_year=2026,
            slug=f"review-fixture-needs-review-{suffix}",
        )
        db.add(case)
        await db.flush()
        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))

        person = Person(full_name="Review Fixture Advocate")
        db.add(person)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label="MR. FIXTURE",
            side=SideEnum.PETITIONER,
            review_state=ReviewState.NEEDS_REVIEW,
        )
        db.add(participant)
        await db.commit()

        return {
            "argument_id": arg.id,
            "case_id": case.id,
            "person_id": person.id,
            "participant_id": participant.id,
        }


async def _teardown_needs_review_participant(ids: dict) -> None:
    from sqlalchemy import delete as sa_delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentParticipant, Case, CaseArgument, Person

    async with AsyncSessionLocal() as db:
        await db.execute(
            sa_delete(ArgumentParticipant).where(ArgumentParticipant.id == ids["participant_id"])
        )
        await db.execute(
            sa_delete(CaseArgument).where(CaseArgument.argument_id == ids["argument_id"])
        )
        await db.execute(sa_delete(Case).where(Case.id == ids["case_id"]))
        await db.execute(sa_delete(Person).where(Person.id == ids["person_id"]))
        await db.execute(sa_delete(Argument).where(Argument.id == ids["argument_id"]))
        await db.commit()


async def _seed_healthy_trusted_argument():
    """One PUBLISHED-eligible argument with a single resolved, UNREVIEWED,
    corpus/direct participant — a TRUSTED tier, never flagged. Used to prove
    the queue does NOT falsely include a healthy argument (behavior bullet
    6)."""
    import uuid as _uuid

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Case,
        CaseArgument,
        ImportSource,
        ImportMethod,
        Person,
        ReviewState,
        SideEnum,
    )
    from api.services.trust import recompute_argument_tier

    suffix = _uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.DRAFT)
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number=f"RV-02-{suffix}",
            docket_number_norm=f"rv-02-{suffix}",
            case_name="Review Fixture v. Healthy Argument",
            term_year=2026,
            slug=f"review-fixture-healthy-argument-{suffix}",
        )
        db.add(case)
        await db.flush()
        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))

        person = Person(full_name="Review Fixture Healthy Advocate")
        db.add(person)
        await db.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label="MS. HEALTHY",
            side=SideEnum.RESPONDENT,
            review_state=ReviewState.UNREVIEWED,
            source=ImportSource.CORPUS,
            method=ImportMethod.DIRECT,
        )
        db.add(participant)
        await db.flush()

        await recompute_argument_tier(db, arg.id)
        await db.commit()

        return {"argument_id": arg.id, "case_id": case.id, "person_id": person.id}


async def _teardown_healthy_trusted_argument(ids: dict) -> None:
    from sqlalchemy import delete as sa_delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentParticipant, Case, CaseArgument, Person

    async with AsyncSessionLocal() as db:
        await db.execute(
            sa_delete(ArgumentParticipant).where(ArgumentParticipant.argument_id == ids["argument_id"])
        )
        await db.execute(
            sa_delete(CaseArgument).where(CaseArgument.argument_id == ids["argument_id"])
        )
        await db.execute(sa_delete(Case).where(Case.id == ids["case_id"]))
        await db.execute(sa_delete(Person).where(Person.id == ids["person_id"]))
        await db.execute(sa_delete(Argument).where(Argument.id == ids["argument_id"]))
        await db.commit()


@pytest_asyncio.fixture
async def review_client():
    from httpx import ASGITransport, AsyncClient
    from api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Behavior 1 — GET /arguments returns the flagged argument exactly once,
# with the needs_review participant listed as a constituent.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_get_review_queue_returns_flagged_argument_once_with_constituent(
    review_client,
) -> None:
    ids = await _seed_needs_review_participant()
    try:
        response = await review_client.get(
            "/api/admin/review/arguments", headers=_admin_headers()
        )
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)

        matches = [item for item in body if item["id"] == ids["argument_id"]]
        assert len(matches) == 1, "argument must appear exactly once (D-05)"

        item = matches[0]
        participant_ids = [c["participant_id"] for c in item["constituents"]]
        assert ids["participant_id"] in participant_ids
        constituent = next(
            c for c in item["constituents"] if c["participant_id"] == ids["participant_id"]
        )
        assert constituent["review_state"] == "needs_review"
        assert item["attention_count"] >= 1
    finally:
        await _teardown_needs_review_participant(ids)


# ---------------------------------------------------------------------------
# Behaviors 2 + 3 — PATCH confirm advances review_state and recomputes the
# argument's trust_tier in the same transaction.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_patch_confirm_advances_review_state_and_recomputes_tier(
    review_client,
) -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentParticipant
    from api.domain.trust import TrustTier

    ids = await _seed_needs_review_participant()
    try:
        response = await review_client.patch(
            f"/api/admin/review/participants/{ids['participant_id']}",
            json={"action": "confirm"},
            headers=_admin_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["review_state"] == "operator_confirmed"

        async with AsyncSessionLocal() as db:
            participant = await db.get(ArgumentParticipant, ids["participant_id"])
            argument = await db.get(Argument, ids["argument_id"])
            assert participant.review_state.value == "operator_confirmed"
            # derive_tier rule 1: operator_confirmed -> VERIFIED, regardless
            # of the (absent) source/method — the recompute must have run
            # in the same transaction as the PATCH's own commit.
            assert argument.trust_tier == TrustTier.VERIFIED
    finally:
        await _teardown_needs_review_participant(ids)


# ---------------------------------------------------------------------------
# Behavior 4 — a nonexistent participant id returns 404.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_patch_confirm_missing_participant_returns_404(review_client) -> None:
    response = await review_client.patch(
        "/api/admin/review/participants/999999999",
        json={"action": "confirm"},
        headers=_admin_headers(),
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Behavior 5 — zero-constituent recompute stores UNCERTAIN, never raises.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_recompute_zero_constituents_stores_uncertain_no_exception() -> None:
    from sqlalchemy import delete as sa_delete

    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ArgumentStatusEnum
    from api.services.trust import recompute_argument_tier

    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.CANDIDATE)
        db.add(arg)
        await db.commit()
        arg_id = arg.id

    async with AsyncSessionLocal() as db:
        result = await recompute_argument_tier(db, arg_id)
        await db.commit()
    assert result == TrustTier.UNCERTAIN

    async with AsyncSessionLocal() as db:
        stored = await db.get(Argument, arg_id)
        assert stored.trust_tier == TrustTier.UNCERTAIN
        await db.execute(sa_delete(Argument).where(Argument.id == arg_id))
        await db.commit()


# ---------------------------------------------------------------------------
# Behavior 6 — nothing flagged -> 200 (never 404), healthy argument excluded.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_list_review_queue_returns_200_and_excludes_healthy_argument(
    review_client,
) -> None:
    ids = await _seed_healthy_trusted_argument()
    try:
        response = await review_client.get(
            "/api/admin/review/arguments", headers=_admin_headers()
        )
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert all(item["id"] != ids["argument_id"] for item in body)
    finally:
        await _teardown_healthy_trusted_argument(ids)


# ---------------------------------------------------------------------------
# Tracer feedback gate defect 1 — deterministic constituent ordering.
# A write to one constituent must not change the returned order (PostgreSQL
# writes an UPDATEd row as a new heap tuple; without an explicit ordering on
# the participant, a sequential scan returns the just-written row last).
# ---------------------------------------------------------------------------


async def _seed_three_unresolved_constituents():
    """One CANDIDATE argument with three person_id-IS-NULL participants
    (all flagged via the unresolved-participant leg), seeded in a known id
    order. Used to prove ordering is stable regardless of write recency."""
    import uuid as _uuid

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Case,
        CaseArgument,
        SideEnum,
    )

    suffix = _uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.CANDIDATE)
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number=f"RV-03-{suffix}",
            docket_number_norm=f"rv-03-{suffix}",
            case_name="Review Fixture v. Ordering",
            term_year=2026,
            slug=f"review-fixture-ordering-{suffix}",
        )
        db.add(case)
        await db.flush()
        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))

        participant_ids: list[int] = []
        for i, side in enumerate((SideEnum.PETITIONER, SideEnum.PETITIONER, SideEnum.RESPONDENT)):
            participant = ArgumentParticipant(
                argument_id=arg.id,
                person_id=None,
                raw_speaker_label=f"UNKNOWN SPEAKER {i}",
                side=side,
            )
            db.add(participant)
            await db.flush()
            participant_ids.append(participant.id)
        await db.commit()

        return {
            "argument_id": arg.id,
            "case_id": case.id,
            "participant_ids": participant_ids,
        }


async def _teardown_three_unresolved_constituents(ids: dict) -> None:
    from sqlalchemy import delete as sa_delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentParticipant, Case, CaseArgument

    async with AsyncSessionLocal() as db:
        await db.execute(
            sa_delete(ArgumentParticipant).where(
                ArgumentParticipant.argument_id == ids["argument_id"]
            )
        )
        await db.execute(
            sa_delete(CaseArgument).where(CaseArgument.argument_id == ids["argument_id"])
        )
        await db.execute(sa_delete(Case).where(Case.id == ids["case_id"]))
        await db.execute(sa_delete(Argument).where(Argument.id == ids["argument_id"]))
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_constituent_order_is_stable_across_an_update(review_client) -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentParticipant

    ids = await _seed_three_unresolved_constituents()
    try:
        response = await review_client.get(
            "/api/admin/review/arguments", headers=_admin_headers()
        )
        assert response.status_code == 200
        item = next(i for i in response.json() if i["id"] == ids["argument_id"])
        order_before = [c["participant_id"] for c in item["constituents"]]
        assert order_before == sorted(order_before)
        assert set(order_before) == set(ids["participant_ids"])

        # Write to the FIRST constituent in the returned order — PostgreSQL
        # rewrites it as a new heap tuple. Without the participant-level
        # ordering fix this would surface last on the next scan.
        target_id = order_before[0]
        async with AsyncSessionLocal() as db:
            from sqlalchemy import update as sa_update

            await db.execute(
                sa_update(ArgumentParticipant)
                .where(ArgumentParticipant.id == target_id)
                .values(raw_speaker_label="UNKNOWN SPEAKER (rewritten)")
            )
            await db.commit()

        response_after = await review_client.get(
            "/api/admin/review/arguments", headers=_admin_headers()
        )
        item_after = next(
            i for i in response_after.json() if i["id"] == ids["argument_id"]
        )
        order_after = [c["participant_id"] for c in item_after["constituents"]]
        assert order_after == order_before, (
            "constituent order must not change when one row is rewritten"
        )
    finally:
        await _teardown_three_unresolved_constituents(ids)


# ---------------------------------------------------------------------------
# Tracer feedback gate defect 2a — Confirm is rejected on a participant
# whose person_id IS NULL (an unresolved speaker). resolve_participant_review
# only ever writes review_state, never person_id, so allowing a confirm here
# would be a permanent no-op that silently pretends to succeed.
# ---------------------------------------------------------------------------


async def _seed_unresolved_participant():
    """One CANDIDATE argument with a single person_id-IS-NULL participant."""
    import uuid as _uuid

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Case,
        CaseArgument,
        SideEnum,
    )

    suffix = _uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.CANDIDATE)
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number=f"RV-04-{suffix}",
            docket_number_norm=f"rv-04-{suffix}",
            case_name="Review Fixture v. Unresolved Speaker",
            term_year=2026,
            slug=f"review-fixture-unresolved-speaker-{suffix}",
        )
        db.add(case)
        await db.flush()
        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=None,
            raw_speaker_label="MR. UNKNOWN",
            side=SideEnum.PETITIONER,
        )
        db.add(participant)
        await db.commit()

        return {
            "argument_id": arg.id,
            "case_id": case.id,
            "participant_id": participant.id,
        }


async def _teardown_unresolved_participant(ids: dict) -> None:
    from sqlalchemy import delete as sa_delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentParticipant, Case, CaseArgument

    async with AsyncSessionLocal() as db:
        await db.execute(
            sa_delete(ArgumentParticipant).where(ArgumentParticipant.id == ids["participant_id"])
        )
        await db.execute(
            sa_delete(CaseArgument).where(CaseArgument.argument_id == ids["argument_id"])
        )
        await db.execute(sa_delete(Case).where(Case.id == ids["case_id"]))
        await db.execute(sa_delete(Argument).where(Argument.id == ids["argument_id"]))
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_patch_confirm_rejects_unresolved_speaker(review_client) -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentParticipant

    ids = await _seed_unresolved_participant()
    try:
        response = await review_client.patch(
            f"/api/admin/review/participants/{ids['participant_id']}",
            json={"action": "confirm"},
            headers=_admin_headers(),
        )
        assert response.status_code == 422

        async with AsyncSessionLocal() as db:
            participant = await db.get(ArgumentParticipant, ids["participant_id"])
            # Confirm must be rejected before any write — review_state stays
            # whatever it started as (server_default 'unreviewed'), and
            # person_id remains untouched.
            assert participant.review_state.value == "unreviewed"
            assert participant.person_id is None
    finally:
        await _teardown_unresolved_participant(ids)


# ---------------------------------------------------------------------------
# Tracer feedback gate defect 2b — the queue payload carries the argument's
# admin_job_id (nullable), populated from the most recently linked AdminJob
# without multiplying the argument's constituent rows.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_queue_payload_admin_job_id_none_when_unlinked(review_client) -> None:
    ids = await _seed_needs_review_participant()
    try:
        response = await review_client.get(
            "/api/admin/review/arguments", headers=_admin_headers()
        )
        assert response.status_code == 200
        item = next(i for i in response.json() if i["id"] == ids["argument_id"])
        assert item["admin_job_id"] is None
    finally:
        await _teardown_needs_review_participant(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_queue_payload_admin_job_id_populated_and_does_not_duplicate_constituents(
    review_client,
) -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import AdminJob, AdminJobStatus

    ids = await _seed_needs_review_participant()
    job_id: int | None = None
    try:
        async with AsyncSessionLocal() as db:
            job = AdminJob(status=AdminJobStatus.PAUSED, argument_id=ids["argument_id"])
            db.add(job)
            await db.commit()
            job_id = job.id

        response = await review_client.get(
            "/api/admin/review/arguments", headers=_admin_headers()
        )
        assert response.status_code == 200
        item = next(i for i in response.json() if i["id"] == ids["argument_id"])
        assert item["admin_job_id"] == job_id
        # The AdminJob join is a correlated scalar subquery, not a join —
        # confirm it never multiplied the constituent rows.
        assert len(item["constituents"]) == 1
    finally:
        if job_id is not None:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import delete as sa_delete

                await db.execute(sa_delete(AdminJob).where(AdminJob.id == job_id))
                await db.commit()
        await _teardown_needs_review_participant(ids)


# ---------------------------------------------------------------------------
# Plan 49-04, Task 3 — the full resolve-action set, D-17's unattributable
# floor lift, and D-15's shared-timestamp discrepancy close.
# ---------------------------------------------------------------------------


async def _seed_unresolved_participant_task3():
    """One CANDIDATE argument with a single person_id-IS-NULL participant,
    review_state defaulting to unreviewed."""
    import uuid as _uuid

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Case,
        CaseArgument,
        SideEnum,
    )

    suffix = _uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.CANDIDATE)
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number=f"RV-05-{suffix}",
            docket_number_norm=f"rv-05-{suffix}",
            case_name="Review Fixture v. Unattributable",
            term_year=2026,
            slug=f"review-fixture-unattributable-{suffix}",
        )
        db.add(case)
        await db.flush()
        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=None,
            raw_speaker_label="MR. NEVER RESOLVED",
            side=SideEnum.PETITIONER,
        )
        db.add(participant)
        await db.commit()

        return {
            "argument_id": arg.id,
            "case_id": case.id,
            "participant_id": participant.id,
        }


async def _teardown_task3_participant(ids: dict) -> None:
    from sqlalchemy import delete as sa_delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentParticipant, Case, CaseArgument, ValueDiscrepancy

    async with AsyncSessionLocal() as db:
        await db.execute(
            sa_delete(ValueDiscrepancy).where(
                ValueDiscrepancy.target_type == "argument_participant",
                ValueDiscrepancy.target_id == ids["participant_id"],
            )
        )
        await db.execute(
            sa_delete(ArgumentParticipant).where(ArgumentParticipant.id == ids["participant_id"])
        )
        await db.execute(
            sa_delete(CaseArgument).where(CaseArgument.argument_id == ids["argument_id"])
        )
        await db.execute(sa_delete(Case).where(Case.id == ids["case_id"]))
        await db.execute(sa_delete(Argument).where(Argument.id == ids["argument_id"]))
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_confirm_unattributable_lifts_uncertain_floor(review_client) -> None:
    """confirm_unattributable on a person_id-IS-NULL participant sets
    operator_confirmed, and the argument's recomputed tier is no longer
    floored to UNCERTAIN by that participant (D-17)."""
    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument, ArgumentParticipant

    ids = await _seed_unresolved_participant_task3()
    try:
        response = await review_client.patch(
            f"/api/admin/review/participants/{ids['participant_id']}",
            json={"action": "confirm_unattributable"},
            headers=_admin_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["review_state"] == "operator_confirmed"

        async with AsyncSessionLocal() as db:
            participant = await db.get(ArgumentParticipant, ids["participant_id"])
            argument = await db.get(Argument, ids["argument_id"])
            assert participant.review_state.value == "operator_confirmed"
            assert participant.person_id is None  # confirm_unattributable never sets person_id
            assert argument.trust_tier == TrustTier.VERIFIED
    finally:
        await _teardown_task3_participant(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_confirm_on_unresolved_participant_rejected_with_distinct_error(review_client) -> None:
    """confirm (not confirm_unattributable) on a person_id-IS-NULL
    participant is rejected with a distinct tagged error — an ordinary
    confirm never lifts the unresolved-speaker floor as a side effect
    (D-17)."""
    ids = await _seed_unresolved_participant_task3()
    try:
        response = await review_client.patch(
            f"/api/admin/review/participants/{ids['participant_id']}",
            json={"action": "confirm"},
            headers=_admin_headers(),
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "unresolved_requires_unattributable"
    finally:
        await _teardown_task3_participant(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_confirm_unattributable_on_resolved_participant_rejected(review_client) -> None:
    """confirm_unattributable on an already-resolved participant
    (person_id IS NOT NULL) is rejected with a distinct tagged error — it
    is not the action for a resolved row."""
    ids = await _seed_needs_review_participant()
    try:
        response = await review_client.patch(
            f"/api/admin/review/participants/{ids['participant_id']}",
            json={"action": "confirm_unattributable"},
            headers=_admin_headers(),
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "participant_is_resolved"
    finally:
        await _teardown_needs_review_participant(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_reflag_sets_needs_review_on_operator_confirmed_row(review_client) -> None:
    """reflag on an operator_confirmed row sets needs_review — the only
    backward transition available (D-25)."""
    ids = await _seed_needs_review_participant()
    try:
        confirm_response = await review_client.patch(
            f"/api/admin/review/participants/{ids['participant_id']}",
            json={"action": "confirm"},
            headers=_admin_headers(),
        )
        assert confirm_response.status_code == 200

        reflag_response = await review_client.patch(
            f"/api/admin/review/participants/{ids['participant_id']}",
            json={"action": "reflag"},
            headers=_admin_headers(),
        )
        assert reflag_response.status_code == 200
        assert reflag_response.json()["review_state"] == "needs_review"
    finally:
        await _teardown_needs_review_participant(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_reflag_rejected_on_never_reviewed_row(review_client) -> None:
    """reflag on a row that is still unreviewed is rejected — no action
    ever writes a row back to unreviewed (D-25), and reflag only makes
    sense on a row a human has already touched."""
    ids = await _seed_unresolved_participant_task3()
    try:
        # This participant's review_state is still the server default
        # (unreviewed) — reflag should reject rather than accept.
        response = await review_client.patch(
            f"/api/admin/review/participants/{ids['participant_id']}",
            json={"action": "reflag"},
            headers=_admin_headers(),
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "row_not_yet_reviewed"
    finally:
        await _teardown_task3_participant(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_multiple_open_discrepancies_close_with_identical_resolved_at(review_client) -> None:
    """A resolve action on a row with three open discrepancies stamps the
    identical resolved_at on all three (D-15: one UPDATE, one shared
    timestamp, so the close order is unobservable)."""
    from sqlalchemy import select as sa_select

    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentParticipant, ValueDiscrepancy
    from api.services.admin_review import record_value_discrepancy

    ids = await _seed_needs_review_participant()
    try:
        async with AsyncSessionLocal() as db:
            for field in ("side", "descriptor", "raw_speaker_label"):
                await record_value_discrepancy(
                    db,
                    target_type="argument_participant",
                    target_id=ids["participant_id"],
                    field=field,
                    import_run_id=None,
                    incoming_value="incoming",
                    existing_value="existing",
                    incoming_source="corpus",
                    incoming_method="direct",
                    existing_source="operator",
                    existing_method="manual",
                )
            await db.commit()

        response = await review_client.patch(
            f"/api/admin/review/participants/{ids['participant_id']}",
            json={"action": "confirm"},
            headers=_admin_headers(),
        )
        assert response.status_code == 200

        async with AsyncSessionLocal() as db:
            rows = (
                await db.execute(
                    sa_select(ValueDiscrepancy).where(
                        ValueDiscrepancy.target_type == "argument_participant",
                        ValueDiscrepancy.target_id == ids["participant_id"],
                    )
                )
            ).scalars().all()
            assert len(rows) == 3
            resolved_ats = {r.resolved_at for r in rows}
            assert None not in resolved_ats
            assert len(resolved_ats) == 1, "all three rows must share the identical resolved_at"
    finally:
        await _teardown_needs_review_participant(ids)
