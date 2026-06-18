# Phase 6: Auth - Pattern Map

**Mapped:** 2026-06-16
**Files analyzed:** 6 new files
**Analogs found:** 5 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/src/hooks.server.ts` | middleware | request-response | `app/src/routes/cases/[slug]/+page.server.ts` (redirect pattern) | partial (role differs, redirect/guard data flow matches) |
| `app/src/routes/admin/+layout.svelte` | component | request-response | `app/src/routes/+layout.svelte` | exact (layout + children render) |
| `app/src/routes/admin/+page.svelte` | component | request-response | `app/src/routes/cases/+page.svelte` | role-match |
| `app/src/routes/admin/login/+page.svelte` | component | request-response | `app/src/routes/cases/+page.svelte` | role-match (dark theme, inline styles) |
| `app/src/routes/admin/login/+page.server.ts` | controller | request-response | `app/src/routes/cases/[slug]/+page.server.ts` | role-match (server-side, redirect, error patterns) |
| `api/core/config.py` (modify) | config | — | `api/core/config.py` itself | exact (additive only) |

---

## Pattern Assignments

### `app/src/hooks.server.ts` (middleware, request-response)

**Analog:** `app/src/routes/cases/[slug]/+page.server.ts` (redirect usage)

No existing `hooks.server.ts` exists — this is the first file of its kind. Use the SvelteKit `Handle` type and the `redirect` helper from `@sveltejs/kit`. The redirect pattern is already used in the analog.

**Imports pattern** — follow the established server-file import style:
```typescript
// From app/src/routes/cases/[slug]/+page.server.ts lines 1-3
import { redirect } from '@sveltejs/kit';
// Add for hooks:
import type { Handle } from '@sveltejs/kit';
import { ADMIN_USERNAME, ADMIN_PASSWORD, SESSION_SECRET } from '$env/static/private';
import { createHmac, timingSafeEqual } from 'node:crypto';
```

**Guard skeleton** — SvelteKit hooks pattern (no codebase analog; follows SvelteKit docs):
```typescript
export const handle: Handle = async ({ event, resolve }) => {
  const path = event.url.pathname;

  // D-07: /admin/login is publicly accessible — never redirect it
  if (path.startsWith('/admin') && !path.startsWith('/admin/login')) {
    const sessionCookie = event.cookies.get('scotus_admin_session');
    if (!isValidSession(sessionCookie)) {
      throw redirect(302, '/admin/login');
    }
  }

  return resolve(event);
};
```

**Redirect pattern** (from `app/src/routes/cases/[slug]/+page.server.ts` line 13):
```typescript
throw redirect(307, `/cases/${params.slug}/arguments/${matches[0].argument_id}`);
// Auth redirect uses 302 (temporary) per standard login redirect convention
throw redirect(302, '/admin/login');
```

**Error handling** — no uncaught errors from the guard itself; invalid session results in redirect, not throw error.

---

### `app/src/routes/admin/+layout.svelte` (component, request-response)

**Analog:** `app/src/routes/+layout.svelte`

**Full analog** (`app/src/routes/+layout.svelte` lines 1-34):
```svelte
<script lang="ts">
  import '../app.css';
  let { children } = $props();
</script>

<header>
  <nav aria-label="Site navigation" style="
    background-color: #0f1117;
    border-bottom: 1px solid #334155;
    padding: 12px 24px;
    display: flex;
    align-items: center;
    gap: 16px;
  ">
    <span style="font-size: 14px; font-weight: 600; color: #94a3b8; letter-spacing: 0.05em;">
      SCOTUS CHAT
    </span>
    <a href="/cases" style="font-size: 13px; color: #93c5fd; text-decoration: none;">
      Cases
    </a>
  </nav>
</header>

{@render children()}
```

**Copy exactly, then adapt for admin:**
- Keep `$props()` / `{@render children()}` pattern (Svelte 5 Runes — D-08)
- Replace public nav links with admin nav: logout button + disabled placeholder links (Pipeline Runner, People Editor) per D-09
- Import path for `app.css`: admin layout is one level deeper than public layout — use `'../../app.css'`
- D-08: admin layout is isolated — do NOT import or extend the public `+layout.svelte`
- Logout button submits to the logout form action (a `<form method="POST" action="/admin/login?/logout">`)
- Disabled nav items: render as `<span>` (not `<a>`) styled with `color: #475569; cursor: not-allowed` to signal "coming soon"

