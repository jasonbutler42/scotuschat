"""
End-to-end provenance tests for the `import_run` table (Phase 47, PROV-01,
PROV-02, PROV-04, PROV-05, PROV-06).

Covers the corpus/direct leg of D-06's three-combination verification
guardrail: every `import_run` row written by
`pipeline.commands.import_convokit.run_import_convokit` carries a declared
`source=ImportSource.CORPUS` / `method=ImportMethod.DIRECT`, `external_id`
dual-writes the ConvoKit conversation id, `pdf_path`/`pdf_url` stay NULL
(the corpus path fabricates no PDF artifacts, PROV-06), and
`Argument.oyez_transcript_id` is unchanged (RESEARCH.md Pitfall 1). Also
proves the NOT NULL storage-boundary guarantee (T-47-06): an `import_run`
row cannot exist without a declared `source` or `method`.

Plan 47-02 adds the two pdf_pipeline legs (rule_based/llm_corrective) below,
proving all three D-06 combinations end-to-end: `pipeline.commands.parse.run_parse`
stamps `source=ImportSource.PDF_PIPELINE` and exactly one of
`ImportMethod.RULE_BASED` / `ImportMethod.LLM_CORRECTIVE`, decided by whether
the LLM corrective pass raised or returned (T-47-07).

DB-dependent tests use `async_session` from `pipeline/tests/conftest.py` so
every write goes to `TEST_DATABASE_URL` (never a bare `DATABASE_URL`
connection); the fixture rolls back after each test. Never touches the
real 900MB corpus — fixtures are small, synthetic corpus_dir trees written
to `tmp_path`, reused from `pipeline/tests/test_import_convokit_core.py`.
"""

import argparse
import json
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.models.models import (
    Argument,
    ArgumentStatusEnum,
    Case,
    CaseArgument,
    ImportMethod,
    ImportRun,
    ImportRunStatus,
    ImportSource,
    Utterance,
)
from pipeline.commands.import_convokit import run_import_convokit
from pipeline.commands.parse import run_parse
from pipeline.parser.llm_pass import ParsedUtterance, ParseResponse

# ---------------------------------------------------------------------------
# Fixture helpers/constants copied (not imported) from
# pipeline/tests/test_import_convokit_core.py -- that module's own top-level
# `from api.models.models import (..., PipelineRun, PipelineRunStatus, ...)`
# is broken until plans 47-04/47-05 convert the test suite (wave 3, see
# 47-01-PLAN.md <intermediate_state_note>), so importing it here would fail
# collection. The plan's own action explicitly allows "import them or copy
# them locally" -- copied verbatim, never touches the real 900MB corpus.
# ---------------------------------------------------------------------------


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
    # run_import_convokit requires utterances.jsonl to exist (streamed once
    # per term) -- these provenance tests don't exercise utterance content,
    # so an empty file (zero turns) is enough (also proves the PROV-05 empty
    # edge: a zero-utterance import still writes a provenance-carrying run).
    (corpus_dir / "utterances.jsonl").write_text("", encoding="utf-8")
    return corpus_dir


_CONVERSATION_9999_71 = {
    "9999_71": {
        "conversation_id": "9999_71",
        "case_id": "9999_71",
        "advocates": {"adv__john_smith": {"side": 1}},
        # Forbidden apolitical fields present in the raw source -- must
        # never reach any DB column (T-29-02) -- irrelevant to this test
        # file but kept for fixture parity with test_import_convokit_core.py.
        "win_side": 1,
        "votes_side": 1,
    }
}

