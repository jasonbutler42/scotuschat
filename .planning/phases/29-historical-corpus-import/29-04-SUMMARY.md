---
phase: 29-historical-corpus-import
plan: 04
subsystem: pipeline
tags: [sqlalchemy, asyncpg, convokit, apolitical-allowlist, idempotency, dateutil]

# Dependency graph
requires:
  - phase: 29-historical-corpus-import (Plan 01)
    provides: data/corpus/ scaffolding, oyez_case_id/oyez_transcript_id/oyez_speaker_id migration
  - phase: 29-historical-corpus-import (Plan 02)
    provides: pipeline/corpus/loader.py, pipeline/corpus/apolitical.py allowlist extractors
  - phase: 29-historical-corpus-import (Plan 03)
    provides: import-justices CLI, seeded/upgraded justice Person + CourtTenure rows
provides:
  - "pipeline/commands/import_convokit.py: run_import_convokit(args) term-batched orchestrator"
  - "import-convokit CLI subcommand (--term/--term-range/--corpus-dir) registered in pipeline/__main__.py"
  - "Idempotent Case/Argument/CaseArgument/PipelineRun scaffolding at status=draft with Oyez external IDs"
  - "Person/ArgumentParticipant speaker resolution (D-11 oyez_speaker_id-first, D-12/D-13 no-QA-gate + full_name fallback)"
affects: [29-05, 29-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-conversation session + try/except in the term loop (one DB transaction per conversation) so a single bad/missing join is flagged without rolling back or aborting sibling conversations in the same term"
    - "Generic speaker-resolution/side-classification helpers (_resolve_person, _resolve_and_link_participant) that don't care which caller/dict supplied the speaker_id -- designed for Plan 05 to reuse unchanged once utterances.jsonl reveals the real per-conversation bench roster"

key-files:
  created:
    - pipeline/commands/import_convokit.py
    - pipeline/tests/test_import_convokit_core.py
  modified:
    - pipeline/__main__.py

key-decisions:
  - "conversations.json-to-cases.jsonl join key is case_id equality (cases.jsonl carries its own case_id field matching the conversation key), not docket matching -- pipeline.corpus.loader.load_cases indexes by docket_no (needed for Case.docket_number), so a secondary case_id -> raw_case index is built locally in import_convokit.py from load_cases' values"
  - "Task 3's speaker-resolution/ArgumentParticipant-linking logic is generic and reusable; this plan only has conversations.json's advocates dict as a participant source (no utterances yet), so it's wired up for every id in that dict now -- Plan 05 reuses the same helpers unchanged once it streams utterances.jsonl and discovers the real per-conversation bench roster"
  - "question_number is hardcoded to 1 for every imported Argument per the plan's literal instruction -- a future re-argued historical case sharing a docket would collide with the (source_docket, question_number) UNIQUE constraint on its second conversation; out of scope for this plan (D-19's lead-docket-only boundary), not fixed here"

patterns-established:
  - "Per-conversation transaction isolation: each conversation gets its own get_session() context so a crash/exception mid-conversation only rolls back that one row, leaving prior/subsequent conversations' commits untouched (D-08 resumability)"

requirements-completed: [CORPUS-03, CORPUS-05]

coverage:
  - id: D1
    description: "import-convokit CLI subcommand with --term/--term-range (mutually exclusive, validated) and --corpus-dir (validated to exist before any file load)"
    requirement: "CORPUS-03"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::TestParseTermRange -k term_range"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_missing_corpus_dir_fails_fast_not_keyerror"
        status: pass
      - kind: other
        ref: "python -m pipeline import-convokit --help (exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Idempotent Case/Argument/CaseArgument/PipelineRun scaffolding at status=draft with Oyez external IDs (oyez_case_id/oyez_transcript_id), term_year sourced from cases.jsonl year (D-15), apolitical fields never persisted (T-29-02)"
    requirement: "CORPUS-03"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_creates_case_argument_caseargument_pipelinerun_entities"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_apolitical_fields_never_persisted_to_any_column"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_idempotent_rerun_creates_no_duplicate_arguments"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_malformed_conversation_flagged_not_aborting_term"
        status: pass
    human_judgment: false
  - id: D3
    description: "Bench/advocate speaker resolution into Person (oyez_speaker_id-first, full_name fallback with D-11 backfill) and ArgumentParticipant rows with correct side (advocate codes 0/1/2/3 -> RESPONDENT/PETITIONER/AMICUS/UNKNOWN; justice type -> BENCH), idempotent on (argument_id, raw_speaker_label)"
    requirement: "CORPUS-05"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_advocate_side_codes_map_onto_side_enum"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_existing_oyez_speaker_id_match_reuses_person_no_new_row"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_full_name_only_match_backfills_oyez_speaker_id"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_brand_new_speaker_creates_person_with_oyez_id_and_is_justice_false"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_justice_type_speaker_resolves_to_bench_side"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_rerun_creates_no_duplicate_argument_participants"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_resolve_and_link_participant_idempotent_check_before_insert"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-10
status: complete
---

# Phase 29 Plan 04: import-convokit core (CLI + entity scaffolding + speaker resolution) Summary

**New `import-convokit` term-batched CLI command that idempotently scaffolds draft Case/Argument/CaseArgument/PipelineRun rows and resolves bench/advocate speakers into Person/ArgumentParticipant rows, entirely from conversations.json/cases.jsonl/speakers.json with a provably apolitical field allowlist.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-10T11:15:00Z
- **Completed:** 2026-07-10T11:35:10Z
- **Tasks:** 3
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments
- `import-convokit` CLI subcommand: `--term`/`--term-range` (mutually exclusive, validated) + `--corpus-dir` (validated to exist before any file load), registered in `pipeline/__main__.py`
- Idempotent Case/Argument/CaseArgument/PipelineRun scaffolding: Argument dedup on `oyez_transcript_id`, Case dedup on `docket_number`, `term_year` sourced directly from cases.jsonl's `year` field (D-15, verified against a fixture where the argued_date's calendar year differs from the term), `PipelineRun.strategy="convokit_import"` created before any future utterance write path
- Bench/advocate speaker resolution: `Person.oyez_speaker_id`-first match, `full_name` fallback with ID backfill (D-11), `is_justice` sourced from speakers.json's authoritative `type` field (never a name-pattern guess), `ArgumentParticipant.side` mapped from advocate side codes 0/1/2/3 or BENCH for justices, idempotent on `(argument_id, raw_speaker_label)`
- Apolitical field stripping proven by test: raw source dicts carrying `win_side`/`votes_side`/`scdb_docket_id`/etc. never leak into any created row's columns

