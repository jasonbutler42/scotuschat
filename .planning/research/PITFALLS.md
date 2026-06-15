# Domain Pitfalls

**Domain:** LLM-based legal transcript parsing pipeline + SCOTUS oral argument chat interface + operator admin web interface
**Researched:** 2026-06-15 (v1.1 additions); 2026-06-11 (v1.0 foundation)
**Scope:** v1.1 additions — session auth without user DB, subprocess pipeline runner, admin route protection, file upload, resumable job state machine, Digital Ocean deployment; v1.0 foundation — LLM pipelines, SCOTUS transcript quirks, speaker resolution, SvelteKit/FastAPI integration

---

## Critical Pitfalls — v1.1 Admin Interface

Mistakes specific to adding auth, background jobs, and admin routes to the existing system.

---

### Pitfall V1: Infinite Redirect Loop When Login Page Is Not Excluded from Auth Guard

**What goes wrong:** `hooks.server.ts` redirects any unauthenticated request to `/admin/login`. If the guard does not explicitly exclude `/admin/login` itself, the login page request is unauthenticated → gets redirected to `/admin/login` → which is also unauthenticated → redirect → infinite 302 loop. The browser shows ERR_TOO_MANY_REDIRECTS.

**Why it happens:** Auth guards are written as "if not authenticated, redirect to login" without thinking about what happens when the redirect destination is itself guarded. The error is invisible during development if the developer happens to be authenticated in their browser session.

**How to avoid:**
- In `hooks.server.ts`, check `event.url.pathname` and return early for the login page before applying the auth check:
  ```typescript
  if (event.url.pathname === '/admin/login') return resolve(event);
  if (event.url.pathname.startsWith('/admin')) { /* check session */ }
  ```
- Also exclude static asset paths (`/_app/`, `/favicon.ico`) from auth checks — these are not guarded routes.
- Write a test that hits `/admin/login` while unauthenticated and asserts a 200 response, not a 302.

**Warning signs:** Browser console shows ERR_TOO_MANY_REDIRECTS; server logs show rapid repeated requests to the same URL.

**Phase to address:** Auth foundation phase (first admin work).

---

### Pitfall V2: Session Cookie Missing HttpOnly or SameSite Attributes

**What goes wrong:** Session cookie is set without `httpOnly: true`, making it accessible via `document.cookie` in the browser. Any XSS vulnerability (even in a dependency) can read and exfiltrate the session token. Alternatively, `sameSite` defaults to `'lax'` in SvelteKit's cookie API, which is correct — but developers sometimes explicitly set it to `'none'` to work around perceived CORS issues between the main app and the admin subdomain. `sameSite: 'none'` requires `secure: true` to function and opens CSRF exposure.

**Why it happens:** Developers copy-paste cookie examples without auditing the attributes. Cross-subdomain scenarios (`scotuschat.com` vs. `admin.scotuschat.com`) create pressure to set `sameSite: 'none'` when the real fix is `domain: '.scotuschat.com'` with `sameSite: 'lax'`.

**How to avoid:**
- Always set session cookies with at minimum: `httpOnly: true`, `sameSite: 'lax'`, `path: '/'`, `secure: true` (auto-set by SvelteKit in production).
- For subdomain sharing: set `domain: '.scotuschat.com'` — this allows the cookie to be sent to `admin.scotuschat.com` without weakening `sameSite`.
- Never set `sameSite: 'none'` on an admin session cookie. If cross-origin requests are needed, fix CORS headers instead.
- SvelteKit's CSRF protection validates the `Origin` header by default — do not disable `csrf.checkOrigin` in `svelte.config.js`.

**Warning signs:** DevTools Application tab shows session cookie without HttpOnly flag; `SameSite=None` without `Secure` attribute in production.

**Phase to address:** Auth foundation phase.

---

### Pitfall V3: Credentials Compared with == Instead of Timing-Safe Equality

**What goes wrong:** Username and password are stored as env vars and compared with `=== ` string equality in the login action. JavaScript's `===` short-circuits on the first differing character — a timing attack can measure response time differences to enumerate valid usernames before attacking passwords.

**Why it happens:** Single-operator systems feel low-risk, so developers skip cryptographic hygiene. The attack surface for timing attacks on a single-operator admin tool is genuinely low, but the fix is one line of code and the cost of skipping it is a false sense of security.

**How to avoid:**
- For password comparison, use Node's `crypto.timingSafeEqual()` on Buffer representations of both strings.
- Never log the raw password value anywhere — not in error messages, not in structured logs, not in `console.error` traces.
- Session token should be a cryptographically random value (`crypto.randomBytes(32).toString('hex')`), not a hash of the credentials.

**Warning signs:** Login action uses `password === process.env.ADMIN_PASSWORD` directly.

