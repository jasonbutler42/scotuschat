# Stack Research — v1.1 Admin Interface Additions

**Domain:** Operator admin interface additions to existing SvelteKit + FastAPI app
**Researched:** 2026-06-15
**Confidence:** HIGH for auth and file upload patterns; MEDIUM for job execution architecture (multiple valid approaches; recommendation is opinionated toward simplicity for solo operator)

---

## Context: What Already Exists (Do Not Re-research)

The existing validated stack (from v1.0) is:

- SvelteKit 2.x + adapter-node, Svelte 5 Runes (`$state`, `$derived`, `$effect`)
- FastAPI 0.115+, Pydantic v2, SQLAlchemy 2.0 async, asyncpg, Alembic
- PostgreSQL 16 on Digital Ocean managed Postgres (PgBouncer transaction mode — `statement_cache_size=0` in `connect_args` is already set)
- All FastAPI calls from SvelteKit go through `+page.server.ts` server load functions; `FASTAPI_BASE_URL` is server-only

This document covers ONLY net-new additions for the three v1.1 capability areas. Do not change the existing stack.

---

## Area 1: SvelteKit Session Auth (username+password, no user DB)

### Recommended Approach: DIY hooks + `bcryptjs` — no auth library

**Rationale:** Credentials live in two env vars (`ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH`). No user table exists or should be added. Auth.js, Better Auth, and Lucia are all overkill — they require a database-backed session store and adapter wiring. This is a single-operator tool; the entire auth system fits in ~50 lines across two files.

**Implementation pattern:**

1. **Login action** (`src/routes/admin/login/+page.server.ts`) — Reads `ADMIN_USERNAME` and `ADMIN_PASSWORD_HASH` from `$env/static/private`. Calls `bcrypt.compare(submittedPassword, storedHash)`. On success: generates `crypto.randomUUID()`, signs it with HMAC-SHA256 using `SESSION_SECRET` env var (Node `crypto.createHmac`), sets it as an httpOnly cookie. On failure: returns `{ error: 'Invalid credentials' }`.

2. **`src/hooks.server.ts` `handle` function** — Runs before every request. Reads the session cookie, re-validates the HMAC signature. If the path starts with `/admin` and the session is invalid, calls `redirect(302, '/admin/login')`. On valid session, populates `event.locals.user = { username: string }`.

3. **`src/app.d.ts`** — Extend `App.Locals` with `user: { username: string } | null`.

4. **Route protection** — Each admin `+page.server.ts` load function checks `if (!locals.user) redirect(302, '/admin/login')` as a belt-and-suspenders guard beyond the hook.

**Session is stateless** — no DB round-trip per request. A signed random token stored in the cookie is sufficient. The operator cannot invalidate a session remotely (deleting the cookie is the only logout mechanism), which is acceptable for single-operator use.

**One-time setup:** Generate the bcrypt hash offline and store it as `ADMIN_PASSWORD_HASH`:

```bash
node -e "const b = require('bcryptjs'); b.hash('yourpassword', 12).then(console.log)"
```

### New JavaScript/TypeScript Dependencies

| Package | Version | Purpose | Install location |
|---------|---------|---------|-----------------|
| `bcryptjs` | `^2.4.3` | Password hash comparison in login action. Pure JS — no native bindings. | `app/` (dependency) |
| `@types/bcryptjs` | `^2.4.6` | TypeScript types for bcryptjs | `app/` (devDependency) |

