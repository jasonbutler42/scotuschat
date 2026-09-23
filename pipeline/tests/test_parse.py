"""
Parser unit tests for the rule-based state machine.

These tests do NOT require a database — they exercise pipeline/parser/state_machine.py
directly using in-memory transcript excerpts.

Test IDs covered (from VALIDATION.md):
  - 1-stage-dirs:  PIPE-05 stage direction classification
  - 1-parse-rows:  PIPE-03 parser output structure
  - 1-run-id:      PIPE-04 import_run_id and method (DB-dependent, skips if no DB)
  - 1-llm-failures: PIPE-06 LLM failure mode classification

Regression tests:
  - test_section_hint_not_cascade: Pitfall 3 (section hint must not cascade)
  - test_on_behalf_of_not_appended_to_prior_speaker: F04 regression (ON BEHALF OF fix)
"""

import argparse
import datetime
import inspect
import os
import tempfile
from contextlib import asynccontextmanager

import pytest

from api.models.models import Argument
from pipeline.commands.parse import _run_parse_inner, run_parse


def test_parse_docket_fill_uses_pair_precheck_and_named_race_classification():
    source = inspect.getsource(_run_parse_inner)
    assert "find_argument_by_pair(" in source
    assert "exclude_argument_id=source_run.argument_id" in source
    assert "argument_row.source_docket is None" in source
    assert "argument_row.question_number," in source
    assert "is_argument_pair_violation(exc)" in source
    assert "await session.rollback()" in source


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_page(*lines: str) -> str:
    """Join lines into a page string (simulates extract_pages output)."""
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Test 1: Stage direction classification (PIPE-05 / 1-stage-dirs)
# ---------------------------------------------------------------------------


def test_stage_directions():
    """
    Stage directions — lines like "(Laughter.)" and "(Brief pause.)" — must
    have is_stage_direction=True and raw_speaker_label=None.
    """
    from pipeline.parser.state_machine import parse_transcript

    page = make_page(
        "CHIEF JUSTICE ROBERTS: Thank you, counsel.",
        "(Laughter.)",
        "JUSTICE KAGAN: I have a question.",
        "(Brief pause.)",
        "MR. OLSON: Yes, Justice Kagan.",
    )
    utterances = parse_transcript([page])

    # Collect stage directions
    stage_dirs = [u for u in utterances if u["is_stage_direction"]]
    speech_turns = [u for u in utterances if not u["is_stage_direction"]]

    assert len(stage_dirs) == 2, (
        f"Expected 2 stage directions, got {len(stage_dirs)}: "
        f"{[u['text'] for u in stage_dirs]}"
    )
    assert len(speech_turns) == 3, (
        f"Expected 3 speech turns, got {len(speech_turns)}"
    )

    # All stage directions must have raw_speaker_label=None
    for sd in stage_dirs:
        assert sd["raw_speaker_label"] is None, (
            f"Stage direction should have raw_speaker_label=None, "
            f"got: {sd['raw_speaker_label']!r} for text: {sd['text']!r}"
        )
        assert sd["is_stage_direction"] is True

    # Stage direction texts should match
    stage_texts = {u["text"] for u in stage_dirs}
    assert "(Laughter.)" in stage_texts
    assert "(Brief pause.)" in stage_texts

    # Speech turns must NOT be stage directions
    for turn in speech_turns:
        assert turn["is_stage_direction"] is False
        assert turn["raw_speaker_label"] is not None