**Phase to address:** Auth foundation phase.

---

### Pitfall V4: Session Token Stored in Cookie Body (No Server-Side Invalidation)

**What goes wrong:** Session is implemented as a signed cookie containing `{ username, expires }` — the session _is_ the cookie. There is no server-side session store. Logging out clears the cookie client-side, but the token remains valid until its embedded expiry. If an attacker captures the cookie value (e.g., via network sniff before HTTPS was fully enforced), they can replay it after logout.

**Why it happens:** Stateless JWT-style sessions are simpler to implement — no database table, no lookup on every request. For a single-operator internal tool this is a reasonable tradeoff only if the implications are understood.

**How to avoid:** For this project, a simple in-memory or database-backed session store is the right call. Store `{ session_id, created_at, expires_at }` in PostgreSQL. The cookie carries only the opaque session ID. Logout deletes the row. This uses the existing DB and adds one table via Alembic — consistent with the project's DDL authority rule.
- The session table must go through an Alembic migration, never `Base.metadata.create_all`.

**Warning signs:** Cookie value is a JWT or base64-encoded JSON blob; no sessions table in the schema.

**Phase to address:** Auth foundation phase — decide on stateful vs. stateless before writing the cookie handler.

---

### Pitfall V5: Layout-Based Route Protection Is Bypassed by Direct +page.server.ts Access

**What goes wrong:** Auth check is placed in `+layout.server.ts` for the `/admin` group. Direct navigation to a protected URL works correctly. But SvelteKit's server load function hierarchy means a layout's auth check runs when the layout is rendered — if a route is accessed via a `fetch` call to its `+page.server.ts` endpoint directly (e.g., internal server-side fetch), the layout load may not run. More critically, any `+server.ts` API endpoints inside `/admin/` do not inherit layout protection at all — they receive requests without the layout running.

**Why it happens:** The mental model of "layout wraps routes" maps cleanly to visual nesting but does not map 1:1 to server-side security for API endpoints. This is a documented known issue in the SvelteKit ecosystem.

**How to avoid:**
- Place the auth check in `hooks.server.ts`, not in a layout. The `handle` hook runs for every request — pages, API endpoints, and assets — before any route-specific code executes.
- `+layout.server.ts` may still run auth-dependent logic (e.g., passing `locals.user` to components), but the _gate_ (redirect unauthenticated users) must be in the hook.
- After adding any new `+server.ts` endpoint under `/admin/`, explicitly verify it returns 401/403 when the session cookie is absent.

**Warning signs:** Auth check is only in `+layout.server.ts` and not in `hooks.server.ts`; `+server.ts` files exist under `/admin/` without hook-level protection.

**Phase to address:** Auth foundation phase — lock the pattern before building any admin pages.

---

### Pitfall V6: App.Locals Not Typed in app.d.ts Causes Runtime Errors Invisible to TypeScript

**What goes wrong:** `hooks.server.ts` sets `event.locals.session` but `app.d.ts` does not declare `session` on `App.Locals`. TypeScript does not error — it silently infers `any`. Downstream code that reads `locals.session` in a page server load gets `undefined` in production (e.g., when the session expires) but TypeScript does not warn. The bug surfaces as a runtime crash or unexpected redirect, not a type error.

**Why it happens:** `app.d.ts` is boilerplate that developers skip. The existing codebase has `App.Locals` as an empty commented interface — this will require an explicit update.

**How to avoid:**
- Update `app.d.ts` when adding session to locals:
  ```typescript
  declare global {
    namespace App {
      interface Locals {
        session: { userId: string; expiresAt: Date } | null;
      }
    }
  }
  ```
- Do NOT import types using ES `import` statements at the top of `app.d.ts` — this converts it from an ambient declaration file to a module and breaks global type augmentation. Use inline `import type` inside the namespace block if needed.

**Warning signs:** `event.locals` properties access compiles without errors but produces `undefined` at runtime; `App.Locals` interface body is empty or commented out while hooks set locals.

**Phase to address:** Auth foundation phase.

---

### Pitfall V7: ORIGIN Environment Variable Not Set in Production — CSRF Errors at Login

**What goes wrong:** `adapter-node` requires the `ORIGIN` environment variable to be set in production so SvelteKit can validate CSRF via the `Origin` request header. In development, `localhost` is auto-detected. On Digital Ocean App Platform, if `ORIGIN` is not explicitly set to `https://admin.scotuschat.com`, every form submission (including the login form) returns a 403 CSRF error. This is silent — the error message says "forbidden" not "missing ORIGIN."

**Why it happens:** `ORIGIN` is not in any `.env` file because it is a runtime variable that changes per environment. Developers add it to their local `.env` but forget to add it to the Digital Ocean App Platform environment variable configuration.

