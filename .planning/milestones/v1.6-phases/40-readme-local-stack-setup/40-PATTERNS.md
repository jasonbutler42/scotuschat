# Phase 40: README - How to Start the Local Stack - Pattern Map

**Mapped:** 2026-07-14
**Files analyzed:** 4 new/modified files
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `README.md` | documentation | procedural/file-I/O | `README.md`, `scripts/dev-start.ps1`, `CLAUDE.md` | role-match (existing document plus runtime contracts) |
| `.env.example` | config | environment-to-process | `.env.example`, `api/core/config.py` | exact |
| `app/.env.example` | config | environment-to-process | `.env.example`, `app/src/routes/admin/login/+page.server.ts`, `app/src/lib/server/session.ts` | role-match |
| `.gitignore` | config | file-I/O filtering | `.gitignore`, `app/.gitignore` | exact |

## Pattern Assignments

### `README.md` (documentation, procedural/file-I/O)

**Analogs:** `README.md`, `scripts/dev-start.ps1`, `CLAUDE.md`

**Preserved attribution pattern** (`README.md` lines 3-22):

```markdown
## Attribution / Credits

Some oral arguments on this site come from a historical bulk import rather
than direct PDF ingestion. This project credits the sources that made that
import possible:
...
See `/attributions` on the live site for the full attribution and licensing
page.
```

Keep this section and its links/citations intact. Add contributor setup before it so the README leads with how to run the project without displacing attribution.

**Portable recurring-start contract** (`scripts/dev-start.ps1` lines 5-22, 29-47):

```powershell
$REPO_ROOT = Split-Path -Parent $PSScriptRoot
$PGDATA = "$REPO_ROOT\data\pgdata"
$PGBIN = "$REPO_ROOT\data\pgsql\bin"
& "$PGBIN\pg_ctl" start -D $PGDATA -l "$PGDATA\logfile"
...
alembic upgrade head
...
uvicorn api.main:app --reload --port 8000
...
Set-Location "$using:REPO_ROOT\app"
npm run dev
```

Document this script only after the one-time bootstrap. State that the virtual environment must be active because the script resolves `alembic` and `uvicorn` from `PATH`. Preserve the canonical paths and ports: portable PostgreSQL under `data/pgsql/bin` with cluster data under `data/pgdata`, FastAPI on 8000, and SvelteKit on 5173.

**Stack/version and architecture wording** (`CLAUDE.md` lines 24-40, 55-59):

```markdown
- **Alembic is the sole DDL authority.** Never call `Base.metadata.create_all` anywhere.
| Frontend | SvelteKit 2.x / Svelte 5 (Runes — no legacy stores) |
| Backend | FastAPI 0.115+ with Pydantic v2 |
| Database | PostgreSQL 16, SQLAlchemy 2.0 async, Alembic migrations |
| Pipeline | Python 3.12, pdfplumber, Anthropic SDK, instructor, tenacity |
...
All FastAPI calls from SvelteKit go through `+page.server.ts` server load functions —
`FASTAPI_BASE_URL` is a server-only env var, never `PUBLIC_`.
```

Use these declarations as the prerequisite and security-boundary source of truth. Migration examples must use Alembic; do not introduce direct schema creation.

**Health verification pattern** (`api/main.py` lines 40-43):

```python
@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

The verification checklist should test `http://localhost:8000/health` for `{"status":"ok"}`, then public UI at `http://localhost:5173`, and finally `/admin/login` with the configured frontend credentials.

**Optional test-database pattern** (`scripts/provision_test_db.py` lines 81-92, 108-117):

```python
env = {**os.environ, "DATABASE_URL": test_url}
subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    env=env,
    check=True,
)
...
test_url = os.environ.get("TEST_DATABASE_URL", "")
if not test_url:
    print("ERROR: TEST_DATABASE_URL is not set...", file=sys.stderr)
    sys.exit(1)
```

Keep `python scripts/provision_test_db.py` explicitly optional and explain that `TEST_DATABASE_URL` must be configured first. Likewise, keep `python -m pipeline import-justices` as optional first content, not part of a healthy empty-stack definition.

### `.env.example` (config, environment-to-process)

**Analog:** current `.env.example` plus `api/core/config.py`

**Backend grouping pattern** (`api/core/config.py` lines 11-33, 35-55):

```python
class Settings(BaseSettings):
    database_url: str
    test_database_url: str = ""
    anthropic_api_key: str = ""
    debug: bool = False
    admin_token: str
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    do_spaces_bucket: str = ""
    do_spaces_endpoint: str = ""
    do_spaces_region: str = ""
```

