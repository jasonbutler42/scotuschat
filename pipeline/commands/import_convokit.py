"""
Pipeline import-convokit command.

Term-batched orchestration (D-07) for Phase 29's bulk historical import: for
one October Term (--term) or an inclusive range (--term-range), scaffolds
Case / Argument / CaseArgument / PipelineRun rows and resolves bench/advocate
speakers into Person + ArgumentParticipant rows -- entirely from
conversations.json + cases.jsonl + speakers.json (D-21). Utterance import and
the batch summary land in Plan 05/06 -- this module stops at scaffolding +
speaker resolution (this plan's declared objective boundary).

Built task-by-task per 29-04-PLAN.md:
    Task 1: CLI subcommand, --term/--term-range validation, --corpus-dir
        validation, and the per-term file-loading skeleton.
    Task 2: idempotent Case/Argument/CaseArgument/PipelineRun entity
        creation, apolitical field stripping (T-29-02), and per-conversation
        resilience (T-29-05b).
    Task 3: bench/advocate speaker resolution into Person (D-11 key order)
        + ArgumentParticipant rows (side classification, D-12/D-13).

Join key note: cases.jsonl rows carry their OWN "case_id" field with the
same value as conversations.json's top-level key/"case_id" attribute (the
apolitical-extractor test fixtures confirm this: case_id "1955_71" on both
sides, vs. a differently-formatted "docket_no" like "55-71" used for the
Case.docket_number column). The conversation/case join is therefore done on
case_id equality, not on docket matching -- pipeline.corpus.loader.load_cases
indexes by docket_no (for the Case.docket_number lookups this module also
needs), so a secondary case_id -> raw_case index is built here from its
values.

Speaker-resolution scope note (Task 3): conversations.json's "advocates"
dict is the only per-conversation participant list available at this
plan's stage -- utterances.jsonl (Plan 05's input) is what actually reveals
which bench justices spoke in a given conversation. The speaker-resolution
+ side-classification helpers below are written generically (a speaker's
side is derived from speakers.json's authoritative `type` field, not from
which caller/dict supplied the id), so Plan 05 can reuse them unchanged
once it streams utterances and discovers the real per-conversation bench
roster. This plan wires them up for every id in the conversation's
"advocates" dict now.

Usage:
    python -m pipeline import-convokit --term 1955
    python -m pipeline import-convokit --term-range 1955-1960
    python -m pipeline import-convokit --term 1955 --corpus-dir data/corpus
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from dateutil import parser as dateutil_parser
from sqlalchemy import select

from api.models.models import (
    Argument,
    ArgumentParticipant,
    ArgumentStatusEnum,
    Case,
    CaseArgument,
    Person,
    PipelineRun,
    PipelineRunStatus,
    SideEnum,
)
from pipeline.commands.ingest import _derive_slug
from pipeline.corpus import apolitical
from pipeline.corpus.loader import (
    load_cases,
    load_conversations_for_term,
    load_speakers,
)
from pipeline.db import get_session

# Matches the data/corpus/ scaffolding (D-20/D-21) -- the operator copies the
# ConvoKit source files here locally; it is gitignored, not tracked.
DEFAULT_CORPUS_DIR = Path("data/corpus")

# D-09: every argument imported by this command gets a real pipeline_runs
# row stamped with this strategy value, ahead of any utterance write path
# (Utterance.pipeline_run_id is NOT NULL, T-29-09).
PIPELINE_RUN_STRATEGY = "convokit_import"

# conversations.json advocate side codes -> SideEnum (RESEARCH.md Standard
# Stack cross-check / ConvoKit's official Supreme Court Corpus docs; A2).
_ADVOCATE_SIDE_MAP: dict[int, SideEnum] = {
    0: SideEnum.RESPONDENT,
    1: SideEnum.PETITIONER,
    2: SideEnum.AMICUS,
    3: SideEnum.UNKNOWN,
}

# speakers.json speaker `type` values treated as the bench classification
# (RESEARCH.md Open Question 3: type is authoritative, never a name-pattern
# guess like a "j__" id prefix).
_JUSTICE_TYPE_VALUES = {"justice", "j", "bench"}


# ---------------------------------------------------------------------------
# Task 1: term-range parsing + CLI arg validation (V5)
# ---------------------------------------------------------------------------


def _parse_term_range(value: str) -> tuple[int, int]:
    """
    Parse an inclusive "<start>-<end>" October Term range string.

    Raises argparse.ArgumentTypeError on malformed input (not exactly one
    '-' separator, non-integer parts) or when start > end -- validated
    before use, per RESEARCH.md's V5 input-validation guidance (this is
    operator-only offline tooling, but malformed input must still fail
    fast and clearly rather than corrupt a term filter downstream).
    """
    parts = value.split("-")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            f"--term-range must be '<start>-<end>' (e.g. 1955-1960), got {value!r}"
        )
    start_str, end_str = parts
    try:
        start, end = int(start_str), int(end_str)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--term-range values must be integers, got {value!r}"
        )
    if start > end:
        raise argparse.ArgumentTypeError(
            f"--term-range start term {start} is after end term {end}"
        )
    return start, end


def _resolve_terms(args) -> list[int]:
    """
    Resolve the --term/--term-range mutually-exclusive group into a sorted
    list of October Term years to process.
    """
    term = getattr(args, "term", None)
    if term is not None:
        return [term]
    term_range = getattr(args, "term_range", None)
    if term_range:
        start, end = _parse_term_range(term_range)
        return list(range(start, end + 1))
    raise argparse.ArgumentTypeError("Either --term or --term-range is required.")


def _resolve_corpus_dir(args) -> Path:
    """
    Resolve and validate --corpus-dir exists BEFORE any file load, so a
    missing/nonexistent path fails fast with a clear error instead of a
    KeyError/FileNotFoundError raised deep inside a loader call mid-run.
    """
    raw = getattr(args, "corpus_dir", None)
    corpus_dir = Path(raw) if raw else DEFAULT_CORPUS_DIR
    if not corpus_dir.is_dir():
        raise FileNotFoundError(
            f"--corpus-dir does not exist: {corpus_dir}. Place the ConvoKit "
            "supreme-corpus source files (conversations.json, cases.jsonl, "
            "speakers.json) there before running import-convokit."
        )
    return corpus_dir


# ---------------------------------------------------------------------------
# Task 2: per-conversation entity creation (Case/Argument/CaseArgument/PipelineRun)
# ---------------------------------------------------------------------------


def _parse_argued_date(case_fields: dict) -> date | None:
    """
    Parse an argued_date from the first entry of cases.jsonl's allowlisted
    "transcripts" list (e.g. "Oral Argument - November 15, 1955"), via
    dateutil fuzzy parsing (RESEARCH.md Standard Stack). None-safe: returns
    None when there is no transcripts entry or no parseable date
    (Argument.argued_date is nullable, matching ingest.py's D-08 precedent).
    """
    transcripts = case_fields.get("transcripts") or []
    if not transcripts:
        return None
    first = transcripts[0]
    name = first.get("name") if isinstance(first, dict) else None
    if not name:
        return None
    try:
        return dateutil_parser.parse(name, fuzzy=True).date()
    except (ValueError, OverflowError):
        return None


def _case_name_from_fields(case_fields: dict) -> str:
    """Prefer cases.jsonl's "title"; fall back to "{petitioner} v. {respondent}"."""
    title = case_fields.get("title")
    if title:
        return title
    petitioner = case_fields.get("petitioner") or "Unknown"
    respondent = case_fields.get("respondent") or "Unknown"
    return f"{petitioner} v. {respondent}"


async def _get_or_create_case(session, case_fields: dict, counters: dict) -> Case:
    """
    Idempotent Case create (select on Case.docket_number, D-08). term_year
    comes DIRECTLY from cases.jsonl's allowlisted "year" field (D-15) --
    never derived from argued_date's calendar year. Lead-docket-only
    (D-19): this is the single Case row for the conversation's docket; no
    consolidated-companion sourcing happens here.

    Increments counters["cases_created"] only when a new row is actually
    created (not on the reuse-existing path).
    """
    docket = case_fields["docket_no"]
    result = await session.execute(select(Case).where(Case.docket_number == docket))
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    case_name = _case_name_from_fields(case_fields)
    new_case = Case(
        docket_number=docket,
        docket_number_norm=docket.replace("-", ""),
        case_name=case_name,
        term_year=case_fields["year"],  # D-15 -- never int(argued_date[:4])
        slug=_derive_slug(case_name),
        oyez_case_id=case_fields.get("case_id"),  # D-10
    )
    session.add(new_case)
    await session.flush()
    counters["cases_created"] += 1
    return new_case


async def _import_conversation(
    session,
    conversation_id: str,
    raw_conversation: dict,
    cases_by_case_id: dict[str, dict],
    speakers_index: dict,
    counters: dict,
) -> None:
    """
    Import one conversation: idempotent Case/Argument/CaseArgument/
    PipelineRun scaffolding (Task 2). Speaker resolution (Task 3) lands in
    the next task.

    Never raises for an anticipated bad/missing join -- increments
    counters["flagged"] and returns early (T-29-05b / RESEARCH Pitfall 5)
    so one malformed conversation doesn't abort the whole term batch. Truly
    unexpected exceptions are left to propagate to the caller's per-row
    try/except (run_import_convokit), which also flags and continues.
    """
    conversation = apolitical.extract_conversation_fields(raw_conversation)

    raw_case = cases_by_case_id.get(conversation["case_id"])
    if raw_case is None:
        counters["flagged"] += 1
        print(
            f"WARNING: conversation {conversation_id!r} (case_id="
            f"{conversation['case_id']!r}) has no matching cases.jsonl row "
            "-- flagged, skipped."
        )
        return

    case_fields = apolitical.extract_case_fields(raw_case)
    if not case_fields.get("docket_no") or not case_fields.get("year"):
        counters["flagged"] += 1
        print(
            f"WARNING: conversation {conversation_id!r} case row is missing "
            "docket_no/year -- flagged, skipped."
        )
        return

    # ---- Idempotent Argument dedup on oyez_transcript_id (D-08) ----
    existing_argument_result = await session.execute(
        select(Argument).where(Argument.oyez_transcript_id == conversation_id)
    )
    if existing_argument_result.scalar_one_or_none() is not None:
        counters["skipped_existing"] += 1
        return

    case = await _get_or_create_case(session, case_fields, counters)

    argued_date = _parse_argued_date(case_fields)

    argument = Argument(
        argued_date=argued_date,
        question_number=1,
        source_docket=case_fields["docket_no"],
        status=ArgumentStatusEnum.DRAFT,  # D-06
        oyez_transcript_id=conversation_id,  # D-10
    )
    session.add(argument)
    await session.flush()
    counters["arguments_created"] += 1

    # ---- CaseArgument (lead-docket-only, D-19) ----
    link_result = await session.execute(
        select(CaseArgument).where(
            CaseArgument.case_id == case.id,
            CaseArgument.argument_id == argument.id,
        )
    )
    if link_result.scalar_one_or_none() is None:
        session.add(CaseArgument(case_id=case.id, argument_id=argument.id, is_lead=True))

    # ---- PipelineRun -- BEFORE any utterance write path (T-29-09) ----
    run = PipelineRun(
        argument_id=argument.id,
        step="ingest",
        status=PipelineRunStatus.COMPLETED,
        strategy=PIPELINE_RUN_STRATEGY,  # D-09
    )
    session.add(run)
    await session.flush()

    # ---- Task 3: speaker resolution for the conversation's advocates ----
    advocates = conversation.get("advocates") or {}
    for speaker_id, advocate_meta in advocates.items():
        side_code = (
            advocate_meta.get("side") if isinstance(advocate_meta, dict) else advocate_meta
        )
        await _resolve_and_link_participant(
            session=session,
            argument_id=argument.id,
            speaker_id=speaker_id,
            speakers_index=speakers_index,
            side_code=side_code,
            counters=counters,
        )


# ---------------------------------------------------------------------------
# Task 3: speaker resolution -- Person (D-11) + ArgumentParticipant (side)
# ---------------------------------------------------------------------------


def _is_justice_type(speaker_meta: dict) -> bool | None:
    """
    Read speakers.json's speaker `type` field as the AUTHORITATIVE bench vs.
    advocate signal (RESEARCH.md Open Question 3) -- never inferred from a
    speaker id's naming convention (e.g. a "j__" prefix). Returns None when
    the type is missing/unrecognized so the caller can flag it (D-12)
    instead of guessing.
    """
    speaker_type = speaker_meta.get("type")
    if speaker_type is None:
        return None
    return str(speaker_type).strip().lower() in _JUSTICE_TYPE_VALUES


async def _resolve_person(
    session, speaker_id: str, full_name: str, is_justice: bool
) -> Person:
    """
    Resolve or create a Person for `speaker_id`, per D-11's key order:
    Person.oyez_speaker_id checked FIRST, then Person.full_name (D-13, same
    exact-match dedup as the justice importer). When a full_name match is
    found with no oyez_speaker_id yet, backfill it (D-11) so the next run
    matches by the stable ID.
    """
    result = await session.execute(
        select(Person).where(Person.oyez_speaker_id == speaker_id)
    )
    person = result.scalar_one_or_none()
    if person is not None:
        return person

    result = await session.execute(select(Person).where(Person.full_name == full_name))
    person = result.scalar_one_or_none()
    if person is not None:
        if person.oyez_speaker_id is None:
            person.oyez_speaker_id = speaker_id  # D-11 backfill
        return person

    person = Person(
        full_name=full_name,
        oyez_speaker_id=speaker_id,
        is_justice=is_justice,
    )
    session.add(person)
    await session.flush()
    return person


async def _resolve_and_link_participant(
    session,
    argument_id: int,
    speaker_id: str,
    speakers_index: dict,
    side_code,
    counters: dict,
) -> ArgumentParticipant:
    """
    Resolve `speaker_id` to a Person and idempotently create its
    ArgumentParticipant row for `argument_id` (D-11/D-12/D-13).

    `side_code` is the raw conversations.json 0/1/2/3 advocate side code;
    it is ignored (side is always BENCH) when the resolved speaker's
    speakers.json `type` classifies as a justice. No automated QA gate on
    identity matching (D-12) -- ambiguous/missing types are imported and
    flagged for the batch summary, never silently skipped.
    """
    speaker_meta = speakers_index.get(speaker_id)
    if speaker_meta is None:
        counters["flagged"] += 1
        print(
            f"WARNING: speaker {speaker_id!r} not found in speakers.json -- "
            "flagged, imported anyway (D-12)."
        )
        speaker_meta = {}

    is_justice = _is_justice_type(speaker_meta)
    if is_justice is None:
        counters["flagged"] += 1
        print(
            f"WARNING: speaker {speaker_id!r} has ambiguous/missing 'type' in "
            "speakers.json -- treated as non-justice, flagged for summary "
            "(D-12, RESEARCH Open Question 3)."
        )
        is_justice = False

    full_name = speaker_meta.get("name") or speaker_meta.get("full_name") or speaker_id
    raw_speaker_label = full_name

    person = await _resolve_person(session, speaker_id, full_name, is_justice)

    side = SideEnum.BENCH if is_justice else _ADVOCATE_SIDE_MAP.get(side_code, SideEnum.UNKNOWN)

    existing = await session.execute(
        select(ArgumentParticipant).where(
            ArgumentParticipant.argument_id == argument_id,
            ArgumentParticipant.raw_speaker_label == raw_speaker_label,
        )
    )
    participant = existing.scalar_one_or_none()
    if participant is not None:
        return participant

    participant = ArgumentParticipant(
        argument_id=argument_id,
        person_id=person.id,
        raw_speaker_label=raw_speaker_label,
        side=side,
    )
    session.add(participant)
    await session.flush()
    counters["participants_created"] += 1
    return participant


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def run_import_convokit(args) -> None:
    """
    Entry point for `python -m pipeline import-convokit`.

    Resolves --term/--term-range into a sorted list of October Terms,
    validates --corpus-dir exists, loads speakers.json/cases.jsonl once
    (global directories, not term-scoped), then for each term loads
    conversations.json filtered to that term and delegates each conversation
    to _import_conversation (Task 2/3 implement the real entity-creation and
    speaker-resolution logic there).
    """
    terms = _resolve_terms(args)
    corpus_dir = _resolve_corpus_dir(args)

    conversations_path = corpus_dir / "conversations.json"
    cases_path = corpus_dir / "cases.jsonl"
    speakers_path = corpus_dir / "speakers.json"
    for required in (conversations_path, cases_path, speakers_path):
        if not required.exists():
            raise FileNotFoundError(f"Required corpus file not found: {required}")

    speakers_index = load_speakers(speakers_path)
    cases_by_docket = load_cases(cases_path)
    # Secondary index: cases.jsonl carries its own "case_id" field matching
    # conversations.json's key/case_id (docket_no is a DIFFERENT format,
    # used for the Case.docket_number column -- see Task 2).
    cases_by_case_id = {
        row["case_id"]: row for row in cases_by_docket.values() if row.get("case_id")
    }

    for term in terms:
        conversations = load_conversations_for_term(conversations_path, term)
        counters = {
            "cases_created": 0,
            "arguments_created": 0,
            "skipped_existing": 0,
            "participants_created": 0,
            "flagged": 0,
        }
        for conversation_id, raw_conversation in conversations.items():
            try:
                async with get_session() as session:
                    await _import_conversation(
                        session=session,
                        conversation_id=conversation_id,
                        raw_conversation=raw_conversation,
                        cases_by_case_id=cases_by_case_id,
                        speakers_index=speakers_index,
                        counters=counters,
                    )
            except Exception as exc:  # per-row resilience, T-29-05b/Pitfall 5
                counters["flagged"] += 1
                print(
                    f"WARNING: conversation {conversation_id!r} raised "
                    f"{exc!r} -- flagged, term continues."
                )

        print(
            f"Term {term}: {counters['arguments_created']} arguments created, "
            f"{counters['skipped_existing']} already existed, "
            f"{counters['cases_created']} cases created, "
            f"{counters['participants_created']} participants created, "
            f"{counters['flagged']} conversations flagged."
        )