**How to avoid:**
- Set `ORIGIN=https://admin.scotuschat.com` in the Digital Ocean App Platform environment variables for the SvelteKit service.
- Also set `PROTOCOL_HEADER=x-forwarded-proto` and `HOST_HEADER=x-forwarded-host` since the app runs behind Digital Ocean's load balancer/proxy.
- Test the login form submission (not just page load) in the staging environment before declaring deployment complete.

**Warning signs:** Login page loads but submitting credentials returns 403; server logs show "Cross-site POST form submissions are forbidden."

**Phase to address:** Deployment phase — must be in the DO App Platform environment config checklist.

---

### Pitfall V8: Subprocess Pipeline Jobs Leave status='running' After Server Crash

**What goes wrong:** SvelteKit server action spawns a Python subprocess to run a pipeline step. The action writes `status='running'` to the `pipeline_runs` table before spawning. The server crashes (OOM, deploy, restart) before the subprocess completes. The subprocess dies with the server. The pipeline run is permanently stuck at `status='running'` with no way to recover via the UI — every subsequent check sees "running" and either blocks a new run or shows stale progress.

**Why it happens:** The status write and subprocess lifecycle are not transactionally linked. There is no heartbeat or timeout mechanism to detect that the subprocess is no longer alive.

**How to avoid:**
- Add a `started_at` timestamp and a `heartbeat_at` timestamp to `pipeline_runs` (or a new `pipeline_jobs` table).
- On server startup, run a recovery query: any pipeline run with `status='running'` and `heartbeat_at < NOW() - interval '5 minutes'` is transitioned to `status='failed'` with `failure_reason='interrupted'`.
- The subprocess updates `heartbeat_at` via a DB write (or the SvelteKit server updates it while polling the subprocess) at regular intervals.
- This recovery logic must run before the first request is accepted — place it in a server startup hook or the first admin page's server load.

**Warning signs:** After a server restart, any in-progress pipeline run shows `status='running'` indefinitely; operator has no way to start a new run for the same argument.

**Phase to address:** Pipeline runner phase — heartbeat/recovery must be designed before the first subprocess spawn.

---

### Pitfall V9: Subprocess stdout/stderr Buffering Causes Silent Job Hang

**What goes wrong:** SvelteKit server action spawns `python -m pipeline ingest ...` as a child process and reads its output. Python's stdout is line-buffered when connected to a terminal but _block-buffered_ (8KB buffer) when connected to a pipe. The subprocess writes log lines but they accumulate in the buffer without flushing. The parent process waits for output that never arrives. The job appears hung even though the subprocess is running correctly.

**Why it happens:** Python buffering behavior differs between TTY and pipe contexts. Developers test the subprocess in a terminal (where buffering is not an issue) and don't encounter the bug until it runs from within SvelteKit.

**How to avoid:**
- Run the Python subprocess with `PYTHONUNBUFFERED=1` in the environment, or pass `-u` flag: `python -u -m pipeline ...`. Either disables output buffering.
- Use `asyncio.create_subprocess_exec` with `stdout=PIPE, stderr=PIPE` and `await process.communicate()` — do not mix blocking `subprocess.run` with async SvelteKit handlers.
- For progress streaming, prefer polling the `pipeline_runs` DB status from the client (every 2 seconds via a SvelteKit `+server.ts` status endpoint) rather than piping subprocess stdout to the HTTP response — the latter couples job lifetime to the HTTP connection lifetime.

**Warning signs:** Subprocess runs correctly from CLI but appears to hang or produce no output when invoked from SvelteKit; `ps aux` shows the Python process running but no output in server logs.

**Phase to address:** Pipeline runner phase.

---

### Pitfall V10: BODY_SIZE_LIMIT Blocks PDF Uploads Silently at Default 512KB

**What goes wrong:** `@sveltejs/adapter-node` has a default `BODY_SIZE_LIMIT` of 512KB. SCOTUS transcript PDFs typically range from 200KB to 2MB. Uploads above 512KB fail with a generic HTTP 413 error. The SvelteKit form action receives no data — `request.formData()` throws or returns empty. Without explicit error handling for 413, the operator sees a blank failure with no message.

**Why it happens:** The 512KB default is documented but easy to miss. The error manifests as a form action failure with no useful error message if the action is not written to handle the case where formData is unavailable.

**How to avoid:**
- Set `BODY_SIZE_LIMIT=10M` as an environment variable on the Digital Ocean App Platform SvelteKit service. This covers PDFs up to 10MB.
- Alternatively, configure it in `svelte.config.js` via the adapter: `adapter({ bodySize: 10 * 1024 * 1024 })` — but the env var approach is simpler for PaaS deployments.
- In the upload form action, wrap `await request.formData()` in a try/catch and return a `fail(413, { message: 'File too large' })` response with an operator-visible error message.
- Validate file size client-side too (before upload) to give immediate feedback.

