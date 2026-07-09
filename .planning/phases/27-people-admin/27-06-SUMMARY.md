---
phase: 27-people-admin
plan: 06
subsystem: ui
tags: [sveltekit, svelte5-runes, forms, admin-service, create-flow]

# Dependency graph
requires:
  - phase: 27-people-admin
    plan: 05
    provides: "Restructured /admin/people/[id] editor (Identity/Photo/Biography/Person Type cards); Merge/Delete cards guarded behind {#if data.person.id} for reuse by this create route; form=\"save-form\" cross-form association idiom"
  - phase: 27-people-admin
    plan: 03
    provides: "POST /people (create_person service, status 201, response_model PersonDetail) behind the standard admin-auth dependency"
provides:
  - "/admin/people/new route: blank load() + create action, reusing the [id] editor's Identity/Person Type card structure per D-07"
  - "D-08 minimum-required validation (full_name + explicit Bench/Advocate choice) before POST /api/admin/people"
  - "Static /admin/people/new resolves ahead of dynamic /admin/people/[id] (confirmed via npm run build output ordering)"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Three-state segmented toggle (boolean | null) — extends the [id] editor's Bench/Advocate toggle pattern with a null 'not yet chosen' state so neither segment renders selected on first load; hidden input submits '' when null so the server can distinguish 'not chosen' from a real true/false value and return the D-08 'Choose Bench or Advocate to continue.' message"
    - "Redirect-after-create idiom — POST /api/admin/people returns the full PersonDetail; the action reads .id and throws redirect(303, '/admin/people/' + id), identical in shape to the [id] editor's merge action redirect"

key-files:
  created:
    - app/src/routes/admin/people/new/+page.server.ts
    - app/src/routes/admin/people/new/+page.svelte
  modified: []

key-decisions:
  - "Photo and Biography cards are omitted entirely on the create route (not just Photo, as the plan's item 4 literally called out) — both cards share a single <form action=\"?/photo\"> on the [id] editor (Pitfall 7 extended), that action does not exist on this route, and D-08 explicitly excludes bio_text/photo_url from the create payload ('filled in on the editor after redirect'). Rendering Biography without a valid submit target would either 404 on submit or silently discard input, so both cards are hidden together rather than splitting Biography into its own inert form."
  - "Removed the [id] template's data.person.id-keyed $effect that resets isJustice to `data.person.is_justice ?? false` — copying it verbatim would have overridden isJustice back to false on mount, defeating D-08's 'neither Bench nor Advocate pre-selected' requirement (this route has no soft-navigation between different person ids to guard against, unlike [id])."
  - "Merge and Delete blocks (and their backing $state/fetchMergePreview) are removed from the component entirely rather than left in place behind {#if data.person.id} — this route has no merge/delete actions for those forms to target, and TypeScript's Actions-derived form? typing correctly rejected the dead mergeError/deleteError references during npm run check (caught and fixed before commit)."
  - "load() returns only { person } — the merge-picker (people) and delete-eligibility (can_delete/delete_block_count) fields the [id] route needs are omitted since the corresponding cards never render here; keeping them would have required an unused, incorrectly-typed empty array (people: [] inferred as never[], another npm run check catch)."
  - "create action name is 'create' (not 'save') targeting form action=\"?/create\", to keep the create and edit flows' server actions distinctly named even though they share one visual template (D-07)."

requirements-completed: [PDIR-07, PEDIT-11, PEDIT-12]

