---
phase: 07-pipeline-runner
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, boto3, subprocess, digitalocean-spaces, admin-jobs]

# Dependency graph
requires:
  - phase: 05-admin-foundation
    provides: AdminJob ORM model, AdminJobStatus/AdminJobStep enums, migration 0003
  - phase: 06-auth
    provides: admin auth layer (verify_admin_token) that Plan 02 routes will rely on
provides:
  - api/schemas/admin_jobs.py: AdminJobResponse, AdminJobCreateURL, ResolveMatch, ResolveRequest, PersonCreate, PersonResponse
  - api/services/spaces.py: upload_pdf_to_spaces via boto3 S3 client
  - api/services/pipeline_spawn.py: spawn_pipeline_step detached Popen with sys.executable
  - api/services/admin_jobs.py: create_job, get_job, list_jobs, try_advance_ingest_to_parse, try_advance_parse_to_resolve, get_run_id_for_step, resolve_job, create_person_for_job
  - api/core/config.py: five optional DO Spaces Settings fields
  - requirements.txt: boto3>=1.34 dependency
affects:
  - 07-02 (admin routes consume all services and schemas built here)
  - 07-03 (pipeline ingest/parse/resolve commands consume spawn utility and config)
  - 07-04 (SvelteKit pipeline page calls routes built in 07-02)
  - 07-05 (resolve UI calls routes built in 07-02)

# Tech tracking
tech-stack:
  added:
    - boto3>=1.34 (official AWS SDK — pending human legitimacy verification at checkpoint)
  patterns:
    - Atomic rowcount guard: update(AdminJob).where(step+status).values(...).execution_options(synchronize_session=False); return result.rowcount == 1; no RETURNING
    - Fire-and-forget subprocess: sys.executable + CREATE_NEW_PROCESS_GROUP (win32) or start_new_session=True (posix); never .wait()/.communicate()
    - Validate-first resolve: select(Person) for every person_id before any alias/utterance write
    - Resumable run-id lookup: re-derive pipeline_run id from (argument_id, step) — no admin_jobs column needed (PIPE-17)

key-files:
  created:
    - api/schemas/admin_jobs.py
    - api/services/spaces.py
    - api/services/pipeline_spawn.py
    - api/services/admin_jobs.py
  modified:
    - api/core/config.py
    - requirements.txt

key-decisions:
  - "DO Spaces credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, DO_SPACES_*) belong to the FastAPI service in DO App Platform — never SvelteKit; boto3 runs in the FastAPI container (upload route) and in pipeline subprocesses (--spaces-key download), never in the browser or Node.js"
  - "Atomic advance guards use rowcount == 1 without RETURNING — RETURNING nullifies rowcount on some PG driver versions (Pattern 3)"
  - "get_run_id_for_step re-derives pipeline_run id from (argument_id, step) ordered by created_at DESC — no extra admin_jobs column needed; migration 0003 stays frozen (anti-pattern in RESEARCH.md)"
  - "resolve_job validates all person_ids before any alias/utterance write to prevent partial mutations on bad input (Pitfall 5)"
  - "normalize_label imported from pipeline.commands.resolve — single source of truth for label normalization"

patterns-established:
  - "Atomic step-advance guard: rowcount == 1 check, no RETURNING, execution_options(synchronize_session=False)"
  - "All update() calls use execution_options(synchronize_session=False) — mandatory project guard"
  - "Validate-first pattern: all external ids verified before any DB mutations"

requirements-completed: [PIPE-12, PIPE-13, PIPE-14, PIPE-15, PIPE-16, PIPE-17]

# Metrics
duration: ~35min (Tasks 1-3 across two sessions; paused at checkpoint)
completed: 2026-06-16
---

# Phase 07 Plan 01: Pipeline Runner Backend Contract Layer Summary

**FastAPI admin-job service layer: Pydantic schemas, boto3 Spaces upload, detached subprocess spawn, and full CRUD + atomic advance guards + validate-first resolve built ahead of routes**

## Performance

- **Duration:** ~35 min (Tasks 1-2 in prior session; Task 3 in this session)
- **Started:** 2026-06-16
- **Completed:** 2026-06-16 (Tasks 1-3; paused at boto3 legitimacy checkpoint)
- **Tasks:** 3 of 4 complete (Task 4 is checkpoint:human-verify awaiting approval)
- **Files modified:** 6

## Accomplishments

- Six Pydantic v2 schemas built with `from_attributes` on response models, enum imports from ORM
- DO Spaces upload service using boto3 S3 client; five optional config fields added (API starts without Spaces creds)
- Fire-and-forget subprocess spawn with platform detection (win32 vs posix), `sys.executable`, `DEVNULL` output, no `.wait()`/`.communicate()`
- Eight admin_jobs service functions including atomic rowcount advance guards, PIPE-17 resumable run-id lookup, validate-first resolve with SpeakerAlias upsert and Utterance/ArgumentParticipant UPDATE, and inline person/role creation

