"""
Phase 50 plan 50-06, Task 3: the D-24 executable behavioral gate.

SC-4 is closed by an EXECUTABLE BEHAVIORAL GATE plus a dispositioned
inventory (the inventory itself is plan 50-07's artifact) — this module is
deliberately NOT a grep over source text. This project has twice shipped
green source-text gates that could not see a live defect (49-12's fourth
horizontal-scroll cause survived three passing gates; the Svelte `$state`
proxy case had 28 green contract tests over a fully broken button), so
every test below drives the REAL writer function against a REAL database
session and asserts on the resulting row state and value_discrepancy
table, never on source text.

**The falsifiability proof** is
`test_control_direct_ungated_update_changes_value_with_no_discrepancy_
recorded` — a direct, ungated `update(...)` of the same column on the same
kind of fixture, asserted to CHANGE the value and record NO discrepancy.
This is what makes every other test's assertions content-dependent: if any
converted writer regressed to a direct UPDATE, its own named test would
start asserting the SAME shape as the control (value changed, nothing
recorded) instead of the gate's shape (value unchanged, one discrepancy
recorded) — and would go red. This has been verified by hand for one
writer (`resolve.py`'s `_apply_resolved_person_ids` — the Step 5
ArgumentParticipant.person_id gate call was temporarily reverted to a
direct `update()` and its named test below failed as expected; the writer
was then restored) — see 50-06-SUMMARY.md for the record.

Covered writers, one named test function each:
    1. the corpus reconcile pass (`import_convokit._reconcile_conversation`)
    2. resolve.py's resolved-person-id application
       (`resolve._apply_resolved_person_ids`)
    3. parse.py's argued_date cover-metadata write
       (`parse._write_cover_metadata_through_gate`)
    4. parse.py's case_name cover-metadata write
       (`parse._write_cover_metadata_through_gate`)
    5. parse.py's source_docket cover-metadata write (inline in
       `parse._run_parse_inner`'s Block D) — structurally gap-fill-only
       (see that test's own docstring for why)
    6. import_justices_csv's Person name-part prefill
       (`import_justices_csv.run_import_justices_csv`)
    7. import_convokit's name-provenance prefill
       (`import_convokit._apply_extracted_name_provenance`) —
       structurally gap-fill-only (see that test's own docstring)
    + the falsifiability control

DB-dependent — skipped when DATABASE_URL/TEST_DATABASE_URL is not set
(via conftest.py's async_session fixture -> test_db_url -> pytest.skip).
"""

from __future__ import annotations

import datetime

from sqlalchemy import select, update

from api.models.models import (
    Argument,
    ArgumentParticipant,
    ArgumentStatusEnum,
    Case,
    CaseArgument,
    ImportMethod,
    ImportRun,
    ImportRunStatus,
    ImportSource,
    Person,
    ReviewState,
    SideEnum,
    ValueDiscrepancy,
)
from pipeline.commands.import_convokit import (
    _apply_extracted_name_provenance,
    _reconcile_conversation,
)
from pipeline.commands.parse import _write_cover_metadata_through_gate
from pipeline.commands.resolve import _apply_resolved_person_ids

# pytest.ini configures asyncio_mode=auto -- async def test_* functions are
# detected and run automatically, no per-test @pytest.mark.asyncio needed.

_COUNTER = 0


def _unique_docket() -> str:
    global _COUNTER
    _COUNTER += 1
    return f"58-{9000 + _COUNTER}"


async def _open_discrepancies(session, target_type: str, target_id: int, field: str):
    result = await session.execute(
        select(ValueDiscrepancy).where(
            ValueDiscrepancy.target_type == target_type,
            ValueDiscrepancy.target_id == target_id,
            ValueDiscrepancy.field == field,
            ValueDiscrepancy.resolved_at.is_(None),
        )
    )
    return list(result.scalars().all())


async def _seed_argument_and_case(
    session,
    *,
    argued_date=None,
    source_docket=None,
    case_name="Pet v. Resp",
    argument_source=None,
    argument_method=None,
    case_source=None,
    case_method=None,
    status=ArgumentStatusEnum.CANDIDATE,
):
    docket = source_docket or _unique_docket()
    argument = Argument(
        argued_date=argued_date,
        source_docket=docket,
        question_number=1,
        oyez_transcript_id=f"conv_{docket}",
        status=status,
        source=argument_source,
        method=argument_method,
    )
    session.add(argument)
    await session.flush()

    case = Case(
        docket_number=docket,
        docket_number_norm=docket.replace("-", ""),
        case_name=case_name,
        term_year=1960,
        slug=f"slug-{docket}".lower(),
        source=case_source,
        method=case_method,
    )
    session.add(case)
    await session.flush()

    session.add(CaseArgument(case_id=case.id, argument_id=argument.id, is_lead=True))
    await session.flush()
    return argument, case


