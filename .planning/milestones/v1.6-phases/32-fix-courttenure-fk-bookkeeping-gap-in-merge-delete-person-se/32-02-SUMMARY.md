---
phase: 32-fix-courttenure-fk-bookkeeping-gap-in-merge-delete-person-se
plan: 02
subsystem: ui
tags: [sveltekit, svelte5-runes, typescript, admin-people, fk-integrity]

# Dependency graph
requires:
  - phase: 32-fix-courttenure-fk-bookkeeping-gap-in-merge-delete-person-se
    provides: "Plan 01's backend MergePreview.tenures: int field on the merge-preview response contract"
provides:
  - "MergePreviewCounts.tenures on the SvelteKit server-load interface"
  - "can_delete/delete_block_count client-side blocking check including tenures"
  - "mergePreview $state type + all-zero guard + breakdown string rendering tenures"
affects: [admin-people-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - app/src/routes/admin/people/[id]/+page.server.ts
    - app/src/routes/admin/people/[id]/+page.svelte

key-decisions:
  - "tenures joins the blocking tier (utterances/appearances/argument_participants) in can_delete and delete_block_count, not the aliases bucket (D-01/D-05, locked in 32-CONTEXT.md)"
  - "Breakdown copy 'N tenure(s)' appended after 'argument participant(s)', matching table declaration order (Claude's Discretion per 32-CONTEXT.md)"
  - "Delete-blocked tooltip copy left unchanged — existing generic text already covers all blocking tables"

patterns-established: []

requirements-completed: [PADM-05]

coverage:
  - id: D1
    description: "Merge-preview breakdown line renders 'N tenure(s)' alongside the other four counts (SC#1 display surface)"
    requirement: "PADM-05"
    verification:
      - kind: automated_ui
        ref: "node verify script asserting /tenure\\(s\\)/.test(+page.svelte) — see Task 2 <verify>"
        status: pass
    human_judgment: false
  - id: D2
    description: "The all-zero 'no records to transfer' message only shows when tenures is also 0"
    requirement: "PADM-05"
    verification:
      - kind: automated_ui
        ref: "node verify script asserting /mergePreview\\.tenures\\s*===\\s*0/.test(+page.svelte) — see Task 2 <verify>"
        status: pass
    human_judgment: false
  - id: D3
    description: "can_delete is false and the delete button shows disabled when the person has >=1 CourtTenure row (SC#3 defense-in-depth)"
    requirement: "PADM-05"
    verification:
      - kind: automated_ui
        ref: "node verify script asserting /counts\\.tenures\\s*===\\s*0/.test(+page.server.ts) — see Task 1 <verify>"
        status: pass
    human_judgment: false
  - id: D4
    description: "svelte-check (npm run check) passes with no new type errors on both modified files"
    requirement: "PADM-05"
    verification:
      - kind: other
        ref: "npm run check (svelte-kit sync && svelte-check --tsconfig ./tsconfig.json) — COMPLETED 800 FILES 0 ERRORS 16 WARNINGS (all 16 warnings pre-existing, none on the tenures diff lines)"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-07-13
status: complete
---

# Phase 32 Plan 02: Frontend CourtTenure Merge-Preview Sync Summary

**Synced both admin-people frontend surfaces (`+page.server.ts` and `+page.svelte`) to the Plan 01 backend contract, adding `tenures` as a 5th field so the merge breakdown renders the count and the delete button's client-side defense-in-depth check blocks on tenure rows.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-07-13T19:05:00Z (approx)
- **Completed:** 2026-07-13T19:15:00Z (approx)
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `MergePreviewCounts` TypeScript interface in `+page.server.ts` gains a required `tenures: number` field, mirroring the Plan 01 Pydantic `MergePreview.tenures: int` field name exactly (no silent-drop mismatch)
- Server-load `can_delete`/`delete_block_count` derivation now includes `counts.tenures` in the blocking bucket alongside `utterances`/`appearances`/`argument_participants`; `aliases` remains deliberately excluded (auto-delete tier, unchanged)
- Component `mergePreview` `$state` type gains `tenures: number`; the all-zero "No records to transfer" guard now requires `mergePreview.tenures === 0` too
- Breakdown string renders `· {mergePreview.tenures} tenure(s)` appended after `argument participant(s)`, matching the existing sentence order convention
- `npm run check` (svelte-check) passes at 0 errors across all 800 project files after both edits — no new type errors introduced

## Task Commits

Each task was committed atomically:

1. **Task 1: Add tenures to server-load interface and blocking delete logic** - `67336a4f` (feat)
2. **Task 2: Add tenures to component state type, all-zero check, and breakdown string** - `6e25fe04` (feat)

**Plan metadata:** (pending — final docs commit follows this SUMMARY)

## Files Created/Modified
- `app/src/routes/admin/people/[id]/+page.server.ts` - `MergePreviewCounts` interface gains `tenures: number`; `can_delete`/`delete_block_count` derivation extended to include `counts.tenures` in the blocking tier
- `app/src/routes/admin/people/[id]/+page.svelte` - `mergePreview` `$state` type gains `tenures: number`; all-zero `{#if}` guard and breakdown `{:else}` string both updated to include the tenure count

## Decisions Made
- `tenures` joins the blocking tier (utterances/appearances/argument_participants) in both `can_delete` and `delete_block_count` — locked by D-01/D-05 in `32-CONTEXT.md`; `aliases` stays excluded from both since aliases auto-delete rather than block.
- Breakdown copy "N tenure(s)" appended after "argument participant(s)" (Claude's Discretion per `32-CONTEXT.md`, matching table declaration order).
- Delete-blocked tooltip copy intentionally left unchanged — the existing generic text ("Cannot delete — this person has associated records and cannot be removed") already covers tenures with no per-table wording needed.

## Deviations from Plan

None - plan executed exactly as written. Both tasks matched the plan's `<action>` and `<read_first>` guidance exactly (one field added to each interface/type, one boolean/sum extended, one string interpolation appended). Verification greps from the plan passed unmodified on both files, and `npm run check` (not explicitly required by the plan's automated verify blocks, but listed in the plan's `<verification>` section as an available additional check) confirmed 0 new type errors.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both PADM-05 frontend surfaces are now in lockstep with the Plan 01 backend `MergePreview.tenures` contract — the phase's full stack (schema, service, both frontend files) is consistent.
- SC#1 (display) and SC#3 (client-side defense-in-depth) are both satisfied; the phase's remaining success criteria (SC#2/SC#4, server-side atomicity and orphan detection) were delivered in Plan 01.
- Recommend an operator manually exercise the merge/delete UI against a Justice with `CourtTenure` rows (e.g., in the dev/staging environment) to visually confirm the "N tenure(s)" breakdown text and the disabled delete button, since this plan's verification was static (grep + svelte-check) rather than a live browser check.

---
*Phase: 32-fix-courttenure-fk-bookkeeping-gap-in-merge-delete-person-se*
*Completed: 2026-07-13*

## Self-Check: PASSED

- FOUND: app/src/routes/admin/people/[id]/+page.server.ts
- FOUND: app/src/routes/admin/people/[id]/+page.svelte
- FOUND: .planning/phases/32-fix-courttenure-fk-bookkeeping-gap-in-merge-delete-person-se/32-02-SUMMARY.md
- FOUND: 67336a4f (Task 1 commit)
- FOUND: 6e25fe04 (Task 2 commit)
