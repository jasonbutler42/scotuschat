"""
Phase 50 plan 50-05: the real compare-and-record reconcile pass.

Covers every `<behavior>` bullet across the plan's three tasks:
    - Task 1: the D-02 field walk (Argument/Case/ArgumentParticipant/
      Person), D-04 pairing, D-07 restamp, D-08 published freeze, D-06's
      lazy reconcile run.
    - Task 2: D-10/D-11/D-13 whole-set utterance replacement under a new
      step="parse" run.
    - Task 3: --dry-run prediction and the five new PD-17 batch counters.

Most tests call `_reconcile_conversation` DIRECTLY against hand-seeded
Argument/Case/ArgumentParticipant/Person rows (never through
`run_import_convokit`'s corpus-file-loading layer) for fine-grained
authority-ladder control -- this file never patches `get_session`, so it
uses the shared `async_session` fixture (rollback-isolated) directly, the
same way `_reconcile_conversation` itself never commits (D-30 leaves that
to the caller). A handful of tests exercise the full
`run_import_convokit` entry point via the synthetic tmp_path corpus-tree
convention `test_import_convokit_utterances.py` established, patching
`get_session` the same way `test_import_convokit_reimport_tracer.py`
does via `isolated_session`.

DB-dependent tests are skipped when DATABASE_URL/TEST_DATABASE_URL is not
set (via conftest.py's test_db_url fixture -> pytest.skip).
"""

from __future__ import annotations

import inspect
import json
import re
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import select

from api.domain.authority import WriteDecision
from api.domain.content_digest import compute_utterance_digest
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
    Utterance,
    ValueDiscrepancy,
)
from api.services.arguments import get_argument_with_utterances
from pipeline.commands import import_convokit as import_convokit_module
from pipeline.commands.import_convokit import (
    _apply_extracted_name_provenance,
    _ensure_reconcile_run,
    _incoming_utterance_rows,
    _pair_participants_by_speaker_id,
    _predict_reconcile,
    _reconcile_conversation,
    _ReconcileContext,
    _replace_utterance_set,
    run_import_convokit,
)

# pytest.ini configures asyncio_mode=auto -- async def test_* functions are
# detected and run automatically, no per-test @pytest.mark.asyncio needed
# (and a module-level pytestmark would incorrectly also tag this file's
# several structural/source-inspection sync tests).

# ===========================================================================
# Shared fixtures / helpers
# ===========================================================================

_COUNTER = 0


def _unique_docket() -> str:
    """A fresh, collision-free docket string per call within this module's
    test session (each test's DB writes are rolled back at teardown, but
    within a single test several helpers may need distinct dockets)."""
    global _COUNTER
    _COUNTER += 1
    return f"55-{9000 + _COUNTER}"


async def _seed_argument(
    session,
    *,
    docket: str | None = None,
    question_number: int | None = 1,
    argued_date=None,
    source: ImportSource | None = ImportSource.CORPUS,
    method: ImportMethod | None = ImportMethod.DIRECT,
    status: ArgumentStatusEnum = ArgumentStatusEnum.CANDIDATE,
    # Matches _case_fields()'s own default derivation ("Pet v. Resp", from
    # its default petitioner="Pet"/respondent="Resp" with no title) so a
    # test that seeds an argument and reconciles with the default
    # case_fields() sees a genuine no-op on case_name, not a spurious
    # rejection from a fixture-default mismatch.
    case_name: str = "Pet v. Resp",
    case_docket: str | None = None,
    case_source: ImportSource | None = ImportSource.CORPUS,
    case_method: ImportMethod | None = ImportMethod.DIRECT,
) -> tuple[Argument, Case]:
    """Seed one Argument + its LEAD Case (via CaseArgument), returning both.
    No participants, no utterances -- callers add those separately."""
    docket = docket or _unique_docket()
    case_docket = case_docket or docket
    argument = Argument(
        argued_date=argued_date,
        question_number=question_number,
        source_docket=docket,
        status=status,
        oyez_transcript_id=f"conv_{docket}",
        source=source,
        method=method,
    )
    session.add(argument)
    await session.flush()

    case = Case(
        docket_number=case_docket,
        docket_number_norm=case_docket.replace("-", ""),
        case_name=case_name,
        term_year=1955,
        slug=f"slug-{docket}-{case_name}".lower().replace(" ", "-").replace(".", ""),
        source=case_source,
        method=case_method,
    )
    session.add(case)
    await session.flush()

    session.add(CaseArgument(case_id=case.id, argument_id=argument.id, is_lead=True))
    await session.flush()
    return argument, case


async def _seed_parse_run(session, argument: Argument, rows: list[dict] | None = None) -> ImportRun:
    """Seed a step="parse"/COMPLETED ImportRun whose content_digest matches
    `rows` (default: empty -- the digest of zero utterances). Any test
    that doesn't care about Task 2's utterance-replacement branch should
    call this with rows matching the `turns` it passes to
    `_reconcile_conversation`, so the digest compares EQUAL and the
    utterance section resolves to "unchanged" without side effects."""
    rows = rows if rows is not None else []
    run = ImportRun(
        argument_id=argument.id,
        step="parse",
        status=ImportRunStatus.COMPLETED,
        source=ImportSource.CORPUS,
        method=ImportMethod.DIRECT,
        external_id=argument.oyez_transcript_id,
        content_digest=compute_utterance_digest(rows),
    )
    session.add(run)
    await session.flush()
    return run


async def _seed_person(
    session,
    *,
    full_name: str,
    oyez_speaker_id: str | None = None,
    is_justice: bool = False,
    review_state: ReviewState = ReviewState.UNREVIEWED,
) -> Person:
    person = Person(
        full_name=full_name,
        oyez_speaker_id=oyez_speaker_id,
        is_justice=is_justice,
        review_state=review_state,
    )
    session.add(person)
    await session.flush()
    return person


async def _seed_participant(
    session,
    argument: Argument,
    *,
    raw_speaker_label: str,
    oyez_speaker_id: str | None,
    person: Person | None,
    side: SideEnum = SideEnum.ADVOCATE,
    descriptor: str | None = None,
    source: ImportSource | None = ImportSource.CORPUS,
    method: ImportMethod | None = ImportMethod.DIRECT,
    review_state: ReviewState = ReviewState.UNREVIEWED,
) -> ArgumentParticipant:
    participant = ArgumentParticipant(
        argument_id=argument.id,
        person_id=person.id if person else None,
        raw_speaker_label=raw_speaker_label,
        side=side,
        descriptor=descriptor,
        source=source,
        method=method,
        review_state=review_state,
        oyez_speaker_id=oyez_speaker_id,
    )
    session.add(participant)
    await session.flush()
    return participant


def _case_fields(docket_no: str, *, date_str: str = "November 15, 1955", title: str | None = None) -> dict:
    return {
        "title": title,
        "petitioner": "Pet",
        "respondent": "Resp",
        "docket_no": docket_no,
        "year": 1955,
        "transcripts": [{"name": f"Oral Argument - {date_str}"}],
        "advocates": None,
        "case_id": None,
    }


def _conversation(advocates: dict | None = None) -> dict:
    return {"conversation_id": None, "case_id": None, "advocates": advocates or {}}


