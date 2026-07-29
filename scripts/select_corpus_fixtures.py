#!/usr/bin/env python3
"""
Offline, read-only path-coverage scoring script over the local ConvoKit
Supreme Court corpus (``data/corpus/``), built for Phase 41 (canonical
corpus fixture selection).

Implements:
  - D-03: ranks candidates for the complexity fixture by path-coverage
    breadth (how many distinct importer-stressing signals a candidate
    clears at once), never by a weighted composite of raw magnitudes.
  - D-04: apolitical hard exclusion -- every raw corpus read goes through
    ``pipeline.corpus.apolitical.extract_case_fields`` /
    ``extract_conversation_fields``, the sole sanctioned allowlisted read
    path into this script. No name in that module's ``FORBIDDEN_FIELDS``
    frozenset is ever read, stored, or printed by this script.
  - D-05: prints the top 5 ranked candidates by default.
  - D-06: each shortlisted candidate carries its raw structural signal
    numbers plus which named path-coverage flags it hit.

Exit code contract: 0 on a successful run (including ``--self-check`` when
every check passes); 1 when the corpus directory or any required corpus
file is missing, when a persisted cache is unreadable/incomplete without
``--allow-partial``, or when ``--self-check`` finds a failing check.

Usage:
    python3 scripts/select_corpus_fixtures.py
    python3 scripts/select_corpus_fixtures.py --corpus-dir data/corpus --max-utterance-rows 50000
    python3 scripts/select_corpus_fixtures.py --self-check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.corpus.apolitical import (  # noqa: E402
    FORBIDDEN_FIELDS,
    extract_case_fields,
    extract_conversation_fields,
)
from pipeline.corpus.loader import (  # noqa: E402
    load_cases,
    load_speakers,
    stream_utterances_for_conversation_ids,
)

DEFAULT_CORPUS_DIR = ROOT / "data" / "corpus"
REQUIRED_CORPUS_FILES = ("cases.jsonl", "conversations.json", "speakers.json", "utterances.jsonl")

# RESEARCH A3: approximate top-1% cutoffs on the observed real-corpus
# distributions. Tunable -- moving these only shifts where the shortlist
# boundary falls, never which candidate wins the recommendation.
THRESH_ADVOCATE = 9
THRESH_SPEAKER = 14
THRESH_TURN = 700
THRESH_TRANSCRIPTS = 2

FLAG_NAMES = (
    "multi_advocate_resolution",
    "high_speaker_dedup",
    "long_transcript_streaming",
    "reargument_question_number",
)

PROGRESS_INTERVAL = 300_000
DEFAULT_TOP = 5

# Copied from pipeline.commands.import_convokit's _JUSTICE_TYPE_VALUES /
# _UNATTRIBUTED_TYPE_VALUES -- that module is the source of truth for
# which speakers.json `type` values mean "bench" vs. "no real speaker".
JUSTICE_TYPE_VALUES = {"justice", "j", "bench"}
UNATTRIBUTED_TYPE_VALUES = {"u", "unattributed", "unknown"}


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus-dir",
        default=None,
        help="Directory holding the 4 ConvoKit source files (default: data/corpus)",
    )
    parser.add_argument(
        "--max-utterance-rows",
        type=int,
        default=None,
        help="Bound the utterances.jsonl streaming pass to this many rows (default: unbounded)",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Run the corpus-free assertion harness and exit; touches no corpus file",
    )
    return parser.parse_args(argv)


def _resolve_corpus_dir(args: argparse.Namespace) -> Path:
    """
    Resolve --corpus-dir and validate it exists BEFORE any file load, so a
    missing directory fails fast with a clear message instead of a
    FileNotFoundError raised deep inside a loader call mid-run. Mirrors
    import_convokit.py::_resolve_corpus_dir's shape and message style.
    """
    raw = getattr(args, "corpus_dir", None)
    corpus_dir = Path(raw) if raw else DEFAULT_CORPUS_DIR
    if not corpus_dir.is_dir():
        raise FileNotFoundError(
            f"--corpus-dir does not exist: {corpus_dir}. Place the ConvoKit "
            "supreme-corpus source files (cases.jsonl, conversations.json, "
            "speakers.json, utterances.jsonl) there before running "
            "select_corpus_fixtures.py."
        )
    return corpus_dir


def _require_corpus_files(corpus_dir: Path) -> dict[str, Path]:
    """
    Check every name in REQUIRED_CORPUS_FILES exists under corpus_dir. On
    any miss, raise FileNotFoundError naming the missing file(s) AND all
    four expected filenames, so the operator never has to guess what else
    is required.
    """
    paths = {name: corpus_dir / name for name in REQUIRED_CORPUS_FILES}
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing required corpus file(s) in {corpus_dir}: {', '.join(missing)}. "
            f"Expected all four: {', '.join(REQUIRED_CORPUS_FILES)}."
        )
    return paths


def _stream_signals(
    utterances_path: Path,
    wanted_ids: set[str],
    speakers: dict,
    max_rows: int | None,
) -> dict[str, dict]:
    """
    One streaming pass over utterances.jsonl (via
    stream_utterances_for_conversation_ids -- never a whole-file load),
    aggregating per-conversation turn_count / distinct_speaker_count /
    bench_speaker_count. Every id in wanted_ids gets an entry, including
    conversations with zero utterance rows. Speaker classification reads
    speakers.json's own `type` field (never a naming-convention guess).
    """
    turn_counts: dict[str, int] = {cid: 0 for cid in wanted_ids}
    speaker_sets: dict[str, set] = {cid: set() for cid in wanted_ids}
    bench_sets: dict[str, set] = {cid: set() for cid in wanted_ids}

    for i, row in enumerate(
        stream_utterances_for_conversation_ids(utterances_path, wanted_ids), start=1
    ):
        cid = row.get("conversation_id")
        speaker_id = row.get("speaker")
        turn_counts[cid] = turn_counts.get(cid, 0) + 1

        speaker_meta = speakers.get(speaker_id) or {}
        speaker_type = str(speaker_meta.get("type") or "").strip().lower()
        if speaker_type not in UNATTRIBUTED_TYPE_VALUES:
            speaker_sets.setdefault(cid, set()).add(speaker_id)
        if speaker_type in JUSTICE_TYPE_VALUES:
            bench_sets.setdefault(cid, set()).add(speaker_id)

        if i % PROGRESS_INTERVAL == 0:
            print(f"...processed {i:,} utterance rows", file=sys.stderr)
        if max_rows is not None and i >= max_rows:
            break

    return {
        cid: {
            "turn_count": turn_counts.get(cid, 0),
            "distinct_speaker_count": len(speaker_sets.get(cid, set())),
            "bench_speaker_count": len(bench_sets.get(cid, set())),
        }
        for cid in wanted_ids
    }


def _case_name(case_fields: dict) -> str:
    """Prefer cases.jsonl's "title"; fall back to "{petitioner} v. {respondent}"."""
    title = case_fields.get("title")
    if title:
        return title
    petitioner = case_fields.get("petitioner") or "Unknown"
    respondent = case_fields.get("respondent") or "Unknown"
    return f"{petitioner} v. {respondent}"


