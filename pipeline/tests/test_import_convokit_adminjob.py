"""
Tests for pipeline.commands.import_convokit's paired AdminJob creation
(Phase 30, Plan 01, Task 2).

Covers:
    - The Argument created by a corpus import lands at
      ArgumentStatusEnum.PIPELINE (not DRAFT) -- 30-RESEARCH.md Pitfall 1.
    - Exactly one AdminJob(status=PAUSED, current_step=RESOLVE,
      argument_id=<arg>) row is created per imported conversation (D-01,
      D-03), in the same per-conversation transaction.
    - That AdminJob's discrepancies JSONB holds one HIT-shaped dict per
      already-resolved ArgumentParticipant, matching ResolveCard.svelte's
      Action-column rendering contract (D-05).
    - Re-running an already-imported conversation_id creates NO additional
      AdminJob row (rides the existing oyez_transcript_id early-return
      idempotency gate -- no second AdminJob-specific select is added).

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
from sqlalchemy import select

from api.models.models import (
    AdminJob,
    AdminJobStatus,
    AdminJobStep,
    Argument,
    ArgumentStatusEnum,
)
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
# bench turn (discovered only while streaming utterances) -- exercises the
# D-01/D-03 insertion point that requires both resolution paths to have
# completed before resolved_participants.values() is read.
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
async def test_argument_status_is_pipeline_not_draft(isolated_session, tmp_path):
    await _run_import(isolated_session, tmp_path)
    argument = await _fetch_argument(isolated_session)

    assert argument.status == ArgumentStatusEnum.PIPELINE
    assert argument.resolved_at is None


@pytest.mark.asyncio
async def test_exactly_one_paused_resolve_adminjob_created(isolated_session, tmp_path):
    await _run_import(isolated_session, tmp_path)
    argument = await _fetch_argument(isolated_session)

    jobs = (
        await isolated_session.execute(
            select(AdminJob).where(AdminJob.argument_id == argument.id)
        )
    ).scalars().all()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.status == AdminJobStatus.PAUSED
    assert job.current_step == AdminJobStep.RESOLVE
    assert job.argument_id == argument.id


@pytest.mark.asyncio
async def test_discrepancies_are_hit_shaped_for_advocate_and_bench(
    isolated_session, tmp_path
):
    await _run_import(isolated_session, tmp_path)
    argument = await _fetch_argument(isolated_session)

    job = (
        await isolated_session.execute(
            select(AdminJob).where(AdminJob.argument_id == argument.id)
        )
    ).scalar_one()

    assert isinstance(job.discrepancies, list)
    # One resolved participant from the advocates loop (Jane Roe) and one
    # from utterance streaming (Test Justice Bench) -- both present because
    # the AdminJob insert happens after _import_utterances returns.
    assert len(job.discrepancies) == 2

    expected_keys = {
        "raw_speaker_label",
        "normalized",
        "candidates",
        "auto_match_id",
        "auto_match_name",
        "auto_match_role",
        "auto_resolved",
        "extracted_side",
    }
    labels = {d["raw_speaker_label"] for d in job.discrepancies}
    assert labels == {"Jane Roe", "Test Justice Bench"}

    for d in job.discrepancies:
        assert set(d.keys()) == expected_keys
        assert d["auto_resolved"] is True
        assert d["candidates"] == []
        assert d["auto_match_id"] is not None
        assert d["auto_match_name"] == d["raw_speaker_label"]
        assert d["auto_match_role"] is None
        # Phase 44 hint-snapshot fix: the side classified at import time,
        # frozen into the discrepancy blob so the Resolve card's hint can
        # show it independent of any later operator edit.
        assert d["extracted_side"] in ("BENCH", "PETITIONER", "RESPONDENT", "AMICUS", "UNKNOWN")


@pytest.mark.asyncio
async def test_reimport_same_conversation_creates_no_additional_adminjob(
    isolated_session, tmp_path
):
    await _run_import(isolated_session, tmp_path)
    argument = await _fetch_argument(isolated_session)

    # Re-run the same conversation a second time (fresh corpus_dir tree,
    # same conversation_id/oyez_transcript_id) -- the existing
    # oyez_transcript_id early-return in _import_conversation should skip
    # this conversation entirely, so no second AdminJob is ever created.
    await _run_import(isolated_session, tmp_path, subdir="corpus2")

    jobs = (
        await isolated_session.execute(
            select(AdminJob).where(AdminJob.argument_id == argument.id)
        )
    ).scalars().all()

    assert len(jobs) == 1