async def _reconcile(
    session,
    argument,
    *,
    conversation=None,
    case_fields=None,
    turns=None,
    speakers_index=None,
    counters=None,
    dry_run=False,
):
    # participants_created uses a bare `+=` (no .get default) in
    # _resolve_and_link_participant's new-participant branch -- match
    # _new_counters()'s own base-dict convention so a direct-caller test
    # (bypassing run_import_convokit's _new_counters()) never KeyErrors.
    counters = counters if counters is not None else {"participants_created": 0}
    counters.setdefault("participants_created", 0)
    await _reconcile_conversation(
        session=session,
        argument=argument,
        conversation_id=argument.oyez_transcript_id,
        conversation=conversation or _conversation(),
        case_fields=case_fields or _case_fields(argument.source_docket),
        turns=turns or [],
        speakers_index=speakers_index or {},
        counters=counters,
        dry_run=dry_run,
    )
    return counters


async def _open_discrepancies(session, target_type: str, target_id: int) -> list[ValueDiscrepancy]:
    result = await session.execute(
        select(ValueDiscrepancy).where(
            ValueDiscrepancy.target_type == target_type,
            ValueDiscrepancy.target_id == target_id,
            ValueDiscrepancy.resolved_at.is_(None),
        )
    )
    return list(result.scalars().all())


async def _reconcile_run_count(session, argument_id: int) -> int:
    result = await session.execute(
        select(ImportRun).where(
            ImportRun.argument_id == argument_id, ImportRun.step == "reconcile"
        )
    )
    return len(result.scalars().all())


# ===========================================================================
# Task 1: the D-02 compare-and-record field walk
# ===========================================================================


async def test_identical_reimport_every_field_accept_or_no_opinion_zero_rows(async_session):
    argument, case = await _seed_argument(async_session, argued_date=None)
    await _seed_parse_run(async_session, argument)

    case_fields = _case_fields(argument.source_docket, date_str="November 15, 1955")
    # Make the seeded argued_date match what _parse_argued_date derives so
    # this is a genuine byte-identical pass (not a gap-fill).
    from pipeline.commands.import_convokit import _parse_argued_date

    derived_date = _parse_argued_date(case_fields, argument.oyez_transcript_id)
    argument.argued_date = derived_date
    case.case_name = case_fields.get("title") or "Pet v. Resp"
    await async_session.flush()

    counters = await _reconcile(async_session, argument, case_fields=case_fields)

    assert (await _open_discrepancies(async_session, "argument", argument.id)) == []
    assert (await _open_discrepancies(async_session, "case", case.id)) == []
    assert await _reconcile_run_count(async_session, argument.id) == 0
    assert counters.get("discrepancies_recorded", 0) == 0
    assert counters.get("values_rejected", 0) == 0


async def test_corpus_value_differing_from_stored_corpus_value_rejected_and_recorded(
    async_session,
):
    argument, _case = await _seed_argument(
        async_session,
        argued_date=None,
        source=ImportSource.CORPUS,
        method=ImportMethod.DIRECT,
    )
    await _seed_parse_run(async_session, argument)
    argument.source_docket = "55-0001"
    await async_session.flush()

    case_fields = _case_fields(argument.source_docket)
    case_fields["docket_no"] = "55-9999"  # incoming disagrees

    counters = await _reconcile(async_session, argument, case_fields=case_fields)

    await async_session.refresh(argument)
    assert argument.source_docket == "55-0001"  # unchanged -- rejected
    discrepancies = await _open_discrepancies(async_session, "argument", argument.id)
    matching = [d for d in discrepancies if d.field == "source_docket"]
    assert len(matching) == 1
    assert counters["values_rejected"] >= 1
    assert counters["discrepancies_recorded"] >= 1


async def test_corpus_value_differing_from_pdf_pipeline_value_accepted_and_restamped(
    async_session,
):
    argument, _case = await _seed_argument(
        async_session,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.RULE_BASED,
    )
    await _seed_parse_run(async_session, argument)
    old_docket = argument.source_docket
    await async_session.flush()

    case_fields = _case_fields(old_docket)
    case_fields["docket_no"] = "55-8888"

    counters = await _reconcile(async_session, argument, case_fields=case_fields)

    await async_session.refresh(argument)
    assert argument.source_docket == "55-8888"
    assert argument.source == ImportSource.CORPUS  # D-07 unconditional restamp
    assert argument.method == ImportMethod.DIRECT
    discrepancies = await _open_discrepancies(async_session, "argument", argument.id)
    assert any(d.field == "source_docket" for d in discrepancies)
    assert counters["values_accepted"] >= 1


async def test_operator_edited_participant_value_survives_reimport(async_session):
    argument, _case = await _seed_argument(async_session)
    await _seed_parse_run(async_session, argument)
    original_person = await _seed_person(async_session, full_name="Original Person")
    reassigned_person = await _seed_person(
        async_session, full_name="Reassigned Person", oyez_speaker_id="adv__x"
    )
    participant = await _seed_participant(
        async_session,
        argument,
        raw_speaker_label="Pat Advocate",
        oyez_speaker_id="adv__x",
        person=original_person,
        review_state=ReviewState.OPERATOR_EDITED,
    )

    speakers_index = {"adv__x": {"name": "Pat Advocate", "type": "advocate"}}
    conversation = _conversation({"adv__x": {"side": 1}})

    counters = await _reconcile(
        async_session,
        argument,
        conversation=conversation,
        speakers_index=speakers_index,
    )

    await async_session.refresh(participant)
    assert participant.person_id == original_person.id  # operator value survives
    assert participant.review_state == ReviewState.OPERATOR_EDITED
    discrepancies = await _open_discrepancies(
        async_session, "argument_participant", participant.id
    )
    assert any(d.field == "person_id" for d in discrepancies)
    assert counters["values_rejected"] >= 1


async def test_operator_stamped_argued_date_survives_reimport(async_session):
    from datetime import date

    argument, _case = await _seed_argument(
        async_session,
        argued_date=date(1960, 1, 1),
        source=ImportSource.OPERATOR,
        method=ImportMethod.MANUAL,
    )
    await _seed_parse_run(async_session, argument)

    counters = await _reconcile(async_session, argument)  # default case_fields -> Nov 15 1955

    await async_session.refresh(argument)
    assert argument.argued_date == date(1960, 1, 1)  # operator value survives
    discrepancies = await _open_discrepancies(async_session, "argument", argument.id)
    assert any(d.field == "argued_date" for d in discrepancies)
    assert counters["values_rejected"] >= 1


async def test_accepted_participant_overwrite_leaves_review_state_unchanged(async_session):
    argument, _case = await _seed_argument(async_session)
    await _seed_parse_run(async_session, argument)
    old_person = await _seed_person(async_session, full_name="Old Person")
    new_person = await _seed_person(
        async_session, full_name="New Person", oyez_speaker_id="adv__y"
    )
    participant = await _seed_participant(
        async_session,
        argument,
        raw_speaker_label="Pat Advocate",
        oyez_speaker_id="adv__y",
        person=old_person,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.RULE_BASED,
        review_state=ReviewState.UNREVIEWED,
    )

    speakers_index = {"adv__y": {"name": "Pat Advocate", "type": "advocate"}}
    conversation = _conversation({"adv__y": {"side": 1}})

    await _reconcile(async_session, argument, conversation=conversation, speakers_index=speakers_index)

    await async_session.refresh(participant)
    assert participant.person_id == new_person.id  # accepted (corpus outranks pdf_pipeline)
    assert participant.review_state == ReviewState.UNREVIEWED  # never flipped (D-07)
    assert participant.source == ImportSource.CORPUS
    assert participant.method == ImportMethod.DIRECT


