"""
Pipeline import-convokit command.

Term-batched orchestration (D-07) for Phase 29's bulk historical import: for
one October Term (--term) or an inclusive range (--term-range), scaffolds
Case / Argument / CaseArgument / PipelineRun rows and resolves bench/advocate
speakers into Person + ArgumentParticipant rows -- entirely from
conversations.json + cases.jsonl + speakers.json (D-21). Utterance import and
the batch summary land in Plan 05/06 -- this module stops at scaffolding +
speaker resolution (this plan's declared objective boundary).

This file is built up task-by-task per 29-04-PLAN.md:
    Task 1 (this stage): CLI subcommand, --term/--term-range validation,
        --corpus-dir validation, and the per-term file-loading skeleton
        that delegates entity creation to Task 2's function.
    Task 2: Case/Argument/CaseArgument/PipelineRun entity creation.
    Task 3: bench/advocate speaker resolution into Person/ArgumentParticipant.

Usage:
    python -m pipeline import-convokit --term 1955
    python -m pipeline import-convokit --term-range 1955-1960
    python -m pipeline import-convokit --term 1955 --corpus-dir data/corpus
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.corpus.loader import (
    load_cases,
    load_conversations_for_term,
    load_speakers,
)

# Matches the data/corpus/ scaffolding (D-20/D-21) -- the operator copies the
# ConvoKit source files here locally; it is gitignored, not tracked.
DEFAULT_CORPUS_DIR = Path("data/corpus")


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
# Per-conversation entity creation -- Task 2 implements the real logic;
# this skeleton stage just counts conversations seen so the per-term loop
# below is fully wired end-to-end.
# ---------------------------------------------------------------------------


async def _import_conversation(
    session,
    conversation_id: str,
    raw_conversation: dict,
    cases_by_case_id: dict[str, dict],
    speakers_index: dict,
    counters: dict,
) -> None:
    """
    Import one conversation -- Case/Argument/CaseArgument/PipelineRun
    scaffolding (Task 2) + speaker resolution (Task 3) land here in
    subsequent tasks. This skeleton stage records that the conversation was
    reached by the per-term loop.
    """
    counters["seen"] = counters.get("seen", 0) + 1


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
        counters: dict = {}
        for conversation_id, raw_conversation in conversations.items():
            await _import_conversation(
                session=None,
                conversation_id=conversation_id,
                raw_conversation=raw_conversation,
                cases_by_case_id=cases_by_case_id,
                speakers_index=speakers_index,
                counters=counters,
            )
        print(
            f"Term {term}: {counters.get('seen', 0)} conversations seen "
            "(entity creation lands in Task 2)."
        )
