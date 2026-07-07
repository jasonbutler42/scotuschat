---
phase: 24-pipeline-list-page
plan: 04
subsystem: admin-pipeline-list
tags: [sveltekit, fastapi, alembic, docket-pills, compound-badge]
dependency_graph:
  requires: ["24-02"]
  provides: ["pipeline-list-page-v2", "admin-jobs-source-dockets"]
  affects: ["app/src/routes/admin/pipeline/+page.svelte", "app/src/routes/admin/pipeline/+page.server.ts", "api/routers/admin.py", "api/services/admin_jobs.py", "api/schemas/admin_jobs.py", "api/models/models.py", "pipeline/__main__.py", "pipeline/commands/ingest.py", "alembic/versions/0015_add_admin_job_source_dockets.py"]
tech_stack:
  added: []
  patterns:
    - "Read pill values from formEl.querySelectorAll('input[name=\"docket[]\"]') at submit time instead of a bound $state variable (keeps DocketPillInput self-contained)"
    - "Sequential per-pill duplicate preflight, stopping on first match and naming the specific docket"
    - "Compound badge label combining current_step + status with a middot separator; badgeStyle stays keyed on status alone"
    - "Run-start docket list persisted on admin_jobs.source_dockets (nullable ARRAY) because Argument does not exist until ingest completes — D-07 supersession, no immediate metadata PATCH"
    - "Shared docket normalization pattern (trim, drop blanks, dedupe preserving order) mirrored between the FastAPI router and admin_arguments.update_argument_metadata"
key_files:
  created:
    - alembic/versions/0015_add_admin_job_source_dockets.py
  modified:
    - app/src/routes/admin/pipeline/+page.svelte
    - app/src/routes/admin/pipeline/+page.server.ts
    - api/routers/admin.py
    - api/services/admin_jobs.py
    - api/schemas/admin_jobs.py
    - api/models/models.py
    - pipeline/__main__.py
    - pipeline/commands/ingest.py
decisions:
  - "D-07 supersession confirmed and implemented as designed: full docket list is carried as run-start metadata (admin_jobs.source_dockets) rather than an immediate metadata PATCH, because argument_id is null until the ingest subprocess completes."
  - "Router normalization inserts primary_docket at index 0 of source_dockets when not already present, preserving backward compatibility for legacy callers that only send primary_docket."
  - "rerun_job copies original.source_dockets onto the new job so a rerun preserves the originally submitted docket list; the rerun router rebuilds --primary-docket/--dockets from that copied list."
metrics:
  duration: "~35m"
  completed: 2026-07-07
status: complete
---

# Phase 24 Plan 04: Pipeline List Page — Free-Text Question, Docket Pills, Compound Badge, Full Docket Persistence Summary

Replaced the pipeline list page's question dropdown with free text, swapped the single docket field for the shared `DocketPillInput` with per-pill duplicate preflight, collapsed Status+Step into one compound badge, renamed the section heading to "All Runs", and carried every submitted docket pill through SvelteKit → FastAPI → `admin_jobs.source_dockets` → ingest subprocess → `Argument.source_dockets` without any immediate metadata PATCH.

## What Was Built

**Task 1 — `+page.svelte` UI changes (PLIST-01, PLIST-02, PLIST-04, PLIST-05):**
- Replaced `<select name="question_number">` (Q1/Q2 options) with a free-text `<input type="text" name="question_number">`, still pre-filled `"1"` via the existing `questionInput` `$state`.
- Replaced the single `<input name="primary_docket">` with `<DocketPillInput initialValues={[]} name="docket[]" id="primary_docket" />` (the shared component built in Plan 02), rendered inside the existing form — no nested-form issue.
- Removed the now-unused `docketInput` `$state`.
- Rewrote `handleSubmit` to read pill values from the form via `formEl.querySelectorAll('input[name="docket[]"]')` instead of a bound text value. Preflight now loops sequentially over every pill, calling the existing `check-duplicate` proxy once per pill; on the first match it sets `duplicateWarning` naming that specific docket and stops; on a non-OK response or network error it fails open (existing WR-02 behavior, preserved).
- Updated `badgeLabel(status, currentStep)` to a compound label: `"{Step} · {StatusLabel}"` when a step is active and status isn't `completed`, otherwise the bare status label. `paused` now maps to "Needs Review" (capital R). `badgeStyle` is unchanged (still keyed on status alone).
- Removed the Step `<th>` and its corresponding `<td>{job.current_step ?? '—'}</td>` from the runs table — three columns remain: Status | Created | (View).
- Renamed the "Recent Runs" heading to "All Runs".
- Left the "Show incomplete only" toggle, the unconditional polling `$effect`, and the `pageshow` handler untouched.

