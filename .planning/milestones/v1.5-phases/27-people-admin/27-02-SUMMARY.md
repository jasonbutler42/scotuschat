---
phase: 27-people-admin
plan: 02
subsystem: api
tags: [sqlalchemy, fastapi, admin-service]

# Dependency graph
requires:
  - phase: 27-people-admin
    plan: 01
    provides: Person.birthdate column, PersonListItem.argument_count/tenure_coverage/has_tenure_gap fields, role_id/role_name removal from admin_people schemas
provides:
  - "list_people(db, is_justice=None, missing=None, tenure_gaps=False) — Bench/Advocate tab filter, single-field missing filter, per-tab columns"
  - "_missing_fields(person, tenure_count) — per-is_justice field-label sets, no role check"
  - "_tenure_coverage(tenures) — display-string helper for the Bench tenure_coverage column"
affects: [27-03-plan, 27-04-plan]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single grouped prefetch query (dict[int, list[CourtTenure]] / dict[int, int]) built once per list_people call, reused across _missing_fields/tenure_coverage/argument_count/has_tenure_gap annotation — no per-person N+1 queries"
    - "missing filter routes through an explicit Python dict allow-list of known field labels before touching SQLAlchemy .where() (T-27-03) — unrecognized values apply no filter, never reach string interpolation"

key-files:
  modified:
    - api/services/admin_people.py
    - api/tests/test_admin_people_schemas_service.py

key-decisions:
  - "_missing_fields signature changed to (person, tenure_count) rather than a dict-of-counts, matching the plan's stated flexibility ('planner leaves the exact parameter shape to the executor') — list_people still builds one grouped prefetch dict and does the per-person lookup before calling the helper"
  - "has_tenure_gap reuses the exact BENCH-side gap-detection subquery from the tenure_gaps filter, keyed on ArgumentParticipant.side == BENCH — this is independent of the row's current Person.is_justice flag, matching the plan's instruction to 'reuse the same gap logic as the tenure_gaps filter' verbatim rather than re-deriving a is_justice-scoped variant"
  - "argument_count is populated only when not person.is_justice (None for Bench rows) — a plain conditional on the already-loaded is_justice attribute, no extra query needed to decide"
  - "Fixed the 6 direct _missing_fields unit tests in test_admin_people_schemas_service.py to the new signature/semantics (Rule 1 auto-fix) since the old tests called _missing_fields(person) with a single arg and role_id-based _FakePerson fields — both incompatible with the rewritten function. Left api/routers/admin.py and the DB-backed integration test in test_admin_people.py untouched (out of this plan's file scope, matching 27-01 SUMMARY's explicit hand-off of router updates to Plan 27-03)."

requirements-completed: [PDIR-02, PDIR-03, PDIR-04, PDIR-05, PDIR-06]

coverage:
  - id: D1
    description: "_missing_fields branches by is_justice with no role_id check; Bench adds birthdate/no-tenures from a pre-fetched tenure_count (D-05, D-06)"
    requirement: "PDIR-05"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_people_schemas_service.py::test_missing_fields_advocate_all_missing, test_missing_fields_advocate_none_missing, test_missing_fields_advocate_never_flags_birthdate_or_tenures, test_missing_fields_bench_all_missing, test_missing_fields_bench_with_tenures_and_birthdate, test_missing_fields_bench_birthdate_only — all pass"
        status: pass
    human_judgment: false
  - id: D2
    description: "list_people signature exposes is_justice/missing, drops incomplete/Role join, keeps tenure_gaps filter verbatim, adds argument_count/tenure_coverage/has_tenure_gap per row"
    requirement: "PDIR-02, PDIR-03, PDIR-04, PDIR-06"
    verification:
      - kind: unit
        ref: "python -c import/inspect.getsource assertions from Task 2's verify step (is_justice/missing present, role_id/role_name absent, distinct present) — MISSING_OK/LIST_OK"
        status: pass
      - kind: other
        ref: "Live sanity check against the dev database: is_justice=True/False tab filters, missing='no tenures', tenure_gaps=True all returned expected row shapes/counts; argument_count populated for Advocate rows and None for Bench rows; tenure_coverage renders '{start}–{end}'/'{start}–present'/None correctly (confirmed via unicode_escape, a Windows console display artifact only)"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-07-09
