---
phase: 42-corpus-import-fidelity-diff-fix
plan: 01
subsystem: pipeline
tags: [convokit, sqlalchemy, argparse, postgres, corpus-import]

# Dependency graph
requires:
  - phase: 41-canonical-corpus-fixture-selection
    provides: confirmed complexity fixture identity (conversation 15169, docket 642, term 1966) in .planning/FIXTURES.md
provides:
  - --conversation-id scoped single-conversation import option on the import-convokit CLI subcommand
  - pipeline/corpus/loader.py::load_conversation_by_id
  - pipeline/commands/import_convokit.py::_resolve_scoped_conversation
  - ConvoKit conversation 15169 landed in the dev database as the phase's diff/fix target
affects: [42-02-corpus-import-fidelity-diff-fix, 42-03-corpus-import-fidelity-diff-fix, 42-04-corpus-import-fidelity-diff-fix, 42-05-corpus-import-fidelity-diff-fix, 43-dev-only-reset-to-fixture]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Scoped single-conversation import narrows the conversations dict to one id BEFORE wanted_ids is built, so the 900MB utterances.jsonl stream filters to one conversation instead of a whole term"
    - "CLI flag presence read via getattr(args, 'flag', None) so pre-existing test Namespaces without the attribute take the untouched legacy branch instead of raising AttributeError"

key-files:
  created: []
  modified:
    - pipeline/corpus/loader.py
    - pipeline/commands/import_convokit.py
    - pipeline/__main__.py
    - pipeline/tests/test_corpus_loader.py
    - pipeline/tests/test_import_convokit_core.py

key-decisions:
  - "--conversation-id joins the existing --term/--term-range mutually-exclusive group (rather than a bolt-on separate flag) so argparse enforces exactly one of the three at parse time"
  - "The scoped path derives its own October Term from the conversation's case_id prefix and never calls _resolve_terms, matching D-01's 'never operator-supplied' requirement"

patterns-established:
  - "Pattern: narrow to a single id before wanted_ids is built (not after) whenever a new scoped-import variant is added to run_import_convokit"

requirements-completed: [CORPUS-13, CORPUS-14]

coverage:
  - id: D1
    description: "--conversation-id CLI option imports exactly one ConvoKit conversation end-to-end (CLI to database), deriving its own October Term from the conversation's case_id"
    requirement: "CORPUS-13"
    verification:
      - kind: e2e
        ref: "./.venv/Scripts/python.exe -m pipeline import-convokit --conversation-id 15169 (real dev DB)"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::TestResolveScopedConversation"
        status: pass
    human_judgment: false
  - id: D2
    description: "An unknown --conversation-id fails fast (non-zero exit, error names the id) before any database write"
    requirement: "CORPUS-13"
    verification:
      - kind: e2e
        ref: "./.venv/Scripts/python.exe -m pipeline import-convokit --conversation-id 99999999 (exit code 1, stderr contains 99999999)"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::TestResolveScopedConversation::test_raises_argument_type_error_naming_rejected_id_when_absent"
        status: pass
    human_judgment: false
  - id: D3
    description: "Re-running the scoped import against an already-imported conversation is a no-op skip (idempotency, CORPUS-14)"
    requirement: "CORPUS-14"
    verification:
      - kind: e2e
        ref: "second run of import-convokit --conversation-id 15169 printed '0 arguments created, 1 arguments skipped'; arguments count stayed at 166"
        status: pass
    human_judgment: false
  - id: D4
    description: "Scoped import creates zero side effects on other conversations in the same term (only conversation 15169 lands, not the other 134 term-1966 conversations)"
    requirement: "CORPUS-13"
    verification:
      - kind: e2e
        ref: "post-import query: cases where term_year=1966 = 1; arguments joined to term-1966 cases = 1"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_scoped_import_creates_only_the_scoped_conversation"
        status: pass
    human_judgment: false
  - id: D5
    description: "question_number is derived via _next_question_number in scoped mode too, never hardcoded to 1 (Phase 29 CR-01)"
    requirement: "CORPUS-14"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_scoped_import_derives_question_number_via_next_question_number"
        status: pass
    human_judgment: false
  - id: D6
    description: "A scoped conversation with zero matching turns still creates its Argument/PipelineRun rows, creates zero Utterance rows, and does not raise"
    requirement: "CORPUS-14"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_scoped_import_zero_turn_conversation_creates_argument_zero_utterances"
        status: pass
    human_judgment: false
  - id: D7
    description: "Existing --term/--term-range behavior and every pre-existing test remain byte-for-byte unchanged"
    verification:
      - kind: unit
        ref: "pipeline/tests/ full suite (198 passed, 5 xfailed pre-existing)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-30
status: complete
---

# Phase 42 Plan 1: Scoped Single-Conversation Import & Fixture Landing Summary

**New `--conversation-id` option on `import-convokit` narrows the corpus loaders to one conversation before the 900MB utterance stream, landing ConvoKit conversation 15169 in the dev database as an isolated `status=pipeline` Argument.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-30T16:09:23Z (per STATE.md `last_updated`)
- **Completed:** 2026-07-30T16:34:00Z (approx, from git commit timestamps)
- **Tasks:** 2 completed
- **Files modified:** 5

