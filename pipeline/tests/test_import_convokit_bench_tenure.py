"""
Tests for pipeline.commands.import_convokit's bench-versus-advocate
classification decision (Phase 42 Task 3, Review Gate item 2).

Covers option `bench-warn-only`, the option the operator approved
2026-07-30 for Review Gate item 2 (`.planning/CORPUS-FIDELITY-DIFF.md`'s
Disposition section): a speaker typed a Justice in speakers.json whose
resolved Person has no `CourtTenure` row covering the argument's
`argued_date` is still classified BENCH -- `side` is never reassigned --
but the mismatch is counted in `counters["bench_tenure_mismatch"]` and a
warning is printed naming the speaker id, `argued_date`, and the earliest
`CourtTenure.start_date` on record for that person.

Includes the exact boundary pair the plan requires: one test where the
tenure `start_date` equals `argued_date` (inclusive start -- covers, no
mismatch), one where it is one day later (does not cover -- mismatch),
plus a null-`argued_date` fallback test (no tenure check runs at all).

DB-dependent tests are skipped when DATABASE_URL/TEST_DATABASE_URL is not
set (via conftest.py's test_db_url fixture -> pytest.skip). Never reads
the real data/corpus/ files -- all fixtures are small, synthetic
corpus_dir trees written to tmp_path, matching
test_import_convokit_core.py's/test_import_convokit_utterances.py's
established per-module fixture pattern.
"""

import argparse
import json
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import select

from api.models.models import (
    Argument,
    ArgumentParticipant,
    CourtTenure,
    Person,
    SideEnum,
)
from pipeline.commands.import_convokit import run_import_convokit

# ===========================================================================
# Shared fixtures / helpers (same pattern as test_import_convokit_core.py /
# test_import_convokit_utterances.py)
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
    back after the test -- avoids the pre-existing Windows/asyncpg +
    pytest-asyncio stale-event-loop issue (see test_import_convokit_core.py's
    identical fixture)."""
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
    """Write a small synthetic corpus_dir tree (never the real corpus
    files). No utterances.jsonl rows are needed for these tests -- the
    justice is already present in the conversation's "advocates" dict, so
    the advocates loop alone resolves and links the participant -- but
    run_import_convokit still requires utterances.jsonl to exist."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "conversations.json").write_text(
        json.dumps(conversations), encoding="utf-8"
    )
    with (corpus_dir / "cases.jsonl").open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case) + "\n")
    (corpus_dir / "speakers.json").write_text(json.dumps(speakers), encoding="utf-8")
    (corpus_dir / "utterances.jsonl").write_text("", encoding="utf-8")
    return corpus_dir


def _args(term, corpus_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(term=term, term_range=None, corpus_dir=str(corpus_dir))


async def _seed_justice_person(
    isolated_session, oyez_speaker_id: str, full_name: str, tenures: list[tuple]
) -> Person:
    """Pre-create a Person row (is_justice=True) with oyez_speaker_id
    already set, plus zero or more CourtTenure rows -- so
    _resolve_person's FIRST lookup (Person.oyez_speaker_id) matches this
    exact row directly, bypassing full_name dedup entirely. `tenures` is a
    list of (start_date, end_date) tuples; end_date may be None (open
    tenure)."""
    person = Person(full_name=full_name, oyez_speaker_id=oyez_speaker_id, is_justice=True)
    isolated_session.add(person)
    await isolated_session.flush()
    for start_date, end_date in tenures:
        isolated_session.add(
            CourtTenure(
                person_id=person.id,
                office="associate",
                start_date=start_date,
                end_date=end_date,
            )
        )
    await isolated_session.flush()
    return person


def _conversation_and_case(
    conversation_id: str, docket: str, transcripts: list[dict]
) -> tuple[dict, dict]:
    conversation = {
        conversation_id: {
            "conversation_id": conversation_id,
            "case_id": conversation_id,
            "advocates": {"j__test_justice_doe": {"side": 3}},
        }
    }
    case = {
        "id": conversation_id,
        "docket_no": docket,
        "title": "Bench Tenure v. Test",
        "petitioner": "Bench Tenure",
        "respondent": "Test",
        "year": 1967,
        "transcripts": transcripts,
    }
    return conversation, case


_SPEAKERS = {"j__test_justice_doe": {"name": "Test Justice Doe", "type": "justice"}}


async def _run_and_fetch(
    isolated_session, tmp_path, conversation_id: str, docket: str, transcripts: list[dict]
) -> tuple[Argument, ArgumentParticipant]:
    conversation, case = _conversation_and_case(conversation_id, docket, transcripts)
    corpus_dir = _write_corpus_fixture(tmp_path, conversation, [case], _SPEAKERS)
    args = _args(1967, corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == conversation_id)
        )
    ).scalar_one()
    participant = (
        await isolated_session.execute(
            select(ArgumentParticipant).where(
                ArgumentParticipant.argument_id == argument.id
            )
        )
    ).scalar_one()
    return argument, participant