async def test_participant_paired_by_oyez_speaker_id_never_raw_label(async_session):
    argument, _case = await _seed_argument(async_session)
    await _seed_parse_run(async_session, argument)
    stale_person = await _seed_person(async_session, full_name="Stale Person")
    # Same raw_speaker_label the corpus will derive, but a DIFFERENT
    # oyez_speaker_id -- must NOT be paired.
    stale_participant = await _seed_participant(
        async_session,
        argument,
        raw_speaker_label="Pat Advocate",
        oyez_speaker_id="adv__stale_id",
        person=stale_person,
    )

    # Deliberately a DIFFERENT raw_speaker_label from the stale row's --
    # _resolve_and_link_participant's own (argument_id, raw_speaker_label)
    # idempotency check (T-29-04, pre-existing/unchanged by this plan) is a
    # SEPARATE dedup key from D-04's oyez_speaker_id pairing; a genuinely
    # new speaker whose display name happens to collide with a stale row's
    # label is an orthogonal, pre-existing edge case this test does not
    # exercise.
    speakers_index = {"adv__real_id": {"name": "Real Advocate", "type": "advocate"}}
    conversation = _conversation({"adv__real_id": {"side": 1}})

    await _reconcile(async_session, argument, conversation=conversation, speakers_index=speakers_index)

    await async_session.refresh(stale_participant)
    assert stale_participant.person_id == stale_person.id  # untouched
    assert stale_participant.oyez_speaker_id == "adv__stale_id"  # never repaired

    all_participants = (
        await async_session.execute(
            select(ArgumentParticipant).where(ArgumentParticipant.argument_id == argument.id)
        )
    ).scalars().all()
    assert len(all_participants) == 2  # stale row + a genuinely NEW one
    new_ones = [p for p in all_participants if p.oyez_speaker_id == "adv__real_id"]
    assert len(new_ones) == 1


async def test_participant_paired_by_oyez_speaker_id_survives_label_change(async_session):
    """The affirmative half of D-04: pairing succeeds via oyez_speaker_id
    even when the corpus's OWN display label for that speaker changes
    between passes (e.g. a speakers.json name correction) -- exactly the
    scenario raw_speaker_label-based dedup could not have handled."""
    argument, _case = await _seed_argument(async_session)
    await _seed_parse_run(async_session, argument)
    person = await _seed_person(async_session, full_name="Pat Advocate", oyez_speaker_id="adv__stable")
    participant = await _seed_participant(
        async_session,
        argument,
        raw_speaker_label="Pat OLD Label",
        oyez_speaker_id="adv__stable",
        person=person,
        source=ImportSource.PDF_PIPELINE,
        method=ImportMethod.RULE_BASED,
    )

    speakers_index = {"adv__stable": {"name": "Pat NEW Label", "type": "advocate"}}
    conversation = _conversation({"adv__stable": {"side": 1}})

    await _reconcile(async_session, argument, conversation=conversation, speakers_index=speakers_index)

    all_participants = (
        await async_session.execute(
            select(ArgumentParticipant).where(ArgumentParticipant.argument_id == argument.id)
        )
    ).scalars().all()
    assert len(all_participants) == 1  # paired, no duplicate row
    await async_session.refresh(participant)
    assert participant.person_id == person.id
    assert participant.source == ImportSource.CORPUS  # restamped (D-07)


async def test_participant_with_null_oyez_speaker_id_never_paired_or_written(async_session):
    argument, _case = await _seed_argument(async_session)
    await _seed_parse_run(async_session, argument)
    orphan_person = await _seed_person(async_session, full_name="Orphan Person")
    orphan = await _seed_participant(
        async_session,
        argument,
        raw_speaker_label="Orphan Label",
        oyez_speaker_id=None,
        person=orphan_person,
        side=SideEnum.PETITIONER,
        descriptor="Custom",
    )

    speakers_index = {"adv__someone": {"name": "Someone Else", "type": "advocate"}}
    conversation = _conversation({"adv__someone": {"side": 1}})

    await _reconcile(async_session, argument, conversation=conversation, speakers_index=speakers_index)

    await async_session.refresh(orphan)
    assert orphan.person_id == orphan_person.id
    assert orphan.side == SideEnum.PETITIONER
    assert orphan.descriptor == "Custom"
    assert orphan.oyez_speaker_id is None


async def test_unmentioned_stored_participant_untouched_no_discrepancy(async_session):
    argument, _case = await _seed_argument(async_session)
    await _seed_parse_run(async_session, argument)
    gone_person = await _seed_person(async_session, full_name="Gone Person", oyez_speaker_id="adv__gone")
    gone = await _seed_participant(
        async_session,
        argument,
        raw_speaker_label="Gone Advocate",
        oyez_speaker_id="adv__gone",
        person=gone_person,
    )

    # Corpus this pass mentions a DIFFERENT speaker entirely.
    speakers_index = {"adv__new": {"name": "New Advocate", "type": "advocate"}}
    conversation = _conversation({"adv__new": {"side": 1}})

    await _reconcile(async_session, argument, conversation=conversation, speakers_index=speakers_index)

    await async_session.refresh(gone)
    assert gone.person_id == gone_person.id
    assert (await _open_discrepancies(async_session, "argument_participant", gone.id)) == []


async def test_new_corpus_speaker_creates_new_participant_row(async_session):
    argument, _case = await _seed_argument(async_session)
    await _seed_parse_run(async_session, argument)

    speakers_index = {"adv__brand_new": {"name": "Brand New Advocate", "type": "advocate"}}
    conversation = _conversation({"adv__brand_new": {"side": 0}})

    await _reconcile(async_session, argument, conversation=conversation, speakers_index=speakers_index)

    participants = (
        await async_session.execute(
            select(ArgumentParticipant).where(ArgumentParticipant.argument_id == argument.id)
        )
    ).scalars().all()
    assert len(participants) == 1
    p = participants[0]
    assert p.oyez_speaker_id == "adv__brand_new"
    assert p.source == ImportSource.CORPUS
    assert p.method == ImportMethod.DIRECT
    assert p.side == SideEnum.RESPONDENT  # side_code 0 -> RESPONDENT


