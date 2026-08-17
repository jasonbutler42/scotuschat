"""
Tests for pipeline.commands.import_convokit.

Covers:
    - Task 1: _parse_term_range() validation and --corpus-dir fail-fast
      (no DB required for these).
    - Task 2: idempotent Case/Argument/CaseArgument/ImportRun scaffolding,
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
import inspect
import json
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from pipeline.commands.import_convokit import _import_conversation


def test_collision_counter_only_handles_named_pair_constraint():
    source = inspect.getsource(_import_conversation)
    assert "if not is_argument_pair_violation(exc):" in source
    assert "docket_question_conflict" in source
    assert source.index("if not is_argument_pair_violation(exc):") < source.index(
        'counters["docket_question_conflict"]'
    )

from api.models.models import (
    Argument,
    ArgumentParticipant,
    ArgumentStatusEnum,
    Case,
    CaseArgument,
    ImportMethod,
    ImportRun,
    ImportSource,
    Person,
    SideEnum,
    Utterance,
)
from pipeline.commands.import_convokit import (
    _parse_term_range,
    _resolve_and_link_participant,
    _resolve_person,
    _resolve_scoped_conversation,
    run_import_convokit,
)

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


# ===========================================================================
# Shared fixtures / helpers for Task 2 & 3 (DB-dependent)
# ===========================================================================


def _make_session_cm(session):
    """
    Create a context manager that yields `session`.

    Used to patch pipeline.commands.import_convokit.get_session so tests
    inject a test-owned session (rolled back after the test) instead of
    opening real, separately-committed DB connections per conversation.
    Matches the established pattern in pipeline/tests/test_ingest.py and
    pipeline/tests/test_import_justices_csv.py.
    """

    @asynccontextmanager
    async def _cm():
        yield session

    return _cm


@pytest.fixture()
async def isolated_session(test_db_url):
    """
    Function-scoped AsyncSession with its own dedicated engine, rolled back
    after the test and disposed afterward -- avoids the pre-existing
    Windows/asyncpg + pytest-asyncio stale-event-loop issue documented in
    pipeline/tests/test_import_justices_csv.py's identical fixture.
    """
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


def _write_corpus_fixture(
    tmp_path: Path,
    conversations: dict,
    cases: list[dict],
    speakers: dict,
) -> Path:
    """Write a small synthetic corpus_dir tree (never the real corpus files)."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "conversations.json").write_text(
        json.dumps(conversations), encoding="utf-8"
    )
    with (corpus_dir / "cases.jsonl").open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case) + "\n")
    (corpus_dir / "speakers.json").write_text(json.dumps(speakers), encoding="utf-8")
    # Plan 05: run_import_convokit now requires utterances.jsonl to exist
    # (streamed once per term, T-29-03) -- these Task 2/3 tests don't
    # exercise utterance import, so an empty file (zero turns) is enough.
    (corpus_dir / "utterances.jsonl").write_text("", encoding="utf-8")
    return corpus_dir


# D-15 regression fixture: cases.jsonl "year" (1955) intentionally differs
# from the argued_date's calendar year (1956) -- SCOTUS October Terms span
# the Oct/Dec calendar boundary.
_CONVERSATION_9999_71 = {
    "9999_71": {
        "conversation_id": "9999_71",
        "case_id": "9999_71",
        "advocates": {"adv__john_smith": {"side": 1}},
        # Forbidden apolitical fields present in the raw source -- must
        # never reach any DB column (T-29-02).
        "win_side": 1,
        "votes_side": 1,
    }
}

_CASE_9999_71 = {
    "id": "9999_71",
    "docket_no": "55-71",
    "title": "Smith v. Jones",
    "petitioner": "Smith",
    "respondent": "Jones",
    "year": 1955,
    "transcripts": [{"name": "Oral Argument - November 15, 1956"}],
    # Forbidden apolitical fields -- must never reach any DB column (T-29-02).
    "win_side": 1,
    "win_side_detail": "affirmed",
    "votes": [1, 0, 1],
    "votes_detail": "6-3",
    "votes_side": 1,
    "scdb_docket_id": "1955-071-scdb",
}

_SPEAKERS = {
    "adv__john_smith": {"name": "John Smith", "type": "advocate"},
}