def _conversation_rows(cases_by_id: dict, conversations: dict, signals: dict) -> list[dict]:
    """
    Build one uniform record per conversation id, reading raw corpus dicts
    ONLY through extract_case_fields / extract_conversation_fields (D-04).
    Join key is a conversation's case_id against cases_by_id (indexed by
    id -- never docket_no).
    """
    rows: list[dict] = []
    for cid, conv in conversations.items():
        conv_fields = extract_conversation_fields(conv)
        advocates = conv_fields.get("advocates") or {}
        advocate_count = len(advocates)
        case_id = conv_fields.get("case_id")

        raw_case = cases_by_id.get(case_id)
        if raw_case is not None:
            case_fields = extract_case_fields(raw_case)
            case_name = _case_name(case_fields)
        else:
            case_fields = {}
            case_name = "(no matching cases.jsonl row)"

        transcripts = case_fields.get("transcripts") or []
        sig = signals.get(cid) or {
            "turn_count": 0,
            "distinct_speaker_count": 0,
            "bench_speaker_count": 0,
        }

        rows.append(
            {
                "conversation_id": cid,
                "case_id": case_id,
                "case_name": case_name,
                "docket_no": case_fields.get("docket_no"),
                "term": case_fields.get("year"),
                "n_transcripts": len(transcripts),
                "advocate_count": advocate_count,
                "distinct_speaker_count": sig["distinct_speaker_count"],
                "bench_speaker_count": sig["bench_speaker_count"],
                "turn_count": sig["turn_count"],
                "transcripts": transcripts,
            }
        )
    return rows


def _path_coverage_flags(row: dict, thresholds: dict) -> dict[str, bool]:
    return {
        "multi_advocate_resolution": row["advocate_count"] >= thresholds["advocate"],
        "high_speaker_dedup": row["distinct_speaker_count"] >= thresholds["speaker"],
        "long_transcript_streaming": row["turn_count"] >= thresholds["turn"],
        "reargument_question_number": row["n_transcripts"] >= thresholds["transcripts"],
    }


