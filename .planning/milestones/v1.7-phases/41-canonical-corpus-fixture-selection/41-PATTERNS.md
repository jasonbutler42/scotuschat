# Phase 41: Canonical Corpus Fixture Selection - Pattern Map

**Mapped:** 2026-07-29
**Files analyzed:** 2 (both new; this phase makes no modifications to existing files)
**Analogs found:** 2 / 2

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `scripts/select_corpus_fixtures.py` (NEW) | utility (offline analysis/audit script) | batch (read-only scan → ranked printout) | `scripts/audit_tenure_seat_identifiers.py` | role-match (same directory, same "one-off audit that reads repo/data and prints a verdict" shape; data flow differs slightly — audit script exits pass/fail on source code, this one ranks candidates from corpus data — but the CLI script skeleton, docstring-as-spec convention, and "no persistence beyond a printout" shape are directly reusable) |
| `.planning/FIXTURES.md` (NEW) | config / durable planning doc (not code) | transform (confirmed operator decision → durable markdown record) | No close in-repo analog (first cross-phase fixture doc of this kind) — structure instead dictated by CONTEXT.md D-08's required-fields list and RESEARCH.md's Code Examples tables (Top-5 shortlist table, state-variety candidates table) | no analog — use D-08 field list + RESEARCH.md table shape directly |

Note: no importer/API/DB/frontend files are created or modified this phase (decision-gate only, per CONTEXT.md domain statement and success criterion 5). `pipeline/corpus/loader.py` is read-only reused, never modified.

## Pattern Assignments

### `scripts/select_corpus_fixtures.py` (utility, batch/read-only-scan)

**Analog:** `scripts/audit_tenure_seat_identifiers.py` (267 lines, full file read)

**Script skeleton pattern** (lines 1-45, 187-206, 265-267):
```python
#!/usr/bin/env python3
"""<Docstring is the spec: states the exact phase/decision this script
proves, cites the CONTEXT.md decision IDs it implements, states the
exact exit-code contract, and gives a Usage: line.>

Usage: python scripts/audit_tenure_seat_identifiers.py
Exit code 0: no unclassified hits. Exit code 1: unclassified hit(s) found...
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# ... module-level constants for thresholds/paths, named after the
# decision they encode (mirrors this phase's THRESH_ADVOCATE=9 etc.
# from RESEARCH.md Pattern 1) ...

def main() -> int:
    ...
    return 0  # or 1 on failure/missing-input

if __name__ == "__main__":
    raise SystemExit(main())
```
Apply directly: `select_corpus_fixtures.py` should keep this exact shape — shebang, `from __future__ import annotations`, a spec-as-docstring naming the exact decisions (D-03/D-05/D-06) it implements, a `main() -> int` returning a stable exit code, and the `if __name__ == "__main__": raise SystemExit(main())` footer. Since this phase's script only prints a ranked report (no pass/fail audit gate), `main()` can simply `return 0` after printing — there is no failure exit code needed unless the corpus dir is missing (see below).

**Fail-fast input validation pattern** — reuse `import_convokit.py`'s `_resolve_corpus_dir` (lines 190-205 of `pipeline/commands/import_convokit.py`), don't hand-roll a new one:
```python
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
```
RESEARCH.md's own Security Domain section (V5) explicitly says to reuse this exact fail-fast pattern if the new script takes a `--corpus-dir` flag.

**Deterministic "walk and classify" iteration pattern** (lines 187-227, adapted from files → conversations):
```python
def _iter_scanned_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in INCLUDED_SUFFIXES:
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        yield path
```
The audit script's "walk deterministically, filter, classify each item, accumulate into an unclassified/classified split" shape maps directly onto this phase's "iterate all conversations, compute 4 flags per conversation, accumulate into a ranked list" shape — same control-flow skeleton, different predicate/accumulator.

