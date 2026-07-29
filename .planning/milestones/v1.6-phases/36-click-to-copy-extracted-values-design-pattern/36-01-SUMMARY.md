---
phase: 36-click-to-copy-extracted-values-design-pattern
plan: 01
subsystem: ui
tags: [svelte5, clipboard, accessibility]
requires: []
provides:
  - Reusable extracted-value clipboard control with local feedback and disabled states
  - Copy controls for argument-detail docket, question-number, and argued-date hints
affects: [36-02, extracted-value-displays]
tech-stack:
  added: []
  patterns: [component-local clipboard state, exact display-string copying]
key-files:
  created: [app/src/lib/components/CopyableExtractedValue.svelte]
  modified: [app/src/lib/components/ArgumentDetailsCard.svelte]
key-decisions:
  - "The shared control receives one final display string and uses it unchanged for rendering and clipboard writes."
patterns-established:
  - "Eligible extracted values use CopyableExtractedValue rather than consumer-owned clipboard state."
requirements-completed: [UX-01]
coverage:
  - id: D1
    description: "Reusable copy control implements exact-string clipboard writes, local feedback, timer cleanup, and disabled N/A behavior."
    requirement: UX-01
    verification:
      - kind: other
        ref: "app: npm run check && npm run build"
        status: pass
    human_judgment: true
    rationale: "Clipboard timing, browser permission failure, keyboard activation, and visual presentation require browser UAT."
  - id: D2
    description: "Argument details expose separate copy targets for each docket plus question number and argued date."
    requirement: UX-01
    verification:
      - kind: other
        ref: "app: npm run check && npm run build"
        status: pass
    human_judgment: true
    rationale: "Exact pasted values and focus behavior require browser UAT."
duration: 16min
completed: 2026-07-15
status: complete
---

# Phase 36 Plan 01: Shared Extracted-Value Copy Control Summary

**A reusable Svelte 5 clipboard affordance now serves every argument-detail docket, question-number, and argued-date hint.**

## Performance

- **Duration:** 16 min
- **Completed:** 2026-07-15
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added one typed component owning exact-value clipboard writes, 1,500ms success feedback, retryable local errors, cleanup, SVG, tooltip, disabled semantics, and text/pill visuals.
- Converted every argument-details extracted docket into its own copy target, including a visible disabled `N/A` target when no docket exists.
- Converted question-number and argued-date hints without changing their form inputs, saved values, submission behavior, or caller formatting.

## Task Commits

1. **Task 1: Build the reusable extracted-value copy control** - `fae81dc6`
2. **Task 2: Adopt the shared control for argument detail hints** - `ea96764f`

## Files Created/Modified

- `app/src/lib/components/CopyableExtractedValue.svelte` - Reusable native-button clipboard interaction and presentation.
- `app/src/lib/components/ArgumentDetailsCard.svelte` - Shared control adoption for eligible extracted hints.

## Decisions Made

- The component uses the supplied display string for both interpolation and `navigator.clipboard.writeText`, keeping formatting ownership at the caller boundary.

## Deviations from Plan

None - plan behavior and scope were implemented as specified.

## Issues Encountered

- The restricted Windows sandbox temporarily refused updates to the existing card file. The orchestrator applied the exact scoped patch through its approved elevated fallback, after which verification and the atomic task commit completed normally.

## User Setup Required

None - no external service configuration or dependency installation is required.

## Next Phase Readiness

- The shared primitive is ready for Plan 02 adoption across remaining eligible pipeline and argument-editor surfaces.
- Browser UAT remains intentionally assigned to Plan 02's blocking verification checkpoint.

---
*Phase: 36-click-to-copy-extracted-values-design-pattern*
*Completed: 2026-07-15*