def _args(term, corpus_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(term=term, term_range=None, corpus_dir=str(corpus_dir))


def _scoped_args(conversation_id, corpus_dir: Path) -> argparse.Namespace:
    """
    Phase 42 D-01: the scoped-import Namespace shape -- term/term_range
    stay unset (None) since _resolve_scoped_conversation's caller must
    never call _resolve_terms in scoped mode.
    """
    return argparse.Namespace(
        term=None,
        term_range=None,
        corpus_dir=str(corpus_dir),
        conversation_id=conversation_id,
    )


# ===========================================================================
# Task 2: entity creation, apolitical stripping, idempotency
# ===========================================================================


@pytest.mark.asyncio
async def test_creates_case_argument_caseargument_importrun_entities(
    isolated_session, tmp_path
):
    """
    Given a synthetic conversation+case fixture, a Case (lead docket only),
    Argument (status=pipeline -- Phase 30 supersedes D-06, see
    30-RESEARCH.md Pitfall 1; oyez_transcript_id set), CaseArgument
    (is_lead=True), and ImportRun (source=corpus, method=direct) are
    created. term_year comes from cases.jsonl's "year" (1955) even though
    the argued_date's calendar year (1956) differs (D-15 regression case).
    """
    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATION_9999_71, [_CASE_9999_71], _SPEAKERS
    )
    args = _args(9999, corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    case = (
        await isolated_session.execute(
            select(Case).where(Case.docket_number == "55-71")
        )
    ).scalar_one()
    assert case.term_year == 1955  # D-15: from cases.jsonl "year", not argued_date
    assert case.oyez_case_id == "9999_71"

    argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "9999_71")
        )
    ).scalar_one()
    # Phase 30 fix: corpus arguments now start at PIPELINE (not DRAFT),
    # matching the state the PDF pipeline's ingest step already produces,
    # so the Resolve card renders editable (30-RESEARCH.md Pitfall 1).
    assert argument.status == ArgumentStatusEnum.PIPELINE
    assert argument.source_docket == "55-71"
    assert argument.argued_date.isoformat() == "1956-11-15"  # calendar year != term_year
    # Standing guard (Phase 47 Task 2): import_run.external_id is a
    # dual-write, never a relocation -- oyez_transcript_id must still carry
    # the same ConvoKit conversation id it always did.
    assert argument.oyez_transcript_id == "9999_71"

    link = (
        await isolated_session.execute(
            select(CaseArgument).where(
                CaseArgument.case_id == case.id,
                CaseArgument.argument_id == argument.id,
            )
        )
    ).scalar_one()
    assert link.is_lead is True

    run = (
        await isolated_session.execute(
            select(ImportRun).where(ImportRun.argument_id == argument.id)
        )
    ).scalar_one()
    assert run.source == ImportSource.CORPUS
    assert run.method == ImportMethod.DIRECT
    assert run.step == "parse"


@pytest.mark.asyncio
async def test_apolitical_fields_never_persisted_to_any_column(
    isolated_session, tmp_path
):
    """
    T-29-02: even though the raw source dicts carry win_side/votes_side/
    scdb_docket_id (and more), no created row's attributes or JSONB blob
    ever contains them.
    """
    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATION_9999_71, [_CASE_9999_71], _SPEAKERS
    )
    args = _args(9999, corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    case = (
        await isolated_session.execute(
            select(Case).where(Case.docket_number == "55-71")
        )
    ).scalar_one()
    case_attrs = {k for k in vars(case) if not k.startswith("_")}
    assert "win_side" not in case_attrs
    assert "votes_side" not in case_attrs
    assert "scdb_docket_id" not in case_attrs

    argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "9999_71")
        )
    ).scalar_one()
    argument_attrs = {k for k in vars(argument) if not k.startswith("_")}
    assert "win_side" not in argument_attrs
    assert "votes_side" not in argument_attrs
    # cover_metadata is never written by this command -- confirm it stays
    # unset (no accidental JSONB dumping-ground use, RESEARCH Pitfall 2).
    assert argument.cover_metadata is None


@pytest.mark.asyncio
async def test_idempotent_rerun_creates_no_duplicate_arguments(
    isolated_session, tmp_path
):
    """D-08: re-running the same conversation creates zero new Argument rows."""
    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATION_9999_71, [_CASE_9999_71], _SPEAKERS
    )
    args = _args(9999, corpus_dir)
    session_cm = _make_session_cm(isolated_session)

    for _ in range(2):
        with patch(
            "pipeline.commands.import_convokit.get_session", new=session_cm
        ):
            await run_import_convokit(args)

    arguments = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "9999_71")
        )
    ).scalars().all()
    assert len(arguments) == 1, (
        "Re-running the same conversation must not create duplicate Argument rows"
    )


@pytest.mark.asyncio
async def test_malformed_conversation_flagged_not_aborting_term(
    isolated_session, tmp_path
):
    """
    T-29-05b/RESEARCH Pitfall 5: a conversation whose case_id has no
    matching cases.jsonl row is flagged (skipped), but a well-formed
    sibling conversation in the same term still imports successfully.
    """
    conversations = {
        "9999_71": _CONVERSATION_9999_71["9999_71"],
        "9999_98": {
            "conversation_id": "9999_98",
            "case_id": "9999_98",  # no matching cases.jsonl row
            "advocates": {},
        },
    }
    corpus_dir = _write_corpus_fixture(
        tmp_path, conversations, [_CASE_9999_71], _SPEAKERS
    )
    args = _args(9999, corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    good_argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "9999_71")
        )
    ).scalar_one()
    # Phase 30 fix: corpus arguments now start at PIPELINE (not DRAFT).
    assert good_argument.status == ArgumentStatusEnum.PIPELINE

    missing_argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "9999_98")
        )
    ).scalar_one_or_none()
    assert missing_argument is None


