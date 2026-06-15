# Architecture Research

**Domain:** Protected admin interface + pipeline job coordination on existing SvelteKit + FastAPI app
**Researched:** 2026-06-15
**Confidence:** HIGH

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Browser                                       │
│  ┌──────────────────────┐    ┌───────────────────────────────────┐   │
│  │  Public routes        │    │  Admin routes (/admin/*)          │   │
│  │  /cases, /arguments   │    │  /admin/login, /admin/run, etc.   │   │
│  └──────────┬───────────┘    └──────────────┬────────────────────┘   │
└─────────────┼──────────────────────────────┼────────────────────────┘
              │                              │
┌─────────────┼──────────────────────────────┼────────────────────────┐
│                  SvelteKit app (adapter-node)                         │
│                                                                       │
│  src/hooks.server.ts  ←─ ALL requests pass through here              │
│    reads admin_session cookie, validates HMAC                         │
│    if /admin/* (not /admin/login) and not authenticated:              │
│      → redirect(302, '/admin/login')                                  │
│    populates event.locals.admin = true | false                        │
│                                                                       │
│  ┌───────────────────────┐   ┌───────────────────────────────────┐   │
│  │  Public +page.server  │   │  Admin +page.server.ts            │   │
│  │  FASTAPI_BASE_URL      │   │  form actions + load via          │   │
│  │  (server-only env var) │   │  FASTAPI_ADMIN_URL (server-only)  │   │
│  └──────────┬────────────┘   └──────────────┬────────────────────┘   │
│             │                               │                         │
│             │               admin form actions:                       │
│             │               - startRun: spawn Python subprocess       │
│             │               - write admin_jobs row via FastAPI        │
│             │               - return { job_id } immediately           │
│             │               - client polls /admin/api/run/[id]        │
└─────────────┼───────────────┼─────────────────────────────────────────┘
              │               │
              ↓               ↓
┌─────────────────────────────────────────────────────────────────────┐
│  FastAPI (read-only public + write-capable admin router)             │
│  GET /cases, /arguments/*/utterances, /people/* (existing)          │
│  GET/POST/PATCH /admin/jobs, /admin/people (new, X-Admin-Token auth) │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  PostgreSQL 16 (Digital Ocean Managed, PgBouncer Transaction mode)   │
│  Existing: pipeline_runs, utterances, people, cases, arguments, ... │
│  New: admin_jobs (pipeline job coordination table)                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `src/hooks.server.ts` | Single auth checkpoint for all requests; populates `event.locals.admin` | SvelteKit `handle` hook — runs before every server request |
| `src/routes/admin/login/+page.server.ts` | Validate env-var credentials, set signed session cookie, redirect | Form action with HMAC-signed cookie; no DB write |
| `src/routes/admin/+layout.server.ts` | Belt-and-suspenders redirect if not authenticated | `load` checks `locals.admin`, throws `redirect(302, '/admin/login')` |
| `src/routes/admin/run/+page.server.ts` | Start pipeline run (form action), render current run status | Named actions: `startRun`, `approveContinue`; load reads job state via FastAPI admin router |
| `src/routes/admin/api/run/[id]/+server.ts` | JSON polling endpoint returning current job status | `GET` handler — called by client `setInterval` every 2.5s |
| `api/routers/admin.py` | Read/write pipeline_runs, admin_jobs, people for admin UI | New FastAPI router; protected by `X-Admin-Token` header |
| `pipeline/__main__.py` | Python subprocess entry point — unchanged CLI | Spawned by SvelteKit Node.js via `child_process.spawn`; no changes required |
| `alembic/versions/0003_add_admin_jobs.py` | New `admin_jobs` coordination table | Alembic is the sole DDL authority — no `Base.metadata.create_all` |

---

## Recommended Project Structure

New files only — existing public routes and API unchanged.

```
app/src/
├── hooks.server.ts                  ← NEW: auth guard for all requests
├── app.d.ts                         ← MODIFIED: add App.Locals.admin: boolean
├── lib/
│   └── components/
│       ├── AdminNav.svelte           ← NEW: admin sidebar navigation
│       └── PipelineStatus.svelte    ← NEW: step progress display (ingest/parse/resolve)
└── routes/
    ├── +layout.svelte               ← UNCHANGED (public layout)
    ├── cases/...                    ← UNCHANGED
    └── admin/
        ├── +layout.svelte           ← NEW: admin shell (nav + content slot)
        ├── +layout.server.ts        ← NEW: belt-and-suspenders redirect guard
        ├── login/
        │   ├── +page.svelte         ← NEW: login form (username + password)
        │   └── +page.server.ts      ← NEW: validate credentials, set cookie, redirect
        ├── logout/
        │   └── +page.server.ts      ← NEW: clear cookie, redirect to /admin/login
        ├── run/
        │   ├── +page.svelte         ← NEW: pipeline runner UI
        │   └── +page.server.ts      ← NEW: startRun / approveContinue + load
        ├── people/
        │   ├── +page.svelte         ← NEW: people directory list
        │   ├── +page.server.ts      ← NEW: load people list + create person action
        │   └── [id]/
        │       ├── +page.svelte     ← NEW: person edit form
        │       └── +page.server.ts  ← NEW: load person + update action
        └── api/
            └── run/
                └── [id]/
                    └── +server.ts   ← NEW: JSON polling endpoint for job status

api/
├── main.py                          ← MODIFIED: include admin_router
├── routers/
│   └── admin.py                     ← NEW: admin reads/writes (jobs, people)
├── schemas/
│   └── admin.py                     ← NEW: AdminJobSchema, AdminPersonSchema
└── core/
    └── config.py                    ← MODIFIED: add admin_api_token field

alembic/versions/
└── 0003_add_admin_jobs.py           ← NEW: admin_jobs table
```

### Structure Rationale

- **`admin/+layout.server.ts`:** Any new page added under `admin/` is automatically protected without needing a guard in every `+page.server.ts`. Belt-and-suspenders on top of `hooks.server.ts`.
- **`admin/api/run/[id]/+server.ts`:** SvelteKit `+server.ts` returns JSON — this is the polling target. It reads from FastAPI, keeping all DB access behind the same FastAPI boundary as the rest of the app. Named `admin/api/` to distinguish internal endpoints from public API routes.
- **FastAPI `admin.py` router:** Admin data reads and writes go through FastAPI, consistent with the v1.0 pattern (SvelteKit server → FastAPI → DB). FastAPI remains the only app-layer DB writer.

---

## Architectural Patterns

### Pattern 1: HMAC-Signed Stateless Session Cookie

**What:** Generate a random UUID on login, sign it with a `SESSION_SECRET` env var using HMAC-SHA256, store `token.signature` as an HttpOnly cookie. On each request, recompute the HMAC and compare. No session store or Redis needed.

**When to use:** Single-operator apps where you only need to answer "is this person authenticated" — not "which user is this." Avoids a Redis/DB session store dependency.

**Trade-offs:** Simple and stateless. Cannot revoke a specific session without rotating `SESSION_SECRET` (which invalidates all sessions). Acceptable for single-operator use. If rotation is needed, update the env var in DO App Platform and redeploy.

**Example:**
```typescript
// src/routes/admin/login/+page.server.ts
import { createHmac, randomUUID } from 'crypto';
import { redirect, fail } from '@sveltejs/kit';
import { ADMIN_USER, ADMIN_PASS, SESSION_SECRET } from '$env/static/private';

export const actions = {
  default: async ({ request, cookies }) => {
    const data = await request.formData();
    const username = data.get('username') as string;
    const password = data.get('password') as string;

    if (username !== ADMIN_USER || password !== ADMIN_PASS) {
      return fail(401, { invalid: true });
    }

    const token = randomUUID();
    const sig = createHmac('sha256', SESSION_SECRET).update(token).digest('hex');
    cookies.set('admin_session', `${token}.${sig}`, {
      path: '/',
      httpOnly: true,
      sameSite: 'lax',
      secure: true,
      maxAge: 60 * 60 * 8   // 8-hour sessions
    });
    redirect(302, '/admin');
  }
};
```

### Pattern 2: Centralized Route Guard in hooks.server.ts

**What:** The `handle` hook intercepts every request, reads the session cookie, validates the HMAC, and sets `event.locals.admin`. Admin routes test `locals.admin`; unauthenticated requests are redirected to `/admin/login`.

**When to use:** Always — this is the correct SvelteKit pattern for server-side route protection. Client-side navigation guards (`goto()` in `+layout.svelte`) are insufficient: they flash protected content, don't protect load functions, and are bypassable.

**Trade-offs:** One place to change auth logic. The `sequence` helper from `@sveltejs/kit/hooks` composes multiple handle functions if needed later (e.g., adding rate-limiting, CSRF).

**Example:**
```typescript
// src/hooks.server.ts
import type { Handle } from '@sveltejs/kit';
import { createHmac } from 'crypto';
import { SESSION_SECRET } from '$env/static/private';
import { redirect } from '@sveltejs/kit';

export const handle: Handle = async ({ event, resolve }) => {
  // Validate session cookie
  const session = event.cookies.get('admin_session');
  if (session) {
    const dotIndex = session.lastIndexOf('.');
    const token = session.slice(0, dotIndex);
    const sig = session.slice(dotIndex + 1);
    const expected = createHmac('sha256', SESSION_SECRET).update(token).digest('hex');
    if (sig === expected) {
      event.locals.admin = true;
    }
  }

  // Guard /admin/* (exempt: /admin/login itself)
  if (
    event.url.pathname.startsWith('/admin') &&
    !event.url.pathname.startsWith('/admin/login') &&
    !event.locals.admin
  ) {
    redirect(302, '/admin/login');
  }

  return resolve(event);
};
```

**Required `app.d.ts` change:**
```typescript
declare global {
  namespace App {
    interface Locals {
      admin: boolean;
    }
  }
}
export {};
```

### Pattern 3: Fire-and-Poll Pipeline Coordination

**What:** A SvelteKit form action spawns the Python pipeline subprocess via Node.js `child_process.spawn`, then immediately returns `{ job_id }` to the client. The subprocess runs independently; `proc.on('exit')` fires a status update to FastAPI when done. The client polls a SvelteKit JSON endpoint (`/admin/api/run/[id]`) every 2.5 seconds until the job reaches a terminal state.

**When to use:** Long-running processes where HTTP request timeouts make waiting infeasible. The parse step takes 30–120 seconds for a full transcript.

**Trade-offs:** Polling adds minor DB read load (acceptable for single-operator use). SSE would push updates immediately but adds a library (`sveltekit-sse`) and connection management overhead. BullMQ/Redis is overkill for a single-operator tool with no concurrency requirements. Fire-and-poll with a 2.5s interval is the right tradeoff here.

**Action side (form action in +page.server.ts):**
```typescript
import { spawn } from 'child_process';
import { FASTAPI_ADMIN_URL, ADMIN_API_TOKEN } from '$env/static/private';

export const actions = {
  startRun: async ({ request, fetch }) => {
    const data = await request.formData();
    const pdfUrl = data.get('pdf_url') as string;
    // ... collect other ingest params

    // 1. Create admin_jobs record via FastAPI
    const jobRes = await fetch(`${FASTAPI_ADMIN_URL}/admin/jobs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Token': ADMIN_API_TOKEN },
      body: JSON.stringify({ pdf_url: pdfUrl, step: 'ingest', status: 'running' })
    });
    const { job_id } = await jobRes.json();

    // 2. Spawn Python subprocess — non-blocking
    const proc = spawn('python', ['-m', 'pipeline', 'ingest', '--url', pdfUrl /*, ...args */], {
      detached: false,
      stdio: 'pipe',
      env: { ...process.env }
    });

    // 3. Update job status on exit (fire-and-forget fetch)
    proc.on('exit', (code) => {
      fetch(`${FASTAPI_ADMIN_URL}/admin/jobs/${job_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'X-Admin-Token': ADMIN_API_TOKEN },
        body: JSON.stringify({ status: code === 0 ? 'completed' : 'failed' })
      }).catch(() => { /* log but don't crash */ });
    });

    // 4. Return job_id immediately — action does not await subprocess
    return { job_id };
  }
};
```

**Polling endpoint:**
```typescript
// src/routes/admin/api/run/[id]/+server.ts
import { json, error } from '@sveltejs/kit';
import { FASTAPI_ADMIN_URL, ADMIN_API_TOKEN } from '$env/static/private';

export async function GET({ params, locals }) {
  if (!locals.admin) throw error(401, 'Unauthorized');
  const res = await fetch(`${FASTAPI_ADMIN_URL}/admin/jobs/${params.id}`, {
    headers: { 'X-Admin-Token': ADMIN_API_TOKEN }
  });
  if (!res.ok) throw error(res.status, 'Job not found');
  return json(await res.json());
}
```

**Svelte 5 client polling (Runes — no legacy stores):**
```svelte
<script lang="ts">
  let { form } = $props();
  let jobStatus = $state<string | null>(null);

  $effect(() => {
    if (!form?.job_id) return;
    const id = setInterval(async () => {
      const res = await fetch(`/admin/api/run/${form.job_id}`);
      const data = await res.json();
      jobStatus = data.status;
      if (data.status === 'completed' || data.status === 'failed' || data.status === 'awaiting_review') {
        clearInterval(id);
      }
    }, 2500);
    return () => clearInterval(id);
  });
</script>
```

### Pattern 4: FastAPI Admin Router with Internal Token Auth

**What:** A new FastAPI router at `api/routers/admin.py` handles admin reads and writes (job CRUD, people CRUD, run history). Protected by an `X-Admin-Token` header — a shared secret known only to the SvelteKit server process, never transmitted to the browser.

**When to use:** Maintains the v1.0 pattern (SvelteKit server → FastAPI → DB). FastAPI remains the only app-layer DB writer. The browser never touches FastAPI directly — all calls go through SvelteKit `+page.server.ts` or `+server.ts` load/action functions.

**Trade-offs:** Adds one env var (`ADMIN_API_TOKEN`) to manage on both SvelteKit and FastAPI. Alternative (SvelteKit writes to DB via SQLAlchemy directly) would create two separate DB writer processes with separate connection pools — a violation of the v1.0 architectural pattern.

**Example:**
```python
# api/routers/admin.py
from fastapi import APIRouter, Depends, Header, HTTPException, status
from api.core.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])

async def verify_admin_token(x_admin_token: str = Header(...)):
    if x_admin_token != settings.admin_api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

@router.get("/jobs/{job_id}", dependencies=[Depends(verify_admin_token)])
async def get_job(job_id: int, session: AsyncSession = Depends(get_session)):
    # ...returns AdminJobSchema
    pass
```

---

## Data Flow

### Authentication Flow

```
Browser POST /admin/login (username + password)
    ↓
hooks.server.ts — login route is exempt from guard, passes through
    ↓
/admin/login/+page.server.ts action
    compares against ADMIN_USER, ADMIN_PASS env vars
    on match: generate UUID, compute HMAC-SHA256 with SESSION_SECRET
    set HttpOnly cookie: admin_session = token.sig
    redirect(302, '/admin')
    ↓
Browser GET /admin (following redirect)
    ↓
hooks.server.ts
    reads admin_session cookie
    splits token.sig, recomputes HMAC, compares
    match → event.locals.admin = true
    ↓
/admin/+layout.server.ts load
    locals.admin = true → render admin layout (no redirect)
```

### Pipeline Job Execution Flow

```
Operator fills PDF URL form → submits
    ↓
SvelteKit form action: startRun
    POST to FastAPI /admin/jobs → { job_id }   (creates queued record)
    spawn('python', ['-m', 'pipeline', 'ingest', ...])  ← non-blocking
    proc.on('exit') attached (updates job status on completion)
    return { job_id }
    ↓
Load function re-runs (SvelteKit auto-invalidation after action)
form.job_id is set → client $effect starts polling
    ↓
Client polls /admin/api/run/[job_id] every 2.5s
    ↓
Python subprocess runs independently
    writes to pipeline_runs (existing behaviour, unchanged)
    exits 0 on success
    ↓
proc.on('exit') fires
    PATCH FastAPI /admin/jobs/[id] → { status: 'completed', pipeline_run_id: N }
    ↓
Next poll returns { status: 'completed' }
    client stops polling
    page shows "ingest complete — continue to parse?" button
    ↓
Operator clicks "Parse" → startRun action with step='parse', run_id=N
    (same fire-and-poll cycle repeats for parse, then resolve)
    ↓
After resolve: job.status → 'awaiting_review' if discrepancies exist
    operator reviews in /admin/run/[id]/review
    approves → status → 'completed'
```

### Admin_Jobs Table Rationale

The existing `pipeline_runs` table tracks pipeline provenance: which Python process ran which step, what argument it processed, what the outcome was. That table is owned by the pipeline and must not be repurposed.

The new `admin_jobs` table tracks the web UI's view of a pipeline job:
- Which step is currently active in the ingest→parse→resolve chain
- Whether the operator needs to intervene before the next step
- The input the operator provided (PDF URL or upload path)
- Cross-step continuity (linking ingest_run_id → parse_run_id → resolve_run_id)

These are UI/coordination concerns. They belong in a separate table to preserve the v1.0 policy that `pipeline_runs` is pipeline provenance (PIPE-11: re-running produces new rows, old rows preserved).

**New `admin_jobs` schema (Alembic migration 0003):**
```sql
CREATE TABLE admin_jobs (
    id              SERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    status          TEXT NOT NULL DEFAULT 'queued',
        -- queued | running | awaiting_review | completed | failed
    current_step    TEXT NOT NULL DEFAULT 'ingest',
        -- ingest | parse | resolve
    pdf_url         TEXT,
    pdf_path        TEXT,
    ingest_run_id   INTEGER REFERENCES pipeline_runs(id),
    parse_run_id    INTEGER REFERENCES pipeline_runs(id),
    resolve_run_id  INTEGER REFERENCES pipeline_runs(id),
    argument_id     INTEGER REFERENCES arguments(id),
    error_detail    TEXT
);
```

### Request Flow: Admin Page Load

```
Browser GET /admin/run
    ↓
hooks.server.ts → locals.admin = true
    ↓
/admin/+layout.server.ts load → locals.admin confirmed, no redirect
    ↓
/admin/run/+page.server.ts load
    fetch(FASTAPI_ADMIN_URL + '/admin/jobs?limit=20',
          { headers: { 'X-Admin-Token': ADMIN_API_TOKEN } })
    returns { jobs: AdminJob[] }
    ↓
+page.svelte renders job list with PipelineStatus component
```

---

## Digital Ocean App Platform: Subdomain Routing

**Both `scotuschat.com` and `admin.scotuschat.com` point to the same SvelteKit service component.** No app-level routing by domain is needed.

DO App Platform supports multiple domains on a single component natively. Add both domains in the Networking tab or in the `domains:` array of the app spec. TLS certificates for both are provisioned automatically.

The admin route protection lives entirely in SvelteKit `hooks.server.ts`. The subdomain is a UX convention (it communicates "admin area" to the operator); it provides no security boundary itself. Security is the session cookie.

**App spec fragment:**
```yaml
services:
  - name: web
    # ... build/run config
    domains:
      - domain: scotuschat.com
        type: PRIMARY
        zone: scotuschat.com
      - domain: admin.scotuschat.com
        type: ALIAS
        zone: scotuschat.com
```

No component routing rules are needed. Both domains serve the full SvelteKit app. `/admin/*` protection is enforced by the hook on every request regardless of which domain it arrives on.

---

## Scaling Considerations

This is a single-operator tool. Concurrency and throughput are not concerns. The relevant operational risks are:

| Concern | Mitigation |
|---------|------------|
| Parse step (30–120s) times out HTTP request | Fire-and-poll pattern: action returns job_id immediately; subprocess runs to completion independently |
| Subprocess dies without updating job status | `proc.on('error')` and `proc.on('exit', code !== 0)` both PATCH failed status via FastAPI |
| SvelteKit process restarts mid-run | subprocess is `detached: false` — it dies with parent. `admin_jobs.status` stays `running`; operator sees orphaned job and can restart |
| Two operators running simultaneously | Not a realistic scenario. No concurrency controls needed for v1.1 |
| PgBouncer transaction mode | `statement_cache_size=0` in `connect_args` already in FastAPI engine — must not be removed. New admin router uses the same engine. |

---

## Anti-Patterns

### Anti-Pattern 1: Exposing Pipeline Steps as FastAPI HTTP Endpoints

**What people do:** Add `POST /pipeline/ingest` to FastAPI that SvelteKit calls, which then runs the pipeline logic.

**Why it's wrong:** Violates the explicit architectural constraint ("pipeline is offline only"). Makes ingest reachable over the network. The ingest step downloads URLs — exposing it as an HTTP endpoint creates an SSRF attack surface. Keeps v1.0's clean separation.

**Do this instead:** SvelteKit form action spawns `python -m pipeline ingest` as a subprocess. The pipeline writes directly to the DB as it always has. FastAPI admin endpoints only track job coordination state in `admin_jobs`.

### Anti-Pattern 2: Server-Side Session Store (Redis or in-memory Map)

**What people do:** Generate a session ID, store session data in Redis or a Node.js `Map`, look it up on every request.

**Why it's wrong:** Redis is not in the approved stack — it would be a Golden Path deviation requiring review. In-memory state is lost on server restart, which happens on every DO App Platform deploy (frequent during development).

**Do this instead:** HMAC-signed stateless cookie. Signature proves authenticity without storage. The only trade-off (cannot revoke without rotating `SESSION_SECRET`) is acceptable for single-operator use.

### Anti-Pattern 3: Client-Side Route Guards

**What people do:** In `+layout.svelte`, check `page.data.admin` and call `goto('/admin/login')` if not set.

**Why it's wrong:** Client-side guards flash protected content before redirect. They do not protect server load functions (where DB queries actually run). They are bypassable by disabling JavaScript.

**Do this instead:** `hooks.server.ts` handle hook. Redirect fires before any route renders — no flash, no bypass, no JS dependency.

### Anti-Pattern 4: SvelteKit Writing Directly to PostgreSQL

**What people do:** Import SQLAlchemy in `+page.server.ts`, create an async session, write to the DB directly.

**Why it's wrong:** Creates two DB writer processes (FastAPI and SvelteKit Node.js) with separate connection pools and separate SQLAlchemy engine instances. Pool sizing becomes unpredictable. The v1.0 pattern — FastAPI as the sole app-layer DB writer — must be maintained.

**Do this instead:** All SvelteKit DB operations (admin job creation, status updates, people edits) go through FastAPI admin endpoints via `fetch` with `X-Admin-Token`. The one exception is the `proc.on('exit')` callback, which fires a `fetch` to FastAPI — still FastAPI writing, not SvelteKit.

### Anti-Pattern 5: Awaiting Subprocess Completion in the Form Action

**What people do:** `await new Promise((resolve) => proc.on('exit', resolve))` inside the form action before returning.

**Why it's wrong:** The parse step takes 30–120 seconds. The HTTP request times out (DO App Platform default: 60s). The client gets an error, but the subprocess is still running, leaving the job state inconsistent.

**Do this instead:** Spawn, attach the exit handler, return `{ job_id }` immediately. The client polls for status updates.

### Anti-Pattern 6: Using `PUBLIC_` Prefix for Server-Only Env Vars

**What people do:** Set `PUBLIC_FASTAPI_ADMIN_URL` and `PUBLIC_ADMIN_API_TOKEN` so they're accessible in Svelte components.

**Why it's wrong:** These are server-side credentials. `PUBLIC_` env vars are embedded in the browser JavaScript bundle — anyone loading the page can extract them. `ADMIN_API_TOKEN` in the browser bundle completely defeats the internal token auth model.

**Do this instead:** `FASTAPI_ADMIN_URL` and `ADMIN_API_TOKEN` in `$env/static/private` only. They are accessed only in `+page.server.ts`, `+layout.server.ts`, and `+server.ts` — never in `.svelte` components.

---

## Integration Points

### Modified Existing Components

| Component | Change | Why |
|-----------|--------|-----|
| `src/app.d.ts` | Add `App.Locals { admin: boolean }` | Type-safe access to `event.locals.admin` throughout load functions and hooks |
| `api/main.py` | `app.include_router(admin_router.router)` | Include new admin router |
| `api/core/config.py` | Add `admin_api_token: str` setting | Internal service credential for admin router auth |
| `alembic/versions/` | New migration `0003_add_admin_jobs.py` | `admin_jobs` coordination table — Alembic is sole DDL authority |

### New Components — Build Order

Build in this order. Each layer unblocks the next.

**Layer 1 — Schema + API foundation (no UI):**
1. `alembic/versions/0003_add_admin_jobs.py` — migration must run before anything uses `admin_jobs`
2. `api/core/config.py` — add `admin_api_token` field
3. `api/routers/admin.py` + `api/schemas/admin.py` — FastAPI admin endpoints
4. `api/main.py` — include admin router

**Layer 2 — Auth (SvelteKit):**
5. `src/app.d.ts` — add `App.Locals.admin: boolean`
6. `src/hooks.server.ts` — route guard (requires `app.d.ts` types)
7. `src/routes/admin/+layout.server.ts` — belt-and-suspenders redirect guard
8. `src/routes/admin/login/+page.server.ts` + `+page.svelte` — login form + action
9. `src/routes/admin/logout/+page.server.ts` — cookie clear action

**Layer 3 — Pipeline Runner:**
10. `src/routes/admin/api/run/[id]/+server.ts` — polling endpoint (needed before page can poll)
11. `src/routes/admin/run/+page.server.ts` — `startRun` / `approveContinue` actions + load
12. `src/routes/admin/run/+page.svelte` + `src/lib/components/PipelineStatus.svelte`

**Layer 4 — People Editor:**
13. `src/routes/admin/people/+page.server.ts` + `+page.svelte` — directory list + create
14. `src/routes/admin/people/[id]/+page.server.ts` + `+page.svelte` — edit form

**Layer 5 — Deployment:**
15. DO App Platform app spec update — add `admin.scotuschat.com` as ALIAS domain, add new env vars (`ADMIN_USER`, `ADMIN_PASS`, `SESSION_SECRET`, `ADMIN_API_TOKEN`, `FASTAPI_ADMIN_URL`)

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Digital Ocean App Platform | Both `scotuschat.com` and `admin.scotuschat.com` bound to same SvelteKit component; DO manages TLS | Add `admin.scotuschat.com` as ALIAS in app spec `domains:` array |
| Digital Ocean Managed Postgres | Unchanged — FastAPI engine with `statement_cache_size=0` in `connect_args` (PgBouncer transaction mode) | New admin router uses the same engine/session dependency |
| Python pipeline subprocess | `child_process.spawn` from SvelteKit Node.js process | No pipeline code changes required; same CLI entry point `python -m pipeline` |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Browser ↔ SvelteKit | HttpOnly session cookie + standard HTTP | Cookie validated server-side only; browser JS cannot read it |
| SvelteKit server ↔ FastAPI admin | `X-Admin-Token` header (shared secret, `$env/static/private`) | Token never exposed to browser; never use `PUBLIC_` prefix |
| SvelteKit server ↔ Python pipeline | `child_process.spawn` (subprocess of SvelteKit Node process) | No network call; pipeline writes DB directly as in v1.0 |
| FastAPI ↔ PostgreSQL | SQLAlchemy 2.0 async via asyncpg; PgBouncer transaction mode | `statement_cache_size=0` in `connect_args` — already in place, must not be removed |

---

## Sources

- [SvelteKit Hooks documentation](https://svelte.dev/docs/kit/hooks) — `handle` hook, `event.locals`, cookie access patterns
- [SvelteKit Form Actions documentation](https://svelte.dev/docs/kit/form-actions) — named actions, `fail()`, automatic load re-execution after action
- [Joy of Code: SvelteKit Authentication Using Cookies](https://joyofcode.xyz/sveltekit-authentication-using-cookies) — HMAC-signed cookie pattern basis
- [Digital Ocean App Platform: Manage Domains](https://docs.digitalocean.com/products/app-platform/how-to/manage-domains/) — multiple domains on single component, app spec `domains:` array

---
*Architecture research for: SCOTUS Chat v1.1 admin interface + pipeline job coordination*
*Researched: 2026-06-15*
