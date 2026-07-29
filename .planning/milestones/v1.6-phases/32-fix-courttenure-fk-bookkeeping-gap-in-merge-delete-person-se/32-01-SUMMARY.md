---
phase: 32-fix-courttenure-fk-bookkeeping-gap-in-merge-delete-person-se
plan: 01
subsystem: api
tags: [sqlalchemy, pydantic, fastapi, fk-integrity, admin-people]

# Dependency graph
requires:
  - phase: 27-people-admin
    provides: CourtTenure CRUD in the People editor, which made the pre-existing merge/delete FK gap newly reachable
provides:
  - MergePreview.tenures required field
  - CourtTenure counted in get_merge_preview, transferred in merge_people, and checked (blocking) in delete_person_if_orphan
affects: [32-02, admin-people-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns: [5-table FK loop pattern (extends existing 4-table for-loop-over-model-tuples in admin_people.py)]

key-files:
  created: []
  modified:
    - api/schemas/admin_people.py
    - api/services/admin_people.py
    - api/tests/test_admin_people_merge.py

key-decisions:
  - "CourtTenure joins the blocking tier (Utterance/CaseAppearance/ArgumentParticipant), not the SpeakerAlias intrinsic-unconditional-delete tier (D-01)"
  - "New field/key name is 'tenures' (matches existing tenure_coverage/tenure_gaps naming convention in the module), not 'court_tenure'"

patterns-established:
  - "Pattern: FK bookkeeping tables are enumerated as a `for key, model, col in [...]` (or `for model, col in [...]`) tuple list inside get_merge_preview/merge_people/delete_person_if_orphan; adding a table is a one-line tuple append, never a new code path"

requirements-completed: [PADM-05]

coverage:
  - id: D1
    description: "get_merge_preview returns a counts dict whose 'tenures' key reflects the source person's CourtTenure row count"
    requirement: "PADM-05"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_people_merge.py#test_get_merge_preview_counts_tenures"
        status: unknown
      - kind: unit
        ref: "api/tests/test_admin_people_merge.py#test_merge_schemas_import"
        status: pass
    human_judgment: false
  - id: D2
    description: "merge_people reassigns every CourtTenure row's person_id from source to target inside the single atomic transaction, no IntegrityError"
    requirement: "PADM-05"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_people_merge.py#test_merge_people_transfers_tenures"
        status: unknown
    human_judgment: false
  - id: D3
    description: "delete_person_if_orphan returns False (router -> 409) when the person has >=1 CourtTenure row"
    requirement: "PADM-05"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_people_merge.py#test_delete_person_if_orphan_blocked_by_tenure"
        status: unknown
    human_judgment: false
  - id: D4
    description: "delete_person_if_orphan still returns True and deletes the person when zero CourtTenure rows exist (no regression)"
    requirement: "PADM-05"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_people_merge.py#test_delete_person_if_orphan_deletes_orphaned_person"
        status: unknown
    human_judgment: false

duration: 15min
completed: 2026-07-13
status: complete
---

# Phase 32 Plan 01: Backend CourtTenure FK Bookkeeping Fix Summary

**Extended MergePreview and all three admin-people service functions (get_merge_preview, merge_people, delete_person_if_orphan) to count, transfer, and block on CourtTenure rows, closing the unhandled-IntegrityError gap on merging/deleting Justices with tenure history.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-13T13:51:00-05:00 (approx, based on first task commit)
- **Completed:** 2026-07-13T13:53:40-05:00
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `MergePreview` now has a required `tenures: int` field (5th field), automatically picked up by the router's `MergePreview(**counts)` dict unpacking — no router change needed
- `get_merge_preview` counts `court_tenures` rows for the source person as the 5th entry in its existing table loop
- `merge_people` transfers `court_tenures.person_id` from source to target inside the same single-`db.commit()` atomic transaction as the other 4 tables — no second commit added
- `delete_person_if_orphan` now blocks (returns `False` -> 409) when the person has `>=1` CourtTenure row, joining the blocking tier alongside Utterance/CaseAppearance/ArgumentParticipant; the SpeakerAlias intrinsic-unconditional-delete step is untouched
- Test suite mirrors the existing 4-table rigor with 3 new DB-guarded tests plus an updated schema-construction test for the 5th table

## Task Commits

Each task was committed atomically:

1. **Task 1: Add tenures to MergePreview schema and all three service FK loops** - `3f9d2059` (feat)
2. **Task 2: Mirror the 4-table test coverage for CourtTenure (5th table)** - `73f721d9` (test)

**Plan metadata:** (pending — final docs commit follows this SUMMARY)

## Files Created/Modified
- `api/schemas/admin_people.py` - `MergePreview` gains required `tenures: int` field
- `api/services/admin_people.py` - `CourtTenure` appended to the FK loops in `get_merge_preview` (counting tier), `merge_people` (transfer tier), and `delete_person_if_orphan` (blocking tier); docstrings updated 4→5 tables
- `api/tests/test_admin_people_merge.py` - `test_merge_schemas_import` updated with `tenures=`; new tests `test_get_merge_preview_counts_tenures`, `test_delete_person_if_orphan_blocked_by_tenure`, `test_merge_people_transfers_tenures`

## Decisions Made
- Field/key name `tenures` (not `court_tenure`) — matches the module's existing `tenure_coverage`/`tenure_gaps` naming convention (Claude's Discretion per 32-CONTEXT.md).
- CourtTenure placed in the blocking tier of `delete_person_if_orphan`, not the SpeakerAlias unconditional-delete tier — locked by D-01 in 32-CONTEXT.md and Success Criteria #3/#4.
- New DB-guarded tests insert `court_tenures` rows using only the `person_id` column (the sole `NOT NULL` column on the table besides the PK), matching the raw-SQL insert style already used elsewhere in the test file.
- Test cleanup order in all three new DB tests deletes the `court_tenures` row(s) before the `people` row, since the FK has no `ON DELETE CASCADE`.

