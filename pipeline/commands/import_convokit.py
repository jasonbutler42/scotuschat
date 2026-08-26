"""
Pipeline import-convokit command.

Term-batched orchestration (D-07) for Phase 29's bulk historical import: for
one October Term (--term) or an inclusive range (--term-range), scaffolds
Case / Argument / CaseArgument / ImportRun rows, resolves bench/advocate
speakers into Person + ArgumentParticipant rows, streams each argument's
utterances.jsonl turns into Utterance rows (D-18), splits detected stage
directions into their own rows (D-16/D-17), and prints a per-batch summary
report (D-14).

Built task-by-task:
    29-04 Task 1: CLI subcommand, --term/--term-range validation,
        --corpus-dir validation, and the per-term file-loading skeleton.
    29-04 Task 2: idempotent Case/Argument/CaseArgument/ImportRun entity
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
    python -m pipeline import-convokit --conversation-id 15169

Phase 42 (D-01) added --conversation-id: a scoped single-conversation import
path that derives its own October Term from the conversation's own case_id
field (never operator-supplied), for landing exactly one conversation
without pulling in the rest of its term as a side effect.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
from pathlib import Path

from dateutil import parser as dateutil_parser
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from api.domain.content_digest import compute_utterance_digest
from api.domain.person_names import prepare_name_provenance, split_legacy_full_name
from api.services.argument_uniqueness import is_argument_pair_violation
from api.services.trust import recompute_argument_tier

from api.models.models import (
    Argument,
    ArgumentParticipant,
    ArgumentStatusEnum,
    ArgumentStatusLog,
    Case,
    CaseArgument,
    CourtTenure,
    ImportMethod,
    ImportRun,
    ImportRunStatus,
    ImportSource,
    Person,
    ReviewState,
    SideEnum,
    Utterance,
)
from pipeline.commands.ingest import _derive_slug
from pipeline.corpus import apolitical, stage_directions
from pipeline.corpus.loader import (
    load_cases,
    load_conversation_by_id,
    load_conversations_for_term,
    load_speakers,
    stream_utterances_for_conversation_ids,
)
from pipeline.db import get_session

# Matches the data/corpus/ scaffolding (D-20/D-21) -- the operator copies the
# ConvoKit source files here locally; it is gitignored, not tracked.
DEFAULT_CORPUS_DIR = Path("data/corpus")


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

# Phase 38 (D-14-D-18): source tag stamped on every Person.name_extraction_
# metadata envelope this command writes, matching the same
# {source, raw, confidence, reason, auto_applied} shape
# alembic/versions/0022_person_name_authority.py's legacy backfill and
# import_justices_csv.py already use.
_EXTRACTION_SOURCE = "import_convokit"

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


def _resolve_scoped_conversation(
    args, conversations_path: Path
) -> tuple[str, int] | None:
    """
    Resolve the optional --conversation-id flag (Phase 42 D-01) into a
    (conversation_id, term) pair, or None when the flag is unset -- in
    which case the caller keeps its existing --term/--term-range flow
    untouched.

    Reads the flag via getattr(args, "conversation_id", None) rather than
    args.conversation_id so every pre-existing test Namespace (which has no
    such attribute at all) continues to hit the None branch without an
    AttributeError.

    When --conversation-id IS set: loads the single raw conversation record
    via load_conversation_by_id and fails fast (argparse.ArgumentTypeError,
    naming the rejected id, mirroring _resolve_terms/_resolve_corpus_dir's
    V5 style) when it is absent from conversations.json. Otherwise derives
    the October Term from the record's own "case_id" field (the integer
    before the first underscore, e.g. "1966_642" -> 1966) -- never supplied
    by the operator -- and fails fast the same way when case_id is missing
    or has no parseable term prefix.
    """
    conversation_id = getattr(args, "conversation_id", None)
    if conversation_id is None:
        return None

    raw_conversation = load_conversation_by_id(conversations_path, conversation_id)
    if raw_conversation is None:
        raise argparse.ArgumentTypeError(
            f"--conversation-id {conversation_id!r} was not found in "
            f"{conversations_path}."
        )

    case_id = raw_conversation.get("case_id")
    case_id_str = str(case_id) if case_id else ""
    if "_" not in case_id_str:
        raise argparse.ArgumentTypeError(
            f"--conversation-id {conversation_id!r} has a case_id {case_id!r} "
            "with no '<term>_<docket>' prefix -- cannot derive its October Term."
        )
    term_prefix = case_id_str.split("_", 1)[0]
    try:
        term = int(term_prefix)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--conversation-id {conversation_id!r} has an unparseable "
            f"case_id {case_id!r} -- cannot derive its October Term."
        )

    return conversation_id, term


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
# Task 2: per-conversation entity creation (Case/Argument/CaseArgument/ImportRun)
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
    ImportRun scaffolding (29-04 Task 2), bench/advocate speaker
    resolution (29-04 Task 3), and utterance streaming/stage-direction
    splitting (29-05 Task 1) for this conversation's `turns` (already
    filtered/grouped by the caller from utterances.jsonl, T-29-03).

    Phase 50 (D-01): a conversation whose oyez_transcript_id already
    exists is no longer skipped -- it is handed to _reconcile_conversation
    (the branch this plan's Task 3 establishes; the real compare-and-write
    body lands in plan 50-05).

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
    # Phase 50 (D-01): no more skip-existing early return -- an already-
    # imported conversation is handed to the reconcile branch instead.
    existing_argument_result = await session.execute(
        select(Argument).where(Argument.oyez_transcript_id == conversation_id)
    )
    existing_argument = existing_argument_result.scalar_one_or_none()
    if existing_argument is not None:
        await _reconcile_conversation(
            session=session,
            argument=existing_argument,
            conversation_id=conversation_id,
            turns=turns,
            speakers_index=speakers_index,
            counters=counters,
        )
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
        # editability keys on ArgumentStatusEnum.CANDIDATE (Phase 48 D-01
        # retired PIPELINE as the born state; plan 48-04 swapped those read
        # paths in this same phase), so a corpus argument must start there,
        # not DRAFT, to ever become editable. This kwarg is explicit
        # precisely because an explicit value does not inherit a changed
        # model default — it must be edited directly (48-RESEARCH.md
        # Anti-Patterns).
        status=ArgumentStatusEnum.CANDIDATE,
        oyez_transcript_id=conversation_id,  # D-10
    )
    session.add(argument)
    try:
        await session.flush()
    except IntegrityError as exc:
        if not is_argument_pair_violation(exc):
            raise
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
    # D-03: log the born-state transition immediately on the flush success
    # path -- placing it here means the docket/question conflict-rollback
    # branch above (which returns early) can never orphan a status-log row.
    # This is a genuinely new write site: neither this file nor ingest.py
    # wrote an ArgumentStatusLog row before Phase 48.
    session.add(
        ArgumentStatusLog(argument_id=argument.id, status=ArgumentStatusEnum.CANDIDATE)
    )
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

    # ---- Task 3: speaker resolution for the conversation's advocates ----
    # `resolved_participants` caches speaker_id -> ArgumentParticipant for
    # this conversation only (not persisted/global) -- the advocates loop
    # below, _incoming_utterance_rows (read-only), and _import_utterances
    # (write) all share it, so a speaker with many turns is resolved via
    # _resolve_and_link_participant (a DB round trip + counters increment)
    # exactly ONCE per conversation, not once per turn.
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
            argued_date=argued_date,
        )

    # ---- Phase 50 (D-13, Task 2/Task 3): compute the ordered incoming rows
    # and their frozen content digest BEFORE any DB write on this path --
    # _incoming_utterance_rows resolves/creates NO Person/ArgumentParticipant
    # row, so this is safe to call on the reconcile branch too (see
    # _reconcile_conversation below) without violating its no-write
    # guarantee. Factoring turn-splitting/label-derivation through this ONE
    # helper is what keeps the digest from ever disagreeing with the rows
    # _import_utterances goes on to write.
    incoming_rows = _incoming_utterance_rows(
        turns=turns,
        speakers_index=speakers_index,
        resolved_participants=resolved_participants,
        counters=counters,
    )
    content_digest = compute_utterance_digest(incoming_rows)

    # ---- ImportRun -- this single row performs the combined work the PDF
    # pipeline splits across three separate CLI-invoked stages (ingest,
    # parse, resolve), but is labeled by its function -- the run that writes
    # this argument's Utterance rows -- matching the meaning
    # api/services/arguments.py's get_argument_with_utterances and
    # api/services/admin_jobs.py's get_run_id_for_step already give
    # step="parse" everywhere else in the codebase. Created BEFORE any
    # utterance write path (T-29-09; the participant resolution above does
    # not write Utterance rows, so this ordering constraint still holds).
    # Phase 47 (D-03's locked mapping, convokit_import -> corpus/direct):
    # declares source=CORPUS/method=DIRECT explicitly; external_id is a
    # dual-write of the ConvoKit conversation id (Argument.oyez_transcript_id,
    # set above at argument creation, remains the live dedup key and public
    # API field -- RESEARCH.md Pitfall 1). No pdf_path/pdf_url -- the corpus
    # path fabricates no PDF artifacts (PROV-06). content_digest (D-13) is
    # stamped at construction time, not via a later UPDATE.
    run = ImportRun(
        argument_id=argument.id,
        step="parse",
        status=ImportRunStatus.COMPLETED,
        source=ImportSource.CORPUS,
        method=ImportMethod.DIRECT,
        external_id=conversation_id,
        content_digest=content_digest,
    )
    session.add(run)
    await session.flush()

    # ---- 29-05 Task 1: write this conversation's precomputed rows as
    # Utterance rows, resolving any bench/turn-discovered participant not
    # already in resolved_participants from the advocates loop above ----
    await _import_utterances(
        session=session,
        argument_id=argument.id,
        import_run_id=run.id,
        rows=incoming_rows,
        speakers_index=speakers_index,
        resolved_participants=resolved_participants,
        counters=counters,
        argued_date=argued_date,
    )

    # D-07/writer #1 (48-RESEARCH.md): stamp the tier last, after every
    # constituent (utterances, participants) for this argument has been
    # written -- the floor must see the complete set. get_session() commits
    # on clean exit of run_import_convokit's `async with` block, so this
    # call is inside the same birth transaction; no session.commit() is
    # added here (48-RESEARCH.md Pitfall 2).
    #
    # Phase 50 (D-14/D-19): no AdminJob is created here -- the corpus path
    # no longer fabricates a job to borrow the PDF path's resolve/approve
    # machinery. A corpus argument reaches DRAFT via api.services.
    # admin_arguments.approve_argument instead (Task 3, argument-scoped).
    await recompute_argument_tier(session, argument.id)


async def _reconcile_conversation(
    session,
    argument: Argument,
    conversation_id: str,
    turns: list[dict],
    speakers_index: dict,
    counters: dict,
) -> None:
    """
    Phase 50 (D-01/D-06/D-09/D-13, OQ-3; 50-01-PLAN.md Task 3, item 5):
    the reconcile branch a repeat corpus import over an already-imported
    conversation takes, replacing the old skip-existing early return.

    THIS TASK establishes only the branch, the digest read, and the no-op
    guarantee D-09's byte-identical proof rests on -- it writes NOTHING in
    either branch below. The full compare-and-apply body (D-02's field
    walk, D-07's restamp, D-08's published check, D-10's utterance
    rewrite) is built in plan 50-05 of this same phase.

    Reads the argument's LATEST step="parse" run's content_digest (OQ-3 --
    never a step="reconcile" run's; there are none yet at this point in
    the phase) and computes the incoming digest via
    _incoming_utterance_rows/compute_utterance_digest -- the SAME
    write-free helper _import_conversation's first-import path uses, so an
    identical re-import produces an identical digest with zero DB writes
    (no participant resolution, no Utterance rows) on this path.

    Equal digests: counters["arguments_unchanged"] increments, nothing is
    written, nothing is recorded.

    Unequal digests, OR the stored digest is NULL (the row predates this
    phase and was never stamped): counters["arguments_reconciled"]
    increments and a WARNING names the argument id and conversation id --
    still nothing is written. A future pass (plan 50-05) is what actually
    applies D-02's field-level compare-and-write here.
    """
    latest_parse_digest = (
        await session.execute(
            select(ImportRun.content_digest)
            .where(ImportRun.argument_id == argument.id, ImportRun.step == "parse")
            .order_by(ImportRun.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    # No Person/ArgumentParticipant resolution happens here -- an empty
    # resolved_participants seed means every row's raw_speaker_label is
    # derived purely from speakers_index (a pure function of speaker_id),
    # identical to what the first-import path would have derived via the
    # advocates loop, and with zero DB writes either way.
    incoming_rows = _incoming_utterance_rows(
        turns=turns,
        speakers_index=speakers_index,
        resolved_participants={},
        counters=counters,
    )
    incoming_digest = compute_utterance_digest(incoming_rows)

    if latest_parse_digest is not None and latest_parse_digest == incoming_digest:
        counters["arguments_unchanged"] = counters.get("arguments_unchanged", 0) + 1
        return

    counters["arguments_reconciled"] = counters.get("arguments_reconciled", 0) + 1
    print(
        f"WARNING: conversation {conversation_id!r} (argument_id="
        f"{argument.id}) content digest differs from the stored step="
        "'parse' run (or none is stored yet) -- reconcile compare-and-"
        "write is not implemented until plan 50-05; no rows written."
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


def _apply_extracted_name_provenance(person: Person, full_name: str) -> None:
    """
    Persist a conservative interpreted-parts + provenance extraction for
    `person` from its `full_name` (D-14-D-18), reusing the same pure
    `api.domain.person_names.split_legacy_full_name` splitter and
    envelope shape (`{source, raw, confidence, reason, auto_applied}`)
    alembic/versions/0022_person_name_authority.py's legacy backfill
    already established.

    Every call refreshes `provenance_metadata` unconditionally (D-17 --
    "if extraction/reprocessing occurs later, replace the extracted
    reference with the latest result"). Structured parts are only ever
    written when the row currently carries NO structured part at all
    (mirrors migration 0022's own guard exactly -- a row that already has
    any operator/import-authored part is left completely untouched, never
    partially clobbered) and only for a High-confidence, round-trip-exact
    split (`auto_apply=True`, D-11) -- an ambiguous/uncertain interpretation
    (Low/Medium) is still recorded in the provenance envelope so the
    operator can see what the extractor thought it saw (D-18), but is never
    silently written into the authoritative saved columns, and the row's
    `review_state` is set to NEEDS_REVIEW for the People directory's Name
    review filter (D-12).

    Note the asymmetry deliberately (Phase 49 D-08, D-11, D-24): the
    confident branch below sets UNREVIEWED, never a human-only operator
    review state -- only a human action ever produces one; an importer
    must never mint one.
    """
    split = split_legacy_full_name(full_name)
    provenance = prepare_name_provenance(None, full_name, split.confidence)
    person.provenance_metadata = {
        "source": _EXTRACTION_SOURCE,
        "raw": provenance.raw,
        "confidence": provenance.confidence,
        "reason": split.reason,
        "auto_applied": split.auto_apply,
    }

    has_any_part = bool(
        person.first_name or person.middle_name or person.last_name or person.name_suffix
    )
    if has_any_part:
        # D-16: never overwrite a row that already carries any saved part --
        # whether authored by an operator or a prior confident extraction.
        return

    if split.auto_apply:
        person.first_name = split.first_name
        person.middle_name = split.middle_name
        person.last_name = split.last_name
        person.name_suffix = split.name_suffix
        person.review_state = ReviewState.UNREVIEWED
    else:
        person.review_state = ReviewState.NEEDS_REVIEW


async def _resolve_person(
    session, speaker_id: str, full_name: str, is_justice: bool, counters: dict
) -> Person:
    """
    Resolve or create a Person for `speaker_id`, per D-11's key order:
    Person.oyez_speaker_id checked FIRST, then Person.full_name (D-13, same
    exact-match dedup as the justice importer). When a full_name match is
    found with no oyez_speaker_id yet, backfill it (D-11) so the next run
    matches by the stable ID.

    Phase 38 (D-14-D-18, T-38-10/T-38-11): every resolution path -- brand
    new, oyez_speaker_id match, or full_name-only match -- also runs
    `_apply_extracted_name_provenance` so provenance_metadata is always
    refreshed and blank rows get a conservative interpreted-parts prefill.
    `full_name` itself is never touched by this function on any matched
    path -- only `_get_or_create_case`-style ID matching decides identity,
    exactly as before (D-13 dedup precedent).

    Increments counters["people_matched"] on either reuse path, or
    counters["people_created"] when a brand-new Person row is created
    (D-14 per-batch summary).
    """
    result = await session.execute(
        select(Person).where(Person.oyez_speaker_id == speaker_id)
    )
    person = result.scalar_one_or_none()
    if person is not None:
        _apply_extracted_name_provenance(person, person.full_name)
        counters["people_matched"] = counters.get("people_matched", 0) + 1
        return person

    result = await session.execute(select(Person).where(Person.full_name == full_name))
    person = result.scalar_one_or_none()
    if person is not None:
        if person.oyez_speaker_id is None:
            person.oyez_speaker_id = speaker_id  # D-11 backfill
        _apply_extracted_name_provenance(person, person.full_name)
        counters["people_matched"] = counters.get("people_matched", 0) + 1
        return person

    person = Person(
        full_name=full_name,
        oyez_speaker_id=speaker_id,
        is_justice=is_justice,
    )
    _apply_extracted_name_provenance(person, full_name)
    session.add(person)
    await session.flush()
    counters["people_created"] = counters.get("people_created", 0) + 1
    return person


async def _check_bench_tenure_mismatch(session, person_id: int, argued_date) -> bool:
    """
    Phase 42 Task 3 (item 2, `bench-warn-only`): True when `person_id` has
    NO `CourtTenure` row covering `argued_date` -- inclusive start
    boundary (`start_date <= argued_date`), open-ended `end_date` treated
    as still active (`end_date IS NULL OR end_date >= argued_date`).
    Read-only: issues a single `select(CourtTenure)`, never creates,
    updates, or deletes a `CourtTenure` row (D-03) and never touches
    `Person.is_justice`.
    """
    result = await session.execute(
        select(CourtTenure).where(
            CourtTenure.person_id == person_id,
            CourtTenure.start_date <= argued_date,
            or_(CourtTenure.end_date.is_(None), CourtTenure.end_date >= argued_date),
        )
    )
    return result.first() is None


async def _resolve_and_link_participant(
    session,
    argument_id: int,
    speaker_id: str,
    speakers_index: dict,
    side_code,
    counters: dict,
    argued_date=None,
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

    `argued_date` (Phase 42 Task 3, Review Gate item 2, option
    `bench-warn-only`, operator-approved 2026-07-30): when the resolved
    speaker is typed a Justice AND `argued_date` is not None, cross-checks
    `CourtTenure` coverage of that date via `_check_bench_tenure_mismatch`.
    A mismatch increments `counters["bench_tenure_mismatch"]` and prints a
    warning naming the speaker id, `argued_date`, and the earliest
    `CourtTenure.start_date` on record for that person -- `side` is left
    UNCHANGED (still BENCH) per the operator's warn-and-count-only
    decision; no `ArgumentParticipant.side` reassignment happens here.
    When `argued_date` is None (nullable column, no parseable transcript
    date), no tenure check runs and today's behavior is unchanged --
    trusting speakers.json's `type` outright.
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

    if is_justice and argued_date is not None:
        mismatch = await _check_bench_tenure_mismatch(session, person.id, argued_date)
        if mismatch:
            counters["bench_tenure_mismatch"] = (
                counters.get("bench_tenure_mismatch", 0) + 1
            )
            earliest_start_result = await session.execute(
                select(func.min(CourtTenure.start_date)).where(
                    CourtTenure.person_id == person.id
                )
            )
            earliest_start = earliest_start_result.scalar()
            print(
                f"WARNING: speaker {speaker_id!r} (person_id={person.id}) is "
                "typed a Justice in speakers.json but no CourtTenure row "
                f"covers argued_date {argued_date} -- earliest CourtTenure "
                f"start_date on record for this person is {earliest_start} "
                "(bench_tenure_mismatch, D-03 flag-only, side unchanged)."
            )

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
        # Phase 49 D-20's locked mapping: every corpus-resolution mechanism
        # (oyez_speaker_id match, full_name fallback, or brand-new person)
        # gets source=CORPUS/method=DIRECT -> TRUSTED, mirroring the
        # ImportRun stamp this same module already writes above. Without
        # this, source/method stay NULL and derive_tier floors every
        # freshly-resolved corpus participant to UNCERTAIN (D-18).
        source=ImportSource.CORPUS,
        method=ImportMethod.DIRECT,
        # Phase 50 (D-04): the explicit re-import pairing key -- the
        # ConvoKit speaker id this participant row was resolved from.
        # Threaded into every corpus participant this importer writes so
        # plan 50-05's reconcile pass can pair by id rather than by the
        # display-string raw_speaker_label dedup key above.
        oyez_speaker_id=speaker_id,
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


def _incoming_utterance_rows(
    turns: list[dict],
    speakers_index: dict,
    resolved_participants: dict[str, "ArgumentParticipant | None"],
    counters: dict,
) -> list[dict]:
    """
    Phase 50 (D-13, Task 3 item 3): compute the ordered incoming row dicts
    `_import_utterances` would write for ONE argument's `turns`, WITHOUT
    writing any Utterance row and WITHOUT resolving or creating any
    Person/ArgumentParticipant row -- so this is safe to call from
    `_reconcile_conversation`'s no-write digest comparison as well as the
    first-import path (D-09's byte-identical proof depends on this).

    Factors `_import_utterances`'s (pre-Phase-50) turn-splitting,
    malformed-row validation (V5), and sequence-assignment logic through
    this ONE place -- two implementations of "the incoming row set" is
    exactly how the digest would start disagreeing with the rows actually
    written (D-13).

    Each returned row dict carries the four D-13-frozen digest fields
    (`sequence`, `raw_speaker_label`, `text`, `is_stage_direction`) PLUS one
    extra field, `speaker_id` (`None` for stage-direction rows and for rows
    with no attributable speaker) -- `compute_utterance_digest` ignores any
    key outside its frozen four, so this extra field never affects the
    digest. It exists purely so a caller that DOES need to write Utterance
    rows (`_import_utterances`) can resolve/create the row's participant
    without re-deriving `speaker_id` from `turns` a second time.

    `raw_speaker_label` is derived the SAME way
    `_resolve_and_link_participant` derives `full_name` -- directly from
    `speakers_index`, never via a DB round trip -- because that value is a
    pure function of `(speaker_id, speakers_index)`, identical whether the
    participant was resolved via the advocates loop, turn discovery, or (on
    a reconcile pass) never resolved at all. `resolved_participants` is
    read-only here: an already-resolved advocate's `raw_speaker_label` is
    reused directly instead of recomputed; this function NEVER writes to
    `resolved_participants` -- that cache mutation stays
    `_import_utterances`'s job.

    Malformed turns/rows (missing "conversation_id"/"text", or missing
    "speaker" on a spoken row) are counted in
    counters["utterance_rows_errored"] and skipped (V5), matching
    pre-Phase-50 behavior exactly.
    """
    rows: list[dict] = []
    sequence = 0
    seen_unattributed: set[str] = set()

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

        split_rows = _split_turn_into_rows(turn["text"])
        if not split_rows:
            continue

        speaker_id: str | None = None
        raw_speaker_label: str | None = None
        if any(not is_stage for _, is_stage in split_rows):
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

            if speaker_id in resolved_participants:
                # Already resolved (advocates loop) -- reuse its
                # raw_speaker_label directly, no recomputation, no write.
                cached = resolved_participants[speaker_id]
                if cached is None:
                    raw_speaker_label = None
                    speaker_id = None  # no attributable speaker
                else:
                    raw_speaker_label = cached.raw_speaker_label
            else:
                speaker_meta = speakers_index.get(speaker_id) or {}
                if _is_unattributed_speaker_type(speaker_meta):
                    if speaker_id not in seen_unattributed:
                        seen_unattributed.add(speaker_id)
                        counters["unattributed_speakers_skipped"] = (
                            counters.get("unattributed_speakers_skipped", 0) + 1
                        )
                    raw_speaker_label = None
                    speaker_id = None  # no attributable speaker
                else:
                    raw_speaker_label = (
                        speaker_meta.get("name")
                        or speaker_meta.get("full_name")
                        or turn.get("speaker")
                    )

        for row_text, is_stage in split_rows:
            sequence += 1
            rows.append(
                {
                    "sequence": sequence,
                    "raw_speaker_label": None if is_stage else raw_speaker_label,
                    "text": row_text,
                    "is_stage_direction": is_stage,
                    "speaker_id": None if is_stage else speaker_id,
                }
            )

    return rows


async def _import_utterances(
    session,
    argument_id: int,
    import_run_id: int,
    rows: list[dict],
    speakers_index: dict,
    resolved_participants: dict[str, ArgumentParticipant],
    counters: dict,
    argued_date=None,
) -> None:
    """
    Write one Utterance row per precomputed row dict from
    `_incoming_utterance_rows` (D-13; see that function's docstring for why
    turn-splitting/sequence-assignment/label-derivation was factored out of
    this function), in the same streamed (transcript) order the rows were
    computed in.

    `argued_date` (Phase 42 Task 3, item 2) is threaded through to every
    fresh `_resolve_and_link_participant` call this function makes below
    (a speaker first discovered while streaming utterances, not already
    present in `resolved_participants` from the advocates loop), so the
    bench-tenure mismatch check runs for those speakers too.

    `resolved_participants` is a per-conversation speaker_id ->
    ArgumentParticipant cache shared with the caller's advocates-loop
    resolution (Task 3) -- a speaker with many turns is resolved via
    `_resolve_and_link_participant` (a DB round trip + people-counter
    increment) exactly ONCE per conversation, not once per turn, keeping
    the D-14 summary's people-created/matched counts accurate and avoiding
    redundant DB round trips across a conversation's turns. A row's
    `speaker_id` is `None` for a stage-direction row or a row with no
    attributable speaker (ConvoKit's own unattributed-speaker sentinel) --
    matching the pre-Phase-50 `participant is None` path exactly, and never
    triggering a resolution call.

    `sequence` on each row is already a fresh monotonic counter starting at
    1 for this argument_id/import_run_id pair (T-29-09 -- every row created
    here carries a non-null import_run_id and a sequence unique within
    (argument_id, import_run_id), matching uq_utterance_arg_run_seq).
    """
    # D-04 (Phase 42 Task 2, section-hint-derive): tracks which side
    # currently owns the open section, and whether a respondent section
    # has been seen yet -- both persist across the WHOLE conversation's
    # rows (a section can span many turns), matching parse.py's
    # non-cascading section_hint semantics (see
    # test_section_hint_not_cascade: exactly one utterance per section
    # carries the hint, every later utterance in that section is null).
    # The corpus importer has no page-by-page TOC markers to key off of --
    # instead, a PETITIONER/RESPONDENT/AMICUS-side row whose resolved side
    # differs from the side that opened the current section starts a new
    # one; a PETITIONER side arriving after a respondent section has
    # already started yields "rebuttal" rather than a second "petitioner".
    # BENCH/UNKNOWN rows and rows with no attributable speaker never
    # change these locals and never carry a hint.
    current_section_side: SideEnum | None = None
    respondent_section_started = False

    for row in rows:
        sequence = row["sequence"]
        text = row["text"]

        if row["is_stage_direction"]:
            session.add(
                Utterance(
                    argument_id=argument_id,
                    import_run_id=import_run_id,
                    sequence=sequence,
                    raw_speaker_label=None,  # D-16
                    text=text,
                    is_stage_direction=True,
                    side=SideEnum.UNKNOWN,
                    person_id=None,
                    section_hint=None,  # D-04: stage directions never
                    # carry or change a section.
                )
            )
            counters["stage_direction_utterances_created"] = (
                counters.get("stage_direction_utterances_created", 0) + 1
            )
            continue

        # `speaker_id` is None for "no attributable speaker" rows -- the
        # row's spoken text is still preserved verbatim, just with no
        # speaker attribution, mirroring how a stage-direction row already
        # carries no participant.
        speaker_id = row.get("speaker_id")
        participant: ArgumentParticipant | None = None
        if speaker_id:
            # `in` (not `.get(...) is None`) -- a speaker can legitimately
            # resolve to None; using a None-check here would re-attempt
            # resolution on every subsequent row by that same speaker_id
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
                    argued_date=argued_date,
                )
            participant = resolved_participants[speaker_id]

        resolved_side = participant.side if participant else SideEnum.UNKNOWN

        # D-04: derive section_hint. Only a PETITIONER/RESPONDENT/AMICUS
        # side can open a section; BENCH, UNKNOWN, and "no attributable
        # speaker" rows fall through with section_hint left None and
        # current_section_side/respondent_section_started untouched (they
        # never change the current section). A side that matches the side
        # which already opened the current section also gets None -- this
        # is what keeps the hint non-cascading (one row per section).
        section_hint = None
        if (
            resolved_side in (SideEnum.PETITIONER, SideEnum.RESPONDENT, SideEnum.AMICUS)
            and resolved_side != current_section_side
        ):
            if resolved_side == SideEnum.RESPONDENT:
                section_hint = "respondent"
                respondent_section_started = True
            elif resolved_side == SideEnum.PETITIONER:
                # A petitioner side returning after a respondent section
                # already opened is rebuttal, not a second "petitioner".
                section_hint = (
                    "rebuttal" if respondent_section_started else "petitioner"
                )
            else:  # SideEnum.AMICUS
                section_hint = "amicus"
            current_section_side = resolved_side

        session.add(
            Utterance(
                argument_id=argument_id,
                import_run_id=import_run_id,
                sequence=sequence,
                raw_speaker_label=row["raw_speaker_label"],
                text=text,  # D-18: verbatim, \n preserved
                is_stage_direction=False,
                side=resolved_side,
                person_id=participant.person_id if participant else None,
                section_hint=section_hint,
            )
        )
        counters["utterances_created"] = counters.get("utterances_created", 0) + 1

    await session.flush()


# ---------------------------------------------------------------------------
# 29-05 Task 2: per-batch/rollup summary report (D-14)
# ---------------------------------------------------------------------------

# Every counter key referenced by the summary print, in report order. Using
# .get(key, 0) throughout means a missing key never raises -- new counters
# introduced here don't need every call site retrofitted.
_SUMMARY_COUNTER_KEYS: tuple[str, ...] = (
    "arguments_created",
    # Phase 50 (D-01/PD-03): "skipped_existing" is RETIRED, not repurposed
    # -- D-01 removes the early return no code path incremented it from,
    # and a permanently-zero "arguments skipped" line would misreport what
    # the batch did. Replaced by arguments_reconciled/arguments_unchanged
    # below (the reconcile branch this plan's Task 3 establishes).
    "arguments_reconciled",
    "arguments_unchanged",
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
    # Phase 42 Task 3 (item 2, bench-warn-only, operator-approved
    # 2026-07-30): a speaker typed a Justice in speakers.json with no
    # CourtTenure row covering the argument's argued_date. Flag-only --
    # side is never reassigned for this counter (D-03).
    "bench_tenure_mismatch",
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
    created, arguments reconciled (content differs, or no stored digest --
    Phase 50 D-01/D-13, plan 50-05 does the actual compare-and-write) and
    arguments unchanged (identical content digest, zero-write no-op), cases
    created, utterances created, stage-direction utterances created, people
    created, people matched (reused), speakers flagged (ambiguous/missing
    type), cases/conversations errored (join failures or bad rows),
    docket/question conflicts -- a distinct, clearly-labeled count of any
    residual (source_docket, question_number) collision caught at flush
    (CR-01, 29-VERIFICATION.md), never folded into conversations_errored --
    unattributed speakers skipped (ConvoKit's own "<INAUDIBLE>"/
    "<UNKNOWN>" sentinels, never turned into a Person row), and
    bench-tenure mismatches (Phase 42 Task 3, item 2: a Justice-typed
    speaker with no CourtTenure row covering argued_date -- flag-only,
    side never reassigned).
    """
    c = counters
    print(
        f"{label}: "
        f"{c.get('arguments_created', 0)} arguments created, "
        f"{c.get('arguments_reconciled', 0)} arguments reconciled, "
        f"{c.get('arguments_unchanged', 0)} arguments unchanged, "
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
        f"{c.get('unattributed_speakers_skipped', 0)} unattributed speakers skipped, "
        f"{c.get('bench_tenure_mismatch', 0)} bench tenure mismatches."
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def run_import_convokit(args) -> None:
    """
    Entry point for `python -m pipeline import-convokit`.

    Resolves --term/--term-range into a sorted list of October Terms, OR --
    when --conversation-id is set (Phase 42 D-01) -- resolves that single
    conversation's own derived term instead and skips _resolve_terms
    entirely (which would otherwise raise, since neither term flag is
    present in scoped mode). Validates --corpus-dir exists, loads
    speakers.json/cases.jsonl once (global directories, not term-scoped),
    then for each term: loads conversations.json filtered to that term --
    narrowed further to just the scoped conversation id when scoped mode is
    active, so the streaming pass below only ever touches one conversation
    instead of the whole term -- streams utterances.jsonl ONCE per term
    (never the whole 900MB file, T-29-03) filtered to that term's (or that
    one scoped conversation's) conversation_id set and grouped into an
    in-memory conversation_id -> [turn, ...] index, then delegates each
    conversation to _import_conversation (entity creation, speaker
    resolution, and utterance import). Prints a per-term summary (D-14); a
    --term-range spanning more than one term also prints a final rollup
    block.
    """
    corpus_dir = _resolve_corpus_dir(args)

    conversations_path = corpus_dir / "conversations.json"
    cases_path = corpus_dir / "cases.jsonl"
    speakers_path = corpus_dir / "speakers.json"
    utterances_path = corpus_dir / "utterances.jsonl"
    for required in (conversations_path, cases_path, speakers_path, utterances_path):
        if not required.exists():
            raise FileNotFoundError(f"Required corpus file not found: {required}")

    scoped = _resolve_scoped_conversation(args, conversations_path)
    if scoped is not None:
        scoped_conversation_id, scoped_term = scoped
        terms = [scoped_term]
    else:
        scoped_conversation_id = None
        terms = _resolve_terms(args)

    speakers_index = load_speakers(speakers_path)
    # load_cases already indexes by "id" (cases.jsonl's own globally-unique
    # identifier, matching conversations.json's per-conversation "case_id"
    # field); docket_no is a DIFFERENT format, used for the
    # Case.docket_number column -- see Task 2.
    cases_by_case_id = load_cases(cases_path)

    rollup = _new_counters()

    for term in terms:
        conversations = load_conversations_for_term(conversations_path, term)

        if scoped_conversation_id is not None:
            # D-01: narrow to exactly the one scoped conversation BEFORE
            # wanted_ids is built below, so the streaming pass over the
            # 900MB utterances.jsonl file filters to one conversation
            # instead of the whole term.
            conversations = {
                cid: conv
                for cid, conv in conversations.items()
                if cid == scoped_conversation_id
            }
            if not conversations:
                raise argparse.ArgumentTypeError(
                    f"--conversation-id {scoped_conversation_id!r} was not "
                    f"found among term {term}'s conversations after "
                    "narrowing."
                )

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
