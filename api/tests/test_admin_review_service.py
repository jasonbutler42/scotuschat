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