# ---------------------------------------------------------------------------
# Test 2: run_id and method on utterance rows (PIPE-04 / 1-run-id)
# DB-dependent — skips gracefully if no DATABASE_URL configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_id_and_method(async_session, monkeypatch):
    """
    Every utterance row must have import_run_id set, and the parent run's
    method must be declared (PIPE-04). The per-utterance strategy column was
    dropped in Phase 47 (D-05) — the method now lives on the parent
    ImportRun only.

    Skips if no database is configured (async_session fixture handles skip).
    """
    # Import here so skip happens before imports if DB not available
    import os
    from sqlalchemy import select
    from api.models.models import (
        Argument,
        Case,
        CaseArgument,
        ImportMethod,
        ImportRun,
        ImportRunStatus,
        ImportSource,
        Utterance,
    )

    # Monkeypatch LLM to avoid real API calls
    async def mock_parse_with_llm(pages_text):
        raise RuntimeError("LLM not available in unit tests")

    monkeypatch.setattr(
        "pipeline.commands.parse.parse_with_llm",
        mock_parse_with_llm,
    )

    # Also monkeypatch extract_pages to return a minimal transcript
    def mock_extract_pages(pdf_path):
        return [
            "CHIEF JUSTICE ROBERTS: We will hear argument now.\n"
            "MR. OLSON: Thank you, Mr. Chief Justice.\n"
            "(Laughter.)\n"
        ]

    monkeypatch.setattr(
        "pipeline.commands.parse.extract_pages",
        mock_extract_pages,
    )

    # Create minimal DB records
    import datetime

    case = Case(
        docket_number="99-TEST",
        docket_number_norm="99-TEST",
        case_name="Test v. Test",
        term_year=2024,
        slug="test-v-test",
    )
    async_session.add(case)
    await async_session.flush()

    argument = Argument(argued_date=datetime.date(2024, 1, 1), question_number=1)
    async_session.add(argument)
    await async_session.flush()

    case_arg = CaseArgument(case_id=case.id, argument_id=argument.id, is_lead=True)
    async_session.add(case_arg)
    await async_session.flush()

    # Write a temp PDF path (file doesn't need to exist for mock)
    import tempfile
    import pathlib
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name

    source_run = ImportRun(
        argument_id=argument.id,
        step="ingest",
        status=ImportRunStatus.COMPLETED,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.NORMALIZED,
        pdf_path=tmp_path,
    )
    async_session.add(source_run)
    await async_session.flush()

    # Run the parse command
    import argparse
    args = argparse.Namespace(run_id=source_run.id, dry_run=False, job_id=None)

    # Override get_session to use the test session
    from unittest.mock import AsyncMock, MagicMock
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_get_session():
        yield async_session

    monkeypatch.setattr("pipeline.commands.parse.get_session", mock_get_session)

    from pipeline.commands.parse import run_parse
    await run_parse(args)

    # run_parse() creates a BRAND-NEW ImportRun row for this parse attempt
    # (PIPE-11 re-run semantics: re-running a step never overwrites a prior
    # run's row) rather than writing utterances against `source_run` above
    # — that row is only the *source* record parse reads pdf_path/argument_id
    # from via args.run_id. Utterances link to the new run's id, not the
    # source run's id.
    new_run_result = await async_session.execute(
        select(ImportRun).where(
            ImportRun.argument_id == argument.id,
            ImportRun.step == "parse",
            ImportRun.id != source_run.id,
        )
    )
    new_run = new_run_result.scalar_one()

    # ImportMethod is declared on the parent run (Phase 47, D-05) — the
    # per-utterance strategy column no longer exists.
    assert new_run.method in (ImportMethod.RULE_BASED, ImportMethod.LLM_CORRECTIVE), (
        f"Expected new_run.method to be rule_based or llm_corrective, got {new_run.method}"
    )

    # Verify utterance rows have import_run_id set
    result = await async_session.execute(
        select(Utterance).where(Utterance.import_run_id == new_run.id)
    )
    rows = result.scalars().all()

    assert len(rows) > 0, "Expected at least 1 utterance row after parse"
    for row in rows:
        assert row.import_run_id is not None, "import_run_id must not be None"
        assert row.import_run_id == new_run.id

    # Cleanup temp file
    import os
    try:
        os.unlink(tmp_path)
    except OSError:
        pass


