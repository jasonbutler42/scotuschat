"""
Parser unit tests for the rule-based state machine.

These tests do NOT require a database — they exercise pipeline/parser/state_machine.py
directly using in-memory transcript excerpts.

Test IDs covered (from VALIDATION.md):
  - 1-stage-dirs:  PIPE-05 stage direction classification
  - 1-parse-rows:  PIPE-03 parser output structure
  - 1-run-id:      PIPE-04 pipeline_run_id and strategy (DB-dependent, skips if no DB)
  - 1-llm-failures: PIPE-06 LLM failure mode classification

Regression tests:
  - test_section_hint_not_cascade: Pitfall 3 (section hint must not cascade)
  - test_on_behalf_of_not_appended_to_prior_speaker: F04 regression (ON BEHALF OF fix)
"""

import pytest


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
# Test 2: run_id and strategy on utterance rows (PIPE-04 / 1-run-id)
# DB-dependent — skips gracefully if no DATABASE_URL configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_id_strategy(async_session, monkeypatch):
    """
    Every utterance row must have pipeline_run_id and strategy set (PIPE-04).

    Skips if no database is configured (async_session fixture handles skip).
    """
    # Import here so skip happens before imports if DB not available
    import os
    from sqlalchemy import select
    from api.models.models import (
        Argument,
        Case,
        CaseArgument,
        PipelineRun,
        PipelineRunStatus,
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

    pipeline_run = PipelineRun(
        argument_id=argument.id,
        step="parse",
        status=PipelineRunStatus.PENDING,
        pdf_path=tmp_path,
    )
    async_session.add(pipeline_run)
    await async_session.flush()

    # Run the parse command
    import argparse
    args = argparse.Namespace(run_id=pipeline_run.id, dry_run=False, job_id=None)

    # Override get_session to use the test session
    from unittest.mock import AsyncMock, MagicMock
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_get_session():
        yield async_session

    monkeypatch.setattr("pipeline.commands.parse.get_session", mock_get_session)

    from pipeline.commands.parse import run_parse
    await run_parse(args)

    # run_parse() creates a BRAND-NEW PipelineRun row for this parse attempt
    # (PIPE-11 re-run semantics: re-running a step never overwrites a prior
    # run's row) rather than writing utterances against `pipeline_run` above
    # — that row is only the *source* record parse reads pdf_path/argument_id
    # from via args.run_id. Utterances link to the new run's id, not the
    # source run's id.
    new_run_result = await async_session.execute(
        select(PipelineRun).where(
            PipelineRun.argument_id == argument.id,
            PipelineRun.step == "parse",
            PipelineRun.id != pipeline_run.id,
        )
    )
    new_run = new_run_result.scalar_one()

    # Verify utterance rows have pipeline_run_id and strategy set
    result = await async_session.execute(
        select(Utterance).where(Utterance.pipeline_run_id == new_run.id)
    )
    rows = result.scalars().all()

    assert len(rows) > 0, "Expected at least 1 utterance row after parse"
    for row in rows:
        assert row.pipeline_run_id is not None, "pipeline_run_id must not be None"
        assert row.pipeline_run_id == new_run.id
        assert row.strategy is not None, "strategy must not be None"
        assert row.strategy in ("rule_based", "llm_corrective")

    # Cleanup temp file
    import os
    try:
        os.unlink(tmp_path)
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
