"""
D-09's byte-identical double-import proof (Phase 50, plan 50-01, Task 3).

Imports ONE synthetic conversation, snapshots every row of the eight
tables an import can touch (arguments, cases, case_arguments,
argument_participants, import_run, utterances, value_discrepancy,
admin_jobs) for that argument, re-imports the IDENTICAL input, snapshots
again, and asserts the two snapshots are equal -- proof the reconcile
branch this plan's Task 3 establishes (_reconcile_conversation) writes
NOTHING when the incoming content digest matches the stored one (D-01,
D-06, D-09, IMPORT-04).

Also asserts:
    - content_digest is a 64-character lowercase hex string on the
      step="parse" ImportRun (D-13).
    - oyez_speaker_id is non-NULL on every ArgumentParticipant row the
      importer writes (D-04).
    - counters["arguments_unchanged"] increments by exactly 1 on the
      second pass (captured via the printed per-term summary, matching
      test_import_convokit_utterances.py's existing capsys convention).

DB-dependent tests are skipped when DATABASE_URL/TEST_DATABASE_URL is not
set (via conftest.py's test_db_url fixture -> pytest.skip). Uses a small
synthetic corpus_dir tree written to tmp_path (same convention as
test_import_convokit_adminjob.py) -- never the real 900MB
utterances.jsonl.
"""

import json
import re
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import select

from api.models.models import (
    AdminJob,
    Argument,
    ArgumentParticipant,
    Case,
    CaseArgument,
    ImportRun,
    Utterance,
    ValueDiscrepancy,
)
from pipeline.commands.import_convokit import run_import_convokit

# ===========================================================================
# Shared fixtures / helpers (same pattern as test_import_convokit_adminjob.py)
# ===========================================================================


def _make_session_cm(session):
    @asynccontextmanager
    async def _cm():
        yield session

    return _cm


@pytest.fixture()
async def isolated_session(test_db_url):
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
    subdir: str,
) -> Path:
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


_CONVERSATION_ID = "9997_71"

_CONVERSATION = {
    _CONVERSATION_ID: {
        "conversation_id": _CONVERSATION_ID,
        "case_id": _CONVERSATION_ID,
        "advocates": {"adv__pat_tracer50": {"side": 1}},
    }
}
_CASE = {
    "id": _CONVERSATION_ID,
    "docket_no": "55-97",
    # A distinct case name/slug from test_import_convokit_adminjob.py's
    # "Roe v. Doe" fixture ("55-98") -- both files' cases would otherwise
    # collide on the same derived slug ("roe-v-doe") when run in the same
    # pytest session, since Case.slug carries a UNIQUE constraint.
    "title": "Tracer50 v. Reimport",
    "petitioner": "Tracer50",
    "respondent": "Reimport",
    "year": 1955,
    "transcripts": [{"name": "Oral Argument - November 15, 1955"}],
}
_SPEAKERS = {
    "adv__pat_tracer50": {"name": "Pat Tracer50", "type": "advocate"},
    "j__tracer50_bench_justice": {"name": "Tracer50 Bench Justice", "type": "justice"},
}
_UTTERANCES = [
    {
        "id": "u1",
        "conversation_id": _CONVERSATION_ID,
        "speaker": "adv__pat_tracer50",
        "text": "May it please the Court.",
    },
    {
        "id": "u2",
        "conversation_id": _CONVERSATION_ID,
        "speaker": "j__tracer50_bench_justice",
        "text": "Counsel, what about the statute's plain text?\n(Laughter)",
    },
]


async def _run_import(isolated_session, tmp_path, subdir: str, term: int = 9997):
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


def _row_to_dict(row) -> dict:
    """Plain column-name -> value dict for one ORM row (excludes SQLAlchemy
    internal instance state) -- used for byte-identical snapshot equality."""
    return {c.key: getattr(row, c.key) for c in row.__table__.columns}