_CASE_9999_71 = {
    "id": "9999_71",
    "docket_no": "55-71",
    "title": "Smith v. Jones",
    "petitioner": "Smith",
    "respondent": "Jones",
    "year": 1955,
    "transcripts": [{"name": "Oral Argument - November 15, 1956"}],
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


def _make_session_cm(session):
    """
    Create a context manager that yields `session`.

    Mirrors pipeline/tests/test_import_convokit_core.py's identical helper
    -- patches pipeline.commands.import_convokit.get_session so the run
    writes through this test's own async_session (TEST_DATABASE_URL,
    rolled back after the test) instead of opening a real, separately
    committed connection.
    """

    @asynccontextmanager
    async def _cm():
        yield session

    return _cm


async def _run_corpus_import(async_session, tmp_path, monkeypatch, conversation_id="9999_71"):
    """Shared setup: write the synthetic corpus fixture and import it once."""
    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATION_9999_71, [_CASE_9999_71], _SPEAKERS
    )
    args = _args(9999, corpus_dir)
    monkeypatch.setattr(
        "pipeline.commands.import_convokit.get_session",
        _make_session_cm(async_session),
    )
    await run_import_convokit(args)
    return conversation_id, args


async def _rerun_corpus_import(async_session, args, monkeypatch):
    """Re-run run_import_convokit against an already-written corpus_dir."""
    monkeypatch.setattr(
        "pipeline.commands.import_convokit.get_session",
        _make_session_cm(async_session),
    )
    await run_import_convokit(args)


@pytest.mark.asyncio
async def test_corpus_import_stamps_source_corpus_method_direct(
    async_session, tmp_path, monkeypatch
):
    conversation_id, _ = await _run_corpus_import(async_session, tmp_path, monkeypatch)

    run = (
        await async_session.execute(
            select(ImportRun).where(ImportRun.external_id == conversation_id)
        )
    ).scalar_one()
    assert run.source == ImportSource.CORPUS
    assert run.method == ImportMethod.DIRECT


@pytest.mark.asyncio
async def test_corpus_import_populates_external_id(async_session, tmp_path, monkeypatch):
    conversation_id, _ = await _run_corpus_import(async_session, tmp_path, monkeypatch)

    run = (
        await async_session.execute(
            select(ImportRun).where(ImportRun.source == ImportSource.CORPUS)
        )
    ).scalar_one()
    assert run.external_id == conversation_id


@pytest.mark.asyncio
async def test_corpus_import_leaves_pdf_fields_null(async_session, tmp_path, monkeypatch):
    conversation_id, _ = await _run_corpus_import(async_session, tmp_path, monkeypatch)

    run = (
        await async_session.execute(
            select(ImportRun).where(ImportRun.external_id == conversation_id)
        )
    ).scalar_one()
    assert run.pdf_path is None
    assert run.pdf_url is None


@pytest.mark.asyncio
async def test_corpus_import_preserves_argument_oyez_transcript_id(
    async_session, tmp_path, monkeypatch
):
    """
    RESEARCH.md Pitfall 1: import_run.external_id is a dual-write, never a
    relocation -- Argument.oyez_transcript_id must still carry the same
    ConvoKit conversation id it always did.
    """
    conversation_id, _ = await _run_corpus_import(async_session, tmp_path, monkeypatch)

    argument = (
        await async_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == conversation_id)
        )
    ).scalar_one()
    assert argument.oyez_transcript_id == conversation_id


@pytest.mark.asyncio
async def test_corpus_reimport_is_idempotent_on_argument_and_stamps_provenance(
    async_session, tmp_path, monkeypatch
):
    """
    Re-running the corpus import for the same conversation id must not
    create a second Argument row, and every import_run row the corpus path
    wrote (across both runs) must still read source=corpus/method=direct.
    """
    conversation_id, args = await _run_corpus_import(async_session, tmp_path, monkeypatch)
    # Second import of the same conversation id, same corpus_dir -- the
    # idempotency dedup key (Argument.oyez_transcript_id) short-circuits
    # before any second ImportRun/Argument is created.
    await _rerun_corpus_import(async_session, args, monkeypatch)

    arguments = (
        await async_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == conversation_id)
        )
    ).scalars().all()
    assert len(arguments) == 1

    runs = (
        await async_session.execute(
            select(ImportRun).where(ImportRun.external_id == conversation_id)
        )
    ).scalars().all()
    assert len(runs) >= 1
    for run in runs:
        assert run.source == ImportSource.CORPUS
        assert run.method == ImportMethod.DIRECT