## Deployment-Tier Note

The DO Spaces credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `DO_SPACES_BUCKET`, `DO_SPACES_ENDPOINT`, `DO_SPACES_REGION`) **must be configured on the FastAPI service** in the DO App Platform dashboard — not on the SvelteKit service. boto3 runs in:

1. The FastAPI container (Plan 02 upload route)
2. Pipeline subprocesses spawned by FastAPI (Plan 03 `--spaces-key` download)

It never runs in SvelteKit (Node.js). Adding these env vars to the wrong service will cause boto3 import failures at runtime.

## Task Commits

1. **Task 1: boto3, DO Spaces config, admin-job schemas** - `e123c20` (feat)
2. **Task 2: DO Spaces upload service and subprocess spawn** - `6cb2007` (feat)
3. **Task 3: admin_jobs service** - `1cb41c0` (feat)
4. **Task 4: checkpoint:human-verify** — AWAITING boto3 legitimacy confirmation

## Files Created/Modified

- `api/schemas/admin_jobs.py` — AdminJobResponse, AdminJobCreateURL, ResolveMatch, ResolveRequest, PersonCreate, PersonResponse
- `api/services/spaces.py` — get_spaces_client(), upload_pdf_to_spaces(file_bytes, key)
- `api/services/pipeline_spawn.py` — spawn_pipeline_step(step, job_id, extra_args)
- `api/services/admin_jobs.py` — 8 service functions, 8x synchronize_session=False guards
- `api/core/config.py` — 5 optional DO Spaces fields with deployment-tier comment
- `requirements.txt` — boto3>=1.34 added

## Decisions Made

- DO Spaces credentials belong to FastAPI service container, not SvelteKit (boto3 is a Python library; never runs in Node.js)
- Atomic advance guards use `result.rowcount == 1` without RETURNING — RETURNING nullifies rowcount on certain PG driver versions (Pattern 3)
- `get_run_id_for_step` re-derives pipeline_run id from `(argument_id, step)` — no new admin_jobs column; migration 0003 remains frozen
- `resolve_job` validates all person_ids before any alias/utterance write — prevents partial mutations on invalid input (Pitfall 5)
- `normalize_label` imported from `pipeline.commands.resolve` — single normalization source of truth

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused `insert` import**
- **Found during:** Task 3 (admin_jobs service)
- **Issue:** `from sqlalchemy import insert, select, update` — `insert` is not used; the service uses `db.add()` for inserts
- **Fix:** Removed `insert` from the import line
- **Files modified:** api/services/admin_jobs.py
- **Committed in:** 1cb41c0 (part of Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug/cleanup)
**Impact on plan:** Minor cleanup only. No scope creep.

## Issues Encountered

None — all three tasks executed cleanly. Plan is paused at the boto3 package legitimacy checkpoint (blocking-human gate, cannot be auto-approved).

## User Setup Required

The following env vars must be added to the **FastAPI service** in DO App Platform (not SvelteKit):

| Env Var | Source |
|---------|--------|
| `AWS_ACCESS_KEY_ID` | DO Console → API → Spaces Keys → Generate New Key (access key) |
| `AWS_SECRET_ACCESS_KEY` | DO Console → API → Spaces Keys (secret shown once at creation) |
| `DO_SPACES_BUCKET` | DO Console → Spaces → bucket name |
| `DO_SPACES_ENDPOINT` | e.g. `https://nyc3.digitaloceanspaces.com` |
| `DO_SPACES_REGION` | e.g. `nyc3` |

These are optional for URL-mode jobs (PIPE-12). They are required for file-upload mode (PIPE-13) and for the pipeline subprocess to download the PDF from Spaces.

## Next Phase Readiness

- Plan 01 is functionally complete pending boto3 legitimacy checkpoint approval
- Plan 02 (admin routes) can wire all schemas + service functions from this plan
- No blockers for Plan 02 execution other than the pending checkpoint

## Known Stubs

None — all functions are fully implemented with real DB operations. No placeholder returns.

## Threat Flags

No new trust boundaries introduced beyond those in the plan's threat model. All mitigations applied:
- T-07-02 (shell=False): spawn_pipeline_step uses shell=False (default) with typed argv
- T-07-03 (Spaces creds): credentials are server-only env vars, never returned in responses
- T-07-SC (boto3 supply chain): blocking-human checkpoint pending human verification

---
*Phase: 07-pipeline-runner*
*Completed: 2026-06-16 (partial — paused at checkpoint)*
