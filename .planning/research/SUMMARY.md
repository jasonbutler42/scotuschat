# Research Summary: SCOTUS Chat v1.1 — Operator Admin Interface

**Domain:** Protected admin UI + background pipeline job coordination on existing SvelteKit + FastAPI app
**Researched:** 2026-06-15
**Confidence:** HIGH

---

## Executive Summary

SCOTUS Chat v1.1 adds a single-operator admin interface on top of a validated v1.0 stack. The goal is to make the existing Python pipeline operable from a browser: trigger ingest/parse/resolve steps, monitor their progress, review speaker resolution discrepancies, and maintain the people directory. The system has one operator, runs at most one pipeline job at a time, and has no concurrency or throughput requirements.

Recommended approach: stateless HMAC-signed session cookie for auth (no user DB, no Redis, no auth library), fire-and-poll for pipeline job execution (subprocess spawned from SvelteKit form action, client polls DB-backed status endpoint every 2.5s), and DigitalOcean Spaces for PDF storage (DO App Platform container filesystem is ephemeral).

Net-new additions: two npm packages (`bcryptjs`, `@types/bcryptjs`), one Python package (`boto3`), one Alembic migration (`admin_jobs` table), and new SvelteKit routes under `/admin/*`. No new services, no new infrastructure categories beyond Spaces.

---

## Recommended Stack

| Package | Layer | Purpose |
|---------|-------|---------|
| `bcryptjs@^2.4.3` | SvelteKit (`app/`) | Password hash comparison — pure JS, no native build friction |
| `@types/bcryptjs@^2.4.6` | SvelteKit dev | TypeScript types |
| `boto3@^1.34` | Python (api/pipeline) | Upload PDF to DO Spaces; fetch in pipeline ingest |

**Key rejections:**
- `@node-rs/argon2` — native binaries break SvelteKit production builds (confirmed GitHub issues through late 2024)
- All auth libraries (Auth.js, Better Auth, Lucia) — require DB-backed adapters; conflicts with Alembic-only DDL constraint
- Celery/Redis — new infra for a single-operator sequential tool; stdlib subprocess is sufficient
- SSE/WebSocket — overkill for one polling client watching sub-60s steps; `setInterval` polling is sufficient

Node stdlib handles the rest: `node:crypto` for HMAC signing, `node:fs/promises` for temp file writes, Python `asyncio.create_subprocess_exec` (3.12 stdlib) for non-blocking subprocess execution.

---

## Table Stakes Features

**Must have (P1 — launch blockers):**
1. Auth: login form, HMAC cookie, `hooks.server.ts` guard, logout
2. Pipeline trigger: tabbed widget — URL input + file upload in one form
3. Step-by-step status cards (Ingest / Parse / Resolve) with status badges + error display
4. Auto-advance when no discrepancies; pause-for-review when discrepancies exist
5. Inline participant review with alias auto-save (writes to `speaker_alias`)
6. People directory list and edit form (name, role, bio text, photo URL, tenure dates)

**Should have (P2 — after core stable):**
- Unresolved count badge, photo URL preview, pipeline run history panel, "Create new person" inline modal

**Defer to v1.2+:** Automated enrichment (Oyez/FJC API), batch ingestion

**Hard anti-features (never build):**
- SSE log streaming — PgBouncer transaction mode makes this structurally difficult
- Celery/Redis queue — two new infra components for one operator
- Bulk import — obscures per-argument discrepancy review, which is inherently sequential
- Inline utterance editing — violates the immutable-PDF / regenerate-from-source principle
- RBAC, analytics dashboard — no beneficiary for single operator

---

## Architecture

### Pattern
Protected `/admin/*` route tree on v1.0's SvelteKit server → FastAPI → PostgreSQL pattern. `hooks.server.ts` handle function is the sole auth checkpoint — fires before every request including `+server.ts` API endpoints. Python subprocess spawned from SvelteKit Node process; FastAPI gains `api/routers/admin.py` (`X-Admin-Token` auth); new `admin_jobs` table (migration 0003) tracks UI-level job coordination separately from pipeline-owned `pipeline_runs`.

### New Components
| Component | Purpose |
|-----------|---------|
| `src/hooks.server.ts` | HMAC session validation; fires before every request |
| `src/routes/admin/+layout.server.ts` | Belt-and-suspenders redirect guard for page routes |
| `src/routes/admin/run/+page.server.ts` | `startRun` / `approveContinue` form actions; spawns Python subprocess |
| `src/routes/admin/api/run/[id]/+server.ts` | JSON polling target; client polls every 2.5s |
| `api/routers/admin.py` | New FastAPI router; `admin_jobs` and people CRUD; `X-Admin-Token` protected |
| `alembic/versions/0003_add_admin_jobs.py` | `admin_jobs` table |
| DigitalOcean Spaces (boto3) | Persistent PDF storage |

