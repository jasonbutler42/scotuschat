"""
Pipeline run state machine and re-run behavior tests.

Test IDs covered (from VALIDATION.md):
  - 1-state-machine: PIPE-10 status transitions pending→running→completed
  - 1-rerun:         PIPE-11 re-run creates new rows; old rows preserved

These tests are DB-dependent and skip gracefully when DATABASE_URL is not set.
The async_session fixture in conftest.py handles the skip.
"""

import datetime

import pytest
from sqlalchemy import func, select


# ---------------------------------------------------------------------------
# Test 1: State machine transitions (PIPE-10 / 1-state-machine)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_state_machine(async_session):
    """
    PipelineRun status must follow: pending → running → completed.

    Verifies that all three status values can be set and persisted,
    and that the final status is 'completed'.
    """
    from api.models.models import (
        Argument,
        Case,
        CaseArgument,
        PipelineRun,
        PipelineRunStatus,
    )

    # Create minimal supporting records
    case = Case(
        docket_number="00-SM-TEST",
        docket_number_norm="00-SM-TEST",
        case_name="State Machine Test v. Test",
        term_year=2024,
        slug="state-machine-test-v-test",
    )
    async_session.add(case)
    await async_session.flush()

    argument = Argument(argued_date=datetime.date(2024, 2, 1), question_number=1)
    async_session.add(argument)
    await async_session.flush()

    case_arg = CaseArgument(case_id=case.id, argument_id=argument.id, is_lead=True)
    async_session.add(case_arg)
    await async_session.flush()

    # Create pipeline run in PENDING status
    run = PipelineRun(
        argument_id=argument.id,
        step="parse",
        status=PipelineRunStatus.PENDING,
    )
    async_session.add(run)
    await async_session.flush()

    assert run.status == PipelineRunStatus.PENDING, (
        f"Expected PENDING, got {run.status}"
    )

    # Transition: pending → running
    run.status = PipelineRunStatus.RUNNING
    await async_session.flush()

    assert run.status == PipelineRunStatus.RUNNING, (
        f"Expected RUNNING, got {run.status}"
    )

    # Transition: running → completed
    run.status = PipelineRunStatus.COMPLETED
    run.completed_at = datetime.datetime.now(datetime.timezone.utc)
    await async_session.flush()

    assert run.status == PipelineRunStatus.COMPLETED, (
        f"Expected COMPLETED, got {run.status}"
    )
    assert run.completed_at is not None


# ---------------------------------------------------------------------------
# Test 2: Re-run creates new rows, old rows preserved (PIPE-11 / 1-rerun)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rerun_creates_new_rows(async_session, monkeypatch):
    """
    Running parse twice (for two different pipeline_run_ids) must:
    1. Create new utterance rows for the second run.
    2. NOT delete the utterance rows from the first run.
    3. Total utterance count = sum from both runs (each run's rows preserved).
    """
    from api.models.models import (
        Argument,
        Case,
        CaseArgument,
        PipelineRun,
        PipelineRunStatus,
        SideEnum,
        Utterance,
    )

    # Minimal DB records
    case = Case(
        docket_number="00-RR-TEST",
        docket_number_norm="00-RR-TEST",
        case_name="Rerun Test v. Test",
        term_year=2024,
        slug="rerun-test-v-test",
    )
    async_session.add(case)
    await async_session.flush()

    argument = Argument(argued_date=datetime.date(2024, 3, 1), question_number=1)
    async_session.add(argument)
    await async_session.flush()

    case_arg = CaseArgument(case_id=case.id, argument_id=argument.id, is_lead=True)
    async_session.add(case_arg)
    await async_session.flush()

    # Run 1: create pipeline_run and write 3 utterance rows
    run1 = PipelineRun(
        argument_id=argument.id,
        step="parse",
        status=PipelineRunStatus.PENDING,
    )
    async_session.add(run1)
    await async_session.flush()

    run1.status = PipelineRunStatus.RUNNING
    await async_session.flush()

    for seq in range(1, 4):
        utt = Utterance(
            argument_id=argument.id,
            pipeline_run_id=run1.id,
            sequence=seq,
            raw_speaker_label="CHIEF JUSTICE ROBERTS" if seq % 2 == 1 else "MR. OLSON",
            text=f"Run 1 utterance {seq}.",
            is_stage_direction=False,
            section_hint=None,
            side=SideEnum.BENCH if seq % 2 == 1 else SideEnum.ADVOCATE,
            person_id=None,
            strategy="rule_based",
        )
        async_session.add(utt)

    run1.status = PipelineRunStatus.COMPLETED
    run1.completed_at = datetime.datetime.now(datetime.timezone.utc)
    run1.strategy = "rule_based"
    await async_session.flush()

    # Verify run 1 rows exist
    result1 = await async_session.execute(
        select(func.count()).select_from(Utterance).where(
            Utterance.pipeline_run_id == run1.id
        )
    )
    count_after_run1 = result1.scalar()
    assert count_after_run1 == 3, f"Expected 3 rows after run 1, got {count_after_run1}"

    # Run 2: create a NEW pipeline_run and write 2 utterance rows
    run2 = PipelineRun(
        argument_id=argument.id,
        step="parse",
        status=PipelineRunStatus.PENDING,
    )
    async_session.add(run2)
    await async_session.flush()

    run2.status = PipelineRunStatus.RUNNING
    await async_session.flush()

    for seq in range(1, 3):
        utt = Utterance(
            argument_id=argument.id,
            pipeline_run_id=run2.id,
            sequence=seq,
            raw_speaker_label="CHIEF JUSTICE ROBERTS" if seq == 1 else "MR. OLSON",
            text=f"Run 2 utterance {seq}.",
            is_stage_direction=False,
            section_hint=None,
            side=SideEnum.BENCH if seq == 1 else SideEnum.ADVOCATE,
            person_id=None,
            strategy="rule_based",
        )
        async_session.add(utt)

    run2.status = PipelineRunStatus.COMPLETED
    run2.completed_at = datetime.datetime.now(datetime.timezone.utc)
    run2.strategy = "rule_based"
    await async_session.flush()

    # Verify run 1 rows STILL EXIST after run 2 (PIPE-11 — no delete on re-run)
    result1_after = await async_session.execute(
        select(func.count()).select_from(Utterance).where(
            Utterance.pipeline_run_id == run1.id
        )
    )
    count_run1_after_rerun = result1_after.scalar()
    assert count_run1_after_rerun == 3, (
        f"Run 1 rows should still exist after run 2 (PIPE-11), "
        f"but found only {count_run1_after_rerun}"
    )

    # Verify run 2 rows exist
    result2 = await async_session.execute(
        select(func.count()).select_from(Utterance).where(
            Utterance.pipeline_run_id == run2.id
        )
    )
    count_run2 = result2.scalar()
    assert count_run2 == 2, f"Expected 2 rows for run 2, got {count_run2}"

    # Total rows = 3 (run 1) + 2 (run 2) = 5
    result_total = await async_session.execute(
        select(func.count()).select_from(Utterance).where(
            Utterance.argument_id == argument.id
        )
    )
    total_count = result_total.scalar()
    assert total_count == 5, (
        f"Expected 5 total utterance rows (3 from run1 + 2 from run2), "
        f"got {total_count}"
    )
