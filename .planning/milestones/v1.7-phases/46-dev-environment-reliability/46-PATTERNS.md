# Phase 46: Dev Environment Reliability - Pattern Map

**Mapped:** 2026-08-12
**Files analyzed:** 7 (new/modified)
**Analogs found:** 6 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `./conftest.py` (NEW, root) | test-config / event-driven (pytest hooks) | event-driven | `tests/conftest.py` (current, being relocated) | exact — this is a verbatim relocation, not a new pattern |
| `tests/conftest.py` (MODIFIED — shrink/empty) | test-config | event-driven | `./conftest.py` (post-move) | exact |
| `api/tests/conftest.py` (MODIFIED — add fail-closed assertion) | test-config / fixture | request-response (fixture setup) | itself (existing `_db_configured()` + `_api_lifespan` autouse fixture) | exact |
| `pipeline/tests/conftest.py` (MODIFIED — add fail-closed assertion) | test-config / fixture | request-response (fixture setup) | itself (existing `_reset_test_db` autouse fixture, same guard idiom) | exact |
| `scripts/dev-start.sh` (NEW) | utility / orchestration script | event-driven (process lifecycle) + request-response (health polling) | `scripts/dev-start.ps1` (logic/ordering to port) + `scripts/provision_test_db.py` (DB-URL-parsing/guard idiom in Python, cross-language reference only) | role-match (cross-language: PowerShell → bash) |
| `scripts/dev-start.ps1` (MODIFIED — thin WSL wrapper, or deleted) | utility / orchestration script | event-driven | itself (current PowerShell version) | exact |
| `.planning/config.json` (`workflow.test_command`) | config | — | itself (`test_command` field, current value) | exact |
| `app/vite.config.ts` (MODIFIED — add polling watch config, optional) | config | — | itself (current `server` block) | exact |

## Pattern Assignments

### `./conftest.py` (NEW — root-level test config, event-driven pytest hooks)

**Analog:** `tests/conftest.py` (verbatim relocation target — read in full above)

This is not a "similar pattern," it is the literal source of truth to move. Per RESEARCH.md's root-cause analysis: pytest's conftest.py discovery is strictly hierarchical (ancestor-to-descendant), so a conftest.py at `tests/` (a sibling of `api/tests/` and `pipeline/tests/`) is never loaded when explicit paths under those siblings are passed to pytest. The fix is relocating this file's content to the pytest rootdir (repo root, alongside `pytest.ini`), which is always an ancestor of every `testpaths` entry.

**Imports pattern** (from `tests/conftest.py` lines 13-15):
```python
import os

from dotenv import load_dotenv
```

**Core pattern — redirect + capture-before-override** (`tests/conftest.py` lines 17-36):
```python
load_dotenv()

_REAL_DATABASE_URL = os.environ.get("DATABASE_URL")

if os.environ.get("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
```
Critical ordering constraint carried over as a comment: this must execute before any module imports `api.core.config.settings` — pytest's collection order guarantees this only when the file lives at rootdir.

**Shared guard idiom** (`tests/conftest.py` lines 39-41, identical to `api/tests/conftest.py` lines 19-22):
```python
def _db_configured(url: str | None) -> bool:
    """Same placeholder guard every DB-gated fixture in this suite uses."""
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"
```

**Event-driven hook pattern — session guard** (`tests/conftest.py` lines 44-135, `pytest_sessionstart`/`pytest_sessionfinish`): move verbatim. Uses `_REAL_DATABASE_URL` (captured before redirect) to snapshot/recheck `people`/`arguments` row counts and raise `AssertionError` on mismatch — this is the existing "tripwire" layer; RESEARCH.md's Pattern 1 additionally recommends adding a `pytest_configure(config)` hook here that sets a sentinel (`config._scotus_redirect_fired = True`) so sibling conftests can fail closed if this file is ever not collected:
```python
def pytest_configure(config):
    config._scotus_redirect_fired = True
```