### DO App Platform Subdomain
Add `admin.scotuschat.com` as an ALIAS entry in the app spec `domains:` array alongside `scotuschat.com`. DO provisions TLS for both. Admin security is entirely in `hooks.server.ts`, not at the network layer.

### `admin_jobs` vs `pipeline_runs`
`pipeline_runs` is pipeline provenance (step, argument, strategy, status — the PIPE-11 policy). `admin_jobs` is the web UI's coordination record: which step is active, whether review is needed, cross-step run ID linkage. Do not repurpose `pipeline_runs` — a new Alembic migration is required.

### Build Order
Schema + FastAPI router → Auth → Pipeline runner → People editor → DO deployment config.

---

## Critical Pitfalls

### Auth (address before building any admin page)
1. **Infinite redirect loop** — explicitly exclude `/admin/login` from the auth guard; test unauthenticated hit expects 200
2. **Layout-only guard bypasses `+server.ts` endpoints** — `hooks.server.ts` is mandatory; layout guards alone do not protect API endpoints
3. **Session cookie missing `httpOnly`/`sameSite`** — always `httpOnly: true`, `sameSite: 'lax'`, `secure: true`; use `domain: '.scotuschat.com'` for subdomain sharing
4. **`App.Locals` untyped in `app.d.ts`** — declare `admin: boolean` before writing hooks; ES `import` in `app.d.ts` converts it to a module and silently breaks all type inference
5. **`ORIGIN` env var missing on DO → CSRF 403 at login (silent, not obvious)** — set `ORIGIN`, `PROTOCOL_HEADER`, `HOST_HEADER` in DO App Platform env vars; test form submission on staging

### Pipeline Runner
6. **Blocking subprocess causes HTTP timeout** — fire subprocess, return `{ job_id }` immediately; never `await` completion; this is the foundational pattern
7. **Stuck `running` jobs after server crash** — add `heartbeat_at` to `admin_jobs`; startup recovery query transitions stale `running` → `failed`
8. **In-memory job state lost on container restart** — all state in DB; no `Map` or module-level cache; DO restarts on every deploy

### File Upload
9. **`BODY_SIZE_LIMIT` default 512KB blocks real SCOTUS PDFs (200KB–2MB)** — set `BODY_SIZE_LIMIT=10M` in DO App Platform
10. **MIME validation trusts client header** — check magic bytes server-side (`%PDF-` = hex `25 50 44 46 2D`)

---

## Roadmap Implications

| Phase | Focus | Research needed? |
|-------|-------|-----------------|
| 5 | Schema + FastAPI admin foundation (`admin_jobs` migration, `admin.py` router) | No |
| 6 | Auth layer (`hooks.server.ts`, login/logout, HMAC cookie) | No |
| 7 | Pipeline runner (PDF upload to Spaces, fire-and-poll, step review UI) | Yes — multiple interacting failure modes |
| 8 | People editor + resolve review (directory, edit form, per-argument review) | No |
| 9 | DO App Platform deployment (subdomain, env vars, smoke test) | No |

**Phase ordering rationale:**
- Phase 5 before 6: FastAPI admin router must exist before SvelteKit calls it
- Phase 6 before 7: All pipeline runner routes are under `/admin/*`; auth must be verified first
- Phase 7 before 8: Participant review data only exists after a pipeline run completes resolve
- Phase 9 last: Deployment config depends on all feature env vars being finalized; CSRF only testable on deployed environment

### Research Flags
- Phase 7 (Pipeline runner): recommend `/gsd-plan-phase --research` — multiple interacting failure modes between subprocess management, job state machine, and Spaces upload
- Phases 5, 6, 8, 9: standard patterns, skip research

---

## Open Questions for Planning

- DO Spaces bucket name, region, and credential env var names — decide in Phase 7 planning and add to env var checklist
- Stateless HMAC cookie tradeoff (cannot revoke individual sessions without rotating `SESSION_SECRET`) — document explicitly in Phase 6 plan
- Python interpreter path in DO App Platform container — resolve in Phase 7 planning
- `admin.scotuschat.com` DNS entry — must be created before Phase 9; flag as deployment prerequisite

---

*Synthesized from STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md*
*Date: 2026-06-15*
