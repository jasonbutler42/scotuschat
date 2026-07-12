---
phase: 25-pipeline-job-detail-page
plan: 02
subsystem: api
tags: [fastapi, pydantic, sqlalchemy, admin-jobs, resolve, tenure]

# Dependency graph
requires:
  - phase: 25-01
    provides: "api/routers/admin.py file surface (PATCH /jobs/{job_id}/resolve-rows already registered there); ResolveRowUpdate mutation this plan's read shape mirrors"
provides:
  - "ResolveRow Pydantic schema (api/schemas/admin_people.py) — the locked Resolve card column contract"
  - "list_resolve_rows_for_job service (api/services/admin_people.py) — every ArgumentParticipant row for a job's linked argument, including unresolved rows"
  - "_bench_role_and_missing_tenure helper — explicit Missing tenure state with no D-14 fallback"
  - "GET /api/admin/jobs/{job_id}/resolve-rows endpoint (api/routers/admin.py) — the HTTP data source for the restructured Resolve card"
affects: [25-03-page-server-wiring, 25-04-page-composition]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Explicit Missing-tenure state: _bench_role_and_missing_tenure never falls back to the most-recent tenure (unlike speakers._tenure_role_name's D-14 public-popover fallback) — bench_role is null and missing_tenure is true whenever no CourtTenure covers Argument.argued_date, so the Resolve card can render an explicit warning plus edit-person link (D-15, D-16)."
    - "Read-shape reuses ADVOCATE_LABEL_MAP from api.services.speakers instead of duplicating the side-to-label mapping."
    - "N+1 avoidance: bench-participant CourtTenure rows are fetched in a single IN-query keyed by person_id, mirroring speakers.get_argument_speakers' batching pattern."

key-files:
  created:
    - api/tests/test_admin_people_phase25.py
  modified:
    - api/schemas/admin_people.py
    - api/services/admin_people.py
    - api/routers/admin.py

key-decisions:
  - "title_hint is sourced from the same ArgumentParticipant.title column as title (not a separate stored 'originally extracted' value) — unlike cover_metadata for argued_date/docket, there is no schema field preserving the pre-edit TOC-extracted title once the operator overwrites it via the resolve-row mutation. This is a literal reading of the plan's Task 2 action text ('title_hint sourced from ArgumentParticipant.title'); documented here as a scope clarification for Plan 25-03/25-04, which render the Extracted: [value] hint from this field."
  - "_bench_role_and_missing_tenure is a new, Phase-25-specific helper distinct from speakers._tenure_role_name — the two functions have opposite no-coverage behavior by design (D-14 fallback for public popovers vs. D-15 explicit Missing tenure for the operator Resolve card), so they must not be unified."
  - "list_resolve_rows_for_job raises ValueError (not None) for a missing job/unlinked argument, matching the established admin_jobs.py pattern (get_job_readiness, get_failed_step_recovery) so the router can map it to a 422 rather than inventing a new null-return convention."

patterns-established:
  - "Resolve-row read endpoint: GET /api/admin/jobs/{job_id}/resolve-rows — job-scoped, read-only, mirrors the PATCH .../resolve-rows mutation's argument-ownership derivation and 422-on-ValueError error mapping."

requirements-completed: [PJOB-14, PJOB-15, PJOB-16, PJOB-18, PJOB-19, PJOB-21]

coverage:
  - id: D1
    description: "ResolveRow schema and list_resolve_rows_for_job return every ArgumentParticipant row (including unresolved) for a job's linked argument, scoped strictly to that argument, with editable=false once the argument leaves the pipeline status (D-10, D-11, D-18, D-19)."
    requirement: "PJOB-14"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_people_phase25.py#test_resolve_row_schema_fields"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_people_phase25.py#test_resolve_row_schema_defaults_for_unresolved_row"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_people_phase25.py#test_list_resolve_rows_scoped_to_job_argument"
        status: unknown
      - kind: integration
        ref: "api/tests/test_admin_people_phase25.py#test_list_resolve_rows_editable_false_when_argument_not_pipeline"
        status: unknown
      - kind: integration
        ref: "api/tests/test_admin_people_phase25.py#test_list_resolve_rows_raises_for_missing_job"
        status: unknown
      - kind: integration
        ref: "api/tests/test_admin_people_phase25.py#test_list_resolve_rows_raises_for_unlinked_job"
        status: unknown
    human_judgment: true
    rationale: "DB-gated behavioral tests (real ArgumentParticipant/Argument rows, editable derivation, ValueError raising) are skipped in this environment (no DATABASE_URL configured); schema, pure-function, and structural (source-inspection) tests run and pass without a DB. Needs a DB-backed run before sign-off."
  - id: D2
    description: "Bench rows derive bench_role from a CourtTenure covering Argument.argued_date, or explicit missing_tenure=true plus person_edit_href when none covers it (no fallback, unlike the public speaker popover); bench rows always carry title=null/title_hint=null, advocate rows carry ADVOCATE_LABEL_MAP argument_role and their real title/title_hint (D-15, D-16, PJOB-15, PJOB-16)."
    requirement: "PJOB-16"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_people_phase25.py#test_bench_role_and_missing_tenure_covers_argued_date"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_people_phase25.py#test_bench_role_and_missing_tenure_no_covering_tenure"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_people_phase25.py#test_bench_role_and_missing_tenure_no_argued_date"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_people_phase25.py#test_bench_role_and_missing_tenure_empty_tenures"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_people_phase25.py#test_bench_row_with_covering_tenure_returns_role"
        status: unknown
      - kind: integration
        ref: "api/tests/test_admin_people_phase25.py#test_bench_row_without_covering_tenure_returns_missing_tenure"
        status: unknown
      - kind: integration
        ref: "api/tests/test_admin_people_phase25.py#test_advocate_row_no_missing_tenure_keeps_role_and_title"
        status: unknown
      - kind: integration
        ref: "api/tests/test_admin_people_phase25.py#test_bench_row_title_null_advocate_row_title_present"
        status: unknown
    human_judgment: true
    rationale: "The pure tenure-window predicate is fully unit-tested and passing without a DB. The DB-backed row-assembly tests (real Person/CourtTenure/ArgumentParticipant rows through list_resolve_rows_for_job) are skipped without DATABASE_URL in this environment — needs a DB-backed run or manual UAT against /admin/pipeline/[id] before sign-off."
  - id: D3
    description: "GET /api/admin/jobs/{job_id}/resolve-rows is registered on the shared admin router (inherits X-Admin-Token), calls list_resolve_rows_for_job, returns list[ResolveRow], and maps the service's ValueError to a 422 rather than a 500 for an unknown or unlinked job_id (T-25-04, T-25-06)."
    requirement: "PJOB-21"
    verification:
      - kind: unit
        ref: "api/tests/test_admin_people_phase25.py#test_list_resolve_rows_route_registered"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_people_phase25.py#test_list_resolve_rows_route_maps_value_error_to_4xx"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_people_phase25.py#test_get_resolve_rows_endpoint_requires_admin_token"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_people_phase25.py#test_get_resolve_rows_endpoint_returns_rows"
        status: unknown
      - kind: integration
        ref: "api/tests/test_admin_people_phase25.py#test_get_resolve_rows_endpoint_unknown_job_returns_4xx"
        status: unknown
    human_judgment: true
    rationale: "Auth-rejection (401 with a wrong token, no DB needed) passes in this environment. The DB-backed end-to-end HTTP tests (200 with real rows, 4xx for an unknown job) are skipped without DATABASE_URL — needs a DB-backed run before sign-off."

duration: ~35min
completed: 2026-07-07
status: complete
---

# Phase 25 Plan 02: Resolve-Row Backend Contract Summary

**Typed FastAPI/Pydantic `ResolveRow` shape and job-scoped `GET /api/admin/jobs/{job_id}/resolve-rows` endpoint that returns every participant on a job's argument — including unresolved rows — with backend-derived tenure-based bench role, an explicit "Missing tenure" state, and advocate title/hint data.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3 completed
- **Files modified:** 3 (`api/schemas/admin_people.py`, `api/services/admin_people.py`, `api/routers/admin.py`)
- **Files created:** 1 (`api/tests/test_admin_people_phase25.py`)

## Accomplishments

- Added `ResolveRow` (`api/schemas/admin_people.py`) — the locked Resolve card column contract (raw label, resolved-as, side, argument role, advocate-only title/hint, bench role/missing tenure/person-edit link, editable) covering D-10 through D-19 and PJOB-14/15/16.
- Added `list_resolve_rows_for_job` (`api/services/admin_people.py`) — returns EVERY `ArgumentParticipant` row for the job's linked argument (not just resolved ones like the older `list_participants_for_job`, which is left unchanged), scoped strictly by `argument.id` derived from `job_id`, with `editable` false once the argument leaves the `pipeline` lifecycle state.
- Added `_bench_role_and_missing_tenure` — a Phase-25-specific tenure-window lookup that, unlike `speakers._tenure_role_name`'s public-popover D-14 fallback, returns an explicit `missing_tenure=True` (no fallback to the most-recent tenure) when no `CourtTenure` covers `Argument.argued_date`, satisfying D-15/D-16's requirement for a visible "Missing tenure" state plus a `person_edit_href` link.
- Wired `GET /api/admin/jobs/{job_id}/resolve-rows` on the existing admin router (inherits the router-level `X-Admin-Token` dependency), giving the Resolve card a concrete HTTP data source and mapping the service's `ValueError` to 422.

## Task Commits

Each task was committed atomically (Tasks 1 and 2 share one commit — see TDD Gate Compliance / Deviations below for why):

1. **Task 1 + Task 2: Add resolve-row schema and tenure-derived bench role service** - `c7cab1a4` (feat)
2. **Task 3: Wire job-scoped GET endpoint exposing resolve rows over HTTP** - `7c57cff9` (feat)

## Files Created/Modified

- `api/schemas/admin_people.py` - Added `ResolveRow` (imports `SideEnum` from `api.models.models`).
- `api/services/admin_people.py` - Added `_bench_role_and_missing_tenure` and `list_resolve_rows_for_job`; imports `ArgumentStatusEnum` from `api.models.models` and reuses `ADVOCATE_LABEL_MAP` from `api.services.speakers`.
- `api/routers/admin.py` - Added `GET /jobs/{job_id}/resolve-rows`; imports `ResolveRow` from `api.schemas.admin_people`.
- `api/tests/test_admin_people_phase25.py` - Schema, pure-function, structural (source-inspection), and DB-gated tests for all three tasks, plus HTTP-level endpoint tests via `httpx.ASGITransport`.

## Decisions Made

- `title_hint` is sourced from the same `ArgumentParticipant.title` column as `title` — there is no separate stored "originally extracted" value for title (unlike `cover_metadata` for `argued_date`/`docket`, which preserves the raw extraction alongside the editable column). This is a literal reading of the plan's Task 2 action text; flagged so Plan 25-03/25-04 know the `Extracted: [value]` hint reflects the current DB value, not an immutable extraction snapshot.
- `_bench_role_and_missing_tenure` is intentionally NOT a reuse of `speakers._tenure_role_name` — the two helpers have opposite no-coverage behavior by design (D-14 fallback for the public speaker popover vs. D-15's explicit Missing-tenure requirement for the operator Resolve card).
- `list_resolve_rows_for_job` raises `ValueError` (not `None`) for a missing job or unlinked argument, matching `admin_jobs.py`'s established pattern (`get_job_readiness`, `get_failed_step_recovery`) so the router's 422 mapping is consistent across Phase 25's new endpoints.
- Bench rows carry `argument_role` equal to `bench_role` (both `None` when tenure is missing); advocate rows carry `argument_role` from `ADVOCATE_LABEL_MAP` and leave `bench_role`/`missing_tenure`/`person_edit_href` at their `None`/`False` defaults — keeps a single "Argument Role" column semantically correct for both row kinds while still exposing the bench-specific fields the UI-SPEC's Missing-tenure UI needs.

## Deviations from Plan

### Commit Grouping (not a Rule 1-4 deviation — documented for traceability)

Tasks 1 ("Add resolve row schema and job-scoped listing service") and 2 ("Add tenure-derived bench role and Missing tenure flags") were implemented and committed together rather than as two separate commits. Both tasks modify the same new function (`list_resolve_rows_for_job`), and Task 1's own `ResolveRow` schema already declares the `bench_role`/`missing_tenure`/`person_edit_href` fields that Task 2's logic populates — the schema and its tenure-derivation logic are not meaningfully separable into two working intermediate states. This mirrors 25-01's precedent of consolidating same-file, tightly-coupled task work into one commit when `tdd_mode` is `false`.

**Total deviations:** 0 auto-fixed. One documented commit-grouping decision (not a code deviation).
**Impact on plan:** No scope creep; all three tasks' `<done>` criteria are met.

## Issues Encountered

- Running the full `api/tests` suite as a sanity check surfaced the same 3 pre-existing failures already logged in `.planning/phases/25-pipeline-job-detail-page/deferred-items.md` by Plan 25-01 (`test_arguments.py::test_get_utterances_returns_404_for_unknown_argument`, `test_people.py::test_get_person`, `test_people.py::test_get_person_404` — `RuntimeError: Database session factory is not initialised`). Confirmed unrelated to this plan's files; not re-logged (already documented).
- No `DATABASE_URL` is configured in this execution environment, so all DB-gated behavioral tests in `test_admin_people_phase25.py` are skipped (`skipif`), consistent with Plan 25-01's own environment. All schema, pure-function, and structural (source-inspection) tests run and pass without a DB (36 passed, 10 skipped across the targeted test run).

## TDD Gate Compliance

Each task declares `tdd="true"` in the plan, but `.planning/config.json` has `workflow.tdd_mode: false` and no `DATABASE_URL` is configured in this environment (same conditions as 25-01). Tests and implementation were written and verified together per commit rather than as separate RED/GREEN commits. No `test(...)`-only commit exists in the git log for this plan; both commits are `feat(...)` commits that include new tests alongside the implementation they exercise, verified passing (`pytest api/tests/test_admin_people_phase25.py -q` — 12 passed, 10 skipped) before each commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 25-03 can now build the SvelteKit `+page.server.ts` load function against a stable `GET /api/admin/jobs/{job_id}/resolve-rows` contract returning `list[ResolveRow]`, and against Plan 25-01's `PATCH .../resolve-rows` mutation and `create_person_for_job` mini popover support.
- Plan 25-04's `ResolveCard.svelte` has a concrete row shape to render: `raw_speaker_label`, `full_name`/`photo_url`, `side`, `argument_role`, advocate-only `title`/`title_hint`, `bench_role`/`missing_tenure`/`person_edit_href`, and `editable`.
- Before UAT/production sign-off, run the DB-gated tests in `api/tests/test_admin_people_phase25.py` against a real `DATABASE_URL` (or exercise `GET /api/admin/jobs/{job_id}/resolve-rows` manually against `/admin/pipeline/[id]`) — see the `coverage` block above for the specific skipped test names per deliverable. Per Offen's AI Innovation Program stage-gate, confirm this backend work has cleared Sandbox → Pilot review before any production-facing rollout of the downstream UI plans (25-03, 25-04) that depend on it.

---

*Phase: 25-pipeline-job-detail-page*
*Completed: 2026-07-07*

## Self-Check: PASSED

All created/modified files exist on disk and both task commit hashes (`c7cab1a4`, `7c57cff9`) are present in git history.
