---
phase: 44-resolve-table-rework
plan: 06
subsystem: api
tags: [fastapi, sqlalchemy, resolve-row-write-path, tenure-derivation, regression-lock, figma-reconciliation]

# Dependency graph
requires:
  - phase: 44-05
    provides: "Structural four-column ResolveCard.svelte rework (independent of this plan's service-layer work — this plan runs in parallel, touching only api/services/admin_jobs.py and tests)"
provides:
  - "update_resolve_row_for_job omits the descriptor column from its UPDATE values on a BENCH write instead of overwriting it with null — the stored value survives a Bench toggle and a client-supplied bench descriptor is never written (RESOLVE-13, server half)"
  - "api/tests/test_admin_jobs_phase25.py's bench-descriptor test inverted to assert preservation, plus a new three-step advocate->bench->advocate round-trip test"
  - "api/tests/test_phase44_live_tenure_recompute.py — four DB-gated tests locking RESOLVE-11's live tenure-derived bench_role/missing_tenure on both list_resolve_rows_for_job and list_argument_speakers, including a published argument"
affects: [44-08]

# Actuals (#2632)
actuals:
  tokens: 7711
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Conditional UPDATE values dict: build `values = {\"side\": ...}` and add optional keys only under a guard, so the generated SQL never mentions a column the write path should leave untouched — cleaner than writing the column's existing value back or writing null over it"

key-files:
  created:
    - api/tests/test_phase44_live_tenure_recompute.py
  modified:
    - api/tests/test_admin_jobs_phase25.py
    - api/services/admin_jobs.py
    - api/tests/test_phase44_argument_role_roundtrip.py

key-decisions:
  - "Task 2 broke a second test outside this plan's declared files_modified list: test_phase44_argument_role_roundtrip.py (from Phase 44 Plan 03) had its own PJOB-15 re-assertion asserting the exact discard behavior being reversed. Fixed inline (Rule 1 — auto-fix a bug directly caused by the current task's change) rather than leaving the suite red; documented in the Task 2 commit message. This is the only deviation from the plan's literal `files_modified` list, and Task 2's own verify command (full api test suite) required it."
  - "RESOLVE-11 and RESOLVE-13 intentionally left un-checked in REQUIREMENTS.md, mirroring Phase 44 Plan 01's precedent with RESOLVE-04. Both requirements split across this plan and 44-08: RESOLVE-13's client half (suppressing the bench descriptor hint line in ResolveCard.svelte) and RESOLVE-11's 'Edit person' new-tab markup both ship in 44-08. Marking either complete now would misrepresent state before 44-08 lands its half."
  - "Chose 1966 as the fixed argued_date for all four Task 3 fixtures (matching the phase's own Baltimore & Ohio Railroad Co. complexity fixture era) with a not-covering tenure start_date of 1967-01-01 and a covering start_date of 1960-01-01, so the coverage relationship is unambiguous and readable in a failure diff without relying on today's date."

requirements-completed: []

coverage:
  - id: T1
    description: "Bench-descriptor test in test_admin_jobs_phase25.py inverted to assert preservation; new advocate->bench->advocate round-trip test added; both fail against the unfixed service"
    requirement: "RESOLVE-13"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_jobs_phase25.py::test_update_resolve_row_advocate_descriptor_persists_bench_descriptor_preserved"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_jobs_phase25.py::test_update_resolve_row_descriptor_survives_advocate_bench_advocate_round_trip"
        status: pass
    human_judgment: false
  - id: T2
    description: "update_resolve_row_for_job omits the descriptor column from the UPDATE on a BENCH write instead of overwriting it with null; docstring rewritten; all guards untouched; no Alembic migration"
    requirement: "RESOLVE-13"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_jobs_phase25.py (36 passed) and full api test suite (605 passed)"
        status: pass
      - kind: command
        ref: "git status --porcelain alembic/versions/ (no new files)"
        status: pass
    human_judgment: false
  - id: T3
    description: "Four DB-gated regression tests locking live tenure-derived bench role on both read paths, including a published argument, all green against unmodified service code"
    requirement: "RESOLVE-11"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_live_tenure_recompute.py (4 passed)"
        status: pass
      - kind: command
        ref: "git diff --name-only && git status --porcelain api/services/ (no service changes from this task)"
        status: pass
    human_judgment: false
---

# Phase 44 Plan 06: Descriptor Preservation Fix + Live Tenure Recompute Lock Summary

Fixed the one genuine backend bug the Figma reconciliation surfaced — toggling a resolve row to
Bench was silently nulling out the operator's stored descriptor in the database — and locked, via a
new DB-gated regression file, the one behaviour reconciliation flagged as highest-risk but research
proved was already correct: bench role and missing-tenure state are derived fresh from `court_tenures`
on every read, on both the job-scoped Resolve card path and the argument-scoped Speakers path,
including for arguments that have already been published.

## What Was Built

**Task 1 (red-first test inversion).** `api/tests/test_admin_jobs_phase25.py`'s second
bench-descriptor test was renamed from `..._bench_descriptor_forced_null` to
`..._bench_descriptor_preserved` and rewritten: the bench participant now starts with a real stored
descriptor (`"Solicitor General"`), and a BENCH write carrying a *different* descriptor string must
leave the stored value untouched — asserted both against the returned ORM instance and against a
fresh re-read in a new session. A second new test,
`test_update_resolve_row_descriptor_survives_advocate_bench_advocate_round_trip`, drives one
participant through three sequential writes (PETITIONER with a descriptor → BENCH with
`descriptor=None` → RESPONDENT with the same descriptor sent back, mirroring what the real hidden
form resubmits), asserting the descriptor survives every step. Both tests failed against the
unfixed service, confirming the red-first precondition.