status: complete
---

# Phase 27 Plan 2: Read/Directory Rework of admin_people Summary

**`list_people`/`_missing_fields` now drive Bench/Advocate tabs, click-to-filter-by-missing-field, and per-tab columns (tenure coverage/gap, distinct argument count) with zero person-level Role and zero N+1 tenure queries**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-09T04:37:00Z
- **Completed:** 2026-07-09T04:41:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Rewrote `_missing_fields(person, tenure_count)` to drop the `role_id` check entirely (D-10) and branch on `person.is_justice`: Advocate rows check first name/last name/photo/bio only; Bench rows add birthdate and "no tenures" from a pre-fetched count, never issuing a per-person tenure query
- Changed `list_people`'s signature from `(db, incomplete=False, tenure_gaps=False)` to `(db, is_justice=None, missing=None, tenure_gaps=False)`, deleting the person-level `Role` outerjoin/`role_id`/`role_name` from both the query and the returned dict (D-10)
- Implemented the `missing` single-field click-to-filter (D-04) as a Python dict allow-list mapping each of the six known labels to a `.where(...)` clause — unrecognized values apply no filter and are never interpolated into SQL (T-27-03)
- Kept the existing Bench-only `tenure_gaps` EXISTS-subquery filter verbatim, and reused that exact subquery to annotate `has_tenure_gap` on every returned row
- Added `_tenure_coverage()` to render a person's tenure date range as `"{start}–{end}"`, `"{start}–present"` (open-ended), or `None` (zero tenures) from a single prefetched tenure list
- Added a DISTINCT `ArgumentParticipant.argument_id` count per person (not participant-row count) for the Advocate-tab `argument_count` column, populated only for non-Justice rows
- All four per-row annotations (`missing`, `tenure_coverage`, `has_tenure_gap`, `argument_count`) are computed from exactly three prefetch queries per `list_people` call (tenure rows, argument counts, gap-person-ids) — no per-person N+1 queries, verified via a live sanity run against the dev database

## Task Commits

Each task was committed atomically:

1. **Task 1: Branch `_missing_fields` by is_justice and add a tenure prefetch** - `e4b7e445` (feat)
2. **Task 2: Rework `list_people` for tab filter, missing filter, and per-tab columns** - `31b987ac` (feat)

