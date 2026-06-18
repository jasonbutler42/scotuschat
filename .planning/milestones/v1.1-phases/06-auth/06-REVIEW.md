---
phase: 06-auth
reviewed: 2026-06-16T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - app/src/lib/server/session.ts
  - app/src/hooks.server.ts
  - app/src/app.d.ts
  - api/core/config.py
  - app/package.json
  - app/src/routes/admin/login/+page.server.ts
  - app/src/routes/admin/login/+page.svelte
  - app/src/routes/admin/+page.server.ts
  - app/src/routes/admin/+layout.svelte
  - app/src/routes/admin/+page.svelte
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-06-16T00:00:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

This phase implements a stateless HMAC-signed cookie session system for a single-operator admin area. The overall architecture is sound: the auth guard lives in `hooks.server.ts` (the only checkpoint that covers both page and endpoint routes), credential comparison uses `timingSafeEqual`, and the HMAC verification is correctly structured. However, two critical issues require fixes before this ships: an unguarded crash path on malformed `multipart/form-data` login submissions, and a missing `secure` flag escape hatch that silently breaks auth in local development. Four warnings cover the admin nav bleeding into the login page, missing brute-force protection, always-on `secure: true` breaking dev workflows, and a plain-text credential design note that should be documented as a deliberate constraint.

---

## Critical Issues

### CR-01: `Buffer.from(File)` crash in login action on multipart form submissions

**File:** `app/src/routes/admin/login/+page.server.ts:18-27`

**Issue:** `request.formData()` is called without constraining the request content type. When a client posts `Content-Type: multipart/form-data` and sets a `username` or `password` field to a file upload, `FormData.get('username')` returns a `File` object, not a string. The subsequent `as string` TypeScript cast suppresses the type error at compile time but does not coerce the runtime value. `Buffer.from(File)` then throws a `TypeError: The "string" argument must be of type string or an instance of Buffer or ArrayBuffer. Received an instance of File`, crashing the action handler with an unhandled 500.

An attacker can trivially trigger this to produce a 500 response, leaking stack-trace information if SvelteKit's error page reveals it, or simply DoS the login endpoint.

**Fix:** Reject non-string form values before touching the buffers:

```typescript
export const actions: Actions = {
    default: async ({ request, cookies }) => {
        const data = await request.formData();
        const rawUsername = data.get('username');
        const rawPassword = data.get('password');

        // Reject file uploads or missing fields — formData values can be File objects.
        if (typeof rawUsername !== 'string' || typeof rawPassword !== 'string') {
            return fail(400, { error: 'Invalid request.' });
        }

        const username = rawUsername;
        const password = rawPassword;
        // ... rest of comparison unchanged
    }
};
```

---

### CR-02: `secure: true` cookie flag always set — silently breaks auth in local development, risks future misconfiguration

**File:** `app/src/lib/server/session.ts:11-17`

**Issue:** `sessionCookieOptions` hard-codes `secure: true` unconditionally. In local development over HTTP (`http://localhost`), browsers will not send a `Secure`-flagged cookie back to the server. The login action sets the cookie successfully (no error is thrown), but the browser silently discards it, so the next request arrives with no session cookie and the user is immediately redirected back to `/admin/login`. This makes the entire auth flow untestable without TLS locally.

Additionally, the hard-coded `true` means there is no environment-based escape hatch. If the app is ever deployed behind a reverse proxy that terminates TLS and forwards plain HTTP internally (a common DO App Platform configuration), the `secure` flag may cause identical silent failures in production depending on the proxy configuration.

**Fix:** Derive the flag from the environment:

```typescript
import { SESSION_SECRET } from '$env/static/private';
// Add to $env/static/private in .env.local: SECURE_COOKIE=false for dev
import { env } from '$env/dynamic/private';

export const sessionCookieOptions = {
    httpOnly: true,
    sameSite: 'strict' as const,
    secure: env.SECURE_COOKIE !== 'false',   // default true; set to 'false' in dev
    maxAge: 86400,
    path: '/'
};
```