def _magnitude_sum(row: dict) -> int:
    return (
        row["advocate_count"]
        + row["distinct_speaker_count"]
        + row["turn_count"]
        + row["n_transcripts"]
    )


def _id_sort_key(conversation_id):
    """
    Coerce an all-digit id to int for numeric-stable ascending order;
    fall back to the raw string otherwise. Wrapped in a (kind, value)
    tuple so int and str components are never compared against each
    other directly (which would raise TypeError).
    """
    s = str(conversation_id)
    if s.isdigit():
        return (0, int(s))
    return (1, s)


def _rank_candidates(rows: list[dict], thresholds: dict, top: int) -> list[dict]:
    """
    Attach flags/coverage/magnitude_sum to each row and sort by the TOTAL
    ORDER (-coverage, -magnitude_sum, conversation_id ascending). Never
    collapses the four signals into a single weighted composite (D-03).
    An empty rows list returns []; top > len(rows) returns every row.
    """
    annotated = []
    for row in rows:
        flags = _path_coverage_flags(row, thresholds)
        coverage = sum(1 for v in flags.values() if v)
        annotated.append(
            {
                **row,
                "flags": flags,
                "coverage": coverage,
                "magnitude_sum": _magnitude_sum(row),
            }
        )
    annotated.sort(
        key=lambda r: (-r["coverage"], -r["magnitude_sum"], _id_sort_key(r["conversation_id"]))
    )
    return annotated[:top]


def _print_shortlist(ranked: list[dict], thresholds: dict) -> None:
    """
    Markdown shortlist table on stdout. No timestamp, elapsed time,
    hostname, or absolute path anywhere -- Task 2's determinism gate
    compares two runs byte for byte.
    """
    header = (
        "| Rank | Coverage | Conversation ID | Case Name | Docket | Term | "
        "Advocates | Distinct Speakers | Bench Speakers | Turns | Transcripts | Flags hit |"
    )
    sep = "|---|---|---|---|---|---|---|---|---|---|---|---|"
    print(header)
    print(sep)
    for i, row in enumerate(ranked, start=1):
        flags_hit = ", ".join(name for name in FLAG_NAMES if row["flags"].get(name)) or "—"
        print(
            f"| {i} | {row['coverage']}/4 | {row['conversation_id']} | {row['case_name']} | "
            f"{row['docket_no']} | {row['term']} | {row['advocate_count']} | "
            f"{row['distinct_speaker_count']} | {row['bench_speaker_count']} | "
            f"{row['turn_count']} | {row['n_transcripts']} | {flags_hit} |"
        )