@pytest.mark.asyncio
async def test_parse_preserves_operator_docket_when_extracted_pair_conflicts(
    async_session, monkeypatch
):
    """A no-op extracted docket fill must not enter duplicate recovery."""
    import argparse
    import datetime
    import os
    import tempfile
    from contextlib import asynccontextmanager

    from api.models.models import (
        Argument,
        Case,
        CaseArgument,
        ImportMethod,
        ImportRun,
        ImportRunStatus,
        ImportSource,
    )
    from pipeline.commands.parse import run_parse

    case = Case(
        docket_number="99-OPERATOR",
        docket_number_norm="99-OPERATOR",
        case_name="Operator v. Extractor",
        term_year=2024,
        slug="operator-v-extractor",
    )
    async_session.add(case)
    await async_session.flush()

    target = Argument(
        argued_date=datetime.date(2024, 1, 1),
        source_docket="OPERATOR-DOCKET",
        question_number=1,
    )
    conflict = Argument(
        argued_date=datetime.date(2024, 1, 2),
        source_docket="EXTRACTED-DOCKET",
        question_number=1,
    )
    async_session.add_all([target, conflict])
    await async_session.flush()
    async_session.add(CaseArgument(case_id=case.id, argument_id=target.id, is_lead=True))

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pdf:
        pdf_path = pdf.name

    source_run = ImportRun(
        argument_id=target.id,
        step="ingest",
        status=ImportRunStatus.COMPLETED,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.NORMALIZED,
        pdf_path=pdf_path,
    )
    async_session.add(source_run)
    await async_session.flush()

    @asynccontextmanager
    async def mock_get_session():
        yield async_session

    monkeypatch.setattr("pipeline.commands.parse.get_session", mock_get_session)
    monkeypatch.setattr(
        "pipeline.commands.parse.extract_cover_metadata",
        lambda _path: {"primary_docket": "EXTRACTED-DOCKET"},
    )
    monkeypatch.setattr(
        "pipeline.commands.parse.extract_toc_data",
        lambda _path: {"sides": {}, "titles": {}},
    )
    monkeypatch.setattr(
        "pipeline.commands.parse.extract_pages",
        lambda _path: ["CHIEF JUSTICE ROBERTS: We will hear argument now."],
    )

    async def mock_parse_with_llm(_pages_text):
        raise RuntimeError("LLM not available in unit tests")

    monkeypatch.setattr("pipeline.commands.parse.parse_with_llm", mock_parse_with_llm)

    try:
        await run_parse(argparse.Namespace(run_id=source_run.id, dry_run=False, job_id=None))
        await async_session.refresh(target)
        assert target.source_docket == "OPERATOR-DOCKET"
    finally:
        try:
            os.unlink(pdf_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Phase 50 plan 50-06, Task 2: cover-metadata writes route through the
# Argument/Case authority gates (D-21/D-22). Real-writer integration tests.
# ---------------------------------------------------------------------------


async def _seed_parse_gate_fixture(
    async_session,
    *,
    argued_date=None,
    source_docket="EXISTING-DOCKET",
    case_name="Pet v. Resp",
    case_source=None,
    case_method=None,
):
    import datetime

    from api.models.models import Case, CaseArgument, ImportMethod, ImportRun, ImportRunStatus, ImportSource

    case = Case(
        docket_number=source_docket,
        docket_number_norm=source_docket.replace("-", ""),
        case_name=case_name,
        term_year=2024,
        slug=f"slug-{source_docket}".lower(),
        source=case_source,
        method=case_method,
    )
    async_session.add(case)
    await async_session.flush()

    argument = Argument(
        argued_date=argued_date,
        source_docket=source_docket,
        question_number=1,
    )
    async_session.add(argument)
    await async_session.flush()

    async_session.add(CaseArgument(case_id=case.id, argument_id=argument.id, is_lead=True))
    await async_session.flush()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pdf:
        pdf_path = pdf.name

    source_run = ImportRun(
        argument_id=argument.id,
        step="ingest",
        status=ImportRunStatus.COMPLETED,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.NORMALIZED,
        pdf_path=pdf_path,
    )
    async_session.add(source_run)
    await async_session.flush()

    return argument, case, source_run, pdf_path


def _patch_parse_environment(monkeypatch, async_session, *, cover_meta, llm_mode):
    """
    llm_mode: "rule_based" (LLM raises, falls back) or "llm_corrective"
    (LLM returns a real ParseResponse).
    """

    @asynccontextmanager
    async def mock_get_session():
        yield async_session

    monkeypatch.setattr("pipeline.commands.parse.get_session", mock_get_session)
    monkeypatch.setattr(
        "pipeline.commands.parse.extract_cover_metadata", lambda _path: cover_meta
    )
    monkeypatch.setattr(
        "pipeline.commands.parse.extract_toc_data",
        lambda _path: {"sides": {}, "titles": {}},
    )
    monkeypatch.setattr(
        "pipeline.commands.parse.extract_pages",
        lambda _path: ["CHIEF JUSTICE ROBERTS: We will hear argument now."],
    )

    if llm_mode == "rule_based":
        async def mock_parse_with_llm(_pages_text):
            raise RuntimeError("LLM not available in unit tests")
    else:
        from pipeline.parser.llm_pass import ParsedUtterance, ParseResponse

        async def mock_parse_with_llm(_pages_text):
            return ParseResponse(
                utterances=[
                    ParsedUtterance(
                        sequence=1,
                        raw_speaker_label="CHIEF JUSTICE ROBERTS",
                        text="We will hear argument now.",
                        is_stage_direction=False,
                        section_hint=None,
                    )
                ]
            )

    monkeypatch.setattr("pipeline.commands.parse.parse_with_llm", mock_parse_with_llm)


@pytest.mark.asyncio
async def test_argued_date_gap_fill_writes_no_discrepancy(async_session, monkeypatch):
    """
    A rule-based parse run writing argued_date into a NULL column writes
    it and creates no value_discrepancy row (PD-13 gap-fill).
    """
    from sqlalchemy import select

    from api.models.models import ValueDiscrepancy

    argument, case, source_run, pdf_path = await _seed_parse_gate_fixture(
        async_session, argued_date=None
    )
    incoming_date = datetime.date(2021, 2, 2)
    _patch_parse_environment(
        monkeypatch,
        async_session,
        cover_meta={"argued_date": incoming_date},
        llm_mode="rule_based",
    )

    try:
        await run_parse(argparse.Namespace(run_id=source_run.id, dry_run=False, job_id=None))
        await async_session.refresh(argument)
        assert argument.argued_date == incoming_date

        discrepancies = (
            await async_session.execute(
                select(ValueDiscrepancy).where(
                    ValueDiscrepancy.target_type == "argument",
                    ValueDiscrepancy.target_id == argument.id,
                    ValueDiscrepancy.field == "argued_date",
                )
            )
        ).scalars().all()
        assert discrepancies == []
    finally:
        try:
            os.unlink(pdf_path)
        except OSError:
            pass


@pytest.mark.asyncio
async def test_argued_date_disagreement_rejected_and_recorded_rule_based(
    async_session, monkeypatch
):
    """
    A rule-based parse run writing argued_date that disagrees with an
    existing (operator-stamped, unstamped-provenance) value does NOT
    overwrite it and creates one discrepancy row whose incoming_source is
    pdf_pipeline and incoming_method is rule_based.
    """
    from sqlalchemy import select

    from api.models.models import ImportMethod, ImportSource, ValueDiscrepancy

    existing_date = datetime.date(2020, 1, 1)
    argument, case, source_run, pdf_path = await _seed_parse_gate_fixture(
        async_session, argued_date=existing_date
    )
    incoming_date = datetime.date(2021, 2, 2)
    _patch_parse_environment(
        monkeypatch,
        async_session,
        cover_meta={"argued_date": incoming_date},
        llm_mode="rule_based",
    )

    try:
        await run_parse(argparse.Namespace(run_id=source_run.id, dry_run=False, job_id=None))
        await async_session.refresh(argument)
        assert argument.argued_date == existing_date, "disagreeing write must not overwrite"

        discrepancies = (
            await async_session.execute(
                select(ValueDiscrepancy).where(
                    ValueDiscrepancy.target_type == "argument",
                    ValueDiscrepancy.target_id == argument.id,
                    ValueDiscrepancy.field == "argued_date",
                )
            )
        ).scalars().all()
        assert len(discrepancies) == 1
        assert discrepancies[0].incoming_source == ImportSource.PDF_PIPELINE
        assert discrepancies[0].incoming_method == ImportMethod.RULE_BASED
    finally:
        try:
            os.unlink(pdf_path)
        except OSError:
            pass


@pytest.mark.asyncio
async def test_argued_date_disagreement_records_llm_corrective_method(
    async_session, monkeypatch
):
    """
    An LLM-corrective parse run's disagreeing write records incoming_method
    llm_corrective, and is likewise rejected against an existing value.
    """
    from sqlalchemy import select

    from api.models.models import ImportMethod, ValueDiscrepancy

    existing_date = datetime.date(2020, 1, 1)
    argument, case, source_run, pdf_path = await _seed_parse_gate_fixture(
        async_session, argued_date=existing_date
    )
    incoming_date = datetime.date(2021, 2, 2)
    _patch_parse_environment(
        monkeypatch,
        async_session,
        cover_meta={"argued_date": incoming_date},
        llm_mode="llm_corrective",
    )

    try:
        await run_parse(argparse.Namespace(run_id=source_run.id, dry_run=False, job_id=None))
        await async_session.refresh(argument)
        assert argument.argued_date == existing_date

        discrepancies = (
            await async_session.execute(
                select(ValueDiscrepancy).where(
                    ValueDiscrepancy.target_type == "argument",
                    ValueDiscrepancy.target_id == argument.id,
                    ValueDiscrepancy.field == "argued_date",
                )
            )
        ).scalars().all()
        assert len(discrepancies) == 1
        assert discrepancies[0].incoming_method == ImportMethod.LLM_CORRECTIVE
    finally:
        try:
            os.unlink(pdf_path)
        except OSError:
            pass


@pytest.mark.asyncio
async def test_case_name_disagreement_no_longer_overwrites_corpus_value(
    async_session, monkeypatch
):
    """
    A parse run's case_name write that disagrees with a corpus-stamped
    lead Case.case_name is rejected and recorded — the previously
    unconditional overwrite no longer clobbers (T-50-20).
    """
    from sqlalchemy import select

    from api.models.models import ImportMethod, ImportSource, ValueDiscrepancy

    argument, case, source_run, pdf_path = await _seed_parse_gate_fixture(
        async_session,
        case_name="Corpus-Authored Case Name",
        case_source=ImportSource.CORPUS,
        case_method=ImportMethod.DIRECT,
    )
    _patch_parse_environment(
        monkeypatch,
        async_session,
        cover_meta={"case_name": "Extracted PDF Cover Name"},
        llm_mode="rule_based",
    )

    try:
        await run_parse(argparse.Namespace(run_id=source_run.id, dry_run=False, job_id=None))
        await async_session.refresh(case)
        assert case.case_name == "Corpus-Authored Case Name", (
            "a disagreeing PDF cover extraction must not clobber a "
            "corpus-stamped case name"
        )

        discrepancies = (
            await async_session.execute(
                select(ValueDiscrepancy).where(
                    ValueDiscrepancy.target_type == "case",
                    ValueDiscrepancy.target_id == case.id,
                    ValueDiscrepancy.field == "case_name",
                )
            )
        ).scalars().all()
        assert len(discrepancies) == 1
    finally:
        try:
            os.unlink(pdf_path)
        except OSError:
            pass


@pytest.mark.asyncio
async def test_seeded_participant_carries_pdf_pipeline_source_and_method(
    async_session, monkeypatch
):
    """
    A newly seeded ArgumentParticipant carries source=pdf_pipeline and the
    run's method (PD-20) — a seeded participant with NULL provenance
    floors the whole argument to UNCERTAIN through derive_tier.
    """
    from sqlalchemy import select

    from api.models.models import ArgumentParticipant, ImportMethod, ImportSource

    argument, case, source_run, pdf_path = await _seed_parse_gate_fixture(async_session)
    _patch_parse_environment(
        monkeypatch, async_session, cover_meta={}, llm_mode="rule_based"
    )

    try:
        await run_parse(argparse.Namespace(run_id=source_run.id, dry_run=False, job_id=None))

        participants = (
            await async_session.execute(
                select(ArgumentParticipant).where(
                    ArgumentParticipant.argument_id == argument.id
                )
            )
        ).scalars().all()
        assert len(participants) >= 1
        for p in participants:
            assert p.source == ImportSource.PDF_PIPELINE
            assert p.method == ImportMethod.RULE_BASED
    finally:
        try:
            os.unlink(pdf_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Test 3: Stage direction classification with parenthetical content (PIPE-05)
# ---------------------------------------------------------------------------


def test_stage_direction_classification():
    """
    Various stage direction formats should be classified correctly.
    Lines in the form "(text)" are stage directions; speaker turns are not.
    """
    from pipeline.parser.state_machine import parse_transcript

    page = make_page(
        "(10:02 a.m.)",
        "CHIEF JUSTICE ROBERTS: We will hear argument.",
        "(Whereupon, at 10:03 a.m., the argument was concluded.)",
    )
    utterances = parse_transcript([page])

    stage_dirs = [u for u in utterances if u["is_stage_direction"]]
    speech_turns = [u for u in utterances if not u["is_stage_direction"]]

    # Both parenthetical lines should be stage directions
    assert len(stage_dirs) >= 1, f"Expected at least 1 stage direction, got {len(stage_dirs)}"

    # Speech turn should not be a stage direction
    assert len(speech_turns) >= 1
    for turn in speech_turns:
        assert turn["is_stage_direction"] is False
        assert turn["raw_speaker_label"] is not None


# ---------------------------------------------------------------------------
# Test 4: LLM failure mode classification (PIPE-06 / 1-llm-failures)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_failure_modes(monkeypatch):
    """
    Structural failures (InstructorRetryException) must propagate from
    call_llm_parse (not be swallowed). Transient failures (RateLimitError)
    must be retried by the outer tenacity wrapper.
    """
    import anthropic

    # Test 1: InstructorRetryException propagates from parse_with_llm
    try:
        import instructor
        has_instructor = True
    except ImportError:
        has_instructor = False

    if has_instructor:
        # Monkeypatch call_llm_parse to raise InstructorRetryException
        from pipeline.parser import llm_pass

        class FakeInstructorRetryException(Exception):
            pass

        # Replace call_llm_parse to raise a structural failure
        async def mock_call_structural(pages_text):
            try:
                raise instructor.exceptions.InstructorRetryException(
                    "Schema mismatch after 2 retries",
                    n_attempts=2,
                    last_completion=None,
                    messages=[],
                )
            except AttributeError:
                # instructor version without that exact constructor
                raise Exception("Structural LLM failure")

        monkeypatch.setattr(llm_pass, "call_llm_parse", mock_call_structural)

        # parse_with_llm should propagate structural failures (not retry them)
        # Note: tenacity only retries RateLimitError and APIConnectionError,
        # not InstructorRetryException — so it should raise after 1 attempt.
        with pytest.raises(Exception):
            await llm_pass.parse_with_llm("test transcript")

    # Test 2: RateLimitError is retried (check via tenacity statistics)
    from pipeline.parser import llm_pass as lp

    call_count = {"n": 0}

    # anthropic.RateLimitError.__init__ dereferences response.request unconditionally
    # (current anthropic SDK) — a bare response=None (as older SDKs tolerated)
    # now raises AttributeError before the test's own assertion is ever reached.
    # Build a real httpx.Response bound to a request so construction succeeds.
    import httpx

    def _make_rate_limit_error() -> "anthropic.RateLimitError":
        fake_request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        fake_response = httpx.Response(429, request=fake_request, headers={"request-id": "test-request-id"})
        return anthropic.RateLimitError(
            "Rate limited",
            response=fake_response,
            body={"error": {"type": "rate_limit_error"}},
        )

    async def mock_call_rate_limited(pages_text):
        call_count["n"] += 1
        raise _make_rate_limit_error()

    monkeypatch.setattr(lp, "call_llm_parse", mock_call_rate_limited)

    with pytest.raises(anthropic.RateLimitError):
        await lp.parse_with_llm("test transcript")

    # tenacity should have retried — at least 2 attempts (stop_after_attempt=5)
    assert call_count["n"] > 1, (
        f"Expected tenacity to retry RateLimitError (got {call_count['n']} attempts)"
    )


# ---------------------------------------------------------------------------
# Test 5: Section hint must NOT cascade (Pitfall 3 / cascade fix)
# ---------------------------------------------------------------------------


def test_section_hint_not_cascade():
    """
    After a TOC section marker, only the FIRST utterance in the new section
    should carry the section_hint. All subsequent utterances must have
    section_hint=None.

    This tests the two-variable design (pending_section_hint / current_section_hint).
    """
    from pipeline.parser.state_machine import parse_transcript

    page = make_page(
        "ORAL ARGUMENT OF MR. OLSON ON BEHALF OF PETITIONERS",
        "MR. OLSON: Thank you, Mr. Chief Justice.",
        "CHIEF JUSTICE ROBERTS: Proceed.",
        "MR. OLSON: The question before this Court is fundamental.",
        "CHIEF JUSTICE ROBERTS: I understand.",
    )
    utterances = parse_transcript([page])

    # Get the utterances with a section_hint
    hints = [u for u in utterances if u["section_hint"] is not None]

    assert len(hints) == 1, (
        f"Expected exactly 1 utterance with section_hint, got {len(hints)}: "
        f"{[(u['sequence'], u['raw_speaker_label'], u['section_hint']) for u in hints]}"
    )

    # The hint should be on MR. OLSON's first utterance
    first_hint_utt = hints[0]
    assert first_hint_utt["raw_speaker_label"] == "MR. OLSON"
    assert first_hint_utt["section_hint"] == "petitioner"

    # All subsequent utterances must have section_hint=None
    for u in utterances:
        if u["sequence"] > first_hint_utt["sequence"]:
            assert u["section_hint"] is None, (
                f"Utterance #{u['sequence']} ({u['raw_speaker_label']!r}) "
                f"should have section_hint=None but got {u['section_hint']!r}"
            )


# ---------------------------------------------------------------------------
# Test 6: "ON BEHALF OF" not appended to prior speaker (F04 regression)
# ---------------------------------------------------------------------------


def test_on_behalf_of_not_appended_to_prior_speaker():
    """
    F04 regression: "ON BEHALF OF PETITIONERS ON QUESTION 1" is a TOC section
    header, not a speaker or continuation line. It must NOT be appended to the
    prior speaker's utterance text.

    This tests the F04 fix: ON\\s+BEHALF\\s+OF in TOC_SECTION_RE.
    """
    from pipeline.parser.state_machine import parse_transcript

    page = make_page(
        "CHIEF JUSTICE ROBERTS: We'll hear argument now.",
        "ON BEHALF OF PETITIONERS ON QUESTION 1",
        "MR. OLSON: Mr. Chief Justice, and may it please the Court.",
    )
    utterances = parse_transcript([page])

    # No utterance's text should contain "ON BEHALF OF PETITIONERS"
    for u in utterances:
        assert "ON BEHALF OF PETITIONERS" not in u["text"], (
            f"Utterance #{u['sequence']} ({u['raw_speaker_label']!r}) "
            f"contains 'ON BEHALF OF PETITIONERS' in text — F04 fix failed. "
            f"Text: {u['text']!r}"
        )

    # We should have exactly 2 speech utterances (Roberts + Olson)
    speech_turns = [u for u in utterances if not u["is_stage_direction"]]
    assert len(speech_turns) == 2, (
        f"Expected 2 speech turns (Roberts + Olson), got {len(speech_turns)}: "
        f"{[(u['sequence'], u['raw_speaker_label']) for u in speech_turns]}"
    )

    # Roberts' utterance should only contain his speech
    roberts_utt = next(
        u for u in speech_turns if u["raw_speaker_label"] == "CHIEF JUSTICE ROBERTS"
    )
    assert roberts_utt["text"] == "We'll hear argument now.", (
        f"Roberts' utterance text is wrong: {roberts_utt['text']!r}"
    )