async def _snapshot(isolated_session, argument_id: int) -> dict:
    """Snapshot every row across all eight D-01-named tables this import
    can touch, scoped to `argument_id` (and, for `cases`, the case(s)
    linked to it via case_arguments)."""
    isolated_session.expire_all()

    argument_row = (
        await isolated_session.execute(select(Argument).where(Argument.id == argument_id))
    ).scalar_one()

    case_arguments = (
        (
            await isolated_session.execute(
                select(CaseArgument)
                .where(CaseArgument.argument_id == argument_id)
                .order_by(CaseArgument.case_id)
            )
        )
        .scalars()
        .all()
    )
    case_ids = [ca.case_id for ca in case_arguments]
    cases = (
        (
            await isolated_session.execute(
                select(Case).where(Case.id.in_(case_ids)).order_by(Case.id)
            )
        )
        .scalars()
        .all()
        if case_ids
        else []
    )

    participants = (
        (
            await isolated_session.execute(
                select(ArgumentParticipant)
                .where(ArgumentParticipant.argument_id == argument_id)
                .order_by(ArgumentParticipant.id)
            )
        )
        .scalars()
        .all()
    )
    runs = (
        (
            await isolated_session.execute(
                select(ImportRun)
                .where(ImportRun.argument_id == argument_id)
                .order_by(ImportRun.id)
            )
        )
        .scalars()
        .all()
    )
    utterances = (
        (
            await isolated_session.execute(
                select(Utterance)
                .where(Utterance.argument_id == argument_id)
                .order_by(Utterance.sequence)
            )
        )
        .scalars()
        .all()
    )
    # Phase 50 Task 3 writes NOTHING to value_discrepancy (the compare-and-
    # record body lands in plan 50-05) -- this table has no argument_id
    # column of its own (target_type/target_id is a generic polymorphic
    # reference), so scope by the two target_types this argument's own
    # constituents COULD ever carry (argument_participant rows belonging to
    # this argument) rather than assuming a bare "argument" target_type
    # that api/services/admin_review.py never actually uses.
    participant_ids_for_discrepancy_scope = [p.id for p in participants]
    if participant_ids_for_discrepancy_scope:
        discrepancies = (
            (
                await isolated_session.execute(
                    select(ValueDiscrepancy).where(
                        ValueDiscrepancy.target_type == "argument_participant",
                        ValueDiscrepancy.target_id.in_(
                            participant_ids_for_discrepancy_scope
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )
    else:
        discrepancies = []
    admin_jobs = (
        (
            await isolated_session.execute(
                select(AdminJob).where(AdminJob.argument_id == argument_id)
            )
        )
        .scalars()
        .all()
    )

    return {
        "arguments": [_row_to_dict(argument_row)],
        "cases": [_row_to_dict(row) for row in cases],
        "case_arguments": [_row_to_dict(row) for row in case_arguments],
        "argument_participants": [_row_to_dict(row) for row in participants],
        "import_run": [_row_to_dict(row) for row in runs],
        "utterances": [_row_to_dict(row) for row in utterances],
        "value_discrepancy": [_row_to_dict(row) for row in discrepancies],
        "admin_jobs": [_row_to_dict(row) for row in admin_jobs],
    }


# ===========================================================================
# Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_double_import_is_byte_identical_across_all_eight_tables(
    isolated_session, tmp_path
):
    await _run_import(isolated_session, tmp_path, subdir="corpus1")
    argument = await _fetch_argument(isolated_session)
    before = await _snapshot(isolated_session, argument.id)

    # Re-import the IDENTICAL input a second time (fresh corpus_dir tree,
    # same conversation_id/oyez_transcript_id, same content).
    await _run_import(isolated_session, tmp_path, subdir="corpus2")

    after = await _snapshot(isolated_session, argument.id)

    for table_name in before:
        assert after[table_name] == before[table_name], (
            f"{table_name} snapshot changed across an identical re-import"
        )


@pytest.mark.asyncio
async def test_zero_admin_job_and_zero_value_discrepancy_rows(
    isolated_session, tmp_path
):
    await _run_import(isolated_session, tmp_path, subdir="corpus1")
    argument = await _fetch_argument(isolated_session)
    await _run_import(isolated_session, tmp_path, subdir="corpus2")

    snapshot = await _snapshot(isolated_session, argument.id)
    assert snapshot["admin_jobs"] == []
    assert snapshot["value_discrepancy"] == []


@pytest.mark.asyncio
async def test_content_digest_is_64_char_lowercase_hex_on_parse_run(
    isolated_session, tmp_path
):
    await _run_import(isolated_session, tmp_path, subdir="corpus1")
    argument = await _fetch_argument(isolated_session)

    run = (
        await isolated_session.execute(
            select(ImportRun).where(
                ImportRun.argument_id == argument.id, ImportRun.step == "parse"
            )
        )
    ).scalar_one()

    assert run.content_digest is not None
    assert len(run.content_digest) == 64
    assert run.content_digest == run.content_digest.lower()
    assert all(c in "0123456789abcdef" for c in run.content_digest)


@pytest.mark.asyncio
async def test_every_participant_row_has_non_null_oyez_speaker_id(
    isolated_session, tmp_path
):
    await _run_import(isolated_session, tmp_path, subdir="corpus1")
    argument = await _fetch_argument(isolated_session)

    participants = (
        (
            await isolated_session.execute(
                select(ArgumentParticipant).where(
                    ArgumentParticipant.argument_id == argument.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(participants) == 2  # Pat Tracer50 (advocate) + Tracer50 Bench Justice
    for participant in participants:
        assert participant.oyez_speaker_id is not None


@pytest.mark.asyncio
async def test_arguments_unchanged_counter_increments_by_one_on_second_pass(
    isolated_session, tmp_path, capsys
):
    await _run_import(isolated_session, tmp_path, subdir="corpus1")
    capsys.readouterr()  # discard first pass's output

    await _run_import(isolated_session, tmp_path, subdir="corpus2")
    captured = capsys.readouterr()

    match = re.search(r"(\d+) arguments unchanged", captured.out)
    assert match is not None, captured.out
    assert int(match.group(1)) == 1

    reconciled_match = re.search(r"(\d+) arguments reconciled", captured.out)
    assert reconciled_match is not None, captured.out
    assert int(reconciled_match.group(1)) == 0