## Task Commits

Each task was committed atomically:

1. **Task 1: import-convokit CLI subcommand + term-range parsing + file-load orchestration skeleton** - `a5709a3e` (feat)
2. **Task 2: Per-argument entity creation — Case, Argument, CaseArgument, PipelineRun** - `be0189ea` (feat)
3. **Task 3: Speaker resolution — Person (oyez_speaker_id-first) + ArgumentParticipant with side** - `54ac5cf4` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `pipeline/commands/import_convokit.py` - `run_import_convokit(args)` orchestrator, `_parse_term_range`/`_resolve_terms`/`_resolve_corpus_dir` (Task 1), `_get_or_create_case`/`_parse_argued_date`/`_import_conversation` (Task 2), `_resolve_person`/`_resolve_and_link_participant`/`_is_justice_type` (Task 3)
- `pipeline/__main__.py` - registers the `import-convokit` subparser (`--term`/`--term-range`/`--corpus-dir`) and its dispatch branch
- `pipeline/tests/test_import_convokit_core.py` - 17 tests covering term-range parsing, entity creation, apolitical stripping, idempotency, and speaker/side resolution

## Decisions Made
- **Join key is `case_id` equality, not docket matching:** cases.jsonl rows carry their own `case_id` field with the same value as conversations.json's key/`case_id` attribute (confirmed via Plan 02's already-committed apolitical-extractor test fixtures — `case_id: "1955_71"` on both sides, vs. a differently-formatted `docket_no: "55-71"`). `pipeline.corpus.loader.load_cases` indexes by `docket_no` (needed separately for the `Case.docket_number` column), so `import_convokit.py` builds a secondary `case_id -> raw_case` index locally from `load_cases`' values rather than modifying the already-committed loader module.
- **Speaker-resolution scope for this plan:** conversations.json's `advocates` dict is the *only* per-conversation participant list available before Plan 05 streams `utterances.jsonl` (which is what actually reveals which bench justices spoke in a given conversation — no source file loaded by this plan lists bench participants per-conversation). The resolution/classification helpers (`_resolve_person`, `_resolve_and_link_participant`) are written generically — side is derived purely from `speakers.json`'s `type` field, independent of which dict supplied the id — so this plan wires them up for every id in the `advocates` dict now, and Plan 05 can call the identical functions unchanged once it discovers the real bench roster from utterances. This was validated directly with a test (`test_justice_type_speaker_resolves_to_bench_side`) that places a justice-typed speaker id in the advocates dict to prove the classification logic is correct regardless of caller.
- **Per-conversation transaction isolation:** `run_import_convokit` opens one `get_session()` per conversation (not one session for the whole term), wrapped in try/except, so a single bad/missing join or unexpected exception rolls back only that conversation and increments a `flagged` counter — sibling conversations in the same term are unaffected (T-29-05b).
- **`question_number` hardcoded to `1`:** matches the plan's literal instruction ("question_number default 1"). Not addressed: a re-argued historical case sharing the same docket across two conversations would collide with the `(source_docket, question_number)` UNIQUE constraint on the second one. This is a pre-existing gap in the plan's own scope (D-19 restricts this phase to lead-docket-only, single-question handling) — not fixed here, flagged for awareness if Plan 05/06 or a future audit surfaces it.

## Deviations from Plan

None — plan executed as written. The "join key" and "speaker-resolution scope" points above are implementation clarifications of genuinely ambiguous plan wording (RESEARCH.md's Pitfall 5 described the join only as "docket/case_id," and Task 3's "bench justices + advocates dict" phrasing presumes a bench-listing data source that does not exist in conversations.json/cases.jsonl at this plan's stage), not deviations from locked decisions (D-06/D-08/D-09/D-10/D-11/D-12/D-13/D-15/D-19 are all implemented exactly as specified).

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `import_convokit.py`'s per-term entity-creation and speaker-resolution logic is complete and independently reusable by Plan 05, which adds utterance streaming (`pipeline.corpus.loader.stream_utterances_for_conversation_ids`) and stage-direction splitting (`pipeline.corpus.stage_directions`), calling `_resolve_person`/`_resolve_and_link_participant` for the real per-conversation bench roster once utterances reveal it.
- No blockers. `data/corpus/` still has no real ConvoKit source files locally (expected — this plan's tests use synthetic fixtures per its own acceptance criteria); an operator must place the real files there before running `import-convokit` against real terms.

---
*Phase: 29-historical-corpus-import*
*Completed: 2026-07-10*

## Self-Check: PASSED

- FOUND: pipeline/commands/import_convokit.py
- FOUND: pipeline/tests/test_import_convokit_core.py
- FOUND: .planning/phases/29-historical-corpus-import/29-04-SUMMARY.md
- FOUND commit: a5709a3e
- FOUND commit: be0189ea
- FOUND commit: 54ac5cf4
