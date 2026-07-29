---
phase: 33-metadata-update-unique-constraint-guard
plan: 02
subsystem: pipeline
tags: [sqlalchemy, postgresql, uniqueness, ingest, convokit, parse]
requires:
  - phase: 33-01
    provides: shared argument pair lookup and named constraint classifier
provides:
  - Exact named-constraint handling for all offline argument writers
  - Race-safe conditional parse docket metadata fill
affects: [pipeline-ingest, corpus-import, transcript-parse]
tech-stack:
  added: []
  patterns: [shared offline constraint classification, conditional pair precheck]
key-files:
  created: []
  modified: [pipeline/commands/ingest.py, pipeline/commands/import_convokit.py, pipeline/commands/parse.py, pipeline/tests/test_ingest.py, pipeline/tests/test_import_convokit_core.py, pipeline/tests/test_parse.py]
key-decisions:
  - "Offline duplicate recovery is entered only for uq_arguments_source_docket_question; unrelated integrity failures propagate without duplicate wording or counters."
  - "Parse combines an extracted docket with the stored question, excludes the current row, and flushes at the conditional update boundary for race classification."
requirements-completed: [PIPE-27]
coverage:
  - id: D1
    description: "Ingest and ConvoKit preserve channel-specific duplicate behavior only for the named pair constraint."
    requirement: PIPE-27
    verification:
      - kind: unit
        ref: "pipeline/tests/test_ingest.py"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Parse pre-checks the concrete final pair with self exclusion and distinguishes the named race from other integrity failures."
    requirement: PIPE-27
    verification:
      - kind: unit
        ref: "pipeline/tests/test_parse.py"
        status: pass
    human_judgment: false
duration: 8min
completed: 2026-07-14
status: complete
---

# Phase 33 Plan 02: Offline Writer Constraint Guard Summary

**All offline argument writers now use the shared concrete-pair semantics and reserve duplicate recovery for the exact PostgreSQL constraint.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-07-14T12:57:00Z
- **Completed:** 2026-07-14T13:05:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Narrowed ingest's existing duplicate `ValueError` to the named docket/question constraint.
- Preserved ConvoKit rollback and conflict-counter behavior while allowing unrelated integrity failures to escape the duplicate path.
- Added parse's final-pair pre-check, self exclusion, NULL-compatible lookup, and rollback-first named race classification.

## Task Commits

1. **Task 1: Narrow ingest duplicate handling** - `d59aab17`
2. **Task 2: Preserve ConvoKit counter behavior with exact classification** - `56fcccf5`
3. **Task 3: Guard parse conditional docket updates** - `bc8b867d`

## Decisions Made

- Reused the API-neutral helper directly; no HTTP response structures or wording enter pipeline commands.
- Forced parse's conditional update to flush at its smallest safe boundary so a database race is classified before later work.

## Deviations from Plan

None.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

Phase 33 implementation is complete and ready for phase verification.
