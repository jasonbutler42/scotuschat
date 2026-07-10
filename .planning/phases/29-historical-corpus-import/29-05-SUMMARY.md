---
phase: 29-historical-corpus-import
plan: 05
subsystem: pipeline
tags: [sqlalchemy, asyncpg, convokit, streaming, stage-directions, apolitical-allowlist]

# Dependency graph
requires:
  - phase: 29-historical-corpus-import (Plan 02)
    provides: pipeline/corpus/loader.py stream_utterances_for_conversation_ids, pipeline/corpus/stage_directions.py detect_stage_direction
  - phase: 29-historical-corpus-import (Plan 04)
    provides: import_convokit.py CLI scaffolding, idempotent Case/Argument/CaseArgument/PipelineRun creation, _resolve_person/_resolve_and_link_participant speaker-resolution helpers
provides:
  - "Streaming utterance import in run_import_convokit: one Utterance row per ConvoKit turn (D-18), \\n boundaries preserved verbatim"
  - "Stage-direction row-splitting (D-16/D-17) delegated to stage_directions.detect_stage_direction, including inline-marker mid-turn splitting"
  - "Per-conversation speaker-resolution cache (resolved_participants) shared between advocates-dict resolution and utterance-speaker resolution"
  - "Per-term/rollup summary report (D-14): arguments/cases/utterances/stage-direction counts, people created/matched, speakers flagged, conversations/rows errored"
