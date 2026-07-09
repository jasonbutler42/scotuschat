---
phase: 27-people-admin
plan: 09
subsystem: ui
tags: [svelte, svelte5-runes, pydantic, admin-people, dropdown]

# Dependency graph
requires:
  - phase: 27-08
    provides: PersonCreateRequest/create_person name-part fields (unrelated file overlap only in api/schemas/admin_people.py docstring area)
provides:
  - Curated President's Party dropdown in the tenure editor sub-card (appointing_president_party only)
  - Legacy-value preservation guard for out-of-list stored party values
  - D-16 amendment record scoping the reversal to appointing_president_party only
affects: [27-verify-work, future-tenure-editor-changes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Curated <select> with a blank '— None —' option plus a conditional legacy-value <option> for out-of-list stored strings — preserves free-text-compatible schema columns while narrowing the UI to a maintained list"

key-files:
  created: []
  modified:
    - "app/src/routes/admin/people/[id]/+page.svelte"
    - "api/schemas/admin_people.py"
    - ".planning/phases/27-people-admin/27-CONTEXT.md"

key-decisions:
  - "D-16 amendment (2026-07-09): appointing_president_party reversed from free-text to a curated <select>, scoped to that field only; appointed_by remains free-text; Seat-as-toggle deferred to BACKLOG.md B-020"

patterns-established:
  - "Curated dropdown + blank option + legacy-value fallback <option> pattern for narrowing a free-text-compatible column's UI without a schema/type change"

requirements-completed: [PEDIT-09, PEDIT-10]

coverage:
  - id: D1
    description: "President's Party renders as a curated <select> (six parties + blank option) instead of free-text input, bound to the same row.appointing_president_party state"
    requirement: "PEDIT-09"
    verification:
      - kind: unit
        ref: "cd app && npm run check (svelte-check: 0 errors)"
        status: pass
      - kind: other
        ref: "grep -c PARTY_OPTIONS +page.svelte returns 3"
        status: pass
    human_judgment: false
  - id: D2
    description: "Appointing President (appointed_by) input is unchanged and remains free-text"
    requirement: "PEDIT-10"
    verification:
      - kind: other
        ref: "grep -c 'bind:value={row.appointed_by}' +page.svelte returns 1"
        status: pass
    human_judgment: false
  - id: D3
    description: "Selected party persists through Save Person round-trip and legacy non-list values still display selected on load"
    verification: []
    human_judgment: true
    rationale: "Requires opening the person editor, selecting/saving a party, and reloading — deferred to Phase 27 UAT retest per the plan's own verification section; not exercisable via static checks alone"
  - id: D4
    description: "TenureRow docstring and D-16 amendment note accurately record the reversal scope"
    verification:
      - kind: other
        ref: "python -c \"import ast; ast.parse(open('api/schemas/admin_people.py').read())\" succeeds"
        status: pass
      - kind: other
        ref: "grep -c 2026-07-09 27-CONTEXT.md returns 1"
        status: pass
    human_judgment: false

duration: 7min
completed: 2026-07-09
status: complete
---

# Phase 27 Plan 09: President's Party Dropdown Summary

**Converted the tenure sub-card's President's Party free-text input to a curated `<select>` (six historical US parties + blank + legacy-value fallback), reversing D-16 for that field only while leaving Appointing President free-text.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-07-09T13:33:00Z
- **Completed:** 2026-07-09T13:40:10Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- President's Party in the Tenure Period sub-card now renders as an HTML `<select>` populated with `PARTY_OPTIONS` (Federalist, Democratic-Republican, Democratic, Whig, Republican, Independent), plus a blank "— None —" option
- Added a data-preservation guard: any stored `appointing_president_party` value not in the curated list renders as an extra selected `<option>` so legacy/non-standard values never silently reset to blank on load
- Appointing President (`appointed_by`) input left completely untouched — still free-text per the original D-16 decision
- Updated `TenureRow`'s docstring in `api/schemas/admin_people.py` to describe the split: `appointed_by` free-text (D-16 unchanged), `appointing_president_party` now a curated dropdown in the UI while staying `Optional[str]` free-text-compatible at the schema/API level (no type/enum constraint added)
- Amended decision D-16 in `27-CONTEXT.md` with a dated note (2026-07-09) scoping the reversal to `appointing_president_party` only, confirming `appointed_by` is unaffected, and cross-referencing the Seat-as-toggle deferral to `BACKLOG.md` B-020

## Task Commits

Each task was committed atomically:

1. **Task 1: Convert President's Party to a curated dropdown in the tenure sub-card** - `d2e37223` (feat)
2. **Task 2: Update the TenureRow docstring and amend D-16 in CONTEXT.md** - `4e3e4359` (docs)

**Plan metadata:** (recorded below after final commit)

## Files Created/Modified
- `app/src/routes/admin/people/[id]/+page.svelte` - Added `PARTY_OPTIONS` module-level constant; replaced the President's Party `<input>` with a styled `<select>` (blank option, six curated options, conditional legacy-value option)
- `api/schemas/admin_people.py` - `TenureRow` docstring updated to describe the D-16 reversal scoped to `appointing_president_party`; field declarations (`Optional[str] = None`) unchanged
- `.planning/phases/27-people-admin/27-CONTEXT.md` - D-16 amended with a dated note; original D-16 text preserved verbatim above the amendment

## Decisions Made
- D-16 amendment (2026-07-09): `appointing_president_party` reversed from free-text to a curated `<select>`, scoped to that field only, per explicit operator request during Phase 27 UAT — `appointed_by` remains free-text as originally decided; the related Seat-as-toggle idea was deferred to `BACKLOG.md` B-020, not implemented here
- No "Other" free-text escape hatch added to the party dropdown — every U.S. president who has appointed a Justice belonged to one of the six curated parties (or was unaffiliated → "Independent"), and the legacy-value fallback `<option>` already covers any pre-existing out-of-list data

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Task 1's `<select>` and Task 2's schema/docstring/decision-record updates are both committed; no code changes remain outstanding for this gap
- Functional confirmation (select-save-reload round-trip, legacy-value display) is explicitly deferred to the Phase 27 UAT retest per this plan's own `<verification>` block — D3 above is flagged `human_judgment: true` for that reason
- No blockers for Phase 27 verification

---
*Phase: 27-people-admin*
*Completed: 2026-07-09*

## Self-Check: PASSED

All created/modified files verified present on disk; both task commits (`d2e37223`, `4e3e4359`) verified present in git log.
