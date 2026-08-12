# Phase 46: Dev Environment Reliability - Context

**Gathered:** 2026-08-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the local dev environment reliable now that the operator has migrated to
a machine with Windows admin access — removing the original "must work
without admin rights" constraint that shaped the current portable-Postgres +
Windows-venv-via-WSL-interop setup. Two concrete problems drive this phase:

1. A data-loss bug discovered during Phase 45: invoking `pytest` with
   explicit paths under `api/tests/`/`pipeline/tests/` skips the root
   `tests/conftest.py` `TEST_DATABASE_URL` redirect, silently running
   "DB-gated" tests against the live shared dev database. It wiped the dev
   DB to 0 rows twice during Phase 45's own execution.
2. General dev-stack friction: today's session lost real time to a Windows
   process serving port 8000 that no Windows process API (`tasklist`,
   `Get-Process`) could identify or kill, plus noisy `--reload` churn from
   stray worktree directories, plus manual `pg_ctl`/`Start-Process` juggling
   to bring the stack up.

Scope for this phase (operator-confirmed): **fix the data-loss bug and
ship basic dev-stack reliability** — not a from-scratch infrastructure
rewrite (no Docker, no CI changes, no docs restructuring beyond what's
needed to reflect the new setup).

</domain>

<decisions>
## Implementation Decisions

### Where the dev stack runs
- **D-01:** Move the Python (FastAPI/uvicorn) and Node (SvelteKit/vite)
  processes to run WSL-native instead of via the Windows-venv-through-WSL-
  interop path used today. WSL already has Node available natively (via
  nvm, confirmed during discussion: `/home/jason/.nvm/versions/node/v24.18.0/bin/node`).
  A fresh WSL-native Python venv will need to be created for the API/pipeline.
  — **Reversibility:** costly — **rationale:** touches `scripts/dev-start.ps1`,
  every doc/comment referencing `.venv/Scripts/python.exe`, and however
  `CLAUDE.md`/README currently describe running the stack. Reverting means
  re-establishing the Windows venv and re-authoring the start script back to
  PowerShell-only.
- **Why:** today's session hit a concrete, costly failure mode from the
  Windows/WSL boundary — a live server on port 8000 that answered HTTP
  requests correctly but had no discoverable owning process from either
  `tasklist.exe` or `Get-Process` (even `Get-NetTCPConnection`'s own
  `OwningProcess` field pointed at a PID that didn't exist). Running
  everything WSL-native means Claude Code (and the operator, from a WSL
  shell) can use plain `ps`/`kill` and get consistent answers.

### Postgres
- **D-02:** Use the already-installed Windows Postgres 18 service
  (`postgresql-x64-18`, confirmed present but stopped via
  `Get-Service -Name '*postgres*'`) instead of the project's portable
  `data/pgsql` + `pg_ctl` setup. Connect to it from WSL-native code over the
  network (not via the portable binaries).
  — **Reversibility:** one-way for the *portable-Postgres data* —
  **rationale:** whatever's currently in `data/pgdata` is disposable dev
  fixture data anyway (the project has `POST /api/admin/dev/reset-to-fixture`
  specifically to reseed it from scratch), so there's no real migration to
  perform — just point `DATABASE_URL`/`TEST_DATABASE_URL` at the new
  service and reseed. The portable `data/pgsql`/`data/pgdata` directories
  can be deleted once the new service is confirmed working.
- **Why:** the portable pg_ctl approach existed specifically to avoid
  needing admin rights to install a real Postgres service. That constraint
  is gone. A real Windows service means normal `Services.msc`/`net start`
  lifecycle instead of manually running `pg_ctl start -D ...` every session.
- **Technical note for the planner (Claude's own investigation, not asked
  of the operator):** this machine's WSL2 is in default NAT networking mode
  (confirmed via `/etc/resolv.conf`'s distinct nameserver IP, not a
  mirrored-mode passthrough). WSL-native code reaching a Windows-hosted
  service must use the Windows host's IP (visible as the `nameserver` line
  in `/etc/resolv.conf` from inside WSL, e.g. `172.26.32.1` at investigation
  time — this can change across reboots unless pinned), NOT `localhost`.
  The Postgres service will also need `listen_addresses` widened from the
  default `localhost`-only and a `pg_hba.conf` rule permitting the WSL
  subnet, or connections from WSL will be refused even once the service is
  running.
- **Test DB:** keep using a distinct database name on the same service for
  `TEST_DATABASE_URL` (matching the existing `settings.test_database_url`
  pattern) — no separate test-only Postgres instance needed.

### Scope ceiling
- **D-03:** This phase fixes the pytest DB-isolation bypass definitively
  (must work correctly regardless of how pytest is invoked — bare, explicit
  single-file path, or any subset) and delivers a single reliable start/stop
  entry point for the three services (Postgres service start/verify,
  uvicorn, vite) with real health checks — not a redesign of the test suite,
  not new CI integration, not containerization.
  — **Reversibility:** reversible

