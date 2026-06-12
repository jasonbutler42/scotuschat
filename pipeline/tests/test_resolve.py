"""
Unit and integration tests for the pipeline resolve command.

Covers: PIPE-07 (resolve step — alias lookup + interactive prompt)
        PIPE-09 (interrupt → needs_review; resume skips already-resolved labels)

DB-dependent tests are skipped when DATABASE_URL is not set.
"""

import os

import pytest

# ---------------------------------------------------------------------------
# requires_db marker — skip DB-dependent tests when DATABASE_URL not set
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "")
requires_db = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set — skipping database connectivity tests",
)


# ---------------------------------------------------------------------------
# test_normalize_label — unit test (no DB required)
# ---------------------------------------------------------------------------


def test_normalize_label():
    """normalize_label strips whitespace, trailing colon, and uppercases.

    Implements D-02: examples from CONTEXT.md.
    """
    from pipeline.commands.resolve import normalize_label

    assert normalize_label("Justice Kagan:") == "JUSTICE KAGAN"
    assert normalize_label("  CHIEF JUSTICE:  ") == "CHIEF JUSTICE"
    assert normalize_label("MR. JONES") == "MR. JONES"


# ---------------------------------------------------------------------------
# test_resolve_alias_hit — integration test (requires DB)
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.asyncio
async def test_resolve_alias_hit(async_session):
    """
    When a SpeakerAlias row exists for a label, run_resolve() sets
    utterances.person_id on all matching utterance rows automatically.
    """
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# test_resolve_interactive_prompt — unit test with mocked input()
# ---------------------------------------------------------------------------


def test_resolve_interactive_prompt():
    """
    When no SpeakerAlias row exists, run_resolve() displays a numbered
    list of existing people and prompts the operator via input().
    """
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# test_resolve_interrupt_sets_needs_review — unit test with mocked KeyboardInterrupt
# ---------------------------------------------------------------------------


def test_resolve_interrupt_sets_needs_review():
    """
    When a KeyboardInterrupt is raised during the resolve loop, the resolve
    PipelineRun's status is set to NEEDS_REVIEW and session.flush() is called.

    This is a unit test using a mocked session — no live DB required.
    """
    import argparse
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, patch
    from contextlib import asynccontextmanager

    from api.models.models import PipelineRun, PipelineRunStatus

    # Build a fake parse_run that looks like a completed parse step
    fake_parse_run = MagicMock(spec=PipelineRun)
    fake_parse_run.id = 1
    fake_parse_run.argument_id = 10
    fake_parse_run.step = "parse"
    fake_parse_run.status = PipelineRunStatus.COMPLETED

    # Build a fake resolve_run that will be created by run_resolve
    fake_resolve_run = MagicMock(spec=PipelineRun)
    fake_resolve_run.id = 2

    # Session mock: get() returns parse_run; flush is async no-op
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=fake_parse_run)
    mock_session.flush = AsyncMock()
    mock_session.add = MagicMock()

    # The labels query raises KeyboardInterrupt to simulate Ctrl+C
    mock_session.execute = AsyncMock(side_effect=KeyboardInterrupt)

    # Patch session.add so that the second "add" (resolve_run) captures the object
    added_objects = []
    mock_session.add.side_effect = lambda obj: added_objects.append(obj)

    # Override flush to assign id to the resolve_run on the FIRST flush only
    flush_call_count = {"n": 0}

    async def fake_flush():
        flush_call_count["n"] += 1
        if flush_call_count["n"] == 1:
            # First flush: assign the resolve_run's id (simulates DB auto-increment)
            for obj in added_objects:
                if isinstance(obj, PipelineRun):
                    obj.id = 2
        # Subsequent flushes (e.g., from the except block) are no-ops
        # so that status mutations set by run_resolve() are preserved.

    mock_session.flush.side_effect = fake_flush

    @asynccontextmanager
    async def fake_get_session():
        yield mock_session

    args = argparse.Namespace(run_id=1)

    with patch("pipeline.commands.resolve.get_session", new=fake_get_session):
        asyncio.run(_run_resolve_catching_interrupt(args))

    # After KeyboardInterrupt, the resolve_run's status must be NEEDS_REVIEW
    resolve_runs = [obj for obj in added_objects if isinstance(obj, PipelineRun)]
    assert len(resolve_runs) == 1, (
        f"Expected exactly 1 PipelineRun added, got {len(resolve_runs)}"
    )
    assert resolve_runs[0].status == PipelineRunStatus.NEEDS_REVIEW, (
        f"Expected NEEDS_REVIEW, got {resolve_runs[0].status}"
    )


async def _run_resolve_catching_interrupt(args):
    """Helper: run run_resolve and handle KeyboardInterrupt at the asyncio level."""
    from pipeline.commands.resolve import run_resolve

    try:
        await run_resolve(args)
    except KeyboardInterrupt:
        pass  # outer guard in __main__.py handles this; inner guard sets NEEDS_REVIEW


# ---------------------------------------------------------------------------
# test_resolve_resumes_after_interrupt — integration test (requires DB)
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.asyncio
async def test_resolve_resumes_after_interrupt(async_session):
    """
    Re-running resolve after a prior interrupted run skips labels that
    already have person_id populated and only prompts for unresolved labels.
    """
    pytest.fail("not implemented")
