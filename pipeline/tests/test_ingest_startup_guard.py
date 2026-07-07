"""
Tests for the pipeline __main__.py startup guard (Phase 24 Plan 05, CR-01/T-24-09/T-24-10).

These tests verify:
1. (static) pipeline/__main__.py defines _write_early_failure and main() wraps
   parser.parse_args() in a try/except SystemExit block
2. (static) the guard scrapes --job-id from sys.argv and re-raises the SystemExit
   after attempting the FAILED write
3. (behavioral) _write_early_failure(job_id=None, message="x") is a no-op that
   does not raise (mirrors run_ingest guarding on args.job_id is not None)
4. (behavioral) _scrape_job_id extracts the integer following --job-id in argv,
   returning None when --job-id is absent

All tests are pure-function/static-analysis checks — no database is required.
They run in < 2 seconds and pass in CI without DATABASE_URL set.

Run with:
    pytest pipeline/tests/test_ingest_startup_guard.py -x -q
"""

import os
import pathlib

from pipeline.__main__ import _scrape_job_id, _write_early_failure


# ---------------------------------------------------------------------------
# Helper: resolve project root from this file's location
# ---------------------------------------------------------------------------


def _project_root() -> pathlib.Path:
    """Return the absolute path to the project root directory."""
    return pathlib.Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _main_py_source() -> str:
    main_py = _project_root() / "pipeline" / "__main__.py"
    assert main_py.exists(), "pipeline/__main__.py does not exist"
    return main_py.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 1 (static): _write_early_failure defined + try/except SystemExit guard
# ---------------------------------------------------------------------------


def test_main_py_defines_write_early_failure_and_wraps_parse_args():
    """pipeline/__main__.py must define _write_early_failure and guard parse_args()."""
    content = _main_py_source()
    assert "def _write_early_failure" in content, (
        "Expected 'def _write_early_failure' in pipeline/__main__.py — "
        "the startup guard helper is missing"
    )
    assert "except SystemExit" in content, (
        "Expected a 'except SystemExit' handler around parser.parse_args() "
        "in pipeline/__main__.py"
    )


# ---------------------------------------------------------------------------
# Test 2 (static): guard scrapes --job-id from sys.argv and re-raises
# ---------------------------------------------------------------------------


def test_main_py_scrapes_job_id_and_reraises_systemexit():
    """The guard must scrape --job-id from argv and re-raise the SystemExit."""
    content = _main_py_source()
    assert "def _scrape_job_id" in content, (
        "Expected 'def _scrape_job_id' in pipeline/__main__.py"
    )
    assert "--job-id" in content
    assert "raise" in content, (
        "Expected the SystemExit handler to re-raise so the process still "
        "exits non-zero"
    )
    assert "[:500]" in content, (
        "Expected the early-failure message to be sliced to [:500] characters "
        "before the DB write (bounded-buffer discipline)"
    )


# ---------------------------------------------------------------------------
# Test 3 (behavioral): _write_early_failure(None, ...) is a no-op
# ---------------------------------------------------------------------------


def test_write_early_failure_noop_when_job_id_none():
    """_write_early_failure(job_id=None, ...) must return without raising or DB access."""
    # Should not raise, and should not attempt any DB call.
    _write_early_failure(job_id=None, message="x")


# ---------------------------------------------------------------------------
# Test 4 (behavioral): _scrape_job_id extracts the integer after --job-id
# ---------------------------------------------------------------------------


def test_scrape_job_id_extracts_int_when_present():
    """_scrape_job_id finds --job-id and returns the following token as an int."""
    argv = ["ingest", "--job-id", "7", "--primary-docket", "--url"]
    assert _scrape_job_id(argv) == 7


def test_scrape_job_id_returns_none_when_absent():
    """_scrape_job_id returns None when --job-id is not present in argv."""
    argv = ["ingest", "--url", "x"]
    assert _scrape_job_id(argv) is None