# ===========================================================================
# Task 3: speaker resolution -- Person (D-11) + ArgumentParticipant (side)
# ===========================================================================

_CONVERSATION_MULTI_SIDE = {
    "9999_72": {
        "conversation_id": "9999_72",
        "case_id": "9999_72",
        "advocates": {
            "adv__resp_counsel": {"side": 0},
            "adv__pet_counsel": {"side": 1},
            "adv__amicus_counsel": {"side": 2},
            "adv__unknown_counsel": {"side": 3},
        },
    }
}
_CASE_9999_72 = {
    "id": "9999_72",
    "docket_no": "55-72",
    "title": "Doe v. Roe",
    "petitioner": "Doe",
    "respondent": "Roe",
    "year": 1955,
    "transcripts": [{"name": "Oral Argument - December 1, 1955"}],
}
_SPEAKERS_SIDES = {
    "adv__resp_counsel": {"name": "Resp Counsel", "type": "advocate"},
    "adv__pet_counsel": {"name": "Pet Counsel", "type": "advocate"},
    "adv__amicus_counsel": {"name": "Amicus Counsel", "type": "advocate"},
    "adv__unknown_counsel": {"name": "Unknown Counsel", "type": "advocate"},
}


@pytest.mark.asyncio
async def test_advocate_side_codes_map_onto_side_enum(isolated_session, tmp_path):
    """Advocate side codes 0/1/2/3 map to RESPONDENT/PETITIONER/AMICUS/UNKNOWN."""
    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATION_MULTI_SIDE, [_CASE_9999_72], _SPEAKERS_SIDES
    )
    args = _args(9999, corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "9999_72")
        )
    ).scalar_one()
    participants = (
        await isolated_session.execute(
            select(ArgumentParticipant).where(
                ArgumentParticipant.argument_id == argument.id
            )
        )
    ).scalars().all()
    side_by_label = {p.raw_speaker_label: p.side for p in participants}
    assert side_by_label["Resp Counsel"] == SideEnum.RESPONDENT
    assert side_by_label["Pet Counsel"] == SideEnum.PETITIONER
    assert side_by_label["Amicus Counsel"] == SideEnum.AMICUS
    assert side_by_label["Unknown Counsel"] == SideEnum.UNKNOWN


