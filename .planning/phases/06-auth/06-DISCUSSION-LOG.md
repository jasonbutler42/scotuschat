# Phase 6: Auth - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-16
**Phase:** 06-auth
**Areas discussed:** Post-login dashboard, Session lifetime, FastAPI admin auth replacement, Login page styling

---

## Post-login dashboard

| Option | Description | Selected |
|--------|-------------|----------|
| Placeholder stub | Simple 'Admin Dashboard' page with headline and two disabled nav links (Pipeline Runner, People Editor) | ✓ |
| Blank page with logout link | Absolute minimum — just heading and logout button, no nav structure | |
| Redirect to first available feature | Login redirects to pipeline runner page (Phase 7 work) | |

**Follow-up:** Should Phase 6 build the admin layout shell now or defer?

| Option | Description | Selected |
|--------|-------------|----------|
| Build layout shell now | `app/src/routes/admin/+layout.svelte` with sidebar/top nav; Phases 7 and 8 slot under it | ✓ |
| Standalone page, layout deferred | Bare dashboard page, Phase 7/8 refactors nav when needed | |

**Follow-up:** Where does the operator land after login?

| Option | Description | Selected |
|--------|-------------|----------|
| /admin is the dashboard | GET /admin renders dashboard directly. `+page.svelte` at `app/src/routes/admin/+page.svelte`. | ✓ |
| /admin/dashboard is the landing page | Login redirects to /admin/dashboard explicitly | |

**Notes:** All three sub-questions resolved quickly with recommended defaults. Admin scaffold established in Phase 6 so Phases 7 and 8 don't need to refactor routing.

---

## Session lifetime

| Option | Description | Selected |
|--------|-------------|----------|
| 24 hours from login | Fixed 24h expiry. Cookie Max-Age=86400, no sliding renewal. | ✓ |
| Until explicit logout only | Session cookie with no Max-Age. Survives until browser clear or logout. | |
| 7 days, sliding | 7-day window that refreshes on each request. Adds hook overhead. | |

**Follow-up:** Cookie security flags?

| Option | Description | Selected |
|--------|-------------|----------|
| httpOnly + SameSite=Strict + Secure | Standard hardened session cookie configuration | |
| httpOnly + SameSite=Lax + Secure | Slightly looser; framework default in most libraries | |
| You decide | Leave cookie flags to Claude's discretion | ✓ |

**Notes:** 24h is a practical daily-use session length. Cookie flags deferred to Claude's discretion.

---

## FastAPI admin auth replacement

| Option | Description | Selected |
|--------|-------------|----------|
| Keep X-Admin-Token for server-to-server | SvelteKit hooks validate session cookie for browser. SvelteKit passes ADMIN_TOKEN as X-Admin-Token to FastAPI for internal calls. Two auth layers. | ✓ |
| Remove FastAPI auth entirely | Only SvelteKit hooks protects admin. FastAPI trusts all internal callers. | |
| Forward session cookie to FastAPI | SvelteKit passes HMAC token as Bearer; FastAPI validates independently (needs SESSION_SECRET too). | |

**Notes:** Phase 5's `verify_admin_token` stays in place. Phase 6 adds SvelteKit-side auth without touching FastAPI. Simplest path; the "throwaway" label in Phase 5 was about it being insufficient as the *only* guard (browser-side), not that it needs removal.

---

## Login page styling

| Option | Description | Selected |
|--------|-------------|----------|
| Match v1.0 dark theme | Same dark background/palette. Centered login card. One design language. | ✓ |
| Neutral/light admin look | White card on light grey. Distinct from public UI. Requires second palette. | |

**Follow-up:** Shared public layout or isolated admin layout?

| Option | Description | Selected |
|--------|-------------|----------|
| Isolated admin layout | Own `+layout.svelte` under `/admin/`. No 'Cases' link on admin pages. Admin nav only. | ✓ |
| Extend public layout | Admin renders under existing `+layout.svelte`. Public nav visible on admin pages. | |

**Notes:** Consistent dark theme, isolated layout. Clean separation of public and operator contexts.

---

## Claude's Discretion

- Cookie security flags (httpOnly, SameSite, Secure combination) — standard hardened session cookie
- Exact HMAC algorithm and cookie payload structure
- Cookie name (e.g., `scotus_admin_session`)
- Exact visual styling of login card and admin nav within dark theme constraints
- Error display pattern for invalid credentials (inline position)

## Deferred Ideas

None — discussion stayed within Phase 6 scope.