Alternatively, SvelteKit's `adapter-node` exposes `ORIGIN` — derive it from `process.env.NODE_ENV === 'development'` if a simpler heuristic is acceptable.

---

## Warnings

### WR-01: Admin layout (`+layout.svelte`) wraps the login page — logout nav shown to unauthenticated users

**File:** `app/src/routes/admin/+layout.svelte:44`

**Issue:** SvelteKit layout inheritance means `admin/+layout.svelte` is the parent layout for `admin/login/+page.svelte` as well. There is no `admin/login/+layout.svelte` override and no `(group)` route grouping to isolate the login page. As a result, the login page renders the admin nav bar (including the wordmark, two disabled placeholder spans, and a functional "Log out" POST form targeting `/admin?/logout`). Submitting the logout form while unauthenticated triggers the logout action, which deletes a cookie that doesn't exist and then redirects to `/admin/login` — functionally harmless but visually confusing and structurally wrong.

**Fix (option A — minimal):** Move the login route outside the shared layout by using a SvelteKit route group:

```
app/src/routes/
  admin/
    (authed)/
      +layout.svelte    ← nav bar lives here
      +page.svelte      ← dashboard
      +page.server.ts   ← logout action
    login/
      +page.svelte      ← no nav bar
      +page.server.ts
```

**Fix (option B — simpler short-term):** Accept the current structure but strip the nav bar content from the login page by checking `locals.session` in `+layout.server.ts` and passing it as a prop to conditionally hide the nav.

---

### WR-02: No rate limiting or brute-force protection on the login action

**File:** `app/src/routes/admin/login/+page.server.ts:15-51`

**Issue:** The login form action performs no rate limiting. There is no delay on failure, no account lockout, no CAPTCHA, and no IP-based throttling. The constant-time comparison prevents timing attacks but does nothing to prevent automated credential stuffing or brute-force attempts. The `ADMIN_PASSWORD` is described as a "strong random value" in `config.py`, which mitigates the practical risk, but the endpoint remains an open, unlimited authentication oracle.

For a single-operator tool with a strong random password this is a lower-severity gap, but it is still a gap.

**Fix:** Add a fixed artificial delay on failed login attempts using `setTimeout`/`await` to raise the cost of automation, or integrate a lightweight in-memory rate limiter keyed by IP. SvelteKit's `event.getClientAddress()` is available inside the action.

```typescript
// On auth failure, sleep 1s before returning — raises brute-force cost.
if (!usernameMatch || !passwordMatch) {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    return fail(401, { error: 'Invalid username or password.' });
}
```

---

### WR-03: Plain-text `ADMIN_PASSWORD` stored in env and compared directly — no hashing

**File:** `api/core/config.py:36-38` and `app/src/routes/admin/login/+page.server.ts:27,34`

**Issue:** The `ADMIN_PASSWORD` env var is a plain-text password that is loaded into memory and compared via `timingSafeEqual` without hashing. The `config.py` comment acknowledges this as a deliberate design choice ("no DB-backed hashing") but does not document it as a threat-modeled decision or explain why hashing was rejected (e.g., bcrypt at login time is negligible latency for a single operator). If the `.env` file or environment variable store is ever exfiltrated, the password is immediately usable on any service that reuses it.

This is not a code bug per se, but the absence of a documented rationale for this choice means a future maintainer may not understand the risk they are accepting.

**Fix:** At minimum, document the deliberate constraint with a threat-model note. Ideally, store a bcrypt hash in `ADMIN_PASSWORD_HASH` and compare using `bcrypt.checkpw` / equivalent at login time — the latency cost (~100ms) is irrelevant for an infrequently used admin login.

---

### WR-04: Login form inputs missing `autocomplete` attributes

**File:** `app/src/routes/admin/login/+page.svelte:58-76, 92-109`