**Dark theme tokens** (from `app/src/routes/cases/+page.svelte`):
```
background:   #0f1117
card/nav bg:  #1e293b
border:       #334155
heading text: #e2e8f0
label/muted:  #94a3b8
accent/link:  #93c5fd
```

---

### `app/src/routes/admin/+page.svelte` (component, request-response)

**Analog:** `app/src/routes/cases/+page.svelte`

**Props pattern** (line 2):
```svelte
<script lang="ts">
  let { data } = $props();
</script>
```

**Page shell pattern** (lines 23-44 of `app/src/routes/cases/+page.svelte`):
```svelte
<main style="background-color: #0f1117; min-height: 100vh;">
  <header style="
    background-color: #1e293b;
    border-bottom: 1px solid #334155;
    padding: 16px 24px;
  ">
    <h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0; line-height: 1.2;">
      Admin Dashboard
    </h1>
  </header>
  <div style="max-width: 860px; margin: 0 auto; padding: 48px 24px;">
    <!-- stub content -->
  </div>
</main>
```

**Note:** This page is a stub — Phase 6 only needs it to confirm the guard redirects to `/admin` post-login. Minimal content is correct.

---

### `app/src/routes/admin/login/+page.svelte` (component, request-response)

**Analog:** `app/src/routes/cases/+page.svelte` (dark theme, inline styles, `$props()`)

**Props + form action data pattern** — SvelteKit form actions expose `form` alongside `data`:
```svelte
<script lang="ts">
  let { form } = $props();
  // `form` is the ActionData returned from the form action on POST
  // On GET (initial load) form is null/undefined
</script>
```

**Dark theme card centered on full-height background** (adapt from `cases/+page.svelte` layout):
```svelte
<main style="background-color: #0f1117; min-height: 100vh; display: flex; align-items: center; justify-content: center;">
  <div style="
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 32px;
    width: 100%;
    max-width: 360px;
  ">
    <!-- heading, form fields, error, submit -->
  </div>
</main>
```

**Form submission pattern** — SvelteKit progressive enhancement (D-14):
```svelte
<form method="POST">
  <label style="color: #94a3b8; font-size: 13px; display: block; margin-bottom: 4px;">
    Username
  </label>
  <input type="text" name="username" ... />

  <label style="color: #94a3b8; font-size: 13px; display: block; margin-bottom: 4px;">
    Password
  </label>
  <input type="password" name="password" ... />

  {#if form?.error}
    <p style="color: #f87171; font-size: 13px; margin: 8px 0 0 0;">{form.error}</p>
  {/if}

  <button type="submit" ...>Sign in</button>
</form>
```

**Error display pattern** (D-13): inline below the inputs, above submit, single message `"Invalid username or password"`. Use `#f87171` (red-400) for error text color, consistent with the dark palette.

---

### `app/src/routes/admin/login/+page.server.ts` (controller, request-response)

**Analog:** `app/src/routes/cases/[slug]/+page.server.ts`

**Imports pattern** — extends the existing server file pattern with form action imports (lines 1-3 of analog):
```typescript
import { ADMIN_USERNAME, ADMIN_PASSWORD, SESSION_SECRET } from '$env/static/private';
import { redirect, fail } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { createHmac } from 'node:crypto';
```

**Load function pattern** (analog lines 5-9 — minimal load for the login page):
```typescript
export const load: PageServerLoad = async ({ locals }) => {
  // If already authenticated, redirect to admin dashboard
  // locals.session is set by hooks.server.ts
  if (locals.session) {
    throw redirect(302, '/admin');
  }
  return {};
};
```

**Form action pattern** — no existing codebase analog; follows SvelteKit `Actions` convention:
```typescript
export const actions: Actions = {
  default: async ({ request, cookies }) => {
    const data = await request.formData();
    const username = data.get('username') as string;
    const password = data.get('password') as string;

    // Constant-time comparison — no timing oracle (T-05-01)
    const usernameMatch = timingSafeEqual(
      Buffer.from(username ?? ''),
      Buffer.from(ADMIN_USERNAME)
    );
    const passwordMatch = timingSafeEqual(
      Buffer.from(password ?? ''),
      Buffer.from(ADMIN_PASSWORD)
    );

    if (!usernameMatch || !passwordMatch) {
      // D-13: same message for both bad username and bad password
      return fail(401, { error: 'Invalid username or password' });
    }

    // Build HMAC-signed session payload
    const expiry = Date.now() + 86400_000; // 24h — D-02
    const payload = `${expiry}`;
    const sig = createHmac('sha256', SESSION_SECRET).update(payload).digest('hex');
    const cookieValue = `${payload}.${sig}`;

    cookies.set('scotus_admin_session', cookieValue, {
      httpOnly: true,       // D-03
      sameSite: 'strict',   // D-03
      secure: true,         // D-03 (DO App Platform serves HTTPS)
      maxAge: 86400,        // D-02: 86400 seconds = 24h
      path: '/',
    });

    throw redirect(302, '/admin'); // D-06
  },

  logout: async ({ cookies }) => {
    cookies.delete('scotus_admin_session', { path: '/' });
    throw redirect(302, '/admin/login');
  },
};
```

