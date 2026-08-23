"""
End-to-end test for the dev-only "Seed unresolved speaker" mechanism
(Phase 49, plan 49-06, D-33a).

Covers this plan's six `<behavior>` bullets for
`api.services.admin_dev.seed_unresolved_speaker_fixture`, one named test
per bullet:

  1. test_seeder_nulls_person_id_of_one_advocate_participant_and_flags_needs_review
  2. test_seeder_recomputes_uncertain_tier_and_bumps_unresolved_participant_blocker
  3. test_seeded_argument_appears_in_review_queue_with_null_person_id_constituent
  4. test_seeder_called_twice_is_idempotent_no_second_row_touched
  5. test_seeder_raises_distinct_error_when_fixture_argument_absent
  6. test_seed_unresolved_speaker_route_absent_outside_development

Two supplementary tests go beyond the six named bullets, added for
completeness — neither is required by the plan's acceptance criteria:
`test_seeder_raises_distinct_error_when_no_eligible_participant` covers
the sibling half of bullet 5's "un-reset database" class (the argument
exists but has no non-BENCH participant); `test_seed_unresolved_speaker_
route_returns_200_and_is_idempotent_over_http` is the fully automated
substitute for the plan's curl-based acceptance criterion (see that
test's own comment for why).

DB-dependent tests (1-5, 7) use a synthetic Argument/ArgumentParticipant
pair with a test-only `conversation_id`, seeded via a bare AsyncSessionLocal
and passed explicitly to the service function's `conversation_id` keyword
argument — this repo's real "15169" Complexity fixture is never touched by
an automated test (that fixture only exists after a human's own
`reset_to_fixture` run). Follows the established DB-gated integration
pattern from `test_admin_review_service.py`: seed via raw AsyncSessionLocal
(uncommitted state is invisible to the app's own request-scoped sessions),
exercise through a real ASGI TestClient where the behavior needs the
router, then tear down explicitly.

Test 6 achieves the same "genuinely absent, not merely refused" proof as
`tests/test_admin_dev_router_gate.py`, but via a different mechanism:
mutating `settings.environment` in place and reloading only `api.main`
(never touching `api.core.database`'s module identity, which this file's
autouse `_api_lifespan`/orphan-sweep fixtures depend on staying stable —
see the comment above that test for why the sys.modules-purge technique
would break those fixtures' teardown if used here). The assertion is
against a freshly constructed app instance with a non-development
environment, never a handler-level 403 check, per this plan's acceptance
criteria.
"""

import os
import uuid as _uuid

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


async def _seed_fixture_argument(conversation_id: str) -> dict:
    """One CANDIDATE argument carrying two resolved participants: a BENCH
    justice and an advocate-side speaker — so a test can confirm the
    seeder selects the non-BENCH row and leaves the BENCH row untouched."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Case,
        CaseArgument,
        ImportMethod,
        ImportSource,
        Person,
        ReviewState,
        SideEnum,
    )

    suffix = _uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.CANDIDATE,
            oyez_transcript_id=conversation_id,
        )
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number=f"SEED-{suffix}",
            docket_number_norm=f"seed-{suffix}",
            case_name="Seed Fixture v. Unresolved Speaker",
            term_year=2026,
            slug=f"seed-fixture-unresolved-speaker-{suffix}",
        )
        db.add(case)
        await db.flush()
        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))

        bench_person = Person(full_name="Seed Fixture Justice")
        db.add(bench_person)
        await db.flush()
        bench_participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=bench_person.id,
            raw_speaker_label="JUSTICE SEED FIXTURE",
            side=SideEnum.BENCH,
            source=ImportSource.CORPUS,
            method=ImportMethod.DIRECT,
            review_state=ReviewState.UNREVIEWED,
        )
        db.add(bench_participant)
        await db.flush()

        advocate_person = Person(full_name="Seed Fixture Advocate")
        db.add(advocate_person)
        await db.flush()
        advocate_participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=advocate_person.id,
            raw_speaker_label="MR. SEED FIXTURE",
            side=SideEnum.PETITIONER,
            source=ImportSource.CORPUS,
            method=ImportMethod.DIRECT,
            review_state=ReviewState.UNREVIEWED,
        )
        db.add(advocate_participant)
        await db.commit()

        return {
            "argument_id": arg.id,
            "case_id": case.id,
            "bench_person_id": bench_person.id,
            "bench_participant_id": bench_participant.id,
            "advocate_person_id": advocate_person.id,
            "advocate_participant_id": advocate_participant.id,
        }


async def _seed_bench_only_argument(conversation_id: str) -> dict:
    """A CANDIDATE argument with exactly one BENCH participant and no
    advocate-side row at all — the "no eligible participant" branch of
    FixtureNotSeededError."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Case,
        CaseArgument,
        ImportMethod,
        ImportSource,
        Person,
        ReviewState,
        SideEnum,
    )

    suffix = _uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.CANDIDATE,
            oyez_transcript_id=conversation_id,
        )
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number=f"SEEDB-{suffix}",
            docket_number_norm=f"seedb-{suffix}",
            case_name="Seed Fixture v. Bench Only",
            term_year=2026,
            slug=f"seed-fixture-bench-only-{suffix}",
        )
        db.add(case)
        await db.flush()
        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))

        bench_person = Person(full_name="Seed Fixture Bench-Only Justice")
        db.add(bench_person)
        await db.flush()
        bench_participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=bench_person.id,
            raw_speaker_label="JUSTICE SEED FIXTURE BENCH ONLY",
            side=SideEnum.BENCH,
            source=ImportSource.CORPUS,
            method=ImportMethod.DIRECT,
            review_state=ReviewState.UNREVIEWED,
        )
        db.add(bench_participant)
        await db.commit()

        return {
            "argument_id": arg.id,
            "case_id": case.id,
            "bench_person_id": bench_person.id,
            "bench_participant_id": bench_participant.id,
        }


