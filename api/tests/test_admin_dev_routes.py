"""
End-to-end test for the dev-only "Reset to Fixture" endpoint (Phase 43,
DEVTOOL-01).

DB-dependent tests are gated by _require_test_db(): they skip the whole
module unless TEST_DATABASE_URL is set AND the effective DATABASE_URL
(after tests/conftest.py's redirect) equals it. This is a SECOND,
in-file safety net on top of the root conftest.py redirect — no automated
test in this file may ever execute reset_to_fixture against the shared dev
database (carry-forward constraint from Phase 31).

The synthetic corpus fixture mirrors
pipeline/tests/test_import_convokit_adminjob.py's `_write_corpus_fixture`
shape, extended (Plan 43-02) to all four of FIXTURE_SET's conversations —
15169, 13015, 18897, 22372 — each with its own October-Term-prefixed
`case_id` (matching .planning/FIXTURES.md's Term column) and distinct
docket, so the reseed exercises the real (source_docket, question_number)
uniqueness contract across four different dockets/terms, never the real
900MB corpus.

`corpus_dir` is a Python-level keyword argument used only by tests — the HTTP
client's request carries no body, query parameter, or header naming a
corpus directory at all. Every corpus-dependent test reaches its synthetic
corpus dir by patching api.routers.admin_dev.admin_dev_service.reset_to_fixture
with a thin wrapper that forwards corpus_dir to the real service function —
same module object as api.services.admin_dev, so this is not a redefinition
of the service, just an injected default for the one HTTP call under test.
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from api.models.models import (
    AdminJob,
    AdminJobStatus,
    AdminJobStep,
    Argument,
    ArgumentStatusEnum,
    ArgumentStatusLog,
    CourtTenure,
    ImportMethod,
    ImportRun,
    ImportSource,
    Person,
    Role,
    Utterance,
)

# ===========================================================================
# Shared fixture data — the four FIXTURE_SET conversations, transcribed from
# .planning/FIXTURES.md's Fixture Set table (case_join_id carries the real
# October Term as its "<term>_" prefix, matching that table's Term column;
# docket_no matches that table's Docket(s) column). Titles/speaker
# ids/utterance text are synthetic — the reset response's case_name always
# comes from api.services.admin_dev.FIXTURE_SET, never from these corpus
# files, so assertions below check against FIXTURES.md's names regardless
# of what these synthetic titles say.
# ===========================================================================

FIXTURE_CONVERSATIONS: dict[str, dict] = {
    "15169": {
        "case_join_id": "1966_642",
        "docket_no": "642",
        "title": "Baltimore & Ohio Railroad Company v. United States",
        "petitioner": "Baltimore & Ohio Railroad Company",
        "respondent": "United States",
        "year": 1966,
        "transcript_name": "Oral Argument - January 9, 1967",
    },
    "13015": {
        "case_join_id": "1955_351",
        "docket_no": "351",
        "title": "Archawski v. Hanioti",
        "petitioner": "Archawski",
        "respondent": "Hanioti",
        "year": 1955,
        "transcript_name": "Oral Argument - March 5, 1956",
    },
    "18897": {
        "case_join_id": "1985_84-1602",
        "docket_no": "84-1602",
        "title": "Anderson v. Liberty Lobby, Inc.",
        "petitioner": "Anderson",
        "respondent": "Liberty Lobby, Inc.",
        "year": 1985,
        "transcript_name": "Oral Argument - December 3, 1985",
    },
    "22372": {
        "case_join_id": "2010_09-479",
        "docket_no": "09-479",
        "title": "Abbott v. United States",
        "petitioner": "Abbott",
        "respondent": "United States",
        "year": 2010,
        "transcript_name": "Oral Argument - October 4, 2010",
    },
}

FIXTURE_ORDER = ["15169", "13015", "18897", "22372"]


def _require_test_db() -> None:
    """Skip the whole module unless TEST_DATABASE_URL is set AND the
    effective DATABASE_URL equals it (carry-forward Phase 31 constraint —
    this destructive reset must never run against the shared dev DB)."""
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url or os.environ.get("DATABASE_URL") != test_url:
        pytest.skip(
            "Requires TEST_DATABASE_URL set and DATABASE_URL redirected to it "
            "(tests/conftest.py) — refusing to run a destructive reset test "
            "without confirmed test-DB isolation."
        )


def _write_corpus_fixture(tmp_path: Path, *, omit_conversation_id: str | None = None) -> Path:
    """Write a synthetic corpus_dir tree containing all four FIXTURE_SET
    conversations (15169, 13015, 18897, 22372) — one advocate turn and one
    bench turn each, with per-conversation-unique speaker ids to avoid
    unintended cross-conversation Person dedup.

    `omit_conversation_id`, when set, drops exactly that one conversation
    from conversations.json (its case/speakers/utterances rows are still
    written) — used by test_reset_incomplete_reseed_raises to simulate a
    partial reseed without inventing a fake fifth conversation id.
    """
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()

    conversations: dict = {}
    cases: list[dict] = []
    speakers: dict = {}
    utterances: list[dict] = []

    for conversation_id, meta in FIXTURE_CONVERSATIONS.items():
        advocate_key = f"adv__{conversation_id}"
        justice_key = f"j__{conversation_id}"

        if conversation_id != omit_conversation_id:
            conversations[conversation_id] = {
                "case_id": meta["case_join_id"],
                "advocates": {advocate_key: {"side": 1}},
            }

        cases.append(
            {
                "id": meta["case_join_id"],
                "docket_no": meta["docket_no"],
                "title": meta["title"],
                "petitioner": meta["petitioner"],
                "respondent": meta["respondent"],
                "year": meta["year"],
                "transcripts": [
                    {"id": conversation_id, "name": meta["transcript_name"]}
                ],
            }
        )
        speakers[advocate_key] = {
            "name": f"Advocate {conversation_id}",
            "type": "advocate",
        }
        speakers[justice_key] = {
            "name": f"Justice {conversation_id}",
            "type": "justice",
        }
        utterances.append(
            {
                "id": f"{conversation_id}-u1",
                "conversation_id": conversation_id,
                "speaker": advocate_key,
                "text": "May it please the Court.",
            }
        )
        utterances.append(
            {
                "id": f"{conversation_id}-u2",
                "conversation_id": conversation_id,
                "speaker": justice_key,
                "text": "Counsel, what about the statute's plain text?",
            }
        )

    (corpus_dir / "conversations.json").write_text(
        json.dumps(conversations), encoding="utf-8"
    )
    with (corpus_dir / "cases.jsonl").open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case) + "\n")
    (corpus_dir / "speakers.json").write_text(json.dumps(speakers), encoding="utf-8")
    with (corpus_dir / "utterances.jsonl").open("w", encoding="utf-8") as f:
        for row in utterances:
            f.write(json.dumps(row) + "\n")

    return corpus_dir


@pytest_asyncio.fixture
async def client():
    """Async httpx test client for the FastAPI app (ASGITransport, no socket)."""
    from api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture
async def db():
    """
    Dedicated session with its own engine, NOT wrapped in an auto-rollback
    transaction — api/tests/conftest.py's db_session fixture wraps the whole
    test in one `session.begin()` block that it rolls back at the end, which
    is unusable here: this test needs its seeded rows and post-reset
    assertions to see genuinely COMMITTED state, since the reset endpoint's
    TRUNCATE and reseed run on a completely separate connection/session
    (get_db's own AsyncSessionLocal, and pipeline.db.get_session() for each
    run_import_convokit call) that cannot see this test's uncommitted rows.
    No rollback needed for THIS destructive test's own seed data — the
    reset's TRUNCATE (or the module-level _require_test_db() gate refusing
    to run at all against a non-test DB) is what keeps this safe.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(
        os.environ["DATABASE_URL"],
        connect_args={"statement_cache_size": 0},
        pool_size=2,
        echo=False,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
    await engine.dispose()


def _admin_headers() -> dict:
    from api.core.config import settings

    return {"X-Admin-Token": settings.admin_token}


async def _post_reset(client, corpus_dir: Path):
    """POST /api/admin/dev/reset-to-fixture, patching in the given synthetic
    corpus_dir via the same corpus_dir-forwarding wrapper technique proven in
    Plan 43-01 (never a request field)."""
    from api.services import admin_dev as admin_dev_service

    real_reset = admin_dev_service.reset_to_fixture

    async def _patched(request_db):
        return await real_reset(request_db, corpus_dir=corpus_dir)

    with patch(
        "api.routers.admin_dev.admin_dev_service.reset_to_fixture", new=_patched
    ):
        return await client.post(
            "/api/admin/dev/reset-to-fixture", headers=_admin_headers()
        )


async def _fetch_argument(db, conversation_id: str) -> Argument:
    db.expire_all()
    return (
        await db.execute(
            select(Argument).where(Argument.oyez_transcript_id == conversation_id)
        )
    ).scalar_one()


async def _fetch_admin_job(db, argument_id: int) -> AdminJob:
    # Deliberately does NOT call db.expire_all() (unlike _fetch_argument) --
    # callers commonly do `arg = await _fetch_argument(...)` followed by
    # `job = await _fetch_admin_job(db, arg.id)` and then keep reading
    # attributes off `arg`; expiring here would force a synchronous
    # re-load of `arg`'s already-fetched attributes on next access, which
    # raises sqlalchemy.exc.MissingGreenlet outside of an explicit await.
    return (
        await db.execute(select(AdminJob).where(AdminJob.argument_id == argument_id))
    ).scalar_one()


@pytest.mark.asyncio
async def test_reset_requires_admin_token(client):
    """POST without a valid X-Admin-Token returns non-200/non-5xx and does
    not mutate the database. Runs without needing a corpus dir at all."""
    _require_test_db()

    resp = await client.post("/api/admin/dev/reset-to-fixture")
    assert resp.status_code != 200
    assert resp.status_code < 500


@pytest.mark.asyncio
async def test_reset_wipes_and_reseeds_fixtures(client, tmp_path, db):
    """One HTTP POST wipes the test database and reseeds all four
    FIXTURE_SET conversations through the real import-convokit path, and
    nothing that predated the reset survives."""
    _require_test_db()

    # Seed throwaway rows across every table this reset must clear. Primary
    # keys are captured as plain ints BEFORE the reset (rather than read off
    # the ORM objects afterward) because db.expire_all() below expires every
    # attribute, including each object's own `id` -- re-accessing an expired
    # PK attribute after its row has been TRUNCATEd away would attempt a
    # synchronous lazy-reload that raises sqlalchemy.exc.MissingGreenlet in
    # this async context.
    throwaway_person = Person(full_name="Throwaway Person")
    db.add(throwaway_person)
    await db.flush()
    throwaway_person_id = throwaway_person.id

    throwaway_tenure = CourtTenure(person_id=throwaway_person_id, office="associate")
    db.add(throwaway_tenure)

    throwaway_argument = Argument(
        oyez_transcript_id="not-a-fixture-id",
        status=ArgumentStatusEnum.DRAFT,
    )
    db.add(throwaway_argument)
    await db.flush()
    throwaway_argument_id = throwaway_argument.id

    throwaway_run = ImportRun(
        argument_id=throwaway_argument_id,
        step="resolve",
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.NORMALIZED,
    )
    db.add(throwaway_run)
    await db.flush()
    throwaway_run_id = throwaway_run.id

    throwaway_utterance = Utterance(
        argument_id=throwaway_argument_id,
        import_run_id=throwaway_run_id,
        sequence=0,
        text="Throwaway utterance.",
    )
    db.add(throwaway_utterance)
    await db.commit()
    throwaway_utterance_id = throwaway_utterance.id

    roles_before = (
        await db.execute(select(func.count()).select_from(Role))
    ).scalar_one()

    corpus_dir = _write_corpus_fixture(tmp_path)
    resp = await _post_reset(client, corpus_dir)

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["fixtures"]) == 4

    db.expire_all()

    # Throwaway rows are all gone.
    assert (
        await db.execute(
            select(Argument).where(Argument.oyez_transcript_id == "not-a-fixture-id")
        )
    ).scalar_one_or_none() is None
    assert (
        await db.execute(
            select(Person).where(Person.full_name == "Throwaway Person")
        )
    ).scalar_one_or_none() is None
    assert (
        await db.execute(
            select(CourtTenure).where(CourtTenure.person_id == throwaway_person_id)
        )
    ).scalar_one_or_none() is None
    assert (
        await db.execute(
            select(Utterance).where(Utterance.id == throwaway_utterance_id)
        )
    ).scalar_one_or_none() is None

    # Exactly four Argument rows, the fixture set.
    all_arguments = (await db.execute(select(Argument))).scalars().all()
    assert len(all_arguments) == 4
    assert {a.oyez_transcript_id for a in all_arguments} == set(FIXTURE_ORDER)

    # Each fixture argument has exactly one paired AdminJob.
    all_jobs = (await db.execute(select(AdminJob))).scalars().all()
    assert len(all_jobs) == 4
    job_argument_ids = {j.argument_id for j in all_jobs}
    assert job_argument_ids == {a.id for a in all_arguments}

    # The fixtures' own people were created.
    person_count = (
        await db.execute(select(func.count()).select_from(Person))
    ).scalar_one()
    assert person_count > 0

    # roles table untouched — same row count before and after.
    roles_after = (
        await db.execute(select(func.count()).select_from(Role))
    ).scalar_one()
    assert roles_after == roles_before