**Warning signs:** PDF uploads fail for files over ~500KB; form action receives no file data; server logs show "Content-length exceeds limit."

**Phase to address:** File upload phase — set BODY_SIZE_LIMIT before testing any upload functionality.

---

### Pitfall V11: PDF MIME Type Not Validated Server-Side (Content-Type Header Spoofable)

**What goes wrong:** Upload handler checks `file.type === 'application/pdf'` from the multipart form data. The `Content-Type` header in multipart is set by the browser/client and is trivially spoofable. A malicious or accidentally incorrect upload of an HTML file named `transcript.pdf` passes this check.

**Why it happens:** Client-supplied MIME type feels like a reasonable validation. The distinction between client-reported and server-verified content type is easy to overlook.

**How to avoid:**
- After receiving the uploaded file bytes, check the magic bytes (PDF files begin with `%PDF-` — hex `25 50 44 46 2D`). Read the first 5 bytes of the file and verify against this signature before passing to the pipeline.
- Optionally use Python's `filetype` library on the server side where the pipeline runs for a deeper check.
- Enforce a maximum file size (e.g., 15MB) — real SCOTUS PDFs are never this large; a larger upload is a signal of a problem.
- Store the validated file to a dedicated `data/pending/` directory, not to the final `data/` immutable path, until the ingest step confirms the PDF is parseable.

**Warning signs:** Upload handler accepts any file with a `.pdf` extension; no magic byte check anywhere in the upload or ingest code path.

**Phase to address:** File upload phase.

---

### Pitfall V12: Uploaded PDF Temp Files Accumulate If Pipeline Fails Before Ingest

**What goes wrong:** Uploaded PDF is written to a temp path before the pipeline ingest step runs. If the ingest step fails, throws, or the server restarts, the temp file is never cleaned up. Over time, failed uploads fill disk space. On Digital Ocean App Platform, ephemeral container storage is limited (typically a few GB) and not visible in the UI until it causes a crash.

**Why it happens:** Happy-path thinking — cleanup is only considered when the upload succeeds. Failure paths (pipeline error, server restart, network drop mid-ingest) do not trigger cleanup.

**How to avoid:**
- Keep `pending/` PDFs separate from `data/` (permanent, immutable). Ingest step moves the file from `pending/` to `data/` on success.
- Add a startup cleanup routine: any file in `pending/` older than 1 hour with no associated `pipeline_run` record in `running` or `pending` status is deleted.
- For Digital Ocean App Platform: prefer storing uploaded files to Digital Ocean Spaces (object storage) rather than the container filesystem — this avoids ephemeral storage limits and survives container restarts.
- The PDF immutability rule from PROJECT.md applies to `data/` only — `pending/` files are mutable until promoted.

**Warning signs:** `pending/` directory grows after failed ingest attempts; no cleanup logic in the upload or ingest code.

**Phase to address:** File upload and pipeline runner phases.

---

### Pitfall V13: Pipeline Job State Machine Has No Guard Against Concurrent Runs on Same Argument

**What goes wrong:** Operator submits a pipeline run for argument ID 42. Before it completes, they refresh the page and submit again. Two concurrent pipeline runs are now writing to `pipeline_runs` for the same `argument_id`. Both write utterance rows with different `pipeline_run_id` values. The `max(pipeline_run_id)` filter in the service layer will eventually show only the latest, but during the concurrent window, queries may see mixed rows from both runs. If both runs complete, the second run may overwrite aliases or participant records set by the first.

**Why it happens:** Idempotency for a pipeline with DB side-effects is hard. Re-run semantics (new rows under new pipeline_run_id) protect utterances but not all derived state (alias table updates, participant records).

**How to avoid:**
- Before starting any pipeline step, check: is there a `pipeline_run` for this `argument_id` and `step` with `status IN ('pending', 'running')`? If yes, reject the new run with a clear error.
- This guard must be atomic — use a PostgreSQL advisory lock or a `SELECT FOR UPDATE` on the pipeline_runs row to prevent a TOCTOU race.
- The admin UI must disable the "Run" button while any step for the current argument is in `pending` or `running` status. The server-side guard is the real protection; the UI guard is UX.

**Warning signs:** No uniqueness constraint or status check before inserting a new `pipeline_runs` row for an already-in-progress argument.

**Phase to address:** Pipeline runner phase — concurrency guard before the first subprocess spawn.

---

### Pitfall V14: Resumable Jobs Track Step Progress in Application Memory Instead of DB

**What goes wrong:** Pipeline job state (current step, sub-step progress, errors encountered) is tracked in a server-side in-memory object (e.g., a `Map<jobId, JobState>`). This survives for the duration of the server process. When the server restarts (deploy, crash, DO App Platform container cycling), all in-memory state is lost. The operator sees no active jobs — the DB shows `status='running'` but the in-memory state that would drive the UI is gone.