@pytest.mark.asyncio
async def test_corpus_import_writes_run_row_when_no_utterances(
    async_session, tmp_path, monkeypatch
):
    """
    PROV-05 empty edge: _write_corpus_fixture always writes an empty
    utterances.jsonl (zero turns) for these Task 2/3-style fixtures -- the
    corpus import must still write an import_run row carrying declared,
    non-null source/method even though it produces zero Utterance rows.
    """
    conversation_id, _ = await _run_corpus_import(async_session, tmp_path, monkeypatch)

    run = (
        await async_session.execute(
            select(ImportRun).where(ImportRun.external_id == conversation_id)
        )
    ).scalar_one()
    assert run.source is not None
    assert run.method is not None


@pytest.mark.asyncio
async def test_import_run_rejects_missing_source_and_method(async_session):
    """
    T-47-06: the database itself rejects an out-of-vocabulary/missing
    source or method at the storage boundary -- NOT NULL on both columns,
    no default (D-02, every writer declares provenance explicitly).
    """
    argument = Argument(status=ArgumentStatusEnum.PIPELINE)
    async_session.add(argument)
    await async_session.flush()

    async_session.add(
        ImportRun(
            argument_id=argument.id,
            step="parse",
            source=None,
            method=ImportMethod.DIRECT,
        )
    )
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()

    argument2 = Argument(status=ArgumentStatusEnum.PIPELINE)
    async_session.add(argument2)
    await async_session.flush()

    async_session.add(
        ImportRun(
            argument_id=argument2.id,
            step="parse",
            source=ImportSource.CORPUS,
            method=None,
        )
    )
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()


# ---------------------------------------------------------------------------
# pdf_pipeline legs (Plan 47-02): pipeline.commands.parse.run_parse stamps
# source=ImportSource.PDF_PIPELINE plus exactly one of ImportMethod.RULE_BASED
# / ImportMethod.LLM_CORRECTIVE, decided by whether the LLM corrective pass
# raised or returned (T-47-07). Skeleton reused from
# pipeline/tests/test_parse.py::test_run_id_strategy.
# ---------------------------------------------------------------------------


def _mock_extract_pages(pdf_path):
    """Minimal synthetic transcript — no real PDF is ever opened."""
    return [
        "CHIEF JUSTICE ROBERTS: We will hear argument now.\n"
        "MR. OLSON: Thank you, Mr. Chief Justice.\n"
        "(Laughter.)\n"
    ]


async def _seed_ingest_source_run(async_session, docket: str) -> ImportRun:
    """
    Seed a Case/Argument/CaseArgument/ImportRun(step="ingest") trio matching
    the shape pipeline/commands/ingest.py now writes (source=PDF_PIPELINE,
    method=NORMALIZED, pdf_path set), so the parse fixture matches production.
    The temp pdf_path is never opened — extract_pages is monkeypatched.
    """
    case = Case(
        docket_number=docket,
        docket_number_norm=docket.replace("-", ""),
        case_name=f"Test case {docket}",
        term_year=2024,
        slug=f"test-{docket}",
    )
    async_session.add(case)
    await async_session.flush()

    argument = Argument(question_number=1)
    async_session.add(argument)
    await async_session.flush()

    async_session.add(
        CaseArgument(case_id=case.id, argument_id=argument.id, is_lead=True)
    )
    await async_session.flush()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_pdf_path = f.name

    source_run = ImportRun(
        argument_id=argument.id,
        step="ingest",
        status=ImportRunStatus.COMPLETED,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.NORMALIZED,
        pdf_path=tmp_pdf_path,
    )
    async_session.add(source_run)
    await async_session.flush()

    return source_run


async def _run_parse_leg(async_session, monkeypatch, docket: str, llm_side_effect):
    """
    Seed an ingest source run, monkeypatch parse's LLM/extract/session
    dependencies, drive run_parse, and return (source_run, new_parse_run).
    """
    source_run = await _seed_ingest_source_run(async_session, docket)

    monkeypatch.setattr(
        "pipeline.commands.parse.extract_pages",
        _mock_extract_pages,
    )
    monkeypatch.setattr(
        "pipeline.commands.parse.parse_with_llm",
        llm_side_effect,
    )
    monkeypatch.setattr(
        "pipeline.commands.parse.get_session",
        _make_session_cm(async_session),
    )

    args = argparse.Namespace(run_id=source_run.id, dry_run=False, job_id=None)
    await run_parse(args)

    new_run = (
        await async_session.execute(
            select(ImportRun).where(
                ImportRun.argument_id == source_run.argument_id,
                ImportRun.step == "parse",
                ImportRun.id != source_run.id,
            )
        )
    ).scalar_one()

    return source_run, new_run