affects: [29-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One streaming pass over utterances.jsonl per term (never the whole 900MB file), grouped into an in-memory conversation_id -> [turn, ...] index held only for the current term (RESEARCH.md Pattern 3 option (b))"
    - "\\n-segment splitting + stage-direction reclassification: contiguous non-marker segments rejoin into one row (D-18 default); each detected marker segment splits into its own adjacent row (D-16), all via detect_stage_direction (no re-implemented regex)"
    - "Per-conversation resolved_participants cache shared between the advocates-dict loop and the utterance-import loop, so a speaker with many turns is resolved via a DB round trip exactly once per conversation, not once per turn"

key-files:
  created:
    - pipeline/tests/test_import_convokit_utterances.py
  modified:
    - pipeline/commands/import_convokit.py
    - pipeline/tests/test_import_convokit_core.py

key-decisions:
  - "Turn ordering is the order rows are encountered in the per-term streaming pass (file order for a given conversation_id), not a separately-derived timestamp/reply-to chain -- ConvoKit's utterances.jsonl has no documented alternative ordering signal, and ordering fixtures in tests confirm sequence increments correctly from stream order"
  - "Speaker resolution is cached per-conversation (resolved_participants dict) and shared between the advocates-dict loop (Task 3, Plan 04) and the new utterance-speaker loop (Task 1) -- without this, a speaker with many turns would re-resolve (extra DB round trips) and inflate the people-matched counter once per turn instead of once per conversation"
  - "Inline \\n-segment stage-direction splitting: a turn whose \\n-delimited segments mix spoken text with a whole-segment marker is split into adjacent rows (marker isolated, spoken remainder(s) keep their own row/rows) -- this reconciles D-16 (split markers) with D-18 (one row per turn by default) using only detect_stage_direction's existing whole-token check per segment, no new regex"
  - "Counters conversations_errored/speakers_flagged/people_created/people_matched are new/renamed (from Plan 04's single undifferentiated 'flagged' counter) to satisfy D-14's richer per-batch summary; all counter increments use counters.get(key, 0) so a caller passing a partial counters dict never raises KeyError"

requirements-completed: [CORPUS-06, CORPUS-07, CORPUS-08]

coverage:
  - id: D1
    description: "Each ConvoKit turn becomes one Utterance row with \\n-delimited segment boundaries preserved verbatim in Text (D-18)"
    requirement: "CORPUS-07"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_multi_segment_turn_stored_as_one_row_newline_preserved"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_stage_direction_delegated_to_detect_stage_direction_no_regex"
        status: pass
    human_judgment: false
  - id: D2
    description: "Detected stage directions become separate Utterance rows with is_stage_direction=true and raw_speaker_label=None, in transcript sequence, including inline markers mixed with spoken segments (D-16/D-17)"
    requirement: "CORPUS-06"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_whole_turn_stage_direction_produces_separate_row"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_inline_marker_segment_splits_spoken_remainder_into_own_rows"
        status: pass
    human_judgment: false
  - id: D3
    description: "Utterance streaming never loads utterances.jsonl fully into memory; one streaming pass per term, monotonic sequence unique per (argument_id, pipeline_run_id), pipeline_run_id always non-null; malformed rows flagged not crashed"
    requirement: "CORPUS-07"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_every_utterance_has_pipeline_run_id_and_unique_sequence"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_malformed_utterance_row_flagged_not_crashing_import"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_repeat_speaker_across_many_turns_resolved_once_no_duplicate_participant"
        status: pass
    human_judgment: false
  - id: D4
    description: "Per-batch summary report printed at the end of each term/batch run: term year, created/skipped/flagged/errored counts; broken cases.jsonl joins counted as errored rather than crashing the batch (D-14)"
    requirement: "CORPUS-08"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_summary_prints_term_year_and_core_counts"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_broken_case_join_counted_as_errored_not_crashing_batch"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-07-10
status: complete
---

# Phase 29 Plan 05: import-convokit utterance streaming, stage-direction splitting, and batch summary Summary

**Streams ConvoKit utterances.jsonl one term at a time (never the full 900MB file) into Utterance rows with `\n` boundaries preserved verbatim, splits curated-vocabulary stage-direction markers (including inline mid-turn ones) into their own rows via the existing `detect_stage_direction` helper, and prints a per-term/rollup summary of created/skipped/matched/flagged/errored counts.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-07-10T11:40:00Z
- **Completed:** 2026-07-10T12:25:00Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- `run_import_convokit` now streams `utterances.jsonl` once per term via `pipeline.corpus.loader.stream_utterances_for_conversation_ids`, filtered to that term's conversation_id set and grouped into an in-memory `conversation_id -> [turn, ...]` index (never the whole 900MB file, T-29-03)
- `_split_turn_into_rows` splits a turn's `\n`-delimited segments, classifying each via `stage_directions.detect_stage_direction`: contiguous non-marker segments rejoin into one row (D-18 default, verbatim `\n` preservation), each marker segment becomes its own adjacent row (D-16), including the mixed case where spoken text surrounds an inline marker
- `_import_utterances` writes one `Utterance` row per resulting split row, with a monotonic `sequence` per `(argument_id, pipeline_run_id)`, `pipeline_run_id` always non-null (T-29-09), and per-row validation (missing `conversation_id`/`text`/`speaker`) counted rather than raising `KeyError` (V5)
- Speaker resolution for utterance turns reuses Plan 04's `_resolve_and_link_participant`/`_resolve_person` unchanged, now via a per-conversation `resolved_participants` cache shared with the advocates-dict loop so a repeat speaker across many turns is resolved once, not once per turn
- Per-term/rollup summary report (`_print_summary`) covers: arguments created, arguments skipped (already imported), cases created, utterances created, stage-direction utterances created, people created, people matched (reused), speakers flagged, conversations errored, utterance rows errored — printed per term, plus a final rollup block when `--term-range` spans more than one term

## Task Commits

Tasks 1 (utterance streaming + stage-direction splitting) and 2 (per-batch summary report) were committed together in a single commit rather than two separate ones — both tasks rework the same shared counters and functions (`_resolve_person`, `_resolve_and_link_participant`, `_import_conversation`, `run_import_convokit`) in `pipeline/commands/import_convokit.py`; splitting them into two commits would have required error-prone manual reverting/reapplying rather than a clean per-hunk split. See "Deviations from Plan" below.

1. **Task 1 + Task 2: utterance streaming, stage-direction splitting, and per-batch summary report** - `edd4443e` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `pipeline/commands/import_convokit.py` - Added `_split_turn_into_rows`, `_import_utterances` (Task 1); `_new_counters`, `_accumulate_counters`, `_print_summary` (Task 2); wired streaming + `resolved_participants` cache into `_import_conversation`/`run_import_convokit`; renamed the undifferentiated `flagged` counter into `speakers_flagged`/`conversations_errored`; added `people_created`/`people_matched` tracking to `_resolve_person`
- `pipeline/tests/test_import_convokit_utterances.py` - 9 new tests: `\n` preservation, whole-turn and inline-marker stage-direction splitting, no-reimplemented-regex delegation, `pipeline_run_id`/sequence invariants, malformed-row handling, repeat-speaker caching, and the two summary-report tests
- `pipeline/tests/test_import_convokit_core.py` - Fixed `_write_corpus_fixture` to also write an empty `utterances.jsonl` (Rule 3 — see Deviations)

## Decisions Made
- **Streaming grouped by term, not by conversation:** a single pass over `utterances.jsonl` per term (filtered to that term's `wanted_ids`, grouped into an in-memory dict) rather than one pass per conversation — re-scanning the 900MB file per conversation (thousands of times for the full corpus) would be far more expensive than one pass per term (~65 total passes), matching RESEARCH.md Pattern 3 option (b).
- **`\n`-segment splitting reconciles D-16 and D-18 via a single algorithm:** split on `\n`, classify each segment with `detect_stage_direction`, rejoin contiguous non-marker segments — this makes the "whole turn is a marker" case and the "turn has no markers at all" case both fall out of the same code path as the "inline marker mixed with spoken segments" case, with zero re-implemented classification logic.
- **Per-conversation `resolved_participants` cache:** without it, a speaker who spoke 50 times in one conversation would trigger 50 separate `_resolve_and_link_participant` calls, each hitting the DB and incrementing `people_matched` — inflating the D-14 summary's people counts and adding unnecessary DB round trips at corpus scale. The cache (seeded from the advocates-dict loop, extended by the utterance loop) guarantees exactly one resolution per speaker per conversation.
- **Counter rename/split (`flagged` -> `speakers_flagged`/`conversations_errored`, plus new `people_created`/`people_matched`/`utterances_created`/`stage_direction_utterances_created`/`utterance_rows_errored`):** Plan 04 left a single undifferentiated `flagged` counter; D-14 explicitly asks for separate categories ("speakers flagged" vs. "cases/conversations errored") in the summary. All increments use `counters.get(key, 0) + 1` so any caller (including Plan 04's own unit test that constructs a bare `{"participants_created": 0, "flagged": 0}` dict) never raises `KeyError` even when it omits a key this plan introduced.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed `test_import_convokit_core.py`'s corpus fixture helper to include a required `utterances.jsonl`**
- **Found during:** Task 1 (adding `utterances.jsonl` to `run_import_convokit`'s required-file validation)
- **Issue:** This plan's `run_import_convokit` now validates `utterances.jsonl` exists (alongside `conversations.json`/`cases.jsonl`/`speakers.json`) before any file load. Plan 04's `_write_corpus_fixture` helper in `test_import_convokit_core.py` only wrote the first three files, so all 17 of Plan 04's DB-dependent tests would start raising `FileNotFoundError` — a regression this plan's own required-file check directly caused.
- **Fix:** Added a one-line write of an empty `utterances.jsonl` to `_write_corpus_fixture` (Plan 04's tests don't exercise utterance import, so zero turns is correct for them).
- **Files modified:** `pipeline/tests/test_import_convokit_core.py`
- **Verification:** All 17 of Plan 04's tests still pass (`pytest pipeline/tests/test_import_convokit_core.py -q` — 17 passed).
- **Committed in:** `edd4443e` (part of the combined Task 1+2 commit)

**2. [Rule 1 - Bug] Cached per-conversation speaker resolution to prevent inflated summary counts / redundant DB round trips**
- **Found during:** Task 1 (writing the utterance-import loop)
- **Issue:** An initial implementation called `_resolve_and_link_participant` once per turn. A speaker who spoke in many turns within one conversation would trigger a fresh DB-backed resolution (and a `people_matched` counter increment) on every single turn instead of once per conversation — both an efficiency problem at corpus scale and an accuracy problem for D-14's summary counts.
- **Fix:** Added a `resolved_participants: dict[str, ArgumentParticipant]` cache, seeded by the advocates-dict loop and shared with (and extended by) the utterance-import loop, so each speaker is resolved via a DB round trip exactly once per conversation.
- **Files modified:** `pipeline/commands/import_convokit.py`
- **Verification:** New test `test_repeat_speaker_across_many_turns_resolved_once_no_duplicate_participant` asserts exactly one `Person` row and one `ArgumentParticipant` row for a speaker appearing in 5 turns of the same conversation.
- **Committed in:** `edd4443e` (part of the combined Task 1+2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking regression fix, 1 bug fix for accuracy/efficiency)
**Impact on plan:** Both fixes were necessary for correctness (no test regressions, accurate summary counts); no scope creep beyond this plan's declared objective.

## Issues Encountered

Both plan tasks (utterance streaming/splitting and the summary report) ended up reworking the exact same shared counters and functions in `pipeline/commands/import_convokit.py` (Plan 04's `_resolve_person`/`_resolve_and_link_participant`, plus the new `_import_conversation`/`run_import_convokit` wiring), so they were committed together in a single commit rather than as two separate atomic task commits. Splitting them after the fact would have required manually reverting and reapplying interleaved edits to the same functions — judged higher-risk than committing the intertwined, fully-tested result as one unit. This is disclosed here rather than silently deviating from the "commit each task" norm.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `import_convokit.py`'s utterance-import path is complete: streaming, `\n` preservation, stage-direction splitting, and the summary report all work end-to-end against synthetic fixtures. `data/corpus/` still has no real ConvoKit source files locally (expected — tests use synthetic fixtures per D-18/RESEARCH.md convention); an operator must place the real files there before running `import-convokit` against real terms.
- This closes CORPUS-03's utterance path (Phase 29's declared boundary for Plan 05). Plan 06 (Attributions page + per-argument attribution note) is unaffected by this plan's changes and can proceed independently.
- No blockers.

---
*Phase: 29-historical-corpus-import*
*Completed: 2026-07-10*

## Self-Check: PASSED

- FOUND: pipeline/commands/import_convokit.py
- FOUND: pipeline/tests/test_import_convokit_utterances.py
- FOUND: pipeline/tests/test_import_convokit_core.py
- FOUND: .planning/phases/29-historical-corpus-import/29-05-SUMMARY.md
- FOUND commit: edd4443e