@pytest.mark.asyncio
async def test_existing_oyez_speaker_id_match_reuses_person_no_new_row(
    isolated_session, tmp_path
):
    """D-11: a Person row already matched by oyez_speaker_id is reused, not
    duplicated -- even if its full_name differs from the corpus label."""
    existing = Person(
        full_name="Some Other Name", oyez_speaker_id="adv__john_smith", is_justice=False
    )
    isolated_session.add(existing)
    await isolated_session.flush()
    existing_id = existing.id

    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATION_9999_71, [_CASE_9999_71], _SPEAKERS
    )
    args = _args(9999, corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    people = (
        await isolated_session.execute(
            select(Person).where(Person.oyez_speaker_id == "adv__john_smith")
        )
    ).scalars().all()
    assert len(people) == 1
    assert people[0].id == existing_id
    assert people[0].full_name == "Some Other Name"  # matched by ID, untouched


@pytest.mark.asyncio
async def test_full_name_only_match_backfills_oyez_speaker_id(
    isolated_session, tmp_path
):
    """D-11: a pre-existing Person matched only by full_name gets its
    oyez_speaker_id backfilled so the next run matches by stable ID."""
    existing = Person(full_name="John Smith", oyez_speaker_id=None, is_justice=False)
    isolated_session.add(existing)
    await isolated_session.flush()
    existing_id = existing.id

    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATION_9999_71, [_CASE_9999_71], _SPEAKERS
    )
    args = _args(9999, corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    people = (
        await isolated_session.execute(
            select(Person).where(Person.full_name == "John Smith")
        )
    ).scalars().all()
    assert len(people) == 1, "Full-name match must not create a duplicate Person row"
    assert people[0].id == existing_id
    assert people[0].oyez_speaker_id == "adv__john_smith"  # D-11 backfill


@pytest.mark.asyncio
async def test_brand_new_speaker_creates_person_with_oyez_id_and_is_justice_false(
    isolated_session, tmp_path
):
    """A speaker with no existing Person match at all gets a new row with
    oyez_speaker_id set and is_justice derived from speakers.json's type."""
    conversations = {
        "9999_73": {
            "conversation_id": "9999_73",
            "case_id": "9999_73",
            "advocates": {"adv__brand_new": {"side": 1}},
        }
    }
    case = {
        "id": "9999_73",
        "docket_no": "55-73",
        "title": "New v. Case",
        "petitioner": "New",
        "respondent": "Case",
        "year": 1955,
        "transcripts": [{"name": "Oral Argument - January 10, 1955"}],
    }
    speakers = {"adv__brand_new": {"name": "Brand New Advocate", "type": "advocate"}}
    corpus_dir = _write_corpus_fixture(tmp_path, conversations, [case], speakers)
    args = _args(9999, corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    person = (
        await isolated_session.execute(
            select(Person).where(Person.oyez_speaker_id == "adv__brand_new")
        )
    ).scalar_one()
    assert person.full_name == "Brand New Advocate"
    assert person.is_justice is False


@pytest.mark.asyncio
async def test_justice_type_speaker_resolves_to_bench_side(isolated_session, tmp_path):
    """
    speakers.json's `type` field is authoritative for BENCH classification
    (RESEARCH Open Question 3) -- a justice-typed speaker id gets
    is_justice=True and side=BENCH regardless of which dict it's supplied
    through (Plan 04 only has conversations.json's "advocates" dict
    available pre-utterance-import; Plan 05 supplies the real bench roster
    once utterances.jsonl is streamed, reusing this same classification
    logic unchanged).
    """
    conversations = {
        "9999_74": {
            "conversation_id": "9999_74",
            "case_id": "9999_74",
            "advocates": {"j__test_justice_doe": {"side": 3}},
        }
    }
    case = {
        "id": "9999_74",
        "docket_no": "55-74",
        "title": "Bench v. Test",
        "petitioner": "Bench",
        "respondent": "Test",
        "year": 1955,
        "transcripts": [{"name": "Oral Argument - February 2, 1955"}],
    }
    speakers = {"j__test_justice_doe": {"name": "Test Justice Doe", "type": "justice"}}
    corpus_dir = _write_corpus_fixture(tmp_path, conversations, [case], speakers)
    args = _args(9999, corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    person = (
        await isolated_session.execute(
            select(Person).where(Person.oyez_speaker_id == "j__test_justice_doe")
        )
    ).scalar_one()
    assert person.is_justice is True

    argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "9999_74")
        )
    ).scalar_one()
    participant = (
        await isolated_session.execute(
            select(ArgumentParticipant).where(
                ArgumentParticipant.argument_id == argument.id
            )
        )
    ).scalar_one()
    assert participant.side == SideEnum.BENCH


@pytest.mark.asyncio
async def test_rerun_creates_no_duplicate_argument_participants(
    isolated_session, tmp_path
):
    """Re-running creates zero duplicate ArgumentParticipant rows."""
    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATION_9999_71, [_CASE_9999_71], _SPEAKERS
    )
    args = _args(9999, corpus_dir)
    session_cm = _make_session_cm(isolated_session)

    for _ in range(2):
        with patch(
            "pipeline.commands.import_convokit.get_session", new=session_cm
        ):
            await run_import_convokit(args)

    argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "9999_71")
        )
    ).scalar_one()
    participants = (
        await isolated_session.execute(
            select(ArgumentParticipant).where(
                ArgumentParticipant.argument_id == argument.id
            )
        )
    ).scalars().all()
    assert len(participants) == 1


@pytest.mark.asyncio
async def test_resolve_and_link_participant_idempotent_check_before_insert(
    isolated_session,
):
    """
    Direct unit test of the participant-linking helper's check-before-insert
    idempotency (T-29-04) -- defense-in-depth beyond the Argument-level
    oyez_transcript_id dedup, exercising the (argument_id,
    raw_speaker_label) uniqueness guard described in the plan directly.
    """
    argument = Argument(
        question_number=1,
        status=ArgumentStatusEnum.DRAFT,
        source_docket="55-99",
        oyez_transcript_id="9999_99",
    )
    isolated_session.add(argument)
    await isolated_session.flush()

    speakers_index = {"adv__repeat": {"name": "Repeat Advocate", "type": "advocate"}}
    counters = {"participants_created": 0, "flagged": 0}

    for _ in range(2):
        await _resolve_and_link_participant(
            session=isolated_session,
            argument_id=argument.id,
            speaker_id="adv__repeat",
            speakers_index=speakers_index,
            side_code=1,
            counters=counters,
        )

    participants = (
        await isolated_session.execute(
            select(ArgumentParticipant).where(
                ArgumentParticipant.argument_id == argument.id
            )
        )
    ).scalars().all()
    assert len(participants) == 1
    assert counters["participants_created"] == 1


# ===========================================================================
# 29-09 (CR-01 gap closure): per-docket question_number derivation +
# distinct docket_question_conflict counter
# ===========================================================================


