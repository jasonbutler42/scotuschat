"""
Integration tests for the arguments API endpoints.

Tests 1 and 2 (health, 404) work without a real database.
Tests 3 and 4 (utterances content, ordering) require a live Postgres database
with ingested and parsed Obergefell data — they are skipped when DATABASE_URL
is not configured or when the DB is unreachable.

The lifespan on the ASGI app connects to the database during the test client
context. If the connection fails (no DB configured), tests that depend on a
running DB are marked as skip-on-error.

Uses httpx + ASGITransport for async test client (no real HTTP server needed).
"""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    """
    Async test client for the FastAPI app.

    Uses ASGITransport so tests run without a real network socket.
    The lifespan event will attempt a DB connection — tests that require
    the DB are guarded by the `db_available` fixture below.
    """
    from api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


def assert_no_key_anywhere(payload, key: str, context: str) -> None:
    """
    Recursively walk a decoded JSON payload (dicts/lists, any nesting) and
    raise an AssertionError naming the exact JSON path if `key` is found at
    any depth — so a nested leak is caught, not just a top-level one.

    Phase 48 (D-23): trust must never be inferred as a quality/trust signal
    on any public response, same rationale as the Phase 47 provenance ban
    below. `context` names the endpoint/response under test so a failure
    message is actionable without re-deriving which call produced it.
    """

    def _walk(node, path: str) -> None:
        if isinstance(node, dict):
            assert key not in node, (
                f"'{key}' found at path '{path or '<root>'}' in {context} — "
                "trust is operator-facing only and must never appear on a "
                "public response, at any nesting depth (CLAUDE.md apolitical "
                "hard constraint; D-23)."
            )
            for k, v in node.items():
                _walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                _walk(item, f"{path}[{i}]")

    _walk(payload, "")


@pytest_asyncio.fixture
async def seeded_argument():
    """
    Self-contained Argument + Case + CaseArgument(is_lead) + Person/Role +
    a COMPLETED parse ImportRun + 2 Utterances (one resolved to a Person).

    Phase 31 (TEST-02): Tests 3-5 used to assume a persistent, pre-seeded
    Obergefell Q1 row at argument_id=1 on the shared dev DB. Against the
    isolated scotus_test DB (empty except migrations), that row does not
    exist, so every request 404'd. Each test now seeds and tears down its
    own minimal argument instead of depending on external state.
    """
    import datetime

    from sqlalchemy import delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentStatusEnum,
        Case,
        CaseArgument,
        ImportMethod,
        ImportRun,
        ImportRunStatus,
        ImportSource,
        Person,
        Role,
        Utterance,
    )

    async with AsyncSessionLocal() as db:
        role = Role(name="Test Arguments Fixture Role (Phase 31 seed)")
        db.add(role)
        await db.flush()

        person = Person(full_name="Test Fixture Speaker", role_id=role.id)
        db.add(person)
        await db.flush()

        arg = Argument(
            status=ArgumentStatusEnum.DRAFT,
            argued_date=datetime.date(2015, 4, 28),
            question_number=1,
            resolved_at=datetime.datetime.now(datetime.timezone.utc),
            # get_argument_with_utterances() gates on published_at (BUG-01/D-02) —
            # this fixture tests the utterances payload, not the publish gate, so
            # it publishes the argument to keep the pre-existing assertions live.
            published_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number="14-556-TEST-SEED",
            docket_number_norm="14-556-test-seed",
            case_name="Test Fixture Case v. Seed",
            term_year=2015,
            slug="test-fixture-case-v-seed-14-556",
        )
        db.add(case)
        await db.flush()

        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))

        run = ImportRun(
            argument_id=arg.id,
            step="parse",
            status=ImportRunStatus.COMPLETED,
            source=ImportSource.PDF_PIPELINE,
            method=ImportMethod.RULE_BASED,
        )
        db.add(run)
        await db.flush()

        db.add_all(
            [
                # Sequence 1 is left unresolved (person_id=None) — Test 3
                # (test_get_utterances_returns_utterances) asserts the first
                # utterance has no person_id at Phase 1, before Resolve runs.
                Utterance(
                    argument_id=arg.id,
                    import_run_id=run.id,
                    sequence=1,
                    raw_speaker_label="TEST FIXTURE SPEAKER",
                    text="First utterance.",
                    person_id=None,
                ),
                # Sequence 2 is resolved — Test 5
                # (test_utterances_have_speaker_name_after_resolve) asserts at
                # least one resolved utterance has a non-null speaker_name.
                Utterance(
                    argument_id=arg.id,
                    import_run_id=run.id,
                    sequence=2,
                    raw_speaker_label="TEST FIXTURE SPEAKER",
                    text="Second utterance.",
                    person_id=person.id,
                ),
            ]
        )
        await db.commit()

        arg_id = arg.id
        case_id = case.id
        run_id = run.id
        person_id = person.id
        role_id = role.id

    yield arg_id

    async with AsyncSessionLocal() as db:
        await db.execute(delete(Utterance).where(Utterance.argument_id == arg_id))
        await db.execute(delete(ImportRun).where(ImportRun.id == run_id))
        await db.execute(delete(CaseArgument).where(CaseArgument.argument_id == arg_id))
        case_obj = await db.get(Case, case_id)
        if case_obj is not None:
            await db.delete(case_obj)
        arg_obj = await db.get(Argument, arg_id)
        if arg_obj is not None:
            await db.delete(arg_obj)
        person_obj = await db.get(Person, person_id)
        if person_obj is not None:
            await db.delete(person_obj)
        role_obj = await db.get(Role, role_id)
        if role_obj is not None:
            await db.delete(role_obj)
        await db.commit()


