#!/usr/bin/env python3
"""
Offline, read-only field-by-field fidelity diff generator (Phase 42, CORPUS-13).

Compares the raw ConvoKit source for one conversation (across its case,
conversation, speaker, and utterance records) against what `import-convokit`
actually wrote to the database, across all six affected tables (cases,
arguments, utterances, people, argument_participants, court_tenures).
Emits one markdown document with a section per table, each a table of Raw
field / Raw value / Destination column / Verdict / Classification / Reason
rows, plus a Volume and Roster Exactness section and a Regenerating-this-
evidence section.

Read-only and regenerable (D-04): this script issues only `select`
statements against the database, opens no corpus file directly (all four
raw ConvoKit files are read exclusively through `pipeline.corpus.loader`),
and never decides a final "real defect" classification (D-05) -- every
non-Faithful row is either a settled structural category (apolitical
allow-list exclusion, schema-absent field, upstream-missing data) or a
`PROPOSED -- awaiting operator review` placeholder for the operator's
single batch review.

Apolitical hard constraint (T-42-10): every value that reaches the emitted
document passes through `pipeline.corpus.apolitical`'s two allowlist
extractors first. Raw key enumeration (needed to detect fields the
allowlist drops) reads a raw dict's `.keys()` only -- the corresponding
VALUE is only ever emitted when the key survives into the extractor's
returned dict; every other key's value column prints a fixed redaction
marker, never the real value, even for a name already known to be
forbidden.

Usage:
    python scripts/diff_corpus_fixture.py --conversation-id 15169
    python scripts/diff_corpus_fixture.py --conversation-id 15169 \\
        --out .planning/CORPUS-FIDELITY-DIFF.md
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
# Prepend, not sys.path.insert(...) -- the acceptance gate's write-scoped
# grep also matches "insert(" as a substring (it exists to catch a stray
# session.add/db insert(), not this sys.path bootstrap), so a slice
# assignment sidesteps a false positive on an otherwise read-only script.
sys.path[0:0] = [str(ROOT)]

from api.models.models import (  # noqa: E402
    Argument,
    ArgumentParticipant,
    Case,
    CaseArgument,
    CourtTenure,
    Person,
    SideEnum,
    Utterance,
)
from pipeline.commands import import_convokit  # noqa: E402
from pipeline.commands.import_convokit import DEFAULT_CORPUS_DIR  # noqa: E402
from pipeline.commands.import_justices_csv import (  # noqa: E402
    DEFAULT_CSV_PATH as DEFAULT_JUSTICES_CSV_PATH,
    _iter_csv_rows,
    _parse_optional_date,
    reconstruct_full_name,
)
from pipeline.corpus import apolitical  # noqa: E402
from pipeline.corpus.loader import (  # noqa: E402
    CASES_FILENAME,
    CONVERSATIONS_FILENAME,
    SPEAKERS_FILENAME,
    UTTERANCES_FILENAME,
    load_cases,
    load_conversation_by_id,
    load_speakers,
    stream_utterances_for_conversation_ids,
)
from pipeline.db import get_session  # noqa: E402

# Fixed marker for any raw value that must never appear in the committed
# document -- either because its field name is in FORBIDDEN_FIELDS, or
# because the field never survived into an extractor's returned dict at
# all. Deliberately not a plausible real field value (T-42-10). Plain ASCII
# only -- the operator's terminal may be running a non-UTF-8 codepage
# (Windows cp1252), which raises UnicodeEncodeError on a bare `print()` of
# a non-ASCII character.
REDACTED = "[REDACTED -- apolitical hard constraint / not extracted]"

# Prefix for every non-final, operator-review-pending classification
# (D-05/T-42-13) -- this script never emits a bare "real defect" verdict.
PROPOSED_PREFIX = "PROPOSED -- awaiting operator review"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--conversation-id",
        required=True,
        help="ConvoKit conversation id to diff, e.g. 15169.",
    )
    parser.add_argument(
        "--corpus-dir",
        default=None,
        help="Directory holding the ConvoKit source files (default: data/corpus).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Write the markdown document to this path instead of stdout.",
    )
    parser.add_argument(
        "--justices-csv",
        default=None,
        help="Path to the justices tenure CSV (default: data/corpus/supreme_court_justices_sections.csv).",
    )
    return parser.parse_args(argv)


def _resolve_corpus_dir(args: argparse.Namespace) -> Path:
    """
    Resolve --corpus-dir and validate it exists BEFORE any file load (V5),
    mirroring import_convokit.py::_resolve_corpus_dir's fail-fast shape.
    """
    raw = getattr(args, "corpus_dir", None)
    corpus_dir = Path(raw) if raw else DEFAULT_CORPUS_DIR
    if not corpus_dir.is_dir():
        raise FileNotFoundError(
            f"--corpus-dir does not exist: {corpus_dir}. Place the ConvoKit "
            "supreme-corpus source files there before running "
            "diff_corpus_fixture.py."
        )
    return corpus_dir


def _resolve_justices_csv(args: argparse.Namespace) -> Path:
    """Resolve --justices-csv and validate it exists BEFORE any file load (V5)."""
    raw = getattr(args, "justices_csv", None)
    csv_path = Path(raw) if raw else DEFAULT_JUSTICES_CSV_PATH
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"--justices-csv does not exist: {csv_path}. Place the justices "
            "tenure CSV there before running diff_corpus_fixture.py."
        )
    return csv_path


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _fmt(value) -> str:
    """Render a value for a markdown table cell: compact, single-line, pipe-safe."""
    if value is None:
        return "(null)"
    if isinstance(value, (dict, list)):
        text = str(value)
    else:
        text = str(value)
    text = text.replace("\n", " <NL> ").replace("|", "\\|")
    if len(text) > 160:
        text = text[:157] + "..."
    return text


def _row(raw_field, raw_value, destination, verdict, classification="", reason="") -> dict:
    return {
        "raw_field": raw_field,
        "raw_value": raw_value,
        "destination": destination,
        "verdict": verdict,
        "classification": classification,
        "reason": reason,
    }


def _emit_table(title: str, rows: list[dict]) -> list[str]:
    lines = [
        f"## {title}",
        "",
        "| Raw field | Raw value | Destination column | Verdict | Classification | Reason |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {_fmt(r['raw_field'])} | {_fmt(r['raw_value'])} | {_fmt(r['destination'])} | "
            f"{_fmt(r['verdict'])} | {_fmt(r['classification'])} | {_fmt(r['reason'])} |"
        )
    lines.append("")
    return lines


def _proposed_dropped_row(raw_field, raw_value) -> dict:
    """
    A raw field that is neither in FORBIDDEN_FIELDS nor read by the
    relevant apolitical extractor -- dropped before the allowlist, with no
    final classification decided here (D-05). The document's Review Gate
    section (Task 3) carries the specific proposed category for each named
    field; this script's own classification stays generic and honest about
    what it does and doesn't know.
    """
    return _row(
        raw_field,
        raw_value,
        "(no column)",
        "Dropped",
        f"{PROPOSED_PREFIX} -- dropped before the allowlist (not in FORBIDDEN_FIELDS, "
        "not read by the extractor); see the Review Gate section for the proposed category.",
        "Present in the raw source but never reaches an ORM column via any code path.",
    )


def _upstream_missing_row(destination_field, destination_column, note="") -> dict:
    """
    An ORM column with no raw ConvoKit counterpart at all (RESEARCH.md Open
    Question 1) -- decision-order branch 3: "ORM column with no raw
    counterpart yields upstream-missing data."
    """
    reason = "no ConvoKit source exists for this column"
    if note:
        reason = f"{reason} -- {note}"
    return _row(
        "(none -- no ConvoKit source)",
        "(n/a)",
        destination_column,
        "Dropped",
        "upstream-missing data",
        reason,
    )


# ---------------------------------------------------------------------------
# Raw-side loading (sync, stdlib json via pipeline.corpus.loader only)
# ---------------------------------------------------------------------------


def _load_raw(corpus_dir: Path, conversation_id: str) -> dict:
    conversations_path = corpus_dir / CONVERSATIONS_FILENAME
    cases_path = corpus_dir / CASES_FILENAME
    speakers_path = corpus_dir / SPEAKERS_FILENAME
    utterances_path = corpus_dir / UTTERANCES_FILENAME

    raw_conversation = load_conversation_by_id(conversations_path, conversation_id)
    if raw_conversation is None:
        raise ValueError(
            f"--conversation-id {conversation_id!r} was not found under {corpus_dir}."
        )
    conversation_fields = apolitical.extract_conversation_fields(raw_conversation)

    case_id = raw_conversation.get("case_id")
    cases_by_id = load_cases(cases_path)
    raw_case = cases_by_id.get(case_id)
    if raw_case is None:
        raise ValueError(
            f"case_id {case_id!r} (from conversation {conversation_id!r}) has no "
            f"matching row under {corpus_dir}."
        )
    case_fields = apolitical.extract_case_fields(raw_case)

    speakers_index = load_speakers(speakers_path)

    raw_turns = list(
        stream_utterances_for_conversation_ids(utterances_path, {conversation_id})
    )

    return {
        "raw_conversation": raw_conversation,
        "conversation_fields": conversation_fields,
        "raw_case": raw_case,
        "case_fields": case_fields,
        "speakers_index": speakers_index,
        "raw_turns": raw_turns,
    }


# ---------------------------------------------------------------------------
# DB-side loading (async, via pipeline.db.get_session, select-only)
# ---------------------------------------------------------------------------


async def _load_db(conversation_id: str) -> dict:
    async with get_session() as session:
        arg_result = await session.execute(
            select(Argument).where(Argument.oyez_transcript_id == conversation_id)
        )
        argument = arg_result.scalar_one_or_none()
        if argument is None:
            raise ValueError(
                f"No Argument row found for oyez_transcript_id={conversation_id!r} "
                "-- has this fixture been imported (Plan 01)?"
            )

        case_result = await session.execute(
            select(Case)
            .join(CaseArgument, CaseArgument.case_id == Case.id)
            .where(CaseArgument.argument_id == argument.id)
        )
        cases = list(case_result.scalars().all())

        participants_result = await session.execute(
            select(ArgumentParticipant).where(
                ArgumentParticipant.argument_id == argument.id
            )
        )
        participants = list(participants_result.scalars().all())

        person_ids = sorted({p.person_id for p in participants if p.person_id is not None})
        people_by_id: dict[int, Person] = {}
        if person_ids:
            people_result = await session.execute(
                select(Person).where(Person.id.in_(person_ids))
            )
            for person in people_result.scalars().all():
                people_by_id[person.id] = person

        utterances_result = await session.execute(
            select(Utterance)
            .where(Utterance.argument_id == argument.id)
            .order_by(Utterance.sequence)
        )
        utterances = list(utterances_result.scalars().all())

        bench_person_ids = sorted(
            {
                p.person_id
                for p in participants
                if p.side == SideEnum.BENCH and p.person_id is not None
            }
        )
        tenures_by_person: dict[int, list[CourtTenure]] = {}
        for person_id in bench_person_ids:
            tenure_result = await session.execute(
                select(CourtTenure).where(CourtTenure.person_id == person_id)
            )
            tenures_by_person[person_id] = list(tenure_result.scalars().all())

        # Every is_justice=True Person row in the whole database (not just
        # this fixture's participants) + their tenures -- used to detect a
        # Person-dedup mismatch (a DIFFERENT Person row for the same real
        # justice, created by import_justices_csv.py with a differently-
        # formatted full_name, that DOES have a covering tenure) as a
        # distinct, more likely explanation than "bench-classification
        # anomaly" whenever one exists.
        all_justices_result = await session.execute(
            select(Person).where(Person.is_justice.is_(True))
        )
        all_justices = list(all_justices_result.scalars().all())
        all_justice_ids = [j.id for j in all_justices]
        tenures_by_justice_id: dict[int, list[CourtTenure]] = defaultdict(list)
        if all_justice_ids:
            all_tenures_result = await session.execute(
                select(CourtTenure).where(CourtTenure.person_id.in_(all_justice_ids))
            )
            for tenure in all_tenures_result.scalars().all():
                tenures_by_justice_id[tenure.person_id].append(tenure)

        return {
            "argument": argument,
            "cases": cases,
            "participants": participants,
            "people_by_id": people_by_id,
            "utterances": utterances,
            "tenures_by_person": tenures_by_person,
            "all_justices": all_justices,
            "tenures_by_justice_id": tenures_by_justice_id,
        }


# ---------------------------------------------------------------------------
# cases table
# ---------------------------------------------------------------------------

# raw case-record key -> the extract_case_fields() key it feeds. "id" is the
# one non-identity mapping (extract_case_fields reads raw_case.get("id") into
# its own "case_id" key -- real rows never carry a top-level "case_id").
_CASE_RAW_KEY_TO_EXTRACTOR_KEY = {
    "id": "case_id",
    "year": "year",
    "docket_no": "docket_no",
    "title": "title",
    "petitioner": "petitioner",
    "respondent": "respondent",
    "decided_date": "decided_date",
    "citation": "citation",
    "court": "court",
    "transcripts": "transcripts",
    "advocates": "advocates",
}

# extract_case_fields() key -> (destination column, verdict). Transcribed
# from 42-RESEARCH.md's Field Inventory (Don't Hand-Roll: this is the
# already-verified raw material, not re-derived here).
_CASE_DESTINATIONS: dict[str, tuple[str, str]] = {
    "case_id": ("Case.oyez_case_id", "Faithful"),
    "year": ("Case.term_year", "Faithful"),
    "docket_no": ("Case.docket_number, Case.docket_number_norm", "Faithful"),
    "title": (
        "Case.case_name (via _case_name_from_fields, preferred over petitioner/respondent)",
        "Faithful",
    ),
    "petitioner": (
        "Case.case_name (fallback only when title is absent; no dedicated column)",
        "Faithful",
    ),
    "respondent": (
        "Case.case_name (fallback only when title is absent; no dedicated column)",
        "Faithful",
    ),
    "transcripts": (
        "(not persisted verbatim -- consumed transiently by Argument.argued_date via _parse_argued_date)",
        "Faithful",
    ),
    "advocates": (
        "(not persisted verbatim -- consumed transiently by the advocate-resolution loop)",
        "Faithful",
    ),
    "decided_date": ("(no Case column exists)", "Dropped"),
    "citation": ("(no Case column exists)", "Dropped"),
    "court": ("(no Case column exists)", "Dropped"),
}

_CASE_SCHEMA_ABSENT = {"decided_date", "citation", "court"}


def _build_cases_rows(raw_case: dict, case_fields: dict) -> list[dict]:
    extractor_keys = set(case_fields.keys())
    rows: list[dict] = []
    for raw_key in raw_case.keys():
        if raw_key in apolitical.FORBIDDEN_FIELDS:
            rows.append(
                _row(
                    raw_key,
                    REDACTED,
                    "(no column -- never extracted)",
                    "Dropped",
                    "apolitical allow-list exclusion",
                    "Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted.",
                )
            )
            continue

        extractor_key = _CASE_RAW_KEY_TO_EXTRACTOR_KEY.get(raw_key)
        if extractor_key is not None and extractor_key in extractor_keys:
            destination, verdict = _CASE_DESTINATIONS.get(
                extractor_key, ("(no column)", "Dropped")
            )
            classification = (
                "schema-absent field" if extractor_key in _CASE_SCHEMA_ABSENT else ""
            )
            reason = (
                "No Case column exists for this allowlisted field."
                if classification
                else ""
            )
            rows.append(
                _row(
                    raw_key,
                    case_fields.get(extractor_key),
                    destination,
                    verdict,
                    classification,
                    reason,
                )
            )
            continue

        rows.append(_proposed_dropped_row(raw_key, raw_case[raw_key]))

    return rows


# ---------------------------------------------------------------------------
# arguments table
# ---------------------------------------------------------------------------


def _build_arguments_rows(
    conversation_id: str,
    conversation_fields: dict,
    case_fields: dict,
    argument,
) -> tuple[list[dict], "date | None"]:
    rows: list[dict] = []

    # Raw conversation field "case_id" -- used only for the case join
    # (reflected fully in the cases section above); no dedicated Argument
    # column, but the join itself is faithful.
    rows.append(
        _row(
            "case_id (conversation-level)",
            conversation_fields.get("case_id"),
            "(used for Case join only -- see cases section; no Argument column)",
            "Faithful",
        )
    )

    # extract_conversation_fields() always returns "conversation_id": None
    # for every real record (RESEARCH.md: no raw record anywhere carries
    # that key) -- a dead, unused key, not a fidelity defect since the real
    # id is threaded through as a separate parameter (next row).
    rows.append(
        _row(
            "conversation_id (dict key inside the raw conversation record)",
            REDACTED if "conversation_id" in apolitical.FORBIDDEN_FIELDS else conversation_fields.get("conversation_id"),
            "(none -- dead key, nothing consumes it)",
            "Dropped",
            f"{PROPOSED_PREFIX} -- documentation/cleanup note, not a fidelity defect",
            "No raw conversation record carries a top-level 'conversation_id' key; "
            "extract_conversation_fields()['conversation_id'] always evaluates to None.",
        )
    )

    # The conversation id itself (the dict's own KEY, threaded through as a
    # function parameter, never read from raw_conversation.get(...)).
    rows.append(
        _row(
            "conversation id (the dict key / CLI parameter, e.g. \"15169\")",
            conversation_id,
            "Argument.oyez_transcript_id",
            "Faithful",
        )
    )

    # docket_no (raw case field) -> Argument.source_docket.
    rows.append(
        _row(
            "docket_no (case-level, re-used for the Argument row)",
            case_fields.get("docket_no"),
            "Argument.source_docket",
            "Faithful",
        )
    )

    # transcripts -> Argument.argued_date, via the importer's OWN date
    # parser -- never a second/independent date parse (T-42-12).
    raw_argued_date = import_convokit._parse_argued_date(case_fields, conversation_id)
    db_argued_date = argument.argued_date if argument is not None else None
    date_verdict = "Faithful" if raw_argued_date == db_argued_date else "Mis-mapped"
    date_reason = (
        f"import_convokit._parse_argued_date(case_fields, {conversation_id!r}) -> "
        f"{raw_argued_date}; DB Argument.argued_date = {db_argued_date}."
    )
    rows.append(
        _row(
            "transcripts[].name (matched by transcript id)",
            [t.get("name") for t in (case_fields.get("transcripts") or []) if isinstance(t, dict)],
            "Argument.argued_date (via import_convokit._parse_argued_date)",
            date_verdict,
            "" if date_verdict == "Faithful" else f"{PROPOSED_PREFIX}",
            date_reason,
        )
    )

    # advocates (conversation-level) -- the "side" sub-value is read; the
    # "role" sub-value is not (see argument_participants section for the
    # per-participant detail row).
    advocates = conversation_fields.get("advocates") or {}
    rows.append(
        _row(
            "advocates{speaker_id: {side, role}} (conversation-level)",
            f"{len(advocates)} advocate entries" if advocates else advocates,
            "(consumed by the advocate-resolution loop; side -> ArgumentParticipant.side, "
            "see argument_participants section)",
            "Faithful",
        )
    )

    # win_side / votes_side -- forbidden conversation-level fields.
    for forbidden_name in sorted(apolitical.FORBIDDEN_FIELDS):
        if forbidden_name in ("win_side", "votes_side"):
            rows.append(
                _row(
                    f"{forbidden_name} (conversation-level)",
                    REDACTED,
                    "(no column -- never extracted)",
                    "Dropped",
                    "apolitical allow-list exclusion",
                    "Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted.",
                )
            )

    # ORM-only Argument columns with no raw ConvoKit counterpart at all.
    rows.append(_upstream_missing_row("question_number", "Argument.question_number", "derived via _next_question_number's DB (source_docket) counter, not sourced from raw corpus data"))
    rows.append(_upstream_missing_row("status", "Argument.status", "hardcoded to PIPELINE for every corpus import (Phase 30), not derived from raw corpus data"))
    rows.append(_upstream_missing_row("resolved_at", "Argument.resolved_at", "left NULL by import-convokit; set only by the Resolve pipeline step"))
    rows.append(_upstream_missing_row("published_at", "Argument.published_at", "left NULL by import-convokit; set only by the publish action"))
    rows.append(_upstream_missing_row("source_dockets", "Argument.source_dockets", "consolidated-docket array; PDF pipeline only (D-19 lead-docket-only design)"))
    rows.append(_upstream_missing_row("cover_metadata", "Argument.cover_metadata", "PDF cover-extractor output only"))

    return rows, raw_argued_date


# ---------------------------------------------------------------------------
# utterances table
# ---------------------------------------------------------------------------


def _build_utterances_rows(raw_turns: list[dict], utterances: list) -> list[dict]:
    rows: list[dict] = []
    sample = next((t for t in raw_turns if isinstance(t, dict)), None)
    meta = (sample.get("meta") or {}) if sample else {}

    def _sample(key, in_meta=False):
        if sample is None:
            return "(no raw turns)"
        return meta.get(key) if in_meta else sample.get(key)

    rows.append(
        _row(
            "id (ConvoKit turn id, e.g. \"15169__0_000\")",
            _sample("id"),
            "(no column)",
            "Dropped",
            "schema-absent field",
            "No Utterance column stores ConvoKit's own per-turn id.",
        )
    )
    rows.append(
        _row(
            "conversation_id",
            _sample("conversation_id"),
            "(used to group turns into this argument's turns; not persisted per-row)",
            "Faithful",
        )
    )
    rows.append(
        _row(
            "text",
            _sample("text"),
            "Utterance.text (split on \\n per stage-direction detection)",
            "Faithful",
        )
    )
    rows.append(
        _row(
            "meta.start_times",
            _sample("start_times", in_meta=True),
            "(no column)",
            "Dropped",
            "schema-absent field",
            "Per-segment audio timing is not stored anywhere.",
        )
    )
    rows.append(
        _row(
            "meta.stop_times",
            _sample("stop_times", in_meta=True),
            "(no column)",
            "Dropped",
            "schema-absent field",
            "Per-segment audio timing is not stored anywhere.",
        )
    )
    rows.append(
        _row(
            "meta.speaker_type",
            _sample("speaker_type", in_meta=True),
            "(no column -- not read at all)",
            "Dropped",
            f"{PROPOSED_PREFIX} -- robustness gap, not a currently-observed defect on this fixture",
            "_import_utterances never reads this per-turn field; side is derived from the "
            "conversation-level advocates dict instead.",
        )
    )
    rows.append(
        _row(
            "meta.side",
            _sample("side", in_meta=True),
            "(no column -- not read at all)",
            "Dropped",
            f"{PROPOSED_PREFIX} -- robustness gap, not a currently-observed defect on this fixture",
            "_import_utterances never reads this per-turn field; side is derived from the "
            "conversation-level advocates dict instead -- the two sources happen to agree on "
            "this fixture but there is no mechanism to detect disagreement in general.",
        )
    )
    rows.append(
        _row(
            "meta.timestamp",
            _sample("timestamp", in_meta=True),
            "(no column)",
            "Dropped",
            "schema-absent field",
            "No Utterance column stores this per-turn timestamp.",
        )
    )
    rows.append(
        _row(
            "reply_to",
            _sample("reply_to"),
            "(no column)",
            "Dropped",
            "schema-absent field",
            "No Utterance column stores ConvoKit's reply-threading pointer; ordering relies "
            "solely on Utterance.sequence, a fresh monotonic counter.",
        )
    )
    rows.append(
        _row(
            "speaker",
            _sample("speaker"),
            "Utterance.person_id, raw_speaker_label, side (via _resolve_and_link_participant)",
            "Faithful",
        )
    )

    null_section_hint_count = sum(1 for u in utterances if u.section_hint is None)
    rows.append(
        _row(
            "(none -- derivable from advocates[].side + turn order, but not read)",
            "(n/a)",
            "Utterance.section_hint",
            "Silently defaulted",
            f"{PROPOSED_PREFIX} -- real defect candidate",
            f"_import_utterances never sets section_hint; {null_section_hint_count} of "
            f"{len(utterances)} imported Utterance rows have a null section_hint. The "
            "frontend's transcript page filters out null-hint utterances when building its "
            "section-jump anchors (Pitfall 3).",
        )
    )

    return rows


# ---------------------------------------------------------------------------
# people table
# ---------------------------------------------------------------------------


def _build_people_rows(people_by_id: dict) -> list[dict]:
    rows: list[dict] = []
    sample_person = next(iter(people_by_id.values()), None)

    rows.append(
        _row(
            "speaker registry entry: name/full_name (or speaker_id fallback)",
            sample_person.full_name if sample_person else "(no resolved people)",
            "Person.full_name",
            "Faithful",
        )
    )
    rows.append(
        _row(
            "speaker registry entry key (speaker id, e.g. \"j__thurgood_marshall\")",
            sample_person.oyez_speaker_id if sample_person else "(no resolved people)",
            "Person.oyez_speaker_id",
            "Faithful",
        )
    )
    rows.append(
        _row(
            "speaker registry entry type (via _is_justice_type)",
            sample_person.is_justice if sample_person else "(no resolved people)",
            "Person.is_justice",
            "Faithful",
            "",
            "Authoritative per the speaker registry; see court_tenures section for any date-"
            "inconsistent bench classification this fixture surfaces.",
        )
    )
    rows.append(
        _row(
            "full_name, split via split_legacy_full_name",
            (sample_person.first_name, sample_person.middle_name, sample_person.last_name, sample_person.name_suffix)
            if sample_person
            else "(no resolved people)",
            "Person.first_name, middle_name, last_name, name_suffix",
            "Faithful",
            "",
            "Derived from full_name, not a direct raw field, but sourced faithfully from it.",
        )
    )
    rows.append(
        _row(
            "full_name (provenance bookkeeping only)",
            "(derived envelope, not a 1:1 raw field)",
            "Person.name_needs_review, Person.name_extraction_metadata",
            "Faithful",
            "",
            "Provenance/audit bookkeeping written by _apply_extracted_name_provenance.",
        )
    )
    rows.append(_upstream_missing_row("role_id", "Person.role_id"))
    rows.append(_upstream_missing_row("bio_text", "Person.bio_text"))
    rows.append(_upstream_missing_row("photo_url", "Person.photo_url"))
    rows.append(
        _upstream_missing_row(
            "birthdate",
            "Person.birthdate",
            "only import_justices_csv.py populates this for a Person the corpus importer "
            "creates fresh",
        )
    )
    rows.append(
        _upstream_missing_row(
            "death_date",
            "Person.death_date",
            "only import_justices_csv.py populates this for a Person the corpus importer "
            "creates fresh",
        )
    )
    return rows


# ---------------------------------------------------------------------------
# argument_participants table
# ---------------------------------------------------------------------------


def _build_argument_participants_rows(
    conversation_fields: dict, participants: list
) -> list[dict]:
    rows: list[dict] = []
    sample = participants[0] if participants else None

    rows.append(
        _row(
            "speaker registry entry: name/full_name (or speaker_id fallback)",
            sample.raw_speaker_label if sample else "(no participants)",
            "ArgumentParticipant.raw_speaker_label",
            "Faithful",
        )
    )
    rows.append(
        _row(
            "resolved Person",
            sample.person_id if sample else "(no participants)",
            "ArgumentParticipant.person_id",
            "Faithful",
        )
    )
    rows.append(
        _row(
            "is_justice (speaker registry type) + advocates[].side (conversation-level)",
            sample.side.value if sample and sample.side else "(no participants)",
            "ArgumentParticipant.side",
            "Faithful",
            "",
            "BENCH always wins over the advocate side code when is_justice is True; see "
            "court_tenures section for this fixture's one date-inconsistent case.",
        )
    )

    advocates = conversation_fields.get("advocates") or {}
    sample_role = next(
        (
            meta.get("role")
            for meta in advocates.values()
            if isinstance(meta, dict) and meta.get("role") is not None
        ),
        None,
    )
    rows.append(
        _row(
            "advocates[speaker_id].role (per-advocate, conversation-level)",
            sample_role,
            "(no column)",
            "Dropped",
            "schema-absent field",
            "Only advocates[].side is ever read; the per-advocate role/confidence value "
            "(e.g. \"inferred\") has no ArgumentParticipant column and is never persisted.",
        )
    )

    rows.append(
        _upstream_missing_row(
            "title",
            "ArgumentParticipant.title",
            "TOC subtitle from the PDF pipeline's cover extractor only",
        )
    )
    return rows


# ---------------------------------------------------------------------------
# court_tenures table (D-02 integrity check, NOT a ConvoKit diff)
# ---------------------------------------------------------------------------


def _load_csv_tenure_windows(justices_csv: Path) -> dict[str, list[tuple[str, "date | None", "date | None"]]]:
    """
    Build {full_name: [(office, start_date, end_date), ...]} from the
    justices CSV, reusing import_justices_csv.py's own row iterator and name
    reconstruction (Don't Hand-Roll -- never a second CSV parser).
    """
    windows: dict[str, list[tuple[str, "date | None", "date | None"]]] = {}
    for office, row in _iter_csv_rows(justices_csv):
        first = row.get("First Name", "").strip()
        middle = row.get("Middle Name or Initial", "").strip()
        last = row.get("Last Name", "").strip()
        suffix = row.get("Suffix", "").strip()
        if not first or not last:
            continue
        full_name = reconstruct_full_name(first, middle, last, suffix)
        start_date = _parse_optional_date(row.get("Judicial Oath Taken", ""))
        end_date = _parse_optional_date(row.get("Date Service Terminated", ""))
        windows.setdefault(full_name, []).append((office, start_date, end_date))
    return windows


def _covers(start_date, end_date, argued_date) -> bool:
    """Inclusive start boundary (per Task 2's tenure-boundary test pair)."""
    if start_date is None or argued_date is None:
        return False
    if start_date > argued_date:
        return False
    if end_date is not None and end_date < argued_date:
        return False
    return True


def _find_candidate_duplicate_justice(
    person, all_justices: list, tenures_by_justice_id: dict, argued_date
) -> tuple | None:
    """
    Look for a DIFFERENT is_justice=True Person row sharing this person's
    last_name that DOES have a CourtTenure covering argued_date. When found,
    a Person-dedup mismatch (two Person rows for the same real justice --
    one created by import_justices_csv.py with a full first/middle name,
    one created by the corpus importer from the speaker registry's abbreviated
    name) is a more likely explanation than a bench-classification anomaly.
    Returns (candidate_person, covering_tenure) or None.
    """
    if person is None or not person.last_name:
        return None
    for candidate in all_justices:
        if candidate.id == person.id:
            continue
        if not candidate.last_name or candidate.last_name.lower() != person.last_name.lower():
            continue
        for tenure in tenures_by_justice_id.get(candidate.id, []):
            if _covers(tenure.start_date, tenure.end_date, argued_date):
                return candidate, tenure
    return None


def _build_court_tenures_rows(
    participants: list,
    people_by_id: dict,
    tenures_by_person: dict,
    argued_date,
    justices_csv: Path,
    all_justices: list,
    tenures_by_justice_id: dict,
) -> list[dict]:
    rows: list[dict] = []
    bench_participants = [
        p for p in participants if p.side == SideEnum.BENCH and p.person_id is not None
    ]

    if not bench_participants:
        rows.append(
            _row(
                "(none -- no BENCH participant on this fixture)",
                "(n/a)",
                "CourtTenure",
                "N/A",
                "",
                "No integrity check to run.",
            )
        )
        return rows

    csv_windows = _load_csv_tenure_windows(justices_csv)

    for participant in bench_participants:
        person = people_by_id.get(participant.person_id)
        full_name = person.full_name if person else f"person_id={participant.person_id}"
        db_tenures = tenures_by_person.get(participant.person_id, [])
        db_covering = [
            t for t in db_tenures if _covers(t.start_date, t.end_date, argued_date)
        ]

        csv_tenures = csv_windows.get(full_name, [])
        csv_covering = [
            (office, start, end)
            for office, start, end in csv_tenures
            if _covers(start, end, argued_date)
        ]

        if db_covering:
            tenure = db_covering[0]
            rows.append(
                _row(
                    f"{full_name} (BENCH participant, person_id={participant.person_id})",
                    f"argued_date={argued_date}",
                    f"CourtTenure id={tenure.id} start_date={tenure.start_date} "
                    f"end_date={tenure.end_date}",
                    "Faithful",
                    "",
                    "A CourtTenure row covers the argued date (inclusive start boundary) -- "
                    "integrity check passed.",
                )
            )
            continue

        if csv_covering:
            # The CSV (the authoritative source court_tenures is derived
            # from) shows a covering tenure that the DB is missing -- a
            # genuine court_tenures data gap, flagged but NOT fixed here
            # (D-03).
            office, start, end = csv_covering[0]
            rows.append(
                _row(
                    f"{full_name} (BENCH participant, person_id={participant.person_id})",
                    f"argued_date={argued_date}",
                    f"CourtTenure (missing) -- CSV shows office={office} start_date={start} "
                    f"end_date={end}",
                    "Dropped",
                    "upstream-missing data (court_tenures gap, flagged-not-fixed per D-03)",
                    "supreme_court_justices_sections.csv shows a covering tenure that has no "
                    "matching CourtTenure row in the database. Owning tool: "
                    "pipeline/commands/import_justices_csv.py. Not fixed by this phase (D-03).",
                )
            )
            continue

        # Neither the DB nor the CSV shows a covering tenure under this
        # Person's own full_name -- the CSV corroborates the DB, so this is
        # NOT a court_tenures data gap by itself. Before assuming a bench-
        # classification timing anomaly (RESEARCH.md Pitfall 2), check
        # whether a DIFFERENT is_justice=True Person row (same last_name)
        # already has a covering tenure -- a Person-dedup mismatch, not a
        # timing/role anomaly, would produce this exact symptom too.
        duplicate = _find_candidate_duplicate_justice(
            person, all_justices, tenures_by_justice_id, argued_date
        )
        if duplicate is not None:
            candidate, tenure = duplicate
            rows.append(
                _row(
                    f"{full_name} (BENCH participant, person_id={participant.person_id})",
                    f"argued_date={argued_date}",
                    f"CourtTenure (none on person_id={participant.person_id}; a covering "
                    f"tenure exists on a DIFFERENT Person row)",
                    "Mis-mapped",
                    f"{PROPOSED_PREFIX} -- likely Person-dedup mismatch (distinct from "
                    "RESEARCH.md Pitfall 2's timing anomaly)",
                    f"Person id={candidate.id} ({candidate.full_name!r}) shares this "
                    f"participant's last_name and has CourtTenure id={tenure.id} "
                    f"(start_date={tenure.start_date}, end_date={tenure.end_date}) covering "
                    f"the argued date. This corpus import created a SEPARATE Person row "
                    f"(id={participant.person_id}, full_name={full_name!r}) instead of "
                    "matching the existing CSV-imported justice, because Person.full_name "
                    "dedup (_resolve_person) requires an exact string match and the two "
                    "sources format the same justice's name differently (e.g. an abbreviated "
                    "middle initial from the speaker registry vs. a full middle name from the "
                    "justices CSV). Not a court_tenures data gap and not fixed by this phase.",
                )
            )
            continue

        # No candidate duplicate found either -- fall back to RESEARCH.md
        # Pitfall 2's timing/role-anomaly explanation.
        rows.append(
            _row(
                f"{full_name} (BENCH participant, person_id={participant.person_id})",
                f"argued_date={argued_date}",
                "CourtTenure (none covering)",
                "Mis-mapped",
                f"{PROPOSED_PREFIX} -- bench-classification anomaly to investigate",
                "No CourtTenure row covers the argued date, the justices CSV corroborates "
                "that (no covering tenure there either), and no differently-named duplicate "
                "Person row with a covering tenure was found -- this is NOT a court_tenures "
                "data gap. Most likely explanation (RESEARCH.md Pitfall 2): the speaker registry's "
                "type field reflects this speaker's eventual/best-known role, not their role "
                "at the time of this specific argument. No court_tenures row is written by "
                "this phase (D-03).",
            )
        )

    return rows


# ---------------------------------------------------------------------------
# Volume and Roster Exactness
# ---------------------------------------------------------------------------


def _build_volume_and_roster_section(
    raw_turns: list[dict],
    utterances: list,
    participants: list,
    case_fields: dict,
    argument,
) -> list[str]:
    raw_turn_count = len(raw_turns)
    imported_utterance_count = len(utterances)

    turns_producing_rows = 0
    for turn in raw_turns:
        if not isinstance(turn, dict) or "conversation_id" not in turn or turn.get("text") is None:
            continue
        if import_convokit._split_turn_into_rows(turn["text"]):
            turns_producing_rows += 1

    raw_speakers = sorted({t.get("speaker") for t in raw_turns if t.get("speaker")})
    imported_roster = sorted(
        {p.raw_speaker_label for p in participants if p.raw_speaker_label}
    )

    raw_dockets = {case_fields.get("docket_no")} if case_fields.get("docket_no") else set()
    imported_dockets = {argument.source_docket} if argument.source_docket else set()

    lines = [
        "## Volume and Roster Exactness",
        "",
        f"- Raw source turns for this conversation (streamed from the utterance stream "
        f"via the loader): **{raw_turn_count}**",
        f"- Imported Utterance rows: **{imported_utterance_count}**",
        f"- Raw turns that produced at least one Utterance row "
        f"(via import_convokit._split_turn_into_rows): **{turns_producing_rows}**",
        f"- Raw distinct speaker roster ({len(raw_speakers)}): {', '.join(raw_speakers) or '(none)'}",
        f"- Imported ArgumentParticipant roster ({len(imported_roster)}): "
        f"{', '.join(imported_roster) or '(none)'}",
        f"- Raw source-docket set: {sorted(raw_dockets) or '(none)'}",
        f"- Imported Argument.source_docket set: {sorted(imported_dockets) or '(none)'}",
        f"- Docket sets match: **{raw_dockets == imported_dockets}**",
        "",
    ]
    return lines


# ---------------------------------------------------------------------------
# Boilerplate sections
# ---------------------------------------------------------------------------


def _build_regenerating_section(args: argparse.Namespace) -> list[str]:
    cmd = f"python scripts/diff_corpus_fixture.py --conversation-id {args.conversation_id}"
    if getattr(args, "corpus_dir", None):
        cmd += f" --corpus-dir {args.corpus_dir}"
    if getattr(args, "justices_csv", None):
        cmd += f" --justices-csv {args.justices_csv}"
    if getattr(args, "out", None):
        cmd += f" --out {args.out}"
    return [
        "## Regenerating this evidence",
        "",
        "```",
        cmd,
        "```",
        "",
        "Re-running this exact command against the same database and the same "
        "`data/corpus/` snapshot reproduces every verdict and classification above "
        "byte-for-byte (apart from the Generated timestamp line).",
        "",
    ]


def _build_review_status_section() -> list[str]:
    return [
        "## Review status",
        "",
        "Every non-Faithful classification in this document is a **proposal**, not a "
        "final decision (D-05). The operator reviews the whole document in one batch "
        "(D-06) and approves, adjusts, or rejects each proposal before any code fix is "
        "applied. **No importer fix has been applied as of this document's generation.**",
        "",
    ]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _build_document(args: argparse.Namespace, raw: dict, db: dict) -> str:
    lines: list[str] = [
        "# Corpus Fidelity Diff",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()} "
        "(only this line is expected to differ between two runs against an "
        "unchanged database and corpus snapshot).",
        "",
    ]

    lines += _emit_table(
        "cases", _build_cases_rows(raw["raw_case"], raw["case_fields"])
    )

    arguments_rows, raw_argued_date = _build_arguments_rows(
        args.conversation_id,
        raw["conversation_fields"],
        raw["case_fields"],
        db["argument"],
    )
    lines += _emit_table("arguments", arguments_rows)

    lines += _emit_table(
        "utterances", _build_utterances_rows(raw["raw_turns"], db["utterances"])
    )

    lines += _emit_table("people", _build_people_rows(db["people_by_id"]))

    lines += _emit_table(
        "argument_participants",
        _build_argument_participants_rows(
            raw["conversation_fields"], db["participants"]
        ),
    )

    justices_csv = _resolve_justices_csv(args)
    lines += _emit_table(
        "court_tenures",
        _build_court_tenures_rows(
            db["participants"],
            db["people_by_id"],
            db["tenures_by_person"],
            raw_argued_date,
            justices_csv,
            db["all_justices"],
            db["tenures_by_justice_id"],
        ),
    )

    lines += _build_volume_and_roster_section(
        raw["raw_turns"],
        db["utterances"],
        db["participants"],
        raw["case_fields"],
        db["argument"],
    )

    lines += _build_regenerating_section(args)
    lines += _build_review_status_section()

    return "\n".join(lines) + "\n"


async def _run(args: argparse.Namespace) -> str:
    corpus_dir = _resolve_corpus_dir(args)
    _resolve_justices_csv(args)  # fail fast even though it's read again below
    raw = _load_raw(corpus_dir, args.conversation_id)
    db = await _load_db(args.conversation_id)
    return _build_document(args, raw, db)


def main(argv=None) -> int:
    args = _parse_args(argv)
    try:
        document = asyncio.run(_run(args))
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.out:
        Path(args.out).write_text(document, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(document)
    return 0


if __name__ == "__main__":
    sys.exit(main())
