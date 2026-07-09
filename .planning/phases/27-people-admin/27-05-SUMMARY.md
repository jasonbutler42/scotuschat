---
phase: 27-people-admin
plan: 05
subsystem: ui
tags: [sveltekit, svelte5-runes, forms, admin-service]

# Dependency graph
requires:
  - phase: 27-people-admin
    plan: 01
    provides: Person.birthdate column, TenureRow.appointed_by/appointing_president_party, role_id/role_name removed from admin_people schemas
  - phase: 27-people-admin
    plan: 03
    provides: "get_person_detail/update_person carrying birthdate + per-tenure appointed_by/appointing_president_party with no role_id; POST /people create_person endpoint"
provides:
  - "Restructured /admin/people/[id] editor: Identity / Photo / Biography / Person Type card layout matching 27-UI-SPEC.md"
  - "Person Type card: Bench/Advocate segmented toggle (sets is_justice) that slide-reveals Birth Date + disabled Death Date + repeatable Tenure Period sub-cards"
  - "Tenure Period sub-cards with free-text Appointing President / President's Party, disabled Reason Left, Remove button"
  - "save action extended to PATCH birthdate + per-tenure appointed_by/appointing_president_party; is_justice parsed from a hidden 'true'/'false' input"
  - "Role field and inline-role-creation machinery (select, createRole action, RoleItem type, roles-building load() loop) fully deleted (D-10)"
  - "Merge and Delete cards guarded behind {#if data.person.id} for reuse by the create route (Plan 27-06)"
affects: [27-06-plan]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-form field association via the HTML `form=\"save-form\"` attribute — used for the Person Type card's hidden is_justice/birthdate/tenures inputs, which sit outside the <form id=\"save-form\"> element (the Photo/Biography form interrupts the DOM between them) but still submit as part of the ?/save action. Same idiom the file already used for the standalone Save button (Gap E fix)."
    - "Segmented Bench/Advocate toggle reuses the exact list-page tab-toggle visual/ARIA idiom (aria-pressed, solid-accent-fill-when-selected) verbatim inside the Person Type card"

key-files:
  created: []
  modified:
    - app/src/routes/admin/people/[id]/+page.server.ts
    - app/src/routes/admin/people/[id]/+page.svelte

key-decisions:
  - "Split the combined 'Bio & Photo' card into two visually separate cards (Photo, Biography) per the UI-SPEC's card order, but kept them inside the single existing ?/photo <form> — save/submit behavior is unchanged (bio_text still saves together with photo, Pitfall 7 extended), only the visual card boundary moved"
  - "TenureRow keeps a `seat` field in state and payload with no corresponding input in the sub-card UI (D-18's field list omits Seat) — Task 1 explicitly instructed 'drop nothing else' from the tenure mapping, so seat is carried through silently to avoid wiping existing seat data on save"
  - "Breadcrumb 'People' link and the new 'Cancel' button both target the tab derived from the person's *persisted* is_justice value at load time (`backTab`), not the live in-progress Bench/Advocate toggle state — so navigating away mid-edit returns to the tab the operator actually came from"
  - "Moved the Save Person / Cancel action row to the very bottom of the page (after Merge and Delete), matching the UI-SPEC's explicit card order item 8, even though this differs from today's mid-page placement"
  - "Removed the now-dead roles-building/dedup loop in +page.server.ts's load() (and the RoleItem type, and role_id/role_name from PersonDetail/PersonListItem) since the only consumer — the Role <select> dropdown — is deleted per D-10; this went slightly beyond Task 1's literal action list but is required to fully satisfy D-10's 'fully removed' instruction and leaves no dead code"
  - "is_justice's hidden form input always submits 'true'/'false' (a segmented toggle always has a value), replacing the old checkbox's on/absent-when-unchecked convention — the server parses via `=== 'true'` instead of `=== 'on'`"

requirements-completed: [PEDIT-01, PEDIT-02, PEDIT-03, PEDIT-05, PEDIT-06, PEDIT-07, PEDIT-09, PEDIT-10, PEDIT-11, PEDIT-12]

