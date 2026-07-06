---
phase: 23-shared-argument-details-component
plan: "05"
subsystem: frontend
tags: [svelte, docket-pill, ux-guard, gap-closure]
dependency_graph:
  requires: []
  provides: [docket-pill-max-count-guard]
  affects: [ArgumentDetailsCard.svelte]
tech_stack:
  added: []
  patterns: [svelte-runes-state, conditional-disabled-attribute]
key_files:
  created: []
  modified:
    - app/src/lib/components/ArgumentDetailsCard.svelte
decisions:
  - "Client-side max-count guard is UX convenience only; server CR-02 guard remains the authoritative control"
  - "Inline hint suppressed in readonly mode because the Remove button is also hidden there"
metrics:
  duration: "5m"
  completed_date: "2026-07-06"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 1
status: complete
requirements: [PJOB-04]
---

# Phase 23 Plan 05: Docket Pill Max-Count Guard Summary

**One-liner:** Client-side max-count guard prevents a second docket pill from being added, making the server CR-02 rejection unreachable from normal UI interaction.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add max-count guard to docket pill input | 89c04d9a | app/src/lib/components/ArgumentDetailsCard.svelte |

## What Was Built

Four coordinated changes to `ArgumentDetailsCard.svelte`, all confined to the docket input section:

1. **`addPill()` early-return guard** — `if (pills.length >= 1) return;` added as the first statement in `addPill()`, before the existing empty/duplicate check.

2. **Input `disabled` attribute** — Changed from `disabled={readonly}` to `disabled={readonly || pills.length >= 1}`, visually locking the field when a pill already exists.

3. **Enter key guard** — The `onkeydown` handler now checks `pills.length < 1` before calling `addPill()`, so pressing Enter on a focused-but-disabled input is a no-op.

4. **Inline hint paragraph** — A conditionally rendered `<p>` with "Remove the existing entry to add a different one." appears below the input when `pills.length >= 1 && !readonly`. Hidden in readonly mode because the Remove button is also hidden there.

## Verification

- `svelte-check`: 0 errors, 18 warnings (all pre-existing in unrelated files — `ArgumentDetailsCard.svelte` produces no warnings)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. The client-side guard is UX convenience only. The authoritative server-side CR-02 guard at `+page.server.ts` lines 374–379 remains unchanged and is not affected by this plan.

## Self-Check: PASSED

- [x] `app/src/lib/components/ArgumentDetailsCard.svelte` modified with all four changes
- [x] Commit `89c04d9a` exists: `fix(23-05): add max-count guard to docket pill input`
- [x] svelte-check: 0 errors