@pytest.mark.asyncio
async def test_reset_response_order_is_declaration_order(client, tmp_path, db):
    """The response's four conversation_id values, read in array order, are
    exactly FIXTURE_ORDER — on both a first and second consecutive run
    (Edge probe: ordering)."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)

    resp1 = await _post_reset(client, corpus_dir)
    assert resp1.status_code == 200
    order1 = [f["conversation_id"] for f in resp1.json()["fixtures"]]
    assert order1 == FIXTURE_ORDER

    resp2 = await _post_reset(client, corpus_dir)
    assert resp2.status_code == 200
    order2 = [f["conversation_id"] for f in resp2.json()["fixtures"]]
    assert order2 == FIXTURE_ORDER


@pytest.mark.asyncio
async def test_reset_is_repeatable(client, tmp_path, db):
    """Running the reset twice in a row produces the identical four-fixture
    end state: still exactly four arguments, no duplicates, and the same
    per-docket question_number values as the first run (Edge probe:
    adjacency)."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)

    resp1 = await _post_reset(client, corpus_dir)
    assert resp1.status_code == 200

    db.expire_all()
    first_run_numbers = {
        a.oyez_transcript_id: (a.source_docket, a.question_number)
        for a in (await db.execute(select(Argument))).scalars().all()
    }
    assert len(first_run_numbers) == 4
    # Commit (ends this session's implicit read transaction) before the
    # second reset's own TRUNCATE runs on a separate session/connection —
    # Postgres's TRUNCATE takes ACCESS EXCLUSIVE, which conflicts with any
    # still-open transaction that has touched the same table, even a bare
    # SELECT (autobegin leaves the transaction open until commit/rollback).
    # Leaving this uncommitted deadlocks the second POST against this
    # fixture's own held lock.
    await db.commit()

    resp2 = await _post_reset(client, corpus_dir)
    assert resp2.status_code == 200

    db.expire_all()
    second_run_arguments = (await db.execute(select(Argument))).scalars().all()
    assert len(second_run_arguments) == 4
    assert {a.oyez_transcript_id for a in second_run_arguments} == set(FIXTURE_ORDER)

    seen_pairs = set()
    for argument in second_run_arguments:
        pair = (argument.source_docket, argument.question_number)
        assert pair not in seen_pairs, "duplicate (source_docket, question_number) pair"
        seen_pairs.add(pair)
        assert pair == first_run_numbers[argument.oyez_transcript_id]


