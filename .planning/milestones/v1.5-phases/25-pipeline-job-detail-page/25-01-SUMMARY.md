---
phase: 25-pipeline-job-detail-page
plan: 01
subsystem: api
tags: [fastapi, pydantic, sqlalchemy, admin-jobs, resolve, readiness]

# Dependency graph
requires: []
provides:
  - "RunReadiness/ReadinessBlocker schemas and get_job_readiness service helper (not_ready/ready/already_created)"
  - "FailedStepRecovery schema, derive_failed_step_recovery pure function, and get_failed_step_recovery service helper"
  - "PersonCreate raw_speaker_label/side fields and job-scoped create_person_for_job mutation (is_justice + participant side)"
  - "ResolveRowUpdate schema, update_resolve_row_for_job service helper, and PATCH /api/admin/jobs/{job_id}/resolve-rows endpoint"
affects: [25-02-resolve-row-shape, 25-03-page-server-wiring, 25-04-page-composition]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Job-scoped IDOR guard: derive argument_id from job_id server-side, then verify the target row (participant) belongs to that argument before any mutation — never trust a client-supplied argument_id or participant_id alone."
    - "Validate-before-mutate ordering (mirrors resolve_job's Pitfall 5): the target ArgumentParticipant is looked up and checked before any Person/ArgumentParticipant row is created or updated."
    - "Separate human guidance from raw technical error in response schemas (FailedStepRecovery.guidance vs .raw_error) so the UI can show one first and hide the other behind a details disclosure."

key-files:
  created:
    - api/tests/test_admin_jobs_phase25.py
    - .planning/phases/25-pipeline-job-detail-page/deferred-items.md
  modified:
    - api/schemas/admin_jobs.py
    - api/services/admin_jobs.py
    - api/routers/admin.py

key-decisions:
  - "get_job_readiness treats already_created as a short-circuit: once the linked argument's status is no longer PIPELINE, the run is reported already_created regardless of any other blocker (D-01, D-04, D-18, D-20)."
  - "Failed-step guidance copy matches 25-UI-SPEC.md's Failed-Step Guidance Copy table verbatim and never mentions rerun/same-source (D-05, PJOB-22 supersession)."
  - "update_resolve_row_for_job is a new job-scoped mutation, not a reuse of admin_arguments.update_participant_side, because that endpoint rejects BENCH by design (RESEARCH.md Open Question #1)."
  - "title is forced to null server-side whenever side == BENCH in update_resolve_row_for_job, regardless of what the client sends (PJOB-15)."

patterns-established:
  - "Pattern: resolve-row mutation endpoint PATCH /api/admin/jobs/{job_id}/resolve-rows — job-scoped, body-only participant_id (no path param duplication), argument ownership derived server-side."

requirements-completed: [PJOB-01, PJOB-02, PJOB-08, PJOB-14, PJOB-18, PJOB-19, PJOB-20, PJOB-22]