**Issue:** The `username` input has no `autocomplete="username"` attribute and the `password` input has no `autocomplete="current-password"`. Without these, browsers may not offer credential manager autofill, and some browsers apply heuristics that can conflict with the form's behavior (e.g., treating the field as a search input). More critically, the absence of `autocomplete="current-password"` may cause some password managers to fail to detect and fill the field, pushing operators toward weaker remembered passwords.

**Fix:**

```svelte
<input
    type="text"
    name="username"
    id="username"
    autocomplete="username"
    required
    autofocus
    ...
/>

<input
    type="password"
    name="password"
    id="password"
    autocomplete="current-password"
    required
    ...
/>
```

---

## Info

### IN-01: `verifySession` — length check before `timingSafeEqual` is correct but comment misleads

**File:** `app/src/lib/server/session.ts:62-63`

**Issue:** The comment says "Reject if lengths differ before calling timingSafeEqual (which throws on mismatch)." This is accurate. However, `expBuf` is always 32 bytes (SHA-256 hex → 64 chars → 32 bytes as `Buffer.from(hex, 'hex')`), while `sigBuf` will be 0-32 bytes depending on the attacker-supplied hex string. The length check thus leaks one bit of information: an attacker can distinguish "signature is 64 hex chars but wrong" (passes length check, fails `timingSafeEqual`) from "signature is wrong length" (fails length check). This is not a practical oracle attack given the HMAC key is secret, but the comment should note that the length check itself is not timing-sensitive — it is equivalent to a `!==` on fixed-domain values.

**Fix:** No code change required. Optionally amend the comment to clarify that the 32-byte expected length is a fixed constant (not secret), making the length check non-sensitive.

---

### IN-02: `admin/+page.server.ts` — unused `redirect` import

**File:** `app/src/routes/admin/+page.server.ts:1`

**Issue:** `redirect` is imported from `@sveltejs/kit` at line 1 and is used at line 15 (`throw redirect(302, '/admin/login')`). On re-reading, this is actually used — no issue. Disregard.

*(Self-correction: import is used. Finding withdrawn.)*

---

### IN-02: `app.d.ts` — `session: boolean` is a weak locals type

**File:** `app/src/app.d.ts:7`

**Issue:** `locals.session` is typed as `boolean`. This works for the current single-flag use case but provides no room to attach session metadata (expiry time, operator identity, etc.) without a breaking change to the interface. If Phase 7 needs to read the session expiry in a load function for "session expires in X minutes" UX, the type will need to change, requiring updates across all files that read `locals.session`.

**Fix:** Define a typed session object now while the codebase is small:

```typescript
interface Locals {
    session: { authenticated: boolean; expiresAt?: number } | null;
}
```

Or keep it minimal but use a distinct type alias that can be widened:

```typescript
type AdminSession = boolean;
interface Locals {
    session: AdminSession;
}
```

The boolean approach is not wrong — it is just inflexible. Flag for team awareness.

---

### IN-03: `sessionCookieOptions.maxAge` and `signSession` expiry are separately hardcoded — can drift

**File:** `app/src/lib/server/session.ts:15` and `app/src/routes/admin/login/+page.server.ts:44`

**Issue:** The cookie's `maxAge` is set to `86400` (24 hours) in `sessionCookieOptions`, and the HMAC-signed expiry timestamp is independently computed as `Date.now() + 86400_000` in the login action. These two durations are independently hardcoded. If a future change updates one but forgets the other, the cookie will either outlive its valid HMAC signature (cookie is present but `verifySession` returns false — invisible auth failure) or the HMAC signature will outlive the cookie (harmless, but wasteful).

**Fix:** Export a single `SESSION_DURATION_MS` constant from `session.ts` and derive both values from it:

```typescript
// session.ts
export const SESSION_DURATION_MS = 86_400_000; // 24 hours

export const sessionCookieOptions = {
    ...
    maxAge: SESSION_DURATION_MS / 1000,
    ...
};

// login/+page.server.ts
import { SESSION_DURATION_MS, signSession, ... } from '$lib/server/session';
const expiry = Date.now() + SESSION_DURATION_MS;
```

---

_Reviewed: 2026-06-16T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