coverage:
  - id: D1
    description: "save action persists birthdate and per-tenure appointed_by/appointing_president_party via PATCH, with is_justice parsed as a boolean from an always-present toggle value and no role_id anywhere"
    requirement: "PEDIT-02, PEDIT-09"
    verification:
      - kind: unit
        ref: "grep of +page.server.ts confirms zero role_id/createRole matches; PATCH body includes birthdate and tenure objects include appointed_by/appointing_president_party, not reason_ended"
        status: pass
      - kind: other
        ref: "npm run check (svelte-check) — 0 errors"
        status: pass
    human_judgment: false
  - id: D2
    description: "Editor renders Identity/Photo/Biography/Person Type cards with a Bench/Advocate segmented toggle that slide-reveals Birth Date, disabled Death Date, and repeatable Tenure Period sub-cards with disabled Reason Left; Role subsystem fully removed; Merge/Delete guarded for create-route reuse"
    requirement: "PEDIT-01, PEDIT-03, PEDIT-05, PEDIT-06, PEDIT-07, PEDIT-10, PEDIT-11, PEDIT-12"
    verification:
      - kind: unit
        ref: "grep of +page.svelte confirms zero selectedRoleId/showAddRoleForm/ADD_NEW_ROLE_SENTINEL/handleRoleChange/createRole/role_id matches; slide import present; 'Upload photo'/'Save Person' copy present; {#if data.person.id} guards present around Merge and Delete"
        status: pass
      - kind: other
        ref: "npm run check && npm run build — both pass, 0 errors"
        status: pass
    human_judgment: true
    rationale: "Visual verification of the slide animation, card spacing/colors against DESIGN-SYSTEM.md tokens, and the actual Bench<->Advocate data-preservation behavior in a running browser cannot be confirmed by static grep/build checks alone — deferred to phase-level UAT (Plan 27-06 lands the create route in the same wave and phase verification will exercise this template end-to-end)."

duration: 15min
completed: 2026-07-09
status: complete
---

# Phase 27 Plan 5: Person Editor Restructure Summary

**`/admin/people/[id]` rebuilt into Identity/Photo/Biography/Person Type cards with a Bench/Advocate segmented toggle that slide-reveals Birth Date, disabled Death Date, and bordered Tenure Period sub-cards carrying free-text appointment fields — the Role field and its inline-creation machinery are gone entirely**

## Performance

