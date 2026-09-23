"""
Pipeline import-convokit command.

Term-batched orchestration for Phase 29's bulk historical import: for
one October Term (--term) or an inclusive range (--term-range), scaffolds
Case / Argument / CaseArgument / ImportRun rows, resolves bench/advocate
speakers into Person + ArgumentParticipant rows, streams each argument's
utterances.jsonl turns into Utterance rows, splits detected stage
directions into their own rows, and prints a per-batch summary
report.

Built task-by-task:
    29-04 Task 1: CLI subcommand, --term/--term-range validation,
        --corpus-dir validation, and the per-term file-loading skeleton.
    29-04 Task 2: idempotent Case/Argument/CaseArgument/ImportRun entity
        creation, apolitical field stripping, and per-conversation
        resilience.
    29-04 Task 3: bench/advocate speaker resolution into Person (D-11 key
        order) + ArgumentParticipant rows (side classification, D-12/D-13).
    29-05 Task 1: streaming utterance import -- one Utterance row per
        ConvoKit turn, \\n segment boundaries preserved verbatim, stage
        directions split into their own rows via
        pipeline.corpus.stage_directions.detect_stage_direction.
    29-05 Task 2: per-batch/rollup summary report.

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
never loaded whole -- one streaming pass per term is made via
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

Phase 42 added --conversation-id: a scoped single-conversation import
path that derives its own October Term from the conversation's own case_id
field (never operator-supplied), for landing exactly one conversation
without pulling in the rest of its term as a side effect.
"""

from __future__ import annotations

import argparse
import functools
from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from dateutil import parser as dateutil_parser
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError

from api.domain.argument_slug import derive_argument_slug
from api.domain.authority import WriteDecision, decide_write
from api.domain.content_digest import compute_utterance_digest
from api.domain.person_names import prepare_name_provenance, split_legacy_full_name
from api.services.admin_review import (
    _is_gap_fill,  # noqa: F401 -- Phase 50: imported directly (never
    # re-implemented) so the lazy-run predictor below can never diverge from
    # the gate's own gap-fill decision.
    _normalize_generic,  # noqa: F401 -- ditto, for the D-03 blank-incoming
    # predictor (argument/case fields) and the published-freeze record-only
    # branch's own no-opinion check.
    _values_differ,  # noqa: F401 -- ditto, the equality predictor.
    apply_argument_value_change,
    apply_case_value_change,
    apply_participant_value_change,
    apply_person_value_change,
    record_value_discrepancy,
)
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

# Matches the data/corpus/ scaffolding -- the operator copies the
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
    reused rather than duplicated; the existing row's oyez_case_id
    is then backfilled, mirroring the same pattern already used for
    Person.oyez_speaker_id. term_year comes DIRECTLY from
    cases.jsonl's allowlisted "year" field -- never derived from
    argued_date's calendar year. Lead-docket-only: this is the single
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
        # Phase 50 plan 50-05 (Rule 2 deviation, D-21/D-22): see the
        # matching Argument(...) comment above -- same gap, same fix.
        source=ImportSource.CORPUS,
        method=ImportMethod.DIRECT,
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


async def _taken_slugs_like(session, base_slug: str) -> set[str]:
    """
    Return every existing `Argument.slug` value starting with `base_slug`
    (Phase 51 plan 51-02, D-12). Scoped by prefix rather than a full-table
    scan -- collisions only matter among arguments that share the same
    case-name-derived base. `session.flush()` is called before every
    `Argument` insert in this module, so a slug minted earlier in the SAME
    batch is already visible to this SELECT even though the batch has not
    committed yet.
    """
    result = await session.execute(
        select(Argument.slug).where(Argument.slug.like(f"{base_slug}%"))
    )
    return {row[0] for row in result.all() if row[0] is not None}