### Claude's Discretion
- Exact mechanism for the pytest isolation fix (`pytest_configure` hook vs.
  duplicating the redirect into every `conftest.py` vs. a fail-closed guard)
  — investigate during planning/research and pick the most robust one; the
  operator only fixed the *outcome* requirement ("must not silently hit the
  live dev DB regardless of invocation"), not the mechanism.
- Whether the new start/stop entry point is a rewritten `dev-start.ps1`
  invoked from Windows, a new WSL-native shell script, or both (a thin
  Windows wrapper that shells into WSL) — driven by D-01 (WSL-native
  processes) but the exact script shape/name is an implementation detail.
- Whether to delete the old portable `data/pgsql`/`data/pgdata` directories
  as part of this phase or just leave them unused — low stakes either way,
  default to deleting them once the new Postgres service is confirmed
  working, to avoid two competing "how do I start Postgres" stories in the
  repo.

### Folded Todos
- **`2026-08-12-pytest-explicit-paths-bypass-db-isolation.md`** — "pytest
  explicit-path invocations bypass DB test isolation and can wipe the dev
  DB." This is the priority item for this phase (D-03) and the todo's own
  "Suggested fix" options (move the redirect into a `pytest_configure` hook,
  or duplicate it per-directory, or fail closed) are exactly the mechanism
  Claude has discretion over above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Dev-isolation bug (the priority fix)
- `.planning/todos/pending/2026-08-12-pytest-explicit-paths-bypass-db-isolation.md` — full root-cause narrative, the observed `AssertionError` from `tests/conftest.py`'s own leak-detection guard, and candidate fix mechanisms.
- `tests/conftest.py` — the root-level conftest that redirects `DATABASE_URL` → `TEST_DATABASE_URL` and runs the `pytest_sessionstart`/`pytest_sessionfinish` dev-DB row-count guard. This is the mechanism that needs to fire unconditionally.
- `api/tests/conftest.py` — the `api/tests`-local conftest with its own `_db_configured()` guard and `_api_lifespan` autouse fixture; currently has no awareness of the root conftest's redirect.
- `pytest.ini` — `testpaths = tests pipeline/tests api/tests`; this is why bare `pytest` (no path args) works correctly but explicit paths don't.
- `api/core/config.py` — `Settings.database_url` / `Settings.test_database_url` fields (env-var driven via `pydantic-settings`, reads `.env` directly).

### Current dev-stack setup (what's being replaced/hardened)
- `scripts/dev-start.ps1` — current Windows-only start script: portable `pg_ctl` start, `alembic upgrade head`, then backgrounds `uvicorn` and `npm run dev` as PowerShell jobs.
- `.env` / `app/.env` — `DATABASE_URL`, `ENVIRONMENT`, and other required settings (see `api/core/config.py`'s `Settings` class for the full required-field list and inline comments on what SvelteKit vs. Python each read).
- `data/pgsql/`, `data/pgdata/` — the portable Postgres binaries + data directory being replaced by the installed Windows Postgres 18 service per D-02.
- `api/routers/admin_dev.py` / `api/services/admin_dev.py` — the existing `POST /api/admin/dev/reset-to-fixture` dev-only endpoint (Phase 43) that reseeds all fixture data through the real import path; this is how the new Postgres service gets its dev data populated, no manual migration needed.

### Project-level constraints (from PROJECT.md/CLAUDE.md — unaffected by this phase)
- `CLAUDE.md` — "Alembic is the sole DDL authority" and "asyncpg requires `statement_cache_size=0` behind PgBouncer" hard constraints still apply regardless of which Postgres instance is used.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `POST /api/admin/dev/reset-to-fixture` (Phase 43) — already the correct way to populate a fresh Postgres instance with dev data; no new seeding mechanism needed once the new service is reachable.
- WSL-native Node via nvm is already installed and working (`/home/jason/.nvm/versions/node/v24.18.0/bin/node`) — no new Node install needed for the WSL-native move.

### Established Patterns
- `tests/conftest.py`'s `_REAL_DATABASE_URL` capture + `pytest_sessionstart`/`pytest_sessionfinish` row-count guard is the *intended* safety net for exactly this class of bug — it just has the same single-point-of-collection-failure as the redirect itself. Any fix should keep this guard working, not just the redirect.
- `api/core/database.py`'s lifespan-scoped engine creation (`engine`/`AsyncSessionLocal` are `None` until FastAPI's `lifespan()` runs) — relevant if the planner considers any ad-hoc DB connectivity checks in the new start script; a bare `from api.core.database import engine` won't work outside a running app, matching what Claude hit firsthand this session.

### Integration Points
- Whatever start script replaces/wraps `dev-start.ps1` needs to run Alembic migrations against the *new* Postgres service before starting uvicorn (same order as today's script).
- `uvicorn --reload`'s file-watcher noise from stray `.claude/worktrees/agent-*` directories (observed today, though those directories are normally transient/auto-cleaned) — worth an explicit `--reload-exclude` if the new start script still uses `--reload`.

</code_context>

<specifics>
## Specific Ideas

No specific UI/behavior requirements — this is pure dev-tooling. The
operator's concrete pain points from this session are the specifics:
1. Dev DB got wiped twice, losing seeded fixture data mid-work.
2. Couldn't tell what was actually running on port 8000; killing by PID
   failed silently.
3. Manual, multi-step process to bring the stack up at all.

</specifics>

<deferred>
## Deferred Ideas

- **Full stack rework** (containerization, CI integration, docs
  restructuring) — operator explicitly chose the narrower "fix the bug +
  basic reliability" scope over this. Could become its own future phase if
  the basic-reliability version still isn't enough.
- **Hybrid split (Windows for browser-facing, WSL for tooling)** — considered
  as an option but not chosen; operator picked the fuller WSL-native move
  instead.

### Reviewed Todos (not folded)
- `2026-08-12-speaker-popover-frontend-duplication-cleanup.md` — matched by generic keyword overlap only; this is a frontend code-quality item unrelated to dev-environment tooling. Stays pending for its own future pass.
- `2026-08-12-speakers-bench-classification-silent-fallback.md` — matched by generic keyword overlap only; an API behavioral edge case unrelated to dev-environment tooling. Stays pending.
- `2026-08-11-create-person-popover-side-and-selection.md` — matched by generic keyword overlap only (area: ui); unrelated to this phase. Stays pending.

</deferred>

---

*Phase: 46-dev-environment-reliability*
*Context gathered: 2026-08-12*