@pytest.mark.asyncio
async def test_docket_already_at_question_number_1_imports_at_question_number_2(
    isolated_session, tmp_path
):
    """
    A docket already occupying question_number=1 (as if from the PDF
    pipeline, no oyez_transcript_id) does not collide with a corpus-
    imported conversation for the same docket -- the corpus record is
    imported at question_number=2 instead of being silently dropped
    (29-VERIFICATION.md CR-01, reargued-case / PDF-overlap scenario).
    """
    pdf_case = Case(
        docket_number="55-71",
        docket_number_norm="5571",
        case_name="Smith v. Jones (PDF ingest)",
        term_year=1955,
        slug="smith-v-jones-pdf-ingest",
    )
    isolated_session.add(pdf_case)
    await isolated_session.flush()
    pdf_argument = Argument(
        source_docket="55-71",
        question_number=1,
        status=ArgumentStatusEnum.DRAFT,
    )
    isolated_session.add(pdf_argument)
    await isolated_session.flush()
    pdf_argument_id = pdf_argument.id

    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATION_9999_71, [_CASE_9999_71], _SPEAKERS
    )
    args = _args(9999, corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    corpus_argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "9999_71")
        )
    ).scalar_one()
    assert corpus_argument.question_number == 2

    # The pre-existing PDF-ingested row at question_number=1 must still be
    # present -- both rows coexist for this docket, neither was dropped.
    pdf_row_still_present = (
        await isolated_session.execute(
            select(Argument).where(
                Argument.source_docket == "55-71",
                Argument.question_number == 1,
            )
        )
    ).scalar_one_or_none()
    assert pdf_row_still_present is not None
    assert pdf_row_still_present.id == pdf_argument_id


@pytest.mark.asyncio
async def test_forced_collision_increments_docket_question_conflict_not_errored(
    isolated_session, tmp_path, monkeypatch, capsys
):
    """
    Safety-net path: when the per-docket question_number derivation itself
    returns a colliding value (simulating a residual collision that
    _next_question_number cannot prevent, e.g. a concurrent writer), the
    IntegrityError raised at flush is caught, rolled back, and counted in a
    DISTINCT docket_question_conflict counter -- never folded into
    conversations_errored -- and no corpus Argument row is created
    (29-VERIFICATION.md CR-01).
    """
    pdf_case = Case(
        docket_number="55-71",
        docket_number_norm="5571",
        case_name="Smith v. Jones (PDF ingest)",
        term_year=1955,
        slug="smith-v-jones-pdf-collision",
    )
    isolated_session.add(pdf_case)
    await isolated_session.flush()
    isolated_session.add(
        Argument(
            source_docket="55-71",
            question_number=1,
            status=ArgumentStatusEnum.DRAFT,
        )
    )
    await isolated_session.flush()

    async def _always_collide(session, source_docket):
        return 1  # forces a collision with the pre-existing question_number=1 row

    monkeypatch.setattr(
        "pipeline.commands.import_convokit._next_question_number", _always_collide
    )

    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATION_9999_71, [_CASE_9999_71], _SPEAKERS
    )
    args = _args(9999, corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    no_corpus_argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "9999_71")
        )
    ).scalar_one_or_none()
    assert no_corpus_argument is None, (
        "A conversation that hits a docket/question collision at flush "
        "must not create a corpus Argument row."
    )

    captured = capsys.readouterr()
    summary_line = next(
        line for line in captured.out.splitlines() if line.startswith("Term 9999:")
    )
    assert "0 conversations errored" in summary_line
    assert "1 docket/question conflicts" in summary_line


# ===========================================================================
# Migration 0018 gap-closure: historical docket numbers recycle across terms
# ===========================================================================


