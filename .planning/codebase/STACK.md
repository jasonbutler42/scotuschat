# Technology Stack

**Analysis Date:** 2026-07-08

## Languages

**Primary:**
- Python 3.12 - Backend API and pipeline processing
- TypeScript 5.7 - SvelteKit frontend with full type safety
- JavaScript (module type) - Package management and build configuration

**Secondary:**
- SQL - PostgreSQL DDL via Alembic migrations

## Runtime

**Environment:**
- Node.js (version per `.nvmrc` or inferred from adapter)
- Python 3.12 (via `requirements.txt` and development environment)

**Package Manager:**
- npm (frontend) - `app/package.json`
- pip (backend) - `requirements.txt` and `requirements-dev.txt`
- Lockfile: npm (`app/package-lock.json`); pip (not explicitly locked, but pinned versions in requirements)

## Frameworks

**Core:**
- FastAPI 0.115+ - REST API server, lifespan context manager for async database setup
- SvelteKit 2.21.0 - Full-stack frontend framework with server load functions and form actions
- Svelte 5.30.0 - Component framework with Runes (no legacy stores)

**Adapter & Deployment:**
- @sveltejs/adapter-node 5.2.0 - SvelteKit adapter for Node.js (Digital Ocean App Platform compatible)

**Database:**
- SQLAlchemy 2.0 - Async ORM; uses `AsyncSession`, `async_sessionmaker`
- Alembic 1.13+ - DDL migrations (sole authority per CLAUDE.md constraint)
- asyncpg 0.29+ - Async PostgreSQL driver with statement_cache_size=0 for PgBouncer compatibility

**Testing:**
- pytest 8.0+ - Test runner
- pytest-asyncio 0.23+ - Async test support

**Build/Dev:**
- Vite 6.3.0 - Frontend build tool (via SvelteKit)
- TypeScript 5.7.0 - Type checking
- svelte-check 4.2.0 - Svelte component type validation
- TailwindCSS 3.4.0 - Utility-first CSS framework
- @tailwindcss/typography 0.5.0 - Typography plugin
- autoprefixer 10.4.0 - CSS vendor prefixing
- postcss 8.5.0 - CSS transformation
- Uvicorn 0.30+ - ASGI application server (entry point: `uvicorn api.main:app`)

## Key Dependencies

**Critical:**
- anthropic 0.40+ - Anthropic API SDK for claude-haiku-4-5-20251001 LLM calls in parse step
- instructor[anthropic] 2.x - Structured output via Pydantic for LLM validation
- tenacity 8.0+ - Exponential backoff retry strategy (outer layer for transient API errors)
- pdfplumber 0.11+ - PDF text extraction and parsing for oral argument transcripts

**Infrastructure:**
- psycopg2-binary 2.9+ - PostgreSQL C driver (fallback/compatibility)
- python-dotenv 1.0+ - .env file loading for local development
- pydantic-settings 2.0+ - Environment variable validation and type-checking
- httpx 0.27+ - Async HTTP client for SCOTUS website downloads
- boto3 1.34+ - AWS SDK for Digital Ocean Spaces S3-compatible file storage

**Frontend Components:**
- bits-ui 2.18.1 - Headless UI component primitives

## Configuration

**Environment:**
- `.env` file (local development) - Never committed to git; contains DATABASE_URL, ANTHROPIC_API_KEY, ADMIN_TOKEN, DO_SPACES_* credentials
- `pydantic-settings` BaseSettings class at `api/core/config.py` validates and provides type-checked access to env vars
- Database URL: `postgresql+asyncpg://user:pass@host/db` (parsed by SQLAlchemy)

**Build:**
- `svelte.config.js` - SvelteKit config with @sveltejs/adapter-node
- `app/tsconfig.json` - TypeScript compilation settings (SvelteKit-extended)
- `app/vite.config.ts` - Vite configuration for SvelteKit
- `alembic.ini` - Alembic migration configuration; script_location = `alembic/`

**Critical Settings:**
- `statement_cache_size=0` in SQLAlchemy `connect_args` (NOT top-level) — required for Digital Ocean PgBouncer in Transaction mode
- `expire_on_commit=False` in `AsyncSessionLocal` — prevents MissingGreenlet errors in async context
- `pool_size=5, max_overflow=10, pool_pre_ping=True` — connection pooling for async engine

## Platform Requirements

**Development:**
- Python 3.12 runtime
- PostgreSQL 16 (local or remote)
- Node.js and npm
- .env file with DATABASE_URL, ANTHROPIC_API_KEY, ADMIN_TOKEN, SESSION_SECRET, ADMIN_USERNAME, ADMIN_PASSWORD

**Production:**
- Digital Ocean App Platform
- PostgreSQL 16 (managed database or internal)
- FastAPI service for `api.main:app` (uvicorn)
- SvelteKit service (`@sveltejs/adapter-node`) compiled to `app/build/`
- DO Spaces S3-compatible bucket (for optional file uploads)
- Alembic migrations run before API startup (operator or CI/CD responsibility)

---

*Stack analysis: 2026-07-08*