**Error handling pattern** — use `fail()` (not `throw error()`) for form validation failures; `throw redirect()` for success navigation. Both patterns are from `@sveltejs/kit` (consistent with existing server files).

**`fail()` vs `throw error()`** — `fail` returns `ActionData` back to the page component as `form` prop; `error` renders the error page. Use `fail` for expected credential errors.

---

### `api/core/config.py` (modify — additive documentation only)

**Analog:** `api/core/config.py` itself (lines 1-33)

**Current pattern to preserve** (lines 11-30):
```python
class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str = ""
    debug: bool = False
    admin_token: str  # Required — no default; app refuses to start without this

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
```

**Additive change** — add documentation comment only (Python does not read these vars; SvelteKit reads them directly from `.env`):
```python
    # Phase 6 note: SESSION_SECRET, ADMIN_USERNAME, ADMIN_PASSWORD are
    # SvelteKit-side env vars ($env/static/private). They are NOT read by
    # the Python API. Document them here and in .env.example so operators
    # know all required env vars in one place.
    # SESSION_SECRET — HMAC key for scotus_admin_session cookie (min 32 chars)
    # ADMIN_USERNAME — operator login username
    # ADMIN_PASSWORD — operator login password
```

No new Python fields needed. No functional change to `Settings`.

---

## Shared Patterns

### Dark Theme Color Tokens
**Source:** `app/src/routes/cases/+page.svelte` (throughout) and `app/src/routes/+layout.svelte`
**Apply to:** `admin/+layout.svelte`, `admin/+page.svelte`, `admin/login/+page.svelte`
```
Page background:   #0f1117
Nav/card bg:       #1e293b
Border color:      #334155
Primary text:      #e2e8f0
Muted/label text:  #94a3b8
Accent/link:       #93c5fd
Error text:        #f87171  (red-400, consistent with existing error states)
```

### Svelte 5 Runes Props
**Source:** `app/src/routes/+layout.svelte` line 3, `app/src/routes/cases/+page.svelte` line 2
**Apply to:** All new `.svelte` files
```svelte
let { children } = $props();   // layout files
let { data } = $props();       // page files with load function data
let { form } = $props();       // page files with form action data
// NEVER use: export let, $:, legacy stores
```

### Children Render
**Source:** `app/src/routes/+layout.svelte` line 34
**Apply to:** `admin/+layout.svelte`
```svelte
{@render children()}
```

### Private Env Imports
**Source:** `app/src/routes/cases/+page.server.ts` line 1, `app/src/routes/cases/[slug]/+page.server.ts` line 1
**Apply to:** All new `*.server.ts` files
```typescript
import { SOME_VAR } from '$env/static/private';
// NEVER use PUBLIC_ prefix for SESSION_SECRET, ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_TOKEN
```

### Redirect and Error from @sveltejs/kit
**Source:** `app/src/routes/cases/[slug]/+page.server.ts` lines 2, 12-13
**Apply to:** `hooks.server.ts`, `admin/login/+page.server.ts`
```typescript
import { error, redirect } from '@sveltejs/kit';
throw redirect(302, '/admin/login');   // 302 for auth redirects
throw error(res.status, 'message');    // only for unexpected server errors
```

### Inline Style Convention
**Source:** All existing `.svelte` files
**Apply to:** All new `.svelte` files
- All styling is inline `style="..."` — no external CSS classes, no Tailwind, no CSS modules
- Multi-line inline styles use template literal indentation as shown in analog files

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `app/src/hooks.server.ts` | middleware | request-response | No hooks file exists in the codebase; SvelteKit-specific pattern with no prior project analog |

The `handle` export signature and `Handle` type are SvelteKit conventions — reference the SvelteKit docs pattern, not a codebase analog. The redirect and cookie-read patterns are drawn from the partial analogs noted above.

---

## Metadata

**Analog search scope:** `app/src/routes/**`, `api/routers/`, `api/core/`
**Files scanned:** 8
**Pattern extraction date:** 2026-06-16
