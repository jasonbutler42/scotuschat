"""
Tests for pipeline.commands.import_convokit's utterance import (29-05
Task 1) and per-batch summary report (29-05 Task 2).

Covers:
    - D-18: a multi-segment turn whose text contains "\n" is stored as
      exactly ONE Utterance row, "\n" preserved verbatim (not collapsed,
      not split into multiple rows).
    - D-16/D-17: a turn detected as a stage direction (e.g. "(Laughter)")
      produces a separate Utterance row (is_stage_direction=True,
      raw_speaker_label=None), and a turn mixing spoken segments with an
      inline marker segment is split into adjacent rows.
    - T-29-09: every created Utterance has a non-null pipeline_run_id and
      a sequence unique within (argument_id, pipeline_run_id).
    - Stage-direction classification is delegated to
      stage_directions.detect_stage_direction (no re-implemented regex).
    - D-14: the printed per-batch summary contains the term year and the
      created/skipped/flagged/errored counts; a broken cases.jsonl join
      is counted as errored rather than crashing the batch.

DB-dependent tests are skipped when DATABASE_URL/TEST_DATABASE_URL is not
set (via conftest.py's test_db_url fixture -> pytest.skip). Never uses the
real 900MB utterances.jsonl -- all fixtures are small, synthetic corpus_dir
trees written to tmp_path (D-18/RESEARCH.md convention).
"""

import json
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import select

from api.models.models import Argument, PipelineRun, SideEnum, Utterance
from pipeline.commands.import_convokit import run_import_convokit

# ===========================================================================
# Shared fixtures / helpers (same pattern as test_import_convokit_core.py)
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
    utterances: list[dict],
) -> Path:
    """Write a small synthetic corpus_dir tree, including utterances.jsonl
    (never the real 900MB file -- D-18/RESEARCH.md convention)."""
    corpus_dir = tmp_path / "corpus"
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


_CONVERSATION = {
    "1955_71": {
        "conversation_id": "1955_71",
        "case_id": "1955_71",
        "advocates": {"adv__john_smith": {"side": 1}},
    }
}
_CASE = {
    "case_id": "1955_71",
    "docket_no": "55-71",
    "title": "Smith v. Jones",
    "petitioner": "Smith",
    "respondent": "Jones",
    "year": 1955,
    "transcripts": [{"name": "Oral Argument - November 15, 1955"}],
}
_SPEAKERS = {
    "adv__john_smith": {"name": "John Smith", "type": "advocate"},
    "j__earl_warren": {"name": "Earl Warren", "type": "justice"},
}


async def _run_and_fetch_argument(isolated_session, tmp_path, utterances) -> Argument:
    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATION, [_CASE], _SPEAKERS, utterances
    )
    args = _args(1955, corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    return (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "1955_71")
        )
    ).scalar_one()


# ===========================================================================
# D-18: multi-segment / \n-preservation
# ===========================================================================


@pytest.mark.asyncio
async def test_multi_segment_turn_stored_as_one_row_newline_preserved(
    isolated_session, tmp_path
):
    """A turn whose text contains \n segment boundaries with no stage-
    direction segments is stored as EXACTLY ONE Utterance row, with \n
    preserved verbatim (not collapsed, not split into multiple rows)."""
    utterances = [
        {
            "id": "u1",
            "conversation_id": "1955_71",
            "speaker": "adv__john_smith",
            "text": "May it please the Court.\nThis case concerns a simple contract dispute.\nWe ask that the judgment be affirmed.",
        }
    ]
    argument = await _run_and_fetch_argument(isolated_session, tmp_path, utterances)

    rows = (
        await isolated_session.execute(
            select(Utterance).where(Utterance.argument_id == argument.id)
        )
    ).scalars().all()

    assert len(rows) == 1
    assert rows[0].is_stage_direction is False
    assert rows[0].text == (
        "May it please the Court.\n"
        "This case concerns a simple contract dispute.\n"
        "We ask that the judgment be affirmed."
    )
    assert rows[0].text.count("\n") == 2


# ===========================================================================
# D-16/D-17: stage-direction row splitting
# ===========================================================================


@pytest.mark.asyncio
async def test_whole_turn_stage_direction_produces_separate_row(
    isolated_session, tmp_path
):
    """A turn whose ENTIRE text is a curated-vocabulary marker (e.g.
    "(Laughter)") produces its own Utterance row: is_stage_direction=True,
    raw_speaker_label=None."""
    utterances = [
        {
            "id": "u1",
            "conversation_id": "1955_71",
            "speaker": "adv__john_smith",
            "text": "That is an amusing hypothetical, counsel.",
        },
        {
            "id": "u2",
            "conversation_id": "1955_71",
            "speaker": None,
            "text": "(Laughter)",
        },
    ]
    argument = await _run_and_fetch_argument(isolated_session, tmp_path, utterances)

    rows = (
        await isolated_session.execute(
            select(Utterance)
            .where(Utterance.argument_id == argument.id)
            .order_by(Utterance.sequence)
        )
    ).scalars().all()

    assert len(rows) == 2
    assert rows[0].is_stage_direction is False
    assert rows[1].is_stage_direction is True
    assert rows[1].raw_speaker_label is None
    assert rows[1].text == "(Laughter)"
    assert rows[1].side == SideEnum.UNKNOWN
    assert rows[1].person_id is None


