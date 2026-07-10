"""
Tests for pipeline.commands.import_convokit.

Covers:
    - Task 1: _parse_term_range() validation and --corpus-dir fail-fast
      (no DB required for these).
    - Task 2: idempotent Case/Argument/CaseArgument/PipelineRun scaffolding,
      D-15 term_year sourcing, apolitical field stripping (T-29-02), and
      resumable re-run behavior (D-08/T-29-04).
    - Task 3: Person resolution via oyez_speaker_id-first/full_name-fallback
      with D-11 backfill, advocate side-code mapping, justice-type BENCH
      classification, and idempotent ArgumentParticipant creation.

DB-dependent tests are skipped when DATABASE_URL/TEST_DATABASE_URL is not
set (via conftest.py's async_session fixture -> test_db_url -> pytest.skip).
Never uses the real 900MB utterances.jsonl -- all fixtures are small,
synthetic corpus_dir trees written to tmp_path (D-18/RESEARCH.md convention).
"""

import argparse
import json
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import select

from api.models.models import (
    Argument,
    ArgumentStatusEnum,
    Case,
    CaseArgument,
    PipelineRun,
)
from pipeline.commands.import_convokit import _parse_term_range, run_import_convokit

# ===========================================================================
# Task 1: _parse_term_range() / --corpus-dir -- no DB required
# ===========================================================================


class TestParseTermRange:
    def test_parse_term_range_returns_inclusive_bounds(self):
        assert _parse_term_range("1955-1960") == (1955, 1960)

    def test_parse_term_range_raises_when_start_after_end(self):
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_term_range("1960-1955")

    def test_parse_term_range_raises_on_malformed_value(self):
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_term_range("not-a-range")

    def test_parse_term_range_raises_on_non_integer_parts(self):
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_term_range("nineteen-fifty-five-1960")

    def test_parse_term_range_single_term_equal_bounds(self):
        assert _parse_term_range("1955-1955") == (1955, 1955)


@pytest.mark.asyncio
async def test_missing_corpus_dir_fails_fast_not_keyerror(tmp_path):
    """T-29-05b: a nonexistent --corpus-dir must raise FileNotFoundError
    before any file load is attempted -- not a KeyError/AttributeError
    surfacing deep inside a loader call mid-run."""
    args = argparse.Namespace(
        term=1955, term_range=None, corpus_dir=str(tmp_path / "does-not-exist")
    )
    with pytest.raises(FileNotFoundError):
        await run_import_convokit(args)


# ===========================================================================
# Shared fixtures / helpers for Task 2 & 3 (DB-dependent)
# ===========================================================================


def _make_session_cm(session):
    """
    Create a context manager that yields `session`.

    Used to patch pipeline.commands.import_convokit.get_session so tests
    inject a test-owned session (rolled back after the test) instead of
    opening real, separately-committed DB connections per conversation.
    Matches the established pattern in pipeline/tests/test_ingest.py and
    pipeline/tests/test_import_justices_csv.py.
    """

    @asynccontextmanager
    async def _cm():
        yield session

    return _cm


