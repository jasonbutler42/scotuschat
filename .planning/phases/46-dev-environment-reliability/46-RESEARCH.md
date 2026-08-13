# Phase 46: Dev Environment Reliability - Research

**Researched:** 2026-08-12
**Domain:** pytest conftest/collection mechanics; WSL2↔Windows networking; Postgres service configuration; WSL-native process orchestration (bash); uvicorn/vite file-watching on 9p/DrvFs
**Confidence:** HIGH (pytest fix mechanism, WSL filesystem/networking mechanics — verified against this machine directly); MEDIUM (Windows-service-specific pg_hba/firewall steps — standard docs, not exercised on this Windows host from this session)

## Summary

This phase has two independent fixes. The **pytest DB-isolation bypass** has a clean, well-documented root cause: `tests/conftest.py` lives in a directory that is a *sibling* of `api/tests/` and `pipeline/tests/`, not their ancestor. pytest's conftest.py discovery is strictly hierarchical (ancestor-to-descendant) — a conftest.py is only auto-loaded for test paths at or below its own directory. When `pytest` is invoked bare, `testpaths` in `pytest.ini` (`tests pipeline/tests api/tests`) drives collection and `tests/` happens to be first, so `tests/conftest.py` gets loaded as part of that collection. When explicit paths under `api/tests/` or `pipeline/tests/` are passed, `tests/conftest.py` is never an ancestor of those paths and is never loaded — the `DATABASE_URL` → `TEST_DATABASE_URL` redirect and the row-count leak-detection guard both silently no-op. **The fix is a location fix, not a hook fix:** move the redirect + guard logic into a `conftest.py` at the actual pytest **rootdir** (repo root, alongside `pytest.ini` — currently no file exists there), because the rootdir is *always* an ancestor of every one of the three test directories regardless of how pytest is invoked. Wrapping the redirect in a `pytest_configure` hook is a legitimate defense-in-depth *addition* (it lets other conftests assert the redirect fired, i.e. option 3's fail-closed guard) but does not by itself fix anything if the file containing the hook still lives in a sibling directory that doesn't get collected.

This machine's research session ran directly on the operator's real WSL2 environment (hostname `HTPC`, Ubuntu 26.04, kernel `6.18.33.2-microsoft-standard-WSL2`), which let several CONTEXT.md-flagged unknowns be verified directly rather than assumed: the project directory (`/mnt/c/workspace/scotuschat/project`) is mounted via **9p/DrvFs**, not native ext4 — this is the same filesystem type Vite's own docs cite as the cause of unreliable file-watching on WSL2, independent of and in addition to the stray-worktree-dir reload noise CONTEXT.md already named. `ip route show default` returns `172.26.32.1`, matching `/etc/resolv.conf`'s nameserver exactly, and is the standard, more semantically correct way to obtain the Windows host IP (it reads the default gateway, not a DNS config file) — but it should still be **computed at script-start time**, never hardcoded into `.env`, because the WSL2 NAT subnet is documented to shift after Windows/WSL updates. A WSL-native Python 3.12.13 interpreter is *already installed* on this machine via `uv` (`/home/jason/.local/bin/python3.12`), so D-01's "fresh WSL-native Python venv" requires no new interpreter install — just `python3.12 -m venv .venv` (or `uv venv --python 3.12`) run from WSL.