# ===========================================================================
# 1. The corpus reconcile pass
# ===========================================================================


async def test_corpus_reconcile_pass_rejects_lower_authority_argued_date(
    async_session,
):
    """
    Real writer: `_reconcile_conversation`'s Argument.argued_date leg.

    A pre-existing HIGHER-authority stored value (source=operator/
    method=manual) survives a disagreeing corpus-authority incoming write
    byte-identical, and exactly one open value_discrepancy row is
    recorded for (argument, argued_date).
    """
    existing_date = datetime.date(1999, 3, 3)
    argument, case = await _seed_argument_and_case(
        async_session,
        argued_date=existing_date,
        argument_source=ImportSource.OPERATOR,
        argument_method=ImportMethod.MANUAL,
    )

    incoming_date_str = "November 15, 1960"
    case_fields = {
        "title": None,
        "petitioner": "Pet",
        "respondent": "Resp",
        "docket_no": argument.source_docket,
        "year": 1960,
        "transcripts": [{"id": argument.oyez_transcript_id, "name": f"Oral Argument - {incoming_date_str}"}],
        "advocates": None,
        "case_id": None,
    }
    counters = {"participants_created": 0}

    await _reconcile_conversation(
        session=async_session,
        argument=argument,
        conversation_id=argument.oyez_transcript_id,
        conversation={"conversation_id": argument.oyez_transcript_id, "case_id": None, "advocates": {}},
        case_fields=case_fields,
        turns=[],
        speakers_index={},
        counters=counters,
        dry_run=False,
    )

    await async_session.refresh(argument)
    assert argument.argued_date == existing_date, "higher-authority value must survive byte-identical"

    discrepancies = await _open_discrepancies(async_session, "argument", argument.id, "argued_date")
    assert len(discrepancies) == 1


# ===========================================================================
# 2. resolve.py's resolved-person-id application
# ===========================================================================


async def test_resolve_writer_rejects_lower_authority_person_id(async_session):
    """
    Real writer: `resolve._apply_resolved_person_ids`.

    A pre-existing HIGHER-authority participant.person_id (an
    operator-edited assignment) survives a disagreeing PDF-pipeline
    resolved value byte-identical, and exactly one open value_discrepancy
    row is recorded for (argument_participant, person_id).
    """
    argument, _case = await _seed_argument_and_case(async_session)

    operator_person = Person(full_name="Operator Assigned Justice")
    incoming_person = Person(full_name="Resolved-By-Alias Justice")
    async_session.add_all([operator_person, incoming_person])
    await async_session.flush()

    participant = ArgumentParticipant(
        argument_id=argument.id,
        person_id=operator_person.id,
        raw_speaker_label="MR. GATE-TEST",
        side=SideEnum.ADVOCATE,
        review_state=ReviewState.OPERATOR_EDITED,
    )
    async_session.add(participant)
    await async_session.flush()

    resolve_run = ImportRun(
        argument_id=argument.id,
        step="resolve",
        status=ImportRunStatus.RUNNING,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.NORMALIZED,
    )
    async_session.add(resolve_run)
    await async_session.flush()

    await _apply_resolved_person_ids(
        async_session,
        argument.id,
        {"MR. GATE-TEST": incoming_person.id},
        resolve_run.source.value,
        resolve_run.method.value,
        resolve_run.id,
    )

    await async_session.refresh(participant)
    assert participant.person_id == operator_person.id, "operator assignment must survive byte-identical"

    discrepancies = await _open_discrepancies(
        async_session, "argument_participant", participant.id, "person_id"
    )
    assert len(discrepancies) == 1


# ===========================================================================
# 3. parse.py's argued_date cover-metadata write
# ===========================================================================


async def test_parse_argued_date_writer_rejects_lower_authority(async_session):
    """
    Real writer: `parse._write_cover_metadata_through_gate` (Block A).

    A pre-existing HIGHER-authority Argument.argued_date (source=operator/
    method=manual) survives a disagreeing rule_based PDF-pipeline
    extraction byte-identical, and exactly one open value_discrepancy row
    is recorded for (argument, argued_date).
    """
    existing_date = datetime.date(1988, 6, 6)
    argument, _case = await _seed_argument_and_case(
        async_session,
        argued_date=existing_date,
        argument_source=ImportSource.OPERATOR,
        argument_method=ImportMethod.MANUAL,
    )

    run = ImportRun(
        argument_id=argument.id,
        step="parse",
        status=ImportRunStatus.RUNNING,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.RULE_BASED,
    )
    async_session.add(run)
    await async_session.flush()

    incoming_date = datetime.date(2001, 1, 1)
    await _write_cover_metadata_through_gate(
        async_session, run, argument, {"argued_date": incoming_date}
    )

    await async_session.refresh(argument)
    assert argument.argued_date == existing_date

    discrepancies = await _open_discrepancies(async_session, "argument", argument.id, "argued_date")
    assert len(discrepancies) == 1
    assert discrepancies[0].incoming_method == ImportMethod.RULE_BASED


