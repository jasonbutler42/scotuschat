---
phase: 06-auth
plan: 02
subsystem: auth
tags: [sveltekit, hmac, form-actions, svelte5-runes, node-crypto, timingSafeEqual]

# Dependency graph
requires:
  - phase: 06-01
    provides: signSession, SESSION_COOKIE_NAME, sessionCookieOptions, verifySession, hooks guard (event.locals.session)

provides:
  - /admin/login route with dark-theme centered card UI
  - Login form action: constant-time credential validation, HMAC cookie set, redirect to /admin
  - Already-authed guard in load function (redirects to /admin if locals.session truthy)

affects: [06-03, admin layout, Plan 03 logout action]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - SvelteKit form action with fail(401) for credential errors and throw redirect(302) on success
    - timingSafeEqual with length-mismatch guard (buffer lengths checked before call)
    - Svelte 5 Runes form prop binding: let { form } = $props() for ActionData
    - role=alert on error paragraph for screen reader announcement

key-files:
  created:
    - app/src/routes/admin/login/+page.server.ts
    - app/src/routes/admin/login/+page.svelte
  modified: []

key-decisions:
  - "Error string 'Invalid username or password.' appears exactly once; same message for wrong user and wrong password (no enumeration, D-13)"
  - "Length mismatch handled before timingSafeEqual call to avoid throw (T-06-07)"
  - "No logout action in login +page.server.ts — logout lives on /admin?/logout in Plan 03 per UI-SPEC"
  - "autofocus kept on username input despite Svelte a11y lint warning — UI-SPEC explicitly requires it"

patterns-established:
  - "Login form action pattern: read formData -> timingSafeEqual guards -> fail(401) or cookies.set + redirect"
  - "Inline error display: {#if form?.error} with role=alert, color #ef4444"

requirements-completed: [AUTH-01]

# Metrics
duration: 2min
completed: 2026-06-16
---

# Phase 06 Plan 02: Login Page + Form Action Summary

**Dark-theme /admin/login page with SvelteKit form action — constant-time credential validation via timingSafeEqual, HMAC cookie set via session.ts contract, single generic error for all failure modes (no enumeration)**

## Performance

- **Duration:** ~2 min (automated tasks only; paused at Task 3 checkpoint)
- **Started:** 2026-06-16T13:33:02Z
- **Completed (Tasks 1-2):** 2026-06-16T13:35:17Z
- **Tasks:** 2 of 3 complete (Task 3 is human-verify checkpoint)
- **Files modified:** 2

## Accomplishments
- Login form action validates credentials with `timingSafeEqual` (length-mismatch-guarded), sets signed session cookie on success, returns single generic `fail(401)` on any failure
- Load guard in `+page.server.ts` redirects already-authenticated operators away from `/admin/login` to `/admin`
- Dark-theme login card renders per UI-SPEC: #0f1117 bg, #1e293b card, #334155 borders, 20px/600 heading, 14px labels, 44px submit button
- Inline error bound to `form.error` via `role="alert"` for screen-reader accessibility

## Task Commits

1. **Task 1: Login form action (+page.server.ts)** - `aff77b0` (feat)
2. **Task 2: Login page UI (+page.svelte)** - `ac88477` (feat)
3. **Task 3: Verify login flow end-to-end** - PENDING (human-verify checkpoint)

## Files Created/Modified
- `app/src/routes/admin/login/+page.server.ts` — Load guard (locals.session → redirect /admin) + default form action (timingSafeEqual credential check, signSession, cookies.set, redirect /admin)
- `app/src/routes/admin/login/+page.svelte` — Dark login card, Svelte 5 Runes form prop, method=POST form, username/password inputs, role=alert error, 44px Log in button

## Decisions Made
- Error string `'Invalid username or password.'` used exactly once; identical for wrong username, wrong password, and empty inputs (D-13, T-06-06 no enumeration).
- `timingSafeEqual` length-mismatch guard: check `buf.length === expectedBuf.length` before calling the function to prevent the throw on unequal-length buffers (T-06-07).
- No `logout` action in this file — the plan note explicitly resolves the PATTERNS.md vs UI-SPEC discrepancy: logout lives on `/admin?/logout` in Plan 03.
- `autofocus` retained on username input despite Svelte a11y lint warning — UI-SPEC Accessibility Notes explicitly require it ("focus is placed on the Username input (`autofocus` attribute)").

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Svelte a11y lint emits a warning for `autofocus` on the username input. This is expected and intentional — the UI-SPEC mandates it. The warning is not an error and does not block the build.

## Known Stubs

None — both files are fully wired. The login form action calls `signSession` from `session.ts` (Plan 01 contract) and the Svelte page binds `form.error` from the action's `fail()` response.

## Threat Flags

No new threat surface beyond what is documented in the plan's threat model. All STRIDE entries (T-06-06 through T-06-10) are mitigated in the implementation.

## User Setup Required

Before verifying Task 3, ensure `app/.env` contains:
- `SESSION_SECRET` — minimum 32 characters (HMAC key)
- `ADMIN_USERNAME` — operator login username
- `ADMIN_PASSWORD` — operator login password

## Next Phase Readiness
- Login slice complete and type-checked; build passes
- Task 3 human verification needed to confirm end-to-end cookie flow
- After human approval, Plan 03 can add admin layout shell, dashboard stub, and logout action (`/admin?/logout`)

---
*Phase: 06-auth*
*Completed (partial — awaiting Task 3 human verify): 2026-06-16*