async def _teardown_fixture_argument(ids: dict) -> None:
    from sqlalchemy import delete as sa_delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        Case,
        CaseArgument,
        Person,
        ValueDiscrepancy,
    )

    async with AsyncSessionLocal() as db:
        # A resolve/recompute pass never records a value_discrepancy for
        # this fixture's shape, but clean up defensively (no real FK from
        # value_discrepancy.target_id, mirroring the established teardown
        # convention in test_admin_review_service.py).
        for key in ("bench_participant_id", "advocate_participant_id"):
            if key in ids:
                await db.execute(
                    sa_delete(ValueDiscrepancy).where(
                        ValueDiscrepancy.target_type == "argument_participant",
                        ValueDiscrepancy.target_id == ids[key],
                    )
                )
        await db.execute(
            sa_delete(ArgumentParticipant).where(
                ArgumentParticipant.argument_id == ids["argument_id"]
            )
        )
        await db.execute(
            sa_delete(CaseArgument).where(CaseArgument.argument_id == ids["argument_id"])
        )
        await db.execute(sa_delete(Case).where(Case.id == ids["case_id"]))
        if "bench_person_id" in ids:
            await db.execute(sa_delete(Person).where(Person.id == ids["bench_person_id"]))
        if "advocate_person_id" in ids:
            await db.execute(sa_delete(Person).where(Person.id == ids["advocate_person_id"]))
        await db.execute(sa_delete(Argument).where(Argument.id == ids["argument_id"]))
        await db.commit()


@pytest_asyncio.fixture
async def review_client():
    from httpx import ASGITransport, AsyncClient
    from api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Behavior 1 — nulls exactly one advocate-side participant's person_id and
# flags it needs_review; the BENCH participant is untouched.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_seeder_nulls_person_id_of_one_advocate_participant_and_flags_needs_review():
    from sqlalchemy import select

    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentParticipant, ReviewState
    from api.services.admin_dev import seed_unresolved_speaker_fixture

    conversation_id = f"test-seed-{_uuid.uuid4().hex[:10]}"
    ids = await _seed_fixture_argument(conversation_id)
    try:
        async with AsyncSessionLocal() as db:
            result = await seed_unresolved_speaker_fixture(db, conversation_id=conversation_id)

        assert result["participant_id"] == ids["advocate_participant_id"]
        assert result["already_seeded"] is False

        async with AsyncSessionLocal() as db:
            advocate = (
                await db.execute(
                    select(ArgumentParticipant).where(
                        ArgumentParticipant.id == ids["advocate_participant_id"]
                    )
                )
            ).scalar_one()
            bench = (
                await db.execute(
                    select(ArgumentParticipant).where(
                        ArgumentParticipant.id == ids["bench_participant_id"]
                    )
                )
            ).scalar_one()

        assert advocate.person_id is None
        assert advocate.review_state == ReviewState.NEEDS_REVIEW
        # The BENCH row is untouched — the seeder must never null a
        # justice's person_id.
        assert bench.person_id == ids["bench_person_id"]
        assert bench.review_state == ReviewState.UNREVIEWED
    finally:
        await _teardown_fixture_argument(ids)