**Why it happens:** In-memory state is fast and easy to implement for a single-server deployment. The implicit assumption is that the server never restarts — valid for development, invalid for a PaaS deployment.

**How to avoid:**
- All resumable state lives in the DB. The `pipeline_runs` table is the system of record. Add columns as needed (`current_sub_step`, `progress_detail`, `heartbeat_at`) rather than storing state in memory.
- The UI polls a `GET /admin/jobs/:id/status` endpoint that reads from the DB. There is no server-side state to lose.
- Subprocess status updates write directly to the DB (or via a thin FastAPI endpoint). The SvelteKit server polls the DB between status checks.

**Warning signs:** Any `Map`, object cache, or module-level variable used to track job state across requests in SvelteKit server code.

**Phase to address:** Pipeline runner phase — design the state schema before any subprocess code is written.

---

### Pitfall V15: Running Pipeline Step from SvelteKit Server Action Ties HTTP Request to Job Lifetime

**What goes wrong:** Server action `async function run_pipeline() { await subprocess.run(); return { success: true }; }`. The HTTP request from the browser is kept open for the entire duration of the pipeline step. A SCOTUS transcript parse step can take 2-10 minutes (LLM calls). The browser times out (typically 30s for most clients, 60s for some). Digital Ocean's App Platform proxy has its own timeout (typically 60s). The action fails, the operator gets an error, but the subprocess is still running in the background — untracked, with no way to surface its completion.

**Why it happens:** The natural shape of `async/await` makes it tempting to `await` the subprocess directly in the action. The issue is invisible in development (where pipeline steps complete quickly against test data).

**How to avoid:**
- Fire-and-forget pattern: the server action spawns the subprocess and immediately returns `{ status: 'started', runId }`. The subprocess runs independently.
- The operator UI polls a status endpoint (e.g., every 3 seconds) to check `pipeline_runs.status`.
- For streaming output, use Server-Sent Events (SSE) from a `+server.ts` endpoint that streams `pipeline_runs.heartbeat_at` and `failure_reason` updates — not raw subprocess stdout.
- The subprocess must write its own status updates to the DB — do not rely on the SvelteKit process to relay them.

**Warning signs:** Server action `await`s a subprocess call that can take more than 10 seconds; no polling mechanism for job status.

**Phase to address:** Pipeline runner phase — async job pattern must be established before any real pipeline step is wired up.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Stateless session (signed cookie, no DB table) | No migration, no DB query per request | Cannot invalidate sessions; replay attacks after logout possible | Never for a production system; only if server restart is the only logout mechanism |
| Auth check in `+layout.server.ts` only | Less code, co-located with admin UI | API endpoints under `/admin/` are unprotected; bypassed by direct fetch | Never — hooks.server.ts guard is mandatory |
| Blocking `await subprocess.run()` in server action | Simple async/await code | HTTP timeout kills operator UX for any step >30s | Only for sub-second operations; never for LLM pipeline steps |
| Tracking job state in memory | Fast, no DB schema changes | Lost on restart; invisible to second server instance | Never on PaaS; only acceptable in single-server dev with zero restart tolerance |
| Skip PDF magic byte check (trust Content-Type header) | Less code | Allows non-PDF uploads to reach pipeline ingest | Never for file uploads |
| Store PDFs on container filesystem | Simple path-based logic | Ephemeral storage fills; lost on container restart | Dev/local only; Spaces in production |

---

## Integration Gotchas

Common mistakes when connecting the SvelteKit admin UI to the Python pipeline and FastAPI.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| SvelteKit → Python subprocess | Calling pipeline CLI with `subprocess.run(["python", ...])` — wrong interpreter in PaaS | Use the full venv Python path or `sys.executable` from a Python launcher; set working directory explicitly |
| SvelteKit → PostgreSQL (session table) | Using the FastAPI DB session for admin session reads | Admin session reads in SvelteKit happen via a direct Postgres connection (e.g., `postgres.js` or `pg`) — FastAPI is read-only API, not an auth server |
| SvelteKit form action → FastAPI write | POSTing admin mutations through FastAPI rather than direct DB | FastAPI is read-only per CLAUDE.md. Admin mutations (pipeline triggers, people edits) must go SvelteKit → DB directly, or SvelteKit → new FastAPI write endpoints explicitly added for admin use |
| cookies.set() in hooks vs. action | Setting session cookie in login `+page.server.ts` action but reading it in hooks before action runs | Cookie set in an action is available on the _next_ request. The hooks run before the action. Newly set cookies are not visible in the same request's hook. |
| subprocess env vars | Passing `ANTHROPIC_API_KEY` as subprocess env — not inheriting parent env | Explicitly pass required env vars to the subprocess `env` dict; do not assume child inherits parent's environment on all platforms |
| FastAPI admin endpoints | Adding `/admin/` FastAPI routes accessible without auth | Any FastAPI routes added for admin must validate auth independently — FastAPI does not share SvelteKit session state |

