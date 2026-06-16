---
phase: 06-auth
plan: 01
subsystem: auth
tags: [sveltekit, hmac, session, hooks, typescript, node-crypto]

# Dependency graph
requires:
  - phase: 05-admin-foundation
    provides: FastAPI admin router with ADMIN_TOKEN; config.py Settings base
provides:
  - HMAC session sign/verify contract (session.ts) shared by login action and guard
  - SvelteKit auth guard (hooks.server.ts) protecting all /admin/* routes
  - App.Locals.session boolean type for downstream load functions
  - SESSION_SECRET/ADMIN_USERNAME/ADMIN_PASSWORD documented in config.py and .env.example
affects: [06-02-login-flow, 06-03-admin-shell]

# Tech tracking
tech-stack:
  added:
    - "@types/node (devDependency) — enables node:crypto types in svelte-check"
  patterns:
    - "HMAC-SHA256 session cookie signed with node:crypto createHmac; verified with timingSafeEqual"
    - "Length-mismatch guard before timingSafeEqual to prevent throw on unequal buffers (T-06-04)"
    - "SvelteKit Handle hook as sole auth checkpoint — runs before all load/endpoint handlers"
    - "event.locals.session set unconditionally (true/false) so all downstream loads can read it"

key-files:
  created:
    - app/src/lib/server/session.ts
    - app/src/hooks.server.ts
  modified:
    - app/src/app.d.ts
    - api/core/config.py
    - .env.example
    - app/package.json (added @types/node devDep)

key-decisions:
  - "signSession returns expiryMs.hmacHex; verifySession splits on last dot — handles edge cases where payload could contain dots"
  - "timingSafeEqual called only after explicit length check to avoid throw; returns false on mismatch, never 500"
  - "event.locals.session assigned unconditionally (before the guard branch) so Plan 02 login load can read it for already-authenticated redirect"
  - "@types/node installed as devDependency — required for node:crypto types; svelte-kit generated tsconfig already referenced 'node' types"

# Metrics
duration: 5min
completed: 2026-06-16
---

# Phase 06, Plan 01: HMAC Session Contract and Route Guard Summary

**HMAC-SHA256 session sign/verify contract (node:crypto) and SvelteKit hooks.server.ts guard protecting all /admin/* routes except /admin/login**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-16T13:24:12Z
- **Completed:** 2026-06-16T13:29:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- `app/src/lib/server/session.ts` — exports `SESSION_COOKIE_NAME`, `signSession`, `verifySession`, `sessionCookieOptions`; HMAC-SHA256 over expiry timestamp; `timingSafeEqual` with pre-check length guard; expiry rejects sessions past `Date.now()`
- `app/src/hooks.server.ts` — exports `handle: Handle`; guards all `/admin/*` except `/admin/login`; sets `event.locals.session` unconditionally before resolve; `redirect(302, '/admin/login')` for unauthenticated requests
- `app/src/app.d.ts` — `App.Locals` now declares `session: boolean`
- `api/core/config.py` — additive comment block documenting `SESSION_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` as SvelteKit-side vars; no new pydantic fields
- `.env.example` — `SESSION_SECRET=`, `ADMIN_USERNAME=`, `ADMIN_PASSWORD=`, `ADMIN_TOKEN=` placeholders added with explanatory comments
- `app/.env` — `SESSION_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_TOKEN` added as dev placeholders (required for `$env/static/private` to resolve during svelte-check)

## Task Commits

1. **Task 1: HMAC session sign/verify contract + Locals typing** — `0befe92`
2. **Task 2: hooks.server.ts auth guard** — `c5fac58`
3. **Task 3: Document SvelteKit auth env vars** — `6db74f8`

## Files Created/Modified

- `app/src/lib/server/session.ts` — New file: SESSION_COOKIE_NAME, signSession, verifySession, sessionCookieOptions (74 lines)
- `app/src/hooks.server.ts` — New file: handle export with /admin/* guard (33 lines)
- `app/src/app.d.ts` — Added `interface Locals { session: boolean }` to App namespace
- `api/core/config.py` — Added comment block for 3 SvelteKit env vars above model_config
- `.env.example` — Appended ADMIN_TOKEN=, SESSION_SECRET=, ADMIN_USERNAME=, ADMIN_PASSWORD= with comments
- `app/package.json` — Added `@types/node` devDependency

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed @types/node devDependency**
- **Found during:** Task 1 (first npm run check)
- **Issue:** `node:crypto` imports and `Buffer` usage in session.ts produced type errors because `@types/node` was not installed. The svelte-kit generated tsconfig already declared `"types": ["node"]` but the package was absent from node_modules.
- **Fix:** Ran `npm install --save-dev @types/node` — standard stdlib type library, no supply-chain concern.
- **Files modified:** `app/package.json`, `app/package-lock.json`
- **Commit:** `0befe92`

**2. [Rule 3 - Blocking] Added SESSION_SECRET and credentials to app/.env**
- **Found during:** Task 1 (first npm run check)
- **Issue:** `$env/static/private` reads `.env` at type-check time; `SESSION_SECRET` was absent so the type checker reported it as a missing export from the module.
- **Fix:** Appended `SESSION_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_TOKEN` as dev placeholders to `app/.env`. Values are clearly marked as dev-only placeholders that must be replaced before production.
- **Files modified:** `app/.env` (not committed — gitignored)
- **Commit:** Not committed (app/.env is in .gitignore)

**3. [Rule 2 - Missing critical] Added ADMIN_TOKEN to .env.example**
- **Found during:** Task 3
- **Issue:** The plan says "Keep existing ADMIN_TOKEN entry intact" but no ADMIN_TOKEN was in .env.example. Phase 5 added it to config.py but not to .env.example. Added it as an empty placeholder alongside the Phase 6 vars for completeness.
- **Files modified:** `.env.example`
- **Commit:** `6db74f8`

## Decisions Made

- `signSession` and `verifySession` split on `lastIndexOf('.')` not `indexOf('.')` — defensive in case a future payload format includes dots (the signature hex is always at the end)
- `event.locals.session` is assigned unconditionally before the guard check — this allows the Plan 02 login load function to do an already-authenticated redirect (`if (locals.session) throw redirect(302, '/admin')`) without re-reading the cookie

## Threat Model Compliance

| Threat | Status |
|--------|--------|
| T-06-01: Cookie spoofing | Mitigated — HMAC verified via timingSafeEqual |
| T-06-02: /admin +server.ts elevation | Mitigated — hooks.server.ts runs before all handlers |
| T-06-03: Expiry forgery | Mitigated — expiry inside signed payload; tamper fails HMAC |
| T-06-04: timingSafeEqual length throw | Mitigated — explicit length check returns false before call |
| T-06-05: SESSION_SECRET exposure | Mitigated — $env/static/private only; .env.example empty |
| T-06-SC: Supply chain | Accepted — no new packages; @types/node is stdlib types |

## Known Stubs

None — this plan delivers signing/verifying infrastructure with no UI stub content.

## Self-Check: PASSED

- app/src/lib/server/session.ts: FOUND
- app/src/hooks.server.ts: FOUND
- app/src/app.d.ts: FOUND (modified)
- api/core/config.py: FOUND (modified)
- .env.example: FOUND (modified)
- Commit 0befe92 (Task 1): FOUND
- Commit c5fac58 (Task 2): FOUND
- Commit 6db74f8 (Task 3): FOUND

---
*Phase: 06-auth*
*Completed: 2026-06-16*
