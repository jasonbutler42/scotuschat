---
phase: 28-dashboard
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, postgres, pytest]

# Dependency graph
requires:
  - phase: 24-people-argument-list-views
    provides: list_arguments()/list_jobs() unbounded list endpoints (PLIST-03) that this plan avoids reusing for counting
  - phase: 27-people-admin
    provides: list_people(is_justice, missing, tenure_gaps) directory query this plan delegates to for People/Justice stat aggregation
provides:
  - api/schemas/admin_dashboard.py — ArgumentStats, RecentDraft, PeopleStats, IncompletePerson, TenureGapJustice, PipelineStats, UtteranceCount Pydantic response models
  - get_argument_stats/get_recent_drafts/get_utterance_count in api/services/admin_arguments.py
  - get_pipeline_stats in api/services/admin_jobs.py
  - get_people_stats/get_incomplete_people/get_tenure_gap_justices in api/services/admin_people.py
  - api/tests/test_admin_dashboard_stats.py — DB-gated coverage of all seven functions
affects: [28-02 (router endpoints will call these functions), 28-03 (frontend dashboard consumes the router responses)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dedicated func.count()/func.max() COUNT/MAX queries instead of reusing unbounded list_*() functions for aggregation (corpus-scale DoS avoidance, ~7,800 Argument rows)"
    - "Delta-based test assertions (AFTER minus BEFORE baseline) for whole-table aggregates, to avoid brittleness against ambient corpus-scale rows"
    - "Marker-token-scoped top-5 list test assertions (unique run-scoped prefix sorted to rank first) instead of raw absolute-count assertions"

key-files:
  created:
    - api/schemas/admin_dashboard.py
    - api/tests/test_admin_dashboard_stats.py
    - .planning/phases/28-dashboard/deferred-items.md
  modified:
    - api/services/admin_arguments.py
    - api/services/admin_jobs.py
    - api/services/admin_people.py

key-decisions:
  - "get_tenure_gap_justices delegates to the existing list_people(is_justice=True, tenure_gaps=True) rather than duplicating the private gap_person_ids_query subquery"
  - "get_people_stats/get_incomplete_people call list_people(db) unfiltered and count/slice in Python — no new SQL filter surface added to list_people (D-05)"
  - "get_recent_drafts orders by Argument.id DESC, not resolved_at — Argument has no created_at column (Pitfall 3)"
  - "get_utterance_count is a plain module-level function in admin_arguments.py (Utterance already imported there) rather than a new admin_utterances module for a single count"

patterns-established:
  - "Whole-table dashboard aggregates always use func.count()/func.max() at the SQL layer, never fetch-all-and-count-in-Python, even when a corpus-scale table is involved"
  - "DB-gated tests against a corpus-populated shared dev DB assert deltas and marker-scoped subsets, never raw absolute totals"

requirements-completed: [DASH-01, DASH-03]

coverage:
  - id: D1
    description: "get_argument_stats returns total/published/draft/unpublished counts via one grouped COUNT query, excluding PIPELINE-status rows"
    requirement: "DASH-01"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_dashboard_stats.py#test_get_argument_stats_delta_and_pipeline_exclusion"
        status: pass
    human_judgment: false
  - id: D2
    description: "get_recent_drafts returns at most 5 DRAFT arguments ordered by Argument.id DESC, with no age threshold"
    requirement: "DASH-03"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_dashboard_stats.py#test_get_recent_drafts_caps_at_five_ordered_by_id_desc"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_dashboard_stats.py#test_get_recent_drafts_no_marker_rows_when_none_seeded"
        status: pass
    human_judgment: false
  - id: D3
    description: "get_people_stats/get_incomplete_people compute People stat-card counts and a combined top-5 Needs-Attention sub-list without adding a new SQL filter mode to list_people"
    requirement: "DASH-01"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_dashboard_stats.py#test_get_people_stats_delta"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_dashboard_stats.py#test_get_incomplete_people_combined_top_five"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_dashboard_stats.py#test_get_incomplete_people_no_marker_when_all_complete"
        status: pass
    human_judgment: false
  - id: D4
    description: "get_tenure_gap_justices delegates to list_people(is_justice=True, tenure_gaps=True), capped at 5"
    requirement: "DASH-03"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_dashboard_stats.py#test_get_tenure_gap_justices_combined_top_five"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_dashboard_stats.py#test_get_tenure_gap_justices_no_marker_when_tenure_covers_argued_date"
        status: pass
    human_judgment: false
  - id: D5
    description: "get_pipeline_stats returns a 30-day recent_count plus an unbounded last_activity_at MAX"
    requirement: "DASH-01"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_dashboard_stats.py#test_get_pipeline_stats_30_day_window_and_last_activity"
        status: pass
    human_judgment: false
  - id: D6
    description: "get_utterance_count returns a total Utterance row count regardless of parent argument status"
    requirement: "DASH-01"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_dashboard_stats.py#test_get_utterance_count_counts_every_status"
        status: pass
    human_judgment: false
  - id: D7
    description: "api/schemas/admin_dashboard.py defines all seven response models with no apolitical-field leakage"
    verification:
      - kind: unit
        ref: "python -c \"from api.schemas.admin_dashboard import *\" (schema-import-ok)"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-07-11
status: complete
---

# Phase 28 Plan 01: Dashboard Backend Data Layer Summary

**Seven read-only COUNT/MAX/LIMIT aggregation service functions across three admin service files, plus a new Pydantic schema module and DB-gated test suite proving their I/O contracts against the corpus-scale (~7,800 row) dev database.**

## Performance

- **Duration:** ~30 min
- **Completed:** 2026-07-11
- **Tasks:** 3
- **Files modified:** 5 (3 new, 2 modified in addition to the 1 new schema and 1 new test file already counted)

## Accomplishments
- New `api/schemas/admin_dashboard.py` with seven plain BaseModel response shapes (ArgumentStats, RecentDraft, PeopleStats, IncompletePerson, TenureGapJustice, PipelineStats, UtteranceCount) — no apolitical-field leakage (no win/vote-outcome or external case-database identifier fields)
- `get_argument_stats`, `get_recent_drafts`, `get_utterance_count` added to `admin_arguments.py` — dedicated grouped-COUNT / LIMIT / whole-table-COUNT queries, never reusing the unbounded `list_arguments()`
- `get_pipeline_stats` added to `admin_jobs.py` — 30-day recent_count plus an unbounded last_activity_at MAX
- `get_people_stats`, `get_incomplete_people`, `get_tenure_gap_justices` added to `admin_people.py`, all delegating to the existing `list_people()` with zero changes to its signature (D-05)
- `api/tests/test_admin_dashboard_stats.py`: 11 DB-gated tests covering all seven functions, using delta-based assertions for whole-table aggregates and marker-token-scoped assertions for top-5 list functions — designed specifically to remain correct against the corpus-scale dev DB (~7,800 Argument rows, ~328 Person rows) rather than assuming an empty table

## Task Commits

Each task was committed atomically:

1. **Task 1: Create api/schemas/admin_dashboard.py Pydantic response module** - `e9011757` (feat)
2. **Task 2: Add argument, pipeline, and utterance stat service functions** - `b39ab167` (feat)
3. **Task 3: Add people stat service functions + DB-gated test suite** - `a2f2eec9` (feat)

**Plan metadata:** commit pending (see below)

## Files Created/Modified
- `api/schemas/admin_dashboard.py` - new: 7 Pydantic response models for the dashboard stat cards + Needs-Attention sub-lists
- `api/services/admin_arguments.py` - added `get_argument_stats`, `get_recent_drafts`, `get_utterance_count`
- `api/services/admin_jobs.py` - added `get_pipeline_stats`
- `api/services/admin_people.py` - added `get_people_stats`, `get_incomplete_people`, `get_tenure_gap_justices`
- `api/tests/test_admin_dashboard_stats.py` - new: 11 DB-gated tests covering all seven functions
- `.planning/phases/28-dashboard/deferred-items.md` - new: logs 28 pre-existing, unrelated DB-gated test failures found during full-suite verification

## Decisions Made
- `get_tenure_gap_justices` delegates to `list_people(is_justice=True, tenure_gaps=True)` rather than duplicating the private `gap_person_ids_query` subquery (that local variable is not exported from `list_people`)
- `get_people_stats`/`get_incomplete_people` call `list_people(db)` unfiltered and count/slice in Python — no new SQL "any missing field" filter mode added to `list_people` (D-05 upheld)
- `get_recent_drafts` orders by `Argument.id.desc()`, not `resolved_at` — `Argument` has no `created_at` column (Pitfall 3 from RESEARCH.md)
- `get_utterance_count` lives in `admin_arguments.py` (where `Utterance` is already imported) rather than a new single-function `admin_utterances.py` module
- Test suite uses delta-based assertions (AFTER value minus a BEFORE baseline captured pre-seed) for every whole-table aggregate, and unique run-scoped marker-token prefixes for every top-5 list function, specifically because the dev DB already holds ~7,800 corpus-imported Argument/Utterance rows and ~328 Person rows (confirmed empirically: 328/328 people are currently "incomplete", and 7 ambient tenure-gap justices already exist) — a literal `== N` absolute-count or "empty list" assertion would be immediately false or flaky

## Deviations from Plan

None — plan executed exactly as written. One documentation-only self-correction: Task 1's initial docstring for `admin_dashboard.py` described the apolitical constraint using the literal forbidden substrings (`win_side`, `votes_side`, `scdb_docket_id`) as prose examples of what's excluded, which technically violated the plan's own source-assertion acceptance criterion ("file contains ... none of the strings win_side, votes_side, scdb_docket_id"). Reworded the docstring to describe the same constraint without using those literal substrings, before the Task 1 commit — no functional change, and the file's `Write` was not yet committed when this was caught.

## Issues Encountered

While verifying with a full `pytest -q` run (all `testpaths`, DB configured), 28 tests failed across files this plan never touches (`pipeline/tests/test_ingest.py`, `test_parse.py`, `test_pipeline_run.py`, `test_resolve.py`, `test_seed_aliases.py`, and `api/tests/test_admin_arguments_service.py`, `test_admin_jobs_phase25.py`, `test_admin_jobs_service.py`, `test_admin_jobs_stats.py`, `test_argument_oyez_field.py`, `test_arguments.py`). Confirmed pre-existing and out of this plan's scope:
- `test_admin_jobs_stats.py`'s 2 failures were reproduced *before any 28-01 code was written* (first DB-availability check of this execution run) — caused by a `NotNullViolationError` on `utterances.strategy` in an old test-seeding helper.
- `test_admin_arguments_service.py::test_publish_argument_from_draft_writes_one_published_log_row` fails because its own fixture seeds a bare `Argument` with no `Case`/`CaseArgument`, so `get_argument_detail` (called internally by `publish_argument`) returns `None`.
- The rest follow the same shape: tests assuming a clean/empty dev DB (fixed IDs, or committing rows directly without a rollback fixture) now collide with the corpus-scale dev DB populated by Phases 29/30.

Logged to `.planning/phases/28-dashboard/deferred-items.md`; overlaps the already-tracked backlog item 999.19 ("tests leak real Person/Argument rows into shared dev DB"). Not fixed here per the SCOPE BOUNDARY rule (no file this plan modifies is implicated).

This plan's own new test file, `api/tests/test_admin_dashboard_stats.py`, passes 11/11 with `DATABASE_URL` set and skips 11/11 cleanly with it unset.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 28-02 can now add router endpoints (`GET /arguments/stats`, `/people/stats`, `/jobs/stats`, `/utterances/count`, plus the three Needs-Attention sub-list endpoints) that thinly wrap these seven service functions in the seven new Pydantic response models.
- Plan 28-03 (frontend) can build `+page.server.ts`'s sequential-fetch `load()` against those router endpoints once 28-02 lands.
- No blockers. The 28 pre-existing unrelated test failures logged in `deferred-items.md` do not block Plan 28-02/28-03 — none of the functions or files they will touch are among the failing tests.

---
*Phase: 28-dashboard*
*Completed: 2026-07-11*

## Self-Check: PASSED

- FOUND: api/schemas/admin_dashboard.py
- FOUND: api/tests/test_admin_dashboard_stats.py
- FOUND: .planning/phases/28-dashboard/28-01-SUMMARY.md
- FOUND: .planning/phases/28-dashboard/deferred-items.md
- FOUND commit: e9011757
- FOUND commit: b39ab167
- FOUND commit: a2f2eec9