---

## Security Mistakes

Admin-specific security issues for this project.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging raw passwords in error handlers | Password exposed in server logs or crash dumps | Catch auth errors before any string containing the password reaches a logger |
| Hardcoding session secret in source code | Secret committed to public GitHub repo; all sessions compromised | Session secret from `$env/static/private` (not PUBLIC_), rotated via env var |
| `PUBLIC_FASTAPI_BASE_URL` instead of private env var | FastAPI origin exposed in browser; admin URL discoverable | Already a project constraint — enforce it for any new admin API routes too |
| Admin credentials in `.env` committed to repo | Credentials in public GitHub history | `.env` is in `.gitignore`; admin credentials only in Digital Ocean App Platform env vars |
| Session cookie without `secure: true` in production | Cookie transmitted over HTTP; interceptable | SvelteKit auto-sets `secure: true` in production; verify it is not overridden |
| No session expiry | Stolen session token valid indefinitely | Set `Max-Age` on session cookie (e.g., 8 hours); enforce expiry server-side on session table row |

---

## "Looks Done But Isn't" Checklist

- [ ] **Auth guard:** `hooks.server.ts` exists and protects `/admin/*` — verify it also protects any `+server.ts` API endpoints under `/admin/` by hitting them directly with no cookie
- [ ] **Login page:** Submitting login form with wrong credentials shows an error message, not a blank page or unhandled 500
- [ ] **Logout:** After logging out, the session cookie is cleared AND the session row in the DB is deleted (not just cookie cleared client-side)
- [ ] **BODY_SIZE_LIMIT:** Set to `10M` or higher in DO App Platform env vars — test by uploading a 1.5MB PDF
- [ ] **ORIGIN env var:** Set in DO App Platform for the SvelteKit service — test by submitting the login form in the deployed environment (not just loading the page)
- [ ] **Pipeline job recovery:** After simulating a server restart with a job in `running` status, verify the stuck job is transitioned to `failed` on next server start
- [ ] **Concurrent run guard:** Submit the same pipeline run twice in quick succession — verify only one run is started and the second is rejected
- [ ] **Subprocess unbuffered:** Verify `PYTHONUNBUFFERED=1` is in the subprocess environment — check that log lines appear in real time, not in a burst at the end
- [ ] **PDF validation:** Upload a `.pdf`-named HTML file — verify it is rejected at the magic byte check, not passed to the pipeline
- [ ] **Temp file cleanup:** After a failed ingest, verify no orphaned file remains in `pending/`

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Stuck `running` jobs after restart | LOW | SQL update: `UPDATE pipeline_runs SET status='failed', failure_reason='interrupted' WHERE status='running' AND heartbeat_at < NOW() - interval '5 min'` |
| Session loop (infinite 302) | LOW | Clear all cookies for the domain in browser DevTools; fix the hooks exclude-list in code |
| ORIGIN CSRF 403 at login | LOW | Add `ORIGIN` env var to DO App Platform; redeploy |
| BODY_SIZE_LIMIT blocking uploads | LOW | Add `BODY_SIZE_LIMIT=10M` env var; redeploy |
| Temp files accumulating | LOW | Manual delete from `pending/` directory; add startup cleanup routine |
| Concurrent runs corrupted state | MEDIUM | Identify the two conflicting `pipeline_run` IDs; manually set the earlier one to `failed`; re-run the step |
| Job state lost to memory (restart) | MEDIUM | Check DB for last `pipeline_runs` row; determine actual step status; resume from DB state |
| HTTP timeout killed visible action but subprocess still running | MEDIUM | Check DB for `running` pipeline_run; add polling endpoint to expose its status; wait for completion |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| V1: Infinite redirect loop | Auth foundation | Hit `/admin/login` unauthenticated → expect 200 |
| V2: Session cookie attributes | Auth foundation | Check DevTools Application tab for HttpOnly, SameSite=Lax |
| V3: Timing-safe credential compare | Auth foundation | Code review: no `===` on raw password |
| V4: Stateless session (no invalidation) | Auth foundation | Log out, replay captured cookie value → expect 401 |
| V5: Layout-only auth guard | Auth foundation | Hit `/admin/api/...` endpoint directly without session cookie → expect 401 |
| V6: App.Locals not typed | Auth foundation | TypeScript compile in strict mode passes with no implicit any on locals |
| V7: ORIGIN env var missing | Deployment phase | Submit login form on staging → expect 200, not 403 |
| V8: Stuck running jobs after crash | Pipeline runner | Simulate crash with running job → verify recovery on restart |
| V9: Subprocess stdout buffering | Pipeline runner | Verify log lines appear incrementally, not in a burst |
| V10: BODY_SIZE_LIMIT | File upload phase | Upload 1.5MB PDF → expect success, not 413 |
| V11: PDF MIME validation | File upload phase | Upload HTML file named .pdf → expect rejection |
| V12: Temp file accumulation | File upload phase | Fail ingest mid-way → verify pending/ is cleaned up |
| V13: Concurrent run conflict | Pipeline runner | Submit run twice fast → second submit returns error |
| V14: In-memory job state | Pipeline runner | Restart server mid-run → status recoverable from DB |
| V15: HTTP timeout on blocking action | Pipeline runner | Start parse step → verify action returns immediately; status polled separately |

