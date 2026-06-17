---
phase: 07-pipeline-runner
fixed_at: 2026-06-17T15:45:00Z
review_path: .planning/phases/07-pipeline-runner/07-REVIEW.md
iteration: 2
findings_in_scope: 13
fixed: 13
skipped: 0
status: all_fixed
---

# Phase 07: Code Review Fix Report

**Fixed at:** 2026-06-17T15:45:00Z
**Source review:** .planning/phases/07-pipeline-runner/07-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope: 13 (5 Critical + 8 Warning; Info excluded per fix_scope=critical_warning)
- Fixed: 13
- Skipped: 0

## Fixed Issues

### CR-01: HIT rows appended to `discrepancies` — COMPLETED path is dead code

**Files modified:** `pipeline/commands/resolve.py`
**Commit:** `4cab328`
**Applied fix:** Added a separate `misses: list[str]` list that receives only MISS raw labels. The step-6 gate and both post-session guards now key on `misses` rather than `discrepancies`. The full `discrepancies` list (HITs + MISSes) is still written to the JSONB column on the PAUSED path; on the COMPLETED (all-auto-resolved) path, `discrepancies` is also written to JSONB so the browser can show confirmed auto-matches. CLI print now iterates `misses` and reports only unresolved labels.
**Status:** fixed: requires human verification

---

### CR-02: `resolve_job` does not verify PAUSED state before writing aliases

**Files modified:** `api/services/admin_jobs.py`
**Commit:** `6802463`
**Applied fix:** Added a PAUSED state guard immediately after loading the job in `resolve_job`. Raises `ValueError` with descriptive message if `job.status != AdminJobStatus.PAUSED`. The existing router try/except at `admin.py:249-252` re-raises this as HTTP 422 — no router changes required. Also renumbered sub-step comments for consistency.

---

### CR-03: `continueSubmitting` is never reset on successful resolve submit

**Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte`
**Commit:** `64c6bbf`
**Applied fix:** Added `continueSubmitting = false;` in the success branch of the `use:enhance` callback, before `await update({ reset: false })`. This ensures the button is re-enabled and shows "Continue Resolve" even if `invalidateAll` is slow to flip `data.job.status`.

---

### CR-04: `rowStates` never evicts stale keys — operator can submit outdated mappings

**Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte`
**Commit:** `5352b60`
**Applied fix:** Added a stale-key eviction loop at the top of the `$effect` that initialises `rowStates`. Before seeding new rows, computes `incomingKeys` as a Set from the current discrepancy set, then deletes any `rowStates` key not in that set. Prevents stale dispositions from prior resolve attempts persisting into a new run.

---

### CR-05: `--dry-run` early return inside session block persists a PipelineRun row

**Files modified:** `pipeline/commands/parse.py`
**Commit:** `7d6677d`
**Applied fix:** Restructured `_run_parse_inner` so pages extraction (Step 3) and parse passes (Steps 4-5) use `source_run.pdf_path` directly, without creating a `PipelineRun` row. Strategy is tracked in a local `parse_strategy` variable. The dry-run exit check now occurs before `session.add(run)`, so `session.__aexit__` commits nothing in dry-run mode. `PipelineRun` creation was moved past the dry-run gate with `strategy=parse_strategy` set at construction. PDF-path validation errors now raise `ValueError` instead of calling `_fail_run`.
**Status:** fixed: requires human verification

---

### WR-01: `asyncio.get_event_loop()` deprecated in Python 3.10+

**Files modified:** `api/routers/admin.py`
**Commit:** `c7ad7af`
**Applied fix:** Replaced `asyncio.get_event_loop()` with `asyncio.get_running_loop()`. (Batched with WR-04 and WR-06 in the same commit.)

---

### WR-02: `create_person_for_job` accepts `job_id` but never validates it

**Files modified:** `api/services/admin_jobs.py`, `api/routers/admin.py`
**Commit:** `5829331`
**Applied fix:** Added job-existence and PAUSED-state guards at the top of `create_person_for_job`. Raises `ValueError` if the job is not found or not PAUSED. Updated the router's call site to wrap with `try/except ValueError` and re-raise as HTTP 422, mirroring the `resolve_job` pattern.

---

### WR-03: `stepStatus` returns all `'pending'` when job fails with `current_step=null`

**Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte`
**Commit:** `bb51888`
**Applied fix:** Rewrote `stepStatus` to handle `current_step === null/undefined`. `current` is now typed `StepName | undefined` and `currentIdx` defaults to `-1` when undefined. In the failed branch, when `currentIdx === -1`, the first step in `STEP_ORDER` renders as `'failed'` and the rest as `'pending'`, giving the operator a meaningful visual indication of where the job died.
**Status:** fixed: requires human verification

---

### WR-04: `pdf_file.content_type` is client-supplied — magic-bytes check is missing

**Files modified:** `api/routers/admin.py`
**Commit:** `c7ad7af`
**Applied fix:** Added magic-bytes validation after the content-type check. Reads the first 4 bytes, seeks back to 0, and raises HTTP 422 if the header does not equal `b"%PDF"`. This provides a second validation layer independent of the client-supplied Content-Type. (Batched with WR-01 and WR-06.)

---

### WR-05: `resolve_job` broadens Utterance UPDATE to all parse runs when `parse_run_id` is None

**Files modified:** `api/services/admin_jobs.py`
**Commit:** `110bb43`
**Applied fix:** Added an explicit `None` check after fetching `parse_run_id`. Raises `ValueError` with a descriptive message if `parse_run_id` is None. Simplified the Utterance UPDATE WHERE clause to always include `Utterance.pipeline_run_id == parse_run_id` (the conditional branch was removed since None now raises before reaching it).

---

### WR-06: Orphaned job row created if DO Spaces upload fails in upload mode

**Files modified:** `api/routers/admin.py`
**Commit:** `c7ad7af`
**Applied fix:** Wrapped the Spaces upload call in `try/except Exception`. On upload failure, marks the `AdminJob` row as FAILED with a descriptive error message and commits, then raises HTTP 502 to the client. Prevents a dangling PENDING job with no subprocess. (Batched with WR-01 and WR-04.)

---

### WR-07: `if args.job_id:` truthy check silently skips writes when `job_id=0`

**Files modified:** `pipeline/commands/ingest.py`, `pipeline/commands/parse.py`, `pipeline/commands/resolve.py`
**Commit:** `1b0bac4`
**Applied fix:** Applied `replace_all` to replace every occurrence of `if args.job_id:` with `if args.job_id is not None:` across all three pipeline command files (11 locations total).

---

### WR-08: `getRowCandidates` called twice per correcting-row render cycle

**Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte`
**Commit:** `0f7d514`
**Applied fix:** Added `{@const candidates = getRowCandidates(row, rowKey)}` immediately after `{@const listId = ...}` in the correcting-row template block. Both the `oninput` handler and the `{#each}` datalist source now reference `candidates`, halving array construction work per render cycle.

---

_Fixed: 2026-06-17T15:45:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