async def _raise_llm_unavailable(pages_text):
    raise RuntimeError("LLM not available in unit tests")


async def _return_llm_success(pages_text):
    return ParseResponse(
        utterances=[
            ParsedUtterance(
                sequence=1,
                raw_speaker_label="CHIEF JUSTICE ROBERTS",
                text="We will hear argument now.",
                is_stage_direction=False,
                section_hint=None,
            ),
            ParsedUtterance(
                sequence=2,
                raw_speaker_label="MR. OLSON",
                text="Thank you, Mr. Chief Justice.",
                is_stage_direction=False,
                section_hint=None,
            ),
        ]
    )


@pytest.mark.asyncio
async def test_parse_rule_based_stamps_pdf_pipeline_rule_based(
    async_session, monkeypatch
):
    _source_run, new_run = await _run_parse_leg(
        async_session, monkeypatch, "47-02-rb", _raise_llm_unavailable
    )
    assert new_run.source == ImportSource.PDF_PIPELINE
    assert new_run.method == ImportMethod.RULE_BASED


@pytest.mark.asyncio
async def test_parse_llm_success_stamps_pdf_pipeline_llm_corrective(
    async_session, monkeypatch
):
    _source_run, new_run = await _run_parse_leg(
        async_session, monkeypatch, "47-02-llm", _return_llm_success
    )
    assert new_run.source == ImportSource.PDF_PIPELINE
    assert new_run.method == ImportMethod.LLM_CORRECTIVE


@pytest.mark.asyncio
async def test_parse_utterances_link_to_import_run(async_session, monkeypatch):
    _source_run, new_run = await _run_parse_leg(
        async_session, monkeypatch, "47-02-link", _raise_llm_unavailable
    )

    rows = (
        await async_session.execute(
            select(Utterance).where(Utterance.import_run_id == new_run.id)
        )
    ).scalars().all()

    assert len(rows) > 0
    for row in rows:
        assert row.import_run_id == new_run.id
        assert not hasattr(row, "strategy")


@pytest.mark.asyncio
async def test_pdf_pipeline_run_populates_pdf_path(async_session, monkeypatch):
    source_run, new_run = await _run_parse_leg(
        async_session, monkeypatch, "47-02-pdfpath", _raise_llm_unavailable
    )

    assert new_run.pdf_path is not None
    assert new_run.pdf_path == source_run.pdf_path
    assert new_run.external_id is None


@pytest.mark.asyncio
async def test_d06_all_three_combinations_present(
    async_session, tmp_path, monkeypatch
):
    """
    D-06's three-combination verification guardrail: after driving one
    corpus import and both parse branches within this one test/transaction,
    the distinct (source, method) pairs present in import_run include
    exactly (corpus, direct), (pdf_pipeline, rule_based) and
    (pdf_pipeline, llm_corrective).
    """
    await _run_corpus_import(async_session, tmp_path, monkeypatch)
    await _run_parse_leg(
        async_session, monkeypatch, "47-02-d06-rb", _raise_llm_unavailable
    )
    await _run_parse_leg(
        async_session, monkeypatch, "47-02-d06-llm", _return_llm_success
    )

    pair_result = (
        await async_session.execute(
            select(ImportRun.source, ImportRun.method).distinct()
        )
    ).all()
    combos = {(row[0], row[1]) for row in pair_result}

    assert (ImportSource.CORPUS, ImportMethod.DIRECT) in combos
    assert (ImportSource.PDF_PIPELINE, ImportMethod.RULE_BASED) in combos
    assert (ImportSource.PDF_PIPELINE, ImportMethod.LLM_CORRECTIVE) in combos