coverage:
  - id: D1
    description: "Run readiness is backend-derived: not_ready lists strict blockers, ready enables Create Argument, already_created is a short-circuit off argument.status != pipeline with an argument_edit_href (D-01, D-02, D-03, D-04, D-18, D-20; PJOB-01, PJOB-02)."
    requirement: "PJOB-01"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_jobs_phase25.py#test_run_readiness_schema_states"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_jobs_phase25.py#test_get_job_readiness_already_created_short_circuits"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_jobs_phase25.py#test_get_job_readiness_already_created_when_argument_not_pipeline"
        status: unknown
      - kind: integration
        ref: "api/tests/test_admin_jobs_phase25.py#test_get_job_readiness_ready_when_all_conditions_met"
        status: unknown
      - kind: integration
        ref: "api/tests/test_admin_jobs_phase25.py#test_get_job_readiness_not_ready_with_strict_blockers"
        status: unknown
    human_judgment: true
    rationale: "DB-gated behavioral tests for get_job_readiness are skipped in this environment (no DATABASE_URL configured); structural/schema tests pass but the full state-derivation behavior needs a DB-backed test run (or manual UAT against /admin/pipeline/[id]) before sign-off."
  - id: D2
    description: "Failed recovery returns step-specific human guidance separate from the raw error, with a pipeline-page link, and never recommends same-source rerun (D-05 through D-08, PJOB-22 supersession)."
    requirement: "PJOB-08"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_jobs_phase25.py#test_derive_failed_step_recovery_ingest_guidance"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_jobs_phase25.py#test_derive_failed_step_recovery_parse_guidance"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_jobs_phase25.py#test_derive_failed_step_recovery_resolve_guidance"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_jobs_phase25.py#test_derive_failed_step_recovery_never_recommends_same_source_rerun"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_jobs_phase25.py#test_get_failed_step_recovery_loads_job_and_derives_guidance"
        status: unknown
    human_judgment: true
    rationale: "The pure guidance-derivation function is fully unit-tested and passing, but the DB-backed job-loading wrapper (get_failed_step_recovery) is skipped without DATABASE_URL — full path needs a DB-backed run before sign-off."
  - id: D3
    description: "Inline create-person payload captures name plus side, sets Person.is_justice from the Bench/Advocate choice, and updates the matching job-owned ArgumentParticipant with an IDOR guard (D-12, D-13, PJOB-19)."
    requirement: "PJOB-19"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_jobs_phase25.py#test_person_create_accepts_raw_speaker_label_and_side"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_jobs_phase25.py#test_create_person_for_job_validates_participant_before_person_insert"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_jobs_phase25.py#test_create_person_for_job_bench_sets_is_justice_and_participant_side"
        status: unknown
      - kind: integration
        ref: "api/tests/test_admin_jobs_phase25.py#test_create_person_for_job_advocate_sets_is_justice_false"
        status: unknown
      - kind: integration
        ref: "api/tests/test_admin_jobs_phase25.py#test_create_person_for_job_rejects_participant_outside_job_argument"
        status: unknown
    human_judgment: true
    rationale: "DB-gated behavioral tests (BENCH/advocate mutation, IDOR guard) are skipped without DATABASE_URL; structural ordering guard is verified by source inspection, but real-row behavior needs a DB-backed run before sign-off."
  - id: D4
    description: "The job-scoped resolve-row mutation persists ArgumentParticipant side (including BENCH) and advocate title under job/argument ownership guards, forces title null for BENCH, and is rejected once the argument is no longer pipeline (D-14, D-18, PJOB-14, PJOB-18, D-19)."
    requirement: "PJOB-14"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_jobs_phase25.py#test_resolve_row_update_schema_allows_bench"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_jobs_phase25.py#test_update_resolve_row_for_job_does_not_reuse_advocate_side_endpoint"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_jobs_phase25.py#test_update_resolve_row_bench_side_persists"
        status: unknown
      - kind: integration
        ref: "api/tests/test_admin_jobs_phase25.py#test_update_resolve_row_advocate_title_persists_bench_title_forced_null"
        status: unknown
      - kind: integration
        ref: "api/tests/test_admin_jobs_phase25.py#test_update_resolve_row_rejects_participant_outside_job_argument"
        status: unknown
      - kind: integration
        ref: "api/tests/test_admin_jobs_phase25.py#test_update_resolve_row_rejects_edit_when_argument_not_pipeline"
        status: unknown
    human_judgment: true
    rationale: "DB-gated behavioral tests (BENCH persistence, title-forced-null, IDOR guard, pipeline-status editable window) are skipped without DATABASE_URL; structural guard (no reuse of the BENCH-rejecting endpoint, status guard present) is verified by source inspection. Needs a DB-backed run before sign-off."

duration: 45min
completed: 2026-07-07
status: complete
---

# Phase 25 Plan 01: Backend Job-Detail Contract Summary

**Typed FastAPI/Pydantic contract for run readiness, failed-step recovery, job-scoped mini create-person, and a new resolve-row side/title mutation that allows BENCH — all guarded by argument ownership derived from job_id.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 3 completed
- **Files modified:** 3 (`api/schemas/admin_jobs.py`, `api/services/admin_jobs.py`, `api/routers/admin.py`)
- **Files created:** 2 (`api/tests/test_admin_jobs_phase25.py`, `.planning/phases/25-pipeline-job-detail-page/deferred-items.md`)

## Accomplishments

- Added `RunReadiness`/`ReadinessBlocker`/`FailedStepRecovery` schemas and `get_job_readiness`/`derive_failed_step_recovery`/`get_failed_step_recovery` service helpers so the UI can render Not ready / Ready / Already created and step-specific failed guidance from backend-derived facts, not client-side inference (D-01 through D-08, D-18, D-20).
- Extended `PersonCreate` with `raw_speaker_label`/`side` and rewrote `create_person_for_job` to be a job-scoped mini create-person mutation: it validates the target participant belongs to the job's own argument *before* creating any `Person` row, sets `Person.is_justice` from `side == BENCH`, and updates the matched participant's `person_id`/`side` in the same transaction (D-12, D-13, PJOB-19).
- Added a brand-new job-scoped resolve-row mutation — `ResolveRowUpdate` schema, `update_resolve_row_for_job` service function, and `PATCH /api/admin/jobs/{job_id}/resolve-rows` endpoint — that allows setting `side` to `BENCH` (the existing `admin_arguments.update_participant_side` endpoint rejects BENCH by design), forces `title` to `null` whenever `side == BENCH`, and rejects any edit once the linked argument has left the `pipeline` status (D-14, D-18, D-19, PJOB-14, PJOB-18).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add typed job readiness and failed recovery schemas** - `cc84d60e` (feat)
2. **Task 2: Extend mini create-person job support with side and is_justice** - `1b357d54` (feat)
3. **Task 3: Add guarded resolve-row side and title mutation for existing participants** - `0814ea85` (feat)

_Note: `tdd_mode` is `false` in `.planning/config.json`; tasks were implemented and their corresponding tests written/verified together per commit rather than as separate RED/GREEN commits — see TDD Gate Compliance below._

## Files Created/Modified

