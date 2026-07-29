# Phase 40: README - How to Start the Local Stack - Research

**Researched:** 2026-07-13
**Domain:** Clean-checkout developer documentation for PostgreSQL, FastAPI, and SvelteKit
**Confidence:** HIGH for repository contracts; MEDIUM for cross-platform guidance pending a clean-checkout walkthrough

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

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

### Deferred Ideas (OUT OF SCOPE)

None - discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOCS-01 | A README documents how to start the full local stack (SvelteKit, FastAPI, Postgres) end to end | Verified startup entry points, environment boundaries, database bootstrap commands, service ports, health endpoint, admin-login prerequisites, and clean-checkout pitfalls are mapped below. [VERIFIED: `.planning/REQUIREMENTS.md`, repository inspection] |
</phase_requirements>

## Summary

Phase 40 should be planned as a documentation contract backed by three small alignment edits: expand `README.md`, make root `.env.example` backend-only and complete, add `app/.env.example`, and prevent a portable PostgreSQL extraction from dirtying the worktree. The current README contains attribution only, so that section must remain intact while setup material is added ahead of it. [VERIFIED: `README.md`, `.env.example`, `app/.gitignore`]

The repository already contains the runtime truth needed for the guide. `scripts/dev-start.ps1` starts portable PostgreSQL from `data/pgsql/bin`, migrates the root database, then launches FastAPI on port 8000 and SvelteKit on port 5173. It does not initialize PostgreSQL, create roles/databases, install dependencies, or create env files. Manual commands must mirror `uvicorn api.main:app --reload --port 8000`, `npm run dev`, and `alembic upgrade head`. [VERIFIED: `scripts/dev-start.ps1`, `api/main.py`, `app/package.json`, `alembic/env.py`]

The biggest planning risks are operational rather than architectural: `data/pgsql/` is currently unignored; the quick-start script resolves `alembic` and `uvicorn` from `PATH`, so the README must activate `.venv` before invoking it; the frontend and backend require separate env files; and `ADMIN_TOKEN` must match exactly in both. A final documentation walkthrough should exercise the Windows paths without mutating an existing database and should run link/command/static checks for equivalent POSIX instructions. [VERIFIED: `.gitignore`, `git check-ignore`, `scripts/dev-start.ps1`, env consumers under `app/src` and `api/core/config.py`]

**Primary recommendation:** Plan one documentation-and-env-alignment slice, with a required verification task that checks every documented command against the repository and walks both Windows PostgreSQL branches through the same health/admin acceptance checklist.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Local database bootstrap and schema | Database / Storage | Developer shell | PostgreSQL owns cluster/role/database state; Alembic is the repository's sole schema authority. [VERIFIED: `CLAUDE.md`, `alembic/env.py`] |
| Backend startup and health verification | API / Backend | Developer shell | Uvicorn serves `api.main:app`; FastAPI exposes `/health`. [VERIFIED: `api/main.py`] |
| Public UI and admin login | Frontend Server (SSR) | API / Backend | SvelteKit owns login/session handling and calls FastAPI server-side with a shared token. [VERIFIED: `app/src/hooks.server.ts`, `app/src/routes/admin/login/+page.server.ts`, server route imports] |
| Secret and environment setup | Developer shell | API / Backend and Frontend Server | Operators create two ignored env files; runtime consumers read private server-side variables. [VERIFIED: `api/core/config.py`, `app/.gitignore`, `$env/static/private` imports] |
| One-command recurring startup | Developer shell | All runtime tiers | `scripts/dev-start.ps1` coordinates portable PostgreSQL, migration, API, and UI after bootstrap. [VERIFIED: `scripts/dev-start.ps1`] |

## Project Constraints (from CLAUDE.md)