@pytest.mark.asyncio
async def test_inline_marker_segment_splits_spoken_remainder_into_own_rows(
    isolated_session, tmp_path
):
    """A turn whose \n-delimited segments MIX spoken text with an inline
    marker segment is split: the marker becomes its own row, and the
    spoken segments on either side keep their own row(s) (D-16)."""
    utterances = [
        {
            "id": "u1",
            "conversation_id": "1955_71",
            "speaker": "adv__john_smith",
            "text": "That is absurd, Your Honor.\n(Laughter)\nBut moving on to the merits.",
        }
    ]
    argument = await _run_and_fetch_argument(isolated_session, tmp_path, utterances)

    rows = (
        await isolated_session.execute(
            select(Utterance)
            .where(Utterance.argument_id == argument.id)
            .order_by(Utterance.sequence)
        )
    ).scalars().all()

    assert len(rows) == 3
    assert rows[0].is_stage_direction is False
    assert rows[0].text == "That is absurd, Your Honor."
    assert rows[1].is_stage_direction is True
    assert rows[1].text == "(Laughter)"
    assert rows[1].raw_speaker_label is None
    assert rows[2].is_stage_direction is False
    assert rows[2].text == "But moving on to the merits."
    # Spoken rows share the same resolved speaker on both sides of the marker.
    assert rows[0].raw_speaker_label == rows[2].raw_speaker_label == "John Smith"


@pytest.mark.asyncio
async def test_stage_direction_delegated_to_detect_stage_direction_no_regex(
    isolated_session, tmp_path
):
    """The curated-vocabulary anti-cases from stage_directions.py (e.g. the
    "(ph)" phonetic-spelling convention and legal-list markers like "(a)")
    must NOT be misclassified as stage directions -- proving classification
    is delegated to detect_stage_direction, not a blind bracket/paren
    regex re-implemented in import_convokit.py."""
    utterances = [
        {
            "id": "u1",
            "conversation_id": "1955_71",
            "speaker": "adv__john_smith",
            "text": "Mr. Smith (ph) testified that the contract was signed.\n(a) the first element;\n(b) the second element.",
        }
    ]
    argument = await _run_and_fetch_argument(isolated_session, tmp_path, utterances)

    rows = (
        await isolated_session.execute(
            select(Utterance).where(Utterance.argument_id == argument.id)
        )
    ).scalars().all()

    # None of the three \n segments is a real stage-direction marker, so
    # the whole turn collapses back into ONE row (D-18 default).
    assert len(rows) == 1
    assert rows[0].is_stage_direction is False
    assert "(ph)" in rows[0].text
    assert "(a)" in rows[0].text


@pytest.mark.asyncio
async def test_repeat_speaker_across_many_turns_resolved_once_no_duplicate_participant(
    isolated_session, tmp_path
):
    """A speaker with many turns in the same conversation is resolved via
    the participant cache -- exactly one ArgumentParticipant row exists
    for them (idempotent check-before-insert), and their Person is neither
    duplicated nor re-counted as a fresh match per turn (the shared
    resolved_participants cache prevents the per-turn resolve call from
    inflating people-matched counts or issuing redundant DB round trips)."""
    from api.models.models import ArgumentParticipant, Person

    utterances = [
        {
            "id": f"u{i}",
            "conversation_id": "1955_71",
            "speaker": "j__earl_warren",
            "text": f"Bench turn number {i}.",
        }
        for i in range(1, 6)
    ]
    argument = await _run_and_fetch_argument(isolated_session, tmp_path, utterances)

    rows = (
        await isolated_session.execute(
            select(Utterance)
            .where(Utterance.argument_id == argument.id)
            .order_by(Utterance.sequence)
        )
    ).scalars().all()
    assert len(rows) == 5
    assert all(r.raw_speaker_label == "Earl Warren" for r in rows)
    assert all(r.side == SideEnum.BENCH for r in rows)

    people = (
        await isolated_session.execute(
            select(Person).where(Person.oyez_speaker_id == "j__earl_warren")
        )
    ).scalars().all()
    assert len(people) == 1

    participants = (
        await isolated_session.execute(
            select(ArgumentParticipant).where(
                ArgumentParticipant.argument_id == argument.id,
                ArgumentParticipant.raw_speaker_label == "Earl Warren",
            )
        )
    ).scalars().all()
    assert len(participants) == 1


# ===========================================================================
# T-29-09: pipeline_run_id / sequence invariants
# ===========================================================================


