---
phase: 19-pipeline-reliability
plan: "05"
subsystem: ui
tags: [svelte, sveltekit, form, preflight, duplicate-check]

requires:
  - phase: 19-pipeline-reliability
    provides: Duplicate preflight gate with preflightCleared state and handleSubmit early-return branch

provides:
  - formEl ref bound via bind:this on the pipeline runner form
  - Start anyway button uses formEl.requestSubmit() after setting preflightCleared=true, triggering handleSubmit's early-return branch to allow native POST

affects:
  - 19-pipeline-reliability (UAT gap 5 closure)

tech-stack:
  added: []
  patterns:
    - "bind:this for form element ref — avoids fragile document.querySelector DOM queries"
    - "preflightCleared=true + formEl.requestSubmit() pattern — re-enters handleSubmit's early-return branch to set submitting=true without calling preventDefault, letting native POST complete with all form data including file inputs"

key-files:
  created: []
  modified:
    - app/src/routes/admin/pipeline/+page.svelte

key-decisions:
  - "Use formEl.requestSubmit() (not formEl.submit()) so the submit event fires and handleSubmit's early-return branch runs — submit() bypasses the event entirely"
  - "Do not set submitting=true in the onclick — the early-return branch in handleSubmit already sets it; setting it in onclick would create double-execution ordering risk"
  - "Remove document.querySelector('form')?.requestSubmit() — the optional-chain could silently do nothing if the selector fails; bound ref is always reliable"

patterns-established:
  - "bind:this on the form element for imperative submit control — preferred over document.querySelector in SvelteKit"

requirements-completed:
  - PIPE-DUP-05

coverage:
  - id: D1
    description: "Start anyway button calls formEl.requestSubmit() after setting preflightCleared=true, removing document.querySelector usage"
    requirement: PIPE-DUP-05
    verification:
      - kind: manual_procedural
        ref: "Navigate /admin/pipeline, enter docket of existing argument, click Start Run, confirm amber banner, click Start anyway — page navigates to new job detail page without logout"
        status: unknown
    human_judgment: true
    rationale: "Browser-level form submission behavior and navigation outcome require human observation in a running app"

duration: 5min
completed: 2026-07-01
status: complete
---

# Phase 19 Plan 05: Start Anyway Fix Summary

**formEl ref bound via bind:this; Start anyway onclick updated to use preflightCleared=true + formEl.requestSubmit() so the native POST completes without preventing default**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-07-01T11:09:42Z
- **Completed:** 2026-07-01T11:15:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Declared `let formEl: HTMLFormElement` in the script block
- Added `bind:this={formEl}` to the `<form>` element
- Replaced the fragile `document.querySelector('form')?.requestSubmit()` call in the Start anyway onclick with `formEl.requestSubmit()`
- The `preflightCleared = true` flag set in the onclick causes handleSubmit's existing early-return branch to set `submitting = true` and return without calling `e.preventDefault()`, allowing the native multipart POST to complete with all form fields — including file inputs — serialized correctly

## Task Commits

1. **Task 1: Bind formEl ref and fix Start anyway onclick** - `b7a141f7` (fix)

## Files Created/Modified

- `app/src/routes/admin/pipeline/+page.svelte` — added formEl declaration, bind:this on form, updated Start anyway onclick

## Decisions Made

- Used `formEl.requestSubmit()` not `formEl.submit()` — requestSubmit fires the submit event so handleSubmit's early-return branch can run and set submitting=true; submit() would bypass the event and leave submitting=false
- Did not set `submitting = true` in the onclick — the early-return branch already sets it; redundant assignment would create double-execution ordering issues
- Removed optional-chain guard (`?.requestSubmit()`) — bound ref is always present when the button is rendered, so the silent-fail guard was unnecessary and potentially misleading

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- UAT gap 5 ("Duplicate banner — Start anyway proceeds") is now unblocked for manual verification
- Phase 19 UAT can be re-run; Start anyway no longer causes stuck "Starting…" state or unexpected logout
- No blockers for phase 19 closure once UAT passes

---
*Phase: 19-pipeline-reliability*
*Completed: 2026-07-01*