- `api/schemas/admin_jobs.py` - Added `ReadinessBlocker`, `RunReadiness`, `FailedStepRecovery`, `ResolveRowUpdate`; extended `PersonCreate` with `raw_speaker_label`/`side`.
- `api/services/admin_jobs.py` - Added `derive_failed_step_recovery`, `get_failed_step_recovery`, `get_job_readiness`, `update_resolve_row_for_job`; rewrote `create_person_for_job` for job-scoped mini create-person.
- `api/routers/admin.py` - Added `PATCH /api/admin/jobs/{job_id}/resolve-rows`; documented the Phase 25 payload shape on the existing `/jobs/{job_id}/people` endpoint (no functional change there).
- `api/tests/test_admin_jobs_phase25.py` - Schema, pure-function, structural (source-inspection), and DB-gated tests for all three tasks.
- `.planning/phases/25-pipeline-job-detail-page/deferred-items.md` - Logged 3 pre-existing, unrelated test failures found while running the full suite (see Issues Encountered).

## Decisions Made

- `get_job_readiness`'s `already_created` state is a hard short-circuit on `argument.status != PIPELINE` — no other blocker is evaluated once that's true, matching D-04's "show only that the argument was created" requirement.
- Failed-step guidance copy was copied verbatim from `25-UI-SPEC.md`'s Failed-Step Guidance Copy table (Ingest/Parse/Resolve/Unknown) so the backend and approved UI contract never drift.
- `update_resolve_row_for_job` is intentionally a new function/endpoint rather than an extension of `admin_arguments.update_participant_side`, because that existing endpoint explicitly rejects `BENCH` by design (T-15-02-BENCH) — reusing it would require weakening an existing security guard.
- The new resolve-row endpoint takes `participant_id` in the request body (not the URL path) to avoid a redundant path/body duplication; `job_id` in the path is the only trust boundary for argument ownership.

## Deviations from Plan

None — plan executed as written. Two minor documentation-only additions beyond the plan's letter (not scope creep):

1. Added a one-line Phase 25 note to the `/jobs/{job_id}/people` router docstring (no functional/behavioral change) to keep the endpoint's documented contract in sync with the extended `PersonCreate` schema.
2. Logged pre-existing unrelated test failures to `deferred-items.md` per the Scope Boundary rule (see Issues Encountered) instead of silently ignoring them.

## Issues Encountered

- Running the full `api/tests` suite (not just the new Phase 25 file) surfaced 3 pre-existing failures unrelated to this plan's files: `test_arguments.py::test_get_utterances_returns_404_for_unknown_argument`, `test_people.py::test_get_person`, `test_people.py::test_get_person_404`. Root cause is `RuntimeError: Database session factory is not initialised` — these tests exercise a FastAPI route without the app's `lifespan` context having run. Confirmed pre-existing (unaffected by this plan's changes) and logged to `.planning/phases/25-pipeline-job-detail-page/deferred-items.md` per the Scope Boundary rule; not fixed here.
- No `DATABASE_URL` is configured in this execution environment (no `.env` file present), so all DB-gated behavioral tests in `test_admin_jobs_phase25.py` are skipped (`skipif`), consistent with the plan's own verification note ("If DB-backed tests are skipped... document skipped integration coverage in the summary"). All schema, pure-function, and structural (source-inspection) tests run and pass without a DB.

## TDD Gate Compliance

Each task declares `tdd="true"` in the plan, but `.planning/config.json` has `workflow.tdd_mode: false` and no `DATABASE_URL` is configured in this environment. Given the three tasks share the same two files (`api/schemas/admin_jobs.py`, `api/services/admin_jobs.py`) and RED-then-GREEN would have required re-editing already-interleaved code, tests and implementation were written and verified together per task rather than as separate `test(...)` → `feat(...)` commits. No `test(...)`-only commit exists in the git log for this plan; all three commits are `feat(...)` commits that include both new tests and the implementation they exercise, verified passing (`pytest api/tests/test_admin_jobs_phase25.py -q`) before each commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 25-02 can now build the typed resolve-row read shape against a stable `ArgumentParticipant.side`/`.title` write path (Task 3 of this plan) and the `get_job_readiness`/`get_failed_step_recovery` helpers (Task 1) without guessing at backend contracts.
- Plan 25-03's `saveResolveRow` action and `addPerson` action extension have a stable API surface: `PATCH /api/admin/jobs/{job_id}/resolve-rows` and the extended `POST /api/admin/jobs/{job_id}/people` payload (`raw_speaker_label`, `side`).
- Before UAT/production sign-off, run the DB-gated tests in `api/tests/test_admin_jobs_phase25.py` against a real `DATABASE_URL` (or exercise the new endpoints manually against `/admin/pipeline/[id]`) — see the `coverage` block above for the specific skipped test names per deliverable. Per Offen's AI Innovation Program stage-gate, confirm this backend work has cleared Sandbox → Pilot review before any production-facing rollout of the downstream UI plans that depend on it.

---

*Phase: 25-pipeline-job-detail-page*
*Completed: 2026-07-07*

## Self-Check: PASSED

All created/modified files exist on disk and all 3 task commit hashes (`cc84d60e`, `1b357d54`, `0814ea85`) are present in git history.
