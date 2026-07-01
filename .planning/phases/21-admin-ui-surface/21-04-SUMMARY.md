---
phase: 21-admin-ui-surface
plan: "04"
subsystem: frontend-nav
tags: [nav, admin, layout, gap-closure, NAV-02]
requirements: [NAV-02]
dependency_graph:
  requires: [21-03]
  provides: [NAV-02-closed]
  affects: [app/src/routes/admin/+layout.svelte]
tech_stack:
  added: []
  patterns: [two-row nav, admin layout owns both nav rows (Approach A)]
key_files:
  modified:
    - app/src/routes/admin/+layout.svelte
decisions:
  - "Approach A confirmed: admin layout owns both nav rows; root layout /admin/* exclusion guard left intact to prevent double TopNav render"
  - "TopNav and AdminSubNav both inside existing login guard — /admin/login shows neither row"
metrics:
  duration: 46s
  completed: "2026-07-01"
  tasks_completed: 1
  tasks_total: 1
status: complete
---

# Phase 21 Plan 04: Two-Row Admin Nav (NAV-02 Gap Closure) Summary

## One-liner

Added TopNav variant="public" import and render above AdminSubNav in admin layout, closing the NAV-02 two-row nav gap with the login guard preserving /admin/login exclusion.

## What Was Built

- `app/src/routes/admin/+layout.svelte` updated with two minimal changes:
  1. `import TopNav from '$lib/components/TopNav.svelte';` added to script block
  2. `<TopNav variant="public" />` rendered immediately before `<AdminSubNav />` inside the `page.route.id !== '/admin/login'` guard

The root layout (`app/src/routes/+layout.svelte`) was confirmed unchanged — its `/admin/*` exclusion guard (`!page.url.pathname.startsWith('/admin')`) remains on line 8, ensuring exactly one TopNav renders on admin pages with no double-render.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add TopNav to admin layout — two-row nav fix (NAV-02, D-14, D-15) | 9527deab | app/src/routes/admin/+layout.svelte |

## Verification

- `grep -n 'TopNav' app/src/routes/admin/+layout.svelte` returns import line (5) and render line (10) — PASS
- `grep -n 'startsWith' app/src/routes/+layout.svelte` returns `/admin` exclusion guard (line 8) — PASS (root layout unchanged)
- `npx svelte-check --tsconfig ./tsconfig.json --threshold error` — 0 errors, 17 warnings — PASS
- Login guard condition `page.route.id !== '/admin/login'` preserved — /admin/login shows neither nav row — PASS

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new trust boundaries or network surface introduced. T-21-04-LOGINPAGE and T-21-04-DOUBLENAV mitigations confirmed in place.

## Self-Check: PASSED

- `app/src/routes/admin/+layout.svelte` — file exists and contains both TopNav import and render
- Commit `9527deab` present in git log
- Root layout exclusion guard at line 8 of `app/src/routes/+layout.svelte` — unchanged