coverage:
  - id: D1
    description: "/admin/people/new's create action POSTs {full_name, is_justice} to POST /api/admin/people (not a job-scoped endpoint) after D-08 validation, and redirects 303 into the new person's editor using the response id"
    requirement: "PDIR-07"
    verification:
      - kind: unit
        ref: "grep confirms the fetch target is `${FASTAPI_BASE_URL}/api/admin/people` with zero /jobs/ matches; fail(400) messages match 'Full name is required.' and 'Choose Bench or Advocate to continue.' verbatim; redirect(303, '/admin/people/' + created.id) present"
        status: pass
      - kind: other
        ref: "npm run check (0 errors) and npm run build (succeeds) — build output confirms admin/people/new/_page.*.js entries exist and are distinct from admin/people/_id_/_page.*.js"
        status: pass
    human_judgment: false
  - id: D2
    description: "The create page renders the shared editor template with Merge/Delete/Photo/Biography absent and the Person Type toggle unselected on first load"
    requirement: "PEDIT-11, PEDIT-12"
    verification:
      - kind: unit
        ref: "grep confirms zero ?/merge, ?/delete, 'Merge into another person', or 'Delete person' matches in +page.svelte; isJustice initialized from data.person.is_justice (null) with no fallback to false"
        status: pass
      - kind: other
        ref: "npm run check && npm run build — both pass with 0 errors"
        status: pass
    human_judgment: true
    rationale: "Visual verification of the slide-reveal animation when Bench is selected, and the actual absence of any layout gap where Merge/Delete/Photo would have sat, cannot be confirmed by static grep/build checks alone — deferred to phase-level UAT alongside Plan 27-05's deferred visual checks."

duration: 20min
completed: 2026-07-09
status: complete
---

# Phase 27 Plan 6: Create Person Route Summary

**`/admin/people/new` — a new static route reusing the `/admin/people/[id]` editor's Identity/Person Type card structure, with a three-state (unselected) Bench/Advocate toggle, D-08 minimum validation, and a create action that POSTs to the general `POST /api/admin/people` endpoint before redirecting into the freshly-created person's editor**

## Performance

- **Duration:** 20 min
- **Started:** 2026-07-09T05:20:00Z
- **Completed:** 2026-07-09T05:40:00Z
- **Tasks:** 2
- **Files created:** 2

## Accomplishments
- `app/src/routes/admin/people/new/+page.server.ts`: blank `load()` returning `{ person }` with `id: null` and `is_justice: null`; a `create` action validating D-08's minimum (full name + explicit Bench/Advocate choice), POSTing `{full_name, is_justice}` to `POST /api/admin/people`, and redirecting 303 into `/admin/people/{new id}`
- `app/src/routes/admin/people/new/+page.svelte`: adapts the Plan 27-05 `[id]` editor's Identity and Person Type cards verbatim in structure/styling, with a three-state `isJustice` toggle (`boolean | null`) so neither Bench nor Advocate reads as selected until the operator picks one
- Confirmed via `npm run build` output that `/admin/people/new`'s server/component bundles are distinct from `/admin/people/[id]`'s, verifying SvelteKit's static-route-wins-over-dynamic-route precedence holds for this pair
- Merge, Delete, Photo, and Biography are all absent from the create page — documented rationale in Decisions Made below

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the /admin/people/new load and create action** - `7eeb0263` (feat)
2. **Task 2: Create the /admin/people/new component from the shared editor template** - `8b2b4dc3` (feat) — also folds in a small `+page.server.ts` simplification (see Deviations) required to fix type errors this task's component surfaced

## Files Created
- `app/src/routes/admin/people/new/+page.server.ts` - blank `load()`; `create` action with D-08 validation, POST to `/api/admin/people`, redirect-after-create
- `app/src/routes/admin/people/new/+page.svelte` - Identity + Person Type cards adapted from the `[id]` template; three-state Bench/Advocate toggle; no Merge/Delete/Photo/Biography