@pytest.mark.asyncio
async def test_reset_against_empty_database(client, tmp_path, db):
    """A reset against an already-empty database succeeds and produces the
    same four-fixture end state as a reset against a populated one — TRUNCATE
    over empty tables is a no-op, not an error (Edge probe: empty)."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)

    # Reach a known state, then TRUNCATE the wipe set directly to reach a
    # genuinely empty database (bypassing the reset's own reseed step).
    resp1 = await _post_reset(client, corpus_dir)
    assert resp1.status_code == 200

    from api.services.admin_dev import TRUNCATE_SQL
    from sqlalchemy import text

    await db.execute(text(TRUNCATE_SQL))
    await db.commit()

    db.expire_all()
    empty_count = (
        await db.execute(select(func.count()).select_from(Argument))
    ).scalar_one()
    assert empty_count == 0
    # Commit before the second reset's TRUNCATE (see test_reset_is_repeatable
    # for why an uncommitted read-only transaction here would deadlock it).
    await db.commit()

    resp2 = await _post_reset(client, corpus_dir)
    assert resp2.status_code == 200
    body = resp2.json()
    assert len(body["fixtures"]) == 4
    assert [f["conversation_id"] for f in body["fixtures"]] == FIXTURE_ORDER

    db.expire_all()
    all_arguments = (await db.execute(select(Argument))).scalars().all()
    assert len(all_arguments) == 4
    assert {a.oyez_transcript_id for a in all_arguments} == set(FIXTURE_ORDER)


@pytest.mark.asyncio
async def test_reset_incomplete_reseed_raises(client, tmp_path, db):
    """A synthetic corpus missing one of the four conversations causes a
    failure, not a 200 with a three-item fixtures array."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path, omit_conversation_id="22372")

    resp = await _post_reset(client, corpus_dir)

    assert resp.status_code != 200
    assert resp.status_code >= 500


