"""
IMPORT-03 negative-space module (Phase 50, plan 50-01, Task 3, PD-04).

This file used to assert the Phase 30 corpus AdminJob fabrication (paired
PAUSED/RESOLVE job, HIT-shaped discrepancies, idempotent re-import via
skip-existing). Phase 50 D-14/D-19 DELETES that fabrication entirely: the
corpus importer never creates an AdminJob, corpus arguments reach DRAFT via
the argument-scoped `api.services.admin_arguments.approve_argument`
instead, and a repeat import reconciles rather than skipping (D-01).

Every one of the four assertions below is the INVERSE of what this file
used to assert -- proof the deletion actually happened, not just that the
old behavior went untested:
    - A fresh corpus import of one synthetic conversation creates ZERO
      admin_job rows (IMPORT-03).
    - That argument does not appear in
      `api.services.admin_jobs.list_jobs` (no job to list).
    - `api.services.admin_jobs.get_pipeline_stats` is unaffected by the
      import (its counts are scoped to AdminJob rows only).
    - The argument is still reachable and approvable via
      `api.services.admin_arguments.approve_argument` (D-14 -- corpus
      arguments are not orphaned by AdminJob's removal; they have their
      own path to DRAFT/publishable).

DB-dependent tests are skipped when DATABASE_URL/TEST_DATABASE_URL is not
set (via conftest.py's test_db_url fixture -> pytest.skip). Uses a small
synthetic corpus_dir tree written to tmp_path (same convention as
test_import_convokit_utterances.py) -- never the real 900MB
utterances.jsonl.
"""

import json
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import delete, func, select

from api.models.models import (
    AdminJob,
    Argument,
    ArgumentParticipant,
    ArgumentStatusEnum,
    ArgumentStatusLog,
    CaseArgument,
    ImportRun,
    Person,
    Utterance,
)
from api.services.admin_arguments import approve_argument
from api.services.admin_jobs import get_pipeline_stats, list_jobs
from pipeline.commands.import_convokit import run_import_convokit

# ===========================================================================
# Shared fixtures / helpers (same pattern as test_import_convokit_utterances.py)
# ===========================================================================


def _make_session_cm(session):
    """Context manager yielding `session` -- patches get_session in the
    module under test so tests inject a test-owned, rolled-back session."""

    @asynccontextmanager
    async def _cm():
        yield session

    return _cm