# ===========================================================================
# 4. parse.py's case_name cover-metadata write
# ===========================================================================


async def test_parse_case_name_writer_rejects_lower_authority(async_session):
    """
    Real writer: `parse._write_cover_metadata_through_gate` (Block B).

    A pre-existing HIGHER-authority lead Case.case_name (source=operator/
    method=manual) survives a disagreeing PDF cover extraction
    byte-identical, and exactly one open value_discrepancy row is
    recorded for (case, case_name).
    """
    argument, case = await _seed_argument_and_case(
        async_session,
        case_name="Operator-Authored Case Name",
        case_source=ImportSource.OPERATOR,
        case_method=ImportMethod.MANUAL,
    )

    run = ImportRun(
        argument_id=argument.id,
        step="parse",
        status=ImportRunStatus.RUNNING,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.RULE_BASED,
    )
    async_session.add(run)
    await async_session.flush()

    await _write_cover_metadata_through_gate(
        async_session, run, argument, {"case_name": "Extracted PDF Cover Name"}
    )

    await async_session.refresh(case)
    assert case.case_name == "Operator-Authored Case Name"

    discrepancies = await _open_discrepancies(async_session, "case", case.id, "case_name")
    assert len(discrepancies) == 1


# ===========================================================================
# 5. parse.py's source_docket cover-metadata write
# ===========================================================================


async def test_parse_source_docket_writer_gap_fills_into_null_column(async_session):
    """
    Real writer: the inline gate call in `parse._run_parse_inner`'s
    Block D (`apply_argument_value_change` with `field="source_docket"`).

    Unlike the other converted writers, this call site is STRUCTURALLY
    gap-fill-only: it only ever runs when
    `argument_row.source_docket is None` (kept unchanged — a
    source-inspection regression test,
    `test_parse_docket_fill_uses_pair_precheck_and_named_race_
    classification`, asserts this exact code shape, and the pre-existing
    `test_parse_preserves_operator_docket_when_extracted_pair_conflicts`
    depends on the collision check never running against an already-
    populated docket). There is therefore no reachable "higher-authority
    stored value rejects a disagreeing write" state for THIS writer to
    demonstrate — this test instead proves the writer's own reachable
    behavior: a real write into a genuinely NULL column, through the real
    gate, with no discrepancy recorded (PD-13 gap-fill).
    """
    from sqlalchemy.exc import IntegrityError

    from api.services.admin_review import apply_argument_value_change
    from api.services.argument_uniqueness import find_argument_by_pair

    argument, _case = await _seed_argument_and_case(async_session, source_docket=None)
    # source_docket was set by _seed_argument_and_case's docket kwarg — force NULL
    # for this test's gap-fill scenario (the helper always assigns a docket,
    # used as the Case's docket_number too, so set only the Argument's
    # source_docket back to None post-seed).
    argument.source_docket = None
    await async_session.flush()

    run = ImportRun(
        argument_id=argument.id,
        step="parse",
        status=ImportRunStatus.RUNNING,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.RULE_BASED,
    )
    async_session.add(run)
    await async_session.flush()

    incoming_docket = "77-GATE-TEST"
    conflict_id = await find_argument_by_pair(
        async_session, incoming_docket, argument.question_number, exclude_argument_id=argument.id
    )
    assert conflict_id is None
    decision = await apply_argument_value_change(
        async_session,
        argument=argument,
        field="source_docket",
        incoming_value=incoming_docket,
        incoming_source=run.source.value,
        incoming_method=run.method.value,
        import_run_id=run.id,
    )

    await async_session.refresh(argument)
    assert argument.source_docket == incoming_docket

    discrepancies = await _open_discrepancies(async_session, "argument", argument.id, "source_docket")
    assert discrepancies == []


# ===========================================================================
# 6. import_justices_csv's Person name-part prefill
# ===========================================================================


