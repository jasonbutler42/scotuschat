---
phase: 07-pipeline-runner
plan: "07"
subsystem: admin-pipeline-ui
tags: [discrepancy-review, typeahead, use-enhance, gap-closure]
dependency_graph:
  requires: [07-06]
  provides: [discrepancy-review-ux-complete]
  affects: [app/src/routes/admin/pipeline/[job_id]/+page.svelte, api/routers/admin.py, api/services/admin_jobs.py]
tech_stack:
  added: []
  patterns: [use:enhance, server-load-fetch, people-typeahead]
key_files:
  created: []
  modified:
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte
    - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
    - api/routers/admin.py
    - api/services/admin_jobs.py
decisions:
  - "[07-07]: HIT rows pre-dispositioned as 'confirmed' in rowStates init effect — no Confirm click needed"
  - "[07-07]: Single Change button on HIT rows (auto_resolved===true) regardless of current disposition"
  - "[07-07]: getRowCandidates merges data.people before row.candidates for de-duplication by id"
  - "[07-07]: AddNewPersonForm uses use:enhance — SvelteKit handles devalue deserialization automatically"
  - "[07-07]: GET /api/admin/people added to admin router; list_people() uses Person+Role outerjoin ordered by full_name"
metrics:
  duration_seconds: 371
  completed_date: "2026-06-17T15:14:08Z"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 4
---

# Phase 07 Plan 07: Discrepancy Review HIT-row UX + Save Person Summary

**One-liner:** HIT rows pre-confirmed with a single Change button, Change typeahead lists full people roster via server-loaded data, Add-person uses use:enhance for reliable devalue deserialization.

## Tasks Completed

| Task | Name | Commit | Status |
|------|------|--------|--------|
| 1 | Load all people in [job_id] server load for typeahead | 332e571 | DONE |
| 2 | HIT-row Change UX + people-backed typeahead + use:enhance add-person | 01097ae | DONE |
| 3 | Verify discrepancy review UX in browser | — | DONE (human-verified: all 5 checks approved) |

## What Was Built

### Task 1: API + server-side people list

**`api/services/admin_jobs.py`** — new `list_people()` function:
- SELECT Person + Role.name (outerjoin) ordered by full_name
- Returns `list[dict]` with keys: `id`, `full_name`, `role_name`
- Same join pattern used by `pipeline/commands/resolve.py` lines 185-189

**`api/routers/admin.py`** — new `GET /api/admin/people` route:
- Protected by existing router-level `verify_admin_token` dependency
- Returns `list[PersonResponse]`

**`app/src/routes/admin/pipeline/[job_id]/+page.server.ts`** — `load()` updated:
- Fetches `GET /api/admin/people` with `X-Admin-Token` header
- Defaults to `[]` on non-OK response (job view still renders)
- Returns `{ job, people }` — `people: Array<{id, full_name, role_name}>`

### Task 2: Svelte component UX fixes (3 gaps)

**Gap 1a — HIT-row pre-disposition:**
- `Discrepancy` interface extended with `auto_resolved?: boolean | null`
- `rowStates` init `$effect`: when `row.auto_resolved === true`, initializes `disposition: 'confirmed'` and `person_id: row.auto_match_id` — no explicit Confirm click required
- MISS rows unchanged: `disposition: null`
- "Only initialise keys not already tracked" guard preserved

**Gap 1a — Single Change button for HIT rows:**
- Column 3 rewritten with three branches:
  1. `row.auto_resolved === true` → always shows "Change" button (calls `handleCorrect`)
  2. MISS row with `disposition !== null` → shows "Override" button
  3. MISS row with `disposition === null` → shows Confirm (if `auto_match_id`) + Correct buttons

**Gap 1b — People-backed typeahead:**
- `getRowCandidates()` now merges `data.people` before `row.candidates` and `extraCandidates`
- De-duplicated by `id` using a `Set<number>`
- HIT rows (which have `candidates: []`) now list the full roster in the Change typeahead

**Gap 2 — use:enhance add-person form:**
- Removed `handleAddPerson` raw-fetch function
- AddNewPersonForm wrapped in `<form method="POST" action="?/addPerson" use:enhance={...}>`
- Inputs given `name="full_name"` and `name="role_name"` attributes
- `use:enhance` callback: sets `submittingNewPerson = true` before, `false` after
- On `result.type === 'success'`: reads `result.data.person` (already devalue-deserialized by SvelteKit), pushes to `extraCandidates`, selects person, clears form
- On `result.type === 'failure'`: sets `newPersonError` from `result.data.error`
- Does NOT call `update()` with reset — preserves `rowStates`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all data flows are wired.

## Threat Flags

None — no new network endpoints or auth paths introduced beyond the planned `GET /api/admin/people` which is protected by the existing admin token dependency.

## Verification

### Automated

- `svelte-check`: 0 errors, 5 pre-existing warnings (all in ChatBubble.svelte and login/+page.svelte)
- `must_haves.key_links` satisfied:
  - `data.people` pattern present in `getRowCandidates`
  - `use:enhance` present on AddNewPersonForm
  - `auto_resolved` present in rowStates init branch

### Human Verification (Task 3) — PASSED

All 5 checks approved by operator:
1. HIT rows show ONE "Change" button, no "Confirm" button; Continue Resolve appears once all rows are dispositioned.
2. Change typeahead on HIT rows lists many existing people (full roster), not just "— Add new person —".
3. Selecting an existing person from the typeahead flips the row to "Corrected" with that person selected.
4. Picking "— Add new person —", filling Full name + Role, and clicking Save person: form dismisses without hang; new person is auto-selected.
5. Hard-refresh: new person appears in the typeahead list because load() fetches the full people list from the API.

## Self-Check: PASSED

- `api/services/admin_jobs.py` modified: confirmed (list_people added)
- `api/routers/admin.py` modified: confirmed (GET /api/admin/people added)
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` modified: confirmed (people fetch in load)
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` modified: confirmed (all 4 sub-tasks)
- Commit 332e571 (Task 1): confirmed
- Commit 01097ae (Task 2): confirmed
- Fix commit ddf8639 (rename MISS-row Correct → Select button): confirmed
- Task 3 human verification: all 5 checks approved 2026-06-17
- Plan 07-07: COMPLETE
