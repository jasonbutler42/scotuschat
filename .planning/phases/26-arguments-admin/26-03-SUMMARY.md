---
phase: 26-arguments-admin
plan: 03
subsystem: ui
tags: [svelte, sveltekit, admin, status-badges]

# Dependency graph
requires:
  - phase: 26-arguments-admin
    provides: "Plan 26-01's status-keyed publish/unpublish/status-log backend logic (Argument.status, not published_at)"
provides:
  - Three-state lifecycle badge (Draft/Published/Unpublished) on the arguments list
  - "Created" column on the arguments list showing resolved_at
  - Status-driven row actions (Publish/Unpublish/re-Publish) keyed on arg.status
  - "Archived" badge on RunStatusCard for already-created pipeline runs
affects: [arguments-list, pipeline-job-detail]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Badge color/label helpers extended with an additional status branch rather than restructured, preserving exact existing markup shape"
    - "Readiness-state badge override pattern: a component-local $derived checks a higher-priority state (readiness.state) before falling back to the existing status-keyed lookup map"

key-files:
  created: []
  modified:
    - app/src/routes/admin/arguments/+page.svelte
    - app/src/lib/components/RunStatusCard.svelte

key-decisions:
  - "Row actions key on arg.status (draft/unpublished -> Publish, published -> Unpublish) instead of the old published_at-based two-branch check, matching Plan 26-01's backend status model"
  - "RunStatusCard's Archived override lives in the badgeColor/badgeLabel derivations only — BADGE_COLOR/BADGE_LABEL maps stay keyed purely on jobStatus, since Archived is a readiness-state override, not a job status"

patterns-established:
  - "readiness.state === 'already_created' as a badge-priority override pattern for status cards driven by both job status and readiness state"

requirements-completed: [ALIST-02, ALIST-03, ALIST-04]

coverage:
  - id: D1
    description: "Arguments list renders a distinct badge for Draft (violet), Published (green), and Unpublished (orange)"
    requirement: "ALIST-03"
    verification:
      - kind: unit
        ref: "cd app && npm run check (svelte-check, 0 errors)"
        status: pass
    human_judgment: true
    rationale: "Badge color/label correctness is visually verifiable (WCAG contrast, exact hex values); svelte-check confirms no type errors but not the rendered visual result. Recommended manual check per plan's <verification> section."
  - id: D2
    description: "Arguments list has a Created column between Argued and the row-actions column, showing resolved_at"
    requirement: "ALIST-04"
    verification:
      - kind: unit
        ref: "cd app && npm run check (svelte-check, 0 errors)"
        status: pass
    human_judgment: true
    rationale: "Column placement and date formatting are visual/layout concerns best confirmed by a human looking at the rendered table."
  - id: D3
    description: "Row actions are status-driven: Draft and Unpublished show Publish; Published shows Unpublish"
    requirement: "ALIST-02"
    verification:
      - kind: unit
        ref: "cd app && npm run check (svelte-check, 0 errors)"
        status: pass
    human_judgment: true
    rationale: "Requires exercising all three status values against the running app/API to confirm correct action per row; not covered by an automated test suite in this plan."
  - id: D4
    description: "Pipeline run status card shows an Archived badge (neutral grey) when the run's argument has already been created"
    verification:
      - kind: unit
        ref: "cd app && npm run check (svelte-check, 0 errors)"
        status: pass
    human_judgment: true
    rationale: "Requires viewing a job detail page for a run whose argument already exists to visually confirm the Archived badge overrides the jobStatus badge."

duration: 15min
completed: 2026-07-08
status: complete
---

# Phase 26 Plan 03: Arguments Admin Status Badges Summary

**Arguments list gains a three-state (Draft/Published/Unpublished) badge, a Created column, and status-driven row actions; RunStatusCard gains a neutral-grey "Archived" badge override for already-created pipeline runs.**

## Performance

- **Duration:** 15 min
- **Completed:** 2026-07-08T00:36:23Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `badgeStyle`/`badgeLabel` on the arguments list now render a third "Unpublished" badge (`#fb923c`, orange), distinct from Draft (violet) and Published (green)
- A "Created" column was added between "Argued" and the row-actions column, showing `arg.resolved_at` formatted via the existing `formatDate()` helper (or `—` when null)
- The row-action block was rewritten to branch on `arg.status` (`draft`/`unpublished` → Publish; `published` → Unpublish) instead of the stale `arg.resolved_at && !arg.published_at` / `arg.published_at` checks, so a re-published (previously unpublished) argument correctly shows a Publish action
- `RunStatusCard.svelte`'s `badgeColor`/`badgeLabel` derivations now check `readiness?.state === 'already_created'` first, overriding the `jobStatus`-driven lookup with `#cbd5e1` / "Archived" — the `BADGE_COLOR`/`BADGE_LABEL` maps themselves are unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Arguments list — unpublished badge, Created column, status-driven row actions** - `995c4d32` (feat)
2. **Task 2: RunStatusCard — Archived badge when argument already created** - `63b017ae` (feat)

**Plan metadata:** (pending — final commit below)

## Files Created/Modified
- `app/src/routes/admin/arguments/+page.svelte` - Added `unpublished` branch to badgeStyle/badgeLabel; added Created column header+cell; rewrote row-action block to key on `arg.status`
- `app/src/lib/components/RunStatusCard.svelte` - Added `already_created` readiness-state override to badgeColor/badgeLabel derivations, rendering an Archived badge

## Decisions Made
- Kept the exact existing badge markup/border/padding style string unchanged in both files — only extended the color/label mapping logic, per UI-SPEC's explicit instruction to preserve the badge shape
- `unpublished` and `draft` both route to the same Publish form/button style (no visual distinction between first-publish and re-publish), matching the UI-SPEC Copywriting Contract

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Frontend status surfaces (list page, run status card) are now consistent with Plan 26-01's status-keyed backend model
- No known follow-on work from this plan; the folded Phase-25-UAT Archived-badge todo is resolved

## Self-Check: PASSED

- FOUND: app/src/routes/admin/arguments/+page.svelte
- FOUND: app/src/lib/components/RunStatusCard.svelte
- FOUND: 995c4d32
- FOUND: 63b017ae