**Why `bcryptjs` and not `@node-rs/argon2`:** Argon2id is the stronger algorithm, but `@node-rs/argon2` ships native `.node` binaries that Vite/Rollup struggles to bundle in SvelteKit production builds (open GitHub issues through late 2024, including sveltejs/kit#13061). `bcryptjs` is pure JavaScript, builds without friction with adapter-node, and bcrypt at cost 12 is fully adequate for a single hashed credential stored in an env var that never changes. Add argon2 only if a real user DB is introduced in a future milestone.

**Why not `svelte-kit-cookie-session`:** Last released August 2023, 187 stars. The same pattern is ~10 lines using Node's built-in `crypto.createHmac`. Avoid the dependency whose maintenance trajectory is unclear.

**Why not Auth.js / Better Auth / Lucia:** All three require a database adapter. Better Auth and Lucia generate their own schema — that is DDL outside Alembic, which violates the project constraint. Lucia is deprecated as a library (now a learning reference only). These tools exist for multi-user applications with real credential storage; none of that applies here.

---

## Area 2: Background Pipeline Job Execution

### Recommended Approach: FastAPI admin router + `asyncio.create_subprocess_exec` + DB status polling

**Architecture:** Add a new protected router (`api/routers/admin.py`) to the existing FastAPI app — not a second service. The router validates an `X-Admin-Key` header (value from `ADMIN_API_KEY` env var) on every request. SvelteKit server actions set this header; it never reaches the browser.

**Job lifecycle:**

1. SvelteKit action POSTs to `POST /admin/pipeline/runs` with `{ argument_id, step }`.
2. FastAPI creates a `pipeline_run` row (status=`pending`), immediately returns `{ pipeline_run_id }`.
3. FastAPI schedules the pipeline step as an asyncio `BackgroundTask` that calls `asyncio.create_subprocess_exec()` — the subprocess runs the existing Python CLI entry point.
4. The background task updates `pipeline_run.status` to `running` on start, then `completed` / `failed` / `needs_review` on subprocess exit. Stdout+stderr are captured and written to a new `log` TEXT column on `pipeline_run`.
5. SvelteKit polls `GET /admin/pipeline/runs/{id}` every 2–3 seconds. The existing `pipeline_run` status machine already has all needed states — no schema rework required.

**New FastAPI files:**
- `api/routers/admin.py` — pipeline trigger endpoint, status endpoint, people-write endpoints
- `api/dependencies/admin_auth.py` — `Depends` that validates `X-Admin-Key` header

**New schema addition:** One Alembic migration adds `log TEXT` to `pipeline_run`. No new tables needed for job tracking; the existing `pipeline_run` table covers it.

**Why `asyncio.create_subprocess_exec` and not `subprocess.run`:** The pipeline steps run for seconds to minutes. `subprocess.run` blocks the uvicorn event loop, stalling all other requests during a run. `create_subprocess_exec` is non-blocking on Linux (the DO App Platform target). The Windows `SelectorEventLoop` limitation (FastAPI discussions/7770) does not apply on Linux containers.

**Why not Celery / ARQ / Redis:** A single-operator tool runs at most one pipeline job at a time. Adding Redis as a broker is a new infrastructure component on App Platform — a second stateful service with its own connection string, health check, and cost. The existing PostgreSQL instance already tracks `pipeline_run` state; polling it at 2–3s intervals is sufficient. Celery is correct for distributed workers and high-throughput queuing; neither applies here.

**Why not FastAPI's built-in `BackgroundTasks` alone (without subprocess):** `BackgroundTasks` runs functions in the same process after the response is sent, with no retry, no crash recovery, and no status persistence. If uvicorn restarts mid-job, the task silently disappears. Spawning a subprocess and tracking status in the DB gives crash-survivability — on restart, the DB row shows `running` and the operator can re-trigger.

**Why no SSE / WebSocket for job progress:** SSE would add either a `sveltekit-sse` library dependency or a custom `ReadableStream` endpoint, plus a persistent HTTP connection, for the sole benefit of sub-second latency updates to one operator. `setInterval` polling against the existing REST status endpoint is sufficient and keeps the implementation within the established `+page.server.ts` → FastAPI pattern.

### New Python Dependencies

None. `asyncio.create_subprocess_exec` is Python 3.12 stdlib. SQLAlchemy async session for status updates is already present. The `log` column write uses existing ORM patterns.

---

## Area 3: File Upload (PDF to Disk)

### Recommended Approach: SvelteKit form action + `node:fs/promises` + DigitalOcean Spaces

**SvelteKit upload pattern** (no new npm packages — stdlib only):

```typescript
// src/routes/admin/pipeline/+page.server.ts
import { writeFile } from 'node:fs/promises';
import { extname } from 'node:path';

export const actions = {
  upload: async ({ request }) => {
    const formData = await request.formData();
    const file = formData.get('pdf') as File;
    const tempPath = `/tmp/${crypto.randomUUID()}${extname(file.name)}`;
    await writeFile(tempPath, Buffer.from(await file.arrayBuffer()));
    // POST tempPath to FastAPI admin trigger endpoint — same request lifecycle
  }
};
```

`request.formData()` handles `multipart/form-data` natively in SvelteKit (no `multer`, no `formidable`). The `Buffer.from(await file.arrayBuffer())` pattern is the validated approach per the SvelteKit community (travishorn.com).

**Critical Digital Ocean constraint:** App Platform containers have no persistent filesystem and no writable volumes. Files written to `/tmp/` are lost on every deploy or container replacement. This means:

1. The uploaded PDF must be relayed to DigitalOcean Spaces (S3-compatible) before the HTTP response is sent — or within the same server action lifecycle.
2. The FastAPI pipeline `ingest` step must be adapted to fetch from Spaces (via a Spaces object key) rather than a local path.

**Storage flow:**

```
Browser → SvelteKit action → /tmp/uuid.pdf (temp)
                           → POST to FastAPI /admin/pipeline/runs with spaces_key
SvelteKit action → boto3.upload_file → DO Spaces bucket
FastAPI ingest step → boto3.download_file → pipeline processing
```

The Python pipeline side uploads via boto3; FastAPI's admin endpoint receives the Spaces key and passes it to the subprocess.

### New Python Dependencies (pipeline/api side)

| Package | Version | Purpose |
|---------|---------|---------|
| `boto3` | `^1.34` | Upload PDF to DO Spaces; fetch from Spaces in pipeline ingest step. S3-compatible — same API as AWS S3. |

`botocore` is installed automatically as a `boto3` dependency; pin them together in requirements.

**Why Spaces and not local filesystem:** DO App Platform does not support persistent volumes. The docs state explicitly: "App Platform does not currently support volumes because instances are scalable and ephemeral." Any file not in the DB or Spaces is gone after the next deploy.

**Why boto3 and not the `s3fs` / `aiobotocore` variants:** The upload happens once at ingest time in a CLI-style context. Standard synchronous boto3 is correct. Async S3 adds complexity with no benefit for this use case.

---

## Complete Installation Reference

```bash
# In app/ — SvelteKit (new additions only)
npm install bcryptjs
npm install -D @types/bcryptjs

# In api/ or pipeline/ Python environment (new additions only)
pip install boto3>=1.34
```

No other new packages. The session token signing uses `node:crypto` (built-in). File writing uses `node:fs/promises` (built-in). The subprocess pattern uses Python `asyncio` (built-in).

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `better-auth` | Requires database schema; that is DDL outside Alembic — violates project constraint. Overkill for env-var credentials. | DIY hooks + `bcryptjs` |
| `auth.js` (NextAuth for SvelteKit) | Same DB adapter problem; complex config for a no-user-DB scenario | DIY hooks + `bcryptjs` |
| `lucia-auth` | Deprecated as a library (now a learning reference only); has the same DB requirement | DIY hooks + `bcryptjs` |
| `svelte-kit-cookie-session` | Last released Aug 2023; low adoption; HMAC pattern achieves the same in stdlib Node crypto | `node:crypto` `createHmac` |
| `@node-rs/argon2` | Native binary causes Vite/Rollup build failures in SvelteKit production builds (open issues through late 2024) | `bcryptjs` |
| Celery + Redis | New infra dependency (Redis service on DO App Platform) for a single-operator sequential job runner | `asyncio.create_subprocess_exec` + DB polling |
| ARQ / SAQ | Also Redis-backed | Same as Celery |
| FastAPI `BackgroundTasks` without subprocess | No crash recovery; job is silently lost on process restart | Subprocess + DB status row |
| SSE / WebSocket for job progress | Library dependency and persistent connection overhead for one operator who can wait 3 seconds | `setInterval` polling on existing REST endpoint |
| `multer` / `formidable` | Node.js multipart libraries; SvelteKit form actions handle multipart natively via `request.formData()` | `request.formData()` + `node:fs/promises` |
| Second FastAPI service for admin | Separate deploy unit, separate DB connection pool, separate auth surface | Protected router on existing FastAPI app |
| Local filesystem for persistent PDFs | DO App Platform has no persistent volumes; files are lost on redeploy | DigitalOcean Spaces via boto3 |

---

## Integration Points with Existing Stack

| Existing piece | How new code hooks in |
|----------------|-----------------------|
| `pipeline_run` table + status machine | Reused as-is for job status tracking; only addition is a `log TEXT` column via new Alembic migration |
| `FASTAPI_BASE_URL` env var in SvelteKit | Admin actions call FastAPI using the same server-only pattern; `ADMIN_API_KEY` added as a second server-only env var |
| `+page.server.ts` load + action pattern | All admin pages follow the same established pattern; write operations use named `actions` exports |
| `hooks.server.ts` | New `handle` export added; if a handle function already exists, use SvelteKit's `sequence()` helper to compose them |
| Alembic migrations | `log TEXT` column on `pipeline_run` goes in a new numbered migration; `Base.metadata.create_all` is never called |
| PgBouncer `statement_cache_size=0` | No change; admin FastAPI router reuses the existing session factory |

---

## Digital Ocean App Platform Compatibility Notes

1. **No persistent filesystem / no volumes.** PDF uploads must be forwarded to Spaces within the same request action before the temp file is at risk. Never depend on disk between requests.
2. **No volumes.** This is a hard platform constraint, not a configuration option. Spaces is the only supported persistent file store.
3. **File upload timeout: 600 seconds.** SCOTUS PDFs are typically 200–800 KB — well within this limit.
4. **Local filesystem cap: 4 GiB.** Write uploaded files to `/tmp/` only; never accumulate them across requests.
5. **Internal service communication.** The SvelteKit service calls FastAPI via the App Platform internal hostname — the same `FASTAPI_BASE_URL` pattern already in use. No change needed.
6. **`asyncio.create_subprocess_exec` on Linux.** The Windows `SelectorEventLoop` limitation does not apply on DO App Platform (Linux containers). This is the production target.

---

## Version Compatibility

| Package | Requires | Notes |
|---------|----------|-------|
| `bcryptjs@^2.4.3` | Node 18+, SvelteKit 2.x | Pure JS; zero native build step; no Vite config changes needed |
| `@types/bcryptjs@^2.4.6` | TypeScript 5.x | Matches bcryptjs 2.4.x API surface |
| `boto3@^1.34` | Python 3.12, botocore 1.34 | Pin botocore alongside boto3; they version together |
| `asyncio.create_subprocess_exec` | Python 3.12 stdlib, Linux only | Correct for DO App Platform; not needed on Windows dev machines (pipeline runs locally anyway) |

---

## Sources

- SvelteKit official docs (Auth page) — session/cookie locals pattern, `hooks.server.ts` structure: https://svelte.dev/docs/kit/auth
- joyofcode.xyz — httpOnly cookie session pattern, `crypto.randomUUID` token: https://joyofcode.xyz/sveltekit-authentication-using-cookies
- Lucia v3 tutorial — `@node-rs/argon2` configuration params, `hooks.server.ts` `locals.user` pattern: https://v3.lucia-auth.com/tutorials/username-and-password/sveltekit
- lucia-auth/lucia issue #1567 — `@node-rs/argon2` production build breakage in SvelteKit (native binary Rollup parse error): https://github.com/lucia-auth/lucia/issues/1567
- sveltejs/kit issue #13061 — `@node-rs/argon2-wasm32-wasi` resolution failure in SvelteKit builds: https://github.com/sveltejs/kit/issues/13061
- travishorn.com — `request.formData()` + `writeFile(Buffer.from(arrayBuffer()))` validated upload pattern: https://travishorn.com/uploading-and-saving-files-with-sveltekit/
- sveltetalk.com — SvelteKit 2.49 streaming upload context: https://sveltetalk.com/posts/stream-file-uploads-249
- DO App Platform storage docs — no volumes; Spaces is the persistent option: https://docs.digitalocean.com/products/app-platform/how-to/store-data/
- DO support — 600s upload timeout, 4 GiB local cap: https://docs.digitalocean.com/support/why-are-large-files-failing-to-upload-to-my-app-on-app-platform/
- fastapi/fastapi discussion #7770 — `asyncio.create_subprocess_exec` in FastAPI BackgroundTasks; Windows caveat confirmed Linux-only: https://github.com/fastapi/fastapi/discussions/7770
- betterstack.com — BackgroundTasks limitations for long-running work: https://betterstack.com/community/guides/scaling-python/background-tasks-in-fastapi/

---
*Stack research for: SCOTUS Chat v1.1 operator admin interface additions*
*Researched: 2026-06-15*