@pytest.fixture()
async def isolated_session(test_db_url):
    """Function-scoped AsyncSession with its own dedicated engine, rolled
    back after the test -- a dedicated per-test engine/session fixture
    (Phase 29-03 decision) avoids the pre-existing Windows asyncpg/
    pytest-asyncio stale-event-loop failure that conftest.py's shared
    session-scoped engine fixture hits."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(
        test_db_url,
        connect_args={"statement_cache_size": 0},
        pool_size=2,
        echo=False,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
    await engine.dispose()


def _write_corpus_fixture(
    tmp_path: Path,
    conversations: dict,
    cases: list[dict],
    speakers: dict,
    utterances: list[dict],
    subdir: str = "corpus",
) -> Path:
    """Write a small synthetic corpus_dir tree, including utterances.jsonl
    (never the real 900MB file)."""
    corpus_dir = tmp_path / subdir
    corpus_dir.mkdir()
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


def _args(term, corpus_dir: Path):
    import argparse

    return argparse.Namespace(term=term, term_range=None, corpus_dir=str(corpus_dir))


_CONVERSATION_ID = "9998_71"

_CONVERSATION = {
    _CONVERSATION_ID: {
        "conversation_id": _CONVERSATION_ID,
        "case_id": _CONVERSATION_ID,
        "advocates": {"adv__jane_roe": {"side": 1}},
    }
}
_CASE = {
    "id": _CONVERSATION_ID,
    "docket_no": "55-98",
    "title": "Roe v. Doe",
    "petitioner": "Roe",
    "respondent": "Doe",
    "year": 1955,
    "transcripts": [{"name": "Oral Argument - November 15, 1955"}],
}
_SPEAKERS = {
    "adv__jane_roe": {"name": "Jane Roe", "type": "advocate"},
    "j__test_justice_bench": {"name": "Test Justice Bench", "type": "justice"},
}

# One advocate turn (already resolved during the advocates loop) and one
# bench turn (discovered only while streaming utterances).
_UTTERANCES = [
    {
        "id": "u1",
        "conversation_id": _CONVERSATION_ID,
        "speaker": "adv__jane_roe",
        "text": "May it please the Court.",
    },
    {
        "id": "u2",
        "conversation_id": _CONVERSATION_ID,
        "speaker": "j__test_justice_bench",
        "text": "Counsel, what about the statute's plain text?",
    },
]


async def _run_import(isolated_session, tmp_path, term=9998, subdir="corpus"):
    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATION, [_CASE], _SPEAKERS, _UTTERANCES, subdir=subdir
    )
    args = _args(term, corpus_dir)
    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)


async def _fetch_argument(isolated_session) -> Argument:
    return (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == _CONVERSATION_ID)
        )
    ).scalar_one()


# ===========================================================================
# Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_fresh_corpus_import_creates_zero_admin_job_rows(
    isolated_session, tmp_path
):
    await _run_import(isolated_session, tmp_path)
    argument = await _fetch_argument(isolated_session)

    jobs_for_argument = (
        (
            await isolated_session.execute(
                select(AdminJob).where(AdminJob.argument_id == argument.id)
            )
        )
        .scalars()
        .all()
    )
    assert jobs_for_argument == []

    total_admin_jobs = (
        await isolated_session.execute(select(func.count()).select_from(AdminJob))
    ).scalar_one()
    assert total_admin_jobs == 0


@pytest.mark.asyncio
async def test_argument_status_is_candidate_with_no_resolved_at(
    isolated_session, tmp_path
):
    await _run_import(isolated_session, tmp_path)
    argument = await _fetch_argument(isolated_session)

    assert argument.status == ArgumentStatusEnum.CANDIDATE
    assert argument.resolved_at is None


@pytest.mark.asyncio
async def test_corpus_argument_absent_from_list_jobs(isolated_session, tmp_path):
    await _run_import(isolated_session, tmp_path)
    argument = await _fetch_argument(isolated_session)

    jobs = await list_jobs(isolated_session)
    job_argument_ids = {j.argument_id for j in jobs}
    assert argument.id not in job_argument_ids


@pytest.mark.asyncio
async def test_get_pipeline_stats_unaffected_by_corpus_import(
    isolated_session, tmp_path
):
    before = await get_pipeline_stats(isolated_session)
    await _run_import(isolated_session, tmp_path)
    after = await get_pipeline_stats(isolated_session)

    # get_pipeline_stats is scoped to AdminJob rows only -- a corpus import
    # that creates zero AdminJob rows must leave it byte-identical.
    assert after["recent_count"] == before["recent_count"]
    assert after["last_activity_at"] == before["last_activity_at"]


@pytest.mark.asyncio
async def test_jobless_corpus_argument_is_reachable_and_approvable(
    isolated_session, tmp_path
):
    """D-14: approve_argument is the ONLY writer of resolved_at for a
    jobless corpus argument -- without it, publish_argument's
    non-overridable resolved_at IS NULL refusal would make it permanently
    unpublishable.

    Unlike every other test in this module, `approve_argument` COMMITS
    internally (mirroring `approve_job`'s established contract) -- once
    committed, `isolated_session`'s fixture-teardown `rollback()` can no
    longer undo it (rollback only ever undoes an OPEN transaction, not
    already-committed work), so this test explicitly deletes every row it
    created before returning rather than relying on that rollback for
    cleanup, keeping this the ONE test in the corpus test suite that is
    ever allowed to leave committed data behind if it doesn't clean up
    after itself.
    """
    await _run_import(isolated_session, tmp_path)
    argument = await _fetch_argument(isolated_session)
    argument_id = argument.id

    result = await approve_argument(isolated_session, argument_id)
    assert result is not None
    assert result["status"] == ArgumentStatusEnum.DRAFT

    await isolated_session.refresh(argument)
    assert argument.status == ArgumentStatusEnum.DRAFT
    assert argument.resolved_at is not None

    # Explicit cleanup (see docstring) -- FK-ordered, mirroring
    # admin_arguments.py::delete_argument's own cascade order.
    person_ids = (
        (
            await isolated_session.execute(
                select(ArgumentParticipant.person_id).where(
                    ArgumentParticipant.argument_id == argument_id
                )
            )
        )
        .scalars()
        .all()
    )
    await isolated_session.execute(
        delete(Utterance).where(Utterance.argument_id == argument_id)
    )
    await isolated_session.execute(
        delete(ImportRun).where(ImportRun.argument_id == argument_id)
    )
    await isolated_session.execute(
        delete(ArgumentParticipant).where(ArgumentParticipant.argument_id == argument_id)
    )
    await isolated_session.execute(
        delete(CaseArgument).where(CaseArgument.argument_id == argument_id)
    )
    await isolated_session.execute(
        delete(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == argument_id)
    )
    await isolated_session.execute(delete(Argument).where(Argument.id == argument_id))
    if person_ids:
        await isolated_session.execute(
            delete(Person).where(Person.id.in_(p for p in person_ids if p is not None))
        )
    await isolated_session.commit()