async def test_published_argument_records_disagreement_without_writing(async_session):
    from datetime import datetime, timezone

    argument, _case = await _seed_argument(
        async_session,
        status=ArgumentStatusEnum.PUBLISHED,
        source=ImportSource.CORPUS,
        method=ImportMethod.DIRECT,
    )
    argument.published_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    await async_session.flush()
    await _seed_parse_run(async_session, argument)
    old_docket = argument.source_docket

    case_fields = _case_fields(old_docket)
    case_fields["docket_no"] = "55-7777"

    counters = await _reconcile(async_session, argument, case_fields=case_fields)

    await async_session.refresh(argument)
    assert argument.source_docket == old_docket  # zero value-column changes
    assert argument.status == ArgumentStatusEnum.PUBLISHED
    assert argument.published_at is not None
    discrepancies = await _open_discrepancies(async_session, "argument", argument.id)
    assert any(d.field == "source_docket" for d in discrepancies)
    assert counters["published_writes_skipped"] == 1
    assert counters.get("values_accepted", 0) == 0
    assert counters.get("values_rejected", 0) == 0


async def test_published_argument_writes_skipped_even_with_no_disagreement(async_session):
    argument, case = await _seed_argument(async_session, status=ArgumentStatusEnum.PUBLISHED)
    await _seed_parse_run(async_session, argument)
    case_fields = _case_fields(argument.source_docket)
    case.case_name = case_fields.get("title") or "Pet v. Resp"
    await async_session.flush()

    counters = await _reconcile(async_session, argument, case_fields=case_fields)
    assert counters["published_writes_skipped"] == 1


async def test_lazy_reconcile_run_minted_once_and_reused_across_records(async_session):
    from datetime import date

    argument, _case = await _seed_argument(async_session, argued_date=date(1955, 11, 15))
    await _seed_parse_run(async_session, argument)
    argument.source_docket = "55-1111"
    await async_session.flush()

    case_fields = _case_fields(argument.source_docket, date_str="December 25, 1970")
    case_fields["docket_no"] = "55-2222"  # disagrees -> argued_date also disagrees

    await _reconcile(async_session, argument, case_fields=case_fields)

    assert await _reconcile_run_count(async_session, argument.id) == 1
    discrepancies = await _open_discrepancies(async_session, "argument", argument.id)
    assert len(discrepancies) >= 2
    run_ids = {d.import_run_id for d in discrepancies}
    assert len(run_ids) == 1
    assert None not in run_ids


async def test_two_identical_reconcile_passes_over_disagreement_are_deterministic(async_session):
    argument, _case = await _seed_argument(async_session)
    await _seed_parse_run(async_session, argument)
    argument.source_docket = "55-3333"
    await async_session.flush()

    case_fields = _case_fields(argument.source_docket)
    case_fields["docket_no"] = "55-4444"

    await _reconcile(async_session, argument, case_fields=case_fields)
    await _reconcile(async_session, argument, case_fields=case_fields)

    result = await async_session.execute(
        select(ValueDiscrepancy).where(
            ValueDiscrepancy.target_type == "argument",
            ValueDiscrepancy.target_id == argument.id,
            ValueDiscrepancy.field == "source_docket",
        )
    )
    rows = result.scalars().all()
    assert len(rows) == 2
    assert {r.incoming_value for r in rows} == {"55-4444"}
    assert {r.existing_value for r in rows} == {"55-3333"}


async def test_new_people_first_import_produces_zero_value_discrepancies(async_session):
    """Acceptance criterion: a first import creating THREE new Person rows
    produces zero value_discrepancy rows -- _apply_extracted_name_
    provenance's gap-fill-only write path (PD-13) must never mint one per
    fresh Person, regardless of how many are created in the same pass."""
    argument, _case = await _seed_argument(async_session)
    counters = {"people_created": 0, "people_matched": 0}
    people = []
    for i, (speaker_id, full_name) in enumerate(
        [
            ("adv__fresh_1", "Fresh Newcomer One"),
            ("adv__fresh_2", "Fresh Newcomer Two"),
            ("adv__fresh_3", "Fresh Newcomer Three"),
        ]
    ):
        person = await import_convokit_module._resolve_person(
            async_session, speaker_id, full_name, False, counters
        )
        people.append(person)
    await async_session.flush()
    assert counters["people_created"] == 3
    for person in people:
        assert (await _open_discrepancies(async_session, "person", person.id)) == []


async def test_apply_extracted_name_provenance_is_async_and_gated():
    assert inspect.iscoroutinefunction(_apply_extracted_name_provenance)
    source = inspect.getsource(_apply_extracted_name_provenance)
    body_after_signature = source.split("\n", 1)[1]
    non_comment_lines = [
        line for line in body_after_signature.splitlines() if not line.strip().startswith("#")
    ]
    assert sum("person.first_name =" in line for line in non_comment_lines) == 0


def test_reconcile_source_defines_required_helpers():
    source = inspect.getsource(import_convokit_module)
    assert "def _pair_participants_by_speaker_id(" in source
    assert "def _ensure_reconcile_run(" in source
    assert "def _restamp_corpus_provenance(" in source


def test_pair_participants_body_never_references_raw_speaker_label():
    """The EXECUTABLE body -- not the docstring's own prose explaining why
    raw_speaker_label is avoided -- must never reference it."""
    import ast
    import textwrap

    source = inspect.getsource(_pair_participants_by_speaker_id)
    tree = ast.parse(textwrap.dedent(source))
    func_def = tree.body[0]
    body_without_docstring = func_def.body[1:] if ast.get_docstring(func_def) else func_def.body
    body_source = "\n".join(ast.unparse(node) for node in body_without_docstring)
    assert "raw_speaker_label" not in body_source


def test_gate_functions_referenced_at_least_four_times():
    source = inspect.getsource(import_convokit_module)
    count = len(
        re.findall(
            r"apply_participant_value_change|apply_person_value_change|"
            r"apply_argument_value_change|apply_case_value_change",
            source,
        )
    )
    assert count >= 4


def test_no_direct_update_of_compare_set_columns_outside_restamp():
    source = inspect.getsource(import_convokit_module)
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("update(Argument)") or stripped.startswith("update(Case)") or stripped.startswith(
            "update(ArgumentParticipant)"
        ):
            # The only direct update(...) calls on these three models must
            # be the unconditional D-07 restamp inside
            # _restamp_corpus_provenance, which sets ONLY source/method.
            pass
    restamp_source = inspect.getsource(import_convokit_module._restamp_corpus_provenance)
    assert "source=ImportSource.CORPUS" in restamp_source
    assert "method=ImportMethod.DIRECT" in restamp_source
    # No OTHER function in the module issues update(Argument)/update(Case)/
    # update(ArgumentParticipant) -- the gates in admin_review own every
    # other compare-set write.
    other_source = source.replace(restamp_source, "")
    for model_name in ("Argument", "Case", "ArgumentParticipant"):
        assert f"update({model_name})" not in other_source


async def test_no_op_pass_creates_zero_import_run_rows(async_session):
    argument, case = await _seed_argument(async_session, argued_date=None)
    await _seed_parse_run(async_session, argument)
    case_fields = _case_fields(argument.source_docket)
    from pipeline.commands.import_convokit import _parse_argued_date, _case_name_from_fields

    argument.argued_date = _parse_argued_date(case_fields, argument.oyez_transcript_id)
    case.case_name = _case_name_from_fields(case_fields)
    case.docket_number = case_fields["docket_no"]
    await async_session.flush()

    before_count = (
        await async_session.execute(
            select(ImportRun).where(ImportRun.argument_id == argument.id)
        )
    )
    before_ids = {r.id for r in before_count.scalars().all()}

    await _reconcile(async_session, argument, case_fields=case_fields)

    after = (
        await async_session.execute(
            select(ImportRun).where(ImportRun.argument_id == argument.id)
        )
    )
    after_ids = {r.id for r in after.scalars().all()}
    assert after_ids == before_ids


