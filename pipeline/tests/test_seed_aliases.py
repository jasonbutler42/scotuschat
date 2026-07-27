"""
Integration tests for the pipeline seed-aliases command.

Covers: PIPE-08 (pre-seeded speaker_alias table for Justice labels;
        idempotent re-run does not duplicate rows)

DB-dependent tests are skipped when DATABASE_URL is not set.

Phase 38 (D-03/D-04, no-DB-required): _JUSTICES_SHARED_FIXTURE_REGRESSION
ties every seed_aliases.py justice's derived full_name back to
pipeline/tests/test_import_justices_csv.py's _SEEDED_JUSTICE_CASES fixture
corpus — the same 13 (first, middle, last, suffix, expected full_name)
tuples the CSV importer's own byte-for-byte regression already verifies.
"""

import os

import pytest

from api.domain.person_names import prepare_person_name
from pipeline.commands.seed_aliases import _JUSTICES
from pipeline.tests.test_import_justices_csv import _SEEDED_JUSTICE_CASES

# ---------------------------------------------------------------------------
# requires_db marker — skip DB-dependent tests when DATABASE_URL not set
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "")
requires_db = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL not set — skipping database connectivity tests",
)


# ---------------------------------------------------------------------------
# Phase 38 (D-03/D-04): shared fixture corpus regression — no DB required
# ---------------------------------------------------------------------------


def test_seed_justices_have_no_independent_formatter():
    """
    seed_aliases.py's _JUSTICES no longer authors a hand-typed full_name
    literal at all — only structured parts. Deriving full_name for every
    entry through the one shared api.domain.person_names.prepare_person_name
    helper must reproduce the exact same 13 literals
    test_import_justices_csv.py's _SEEDED_JUSTICE_CASES fixture corpus
    already establishes and verifies for the CSV importer, in the same
    order (both lists are authored Roberts-through-Breyer).
    """
    assert len(_JUSTICES) == len(_SEEDED_JUSTICE_CASES) == 13

    for (first, middle, last, suffix, _role_name, _labels), (
        exp_first,
        exp_middle,
        exp_last,
        exp_suffix,
        expected_full_name,
    ) in zip(_JUSTICES, _SEEDED_JUSTICE_CASES):
        assert (first, middle, last, suffix) == (
            exp_first,
            exp_middle,
            exp_last,
            exp_suffix,
        )
        prepared = prepare_person_name(
            first or None, middle or None, last or None, suffix or None
        )
        assert prepared.full_name == expected_full_name


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
