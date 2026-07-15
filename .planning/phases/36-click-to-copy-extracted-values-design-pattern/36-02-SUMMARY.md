---
phase: 36-click-to-copy-extracted-values-design-pattern
plan: 02
subsystem: ui
tags: [svelte5, clipboard, accessibility, admin]
requires:
  - phase: 36-01
    provides: Reusable CopyableExtractedValue primitive and argument-detail adoption
provides:
  - Shared click-to-copy controls across editable title hints and eligible pipeline extracted values
  - Paste-compatible MM/DD/YYYY extracted-date presentation plus a native-date-safe Use extracted action
  - Durable project guidance defining eligible and excluded click-to-copy surfaces
affects: [phase-38, extracted-value-displays, admin-pipeline, argument-editor]
tech-stack:
  added: []
  patterns: [shared extracted-value control, operator-editable destination scope, explicit extracted-date fill action]
key-files:
  created: []
  modified: [app/src/lib/components/ResolveCard.svelte, app/src/lib/components/ArgumentDetailsCard.svelte, app/src/lib/components/CopyableExtractedValue.svelte, app/src/routes/admin/arguments/[id]/+page.svelte, app/src/routes/admin/pipeline/[job_id]/+page.svelte, CLAUDE.md]
key-decisions:
  - "Absent N/A values retain disabled semantics and tooltip behavior but omit the copy icon."
  - "Extracted argued dates display and copy as MM/DD/YYYY; Use extracted fills the native segmented date control without autosaving or disrupting manual entry."
  - "Phase 36 owns the copy interaction contract while Phase 38 may evolve its visual presentation."
patterns-established:
  - "Extracted values with operator-editable destinations use CopyableExtractedValue unless a phase explicitly opts out."
  - "When a native date input cannot accept a whole pasted date, provide an explicit Use extracted action while preserving native manual entry."
requirements-completed: [UX-01]
coverage:
  - id: D1
    description: "Eligible pipeline and argument-editor values share exact-value click-to-copy behavior while excluded counts and non-editable values remain plain."
    requirement: UX-01
    verification:
      - kind: other
        ref: "app: npm run check && npm run build"
        status: pass
      - kind: manual_procedural
        ref: "Phase 36 Plan 02 blocking browser UAT: docket, argued date, keyboard, timer, focus, responsive layout, and exclusions"
        status: pass
    human_judgment: true
    rationale: "Clipboard payloads, keyboard behavior, focus, feedback timing, and responsive presentation required browser verification."
  - id: D2
    description: "Absent extracted values are disabled, skipped by Tab, retain explanatory tooltip text, and show no misleading copy icon."
    requirement: UX-01
    verification:
      - kind: manual_procedural
        ref: "Phase 36 Plan 02 browser UAT: Question number N/A"
        status: pass
    human_judgment: true
    rationale: "Disabled semantics, tooltip presentation, icon absence, and keyboard traversal are browser-observable behavior."
  - id: D3
    description: "Use extracted fills a native argued-date input with the extracted date without autosaving and leaves manual entry intact."
    requirement: UX-01
    verification:
      - kind: manual_procedural
        ref: "Phase 36 Plan 02 browser UAT: Use extracted date, save compatibility, and manual entry"
        status: pass
    human_judgment: true
    rationale: "Native segmented date-input behavior varies by browser and required operator verification."
duration: 2h
completed: 2026-07-15
status: complete
---

# Phase 36 Plan 02: Cross-Surface Click-to-Copy Adoption Summary

**One shared extracted-value interaction now covers every eligible pipeline and argument-editor surface, with paste-compatible date presentation and a native-date-safe fill action.**

## Performance

- **Duration:** 2h
- **Started:** 2026-07-15T09:31:57-05:00
- **Completed:** 2026-07-15T11:30:00-05:00
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Adopted `CopyableExtractedValue` for editable title hints and the eligible pipeline case name, argued date, docket, and question-number outputs while leaving excluded readouts plain.
- Verified exact docket payloads, repeated-click timer reset, text/icon activation, keyboard operation, focus visibility, disabled-state traversal, tooltip behavior, and responsive wrapping in the browser.
- Made argued dates display and copy as `MM/DD/YYYY`, then added `Use extracted` so the native date input can be filled correctly without autosave or loss of its manual-entry behavior.
- Recorded the future extracted-plus-editable eligibility rule in `CLAUDE.md`.

## Task Commits

1. **Task 1: Convert eligible editable title hints** - `5ac54648`
2. **Task 2: Convert eligible pipeline parsed-output readouts and record the future default** - `79d581cd`
3. **Task 3: Browser verification and approved UAT fixes** - `5ab1ab33`, `4b0119e9`