async def _import_conversation(
    session,
    conversation_id: str,
    raw_conversation: dict,
    cases_by_case_id: dict[str, dict],
    speakers_index: dict,
    turns: list[dict],
    counters: dict,
    dry_run: bool = False,
) -> None:
    """
    Import one conversation: idempotent Case/Argument/CaseArgument/
    ImportRun scaffolding (29-04 Task 2), bench/advocate speaker
    resolution (29-04 Task 3), and utterance streaming/stage-direction
    splitting (29-05 Task 1) for this conversation's `turns` (already
    filtered/grouped by the caller from utterances.jsonl, T-29-03).

    A conversation whose oyez_transcript_id already
    exists is no longer skipped -- it is handed to _reconcile_conversation,
    which ALWAYS reconciles (the real compare-and-write body plan 50-05
    builds out; plan 50-01 only established the branch and the digest
    no-op guarantee).

    Phase 50 plan 50-05 (D-28, Task 3): `dry_run=True` on the FIRST-import
    path (no existing argument) skips the whole conversation with a
    counted, printed line rather than half-applying entity creation --
    scoped this way per the plan's own note ("never silently import on a
    dry run") rather than threading dry-run through every write site below.
    The reconcile branch's own dry-run handling is separate (see
    _reconcile_conversation / _predict_reconcile).

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

    # ---- Idempotent Argument dedup on oyez_transcript_id ----
    # No more skip-existing early return -- an already-
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
            conversation=conversation,
            case_fields=case_fields,
            turns=turns,
            speakers_index=speakers_index,
            counters=counters,
            dry_run=dry_run,
        )
        return

    if dry_run:
        # D-28/Task 3: a dry run never creates an argument either -- skip
        # the whole conversation with a printed line (PD-17 fixes the full
        # counter set; this path adds none of its own) rather than
        # half-applying first-import entity creation.
        print(
            f"DRY RUN: conversation {conversation_id!r} has no existing "
            "argument -- first-import creation is skipped under --dry-run "
            "(D-28); would create one Argument/Case/CaseArgument/ImportRun "
            "set on a real run."
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

    # D-12/D-13: mint this argument's public slug once, here, at first
    # import. question_number is the primary suffix discriminator (see
    # api/domain/argument_slug.py's module docstring for the corpus-scale
    # rationale) -- it is always populated and unique-by-construction for
    # this write path, unlike argued_date which the real corpus leaves
    # None or colliding for ~46% of multi-argument cases.
    case_name = _case_name_from_fields(case_fields)
    base_slug_for_taken_query = _derive_slug(case_name) or "argument"
    taken_slugs = await _taken_slugs_like(session, base_slug_for_taken_query)
    argument_slug = derive_argument_slug(
        case_name,
        question_number=next_question_number,
        argued_date=argued_date,
        taken=taken_slugs,
    )

    argument = Argument(
        argued_date=argued_date,
        question_number=next_question_number,
        source_docket=case_fields["docket_no"],
        slug=argument_slug,
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
        # Phase 50 plan 50-05 (Rule 2 deviation, D-21/D-22): declared at
        # write time like every other corpus-stamped row in this module
        # (ArgumentParticipant, ImportRun) -- without this, a fresh corpus
        # argument's source/method stay NULL until the FIRST reconcile
        # pass restamps them, which is itself a real column-value
        # change and breaks D-09's byte-identical re-import guarantee.
        source=ImportSource.CORPUS,
        method=ImportMethod.DIRECT,
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
    # Log the born-state transition immediately on the flush success
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
    # path fabricates no PDF artifacts. content_digest is
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

    # D-07/writer #1: stamp the tier last, after every
    # constituent (utterances, participants) for this argument has been
    # written -- the floor must see the complete set. get_session() commits
    # on clean exit of run_import_convokit's `async with` block, so this
    # call is inside the same birth transaction; no session.commit() is
    # added here (48-RESEARCH.md Pitfall 2).
    #
    # No AdminJob is created here -- the corpus path
    # no longer fabricates a job to borrow the PDF path's resolve/approve
    # machinery. A corpus argument reaches DRAFT via api.services.
    # admin_arguments.approve_argument instead (Task 3, argument-scoped).
    await recompute_argument_tier(session, argument.id)


class _ReconcileContext:
    """
    Phase 50 plan 50-05 (Task 1): per-argument bookkeeping shared by every
    helper in a single `_reconcile_conversation` pass -- the session, the
    argument, the running counters, the dry-run flag, and the lazily
    minted `step="reconcile"` `ImportRun` id. One instance per
    reconcile call; never reused across arguments.
    """

    def __init__(self, *, session, argument, conversation_id, speakers_index, counters, dry_run):
        self.session = session
        self.argument = argument
        self.conversation_id = conversation_id
        self.speakers_index = speakers_index
        self.counters = counters
        self.dry_run = dry_run
        self.reconcile_run_id: int | None = None


async def _ensure_reconcile_run(ctx: _ReconcileContext) -> int:
    """
    Create the `step="reconcile"` `ImportRun` on first call and
    return its id thereafter -- memoized on `ctx.reconcile_run_id`.

    MUST NEVER be called speculatively -- only from a code path that is
    about to write a value or record a discrepancy (see `_needs_reconcile_
    run` below, which every call site consults first) -- because a true
    no-op must add zero rows for D-09's byte-identical proof to be
    possible. Never called in dry-run mode (the dry-run branch never
    calls this function at all).
    """
    if ctx.reconcile_run_id is not None:
        return ctx.reconcile_run_id
    run = ImportRun(
        argument_id=ctx.argument.id,
        step="reconcile",
        status=ImportRunStatus.COMPLETED,
        source=ImportSource.CORPUS,
        method=ImportMethod.DIRECT,
        external_id=ctx.conversation_id,
        content_digest=None,  # A reconcile run carries no comparison digest
    )
    ctx.session.add(run)
    await ctx.session.flush()
    ctx.reconcile_run_id = run.id
    return run.id


def _needs_reconcile_run(
    field: str, incoming_value, existing_value, *, has_no_opinion_check: bool
) -> bool:
    """
    Predicts whether calling the real gate for this field could write-and-
    record or reject-and-record -- i.e. whether `_ensure_reconcile_run`
    must fire before the gate call. Used ONLY to decide whether to
    eagerly mint the lazy run; it never makes or duplicates the gate's own
    accept/reject/record decision.

    Reuses admin_review's own `_normalize_generic`/`_is_gap_fill`/
    `_values_differ` (imported directly, never re-implemented) so this
    predictor can never diverge from what the gate itself decides. A field
    the predictor marks "needs a run" that the gate's own D-03/gap-fill
    short-circuit ultimately resolves as ACCEPT-no-record simply mints a
    run that ends up recording nothing -- harmless, and the ONLY case this
    predictor actually protects (D-09's byte-identical no-op) never
    reaches that false-positive: on an identical re-import every field's
    incoming value literally equals its existing value, so
    `_values_differ` returns False for every field simultaneously and no
    run is ever minted.

    `has_no_opinion_check` mirrors D-03's scope exactly: True for
    Argument/Case fields (whose gates implement the blank-incoming
    no-opinion pre-check), False for ArgumentParticipant/Person fields
    (whose gates do not -- PD-15's "the reconcile pass does NOT
    re-implement" is about the real write path, not this
    same-outcome-guaranteed predictor).
    """
    if (
        has_no_opinion_check
        and _normalize_generic(incoming_value) is None
        and _normalize_generic(existing_value) is not None
    ):
        return False
    if _is_gap_fill(field, incoming_value, existing_value):
        return False
    return _values_differ(field, incoming_value, existing_value)


def _count_decision(counters: dict, decision) -> None:
    """Increment the four write/record whole-batch counters from
    one gate call's returned `WriteDecision` (or `None` for D-03's
    no-opinion, which increments nothing)."""
    if decision is None:
        return
    if decision in (WriteDecision.ACCEPT, WriteDecision.ACCEPT_AND_RECORD):
        counters["values_accepted"] = counters.get("values_accepted", 0) + 1
    if decision == WriteDecision.REJECT_AND_RECORD:
        counters["values_rejected"] = counters.get("values_rejected", 0) + 1
    if decision in (WriteDecision.ACCEPT_AND_RECORD, WriteDecision.REJECT_AND_RECORD):
        counters["discrepancies_recorded"] = counters.get("discrepancies_recorded", 0) + 1


async def _reconcile_field(
    ctx: _ReconcileContext,
    gate_call,
    *,
    target,
    field: str,
    incoming_value,
    existing_value,
    has_no_opinion_check: bool,
):
    """
    Walk one D-02 compare-set field through its authority gate on
    the ordinary (non-published, non-dry-run) path.

    `gate_call` is a `functools.partial` of one of the four gate
    functions with its target object already bound (e.g.
    `functools.partial(apply_argument_value_change, argument=argument)`)
    -- this function supplies `field`/`incoming_value`/`incoming_source`/
    `incoming_method`/`import_run_id`.

    Every gate issues its write via `execution_options(synchronize_
    session=False)`, so the in-memory ORM attribute is synced via
    `setattr` on any accepted decision -- later readers in this SAME
    pass (Task 2's participant.person_id sourcing, D-11) must see the
    fresh value, not a stale pre-write one.
    """
    run_id = None
    if _needs_reconcile_run(
        field, incoming_value, existing_value, has_no_opinion_check=has_no_opinion_check
    ):
        run_id = await _ensure_reconcile_run(ctx)
    decision = await gate_call(
        ctx.session,
        field=field,
        incoming_value=incoming_value,
        incoming_source=ImportSource.CORPUS.value,
        incoming_method=ImportMethod.DIRECT.value,
        import_run_id=run_id,
    )
    if decision in (WriteDecision.ACCEPT, WriteDecision.ACCEPT_AND_RECORD):
        setattr(target, field, incoming_value)
    _count_decision(ctx.counters, decision)
    return decision


async def _record_published_diff(
    ctx: _ReconcileContext,
    *,
    target_type: str,
    target_id: int,
    field: str,
    incoming_value,
    existing_value,
    existing_source: str | None,
    existing_method: str | None,
) -> None:
    """
    The PUBLISHED-argument record-only branch. Never calls a gate
    and never writes a column -- compares `incoming_value` against
    `existing_value` directly and records one open `value_discrepancy`
    row when (and only when) they genuinely disagree.

    This is the ONE place besides the dry-run branch that reads the
    normalization/gap-fill contract without going through a gate --
    unavoidable, since D-08 forbids calling a gate AT ALL here (a gate
    call is inseparable from its own write). Mirrors the same no-opinion
    (blank incoming vs. populated existing) and gap-fill (blank existing
    vs. populated incoming) skip conditions the real gates apply, so a
    corpus with genuinely no data for this field, or a genuine blank-slate
    fill, is never misreported as a "disagreement" on a published
    argument's discrepancy log.
    """
    if _normalize_generic(incoming_value) is None and _normalize_generic(existing_value) is not None:
        return
    if _is_gap_fill(field, incoming_value, existing_value):
        return
    if not _values_differ(field, incoming_value, existing_value):
        return
    run_id = await _ensure_reconcile_run(ctx)
    await record_value_discrepancy(
        ctx.session,
        target_type=target_type,
        target_id=target_id,
        field=field,
        import_run_id=run_id,
        incoming_value=incoming_value,
        existing_value=existing_value,
        incoming_source=ImportSource.CORPUS.value,
        incoming_method=ImportMethod.DIRECT.value,
        existing_source=existing_source,
        existing_method=existing_method,
    )
    ctx.counters["discrepancies_recorded"] = ctx.counters.get("discrepancies_recorded", 0) + 1


async def _pair_participants_by_speaker_id(
    session, argument_id: int, incoming_speaker_ids: set[str]
) -> dict[str, ArgumentParticipant]:
    """
    Build a `oyez_speaker_id -> ArgumentParticipant` map for this
    argument's STORED rows, read-only, ordered by `ArgumentParticipant.id`
    ASC. Pairing is on `oyez_speaker_id` ONLY -- never
    `raw_speaker_label`, never a `Person` lookup.

    A stored row is included ONLY when its `oyez_speaker_id` is non-NULL
    AND present in `incoming_speaker_ids` -- i.e. genuinely paired to a
    speaker the corpus still mentions this pass. A stored row with a NULL
    `oyez_speaker_id` (operator-created or otherwise undervivable) is
    unpairable and simply never appears in the returned map -- the caller
    never iterates it, so it is left entirely alone (D-05, Claude's
    Discretion note). A stored row whose `oyez_speaker_id` the corpus no
    longer mentions is likewise absent from the map and left untouched
    (D-05).
    """
    result = await session.execute(
        select(ArgumentParticipant)
        .where(ArgumentParticipant.argument_id == argument_id)
        .order_by(ArgumentParticipant.id)
    )
    rows = result.scalars().all()
    return {
        row.oyez_speaker_id: row
        for row in rows
        if row.oyez_speaker_id is not None and row.oyez_speaker_id in incoming_speaker_ids
    }


def _row_should_restamp(decisions: Sequence[WriteDecision | None]) -> bool:
    """
    Decide whether one row's whole-row provenance may be demoted to
    corpus/direct after its full compare-set walk.

    `source`/`method` are ROW-level columns, but `decide_write` runs
    PER-FIELD. Firing the restamp from a single field's ACCEPT therefore
    demoted the entire row -- including sibling fields whose stored value
    had just been REJECT_AND_RECORDed for outranking the incoming one. On
    `Argument` and `Case` that silently destroyed operator authority,
    because neither table has a `review_state` column and `source` is the
    only carrier of the ladder's `operator` rung (see
    `api.services.admin_arguments._stamp_operator_provenance`). Found by
    the D-09 live walkthrough, 2026-08-26: an operator-edited `case_name`
    was rejected while its sibling `docket_number` agreed, and the
    agreeing field's ACCEPT reverted the row to corpus/direct.

    The rule, fail-closed in the same spirit as `authority_rank`'s
    rule 6: a row that still holds at least one field whose stored value
    OUTRANKED this pass's incoming value is not a wholly corpus-sourced
    row, so it is never demoted. The row keeps the higher authority; a
    later disagreeing corpus write is then still rejected and recorded,
    leaving an audit trail, rather than being silently accepted.

    Returns True only when the walk both (a) accepted at least one write
    and (b) rejected nothing. A gate returns `None` for a field it has no
    opinion on (incoming blank against a populated stored value), so the
    sequence is mixed; a `None` neither licenses nor blocks a restamp, and
    an all-`None` walk wrote nothing and must not restamp.
    """
    if any(d == WriteDecision.REJECT_AND_RECORD for d in decisions):
        return False
    return any(
        d in (WriteDecision.ACCEPT, WriteDecision.ACCEPT_AND_RECORD) for d in decisions
    )


async def _restamp_corpus_provenance(session, model, row_id: int) -> None:
    """
    After an accepted overwrite on this reconcile pass,
    restamp `source`/`method` to corpus/direct -- even a row that already
    carried a `source` value. The provenance columns describe where the
    value came FROM, not where it originally came from. `review_state` is
    deliberately NOT touched here (
    50-CONTEXT.md). `Person` has no `source`/`method` columns, so this is
    only ever called for `Argument`, `Case`, and `ArgumentParticipant`.

    Unconditional WITHIN a row -- it does not consult the row's existing
    `source`, so it is still distinct from the backfill-only precedent at
    `api/services/admin_jobs.py`'s `resolve_participant_review` (guarded
    on `participant.source is None`), which must NOT be reused verbatim
    here. What D-07's "unconditional" never licensed is demoting a row on
    behalf of a field that was rejected: every caller must gate this on
    `_row_should_restamp` over that row's COMPLETE compare-set walk, and
    call it once per row rather than once per accepted field.
    """
    await session.execute(
        update(model)
        .where(model.id == row_id)
        .values(source=ImportSource.CORPUS, method=ImportMethod.DIRECT)
        .execution_options(synchronize_session=False)
    )


async def _fetch_lead_case(session, argument_id: int) -> Case | None:
    """Read-only: this argument's LEAD linked `Case` row (D-19's
    lead-docket-only convention), or `None` if somehow unlinked."""
    result = await session.execute(
        select(Case)
        .join(CaseArgument, CaseArgument.case_id == Case.id)
        .where(CaseArgument.argument_id == argument_id, CaseArgument.is_lead == True)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def _reconcile_conversation(
    session,
    argument: Argument,
    conversation_id: str,
    conversation: dict,
    case_fields: dict,
    turns: list[dict],
    speakers_index: dict,
    counters: dict,
    dry_run: bool = False,
) -> None:
    """
    Phase 50 plan 50-05 (D-01/D-02/D-04/D-06/D-07/D-08/D-09/D-10/D-11/
    D-13, OQ-3, PD-14/PD-15/PD-16): the real compare-and-record pass a
    repeat corpus import over an already-imported conversation takes,
    replacing plan 50-01's placeholder branch.

    Walks the WHOLE D-02 compare set in PD-14's fixed order --
    `Argument.argued_date`/`question_number`/`source_docket`, lead
    `Case.case_name`/`docket_number`, each paired participant's
    `person_id`/`side`/`descriptor`, then each paired participant's
    `Person` name-parts (via `_resolve_person`, visiting each Person at
    most once) -- on EVERY reconcile pass, including a byte-identical
    re-import (every field then resolves ACCEPT-no-record or D-03's
    no-opinion, and `_needs_reconcile_run`'s predictor never mints a run,
    so D-09's zero-rows guarantee holds).

    `question_number` has no corpus source at all -- ConvoKit carries no
    concept of it, so its incoming value is always `None`, which the
    Argument gate's own D-03 pre-check resolves as permanent no-opinion.
    It is still walked (present in PD-14's order) for documentation/
    symmetry, at zero cost.

    When `argument.status == PUBLISHED`, the ENTIRE pass runs in
    record-only mode via `_record_published_diff` for the Argument/Case
    legs -- no gate is called, no column is written, no participant/
    person walk happens (nothing there could ever accept-and-record once
    `_apply_extracted_name_provenance`'s own gap-fill-only design is
    accounted for -- see that function's docstring), and no utterance
    replacement happens either (guarded further down).
    `published_writes_skipped` increments exactly once per pass,
    unconditionally.

    Utterance replacement is delegated to
    `_replace_utterance_set` when the incoming content digest differs
    from the latest stored `step="parse"` run's -- see that
    function and the digest-comparison block at the end of this one.
    """
    ctx = _ReconcileContext(
        session=session,
        argument=argument,
        conversation_id=conversation_id,
        speakers_index=speakers_index,
        counters=counters,
        dry_run=dry_run,
    )
    is_published = argument.status == ArgumentStatusEnum.PUBLISHED

    if dry_run:
        await _predict_reconcile(ctx, conversation, case_fields, turns, is_published=is_published)
        return

    if is_published:
        counters["published_writes_skipped"] = counters.get("published_writes_skipped", 0) + 1

    # ---- PD-14 items 1-3: Argument fields ----
    incoming_argued_date = _parse_argued_date(case_fields, conversation_id)
    argument_field_plan = (
        ("argued_date", incoming_argued_date, argument.argued_date),
        # No corpus source exists for question_number -- always no-opinion
        # (D-03); walked for PD-14 order/documentation only.
        ("question_number", None, argument.question_number),
        ("source_docket", case_fields.get("docket_no"), argument.source_docket),
    )
    # Collect this row's per-field decisions across the WHOLE
    # compare-set walk and restamp once at the end, never per field.
    argument_decisions: list[WriteDecision | None] = []
    for arg_field, incoming_value, existing_value in argument_field_plan:
        if is_published:
            existing_source_value = argument.source.value if argument.source else None
            existing_method_value = argument.method.value if argument.method else None
            await _record_published_diff(
                ctx,
                target_type="argument",
                target_id=argument.id,
                field=arg_field,
                incoming_value=incoming_value,
                existing_value=existing_value,
                existing_source=existing_source_value,
                existing_method=existing_method_value,
            )
        else:
            decision = await _reconcile_field(
                ctx,
                functools.partial(apply_argument_value_change, argument=argument),
                target=argument,
                field=arg_field,
                incoming_value=incoming_value,
                existing_value=existing_value,
                has_no_opinion_check=True,
            )
            argument_decisions.append(decision)
    if _row_should_restamp(argument_decisions):
        await _restamp_corpus_provenance(session, Argument, argument.id)

    # ---- PD-14 items 4-5: lead Case fields ----
    lead_case = await _fetch_lead_case(session, argument.id)
    if lead_case is not None:
        case_field_plan = (
            ("case_name", _case_name_from_fields(case_fields), lead_case.case_name),
            ("docket_number", case_fields.get("docket_no"), lead_case.docket_number),
        )
        # One restamp decision per row, over the whole walk. This
        # is the exact pair the live walkthrough caught -- an operator's
        # `case_name` rejected while `docket_number` agreed.
        case_decisions: list[WriteDecision | None] = []
        for c_field, incoming_value, existing_value in case_field_plan:
            if is_published:
                existing_source_value = lead_case.source.value if lead_case.source else None
                existing_method_value = lead_case.method.value if lead_case.method else None
                await _record_published_diff(
                    ctx,
                    target_type="case",
                    target_id=lead_case.id,
                    field=c_field,
                    incoming_value=incoming_value,
                    existing_value=existing_value,
                    existing_source=existing_source_value,
                    existing_method=existing_method_value,
                )
            else:
                decision = await _reconcile_field(
                    ctx,
                    functools.partial(apply_case_value_change, case=lead_case),
                    target=lead_case,
                    field=c_field,
                    incoming_value=incoming_value,
                    existing_value=existing_value,
                    has_no_opinion_check=True,
                )
                case_decisions.append(decision)
        if _row_should_restamp(case_decisions):
            await _restamp_corpus_provenance(session, Case, lead_case.id)

    # No Person/ArgumentParticipant resolution happens for the digest
    # computation below -- an empty resolved_participants seed means every
    # row's raw_speaker_label is derived purely from speakers_index (a
    # pure function of speaker_id), identical whether or not the
    # participant walk below has already run.
    incoming_rows = _incoming_utterance_rows(
        turns=turns,
        speakers_index=speakers_index,
        resolved_participants={},
        counters=counters,
    )
    advocates = conversation.get("advocates") or {}
    incoming_speaker_ids = {
        row["speaker_id"] for row in incoming_rows if row.get("speaker_id")
    }
    incoming_speaker_ids |= set(advocates.keys())

    # ---- PD-14 items 6-7: paired participants + their Person name-parts.
    #
    # D-08 on a PUBLISHED argument: compare and RECORD, never write —
    # the same contract the Argument/Case legs above already honour via
    # `_record_published_diff`.
    #
    # This block used to be skipped ENTIRELY when published, justified by
    # the claim that nothing here could ever accept-and-record. That claim
    # holds only for the four `Person` name-part writes
    # (`_apply_extracted_name_provenance` really is gap-fill-or-no-op). It
    # was false for `ArgumentParticipant.person_id`/`.side`/`.descriptor`,
    # which go through `apply_participant_value_change` — a full authority
    # gate that returns ACCEPT_AND_RECORD or REJECT_AND_RECORD whenever
    # the values genuinely differ. So a corpus re-import that re-resolved
    # a speaker to a different Person, or disagreed on a side, was
    # silently dropped on a live published argument: never written
    # (correct) but never surfaced to the operator either (50-REVIEW.md
    # CR-01).
    #
    # Still skipped when published, deliberately: the Person name-part
    # writes (gap-fill only — genuinely nothing to record) and the
    # new-participant-creation leg below (creating a row IS a write).
    if is_published:
        paired = await _pair_participants_by_speaker_id(
            session, argument.id, incoming_speaker_ids
        )
        for speaker_id, participant in paired.items():
            speaker_meta = speakers_index.get(speaker_id) or {}
            is_justice = _is_justice_type(speaker_meta)
            if is_justice is None:
                is_justice = False
            full_name = (
                speaker_meta.get("name") or speaker_meta.get("full_name") or speaker_id
            )
            existing_source_value = participant.source.value if participant.source else None
            existing_method_value = participant.method.value if participant.method else None

            incoming_person = await _lookup_person_readonly(session, speaker_id, full_name)
            if incoming_person is not None:
                await _record_published_diff(
                    ctx,
                    target_type="argument_participant",
                    target_id=participant.id,
                    field="person_id",
                    incoming_value=incoming_person.id,
                    existing_value=participant.person_id,
                    existing_source=existing_source_value,
                    existing_method=existing_method_value,
                )

            side_meta = advocates.get(speaker_id)
            side_code = side_meta.get("side") if isinstance(side_meta, dict) else side_meta
            incoming_side = (
                SideEnum.BENCH if is_justice else _ADVOCATE_SIDE_MAP.get(side_code, SideEnum.UNKNOWN)
            )
            await _record_published_diff(
                ctx,
                target_type="argument_participant",
                target_id=participant.id,
                field="side",
                incoming_value=incoming_side,
                existing_value=participant.side,
                existing_source=existing_source_value,
                existing_method=existing_method_value,
            )

            # descriptor: corpus never supplies one, so this is always a
            # no-opinion skip inside _record_published_diff. Walked anyway
            # to keep PD-14's field order identical on both branches.
            await _record_published_diff(
                ctx,
                target_type="argument_participant",
                target_id=participant.id,
                field="descriptor",
                incoming_value=None,
                existing_value=participant.descriptor,
                existing_source=existing_source_value,
                existing_method=existing_method_value,
            )

    if not is_published:
        paired = await _pair_participants_by_speaker_id(
            session, argument.id, incoming_speaker_ids
        )
        visited_person_ids: set[int] = set()
        for speaker_id, participant in paired.items():
            speaker_meta = speakers_index.get(speaker_id) or {}
            is_justice = _is_justice_type(speaker_meta)
            if is_justice is None:
                is_justice = False
            full_name = (
                speaker_meta.get("name") or speaker_meta.get("full_name") or speaker_id
            )

            # ---- Person leg: resolves (and gap-fills, D-21) the Person
            # this speaker currently maps to -- the SAME oyez_speaker_id
            # -first/full_name-fallback resolution the first-import path
            # uses -- so an operator's participant REASSIGNMENT (this
            # participant's stored person_id pointing at a DIFFERENT
            # Person than the one this speaker id resolves to) is exactly
            # what the person_id comparison below detects (D-04's stated
            # highest-value case).
            person = await _resolve_person(
                session, speaker_id, full_name, is_justice, counters
            )
            visited_person_ids.add(person.id)

            # Accumulate across this participant's three compare-set
            # fields; the single restamp decision comes after the walk.
            participant_decisions: list[WriteDecision | None] = []

            decision = await _reconcile_field(
                ctx,
                functools.partial(apply_participant_value_change, participant=participant),
                target=participant,
                field="person_id",
                incoming_value=person.id,
                existing_value=participant.person_id,
                has_no_opinion_check=False,
            )
            participant_decisions.append(decision)

            side_meta = advocates.get(speaker_id)
            side_code = side_meta.get("side") if isinstance(side_meta, dict) else side_meta
            incoming_side = (
                SideEnum.BENCH if is_justice else _ADVOCATE_SIDE_MAP.get(side_code, SideEnum.UNKNOWN)
            )
            decision = await _reconcile_field(
                ctx,
                functools.partial(apply_participant_value_change, participant=participant),
                target=participant,
                field="side",
                incoming_value=incoming_side,
                existing_value=participant.side,
                has_no_opinion_check=False,
            )
            participant_decisions.append(decision)

            # descriptor: corpus never supplies one (PDF-cover-extractor-only
            # field) -- incoming is always None; walked for PD-14 order.
            decision = await _reconcile_field(
                ctx,
                functools.partial(apply_participant_value_change, participant=participant),
                target=participant,
                field="descriptor",
                incoming_value=None,
                existing_value=participant.descriptor,
                has_no_opinion_check=False,
            )
            participant_decisions.append(decision)

            if _row_should_restamp(participant_decisions):
                await _restamp_corpus_provenance(
                    session, ArgumentParticipant, participant.id
                )

        # ---- A speaker present in the corpus with no paired stored row is
        # a NEW participant -- route through the existing first-import
        # machinery, which already stamps source/method/oyez_speaker_id.
        for speaker_id in incoming_speaker_ids:
            if speaker_id in paired:
                continue
            side_meta = advocates.get(speaker_id)
            side_code = side_meta.get("side") if isinstance(side_meta, dict) else side_meta
            await _resolve_and_link_participant(
                session=session,
                argument_id=argument.id,
                speaker_id=speaker_id,
                speakers_index=speakers_index,
                side_code=side_code,
                counters=counters,
                argued_date=argument.argued_date,
            )

    # ---- D-10/D-11/D-13: utterance replacement, gated on the content
    # digest and D-08's published freeze.
    latest_parse_digest = (
        await session.execute(
            select(ImportRun.content_digest)
            .where(ImportRun.argument_id == argument.id, ImportRun.step == "parse")
            .order_by(ImportRun.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    incoming_digest = compute_utterance_digest(incoming_rows)

    wrote_anything = ctx.reconcile_run_id is not None

    if latest_parse_digest is not None and latest_parse_digest == incoming_digest:
        counters["arguments_unchanged"] = counters.get("arguments_unchanged", 0) + 1
    elif not incoming_rows and latest_parse_digest is not None:
        # Blank-page hazard defense: an empty incoming set against a
        # non-empty stored one is far more likely a load/filter defect
        # than a genuine claim the argument now has zero utterances --
        # refuse outright rather than silently blanking the public page.
        counters["conversations_errored"] = counters.get("conversations_errored", 0) + 1
        print(
            f"WARNING: conversation {conversation_id!r} (argument_id="
            f"{argument.id}) incoming utterance set is EMPTY but "
            f"{len(incoming_rows)} stored rows exist under a prior run -- "
            "refusing to replace (D-10 blank-page hazard); left untouched, "
            "counted as an error."
        )
    elif is_published:
        counters["arguments_reconciled"] = counters.get("arguments_reconciled", 0) + 1
        print(
            f"WARNING: conversation {conversation_id!r} (argument_id="
            f"{argument.id}) content digest differs but the argument is "
            "PUBLISHED -- utterance set left untouched (D-08); unpublish "
            "to allow a reconcile-driven replacement."
        )
    else:
        counters["arguments_reconciled"] = counters.get("arguments_reconciled", 0) + 1
        await _replace_utterance_set(ctx, incoming_rows)
        wrote_anything = True

    if not is_published and wrote_anything:
        await recompute_argument_tier(session, argument.id)


async def _replace_utterance_set(ctx: _ReconcileContext, incoming_rows: list[dict]) -> None:
    """
    Whole-set utterance replacement under a NEW
    `step="parse"`/`COMPLETED` `ImportRun`, minted and populated in the
    SAME transaction as the reconcile pass's caller (`run_import_convokit`
    's per-conversation `async with get_session()` block, D-30) -- never
    an intervening commit between minting the run and writing its rows.

    THE HARDEST CONSTRAINT IN THIS PHASE: `api/services/arguments.py`'s
    `get_argument_with_utterances` selects the newest `step="parse"`/
    `COMPLETED` run via `MAX(ImportRun.id)`, deliberately not a max over
    utterances -- a run flushed without its rows makes that argument's
    public chat page render EMPTY. Steps 1 and 2 below MUST occur with no
    intervening commit; the caller's own `<precondition>`-equivalent
    guarantee is the outer per-conversation transaction, and any failure
    mid-write rolls the whole thing back (D-30's own per-argument
    atomicity, unchanged).

    Deletes nothing -- superseded rows and their run are retained;
    `pipeline prune-runs` is the only thing that ever removes
    them.

    Person ids on the new rows come from the POST-reconcile
    `ArgumentParticipant` state, never the raw corpus speaker
    mapping: `_import_utterances` is called with a FRESH
    `resolved_participants={}`, so its own `_resolve_and_link_participant`
    call performs a fresh `(argument_id, raw_speaker_label)` lookup for
    every speaker -- for a speaker this pass already paired and
    reconciled above, that lookup returns the SAME row this transaction
    already restamped/reassigned, so an operator's participant
    reassignment survives a re-import for free without this function
    needing to know anything about the D-02 walk that ran before it.
    """
    incoming_digest = compute_utterance_digest(incoming_rows)
    run = ImportRun(
        argument_id=ctx.argument.id,
        step="parse",
        status=ImportRunStatus.COMPLETED,
        source=ImportSource.CORPUS,
        method=ImportMethod.DIRECT,
        external_id=ctx.conversation_id,
        content_digest=incoming_digest,
    )
    ctx.session.add(run)
    await ctx.session.flush()

    await _import_utterances(
        session=ctx.session,
        argument_id=ctx.argument.id,
        import_run_id=run.id,
        rows=incoming_rows,
        speakers_index=ctx.speakers_index,
        resolved_participants={},
        counters=ctx.counters,
        argued_date=ctx.argument.argued_date,
    )
    ctx.counters["utterance_sets_replaced"] = (
        ctx.counters.get("utterance_sets_replaced", 0) + 1
    )


async def _predict_reconcile(
    ctx: _ReconcileContext,
    conversation: dict,
    case_fields: dict,
    turns: list[dict],
    *,
    is_published: bool,
) -> None:
    """
    Phase 50 plan 50-05 Task 3: the `--dry-run` prediction path.
    Computes every decision `_reconcile_conversation`'s ordinary path
    would reach -- the SAME extracted incoming values, the SAME
    `decide_write` ladder call -- but touches ZERO rows: no gate call
    (which is inseparable from its own write), no `_ensure_reconcile_run`,
    no `record_value_discrepancy`, no participant/person resolution or
    creation, no utterance replacement.

    This is the ONE place in this module that calls
    `api.domain.authority.decide_write` directly instead of going through
    a gate -- deliberately, and ONLY because it writes nothing: calling
    the real gate and rolling back would still consume sequence values
    and risk a partial flush, which is exactly what `--dry-run` exists to
    avoid. This path MUST NEVER be reachable when `ctx.dry_run` is False
    -- `_reconcile_conversation` branches to this function before doing
    ANY other work, so the ordinary path never touches `decide_write`.

    Scoped to Argument/Case fields only (participant/person prediction is
    a documented simplification -- see 50-05-SUMMARY.md's Deviations
    section) plus the utterance-replacement prediction via the same
    digest comparison the real path uses.
    """
    counters = ctx.counters
    argument = ctx.argument

    if is_published:
        counters["published_writes_skipped"] = (
            counters.get("published_writes_skipped", 0) + 1
        )

    def _predict(field, incoming_value, existing_value, existing_source, existing_method):
        if (
            _normalize_generic(incoming_value) is None
            and _normalize_generic(existing_value) is not None
        ):
            return  # D-03 no-opinion -- nothing to predict
        if _is_gap_fill(field, incoming_value, existing_value):
            counters["values_accepted"] = counters.get("values_accepted", 0) + 1
            return
        differ = _values_differ(field, incoming_value, existing_value)
        decision = decide_write(
            incoming_source=ImportSource.CORPUS.value,
            incoming_method=ImportMethod.DIRECT.value,
            incoming_review_state="",
            existing_source=existing_source or "",
            existing_method=existing_method or "",
            existing_review_state="",
            values_differ=differ,
        )
        _count_decision(counters, decision)

    incoming_argued_date = _parse_argued_date(case_fields, ctx.conversation_id)
    _predict(
        "argued_date",
        incoming_argued_date,
        argument.argued_date,
        argument.source.value if argument.source else None,
        argument.method.value if argument.method else None,
    )
    _predict(
        "question_number",
        None,
        argument.question_number,
        argument.source.value if argument.source else None,
        argument.method.value if argument.method else None,
    )
    _predict(
        "source_docket",
        case_fields.get("docket_no"),
        argument.source_docket,
        argument.source.value if argument.source else None,
        argument.method.value if argument.method else None,
    )

    lead_case = await _fetch_lead_case(ctx.session, argument.id)
    if lead_case is not None:
        _predict(
            "case_name",
            _case_name_from_fields(case_fields),
            lead_case.case_name,
            lead_case.source.value if lead_case.source else None,
            lead_case.method.value if lead_case.method else None,
        )
        _predict(
            "docket_number",
            case_fields.get("docket_no"),
            lead_case.docket_number,
            lead_case.source.value if lead_case.source else None,
            lead_case.method.value if lead_case.method else None,
        )

    latest_parse_digest = (
        await ctx.session.execute(
            select(ImportRun.content_digest)
            .where(ImportRun.argument_id == argument.id, ImportRun.step == "parse")
            .order_by(ImportRun.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    incoming_rows = _incoming_utterance_rows(
        turns=turns,
        speakers_index=ctx.speakers_index,
        resolved_participants={},
        counters=counters,
    )
    incoming_digest = compute_utterance_digest(incoming_rows)

    if latest_parse_digest is not None and latest_parse_digest == incoming_digest:
        counters["arguments_unchanged"] = counters.get("arguments_unchanged", 0) + 1
    elif not incoming_rows and latest_parse_digest is not None:
        counters["conversations_errored"] = counters.get("conversations_errored", 0) + 1
    elif is_published:
        counters["arguments_reconciled"] = counters.get("arguments_reconciled", 0) + 1
        counters["published_writes_skipped"] = (
            counters.get("published_writes_skipped", 0) + 1
        )
    else:
        counters["arguments_reconciled"] = counters.get("arguments_reconciled", 0) + 1
        counters["utterance_sets_replaced"] = (
            counters.get("utterance_sets_replaced", 0) + 1
        )


# ---------------------------------------------------------------------------
# Task 3: speaker resolution -- Person + ArgumentParticipant (side)
# ---------------------------------------------------------------------------


def _is_justice_type(speaker_meta: dict) -> bool | None:
    """
    Read speakers.json's speaker `type` field as the AUTHORITATIVE bench vs.
    advocate signal (RESEARCH.md Open Question 3) -- never inferred from a
    speaker id's naming convention (e.g. a "j__" prefix). Returns None when
    the type is missing/unrecognized so the caller can flag it
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


async def _apply_extracted_name_provenance(session, person: Person, full_name: str) -> None:
    """
    Persist a conservative interpreted-parts + provenance extraction for
    `person` from its `full_name` (D-14-D-18), reusing the same pure
    `api.domain.person_names.split_legacy_full_name` splitter and
    envelope shape (`{source, raw, confidence, reason, auto_applied}`)
    alembic/versions/0022_person_name_authority.py's legacy backfill
    already established.

    Every call refreshes `provenance_metadata` unconditionally (D-17 --
    "if extraction/reprocessing occurs later, replace the extracted
    reference with the latest result") -- this is metadata, not a D-02
    gated column, so it is a plain attribute write, never routed through
    a gate. Structured parts are only ever written when the row currently
    carries NO structured part at all (mirrors migration 0022's own guard
    exactly -- a row that already has any operator/import-authored part is
    left completely untouched, never partially clobbered) and only for a
    High-confidence, round-trip-exact split (`auto_apply=True`, D-11) -- an
    ambiguous/uncertain interpretation (Low/Medium) is still recorded in
    the provenance envelope so the operator can see what the extractor
    thought it saw, but is never silently written into the
    authoritative saved columns, and the row's `review_state` is set to
    NEEDS_REVIEW for the People directory's Name review filter.

    Note the asymmetry deliberately (Phase 49 D-08, D-11, D-24): the
    confident branch below sets UNREVIEWED, never a human-only operator
    review state -- only a human action ever produces one; an importer
    must never mint one.

    Phase 50 (Task 1, D-21/D-22): the four structured-part writes are an
    ungated writer D-22's enumeration did not name -- each now routes
    through `apply_person_value_change` (`incoming_source=corpus`,
    `incoming_method=direct`; this is the corpus importer, not the
    justice seeder, so `seed` is the wrong vocabulary even though
    `authority_rank` ranks the two identically). Every write this
    function performs only ever reaches the gate's own gap-fill
    short-circuit (existing part is always blank here, per the
    `has_any_part` guard above it) or a no-op ACCEPT (both sides blank) --
    it can never reach ACCEPT_AND_RECORD/REJECT_AND_RECORD, so
    `import_run_id=None` is always safe: PD-13's gap-fill rule is what
    keeps this from minting four discrepancy rows per new Person on every
    reseed. The gate issues its own `execution_options(synchronize_
    session=False)` UPDATE, so the in-memory `person` attribute is synced
    via `setattr` on any accepted decision -- callers in this same
    transaction (including this function's own caller) must see the
    fresh value, not a stale pre-write one.
    """
    # A brand-new Person object has review_state=None in-memory until
    # flush (the model's `default=ReviewState.UNREVIEWED` is an INSERT-time
    # default, not applied at construction) -- apply_person_value_change
    # below reads `person.review_state.value` unconditionally, so a
    # not-yet-flushed row must be seeded with the same value the column's
    # own default would apply, before any gate call.
    if person.review_state is None:
        person.review_state = ReviewState.UNREVIEWED

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
        # Never overwrite a row that already carries any saved part --
        # whether authored by an operator or a prior confident extraction.
        return

    if split.auto_apply:
        for name_field, incoming_value in (
            ("first_name", split.first_name),
            ("middle_name", split.middle_name),
            ("last_name", split.last_name),
            ("name_suffix", split.name_suffix),
        ):
            decision = await apply_person_value_change(
                session,
                person=person,
                field=name_field,
                incoming_value=incoming_value,
                incoming_source=ImportSource.CORPUS.value,
                incoming_method=ImportMethod.DIRECT.value,
                import_run_id=None,
            )
            if decision in (WriteDecision.ACCEPT, WriteDecision.ACCEPT_AND_RECORD):
                setattr(person, name_field, incoming_value)
        person.review_state = ReviewState.UNREVIEWED
    else:
        person.review_state = ReviewState.NEEDS_REVIEW


async def _resolve_person(
    session, speaker_id: str, full_name: str, is_justice: bool, counters: dict
) -> Person:
    """
    Resolve or create a Person for `speaker_id`
    Person.oyez_speaker_id checked FIRST, then Person.full_name (D-13, same
    exact-match dedup as the justice importer). When a full_name match is
    found with no oyez_speaker_id yet, backfill it so the next run
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
        await _apply_extracted_name_provenance(session, person, person.full_name)
        counters["people_matched"] = counters.get("people_matched", 0) + 1
        return person

    result = await session.execute(select(Person).where(Person.full_name == full_name))
    person = result.scalar_one_or_none()
    if person is not None:
        if person.oyez_speaker_id is None:
            person.oyez_speaker_id = speaker_id  # D-11 backfill
        await _apply_extracted_name_provenance(session, person, person.full_name)
        counters["people_matched"] = counters.get("people_matched", 0) + 1
        return person

    person = Person(
        full_name=full_name,
        oyez_speaker_id=speaker_id,
        is_justice=is_justice,
    )
    await _apply_extracted_name_provenance(session, person, full_name)
    session.add(person)
    await session.flush()
    counters["people_created"] = counters.get("people_created", 0) + 1
    return person


async def _lookup_person_readonly(session, speaker_id: str, full_name: str) -> Person | None:
    """
    Read-only twin of `_resolve_person`'s identity lookup, for the
    PUBLISHED record-only branch (50-REVIEW.md CR-01).

    Same D-11 key order — `Person.oyez_speaker_id` first, then
    `Person.full_name` — but it never creates a `Person`, never backfills
    `oyez_speaker_id`, never applies name provenance, and never touches a
    counter. Every one of those is a write, and D-08 forbids writes on a
    published argument; `_resolve_person` does all four, which is why it
    cannot be reused here.

    Returns `None` when the corpus names somebody this database has never
    seen. There is then no comparable stored `person_id` — recording a
    "disagreement" between a name and an id would pollute the discrepancy
    log with something no operator could act on, and materialising an id
    to compare against is exactly the write D-08 forbids. The case CR-01
    exists to catch (and D-04 calls the highest-value one) is the corpus
    re-resolving a speaker to a DIFFERENT Person we already know about,
    which this does surface.
    """
    result = await session.execute(
        select(Person).where(Person.oyez_speaker_id == speaker_id)
    )
    person = result.scalar_one_or_none()
    if person is not None:
        return person
    result = await session.execute(select(Person).where(Person.full_name == full_name))
    return result.scalar_one_or_none()


async def _check_bench_tenure_mismatch(session, person_id: int, argued_date) -> bool:
    """
    Phase 42 Task 3 (item 2, `bench-warn-only`): True when `person_id` has
    NO `CourtTenure` row covering `argued_date` -- inclusive start
    boundary (`start_date <= argued_date`), open-ended `end_date` treated
    as still active (`end_date IS NULL OR end_date >= argued_date`).
    Read-only: issues a single `select(CourtTenure)`, never creates,
    updates, or deletes a `CourtTenure` row and never touches
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
    ArgumentParticipant row for `argument_id`.

    Returns None -- creating no Person/ArgumentParticipant row at all --
    when speakers.json's `type` is ConvoKit's own "no identifiable speaker"
    sentinel ("U", e.g. "<INAUDIBLE>"/"<UNKNOWN>"). Callers must treat a
    None return as "this turn has no attributable speaker" (mirrors how a
    stage-direction row already has no participant), not as an error.

    `side_code` is the raw conversations.json 0/1/2/3 advocate side code;
    it is ignored (side is always BENCH) when the resolved speaker's
    speakers.json `type` classifies as a justice. No automated QA gate on
    identity matching -- ambiguous/missing types are imported and
    counted in counters["speakers_flagged"] for the batch summary, never
    silently skipped.

    `argued_date` (Phase 42 Task 3, Review Gate item 2, option
    `bench-warn-only`, operator-approved 2026-07-30): when the resolved
    speaker is typed a Justice AND `argued_date` is not None, cross-checks
    `CourtTenure` coverage of that date via `_check_bench_tenure_mismatch`.
    A mismatch increments `counters["bench_tenure_mismatch"]` and prints a
    warning naming the speaker id, `argued_date`, and the earliest
    `CourtTenure.start_date` on record for that person -- `side` is left
    UNCHANGED (still BENCH)
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
        # freshly-resolved corpus participant to UNCERTAIN.
        source=ImportSource.CORPUS,
        method=ImportMethod.DIRECT,
        # The explicit re-import pairing key -- the
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
#
# ---------------------------------------------------------------------------


def _split_turn_into_rows(text: str) -> list[tuple[str, bool]]:
    """
    Split one ConvoKit turn's `text` on its `\\n`-delimited segment
    boundaries and classify each segment via
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
    written.

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
                    section_hint=None,  # Stage directions never
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

        # Derive section_hint. Only a PETITIONER/RESPONDENT/AMICUS
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
                text=text,  # Verbatim, \n preserved
                is_stage_direction=False,
                side=resolved_side,
                person_id=participant.person_id if participant else None,
                section_hint=section_hint,
            )
        )
        counters["utterances_created"] = counters.get("utterances_created", 0) + 1

    await session.flush()


# ---------------------------------------------------------------------------
# 29-05 Task 2: per-batch/rollup summary report
# ---------------------------------------------------------------------------

# Every counter key referenced by the summary print, in report order. Using
# .get(key, 0) throughout means a missing key never raises -- new counters
# introduced here don't need every call site retrofitted.
_SUMMARY_COUNTER_KEYS: tuple[str, ...] = (
    "arguments_created",
    # "skipped_existing" is RETIRED, not repurposed
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
    # side is never reassigned for this counter.
    "bench_tenure_mismatch",
    # Phase 50 plan 50-05: the reconcile pass's own whole-batch
    # totals -- values accepted/rejected by the authority ladder across
    # every D-02 compare-set field, discrepancies recorded (the union of
    # every ACCEPT_AND_RECORD/REJECT_AND_RECORD outcome plus every
    # PUBLISHED-argument record-only disagreement), utterance sets fully
    # replaced under a new step="parse" run, and PUBLISHED-argument
    # passes that ran in record-only mode. No per-speaker or
    # per-person breakdown of any of these (project apolitical constraint,
    # D-29's own no-report-file decision).
    "values_accepted",
    "values_rejected",
    "discrepancies_recorded",
    "utterance_sets_replaced",
    "published_writes_skipped",
)


def _new_counters() -> dict:
    """Fresh, fully-initialized per-term counters dict."""
    return {key: 0 for key in _SUMMARY_COUNTER_KEYS} | {"participants_created": 0}


def _accumulate_counters(rollup: dict, term_counters: dict) -> dict:
    """Add one term's counters into the running rollup dict (term-range)."""
    for key in _SUMMARY_COUNTER_KEYS:
        rollup[key] = rollup.get(key, 0) + term_counters.get(key, 0)
    return rollup


def _print_summary(label: str, counters: dict) -> None:
    """
    Print one per-batch summary block: term year, arguments
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
    "<UNKNOWN>" sentinels, never turned into a Person row), bench-tenure
    mismatches (Phase 42 Task 3, item 2: a Justice-typed speaker with no
    CourtTenure row covering argued_date -- flag-only, side never
    reassigned), and (Phase 50 plan 50-05, PD-17) the reconcile pass's own
    whole-batch totals: values accepted/rejected by the authority ladder,
    discrepancies recorded, utterance sets fully replaced under a new
    parse run, and PUBLISHED-argument passes run in record-only mode.

    `label` carries a "DRY RUN" marker when the batch ran under --dry-run
 so an operator can never mistake a dry-run report for a
    completed batch -- see run_import_convokit.
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
        f"{c.get('bench_tenure_mismatch', 0)} bench tenure mismatches, "
        f"{c.get('values_accepted', 0)} values accepted, "
        f"{c.get('values_rejected', 0)} values rejected, "
        f"{c.get('discrepancies_recorded', 0)} discrepancies recorded, "
        f"{c.get('utterance_sets_replaced', 0)} utterance sets replaced, "
        f"{c.get('published_writes_skipped', 0)} published writes skipped."
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
    resolution, and utterance import). Prints a per-term summary; a
    --term-range spanning more than one term also prints a final rollup
    block.

    Phase 50 plan 50-05: `--dry-run` (`getattr(args, "dry_run",
    False)` -- the same backward-compatible-Namespace convention
    `_resolve_scoped_conversation` already uses for `conversation_id`, so
    every pre-existing test `argparse.Namespace()` without a `dry_run`
    attribute still hits the False branch) threads through to every
    `_import_conversation` call this term loop makes. Every printed
    summary block is labeled "DRY RUN" so it can never be mistaken for a
    completed batch.
    """
    dry_run = getattr(args, "dry_run", False)
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
            # Narrow to exactly the one scoped conversation BEFORE
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
                        dry_run=dry_run,
                    )
            except Exception as exc:  # per-row resilience, T-29-05b/Pitfall 5
                counters["conversations_errored"] = (
                    counters.get("conversations_errored", 0) + 1
                )
                print(
                    f"WARNING: conversation {conversation_id!r} raised "
                    f"{exc!r} -- errored, term continues."
                )

        term_label = f"DRY RUN Term {term}" if dry_run else f"Term {term}"
        _print_summary(term_label, counters)
        _accumulate_counters(rollup, counters)

    if len(terms) > 1:
        rollup_label = (
            f"DRY RUN Rollup ({terms[0]}-{terms[-1]}, {len(terms)} terms)"
            if dry_run
            else f"Rollup ({terms[0]}-{terms[-1]}, {len(terms)} terms)"
        )
        _print_summary(rollup_label, rollup)
