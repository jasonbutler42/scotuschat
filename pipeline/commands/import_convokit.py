"""
Pipeline import-convokit command.

Term-batched orchestration (D-07) for Phase 29's bulk historical import: for
one October Term (--term) or an inclusive range (--term-range), scaffolds
Case / Argument / CaseArgument / PipelineRun rows, resolves bench/advocate
speakers into Person + ArgumentParticipant rows, streams each argument's
utterances.jsonl turns into Utterance rows (D-18), splits detected stage
directions into their own rows (D-16/D-17), and prints a per-batch summary
report (D-14).

Built task-by-task:
    29-04 Task 1: CLI subcommand, --term/--term-range validation,
        --corpus-dir validation, and the per-term file-loading skeleton.
    29-04 Task 2: idempotent Case/Argument/CaseArgument/PipelineRun entity
        creation, apolitical field stripping (T-29-02), and per-conversation
        resilience (T-29-05b).
    29-04 Task 3: bench/advocate speaker resolution into Person (D-11 key
        order) + ArgumentParticipant rows (side classification, D-12/D-13).
    29-05 Task 1: streaming utterance import (D-18) -- one Utterance row per
        ConvoKit turn, \\n segment boundaries preserved verbatim, stage
        directions split into their own rows via
        pipeline.corpus.stage_directions.detect_stage_direction (D-16/D-17).
    29-05 Task 2: per-batch/rollup summary report (D-14).

Join key note: each cases.jsonl row's term-prefixed identifier lives in its
"id" field (e.g. "1955_71"), matching conversations.json's per-conversation
"case_id" field -- a differently-formatted "docket_no" like "55-71" is used
separately for the Case.docket_number column. The conversation/case join is
therefore done on raw_case["id"] == conversation["case_id"], not on docket
matching -- pipeline.corpus.loader.load_cases already indexes by "id" for
this reason (never by docket_no, which recycles across terms and would
silently drop same-docket rows from earlier terms -- migration 0018).

Speaker-resolution scope note (Task 3): conversations.json's "advocates"
dict is the only per-conversation participant list available at this
plan's stage -- utterances.jsonl (Plan 05's input) is what actually reveals
which bench justices spoke in a given conversation. The speaker-resolution
+ side-classification helpers below are written generically (a speaker's
side is derived from speakers.json's authoritative `type` field, not from
which caller/dict supplied the id), so Plan 05 can reuse them unchanged
once it streams utterances and discovers the real per-conversation bench
roster. This plan wires them up for every id in the conversation's
"advocates" dict now. Plan 05 reuses `_resolve_and_link_participant`
unchanged to resolve each utterance turn's speaker as well.

Utterance streaming note (Plan 05, Task 1): utterances.jsonl (~900MB) is
never loaded whole (T-29-03) -- one streaming pass per term is made via
pipeline.corpus.loader.stream_utterances_for_conversation_ids, filtered to
that term's conversation_id set, grouping rows into an in-memory
conversation_id -> [turn, ...] index that is held only for the term
currently being imported (RESEARCH.md Pattern 3 option (b) -- a single
term's utterance subset is small even though the full file is 900MB).
Turns are written in the order encountered in the stream, which is the
corpus's own transcript order for a given conversation_id.

Usage:
    python -m pipeline import-convokit --term 1955
    python -m pipeline import-convokit --term-range 1955-1960
    python -m pipeline import-convokit --term 1955 --corpus-dir data/corpus
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
from pathlib import Path

from dateutil import parser as dateutil_parser
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from api.models.models import (
    AdminJob,
    AdminJobStatus,
    AdminJobStep,
    Argument,
    ArgumentParticipant,
    ArgumentStatusEnum,
    Case,
    CaseArgument,
    Person,
    PipelineRun,
    PipelineRunStatus,
    SideEnum,
    Utterance,
)
from pipeline.commands.ingest import _derive_slug
from pipeline.commands.resolve import normalize_label
from pipeline.corpus import apolitical, stage_directions
from pipeline.corpus.loader import (
    load_cases,
    load_conversations_for_term,
    load_speakers,
    stream_utterances_for_conversation_ids,
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

# speakers.json speaker `type` value "U" marks ConvoKit's own "could not
# identify a speaker for this turn" placeholders (e.g. "<INAUDIBLE>",
# "<UNKNOWN>") -- these are not real people and must never become a
# Person/ArgumentParticipant row (gap-closure: importing the real corpus
# created a bogus "<INAUDIBLE>" advocate before this guard existed).
_UNATTRIBUTED_TYPE_VALUES = {"u", "unattributed", "unknown"}


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
            "speakers.json, utterances.jsonl) there before running "
            "import-convokit."
        )
    return corpus_dir


# ---------------------------------------------------------------------------
# Task 2: per-conversation entity creation (Case/Argument/CaseArgument/PipelineRun)
# ---------------------------------------------------------------------------


def _parse_argued_date(case_fields: dict, conversation_id: str) -> date | None:
    """
    Parse an argued_date from cases.jsonl's allowlisted "transcripts" list
    entry matching THIS conversation (each transcript's own "id" equals the
    oyez_transcript_id being imported, e.g. "Oral Argument - November 15,
    1955"), via dateutil fuzzy parsing (RESEARCH.md Standard Stack). A case
    argued across multiple sessions has one transcripts entry per session
    with its own date -- blindly using transcripts[0] would stamp every
    session with the first session's date (gap-closure: this produced
    identical argued_date values across multi-session cases before this
    fix). Falls back to the first entry only if no transcript's "id"
    matches (defensive). None-safe: returns None when there is no
    transcripts entry or no parseable date (Argument.argued_date is
    nullable, matching ingest.py's D-08 precedent).
    """
    transcripts = case_fields.get("transcripts") or []
    if not transcripts:
        return None
    matching = next(
        (
            t
            for t in transcripts
            if isinstance(t, dict) and str(t.get("id")) == conversation_id
        ),
        None,
    )
    entry = matching or transcripts[0]
    name = entry.get("name") if isinstance(entry, dict) else None
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
    Idempotent Case create. Historical docket numbers recycle across
    October Terms (migration 0018 gap-closure) -- e.g. docket "71" is a
    distinct, unrelated case in nearly a dozen different terms -- so lookup
    prefers the corpus's stable oyez_case_id first (this alone disambiguates
    same-docket cases from different terms). If that misses, falls back to
    the (docket_number, term_year) composite -- this is what lets a docket
    already occupied by the ordinary PDF pipeline (no oyez_case_id set) be
    reused rather than duplicated (CR-01); the existing row's oyez_case_id
    is then backfilled, mirroring the same pattern already used for
    Person.oyez_speaker_id (D-11). term_year comes DIRECTLY from
    cases.jsonl's allowlisted "year" field (D-15) -- never derived from
    argued_date's calendar year. Lead-docket-only (D-19): this is the single
    Case row for the conversation's docket; no consolidated-companion
    sourcing happens here.

    Increments counters["cases_created"] only when a new row is actually
    created (not on the reuse-existing path).
    """
    docket = case_fields["docket_no"]
    year = case_fields["year"]
    oyez_case_id = case_fields.get("case_id")

    existing = None
    if oyez_case_id:
        result = await session.execute(
            select(Case).where(Case.oyez_case_id == oyez_case_id)
        )
        existing = result.scalar_one_or_none()

    if existing is None:
        result = await session.execute(
            select(Case).where(
                Case.docket_number == docket, Case.term_year == year
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None and oyez_case_id and existing.oyez_case_id is None:
            existing.oyez_case_id = oyez_case_id  # D-11-style backfill

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


async def _next_question_number(session, source_docket: str) -> int:
    """
    Return the next available `question_number` for `source_docket` -- the
    same `(source_docket, question_number)` pair the DB's real
    `uq_arguments_source_docket_question` constraint enforces (CR-01 gap
    closure, 29-VERIFICATION.md).

    Executes `select(func.max(Argument.question_number)).where(source_docket
    == ...)` and returns 1 when no row exists yet for the docket (first
    argument), else `max + 1`. This is what lets a reargued case, or a
    docket already occupying question_number=1 from the ordinary PDF
    pipeline, receive question_number=2 (or higher) instead of colliding at
    `session.flush()`. `source_docket` is always non-null here -- the
    caller already validated `case_fields["docket_no"]` is present before
    calling this.
    """
    result = await session.execute(
        select(func.max(Argument.question_number)).where(
            Argument.source_docket == source_docket
        )
    )
    current_max = result.scalar()
    return 1 if current_max is None else current_max + 1


def _build_discrepancies(participants: list[ArgumentParticipant]) -> list[dict]:
    """
    Build one HIT-shaped discrepancy dict per already-resolved corpus
    participant (D-05 parity), mirroring `pipeline.commands.resolve`'s
    HIT-branch `discrepancies.append(...)` shape exactly (30-PATTERNS.md)
    so `ResolveCard.svelte`'s per-row Action column (Confirm/Change/Create
    person) renders unmodified for corpus jobs.

    Only participants with a resolved `person_id` are included -- there is
    no MISS branch here (corpus speakers are always resolved to a Person
    by `_resolve_and_link_participant` before this is called; a `None`
    entry in `resolved_participants` means "no attributable speaker", not
    "unresolved", and is filtered out by the caller before this function
    ever sees it -- this second guard is defense-in-depth).

    `auto_match_name` is `p.raw_speaker_label` (not a Person query) because
    for corpus rows `full_name IS raw_speaker_label` (see
    `_resolve_and_link_participant`). `auto_match_role` is always `None`
    because corpus-imported Person rows never set `role_id` (Assumptions
    Log A2).
    """
    return [
        {
            "raw_speaker_label": p.raw_speaker_label,
            "normalized": normalize_label(p.raw_speaker_label),
            "candidates": [],
            "auto_match_id": p.person_id,
            "auto_match_name": p.raw_speaker_label,
            "auto_match_role": None,
            "auto_resolved": True,
        }
        for p in participants
        if p.person_id is not None
    ]


async def _import_conversation(
    session,
    conversation_id: str,
    raw_conversation: dict,
    cases_by_case_id: dict[str, dict],
    speakers_index: dict,
    turns: list[dict],
    counters: dict,
) -> None:
    """
    Import one conversation: idempotent Case/Argument/CaseArgument/
    PipelineRun scaffolding (29-04 Task 2), bench/advocate speaker
    resolution (29-04 Task 3), and utterance streaming/stage-direction
    splitting (29-05 Task 1) for this conversation's `turns` (already
    filtered/grouped by the caller from utterances.jsonl, T-29-03).

    Never raises for an anticipated bad/missing join -- increments
    counters["conversations_errored"] and returns early (T-29-05b /
    RESEARCH Pitfall 5) so one malformed conversation doesn't abort the
    whole term batch. Truly unexpected exceptions are left to propagate to
    the caller's per-row try/except (run_import_convokit), which also
    counts the conversation as errored and continues.
    """
    conversation = apolitical.extract_conversation_fields(raw_conversation)

    raw_case = cases_by_case_id.get(conversation["case_id"])
    if raw_case is None:
        counters["conversations_errored"] = counters.get("conversations_errored", 0) + 1
        print(
            f"WARNING: conversation {conversation_id!r} (case_id="
            f"{conversation['case_id']!r}) has no matching cases.jsonl row "
            "-- errored, skipped."
        )
        return

    case_fields = apolitical.extract_case_fields(raw_case)
    if not case_fields.get("docket_no") or not case_fields.get("year"):
        counters["conversations_errored"] = counters.get("conversations_errored", 0) + 1
        print(
            f"WARNING: conversation {conversation_id!r} case row is missing "
            "docket_no/year -- errored, skipped."
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

    argued_date = _parse_argued_date(case_fields, conversation_id)

    # Derive the next available question_number for this docket (CR-01 gap
    # closure) instead of hardcoding 1 -- aligns the write with the DB's
    # real (source_docket, question_number) uniqueness contract so a
    # reargued case, or a docket already occupying question_number=1 from
    # the PDF pipeline, gets question_number=2+ instead of colliding.
    next_question_number = await _next_question_number(
        session, case_fields["docket_no"]
    )

    argument = Argument(
        argued_date=argued_date,
        question_number=next_question_number,
        source_docket=case_fields["docket_no"],
        # Phase 30 fix (supersedes Phase 29's D-06 for this write, see
        # 30-RESEARCH.md Pitfall 1): every read path that gates Resolve-card
        # editability keys on ArgumentStatusEnum.PIPELINE, so a corpus
        # argument must start there, not DRAFT, to ever become editable.
        status=ArgumentStatusEnum.PIPELINE,
        oyez_transcript_id=conversation_id,  # D-10
    )
    session.add(argument)
    try:
        await session.flush()
    except IntegrityError:
        # Defense-in-depth safety net: any residual (source_docket,
        # question_number) collision that _next_question_number could not
        # prevent (e.g. a concurrent writer) is caught here, rolled back,
        # and counted DISTINCTLY from conversations_errored so it is never
        # silently folded into the generic error bucket (CR-01,
        # 29-VERIFICATION.md truth #14 / CORPUS-08 visibility).
        await session.rollback()
        counters["docket_question_conflict"] = (
            counters.get("docket_question_conflict", 0) + 1
        )
        print(
            f"WARNING: conversation {conversation_id!r} (source_docket="
            f"{case_fields['docket_no']!r}) hit a docket/question "
            "uniqueness conflict at flush -- distinct from a generic "
            "error, counted in docket_question_conflict, skipped."
        )
        return
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

    # ---- PipelineRun -- this single row performs the combined work the PDF
    # pipeline splits across three separate CLI-invoked stages (ingest,
    # parse, resolve), but is labeled by its function -- the run that writes
    # this argument's Utterance rows -- matching the meaning
    # api/services/arguments.py's get_argument_with_utterances and
    # api/services/admin_jobs.py's get_run_id_for_step already give
    # step="parse" everywhere else in the codebase. Created BEFORE any
    # utterance write path (T-29-09).
    run = PipelineRun(
        argument_id=argument.id,
        step="parse",
        status=PipelineRunStatus.COMPLETED,
        strategy=PIPELINE_RUN_STRATEGY,  # D-09
    )
    session.add(run)
    await session.flush()

    # ---- Task 3: speaker resolution for the conversation's advocates ----
    # `resolved_participants` caches speaker_id -> ArgumentParticipant for
    # this conversation only (not persisted/global) -- both the advocates
    # loop below and the utterance-import loop (29-05 Task 1) share it, so
    # a speaker with many turns is resolved via _resolve_and_link_participant
    # (a DB round trip + counters increment) exactly ONCE per conversation,
    # not once per turn.
    resolved_participants: dict[str, ArgumentParticipant | None] = {}
    advocates = conversation.get("advocates") or {}
    for speaker_id, advocate_meta in advocates.items():
        side_code = (
            advocate_meta.get("side") if isinstance(advocate_meta, dict) else advocate_meta
        )
        resolved_participants[speaker_id] = await _resolve_and_link_participant(
            session=session,
            argument_id=argument.id,
            speaker_id=speaker_id,
            speakers_index=speakers_index,
            side_code=side_code,
            counters=counters,
        )

    # ---- 29-05 Task 1: stream this conversation's turns into Utterance rows ----
    await _import_utterances(
        session=session,
        argument_id=argument.id,
        pipeline_run_id=run.id,
        strategy=run.strategy,
        turns=turns,
        speakers_index=speakers_index,
        resolved_participants=resolved_participants,
        counters=counters,
    )

    # ---- Phase 30: pause every corpus-imported argument for operator
    # review (D-01, D-03) ---- Inserted here, after _import_utterances
    # returns, because bench (Justice) participants are discovered only
    # while streaming utterances -- both the advocates loop above and
    # _import_utterances write into resolved_participants by reference, so
    # only now does resolved_participants.values() hold every participant
    # for this argument (30-RESEARCH.md Pattern 3). No separate
    # commit/flush -- get_session()'s context manager commits this whole
    # per-conversation transaction atomically on clean exit.
    resolved = [p for p in resolved_participants.values() if p is not None]
    session.add(
        AdminJob(
            status=AdminJobStatus.PAUSED,
            current_step=AdminJobStep.RESOLVE,
            argument_id=argument.id,
            discrepancies=_build_discrepancies(resolved),
        )
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


def _is_unattributed_speaker_type(speaker_meta: dict) -> bool:
    """
    True when speakers.json's `type` field is ConvoKit's own "no
    identifiable speaker" sentinel ("U", e.g. for "<INAUDIBLE>"/"<UNKNOWN>")
    -- distinct from a genuinely missing/ambiguous type (D-12, which is
    still imported as a flagged advocate). This one must never produce a
    Person/ArgumentParticipant row at all.
    """
    speaker_type = speaker_meta.get("type")
    if speaker_type is None:
        return False
    return str(speaker_type).strip().lower() in _UNATTRIBUTED_TYPE_VALUES


async def _resolve_person(
    session, speaker_id: str, full_name: str, is_justice: bool, counters: dict
) -> Person:
    """
    Resolve or create a Person for `speaker_id`, per D-11's key order:
    Person.oyez_speaker_id checked FIRST, then Person.full_name (D-13, same
    exact-match dedup as the justice importer). When a full_name match is
    found with no oyez_speaker_id yet, backfill it (D-11) so the next run
    matches by the stable ID.

    Increments counters["people_matched"] on either reuse path, or
    counters["people_created"] when a brand-new Person row is created
    (D-14 per-batch summary).
    """
    result = await session.execute(
        select(Person).where(Person.oyez_speaker_id == speaker_id)
    )
    person = result.scalar_one_or_none()
    if person is not None:
        counters["people_matched"] = counters.get("people_matched", 0) + 1
        return person

    result = await session.execute(select(Person).where(Person.full_name == full_name))
    person = result.scalar_one_or_none()
    if person is not None:
        if person.oyez_speaker_id is None:
            person.oyez_speaker_id = speaker_id  # D-11 backfill
        counters["people_matched"] = counters.get("people_matched", 0) + 1
        return person

    person = Person(
        full_name=full_name,
        oyez_speaker_id=speaker_id,
        is_justice=is_justice,
    )
    session.add(person)
    await session.flush()
    counters["people_created"] = counters.get("people_created", 0) + 1
    return person


async def _resolve_and_link_participant(
    session,
    argument_id: int,
    speaker_id: str,
    speakers_index: dict,
    side_code,
    counters: dict,
) -> ArgumentParticipant | None:
    """
    Resolve `speaker_id` to a Person and idempotently create its
    ArgumentParticipant row for `argument_id` (D-11/D-12/D-13).

    Returns None -- creating no Person/ArgumentParticipant row at all --
    when speakers.json's `type` is ConvoKit's own "no identifiable speaker"
    sentinel ("U", e.g. "<INAUDIBLE>"/"<UNKNOWN>"). Callers must treat a
    None return as "this turn has no attributable speaker" (mirrors how a
    stage-direction row already has no participant), not as an error.

    `side_code` is the raw conversations.json 0/1/2/3 advocate side code;
    it is ignored (side is always BENCH) when the resolved speaker's
    speakers.json `type` classifies as a justice. No automated QA gate on
    identity matching (D-12) -- ambiguous/missing types are imported and
    counted in counters["speakers_flagged"] for the batch summary, never
    silently skipped.
    """
    speaker_meta = speakers_index.get(speaker_id)
    if speaker_meta is None:
        counters["speakers_flagged"] = counters.get("speakers_flagged", 0) + 1
        print(
            f"WARNING: speaker {speaker_id!r} not found in speakers.json -- "
            "flagged, imported anyway (D-12)."
        )
        speaker_meta = {}

    if _is_unattributed_speaker_type(speaker_meta):
        counters["unattributed_speakers_skipped"] = (
            counters.get("unattributed_speakers_skipped", 0) + 1
        )
        return None

    is_justice = _is_justice_type(speaker_meta)
    if is_justice is None:
        counters["speakers_flagged"] = counters.get("speakers_flagged", 0) + 1
        print(
            f"WARNING: speaker {speaker_id!r} has ambiguous/missing 'type' in "
            "speakers.json -- treated as non-justice, flagged for summary "
            "(D-12, RESEARCH Open Question 3)."
        )
        is_justice = False

    full_name = speaker_meta.get("name") or speaker_meta.get("full_name") or speaker_id
    raw_speaker_label = full_name

    person = await _resolve_person(session, speaker_id, full_name, is_justice, counters)

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
# 29-05 Task 1: utterance streaming + stage-direction row-splitting
# (D-16/D-17/D-18)
# ---------------------------------------------------------------------------


def _split_turn_into_rows(text: str) -> list[tuple[str, bool]]:
    """
    Split one ConvoKit turn's `text` on its `\\n`-delimited segment
    boundaries (D-18) and classify each segment via
    stage_directions.detect_stage_direction (D-16/D-17 -- no re-implemented
    regex here).

    Returns an ordered list of (row_text, is_stage_direction) tuples:
    contiguous non-marker segments are rejoined with `\\n` into a single
    row (D-18's default -- a turn with no marker segments becomes exactly
    one row, `\\n` boundaries preserved verbatim), while each detected
    marker segment becomes its own adjacent row (D-16 -- "a turn that
    begins or contains an inline marker segment" is split, keeping the
    spoken remainder as its own row(s); losslessly reversible later).
    """
    segments = text.split("\n")
    rows: list[tuple[str, bool]] = []
    pending: list[str] = []

    def _flush_pending() -> None:
        if pending:
            rows.append(("\n".join(pending), False))
            pending.clear()

    for segment in segments:
        if stage_directions.detect_stage_direction(segment) is not None:
            _flush_pending()
            rows.append((segment, True))
        else:
            pending.append(segment)
    _flush_pending()
    return rows


async def _import_utterances(
    session,
    argument_id: int,
    pipeline_run_id: int,
    strategy: str,
    turns: list[dict],
    speakers_index: dict,
    resolved_participants: dict[str, ArgumentParticipant],
    counters: dict,
) -> None:
    """
    Write one Utterance row per ConvoKit turn (D-18), or per split-out
    segment when a turn contains stage-direction marker segments (D-16),
    for one already-scaffolded argument + pipeline run, in the streamed
    (transcript) order the turns were encountered (T-29-03 -- `turns` is
    already a small, term-scoped in-memory list; never the full 900MB
    file).

    `resolved_participants` is a per-conversation speaker_id ->
    ArgumentParticipant cache shared with the caller's advocates-loop
    resolution (Task 3) -- a speaker with many turns is resolved via
    _resolve_and_link_participant (a DB round trip + people-counter
    increment) exactly ONCE per conversation, not once per turn, keeping
    the D-14 summary's people-created/matched counts accurate and
    avoiding redundant DB round trips across a conversation's turns.

    `sequence` is a fresh monotonic counter starting at 1 for this
    argument_id/pipeline_run_id pair (T-29-09 -- every row created here
    carries a non-null pipeline_run_id and a sequence unique within
    (argument_id, pipeline_run_id), matching uq_utterance_arg_run_seq).

    Malformed turns (missing "conversation_id"/"text", or missing
    "speaker" on a spoken row) are validated (V5) and counted in
    counters["utterance_rows_errored"] rather than raising an unhandled
    KeyError mid-batch (T-29-10) -- one bad row does not abort the
    argument's whole utterance import.
    """
    sequence = 0
    for turn in turns:
        if not isinstance(turn, dict) or "conversation_id" not in turn or turn.get("text") is None:
            counters["utterance_rows_errored"] = (
                counters.get("utterance_rows_errored", 0) + 1
            )
            print(
                f"WARNING: malformed utterance row {turn!r} -- missing "
                "conversation_id/text key(s), flagged, skipped (V5)."
            )
            continue

        rows = _split_turn_into_rows(turn["text"])
        if not rows:
            continue

        # Resolve the turn's speaker ONCE -- every spoken row split out of
        # this turn shares the same speaker; an all-marker turn needs no
        # participant resolution at all.
        participant = None
        if any(not is_stage for _, is_stage in rows):
            speaker_id = turn.get("speaker")
            if not speaker_id:
                counters["utterance_rows_errored"] = (
                    counters.get("utterance_rows_errored", 0) + 1
                )
                print(
                    f"WARNING: utterance row for conversation "
                    f"{turn.get('conversation_id')!r} missing 'speaker' key "
                    "-- flagged, skipped (V5)."
                )
                continue
            # `in` (not `.get(...) is None`) -- a speaker can legitimately
            # resolve to None (ConvoKit's own unattributed-speaker sentinel,
            # e.g. "<INAUDIBLE>"); using a None-check here would re-attempt
            # resolution on every subsequent turn by that same speaker_id
            # instead of caching the "no attributable speaker" result once.
            if speaker_id not in resolved_participants:
                resolved_participants[speaker_id] = await _resolve_and_link_participant(
                    session=session,
                    argument_id=argument_id,
                    speaker_id=speaker_id,
                    speakers_index=speakers_index,
                    side_code=None,  # BENCH vs advocate side is derived
                    # from speakers.json's authoritative `type` field
                    # inside _resolve_and_link_participant, not a side
                    # code utterance rows carry -- see _is_justice_type.
                    counters=counters,
                )
            participant = resolved_participants[speaker_id]

        for row_text, is_stage in rows:
            sequence += 1
            if is_stage:
                session.add(
                    Utterance(
                        argument_id=argument_id,
                        pipeline_run_id=pipeline_run_id,
                        sequence=sequence,
                        raw_speaker_label=None,  # D-16
                        text=row_text,
                        is_stage_direction=True,
                        side=SideEnum.UNKNOWN,
                        person_id=None,
                        strategy=strategy,
                    )
                )
                counters["stage_direction_utterances_created"] = (
                    counters.get("stage_direction_utterances_created", 0) + 1
                )
            else:
                # participant is None for ConvoKit's own unattributed-speaker
                # sentinel (ambiguous_speaker_id resolved to no Person at
                # all) -- the row's spoken text is still preserved verbatim,
                # just with no speaker attribution, mirroring how a
                # stage-direction row already carries no participant.
                session.add(
                    Utterance(
                        argument_id=argument_id,
                        pipeline_run_id=pipeline_run_id,
                        sequence=sequence,
                        raw_speaker_label=(
                            participant.raw_speaker_label if participant else None
                        ),
                        text=row_text,  # D-18: verbatim, \n preserved
                        is_stage_direction=False,
                        side=participant.side if participant else SideEnum.UNKNOWN,
                        person_id=participant.person_id if participant else None,
                        strategy=strategy,
                    )
                )
                counters["utterances_created"] = (
                    counters.get("utterances_created", 0) + 1
                )

    await session.flush()


# ---------------------------------------------------------------------------
# 29-05 Task 2: per-batch/rollup summary report (D-14)
# ---------------------------------------------------------------------------

# Every counter key referenced by the summary print, in report order. Using
# .get(key, 0) throughout means a missing key never raises -- new counters
# introduced here don't need every call site retrofitted.
_SUMMARY_COUNTER_KEYS: tuple[str, ...] = (
    "arguments_created",
    "skipped_existing",
    "cases_created",
    "utterances_created",
    "stage_direction_utterances_created",
    "people_created",
    "people_matched",
    "speakers_flagged",
    "conversations_errored",
    "utterance_rows_errored",
    "docket_question_conflict",
    "unattributed_speakers_skipped",
)


def _new_counters() -> dict:
    """Fresh, fully-initialized per-term counters dict (D-14)."""
    return {key: 0 for key in _SUMMARY_COUNTER_KEYS} | {"participants_created": 0}


def _accumulate_counters(rollup: dict, term_counters: dict) -> dict:
    """Add one term's counters into the running rollup dict (term-range)."""
    for key in _SUMMARY_COUNTER_KEYS:
        rollup[key] = rollup.get(key, 0) + term_counters.get(key, 0)
    return rollup


def _print_summary(label: str, counters: dict) -> None:
    """
    Print one per-batch summary block (D-14): term year, arguments
    created, arguments skipped (already imported), cases created,
    utterances created, stage-direction utterances created, people
    created, people matched (reused), speakers flagged (ambiguous/missing
    type), cases/conversations errored (join failures or bad rows),
    docket/question conflicts -- a distinct, clearly-labeled count of any
    residual (source_docket, question_number) collision caught at flush
    (CR-01, 29-VERIFICATION.md), never folded into conversations_errored --
    and unattributed speakers skipped (ConvoKit's own "<INAUDIBLE>"/
    "<UNKNOWN>" sentinels, never turned into a Person row).
    """
    c = counters
    print(
        f"{label}: "
        f"{c.get('arguments_created', 0)} arguments created, "
        f"{c.get('skipped_existing', 0)} arguments skipped (already imported), "
        f"{c.get('cases_created', 0)} cases created, "
        f"{c.get('utterances_created', 0)} utterances created, "
        f"{c.get('stage_direction_utterances_created', 0)} stage-direction "
        "utterances created, "
        f"{c.get('people_created', 0)} people created, "
        f"{c.get('people_matched', 0)} people matched (reused), "
        f"{c.get('speakers_flagged', 0)} speakers flagged, "
        f"{c.get('conversations_errored', 0)} conversations errored, "
        f"{c.get('utterance_rows_errored', 0)} utterance rows errored, "
        f"{c.get('docket_question_conflict', 0)} docket/question conflicts, "
        f"{c.get('unattributed_speakers_skipped', 0)} unattributed speakers skipped."
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def run_import_convokit(args) -> None:
    """
    Entry point for `python -m pipeline import-convokit`.

    Resolves --term/--term-range into a sorted list of October Terms,
    validates --corpus-dir exists, loads speakers.json/cases.jsonl once
    (global directories, not term-scoped), then for each term: loads
    conversations.json filtered to that term, streams utterances.jsonl
    ONCE per term (never the whole 900MB file, T-29-03) filtered to that
    term's conversation_id set and grouped into an in-memory
    conversation_id -> [turn, ...] index, then delegates each conversation
    to _import_conversation (entity creation, speaker resolution, and
    utterance import). Prints a per-term summary (D-14); a --term-range
    spanning more than one term also prints a final rollup block.
    """
    terms = _resolve_terms(args)
    corpus_dir = _resolve_corpus_dir(args)

    conversations_path = corpus_dir / "conversations.json"
    cases_path = corpus_dir / "cases.jsonl"
    speakers_path = corpus_dir / "speakers.json"
    utterances_path = corpus_dir / "utterances.jsonl"
    for required in (conversations_path, cases_path, speakers_path, utterances_path):
        if not required.exists():
            raise FileNotFoundError(f"Required corpus file not found: {required}")

    speakers_index = load_speakers(speakers_path)
    # load_cases already indexes by "id" (cases.jsonl's own globally-unique
    # identifier, matching conversations.json's per-conversation "case_id"
    # field); docket_no is a DIFFERENT format, used for the
    # Case.docket_number column -- see Task 2.
    cases_by_case_id = load_cases(cases_path)

    rollup = _new_counters()

    for term in terms:
        conversations = load_conversations_for_term(conversations_path, term)

        # ---- 29-05 Task 1: one streaming pass over utterances.jsonl per
        # term, filtered to this term's conversation_id set (Pattern 3
        # option (b)) -- held in memory only for this term, never the
        # whole 900MB file.
        turns_by_conversation: dict[str, list[dict]] = defaultdict(list)
        wanted_ids = set(conversations.keys())
        for row in stream_utterances_for_conversation_ids(utterances_path, wanted_ids):
            cid = row.get("conversation_id") if isinstance(row, dict) else None
            if cid is not None:
                turns_by_conversation[cid].append(row)

        counters = _new_counters()
        for conversation_id, raw_conversation in conversations.items():
            try:
                async with get_session() as session:
                    await _import_conversation(
                        session=session,
                        conversation_id=conversation_id,
                        raw_conversation=raw_conversation,
                        cases_by_case_id=cases_by_case_id,
                        speakers_index=speakers_index,
                        turns=turns_by_conversation.get(conversation_id, []),
                        counters=counters,
                    )
            except Exception as exc:  # per-row resilience, T-29-05b/Pitfall 5
                counters["conversations_errored"] = (
                    counters.get("conversations_errored", 0) + 1
                )
                print(
                    f"WARNING: conversation {conversation_id!r} raised "
                    f"{exc!r} -- errored, term continues."
                )

        _print_summary(f"Term {term}", counters)
        _accumulate_counters(rollup, counters)

    if len(terms) > 1:
        _print_summary(f"Rollup ({terms[0]}-{terms[-1]}, {len(terms)} terms)", rollup)