**Task 2 (the fix).** `update_resolve_row_for_job` in `api/services/admin_jobs.py` now builds its
`UPDATE` values as a dict starting with `{"side": body.side}` and adds the `descriptor` key only when
`body.side != SideEnum.BENCH`. On a BENCH write, the descriptor column no longer appears in the
generated SQL at all — it is neither read from the client body nor written as null. The docstring's
PJOB-15 paragraph was rewritten to state the new rule and point at `list_resolve_rows_for_job` as the
place bench rows are still hidden (read path unchanged). All three guards (job exists, argument in
`pipeline` status, participant-belongs-to-argument IDOR check) are byte-identical to before.

Running the full `api/tests` suite after this change surfaced a second test — outside this plan's
declared `files_modified` — that encoded the exact discard behavior being reversed:
`test_phase44_argument_role_roundtrip.py` (from Phase 44 Plan 03) had its own "PJOB-15
re-assertion" asserting a BENCH write forces a previously-set advocate descriptor to null. Since this
is a direct, in-scope consequence of Task 2's fix (Rule 1 — auto-fix a bug the current task's change
causes), that assertion was updated to expect preservation instead, with its docstring/comment
updated to reference RESOLVE-13 and point at the canonical inverted test.

**Task 3 (regression lock, no fix expected).** New file `api/tests/test_phase44_live_tenure_recompute.py`
with four DB-gated tests, all green against unmodified service code on the first run:

1. `test_resolve_rows_bench_role_recomputes_after_tenure_correction` — `list_resolve_rows_for_job`
   reports `missing_tenure=True`/`bench_role=None`/a non-null `person_edit_href` for a
   non-covering tenure, then reports the corrected role with `missing_tenure=False` and
   `person_edit_href=None` after the tenure's `start_date` is widened in a separate session — no
   restart, cache clear, or resolve re-run between reads.
2. `test_argument_speakers_bench_role_recomputes_after_tenure_correction` — the identical
   before/after sequence against `list_argument_speakers`.
3. `test_both_read_paths_agree_on_bench_role_and_missing_tenure` — both functions called in the
   same session report equal `bench_role` and equal `missing_tenure`, both while a tenure covers the
   argued date and after it's flipped to not cover it.
4. `test_published_argument_bench_role_recomputes_after_tenure_correction` — a `PUBLISHED`
   argument's `list_resolve_rows_for_job` row keeps `editable=False` throughout, but its
   `missing_tenure`/`bench_role` still recompute correctly after a post-publication tenure
   correction — the reconciliation doc's largest correctness item.

All four fixtures use a fixed 1966 argued date (matching the phase's own complexity-fixture era) with
a not-covering tenure `start_date` of 1967-01-01 and a covering `start_date` of 1960-01-01, so the
coverage relationship reads unambiguously in a failure diff.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a second test broken by the descriptor-preservation fix**
- **Found during:** Task 2, first full-suite pytest run after the service change
- **Issue:** `test_phase44_argument_role_roundtrip.py::test_argument_role_round_trips_for_each_real_advocate_role`
  (parametrized ×3, all three failed) contained its own "PJOB-15 re-assertion" that a BENCH payload
  forces a previously-stored descriptor to null — the exact behavior Task 2 reverses.
- **Fix:** Updated the assertion and its surrounding comment/docstring to expect the stored
  descriptor (`"Counsel of Record"`) survives the bench write, referencing RESOLVE-13 and the
  canonical inverted test in `test_admin_jobs_phase25.py`.
- **Files modified:** `api/tests/test_phase44_argument_role_roundtrip.py`
- **Commit:** `7016bc96`

Or: no other auto-fixed issues — the rest of the plan executed exactly as written.

### Auth Gates

None encountered.

### Prohibited Actions Avoided

- No Alembic migration created (`git status --porcelain alembic/versions/` empty throughout).
- No cache, memoized lookup, or stored snapshot column added for `bench_role` — Task 3 is purely a
  regression test against the existing per-request `court_tenures` query.
- No nearest-tenure fallback added — `_bench_role_and_missing_tenure`'s no-fallback (D-15) contract
  is exercised, not modified, by Task 3's missing-tenure assertions.

## Verification

- `./.venv/Scripts/python.exe -m pytest tests/conftest.py api/tests -q` — **605 passed**, 0
  failures, the same 4 pre-existing collection errors documented in every prior 44-0x SUMMARY
  (Node.js path issue in `test_phase38_people_ui_contract.py`, unrelated to this plan).
- `./.venv/Scripts/python.exe -m pytest tests/conftest.py api/tests/test_admin_jobs_phase25.py -q`
  — 36 passed.
- `./.venv/Scripts/python.exe -m pytest tests/conftest.py api/tests/test_phase44_live_tenure_recompute.py -q`
  — 4 passed, 0 skipped (DATABASE_URL was configured for this run against the real test DB).
- `git status --porcelain alembic/versions/` — empty, no migration created.
- `git diff --stat` on `api/services/admin_people.py api/services/admin_arguments.py` across this
  plan's commit range — empty, neither read path was modified.
- `awk '/async def update_resolve_row_for_job/,/return participant/' api/services/admin_jobs.py | grep -c 'descriptor = None if'`
  — 0, the old unconditional null-forcing expression is gone.

## Self-Check: PASSED

- FOUND: `api/tests/test_phase44_live_tenure_recompute.py`
- FOUND: commit `e080f6fd` (Task 1)
- FOUND: commit `7016bc96` (Task 2)
- FOUND: commit `6761c75d` (Task 3)
