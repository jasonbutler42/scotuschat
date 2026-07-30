"""
Tests for scripts.diff_corpus_fixture (Phase 42 Plan 03, CORPUS-13).

Covers:
    - Apolitical redaction: every FORBIDDEN_FIELDS sentinel value is absent
      from the generated document, while every forbidden field NAME is
      present and classified as an intentional exclusion (T-42-10).
    - schema-absent field classification for decided_date/citation/court.
    - Proposal-flavored (never a final "real defect") classification for a
      dropped field with no settled category (T-42-13).
    - Parser reuse: the document's raw-side argued_date equals
      import_convokit._parse_argued_date's own return for the same input
      (T-42-12).
    - court_tenures tenure-boundary pair: a tenure starting exactly on the
      argued_date covers it (inclusive start boundary); one starting the
      day after does not.
    - Zero-turn exactness: an empty utterances.jsonl reports 0/0 without
      raising.

Never touches the real dev DB or the real data/corpus/ files -- every test
builds a small synthetic corpus_dir tree under tmp_path (never the real
900MB utterances.jsonl) and seeds rows directly through the isolated_session
fixture (rolled back after the test), patching
scripts.diff_corpus_fixture.get_session so the script under test reads that
same rolled-back session -- exactly like
pipeline/tests/test_delete_fixture_argument.py's established pattern.
"""

from __future__ import annotations

import argparse
import json
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from api.models.models import (
    Argument,
    ArgumentParticipant,
    ArgumentStatusEnum,
    Case,
    CaseArgument,
    CourtTenure,
    Person,
    PipelineRun,
    PipelineRunStatus,
    SideEnum,
)
from pipeline.commands import import_convokit
from pipeline.corpus.apolitical import FORBIDDEN_FIELDS
from scripts import diff_corpus_fixture

# ===========================================================================
# Shared fixtures / helpers
# ===========================================================================


def _make_session_cm(session):
    """Mirrors test_delete_fixture_argument.py's established pattern."""

    @asynccontextmanager
    async def _cm():
        yield session

    return _cm


def patch_get_session(session):
    return patch("scripts.diff_corpus_fixture.get_session", new=_make_session_cm(session))


@pytest.fixture()
async def isolated_session(test_db_url):
    """Function-scoped AsyncSession, rolled back after the test (same shape
    as pipeline/tests/test_delete_fixture_argument.py's identical fixture)."""
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
    utterances: list[dict] | None = None,
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
    with (corpus_dir / "utterances.jsonl").open("w", encoding="utf-8") as f:
        for turn in utterances or []:
            f.write(json.dumps(turn) + "\n")
    return corpus_dir


_CSV_HEADER = (
    "First Name,Middle Name or Initial,Last Name,Suffix,Appointed by,Party,"
    "Judicial Oath Taken,Date Service Terminated,Reason Left,Birthdate,Death Date"
)


def _write_justices_csv(tmp_path: Path, chief_rows: str = "", associate_rows: str = "") -> Path:
    """
    Write a minimal synthetic justices tenure CSV matching
    import_justices_csv.py's two-section format exactly. Empty by default
    -- tests that need a covering/non-covering CSV row pass one in as a
    literal CSV data line.
    """
    csv_path = tmp_path / "justices.csv"
    lines = [
        "Supreme Court Chief Justices",
        _CSV_HEADER,
    ]
    if chief_rows:
        lines.append(chief_rows)
    lines += [
        "",
        "Supreme Court Associate Justices",
        _CSV_HEADER,
    ]
    if associate_rows:
        lines.append(associate_rows)
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path


def _args(conversation_id: str, corpus_dir: Path, justices_csv: Path) -> argparse.Namespace:
    return argparse.Namespace(
        conversation_id=conversation_id,
        corpus_dir=str(corpus_dir),
        out=None,
        justices_csv=str(justices_csv),
    )


async def _seed_case_and_argument(
    session,
    conversation_id: str,
    case_id: str,
    docket: str,
    term_year: int,
    argued_date: date | None,
) -> tuple[Case, Argument]:
    case = Case(
        docket_number=docket,
        docket_number_norm=docket.replace("-", ""),
        case_name=f"Synthetic Case {case_id}",
        term_year=term_year,
        slug=f"synthetic-{case_id}",
        oyez_case_id=case_id,
    )
    session.add(case)
    await session.flush()

    argument = Argument(
        argued_date=argued_date,
        question_number=1,
        source_docket=docket,
        status=ArgumentStatusEnum.PIPELINE,
        oyez_transcript_id=conversation_id,
    )
    session.add(argument)
    await session.flush()

    session.add(CaseArgument(case_id=case.id, argument_id=argument.id, is_lead=True))
    await session.flush()
    return case, argument