## Decisions Made
- Photo and Biography cards are both omitted on the create route, not just Photo as literally called out in Task 2's action item 4 — see key-decisions above for the full rationale (shared `?/photo` form/action doesn't exist here; D-08 excludes bio/photo from the create payload).
- Removed the `[id]` template's `$effect` that resets `isJustice` on `data.person.id` change — carrying it forward verbatim would have silently reset `isJustice` from `null` to `false` on mount, defeating the "neither pre-selected" requirement.
- Removed the Merge/Delete markup, state, and `fetchMergePreview` helper entirely (rather than leaving them dead-code-guarded behind `{#if data.person.id}`) after `npm run check` correctly flagged `form?.mergeError`/`form?.deleteError` as invalid against this route's `Actions` type (only `create` exists) and `data.people` as untyped (`load()` never returns it).
- `load()` now returns only `{ person }` instead of also returning `people`/`can_delete`/`delete_block_count` — those fields backed only the Merge/Delete cards, which don't exist on this route.
- Named the action `create` (not `save`) so `/admin/people/new`'s server action and `/admin/people/[id]`'s `save` action stay distinctly named despite sharing one visual template.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed dead-but-broken Merge/Delete markup and simplified load() after npm run check caught real type errors**
- **Found during:** Task 2, first `npm run check` run
- **Issue:** The first draft of `+page.svelte` copied the `[id]` template's Merge/Delete blocks verbatim behind `{#if data.person.id}` guards, per the plan's Task 2 item 1 instruction to reuse cards "verbatim in structure/styling." Because this route's `load()` (Task 1) returns `{ person }` only — no `people`, `can_delete`, or `merge`/`delete` actions — `svelte-check` reported 14 real TypeScript errors: `data.people` had no declared type (empty-array literal inferred as `never[]`), and `form?.mergeError`/`form?.deleteError` don't exist on this route's `Actions`-derived form type (only `create`'s `{ error: string }` shape exists). These blocks never render at runtime (guard is always false), but the plan's own verification step (`npm run check`) requires 0 errors, and shipping code that references non-existent server actions is a latent correctness problem even if currently unreachable.
- **Fix:** Removed the Merge and Delete `<div>`/`<form>` blocks, their backing `$state` (`mergeTargetId`, `mergePreview`, `mergeLoading`, `mergeError`, `mergeSubmitting`, `deleteSubmitting`), and the `fetchMergePreview` helper from `+page.svelte`. Simplified `+page.server.ts`'s `load()` to return `{ person }` only (dropped the unused `people`/`can_delete`/`delete_block_count` fields it had originally returned for parity with `[id]`).
- **Files modified:** `app/src/routes/admin/people/new/+page.svelte`, `app/src/routes/admin/people/new/+page.server.ts`
- **Verification:** `npm run check` — 0 errors (down from 14); `npm run build` succeeds.
- **Committed in:** `8b2b4dc3` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug, caught by the plan's own verification step before commit)
**Impact on plan:** Necessary for correctness — the plan's literal "reuse verbatim" instruction for Merge/Delete conflicted with this route genuinely lacking the actions/data those cards depend on. The `{#if data.person.id}` guard alone (sufficient on `[id]`, where the guard's `false` branch is reachable via soft navigation) was not sufficient here to keep the code type-correct, since `data.person.id` is a compile-time-always-null literal on this route. No scope creep beyond `files_modified` — both edits stayed within the plan's declared `app/src/routes/admin/people/new/+page.server.ts` and `+page.svelte`.

## Issues Encountered
None beyond the type-error deviation documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- The create-person flow (PDIR-07) is complete end-to-end: `/admin/people/new` → fill full name + choose Bench/Advocate → `Save Person` → `POST /api/admin/people` → redirect to `/admin/people/{id}` with a fully populated editor per Plan 27-05.
- Phase-level UAT should visually confirm: the slide-reveal when Bench is selected on the create page, that no visual "gap" appears where Photo/Biography/Merge/Delete would have sat, and that creating a Justice with zero arguments present works (PDIR-07's core scenario) — carried forward alongside Plan 27-05's own deferred visual UAT items.
- No blockers for phase verification. This was the last plan in Phase 27 (6 of 6, wave 5).

---
*Phase: 27-people-admin*
*Completed: 2026-07-09*

## Self-Check: PASSED

- FOUND: app/src/routes/admin/people/new/+page.server.ts
- FOUND: app/src/routes/admin/people/new/+page.svelte
- FOUND: .planning/phases/27-people-admin/27-06-SUMMARY.md
- FOUND commit: 7eeb0263 (Task 1)
- FOUND commit: 8b2b4dc3 (Task 2)