**Error handling pattern:** no try/except — deliberately raises `AssertionError` on leak detection (fail loud, not fail soft). Preserve this.

---

### `tests/conftest.py` (MODIFIED — shrinks after move)

**Analog:** the post-move `./conftest.py` above; there is no other tests/-specific logic in this file today (verified — the entire file is the redirect + guard being relocated). Likely becomes empty or is deleted; if anything genuinely tests/-local remains, it should import nothing that depends on collection order.

---

### `api/tests/conftest.py` (MODIFIED — optional fail-closed assertion)

**Analog:** itself — extend the existing pattern, do not replace it.

**Existing imports** (lines 14-16):
```python
import os

import pytest_asyncio
```

**Existing guard + autouse fixture pattern** (lines 19-44) — unchanged, still correct per RESEARCH.md ("this guard is fine as-is; it reads whatever `DATABASE_URL` resolves to *after* the redirect has had a chance to run"):
```python
def _db_configured() -> bool:
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


@pytest_asyncio.fixture(autouse=True)
async def _api_lifespan():
    if not _db_configured():
        yield
        return
    from api.core.database import lifespan
    from api.main import app

    async with lifespan(app):
        yield
```

**Fail-closed addition (defense-in-depth, RESEARCH.md Pattern 1):** add an assertion inside `_api_lifespan` (or a new autouse fixture ahead of it) that the root conftest's sentinel fired before any DB-gated test runs:
```python
assert getattr(request.config, "_scotus_redirect_fired", False), (
    "Root conftest.py redirect did not fire — refusing to run DB-gated "
    "api/tests against a possibly-unredirected DATABASE_URL."
)
```
Note: this requires adding a `request` (or `pytestconfig`) parameter to the fixture signature — follow the existing `pytest_asyncio.fixture` decorator convention already used in this file.

---

### `pipeline/tests/conftest.py` (MODIFIED — optional fail-closed assertion)

**Analog:** itself — same idiom family as `api/tests/conftest.py`, follow the existing `_reset_test_db` autouse-fixture guard style (lines 131-190), specifically its own internal guard pattern:
```python
test_url = os.getenv("TEST_DATABASE_URL", "")
if not test_url:
    yield
    return

if make_url(test_url).database != "scotus_test":
    yield
    return
```
This "no-op unless explicitly satisfied" idiom is the established local convention for safety guards in this file — the fail-closed sentinel check should follow the same no-op-unless-satisfied shape, but inverted (raise, not no-op) since RESEARCH.md's requirement is "fail loud if the redirect didn't fire," not "silently skip."

**Imports already present** (lines 20-24) — no new imports needed beyond what a sentinel check requires (`pytest` is already imported at line 22 for `pytest.fixture`/`pytest.skip`).

---

### `scripts/dev-start.sh` (NEW — WSL-native bash orchestration script)

**Analog:** `scripts/dev-start.ps1` for the *ordering/intent* (this is the direct functional predecessor being replaced per D-01/D-03), cross-referenced against `scripts/provision_test_db.py` for the project's established DB-URL-parsing and safety-guard idioms (Python, but the "parse the connection string, validate before acting, never silently fall back to the dev DB" idiom should carry over into the bash script's Postgres-reachability check).