# ===========================================================================
# Task 2: D-10/D-11/D-13 whole-set utterance replacement
# ===========================================================================


def _test_counters() -> dict:
    """A minimal counters dict safe to pass to _import_utterances/
    _resolve_and_link_participant directly (bare `{}` KeyErrors on their
    `counters["participants_created"] += 1` no-default increment)."""
    return {"participants_created": 0}


def _turn(speaker: str, text: str, conversation_id: str = "conv") -> dict:
    return {"id": f"u-{speaker}-{hash(text) & 0xffff}", "conversation_id": conversation_id, "speaker": speaker, "text": text}


async def test_identical_utterance_set_produces_no_new_run_or_rows(async_session):
    argument, _case = await _seed_argument(async_session)
    speakers_index = {"adv__u": {"name": "Utterance Advocate", "type": "advocate"}}
    turns = [_turn("adv__u", "Hello Court.", argument.oyez_transcript_id)]
    counters = {}
    incoming_rows = _incoming_utterance_rows(
        turns=turns, speakers_index=speakers_index, resolved_participants={}, counters=counters
    )
    await _seed_parse_run(async_session, argument, rows=incoming_rows)

    before_runs = (
        await async_session.execute(select(ImportRun).where(ImportRun.argument_id == argument.id))
    ).scalars().all()

    await _reconcile(async_session, argument, turns=turns, speakers_index=speakers_index)

    after_runs = (
        await async_session.execute(select(ImportRun).where(ImportRun.argument_id == argument.id))
    ).scalars().all()
    assert len(after_runs) == len(before_runs)
    after_utterances = (
        await async_session.execute(select(Utterance).where(Utterance.argument_id == argument.id))
    ).scalars().all()
    assert after_utterances == []  # nothing was ever written in the first place


async def test_changed_transcript_text_triggers_full_replacement_new_run(async_session):
    argument, _case = await _seed_argument(async_session)
    speakers_index = {"adv__u": {"name": "Utterance Advocate", "type": "advocate"}}
    old_turns = [_turn("adv__u", "Original text.", argument.oyez_transcript_id)]
    old_rows = _incoming_utterance_rows(
        turns=old_turns, speakers_index=speakers_index, resolved_participants={}, counters=_test_counters()
    )
    old_run = await _seed_parse_run(async_session, argument, rows=old_rows)
    await import_convokit_module._import_utterances(
        session=async_session,
        argument_id=argument.id,
        import_run_id=old_run.id,
        rows=old_rows,
        speakers_index=speakers_index,
        resolved_participants={},
        counters=_test_counters(),
    )

    new_turns = [_turn("adv__u", "Changed text!", argument.oyez_transcript_id)]

    counters = await _reconcile(async_session, argument, turns=new_turns, speakers_index=speakers_index)

    runs = (
        await async_session.execute(
            select(ImportRun)
            .where(ImportRun.argument_id == argument.id, ImportRun.step == "parse")
            .order_by(ImportRun.id)
        )
    ).scalars().all()
    assert len(runs) == 2
    assert runs[1].id > runs[0].id
    assert runs[1].content_digest != runs[0].content_digest

    old_run_rows = (
        await async_session.execute(select(Utterance).where(Utterance.import_run_id == runs[0].id))
    ).scalars().all()
    assert len(old_run_rows) == 1  # prior rows untouched

    new_run_rows = (
        await async_session.execute(select(Utterance).where(Utterance.import_run_id == runs[1].id))
    ).scalars().all()
    assert len(new_run_rows) == 1
    assert new_run_rows[0].text == "Changed text!"
    assert counters["utterance_sets_replaced"] == 1


async def test_get_argument_with_utterances_returns_exactly_new_run_rows(async_session):
    from datetime import datetime, timezone

    argument, _case = await _seed_argument(async_session, status=ArgumentStatusEnum.PUBLISHED)
    argument.published_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    await async_session.flush()

    speakers_index = {"adv__u": {"name": "Utterance Advocate", "type": "advocate"}}
    old_turns = [_turn("adv__u", "Old.", argument.oyez_transcript_id)]
    old_rows = _incoming_utterance_rows(
        turns=old_turns, speakers_index=speakers_index, resolved_participants={}, counters=_test_counters()
    )
    old_run = await _seed_parse_run(async_session, argument, rows=old_rows)
    await import_convokit_module._import_utterances(
        session=async_session,
        argument_id=argument.id,
        import_run_id=old_run.id,
        rows=old_rows,
        speakers_index=speakers_index,
        resolved_participants={},
        counters=_test_counters(),
    )
    await async_session.flush()

    # Unpublish is not exercised here -- go directly through a NON-published
    # write path for the replacement itself; publish only to prove the
    # public read filter. Use a private context to call _replace_utterance_set
    # directly, bypassing D-08 (this test is about the READ path, not D-08).
    new_turns = [_turn("adv__u", "New!", argument.oyez_transcript_id)]
    incoming_rows = _incoming_utterance_rows(
        turns=new_turns, speakers_index=speakers_index, resolved_participants={}, counters=_test_counters()
    )
    ctx = _ReconcileContext(
        session=async_session,
        argument=argument,
        conversation_id=argument.oyez_transcript_id,
        speakers_index=speakers_index,
        counters=_test_counters(),
        dry_run=False,
    )
    await _replace_utterance_set(ctx, incoming_rows)
    await async_session.flush()

    result = await get_argument_with_utterances(async_session, argument.id)
    assert result is not None
    texts = [u["text"] for u in result["utterances"]]
    assert texts == ["New!"]


async def test_operator_reassigned_participant_person_id_on_replacement_rows(async_session):
    argument, _case = await _seed_argument(async_session)
    reassigned_person = await _seed_person(async_session, full_name="Reassigned")
    speakers_index = {"adv__r": {"name": "Reassignable Advocate", "type": "advocate"}}
    old_turns = [_turn("adv__r", "Old text.", argument.oyez_transcript_id)]
    old_rows = _incoming_utterance_rows(
        turns=old_turns, speakers_index=speakers_index, resolved_participants={}, counters=_test_counters()
    )
    old_run = await _seed_parse_run(async_session, argument, rows=old_rows)
    await import_convokit_module._import_utterances(
        session=async_session,
        argument_id=argument.id,
        import_run_id=old_run.id,
        rows=old_rows,
        speakers_index=speakers_index,
        resolved_participants={},
        counters=_test_counters(),
    )

    # Operator reassigns the resulting participant row to a DIFFERENT
    # Person and confirms it.
    participant = (
        await async_session.execute(
            select(ArgumentParticipant).where(
                ArgumentParticipant.argument_id == argument.id,
                ArgumentParticipant.raw_speaker_label == "Reassignable Advocate",
            )
        )
    ).scalar_one()
    participant.person_id = reassigned_person.id
    participant.review_state = ReviewState.OPERATOR_EDITED
    await async_session.flush()

    new_turns = [_turn("adv__r", "New text!", argument.oyez_transcript_id)]
    await _reconcile(async_session, argument, turns=new_turns, speakers_index=speakers_index)

    new_run = (
        await async_session.execute(
            select(ImportRun)
            .where(ImportRun.argument_id == argument.id, ImportRun.step == "parse")
            .order_by(ImportRun.id.desc())
            .limit(1)
        )
    ).scalar_one()
    new_rows = (
        await async_session.execute(select(Utterance).where(Utterance.import_run_id == new_run.id))
    ).scalars().all()
    assert len(new_rows) == 1
    assert new_rows[0].person_id == reassigned_person.id