**Task 2 — Full docket persistence through job creation and ingest (PLIST-02):**
- New migration `0015_add_admin_job_source_dockets.py` adds a nullable `admin_jobs.source_dockets ARRAY(VARCHAR(50))` column (chained after 0014, no backfill — old rows keep NULL).
- `AdminJob` model gains `source_dockets`; `AdminJobResponse` schema exposes it.
- `jobs_service.create_job` accepts an optional `source_dockets: list[str] | None` and stores it; `rerun_job` copies `original.source_dockets` onto the new job.
- `api/routers/admin.py` adds two helpers: `_normalize_dockets(primary_docket, source_dockets)` (trim, drop blanks, dedupe preserving order, insert `primary_docket` at index 0 if not already present) and `_dockets_to_ingest_args(normalized_dockets)` (builds `--primary-docket` plus `--dockets` CLI args, or `[]` when the list is empty). `POST /api/admin/jobs` now accepts repeated `source_dockets: list[str] = Form(default=[])` alongside the existing `primary_docket` for backward compatibility, and uses the normalized list across all three creation branches (URL, DO Spaces upload, local-file upload). `POST /jobs/{job_id}/rerun` rebuilds ingest args from `new_job.source_dockets`.
- `pipeline/commands/ingest.py` now writes `Argument.source_dockets = all_dockets or None` alongside the existing `Argument.source_docket = primary_docket or (all_dockets[0] if all_dockets else None)` — the UNIQUE constraint and dedup logic remain keyed on `source_docket` alone, unchanged.
- `pipeline/__main__.py` help text for `--dockets` clarified to state that ingest persists the full ordered list to `Argument.source_dockets`.
- `app/src/routes/admin/pipeline/+page.server.ts` reads `data.getAll('docket[]')`, normalizes client-side (trim/dedupe, same algorithm as the backend), derives `primary_docket = dockets[0]` for backward compatibility, and appends every normalized docket as a repeated `source_dockets` FormData field in both URL and upload branches. No metadata PATCH call is made anywhere in this action.

## Verification Results

- Source assertions (question select removed, DocketPillInput imported/used, old `primary_docket` text input removed, "All Runs" heading present, compound `badgeLabel` call, Step `<th>` removed): **all pass** (verified with a whitespace-tolerant regex variant of the plan's literal-string check, since the project's multiline JSX-like formatting places heading/column text on its own line rather than inline with `>`/`<`).
- `npx svelte-check --tsconfig ./tsconfig.json --threshold error`: **0 errors, 19 warnings** (pre-existing warnings, unrelated to this plan) across both Task 1 and Task 2 verification passes.
- `rg "source_dockets" ...` across all seven target files plus the new migration: **all present**.
- Python syntax check (`ast.parse`) on all seven modified/created Python files: **all pass**.
- Manual unit-check of `_normalize_dockets` / `_dockets_to_ingest_args` via direct import (no DB needed): matches every acceptance-criteria example from the plan (`14-556`,`14-556`,`14-562`,` 14-571 `,`` → `['14-556','14-562','14-571']`; primary-only → single-element list with `--primary-docket`; multi-docket → `--primary-docket X --dockets Y Z`).
- Alembic migration chain confirmed intact: `0013 → 0014 → 0015`.
- `python -m pytest api/tests/test_admin_jobs_service.py pipeline/tests/test_ingest.py -q`: **5 failed, 9 passed**. All 5 failures are pre-existing and environment-caused, not introduced by this plan — confirmed by running the identical test invocation against the pre-change `git stash` state, which reproduces the exact same 5 failures (3 in `test_ingest.py` from an `AttributeError: 'Namespace' object has no attribute 'job_id'` fixture bug, 2 in `test_admin_jobs_service.py` from test-pollution when run alongside `test_ingest.py` — both files pass independently). No live PostgreSQL was reachable in this execution shell (Docker unavailable), consistent with the task's documented environment limitation.

## Deviations from Plan

None — plan executed as written. The plan's verify-script literal string checks (`>All Runs<`, `>Step<`) do not account for the project's existing multiline formatting convention (heading/column text rendered on its own line inside the tag, matching the pre-existing "Recent Runs" and "New Run" headings); source assertions were re-run with an equivalent whitespace-tolerant check and all pass. This is a verification-script nuance, not an implementation deviation — the actual markup exactly matches the UI-SPEC and the plan's `<action>` instructions.

## Known Stubs

None.

## Threat Flags

None — this plan closes the run-start docket persistence gap flagged as T-24-07 in the plan's own threat model (mitigated: router normalizes/dedupes `source_dockets`, stores the ordered list on `admin_jobs`, passes first/rest to ingest, and ingest writes both `Argument.source_docket` and `Argument.source_dockets` in one transaction). No new trust boundaries or attack surface introduced.

## Self-Check: PASSED

- FOUND: app/src/routes/admin/pipeline/+page.svelte
- FOUND: app/src/routes/admin/pipeline/+page.server.ts
- FOUND: api/routers/admin.py
- FOUND: api/services/admin_jobs.py
- FOUND: api/schemas/admin_jobs.py
- FOUND: api/models/models.py
- FOUND: pipeline/__main__.py
- FOUND: pipeline/commands/ingest.py
- FOUND: alembic/versions/0015_add_admin_job_source_dockets.py
- FOUND commit: 80bf6229 (feat(24-04): free-text question, DocketPillInput, compound badge, All Runs heading)
- FOUND commit: e0b2cc90 (feat(24-04): persist all submitted docket pills through job creation and ingest)
