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
duration: 5min
completed: 2026-06-16
---

# Phase 06 Plan 02: Login Page + Form Action Summary

**Dark-theme /admin/login page with SvelteKit form action — constant-time credential validation via timingSafeEqual, HMAC cookie set via session.ts contract, single generic error for all failure modes (no enumeration); end-to-end flow human-verified**

## Performance

- **Duration:** ~5 min (2 automated tasks + human-verify checkpoint)
- **Started:** 2026-06-16T13:33:02Z
- **Completed:** 2026-06-16T14:00:00Z
- **Tasks:** 3 of 3 complete
- **Files modified:** 2

## Accomplishments

- `app/src/routes/admin/login/+page.server.ts` — Load guard redirects already-authenticated operators from `/admin/login` to `/admin`; default form action reads `username`/`password` from formData, compares with `timingSafeEqual` (length-mismatch-guarded), calls `signSession` + `cookies.set` on success, returns `fail(401, { error: 'Invalid username or password.' })` on any failure
- `app/src/routes/admin/login/+page.svelte` — Dark-theme login card (Svelte 5 Runes, `let { form } = $props()`): `#0f1117` full-bleed background, `#1e293b` card, `#334155` borders, 20px/600 "Admin Login" heading, `autofocus` username input, password input, `role="alert"` inline error bound to `form.error`, 44px "Log in" submit button, `<svelte:head>` title
- Human-verify checkpoint (Task 3) approved: all 6 verification steps passed — dark card renders correctly, wrong credentials show generic error without setting a cookie, correct credentials set `scotus_admin_session` cookie and redirect to `/admin`, already-authed `/admin/login` visit bounces immediately to `/admin`

## Task Commits

1. **Task 1: Login form action (+page.server.ts)** — `aff77b0`
2. **Task 2: Login page UI (+page.svelte)** — `ac88477`
3. **Task 3: Verify login flow end-to-end** — Human-verified "approved" (no code commit; checkpoint gate passed)

## Files Created/Modified

- `app/src/routes/admin/login/+page.server.ts` — New file: load guard (locals.session → redirect /admin) + default form action (timingSafeEqual credential check, signSession, cookies.set, redirect /admin on success; fail(401) on any failure)
- `app/src/routes/admin/login/+page.svelte` — New file: dark login card, Svelte 5 Runes form prop, method=POST form, username/password inputs with labels, role=alert error, 44px "Log in" button, svelte:head title

## Decisions Made

- Error string `'Invalid username or password.'` used exactly once; identical for wrong username, wrong password, and empty inputs (D-13, T-06-06 — no user enumeration).
- `timingSafeEqual` length-mismatch guard: check `buf.length === expectedBuf.length` before calling the function; treat length mismatch as a failed compare rather than letting timingSafeEqual throw (T-06-07).
- No `logout` action in this file — plan note explicitly resolves the PATTERNS.md vs UI-SPEC discrepancy: logout lives on `/admin?/logout` in Plan 03.
- `autofocus` retained on username input despite Svelte a11y lint warning — UI-SPEC Accessibility Notes explicitly require it ("focus is placed on the Username input (`autofocus` attribute)").

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Svelte a11y lint emits a warning for `autofocus` on the username input. This is expected and intentional — the UI-SPEC mandates it. The warning is not an error and does not block the build or type-check.

## Threat Model Compliance

| Threat | Status |
|--------|--------|
| T-06-06: Information Disclosure — login error message | Mitigated — single generic "Invalid username or password." for all failure modes; no user enumeration |
| T-06-07: Spoofing — credential timing oracle | Mitigated — timingSafeEqual for both username and password; length-mismatch handled before call |
| T-06-08: Tampering — session issued on partial match | Mitigated — cookie set only when BOTH username AND password match; failure path returns fail() and never calls cookies.set |
| T-06-09: Information Disclosure — credentials in client bundle | Mitigated — ADMIN_USERNAME/ADMIN_PASSWORD imported only via $env/static/private in .server.ts |
| T-06-10: Repudiation — empty-credential bypass | Mitigated — server requires non-empty matches independent of client required attribute |
| T-06-SC: Supply chain | Accepted — no new packages installed |

## Known Stubs

None — both files are fully wired. The login form action calls `signSession` from `session.ts` (Plan 01 contract), and the Svelte page binds `form.error` from the action's `fail()` response. AUTH-01 is fully satisfied.

## Threat Flags

No new threat surface beyond what is documented in the plan's threat model.

## Self-Check: PASSED

- app/src/routes/admin/login/+page.server.ts: FOUND
- app/src/routes/admin/login/+page.svelte: FOUND
- Commit aff77b0 (Task 1 — login form action): FOUND
- Commit ac88477 (Task 2 — login page UI): FOUND
- Task 3 (human-verify): APPROVED by operator

---
*Phase: 06-auth*
*Completed: 2026-06-16*
