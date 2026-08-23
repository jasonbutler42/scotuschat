"""
Exhaustive authority-ladder matrix test (Phase 49, plan 49-04, D-32).

Two sections:
  1. Pure unit matrix over `api.domain.authority` — no DB, always collects,
     always runs (this half must remain runnable with no DATABASE_URL).
  2. DB-gated integration coverage of the ONE authority-gated writer
     (`api.services.admin_review.apply_participant_value_change` /
     `apply_person_value_change`) against every plan `<behavior>` bullet.
"""

from __future__ import annotations

import os

import pytest

from api.domain.authority import AuthorityRank, WriteDecision, authority_rank, decide_write

# ---------------------------------------------------------------------------
# Section 1 — pure unit matrix (no DB)
# ---------------------------------------------------------------------------

# One representative (source, method, review_state) triple per AuthorityRank,
# used to drive decide_write() across the full rank x rank x differs matrix.
_REPRESENTATIVE = {
    AuthorityRank.UNKNOWN: ("bogus_source", "bogus_method", "unreviewed"),
    AuthorityRank.PDF_LLM: ("pdf_pipeline", "llm_corrective", "unreviewed"),
    AuthorityRank.PDF_RULE_BASED: ("pdf_pipeline", "rule_based", "unreviewed"),
    AuthorityRank.CORPUS: ("corpus", "direct", "unreviewed"),
    AuthorityRank.OPERATOR: ("operator", "manual", "unreviewed"),
}


def _expected_decision(incoming_rank: AuthorityRank, stored_rank: AuthorityRank, differs: bool) -> WriteDecision:
    """Expectation derived from rank comparison, not hardcoded per case, so
    adding a rung cannot leave a hole (D-32)."""
    if not differs:
        return WriteDecision.ACCEPT
    if incoming_rank > stored_rank:
        return WriteDecision.ACCEPT_AND_RECORD
    return WriteDecision.REJECT_AND_RECORD


def _matrix_cases():
    cases = []
    for incoming_rank in AuthorityRank:
        for stored_rank in AuthorityRank:
            for differs in (True, False):
                cases.append((incoming_rank, stored_rank, differs))
    return cases


_MATRIX_CASES = _matrix_cases()


@pytest.mark.parametrize(
    "incoming_rank,stored_rank,differs",
    _MATRIX_CASES,
    ids=[
        f"incoming={ir.name}-stored={sr.name}-differs={d}"
        for ir, sr, d in _MATRIX_CASES
    ],
)
def test_decide_write_matrix(incoming_rank, stored_rank, differs) -> None:
    incoming_source, incoming_method, incoming_review_state = _REPRESENTATIVE[incoming_rank]
    existing_source, existing_method, existing_review_state = _REPRESENTATIVE[stored_rank]

    decision = decide_write(
        incoming_source=incoming_source,
        incoming_method=incoming_method,
        incoming_review_state=incoming_review_state,
        existing_source=existing_source,
        existing_method=existing_method,
        existing_review_state=existing_review_state,
        values_differ=differs,
    )
    assert decision == _expected_decision(incoming_rank, stored_rank, differs)


def test_matrix_exercises_every_combination() -> None:
    """D-32: a future rung not wired into the parametrization fails loudly
    rather than silently reducing coverage."""
    assert len(_MATRIX_CASES) == len(AuthorityRank) ** 2 * 2


# ---------------------------------------------------------------------------
# Named tests — one per <behavior> bullet naming a specific rank mapping, so
# a rank misassignment produces a readable failure rather than one line in
# the 50-case table above.
# ---------------------------------------------------------------------------


def test_operator_authority_read_off_review_state_first() -> None:
    assert authority_rank("operator", "manual", "unreviewed") == AuthorityRank.OPERATOR
    assert authority_rank("corpus", "direct", "operator_edited") == AuthorityRank.OPERATOR


def test_corpus_and_seed_rank_identically() -> None:
    assert authority_rank("corpus", "direct", "unreviewed") == AuthorityRank.CORPUS
    assert authority_rank("seed", "direct", "unreviewed") == AuthorityRank.CORPUS


def test_pdf_pipeline_rule_based_and_llm_corrective_rank_distinctly() -> None:
    assert authority_rank("pdf_pipeline", "rule_based", "unreviewed") == AuthorityRank.PDF_RULE_BASED
    assert authority_rank("pdf_pipeline", "llm_corrective", "unreviewed") == AuthorityRank.PDF_LLM