Mirror this backend ownership and required/optional distinction. Retain placeholder-only values. Minimum local stack: `DATABASE_URL` and `ADMIN_TOKEN`; optional groups: LLM parsing (`ANTHROPIC_API_KEY`), test DB (`TEST_DATABASE_URL`), object storage, and deployment-only settings. Remove SvelteKit-owned `SESSION_SECRET`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD` from the root example.

**Loading boundary** (`api/core/config.py` lines 71-74):

```python
model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
)
```

The root example documents the repository-root `.env` loaded by Python. Keep the async FastAPI URL shape already used at `.env.example` line 2 and explain any Alembic sync-driver distinction without putting real credentials in the file.

### `app/.env.example` (config, environment-to-process)

**Analogs:** `.env.example`, `app/src/routes/admin/login/+page.server.ts`, `app/src/lib/server/session.ts`

**Server-private import pattern** (`app/src/routes/admin/login/+page.server.ts` lines 1-5):

```typescript
import { ADMIN_USERNAME, ADMIN_PASSWORD } from '$env/static/private';
import { signSession, SESSION_COOKIE_NAME, sessionCookieOptions } from '$lib/server/session';
```

**Session secret pattern** (`app/src/lib/server/session.ts` lines 1-2, 27-30):

```typescript
import { SESSION_SECRET } from '$env/static/private';
...
const hmacHex = createHmac('sha256', SESSION_SECRET).update(payload).digest('hex');
```

Create a placeholder-only SvelteKit example containing exactly the runtime boundary requested by the phase: `FASTAPI_BASE_URL`, `ADMIN_TOKEN`, `SESSION_SECRET`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD`. Use comments to state that all are server-private and must never receive a `PUBLIC_` prefix. State that `ADMIN_TOKEN` must exactly match the root `.env` value. Preserve `app/.gitignore`'s exception for this committed example.

### `.gitignore` (config, file-I/O filtering)

**Analog:** current `.gitignore`

**Local generated-directory grouping** (`.gitignore` lines 1-5, 18-25):

```gitignore
# Environment variables — never commit secrets
.env

# Postgres data directory (lives inside repo, gitignored — easy to nuke and recreate)
data/pgdata/
...
.venv/
venv/
```

Add `data/pgsql/` next to `data/pgdata/` under the PostgreSQL comment. This follows the existing directory-level trailing-slash convention and prevents the documented portable binary extraction from dirtying the worktree. Do not broaden ignores for checked-in examples; `app/.gitignore` lines 6-8 intentionally ignore real app env files while allowing `app/.env.example`.

## Shared Patterns

### Environment Ownership and Secret Boundaries

**Sources:** `api/core/config.py` lines 71-74; `app/src/routes/admin/login/+page.server.ts` lines 1-5; `CLAUDE.md` lines 57-59

- Root `.env` belongs to Python/FastAPI/PostgreSQL.
- `app/.env` belongs to SvelteKit server code.
- `ADMIN_TOKEN` is intentionally duplicated and must match across both files.
- `FASTAPI_BASE_URL`, admin credentials, token, and session secret remain server-only; never document `PUBLIC_` variants.
- Generate `ADMIN_TOKEN` and `SESSION_SECRET` independently with Python's `secrets.token_urlsafe(32)`; examples contain placeholders, never generated values.

### Command Ownership

**Sources:** `scripts/dev-start.ps1` lines 19-40; `app/package.json` lines 5-10; `api/main.py` lines 1-7

- Run Python commands from repository root with `.venv` active.
- Prefer `python -m alembic` and `python -m uvicorn` in manual instructions to bind tools to the active interpreter.
- Run `npm ci` and `npm run dev` from `app/`.
- Treat `scripts/dev-start.ps1` as recurring start-time orchestration, not installation or initialization.

### Verification and Safety

- Static verification should grep for required variable names and documented ports, confirm examples contain no concrete secrets, and run `npm run check` where dependencies are available.
- Runtime verification should use an isolated/non-production database cluster, migrate to Alembic head, verify `/health`, render the public UI, and complete an admin login.
- Portable PostgreSQL initialization must use explicit password/host authentication; do not recommend `trust` for shared machines.

## No Analog Found

None. The new `app/.env.example` has no same-path committed predecessor, but its exact variables and private-loading behavior have strong role-matched analogs in the current root example and SvelteKit server consumers.

## Metadata

**Analog search scope:** repository root, `api/`, `app/`, `scripts/`, `pipeline/`, and relevant planning history
**Files scanned in detail:** 14
**Pattern extraction date:** 2026-07-14
