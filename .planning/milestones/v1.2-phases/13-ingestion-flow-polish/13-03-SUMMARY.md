---
phase: 13-ingestion-flow-polish
plan: "03"
subsystem: ui
tags: [svelte5, runes, combobox, polling, step-badge, pipeline, discrepancy-review, accessibility]

requires:
  - phase: 07-pipeline-runner
    provides: discrepancy review table, AddNewPersonForm, handleSelectPerson, datalist typeahead
  - phase: 13-ingestion-flow-polish
    provides: phase context, UI-SPEC for combobox and step-badge fallback

provides:
  - lastKnownStep $state fallback preventing step badges from flashing all-pending during null current_step transitions
  - 1s poll interval for running jobs (down from 2500ms)
  - custom Svelte 5 Runes combobox replacing native datalist typeahead in the correcting branch
  - combobox hidden when AddNewPersonForm is active to prevent UI ambiguity

affects: [13-ingestion-flow-polish, 14-ui-polish, pipeline-job-detail-page]

tech-stack:
  added: []
  patterns:
    - "lastKnownStep $state pattern: track last non-null current_step; pass as fallback to stepStatus only when status=running"
    - "Custom combobox pattern: position:relative container + text input + conditional ul[role=listbox]; outside-click via $effect document listener"
    - "Per-row combobox state keyed by raw_speaker_label extended into existing RowState interface"
    - "Combobox visibility tied to sub-form state: hide container when inline form is active"

key-files:
  created: []
  modified:
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte

key-decisions:
  - "lastKnownStep $state declared outside the poll $effect; updated inside setInterval on non-null current_step; effectiveJob spreads in the fallback at the stepStatus call site"
  - "comboOutsideClick is a Svelte action (not a bare $effect) so each combobox instance registers and cleans up its own document listener independently"
  - "filteredCandidates is a {@const} expression inside the #each loop (not a top-level $derived) because candidates are per-row and keyed by rowKey"
  - "Combobox always shows dropdown on focus (not only when query length > 0) per UI-SPEC open/close rules"
  - "comboHighlight index includes filteredCandidates.length as the sentinel for the Add new person item"
  - "Combobox container hidden (display:none) when s.addingPerson is true — form fields unambiguous; combobox input disappears so operator focus goes to Full Name and Role inputs"
  - "Role field in AddNewPersonForm remains a plain text input — confirmed never a select across all git history"

patterns-established:
  - "Step-badge null-transition guard: lastKnownStep fallback pattern for poll-driven step cards"
  - "Combobox visibility tied to form state: hide combobox container when inline sub-form is active"

requirements-completed: [PIPE-18, PIPE-19]

duration: ~45min (including checkpoint verification and regression investigation)
completed: 2026-06-24
status: complete
---

# Phase 13 Plan 03: Step Badge Fallback + Custom Combobox Summary

**`lastKnownStep` fallback keeps Running badge stable during null `current_step` transitions; custom Svelte 5 Runes combobox replaces native datalist with keyboard/outside-click/filter; combobox hidden when AddNewPersonForm is active**

## Performance

- **Duration:** ~45 min (including checkpoint verification and regression investigation)
- **Started:** 2026-06-24T14:15:00Z
- **Completed:** 2026-06-24T15:05:00Z
- **Tasks:** 2 implementation + 1 human-verify checkpoint + 1 post-checkpoint fix
- **Files modified:** 1

## Accomplishments

- PIPE-18: `lastKnownStep $state` tracks the last non-null `current_step`; stepStatus receives `current_step ?? lastKnownStep` when running, keeping the last active step showing "Running" through the null gap between pipeline steps
- PIPE-18: Poll interval reduced from 2500ms to 1000ms; TERMINAL short-circuit (completed/failed/paused) unchanged; `console.debug('[poll]')` diagnostic retained
- PIPE-19: Custom `<input role="combobox">` + `<ul role="listbox">` replaces native `<datalist>`; filters candidates case-insensitively on name+role; "Add new person" always last in accent blue; keyboard Up/Down/Enter/Escape navigation
- Post-checkpoint: Combobox container set to `display:none` when `s.addingPerson` is true, removing the UI ambiguity that caused the user to report a "missing" role field

## Task Commits

1. **Task 1: PIPE-18 — lastKnownStep fallback + 1s poll** — `7ddc157` (fix)
2. **Task 2: PIPE-19 — custom Svelte combobox** — `63118c6` (feat)
3. **Checkpoint docs (pre-verify)** — `e4302e4` (docs)
4. **Post-checkpoint regression fix** — `a25bd41` (fix)

## Files Created/Modified

- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — All changes in this one file:
  - Added `lastKnownStep $state`, poll assignment, `effectiveJob` call-site fallback for `stepStatus`
  - Added `comboQuery`, `comboOpen`, `comboHighlight` per-row state fields to `RowState` interface
  - Replaced `<input list>` + `<datalist>` with custom combobox div + input + ul + `comboOutsideClick` action
  - Set combobox container `display:none` when `s.addingPerson` is true

## What Was Built

### Task 1 — PIPE-18: Step Badge Null-Transition Fallback (7ddc157)

Three changes to `app/src/routes/admin/pipeline/[job_id]/+page.svelte`:

1. **`lastKnownStep` `$state`** — declared outside the `$effect` poll loop, initialized from `data.job.current_step ?? null`. Tracks the most recent non-null `current_step` across poll cycles.

2. **Poll loop updates + diagnostic log** — inside the `setInterval` callback, `lastKnownStep` is assigned when `data.job.current_step` is non-null. `console.debug('[poll]', { status, current_step })` retained for live diagnostics.