**Reusable corpus loaders — call these, never hand-roll parsing** (source: `pipeline/corpus/loader.py`, full file, 102 lines):
```python
def load_cases(cases_path: Path) -> dict:
    """
    Stream cases_path (cases.jsonl, ~13MB) line-by-line and return a
    dict indexed by each row's "id" field (e.g. "1955_71") -- ...
    NOT indexed by docket_no: historical docket numbers recycle across
    October Terms...
    """

def load_speakers(speakers_path: Path) -> dict:
    """Load speakers_path (speakers.json, ~0.6MB) fully. Keyed by
    speaker slug/id (justices: j__firstname_lastname; advocates:
    slugified display name)."""

def stream_utterances_for_conversation_ids(
    utterances_path: Path, wanted_ids: set[str]
) -> Iterator[dict]:
    """Stream utterances_path (JSONL) line-by-line, yielding only rows
    whose conversation_id is in wanted_ids. Never calls .read()/json.load()
    on the whole file..."""

def load_conversations_for_term(conversations_path: Path, term: int) -> dict:
    """Load conversations_path (conversations.json, ~3.8MB -- safe to
    load whole)... [note: term-scoped — RESEARCH.md Pitfall 1 says the
    new script should instead do ONE direct json.load() over the whole
    file since it's "safe to load whole" per this docstring, then
    group/filter in memory itself rather than looping this function
    once per term]"""
```
Concrete usage for the new script:
- `load_cases(cases_path)` → dict keyed by `id` (e.g. `"1955_71"`) — use this exact dict to join a conversation's `case_id` to its case row. **Never** re-key by `docket_no`.
- For conversations: per RESEARCH.md Pitfall 1, do one direct `json.load()` on `conversations.json` (documented "safe to load whole" in the loader's own docstring) rather than calling `load_conversations_for_term` once per term — the loader function itself is not the right call shape for a whole-corpus scan; the same file/format contract it documents *is* still authoritative to imitate.
- `stream_utterances_for_conversation_ids(utterances_path, wanted_ids)` → single streaming pass to compute `turn_count`, `distinct_speaker_count`, `bench_speaker_count` per conversation. `wanted_ids` = the full set of all conversation ids being scored (this phase scores the whole corpus, not a subset).
- `load_speakers(speakers_path)` → use each speaker's own `type` field (`"J"`/`"A"`/`"U"`) to classify bench vs. advocate speakers — mirrors `import_convokit.py::_is_justice_type`'s authoritative-`type`-field pattern (never guess from slug naming convention).

**Join-key pattern — the one rule every score/lookup must respect** (source: `pipeline/commands/import_convokit.py` module docstring + `_get_or_create_case`, lines 259-289):
```python
# Case/conversation join key, verbatim from import_convokit.py's own
# documented contract:
#   raw_case["id"] == conversation["case_id"]
# NEVER raw_case["docket_no"] == conversation[...]["docket_no"] --
# docket numbers recycle across October Terms (migration 0018 fix);
# a docket_no-keyed join silently conflates unrelated cases from
# different terms.
```
Apply verbatim in the new script's per-conversation case lookup: `cases_by_id[conversation["case_id"]]`, never a docket_no-keyed dict.

**Advocate-count signal — read the right dict** (source: `import_convokit.py` line 515, RESEARCH.md Pitfall 2):
```python
advocates = conversation.get("advocates") or {}
```
Use `conversation.get("advocates")` from `conversations.json` for the `advocate_count` signal — **not** `cases.jsonl`'s case-level `"advocates"` field (`apolitical.extract_case_fields` line 54: `"advocates": raw_case.get("advocates")`), which can differ for multi-session cases. Matching `_import_conversation`'s real read means the fixture's advocate count means what the importer will actually resolve.

**Re-argument / transcript-count signal — apolitical-safe substitute for multi-docket** (source: `apolitical.extract_case_fields`, line 53, and `import_convokit.py::_parse_argued_date`, lines 213-246):
```python
"transcripts": raw_case.get("transcripts"),  # apolitical.py's own allowlist — safe to read
```
`len(case_fields["transcripts"])` (or count of transcript entries matching the docket) is the 4th path-coverage flag (`reargument_question_number` in RESEARCH.md Pattern 1), replacing the dropped multi-docket signal. This field is already on `apolitical.py`'s positive allowlist (line 53) — safe to read without touching `FORBIDDEN_FIELDS`.

**Path-coverage checklist scoring — the new script's only genuinely new logic** (source: RESEARCH.md Architecture Patterns Pattern 1, verified against real corpus):
```python
THRESH_ADVOCATE = 9
THRESH_SPEAKER = 14
THRESH_TURN = 700
THRESH_TRANSCRIPTS = 2

flags = {
    "multi_advocate_resolution": advocate_count >= THRESH_ADVOCATE,
    "high_speaker_dedup": distinct_speaker_count >= THRESH_SPEAKER,
    "long_transcript_streaming": turn_count >= THRESH_TURN,
    "reargument_question_number": n_transcripts >= THRESH_TRANSCRIPTS,
}
path_coverage = sum(flags.values())
# Rank by path_coverage desc, tie-break by raw magnitude sum -- never a
# single weighted composite score (CONTEXT.md D-03 explicitly forbids this).
```

**Progress-signal pattern for the 900MB streaming pass** (RESEARCH.md Pitfall 3 — no direct code precedent in-repo, but dictated by the streaming discipline `stream_utterances_for_conversation_ids` already establishes):
```python
for i, row in enumerate(stream_utterances_for_conversation_ids(utterances_path, wanted_ids), start=1):
    ...  # accumulate per-conversation counters
    if i % 300_000 == 0:
        print(f"...processed {i:,} utterance rows", file=sys.stderr)
```

**Error handling pattern** (source: audit script lines 198-205, 213-217):
```python
if missing_roots:
    print(f"ERROR: expected scan root(s) not found: {missing_roots}", file=sys.stderr)
    return 1
...
except (UnicodeDecodeError, OSError) as exc:
    print(f"ERROR: could not read {rel}: {exc}", file=sys.stderr)
    return 1
```
Apply the same "print to stderr, return nonzero from `main()`" shape if the corpus directory or any of the 4 required corpus files is missing — matches `_resolve_corpus_dir`'s `FileNotFoundError` message style (clear, actionable, names the exact files expected).

---

### `.planning/FIXTURES.md` (planning doc, not code)

**No direct in-repo analog** — this is the first cross-phase durable-fixture-record doc. Structure instead directly from CONTEXT.md D-08 (required fields) and RESEARCH.md's Code Examples section (exact table shapes already produced from the real corpus this research session — reuse verbatim, don't re-derive).