# ---------------------------------------------------------------------------
# Behavior 2 — the argument's recomputed trust_tier is uncertain and
# summarize_tier_blockers reports unresolved_participant >= 1.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_seeder_recomputes_uncertain_tier_and_bumps_unresolved_participant_blocker():
    from sqlalchemy import select

    from api.core.database import AsyncSessionLocal
    from api.domain.trust import TrustTier
    from api.models.models import Argument
    from api.services.admin_dev import seed_unresolved_speaker_fixture
    from api.services.trust import summarize_tier_blockers

    conversation_id = f"test-seed-{_uuid.uuid4().hex[:10]}"
    ids = await _seed_fixture_argument(conversation_id)
    try:
        async with AsyncSessionLocal() as db:
            await seed_unresolved_speaker_fixture(db, conversation_id=conversation_id)

        async with AsyncSessionLocal() as db:
            argument = (
                await db.execute(select(Argument).where(Argument.id == ids["argument_id"]))
            ).scalar_one()
            assert argument.trust_tier == TrustTier.UNCERTAIN

            blockers = await summarize_tier_blockers(db, ids["argument_id"])

        unresolved_counts = [b["count"] for b in blockers if b["code"] == "unresolved_participant"]
        assert unresolved_counts and unresolved_counts[0] >= 1
    finally:
        await _teardown_fixture_argument(ids)


# ---------------------------------------------------------------------------
# Behavior 3 — the argument appears in GET /api/admin/review/arguments via
# the unresolved leg, with a constituent whose person_id is null.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_seeded_argument_appears_in_review_queue_with_null_person_id_constituent(
    review_client,
):
    from api.core.database import AsyncSessionLocal
    from api.services.admin_dev import seed_unresolved_speaker_fixture

    conversation_id = f"test-seed-{_uuid.uuid4().hex[:10]}"
    ids = await _seed_fixture_argument(conversation_id)
    try:
        async with AsyncSessionLocal() as db:
            await seed_unresolved_speaker_fixture(db, conversation_id=conversation_id)

        response = await review_client.get(
            "/api/admin/review/arguments", headers=_admin_headers()
        )
        assert response.status_code == 200
        body = response.json()

        matches = [item for item in body if item["id"] == ids["argument_id"]]
        assert len(matches) == 1

        constituents = matches[0]["constituents"]
        null_person_constituents = [
            c for c in constituents if c["person_id"] is None
        ]
        assert len(null_person_constituents) == 1
        assert null_person_constituents[0]["participant_id"] == ids["advocate_participant_id"]
    finally:
        await _teardown_fixture_argument(ids)


# ---------------------------------------------------------------------------
# Behavior 4 — calling the seeder twice is safe: the second call is a
# no-op returning the same participant id, no second row touched.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_seeder_called_twice_is_idempotent_no_second_row_touched():
    from sqlalchemy import select

    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentParticipant
    from api.services.admin_dev import seed_unresolved_speaker_fixture

    conversation_id = f"test-seed-{_uuid.uuid4().hex[:10]}"
    ids = await _seed_fixture_argument(conversation_id)
    try:
        async with AsyncSessionLocal() as db:
            first = await seed_unresolved_speaker_fixture(db, conversation_id=conversation_id)
        async with AsyncSessionLocal() as db:
            second = await seed_unresolved_speaker_fixture(db, conversation_id=conversation_id)

        assert first["already_seeded"] is False
        assert second["already_seeded"] is True
        assert second["participant_id"] == first["participant_id"]

        async with AsyncSessionLocal() as db:
            null_person_rows = (
                await db.execute(
                    select(ArgumentParticipant).where(
                        ArgumentParticipant.argument_id == ids["argument_id"],
                        ArgumentParticipant.person_id.is_(None),
                    )
                )
            ).scalars().all()
        assert len(null_person_rows) == 1, "second call must not null a second row"
    finally:
        await _teardown_fixture_argument(ids)


# ---------------------------------------------------------------------------
# Supplementary — the plan's own acceptance criteria ask for a live curl
# against a running dev server with `-H "X-Admin-Token: $ADMIN_TOKEN"`,
# asserting 200 then 200-with-already_seeded-true. This sandbox's
# permission policy denies reading .env (where ADMIN_TOKEN lives), the
# same constraint recorded in 49-01/49-03/49-05-SUMMARY.md — no attempt
# was made to work around that denial. This test is the fully automated
# substitute: it drives the SAME router endpoint over a real ASGI
# TestClient, with the admin token read in-process from `settings.
# admin_token` (never echoed to any output this executor can see),
# proving the identical HTTP behavior the curl command would.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_seed_unresolved_speaker_route_returns_200_and_is_idempotent_over_http(
    review_client,
):
    from unittest.mock import patch

    from api.services.admin_dev import seed_unresolved_speaker_fixture

    conversation_id = f"test-seed-{_uuid.uuid4().hex[:10]}"
    ids = await _seed_fixture_argument(conversation_id)

    # The endpoint itself takes no request surface for the target
    # conversation (never a request body/query param/header — see this
    # route's own docstring); this thin wrapper forwards a test-only
    # conversation_id to the real service function, the exact technique
    # test_admin_dev_routes.py's module docstring documents for
    # reset_to_fixture's own corpus_dir.
    async def _seed_this_fixture(db):
        return await seed_unresolved_speaker_fixture(db, conversation_id=conversation_id)

    try:
        with patch(
            "api.routers.admin_dev.admin_dev_service.seed_unresolved_speaker_fixture",
            side_effect=_seed_this_fixture,
        ):
            first_resp = await review_client.post(
                "/api/admin/dev/seed-unresolved-speaker", headers=_admin_headers()
            )
            second_resp = await review_client.post(
                "/api/admin/dev/seed-unresolved-speaker", headers=_admin_headers()
            )

        assert first_resp.status_code == 200
        assert first_resp.json()["already_seeded"] is False
        assert second_resp.status_code == 200
        assert second_resp.json()["already_seeded"] is True
        assert second_resp.json()["participant_id"] == first_resp.json()["participant_id"]
    finally:
        await _teardown_fixture_argument(ids)