**Full current PS1 logic to port** (`scripts/dev-start.ps1`, entire file, 63 lines):
1. Start Postgres if not running (`pg_ctl status` / `pg_ctl start`) → **replaced per D-02** with a network reachability probe against the Windows Postgres service (no start/stop management — RESEARCH.md's Architecture Responsibility Map assigns "verify reachability, not manage the service process" to the script).
2. `Push-Location $REPO_ROOT` then `alembic upgrade head`, checking `$LASTEXITCODE`, with an explicit error message and non-zero exit on failure (lines 19-27) — port this fail-fast idiom directly:
```powershell
alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Alembic migration failed. Check your DATABASE_URL in .env and ensure Postgres is running." -ForegroundColor Red
    Pop-Location
    exit 1
}
```
→ bash equivalent (`set -euo pipefail` plus explicit check, matching RESEARCH.md's Pattern 3):
```bash
if ! alembic upgrade head; then
  echo "ERROR: Alembic migration failed. Check your DATABASE_URL in .env and ensure Postgres is reachable." >&2
  exit 1
fi
```
3. Background `uvicorn api.main:app --host 0.0.0.0 --reload --port 8000` (line 33) — port directly, adding `--reload-exclude '.claude/worktrees/*'` per CONTEXT.md's stray-worktree-noise fix and RESEARCH.md Pattern 3.
4. Background `npm run dev` from `app/` (lines 38-41) — port directly with `cd app && npm run dev &`.
5. Combined-output loop + `finally`-block cleanup (`Stop-Job`/`Remove-Job`, lines 52-63) — this is the PS1 analog of bash's `trap cleanup INT TERM EXIT`; port the *intent* (always stop both background processes on exit/interrupt), not the PowerShell job-object mechanics.

**DB-URL / safety-guard idiom to borrow from `scripts/provision_test_db.py`** (lines 43-57, 129-139) — even though this is Python and the new script is bash, the project convention it establishes should carry over conceptually: parse/derive the target DB name from the connection string and explicitly compare against the dev DB before doing anything DB-adjacent, refusing loudly rather than silently proceeding:
```python
dev_url = os.environ.get("DATABASE_URL", "")
if dev_url:
    dev_db = make_url(dev_url).database
    if target_db == dev_db:
        print("ERROR: ... Refusing to provision over the shared dev database.", file=sys.stderr)
        sys.exit(1)
```
Apply the same "never silently assume, refuse loudly" posture in the bash script's Postgres reachability probe and host-IP resolution (RESEARCH.md Pattern 2 already specifies this: `if [ -z "$WIN_HOST_IP" ]; then echo "ERROR: ..." >&2; exit 1; fi`).

**Error handling pattern:** PS1 uses `-ForegroundColor Red`/`Yellow`/`Green` for visual severity and explicit `exit 1` on the one checked failure path (Alembic). Bash equivalent: `set -euo pipefail` for implicit fail-fast on every command, plus explicit `>&2`-directed error messages with `exit 1` for the two checkpoints RESEARCH.md identifies (host-IP resolution failure, Postgres unreachable).

---

### `scripts/dev-start.ps1` (MODIFIED — thin wrapper or deleted)

**Analog:** itself (current file, read in full above). If kept as a thin wrapper (CONTEXT.md/RESEARCH.md leave this as planner's discretion), the replacement content is a single `wsl.exe` invocation, discarding everything except the top-of-file usage comment convention (`# Usage: .\scripts\dev-start.ps1` → update to describe the wrapper's new behavior).

---

### `.planning/config.json` (MODIFIED — `workflow.test_command`)

**Analog:** itself, current field (line 14):
```json
"test_command": "./.venv/Scripts/python.exe -m pytest",
```
Must become the WSL-native equivalent, matching the new `.venv` layout (`bin/` not `Scripts/`):
```json
"test_command": "./.venv/bin/python -m pytest",
```
No other fields in this file are implicated by this phase — `build_command` (line 15, `python3 -m compileall -q pipeline api scripts tests alembic`) already uses a bare `python3` invocation with no venv-path assumption baked in, so it does not need to change, but the planner should verify `python3` on the WSL-native path resolves to 3.12 in context (RESEARCH.md flags that bare `python3` on this WSL distro is 3.14.4, not 3.12 — the *venv's* `bin/python` will correctly be 3.12, but `build_command`'s bare `python3` will not unless the venv is activated first when this command runs).

---

### `app/vite.config.ts` (MODIFIED — optional DrvFs polling mitigation)

**Analog:** itself, current `server` block (lines 4-11):
```typescript
export default defineConfig({
	plugins: [sveltekit()],
	server: {
    	host: true,        // listen on all addresses (0.0.0.0), i.e. LAN-accessible
    	port: 5173,        // optional — pins the port instead of auto-incrementing
		strictPort: true,  // always fail if the port is already in use, instead of trying the next free port
  	},
});
```
Note the file's existing mixed tabs/spaces indentation (tab before `host`/`port`/`strictPort`, spaces elsewhere) — match this exactly rather than reformatting, to keep the diff minimal. Per RESEARCH.md Pitfall 3, the addition is a `watch.usePolling` key inside the same `server` object:
```typescript
server: {
    	host: true,
    	port: 5173,
		strictPort: true,
		watch: {
			usePolling: true,
		},
  	},
```
Corresponding uvicorn-side env var (not a file change, but the same mitigation tier): `WATCHFILES_FORCE_POLLING=true`, set in the new `scripts/dev-start.sh` before backgrounding uvicorn, not hardcoded into `.env` (RESEARCH.md explicitly separates "runtime tool config" fixes like this from `.env`-level settings).

## Shared Patterns

### DB-connection-string parsing / safety-guard idiom
**Source:** `scripts/provision_test_db.py` lines 43-57, 121-139; mirrored in `pipeline/tests/conftest.py` lines 147-159
**Apply to:** `scripts/dev-start.sh`'s Postgres reachability check and any new health-check code that opens its own connection
**Pattern:** never assume a connection string variable is correct without deriving/comparing the database name explicitly; refuse loudly (`exit 1` / raise) rather than falling back silently to whatever `DATABASE_URL` happens to already be.

### `statement_cache_size=0` on every ad-hoc engine
**Source:** `tests/conftest.py` lines 66-68 and 106-109; `pipeline/tests/conftest.py` lines 65-67 and 161-166; `api/core/database.py` (per RESEARCH.md line references)
**Apply to:** any new health-check/connectivity-probe code in `scripts/dev-start.sh` (if it shells out to `python3.12 -c "..."` to open an asyncpg/SQLAlchemy connection rather than a pure bash TCP probe) — must carry `connect_args={"statement_cache_size": 0}` for consistency with the rest of the codebase per CLAUDE.md's hard constraint, even though local dev has no PgBouncer.

### `load_dotenv()` before any env-var read
**Source:** `tests/conftest.py` line 19; `pipeline/tests/conftest.py` line 27; `scripts/provision_test_db.py` line 108
**Apply to:** any new Python code this phase adds (there is no bare `os.environ` read anywhere in this codebase without a preceding `load_dotenv()` in the same module/entrypoint).

### Fail-fast / no-default-credential guard
**Source:** `api/core/config.py` lines 30-33, 35-45 (`admin_token: str`, `environment: str` — both required, no default, comment: "app refuses to start without this set")
**Apply to:** conceptually applicable to the new `./conftest.py`'s fail-closed sentinel assertion — the project convention favors "refuse loudly on missing required config" over silent defaults.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.venv/` (recreated WSL-native) | build artifact | file-I/O | Not source code — no code pattern to map; this is an environment-recreation step (`python3.12 -m venv .venv` or `uv venv --python 3.12`), fully specified in RESEARCH.md's Standard Stack/Code Examples, no codebase analog applicable. |

## Metadata

**Analog search scope:** `tests/`, `api/tests/`, `pipeline/tests/`, `scripts/`, `api/core/`, repo root (`pytest.ini`, `.planning/config.json`), `app/` (vite config only — no `app/src` changes in this phase)
**Files scanned:** `tests/conftest.py`, `api/tests/conftest.py`, `pipeline/tests/conftest.py`, `pytest.ini`, `scripts/dev-start.ps1`, `scripts/provision_test_db.py`, `api/core/config.py`, `app/vite.config.ts`, `.planning/config.json`
**Pattern extraction date:** 2026-08-12