@pytest.mark.asyncio
async def test_reset_realizes_state_variety(client, tmp_path, db):
    """All four fixtures land in four mutually distinguishable end states
    after the reset (D-03, D-04)."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)
    resp = await _post_reset(client, corpus_dir)
    assert resp.status_code == 200

    # 15169 (Complexity): untouched freshly-imported default.
    complexity_arg = await _fetch_argument(db, "15169")
    assert complexity_arg.status == ArgumentStatusEnum.CANDIDATE
    assert complexity_arg.resolved_at is None
    assert complexity_arg.published_at is None
    complexity_job = await _fetch_admin_job(db, complexity_arg.id)
    assert complexity_job.status == AdminJobStatus.PAUSED
    assert complexity_job.current_step == AdminJobStep.RESOLVE

    # 13015 (Draft): CANDIDATE -> DRAFT.
    draft_arg = await _fetch_argument(db, "13015")
    assert draft_arg.status == ArgumentStatusEnum.DRAFT
    assert draft_arg.resolved_at is not None
    assert draft_arg.published_at is None
    draft_job = await _fetch_admin_job(db, draft_arg.id)
    assert draft_job.status == AdminJobStatus.COMPLETED

    # 18897 (Published): CANDIDATE -> DRAFT -> PUBLISHED.
    published_arg = await _fetch_argument(db, "18897")
    assert published_arg.status == ArgumentStatusEnum.PUBLISHED
    assert published_arg.resolved_at is not None
    assert published_arg.published_at is not None
    published_job = await _fetch_admin_job(db, published_arg.id)
    assert published_job.status == AdminJobStatus.COMPLETED

    # 22372 (Mid-pipeline): stays CANDIDATE, AdminJob flipped to RUNNING.
    mid_arg = await _fetch_argument(db, "22372")
    assert mid_arg.status == ArgumentStatusEnum.CANDIDATE
    assert mid_arg.resolved_at is None
    mid_job = await _fetch_admin_job(db, mid_arg.id)
    assert mid_job.status == AdminJobStatus.RUNNING
    assert mid_job.current_step == AdminJobStep.RESOLVE

    # All four AdminJob rows still exist (none deleted).
    all_jobs = (await db.execute(select(AdminJob))).scalars().all()
    assert len(all_jobs) == 4


@pytest.mark.asyncio
async def test_reset_writes_status_log_rows(client, tmp_path, db):
    """argument_status_log has at least one row for 13015's DRAFT transition
    and at least one for 18897's PUBLISHED transition, and zero rows for
    15169/22372 (which never left the candidate state) — proof the transitions went
    through the real service functions, not a column write."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)
    resp = await _post_reset(client, corpus_dir)
    assert resp.status_code == 200

    # Capture each argument's id immediately after its own fetch -- the
    # NEXT _fetch_argument call's internal db.expire_all() would otherwise
    # expire this object's own `id` attribute too, and re-accessing an
    # expired attribute later (outside an explicit await) raises
    # sqlalchemy.exc.MissingGreenlet in this async context.
    draft_argument_id = (await _fetch_argument(db, "13015")).id
    published_argument_id = (await _fetch_argument(db, "18897")).id
    complexity_argument_id = (await _fetch_argument(db, "15169")).id
    mid_argument_id = (await _fetch_argument(db, "22372")).id

    async def _log_count(argument_id: int) -> int:
        return (
            await db.execute(
                select(func.count())
                .select_from(ArgumentStatusLog)
                .where(ArgumentStatusLog.argument_id == argument_id)
            )
        ).scalar_one()

    assert await _log_count(draft_argument_id) >= 1
    assert await _log_count(published_argument_id) >= 1
    assert await _log_count(complexity_argument_id) == 0
    assert await _log_count(mid_argument_id) == 0


@pytest.mark.asyncio
async def test_reset_response_reports_realized_states(client, tmp_path, db):
    """Each response item's argument_status and admin_job_status fields
    match the values read back from the database, not values assumed from
    FIXTURE_SET."""
    _require_test_db()

    corpus_dir = _write_corpus_fixture(tmp_path)
    resp = await _post_reset(client, corpus_dir)
    assert resp.status_code == 200
    body = resp.json()

    for item in body["fixtures"]:
        argument = await _fetch_argument(db, item["conversation_id"])
        admin_job = await _fetch_admin_job(db, argument.id)
        assert item["argument_status"] == argument.status.value
        assert item["admin_job_status"] == admin_job.status.value