# ---------------------------------------------------------------------------
# Behavior 5 — a distinct error when the fixture argument is absent,
# rather than silently succeeding with nothing done.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_seeder_raises_distinct_error_when_fixture_argument_absent():
    from api.core.database import AsyncSessionLocal
    from api.services.admin_dev import FixtureNotSeededError, seed_unresolved_speaker_fixture

    missing_conversation_id = f"test-seed-absent-{_uuid.uuid4().hex[:10]}"

    async with AsyncSessionLocal() as db:
        with pytest.raises(FixtureNotSeededError):
            await seed_unresolved_speaker_fixture(db, conversation_id=missing_conversation_id)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_seeder_raises_distinct_error_when_no_eligible_participant():
    """Sibling of behavior 5: the argument exists but has no non-BENCH
    participant — also FixtureNotSeededError, not a silent success."""
    from api.core.database import AsyncSessionLocal
    from api.services.admin_dev import FixtureNotSeededError, seed_unresolved_speaker_fixture

    conversation_id = f"test-seed-benchonly-{_uuid.uuid4().hex[:10]}"
    ids = await _seed_bench_only_argument(conversation_id)
    try:
        async with AsyncSessionLocal() as db:
            with pytest.raises(FixtureNotSeededError):
                await seed_unresolved_speaker_fixture(db, conversation_id=conversation_id)
    finally:
        await _teardown_fixture_argument(ids)


# ---------------------------------------------------------------------------
# Behavior 6 — POST /api/admin/dev/seed-unresolved-speaker returns 404
# outside development, because the router was never mounted (never a
# handler-level 403).
#
# Deliberately does NOT use tests/test_admin_dev_router_gate.py's own
# sys.modules-purge-and-reimport technique: that technique deletes every
# `api.*` module from sys.modules, which is safe in that file (living
# under tests/, outside api/tests/'s autouse fixture stack) but breaks
# api/tests/conftest.py's autouse `_api_lifespan`/
# `_sweep_orphaned_value_discrepancies` fixtures here — their teardown
# does a fresh `from api.core.database import AsyncSessionLocal` against
# whatever module object is CURRENTLY cached in sys.modules, and a purge
# mid-test replaces that module with a brand-new one whose
# AsyncSessionLocal is still its unset default (None), raising
# `TypeError: 'NoneType' object is not callable` at this test's own
# teardown. Mutating `settings.environment` directly and reloading only
# `api.main` (never `api.core.database`) achieves the identical outcome —
# a freshly constructed FastAPI `app` whose conditional `include_router`
# re-evaluates against the mutated setting — without touching the module
# object the lifespan fixtures depend on.
# ---------------------------------------------------------------------------


def _all_route_paths(app) -> list[str]:
    """Mirrors api/tests/test_admin_dev_routes.py's own helper: walks both
    the plain-route shape and FastAPI's private `_IncludedRouter` wrapper
    shape so this keeps working across FastAPI minor versions."""
    paths: list[str] = []
    for route in app.routes:
        path = getattr(route, "path", None)
        if path:
            paths.append(path)
            continue
        original_router = getattr(route, "original_router", None)
        if original_router is not None:
            for sub_route in getattr(original_router, "routes", []):
                sub_path = getattr(sub_route, "path", None)
                if sub_path:
                    paths.append(sub_path)
    return paths


@pytest.mark.asyncio
async def test_seed_unresolved_speaker_route_absent_outside_development():
    import importlib

    from httpx import ASGITransport, AsyncClient

    import api.main as main_module
    from api.core.config import settings

    original_environment = settings.environment
    try:
        settings.environment = "production"
        importlib.reload(main_module)

        paths = _all_route_paths(main_module.app)
        assert not any(p.startswith("/api/admin/dev") for p in paths)

        async with AsyncClient(
            transport=ASGITransport(app=main_module.app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/admin/dev/seed-unresolved-speaker")

        assert resp.status_code == 404
        assert resp.status_code != 403
    finally:
        settings.environment = original_environment
        importlib.reload(main_module)
