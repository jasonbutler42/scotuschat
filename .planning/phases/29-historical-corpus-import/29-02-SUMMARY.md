---
phase: 29-historical-corpus-import
plan: 02
subsystem: pipeline
tags: [python, pytest, tdd, difflib, jsonl, apolitical-constraint]

# Dependency graph
requires:
  - phase: 29-historical-corpus-import (Plan 01)
    provides: schema foundation (oyez_* external-id columns, data/corpus/ directory)
provides:
  - "pipeline/corpus/loader.py: streaming JSONL/JSON readers for the ConvoKit source files"
  - "pipeline/corpus/stage_directions.py: curated-vocabulary stage-direction detector"
  - "pipeline/corpus/apolitical.py: apolitical allowlist extractors (the sole sanctioned raw-dict-to-ORM-field translation layer)"
affects: [29-historical-corpus-import Plan 04 (justice CSV import), 29-historical-corpus-import Plan 05 (ConvoKit importer)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Whole-turn stage-direction detection: regex requires the ENTIRE utterance text be one bracketed/parenthesized token before any vocabulary match is attempted, so embedded parenthetical citations mid-sentence never match"
    - "Positive allowlist extraction (explicit dict literal keyed by name) as the only sanctioned path from raw external-source dicts into ORM-bound fields"
    - "Streaming line-by-line JSONL iteration (for line in f + json.loads per line) for files too large to load whole; full json.load() only for files verified small enough (conversations.json 3.8MB, speakers.json 0.6MB)"

key-files:
  created:
    - pipeline/corpus/__init__.py
    - pipeline/corpus/loader.py
    - pipeline/corpus/stage_directions.py
    - pipeline/corpus/apolitical.py
    - pipeline/tests/test_corpus_loader.py
    - pipeline/tests/test_corpus_stage_directions.py
    - pipeline/tests/test_corpus_apolitical.py
  modified: []

key-decisions:
  - "detect_stage_direction() only classifies when the ENTIRE input string is a single bracket/paren token (D-16's whole-turn-marker model) -- this alone rules out the 'plain speech with embedded parenthetical citation' anti-case without any extra logic"
  - "Typo tolerance implemented via difflib.get_close_matches with cutoff=0.8 against a normalized curated-vocabulary dict, applied only after exact-match and explicit-rejection checks (numeric-only tokens, and the single-letter/phonetic 'ph' literal) have already ruled a token out"
  - "extract_case_fields/extract_conversation_fields field lists chosen from 29-CONTEXT.md's canonical_refs verified real-data field names (title/petitioner/respondent/docket_no/decided_date/citation/court/year/transcripts/advocates/case_id for cases; conversation_id/case_id/advocates for conversations) rather than the plan's illustrative 'e.g.' list verbatim"

patterns-established:
  - "TDD RED/GREEN commit pairs for correctness-critical pure-Python modules: failing test committed first (import error), then implementation committed separately"

requirements-completed: [CORPUS-05, CORPUS-06]

coverage:
  - id: D1
    description: "Streaming JSONL loader yields one utterance dict per line without loading the whole file into memory, plus term-scoped conversations/speakers/cases loaders"
    requirement: "CORPUS-05"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_corpus_loader.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Stage-direction detector classifies curated markers (brackets or parens, typo-tolerant) and rejects legal-list/phonetic markers"
    requirement: "CORPUS-06"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_corpus_stage_directions.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Apolitical allowlist extractors provably exclude win_side/votes_side/scdb_docket_id and all related outcome fields, and never let unrecognized source keys pass through"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_corpus_apolitical.py"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-07-09
status: complete
---

# Phase 29 Plan 02: Corpus Helper Modules Summary

**Three tested pure-Python modules -- streaming JSONL loader, typo-tolerant curated-vocabulary stage-direction detector, and a positive apolitical allowlist extractor -- that Plan 05's ConvoKit importer will orchestrate.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-09T22:58:49Z
- **Completed:** 2026-07-09T23:10:00Z
- **Tasks:** 3
- **Files modified:** 7 (all new)

## Accomplishments
- `detect_stage_direction()` correctly classifies all curated markers (Inaudible, Laughter/Laughs, Voice Overlap, Recess, Luncheon Recess, Cross Talk) inside either brackets or parens, tolerates real observed typos (Luaghter, Inaudibel) via a difflib close-match, and explicitly rejects the anti-cases that a blind bracket/paren regex would have misclassified: `(a)`/`(b)`/`(1)`/`(2)` legal-list markers, the `(ph)` phonetic-spelling convention, and ordinary sentences that merely contain a parenthetical citation.
- `extract_case_fields`/`extract_conversation_fields` build explicit, positive allowlisted dicts -- proven (via unit test, not just code review) to exclude every field in `FORBIDDEN_FIELDS` (win_side, win_side_detail, votes, votes_detail, votes_side, scdb_docket_id) even when all six are present in the input, and to never leak an unrecognized future source key through.
- `stream_utterances_for_conversation_ids` is confirmed generator-based (`inspect.isgeneratorfunction`) and streams line-by-line rather than loading the whole file, satisfying the 900MB memory constraint; `load_conversations_for_term`/`load_speakers`/`load_cases` round out the file-reading surface Plan 05 needs.

## Task Commits

Each task was committed atomically (Tasks 1 and 2 used TDD RED/GREEN pairs; Task 3 is not TDD-tagged):

1. **Task 1: Stage-direction detector**
   - `38c3d6b3` test(29-02): add failing test for stage-direction detector (RED)
   - `d717c04c` feat(29-02): implement curated-vocabulary stage-direction detector (GREEN)
2. **Task 2: Apolitical allowlist extractors**
   - `52050e3e` test(29-02): add failing test for apolitical allowlist extractors (RED)
   - `d30d613a` feat(29-02): implement apolitical allowlist extractors (GREEN)
3. **Task 3: Streaming JSONL/JSON corpus loader**
   - `3ab50925` feat(29-02): implement streaming JSONL/JSON corpus loader

**Plan metadata:** (this commit)

_Note: TDD tasks (1 and 2) each have a test → feat commit pair; Task 3 (plain `auto`) was committed as a single feat commit alongside its own tests._

## Files Created/Modified
- `pipeline/corpus/__init__.py` - package marker with module purpose docstring
- `pipeline/corpus/loader.py` - `stream_utterances_for_conversation_ids`, `load_conversations_for_term`, `load_speakers`, `load_cases`
- `pipeline/corpus/stage_directions.py` - `CURATED_MARKERS`, `detect_stage_direction(text) -> str | None`
- `pipeline/corpus/apolitical.py` - `FORBIDDEN_FIELDS`, `extract_case_fields`, `extract_conversation_fields`
- `pipeline/tests/test_corpus_stage_directions.py` - 17 tests covering positive/typo/negative cases
- `pipeline/tests/test_corpus_apolitical.py` - 9 tests proving forbidden-field exclusion and positive-allowlist behavior
- `pipeline/tests/test_corpus_loader.py` - 6 tests against tmp_path fixtures (never the real 900MB file)

## Decisions Made
- `detect_stage_direction`'s regex (`_WHOLE_TURN_MARKER_RE`) requires the entire input string be a single bracket/paren token before any vocabulary comparison happens -- this single design choice handles both the "whole-turn marker" positive requirement (D-16) and the "embedded parenthetical citation mid-sentence" negative requirement without any additional heuristics.
- Rejected numeric-only tokens and the curated single-letter/phonetic literal set (`a`, `b`, `c`, `d`, `ph`) are checked BEFORE the fuzzy match, so they can never accidentally close-match a curated term.
- `apolitical.py`'s field lists were sourced from 29-CONTEXT.md's canonical_refs verified real cases.jsonl/conversations.json field names (e.g. `title`, `petitioner`, `respondent`) rather than the plan's illustrative "title/case_name" shorthand, since the actual raw dict uses `title` directly.

## Deviations from Plan

None - plan executed exactly as written. Field-name choices in `apolitical.py` (see Decisions above) are within the plan's explicit "e.g." discretion, not a deviation from a locked requirement.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. These are pure-Python modules with no DB or network dependency.

## Next Phase Readiness
- All three helper modules are import-ready for Plan 04 (justice CSV import, if it needs stage-direction/apolitical helpers) and Plan 05 (the ConvoKit bulk importer), matching the plan's `key_links` requirement of a stable, import-callable function signature.
- No blockers. Plan 05 can call `extract_case_fields`/`extract_conversation_fields` directly as the only sanctioned path from raw `conversations.json`/`cases.jsonl` dicts into ORM-bound values, and `stream_utterances_for_conversation_ids`/`load_conversations_for_term`/`load_speakers`/`load_cases` directly for file I/O.

---
*Phase: 29-historical-corpus-import*
*Completed: 2026-07-09*
