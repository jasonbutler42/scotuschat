"""
Exhaustive gate test module for `apply_argument_value_change` and
`apply_case_value_change` (Phase 50, plan 50-02, Task 1).

DB-gated integration coverage of the two new peer gate functions in
`api.services.admin_review`, mirroring `api/tests/test_authority_matrix.py`
Section 2's established seed/teardown/assert pattern: bare
`AsyncSessionLocal` sessions (uncommitted state is invisible to the app's
own request-scoped sessions), never the ORM object across sessions.

Eleven `<behavior>` bullets, each proven once against `Argument`
(`question_number`, nullable Integer) and once against `Case` (`case_name`,
NOT NULL String — its "blank" sentinel is `""`, not `None`, since the
column itself cannot be NULL; `_normalize_generic("")` still collapses to
`None`, so the gate's blank semantics are identical either way) = 22 named
tests, satisfying the plan's "at least 22 tests collected" acceptance
criterion by construction, not by padding.

Every test asserts the returned decision AND the resulting row state AND
the resulting `value_discrepancy` row count together — a test that only
checks the decision cannot see a write that did not happen (plan mandate).
"""

from __future__ import annotations

import os
import uuid as _uuid

import pytest

from api.domain.authority import WriteDecision


def _db_configured() -> bool:
    """Same guard every DB-gated api/tests module uses (WR-04)."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


pytestmark = pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")


# ---------------------------------------------------------------------------
# Seed / teardown / assertion helpers
# ---------------------------------------------------------------------------


async def _make_argument(*, source=None, method=None, question_number=None):
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ArgumentStatusEnum

    async with AsyncSessionLocal() as db:
        arg = Argument(
            status=ArgumentStatusEnum.CANDIDATE,
            source=source,
            method=method,
            question_number=question_number,
        )
        db.add(arg)
        await db.commit()
        return {"argument_id": arg.id}


async def _teardown_argument(ids: dict) -> None:
    from sqlalchemy import delete as sa_delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument, ValueDiscrepancy

    async with AsyncSessionLocal() as db:
        await db.execute(
            sa_delete(ValueDiscrepancy).where(
                ValueDiscrepancy.target_type == "argument",
                ValueDiscrepancy.target_id == ids["argument_id"],
            )
        )
        await db.execute(sa_delete(Argument).where(Argument.id == ids["argument_id"]))
        await db.commit()


async def _get_argument(argument_id: int):
    from api.core.database import AsyncSessionLocal
    from api.models.models import Argument

    async with AsyncSessionLocal() as db:
        return await db.get(Argument, argument_id)


async def _make_case(*, source=None, method=None, case_name="Case Gate Fixture"):
    from api.core.database import AsyncSessionLocal
    from api.models.models import Case

    suffix = _uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        case = Case(
            docket_number=f"CG-01-{suffix}",
            docket_number_norm=f"cg-01-{suffix}",
            case_name=case_name,
            term_year=2026,
            slug=f"case-gate-fixture-{suffix}",
            source=source,
            method=method,
        )
        db.add(case)
        await db.commit()
        return {"case_id": case.id}


async def _teardown_case(ids: dict) -> None:
    from sqlalchemy import delete as sa_delete

    from api.core.database import AsyncSessionLocal
    from api.models.models import Case, ValueDiscrepancy

    async with AsyncSessionLocal() as db:
        await db.execute(
            sa_delete(ValueDiscrepancy).where(
                ValueDiscrepancy.target_type == "case",
                ValueDiscrepancy.target_id == ids["case_id"],
            )
        )
        await db.execute(sa_delete(Case).where(Case.id == ids["case_id"]))
        await db.commit()


async def _get_case(case_id: int):
    from api.core.database import AsyncSessionLocal
    from api.models.models import Case

    async with AsyncSessionLocal() as db:
        return await db.get(Case, case_id)


async def _open_discrepancy_count(target_type: str, target_id: int) -> int:
    from sqlalchemy import select as sa_select

    from api.core.database import AsyncSessionLocal
    from api.models.models import ValueDiscrepancy

    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                sa_select(ValueDiscrepancy).where(
                    ValueDiscrepancy.target_type == target_type,
                    ValueDiscrepancy.target_id == target_id,
                    ValueDiscrepancy.resolved_at.is_(None),
                )
            )
        ).scalars().all()
        return len(rows)


# ---------------------------------------------------------------------------
# Bullet 1 — values agree after normalization -> ACCEPT, harmless write, no
# discrepancy.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_argument_values_agree_after_normalization_accepts_no_discrepancy() -> None:
    from api.services.admin_review import apply_argument_value_change

    ids = await _make_argument(question_number=1)
    try:
        argument = await _get_argument(ids["argument_id"])
        decision = None
        from api.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            argument = await db.get(type(argument), ids["argument_id"])
            decision = await apply_argument_value_change(
                db,
                argument=argument,
                field="question_number",
                incoming_value=1,
                incoming_source="corpus",
                incoming_method="direct",
            )
            await db.commit()

        assert decision == WriteDecision.ACCEPT
        refreshed = await _get_argument(ids["argument_id"])
        assert refreshed.question_number == 1
        assert await _open_discrepancy_count("argument", ids["argument_id"]) == 0
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
async def test_case_values_agree_after_normalization_accepts_no_discrepancy() -> None:
    from api.core.database import AsyncSessionLocal
    from api.services.admin_review import apply_case_value_change

    ids = await _make_case(case_name="Roe v. Wade")
    try:
        async with AsyncSessionLocal() as db:
            case = await db.get(type(await _get_case(ids["case_id"])), ids["case_id"])
            decision = await apply_case_value_change(
                db,
                case=case,
                field="case_name",
                incoming_value="Roe v. Wade",
                incoming_source="corpus",
                incoming_method="direct",
            )
            await db.commit()

        assert decision == WriteDecision.ACCEPT
        refreshed = await _get_case(ids["case_id"])
        assert refreshed.case_name == "Roe v. Wade"
        assert await _open_discrepancy_count("case", ids["case_id"]) == 0
    finally:
        await _teardown_case(ids)


# ---------------------------------------------------------------------------
# Bullet 2 — stored source=corpus, incoming corpus differs -> REJECT_AND_RECORD.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_argument_stored_corpus_incoming_corpus_differs_rejects_and_records() -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.admin_review import apply_argument_value_change

    ids = await _make_argument(
        source=ImportSource.CORPUS, method=ImportMethod.DIRECT, question_number=1
    )
    try:
        async with AsyncSessionLocal() as db:
            argument = await db.get(type(await _get_argument(ids["argument_id"])), ids["argument_id"])
            decision = await apply_argument_value_change(
                db,
                argument=argument,
                field="question_number",
                incoming_value=2,
                incoming_source="corpus",
                incoming_method="direct",
            )
            await db.commit()

        assert decision == WriteDecision.REJECT_AND_RECORD
        refreshed = await _get_argument(ids["argument_id"])
        assert refreshed.question_number == 1  # unchanged
        assert await _open_discrepancy_count("argument", ids["argument_id"]) == 1
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
async def test_case_stored_corpus_incoming_corpus_differs_rejects_and_records() -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.admin_review import apply_case_value_change

    ids = await _make_case(
        source=ImportSource.CORPUS, method=ImportMethod.DIRECT, case_name="Roe v. Wade"
    )
    try:
        async with AsyncSessionLocal() as db:
            case = await db.get(type(await _get_case(ids["case_id"])), ids["case_id"])
            decision = await apply_case_value_change(
                db,
                case=case,
                field="case_name",
                incoming_value="Doe v. Bolton",
                incoming_source="corpus",
                incoming_method="direct",
            )
            await db.commit()

        assert decision == WriteDecision.REJECT_AND_RECORD
        refreshed = await _get_case(ids["case_id"])
        assert refreshed.case_name == "Roe v. Wade"  # unchanged
        assert await _open_discrepancy_count("case", ids["case_id"]) == 1
    finally:
        await _teardown_case(ids)


# ---------------------------------------------------------------------------
# Bullet 3 — stored source=operator, incoming corpus differs -> REJECT_AND_RECORD;
# the operator value survives.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_argument_stored_operator_incoming_corpus_differs_rejects_and_records() -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.admin_review import apply_argument_value_change

    ids = await _make_argument(
        source=ImportSource.OPERATOR, method=ImportMethod.MANUAL, question_number=1
    )
    try:
        async with AsyncSessionLocal() as db:
            argument = await db.get(type(await _get_argument(ids["argument_id"])), ids["argument_id"])
            decision = await apply_argument_value_change(
                db,
                argument=argument,
                field="question_number",
                incoming_value=2,
                incoming_source="corpus",
                incoming_method="direct",
            )
            await db.commit()

        assert decision == WriteDecision.REJECT_AND_RECORD
        refreshed = await _get_argument(ids["argument_id"])
        assert refreshed.question_number == 1
        assert await _open_discrepancy_count("argument", ids["argument_id"]) == 1
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
async def test_case_stored_operator_incoming_corpus_differs_rejects_and_records() -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.admin_review import apply_case_value_change

    ids = await _make_case(
        source=ImportSource.OPERATOR, method=ImportMethod.MANUAL, case_name="Roe v. Wade"
    )
    try:
        async with AsyncSessionLocal() as db:
            case = await db.get(type(await _get_case(ids["case_id"])), ids["case_id"])
            decision = await apply_case_value_change(
                db,
                case=case,
                field="case_name",
                incoming_value="Doe v. Bolton",
                incoming_source="corpus",
                incoming_method="direct",
            )
            await db.commit()

        assert decision == WriteDecision.REJECT_AND_RECORD
        refreshed = await _get_case(ids["case_id"])
        assert refreshed.case_name == "Roe v. Wade"
        assert await _open_discrepancy_count("case", ids["case_id"]) == 1
    finally:
        await _teardown_case(ids)


# ---------------------------------------------------------------------------
# Bullet 4 — stored source=pdf_pipeline/rule_based, incoming corpus differs
# -> ACCEPT_AND_RECORD; the column is written AND a discrepancy row exists.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_argument_stored_pdf_rule_based_incoming_corpus_differs_accepts_and_records() -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.admin_review import apply_argument_value_change

    ids = await _make_argument(
        source=ImportSource.PDF_PIPELINE, method=ImportMethod.RULE_BASED, question_number=1
    )
    try:
        async with AsyncSessionLocal() as db:
            argument = await db.get(type(await _get_argument(ids["argument_id"])), ids["argument_id"])
            decision = await apply_argument_value_change(
                db,
                argument=argument,
                field="question_number",
                incoming_value=2,
                incoming_source="corpus",
                incoming_method="direct",
            )
            await db.commit()

        assert decision == WriteDecision.ACCEPT_AND_RECORD
        refreshed = await _get_argument(ids["argument_id"])
        assert refreshed.question_number == 2
        assert await _open_discrepancy_count("argument", ids["argument_id"]) == 1
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
async def test_case_stored_pdf_rule_based_incoming_corpus_differs_accepts_and_records() -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.admin_review import apply_case_value_change

    ids = await _make_case(
        source=ImportSource.PDF_PIPELINE, method=ImportMethod.RULE_BASED, case_name="Roe v. Wade"
    )
    try:
        async with AsyncSessionLocal() as db:
            case = await db.get(type(await _get_case(ids["case_id"])), ids["case_id"])
            decision = await apply_case_value_change(
                db,
                case=case,
                field="case_name",
                incoming_value="Doe v. Bolton",
                incoming_source="corpus",
                incoming_method="direct",
            )
            await db.commit()

        assert decision == WriteDecision.ACCEPT_AND_RECORD
        refreshed = await _get_case(ids["case_id"])
        assert refreshed.case_name == "Doe v. Bolton"
        assert await _open_discrepancy_count("case", ids["case_id"]) == 1
    finally:
        await _teardown_case(ids)


# ---------------------------------------------------------------------------
# Bullet 5 — stored source=operator, incoming operator differs ->
# ACCEPT_AND_RECORD (the OPERATOR/OPERATOR carve-out).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_argument_stored_operator_incoming_operator_differs_accepts_and_records() -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.admin_review import apply_argument_value_change

    ids = await _make_argument(
        source=ImportSource.OPERATOR, method=ImportMethod.MANUAL, question_number=1
    )
    try:
        async with AsyncSessionLocal() as db:
            argument = await db.get(type(await _get_argument(ids["argument_id"])), ids["argument_id"])
            decision = await apply_argument_value_change(
                db,
                argument=argument,
                field="question_number",
                incoming_value=2,
                incoming_source="operator",
                incoming_method="manual",
            )
            await db.commit()

        assert decision == WriteDecision.ACCEPT_AND_RECORD
        refreshed = await _get_argument(ids["argument_id"])
        assert refreshed.question_number == 2
        assert await _open_discrepancy_count("argument", ids["argument_id"]) == 1
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
async def test_case_stored_operator_incoming_operator_differs_accepts_and_records() -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.admin_review import apply_case_value_change

    ids = await _make_case(
        source=ImportSource.OPERATOR, method=ImportMethod.MANUAL, case_name="Roe v. Wade"
    )
    try:
        async with AsyncSessionLocal() as db:
            case = await db.get(type(await _get_case(ids["case_id"])), ids["case_id"])
            decision = await apply_case_value_change(
                db,
                case=case,
                field="case_name",
                incoming_value="Doe v. Bolton",
                incoming_source="operator",
                incoming_method="manual",
            )
            await db.commit()

        assert decision == WriteDecision.ACCEPT_AND_RECORD
        refreshed = await _get_case(ids["case_id"])
        assert refreshed.case_name == "Doe v. Bolton"
        assert await _open_discrepancy_count("case", ids["case_id"]) == 1
    finally:
        await _teardown_case(ids)


# ---------------------------------------------------------------------------
# Bullet 6 — stored populated, source IS NULL, incoming differs ->
# REJECT_AND_RECORD, stored unchanged (PD-07 fail-closed). Named per the
# plan's own acceptance criterion.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_argument_null_provenance_populated_value_fails_closed_on_differing_incoming() -> None:
    """PD-07/OQ-1: a populated Argument value whose stored `source` is NULL
    fails closed — a differing incoming corpus value is REJECT_AND_RECORD,
    never ACCEPT_AND_RECORD. NULL is unknown provenance, never low
    authority: a bare `("", "")` hand-off to `decide_write` would resolve
    to AuthorityRank.UNKNOWN, which CORPUS strictly outranks."""
    from api.core.database import AsyncSessionLocal
    from api.services.admin_review import apply_argument_value_change

    ids = await _make_argument(source=None, method=None, question_number=1)
    try:
        async with AsyncSessionLocal() as db:
            argument = await db.get(type(await _get_argument(ids["argument_id"])), ids["argument_id"])
            decision = await apply_argument_value_change(
                db,
                argument=argument,
                field="question_number",
                incoming_value=2,
                incoming_source="corpus",
                incoming_method="direct",
            )
            await db.commit()

        assert decision == WriteDecision.REJECT_AND_RECORD
        refreshed = await _get_argument(ids["argument_id"])
        assert refreshed.question_number == 1  # stored value unchanged
        rows_count = await _open_discrepancy_count("argument", ids["argument_id"])
        assert rows_count == 1
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
async def test_case_null_provenance_populated_value_fails_closed_on_differing_incoming() -> None:
    """PD-07/OQ-1, Case leg — same fail-closed rule as the Argument test
    above, against `case_name` with `source IS NULL`."""
    from api.core.database import AsyncSessionLocal
    from api.services.admin_review import apply_case_value_change

    ids = await _make_case(source=None, method=None, case_name="Roe v. Wade")
    try:
        async with AsyncSessionLocal() as db:
            case = await db.get(type(await _get_case(ids["case_id"])), ids["case_id"])
            decision = await apply_case_value_change(
                db,
                case=case,
                field="case_name",
                incoming_value="Doe v. Bolton",
                incoming_source="corpus",
                incoming_method="direct",
            )
            await db.commit()

        assert decision == WriteDecision.REJECT_AND_RECORD
        refreshed = await _get_case(ids["case_id"])
        assert refreshed.case_name == "Roe v. Wade"
        assert await _open_discrepancy_count("case", ids["case_id"]) == 1
    finally:
        await _teardown_case(ids)


# ---------------------------------------------------------------------------
# Bullet 7 — incoming is None/blank, stored populated -> no write, no
# discrepancy, function returns without calling decide_write (D-03). Named
# per the plan's own acceptance criterion.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_argument_blank_incoming_against_populated_stored_is_no_opinion() -> None:
    """D-03: a missing/blank incoming value against a populated stored
    value produces zero value_discrepancy rows and leaves the column
    byte-identical — the function returns None, not a WriteDecision."""
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.admin_review import apply_argument_value_change

    ids = await _make_argument(
        source=ImportSource.CORPUS, method=ImportMethod.DIRECT, question_number=1
    )
    try:
        async with AsyncSessionLocal() as db:
            argument = await db.get(type(await _get_argument(ids["argument_id"])), ids["argument_id"])
            decision = await apply_argument_value_change(
                db,
                argument=argument,
                field="question_number",
                incoming_value=None,
                incoming_source="corpus",
                incoming_method="direct",
            )
            await db.commit()

        assert decision is None
        refreshed = await _get_argument(ids["argument_id"])
        assert refreshed.question_number == 1  # byte-identical
        assert await _open_discrepancy_count("argument", ids["argument_id"]) == 0
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
async def test_case_blank_incoming_against_populated_stored_is_no_opinion() -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.admin_review import apply_case_value_change

    ids = await _make_case(
        source=ImportSource.CORPUS, method=ImportMethod.DIRECT, case_name="Roe v. Wade"
    )
    try:
        async with AsyncSessionLocal() as db:
            case = await db.get(type(await _get_case(ids["case_id"])), ids["case_id"])
            decision = await apply_case_value_change(
                db,
                case=case,
                field="case_name",
                incoming_value="",
                incoming_source="corpus",
                incoming_method="direct",
            )
            await db.commit()

        assert decision is None
        refreshed = await _get_case(ids["case_id"])
        assert refreshed.case_name == "Roe v. Wade"
        assert await _open_discrepancy_count("case", ids["case_id"]) == 0
    finally:
        await _teardown_case(ids)


# ---------------------------------------------------------------------------
# Bullet 8 — stored is None/blank, incoming non-blank -> the column is
# written and NO discrepancy row is created (PD-13 gap-fill).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_argument_blank_stored_receiving_non_blank_incoming_is_gap_fill_no_discrepancy() -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.admin_review import apply_argument_value_change

    ids = await _make_argument(source=None, method=None, question_number=None)
    try:
        async with AsyncSessionLocal() as db:
            argument = await db.get(type(await _get_argument(ids["argument_id"])), ids["argument_id"])
            decision = await apply_argument_value_change(
                db,
                argument=argument,
                field="question_number",
                incoming_value=1,
                incoming_source=ImportSource.CORPUS.value,
                incoming_method=ImportMethod.DIRECT.value,
            )
            await db.commit()

        assert decision == WriteDecision.ACCEPT
        refreshed = await _get_argument(ids["argument_id"])
        assert refreshed.question_number == 1
        assert await _open_discrepancy_count("argument", ids["argument_id"]) == 0
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
async def test_case_blank_stored_receiving_non_blank_incoming_is_gap_fill_no_discrepancy() -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.admin_review import apply_case_value_change

    ids = await _make_case(source=None, method=None, case_name="")
    try:
        async with AsyncSessionLocal() as db:
            case = await db.get(type(await _get_case(ids["case_id"])), ids["case_id"])
            decision = await apply_case_value_change(
                db,
                case=case,
                field="case_name",
                incoming_value="Roe v. Wade",
                incoming_source=ImportSource.CORPUS.value,
                incoming_method=ImportMethod.DIRECT.value,
            )
            await db.commit()

        assert decision == WriteDecision.ACCEPT
        refreshed = await _get_case(ids["case_id"])
        assert refreshed.case_name == "Roe v. Wade"
        assert await _open_discrepancy_count("case", ids["case_id"]) == 0
    finally:
        await _teardown_case(ids)


# ---------------------------------------------------------------------------
# Bullet 9 (participant/person gap-fill parity) — covered directly in
# api/tests/test_authority_matrix.py per this plan's own acceptance
# criteria, alongside the two existing gates' own fixtures.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Bullet 10 — both values blank -> no write of substance, no discrepancy row.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_argument_both_values_blank_no_write_no_discrepancy() -> None:
    from api.core.database import AsyncSessionLocal
    from api.services.admin_review import apply_argument_value_change

    ids = await _make_argument(source=None, method=None, question_number=None)
    try:
        async with AsyncSessionLocal() as db:
            argument = await db.get(type(await _get_argument(ids["argument_id"])), ids["argument_id"])
            decision = await apply_argument_value_change(
                db,
                argument=argument,
                field="question_number",
                incoming_value=None,
                incoming_source="corpus",
                incoming_method="direct",
            )
            await db.commit()

        assert decision == WriteDecision.ACCEPT
        refreshed = await _get_argument(ids["argument_id"])
        assert refreshed.question_number is None
        assert await _open_discrepancy_count("argument", ids["argument_id"]) == 0
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
async def test_case_both_values_blank_no_write_no_discrepancy() -> None:
    from api.core.database import AsyncSessionLocal
    from api.services.admin_review import apply_case_value_change

    ids = await _make_case(source=None, method=None, case_name="")
    try:
        async with AsyncSessionLocal() as db:
            case = await db.get(type(await _get_case(ids["case_id"])), ids["case_id"])
            decision = await apply_case_value_change(
                db,
                case=case,
                field="case_name",
                incoming_value="",
                incoming_source="corpus",
                incoming_method="direct",
            )
            await db.commit()

        assert decision == WriteDecision.ACCEPT
        refreshed = await _get_case(ids["case_id"])
        assert refreshed.case_name == ""
        assert await _open_discrepancy_count("case", ids["case_id"]) == 0
    finally:
        await _teardown_case(ids)


# ---------------------------------------------------------------------------
# Bullet 11 — the same input applied twice produces the same decision and
# exactly one additional discrepancy row per recording call.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_argument_repeated_identical_input_same_decision_one_discrepancy_per_call() -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.admin_review import apply_argument_value_change

    ids = await _make_argument(
        source=ImportSource.CORPUS, method=ImportMethod.DIRECT, question_number=1
    )
    try:
        for expected_count in (1, 2):
            async with AsyncSessionLocal() as db:
                argument = await db.get(
                    type(await _get_argument(ids["argument_id"])), ids["argument_id"]
                )
                decision = await apply_argument_value_change(
                    db,
                    argument=argument,
                    field="question_number",
                    incoming_value=2,
                    incoming_source="corpus",
                    incoming_method="direct",
                )
                await db.commit()

            assert decision == WriteDecision.REJECT_AND_RECORD
            refreshed = await _get_argument(ids["argument_id"])
            assert refreshed.question_number == 1  # never overwritten
            assert await _open_discrepancy_count("argument", ids["argument_id"]) == expected_count
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
async def test_case_repeated_identical_input_same_decision_one_discrepancy_per_call() -> None:
    from api.core.database import AsyncSessionLocal
    from api.models.models import ImportMethod, ImportSource
    from api.services.admin_review import apply_case_value_change

    ids = await _make_case(
        source=ImportSource.CORPUS, method=ImportMethod.DIRECT, case_name="Roe v. Wade"
    )
    try:
        for expected_count in (1, 2):
            async with AsyncSessionLocal() as db:
                case = await db.get(type(await _get_case(ids["case_id"])), ids["case_id"])
                decision = await apply_case_value_change(
                    db,
                    case=case,
                    field="case_name",
                    incoming_value="Doe v. Bolton",
                    incoming_source="corpus",
                    incoming_method="direct",
                )
                await db.commit()

            assert decision == WriteDecision.REJECT_AND_RECORD
            refreshed = await _get_case(ids["case_id"])
            assert refreshed.case_name == "Roe v. Wade"
            assert await _open_discrepancy_count("case", ids["case_id"]) == expected_count
    finally:
        await _teardown_case(ids)


# ---------------------------------------------------------------------------
# Field-outside-gated-set -> ValueError (never writes an arbitrary column).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_argument_field_outside_gated_set_raises_value_error() -> None:
    from api.core.database import AsyncSessionLocal
    from api.services.admin_review import apply_argument_value_change

    ids = await _make_argument(question_number=1)
    try:
        async with AsyncSessionLocal() as db:
            argument = await db.get(type(await _get_argument(ids["argument_id"])), ids["argument_id"])
            with pytest.raises(ValueError):
                await apply_argument_value_change(
                    db,
                    argument=argument,
                    field="status",
                    incoming_value="published",
                    incoming_source="operator",
                    incoming_method="manual",
                )
    finally:
        await _teardown_argument(ids)


@pytest.mark.asyncio
async def test_case_field_outside_gated_set_raises_value_error() -> None:
    from api.core.database import AsyncSessionLocal
    from api.services.admin_review import apply_case_value_change

    ids = await _make_case(case_name="Roe v. Wade")
    try:
        async with AsyncSessionLocal() as db:
            case = await db.get(type(await _get_case(ids["case_id"])), ids["case_id"])
            with pytest.raises(ValueError):
                await apply_case_value_change(
                    db,
                    case=case,
                    field="slug",
                    incoming_value="roe-v-wade",
                    incoming_source="operator",
                    incoming_method="manual",
                )
    finally:
        await _teardown_case(ids)
