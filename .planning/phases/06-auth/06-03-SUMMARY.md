---
phase: 06-auth
plan: "03"
subsystem: auth
tags: [auth, admin, logout, layout, svelte5]
dependency_graph:
  requires: ["06-01", "06-02"]
  provides: ["AUTH-03", "admin-shell", "logout-action"]
  affects: ["07-pipeline-runner", "08-people-editor"]
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
key-decisions:
  - "Logout action lives on /admin?/logout (admin/+page.server.ts) — cookies.delete path '/' matches sessionCookieOptions from Plan 01 (T-06-12)"
  - "Admin layout imports ../../app.css (one level deeper than public layout) and is fully isolated from public +layout.svelte (D-08)"
  - "Hover state on Log out button implemented via Svelte onmouseenter/onmouseleave event handlers (inline style approach, no CSS pseudo-selectors)"
  - "Disabled nav placeholders as <span aria-disabled='true'> not <a> elements — prevents navigation/404s for unbuilt Phase 7/8 routes (D-09, T-06-13)"
requirements-completed: [AUTH-03]
metrics:
  duration_minutes: 45
  completed_date: "2026-06-16"
  tasks_completed: 3
  tasks_total: 3
  files_created: 3
  files_modified: 0
---

# Phase 6 Plan 03: Admin Shell, Logout, and Dashboard Stub Summary

**Isolated SvelteKit admin layout shell with dark nav, HMAC cookie logout action deleting `scotus_admin_session` on path `/`, and dashboard stub — completing AUTH-03 (logout immediately invalidates the session)**

---

## Performance

- **Duration:** ~45 min (including human-verify checkpoint)
- **Started:** 2026-06-16T14:00:00Z
- **Completed:** 2026-06-16T14:45:00Z
- **Tasks:** 3 (2 code tasks + 1 human-verify checkpoint — all complete)
- **Files modified:** 3 created, 0 modified

---

## Task Commits

Each task committed atomically:

1. **Task 1: Logout named action (+page.server.ts)** — `1d84e48` (feat)
2. **Task 2: Admin layout shell + dashboard stub** — `9f76672` (feat)
3. **Task 3: Human-verify checkpoint** — no code commit; human responded "everything listed is verified" (all 6 verification steps passed)

---

## What Was Built

### Task 1 — `admin/+page.server.ts`

Exports a single `logout` named action. Calls `cookies.delete(SESSION_COOKIE_NAME, { path: '/' })` (path matches `sessionCookieOptions.path` from `session.ts`), then `throw redirect(302, '/admin/login')`. No `load` function — the dashboard stub needs no server data. Satisfies AUTH-03: the deleted cookie cannot pass `verifySession` on the next request; the Plan 01 `hooks.server.ts` guard then redirects to login.

### Task 2 — `admin/+layout.svelte`

Isolated admin layout. Imports `../../app.css` (correct relative path from admin subdirectory). Uses Svelte 5 Runes: `let { children } = $props()` and `{@render children()}`. Nav bar: `#1e293b` background, `1px solid #334155` border-bottom. Contains:
- "SCOTUS CHAT" wordmark (14px/600/`#94a3b8`, letter-spacing 0.05em — matches public nav exactly)
- "Pipeline Runner" and "People Editor" as `<span aria-disabled="true" aria-label="... (coming soon)">` — NOT `<a>` tags (D-09, T-06-13)
- `<form method="POST" action="/admin?/logout" style="margin-left: auto;">` with a Log out button (min-height 44px, WCAG 2.5.5)
- Does NOT import or reference the public `+layout.svelte` (D-08, T-06-14)

### Task 2 — `admin/+page.svelte`

Dashboard stub. `<svelte:head><title>Admin — SCOTUS Chat</title></svelte:head>`. Page structure: `<main>` (`#0f1117` bg), header bar (`#1e293b`, `#334155` border), `<h1>Admin</h1>` (20px/600/`#e2e8f0`), content area with body copy "Select a tool from the navigation to get started." (16px/400/`#94a3b8`).

---

## Verification Results

- `npm run check`: 0 errors (pre-existing warnings: ChatBubble.svelte state_referenced_locally x4, admin/login autofocus x1 — from prior plans)
- `npm run build`: succeeded cleanly
- **Human checkpoint (Task 3):** All 6 verification steps passed — admin shell renders isolated (no Cases link), disabled placeholders non-navigating with `aria-disabled="true"`, logout clears cookie and redirects to `/admin/login`, post-logout `/admin` redirects to login (AUTH-03 confirmed)

---

## Files Created/Modified

- `app/src/routes/admin/+page.server.ts` — logout named action: deletes session cookie on path `/`, redirects 302 to `/admin/login`
- `app/src/routes/admin/+layout.svelte` — isolated admin shell layout: dark nav, wordmark, disabled placeholders, Log out form
- `app/src/routes/admin/+page.svelte` — dashboard stub: "Admin" heading, stub body copy, dark theme tokens

---

## Decisions Made