## Accomplishments
- Built a scoped single-conversation import path (D-01): `load_conversation_by_id` (loader layer), `_resolve_scoped_conversation` (command layer, validates and derives the October Term from the conversation's own `case_id`), and `--conversation-id` registered on the CLI's existing `--term`/`--term-range` mutually-exclusive group.
- Landed ConvoKit conversation 15169 (Baltimore & Ohio Railroad Company v. United States, docket 642, term 1966, argued 1967-01-09) in the real dev database — the first time this fixture has ever been imported.
- Verified live against the real dev database (not a synthetic test DB): exactly one term-1966 `Case`/`Argument` pair was created, no other term-1966 conversation was pulled in as a side effect, and a second run of the exact same command is a clean no-op skip.
- Added automated coverage for the new path: 6 unit tests on `_resolve_scoped_conversation` (unset flag, missing Namespace attribute, unknown id, term derivation, missing/malformed `case_id`), 3 integration tests on `run_import_convokit`'s scoped mode (scoping between two same-term conversations, zero-turn conversation, `question_number` derivation via `_next_question_number`), and 2 loader tests for `load_conversation_by_id`.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end scoped import of one conversation — CLI to database, one path only** - `68e83c55` (feat)
2. **Task 2: Automated coverage for the scoped import path** - `b16a3f40` (test)

_No `docs: complete plan` metadata commit exists yet — that follows this SUMMARY._

## Files Created/Modified
- `pipeline/corpus/loader.py` - Added `load_conversation_by_id(conversations_path, conversation_id) -> dict | None`; loads `conversations.json` whole and returns the raw record for one key, or `None`. No `argparse` import.
- `pipeline/commands/import_convokit.py` - Added `_resolve_scoped_conversation(args, conversations_path)`; reads `--conversation-id` via `getattr`, fails fast (`argparse.ArgumentTypeError`) on an unknown id or an unparseable/missing `case_id` term prefix. `run_import_convokit` now resolves scoped mode before falling back to `_resolve_terms`, and narrows `conversations` to the scoped id before `wanted_ids` is built inside the per-term loop. Module docstring/usage updated.
- `pipeline/__main__.py` - Registered `--conversation-id` on the `import-convokit` subparser's mutually-exclusive term group; corrected the subparser's `description` (no longer claims arguments land at `status=draft`).
- `pipeline/tests/test_corpus_loader.py` - `TestLoadConversationById` (present/absent cases).
- `pipeline/tests/test_import_convokit_core.py` - `_scoped_args` helper (leaves `_args` untouched); `TestResolveScopedConversation` (6 unit tests); 3 scoped-mode integration tests against `run_import_convokit`.

## Decisions Made
- `--conversation-id` joins the existing `--term`/`--term-range` mutually-exclusive group rather than being a bolt-on separate flag, so argparse itself enforces exactly one of the three at parse time and `--help` continues to list all three together.
- Followed the plan's explicit direction on every other point (loader signature, fail-fast validation style, narrowing point in the per-term loop, test helper reuse) — no other deviation from the plan's `<action>` sections.

## Deviations from Plan

None - plan executed exactly as written. No Rule 1/2/3 auto-fixes were needed; the existing codebase's helpers (`_next_question_number`, `load_cases`, `load_speakers`, `stream_utterances_for_conversation_ids`, `_import_conversation`) were reused unchanged exactly as directed.

## Issues Encountered
None. The environment section's exact invocations (`./.venv/Scripts/python.exe` via WSL interop) worked as documented on the first attempt, including real dev-database connectivity.

## Post-Import Dev-DB State (for Plan 02/05 to compare against)

Captured immediately after the scoped import of conversation 15169 and confirmed stable after the idempotent second run:

| Metric | Before | After |
|---|---|---|
| `arguments` (total) | 165 | 166 |
| `people` (total) | 334 | 343 (9 created, 8 matched/reused) |
| `court_tenures` (total) | 123 | 123 (unchanged — `import-convokit` never writes this table, D-02) |
| `cases` where `term_year = 1966` | 0 | 1 |
| `arguments` where `source_docket = '642'` | 0 | 1 |
| `arguments` where `oyez_transcript_id = '15169'` | 0 | 1 |

Fixture argument details: `Argument.id = 1860`, `question_number = 1`, `status = PIPELINE`, `oyez_transcript_id = '15169'`. `Case.docket_number = '642'`, `term_year = 1966`. Utterance rows for the fixture: 480 total (467 spoken + 13 stage-direction) — clears the plan's `>= 479` acceptance threshold. `utterance rows errored` = 0. One PAUSED `AdminJob` at step `RESOLVE` references the argument. No other term-1966 conversation was created (`cases where term_year = 1966` = 1, not 135-derived; joined term-1966 arguments = 1).

Re-running `import-convokit --conversation-id 15169` a second time printed `0 arguments created, 1 arguments skipped (already imported)` with every other counter at 0; the `arguments` total stayed at 166.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Conversation 15169's rows are live in the dev database with the exact counts recorded above — Plan 02 (delete-and-reimport routine) and Plan 03 (fidelity diff script) can now read/act on real, not synthetic, rows for this fixture.
- The scoped `--conversation-id` path built here is explicitly flagged in 42-CONTEXT.md's Reusable Assets as very likely reusable by Phase 43 (Dev-Only Reset to Fixture), which needs to seed 4 conversations across 4 different terms without pulling in each term's other conversations.
- No blockers. `pipeline/tests/` is fully green (198 passed, 5 pre-existing xfailed, unrelated to this plan).

---
*Phase: 42-corpus-import-fidelity-diff-fix*
*Completed: 2026-07-30*