# ===========================================================================
# Boundary pair: start_date == argued_date (covers) vs. one day later (mismatch)
# ===========================================================================


@pytest.mark.asyncio
async def test_tenure_start_date_equal_to_argued_date_covers_inclusive(
    isolated_session, tmp_path, capsys
):
    """A CourtTenure whose start_date exactly equals argued_date IS
    treated as covering (inclusive start boundary) -- no mismatch, no
    warning, side stays BENCH."""
    await _seed_justice_person(
        isolated_session,
        "j__test_justice_doe",
        "Test Justice Doe",
        tenures=[(date(1967, 1, 9), None)],
    )
    argument, participant = await _run_and_fetch(
        isolated_session,
        tmp_path,
        "1967_900",
        "67-900",
        transcripts=[{"name": "Oral Argument - January 09, 1967"}],
    )

    assert argument.argued_date == date(1967, 1, 9)
    assert participant.side == SideEnum.BENCH

    captured = capsys.readouterr()
    assert "bench_tenure_mismatch" not in captured.out
    assert "0 bench tenure mismatches" in captured.out


@pytest.mark.asyncio
async def test_tenure_start_date_one_day_later_is_mismatch_side_unchanged(
    isolated_session, tmp_path, capsys
):
    """A CourtTenure whose ONLY start_date is one day AFTER argued_date
    does NOT cover -- bench_tenure_mismatch increments, a warning names
    the speaker id/argued_date/earliest tenure start_date, and (warn-only)
    side is STILL BENCH -- no reassignment to the advocate side code."""
    await _seed_justice_person(
        isolated_session,
        "j__test_justice_doe",
        "Test Justice Doe",
        tenures=[(date(1967, 1, 10), None)],
    )
    argument, participant = await _run_and_fetch(
        isolated_session,
        tmp_path,
        "1967_901",
        "67-901",
        transcripts=[{"name": "Oral Argument - January 09, 1967"}],
    )

    assert argument.argued_date == date(1967, 1, 9)
    # bench-warn-only: side is UNCHANGED, still BENCH, even though the
    # tenure check found a mismatch.
    assert participant.side == SideEnum.BENCH

    captured = capsys.readouterr()
    assert "j__test_justice_doe" in captured.out
    assert "1967-01-09" in captured.out
    assert "1967-01-10" in captured.out
    assert "1 bench tenure mismatches" in captured.out


@pytest.mark.asyncio
async def test_tenure_check_never_writes_court_tenure_or_is_justice(
    isolated_session, tmp_path
):
    """The mismatch case above never creates, updates, or deletes a
    CourtTenure row, and never flips Person.is_justice (D-03)."""
    await _seed_justice_person(
        isolated_session,
        "j__test_justice_doe",
        "Test Justice Doe",
        tenures=[(date(1967, 1, 10), None)],
    )
    await _run_and_fetch(
        isolated_session,
        tmp_path,
        "1967_902",
        "67-902",
        transcripts=[{"name": "Oral Argument - January 09, 1967"}],
    )

    person = (
        await isolated_session.execute(
            select(Person).where(Person.oyez_speaker_id == "j__test_justice_doe")
        )
    ).scalar_one()
    assert person.is_justice is True

    tenures = (
        await isolated_session.execute(
            select(CourtTenure).where(CourtTenure.person_id == person.id)
        )
    ).scalars().all()
    assert len(tenures) == 1
    assert tenures[0].start_date == date(1967, 1, 10)
    assert tenures[0].end_date is None


# ===========================================================================
# Null argued_date fallback: no tenure check runs at all
# ===========================================================================


@pytest.mark.asyncio
async def test_null_argued_date_skips_tenure_check_trusts_speaker_registry(
    isolated_session, tmp_path, capsys
):
    """When argued_date is None (no parseable transcript date), the
    tenure check does not run at all -- classification falls back to
    today's behavior (trust speakers.json's type outright) even though
    this person has zero CourtTenure rows on file (which would otherwise
    be a mismatch)."""
    await _seed_justice_person(
        isolated_session,
        "j__test_justice_doe",
        "Test Justice Doe",
        tenures=[],  # no tenure at all -- would mismatch if checked
    )
    argument, participant = await _run_and_fetch(
        isolated_session,
        tmp_path,
        "1967_903",
        "67-903",
        transcripts=[],  # no transcripts entry -> _parse_argued_date returns None
    )

    assert argument.argued_date is None
    assert participant.side == SideEnum.BENCH

    captured = capsys.readouterr()
    assert "bench_tenure_mismatch" not in captured.out
    assert "0 bench tenure mismatches" in captured.out