- `cookies.delete` uses `path: '/'` — must match the `path: '/'` in `sessionCookieOptions` (Plan 01); a path mismatch would leave the cookie in the browser after logout (T-06-12 mitigated)
- UI-SPEC line 173 said `path: '/admin'` but that conflicts with the actual set path; plan and `session.ts` take precedence — used `path: '/'`
- Hover state on Log out button implemented via `onmouseenter`/`onmouseleave` Svelte event handlers — inline style attribute cannot express CSS pseudo-selectors; consistent with codebase convention
- Disabled nav items as `<span aria-disabled="true">` not `<a>` elements — prevents navigation to unbuilt Phase 7/8 routes and avoids 404s (D-09, T-06-13)

---

## Deviations from Plan

### Auto-applied Implementation Details

**1. [Rule 2 - Missing Functionality] Hover state on Log out button**
- **Found during:** Task 2 implementation
- **Issue:** UI-SPEC specifies hover color/border change but inline `style=` attributes cannot express CSS pseudo-selectors
- **Fix:** Used Svelte `onmouseenter` / `onmouseleave` event handlers on the button to toggle `color` and `borderColor` imperatively — consistent with inline-styles-only convention in this codebase
- **Files modified:** `app/src/routes/admin/+layout.svelte`
- **Committed in:** `9f76672` (Task 2 commit)

**2. [Rule 2 - UI-SPEC Conflict] Cookie path '/' vs '/admin' discrepancy**
- **Found during:** Task 1 analysis
- **Issue:** UI-SPEC Interaction Contract specified `path: '/admin'` for delete but `session.ts` `sessionCookieOptions` sets `path: '/'` — path at deletion must match path at set time
- **Fix:** Used `path: '/'` as plan and `session.ts` contract require; `/admin` path would leave the cookie in the browser
- **Files modified:** `app/src/routes/admin/+page.server.ts`
- **Committed in:** `1d84e48` (Task 1 commit)

---

**Total deviations:** 2 auto-applied (1 missing functionality, 1 spec conflict resolution)
**Impact on plan:** Both required for correctness; no scope creep.

---

## Known Issues (Deferred — layout nesting bugs)

Two UI bugs observed during human verification (Task 3). These do NOT block AUTH-03 or Phase 6 completion — they are cosmetic nesting issues to resolve in a gap-closure plan before Phase 7 development.

**1. Admin nav appears on /admin/login before authentication**
- **Observed:** `routes/admin/+layout.svelte` wraps all routes under `/admin/`, including the login page itself. The login page shows the wordmark, greyed placeholders, and Log out button before the user is authenticated.
- **Impact:** Confusing UX — nav items that require authentication appear on the unauthenticated login screen.
- **Fix needed:** Use SvelteKit layout groups (e.g., move authenticated routes under `routes/(authed)/admin/`) so the admin shell layout applies only after login, not to `/admin/login`.

**2. Doubled "SCOTUS CHAT" header on admin pages**
- **Observed:** The public root `+layout.svelte` wraps all routes by default, including `/admin/*`. Both the root layout nav and the admin layout nav render "SCOTUS CHAT", producing two stacked nav bars on admin pages.
- **Impact:** Two nav bars visible simultaneously — one from the public layout (with "Cases" link), one from the admin layout (with Pipeline Runner/People Editor placeholders).
- **Fix needed:** Break the admin subtree out of the root public layout using SvelteKit layout groups, so `/admin/*` routes receive only the admin layout.

Both issues share the same root cause (SvelteKit layout group refactor needed) and should be resolved together before Phase 7 UX review.

---

## Stub Tracking

None. All three files deliver their complete functionality. The dashboard body copy "Select a tool from the navigation to get started." is intentional finished copy — the admin area has no tools yet in Phase 6.

---

## Threat Surface Scan

All files align with the threat model in 06-03-PLAN.md — no new surface beyond plan scope:
- T-06-11: logout action deletes cookie — implemented and verified
- T-06-12: `path: '/'` matches set path — implemented and verified
- T-06-13: disabled nav as `<span>` not `<a>` — implemented and verified
- T-06-14: admin layout does not import public layout — confirmed (no `../+layout` import)

---

## Self-Check: PASSED

Files exist:
- `app/src/routes/admin/+page.server.ts` — FOUND
- `app/src/routes/admin/+layout.svelte` — FOUND
- `app/src/routes/admin/+page.svelte` — FOUND

Commits exist: `1d84e48` (Task 1), `9f76672` (Task 2)

---

## Next Phase Readiness

Phase 6 (Auth) is complete:
- AUTH-01: login form + credential check + cookie set — Plan 02
- AUTH-02: route guard on all `/admin/*` routes — Plan 01
- AUTH-03: logout + immediate session invalidation — this plan

Phase 7 (Pipeline Runner) is unblocked. Before starting Phase 7:
- Resolve the layout nesting known issues above (gap-closure plan recommended first)
- Use `--research` flag when planning Phase 7 (subprocess management, job state machine, Spaces upload all interact)
- Set `BODY_SIZE_LIMIT=10M` in DO App Platform env (default 512KB blocks SCOTUS PDFs)
- Set `ORIGIN`, `PROTOCOL_HEADER`, `HOST_HEADER` in DO env vars (silent CSRF 403 without them)

---
*Phase: 06-auth*
*Completed: 2026-06-16*
