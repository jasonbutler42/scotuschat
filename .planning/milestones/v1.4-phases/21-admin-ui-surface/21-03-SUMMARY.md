---
phase: 21-admin-ui-surface
plan: "03"
subsystem: frontend-nav
status: complete
tags: [nav, svelte, admin, cleanup]
dependency_graph:
  requires: []
  provides: [AdminSubNav component, unified admin nav layout, dead-code removal]
  affects: [app/src/lib/components/TopNav.svelte, app/src/routes/admin/+layout.svelte]
tech_stack:
  added: []
  patterns: [Svelte 5 Runes, inline CSS, SvelteKit admin layout]
key_files:
  created:
    - app/src/lib/components/AdminSubNav.svelte
  modified:
    - app/src/routes/admin/+layout.svelte
    - app/src/lib/components/TopNav.svelte
decisions:
  - "AdminSubNav carries admin links and logout, preserving exact TopNav padding (12px 24px) for identical row height"
  - "variant='admin' branch confirmed dead (grep gate) before TopNav edit; prop narrowed to 'public' only"
  - "Login-page gate (pathname !== '/admin/login') left untouched — login page still shows neither nav row"
metrics:
  duration_seconds: 126
  completed_date: "2026-07-01"
  tasks_completed: 3
  files_changed: 3
requirements_closed: [NAV-02]
---

# Phase 21 Plan 03: Admin Sub-Navigation Unification Summary

Admin sub-navigation unified via new `AdminSubNav` component + layout rewire + TopNav dead-code removal.

## What Was Built

**Task 1 — AdminSubNav component** (`7ae23625`)
New `app/src/lib/components/AdminSubNav.svelte`: `<nav aria-label="Admin navigation">` with bg `#1e293b`, `padding: 12px 24px` (inherited verbatim from TopNav for identical row height), links to Pipeline Runner / Arguments / People Editor, and a right-aligned logout form targeting `/admin?/logout`. Hover handlers on the Log out button match the former TopNav admin-variant button exactly.

**Task 2 — Wire AdminSubNav into admin layout** (`045f4ac9`)
`app/src/routes/admin/+layout.svelte` now imports `AdminSubNav` and renders `<TopNav variant="public" /><AdminSubNav />` inside the existing `pathname !== '/admin/login'` guard. The login page continues to show neither nav row.

**Task 3 — Remove dead variant="admin" branch from TopNav** (`d3b89a16`)
Grep gate confirmed zero `variant="admin"` usages in `app/src` before editing. `TopNav.svelte` narrowed: prop type `'public' | 'admin'` → `'public'`; `{:else}` admin branch (lines 38-90) removed; `bgColor` and `aria-label` ternaries collapsed to the public literal values. Public variant markup is byte-for-byte unchanged in behaviour.

## Acceptance Criteria Verified

- `AdminSubNav.svelte` exists with `aria-label="Admin navigation"` ✓
- Nav contains `/admin/pipeline`, `/admin/arguments`, `/admin/people` links and `/admin?/logout` form ✓
- Nav padding is exact string `padding: 12px 24px` ✓
- Label strings Pipeline Runner, Arguments, People Editor, Log out all present ✓
- `+layout.svelte` imports AdminSubNav, contains `<TopNav variant="public" />` and `<AdminSubNav />`, no `variant="admin"` ✓
- Login-page guard still wraps nav rows ✓
- `grep -rn 'variant="admin"' app/src` returns `NO_ADMIN_VARIANT_USAGES` ✓
- TopNav `variant` prop type is `'public'` only, no `variant === 'admin'` conditional ✓
- `svelte-check` 0 errors after every task ✓

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundary changes introduced. Logout form targets existing `/admin?/logout` action unchanged.

## Self-Check: PASSED

- `app/src/lib/components/AdminSubNav.svelte` — FOUND
- `app/src/routes/admin/+layout.svelte` — FOUND (modified)
- `app/src/lib/components/TopNav.svelte` — FOUND (modified)
- Commit `7ae23625` — FOUND (feat(21-03): create AdminSubNav component)
- Commit `045f4ac9` — FOUND (feat(21-03): wire AdminSubNav into admin layout)
- Commit `d3b89a16` — FOUND (refactor(21-03): remove dead variant=admin branch from TopNav)
