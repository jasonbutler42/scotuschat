# Phase 5: Admin Foundation - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 5 delivers two pieces of prerequisite infrastructure for Phases 6 and 7:

1. **Alembic migration 0003** — creates the `admin_jobs` table with all columns Phase 7 needs
2. **`api/routers/admin.py`** — FastAPI admin router mounted at `/api/admin`, with a throwaway X-Admin-Token auth dependency and one health route

No SvelteKit changes. No operator-observable features. This phase exists solely so Phase 6 (auth) and Phase 7 (pipeline runner) have a schema and a router to build on.

</domain>

<decisions>
## Implementation Decisions

### admin_jobs Schema

- **D-01:** Migration 0003 lands the **full schema** — all columns Phase 7 needs. Phase 7 does not run a migration 0004 for this table.
- **D-02:** `argument_id` is a **nullable FK** to the `arguments` table. NULL until ingest creates the argument row. FK enforces referential integrity once populated.
- **D-03:** Discrepancy data lives in a **JSONB column (`discrepancies`)** on `admin_jobs` — not a separate table. Read as a batch during fire-and-poll; no per-row query needed.
- **D-04:** Status enum is **`pending / running / paused / completed / failed`**. `paused` = UI waiting for operator review. Does NOT mirror `pipeline_runs.status` (which uses `needs_review`) — different semantics, different tables.
- **D-05:** `current_step` enum is **`ingest / parse / resolve`**. NULL = not started yet. No `not_started` sentinel — NULL + `status = 'pending'` is unambiguous.
- **D-06:** Input source stored as **two nullable columns**: `pdf_url` (the URL the operator entered; NULL for file uploads) and `spaces_key` (the DO Spaces object key after ingest stores the file; NULL until ingest completes). Preserves full provenance.
- **D-07:** Full column list for migration 0003:
  - `id` — PK (integer or UUID — researcher to pick consistent with existing tables)
  - `status` — enum: pending / running / paused / completed / failed; default pending; not null
  - `current_step` — nullable enum: ingest / parse / resolve
  - `argument_id` — nullable integer FK → arguments.id
  - `pdf_url` — nullable text
  - `spaces_key` — nullable text
  - `discrepancies` — nullable JSONB
  - `error_message` — nullable text
  - `created_at` — timestamp with timezone; default now(); not null
  - `updated_at` — timestamp with timezone; default now(); not null

### ORM Model

- **D-08:** Phase 5 **includes the SQLAlchemy ORM model** for `admin_jobs` in `api/models/models.py`. Migration and ORM class land together so Phase 7 can import `AdminJob` without any model work.

### FastAPI Admin Router

- **D-09:** Router prefix is **`/api/admin`** — unambiguous; avoids naming collision with SvelteKit's `/admin/*` page routes. SvelteKit calls `fetch(FASTAPI_BASE_URL + '/api/admin/...')`.
- **D-10:** **Single file** `api/routers/admin.py` — not a sub-package. Phase 7 can split into sub-routers if needed.
- **D-11:** Router includes **one health route**: `GET /api/admin/health` returns `{"status": "ok"}`. This is the smoke-test target for verifying the 401 dependency works before Phase 7 adds real routes.
- **D-12:** The **X-Admin-Token auth is a throwaway** — a FastAPI dependency that checks `X-Admin-Token == settings.ADMIN_TOKEN`. Phase 6 replaces it entirely with HMAC session cookie auth. No permanent dev bypass.

### Environment Variables

- **D-13:** Phase 5 introduces one new env var: **`ADMIN_TOKEN`** — added to `api/core/config.py` alongside `DATABASE_URL`. Phase 6 will add `SESSION_SECRET` alongside it.

### SvelteKit

- **D-14:** Phase 5 is **FastAPI-only** — zero SvelteKit changes. All `/admin` route files are Phase 6's responsibility.

### Test Coverage

- **D-15:** Phase 5 uses **smoke testing only** — no new test files. Verification: migration runs cleanly, `GET /api/admin/health` returns 401 without token and 200 with valid token. Automated tests for admin routes begin in Phase 6 (permanent cookie auth is the right surface to test).

### Claude's Discretion

- **Route stubs in Phase 5:** One health route (`GET /api/admin/health`) — chosen over zero routes so the 401 auth dependency can be smoke-tested without waiting for Phase 7 routes.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Architecture & Constraints
- `.planning/PROJECT.md` — Key Decisions table; pipeline-is-offline constraint; Alembic-is-sole-DDL-authority constraint; apolitical framing constraint
- `.planning/REQUIREMENTS.md` — Note on Phase 5 (pure infra, no REQ-IDs); v1.1 requirements for Phases 6–8 that this phase must not conflict with
- `.planning/ROADMAP.md` §Phase 5 — Success criteria (the exact three things that must be true)
- `.planning/STATE.md` §Accumulated Context — v1.1 architectural decisions: fire-and-poll pattern, admin_jobs separate from pipeline_runs, DO Spaces for PDF persistence, HMAC session cookie for Phase 6 auth, `BODY_SIZE_LIMIT` / `ORIGIN` env var blockers

### Existing Code to Extend
- `api/main.py` — Where admin router must be mounted (alongside cases/arguments/people routers)
- `api/core/config.py` — Where `ADMIN_TOKEN` env var must be added
- `api/models/models.py` — Where `AdminJob` ORM model must be added (Alembic is sole DDL authority — model must match migration exactly)
- `alembic/versions/0002_add_speaker_alias.py` — Nearest migration to follow for style/pattern
- `api/routers/people.py` — Nearest router to follow for style/dependency injection pattern

### Database
- `alembic/versions/` — Migration naming: next file is `0003_add_admin_jobs.py`
- `api/models/models.py` line 5 — Schema comment: "schema is managed exclusively via migrations in alembic/versions/" — do not call `Base.metadata.create_all`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `api/core/config.py` — `Settings` class (pydantic-settings); add `ADMIN_TOKEN: str` alongside existing `DATABASE_URL`
- `api/core/database.py` — lifespan context manager and `get_db` dependency; admin router uses the same `get_db` dependency for DB access
- `alembic/versions/0002_add_speaker_alias.py` — Migration style template: `upgrade()` / `downgrade()`, explicit `op.create_table()` with columns and FK constraints

### Established Patterns
- **Router registration:** `app.include_router(router)` in `api/main.py` — add admin router the same way
- **FastAPI dependency injection:** Existing routers use `Depends(get_db)` — X-Admin-Token auth should be a `Depends(verify_admin_token)` dependency on router-level (not middleware), so Phase 6 can swap the dependency without touching route definitions
- **Alembic sole DDL authority:** Never call `Base.metadata.create_all` — all schema changes through migrations only
- **asyncpg `statement_cache_size=0`** in `connect_args` (not top-level) — already in `api/core/database.py`; no change needed in Phase 5

### Integration Points
- `api/main.py` — include admin router (one line addition)
- `api/models/models.py` — add `AdminJob` ORM class and `AdminJobStatus` / `AdminJobStep` enums
- `api/core/config.py` — add `ADMIN_TOKEN` field to `Settings`
- `alembic/versions/` — new file `0003_add_admin_jobs.py`

</code_context>

<specifics>
## Specific Ideas

- The X-Admin-Token dependency should be at the **router level** (passed to `APIRouter(dependencies=[...])` or to each route), not as FastAPI middleware — this makes Phase 6's replacement surgical (swap the dependency, don't touch route signatures)
- `paused` status on `admin_jobs` is intentionally distinct from `needs_review` on `pipeline_runs` — they model different things; do not consolidate or alias them

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-admin-foundation*
*Context gathered: 2026-06-15*
