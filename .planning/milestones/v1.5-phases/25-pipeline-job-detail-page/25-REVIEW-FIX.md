---
phase: 25-pipeline-job-detail-page
fixed_at: 2026-07-07T19:20:00Z
review_path: .planning/phases/25-pipeline-job-detail-page/25-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 25: Code Review Fix Report

**Fixed at:** 2026-07-07T19:20:00Z
**Source review:** .planning/phases/25-pipeline-job-detail-page/25-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 7 (critical_warning scope — CR-01, WR-01 through WR-06; IN-01/IN-02 excluded by scope)
- Fixed: 7
- Skipped: 0

## Fixed Issues

### CR-01: Newly created person's Bench/Advocate side is silently discarded, then reverted on next save

**Files modified:** `app/src/lib/components/ResolveCard.svelte`
**Commit:** dc8ad284
**Applied fix:** Threaded the `side` value returned by `CreatePersonPopover`'s `onCreated(person, side)`
callback through `ResolveCard`. `handlePersonCreated` now takes `participantId` and `side` as explicit
parameters (using `row.participant_id`, already in scope at the call site, rather than a
`raw_speaker_label` lookup), writes the chosen side into `pendingSideOverrides[participantId]`, and
calls `submitRow(participantId)` immediately so the corrected side is persisted right away instead of
being left to an unrelated field blur to accidentally overwrite it.
**Verification note:** this closes a state-sync/logic gap (stale client state reverting a DB write on
next save) — recommend a manual click-through of "Create new person" → confirm Bench/Advocate persists
after a follow-up Title blur, in addition to this review-fix pass. Commit status: `fixed: requires human verification`.

### WR-01: Dead pre-Phase-25 code path in the `approve` action silently swallows PATCH failures

**Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts`
**Commit:** b05b5d70
**Applied fix:** Removed the dead `participant_side[<id>]` field-parsing loop, the job fetch for
`argument_id`, and the `Promise.allSettled(...).catch(() => undefined)` PATCH block from the `approve`
action (no component renders that field name anymore — `ResolveCard`'s own `?/saveResolveRow` owns
side/title persistence). Updated the action's docstring to remove the outdated "atomic capture of side
assignments at approve time (D-09)" claim. Also dropped the now-unused `request` destructure from the
action's parameters.

### WR-02: `create_person_for_job` can silently create an orphaned Person when `raw_speaker_label` is set without `side`

**Files modified:** `api/services/admin_jobs.py`
**Commit:** 806f6eb6
**Applied fix:** Added a `ValueError` raised immediately after the participant lookup (before any Role
or Person row is created) when `raw_speaker_label` is provided but `body.side` is `None`. This follows
the existing "validate before mutate" ordering already used for the unknown-`raw_speaker_label` case in
the same function, and keeps the Person insert and participant-scoping validation in sync. Updated the
function docstring to describe the new guard. No existing test exercises this combination, so no test
behavior changed.

### WR-03: `ResolveRowUpdate.title` has no length validation against the `String(500)` DB column

**Files modified:** `api/schemas/admin_jobs.py`
**Commit:** 861db367
**Applied fix:** Changed `title: Optional[str] = None` to `title: Optional[str] = Field(default=None, max_length=500)`
(imported `Field` from `pydantic`) so FastAPI's native Pydantic validation rejects over-length titles
with a 422 before they reach `update_resolve_row_for_job`'s `db.execute`, matching the 422 pattern used
elsewhere in this schema module. Confirmed `ResolveRowUpdate` is a FastAPI route body parameter
(`api/routers/admin.py:518`), so this validation is enforced automatically by the framework.

### WR-04: "Continue Resolve" can never appear when a paused job has zero discrepancies

**Files modified:** `app/src/lib/components/ResolveCard.svelte`
**Commit:** 8492f515
**Applied fix:** Changed the `disc.length === 0` branch of `allDispositioned` from `return false` to
`return true`, so a paused job with an empty (or already-resolved) discrepancy list is treated as fully
dispositioned and the "Continue Resolve" button renders, submitting an empty `matches: []` array to
`?/resolve`. Verified the SvelteKit `resolve` action defaults `matches` to `[]` when absent and the
backend `resolve_job` loop over `matches` handles an empty list correctly (still transitions the job to
`COMPLETED`).
**Verification note:** this is a condition/logic fix (inverted boolean short-circuit) — recommend
manually confirming a paused job with zero discrepancies now shows "Continue Resolve" and successfully
transitions to `COMPLETED`. Commit status: `fixed: requires human verification`.

### WR-05: Dead duplicate `list_people` in `admin_jobs.py`

**Files modified:** `api/services/admin_jobs.py`
**Commit:** 47f36a6e
**Applied fix:** Deleted the unused `list_people` function (and its section header comment) from
`admin_jobs.py`. Confirmed via repo-wide search that only `admin_people.list_people` (the one wired to
`GET /api/admin/people`) has callers; the `Role` import used inside the deleted function remains needed
elsewhere in the file (`create_person_for_job`), so no import cleanup was required.

### WR-06: Local-upload job-creation path issues a no-op `db.commit()`

**Files modified:** `api/routers/admin.py`
**Commit:** d85cb61e
**Applied fix:** Removed the redundant `await db.commit()` in the local-upload branch (no
`update()`/`db.add()` happens between `create_job()`'s commit and this line), keeping
`await db.refresh(job)` for serialization, and added a short comment explaining why no commit is needed
here.

## Skipped Issues

None — all in-scope findings were fixed.

---

_Fixed: 2026-07-07T19:20:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