## Files Created/Modified
- `api/services/admin_people.py` - `_missing_fields` rewritten (new signature, is_justice branching, no role check); new `_tenure_coverage()` helper; `list_people` fully reworked (new signature, tab/missing filters, per-row `argument_count`/`tenure_coverage`/`has_tenure_gap`, no Role join)
- `api/tests/test_admin_people_schemas_service.py` - the 6 direct `_missing_fields` unit tests and `_FakePerson` fixture updated to the new signature and Bench/Advocate semantics (Rule 1 auto-fix — these tests called the old 1-arg, role_id-based function and would otherwise fail immediately after Task 1's edit)

## Decisions Made
- `_missing_fields` takes a plain `tenure_count: int` (not a `tenure_counts: dict`) — the plan explicitly left this shape to the executor's discretion; `list_people` still does exactly one grouped prefetch query and passes the per-person count in, satisfying the "no per-person query" requirement either way.
- `has_tenure_gap` is computed by reusing the `tenure_gaps` filter's BENCH-side gap-detection subquery unmodified, restricted to the current result set's person_ids. This is keyed on `ArgumentParticipant.side == BENCH` participation history, not on the row's current `Person.is_justice` flag — confirmed against the dev database, where several people with stale/incorrect `is_justice=False` values (known real Justices mislabeled in seed data) correctly show `has_tenure_gap=True` because they have BENCH-side argument history. This matches the plan's literal instruction to "reuse the same gap logic as the tenure_gaps filter" rather than deriving a new is_justice-scoped variant, and is a pre-existing data-quality characteristic of the dev database, not a defect introduced by this plan.
- `argument_count` is set to `None` for every Bench row via a plain `if not person.is_justice` check on the already-loaded ORM attribute — no separate query is needed to decide which rows get a count.
- Fixed the 6 `_missing_fields`-specific unit tests in `test_admin_people_schemas_service.py` (Rule 1 auto-fix) since they call the function with the old 1-argument, `role_id`-based signature and would fail the moment Task 1 landed. Left `api/routers/admin.py`'s `list_people(db, incomplete=..., tenure_gaps=...)` call site and the DB-backed `test_list_people_incomplete_filter` integration test in `test_admin_people.py` untouched — both are out of this plan's file scope (`files_modified: [api/services/admin_people.py]`) and are explicitly Plan 27-03's responsibility per 27-01-SUMMARY.md's "Next Phase Readiness" note.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated `_missing_fields` unit tests to the new signature**
- **Found during:** Task 1
- **Issue:** `test_admin_people_schemas_service.py` had 6 tests calling `_missing_fields(person)` (one positional arg) against a `_FakePerson` fixture with `role_id`/`bio_text`/`photo_url` fields — both incompatible with the new `_missing_fields(person, tenure_count)` signature and is_justice-branched behavior.
- **Fix:** Replaced `_FakePerson` with a fixture carrying `first_name`/`last_name`/`photo_url`/`bio_text`/`is_justice`/`birthdate`, and rewrote the 6 tests as `test_missing_fields_advocate_*`/`test_missing_fields_bench_*` covering the new Advocate/Bench label sets.
- **Files modified:** `api/tests/test_admin_people_schemas_service.py`
- **Commit:** `e4b7e445`

## Known Follow-ups (not fixed — out of this plan's scope)

- `api/routers/admin.py`'s `GET /people` route still calls `people_service.list_people(db, incomplete=incomplete, tenure_gaps=tenure_gaps)`. Since `list_people` no longer accepts `incomplete`, this call now raises `TypeError` at request time until Plan 27-03 updates the router to pass `is_justice`/`missing` instead. This matches the exact hand-off pattern documented in 27-01-SUMMARY.md ("those calls... will need to be updated by Plan 27-02 (service) and Plan 27-03 (router)").
- `api/tests/test_admin_people.py::test_list_people_incomplete_filter` (a live-DB integration test, skipped without `DATABASE_URL`) exercises the same now-broken router call site via `GET /api/admin/people?incomplete=true` and will fail once a DB is configured, until Plan 27-03 lands. Left untouched — it is testing router behavior, not service behavior, and is explicitly Plan 27-03's file scope.

## Issues Encountered

`ruff` is not installed in this environment's `.venv` (no `ruff` binary or `ruff` module found on PATH or in the venv's `site-packages`) — the plan's Task 2 verify step (`ruff check api/services/admin_people.py`) could not be run as specified. Substituted `python -m py_compile` (clean) plus a manual review of imports/style as the closest available check. No unused imports were introduced or left behind (`or_`, `and_`, `not_`, `exists` are all still used in the reworked `list_people`; `Role` remains imported and used by `get_person_detail`/`list_participants_for_job`, which this plan did not touch).

## User Setup Required

None for this plan's own scope. Installing `ruff` in the project venv (`pip install ruff` or equivalent) would let future plans' `ruff check` verify steps run as written — flagging this as a environment gap, not a task for this plan to resolve unilaterally per the package-install exclusion in the deviation rules.

## Next Phase Readiness
- `list_people`/`_missing_fields` now produce the full Bench/Advocate tab + click-to-filter + per-tab-column contract that Plan 27-04 (list page frontend) will consume.
- Plan 27-03 (router) must update `GET /people` to accept `tab`/`missing` query params and translate them to `is_justice`/`missing` before calling `list_people` (see Known Follow-ups above) — this is a blocking dependency for the router and frontend plans, not a gap in this plan's own deliverable.
- No blockers for this plan's own scope.

---
*Phase: 27-people-admin*
*Completed: 2026-07-09*

## Self-Check: PASSED

- FOUND: api/services/admin_people.py
- FOUND: api/tests/test_admin_people_schemas_service.py
- FOUND: .planning/phases/27-people-admin/27-02-SUMMARY.md
- FOUND commit: e4b7e445 (Task 1)
- FOUND commit: 31b987ac (Task 2)
