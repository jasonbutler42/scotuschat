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

import pytest

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