async def _seed_bench_participant(
    session, argument_id: int, full_name: str, oyez_speaker_id: str
) -> tuple[Person, ArgumentParticipant]:
    person = Person(full_name=full_name, oyez_speaker_id=oyez_speaker_id, is_justice=True)
    session.add(person)
    await session.flush()

    participant = ArgumentParticipant(
        argument_id=argument_id,
        person_id=person.id,
        raw_speaker_label=full_name,
        side=SideEnum.BENCH,
    )
    session.add(participant)
    await session.flush()
    return person, participant


# ===========================================================================
# Shared fixture: one synthetic conversation whose raw case carries every
# FORBIDDEN_FIELDS name (with a distinctive sentinel value each) plus the
# pre-known schema-absent trio and one field dropped-before-the-allowlist
# with no settled category.
# ===========================================================================

_CONVERSATION_ID = "9999_1"
_CASE_ID = "9999_1"
_DOCKET = "99-1"
_TERM_YEAR = 1999
_TRANSCRIPT_NAME = "Oral Argument - March 02, 1970"


def _sentinel_case_fields() -> dict:
    case: dict = {
        "id": _CASE_ID,
        "docket_no": _DOCKET,
        "year": _TERM_YEAR,
        "title": "Synthetic v. Fixture",
        "petitioner": "Synthetic",
        "respondent": "Fixture",
        "transcripts": [{"id": _CONVERSATION_ID, "name": _TRANSCRIPT_NAME}],
        "advocates": {},
        "decided_date": "2000-01-01",
        "citation": "999 US 1",
        "court": "Synthetic Court",
        # Dropped before the allowlist -- not in FORBIDDEN_FIELDS, not read
        # by extract_case_fields -- a proposal-flavored classification is
        # the only thing this script may ever emit for it.
        "url": "https://example.invalid/synthetic",
    }
    for name in FORBIDDEN_FIELDS:
        case[name] = f"SENTINEL-{name.upper()}-VALUE"
    return case


@pytest.fixture()
async def redacted_fixture_document(isolated_session, tmp_path):
    """
    Build the one shared synthetic fixture used by the redaction /
    schema-absent / proposal-classification / parser-reuse tests, and
    return the generated markdown document text.
    """
    raw_case = _sentinel_case_fields()
    conversations = {
        _CONVERSATION_ID: {
            "case_id": _CASE_ID,
            "advocates": {},
            "win_side": "SENTINEL-CONVERSATION-WIN_SIDE-VALUE",
            "votes_side": "SENTINEL-CONVERSATION-VOTES_SIDE-VALUE",
        }
    }
    speakers: dict = {}
    corpus_dir = _write_corpus_fixture(
        tmp_path, conversations, [raw_case], speakers, utterances=[]
    )
    justices_csv = _write_justices_csv(tmp_path)

    argued_date = import_convokit._parse_argued_date(
        {"transcripts": raw_case["transcripts"]}, _CONVERSATION_ID
    )
    await _seed_case_and_argument(
        isolated_session, _CONVERSATION_ID, _CASE_ID, _DOCKET, _TERM_YEAR, argued_date
    )

    args = _args(_CONVERSATION_ID, corpus_dir, justices_csv)
    with patch_get_session(isolated_session):
        document = await diff_corpus_fixture._run(args)
    return document


# ===========================================================================
# Redaction (T-42-10)
# ===========================================================================