## Files Created/Modified

- `app/src/lib/components/ResolveCard.svelte` - Shared copy control for editable resolve-row title hints.
- `app/src/routes/admin/arguments/[id]/+page.svelte` - Shared copy control for argument-editor speaker title hints.
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` - Shared controls for eligible parsed output with `MM/DD/YYYY` argued dates.
- `app/src/lib/components/CopyableExtractedValue.svelte` - Disabled `N/A` retains behavior without rendering a copy icon.
- `app/src/lib/components/ArgumentDetailsCard.svelte` - Paste-compatible extracted-date rendering and native-input `Use extracted` action.
- `CLAUDE.md` - Durable D-13 eligibility, opt-out, exclusion, and component-reuse guidance.

## Decisions Made

- Phase 36 verifies the interaction foundation; Phase 38 may replace its transitional visual layout without invalidating this interaction contract.
- `N/A` remains visible, disabled, skipped by Tab, and explained by tooltip, but no longer shows a copy icon because there is nothing to copy.
- A native segmented date input remains the canonical manual editor. `Use extracted` bridges the browser's inability to paste a whole formatted date into it and does not save automatically.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Made argued-date display and clipboard payload destination-compatible**
- **Found during:** Task 3 browser UAT
- **Issue:** The extracted date displayed and copied as ISO `YYYY-MM-DD`, while the editable UI presented `MM/DD/YYYY`.
- **Fix:** Both pipeline and argument-detail extracted dates now display and copy as `MM/DD/YYYY`.
- **Files modified:** `app/src/lib/components/ArgumentDetailsCard.svelte`, `app/src/routes/admin/pipeline/[job_id]/+page.svelte`
- **Verification:** Operator confirmed the displayed argued date is `04/26/2010` on both consumers.
- **Committed in:** `5ab1ab33`

**2. [User-approved requirement change] Removed the copy icon from disabled N/A values**
- **Found during:** Task 3 browser UAT
- **Issue:** A copy icon on a disabled empty value suggested an unavailable action.
- **Fix:** Preserved disabled behavior and tooltip while suppressing the icon for `N/A`.
- **Files modified:** `app/src/lib/components/CopyableExtractedValue.svelte`
- **Verification:** Operator confirmed the icon is absent and all previous disabled behavior remains.
- **Committed in:** `5ab1ab33`

**3. [Rule 1 - Bug] Added a native-date-safe Use extracted action**
- **Found during:** Task 3 browser UAT
- **Issue:** Chrome's segmented native date control would not accept a complete pasted date in either ISO or display format.
- **Fix:** Added an explicit `Use extracted` action that validates and assigns the extracted ISO value to the native input without submitting the form.
- **Files modified:** `app/src/lib/components/ArgumentDetailsCard.svelte`
- **Verification:** Operator confirmed the correct date appears, saves successfully, and manual entry remains unchanged.
- **Committed in:** `4b0119e9`

---

**Total deviations:** 3 handled during UAT (2 correctness fixes, 1 user-approved requirement change)
**Impact on plan:** The shared interaction scope remains intact; changes make the affordances honest and compatible with their editable destination without backend, schema, dependency, or autosave changes.

## Issues Encountered

- No populated title-hint fixture was available during manual UAT, so exact copying for that populated state was not manually exercised. The same shared component path passed static checks/build and its `N/A` state was observable.
- Chrome on localhost continued allowing clipboard writes after its Clipboard site permission was disabled. The fixed local `Couldn't copy.` path remains implemented, but the rejected-write state could not be forced manually in this environment.
- A final sandboxed rerun of `npm run check` encountered Windows `spawn EPERM` while starting esbuild. The same check/build gates passed outside that restricted process after each implementation round; this was an execution-environment limitation rather than a code diagnostic.

## User Setup Required

None - no dependency or external-service configuration was added.

## Next Phase Readiness

- UX-01 is complete across the Phase 36 scope and ready for formal phase verification.
- Phase 38 can evolve the presentation to its approved extracted/confidence/raw layout while retaining the shared interaction behavior established here.
- The two manual coverage limitations above should remain visible to any later verification audit.

## Self-Check: PASSED

- All six listed modified files exist and all four implementation commits are present in git history.
- The operator approved the blocking browser checkpoint after verifying the available interaction matrix and both UAT-driven fixes.
- Static check and production build passed after each implementation round; the final sandbox-only spawn EPERM rerun is documented above as an environment limitation.

---
*Phase: 36-click-to-copy-extracted-values-design-pattern*
*Completed: 2026-07-15*