def _self_check() -> int:
    """
    Corpus-free assertion harness. Every check that holds prints a line
    beginning with "PASS "; a failing check prints a line beginning with
    "FAIL " instead. Returns 0 only when every check held.
    """
    ok = True
    thresholds = {"advocate": 5, "speaker": 5, "turn": 5, "transcripts": 2}

    # Check 1: total order -- coverage desc, magnitude desc, id asc; a
    # coverage tie AND, inside it, a magnitude-sum tie both resolve
    # deterministically, and two successive calls return an identical
    # id sequence.
    synthetic_rows = [
        {
            "conversation_id": "300",
            "case_name": "C",
            "docket_no": "3",
            "term": 2000,
            "n_transcripts": 2,
            "advocate_count": 5,
            "distinct_speaker_count": 5,
            "turn_count": 5,
        },
        {
            "conversation_id": "100",
            "case_name": "A",
            "docket_no": "1",
            "term": 2000,
            "n_transcripts": 2,
            "advocate_count": 5,
            "distinct_speaker_count": 5,
            "turn_count": 5,
        },
        {
            "conversation_id": "200",
            "case_name": "B",
            "docket_no": "2",
            "term": 2000,
            "n_transcripts": 2,
            "advocate_count": 5,
            "distinct_speaker_count": 6,
            "turn_count": 5,
        },
        {
            "conversation_id": "1",
            "case_name": "D",
            "docket_no": "4",
            "term": 2000,
            "n_transcripts": 0,
            "advocate_count": 0,
            "distinct_speaker_count": 0,
            "turn_count": 0,
        },
    ]
    ranked_a = _rank_candidates(synthetic_rows, thresholds, top=10)
    ranked_b = _rank_candidates(synthetic_rows, thresholds, top=10)
    ids_a = [r["conversation_id"] for r in ranked_a]
    ids_b = [r["conversation_id"] for r in ranked_b]
    # "200" has a higher magnitude sum (distinct_speaker_count=6) than the
    # coverage-tied "300"/"100" pair, which then breaks their own tie by
    # id ascending ("100" < "300"); "1" clears zero flags, ranks last.
    expected_order = ["200", "100", "300", "1"]
    if ids_a == expected_order and ids_a == ids_b:
        print("PASS total order: coverage-desc/magnitude-desc/id-asc stable across two runs")
    else:
        print(f"FAIL total order: got {ids_a} / {ids_b}, expected {expected_order}")
        ok = False

    # Check 2: degenerate inputs -- empty/single/over-request.
    empty_result = _rank_candidates([], thresholds, top=5)
    single_result = _rank_candidates([synthetic_rows[0]], thresholds, top=5)
    over_request = _rank_candidates(synthetic_rows[:2], thresholds, top=5)
    if empty_result == [] and len(single_result) == 1 and len(over_request) == 2:
        print("PASS degenerate inputs: empty/single/over-request all handled without raising")
    else:
        print("FAIL degenerate inputs: unexpected result shapes")
        ok = False

    # Check 3: zero coverage -- thresholds raised above every synthetic
    # value; all flags false, coverage 0, requested row count still
    # returned rather than an empty table.
    high_thresholds = {"advocate": 999, "speaker": 999, "turn": 999999, "transcripts": 999}
    zero_ranked = _rank_candidates(synthetic_rows, high_thresholds, top=5)
    if len(zero_ranked) == min(5, len(synthetic_rows)) and all(
        r["coverage"] == 0 for r in zero_ranked
    ):
        print("PASS zero coverage: all flags false, requested row count still returned")
    else:
        print("FAIL zero coverage: unexpected coverage or row count")
        ok = False

    # Check 4: apolitical containment -- a synthetic raw case/conversation
    # dict deliberately carries every FORBIDDEN_FIELDS name alongside the
    # allowed ones; the extractors' OWN returned key set must never
    # intersect FORBIDDEN_FIELDS. Names are derived by iterating the
    # imported frozenset, never written out literally.
    synthetic_raw_case = {name: f"synthetic-{name}" for name in FORBIDDEN_FIELDS}
    synthetic_raw_case.update(
        {
            "title": "Synthetic v. Case",
            "petitioner": "Synthetic",
            "respondent": "Case",
            "docket_no": "99-9999",
            "decided_date": "2000-01-01",
            "citation": "999 US 1",
            "court": "scotus",
            "year": 2000,
            "transcripts": [],
            "advocates": {},
            "id": "2000_1",
        }
    )
    case_out = extract_case_fields(synthetic_raw_case)

    synthetic_raw_conversation = {name: f"synthetic-{name}" for name in FORBIDDEN_FIELDS}
    synthetic_raw_conversation.update(
        {
            "conversation_id": "1",
            "case_id": "2000_1",
            "advocates": {},
        }
    )
    conv_out = extract_conversation_fields(synthetic_raw_conversation)

    hits = (set(case_out) | set(conv_out)) & FORBIDDEN_FIELDS
    if not hits:
        print("PASS apolitical containment: extractor output never carries a FORBIDDEN_FIELDS name")
    else:
        print(f"FAIL apolitical containment: forbidden fields leaked: {sorted(hits)}")
        ok = False

    return 0 if ok else 1


def main(argv=None) -> int:
    args = _parse_args(argv)

    if args.self_check:
        return _self_check()

    try:
        corpus_dir = _resolve_corpus_dir(args)
        paths = _require_corpus_files(corpus_dir)
    except (FileNotFoundError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    cases_by_id = load_cases(paths["cases.jsonl"])
    with paths["conversations.json"].open("r", encoding="utf-8") as f:
        conversations = json.load(f)
    speakers = load_speakers(paths["speakers.json"])

    wanted_ids = set(conversations.keys())
    signals = _stream_signals(
        paths["utterances.jsonl"], wanted_ids, speakers, args.max_utterance_rows
    )

    rows = _conversation_rows(cases_by_id, conversations, signals)
    thresholds = {
        "advocate": THRESH_ADVOCATE,
        "speaker": THRESH_SPEAKER,
        "turn": THRESH_TURN,
        "transcripts": THRESH_TRANSCRIPTS,
    }
    ranked = _rank_candidates(rows, thresholds, DEFAULT_TOP)
    _print_shortlist(ranked, thresholds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