class TestApoliticalRedaction:
    async def test_every_forbidden_field_sentinel_value_is_absent(
        self, redacted_fixture_document
    ):
        for name in FORBIDDEN_FIELDS:
            sentinel = f"SENTINEL-{name.upper()}-VALUE"
            assert sentinel not in redacted_fixture_document, (
                f"forbidden field {name!r}'s sentinel value leaked into the document"
            )
        assert "SENTINEL-CONVERSATION-WIN_SIDE-VALUE" not in redacted_fixture_document
        assert "SENTINEL-CONVERSATION-VOTES_SIDE-VALUE" not in redacted_fixture_document

    async def test_every_forbidden_field_name_is_classified_as_intentional_exclusion(
        self, redacted_fixture_document
    ):
        for name in FORBIDDEN_FIELDS:
            # The field NAME must appear, immediately followed (same table
            # row) by the settled "apolitical allow-list exclusion" tag --
            # never a bare mention with no classification attached.
            idx = redacted_fixture_document.find(f"| {name} ")
            assert idx != -1, f"forbidden field name {name!r} not listed anywhere"
            row_end = redacted_fixture_document.find("\n", idx)
            row_text = redacted_fixture_document[idx:row_end]
            assert "apolitical allow-list exclusion" in row_text

    async def test_no_forbidden_field_is_ever_classified_as_a_real_defect(
        self, redacted_fixture_document
    ):
        # Scoped to each forbidden field's OWN row -- "real defect" also
        # appears elsewhere in the document as part of a legitimate
        # "PROPOSED -- ... real defect candidate" proposal phrase (e.g.
        # section_hint), which is not what this assertion is about.
        for name in FORBIDDEN_FIELDS:
            idx = redacted_fixture_document.find(f"| {name} ")
            assert idx != -1
            row_end = redacted_fixture_document.find("\n", idx)
            row_text = redacted_fixture_document[idx:row_end]
            assert "real defect" not in row_text.lower()


# ===========================================================================
# schema-absent field classification
# ===========================================================================


class TestSchemaAbsentClassification:
    async def test_decided_date_citation_court_are_schema_absent(
        self, redacted_fixture_document
    ):
        for name in ("decided_date", "citation", "court"):
            idx = redacted_fixture_document.find(f"| {name} ")
            assert idx != -1, f"{name} row not found"
            row_end = redacted_fixture_document.find("\n", idx)
            row_text = redacted_fixture_document[idx:row_end]
            assert "Dropped" in row_text
            assert "schema-absent field" in row_text


# ===========================================================================
# Proposal-flavored classification (D-05/T-42-13) -- never a bare "real
# defect" for a dropped field with no settled category.
# ===========================================================================


class TestProposalClassification:
    async def test_dropped_field_with_no_settled_category_is_proposed_not_final(
        self, redacted_fixture_document
    ):
        idx = redacted_fixture_document.find("| url ")
        assert idx != -1, "url row not found"
        row_end = redacted_fixture_document.find("\n", idx)
        row_text = redacted_fixture_document[idx:row_end]
        assert "PROPOSED" in row_text
        assert "real defect" not in row_text.lower()


# ===========================================================================
# Parser reuse (T-42-12) -- the document's raw-side argued_date must equal
# import_convokit._parse_argued_date's own return for the same input, never
# an independent date parse.
# ===========================================================================


class TestParserReuse:
    async def test_argued_date_matches_parse_argued_date_return(
        self, redacted_fixture_document
    ):
        expected = import_convokit._parse_argued_date(
            {"transcripts": [{"id": _CONVERSATION_ID, "name": _TRANSCRIPT_NAME}]},
            _CONVERSATION_ID,
        )
        assert expected == date(1970, 3, 2)
        assert str(expected) in redacted_fixture_document
        assert (
            f"import_convokit._parse_argued_date(case_fields, {_CONVERSATION_ID!r}) -> {expected}"
            in redacted_fixture_document
        )


# ===========================================================================
# court_tenures tenure-boundary pair (inclusive start boundary)
# ===========================================================================

_TENURE_CONVERSATION_ID = "9998_1"
_TENURE_CASE_ID = "9998_1"
_TENURE_DOCKET = "99-2"
_TENURE_TERM_YEAR = 1999
_TENURE_TRANSCRIPT_NAME = "Oral Argument - March 02, 1970"
_TENURE_ARGUED_DATE = date(1970, 3, 2)
_TENURE_JUSTICE_NAME = "Xyzzy Testjustice"
_TENURE_SPEAKER_ID = "j__xyzzy_testjustice"