- **Duration:** 15 min
- **Started:** 2026-07-09T05:05:00Z
- **Completed:** 2026-07-09T05:20:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `save` action in `+page.server.ts` now PATCHes `birthdate` and per-tenure `appointed_by`/`appointing_president_party`, parses `is_justice` from an always-present segmented-toggle value, and contains zero `role_id`/`createRole` logic
- Removed the now-dead roles-building/dedup loop from `load()` along with the `RoleItem` type and `role_id`/`role_name` fields on `PersonDetail`/`PersonListItem` — the Role dropdown that fed them no longer exists
- `+page.svelte` renamed "Basic Info" to "Identity" and dropped the "Is Justice" checkbox
- Split the combined "Bio & Photo" card into separate "Photo" and "Biography" cards (same underlying `?/photo` form/action — unchanged save behavior)
- Added a breadcrumb header (`People > {full name}`) that preserves the tab the person belongs to, replacing the plain `← People` back-link
- Added the new "Person Type" card: a Bench/Advocate segmented toggle (reusing the list page's exact tab-toggle visual/ARIA idiom) that sets `is_justice` and, via Svelte's `slide` transition, reveals Birth Date + a disabled Death Date + a "Tenure Periods" sub-heading and repeatable tenure list when Bench is selected
- Restructured each tenure row into a bordered sub-card (Start/End Date, free-text "Appointing President", "President's Party", a disabled "Reason Left", and a "Remove" button) — `seat` is preserved in state/payload with no corresponding input, since D-18's field list omits it
- Deleted the entire Role `<select>` subsystem — `selectedRoleId`, `showAddRoleForm`, `ADD_NEW_ROLE_SENTINEL`, `handleRoleChange`, `cancelAddRole`, and the `createRole` form — none of it carried into the Person Type card
- Guarded the Merge and Delete cards behind `{#if data.person.id}` so Plan 27-06's create route can reuse this file's structure with them hidden
- Replaced the full-width "Save changes" button with a "Save Person" / "Cancel" action row, moved to the bottom of the page per the UI-SPEC's card order

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend the save action for birthdate and per-tenure appointment fields; strip role handling** - `051159f7` (feat)
2. **Task 2: Restructure the editor into Identity / Photo / Biography / Person Type cards** - `de7d55f4` (feat)

## Files Created/Modified
- `app/src/routes/admin/people/[id]/+page.server.ts` - `save` action extended with `birthdate` + per-tenure appointment fields, `is_justice` parsed from toggle value, `role_id`/`createRole` removed; `load()`'s dead roles-building loop and `RoleItem`/`role_id`/`role_name` typing removed
- `app/src/routes/admin/people/[id]/+page.svelte` - Identity/Photo/Biography/Person Type card restructure, breadcrumb header, Bench/Advocate segmented toggle with `transition:slide`, bordered Tenure Period sub-cards, Role subsystem deleted, Merge/Delete guarded, Save Person/Cancel action row

## Decisions Made
- Kept the Photo and Biography cards inside a single `<form action="?/photo">` even though they're now two visually distinct `<div>` cards — matches the UI-SPEC's card-order/title contract while leaving the existing bio+photo-together save mechanic (Pitfall 7 extended) completely untouched.
- `TenureRow.seat` stays in client state and the serialized `tenures` payload with no UI input for it — D-18's sub-card field list (Start/End/Appointing President/President's Party/Reason Left) never mentions Seat, but Task 1 explicitly said "drop nothing else" from the mapping, so removing the input while keeping the field prevents a silent data loss on next save for any person with an existing seat value.
- `backTab` (used by both the breadcrumb "People" link and the new "Cancel" button) is derived from `data.person.is_justice` — the persisted value at load time — not the live Bench/Advocate toggle state, so leaving the page mid-edit always returns to the tab the operator actually arrived from.
- Moved the Save Person/Cancel row to the bottom of the page, after Merge and Delete, following the UI-SPEC's explicit numbered card order (item 8) rather than today's mid-page button placement.
- Removed the dead `roles`/`RoleItem`/role_id`/`role_name` code from `+page.server.ts`'s `load()` and type definitions — not explicitly itemized in Task 1's action list, but required to fully satisfy D-10 ("fully removed... not just from the incomplete check") and to avoid leaving unused code feeding a UI element that no longer exists.
- `is_justice`'s hidden input always submits `'true'`/`'false'` rather than the old checkbox convention (present-when-checked, absent-when-unchecked) — the server's parse changed from `=== 'on'` to `=== 'true'` to match.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug/Dead code] Removed the now-unreachable roles-building loop and Role-only typing from `+page.server.ts`**
- **Found during:** Task 1
- **Issue:** `load()` still fetched the people list to de-duplicate roles for a Role `<select>` dropdown, and `PersonDetail`/`PersonListItem` still typed `role_id`/`role_name` — all of which become dead code once Task 2 deletes the Role subsystem from the component. Leaving it in place would ship unused code and a stale type contract for fields the backend (Plan 27-01/27-03) no longer returns.
- **Fix:** Removed the roles dedup loop, the `roles` variable, the `RoleItem` interface, and `role_id`/`role_name` from `PersonDetail`/`PersonListItem`; updated `load()`'s return value to drop `roles`.
- **Files modified:** `app/src/routes/admin/people/[id]/+page.server.ts`
- **Verification:** `npm run check` (0 errors) and `npm run build` both pass with the component no longer referencing `data.roles` anywhere.
- **Committed in:** `051159f7` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 dead-code cleanup, tightly scoped to D-10's explicit "fully removed" instruction)
**Impact on plan:** Necessary to avoid a stale type contract and genuinely dead code within the same file Task 1 was already modifying. No scope creep beyond D-10's stated intent.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 27-06 (create route) can reuse this file's card structure and rely on the `{#if data.person.id}` guards already in place around Merge/Delete, and on the `form="save-form"` cross-form association pattern for the Person Type card's inputs.
- Phase-level UAT still needs to visually confirm the `slide` animation, DESIGN-SYSTEM.md token application, and that switching Bench→Advocate→Bench in the browser preserves in-progress tenure edits (PEDIT-07) — flagged as `human_judgment: true` in this SUMMARY's coverage block.
- The backend `POST /roles` route and `create_role` service (flagged orphaned by 27-03) are now unambiguously orphaned — their only caller (`createRole` in this file) is deleted. Recommend backlog removal.
- No blockers for downstream plans.

---
*Phase: 27-people-admin*
*Completed: 2026-07-09*

## Self-Check: PASSED

- FOUND: app/src/routes/admin/people/[id]/+page.server.ts
- FOUND: app/src/routes/admin/people/[id]/+page.svelte
- FOUND: .planning/phases/27-people-admin/27-05-SUMMARY.md
- FOUND commit: 051159f7 (Task 1)
- FOUND commit: de7d55f4 (Task 2)
- FOUND commit: 09fd4b45 (SUMMARY)