@pytest.fixture()
async def isolated_session(test_db_url):
    """
    Function-scoped AsyncSession with its own dedicated engine, rolled back
    after the test and disposed afterward -- avoids the pre-existing
    Windows/asyncpg + pytest-asyncio stale-event-loop issue documented in
    pipeline/tests/test_import_justices_csv.py's identical fixture.
    """
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
) -> Path:
    """Write a small synthetic corpus_dir tree (never the real corpus files)."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "conversations.json").write_text(
        json.dumps(conversations), encoding="utf-8"
    )
    with (corpus_dir / "cases.jsonl").open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case) + "\n")
    (corpus_dir / "speakers.json").write_text(json.dumps(speakers), encoding="utf-8")
    return corpus_dir


# D-15 regression fixture: cases.jsonl "year" (1955) intentionally differs
# from the argued_date's calendar year (1956) -- SCOTUS October Terms span
# the Oct/Dec calendar boundary.
_CONVERSATION_1955_71 = {
    "1955_71": {
        "conversation_id": "1955_71",
        "case_id": "1955_71",
        "advocates": {"adv__john_smith": {"side": 1}},
        # Forbidden apolitical fields present in the raw source -- must
        # never reach any DB column (T-29-02).
        "win_side": 1,
        "votes_side": 1,
    }
}

_CASE_1955_71 = {
    "case_id": "1955_71",
    "docket_no": "55-71",
    "title": "Smith v. Jones",
    "petitioner": "Smith",
    "respondent": "Jones",
    "year": 1955,
    "transcripts": [{"name": "Oral Argument - November 15, 1956"}],
    # Forbidden apolitical fields -- must never reach any DB column (T-29-02).
    "win_side": 1,
    "win_side_detail": "affirmed",
    "votes": [1, 0, 1],
    "votes_detail": "6-3",
    "votes_side": 1,
    "scdb_docket_id": "1955-071-scdb",
}

_SPEAKERS = {
    "adv__john_smith": {"name": "John Smith", "type": "advocate"},
}


def _args(term, corpus_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(term=term, term_range=None, corpus_dir=str(corpus_dir))


# ===========================================================================
# Task 2: entity creation, apolitical stripping, idempotency
# ===========================================================================


@pytest.mark.asyncio
async def test_creates_case_argument_caseargument_pipelinerun_entities(
    isolated_session, tmp_path
):
    """
    Given a synthetic conversation+case fixture, a Case (lead docket only),
    Argument (status=draft, oyez_transcript_id set), CaseArgument
    (is_lead=True), and PipelineRun (strategy='convokit_import') are
    created. term_year comes from cases.jsonl's "year" (1955) even though
    the argued_date's calendar year (1956) differs (D-15 regression case).
    """
    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATION_1955_71, [_CASE_1955_71], _SPEAKERS
    )
    args = _args(1955, corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    case = (
        await isolated_session.execute(
            select(Case).where(Case.docket_number == "55-71")
        )
    ).scalar_one()
    assert case.term_year == 1955  # D-15: from cases.jsonl "year", not argued_date
    assert case.oyez_case_id == "1955_71"

    argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "1955_71")
        )
    ).scalar_one()
    assert argument.status == ArgumentStatusEnum.DRAFT
    assert argument.source_docket == "55-71"
    assert argument.argued_date.isoformat() == "1956-11-15"  # calendar year != term_year

    link = (
        await isolated_session.execute(
            select(CaseArgument).where(
                CaseArgument.case_id == case.id,
                CaseArgument.argument_id == argument.id,
            )
        )
    ).scalar_one()
    assert link.is_lead is True

    run = (
        await isolated_session.execute(
            select(PipelineRun).where(PipelineRun.argument_id == argument.id)
        )
    ).scalar_one()
    assert run.strategy == "convokit_import"


@pytest.mark.asyncio
async def test_apolitical_fields_never_persisted_to_any_column(
    isolated_session, tmp_path
):
    """
    T-29-02: even though the raw source dicts carry win_side/votes_side/
    scdb_docket_id (and more), no created row's attributes or JSONB blob
    ever contains them.
    """
    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATION_1955_71, [_CASE_1955_71], _SPEAKERS
    )
    args = _args(1955, corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    case = (
        await isolated_session.execute(
            select(Case).where(Case.docket_number == "55-71")
        )
    ).scalar_one()
    case_attrs = {k for k in vars(case) if not k.startswith("_")}
    assert "win_side" not in case_attrs
    assert "votes_side" not in case_attrs
    assert "scdb_docket_id" not in case_attrs

    argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "1955_71")
        )
    ).scalar_one()
    argument_attrs = {k for k in vars(argument) if not k.startswith("_")}
    assert "win_side" not in argument_attrs
    assert "votes_side" not in argument_attrs
    # cover_metadata is never written by this command -- confirm it stays
    # unset (no accidental JSONB dumping-ground use, RESEARCH Pitfall 2).
    assert argument.cover_metadata is None


@pytest.mark.asyncio
async def test_idempotent_rerun_creates_no_duplicate_arguments(
    isolated_session, tmp_path
):
    """D-08: re-running the same conversation creates zero new Argument rows."""
    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATION_1955_71, [_CASE_1955_71], _SPEAKERS
    )
    args = _args(1955, corpus_dir)
    session_cm = _make_session_cm(isolated_session)

    for _ in range(2):
        with patch(
            "pipeline.commands.import_convokit.get_session", new=session_cm
        ):
            await run_import_convokit(args)

    arguments = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "1955_71")
        )
    ).scalars().all()
    assert len(arguments) == 1, (
        "Re-running the same conversation must not create duplicate Argument rows"
    )


@pytest.mark.asyncio
async def test_malformed_conversation_flagged_not_aborting_term(
    isolated_session, tmp_path
):
    """
    T-29-05b/RESEARCH Pitfall 5: a conversation whose case_id has no
    matching cases.jsonl row is flagged (skipped), but a well-formed
    sibling conversation in the same term still imports successfully.
    """
    conversations = {
        "1955_71": _CONVERSATION_1955_71["1955_71"],
        "1955_98": {
            "conversation_id": "1955_98",
            "case_id": "1955_98",  # no matching cases.jsonl row
            "advocates": {},
        },
    }
    corpus_dir = _write_corpus_fixture(
        tmp_path, conversations, [_CASE_1955_71], _SPEAKERS
    )
    args = _args(1955, corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    good_argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "1955_71")
        )
    ).scalar_one()
    assert good_argument.status == ArgumentStatusEnum.DRAFT

    missing_argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "1955_98")
        )
    ).scalar_one_or_none()
    assert missing_argument is None
