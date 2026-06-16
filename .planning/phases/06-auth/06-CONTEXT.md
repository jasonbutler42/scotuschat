# Phase 6: Auth - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 6 delivers the full operator authentication system for the admin area:

1. **Login page** — `/admin/login` with username+password form (dark theme, isolated admin layout)
2. **SvelteKit session cookie** — HMAC-signed, 24h expiry, set in `hooks.server.ts` POST handler
3. **Route guard** — `hooks.server.ts` redirects all unauthenticated `/admin/*` requests to `/admin/login`
4. **Admin layout shell** — `app/src/routes/admin/+layout.svelte` with admin nav (logout button, placeholder links for Pipeline Runner and People Editor)
5. **Admin dashboard stub** — `/admin` renders the dashboard page directly (not `/admin/dashboard`)
6. **Logout** — session cookie deleted; immediate redirect to `/admin/login`

No pipeline runner, no people editor, no public-facing changes. Phase 5's FastAPI admin router stays protected by X-Admin-Token (used for server-to-server calls from SvelteKit).

</domain>

<decisions>
## Implementation Decisions

### Session Cookie

- **D-01:** Session is a **stateless HMAC-signed cookie** using `node:crypto` — no auth library (e.g., Lucia, better-auth), no database-backed session adapter. Already decided in v1.1 accumulated context.
- **D-02:** Session cookie **expires 24 hours** from login time. Fixed expiry (not sliding). `Max-Age=86400` in the Set-Cookie header.
- **D-03:** Cookie security flags at **Claude's discretion** — standard hardened flags appropriate for a production web admin (httpOnly + SameSite + Secure are the expected choices; Claude picks the specific combination).
- **D-04:** **`SESSION_SECRET`** env var is added to `api/core/config.py` (Python side is not used for HMAC; it's a SvelteKit env var — add to `.env` and document in README). The cookie name should be something like `scotus_admin_session`.

### Route Guard

- **D-05:** **`hooks.server.ts`** is the sole auth checkpoint for SvelteKit. It intercepts all `/admin/*` requests, validates the session cookie, and redirects to `/admin/login` if invalid or absent. Layout guards alone are insufficient — `+server.ts` endpoints are not protected by layout `load` functions.
- **D-06:** After successful login, operator is redirected to **`/admin`** (not `/admin/dashboard`). The dashboard page lives at `app/src/routes/admin/+page.svelte`.
- **D-07:** The login page **`/admin/login`** is publicly accessible (no redirect loop). All other `/admin/*` routes require a valid session.

### Admin Area Structure

- **D-08:** Admin routes get an **isolated layout** at `app/src/routes/admin/+layout.svelte`. This layout is completely separate from the public `+layout.svelte` (which shows the 'Cases' nav link). No public nav header on admin pages.
- **D-09:** The admin layout includes: a minimal admin nav bar (app name/logo, logout button) and **placeholder nav links** for Pipeline Runner and People Editor that will become real in Phases 7 and 8. Mark them visually as coming soon / disabled.
- **D-10:** The `hooks.server.ts` guard must NOT redirect the login page itself (avoid infinite redirect loop).

### FastAPI Admin Auth

- **D-11:** Phase 5's `verify_admin_token` dependency **stays in place**. Phase 6 does NOT remove or replace it. When SvelteKit server-side code calls FastAPI `/api/admin/*` endpoints (starting in Phase 7), it passes `ADMIN_TOKEN` as the `X-Admin-Token` header. Two auth layers: SvelteKit hooks validates the session cookie for the operator's browser; X-Admin-Token protects internal server-to-server FastAPI calls. `ADMIN_TOKEN` lives in SvelteKit's server env (`.env`).

### Login UI

- **D-12:** Login page **matches the v1.0 dark theme**: `#0f1117` background, `#334155` border/card, `#94a3b8` label text, `#93c5fd` accent. Centered login card on the dark background. Consistent with the public-facing site — one design language.
- **D-13:** Login form fields: **Username** and **Password** (both text inputs; password type="password"). A single submit button. Invalid credentials show an inline error message (e.g., "Invalid username or password") — same message for both bad username and bad password (no enumeration).
- **D-14:** Login form submits via a **SvelteKit form action** (`+page.server.ts` with `export const actions = { default: ... }`) — not a client-side fetch. Standard SvelteKit progressive enhancement pattern.

### Environment Variables

- **D-15:** Phase 6 introduces **`SESSION_SECRET`** (SvelteKit-side env var used for HMAC signing) and **`ADMIN_USERNAME`** / **`ADMIN_PASSWORD`** (credentials). These are added to `.env.example` / documented. `ADMIN_TOKEN` from Phase 5 stays for FastAPI server-to-server calls.

### Claude's Discretion

- Cookie security flags (httpOnly, SameSite, Secure combination) — standard hardened session cookie config.
- Exact HMAC algorithm and payload structure (e.g., `userId + expiry timestamp`, signed with SESSION_SECRET).
- Cookie name (e.g., `scotus_admin_session`).
- Exact visual styling of the login card and admin nav within the dark theme constraints.
- Error display pattern (inline below form or above submit button).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Architecture & Constraints
- `.planning/PROJECT.md` — Key Decisions table; apolitical framing constraint; pipeline-is-offline constraint; Alembic-is-sole-DDL-authority constraint
- `.planning/REQUIREMENTS.md` — AUTH-01, AUTH-02, AUTH-03 requirements (Phase 6 scope); note on Phase 5 (pure infra); v1.1 phases 7–8 that this phase must not conflict with
- `.planning/ROADMAP.md` §Phase 6 — Success criteria (4 items that must be TRUE)
- `.planning/STATE.md` §Accumulated Context — v1.1 architectural decisions: HMAC session cookie, hooks.server.ts as sole auth checkpoint, fire-and-poll pattern for Phase 7, `BODY_SIZE_LIMIT` / `ORIGIN` env var blockers for deployment

### Phase 5 Foundation (what Phase 6 builds on)
- `.planning/phases/05-admin-foundation/05-CONTEXT.md` — D-09 (FastAPI prefix `/api/admin`), D-11 (health route), D-12 (X-Admin-Token is a throwaway replaced by Phase 6), D-13 (ADMIN_TOKEN env var)
- `api/routers/admin.py` — Current Phase 5 admin router; X-Admin-Token `verify_admin_token` dependency stays in place (D-11); Phase 6 does NOT modify this file
- `api/core/config.py` — Where SESSION_SECRET and ADMIN_USERNAME/ADMIN_PASSWORD env vars are documented (Python side reads ADMIN_TOKEN; SvelteKit side reads SESSION_SECRET + credentials)

### SvelteKit Auth Pattern
- `app/src/routes/+layout.svelte` — Public layout to NOT extend; admin layout must be isolated from this
- `app/src/routes/cases/+page.server.ts` — Nearest server load pattern to follow for `+page.server.ts` structure; form actions differ but load function style is the same

### Database
- No new Alembic migration needed for Phase 6 — session is stateless (cookie-only); no session table

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `api/core/config.py` — `Settings` class (pydantic-settings); `admin_token: str` already there; add documentation reference for `SESSION_SECRET` and credentials in `.env.example`
- `app/src/routes/+layout.svelte` — Layout pattern to mirror structurally for `app/src/routes/admin/+layout.svelte` (children prop, Svelte 5 Runes `$props()`)
- `app/src/routes/cases/+page.server.ts` — Server load function pattern; admin pages follow the same `export const load` structure with `$env/static/private` imports

### Established Patterns
- **Svelte 5 Runes exclusively**: `$props()`, `$state`, `$derived`, `$effect` — no `export let`, no legacy stores, no `$:` blocks
- **SvelteKit error handling**: `throw redirect(302, '/admin/login')` from `@sveltejs/kit` for auth redirects; `throw error(status, message)` for errors
- **Server-only env vars**: `$env/static/private` only — never `PUBLIC_` prefix; `SESSION_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` must be private
- **No auth library**: `node:crypto` only for HMAC — consistent with accumulated context decision

### Integration Points
- `app/src/hooks.server.ts` — New file; the auth checkpoint that every `/admin/*` request passes through
- `app/src/routes/admin/+layout.svelte` — New file; isolated admin layout shell
- `app/src/routes/admin/+page.svelte` — New file; dashboard stub (landing page after login)
- `app/src/routes/admin/login/+page.svelte` — New file; login form
- `app/src/routes/admin/login/+page.server.ts` — New file; form action for credential validation + cookie set
- No FastAPI changes in Phase 6 (D-11)

</code_context>

<specifics>
## Specific Ideas

- The "throwaway" X-Admin-Token framing in Phase 5 means Phase 6 should add a comment in `api/routers/admin.py` (or leave Phase 5's existing comment) clarifying that the dependency stays for internal server-to-server use, not that it's still temporary
- The admin nav should clearly link to future phases (Pipeline Runner, People Editor) as disabled/greyed items so the operator can see the roadmap without getting 404s
- Invalid credentials: single generic error message ("Invalid username or password") — no differentiation between wrong username vs. wrong password

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-auth*
*Context gathered: 2026-06-16*
