"""
Phase 50 plan 50-07, Task 1: the offline `prune-runs` command (D-12).

Covers every `<behavior>` bullet:
    - a single-parse-run argument removes nothing (the only run is served)
    - a three-parse-run argument removes the two older runs and their
      utterances, leaving the newest run and its rows intact
    - get_argument_with_utterances returns exactly the same rows before
      and after a prune
    - a run carrying an OPEN value_discrepancy row is refused under every
      flag combination
    - a run carrying only RESOLVED value_discrepancy rows is refused by
      default and removed under --include-resolved-discrepancies
    - a step="reconcile" run with no attached discrepancy rows is prunable
    - --dry-run prints the same report and removes nothing
    - --all iterates every argument and reports whole-batch totals
    - utterances are deleted before their run (no ForeignKeyViolation)
    - an argument with zero runs is a no-op, not an error

Follows `test_import_convokit_reimport_tracer.py`'s `isolated_session` +
`_make_session_cm` convention: `run_prune_runs` opens one `get_session()`
per argument internally (mirroring recompute-trust's own per-argument
session boundary), so the module's `get_session` is patched to reuse ONE
shared, uncommitted session across every call within a test -- visible to
both the test's own seeding/assertions and every internal call
`run_prune_runs` makes, and rolled back automatically at teardown (never a
TRUNCATE, never a commit against the shared test DB).

DB-dependent tests are skipped when DATABASE_URL/TEST_DATABASE_URL is not
set (via conftest.py's test_db_url fixture -> pytest.skip).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import func, select

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
    ValueDiscrepancy,
)
from api.services.arguments import get_argument_with_utterances
from pipeline.commands.prune_runs import _prunable_run_ids, run_prune_runs

# pytest.ini configures asyncio_mode=auto -- async def test_* functions are
# detected and run automatically, no per-test @pytest.mark.asyncio needed.

_COUNTER = 0


def _unique_docket() -> str:
    global _COUNTER
    _COUNTER += 1
    return f"57-{9000 + _COUNTER}"


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


# ===========================================================================
# Seeding helpers
# ===========================================================================


async def _seed_argument(
    session,
    *,
    docket: str | None = None,
    status: ArgumentStatusEnum = ArgumentStatusEnum.CANDIDATE,
    published: bool = False,
) -> Argument:
    docket = docket or _unique_docket()
    argument = Argument(
        source_docket=docket,
        question_number=1,
        oyez_transcript_id=f"conv_{docket}",
        status=status,
        published_at=datetime.now(timezone.utc) if published else None,
        source=ImportSource.CORPUS,
        method=ImportMethod.DIRECT,
    )
    session.add(argument)
    await session.flush()
    return argument


async def _seed_lead_case(session, argument: Argument, *, docket: str) -> Case:
    case = Case(
        docket_number=docket,
        docket_number_norm=docket.replace("-", ""),
        case_name="Pet v. Resp",
        term_year=1955,
        slug=f"slug-{docket}".lower(),
        source=ImportSource.CORPUS,
        method=ImportMethod.DIRECT,
    )
    session.add(case)
    await session.flush()
    session.add(CaseArgument(case_id=case.id, argument_id=argument.id, is_lead=True))
    await session.flush()
    return case


async def _seed_run(
    session,
    argument: Argument,
    *,
    step: str,
    status: ImportRunStatus = ImportRunStatus.COMPLETED,
) -> ImportRun:
    run = ImportRun(
        argument_id=argument.id,
        step=step,
        status=status,
        source=ImportSource.CORPUS,
        method=ImportMethod.DIRECT,
    )
    session.add(run)
    await session.flush()
    return run


async def _seed_utterance(
    session, argument: Argument, run: ImportRun, sequence: int
) -> Utterance:
    utterance = Utterance(
        argument_id=argument.id,
        import_run_id=run.id,
        sequence=sequence,
        text=f"utterance {sequence} of run {run.id}",
        is_stage_direction=False,
    )
    session.add(utterance)
    await session.flush()
    return utterance


async def _seed_discrepancy(
    session,
    *,
    run: ImportRun,
    target_type: str = "argument",
    target_id: int,
    field: str = "argued_date",
    resolved: bool,
) -> ValueDiscrepancy:
    discrepancy = ValueDiscrepancy(
        target_type=target_type,
        target_id=target_id,
        field=field,
        import_run_id=run.id,
        incoming_value="incoming",
        existing_value="existing",
        resolved_at=datetime.now(timezone.utc) if resolved else None,
    )
    session.add(discrepancy)
    await session.flush()
    return discrepancy


async def _run_prune(isolated_session, args) -> None:
    with patch(
        "pipeline.commands.prune_runs.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_prune_runs(args)


def _single_args(
    argument_id: int, *, dry_run: bool = False, include_resolved: bool = False
) -> argparse.Namespace:
    return argparse.Namespace(
        all=False,
        argument_id=argument_id,
        dry_run=dry_run,
        include_resolved_discrepancies=include_resolved,
    )


def _all_args(*, dry_run: bool = False, include_resolved: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        all=True,
        argument_id=None,
        dry_run=dry_run,
        include_resolved_discrepancies=include_resolved,
    )


async def _run_ids(session, argument_id: int) -> set[int]:
    result = await session.execute(
        select(ImportRun.id).where(ImportRun.argument_id == argument_id)
    )
    return set(result.scalars().all())


async def _utterance_count(session, run_id: int) -> int:
    result = await session.execute(
        select(func.count(Utterance.id)).where(Utterance.import_run_id == run_id)
    )
    return result.scalar_one()


# ===========================================================================
# Behavior tests
# ===========================================================================


async def test_single_parse_run_removes_nothing(isolated_session):
    """--argument-id on an argument with one parse run removes nothing --
    the only run is the served one."""
    argument = await _seed_argument(isolated_session)
    run = await _seed_run(isolated_session, argument, step="parse")
    await _seed_utterance(isolated_session, argument, run, 1)

    await _run_prune(isolated_session, _single_args(argument.id))

    assert await _run_ids(isolated_session, argument.id) == {run.id}
    assert await _utterance_count(isolated_session, run.id) == 1


async def test_three_parse_runs_removes_two_older_keeps_newest(isolated_session):
    """Three parse runs -> the two older runs and their utterances are
    removed; the newest run and its rows survive untouched."""
    argument = await _seed_argument(isolated_session)
    run1 = await _seed_run(isolated_session, argument, step="parse")
    await _seed_utterance(isolated_session, argument, run1, 1)
    run2 = await _seed_run(isolated_session, argument, step="parse")
    await _seed_utterance(isolated_session, argument, run2, 1)
    run3 = await _seed_run(isolated_session, argument, step="parse")
    await _seed_utterance(isolated_session, argument, run3, 1)
    await _seed_utterance(isolated_session, argument, run3, 2)

    await _run_prune(isolated_session, _single_args(argument.id))

    assert await _run_ids(isolated_session, argument.id) == {run3.id}
    assert await _utterance_count(isolated_session, run3.id) == 2


async def test_get_argument_with_utterances_unchanged_after_prune(isolated_session):
    """After a prune, get_argument_with_utterances returns exactly the
    same rows it returned before."""
    docket = _unique_docket()
    argument = await _seed_argument(
        isolated_session, docket=docket, status=ArgumentStatusEnum.PUBLISHED, published=True
    )
    await _seed_lead_case(isolated_session, argument, docket=docket)
    run1 = await _seed_run(isolated_session, argument, step="parse")
    await _seed_utterance(isolated_session, argument, run1, 1)
    run2 = await _seed_run(isolated_session, argument, step="parse")
    await _seed_utterance(isolated_session, argument, run2, 1)
    await _seed_utterance(isolated_session, argument, run2, 2)

    before = await get_argument_with_utterances(isolated_session, argument.id)
    assert before is not None

    await _run_prune(isolated_session, _single_args(argument.id))

    after = await get_argument_with_utterances(isolated_session, argument.id)
    assert after == before
    assert len(after["utterances"]) == 2


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("include_resolved", [False, True])
async def test_open_discrepancy_blocks_run_under_every_flag_combination(
    isolated_session, dry_run, include_resolved
):
    """A run carrying an OPEN value_discrepancy row is refused no matter
    which flags are set -- no flag deletes an open row."""
    argument = await _seed_argument(isolated_session)
    # old_run must be created FIRST (lower id) -- the served run is
    # whichever step="parse"/COMPLETED run has the HIGHEST id (PD-22's
    # MAX(ImportRun.id) select), so the run intended as "served" for this
    # test must be created second.
    old_run = await _seed_run(isolated_session, argument, step="parse")
    await _seed_utterance(isolated_session, argument, old_run, 1)
    await _seed_discrepancy(
        isolated_session, run=old_run, target_id=argument.id, resolved=False
    )
    served = await _seed_run(isolated_session, argument, step="parse")

    await _run_prune(
        isolated_session,
        _single_args(argument.id, dry_run=dry_run, include_resolved=include_resolved),
    )

    assert await _run_ids(isolated_session, argument.id) == {served.id, old_run.id}
    assert await _utterance_count(isolated_session, old_run.id) == 1
    open_count = (
        await isolated_session.execute(
            select(func.count(ValueDiscrepancy.id)).where(
                ValueDiscrepancy.import_run_id == old_run.id,
                ValueDiscrepancy.resolved_at.is_(None),
            )
        )
    ).scalar_one()
    assert open_count == 1


async def test_resolved_discrepancy_blocked_by_default_removed_with_flag(isolated_session):
    """A run carrying only RESOLVED discrepancy rows is refused by default
    and removed (deleting those resolved rows first) under
    --include-resolved-discrepancies."""
    argument = await _seed_argument(isolated_session)
    # old_run created first (lower id) so it is not the served run.
    old_run = await _seed_run(isolated_session, argument, step="parse")
    await _seed_utterance(isolated_session, argument, old_run, 1)
    discrepancy = await _seed_discrepancy(
        isolated_session, run=old_run, target_id=argument.id, resolved=True
    )
    await _seed_run(isolated_session, argument, step="parse")  # served run

    # Default: refused, nothing removed.
    await _run_prune(isolated_session, _single_args(argument.id))
    assert old_run.id in await _run_ids(isolated_session, argument.id)

    # With the opt-in flag: the resolved discrepancy row, the utterance
    # row, and the run itself are all removed.
    await _run_prune(
        isolated_session, _single_args(argument.id, include_resolved=True)
    )
    assert old_run.id not in await _run_ids(isolated_session, argument.id)
    assert await _utterance_count(isolated_session, old_run.id) == 0
    remaining_discrepancy = (
        await isolated_session.execute(
            select(ValueDiscrepancy.id).where(ValueDiscrepancy.id == discrepancy.id)
        )
    ).scalar_one_or_none()
    assert remaining_discrepancy is None


async def test_reconcile_run_with_no_discrepancies_is_prunable(isolated_session):
    """A step="reconcile" run with no attached discrepancy rows is
    prunable."""
    argument = await _seed_argument(isolated_session)
    served = await _seed_run(isolated_session, argument, step="parse")
    reconcile_run = await _seed_run(isolated_session, argument, step="reconcile")

    await _run_prune(isolated_session, _single_args(argument.id))

    assert await _run_ids(isolated_session, argument.id) == {served.id}
    assert reconcile_run.id not in await _run_ids(isolated_session, argument.id)


async def test_dry_run_leaves_row_counts_identical(isolated_session):
    """--dry-run prints the same report and removes nothing."""
    argument = await _seed_argument(isolated_session)
    run1 = await _seed_run(isolated_session, argument, step="parse")
    await _seed_utterance(isolated_session, argument, run1, 1)
    run2 = await _seed_run(isolated_session, argument, step="parse")
    await _seed_utterance(isolated_session, argument, run2, 1)

    await _run_prune(isolated_session, _single_args(argument.id, dry_run=True))

    assert await _run_ids(isolated_session, argument.id) == {run1.id, run2.id}
    assert await _utterance_count(isolated_session, run1.id) == 1
    assert await _utterance_count(isolated_session, run2.id) == 1


async def test_dry_run_reports_same_totals_as_a_real_run(isolated_session, capsys):
    """A --dry-run report and a real run over the identical fixture print
    the same removal totals."""
    argument = await _seed_argument(isolated_session)
    run1 = await _seed_run(isolated_session, argument, step="parse")
    await _seed_utterance(isolated_session, argument, run1, 1)
    await _seed_run(isolated_session, argument, step="parse")  # served run

    await _run_prune(isolated_session, _single_args(argument.id, dry_run=True))
    dry_out = capsys.readouterr().out
    assert "1 runs removed" in dry_out
    assert "1 utterance rows removed" in dry_out

    await _run_prune(isolated_session, _single_args(argument.id))
    real_out = capsys.readouterr().out
    assert "1 runs removed" in real_out
    assert "1 utterance rows removed" in real_out


async def test_all_iterates_every_argument_and_reports_batch_totals(isolated_session, capsys):
    """--all iterates every argument and reports whole-batch totals."""
    arg1 = await _seed_argument(isolated_session)
    old1 = await _seed_run(isolated_session, arg1, step="parse")
    await _seed_utterance(isolated_session, arg1, old1, 1)
    await _seed_run(isolated_session, arg1, step="parse")  # served (higher id)

    arg2 = await _seed_argument(isolated_session)
    old2 = await _seed_run(isolated_session, arg2, step="parse")
    await _seed_utterance(isolated_session, arg2, old2, 1)
    await _seed_utterance(isolated_session, arg2, old2, 2)
    await _seed_run(isolated_session, arg2, step="parse")  # served (higher id)

    await _run_prune(isolated_session, _all_args())
    out = capsys.readouterr().out

    assert "2 runs removed" in out
    assert "3 utterance rows removed" in out
    assert old1.id not in await _run_ids(isolated_session, arg1.id)
    assert old2.id not in await _run_ids(isolated_session, arg2.id)


async def test_utterances_deleted_before_runs_no_fk_violation(isolated_session):
    """Deleting a prunable run's utterances before the run itself never
    raises a ForeignKeyViolation."""
    argument = await _seed_argument(isolated_session)
    old_run = await _seed_run(isolated_session, argument, step="parse")
    for seq in range(1, 6):
        await _seed_utterance(isolated_session, argument, old_run, seq)
    await _seed_run(isolated_session, argument, step="parse")  # served (higher id)

    # No try/except on purpose -- an uncaught ForeignKeyViolation (wrapped
    # in IntegrityError) is exactly the pre-fix ordering failure this test
    # must never reproduce.
    await _run_prune(isolated_session, _single_args(argument.id))

    assert await _utterance_count(isolated_session, old_run.id) == 0
    assert old_run.id not in await _run_ids(isolated_session, argument.id)


async def test_argument_with_zero_runs_is_noop_not_error(isolated_session, capsys):
    """An argument with zero import_run rows is a no-op, not an error."""
    argument = await _seed_argument(isolated_session)

    await _run_prune(isolated_session, _single_args(argument.id))
    out = capsys.readouterr().out

    assert "0 runs removed" in out
    assert await _run_ids(isolated_session, argument.id) == set()


async def test_unknown_argument_id_raises(isolated_session):
    with pytest.raises(ValueError, match="No argument with id"):
        await _run_prune(isolated_session, _single_args(999_999_999))


async def test_prunable_run_ids_excludes_served_run(isolated_session):
    """Direct unit coverage of `_prunable_run_ids` (PD-22): the served run
    id is never in the prunable set, even when it is the only run."""
    argument = await _seed_argument(isolated_session)
    served = await _seed_run(isolated_session, argument, step="parse")

    info = await _prunable_run_ids(isolated_session, argument.id)

    assert info["served_run_id"] == served.id
    assert info["prunable"] == []


# ===========================================================================
# CLI-level tests
# ===========================================================================


def test_help_lists_all_four_flags():
    result = subprocess.run(
        [sys.executable, "-m", "pipeline", "prune-runs", "--help"],
        cwd=str(Path(__file__).resolve().parents[2]),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "--all" in result.stdout
    assert "--argument-id" in result.stdout
    assert "--dry-run" in result.stdout
    assert "--include-resolved-discrepancies" in result.stdout


def test_no_flag_exits_non_zero():
    result = subprocess.run(
        [sys.executable, "-m", "pipeline", "prune-runs"],
        cwd=str(Path(__file__).resolve().parents[2]),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