- Preserve apolitical framing and attribution; this phase must not add derived editorial content. [VERIFIED: `CLAUDE.md`, `README.md`]
- Keep the pipeline offline-only and do not expose pipeline steps as HTTP or user-facing features. [VERIFIED: `CLAUDE.md`]
- Do not modify raw PDFs. [VERIFIED: `CLAUDE.md`]
- Use Alembic as the sole DDL authority; never recommend `Base.metadata.create_all()`. [VERIFIED: `CLAUDE.md`]
- Keep `FASTAPI_BASE_URL` server-only; never rename it to a `PUBLIC_` variable or expose `ADMIN_TOKEN` to browser code. [VERIFIED: `CLAUDE.md`, `app/src/routes/**/*.server.ts`]
- No `AGENTS.md`, `.codex/AGENTS.md`, or `.claude/CLAUDE.md` exists in this checkout. The root `CLAUDE.md` is the applicable project guide. [VERIFIED: filesystem inspection]
- The only discovered project skill concerns PDF extraction and parsing; it is unrelated to local-stack documentation and adds no Phase 40 rules. [VERIFIED: `.claude/skills/spike-findings-scotuschat/SKILL.md` path and scope]

## Standard Stack

This phase selects no new libraries or packages. Versions below are repository contracts or locally observed versions, not upgrade recommendations. [VERIFIED: repository manifests and local CLI probes]

### Core

| Tool / Runtime | Version Contract | Purpose | Planning Consequence |
|----------------|------------------|---------|----------------------|
| Python | 3.12 project contract | FastAPI, Alembic, and pipeline runtime | README prerequisite should say Python 3.12; create `.venv` at repo root. [VERIFIED: `CLAUDE.md`] |
| PostgreSQL | 16 project contract | Local relational database | Windows docs cover portable and service installs; POSIX assumes an existing service. [VERIFIED: `CLAUDE.md`, CONTEXT D-02/D-03] |
| FastAPI / Uvicorn | `fastapi[standard]>=0.115`, `uvicorn>=0.30` | Backend and dev server | Install from `requirements.txt`; start `api.main:app` on 8000. [VERIFIED: `requirements.txt`, `api/main.py`] |
| SQLAlchemy / Alembic | `sqlalchemy>=2.0`, `alembic>=1.13` | Async persistence and migrations | Schema creation is `python -m alembic upgrade head`, not custom SQL tables. [VERIFIED: `requirements.txt`, `CLAUDE.md`] |
| Node.js / npm | Must satisfy the checked-in lockfile packages | SvelteKit tooling and reproducible install | Verify `node --version` and `npm --version`, then run `npm ci` in `app/`. [VERIFIED: `app/package-lock.json`, npm official docs] |
| SvelteKit / Svelte | `@sveltejs/kit ^2.21.0`, `svelte ^5.30.0` | Frontend SSR and UI | Start with the existing `npm run dev` script. [VERIFIED: `app/package.json`] |

### Supporting