---

## Critical Pitfalls — v1.0 Pipeline and Parsing (Preserved)

---

### Pitfall C1: Retrying Structural LLM Failures Treats Them as Transient

**What goes wrong:** Naive retry logic catches every LLM failure and resubmits the same prompt. When the failure is structural — the prompt is ambiguous, the schema is incompatible with the model's output style, or the input is too large — every retry produces the same bad output or valid-looking JSON with hallucinated values. The pipeline reports success. Downstream rows are silently corrupted.

**Why it happens:** Engineers borrow retry patterns from HTTP networking (where failures are mostly transient). LLM failures have four distinct categories that need different responses: transient infrastructure errors (rate limits, timeouts — safe to retry), prompt-induced failures (same output every time — fix the prompt), schema mismatch (structural incompatibility — fix the schema), and context window overflow (input too large — chunk differently). A single catch-and-retry branch conflates all four.

**How to avoid:**
- Classify failures before deciding to retry. HTTP 429 / 503 → retry with backoff. HTTP 400 / 422 / JSON parse error → log, alert, stop.
- Validate LLM output against a strict Pydantic schema at the pipeline boundary. A valid JSON envelope that fails schema validation is a structural failure, not a transient one.
- Never retry more than 2 times on the same prompt+input combination. On the second failure, write a `pipeline_run_step` error record and halt that step for manual review.

**Warning signs:** Retry rate on the Parse step consistently above 5%; utterance counts per argument vary wildly across reruns; speaker names in the DB that do not match any known pattern.

**Phase to address:** Pipeline Steps (Parse, Resolve).

---

### Pitfall C2: Pre-2004 Transcripts Use "QUESTION" Instead of Justice Names

**What goes wrong:** The Court's policy until October Term 2003 was to label all Justice speech as "QUESTION" rather than using the Justice's name. A parsing strategy that assumes speaker labels are names will correctly attribute post-2004 arguments and silently fail for everything before 2004.

**How to avoid:** Identify transcript era at the Ingest step. Pre-2004 format requires a separate parsing strategy. Project scope explicitly defers pre-2000 transcripts — enforce a guard at Ingest that rejects any transcript identified as pre-2004 with a clear error.

**Warning signs:** Resolve step finds a raw speaker name of "QUESTION" or "Q" in the utterance table.

**Phase to address:** Pipeline Step 1 (Ingest) and Step 2 (Parse).

---

### Pitfall C3: Chunking a Transcript Breaks Speaker Turn Continuity

**What goes wrong:** Splitting transcripts into fixed-size chunks for LLM processing creates chunk boundaries that cut through a speaker's utterance. The LLM invents a speaker attribution or assigns the fragment to the previous speaker it can infer.

**How to avoid:** Chunk on speaker-turn boundaries, not character count. Add 2–3 turn overlap between chunks. For typical SCOTUS transcripts (post-2004, 60–100 pages), a single modern LLM with a 200K+ context window can often process the whole transcript without chunking.

**Warning signs:** Utterance count from a re-run differs from the prior run by more than 5%; utterances with no speaker label or with speaker label "continued."

**Phase to address:** Pipeline Step 2 (Parse).

---

### Pitfall C4: Speaker Resolution Fails on Surname-Only and Role-Only Labels

**What goes wrong:** Simple string matching fails to resolve inconsistent speaker labels ("MR. BOPP", "GENERAL PRELOGAR", "CHIEF JUSTICE") to people records. LLM-based resolution hallucinates confident matches for ambiguous names.

**How to avoid:** Use case metadata (term year, docket number, counsel of record) as context for every resolution call. Maintain a canonical `speaker_alias` table. When LLM resolution is below confidence threshold, write `needs_review`. Never allow Resolve to create new person records without human approval.

**Warning signs:** Duplicate person records with names differing only in middle initial; single argument showing two person_ids for the same Justice.

**Phase to address:** Pipeline Step 3 (Resolve).

