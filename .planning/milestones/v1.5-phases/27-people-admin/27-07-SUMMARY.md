---
phase: 27-people-admin
plan: 07
subsystem: ui
tags: [svelte, css, admin, table-layout]

# Dependency graph
requires:
  - phase: 27-people-admin
    provides: Plan 27-04's per-tab people-list table markup (Bench/Advocate columns) that this plan's padding fix targets
provides:
  - Corrected horizontal gutter padding on the four middle columns of the /admin/people list table (Advocate: Argument count, Missing fields; Bench: Tenure coverage, Tenure gap)
affects: [people-admin UAT gap closure, admin table styling convention]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Middle-column table cells (neighbors on both sides) require horizontal padding (8px 8px header / 12px 8px body); only edge columns (first/last, flush to table border) may use zero horizontal padding — matches admin/arguments/+page.svelte convention."

key-files:
  created: []
  modified:
    - app/src/routes/admin/people/+page.svelte

key-decisions:
  - "Applied the fix to all four middle columns (Bench's Tenure coverage/Tenure gap plus Advocate's Argument count/Missing fields), not just the visibly-reported Advocate pair — the debug diagnosis confirmed the same zero-horizontal-padding defect was latent (masked by left-alignment) on the Bench tab."

patterns-established:
  - "Middle-column gutter convention (8px 8px / {v}px 8px) reaffirmed as the codebase standard for any table column with neighbors on both sides; edge columns keep zero horizontal padding to stay flush with the table border."

requirements-completed: [PDIR-03, PDIR-04]

coverage:
  - id: D1
    description: "Advocate tab's Argument count and Missing fields columns/headers have a visible horizontal gutter (8px 8px header, 12px 8px body) instead of running together."
    requirement: "PDIR-04"
    verification:
      - kind: automated_ui
        ref: "grep -c 'padding: 8px 8px' app/src/routes/admin/people/+page.svelte == 4; grep -c 'padding: 12px 8px' == 4"
        status: pass
    human_judgment: true
    rationale: "Visual gutter spacing is a rendering/perception check — svelte-check and grep confirm the CSS values are correct, but confirming the columns visually read as separated (not just non-zero padding) requires a human looking at the rendered page."
  - id: D2
    description: "Bench tab's Tenure coverage and Tenure gap middle columns carry the same gutter fix, matching the sibling admin/arguments table convention."
    requirement: "PDIR-03"
    verification:
      - kind: automated_ui
        ref: "app/src/routes/admin/people/+page.svelte lines 199-222 (th) and 274-290 (td) — padding: 8px 8px / 12px 8px"
        status: pass
    human_judgment: true
    rationale: "Same rendering-perception caveat as D1; this pair was latent (not previously reported) because left-alignment partially masked the zero-padding defect."

duration: 8min
completed: 2026-07-09
status: complete
---

# Phase 27 Plan 07: People-Table Middle-Column Padding Fix Summary

**Fixed zero-horizontal-padding defect on all four middle columns (Tenure coverage, Tenure gap, Argument count, Missing fields) in the /admin/people list table, restoring the codebase's 8px gutter convention.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-07-09T13:13:00Z
- **Completed:** 2026-07-09T13:21:29Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Advocate-tab "Argument count" and "Missing fields" headers/cells now have an 8px horizontal gutter, resolving the UAT-reported "Argument countMissing fields" run-together defect
- Bench-tab "Tenure coverage" and "Tenure gap" headers/cells received the identical fix, closing the latent (previously unreported) instance of the same defect
- Edge columns (Name, trailing Edit-person action) were left untouched, preserving their flush-to-table-border alignment

## Task Commits

Each task was committed atomically:

1. **Task 1: Add horizontal gutter padding to the people-table middle columns** - `b9ee6eac` (fix)

**Plan metadata:** (recorded below, after this commit)

## Files Created/Modified
- `app/src/routes/admin/people/+page.svelte` - Changed `padding: 8px 0` to `padding: 8px 8px` on the four middle-column `<th>` elements (Tenure coverage, Tenure gap, Argument count, Missing fields) and `padding: 12px 0` to `padding: 12px 8px` on their matching `<td>` elements; Name and trailing action edge columns unchanged.

## Decisions Made
- Fixed all four middle columns (both tabs) rather than only the Advocate-tab pair reported in UAT, per the plan's explicit scope and the debug diagnosis's finding that the Bench-tab pair had the identical latent defect.

## Deviations from Plan

None - plan executed exactly as written. One mechanical note: the Edit tool's exact-string match failed once on the "Missing fields" `<td>` block due to a subtle indentation/context ambiguity between two nearly-identical padding blocks in the file; resolved by using a targeted single-line `sed` replacement on the confirmed line number (306) rather than retrying the whole-block match. No behavior or scope change resulted — verified via `grep -c` counts (4 headers at `8px 8px`, 4 bodies at `12px 8px`) and by confirming the two edge-column lines (195, 258, 271, 333) remained at zero horizontal padding.

## Issues Encountered
None beyond the mechanical Edit-tool retry noted above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- UAT Gap 1 (Test 1, cosmetic) is closed; `svelte-check` reports 0 errors (16 pre-existing warnings, none in this file).
- Remaining Phase 27 UAT gaps (2 more identified in the gap-closure plans referenced in STATE.md) are tracked separately and not addressed by this plan.
- Human visual re-verification of the Advocate and Bench tabs on `/admin/people` is recommended to close out this gap in the UAT record (D1/D2 above are marked `human_judgment: true` for that reason).

---
*Phase: 27-people-admin*
*Completed: 2026-07-09*

## Self-Check: PASSED
- FOUND: app/src/routes/admin/people/+page.svelte
- FOUND: b9ee6eac (commit)
- FOUND: .planning/phases/27-people-admin/27-07-SUMMARY.md