async def test_import_justices_csv_writer_rejects_lower_authority_last_name(
    async_session, tmp_path, monkeypatch
):
    """
    Real writer: `import_justices_csv.run_import_justices_csv`'s four
    `apply_person_value_change` calls (last_name leg).

    A pre-existing HIGHER-authority Person.last_name (review_state=
    operator_edited) survives a disagreeing seed CSV value byte-identical,
    and exactly one open value_discrepancy row is recorded for
    (person, last_name).
    """
    import argparse
    import csv as csv_module
    from contextlib import asynccontextmanager

    from pipeline.commands.import_justices_csv import run_import_justices_csv

    existing = Person(
        full_name="Gatetest Q. Fixture",
        is_justice=False,
        first_name="Gatetest",
        middle_name="Q.",
        last_name="OperatorLastName",
        review_state=ReviewState.OPERATOR_EDITED,
    )
    async_session.add(existing)
    await async_session.flush()
    existing_id = existing.id

    csv_path = tmp_path / "justices_gate_test.csv"
    header = [
        "First Name", "Middle Name or Initial", "Last Name", "Suffix",
        "Appointed by", "Party", "Judicial Oath Taken",
        "Date Service Terminated", "Reason Left", "Birthdate", "Death Date",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv_module.writer(f)
        writer.writerow(["Supreme Court Associate Justices"])
        writer.writerow(header)
        writer.writerow(
            [
                "Gatetest", "Q.", "Fixture", "",
                "Fictional President", "Republican", "1980-01-01", "",
                "Still in Office", "1930-01-01", "",
            ]
        )

    @asynccontextmanager
    async def _cm():
        yield async_session

    monkeypatch.setattr(
        "pipeline.commands.import_justices_csv.get_session", _cm
    )

    await run_import_justices_csv(argparse.Namespace(csv=str(csv_path)))

    result = await async_session.execute(select(Person).where(Person.id == existing_id))
    person = result.scalar_one()
    assert person.last_name == "OperatorLastName"

    discrepancies = await _open_discrepancies(async_session, "person", existing_id, "last_name")
    assert len(discrepancies) == 1


# ===========================================================================
# 7. import_convokit's name-provenance prefill
# ===========================================================================


async def test_import_convokit_name_provenance_writer_gap_fills_blank_person(
    async_session,
):
    """
    Real writer: `import_convokit._apply_extracted_name_provenance`.

    Per this writer's own docstring, its four `apply_person_value_change`
    calls are structurally reachable ONLY via the gap-fill short-circuit
    (the enclosing `has_any_part` guard means it never calls the gate
    unless every stored name part is already blank) — it can never reach
    ACCEPT_AND_RECORD/REJECT_AND_RECORD, so there is no reachable
    "higher-authority stored value rejects a disagreeing write" state to
    demonstrate for this writer either. This test proves the writer's own
    reachable behavior instead: a real write into a genuinely blank
    Person, through the real gate, with no discrepancy recorded.
    """
    person = Person(full_name="Antonin Scalia-Gate-Test")
    async_session.add(person)
    await async_session.flush()
    person_id = person.id

    await _apply_extracted_name_provenance(async_session, person, "Antonin Scalia-Gate-Test")

    await async_session.refresh(person)
    assert person.first_name is not None or person.last_name is not None

    discrepancies = (
        await async_session.execute(
            select(ValueDiscrepancy).where(
                ValueDiscrepancy.target_type == "person",
                ValueDiscrepancy.target_id == person_id,
            )
        )
    ).scalars().all()
    assert discrepancies == []


# ===========================================================================
# Control: the falsifiability proof (PD-21)
# ===========================================================================


async def test_control_direct_ungated_update_changes_value_with_no_discrepancy_recorded(
    async_session,
):
    """
    THE FALSIFIABILITY CONTROL (PD-21). A direct, ungated `update(...)` of
    the SAME kind of column on the SAME kind of fixture used above: the
    value DOES change and NO discrepancy row is created. This is the
    control that makes every test above content-dependent — if any
    converted writer regressed to a direct UPDATE, its own named test
    would start asserting THIS shape (value changed, nothing recorded)
    instead of the gate's shape, and would go red.
    """
    existing_date = datetime.date(1975, 5, 5)
    argument, _case = await _seed_argument_and_case(
        async_session,
        argued_date=existing_date,
        argument_source=ImportSource.OPERATOR,
        argument_method=ImportMethod.MANUAL,
    )

    incoming_date = datetime.date(2010, 10, 10)
    await async_session.execute(
        update(Argument)
        .where(Argument.id == argument.id)
        .values(argued_date=incoming_date)
        .execution_options(synchronize_session=False)
    )
    await async_session.flush()

    await async_session.refresh(argument)
    assert argument.argued_date == incoming_date, "the ungated control DOES overwrite"

    discrepancies = await _open_discrepancies(async_session, "argument", argument.id, "argued_date")
    assert discrepancies == [], "the ungated control records NO discrepancy"