---

### Pitfall C5: Consolidated Cases Assumed to Have One Docket Number

**What goes wrong:** A pipeline that creates one `argument` record per PDF and one `case` record per docket number cannot correctly represent consolidated cases (approximately 10–15% of argued cases in any given term).

**How to avoid:** Design the `argument` ↔ `case` relationship as many-to-many from the start. (Already implemented in v1.0 schema.)

**Phase to address:** Schema design (v1.0 — resolved).

---

## Moderate Pitfalls — v1.0 (Preserved)

### M1: Re-Arguments Treated as Duplicate Ingests
Deduplication key for `argument` should be `(case_id, argument_date)`, not just `case_id`. Schema correctly places utterances under `argument` records.

### M2: Stage Direction Lines Incorrectly Parsed as Utterances
Include explicit prompt instructions for parenthetical stage directions; validate that utterances of type `speech` have non-null speakers.

### M3: SvelteKit SSR Fetch vs. Browser Fetch CORS Confusion
Configure FastAPI `CORSMiddleware` explicitly; never use `allow_origins=["*"]` in production; test client-side navigation separately from SSR.

### M4: PDF Extraction Reading Order Mangled by Layout
Use `pdfplumber` in layout mode; strip page headers/footers before LLM processing.

### M5: LLM Output Schema Version Not Tracked
Store `prompt_version` and `schema_version` on every `pipeline_run` record.

### M6: Oyez API Rate Limits and Availability Are Not Guaranteed
Treat Oyez responses as cacheable enrichment data; Enrich step must be re-runnable independently.

### M7: Apolitical Framing Broken by Asymmetric Bio Depth
Define bio schema (fields, character limits) before building the Enrich step; every person record has the same fields.

---

## Sources

**v1.1 research (2026-06-15):**
- [Protected Routes in SvelteKit — gebna.gg](https://gebna.gg/blog/protected-routes-svelte-kit)
- [Session cookies in SvelteKit — Lucia Auth](https://lucia-next.pages.dev/sessions/cookies/sveltekit)
- [Fixing infinite redirect loops in SvelteKit — khromov.se](https://snippets.khromov.se/fixing-infinite-redirect-loops-in-sveltekit-applications/)
- [Auth — SvelteKit Official Docs](https://svelte.dev/docs/kit/auth)
- [Hooks — SvelteKit Official Docs](https://svelte.dev/docs/kit/hooks)
- [Node servers (adapter-node) — SvelteKit Official Docs](https://svelte.dev/docs/kit/adapter-node)
- [BODY_SIZE_LIMIT issue — SvelteKit GitHub #9475](https://github.com/sveltejs/kit/issues/9475)
- [Form actions — SvelteKit Official Docs](https://svelte.dev/docs/kit/form-actions)
- [SvelteKit Form Example with 10 Mistakes to Avoid — Rodney Lab](https://rodneylab.com/sveltekit-form-example-with-10-mistakes-to-avoid/)
- [External types in app.d.ts — SvelteKit GitHub Discussion #3772](https://github.com/sveltejs/kit/discussions/3772)
- [asyncio subprocess orphan process — CPython Issue #114177](https://github.com/python/cpython/issues/114177)
- [Python subprocess.TimeoutExpired — Python Docs](https://docs.python.org/3/library/subprocess.html)
- [SvelteKit Streaming: The Complete Guide — Stanislav Khromov](https://khromov.se/sveltekit-streaming-the-complete-guide/)
- [File upload vulnerability: MIME type bypass — Sourcery](https://www.sourcery.ai/vulnerabilities/file-upload-content-type-bypass)
- [filetype library — PyPI](https://pypi.org/project/filetype/)
- [DigitalOcean App Platform domain management](https://docs.digitalocean.com/products/app-platform/how-to/manage-domains/)
- [Building Real-time SvelteKit Apps with SSE — sveltetalk.com](https://sveltetalk.com/posts/building-real-time-sveltekit-apps-with-server-sent-events)

**v1.0 research (2026-06-11):**
- [LLMs for Structured Data Extraction from PDFs — Unstract](https://unstract.com/blog/comparing-approaches-for-using-llms-for-structured-data-extraction-from-pdfs/)
- [CORS issues during SSR — SvelteKit GitHub Discussion #9295](https://github.com/sveltejs/kit/discussions/9295)
- [Idempotency in Data Pipelines — Prefect](https://www.prefect.io/blog/the-importance-of-idempotent-data-pipelines-for-resilience)
- [pdfplumber — GitHub](https://github.com/jsvine/pdfplumber)

---
*Pitfalls research for: SCOTUS Chat admin interface (v1.1) and pipeline (v1.0)*
*v1.1 researched: 2026-06-15*
*v1.0 researched: 2026-06-11*