## Deviations from Plan

None - plan executed exactly as written. Both tasks matched the plan's `<action>` and `<read_first>` guidance exactly (one-line tuple appends to each of the 3 existing loops, one new schema field, mirrored test shapes).

## Issues Encountered

- `python -c "from api.schemas..."` initially failed with `ModuleNotFoundError: No module named 'sqlalchemy'` when run with the system `python` — the project's virtualenv (`.venv/Scripts/python.exe`, matching `config.json`'s `workflow.test_command`) was required instead. Not a plan deviation, just an environment-invocation correction before running the verification commands.
- `DATABASE_URL` is not set in the shell environment used for this execution, so all 9 DB-guarded tests in `test_admin_people_merge.py` (including the 3 new CourtTenure tests) skipped cleanly rather than running against a live database. This matches the plan's own acceptance criteria ("DB-guarded tests either pass against the live dev DB or skip cleanly; no collection or assertion errors") — the non-DB tests (`test_merge_schemas_import`, `test_merge_people_same_id_raises_value_error`, etc.) ran and passed. The `coverage` block above marks the DB-guarded verification entries `status: unknown` rather than `pass` to reflect this honestly; an operator running the suite with `DATABASE_URL` configured against the dev DB should re-run `pytest api/tests/test_admin_people_merge.py -q` to get a live pass signal on the 3 new tests.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Backend FK bookkeeping gap is closed for all 3 service functions; `PADM-05` requirement's backend surface is complete.
- Plan 02 (frontend sync, per 32-CONTEXT.md D-05) can proceed independently — it depends on the `tenures` key now existing in the `MergePreview` response contract, which this plan delivers.
- Recommend an operator run the full test suite with `DATABASE_URL` pointed at the dev/staging DB at least once before closing out the phase, to get a live pass on the 3 new DB-guarded tests (currently skip-verified only in this environment).

---
*Phase: 32-fix-courttenure-fk-bookkeeping-gap-in-merge-delete-person-se*
*Completed: 2026-07-13*

## Self-Check: PASSED

- FOUND: api/schemas/admin_people.py
- FOUND: api/services/admin_people.py
- FOUND: api/tests/test_admin_people_merge.py
- FOUND: 3f9d2059 (Task 1 commit)
- FOUND: 73f721d9 (Task 2 commit)