@pytest.mark.asyncio
async def test_recycled_docket_number_across_terms_creates_two_distinct_cases(
    isolated_session, tmp_path
):
    """
    Real historical docket numbers reset every October Term (e.g. docket
    "71" is a different, unrelated case in 1955 and 1956) -- unlike modern
    dockets, which embed the term and are naturally globally unique.
    _get_or_create_case must not conflate two different terms' same-docket
    cases into one Case row; it dedups on the stable oyez_case_id, backed by
    the DB's (docket_number, term_year) composite unique constraint
    (migration 0018), not on docket_number alone.

    Uses an entirely fictional docket ("TEST-71") and term years (9998/9999)
    -- not just a fictional oyez_case_id -- so this test can never silently
    match a real historical Case row already sitting in a dev database that
    has run a real corpus import (docket "71" alone recurs across a dozen
    real terms; reusing a real term_year here previously caused this test
    to match live data via the (docket_number, term_year) fallback path).
    """
    conversations = {
        "9999_TEST-71": {
            "conversation_id": "9999_TEST-71",
            "case_id": "9999_TEST-71",
            "advocates": {"adv__test_advocate_a": {"side": 1}},
        },
        "9998_TEST-71": {
            "conversation_id": "9998_TEST-71",
            "case_id": "9998_TEST-71",
            "advocates": {"adv__test_advocate_b": {"side": 1}},
        },
    }
    case_a = {
        "id": "9999_TEST-71",
        "docket_no": "TEST-71",
        "title": "Test Case A",
        "petitioner": "A",
        "respondent": "Aardvark",
        "year": 9999,
        "transcripts": [{"name": "Oral Argument - November 15, 9999"}],
    }
    case_b = {
        "id": "9998_TEST-71",
        "docket_no": "TEST-71",
        "title": "Test Case B",
        "petitioner": "B",
        "respondent": "Bumblebee",
        "year": 9998,
        "transcripts": [{"name": "Oral Argument - January 8, 9998"}],
    }
    speakers = {
        "adv__test_advocate_a": {"name": "Test Advocate A", "type": "advocate"},
        "adv__test_advocate_b": {"name": "Test Advocate B", "type": "advocate"},
    }
    corpus_dir = _write_corpus_fixture(
        tmp_path, conversations, [case_a, case_b], speakers
    )
    args = argparse.Namespace(
        term=None, term_range="9998-9999", corpus_dir=str(corpus_dir)
    )

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    cases = (
        await isolated_session.execute(
            select(Case)
            .where(Case.docket_number == "TEST-71")
            .order_by(Case.term_year)
        )
    ).scalars().all()

    assert len(cases) == 2, "Both terms' docket-TEST-71 cases must survive as distinct rows"
    assert cases[0].term_year == 9998
    assert cases[0].case_name == "Test Case B"
    assert cases[0].oyez_case_id == "9998_TEST-71"
    assert cases[1].term_year == 9999
    assert cases[1].case_name == "Test Case A"
    assert cases[1].oyez_case_id == "9999_TEST-71"


# ===========================================================================
# Phase 38 (D-14-D-18, T-38-10/T-38-11): conservative name-part extraction
# + persistent provenance in _resolve_person
# ===========================================================================


@pytest.mark.asyncio
async def test_brand_new_speaker_confident_split_gets_parts_and_high_provenance(
    isolated_session,
):
    """
    A brand-new speaker whose corpus full_name is an unambiguous two-token
    name gets its structured parts populated directly (High confidence,
    round-trip-exact split, D-11) plus a matching provenance envelope, and
    is never flagged for review.
    """
    counters = {}
    person = await _resolve_person(
        isolated_session, "adv__jane_roe", "Jane Roe", False, counters
    )
    await isolated_session.flush()

    assert person.first_name == "Jane"
    assert person.last_name == "Roe"
    assert person.middle_name is None
    assert person.name_suffix is None
    assert person.name_needs_review is False
    assert person.name_extraction_metadata is not None
    assert person.name_extraction_metadata["source"] == "import_convokit"
    assert person.name_extraction_metadata["confidence"] == "High"
    assert person.name_extraction_metadata["auto_applied"] is True
    assert person.name_extraction_metadata["raw"] == "Jane Roe"


@pytest.mark.asyncio
async def test_brand_new_speaker_ambiguous_name_gets_provenance_without_parts(
    isolated_session,
):
    """
    A brand-new speaker whose corpus full_name is structurally ambiguous
    (single-part -- D-11/D-18) never gets a guessed structured part, but its
    Low-confidence interpretation is still persisted as provenance so an
    operator can see what the extractor thought it saw, and the row is
    flagged name_needs_review (D-12) for the People directory's Name review
    filter.
    """
    counters = {}
    person = await _resolve_person(
        isolated_session, "adv__cher", "Cher", False, counters
    )
    await isolated_session.flush()

    assert person.first_name is None
    assert person.last_name is None
    assert person.name_needs_review is True
    assert person.name_extraction_metadata is not None
    assert person.name_extraction_metadata["source"] == "import_convokit"
    assert person.name_extraction_metadata["confidence"] == "Low"
    assert person.name_extraction_metadata["auto_applied"] is False
    assert person.name_extraction_metadata["raw"] == "Cher"


@pytest.mark.asyncio
async def test_matched_person_with_operator_edited_parts_never_overwritten(
    isolated_session,
):
    """
    T-38-11 (tampering mitigation): a Person row an operator has already
    given structured parts (that don't even agree with what the splitter
    would derive from full_name) is matched by full_name and never has
    those parts overwritten on reimport -- only name_extraction_metadata is
    refreshed (D-17), demonstrating the operator-edit-then-reimport
    regression this task requires.
    """
    existing = Person(
        full_name="Jane Roe",
        oyez_speaker_id=None,
        is_justice=False,
        first_name="OperatorFirst",
        last_name="OperatorLast",
    )
    isolated_session.add(existing)
    await isolated_session.flush()
    existing_id = existing.id

    counters = {}
    person = await _resolve_person(
        isolated_session, "adv__jane_roe", "Jane Roe", False, counters
    )
    await isolated_session.flush()

    assert person.id == existing_id
    assert person.first_name == "OperatorFirst"
    assert person.last_name == "OperatorLast"
    assert person.oyez_speaker_id == "adv__jane_roe"  # D-11 backfill still happens
    # Metadata still refreshes even though no saved part was eligible to change.
    assert person.name_extraction_metadata is not None
    assert person.name_extraction_metadata["source"] == "import_convokit"


