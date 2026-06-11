# Technology Stack

**Project:** SCOTUS Chat
**Researched:** 2026-06-11
**Overall confidence:** HIGH for core choices, MEDIUM for integration patterns, HIGH for pitfalls

---

## Recommended Stack

### Frontend — SvelteKit

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Svelte | 5.x (stable as of Oct 2024) | Reactive UI component model | Runes reactivity system is now stable; compile-time approach produces smaller bundles than React/Vue |
| SvelteKit | 2.x (currently ~2.43.x) | SSR, routing, server-side load functions | File-based routing, integrated SSR, server-only load functions eliminate a separate BFF layer |
| `@sveltejs/adapter-node` | latest | Node.js server target | Required for Digital Ocean App Platform; produces a standalone `build/` directory run with `node build` |
| TypeScript | 5.x | Type safety | SvelteKit scaffolds TypeScript by default; use it throughout |
| Vite | 6.x (bundled with SvelteKit) | Dev server + bundler | Comes with SvelteKit; no separate configuration needed |

**Svelte 5 note:** The Runes system (`$state`, `$derived`, `$effect`) is the current idiomatic approach. Do not use legacy Svelte 4 store patterns for new code. shadcn-svelte v1.0 now supports Svelte 5 if a component library is needed.

### Backend — FastAPI

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12 | Runtime | 3.12 is the safest practical choice: mature, well-supported, FastAPI tested against it |
| FastAPI | 0.115.x or latest stable | HTTP API layer | Pydantic v2 is default in 0.119+; async-native; automatic OpenAPI docs useful during development |
| Pydantic | v2 (bundled with FastAPI) | Request/response schema validation | v2 is 5-10x faster than v1; model_validate replaces from_orm |
| Uvicorn | 0.30.x+ | ASGI server (dev) | Standard for FastAPI dev; use with `--reload` in dev only |
| Gunicorn + Uvicorn workers | gunicorn 22.x | Process manager (production) | Digital Ocean App Platform uses a Procfile; Gunicorn manages worker lifecycle, Uvicorn handles ASGI |
| python-dotenv | 1.x | Environment config | Load `.env` files locally; App Platform injects env vars at runtime |

### Database Layer — PostgreSQL + ORM

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PostgreSQL | 16 (Digital Ocean managed) | Primary data store | Relational model fits entity structure; DO manages backups, failover |
| SQLAlchemy | 2.x (2.0+ async API) | ORM + query builder | Industry standard, excellent async support with 2.0 style, type-safe, works with Alembic |
| asyncpg | 0.29.x | Async PostgreSQL driver | Highest-performance async driver; used as SQLAlchemy's async dialect; outperforms psycopg3 in benchmarks for direct connections |
| psycopg2-binary | 2.9.x | Sync driver for Alembic | Alembic migration generation (`--autogenerate`) works better with a sync engine; use psycopg2 for that context only |
| Alembic | 1.13.x | Database migrations | Official SQLAlchemy migration tool; autogenerate compares models to DB schema |

**Driver rationale:** asyncpg is faster than psycopg3 for the async path (benchmarks consistently show this). Use asyncpg for the FastAPI application. Use psycopg2 for the sync Alembic context (Alembic docs recommend sync). Do not mix sync and async engines in the same request path.

**psycopg3 note:** psycopg3 is a viable alternative to asyncpg but shows lower throughput at scale. Choose it only if you need a single driver for both sync (Alembic) and async (app) paths, accepting the performance trade-off.

### Pipeline Libraries (Offline Processing)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| anthropic | 0.40.x+ (latest stable) | Claude API client | Official SDK; use `AsyncAnthropic` for async pipeline steps; includes streaming, retries |
| pdfplumber | 0.11.x | PDF text extraction | Better structural awareness than PyPDF2 for layout-sensitive content; character-level positioning helps with transcript formatting; SCOTUS transcripts have consistent structure |
| httpx | 0.27.x | External HTTP calls (Oyez API, FJC) | Async-native, replaces requests for async pipeline code; sync mode available for simple scripts |
| tenacity | 8.x | Retry logic for LLM calls | Handles 429/503 from Anthropic API; exponential backoff with jitter |
| python-ulid or uuid | stdlib | Pipeline run IDs | ULIDs are lexicographically sortable, useful for pipeline_run_id ordering |

**PDF library rationale:** SCOTUS transcripts are text-based PDFs (not scanned), so OCR is unnecessary. pdfplumber provides page-by-page text with positional metadata, which is useful if the parse step needs to reason about column breaks or speaker cues. pypdf (the maintained successor to PyPDF2) is faster but less layout-aware. Start with pdfplumber; it extracts better-structured text for LLM ingestion.

