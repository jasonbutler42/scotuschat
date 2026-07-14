---
phase: 34-blank-case-name-docket-validation
plan: 03
subsystem: admin-ui
tags: [svelte, accessibility, validation, focus]
requires: [34-02]
provides:
  - Exact accessible native Case required feedback and deterministic focus
  - Client-blocked empty docket pills with shared server recovery semantics
affects: []
tech-stack:
  added: []
  patterns: [presence-based attempt restoration, first-invalid focus after tick, imperative custom-control focus]
key-files:
  created: []
  modified:
    - app/src/routes/admin/arguments/[id]/+page.svelte
    - app/src/lib/components/ArgumentDetailsCard.svelte
    - app/src/lib/components/DocketPillInput.svelte
    - api/tests/test_question_number_nullable.py
decisions:
  - Native invalid events are suppressed and both Case constraints are accumulated before focusing
  - Empty editable pill submissions are canceled client-side while readonly behavior remains unchanged
metrics:
  duration: 10m
  completed: 2026-07-14
status: complete
---

# Phase 34 Plan 03: Accessible Required Recovery Summary

Native Case fields and the shared docket-pill control now provide equivalent exact required feedback, preserved blank attempts, conditional ARIA state, red invalid borders, and deterministic first-invalid focus.

## Accomplishments

- Added native required defense-in-depth while suppressing browser bubbles in favor of the existing inline alert.
- Preserved blank Case attempts by property presence and rendered both exact required messages in field order.
- Added invalid/description props and parent-callable focus/pill-state methods to the shared docket control.
- Blocked empty editable pill submissions before transport and routed server-required failures back to the visible pill input.
- Preserved distinct conflict/generic alert focus and unchanged readonly behavior.

## Task Commits

1. `d1f54d2a` — `feat(34-03): add accessible case required errors`
2. `51d64bf3` — `feat(34-03): require accessible docket pills`

## Verification

- `.venv\Scripts\python.exe -m pytest api/tests/test_question_number_nullable.py -q` — 9 passed.
- `Push-Location app; npm run check; Pop-Location` — 0 errors, 16 pre-existing warnings.
- Browser-level human checks remain for phase UAT/verification.

## Decisions Made

- Case constraint state is gathered in DOM order and focuses case name before docket when both fail.
- The pill component exposes only focus and committed-pill presence to its parent; backend validation remains authoritative.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- All four modified UI/test files exist.
- Both task commits are present in git history.
- Focused contracts and frontend diagnostics pass.