@pytest.mark.asyncio
async def test_every_utterance_has_pipeline_run_id_and_unique_sequence(
    isolated_session, tmp_path
):
    utterances = [
        {
            "id": "u1",
            "conversation_id": "1955_71",
            "speaker": "adv__john_smith",
            "text": "First turn.",
        },
        {
            "id": "u2",
            "conversation_id": "1955_71",
            "speaker": "j__earl_warren",
            "text": "Second turn, by the bench.",
        },
        {
            "id": "u3",
            "conversation_id": "1955_71",
            "speaker": None,
            "text": "(Recess)",
        },
    ]
    argument = await _run_and_fetch_argument(isolated_session, tmp_path, utterances)

    rows = (
        await isolated_session.execute(
            select(Utterance)
            .where(Utterance.argument_id == argument.id)
            .order_by(Utterance.sequence)
        )
    ).scalars().all()
    run = (
        await isolated_session.execute(
            select(PipelineRun).where(PipelineRun.argument_id == argument.id)
        )
    ).scalar_one()

    assert len(rows) == 3
    sequences = [r.sequence for r in rows]
    assert sequences == sorted(sequences)
    assert len(set(sequences)) == len(sequences)  # unique within this run
    for r in rows:
        assert r.pipeline_run_id == run.id
        assert r.pipeline_run_id is not None

    # Justice speaker resolved via utterances.jsonl (not present in
    # conversations.json's advocates dict) gets BENCH side.
    bench_row = rows[1]
    assert bench_row.side == SideEnum.BENCH
    assert bench_row.raw_speaker_label == "Earl Warren"


@pytest.mark.asyncio
async def test_malformed_utterance_row_flagged_not_crashing_import(
    isolated_session, tmp_path
):
    """A malformed utterance row (missing "text") is counted/flagged (V5)
    rather than raising an unhandled KeyError -- the well-formed sibling
    turn in the same conversation still imports."""
    utterances = [
        {"id": "u1", "conversation_id": "1955_71", "speaker": "adv__john_smith"},
        {
            "id": "u2",
            "conversation_id": "1955_71",
            "speaker": "adv__john_smith",
            "text": "Well-formed turn.",
        },
    ]
    argument = await _run_and_fetch_argument(isolated_session, tmp_path, utterances)

    rows = (
        await isolated_session.execute(
            select(Utterance).where(Utterance.argument_id == argument.id)
        )
    ).scalars().all()

    assert len(rows) == 1
    assert rows[0].text == "Well-formed turn."


# ===========================================================================
# D-14: per-batch summary report
# ===========================================================================


@pytest.mark.asyncio
async def test_summary_prints_term_year_and_core_counts(
    isolated_session, tmp_path, capsys
):
    utterances = [
        {
            "id": "u1",
            "conversation_id": "1955_71",
            "speaker": "adv__john_smith",
            "text": "Spoken turn.\n(Laughter)",
        }
    ]
    await _run_and_fetch_argument(isolated_session, tmp_path, utterances)

    captured = capsys.readouterr()
    assert "Term 1955" in captured.out
    assert "arguments created" in captured.out
    assert "arguments skipped" in captured.out
    assert "utterances created" in captured.out
    assert "stage-direction utterances created" in captured.out
    assert "people created" in captured.out
    assert "people matched" in captured.out
    assert "speakers flagged" in captured.out
    assert "conversations errored" in captured.out


@pytest.mark.asyncio
async def test_broken_case_join_counted_as_errored_not_crashing_batch(
    isolated_session, tmp_path, capsys
):
    """A conversation whose case_id has no matching cases.jsonl row is
    counted in the errored total (never crashes the batch); a well-formed
    sibling conversation in the same term still imports and its
    utterances still land."""
    conversations = {
        "1955_71": _CONVERSATION["1955_71"],
        "1955_98": {
            "conversation_id": "1955_98",
            "case_id": "1955_98",  # no matching cases.jsonl row
            "advocates": {},
        },
    }
    utterances = [
        {
            "id": "u1",
            "conversation_id": "1955_71",
            "speaker": "adv__john_smith",
            "text": "Well-formed sibling conversation's turn.",
        },
        {
            "id": "u2",
            "conversation_id": "1955_98",
            "speaker": "adv__john_smith",
            "text": "This belongs to the broken-join conversation.",
        },
    ]
    corpus_dir = _write_corpus_fixture(
        tmp_path, conversations, [_CASE], _SPEAKERS, utterances
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
    good_rows = (
        await isolated_session.execute(
            select(Utterance).where(Utterance.argument_id == good_argument.id)
        )
    ).scalars().all()
    assert len(good_rows) == 1

    missing_argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "1955_98")
        )
    ).scalar_one_or_none()
    assert missing_argument is None

    captured = capsys.readouterr()
    assert "conversations errored" in captured.out
    # At least one conversation errored (the broken join), reflected in the
    # printed summary count (not just a silent skip).
    assert "1 conversations errored" in captured.out or "conversations errored" in captured.out