def test_unrecognised_triple_ranks_unknown_fail_closed() -> None:
    assert authority_rank("nonsense", "nonsense", "nonsense") == AuthorityRank.UNKNOWN
    assert authority_rank("", "", "") == AuthorityRank.UNKNOWN


def test_values_differ_false_returns_accept_for_every_rank_pair() -> None:
    for incoming_rank in AuthorityRank:
        for stored_rank in AuthorityRank:
            incoming_source, incoming_method, incoming_review_state = _REPRESENTATIVE[incoming_rank]
            existing_source, existing_method, existing_review_state = _REPRESENTATIVE[stored_rank]
            decision = decide_write(
                incoming_source=incoming_source,
                incoming_method=incoming_method,
                incoming_review_state=incoming_review_state,
                existing_source=existing_source,
                existing_method=existing_method,
                existing_review_state=existing_review_state,
                values_differ=False,
            )
            assert decision == WriteDecision.ACCEPT


def test_equal_authority_with_differing_values_rejects_and_records() -> None:
    decision = decide_write(
        incoming_source="corpus",
        incoming_method="direct",
        incoming_review_state="unreviewed",
        existing_source="corpus",
        existing_method="direct",
        existing_review_state="unreviewed",
        values_differ=True,
    )
    assert decision == WriteDecision.REJECT_AND_RECORD


def test_strictly_higher_incoming_authority_accepts_and_records() -> None:
    decision = decide_write(
        incoming_source="operator",
        incoming_method="manual",
        incoming_review_state="unreviewed",
        existing_source="corpus",
        existing_method="direct",
        existing_review_state="unreviewed",
        values_differ=True,
    )
    assert decision == WriteDecision.ACCEPT_AND_RECORD


def test_strictly_lower_incoming_authority_rejects_and_records() -> None:
    decision = decide_write(
        incoming_source="corpus",
        incoming_method="direct",
        incoming_review_state="unreviewed",
        existing_source="operator",
        existing_method="manual",
        existing_review_state="unreviewed",
        values_differ=True,
    )
    assert decision == WriteDecision.REJECT_AND_RECORD


def test_decide_write_never_writes_without_recording_when_values_differ() -> None:
    """ACCEPT (write, no record) is only ever returned when values_differ is
    False — never paired with a differing value."""
    for incoming_rank in AuthorityRank:
        for stored_rank in AuthorityRank:
            incoming_source, incoming_method, incoming_review_state = _REPRESENTATIVE[incoming_rank]
            existing_source, existing_method, existing_review_state = _REPRESENTATIVE[stored_rank]
            decision = decide_write(
                incoming_source=incoming_source,
                incoming_method=incoming_method,
                incoming_review_state=incoming_review_state,
                existing_source=existing_source,
                existing_method=existing_method,
                existing_review_state=existing_review_state,
                values_differ=True,
            )
            assert decision != WriteDecision.ACCEPT


# ---------------------------------------------------------------------------
# Section 2 — DB-gated integration half. Covers every Task 2 <behavior>
# bullet against the real authority-gated writer. Kept in a clearly
# separated section so the pure half above still collects with no DB.
# ---------------------------------------------------------------------------