### Supporting Frontend Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `$app/stores`, `$app/navigation` | SvelteKit built-in | Page state, navigation | Always; prefer over external state managers |
| `$env/static/private` | SvelteKit built-in | Server-only secrets (API base URL, etc.) | All secrets that should never reach the browser |
| `$env/static/public` | SvelteKit built-in | Client-safe config (PUBLIC_API_URL) | Variables the browser legitimately needs |

---

## Integration Patterns

### SvelteKit → FastAPI: The Server-Side Proxy Pattern

**Do this:** Make all FastAPI API calls from SvelteKit's `+page.server.ts` or `+layout.server.ts` load functions, never directly from client-side `+page.svelte` components.

Why: Server-to-server calls have no CORS overhead, no preflight round-trips, and keep the FastAPI URL invisible to browser clients. The browser only talks to SvelteKit's Node server.

```
Browser → SvelteKit Node server (+page.server.ts) → FastAPI → PostgreSQL
```

**Pattern in practice:**
- `+page.server.ts` load function calls the FastAPI endpoint using `fetch()` (SvelteKit's built-in server fetch, which bypasses CORS)
- Return data as typed objects; SvelteKit serializes and hydrates automatically
- Set `PUBLIC_API_URL` (visible) or store the internal API URL only in server env vars

**Do not:** Export an `export const ssr = false` and call FastAPI directly from the browser with `fetch()`. This requires CORS headers on FastAPI, exposes the API URL, and makes every page visit a two-hop chain (browser → FastAPI) with preflight overhead.

**FastAPI CORS:** Configure `CORSMiddleware` only for development convenience (localhost:5173 → localhost:8000). In production, no CORS headers are needed if all calls go through SvelteKit server.

### Environment Variable Conventions (SvelteKit)

| Variable | Module | Example |
|----------|--------|---------|
| `API_URL` | `$env/static/private` | `http://localhost:8000` (server-only internal URL) |
| `PUBLIC_APP_NAME` | `$env/static/public` | `SCOTUS Chat` (safe for browser) |

Never put API keys or internal hostnames in `PUBLIC_` variables.

### FastAPI Project Structure

```
backend/
  app/
    api/
      v1/
        routes/
          cases.py
          arguments.py
          people.py
    core/
      config.py       # pydantic-settings Settings class
      database.py     # async engine, session factory
    models/           # SQLAlchemy ORM models
    schemas/          # Pydantic request/response models
    services/         # business logic, DB queries
  alembic/
    versions/
    env.py
  tests/
  main.py             # app = FastAPI(); include routers
  requirements.txt
```

Keep routers thin: route → service → DB. Business logic lives in services, not in route handlers.

### Database Session Lifecycle (FastAPI + SQLAlchemy async)

Use a FastAPI dependency to manage session lifecycle:

```python
# core/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

Using `expire_on_commit=False` is mandatory in async SQLAlchemy — otherwise SQLAlchemy tries to lazy-load expired attributes after commit, which triggers a sync DB call and raises `MissingGreenlet` errors.

### Alembic Configuration for Async App

Alembic requires a sync connection to generate migrations. Configure `env.py` to use psycopg2 for autogenerate, separate from the app's asyncpg engine:

```python
# alembic/env.py — synchronous context for autogenerate
def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    # sqlalchemy.url in alembic.ini points to postgresql:// (psycopg2), not postgresql+asyncpg://
```

Load `sqlalchemy.url` from environment at runtime — never hardcode it in `alembic.ini`.

### Pipeline Design

The pipeline runs offline (CLI scripts, not API endpoints). Each step:
1. Reads from DB (prior step's output or source data)
2. Calls external service (Claude API, Oyez, etc.)
3. Writes results to DB linked to a `pipeline_run_id`
4. Is idempotent: re-running creates new rows; promotion step swaps which run_id is active

Use direct `asyncio.run()` entry points for each step script rather than importing FastAPI app machinery.

---

## Digital Ocean App Platform Deployment

### Architecture

```
DO App Platform
├── SvelteKit service (Node.js)    ← runs: node build, port 3000
├── FastAPI service (Python)       ← runs: gunicorn -k uvicorn.workers.UvicornWorker
└── Managed PostgreSQL (database component)
```

### SvelteKit Service Configuration

- **Adapter:** `@sveltejs/adapter-node` (not `adapter-auto`, not `adapter-static`)
- **Build command:** `npm run build`
- **Run command:** `node build`
- **Port:** 3000 (adapter-node default)
- Remove `@sveltejs/adapter-auto` from devDependencies after switching
- Environment variables injected at runtime by App Platform; `$env/dynamic/private` works for runtime-only vars if needed

### FastAPI Service Configuration

- **Procfile:**
  ```
  web: gunicorn app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
  ```
- **`requirements.txt`** must be present at repo root or service root
- Use `$PORT` — App Platform injects this; do not hardcode 8000 in production
- `--workers 2` for a starter instance (1 vCPU); increase with instance size

### PostgreSQL Connection Pooling

Digital Ocean Managed PostgreSQL exposes a PgBouncer-based connection pool. Use it.

- Default PostgreSQL max connections: 25 (shared-tier) or 100 (basic-tier)
- PgBouncer pool mode: **Transaction mode** (recommended for web apps)
- Connection string format from DO: `postgresql://user:pass@host:port/pool_name?sslmode=require`
- For asyncpg: `postgresql+asyncpg://user:pass@host:port/pool_name`
- **Prepared statements conflict with Transaction-mode PgBouncer.** Disable them in asyncpg:

  ```python
  engine = create_async_engine(
      settings.database_url,
      connect_args={"statement_cache_size": 0},  # disables asyncpg prepared stmt cache
  )
  ```

  This is a silent, critical failure mode: connections will succeed but queries will fail or return wrong results under PgBouncer Transaction mode without this setting.

### Service Communication (Internal)

On App Platform, services within the same app communicate via internal hostnames. Set `API_URL` (server-only env var in SvelteKit service) to the FastAPI service's internal hostname (e.g., `http://fastapi-service:8080`) to avoid external round-trips.

---

## Alternatives Considered (and Rejected)

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Frontend adapter | `adapter-node` | `adapter-static` | Static export cannot run server-side load functions; eliminates the SSR proxy pattern |
| Async PG driver | asyncpg | psycopg3 | psycopg3 is slower in benchmarks; asyncpg is the established default for SQLAlchemy async on PostgreSQL |
| ORM | SQLAlchemy 2.0 | SQLModel | SQLModel is a thin wrapper; SQLAlchemy 2.0's native API is equally ergonomic and better documented |
| Migrations | Alembic | manual SQL | Alembic autogenerate is essential for safe schema evolution without manual diff tracking |
| PDF extraction | pdfplumber | pymupdf (fitz) | pymupdf is C-based and faster, but pdfplumber's text layout fidelity is better for structured transcripts; revisit if performance becomes an issue |
| Pipeline concurrency | asyncio per-step | Celery/task queue | Offline pipeline; no queue infrastructure needed; asyncio is sufficient |
| Python version | 3.12 | 3.11 | 3.12 has faster startup, better error messages, and is the current LTS target for most libraries |

---

## Version Matrix (Install Reference)

```bash
# SvelteKit (frontend)
npm create svelte@latest scotuschat-web
npm install
npm install -D @sveltejs/adapter-node

# FastAPI (backend + pipeline)
pip install fastapi[standard]>=0.115     # includes uvicorn, httpx, pydantic v2
pip install sqlalchemy>=2.0
pip install asyncpg>=0.29
pip install alembic>=1.13
pip install psycopg2-binary>=2.9         # sync driver for Alembic only
pip install anthropic>=0.40
pip install pdfplumber>=0.11
pip install httpx>=0.27
pip install tenacity>=8.0
pip install python-dotenv>=1.0
pip install gunicorn>=22.0               # production process manager
```

Use `pip install fastapi[standard]` — this installs FastAPI with its optional performance extras (uvicorn, email-validator, etc.) in a single command.

---

## Sources

- SvelteKit official docs: https://svelte.dev/docs/kit
- SvelteKit adapter-node docs: https://svelte.dev/docs/kit/adapter-node
- FastAPI production docs: https://fastapi.tiangolo.com/deployment/versions/
- FastAPI best practices (community): https://github.com/zhanymkanov/fastapi-best-practices
- SQLAlchemy 2.0 async + asyncpg: https://leapcell.io/blog/building-high-performance-async-apis-with-fastapi-sqlalchemy-2-0-and-asyncpg
- asyncpg vs psycopg3 comparison: https://goldlapel.com/grounds/django-python/asyncpg-vs-psycopg3-fastapi
- Alembic + FastAPI guide (2025): https://blog.greeden.me/en/2025/08/12/no-fail-guide-getting-started-with-database-migrations-fastapi-x-sqlalchemy-x-alembic/
- Digital Ocean App Platform SvelteKit: https://blakedeckard.com/deploy-sveltekit-to-digital-ocean-app-platform
- DO managed PostgreSQL connection pools: https://docs.digitalocean.com/products/app-platform/how-to/connect-pg-pools/
- Anthropic Python SDK: https://github.com/anthropics/anthropic-sdk-python
- pdfplumber GitHub: https://github.com/jsvine/pdfplumber
- PDF extractor comparison (2025): https://onlyoneaman.medium.com/i-tested-7-python-pdf-extractors-so-you-dont-have-to-2025-edition-c88013922257
- FastAPI connection pool pitfalls: https://blog.venturemagazine.net/the-fastapi-dependency-injection-bug-that-leaked-database-connections-5-minute-fix-26082bb4bacf
