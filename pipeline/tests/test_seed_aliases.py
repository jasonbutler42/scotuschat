"""
Integration tests for the pipeline seed-aliases command.

Covers: PIPE-08 (pre-seeded speaker_alias table for Justice labels;
        idempotent re-run does not duplicate rows)

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
# test_seed_creates_justices — integration test (requires DB)
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.asyncio
@pytest.mark.xfail(
    reason=(
        "Never implemented — pre-existing pytest.fail('not implemented') stub, "
        "not schema drift. Out of scope for TEST-02 fixture repair; see "
        "31-06-SUMMARY.md / deferred-items.md."
    ),
    strict=True,
)
async def test_seed_creates_justices(async_session):
    """
    After run_seed_aliases() completes, the database must contain:
    - 4 role rows (Chief Justice, Associate Justice, Petitioner's Counsel, Respondent's Counsel)
    - 13 people rows (all seeded Justices)
    - alias rows including "CHIEF JUSTICE", "CHIEF JUSTICE ROBERTS", "JUSTICE KAGAN"
    """
    pytest.fail("not implemented")


# ---------------------------------------------------------------------------
# test_seed_idempotent — integration test (requires DB)
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.asyncio
@pytest.mark.xfail(
    reason=(
        "Never implemented — pre-existing pytest.fail('not implemented') stub, "
        "not schema drift. Out of scope for TEST-02 fixture repair; see "
        "31-06-SUMMARY.md / deferred-items.md."
    ),
    strict=True,
)
async def test_seed_idempotent(async_session):
    """
    Running run_seed_aliases() twice must produce identical row counts.
    No duplicate roles, people, or alias rows may be created on re-run.
    """
    pytest.fail("not implemented")
