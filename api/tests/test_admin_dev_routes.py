"""
End-to-end test for the dev-only "Reset to Fixture" endpoint (Phase 43,
Plan 43-01, DEVTOOL-01).

DB-dependent tests are gated by _require_test_db(): they skip the whole
module unless TEST_DATABASE_URL is set AND the effective DATABASE_URL
(after tests/conftest.py's redirect) equals it. This is a SECOND,
in-file safety net on top of the root conftest.py redirect — no automated
test in this file may ever execute reset_to_fixture against the shared dev
database (carry-forward constraint from Phase 31).

The synthetic corpus fixture mirrors
pipeline/tests/test_import_convokit_adminjob.py's `_write_corpus_fixture`
shape, scoped to conversation 15169 only (this plan's single fixture) rather
than the real 900MB corpus.

`corpus_dir` is a Python-level keyword argument used only by tests — the HTTP
client's request carries no body, query parameter, or header naming a
corpus directory at all. The corpus-dependent test reaches the synthetic
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
    Person,
    Role,
    Utterance,
)


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


def _write_corpus_fixture(tmp_path: Path) -> Path:
    """Write a small synthetic corpus_dir tree containing ONLY conversation
    15169 (this plan's single fixture) — never the real 900MB corpus.

    conversation_id "15169" is the conversations.json dict KEY (an opaque
    ConvoKit id, unrelated to term/docket numbering) and becomes
    Argument.oyez_transcript_id verbatim (import_convokit.py line ~514).
    The term-prefixed join key "1966_642" lives in the conversation's own
    "case_id" field and joins to cases.jsonl's "id" field — NOT the same
    string as the conversation_id (see import_convokit.py's module
    docstring "Join key note").
    """
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()

    conversation_id = "15169"
    case_join_id = "1966_642"
    conversations = {
        conversation_id: {
            "case_id": case_join_id,
            "advocates": {"adv__jane_roe": {"side": 1}},
        }
    }
    cases = [
        {
            "id": case_join_id,
            "docket_no": "642",
            "title": "Baltimore & Ohio Railroad Company v. United States",
            "petitioner": "Baltimore & Ohio Railroad Company",
            "respondent": "United States",
            "year": 1966,
            "transcripts": [{"id": conversation_id, "name": "Oral Argument - January 9, 1967"}],
        }
    ]
    speakers = {
        "adv__jane_roe": {"name": "Jane Roe", "type": "advocate"},
        "j__test_justice_bench": {"name": "Test Justice Bench", "type": "justice"},
    }
    utterances = [
        {
            "id": "u1",
            "conversation_id": conversation_id,
            "speaker": "adv__jane_roe",
            "text": "May it please the Court.",
        },
        {
            "id": "u2",
            "conversation_id": conversation_id,
            "speaker": "j__test_justice_bench",
            "text": "Counsel, what about the statute's plain text?",
        },
    ]

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
    """One HTTP POST wipes the test database and reseeds conversation 15169
    through the real import-convokit path, landing it at status=PIPELINE with
    a paired PAUSED/RESOLVE AdminJob (Phase 30 invariant), and leaves the
    roles table's row count unchanged (proving roles was not truncated)."""
    _require_test_db()

    # Seed one throwaway Person + Argument with a non-fixture oyez_transcript_id.
    throwaway_person = Person(full_name="Throwaway Person")
    db.add(throwaway_person)
    await db.flush()

    throwaway_argument = Argument(
        oyez_transcript_id="not-a-fixture-id",
        status=ArgumentStatusEnum.DRAFT,
    )
    db.add(throwaway_argument)
    await db.commit()

    roles_before = (
        await db.execute(select(func.count()).select_from(Role))
    ).scalar_one()

    corpus_dir = _write_corpus_fixture(tmp_path)

    from api.services import admin_dev as admin_dev_service

    real_reset = admin_dev_service.reset_to_fixture

    async def _patched(request_db):
        return await real_reset(request_db, corpus_dir=corpus_dir)

    with patch(
        "api.routers.admin_dev.admin_dev_service.reset_to_fixture", new=_patched
    ):
        resp = await client.post(
            "/api/admin/dev/reset-to-fixture", headers=_admin_headers()
        )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["fixtures"]) == 1
    fixture = body["fixtures"][0]
    assert fixture["conversation_id"] == "15169"
    assert fixture["case_name"] == "Baltimore & Ohio Railroad Company v. United States"
    assert fixture["role"] == "Complexity"

    # The reset ran on its own AsyncSession, opened by the get_db dependency —
    # this test's db fixture is a SEPARATE transaction. Use a fresh
    # session-equivalent query via db after an expire_all so reads
    # see the committed state, not a stale snapshot.
    db.expire_all()

    # Throwaway rows are gone.
    throwaway_arg_check = (
        await db.execute(
            select(Argument).where(Argument.oyez_transcript_id == "not-a-fixture-id")
        )
    ).scalar_one_or_none()
    assert throwaway_arg_check is None

    throwaway_person_check = (
        await db.execute(
            select(Person).where(Person.full_name == "Throwaway Person")
        )
    ).scalar_one_or_none()
    assert throwaway_person_check is None

    # Exactly one Argument row, the fixture, at status=PIPELINE.
    all_arguments = (await db.execute(select(Argument))).scalars().all()
    assert len(all_arguments) == 1
    argument = all_arguments[0]
    assert argument.oyez_transcript_id == "15169"
    assert argument.status == ArgumentStatusEnum.PIPELINE

    # Exactly one paired AdminJob, PAUSED/RESOLVE (Phase 30 invariant).
    jobs = (
        await db.execute(
            select(AdminJob).where(AdminJob.argument_id == argument.id)
        )
    ).scalars().all()
    assert len(jobs) == 1
    assert jobs[0].status == AdminJobStatus.PAUSED
    assert jobs[0].current_step == AdminJobStep.RESOLVE

    # At least one Utterance and one Person row exist.
    utterance_count = (
        await db.execute(select(func.count()).select_from(Utterance))
    ).scalar_one()
    assert utterance_count >= 1

    person_count = (
        await db.execute(select(func.count()).select_from(Person))
    ).scalar_one()
    assert person_count >= 1

    # roles table untouched — same row count before and after.
    roles_after = (
        await db.execute(select(func.count()).select_from(Role))
    ).scalar_one()
    assert roles_after == roles_before