**Primary recommendation:** (1) Create a root-level `./conftest.py` carrying the `TEST_DATABASE_URL` redirect + row-count guard (verbatim logic from today's `tests/conftest.py`), add a `pytest_configure` sentinel so `api/tests/conftest.py`'s and `pipeline/tests/conftest.py`'s DB-gated fixtures can fail closed if it's somehow still missing, and delete the now-redundant module-level code from `tests/conftest.py`. (2) Build the new start/stop entry point as a single WSL-native bash script that: computes the Windows host IP fresh via `ip route`, TCP-probes port 5432 (no `pg_isready` binary is installed on this WSL distro today — verified), runs `alembic upgrade head`, backgrounds `uvicorn --reload-exclude` (pattern for `.claude/worktrees/agent-*`) and `npm run dev` with real HTTP health-check polling, and traps `SIGINT`/`SIGTERM` to clean up both. (3) Flag the DrvFs file-watching risk to the operator explicitly — `WATCHFILES_FORCE_POLLING=true` / vite's `usePolling: true` is the low-risk mitigation that fits inside D-03's scope ceiling; relocating the repo to native ext4 is the complete fix but is a bigger structural change than CONTEXT.md's decisions describe and should be a checkpoint question, not a silent default.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Test DB isolation redirect | Test tooling (pytest conftest) | — | Must run before any module imports `api.core.config.settings`; pytest's own collection-order guarantee is the only tier that can do this |
| DB-gated test leak detection | Test tooling (pytest conftest) | — | Session-level guard needs to run for every invocation shape, so it must live at the same tier/location as the redirect |
| Postgres lifecycle (start/verify) | OS / Windows Service Manager | Dev orchestration script (WSL) | The database itself is now a real Windows service (D-02); the WSL script's job is to verify reachability, not manage the service process itself (no admin action needed to poll a status) |
| Network reachability (WSL→Windows Postgres) | OS / Network (WSL2 NAT + Windows Firewall + pg_hba.conf) | — | Three independent gates (listen_addresses, pg_hba.conf, Windows Firewall inbound rule) all live below the application tier; the app only supplies a connection string |
| API/Frontend process lifecycle | Dev orchestration script (WSL) | — | D-01 moves both to WSL-native; a single script is the natural owner per D-03 |
| File-watching (reload/HMR) | Runtime tool config (watchfiles/chokidar) | Filesystem tier (DrvFs vs ext4) | The *symptom* (noisy/missed reloads) is fixed at the runtime-tool-config tier (polling flags); the *root cause* is at the filesystem tier and is out of this phase's decided scope unless the operator elects to relocate the repo |

## User Constraints

<user_constraints>
### Locked Decisions (from 46-CONTEXT.md)

- **D-01:** Move Python (FastAPI/uvicorn) and Node (SvelteKit/vite) processes to run WSL-native instead of via the Windows-venv-through-WSL-interop path. WSL already has Node via nvm (`/home/jason/.nvm/versions/node/v24.18.0/bin/node`). A fresh WSL-native Python venv will need to be created for the API/pipeline. Reversibility: costly.
- **D-02:** Use the already-installed Windows Postgres 18 service (`postgresql-x64-18`, confirmed present but stopped) instead of the project's portable `data/pgsql` + `pg_ctl` setup. Connect to it from WSL-native code over the network (not via portable binaries). Reversibility: one-way for the portable-Postgres data (disposable dev fixture data; `POST /api/admin/dev/reset-to-fixture` reseeds). WSL2 confirmed NAT mode (not mirrored); WSL-native code must use the Windows host's IP (visible in `/etc/resolv.conf`'s `nameserver` line, e.g. `172.26.32.1` at investigation time — can change across reboots unless pinned), NOT `localhost`. Postgres needs `listen_addresses` widened from `localhost`-only and a `pg_hba.conf` rule for the WSL subnet. Test DB: keep using a distinct database name on the same service for `TEST_DATABASE_URL` — no separate test-only Postgres instance.
- **D-03 (scope ceiling):** Fix the pytest DB-isolation bypass definitively (must work regardless of pytest invocation shape) AND deliver a single reliable start/stop entry point for Postgres service start/verify + uvicorn + vite with real health checks. NOT a redesign of the test suite, NOT new CI integration, NOT containerization. Reversibility: reversible.

### Claude's Discretion

- Exact mechanism for the pytest isolation fix (`pytest_configure` hook vs. duplicating the redirect into every `conftest.py` vs. a fail-closed guard) — investigate and pick the most robust one.
- Whether the new start/stop entry point is a rewritten `dev-start.ps1` invoked from Windows, a new WSL-native shell script, or both (a thin Windows wrapper that shells into WSL) — the exact script shape/name is an implementation detail.
- Whether to delete the old portable `data/pgsql`/`data/pgdata` directories as part of this phase or just leave them unused — default to deleting once the new Postgres service is confirmed working.

### Deferred Ideas (OUT OF SCOPE)

- Full stack rework (containerization, CI integration, docs restructuring beyond what's needed to reflect the new setup).
- Hybrid split (Windows for browser-facing, WSL for tooling) — considered, not chosen; operator picked the fuller WSL-native move.
</user_constraints>

## Phase Requirements

<phase_requirements>
No formal REQUIREMENTS.md IDs are assigned to this phase (ROADMAP.md lists `Requirements: TBD`). The operative acceptance criteria are CONTEXT.md's D-01/D-02/D-03 (see User Constraints above) plus the folded todo `2026-08-12-pytest-explicit-paths-bypass-db-isolation.md`.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | WSL-native Python + Node processes | WSL already has Python 3.12.13 available via `uv` at `/home/jason/.local/bin/python3.12` (verified this session) and Node v24.18.0 via nvm (confirmed in CONTEXT.md). No new interpreter/runtime install needed — see Code Examples. |
| D-02 | Windows Postgres 18 service reachable from WSL | Verified NAT-mode networking mechanics (`ip route` vs `/etc/resolv.conf`), pg_hba.conf/listen_addresses/firewall requirements documented in Architecture Patterns and Common Pitfalls. |
| D-03 | pytest isolation fix (invocation-shape-independent) + single start/stop script | Root-cause mechanism verified against this repo's actual `tests/conftest.py` / `api/tests/conftest.py` / `pipeline/tests/conftest.py` / `pytest.ini`; fix pattern in Architecture Patterns / Code Examples. Start/stop script pattern in Architecture Patterns. |
| (folded todo) pytest explicit-path DB wipe | Root cause confirmed (conftest.py sibling-directory scoping); fix mechanism specified. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Alembic is the sole DDL authority.** The new start script must call `alembic upgrade head` before starting uvicorn (same order as today's `dev-start.ps1`) — never `Base.metadata.create_all`.
- **asyncpg requires `statement_cache_size=0`** behind Digital Ocean PgBouncer (Transaction mode). This is already correctly set in `api/core/database.py:38` and both `tests/conftest.py`/`pipeline/tests/conftest.py`'s ad-hoc engines (`connect_args={"statement_cache_size": 0}` — verified at `tests/conftest.py:67-68` and `pipeline/tests/conftest.py:66-67`). This constraint is orthogonal to D-02's Postgres-service change (it protects against PgBouncer in production, not against anything specific to local dev) — any new health-check code that opens its own SQLAlchemy engine against the Windows Postgres service must carry the same `connect_args`, purely for consistency with the rest of the codebase, not because local dev has PgBouncer.
- **Pipeline is offline only** — not directly implicated by this phase (no HTTP endpoints are being added), but the new start/stop script must not accidentally wire any pipeline step behind a route.
- **Raw PDFs are immutable** — not implicated; this phase touches dev tooling and Postgres connectivity only.

## Standard Stack

No new third-party libraries are required for this phase. Every mechanism below uses stack pieces already present in the repo (pytest, existing `dotenv`/SQLAlchemy patterns, bash/coreutils, uvicorn's bundled `watchfiles`, Vite's bundled `chokidar`) or OS/service-level configuration (Windows Postgres service, `pg_hba.conf`, Windows Firewall). See **Package Legitimacy Audit** below — no audit is required.

### Core (already in requirements.txt / package.json — no version changes needed)
| Library | Version (pinned) | Purpose | Why Standard |
|---------|------|---------|--------------|
| pytest | `>=8.0` [VERIFIED: requirements-dev.txt] | Test runner whose conftest/collection mechanics are the root cause and the fix location | Already the project's test runner |
| uvicorn | `>=0.30` [VERIFIED: requirements.txt] | ASGI server; ships `watchfiles`-backed `--reload` via the `[standard]` extra already pinned (`fastapi[standard]>=0.115` pulls uvicorn+watchfiles) | Already in use |
| vite | `^6.3.0` [VERIFIED: app/package.json:24] | Dev server / HMR; `server.watch` wraps chokidar | Already in use |

### Supporting (OS-level, not pip/npm packages)
| Tool | Where | Purpose | When to Use |
|------|-------|---------|-------------|
| `python3.12` (uv-managed) | Already installed at `/home/jason/.local/bin/python3.12` [VERIFIED: shell probe this session — `uv python list` shows `cpython-3.12.13-linux-x86_64-gnu … /home/jason/.local/bin/python3.12`] | Interpreter for the new WSL-native venv, matching CLAUDE.md's Python 3.12 pin | Creating the WSL-native `.venv` for D-01 |
| `uv` | Already installed at `/home/jason/.local/bin/uv`, version `0.11.30` [VERIFIED: shell probe this session] | Fast venv/interpreter manager; optional convenience over plain `python3.12 -m venv` | If the planner wants a faster/more reproducible venv bootstrap than stdlib `venv` |
| `ip` (iproute2) | WSL Ubuntu base install | `ip route show default` to get the Windows host IP dynamically | Every start-script invocation, not cached in `.env` |
| bash `/dev/tcp` | bash builtin | TCP-reachability probe for Postgres port 5432 without a Postgres client binary | This WSL distro has no `pg_isready`/`psql` installed [VERIFIED: shell probe this session — `dpkg -l | grep -i postgresql` returned nothing] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| bash `/dev/tcp` TCP probe for Postgres readiness | Install `postgresql-client` (`apt install postgresql-client`) for `pg_isready` | `pg_isready` gives a real protocol-level readiness signal (distinguishes "accepting connections" from "port open, still starting"); a bare TCP probe can false-positive on port-open-but-not-ready. Given Windows Postgres 18 is a long-running service (not something the script itself starts cold each time), this edge case is narrow — recommend the TCP probe as the zero-install default, with `postgresql-client` as an easy upgrade if false positives are observed. |
| Root-level `conftest.py` | Duplicating the redirect logic into `api/tests/conftest.py` AND `pipeline/tests/conftest.py` | Duplication works today but re-introduces exactly the "single point of collection failure" problem for any *future* test directory added under a new path not covered by `testpaths` — the root-conftest fix is structurally correct because rootdir is an ancestor of everything by definition, while duplication is only correct for the currently-enumerated directories. |
| WATCHFILES_FORCE_POLLING / vite usePolling (stay on `/mnt/c`) | Relocate the git repo to native WSL ext4 (e.g. `~/scotuschat/project`) | Relocation is the complete fix per Vite's own docs but is a much larger structural change (Windows-side editor/IDE access patterns, path references everywhere) than D-01 describes — flag as an operator checkpoint, not a silent default (see Open Questions). |

**Installation:** None required — no `requirements.txt`/`requirements-dev.txt`/`package.json` changes needed for this phase's mechanisms. If the planner chooses `postgresql-client` (see Alternatives), that is an `apt install postgresql-client` OS package, not a pip/npm dependency.

## Package Legitimacy Audit

**Not applicable.** This phase installs no new pip or npm packages — see Standard Stack. All fixes use libraries already pinned in `requirements.txt`/`requirements-dev.txt`/`app/package.json`, OS-level configuration (Windows Services, `pg_hba.conf`, Windows Firewall), or shell builtins. If the planner opts into `postgresql-client` (see Alternatives Considered), it is an OS package via `apt`, outside the scope of this gate.

## Architecture Patterns

### System Architecture Diagram

```
 Operator (WSL shell or thin Windows wrapper)
        │
        ▼
 ┌─────────────────────────────────────────────┐
 │  dev-start.sh (WSL-native, bash)             │
 │                                               │
 │  1. resolve WIN_HOST_IP := $(ip route ...)   │──────► /etc/resolv.conf-independent,
 │  2. probe tcp://$WIN_HOST_IP:5432             │        recomputed every run
 │       (bash /dev/tcp; fail loud if closed)   │
 │  3. alembic upgrade head                      │───┐
 │  4. background: uvicorn --reload              │   │
 │       --reload-exclude '.claude/worktrees/*'  │   │   DATABASE_URL points at
 │       --host 0.0.0.0 --port 8000              │   │   $WIN_HOST_IP:5432/scotus_dev
 │       > .dev-logs/api-out.log 2>&1 &          │   │
 │  5. poll http://localhost:8000/<health> until │   │
 │       200 or timeout                          │   │
 │  6. background: npm run dev (vite --host)     │   │
 │       > .dev-logs/app-out.log 2>&1 &           │   │
 │  7. poll http://localhost:5173 until 200       │   │
 │  8. trap SIGINT/SIGTERM → kill both PIDs,      │   │
 │       wait, exit clean                         │   │
 └──────────────────┬────────────────────────────┘   │
                     │ TCP over WSL2 NAT (172.26.x.x) │
                     ▼                                ▼
        ┌─────────────────────────┐      ┌────────────────────────┐
        │ Windows Postgres 18     │      │ Alembic migrations      │
        │ service (postgresql-    │◄─────┤ (schema DDL — sole      │
        │ x64-18)                 │      │  authority per CLAUDE.md)│
        │ listen_addresses widened│      └────────────────────────┘
        │ pg_hba.conf: WSL subnet │
        │ Windows Firewall: allow │
        │ inbound 5432            │
        └─────────────────────────┘
```

### Recommended Project Structure

No new top-level directories. Changes land in-place:
```
./conftest.py                  # NEW — root-level: TEST_DATABASE_URL redirect + pytest_sessionstart/finish guard
tests/conftest.py               # SHRINKS — only whatever is genuinely tests/-specific remains (likely nothing; may become empty or removed)
api/tests/conftest.py           # UNCHANGED structurally — optionally adds an assertion that the root redirect fired
pipeline/tests/conftest.py      # UNCHANGED structurally — same optional assertion
scripts/dev-start.sh            # NEW — WSL-native bash start/stop entry point (or dev-start.ps1 rewritten to shell into WSL — planner's discretion per CONTEXT.md)
scripts/dev-start.ps1           # Either deleted, or reduced to a thin `wsl.exe -- bash scripts/dev-start.sh` wrapper
.venv/                          # RECREATED as WSL-native (python3.12 -m venv), replacing the Windows Scripts/-layout venv
data/pgsql/, data/pgdata/       # DELETED once new Postgres service confirmed (Claude's discretion, default: delete)
```

### Pattern 1: Root-rootdir conftest.py for invocation-shape-independent hooks

**What:** Any pytest hook or module-level side effect that must fire *regardless of which subset of tests is invoked* belongs in a `conftest.py` at the pytest rootdir (the directory containing `pytest.ini`), never in a subdirectory conftest — subdirectory conftests only apply to their own directory and descendants.

**When to use:** Any cross-cutting test-session concern that spans multiple sibling test directories (here: `tests/`, `api/tests/`, `pipeline/tests/`, all direct children of the repo root where `pytest.ini` lives — [VERIFIED: pytest.ini:5] `testpaths = tests pipeline/tests api/tests`).

**Example (adapted from the current, buggy `tests/conftest.py`, moved to repo-root `./conftest.py`):**
```python
# Source: pattern derived from pytest's documented rootdir/conftest discovery
# (docs.pytest.org/en/stable/reference/customize.html — rootdir is determined
# from pytest.ini's location; a conftest.py at that same location is an
# ancestor of every testpaths entry, so it is always collected regardless
# of which explicit paths are passed on the command line).
import os
from dotenv import load_dotenv

load_dotenv()

_REAL_DATABASE_URL = os.environ.get("DATABASE_URL")

if os.environ.get("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]


def pytest_configure(config):
    # Sentinel other conftests can assert on (fail-closed option, D-03's
    # "must work regardless of invocation" requirement) — this hook itself
    # is guaranteed to run for every invocation shape because THIS FILE is
    # at rootdir, an ancestor of every testpaths entry.
    config._scotus_redirect_fired = True


# ... pytest_sessionstart / pytest_sessionfinish row-count guard: unchanged
# logic from today's tests/conftest.py (lines 44-135), just relocated.
```

**Fail-closed defense-in-depth (optional, addresses todo option 3):** in `api/tests/conftest.py` and `pipeline/tests/conftest.py`, an autouse fixture can assert `getattr(request.config, "_scotus_redirect_fired", False)` before yielding to any DB-gated test, raising loudly if the root conftest somehow didn't load (defends against a future restructuring that breaks the ancestor relationship again).

### Pattern 2: Dynamic Windows-host-IP resolution (never cached in `.env`)

**What:** Resolve the WSL2 NAT gateway IP at the top of every start-script run, not once and saved to a file.

**When to use:** Any WSL-native process that needs to reach a Windows-hosted service (Postgres here; would apply to any future Windows-hosted dependency too).

**Example:**
```bash
# Source: pattern cross-referenced from multiple WSL2 networking guides
# (ip route reads the live routing table's default gateway, which is the
# Windows host in NAT mode — more semantically correct than parsing
# /etc/resolv.conf's nameserver line, and both are confirmed to return the
# identical address on this machine: verified this session, both resolved
# to 172.26.32.1).
WIN_HOST_IP="$(ip route show default | awk '{print $3}')"
if [ -z "$WIN_HOST_IP" ]; then
  echo "ERROR: could not resolve Windows host IP via 'ip route'." >&2
  exit 1
fi
export DATABASE_URL="postgresql+asyncpg://user:pass@${WIN_HOST_IP}:5432/scotus_dev"
```

### Pattern 3: Bash service orchestration with real health checks and clean teardown

**What:** Background both processes, poll their actual HTTP endpoints (not just "did the process start"), and trap signals for clean shutdown of both.

**When to use:** The single start/stop entry point required by D-03.

**Example:**
```bash
# Source: pattern synthesized from standard bash job-control practice
# (trap + kill on PID list) — no single canonical doc source; this is
# general-purpose shell scripting, not a library API.
set -euo pipefail

cleanup() {
  echo "Stopping services..."
  kill "$API_PID" "$APP_PID" 2>/dev/null || true
  wait "$API_PID" "$APP_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

mkdir -p .dev-logs
uvicorn api.main:app --host 0.0.0.0 --reload \
  --reload-exclude '.claude/worktrees/*' \
  --port 8000 > .dev-logs/api-out.log 2> .dev-logs/api-err.log &
API_PID=$!

# Real health check, not sleep-and-hope:
for i in $(seq 1 30); do
  curl -sf http://localhost:8000/docs >/dev/null 2>&1 && break
  sleep 1
done

(cd app && npm run dev) > ../.dev-logs/app-out.log 2> ../.dev-logs/app-err.log &
APP_PID=$!

for i in $(seq 1 30); do
  curl -sf http://localhost:5173 >/dev/null 2>&1 && break
  sleep 1
done

echo "Ready: FastAPI :8000, SvelteKit :5173"
wait
```
Note: `--reload-exclude` glob semantics and defaults (`.*`, `.py[cod]`, `.sw.*`, `~*` excluded by default) per uvicorn's settings documentation [CITED: uvicorn.dev/settings — retrieved via search, direct fetch of the page timed out this session, cross-confirmed by a second independent search summary].

### Anti-Patterns to Avoid
- **Hardcoding the Windows host IP into `.env`:** WSL2's NAT-mode subnet/gateway is documented to be able to change across Windows/WSL restarts and updates — a cached IP silently breaks connectivity with a confusing error, not an obvious one.
- **Using `pytest_sessionstart`/`pytest_sessionfinish` guards as the *only* line of defense:** they detect a leak after it already happened (the guard's own job is "fail the CI/test run," not "prevent the write"). The redirect happening correctly, every invocation, is the actual prevention; the guard is a tripwire, not a fence.
- **Duplicating the redirect logic per-test-directory instead of relocating to rootdir:** works for the three directories that exist today, silently fails to protect any new sibling test directory added later — reintroduces the identical bug class.
- **`sleep N` instead of a real health check** in the start script: guesses a fixed warm-up time; either too short (race) or too long (slow perceived startup). Poll the actual port/endpoint instead.

## Runtime State Inventory

This phase involves migrating from a Windows-venv + portable-Postgres setup to a WSL-native venv + Windows-Postgres-service setup — a genuine runtime-state migration, not just a source-code rename.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Portable Postgres data directory `data/pgdata/` (git-ignored per `.gitignore:1-2` — [VERIFIED: .gitignore] `data/pgsql/`, `data/pgdata/`, `.venv/`, `.venv`, `venv/`) currently holds whatever dev fixture rows exist under the old portable instance. D-02 explicitly classifies this as disposable (reseed via `POST /api/admin/dev/reset-to-fixture`) — **no data migration**, just re-seed against the new Postgres service after cutover. | Reseed via existing endpoint; no export/import script needed. |
| Live service config | Windows Postgres 18 service (`postgresql-x64-18`) is currently **stopped** and configured `listen_addresses`-localhost-only (default) with no WSL-subnet `pg_hba.conf` rule and (presumably) no inbound Windows Firewall rule for 5432 — none of this lives in git, it's Windows-host service/OS state that must be changed out-of-band (Services.msc / `postgresql.conf` / `pg_hba.conf` / `netsh advfirewall`). | Manual one-time Windows-side configuration; document the exact steps in the plan since Claude cannot execute Windows-admin actions from this WSL research session. |
| OS-registered state | None found specific to this phase beyond the Postgres Windows service itself (already covered above). No Windows Task Scheduler entries, no pm2/launchd/systemd units reference the old dev-start flow — `dev-start.ps1` is invoked manually per `scripts/dev-start.ps1`'s own usage comment (`# Usage: .\scripts\dev-start.ps1`), not registered anywhere. | None. |
| Secrets/env vars | `.env` (repo root) and `app/.env` both carry `ENVIRONMENT=<environment>` (uncommitted local edits present — [VERIFIED: git diff this session] both files show a `+ENVIRONMENT=<environment>` addition not yet committed, from a prior session/phase, unrelated to Phase 46 but co-located). `DATABASE_URL`/`TEST_DATABASE_URL` values in `.env` currently point at the portable-Postgres connection string and must be updated to the Windows-service host:port/dbname — this is a **code-adjacent config edit**, not a data migration. `.env` is `.gitignore`d (confirmed: `.env.example`/`app/.env.example` are the tracked templates, not `.env` itself — real `.env` files were not readable in this session due to permission-boundary restrictions on env files, consistent with them being real local secrets). | Update `DATABASE_URL`/`TEST_DATABASE_URL` in the local `.env` (not `.env.example`) after cutover; document the new host-resolution pattern (Pattern 2) rather than a static value. |
| Build artifacts | `.venv/` at repo root is a **Windows-native** venv today ([VERIFIED: .venv/pyvenv.cfg] `home = C:\Users\jason\AppData\Local\Programs\Python\Python312`, `executable = C:\Users\jason\AppData\Local\Programs\Python\Python312\python.exe`, `version = 3.12.10`) with a `Scripts/` layout, matching `.planning/config.json`'s `workflow.test_command: "./.venv/Scripts/python.exe -m pytest"` [VERIFIED: .planning/config.json] — this GSD workflow setting itself becomes stale once D-01 lands and must be updated to a WSL-native path (e.g. `./.venv/bin/python -m pytest`) or this config governs test runs elsewhere (`gsd_run` execute/verify tooling) that would otherwise keep invoking the old Windows venv. `scripts/__pycache__/` already contains **both** `.cpython-312.pyc` and `.cpython-314.pyc` files ([VERIFIED: shell listing this session] `audit_tenure_seat_identifiers.cpython-312.pyc` and `audit_tenure_seat_identifiers.cpython-314.pyc` co-exist), evidence that scripts have already been run once under the Windows 3.12 venv and once under WSL's bare system `python3` (3.14.4, not the project's pinned 3.12) during ad hoc exploration this week — not harmful (pycache is version-tagged, no collision), but confirms the new venv must be explicitly `python3.12`, not whatever `python3`/`python` resolves to on WSL by default (which is 3.14.4, a mismatch against CLAUDE.md's Python 3.12 pin). | Recreate `.venv` via WSL-native `python3.12 -m venv .venv` (or `uv venv --python 3.12`); update `.planning/config.json`'s `test_command`; no action needed on stray `.pyc` files (harmless). |

## Common Pitfalls

### Pitfall 1: conftest.py sibling-directory blind spot (the priority bug)
**What goes wrong:** A conftest.py containing session-critical setup lives in `tests/`, a sibling of `api/tests/` and `pipeline/tests/`, not their ancestor. Any pytest invocation with explicit paths under the sibling directories never loads it.
**Why it happens:** pytest's conftest.py loading is [CITED: general pytest fixture-scoping documentation, docs.pytest.org] hierarchical — a conftest.py's fixtures/hooks apply to "tests in this directory and all subdirectories," which by construction excludes sibling directories. `testpaths` in `pytest.ini` masks this for bare invocations because it happens to enumerate `tests` first, giving a false impression that the redirect is unconditional.
**How to avoid:** Put invocation-shape-independent logic in a conftest.py at the true rootdir (repo root — an ancestor of every testpaths entry), never in one of several sibling test directories.
**Warning signs:** Different behavior between `pytest` (bare) and `pytest <subdir>/test_file.py` for the exact same test — especially any test that silently uses a "real" resource (DB, external API) in one invocation shape but not another. [Empirically confirmed in this repo per the folded todo's own narrative: two real dev-DB wipes during Phase 45, reproduced with `pytest api/tests/test_published_gate.py api/tests/test_arguments.py -q`.]

### Pitfall 2: WSL2 host-IP volatility
**What goes wrong:** A Windows host IP obtained once (from `/etc/resolv.conf` or `ip route`) and pasted into `.env` works until the next reboot/WSL update, then `DATABASE_URL` silently points at a dead or wrong address.
**Why it happens:** WSL2's internal NAT vSwitch subnet allocation is not guaranteed static across Windows restarts [CITED: multiple WSL2 networking guides, cross-referenced this session — e.g. gist.github.com/angus-mcritchie, stevegy.medium.com "WSL 2 Static IP"].
**How to avoid:** Compute `ip route show default | awk '{print $3}'` fresh in the start script every run (Pattern 2); never persist the raw IP to `.env`.
**Warning signs:** Postgres connection errors that appear only after a machine restart, with no code change.

### Pitfall 3: DrvFs (9p) file-watching unreliability compounds the reload-noise problem CONTEXT.md already named
**What goes wrong:** Even after excluding stray `.claude/worktrees/agent-*` directories from uvicorn's watcher (the fix CONTEXT.md names for the *noise* problem), file-save-triggered reloads for both uvicorn `--reload` and `vite`'s HMR can still be unreliable or fail entirely, because the project directory (`/mnt/c/workspace/scotuschat/project`) is mounted via 9p/DrvFs, not native ext4.
**Why it happens:** [VERIFIED: shell probe this session] `mount | grep /mnt/c` shows `C:\ on /mnt/c type 9p (rw,noatime,aname=drvfs;...)`. Vite's own official troubleshooting docs state: *"When running Vite on WSL2, file system watching does not work when a file is edited by Windows applications (non-WSL2 process)... [fix:] Use WSL2 applications to edit files, or move your project folder outside Windows filesystem"* [CITED: vite.dev/guide/troubleshooting]. `watchfiles` (uvicorn's reload backend) documents the identical class of problem for network/VM-backed mounts and the `WATCHFILES_FORCE_POLLING` escape hatch [CITED: watchfiles docs, cross-referenced via search this session].
**How to avoid:** Two tiers, in order of increasing invasiveness: (1) set `WATCHFILES_FORCE_POLLING=true` for uvicorn and `server.watch.usePolling = true` in `app/vite.config.ts` — fits inside D-03's scope ceiling, costs some CPU, fixes the symptom without touching repo location. (2) Relocate the git repo to native WSL ext4 (e.g. `~/scotuschat/project`) — the complete fix per Vite's own recommendation, but changes how the repo is accessed from Windows-side tools and is a bigger structural change than D-01's stated rationale describes. **This is not decided by CONTEXT.md — see Open Questions.**
**Warning signs:** Edits made from a Windows-side editor don't trigger reload/HMR at all, or reloads only fire after a multi-second delay regardless of polling settings.

### Pitfall 4: Windows Postgres reachable from `psql` on the Windows side but still refused from WSL
**What goes wrong:** `listen_addresses` widened correctly but connections from WSL are still refused.
**Why it happens:** Three independent gates must all pass: (1) `postgresql.conf`'s `listen_addresses` (must include the interface WSL reaches, not just `localhost`), (2) `pg_hba.conf`'s host-based rules (must include a `host` line matching the WSL subnet, e.g. `host all all 172.26.32.0/20 scram-sha-256`, not just `127.0.0.1/32`), and (3) **Windows Defender Firewall**, which has no relationship to Postgres config at all and blocks inbound 5432 by default until an explicit inbound rule is added [CITED: multiple WSL2+Postgres setup guides, cross-referenced this session]. Missing any one of the three produces the same symptom (connection refused/timeout) with no clear signal which gate failed.
**How to avoid:** Verify all three explicitly and in this order during setup: `postgresql.conf` → `pg_hba.conf` → Windows Firewall inbound rule for TCP 5432 (`New-NetFirewallRule` or GUI). Restart the Postgres service after config file changes (`net stop`/`net start postgresql-x64-18`, requires the admin access this phase assumes is now available).
**Warning signs:** `psql` succeeds from a Windows-side client but WSL-native connections time out — this specific combination almost always means the Firewall gate, not the Postgres config, since a Postgres-config-only problem tends to also affect same-host connections through non-`localhost` addresses.

### Pitfall 5: Mirrored WSL2 networking mode is not a safe alternative to NAT here
**What goes wrong:** Switching `.wslconfig`'s `networkingMode` to `mirrored` (often recommended for the general "WSL can't reach Windows via localhost" problem) does not reliably solve — and in at least one documented case, actively breaks — the specific direction needed here (WSL reaching a Windows-hosted service).
**Why it happens:** Reports are mixed and machine-specific: one confirmed issue shows a user unable to reach a Windows-host Python server from WSL2 in mirrored mode via `127.0.0.1` (hangs indefinitely), while NAT and virtioProxy modes worked on the same task [CITED: github.com/microsoft/WSL/issues/12399]. Mirrored mode's benefit (bidirectional `localhost`) is real for many setups, but is not guaranteed reliable for this exact WSL→Windows-service direction on this Windows build.
**How to avoid:** Do not switch to mirrored mode as part of this phase. Stay on the confirmed-working NAT model (Pattern 2's dynamic `ip route` resolution) — CONTEXT.md already confirmed this machine is in NAT mode; there's no evidence-backed reason to change it, and doing so risks trading one networking problem for a different, less-documented one.
**Warning signs:** N/A (this is a "don't go here" pitfall, not a detection pattern) — flag only if the planner or a future contributor proposes mirrored mode as a "cleaner" fix.

## Code Examples

### Redirect + guard, relocated (see Pattern 1 for full context)
Verbatim logic to relocate is the existing, already-correct implementation at [VERIFIED: tests/conftest.py:13-135] — the `_REAL_DATABASE_URL` capture (line 25), the `if os.environ.get("TEST_DATABASE_URL"): os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]` redirect (lines 35-36), and both `pytest_sessionstart`/`pytest_sessionfinish` functions (lines 44-135) move as-is into the new root `conftest.py`; only the file's *location* changes.

### `api/tests/conftest.py`'s existing DB-configured guard (unchanged, shown for cross-reference)
```python
# Source: api/tests/conftest.py:19-22 (verbatim, already correct — no change needed)
def _db_configured() -> bool:
    """Same guard every api/tests DB-gated fixture uses."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"
```
This guard is fine as-is; it reads whatever `DATABASE_URL` resolves to *after* the (now-fixed) root conftest's redirect has had a chance to run — the bug was never in this function, it was that the redirect never fired for certain invocations.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Portable `pg_ctl`-managed Postgres (`data/pgsql`/`data/pgdata`) | Windows Postgres 18 service, managed via `Services.msc`/`net start` | This phase (D-02), enabled by newly-available Windows admin access | Normal service lifecycle instead of manual `pg_ctl start` every session; but adds a real network hop (WSL→Windows) that didn't exist when everything ran inside the same Windows process tree |
| Windows-venv-via-WSL-interop for Python/Node | WSL-native Python (fresh `.venv`) + WSL-native Node (already present via nvm) | This phase (D-01) | Eliminates the untraceable-PID class of failure CONTEXT.md describes (Windows process APIs failing to identify/kill a process actually owned by WSL); trades it for the DrvFs file-watching tradeoff (Pitfall 3) since the *files* are staying on `/mnt/c` |
| `dev-start.ps1` (PowerShell-only, `Start-Job`-based) | WSL-native bash script (or PS1 thin wrapper shelling into WSL) | This phase (D-03) | Single entry point with real health checks, replacing manual `pg_ctl`/`Start-Process` juggling |

**Deprecated/outdated:**
- Windows-venv-via-WSL-interop path for running the API/pipeline — CONTEXT.md's own rationale documents the concrete failure mode that motivated dropping it (untraceable port-8000 process).
- Portable pg_ctl Postgres setup — existed only to avoid needing admin rights, a constraint no longer in force.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `postgresql-x64-18`'s exact `postgresql.conf`/`pg_hba.conf` file paths and the precise Windows Firewall command syntax needed on THIS Windows host were not verified directly this session (this research ran from WSL; direct administration of the Windows-side Postgres service/firewall requires Windows-side action the researcher cannot take from here) — guidance is [CITED] from general Postgres-on-Windows/WSL2 setup guides, not this specific installation. | Common Pitfalls (Pitfall 4), Architecture Patterns diagram | If the actual installed Postgres 18's default config paths or Windows build's firewall UI differ from generic guides, the plan's setup steps may need minor path/command adjustments during execution — not a fundamental risk to the approach. |
| A2 | The exact `--reload-exclude`/`--reload-exclude-dir` flag syntax details were retrieved via WebSearch summaries rather than a successful direct fetch of uvicorn's own settings page (both `uvicorn.dev` and `www.uvicorn.org` direct fetches timed out this session) — cross-confirmed by two independent search result summaries citing the same page, but not read verbatim. | Architecture Patterns (Pattern 3), Common Pitfalls | Low risk — the flag names/semantics described are consistent across multiple independent sources and match uvicorn's documented CLI conventions; worst case a minor flag-name correction during implementation. |
| A3 | Whether relocating the repo off `/mnt/c` (Pitfall 3's "complete fix") is something the operator wants as part of this phase, vs. accepting the polling-flag mitigation — CONTEXT.md's decisions do not address this because the DrvFs file-watching risk was not named as a driver of the phase (only the stray-worktree-dir reload noise was named). | Common Pitfalls (Pitfall 3), Open Questions | If the operator would have wanted the full fix and the plan only ships polling flags, reload/HMR reliability may remain a lingering friction point this phase was meant to eliminate. |

## Open Questions

1. **Should the repo be relocated off `/mnt/c` (Windows-mounted DrvFs) onto native WSL ext4 as part of this phase, or is the lower-risk polling-flag mitigation (Pitfall 3) sufficient?**
   - What we know: The project currently lives at `/mnt/c/workspace/scotuschat/project`, mounted via 9p/DrvFs (verified this session). Vite's own docs name this exact configuration as the documented cause of WSL2 HMR unreliability and explicitly recommend relocation as the fix, with polling as a fallback that costs CPU.
   - What's unclear: CONTEXT.md's decisions (D-01) discuss moving *processes* WSL-native but never discuss moving the *repository location* — this may be an oversight, or the operator may have already implicitly ruled it out (e.g. because Windows-side tools need to access the files directly) without it being surfaced in discussion.
   - Recommendation: The planner should raise this explicitly as a checkpoint/confirm-with-operator item rather than silently defaulting to either extreme. Default the *plan* to the low-risk polling-flag mitigation (fits D-03's scope ceiling cleanly) and note repo relocation as a fast-follow option if reload/HMR problems persist after this phase ships.

2. **Exact current Windows-side Postgres 18 config file paths and Firewall state cannot be verified from this WSL research session.**
   - What we know: Standard install paths and standard `pg_hba.conf`/Firewall requirements per generic guides (see Pitfall 4).
   - What's unclear: The actual paths/values on this specific machine's Postgres 18 install, and whether any inbound-5432 firewall rule already exists from a prior, unrelated setup attempt.
   - Recommendation: The plan should include a verification step (run from a Windows admin shell, not WSL) as its first task, rather than assuming generic doc paths are exactly correct.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `python3.12` (WSL-native) | D-01 venv recreation | ✓ [VERIFIED: shell probe this session] | 3.12.13 (via `uv`) | — |
| `uv` | Optional faster venv bootstrap | ✓ [VERIFIED: shell probe this session] | 0.11.30 | Plain `python3.12 -m venv` |
| Node (via nvm) | D-01 vite/SvelteKit | ✓ [VERIFIED: shell probe this session, and confirmed in CONTEXT.md] | v24.18.0 | — |
| `ip` (iproute2) | Pattern 2 host-IP resolution | ✓ [VERIFIED: shell probe this session] | (Ubuntu base install) | — |
| `pg_isready` / `psql` (postgresql-client) | Optional stronger Postgres readiness check | ✗ [VERIFIED: `dpkg -l \| grep -i postgresql` returned nothing this session] | — | bash `/dev/tcp` TCP-reachability probe (see Standard Stack Alternatives) |
| Windows Postgres 18 service (`postgresql-x64-18`) | D-02 | Present but **stopped** [per CONTEXT.md; not independently re-verified from WSL — port 5432 unreachable from WSL this session, consistent with "stopped"] | 18 | — (this is the target service, no fallback) |
| `curl` | Health-check polling in Pattern 3 | ✓ [VERIFIED: shell probe this session] | (Ubuntu base install) | — |

**Missing dependencies with no fallback:**
- Windows Postgres service being started + reachable is the actual deliverable of D-02, not a pre-existing dependency to work around.

**Missing dependencies with fallback:**
- `pg_isready`/`psql` — TCP probe fallback is documented above and sufficient for this phase's scope.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest `>=8.0` [VERIFIED: requirements-dev.txt] with `pytest-asyncio>=0.23` |
| Config file | `pytest.ini` (repo root) [VERIFIED: pytest.ini] |
| Quick run command | `pytest -q` (bare invocation — currently the ONLY invocation shape that engages the isolation guard; this phase's fix must make this true for every invocation shape) |
| Full suite command | `pytest -q` (same command; `testpaths` already covers `tests pipeline/tests api/tests`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-03 (pytest isolation) | `TEST_DATABASE_URL` redirect fires and dev-DB row-count guard runs regardless of invocation shape (bare, explicit single file, explicit subset) | integration/regression | New test: invoke pytest as a subprocess with each of the three shapes against a scratch/fixture DB and assert `os.environ["DATABASE_URL"]` inside the child process resolved to the test DB, not the dev DB, for all three | ❌ Wave 0 — no existing test exercises multiple invocation shapes; today's tests run pytest itself only implicitly (via CI/manual runs), never as a subprocess-under-test |
| D-03 (single start/stop entry point) | Script starts Postgres-verify, alembic, uvicorn, vite in order; health checks pass; SIGINT/SIGTERM cleanly stops both processes | manual / smoke (not unit-testable in the traditional sense — this is an orchestration script, not application code) | Manual: run script, curl both health endpoints, Ctrl+C, verify both PIDs are gone (`ps aux \| grep -E 'uvicorn\|vite'`) | ❌ Wave 0 — no automated test framework naturally covers "did this shell script correctly manage OS processes"; this is appropriately a manual/smoke verification item, not a pytest test |
| D-02 (WSL→Windows Postgres reachable) | A WSL-native process can open a real DB connection to the Windows Postgres service using the dynamically-resolved host IP | integration | `python3.12 -c "..."` or a small pytest test that opens an asyncpg connection using the Pattern-2-resolved host and runs `SELECT 1` | ❌ Wave 0 — no existing test targets network reachability specifically (existing tests assume `DATABASE_URL` already works) |

### Sampling Rate
- **Per task commit:** `pytest -q` (bare) — must stay green throughout, and per D-03 must ALSO stay correct (not just green) under explicit-path invocations.
- **Per wave merge:** `pytest -q` full suite, PLUS a manual explicit-path invocation (`pytest api/tests/test_arguments.py -q`) with dev-DB row counts checked before/after — this is the actual regression check for the priority bug and cannot be fully automated inside the same pytest process that's being tested (a subprocess-based test, per the Phase Requirements → Test Map row above, is the closest automatable approximation).
- **Phase gate:** Full suite green under BOTH bare and explicit-path invocation shapes before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] New test file (name TBD by planner, e.g. `tests/test_pytest_isolation_invocation_shapes.py`) — subprocess-based test asserting the redirect fires for all three invocation shapes (bare, explicit single file, explicit multi-path)
- [ ] Small integration test asserting a live WSL→Windows-Postgres connection succeeds using the dynamically-resolved host IP (guards D-02's networking setup, not just D-03's redirect fix)
- [ ] No pytest-based coverage is appropriate for the start/stop script itself — document this explicitly as an intentional manual-only verification item in the plan, not a gap to "fill" with an inappropriate test

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Dev-tooling phase; no new auth surface |
| V3 Session Management | No | Not implicated |
| V4 Access Control | No | Not implicated — the existing `admin_token`/`environment` gate (CLAUDE.md Architecture Rule, `api/core/config.py:30-45`) is unchanged by this phase |
| V5 Input Validation | No | No new user-facing input surface |
| V6 Cryptography | No | Not implicated |
| V12 Network communication / attack surface (closest applicable, outside the standard ASVS-numbered list above) | Yes | Widening Postgres's `listen_addresses` and opening a Windows Firewall inbound rule for 5432 **increases the local network attack surface of a dev machine** — scope the `pg_hba.conf` rule as narrowly as possible (the actual WSL subnet, e.g. `172.26.32.0/20`, not a broad `172.0.0.0/8` some generic guides suggest) and scope the Windows Firewall rule to the same subnet if the Firewall UI supports a source-address restriction, rather than allowing 5432 from "Any" remote address. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Overly broad `pg_hba.conf`/Firewall rule (e.g. `0.0.0.0/0` or an unnecessarily large CIDR) exposes the dev Postgres instance to the whole LAN, not just this machine's own WSL VM | Elevation of Privilege / Information Disclosure | Scope both the `pg_hba.conf` host rule and the Windows Firewall inbound rule to the actual, currently-observed WSL subnet (`172.26.32.0/20` on this machine, verified this session — re-verify at execution time since it can shift) rather than a broad private-range default. This is a dev machine on a home/office network, not internet-facing, so the residual risk is LAN-scoped, not internet-scoped — proportionate mitigation, not a hard blocker. |
| A dev-only reset endpoint (`POST /api/admin/dev/reset-to-fixture`, Phase 43) reachable once the API is bound to `0.0.0.0` instead of `127.0.0.1` (uvicorn's `--host 0.0.0.0` is already present in the uncommitted `scripts/dev-start.ps1` diff and needed for D-01's WSL-native move so the Windows-side browser can reach it) | Elevation of Privilege | Already mitigated by the existing `environment == "development"` allow-list gate on the router (`api/main.py:41-42` [VERIFIED]) — this phase does not weaken that gate, but the planner should explicitly re-confirm the gate still applies after any settings/env changes this phase makes (it changes `DATABASE_URL`, not `ENVIRONMENT`, so no expected impact — call this out as a smoke-test item, not a code change). |

## Sources

### Primary (HIGH confidence — verified this session against this machine/repo directly)
- `tests/conftest.py`, `api/tests/conftest.py`, `pipeline/tests/conftest.py`, `pytest.ini`, `.env.gitignore` entries, `api/core/config.py`, `api/core/database.py`, `api/main.py`, `.planning/config.json`, `.venv/pyvenv.cfg`, `scripts/dev-start.ps1`, `app/vite.config.ts` (diff), `.dev-logs/*` — all read directly this session.
- Shell probes this session: `mount`/`df -T` (confirms 9p/DrvFs), `ip route show default` (confirms `172.26.32.1`, matches `/etc/resolv.conf`), `uv python list` (confirms Python 3.12.13 + 3.14.4 both present), `dpkg -l | grep postgresql` (confirms no postgresql-client installed), TCP probes to port 5432/8000 on the Windows host IP (confirms currently unreachable, consistent with the Postgres service being stopped).

### Secondary (MEDIUM confidence — official docs, not directly exercised against this exact Windows install)
- [Vite troubleshooting guide](https://vite.dev/guide/troubleshooting) — WSL2 file-watching guidance, quoted directly.
- [pytest customize/rootdir docs](https://docs.pytest.org/en/stable/reference/customize.html) — rootdir determination algorithm.
- [watchfiles / uvicorn settings](https://uvicorn.dev/settings/) — `--reload-exclude`/`WATCHFILES_FORCE_POLLING` semantics (retrieved via search summary; direct fetch timed out this session).
- [WSL2 networking docs, learn.microsoft.com](https://learn.microsoft.com/en-us/windows/wsl/networking) — mirrored vs NAT mode.

### Tertiary (LOW confidence — community guides, cross-referenced but not authoritative)
- Various WSL2+PostgreSQL setup gists/blog posts for `pg_hba.conf`/Firewall steps (Pitfall 4) — consistent across multiple independent sources but none specific to Postgres 18 or this exact Windows build.
- [github.com/microsoft/WSL/issues/12399](https://github.com/microsoft/WSL/issues/12399) — single user report on mirrored-mode failure reaching Windows-host services from WSL; informs the "don't switch to mirrored mode" recommendation (Pitfall 5) but is one anecdotal report, not a systematic study.

## Metadata

**Confidence breakdown:**
- pytest isolation fix mechanism: HIGH — root cause independently re-derived from reading the actual repo files, matches the todo's own empirical observations exactly, and is consistent with pytest's documented conftest-scoping model.
- WSL2 networking/filesystem mechanics: HIGH for what was directly probed this session (subnet, gateway IP, mount type, installed interpreters); MEDIUM for Windows-Postgres-service-specific config steps (paths/Firewall) since those require Windows-side action not available from this WSL research session.
- Dev-stack orchestration script pattern: HIGH — standard, well-understood bash patterns; no exotic dependencies.

**Research date:** 2026-08-12
**Valid until:** 30 days for the pytest/architecture guidance (stable); WSL2 host-IP/subnet specifics should be re-verified at execution time regardless of elapsed time, since CONTEXT.md and this research both flag it as reboot-sensitive, not calendar-sensitive.