@pytest.mark.asyncio
async def test_matched_person_with_blank_parts_gets_confident_prefill_on_reimport(
    isolated_session,
):
    """
    A Person row matched by full_name that has NO structured parts at all
    yet (e.g. a pre-Phase-38 corpus-imported row) gets a confident
    interpretation's parts prefilled on this run -- distinct from the
    already-has-parts case above, which is never touched (D-16).
    """
    existing = Person(full_name="Jane Roe", oyez_speaker_id=None, is_justice=False)
    isolated_session.add(existing)
    await isolated_session.flush()
    existing_id = existing.id

    counters = {}
    person = await _resolve_person(
        isolated_session, "adv__jane_roe", "Jane Roe", False, counters
    )
    await isolated_session.flush()

    assert person.id == existing_id
    assert person.first_name == "Jane"
    assert person.last_name == "Roe"
    assert person.name_needs_review is False


@pytest.mark.asyncio
async def test_oyez_id_matched_person_metadata_refreshes_full_name_never_touched(
    isolated_session,
):
    """
    D-11/D-13 parity: a Person matched by oyez_speaker_id (not full_name) —
    even one whose stored full_name differs from this run's corpus label —
    still gets its provenance envelope refreshed from its OWN stored
    full_name, and that full_name itself is never rewritten.
    """
    existing = Person(
        full_name="Some Other Name", oyez_speaker_id="adv__jane_roe", is_justice=False
    )
    isolated_session.add(existing)
    await isolated_session.flush()
    existing_id = existing.id

    counters = {}
    person = await _resolve_person(
        isolated_session, "adv__jane_roe", "Jane Roe", False, counters
    )
    await isolated_session.flush()

    assert person.id == existing_id
    assert person.full_name == "Some Other Name"  # never touched
    assert person.name_extraction_metadata["raw"] == "Some Other Name"


# ===========================================================================
# Phase 42 D-01: scoped single-conversation import path
# ===========================================================================


class TestResolveScopedConversation:
    """_resolve_scoped_conversation -- no DB required (pure function over a
    synthetic conversations.json path)."""

    def test_returns_none_when_conversation_id_is_none(self, tmp_path):
        path = tmp_path / "conversations.json"
        path.write_text(json.dumps({}), encoding="utf-8")
        args = argparse.Namespace(conversation_id=None)

        assert _resolve_scoped_conversation(args, path) is None

    def test_returns_none_when_namespace_lacks_attribute_entirely(self, tmp_path):
        """The existing --term/--term-range Namespace shape (no
        conversation_id key at all) must not raise AttributeError."""
        path = tmp_path / "conversations.json"
        path.write_text(json.dumps({}), encoding="utf-8")
        args = argparse.Namespace(term=1966, term_range=None)

        assert _resolve_scoped_conversation(args, path) is None

    def test_raises_argument_type_error_naming_rejected_id_when_absent(self, tmp_path):
        path = tmp_path / "conversations.json"
        path.write_text(
            json.dumps({"15169": {"case_id": "1966_642"}}), encoding="utf-8"
        )
        args = argparse.Namespace(conversation_id="99999999")

        with pytest.raises(argparse.ArgumentTypeError, match="99999999"):
            _resolve_scoped_conversation(args, path)

    def test_derives_term_from_case_id_prefix(self, tmp_path):
        path = tmp_path / "conversations.json"
        path.write_text(
            json.dumps({"15169": {"case_id": "1966_642"}}), encoding="utf-8"
        )
        args = argparse.Namespace(conversation_id="15169")

        assert _resolve_scoped_conversation(args, path) == ("15169", 1966)

    def test_raises_when_case_id_is_missing(self, tmp_path):
        path = tmp_path / "conversations.json"
        path.write_text(json.dumps({"15169": {}}), encoding="utf-8")
        args = argparse.Namespace(conversation_id="15169")

        with pytest.raises(argparse.ArgumentTypeError, match="15169"):
            _resolve_scoped_conversation(args, path)

    def test_raises_when_case_id_has_no_parseable_term_prefix(self, tmp_path):
        path = tmp_path / "conversations.json"
        path.write_text(
            json.dumps({"15169": {"case_id": "not-a-term_642"}}), encoding="utf-8"
        )
        args = argparse.Namespace(conversation_id="15169")

        with pytest.raises(argparse.ArgumentTypeError, match="15169"):
            _resolve_scoped_conversation(args, path)