async def test_forced_mid_write_failure_leaves_no_zero_row_parse_run(async_session):
    """Forces a failure inside _import_utterances AFTER the new run has
    already been flushed (mid-write). Uses a SAVEPOINT
    (session.begin_nested()) to isolate JUST the failing reconcile
    attempt's writes -- the outer async_session fixture's own rollback
    only fires at test teardown, so without a savepoint there would be
    nothing left to query after catching the exception (the whole
    uncommitted session, seed data included, would need an explicit
    rollback that undoes everything, not only the failed attempt) -- this
    mirrors what `run_import_convokit`'s real `get_session()` context
    manager does in production: roll back to before the failed
    conversation's own transaction, leaving prior state intact (D-30)."""
    argument, _case = await _seed_argument(async_session)
    speakers_index = {"adv__u": {"name": "Utterance Advocate", "type": "advocate"}}
    old_turns = [_turn("adv__u", "Stable text.", argument.oyez_transcript_id)]
    old_rows = _incoming_utterance_rows(
        turns=old_turns, speakers_index=speakers_index, resolved_participants={}, counters=_test_counters()
    )
    old_run = await _seed_parse_run(async_session, argument, rows=old_rows)
    await import_convokit_module._import_utterances(
        session=async_session,
        argument_id=argument.id,
        import_run_id=old_run.id,
        rows=old_rows,
        speakers_index=speakers_index,
        resolved_participants={},
        counters=_test_counters(),
    )

    new_turns = [_turn("adv__u", "Different text.", argument.oyez_transcript_id)]
    argument_id = argument.id  # captured before the savepoint rollback expires it

    with patch.object(
        import_convokit_module, "_import_utterances", side_effect=RuntimeError("boom")
    ):
        with pytest.raises(RuntimeError):
            async with async_session.begin_nested():
                await _reconcile(
                    async_session, argument, turns=new_turns, speakers_index=speakers_index
                )

    runs = (
        await async_session.execute(
            select(ImportRun).where(ImportRun.argument_id == argument_id, ImportRun.step == "parse")
        )
    ).scalars().all()
    assert len(runs) == 1  # only the originally-seeded run survives
    for run in runs:
        row_count = len(
            (
                await async_session.execute(
                    select(Utterance).where(Utterance.import_run_id == run.id)
                )
            )
            .scalars()
            .all()
        )
        assert row_count > 0 or run.content_digest == compute_utterance_digest([])


async def test_empty_incoming_against_nonempty_stored_refuses_replacement(async_session):
    argument, _case = await _seed_argument(async_session)
    speakers_index = {"adv__u": {"name": "Utterance Advocate", "type": "advocate"}}
    old_turns = [_turn("adv__u", "Real content.", argument.oyez_transcript_id)]
    old_rows = _incoming_utterance_rows(
        turns=old_turns, speakers_index=speakers_index, resolved_participants={}, counters=_test_counters()
    )
    old_run = await _seed_parse_run(async_session, argument, rows=old_rows)
    await import_convokit_module._import_utterances(
        session=async_session,
        argument_id=argument.id,
        import_run_id=old_run.id,
        rows=old_rows,
        speakers_index=speakers_index,
        resolved_participants={},
        counters=_test_counters(),
    )

    counters = await _reconcile(async_session, argument, turns=[], speakers_index=speakers_index)

    runs = (
        await async_session.execute(
            select(ImportRun).where(ImportRun.argument_id == argument.id, ImportRun.step == "parse")
        )
    ).scalars().all()
    assert len(runs) == 1  # no new run written
    assert counters["conversations_errored"] >= 1


async def test_published_argument_utterance_replacement_skipped(async_session):
    from datetime import datetime, timezone

    argument, _case = await _seed_argument(async_session, status=ArgumentStatusEnum.PUBLISHED)
    argument.published_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    await async_session.flush()
    speakers_index = {"adv__u": {"name": "Utterance Advocate", "type": "advocate"}}
    old_turns = [_turn("adv__u", "Stable.", argument.oyez_transcript_id)]
    old_rows = _incoming_utterance_rows(
        turns=old_turns, speakers_index=speakers_index, resolved_participants={}, counters=_test_counters()
    )
    await _seed_parse_run(async_session, argument, rows=old_rows)

    new_turns = [_turn("adv__u", "Different!", argument.oyez_transcript_id)]
    await _reconcile(async_session, argument, turns=new_turns, speakers_index=speakers_index)

    runs = (
        await async_session.execute(
            select(ImportRun).where(ImportRun.argument_id == argument.id, ImportRun.step == "parse")
        )
    ).scalars().all()
    assert len(runs) == 1  # no replacement happened


# ===========================================================================
# Task 3: --dry-run and the PD-17 batch counters
# ===========================================================================


async def test_dry_run_disagreeing_argument_touches_zero_rows(async_session):
    argument, case = await _seed_argument(async_session)
    await _seed_parse_run(async_session, argument)
    old_docket = argument.source_docket

    before_arg_snapshot = (argument.source_docket, argument.argued_date)
    before_case_snapshot = case.case_name

    case_fields = _case_fields(old_docket)
    case_fields["docket_no"] = "55-6666"

    before_disc = await async_session.execute(select(ValueDiscrepancy))
    before_disc_count = len(before_disc.scalars().all())
    before_runs = await async_session.execute(select(ImportRun))
    before_run_count = len(before_runs.scalars().all())

    counters = await _reconcile(
        async_session, argument, case_fields=case_fields, dry_run=True
    )

    await async_session.refresh(argument)
    await async_session.refresh(case)
    assert (argument.source_docket, argument.argued_date) == before_arg_snapshot
    assert case.case_name == before_case_snapshot

    after_disc = await async_session.execute(select(ValueDiscrepancy))
    assert len(after_disc.scalars().all()) == before_disc_count
    after_runs = await async_session.execute(select(ImportRun))
    assert len(after_runs.scalars().all()) == before_run_count

    assert counters["values_rejected"] >= 1


