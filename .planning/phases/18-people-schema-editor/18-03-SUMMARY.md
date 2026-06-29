---
phase: "18"
plan: "03"
subsystem: frontend
status: complete
tags: [svelte, is_justice, conditional-ui, badge, editor]
dependency_graph:
  requires: ["18-02"]
  provides: ["PEOPLE-06", "PEOPLE-07"]
  affects:
    - app/src/routes/admin/people/[id]/+page.svelte
    - app/src/routes/admin/people/[id]/+page.server.ts
    - app/src/routes/admin/people/+page.svelte
    - app/src/routes/admin/people/+page.server.ts
tech_stack:
  added: []
  patterns:
    - "$state reactive conditional UI (isJustice mirrors showAddRoleForm pattern)"
    - "{#if isJustice} DOM-absent inputs treated as 'leave unchanged' by save action"
    - "HTML checkbox submits 'on' when checked; absent when unchecked"
key_files:
  created: []
  modified:
    - app/src/routes/admin/people/[id]/+page.svelte
    - app/src/routes/admin/people/[id]/+page.server.ts
    - app/src/routes/admin/people/+page.svelte
    - app/src/routes/admin/people/+page.server.ts
decisions:
  - "isJustice re-seeded inside existing \$effect (no second \$effect created — soft-nav safe)"
  - "Checkbox uses browser-default styling per UI-SPEC (no custom toggle widget)"
  - "Role, Court Tenure, and Appointment cards all wrapped in {#if isJustice} — DOM-absent when unchecked"
  - "is_justice parsed via formData.get('is_justice') === 'on' — correct for HTML checkbox semantics"
  - "Justice badge uses accent color #93c5fd distinct from warning chip #f59e0b"
metrics:
  duration: 18
  completed_date: "2026-06-29"
  tasks_completed: 3
  files_modified: 4
---

# Phase 18 Plan 03: is_justice Editor UI Summary

**One-liner:** Reactive is_justice checkbox with real-time DOM show/hide of bench sections, is_justice in save PATCH body, and Justice badge in directory listing.

---

## What Was Built

### Task 1 — is_justice checkbox and conditional bench sections (editor)

In `app/src/routes/admin/people/[id]/+page.svelte`:

- Added `let isJustice = $state<boolean>(data.person.is_justice ?? false)` near the other `$state` declarations (mirrors the `showAddRoleForm` pattern).
- Re-seeded `isJustice = data.person.is_justice ?? false` inside the existing `$effect` on `data.person.id` so soft-navigation between people resets the checkbox correctly. No second `$effect` created.
- Inserted the Is Justice checkbox div immediately after the `<h2>Basic Info</h2>` heading and before the Full name field, using the exact markup from UI-SPEC Component Inventory item 1: wrapper div with `margin-bottom: 16px; display: flex; align-items: center; gap: 8px`, native checkbox with `name="is_justice" id="is_justice" bind:checked={isJustice}`, and label with `for="is_justice"`.
- Wrapped the Role select div (including inline add-role form) in `{#if isJustice}` ... `{/if}` (D-05).
- Wrapped the Court Tenure card div in `{#if isJustice}` ... `{/if}` (D-07).
- Wrapped the Appointment card div in `{#if isJustice}` ... `{/if}` (D-07).

Per D-08, when these sections are hidden, their inputs are absent from the DOM and are not submitted — the save action's "absent = leave unchanged" behavior handles this correctly.

### Task 2 — is_justice in save action and PATCH body

In `app/src/routes/admin/people/[id]/+page.server.ts`:

- Added `is_justice: boolean` to the `PersonDetail` interface (Phase 18 comment).
- Added `const is_justice = formData.get('is_justice') === 'on'` to the save action after existing field parsing. The checkbox is at the top of the Basic Info card (always present regardless of isJustice state) so it is always submitted reliably.
- Added `is_justice` to the PATCH body `JSON.stringify({...})` call alongside the other person fields.

### Task 3 — Justice badge in directory listing

In `app/src/routes/admin/people/+page.server.ts`:

- Added `is_justice: boolean` to the `PersonListItem` type. The field flows through the existing `people = await res.json()` load with no additional fetch.

In `app/src/routes/admin/people/+page.svelte`:

- Added a `{#if person.is_justice}` block in the Name `<td>` that renders a `<span>` badge with text "Justice" and the exact style from UI-SPEC Component Inventory item 3: accent color `#93c5fd`, `rgba(147,197,253,0.15)` fill, `border-radius: 4px`, `padding: 2px 6px`, `font-size: 14px`, `margin-left: 8px`. The badge is visually distinct from the warning chip (`#f59e0b`) used for missing fields.

---

## Verification

`npx svelte-check --tsconfig ./tsconfig.json --threshold error` reports **0 errors** after all changes.

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The is_justice checkbox adds a field to an existing form action. SvelteKit's built-in CSRF origin check and the existing ADMIN_TOKEN proxy guard apply (T-18-CSRF — accepted per threat model). No new attack surface.

---

## Self-Check: PASSED

- [x] `app/src/routes/admin/people/[id]/+page.svelte` — modified (isJustice state, checkbox, {#if} wrappers)
- [x] `app/src/routes/admin/people/[id]/+page.server.ts` — modified (PersonDetail.is_justice, save action parsing + PATCH body)
- [x] `app/src/routes/admin/people/+page.svelte` — modified (Justice badge in Name td)
- [x] `app/src/routes/admin/people/+page.server.ts` — modified (PersonListItem.is_justice)
- [x] Commit c0bb5c0f — feat(18-03): add is_justice checkbox and conditional bench sections to editor
- [x] Commit d9e71ce — feat(18-03): render Justice badge in people directory listing
- [x] svelte-check: 0 errors