# ---------------------------------------------------------------------------
# Test 1: Health endpoint — works without a real database
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    """GET /health should return 200 {"status": "ok"} regardless of DB state."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Test 2: 404 for unknown argument — works without real DB data
# (returns 404 when the argument is not found in DB, or 500 if DB is down)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_utterances_returns_404_for_unknown_argument(
    client: AsyncClient,
) -> None:
    """
    GET /arguments/99999/utterances should return 404 when the argument
    does not exist.

    If the DB is not available the endpoint returns 500; we accept both
    404 and 500 here so CI passes without a real database.
    """
    response = await client.get("/arguments/99999/utterances")
    assert response.status_code in (404, 500), (
        f"Expected 404 or 500, got {response.status_code}"
    )
    if response.status_code == 404:
        assert response.json()["detail"] == "Argument not found"


# ---------------------------------------------------------------------------
# Test 3: Full utterances response — requires real DB with parsed data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL with parsed data")
async def test_get_utterances_returns_utterances(client: AsyncClient, seeded_argument: int) -> None:
    """
    GET /arguments/{id}/utterances should return 200 with utterances list and
    argument metadata for a self-seeded argument (Phase 31 — no longer
    hardcoded to argument_id=1; scotus_test starts empty).
    """
    response = await client.get(f"/arguments/{seeded_argument}/utterances")
    assert response.status_code == 200

    body = response.json()

    # Top-level structure
    assert "utterances" in body, "Response must have 'utterances' key"
    assert "argument" in body, "Response must have 'argument' key"

    utterances = body["utterances"]
    assert isinstance(utterances, list), "utterances must be a list"
    assert len(utterances) > 0, "utterances list must not be empty"

    # Argument metadata fields
    argument = body["argument"]
    assert "case_name" in argument
    assert "docket_number" in argument
    assert "argued_date" in argument
    assert "question_number" in argument

    # First utterance starts at sequence 1 and has required fields
    first = utterances[0]
    assert first["sequence"] == 1, "First utterance must have sequence == 1"
    assert "import_run_id" in first, "Utterances must have import_run_id (PROV-04)"
    assert first["import_run_id"] is not None
    # Phase 47 (T-47-17): provenance is operator-facing lineage only — the
    # public utterance contract must never leak strategy/source/method/
    # external_id, and must never be inferred as a quality/trust signal.
    # Phase 48 (D-23) adds trust_tier to this same ban list for the same
    # reason provenance was banned: it must never be inferred as a quality
    # signal on the public site (apolitical hard constraint, CLAUDE.md).
    assert "strategy" not in first, "strategy must not appear on the public utterance contract"
    assert "source" not in first, "source must not appear on the public utterance contract"
    assert "method" not in first, "method must not appear on the public utterance contract"
    assert "external_id" not in first, "external_id must not appear on the public utterance contract"
    assert "trust_tier" not in first, "trust_tier must not appear on the public utterance contract"
    # person_id is null at Phase 1 (Phase 2 Resolve populates it)
    assert first.get("person_id") is None, "person_id must be null at Phase 1"

    # D-23: recursive check over the whole argument-detail envelope, not
    # just the first utterance dict inspected above — a nested leak
    # anywhere in the response must be caught too.
    assert_no_key_anywhere(
        body, "trust_tier", "GET /arguments/{id}/utterances response"
    )


# ---------------------------------------------------------------------------
# Test 4: Utterances ordered by sequence — requires real DB with parsed data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL with parsed data")
async def test_utterances_ordered_by_sequence(client: AsyncClient, seeded_argument: int) -> None:
    """
    Utterances in GET /arguments/{id}/utterances must be monotonically
    ascending by sequence number.
    """
    response = await client.get(f"/arguments/{seeded_argument}/utterances")
    assert response.status_code == 200

    sequences = [u["sequence"] for u in response.json()["utterances"]]
    assert sequences == sorted(sequences), (
        "Utterances must be ordered by sequence ASC"
    )


# ---------------------------------------------------------------------------
# Test 5: Utterances embed speaker_name after resolve — requires real DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL with resolved data")
async def test_utterances_have_speaker_name_after_resolve(
    client: AsyncClient, seeded_argument: int
) -> None:
    """
    GET /arguments/{id}/utterances — utterances must include speaker_name and
    speaker_role keys in the response after the Resolve step has run.

    Both fields may be null for unresolved utterances (e.g. stage directions),
    but the keys must always be present in every utterance object (D-10).
    At least one utterance with a resolved person_id must have a non-null
    speaker_name.
    """
    response = await client.get(f"/arguments/{seeded_argument}/utterances")
    assert response.status_code == 200

    utterances = response.json()["utterances"]
    assert len(utterances) > 0, "utterances list must not be empty"

    # Every utterance must have speaker_name and speaker_role keys (D-10 contract)
    for u in utterances:
        assert "speaker_name" in u, f"Utterance {u.get('id')} missing speaker_name key"
        assert "speaker_role" in u, f"Utterance {u.get('id')} missing speaker_role key"

    # At least one utterance with a resolved person_id must have a non-null speaker_name
    resolved = [u for u in utterances if u.get("person_id") is not None]
    if resolved:
        names = [u["speaker_name"] for u in resolved if u["speaker_name"] is not None]
        assert len(names) > 0, (
            "At least one resolved utterance must have a non-null speaker_name"
        )


# ---------------------------------------------------------------------------
# Phase 48 (D-23): live per-endpoint trust-tier leak-ban assertions
#
# The structural half of the ban (every public Pydantic response model,
# derived from the live public routers) lives in
# api/tests/test_trust_public_leak_ban.py. These three tests are the LIVE
# half — they hit the real endpoints against a seeded row and walk the
# actual decoded JSON body recursively via assert_no_key_anywhere, so a
# leak introduced by a service layer bypassing its own schema (e.g. an
# ORM-row spread instead of the declared allow-list) is also caught, not
# just a leak visible from the Pydantic model definition alone.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL with parsed data")
async def test_cases_list_never_leaks_trust_tier(client: AsyncClient) -> None:
    """
    GET /cases must never expose trust_tier, on any case item or the
    response envelope, at any nesting depth (D-23, T-48-LEAK).
    """
    response = await client.get("/cases")
    assert response.status_code == 200

    body = response.json()
    assert_no_key_anywhere(body, "trust_tier", "GET /cases response")


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL with parsed data")
async def test_argument_speakers_never_leaks_trust_tier(
    client: AsyncClient, seeded_argument: int
) -> None:
    """
    GET /arguments/{id}/speakers must never expose trust_tier on any
    speaker entry, at any nesting depth (D-23, T-48-LEAK).
    """
    response = await client.get(f"/arguments/{seeded_argument}/speakers")
    assert response.status_code == 200

    body = response.json()
    assert_no_key_anywhere(body, "trust_tier", "GET /arguments/{id}/speakers response")


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL with parsed data")
async def test_person_detail_never_leaks_trust_tier(
    client: AsyncClient, seeded_argument: int
) -> None:
    """
    GET /people/{person_id} must never expose trust_tier, at any nesting
    depth (D-23, T-48-LEAK). Resolves a real person_id from the seeded
    argument's own speakers response rather than asserting against a
    guessed id — skips with an explicit reason if the seeded argument has
    no resolved speaker (it should always have one via `seeded_argument`'s
    second, resolved utterance, but this guards against a future fixture
    change silently making the test vacuous-by-skip forever without a
    visible reason).
    """
    speakers_response = await client.get(f"/arguments/{seeded_argument}/speakers")
    assert speakers_response.status_code == 200
    speakers = speakers_response.json()
    if not speakers:
        pytest.skip(
            "seeded_argument fixture produced no resolved speaker — "
            "cannot resolve a real person_id to test against"
        )
    person_id = speakers[0]["person_id"]

    response = await client.get(f"/people/{person_id}")
    assert response.status_code == 200

    body = response.json()
    assert_no_key_anywhere(body, "trust_tier", "GET /people/{person_id} response")