async def test_dry_run_utterance_replacement_predicted_without_writing(async_session):
    argument, _case = await _seed_argument(async_session)
    speakers_index = {"adv__u": {"name": "Utterance Advocate", "type": "advocate"}}
    old_turns = [_turn("adv__u", "Stable.", argument.oyez_transcript_id)]
    old_rows = _incoming_utterance_rows(
        turns=old_turns, speakers_index=speakers_index, resolved_participants={}, counters=_test_counters()
    )
    await _seed_parse_run(async_session, argument, rows=old_rows)

    new_turns = [_turn("adv__u", "Changed.", argument.oyez_transcript_id)]

    before_runs = await async_session.execute(select(ImportRun))
    before_run_count = len(before_runs.scalars().all())
    before_utterances = await async_session.execute(select(Utterance))
    before_utterance_count = len(before_utterances.scalars().all())

    counters = await _reconcile(
        async_session, argument, turns=new_turns, speakers_index=speakers_index, dry_run=True
    )

    after_runs = await async_session.execute(select(ImportRun))
    assert len(after_runs.scalars().all()) == before_run_count
    after_utterances = await async_session.execute(select(Utterance))
    assert len(after_utterances.scalars().all()) == before_utterance_count
    assert counters["utterance_sets_replaced"] == 1


async def test_decide_write_direct_call_unreachable_when_not_dry_run(async_session):
    argument, _case = await _seed_argument(async_session)
    await _seed_parse_run(async_session, argument)
    old_docket = argument.source_docket
    case_fields = _case_fields(old_docket)
    case_fields["docket_no"] = "55-5555"

    with patch.object(
        import_convokit_module, "decide_write", side_effect=AssertionError("must not be called")
    ):
        await _reconcile(async_session, argument, case_fields=case_fields, dry_run=False)


@pytest.fixture()
async def isolated_session(test_db_url):
    """Same shape as test_import_convokit_reimport_tracer.py's own fixture
    -- a dedicated engine/session for tests that exercise the full
    run_import_convokit entry point (which owns get_session() itself)."""
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


def _make_session_cm(session):
    @asynccontextmanager
    async def _cm():
        yield session

    return _cm


async def test_dry_run_summary_labeled_distinctly(isolated_session, tmp_path, capsys):
    import argparse

    conversation_id = "8888_71"
    conversation = {
        conversation_id: {
            "conversation_id": conversation_id,
            "case_id": conversation_id,
            "advocates": {"adv__dryrun": {"side": 1}},
        }
    }
    case = {
        "id": conversation_id,
        "docket_no": "55-8801",
        "title": "DryRun v. Summary",
        "petitioner": "DryRun",
        "respondent": "Summary",
        "year": 1955,
        "transcripts": [{"name": "Oral Argument - November 15, 1955"}],
    }
    speakers = {"adv__dryrun": {"name": "Dry Run Advocate", "type": "advocate"}}
    utterances = [
        {"id": "u1", "conversation_id": conversation_id, "speaker": "adv__dryrun", "text": "Hello."}
    ]

    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "conversations.json").write_text(json.dumps(conversation), encoding="utf-8")
    with (corpus_dir / "cases.jsonl").open("w", encoding="utf-8") as f:
        f.write(json.dumps(case) + "\n")
    (corpus_dir / "speakers.json").write_text(json.dumps(speakers), encoding="utf-8")
    with (corpus_dir / "utterances.jsonl").open("w", encoding="utf-8") as f:
        for row in utterances:
            f.write(json.dumps(row) + "\n")

    args = argparse.Namespace(term=8888, term_range=None, corpus_dir=str(corpus_dir), dry_run=True)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    # First import under --dry-run creates nothing (D-28).
    result = await isolated_session.execute(
        select(Argument).where(Argument.oyez_transcript_id == conversation_id)
    )
    assert result.scalar_one_or_none() is None

    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out


def test_counter_keys_present_in_module():
    source = inspect.getsource(import_convokit_module)
    names = (
        "values_accepted",
        "values_rejected",
        "discrepancies_recorded",
        "utterance_sets_replaced",
        "published_writes_skipped",
    )
    count = sum(source.count(name) for name in names)
    assert count >= 10