**Required fields per D-08:** ConvoKit conversation id, case name, docket(s), term, argued date, role (complexity fixture, or which state variant).

**Recommended table shape** (RESEARCH.md Open Questions #1 recommendation — markdown table, one row per fixture):
```markdown
| Role | Conversation ID | Case Name | Docket(s) | Term | Argued Date |
|------|------------------|-----------|-----------|------|-------------|
| Complexity fixture | 14837 | Permian Basin Area Rate Cases (390 US 747) | 90 | 1967 | [from transcripts[].name matching this conversation] |
| Unpublished/DRAFT target | 13015 | Archawski v. Hanioti (350 US 532) | 351 | 1955 | ... |
| Published target | 18897 | Anderson v. Liberty Lobby, Inc. (477 US 242) | 84-1602 | 1985 | ... |
| Mid-pipeline target | 22372 | Abbott v. United States (562 US 8) | 09-479 | 2010 | ... |
```
Also preserve the actual ranked top-5 shortlist table (RESEARCH.md Code Examples, the 5-row table with Coverage/Advocates/Distinct Speakers/Bench Speakers/Turns/Transcripts/flags columns) somewhere in or adjacent to this doc — satisfies D-05/D-06 (shortlist + per-candidate signal+flag visibility) durably without re-running the 900MB streaming pass.

**Data source for the "Argued Date" column:** reuse `_parse_argued_date`'s logic (match `transcripts[].id == conversation_id`, else fall back to `transcripts[0]`) rather than re-deriving a different date-selection rule — keeps the doc's date consistent with what the importer itself would stamp on `Argument.argued_date`.

## Shared Patterns

### Apolitical hard exclusion (applies to `scripts/select_corpus_fixtures.py` only — no other file touches this)
**Source:** `pipeline/corpus/apolitical.py` lines 24-33 (`FORBIDDEN_FIELDS`) and lines 36-58 (`extract_case_fields`'s positive-allowlist style)
```python
FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "win_side",
        "win_side_detail",
        "votes",
        "votes_detail",
        "votes_side",
        "scdb_docket_id",
    }
)
```
**Apply to:** the scoring script must never read any of these 6 keys off a raw `cases.jsonl` row, even transiently for scoring, and even though `scdb_docket_id` would otherwise be a clean multi-docket-consolidation signal (RESEARCH.md's "multi-docket investigation" — resolved: don't use it, substitute the transcript-count signal instead, which is already on the positive allowlist). Follow `extract_case_fields`'s own convention of building an explicit positive dict of only the fields actually needed (`docket_no`, `year`, `transcripts`, `advocates`, `id`/`case_id`) rather than a blocklist filter over the raw row — this is the same "positive allowlist, never `dict(raw)`/`{**raw}`" discipline the apolitical module itself documents (lines 14-17).

### Join-key discipline (applies to `scripts/select_corpus_fixtures.py`)
**Source:** `pipeline/corpus/loader.py::load_cases` docstring (lines 77-101) and `import_convokit.py` module-level join contract (`raw_case["id"] == conversation["case_id"]`)
**Apply to:** every case lookup in the new script — index by `id`/`case_id`, never `docket_no`.

### Fail-fast missing-input handling (applies to `scripts/select_corpus_fixtures.py`)
**Source:** `pipeline/commands/import_convokit.py::_resolve_corpus_dir` (lines 190-205)
**Apply to:** the new script's corpus-dir resolution, if it accepts a `--corpus-dir` argument — same clear `FileNotFoundError` message naming the 4 expected files.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.planning/FIXTURES.md` | config/planning doc | transform | First cross-phase durable fixture-record doc in this repo; no prior `.planning/*.md` doc of this exact "confirmed decision record consumed by name from multiple later phases" shape exists to copy structurally. Use CONTEXT.md D-08's field list and RESEARCH.md's Code Examples tables directly (already reproduced above) rather than searching further — this is explicitly a new artifact type, not a gap in the search. |

## Metadata

**Analog search scope:** `scripts/` (all 3 existing scripts), `pipeline/corpus/loader.py`, `pipeline/corpus/apolitical.py`, `pipeline/commands/import_convokit.py` (targeted sections per RESEARCH.md's own line citations)
**Files scanned:** 5 (3 scripts directory-listing + loader.py + apolitical.py + import_convokit.py excerpts)
**Pattern extraction date:** 2026-07-29
