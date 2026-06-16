---
phase: 06-auth
plan: "03"
subsystem: auth
status: checkpoint-pending
tags: [auth, admin, logout, layout, svelte5]
dependency_graph:
  requires: ["06-01"]
  provides: ["AUTH-03", "admin-shell", "logout-action"]
  affects: ["06-auth-complete"]
tech_stack:
  added: []
  patterns:
    - SvelteKit named form action (logout)
    - Isolated admin layout (no public layout import)
    - Svelte 5 Runes ($props, {@render children()})
    - WCAG 2.5.5 touch target (44px min-height)
    - aria-disabled on disabled nav spans
key_files:
  created:
    - app/src/routes/admin/+page.server.ts
    - app/src/routes/admin/+layout.svelte
    - app/src/routes/admin/+page.svelte
  modified: []
decisions:
  - "Logout action lives on /admin?/logout (admin/+page.server.ts) — cookies.delete path '/' matches sessionCookieOptions from Plan 01 (T-06-12)"
  - "Admin layout imports ../../app.css (one level deeper than public layout) and is fully isolated from public +layout.svelte (D-08)"
  - "Hover state on Log out button implemented via Svelte onmouseenter/onmouseleave event handlers on the button element (inline style approach consistent with codebase)"
metrics:
  duration_minutes: 8
  completed_date: "2026-06-16"
  tasks_completed: 2
  tasks_total: 3
  files_created: 3
  files_modified: 0
---

# Phase 6 Plan 03: Admin Shell + Logout Summary

**One-liner:** Isolated admin layout shell (wordmark, disabled Pipeline Runner/People Editor spans, Log out form) with logout action that deletes `scotus_admin_session` on `path: '/'` and redirects to `/admin/login` (AUTH-03).

---

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Logout named action | `1d84e48` | `app/src/routes/admin/+page.server.ts` |
| 2 | Admin layout shell + dashboard stub | `9f76672` | `app/src/routes/admin/+layout.svelte`, `app/src/routes/admin/+page.svelte` |
| 3 | Human-verify checkpoint | — | awaiting human verification |

---

## What Was Built

### Task 1 — `admin/+page.server.ts`

Exports a single `logout` named action. It calls `cookies.delete(SESSION_COOKIE_NAME, { path: '/' })` (path matches `sessionCookieOptions.path` from `session.ts`), then `throw redirect(302, '/admin/login')`. No `load` function — the dashboard stub page needs no server data. Satisfies AUTH-03: the deleted cookie cannot pass `verifySession` on the next request; the Plan 01 `hooks.server.ts` guard then redirects to login.

### Task 2 — `admin/+layout.svelte`

Isolated admin layout. Imports `../../app.css` (correct relative path from admin subdirectory). Uses Svelte 5 Runes: `let { children } = $props()` and `{@render children()}`. Nav bar: `#1e293b` background, `1px solid #334155` border-bottom. Contains:
- "SCOTUS CHAT" wordmark (14px/600/`#94a3b8`, letter-spacing 0.05em — matches public nav)
- "Pipeline Runner" and "People Editor" as `<span aria-disabled="true" aria-label="... (coming soon)">` — NOT `<a>` tags, preventing navigation and 404s (D-09, T-06-13)
- `<form method="POST" action="/admin?/logout" style="margin-left: auto;">` with a Log out button (min-height 44px, WCAG 2.5.5)
- Does NOT import or reference the public `+layout.svelte` (D-08, T-06-14)

### Task 2 — `admin/+page.svelte`

Dashboard stub. `<svelte:head><title>Admin — SCOTUS Chat</title></svelte:head>`. Page structure: `<main>` (`#0f1117` bg), header bar (`#1e293b`, `#334155` border), `<h1>Admin</h1>` (20px/600/`#e2e8f0`), content area with body copy "Select a tool from the navigation to get started." (16px/400/`#94a3b8`).

---

## Verification Results

- `npm run check`: 0 errors, 5 pre-existing warnings (ChatBubble.svelte state_referenced_locally × 4, admin/login autofocus × 1 — all pre-existing from prior plans)
- `npm run build`: succeeded cleanly

---

## Deviations from Plan

### Auto-applied Implementation Details

**1. [Rule 2 - Missing Functionality] Hover state on Log out button**
- **Found during:** Task 2 implementation
- **Issue:** UI-SPEC specifies "On hover: color `#e2e8f0`; border-color `#e2e8f0`" but inline CSS `style=` attributes cannot express pseudo-selectors
- **Fix:** Used Svelte `onmouseenter` / `onmouseleave` event handlers on the button to toggle color/borderColor imperatively — consistent with the inline-styles-only convention
- **Files modified:** `app/src/routes/admin/+layout.svelte`

**2. [Rule 2 - UI-SPEC alignment] Cookie path discrepancy**
- **Found during:** Task 1 analysis
- **Issue:** UI-SPEC Interaction Contract (line 173) says `cookies.delete(..., { path: '/admin' })` but `session.ts` `sessionCookieOptions` explicitly sets `path: '/'` and the plan action spec requires `path: '/'`
- **Fix:** Used `path: '/'` as the plan and session.ts contract specify — the path at deletion MUST match the path used at set time; using '/admin' would leave the cookie in the browser
- **Files modified:** `app/src/routes/admin/+page.server.ts`

---

## Stub Tracking

No stubs. All three files deliver their complete functionality. The dashboard page body copy "Select a tool from the navigation to get started." is intentional finished copy (not a placeholder) — the admin area genuinely has no tools yet in Phase 6.

---

## Threat Surface Scan

All files align with the threat model in 06-03-PLAN.md:
- T-06-11: logout action deletes cookie — implemented
- T-06-12: path '/' matches set path — implemented
- T-06-13: disabled nav as `<span>` not `<a>` — implemented
- T-06-14: admin layout does not import public layout — confirmed (grep verified no `../+layout` import)

No new threat surface introduced beyond what the plan's threat model covers.

---

## Known Stubs

None.

---

## Checkpoint Pending

Task 3 is a `checkpoint:human-verify`. Human must verify end-to-end in browser:
1. Admin shell renders correctly at `/admin` (wordmark, disabled placeholders, Log out button, "Admin" heading)
2. Public "Cases" nav link is absent (isolated layout)
3. Log out clears `scotus_admin_session` cookie and redirects to `/admin/login`
4. Post-logout `/admin` access redirects to `/admin/login` (AUTH-03)
5. Disabled nav items are non-navigating with `aria-disabled="true"`

---

## Self-Check

Files exist:
- `app/src/routes/admin/+page.server.ts` — created
- `app/src/routes/admin/+layout.svelte` — created
- `app/src/routes/admin/+page.svelte` — created

Commits exist: `1d84e48` (Task 1), `9f76672` (Task 2)