async def _build_tenure_boundary_document(
    isolated_session, tmp_path, tenure_start_date: date
) -> str:
    raw_case = {
        "id": _TENURE_CASE_ID,
        "docket_no": _TENURE_DOCKET,
        "year": _TENURE_TERM_YEAR,
        "title": "Synthetic Tenure Case",
        "transcripts": [{"id": _TENURE_CONVERSATION_ID, "name": _TENURE_TRANSCRIPT_NAME}],
        "advocates": {},
    }
    conversations = {
        _TENURE_CONVERSATION_ID: {"case_id": _TENURE_CASE_ID, "advocates": {}}
    }
    speakers = {_TENURE_SPEAKER_ID: {"name": _TENURE_JUSTICE_NAME, "type": "justice"}}
    corpus_dir = _write_corpus_fixture(tmp_path, conversations, [raw_case], speakers, utterances=[])
    justices_csv = _write_justices_csv(tmp_path)  # no matching row -- CSV corroborates the DB

    _, argument = await _seed_case_and_argument(
        isolated_session,
        _TENURE_CONVERSATION_ID,
        _TENURE_CASE_ID,
        _TENURE_DOCKET,
        _TENURE_TERM_YEAR,
        _TENURE_ARGUED_DATE,
    )
    person, _participant = await _seed_bench_participant(
        isolated_session, argument.id, _TENURE_JUSTICE_NAME, _TENURE_SPEAKER_ID
    )
    isolated_session.add(
        CourtTenure(person_id=person.id, office="associate", start_date=tenure_start_date, end_date=None)
    )
    await isolated_session.flush()

    args = _args(_TENURE_CONVERSATION_ID, corpus_dir, justices_csv)
    with patch_get_session(isolated_session):
        return await diff_corpus_fixture._run(args)


def _court_tenures_row_for(document: str, justice_name: str) -> str:
    """
    Return the one court_tenures-section row mentioning justice_name.
    justice_name also appears verbatim in the people/argument_participants
    sections (as raw_speaker_label/full_name), so a plain document.find()
    would latch onto the wrong section -- this scopes the search to the
    court_tenures table specifically.
    """
    section_start = document.index("## court_tenures")
    section_end = document.index("## Volume and Roster Exactness", section_start)
    section_text = document[section_start:section_end]
    idx = section_text.index(justice_name)
    row_end = section_text.find("\n", idx)
    return section_text[idx:row_end]


class TestCourtTenureBoundary:
    async def test_tenure_starting_exactly_on_argued_date_covers_it(
        self, isolated_session, tmp_path
    ):
        document = await _build_tenure_boundary_document(
            isolated_session, tmp_path, _TENURE_ARGUED_DATE
        )
        row_text = _court_tenures_row_for(document, _TENURE_JUSTICE_NAME)
        assert "Faithful" in row_text
        assert "integrity check passed" in row_text

    async def test_tenure_starting_the_day_after_argued_date_does_not_cover_it(
        self, isolated_session, tmp_path
    ):
        from datetime import timedelta

        document = await _build_tenure_boundary_document(
            isolated_session, tmp_path, _TENURE_ARGUED_DATE + timedelta(days=1)
        )
        row_text = _court_tenures_row_for(document, _TENURE_JUSTICE_NAME)
        assert "Mis-mapped" in row_text
        assert "bench-classification anomaly to investigate" in row_text


# ===========================================================================
# Zero-turn exactness -- must not raise, must report 0/0.
# ===========================================================================


class TestZeroTurnExactness:
    async def test_zero_utterance_turns_reports_zero_without_raising(
        self, isolated_session, tmp_path
    ):
        conversation_id = "9997_1"
        case_id = "9997_1"
        raw_case = {
            "id": case_id,
            "docket_no": "99-3",
            "year": 1999,
            "title": "Synthetic Zero-Turn Case",
            "transcripts": [{"id": conversation_id, "name": "Oral Argument - March 02, 1970"}],
            "advocates": {},
        }
        conversations = {conversation_id: {"case_id": case_id, "advocates": {}}}
        corpus_dir = _write_corpus_fixture(
            tmp_path, conversations, [raw_case], {}, utterances=[]
        )
        justices_csv = _write_justices_csv(tmp_path)

        await _seed_case_and_argument(
            isolated_session, conversation_id, case_id, "99-3", 1999, date(1970, 3, 2)
        )

        args = _args(conversation_id, corpus_dir, justices_csv)
        with patch_get_session(isolated_session):
            document = await diff_corpus_fixture._run(args)

        assert (
            "Raw source turns for this conversation (streamed from the utterance "
            "stream via the loader): **0**" in document
        )
        assert "Imported Utterance rows: **0**" in document