def test_dry_run_flag_registered_on_cli():
    result = subprocess.run(
        [sys.executable, "-m", "pipeline", "import-convokit", "--help"],
        cwd=str(Path(__file__).resolve().parents[2]),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "--dry-run" in result.stdout


# ===========================================================================
# G-50-2b: row-level provenance must not be demoted on behalf of a field
# that was REJECTED on the same pass.
#
# Found by the D-09 live walkthrough (2026-08-26), not by these tests'
# predecessors -- every one of them exercised a SINGLE field per row, and
# the defect only appears when one row's compare-set walk mixes an accept
# with a reject. `source` is the only carrier of operator authority on
# `Argument`/`Case` (neither has `review_state`), so demoting the row
# silently destroyed the ladder's `operator` rung for the rejected field.
# ===========================================================================


def test_row_should_restamp_blocks_when_any_field_rejected():
    """A mixed walk never demotes -- this is the G-50-2b rule itself."""
    assert (
        import_convokit_module._row_should_restamp(
            [WriteDecision.ACCEPT, WriteDecision.REJECT_AND_RECORD]
        )
        is False
    )
    assert (
        import_convokit_module._row_should_restamp(
            [WriteDecision.ACCEPT_AND_RECORD, WriteDecision.REJECT_AND_RECORD]
        )
        is False
    )
    # Order must not matter -- the reject may be walked first or last.
    assert (
        import_convokit_module._row_should_restamp(
            [WriteDecision.REJECT_AND_RECORD, WriteDecision.ACCEPT]
        )
        is False
    )


def test_row_should_restamp_allows_a_clean_accepting_walk():
    """D-07 is preserved for the case it was actually written for."""
    assert import_convokit_module._row_should_restamp([WriteDecision.ACCEPT]) is True
    assert (
        import_convokit_module._row_should_restamp(
            [WriteDecision.ACCEPT, WriteDecision.ACCEPT_AND_RECORD, None]
        )
        is True
    )


def test_row_should_restamp_blocks_a_walk_that_wrote_nothing():
    """An all-no-opinion or empty walk changed no value, so the row's
    provenance still describes where its CURRENT values came from."""
    assert import_convokit_module._row_should_restamp([]) is False
    assert import_convokit_module._row_should_restamp([None, None]) is False
    assert (
        import_convokit_module._row_should_restamp([WriteDecision.REJECT_AND_RECORD])
        is False
    )


async def test_case_rejected_field_is_not_demoted_by_an_agreeing_sibling(async_session):
    """The exact live scenario: an operator-edited `case_name` is rejected
    while the sibling `docket_number` agrees. The agreeing field's ACCEPT
    must not strip the row's operator authority (G-50-2b)."""
    docket = _unique_docket()
    argument, case = await _seed_argument(
        async_session,
        docket=docket,
        case_name="OPERATOR EDIT — Pet v. Resp",
        case_source=ImportSource.OPERATOR,
        case_method=ImportMethod.MANUAL,
    )
    await _seed_parse_run(async_session, argument)

    # case_name disagrees (corpus derives "Pet v. Resp"); docket_number agrees.
    case_fields = _case_fields(docket)

    counters = await _reconcile(async_session, argument, case_fields=case_fields)

    await async_session.refresh(case)
    assert case.case_name == "OPERATOR EDIT — Pet v. Resp"  # value survived
    # The authority that PROTECTED it must survive too -- this is the bug.
    assert case.source == ImportSource.OPERATOR
    assert case.method == ImportMethod.MANUAL
    assert counters["values_rejected"] >= 1

    # And the audit row must attribute the stored value to the operator,
    # not to corpus -- what /admin/review renders to the operator.
    discrepancies = await _open_discrepancies(async_session, "case", case.id)
    matching = [d for d in discrepancies if d.field == "case_name"]
    assert len(matching) == 1
    assert matching[0].existing_source == ImportSource.OPERATOR.value
    assert matching[0].existing_method == ImportMethod.MANUAL.value


async def test_case_operator_authority_is_durable_across_repeated_reimports(
    async_session,
):
    """The row-18 symptom: authority held on the first re-import but was
    gone by the second, with no operator action in between."""
    docket = _unique_docket()
    argument, case = await _seed_argument(
        async_session,
        docket=docket,
        case_name="OPERATOR EDIT — Pet v. Resp",
        case_source=ImportSource.OPERATOR,
        case_method=ImportMethod.MANUAL,
    )
    await _seed_parse_run(async_session, argument)
    case_fields = _case_fields(docket)

    for pass_number in (1, 2, 3):
        await _reconcile(async_session, argument, case_fields=case_fields)
        await async_session.refresh(case)
        assert case.case_name == "OPERATOR EDIT — Pet v. Resp", (
            f"operator value lost on pass {pass_number}"
        )
        assert case.source == ImportSource.OPERATOR, (
            f"operator authority demoted on pass {pass_number}"
        )


async def test_case_clean_accepting_walk_still_restamps(async_session):
    """Guard against over-correcting: a walk with NO rejection must still
    demote a lower-authority row to corpus (D-07's original purpose)."""
    docket = _unique_docket()
    argument, case = await _seed_argument(
        async_session,
        docket=docket,
        case_name="Pet v. Resp",
        case_source=ImportSource.PDF_PIPELINE,
        case_method=ImportMethod.RULE_BASED,
    )
    await _seed_parse_run(async_session, argument)

    # Both Case fields agree with the corpus -> ACCEPT, ACCEPT, no reject.
    case_fields = _case_fields(docket)

    await _reconcile(async_session, argument, case_fields=case_fields)

    await async_session.refresh(case)
    assert case.source == ImportSource.CORPUS  # D-07 restamp still fires
    assert case.method == ImportMethod.DIRECT


async def test_argument_rejected_field_is_not_demoted_by_an_agreeing_sibling(
    async_session,
):
    """Same rule on `Argument` -- `source_docket` rejected, `argued_date`
    accepted as a gap-fill on the same pass."""
    docket = _unique_docket()
    argument, _case = await _seed_argument(
        async_session,
        docket=docket,
        argued_date=None,  # blank -> the corpus date is a gap-fill ACCEPT
        source=ImportSource.OPERATOR,
        method=ImportMethod.MANUAL,
    )
    await _seed_parse_run(async_session, argument)
    argument.source_docket = "55-0001"
    await async_session.flush()

    case_fields = _case_fields("55-0001")
    case_fields["docket_no"] = "55-9999"  # incoming disagrees -> REJECT

    counters = await _reconcile(async_session, argument, case_fields=case_fields)

    await async_session.refresh(argument)
    assert argument.source_docket == "55-0001"  # operator value survived
    assert argument.argued_date is not None  # sibling gap-fill did land
    assert argument.source == ImportSource.OPERATOR  # authority survived
    assert argument.method == ImportMethod.MANUAL
    assert counters["values_rejected"] >= 1

    discrepancies = await _open_discrepancies(async_session, "argument", argument.id)
    matching = [d for d in discrepancies if d.field == "source_docket"]
    assert len(matching) == 1
    assert matching[0].existing_source == ImportSource.OPERATOR.value


async def test_participant_rejected_field_is_not_demoted_by_an_agreeing_sibling(
    async_session,
):
    """`ArgumentParticipant` carries operator authority on `review_state`,
    so its `source` demotion was never the load-bearing defect -- but the
    same one-restamp-per-row rule applies, and its walk is the widest
    (person_id / side / descriptor)."""
    argument, _case = await _seed_argument(async_session)
    await _seed_parse_run(async_session, argument)
    original_person = await _seed_person(async_session, full_name="Original Person")
    corpus_person = await _seed_person(
        async_session, full_name="Corpus Person", oyez_speaker_id="spk_1"
    )
    participant = await _seed_participant(
        async_session,
        argument,
        raw_speaker_label="MR. ORIGINAL",
        oyez_speaker_id="spk_1",
        person=original_person,
        side=SideEnum.ADVOCATE,
        source=ImportSource.OPERATOR,
        method=ImportMethod.MANUAL,
        review_state=ReviewState.OPERATOR_EDITED,
    )

    # person_id disagrees (operator reassigned it) -> REJECT.
    # side agrees (both ADVOCATE) -> ACCEPT.
    conversation = _conversation(advocates={"spk_1": {"side": 1}})
    speakers_index = {"spk_1": {"name": "Corpus Person", "is_justice": False}}

    counters = await _reconcile(
        async_session,
        argument,
        conversation=conversation,
        speakers_index=speakers_index,
        turns=[],
    )

    await async_session.refresh(participant)
    assert participant.person_id == original_person.id  # operator value survived
    assert participant.source == ImportSource.OPERATOR  # not demoted
    assert participant.method == ImportMethod.MANUAL
    assert counters["values_rejected"] >= 1
    assert corpus_person.id != original_person.id


def test_every_restamp_call_site_is_gated_on_the_row_level_predicate():
    """Structural guard (G-50-2b): a future field added to any compare-set
    walk must not reintroduce a per-field restamp. Every call to
    `_restamp_corpus_provenance` outside its own definition must be paired
    with an `_row_should_restamp(...)` guard, and the old per-field shape
    (`if decision in (...ACCEPT...): await _restamp_corpus_provenance(`)
    must not reappear anywhere.

    Falsifiability-checked 2026-08-27 by restoring the per-field restamp in
    the Case walk and confirming this test fails.
    """
    source = inspect.getsource(import_convokit_module)
    # Strip BOTH helper definitions so only genuine CALL sites are counted —
    # each definition mentions its own name and would mask a lost guard.
    call_sites = source.replace(
        inspect.getsource(import_convokit_module._restamp_corpus_provenance), ""
    ).replace(inspect.getsource(import_convokit_module._row_should_restamp), "")

    call_count = call_sites.count("_restamp_corpus_provenance(")
    guard_count = call_sites.count("_row_should_restamp(")
    assert call_count == 3, (
        f"expected 3 restamp call sites (Argument/Case/Participant), got {call_count}"
    )
    assert guard_count == call_count, (
        f"{call_count} restamp call sites but {guard_count} row-level guards — "
        "a per-field restamp has been reintroduced (G-50-2b)"
    )

    # The old per-field shape, at any indentation.
    per_field = re.compile(
        r"if decision in \(\s*WriteDecision\.ACCEPT,\s*WriteDecision\.ACCEPT_AND_RECORD,?\s*\):"
        r"\s*await _restamp_corpus_provenance\(",
        re.S,
    )
    assert not per_field.search(source), (
        "a per-field `if decision in (...): await _restamp_corpus_provenance(` "
        "has been reintroduced (G-50-2b)"
    )