_CONVERSATIONS_SCOPED_PAIR = {
    "30001": {
        "conversation_id": "30001",
        "case_id": "9997_301",
        "advocates": {"adv__john_smith": {"side": 1}},
    },
    "30002": {
        "conversation_id": "30002",
        "case_id": "9997_302",
        "advocates": {"adv__jane_roe": {"side": 1}},
    },
}
_CASES_SCOPED_PAIR = [
    {
        "id": "9997_301",
        "docket_no": "97-301",
        "title": "Smith v. State",
        "petitioner": "Smith",
        "respondent": "State",
        "year": 9997,
        "transcripts": [{"name": "Oral Argument - November 15, 1997"}],
    },
    {
        "id": "9997_302",
        "docket_no": "97-302",
        "title": "Roe v. State",
        "petitioner": "Roe",
        "respondent": "State",
        "year": 9997,
        "transcripts": [{"name": "Oral Argument - November 20, 1997"}],
    },
]
_SPEAKERS_SCOPED_PAIR = {
    "adv__john_smith": {"name": "John Smith", "type": "advocate"},
    "adv__jane_roe": {"name": "Jane Roe", "type": "advocate"},
}


@pytest.mark.asyncio
async def test_scoped_import_creates_only_the_scoped_conversation(
    isolated_session, tmp_path
):
    """Given two conversations in the same term, scoping to one creates
    exactly one Argument (that one's oyez_transcript_id) -- the sibling
    conversation produces no Argument row at all."""
    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATIONS_SCOPED_PAIR, _CASES_SCOPED_PAIR, _SPEAKERS_SCOPED_PAIR
    )
    args = _scoped_args("30001", corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    scoped_argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "30001")
        )
    ).scalar_one()
    assert scoped_argument.source_docket == "97-301"

    sibling_argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "30002")
        )
    ).scalar_one_or_none()
    assert sibling_argument is None


@pytest.mark.asyncio
async def test_scoped_import_zero_turn_conversation_creates_argument_zero_utterances(
    isolated_session, tmp_path
):
    """A scoped conversation whose utterances.jsonl yields zero matching
    turns still creates its Argument and ImportRun rows, creates zero
    Utterance rows, and raises nothing (empty-input edge item)."""
    conversations = {
        "30003": {
            "conversation_id": "30003",
            "case_id": "9996_400",
            "advocates": {"adv__john_smith": {"side": 1}},
        }
    }
    cases = [
        {
            "id": "9996_400",
            "docket_no": "96-400",
            "title": "Doe v. State",
            "petitioner": "Doe",
            "respondent": "State",
            "year": 9996,
            "transcripts": [{"name": "Oral Argument - November 15, 1996"}],
        }
    ]
    speakers = {"adv__john_smith": {"name": "John Smith", "type": "advocate"}}
    # _write_corpus_fixture writes an empty utterances.jsonl by default --
    # exactly the zero-turn case this test wants.
    corpus_dir = _write_corpus_fixture(tmp_path, conversations, cases, speakers)
    args = _scoped_args("30003", corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)  # must not raise

    argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "30003")
        )
    ).scalar_one()

    run = (
        await isolated_session.execute(
            select(ImportRun).where(ImportRun.argument_id == argument.id)
        )
    ).scalar_one()
    assert run.source == ImportSource.CORPUS
    assert run.method == ImportMethod.DIRECT

    utterance_count = (
        await isolated_session.execute(
            select(func.count())
            .select_from(Utterance)
            .where(Utterance.argument_id == argument.id)
        )
    ).scalar()
    assert utterance_count == 0


@pytest.mark.asyncio
async def test_scoped_import_derives_question_number_via_next_question_number(
    isolated_session, tmp_path
):
    """A docket already occupying question_number=1 (as if from the PDF
    pipeline) does not collide with a scoped corpus import for the same
    docket -- the scoped import lands at question_number=2, derived via
    _next_question_number, never a hardcoded 1 (Phase 29 CR-01)."""
    pdf_case = Case(
        docket_number="97-301",
        docket_number_norm="97301",
        case_name="Smith v. State (PDF ingest)",
        term_year=9997,
        slug="smith-v-state-pdf-ingest",
    )
    isolated_session.add(pdf_case)
    await isolated_session.flush()
    pdf_argument = Argument(
        source_docket="97-301",
        question_number=1,
        status=ArgumentStatusEnum.DRAFT,
    )
    isolated_session.add(pdf_argument)
    await isolated_session.flush()

    corpus_dir = _write_corpus_fixture(
        tmp_path, _CONVERSATIONS_SCOPED_PAIR, _CASES_SCOPED_PAIR, _SPEAKERS_SCOPED_PAIR
    )
    args = _scoped_args("30001", corpus_dir)

    with patch(
        "pipeline.commands.import_convokit.get_session",
        new=_make_session_cm(isolated_session),
    ):
        await run_import_convokit(args)

    scoped_argument = (
        await isolated_session.execute(
            select(Argument).where(Argument.oyez_transcript_id == "30001")
        )
    ).scalar_one()
    assert scoped_argument.question_number == 2