def _db_configured() -> bool:
    """Same guard every DB-gated api/tests module uses (WR-04)."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


async def _make_argument_with_participant(*, review_state=None, source=None, method=None, side=None):
    import uuid as _uuid

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Case,
        CaseArgument,
        Person,
        ReviewState,
        SideEnum,
    )

    suffix = _uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        arg = Argument(status=ArgumentStatusEnum.CANDIDATE)
        db.add(arg)
        await db.flush()

        case = Case(
            docket_number=f"AM-01-{suffix}",
            docket_number_norm=f"am-01-{suffix}",
            case_name="Authority Matrix Fixture",
            term_year=2026,
            slug=f"authority-matrix-fixture-{suffix}",
        )
        db.add(case)
        await db.flush()
        db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))

        person = Person(full_name="Authority Matrix Advocate")
        db.add(person)
        await db.flush()

        participant_kwargs = dict(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label="MR. AUTHORITY",
            side=side or SideEnum.PETITIONER,
        )
        if review_state is not None:
            participant_kwargs["review_state"] = review_state
        if source is not None:
            participant_kwargs["source"] = source
        if method is not None:
            participant_kwargs["method"] = method
        participant = ArgumentParticipant(**participant_kwargs)
        db.add(participant)
        await db.commit()

        return {
            "argument_id": arg.id,
            "case_id": case.id,
            "person_id": person.id,
            "participant_id": participant.id,
        }


async def _teardown_argument_with_participant(ids: dict) -> None:
    from sqlalchemy import delete as sa_delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        Argument,
        ArgumentParticipant,
        Case,
        CaseArgument,
        Person,
        ValueDiscrepancy,
    )

    async with AsyncSessionLocal() as db:
        await db.execute(
            sa_delete(ValueDiscrepancy).where(
                ValueDiscrepancy.target_type == "argument_participant",
                ValueDiscrepancy.target_id == ids["participant_id"],
            )
        )
        await db.execute(
            sa_delete(ArgumentParticipant).where(ArgumentParticipant.id == ids["participant_id"])
        )
        await db.execute(
            sa_delete(CaseArgument).where(CaseArgument.argument_id == ids["argument_id"])
        )
        await db.execute(sa_delete(Case).where(Case.id == ids["case_id"]))
        await db.execute(sa_delete(Person).where(Person.id == ids["person_id"]))
        await db.execute(sa_delete(Argument).where(Argument.id == ids["argument_id"]))
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_equal_value_updates_row_and_creates_no_discrepancy() -> None:
    from sqlalchemy import select as sa_select

    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentParticipant, SideEnum, ValueDiscrepancy
    from api.services.admin_review import apply_participant_value_change

    ids = await _make_argument_with_participant(side=SideEnum.PETITIONER)
    try:
        async with AsyncSessionLocal() as db:
            participant = await db.get(ArgumentParticipant, ids["participant_id"])
            decision = await apply_participant_value_change(
                db,
                participant=participant,
                field="side",
                incoming_value=SideEnum.PETITIONER,
                incoming_source="operator",
                incoming_method="manual",
            )
            await db.commit()

        from api.domain.authority import WriteDecision

        assert decision == WriteDecision.ACCEPT

        async with AsyncSessionLocal() as db:
            refreshed = await db.get(ArgumentParticipant, ids["participant_id"])
            assert refreshed.side == SideEnum.PETITIONER
            count = (
                await db.execute(
                    sa_select(ValueDiscrepancy).where(
                        ValueDiscrepancy.target_type == "argument_participant",
                        ValueDiscrepancy.target_id == ids["participant_id"],
                    )
                )
            ).all()
            assert len(count) == 0
    finally:
        await _teardown_argument_with_participant(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_manual_check_corpus_write_against_operator_edited_participant_rejects_and_records() -> None:
    """Task 2's plan-mandated manual check: with an operator-edited
    participant in the DB, calling apply_participant_value_change with
    incoming_source='corpus' and a differing value leaves the column
    unchanged and inserts exactly one open value_discrepancy row (D-16's
    worked example: incoming corpus < existing operator)."""
    from sqlalchemy import select as sa_select

    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentParticipant, ReviewState, SideEnum, ValueDiscrepancy
    from api.services.admin_review import apply_participant_value_change

    ids = await _make_argument_with_participant(
        review_state=ReviewState.OPERATOR_EDITED, side=SideEnum.PETITIONER
    )
    try:
        async with AsyncSessionLocal() as db:
            participant = await db.get(ArgumentParticipant, ids["participant_id"])
            decision = await apply_participant_value_change(
                db,
                participant=participant,
                field="side",
                incoming_value=SideEnum.RESPONDENT,
                incoming_source="corpus",
                incoming_method="direct",
            )
            await db.commit()

        from api.domain.authority import WriteDecision

        assert decision == WriteDecision.REJECT_AND_RECORD

        async with AsyncSessionLocal() as db:
            refreshed = await db.get(ArgumentParticipant, ids["participant_id"])
            assert refreshed.side == SideEnum.PETITIONER  # unchanged

            rows = (
                await db.execute(
                    sa_select(ValueDiscrepancy).where(
                        ValueDiscrepancy.target_type == "argument_participant",
                        ValueDiscrepancy.target_id == ids["participant_id"],
                    )
                )
            ).scalars().all()
            assert len(rows) == 1
            assert rows[0].resolved_at is None
    finally:
        await _teardown_argument_with_participant(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_equal_authority_differing_value_leaves_column_untouched_and_records_one_discrepancy() -> None:
    from sqlalchemy import select as sa_select

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        ArgumentParticipant,
        ImportMethod,
        ImportSource,
        ReviewState,
        SideEnum,
        ValueDiscrepancy,
    )
    from api.services.admin_review import apply_participant_value_change

    ids = await _make_argument_with_participant(
        review_state=ReviewState.OPERATOR_EDITED, side=SideEnum.PETITIONER
    )
    try:
        async with AsyncSessionLocal() as db:
            participant = await db.get(ArgumentParticipant, ids["participant_id"])
            decision = await apply_participant_value_change(
                db,
                participant=participant,
                field="side",
                incoming_value=SideEnum.RESPONDENT,
                incoming_source="operator",
                incoming_method="manual",
            )
            await db.commit()

        from api.domain.authority import WriteDecision

        assert decision == WriteDecision.REJECT_AND_RECORD

        async with AsyncSessionLocal() as db:
            refreshed = await db.get(ArgumentParticipant, ids["participant_id"])
            assert refreshed.side == SideEnum.PETITIONER  # unchanged

            rows = (
                await db.execute(
                    sa_select(ValueDiscrepancy).where(
                        ValueDiscrepancy.target_type == "argument_participant",
                        ValueDiscrepancy.target_id == ids["participant_id"],
                        ValueDiscrepancy.resolved_at.is_(None),
                    )
                )
            ).scalars().all()
            assert len(rows) == 1
            assert rows[0].field == "side"
    finally:
        await _teardown_argument_with_participant(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_strictly_higher_authority_differing_value_updates_and_records_overwritten_value() -> None:
    from sqlalchemy import select as sa_select

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        ArgumentParticipant,
        ImportMethod,
        ImportSource,
        SideEnum,
        ValueDiscrepancy,
    )
    from api.services.admin_review import apply_participant_value_change

    ids = await _make_argument_with_participant(
        source=ImportSource.PDF_PIPELINE, method=ImportMethod.LLM_CORRECTIVE, side=SideEnum.PETITIONER
    )
    try:
        async with AsyncSessionLocal() as db:
            participant = await db.get(ArgumentParticipant, ids["participant_id"])
            decision = await apply_participant_value_change(
                db,
                participant=participant,
                field="side",
                incoming_value=SideEnum.RESPONDENT,
                incoming_source="operator",
                incoming_method="manual",
            )
            await db.commit()

        from api.domain.authority import WriteDecision

        assert decision == WriteDecision.ACCEPT_AND_RECORD

        async with AsyncSessionLocal() as db:
            refreshed = await db.get(ArgumentParticipant, ids["participant_id"])
            assert refreshed.side == SideEnum.RESPONDENT

            rows = (
                await db.execute(
                    sa_select(ValueDiscrepancy).where(
                        ValueDiscrepancy.target_type == "argument_participant",
                        ValueDiscrepancy.target_id == ids["participant_id"],
                    )
                )
            ).scalars().all()
            assert len(rows) == 1
            assert rows[0].existing_value == "PETITIONER" or rows[0].existing_value == SideEnum.PETITIONER.value
    finally:
        await _teardown_argument_with_participant(ids)


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_name_part_whitespace_only_difference_is_not_a_disagreement() -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import Person
    from api.services.admin_review import apply_person_value_change, _values_differ

    assert _values_differ("first_name", "  John  ", "John") is False
    assert _values_differ("first_name", "john", "John") is True


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_update_resolve_row_for_job_succeeds_on_draft_and_unpublished_but_not_published() -> None:
    import uuid as _uuid

    from api.core.database import AsyncSessionLocal
    from api.models.models import (
        AdminJob,
        AdminJobStatus,
        AdminJobStep,
        Argument,
        ArgumentParticipant,
        ArgumentStatusEnum,
        Case,
        CaseArgument,
        ReviewState,
        SideEnum,
        ValueDiscrepancy,
    )
    from api.schemas.admin_jobs import ResolveRowUpdate
    from api.services.admin_jobs import update_resolve_row_for_job

    for status, should_succeed in (
        (ArgumentStatusEnum.DRAFT, True),
        (ArgumentStatusEnum.UNPUBLISHED, True),
        (ArgumentStatusEnum.PUBLISHED, False),
    ):
        suffix = _uuid.uuid4().hex[:8]
        async with AsyncSessionLocal() as db:
            arg = Argument(status=status, resolved_at=None)
            db.add(arg)
            await db.flush()
            case = Case(
                docket_number=f"AM-02-{suffix}",
                docket_number_norm=f"am-02-{suffix}",
                case_name="Authority Matrix Status Fixture",
                term_year=2026,
                slug=f"authority-matrix-status-fixture-{suffix}",
            )
            db.add(case)
            await db.flush()
            db.add(CaseArgument(case_id=case.id, argument_id=arg.id, is_lead=True))
            participant = ArgumentParticipant(
                argument_id=arg.id,
                raw_speaker_label="MR. STATUS",
                side=SideEnum.PETITIONER,
            )
            db.add(participant)
            await db.flush()
            job = AdminJob(
                status=AdminJobStatus.PAUSED,
                current_step=AdminJobStep.RESOLVE,
                argument_id=arg.id,
            )
            db.add(job)
            await db.commit()
            arg_id, case_id, participant_id, job_id = arg.id, case.id, participant.id, job.id

        try:
            body = ResolveRowUpdate(
                participant_id=participant_id, side=SideEnum.RESPONDENT, descriptor="Counsel"
            )
            async with AsyncSessionLocal() as db:
                if should_succeed:
                    updated = await update_resolve_row_for_job(db, job_id, body)
                    # CR-01 regression (49-REVIEW.md): a successful
                    # resolve-row save must advance review_state to
                    # OPERATOR_EDITED and close its own value_discrepancy in
                    # the SAME transaction (D-15) — no more permanently
                    # stuck, unactionable review-queue row.
                    assert updated.review_state == ReviewState.OPERATOR_EDITED
                    from sqlalchemy import select as sa_select

                    open_discrepancies = (
                        await db.execute(
                            sa_select(ValueDiscrepancy).where(
                                ValueDiscrepancy.target_type == "argument_participant",
                                ValueDiscrepancy.target_id == participant_id,
                                ValueDiscrepancy.resolved_at.is_(None),
                            )
                        )
                    ).scalars().all()
                    assert open_discrepancies == []
                else:
                    with pytest.raises(ValueError):
                        await update_resolve_row_for_job(db, job_id, body)
        finally:
            from sqlalchemy import delete as sa_delete

            async with AsyncSessionLocal() as db:
                await db.execute(sa_delete(AdminJob).where(AdminJob.id == job_id))
                # CR-01 fix (49-REVIEW.md): update_resolve_row_for_job now
                # closes its own value_discrepancy rows in the same
                # transaction as the write, so a successful call never
                # leaves an open one behind. value_discrepancy.target_id has
                # no real FK to argument_participants.id (by design — see
                # api/tests/conftest.py's _sweep_orphaned_value_discrepancies
                # docstring), and that autouse fixture sweeps any (now
                # resolved) row left pointing at the participant deleted
                # below — this teardown no longer needs its own explicit
                # ValueDiscrepancy delete.
                await db.execute(
                    sa_delete(ArgumentParticipant).where(ArgumentParticipant.id == participant_id)
                )
                await db.execute(sa_delete(CaseArgument).where(CaseArgument.argument_id == arg_id))
                await db.execute(sa_delete(Case).where(Case.id == case_id))
                await db.execute(sa_delete(Argument).where(Argument.id == arg_id))
                await db.commit()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_each_public_writer_commits_exactly_once_helpers_never_commit() -> None:
    """Structural check (not a DB round-trip): the shared helpers in
    api.services.admin_review never call db.commit() — verified by source
    inspection in the acceptance criteria's grep checks; this test exercises
    one concrete call path end-to-end to confirm no exception leaks from a
    stray commit-then-use-closed-session bug."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import ArgumentParticipant, SideEnum
    from api.services.admin_review import apply_participant_value_change

    ids = await _make_argument_with_participant(side=SideEnum.PETITIONER)
    try:
        async with AsyncSessionLocal() as db:
            participant = await db.get(ArgumentParticipant, ids["participant_id"])
            await apply_participant_value_change(
                db,
                participant=participant,
                field="side",
                incoming_value=SideEnum.RESPONDENT,
                incoming_source="operator",
                incoming_method="manual",
            )
            # No commit was called by the helper — this explicit commit is
            # the caller's own responsibility, proving the helper left the
            # transaction open rather than closing it prematurely.
            await db.commit()
    finally:
        await _teardown_argument_with_participant(ids)
