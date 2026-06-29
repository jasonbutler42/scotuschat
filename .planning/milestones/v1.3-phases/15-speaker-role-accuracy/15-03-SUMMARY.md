---
phase: 15-speaker-role-accuracy
plan: "03"
subsystem: ui-admin
tags: [svelte5, form-actions, advocate-role, approve, rerun, pipeline-ui]
dependency_graph:
  requires: [15-02-SUMMARY]
  provides: [approve-form-action, rerun-form-action, advocate-role-dropdowns, create-argument-button, rerun-button]
  affects:
    - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte
    - api/schemas/admin_people.py
    - api/services/admin_people.py
tech_stack:
  added: []
  patterns:
    - use:enhance with custom FormData injection for side assignments at approve time
    - Two-step inline confirm for Re-run (no modal — button label swap + Cancel link)
    - PATCH-before-approve pattern for advocate side persistence
    - Status-gated conditional rendering keyed on argument.status === pipeline
key_files:
  created: []
  modified:
    - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte
    - api/schemas/admin_people.py
    - api/services/admin_people.py
    - api/tests/test_admin_people_schemas_service.py
key-decisions:
  - "[15-03] ParticipantItem schema extended with participant_id + side to enable advocate dropdowns; list_participants_for_job updated to return ArgumentParticipant.id and side"
  - "[15-03] Advocate side selections injected into approve FormData via use:enhance({ formData }) callback, not via nested HTML form fields"
  - "[15-03] approve server action PATCHes advocate sides (Promise.allSettled) then POSTs approve — PATCH failures are non-blocking"
  - "[15-03] Participants fetched in paused state (not only completed) so side data is available for dropdowns before approval"
  - "[15-03] Argument status badge updated to use arg.status enum (pipeline/draft/published) replacing resolved_at/published_at null-check logic"
requirements-completed: [ROLE-02]
coverage:
  - id: D1
    description: "approve and rerun form actions in pipeline +page.server.ts proxy to 15-02 admin endpoints with server-only ADMIN_TOKEN"
    requirement: ROLE-02
    verification:
      - kind: automated_ui
        ref: "npx svelte-check --threshold error — 0 errors"
        status: pass
      - kind: other
        ref: "grep: approve: and rerun: present in +page.server.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "Advocate role dropdown column (Role) in resolve table for non-BENCH participants while argument.status === pipeline"
    requirement: ROLE-02
    verification:
      - kind: automated_ui
        ref: "npx svelte-check --threshold error — 0 errors"
        status: pass
    human_judgment: true
    rationale: "Dropdown conditional rendering and BENCH filtering require live stack with a pipeline-state argument to verify"
  - id: D3
    description: "Create Argument button transitions pipeline run to read-only draft state"
    requirement: ROLE-02
    verification: []
    human_judgment: true
    rationale: "Requires live approve endpoint + database to verify state transition and page re-render"
  - id: D4
    description: "Two-step Re-run button starts a new pipeline run and redirects to new job detail page"
    requirement: ROLE-02
    verification: []
    human_judgment: true
    rationale: "Requires live rerun endpoint + ingest pipeline to verify new job creation and redirect"
duration: 35
completed: "2026-06-25"
status: complete
---

# Phase 15 Plan 03: Pipeline Job Detail Approve UI Summary

**Approve + rerun SvelteKit form actions with server-only ADMIN_TOKEN proxy, advocate role `<select>` column in resolve table, Create Argument CTA that flips run to read-only draft state, and inline two-step Re-run button.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-06-25T00:00:00Z
- **Completed:** 2026-06-25
- **Tasks:** 2 (Task 1 auto-complete, Task 2 built — awaiting human verification)
- **Files modified:** 5

## Accomplishments

- `approve` form action: reads advocate side data from FormData, PATCHes each non-BENCH participant side via `Promise.allSettled`, then POSTs to `/api/admin/jobs/{job_id}/approve`; redirects 303 on success, returns `fail(approveError)` on failure
- `rerun` form action: POSTs to `/api/admin/jobs/{job_id}/rerun`, reads new job id from response body, redirects to `/admin/pipeline/{newJobId}`
- Role column (`<th scope="col">Role</th>`) added to resolve table with advocate `<select>` dropdowns for non-BENCH rows while `argument.status === 'pipeline'`; side state tracked in `advocateSides` Svelte 5 `$state` record
- Create Argument button (full-width, 44px min-height, `#93c5fd` border) visible only while `argument.status === 'pipeline'`; loading label "Creating…"; approveError shown in `role="alert"` `<p>` at `#ef4444`
- Post-approval section: read-only role labels (`#94a3b8`), "This run has been approved. The argument is now in draft." notice, and Re-run two-step confirm button (first click shows confirm label + Cancel link; second click submits `?/rerun`)
- `ParticipantItem` schema extended with `participant_id: int` and `side: Optional[str]`; `list_participants_for_job` updated to return `ArgumentParticipant.id` and side value
- Participants now fetched in `paused` state (not only `completed`) so advocate dropdowns have data during resolve review

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add approve and rerun form actions to pipeline job detail +page.server.ts | cf6c583 | +page.server.ts, admin_people.py, admin_people schema, test |
| 2 | Resolve-table advocate dropdowns, Create Argument button, and Re-run button in +page.svelte | 186e804 | +page.svelte |

## Files Created/Modified

- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — added `approve` and `rerun` form actions; extended `ArgumentPreview` with `status`; changed participant fetch condition to include `paused` state
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — added Role column, advocate dropdowns, Create Argument button, post-approval notice, Re-run two-step confirm; updated argument badge to use `arg.status` enum
- `api/schemas/admin_people.py` — `ParticipantItem` extended with `participant_id: int` and `side: Optional[str]`
- `api/services/admin_people.py` — `list_participants_for_job` returns `ArgumentParticipant.id` (as `participant_id`) and `side.value`
- `api/tests/test_admin_people_schemas_service.py` — `test_participant_item_shape` updated to match new schema fields

## Decisions Made

1. **Use:enhance FormData injection for side assignments:** Rather than putting dropdowns inside a nested HTML form (invalid) or using a separate hidden-field form per participant, advocate sides are tracked in a `$state` record and injected into the approve FormData at submission time via `use:enhance({ formData })`. This keeps the table markup clean and avoids nested form issues.
2. **PATCH-before-approve approach:** The approve server action PATCHes each advocate's side via `Promise.allSettled` before POSTing approve. PATCH failures are non-blocking (approve still proceeds) so a side assignment failure doesn't prevent argument creation.
3. **Extend ParticipantItem with participant_id + side:** The `GET /api/admin/jobs/{job_id}/participants` endpoint's schema was extended (Rule 2 — missing critical functionality) to return the `ArgumentParticipant.id` and `side` values needed for the PATCH calls and dropdown pre-population.
4. **Fetch participants during paused state:** The load function previously only fetched participants when `job.status === 'completed'`. Extended to also fetch when `status === 'paused'` so advocate dropdowns have data during resolve review.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Extended ParticipantItem schema and service with participant_id and side**

- **Found during:** Task 1 (planning the approve action)
- **Issue:** The approve form action needs to PATCH advocate sides before approving. The `GET /api/admin/jobs/{job_id}/participants` endpoint returns `person_id` but not `participant_id` (the `ArgumentParticipant.id` needed for PATCH calls) or `side` (to pre-populate dropdowns). Without these fields, the advocate dropdowns can't be wired to the PATCH endpoint.
- **Fix:** Extended `ParticipantItem` Pydantic schema with `participant_id: int` and `side: Optional[str]`. Updated `list_participants_for_job` to SELECT `ArgumentParticipant.id` and `ArgumentParticipant.side`, returning them as `participant_id` and `side.value`. Updated the test to match. Backward-compatible addition (existing callers can ignore new fields).
- **Files modified:** `api/schemas/admin_people.py`, `api/services/admin_people.py`, `api/tests/test_admin_people_schemas_service.py`
- **Verification:** `test_participant_item_shape` passes; svelte-check 0 errors
- **Committed in:** cf6c583 (Task 1 commit)

**2. [Rule 2 - Missing Critical] Extended participants fetch to include paused state**

- **Found during:** Task 1 (reviewing load function)
- **Issue:** The load function only fetched participants when `job.status === 'completed'`. The advocate dropdowns need participant side data during the resolve review step (`status === 'paused'`).
- **Fix:** Changed the fetch condition from `job.status === 'completed'` to `(job.status === 'completed' || job.status === 'paused')` so participant data is available when the operator needs to assign advocate roles.
- **Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts`
- **Committed in:** cf6c583 (Task 1 commit)

**3. [Rule 2 - Missing Critical] Updated argument status badge to use arg.status enum**

- **Found during:** Task 2 (implementing post-approval state)
- **Issue:** The existing badge logic used `resolved_at/published_at` null checks, computing `'resolved'` and `'pending'` labels. With `arg.status` now available (from 15-01 migration + 15-02 service), the badge should use the correct `'pipeline'/'draft'/'published'` enum values so the post-approval state (`argument.status !== 'pipeline'`) gate works correctly.
- **Fix:** Updated `argStatus` computation to `arg.status ?? (derived fallback)` and updated badge color/label maps to match the three-state enum.
- **Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte`
- **Committed in:** 186e804 (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 2 — missing critical functionality)
**Impact on plan:** All three are required for the approve flow to function. No scope creep.

## Known Stubs

None — all functionality is wired. The advocate side dropdowns read from `data.participants`, the approve form injects side data into FormData at submission time, and the server action makes real PATCH + POST calls to 15-02 endpoints.

## Threat Flags

None — all new code is within the existing admin SvelteKit server module behind `$env/static/private`. The `ADMIN_TOKEN` is only referenced server-side and never sent to the browser (T-15-03-TOKENLEAK mitigated). The approve endpoint's double-approve guard (T-15-03-DOUBLEAPPROVE) is enforced by the 15-02 backend — the UI hides the button post-approval as defense-in-depth.

## Self-Check: PASSED

- [x] `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` exists and has `approve:` and `rerun:` actions
- [x] `app/src/routes/admin/pipeline/[job_id]/+page.svelte` exists and has Role column, Create Argument button, Re-run two-step confirm
- [x] Commit cf6c583 exists (Task 1)
- [x] Commit 186e804 exists (Task 2)
- [x] svelte-check 0 errors
- [x] No `export let`, no `$:`, no `svelte/store` in +page.svelte
- [x] `ParticipantItem` has `participant_id` and `side` fields
- [x] `test_participant_item_shape` passes
