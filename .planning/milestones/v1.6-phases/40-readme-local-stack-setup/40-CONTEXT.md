# Phase 40: README - How to Start the Local Stack - Context

**Gathered:** 2026-07-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Expand `README.md` so a contributor or returning operator can go from a clean checkout to a running local PostgreSQL, FastAPI, and SvelteKit stack without relying on memory or git history. Preserve existing attribution. This is documentation and environment-example alignment only.

</domain>

<decisions>
## Implementation Decisions

### Supported Platforms
- **D-01:** Windows-first. Label Windows as verified and macOS/Linux commands as equivalent guidance.
- **D-02:** Give equal Windows coverage to portable PostgreSQL under `data/pgsql` plus `data/pgdata` and PostgreSQL managed as a Windows service.
- **D-03:** Give macOS/Linux runnable project commands for venv, dependencies, migrations, FastAPI, and SvelteKit. Assume externally managed PostgreSQL; omit package-manager-specific PostgreSQL recipes.

### Primary Startup Path
- **D-04:** After one-time setup, lead with `./scripts/dev-start.ps1` for portable PostgreSQL, followed by manual commands.
- **D-05:** The script remains start-time only: start portable PostgreSQL, migrate, and launch FastAPI/SvelteKit. It does not install, initialize, configure env files, or import data.
- **D-06:** System-PostgreSQL Windows users run FastAPI and SvelteKit in two visible terminals.
- **D-07:** Verify FastAPI `/health`, public UI, admin login, and expected ports.

### Clean-Checkout Depth
- **D-08:** Required setup ends with an empty but usable stack: role/database created, schema migrated, services healthy, UI reachable, and admin login working. Content import is optional.
- **D-09:** Include complete bootstrap commands: verify runtimes, create `.venv`, install Python dependencies, use `npm ci`, configure env files, create the database, and migrate.
- **D-10:** Fully document portable PostgreSQL from a clean checkout: obtain/extract into `data/pgsql`, initialize `data/pgdata`, start it, and create the role/database expected by `DATABASE_URL`.
- **D-11:** Include optional `scripts/provision_test_db.py` and first-content import pointers.

### Environment Files
- **D-12:** Root `.env` is for Python/FastAPI/PostgreSQL; `app/.env` is for SvelteKit. Identify shared matching values such as `ADMIN_TOKEN`.
- **D-13:** Provide PowerShell and POSIX commands generating strong `ADMIN_TOKEN` and `SESSION_SECRET`; users choose local admin credentials.
- **D-14:** Group variables by minimum stack, optional LLM parsing, test DB, object storage, and deployment-only use.
- **D-15:** Keep root `.env.example` backend-focused and add `app/.env.example` with `FASTAPI_BASE_URL`, `ADMIN_TOKEN`, `SESSION_SECRET`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD` placeholders.

### the agent's Discretion
- README ordering, copy, and troubleshooting wording.
- Exact safe PowerShell/POSIX secret-generation commands.
- The verified current CLI command used as a brief first-content pointer.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/ROADMAP.md` - Phase 40 goal and success criteria.
- `.planning/REQUIREMENTS.md` - DOCS-01.

### Existing setup assets
- `README.md` - Attribution content that must remain.
- `scripts/dev-start.ps1` - Portable quick start.
- `.env.example` - Current combined example to align.
- `scripts/provision_test_db.py` - Optional test DB provisioning.

### Runtime contracts
- `app/package.json` - Frontend commands.
- `requirements.txt` and `requirements-dev.txt` - Python dependencies.
- `api/main.py` - Uvicorn entry point and `/health`.
- `api/core/config.py` - Backend env loading.
- `CLAUDE.md` - Server-only `FASTAPI_BASE_URL` constraint.

No external specs or ADRs were referenced.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/dev-start.ps1` implements the portable Windows quick start.
- `scripts/provision_test_db.py` safely provisions `scotus_test`.
- `api/main.py` exposes `/health`.

### Established Patterns
- Python loads root `.env`; SvelteKit `$env/static/private` loads in the `app` runtime context.
- Alembic is the sole schema authority.
- API URLs, admin credentials, and tokens stay server-only.

### Integration Points
- `README.md` gains prerequisites, env setup, DB bootstrap, startup, verification, optional setup, and troubleshooting while retaining attribution.
- `.env.example` is aligned for backend use; `app/.env.example` documents SvelteKit settings.
- Portable instructions match `data/pgsql/bin` and `data/pgdata` used by the script.

</code_context>

<specifics>
## Specific Ideas

- Be candid about Windows verification versus equivalent POSIX guidance.
- Keep both Windows PostgreSQL arrangements first-class.
- Successful setup includes a working admin login.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 40-readme-local-stack-setup*
*Context gathered: 2026-07-13*