| Tool | Version / Source | Purpose | When to Use |
|------|------------------|---------|-------------|
| PowerShell | Windows shell | Portable quick start and Windows bootstrap | Required for `scripts/dev-start.ps1`; commands should be copy/paste-safe. [VERIFIED: script extension and contents] |
| PostgreSQL CLIs | Same distribution as server | `initdb`, `pg_ctl`, `createuser`, `createdb`, `psql` | Use for one-time portable setup and service-backed role/database creation. [CITED: https://www.postgresql.org/docs/current/reference-server.html] |
| Python `secrets` | Standard library | Strong `ADMIN_TOKEN` and `SESSION_SECRET` generation | Use `secrets.token_urlsafe(32)` in both PowerShell and POSIX examples. [CITED: https://docs.python.org/3/library/secrets.html] |

### Package Legitimacy Audit

Not applicable: Phase 40 adds no package and recommends only installing the repository's existing `requirements.txt` and checked-in `app/package-lock.json`. The planner must not add dependency-upgrade or package-selection work. [VERIFIED: phase boundary, manifests]

## Architecture Patterns

### System Architecture Diagram

```text
Clean checkout
    |
    +--> one-time bootstrap
    |      +--> root .venv + requirements.txt
    |      +--> app/node_modules from package-lock via npm ci
    |      +--> root .env (backend/database)
    |      +--> app/.env (SvelteKit private server env)
    |      +--> PostgreSQL branch
    |             +--> portable: data/pgsql + data/pgdata
    |             +--> Windows service / external POSIX service
    |      +--> create scotus role/database --> Alembic upgrade head
    |
    +--> recurring startup
           +--> portable Windows: scripts/dev-start.ps1
           |      +--> pg_ctl --> PostgreSQL :5432
           |      +--> Alembic
           |      +--> Uvicorn --> FastAPI :8000
           |      +--> Vite --> SvelteKit :5173
           |
           +--> manual path: database already running
                  +--> terminal 1: Uvicorn/FastAPI :8000
                  +--> terminal 2: npm run dev/SvelteKit :5173

Acceptance trace:
GET :8000/health --> public UI :5173 --> /admin/login --> authenticated admin page
```

All ports and entry points above come from current repository code or examples. [VERIFIED: `scripts/dev-start.ps1`, `api/main.py`, `.env.example`]

### Recommended Project Structure

```text
README.md                  # full setup, recurring startup, verification, troubleshooting, attribution
.env.example               # backend/database groups only; no real secrets
.gitignore                 # must ignore data/pgsql/ as well as data/pgdata/
app/.env.example           # SvelteKit private server variables
app/.gitignore             # already ignores app/.env and permits app/.env.example
scripts/dev-start.ps1      # existing recurring portable-Windows startup contract
scripts/provision_test_db.py # existing optional test DB setup
```

### Pattern 1: Bootstrap Once, Start Repeatedly

**What:** Separate prerequisites, installation, env/database initialization, and migration from the short recurring startup path. [VERIFIED: CONTEXT D-04/D-05]

**When to use:** The README should open with a compact “Already set up?” path and then provide the full clean-checkout path. The quick path must explicitly require an activated `.venv` because `dev-start.ps1` invokes `alembic` and `uvicorn` by command name. [VERIFIED: `scripts/dev-start.ps1`]

### Pattern 2: Two Explicit Environment Boundaries

**What:** Root `.env` contains backend/database/pipeline settings; `app/.env` contains SvelteKit private server settings. `ADMIN_TOKEN` is duplicated intentionally and must match exactly. [VERIFIED: `api/core/config.py`, `app/src/**/*.server.ts`, CONTEXT D-12]

**When to use:** Document copy commands separately (`Copy-Item .env.example .env`; `Copy-Item app/.env.example app/.env` and POSIX equivalents), then show the minimum required variables before optional groups. [VERIFIED: CONTEXT D-09/D-14]

### Pattern 3: Branch Only at PostgreSQL Ownership

**What:** Both Windows PostgreSQL options converge on the same role/database, `DATABASE_URL`, migration, startup, and verification steps. Only server installation/start instructions differ. [VERIFIED: CONTEXT D-02, repository database URL]

**When to use:** Keep portable and Windows-service sections parallel; do not duplicate the later FastAPI/SvelteKit guide. POSIX starts at “ensure your external PostgreSQL service is running.” [VERIFIED: CONTEXT D-03]

### Pattern 4: Commands are the Acceptance Criteria

**What:** Every README command should map to a checked-in file, executable, or official CLI contract. [VERIFIED: repository inspection; official Python/PostgreSQL/npm docs]

**When to use:** Verification should grep for required env names and ports, run non-destructive version/help commands, run `npm ci`/`npm run check`, and manually check `/health`, public UI, and admin login where a local stack is available. [VERIFIED: CONTEXT D-07]

### Anti-Patterns to Avoid

- **Treating `dev-start.ps1` as an installer:** It cannot create `.venv`, install packages, initialize `data/pgdata`, create env files, or create the database. [VERIFIED: script contents]
- **A single combined `.env`:** SvelteKit reads from its `app/` runtime context and uses `$env/static/private`; root `.env` is not the frontend contract. [VERIFIED: env imports and CONTEXT D-12]
- **`PUBLIC_FASTAPI_BASE_URL`:** This contradicts the server-only architecture and risks leaking internal API configuration. [VERIFIED: `CLAUDE.md`]
- **`npm install` for clean checkout:** The repository has a lockfile; `npm ci` is the frozen clean-install path and will not rewrite manifests. [CITED: https://docs.npmjs.com/cli/commands/npm-ci/]
- **Handwritten table DDL:** Alembic is the sole schema authority. [VERIFIED: `CLAUDE.md`]
- **Package-manager recipes for macOS/Linux PostgreSQL:** Explicitly out of scope; assume an externally managed service. [VERIFIED: CONTEXT D-03]
- **Claiming POSIX verification:** Label those commands “equivalent guidance” unless actually exercised on a POSIX host. [VERIFIED: CONTEXT D-01]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Recurring portable-stack orchestration | A new shell runner or Docker setup | Existing `scripts/dev-start.ps1` | The phase locks this script as the lead recurring path and excludes feature work. [VERIFIED: CONTEXT D-04/D-05] |
| Python isolation | Custom PATH manipulation | `python -m venv .venv` and documented activation | Standard, disposable environment with official cross-platform activation. [CITED: https://docs.python.org/3/library/venv.html] |
| Frontend dependency resolution | Manual package list | `npm ci` from `app/package-lock.json` | Reproducible full-project install without manifest writes. [CITED: https://docs.npmjs.com/cli/commands/npm-ci/] |
| Database schema creation | SQL copied into README | `python -m alembic upgrade head` | Keeps current migration head authoritative. [VERIFIED: `CLAUDE.md`, `alembic/env.py`] |
| Secret generation | Ad hoc strings or `random` | Python `secrets.token_urlsafe(32)` | Uses OS-backed cryptographic randomness and yields URL-safe text. [CITED: https://docs.python.org/3/library/secrets.html] |
| PostgreSQL lifecycle | Custom process supervision | `initdb`, `pg_ctl`, and the installed Windows service | These tools own cluster initialization and server lifecycle. [CITED: https://www.postgresql.org/docs/current/app-initdb.html, https://www.postgresql.org/docs/current/app-pg-ctl.html] |

**Key insight:** The phase should document and align existing contracts, not introduce another setup abstraction.

## Common Pitfalls

### Pitfall 1: Portable PostgreSQL Makes the Worktree Dirty

**What goes wrong:** Extracting PostgreSQL to `data/pgsql` creates thousands of untracked files. [VERIFIED: `git status --short`, `git check-ignore`]

**Why it happens:** Root `.gitignore` ignores `data/pgdata/` but not `data/pgsql/`. [VERIFIED: `.gitignore`]

**How to avoid:** Include `data/pgsql/` in the Phase 40 alignment edits before telling users to extract there. [VERIFIED: CONTEXT D-10]

**Warning signs:** `git status --short` reports `?? data/pgsql/` after setup. [VERIFIED: current worktree]

### Pitfall 2: Quick Start Uses the Wrong Python Environment

**What goes wrong:** `alembic` or `uvicorn` is missing, or a global version is used. [VERIFIED: `scripts/dev-start.ps1` command resolution]

**Why it happens:** The script invokes command names, not `.venv/Scripts/...` paths, and it does not activate the environment. [VERIFIED: `scripts/dev-start.ps1`]

**How to avoid:** Make venv activation an explicit prerequisite immediately above the quick-start command. Use `python -m alembic` and `python -m uvicorn` in manual examples so interpreter ownership is unambiguous. [CITED: https://docs.python.org/3/library/venv.html]

**Warning signs:** `Get-Command alembic`/`Get-Command uvicorn` resolves outside `.venv`, or the script fails before service launch. [VERIFIED: PowerShell behavior]

### Pitfall 3: Shared Token Drift

**What goes wrong:** SvelteKit starts but admin API requests fail authentication. [VERIFIED: SvelteKit server requests send `X-Admin-Token`; FastAPI validates `ADMIN_TOKEN`]

**Why it happens:** Root `.env` and `app/.env` contain different `ADMIN_TOKEN` values. [VERIFIED: CONTEXT D-12]

**How to avoid:** Generate once, paste the same value into both files, and call this invariant out next to both examples. [CITED: https://docs.python.org/3/library/secrets.html]

**Warning signs:** Public pages may load while admin requests return authorization errors. [VERIFIED: separate public/admin request paths]

### Pitfall 4: Database Role and URL Do Not Match

**What goes wrong:** Alembic or FastAPI cannot authenticate even though PostgreSQL is running. [VERIFIED: `DATABASE_URL` is required by `alembic/env.py` and `api/core/config.py`]

**Why it happens:** The password entered for `createuser -P`, role name, database name, host, or port differs from `DATABASE_URL`. [CITED: https://www.postgresql.org/docs/current/app-createuser.html, https://www.postgresql.org/docs/current/app-createdb.html]

**How to avoid:** Use one concrete local example and state that the URL must be updated if the operator chooses different credentials. Prefer an interactive password prompt over embedding a password in shell history. [CITED: https://www.postgresql.org/docs/current/app-createuser.html]

**Warning signs:** `password authentication failed`, `role does not exist`, or `database does not exist` during migration. [VERIFIED: standard PostgreSQL failure modes from the named mismatches]

### Pitfall 5: Portable Cluster Uses Unsafe Default Authentication

**What goes wrong:** A cluster initialized with permissive `trust` authentication may accept local connections without a password. [CITED: https://www.postgresql.org/docs/current/app-initdb.html]

**Why it happens:** `initdb` documents `trust` as an ease-of-installation default in some configurations. [CITED: https://www.postgresql.org/docs/current/app-initdb.html]

**How to avoid:** Initialize with an explicit bootstrap user/password and host authentication, then make the README's role/database creation steps match. Do not recommend `trust` on a machine with untrusted local users. [CITED: https://www.postgresql.org/docs/current/app-initdb.html]

**Warning signs:** `pg_hba.conf` host entries use `trust`. [CITED: https://www.postgresql.org/docs/current/auth-pg-hba-conf.html]

### Pitfall 6: Admin Login Is Not Tested End to End

**What goes wrong:** `/health` and the public UI pass, but login fails because credentials/session config are absent or mismatched. [VERIFIED: `app/src/routes/admin/login/+page.server.ts`, `app/src/lib/server/session.ts`]

**Why it happens:** `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `SESSION_SECRET` are frontend-only requirements and are easy to omit when copying the old combined root example. [VERIFIED: current `.env.example`, env consumers]

**How to avoid:** Make admin login a required acceptance step after public UI verification. [VERIFIED: CONTEXT D-07/D-08]

**Warning signs:** Login action returns the generic invalid-credentials response, or session cookies do not persist. [VERIFIED: login/session code]

## Code Examples

These are planning-grade command shapes. Implementation must verify copy/paste behavior and adjust only for the exact PostgreSQL archive layout selected in the README. [VERIFIED: repo contracts; MEDIUM cross-platform confidence]

### Secret Generation (PowerShell and POSIX)

```powershell
# Run twice: once for ADMIN_TOKEN and once for SESSION_SECRET.
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

```bash
# Run twice: once for ADMIN_TOKEN and once for SESSION_SECRET.
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

The command uses 32 random bytes and emits URL-safe text. [CITED: https://docs.python.org/3/library/secrets.html]

### Windows Python and Frontend Bootstrap

```powershell
python --version
node --version
npm --version

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

Push-Location app
npm ci
Pop-Location

Copy-Item .env.example .env
Copy-Item app\.env.example app\.env
```

Python venv creation/activation and npm clean-install semantics are official patterns. [CITED: https://docs.python.org/3/library/venv.html, https://docs.npmjs.com/cli/commands/npm-ci/]

### Portable PostgreSQL Bootstrap Shape (PowerShell)

```powershell
# After extracting the official Windows distribution so this file exists:
Test-Path .\data\pgsql\bin\initdb.exe

.\data\pgsql\bin\initdb.exe -D .\data\pgdata -U postgres -W --auth-host=scram-sha-256
.\data\pgsql\bin\pg_ctl.exe start -D .\data\pgdata -l .\data\pgdata\logfile
.\data\pgsql\bin\createuser.exe -h localhost -U postgres -P scotus
.\data\pgsql\bin\createdb.exe -h localhost -U postgres -O scotus scotus
```

`initdb -D`, `pg_ctl start -D -l`, `createuser -P`, and `createdb -O` are supported official CLI forms. [CITED: https://www.postgresql.org/docs/current/app-initdb.html, https://www.postgresql.org/docs/current/app-pg-ctl.html, https://www.postgresql.org/docs/current/app-createuser.html, https://www.postgresql.org/docs/current/app-createdb.html]

The password supplied for role `scotus` must match the password in root `DATABASE_URL`. If the bootstrap role or port differs, the commands must be adjusted consistently. [VERIFIED: `.env.example`; CITED: PostgreSQL CLI docs above]

### Migration and Recurring Startup

```powershell
# Run from repo root with .venv active and env files configured.
python -m alembic upgrade head

# Portable PostgreSQL path after one-time setup:
.\scripts\dev-start.ps1
```

```powershell
# Windows service-backed PostgreSQL: terminal 1, repo root, .venv active
python -m alembic upgrade head
python -m uvicorn api.main:app --reload --port 8000
```

```powershell
# Windows service-backed PostgreSQL: terminal 2
Set-Location app
npm run dev
```

These entry points match current repository code. [VERIFIED: `scripts/dev-start.ps1`, `api/main.py`, `app/package.json`, `alembic/env.py`]

### Equivalent POSIX Project Commands

```bash
python3 --version
node --version
npm --version

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
(cd app && npm ci)

cp .env.example .env
cp app/.env.example app/.env

# PostgreSQL service/role/database are externally managed on POSIX.
python -m alembic upgrade head
python -m uvicorn api.main:app --reload --port 8000
```

```bash
# Separate terminal
cd app
npm run dev
```

Venv commands are official; project commands match repository entry points. [CITED: https://docs.python.org/3/library/venv.html; VERIFIED: repository inspection]

### Verification Checklist

```powershell
Invoke-RestMethod http://localhost:8000/health
# Expected JSON object: status = ok
```

- Open `http://localhost:5173` and confirm the public UI renders. [VERIFIED: `scripts/dev-start.ps1`]
- Open `http://localhost:5173/admin/login`, sign in with `app/.env` credentials, and confirm an authenticated admin page loads. [VERIFIED: login/session routes]
- Confirm PostgreSQL is on 5432, FastAPI on 8000, and SvelteKit on 5173 unless the operator intentionally changed all dependent configuration. [VERIFIED: `.env.example`, startup script]

### Optional Test Database and First Content

```powershell
python scripts\provision_test_db.py
python -m pipeline import-justices
```

`provision_test_db.py` creates/migrates the database named by `TEST_DATABASE_URL` with guards against the dev database. `python -m pipeline import-justices` is the current idempotent first-content pointer and uses the checked-in default CSV path. [VERIFIED: `scripts/provision_test_db.py`, `pipeline/__main__.py`, `pipeline/commands/import_justices_csv.py`]

## State of the Art

| Old / Current Gap | Required Phase 40 Approach | Impact |
|-------------------|----------------------------|--------|
| README contains attribution only | Keep attribution and add complete setup/start/verify/troubleshoot material | Satisfies DOCS-01 without losing licensing credit. [VERIFIED: `README.md`] |
| Root `.env.example` mixes backend and SvelteKit values | Split backend root example from new `app/.env.example` | Matches actual runtime loading boundaries. [VERIFIED: env consumers, CONTEXT D-12/D-15] |
| Dependency setup is implicit | `python -m pip install -r requirements.txt` plus `npm ci` | Makes clean checkout reproducible from checked-in manifests. [VERIFIED: manifests; CITED: npm docs] |
| PostgreSQL setup is implicit | Two Windows branches plus externally managed POSIX service guidance | Covers locked supported-platform decisions. [VERIFIED: CONTEXT D-01-D-03] |
| Portable binaries are not ignored | Add `data/pgsql/` ignore coverage | Prevents setup from polluting git status. [VERIFIED: `.gitignore`, `git check-ignore`] |

**Deprecated/outdated:** Do not repeat `.env.example`'s old guidance that SvelteKit variables belong in root `.env`; Phase 40 explicitly replaces that combined layout. [VERIFIED: CONTEXT D-12/D-15]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The exact PostgreSQL Windows archive extraction layout will place executables directly at `data/pgsql/bin`. [ASSUMED] | Code Examples | Official downloads may add a versioned top-level directory; README must instruct users to normalize the extracted directory and verify `data/pgsql/bin/initdb.exe` exists. |
| A2 | Python 3.12 remains the intended contributor prerequisite even though the research machine currently runs Python 3.14.4 successfully enough for installed tooling. [ASSUMED] | Standard Stack | A newer formally supported minimum would change prerequisite wording; `CLAUDE.md` currently governs. |

No package names or security controls depend on these assumptions. The planner can resolve A1 with an explicit `Test-Path` checkpoint and should preserve the repository-declared Python 3.12 contract for A2.

## Open Questions

1. **Which official Windows PostgreSQL distribution URL should the README link?**
   - What we know: the locked filesystem contract is `data/pgsql/bin`, and the README must explain obtain/extract. [VERIFIED: CONTEXT D-10, `scripts/dev-start.ps1`]
   - What's unclear: official PostgreSQL Windows pages may route to installer or third-party-hosted binary packages, and archive layouts can vary. [ASSUMED]
   - Recommendation: link the official PostgreSQL Windows download landing page, avoid pinning a transient deep binary URL, and require `Test-Path data/pgsql/bin/initdb.exe` before initialization. [CITED: https://www.postgresql.org/download/windows/]

2. **How should “Windows verified” be evidenced?**
   - What we know: this research machine has Python 3.14.4, Node 24.15.0, npm 11.12.1, PostgreSQL 18.4 binaries, and an existing `.venv`; it is not a clean Python 3.12/PostgreSQL 16 checkout. [VERIFIED: local CLI probes]
   - What's unclear: a destructive clean-cluster walkthrough was intentionally not performed against the user's existing environment. [VERIFIED: research actions]
   - Recommendation: the plan must include a non-production scratch-cluster walkthrough or an explicit operator verification checkpoint before the README labels Windows as verified. Do not infer verification from static review alone.

## Environment Availability

| Dependency | Required By | Available | Observed Version | Planning Note |
|------------|-------------|-----------|------------------|---------------|
| PowerShell | Windows docs and quick start | Yes | Current session | Primary documented Windows shell. [VERIFIED: environment] |
| Python | venv, backend, migration | Yes | 3.14.4 | Project contract is 3.12; use contract in README and avoid claiming 3.14 certification. [VERIFIED: CLI, `CLAUDE.md`] |
| Node.js | SvelteKit | Yes | 24.15.0 | Available for command verification. [VERIFIED: CLI] |
| npm | Frontend install/start | Yes | 11.12.1 | Available; checked-in lockfile is version 3. [VERIFIED: CLI, `app/package-lock.json`] |
| PostgreSQL binaries | Portable/service paths | Yes | 18.4 observed | Both PATH-based and `data/pgsql/bin` binaries exist locally; project contract remains PostgreSQL 16. [VERIFIED: CLI, filesystem, `CLAUDE.md`] |
| Alembic | Migration | Yes in `.venv` | 1.18.4 | Manual docs should use `python -m alembic`; quick script requires active `.venv`. [VERIFIED: CLI, script] |
| Uvicorn | FastAPI dev server | Yes in `.venv` | 0.49.0 | Manual docs should use `python -m uvicorn`. [VERIFIED: CLI] |

**Missing dependencies with no fallback:** None on the research machine. [VERIFIED: availability probes]

**Important limitation:** Availability does not equal a clean-checkout verification. PostgreSQL initialization, role/database creation, and admin login require an isolated walkthrough during execution. [VERIFIED: research scope]

## Security Domain

Security enforcement is not explicitly disabled in `.planning/config.json`, so the documentation must preserve existing secret and server-boundary controls. Nyquist validation is explicitly false, so no Validation Architecture section is included. [VERIFIED: `.planning/config.json`]

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | Require operator-chosen `ADMIN_USERNAME`/`ADMIN_PASSWORD`; backend service calls require matching `ADMIN_TOKEN`. [VERIFIED: login and API auth code] |
| V3 Session Management | Yes | Generate a strong `SESSION_SECRET`; keep it in ignored `app/.env`; verify admin login. [VERIFIED: `app/src/lib/server/session.ts`, `app/.gitignore`] |
| V4 Access Control | Yes | Keep `ADMIN_TOKEN` server-side and identical across backend/frontend env files; never expose it via `PUBLIC_` variables. [VERIFIED: `CLAUDE.md`, server imports] |
| V5 Input Validation | Limited | Pydantic settings validate required backend env; README must present syntactically valid URLs and explicit placeholders. [VERIFIED: `api/core/config.py`] |
| V6 Cryptography | Yes | Use Python `secrets` for 32-byte tokens; do not hand-roll randomness. [CITED: https://docs.python.org/3/library/secrets.html] |

### Known Threat Patterns for Local Setup

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secrets committed through example or real env files | Information Disclosure | Examples contain placeholders only; `.env` and `app/.env` remain ignored; verification greps for accidental concrete secrets. [VERIFIED: ignore files] |
| Backend token exposed to browser code | Information Disclosure / Elevation of Privilege | Keep imports in `$env/static/private` and `+*.server.ts`; never use a public env prefix. [VERIFIED: `CLAUDE.md`, current code] |
| Weak hand-chosen tokens | Spoofing | Generate `ADMIN_TOKEN` and `SESSION_SECRET` with 32 bytes of OS-backed randomness. [CITED: https://docs.python.org/3/library/secrets.html] |
| PostgreSQL `trust` authentication on a shared machine | Spoofing / Elevation of Privilege | Use explicit password and host authentication in portable initialization; warn against `trust`. [CITED: https://www.postgresql.org/docs/current/app-initdb.html] |
| Production credentials copied into local docs | Information Disclosure | Group object storage and deployment-only variables separately with empty placeholders and label them unnecessary for the minimum local stack. [VERIFIED: CONTEXT D-14, `api/core/config.py`] |

## Sources

### Primary (HIGH confidence)

- Repository contracts: `README.md`, `.env.example`, `.gitignore`, `app/.gitignore`, `scripts/dev-start.ps1`, `scripts/provision_test_db.py`, `app/package.json`, `app/package-lock.json`, `requirements.txt`, `requirements-dev.txt`, `api/main.py`, `api/core/config.py`, `alembic/env.py`, `pipeline/__main__.py`, and `CLAUDE.md` - current implementation truth inspected on 2026-07-13.
- Phase contracts: `40-CONTEXT.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/config.json`, and `.planning/STATE.md` - scope, decisions, DOCS-01, and workflow flags.

### Secondary (MEDIUM confidence)

- https://docs.python.org/3/library/venv.html - official venv creation and PowerShell/POSIX activation commands; current page checked 2026-07-13.
- https://docs.python.org/3/library/secrets.html - official cryptographic token-generation guidance; current page checked 2026-07-13.
- https://docs.npmjs.com/cli/commands/npm-ci/ - official clean-install and lockfile behavior; current page checked 2026-07-13.
- https://www.postgresql.org/docs/current/app-initdb.html - official cluster initialization and authentication options; current page checked 2026-07-13.
- https://www.postgresql.org/docs/current/app-pg-ctl.html - official server start/status/stop forms; current page checked 2026-07-13.
- https://www.postgresql.org/docs/current/app-createuser.html - official role creation/password prompting; current page checked 2026-07-13.
- https://www.postgresql.org/docs/current/app-createdb.html - official database creation/ownership; current page checked 2026-07-13.
- https://www.postgresql.org/download/windows/ - official Windows download landing page; current route selected to avoid a transient binary URL.

### Tertiary (LOW confidence)

- None. Unverified items are isolated in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - versions and entry points come from checked-in manifests and project constraints.
- Architecture: HIGH - env boundaries, service ownership, and ports were traced through current source.
- Windows bootstrap commands: MEDIUM - official CLI forms and local binaries were verified, but no destructive clean-cluster walkthrough was performed.
- POSIX commands: MEDIUM - official venv commands and repository entry points are verified, but CONTEXT requires them to be labeled equivalent guidance.
- Pitfalls: HIGH - each is observable in current files or follows directly from the documented CLI contracts.

**Research date:** 2026-07-13
**Valid until:** 2026-08-12 for repository contracts; recheck official download routing and CLI docs if planning occurs later.