3. **`effectiveJob` at the call site** — `{#each STEP_ORDER}` computes `effectiveJob` via a spread that substitutes `lastKnownStep` for `current_step` when `status === 'running'` and `current_step === null`. Passed to `stepStatus()` instead of `data.job` directly. Failed/paused/completed branches unchanged.

4. **Poll interval** — `setInterval` delay changed from `2500` to `1000`. TERMINAL short-circuit unchanged.

### Task 2 — PIPE-19: Custom Svelte Combobox (63118c6)

Replaced `<input list> + <datalist>` in `{:else if s?.correcting}` with a fully custom combobox.

**State additions to `RowState`:** `comboQuery: string`, `comboOpen: boolean`, `comboHighlight: number` (index into `filteredCandidates`; `.length` = "Add new person" sentinel).

**`comboOutsideClick` Svelte action:** uses an internal `$effect` to add/remove a `document` click listener; closes dropdown when click target is outside the container.

**Combobox structure:** container `<div style="position: relative; width: 100%;">` + `<input role="combobox">` + `{#if s.comboOpen}` `<ul role="listbox">` with `<li role="option">` candidates. "Add new person" always last, color `#93c5fd`. `handleSelectPerson` and `getRowCandidates` functions unchanged.

### Post-Checkpoint Fix — Combobox Hidden When AddNewPersonForm Active (a25bd41)

During human verification, user reported "no longer the dropdown to select/add Role" when clicking "Add new person."

**Investigation:** Full git bisect from `d24329a` through `a25bd41` confirmed the AddNewPersonForm role field has always been `<input type="text" name="role_name">` — never a `<select>`. The plain text input was not removed or altered by Task 2.

**Root cause identified:** When `s.addingPerson = true`, the combobox search input remained visible above the AddNewPersonForm, presenting two unlabeled text inputs simultaneously. The combobox input (which was no longer relevant) was the source of confusion.

**Fix:** Added `{s.addingPerson ? ' display: none;' : ''}` to the combobox container `<div>` style. When AddNewPersonForm is open, the combobox input hides; when the form closes (on successful save), it reappears.

## Decisions Made

- `lastKnownStep` initialized from `data.job.current_step ?? null` on page load — retains last known step across null transitions without resetting on each poll
- `comboOutsideClick` uses Svelte action (not bare `$effect`) so each row instance owns its own listener lifecycle
- Combobox hidden (not conditionally removed) on `s.addingPerson` to avoid remounting and resetting combobox state
- Role field kept as `<input type="text">` — confirmed correct per historical intent (D-13 from 07-CONTEXT: "name + role only" minimal creation form; role is free-text, not a join to the roles table)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Combobox input visible alongside AddNewPersonForm causing UI ambiguity**

- **Found during:** Human checkpoint verification (Task 3)
- **Issue:** User reported "no longer the dropdown to select/add Role." Investigation confirmed the role text input in AddNewPersonForm was present and unchanged. The actual problem: the combobox search input remained visible above the AddNewPersonForm when `s.addingPerson = true`, making the UI ambiguous.
- **Fix:** `{s.addingPerson ? ' display: none;' : ''}` added to combobox container style attribute
- **Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte`
- **Verification:** `svelte-check` 0 errors; `grep -n "new-person-role"` confirms role input at lines 755 and 761
- **Committed in:** `a25bd41`

---

**Total deviations:** 1 auto-fixed (Rule 1 — UI ambiguity bug discovered at verification)
**Impact on plan:** Surgical single-attribute fix. AddNewPersonForm behavior and server action unchanged.

## Future Consideration (captured, not implemented)

**Cancel button UX (user-requested, deferred):** When the combobox dropdown is open, the trigger/search input button could visually change to "Cancel" text. This is a UX polish enhancement — not a bug, not part of PIPE-18 or PIPE-19 scope. Candidate for Phase 14 UI polish.

## Known Stubs

None — all form fields wire to live server actions; no placeholder or mock data.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. Combobox query is used only for client-side `.includes` filtering of already-loaded `data.people`. Selection submits a numeric `person_id` through the existing validated resolve action. Consistent with T-13-05 and T-13-06 accepted dispositions in the plan threat register.

## Self-Check: PASSED

- [x] `app/src/routes/admin/pipeline/[job_id]/+page.svelte` modified and committed
- [x] Commit `7ddc157` exists (Task 1)
- [x] Commit `63118c6` exists (Task 2)
- [x] Commit `a25bd41` exists (post-checkpoint fix)
- [x] `grep -c "<datalist"` → 0
- [x] `grep -n 'role="combobox"'` → present
- [x] `grep -n 'role="listbox"'` → present
- [x] `grep -n 'role="option"'` → present
- [x] `grep -n "lastKnownStep"` → 4+ matches
- [x] `grep -c "2500"` → 0
- [x] `grep -n "new-person-role"` → lines 755 and 761 (role field present in AddNewPersonForm)
- [x] `npx svelte-check` → 0 errors
- [x] Human checkpoint: PIPE-18 passing, PIPE-19 all 7 interaction tests passing
- [x] Post-checkpoint fix applied and committed

## Next Phase Readiness

- PIPE-18 and PIPE-19 complete; job detail page step-badge and combobox UX are verified
- Phase 13 Plan 03 is the final plan in Phase 13 — phase complete
- Ready for Phase 13 wrap-up or Phase 14

---
*Phase: 13-ingestion-flow-polish*
*Completed: 2026-06-24*
