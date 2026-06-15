# Technology Stack

**Analysis Date:** 2026-06-15

## Languages

**Primary:**
- TypeScript 5.7.0 - Frontend (SvelteKit/Svelte application in `/app/src`)
- Python 3.12+ - Backend API and pipeline scripts (`/api` and `/pipeline`)

**Secondary:**
- JavaScript - SvelteKit configuration files, PostCSS config

## Runtime

**Environment:**
- Node.js (for SvelteKit frontend build and dev server)
- Python 3.12+ (for FastAPI backend and CLI pipeline; codebase tested with Python 3.14.4)

**Package Manager:**
- npm (Node.js packages for `/app`)
  - Lockfile: `app/package-lock.json` (present)
- pip (Python packages via `requirements.txt` and `requirements-dev.txt`)
  - Virtual environment: `.venv/` directory present

## Frameworks

**Core:**
- SvelteKit 2.21.0 - Full-stack meta-framework for frontend (includes Vite)
- Svelte 5.30.0 - Component framework (using Runes, no legacy stores)
- FastAPI 0.115+ - Async HTTP API framework for backend (`api/main.py`)

**Styling:**
- Tailwind CSS 3.4.0 - Utility-first CSS framework for frontend styling
- PostCSS 8.5.0 - CSS transformation tool (configured in `app/postcss.config.js`)
- @tailwindcss/typography 0.5.0 - Typography plugin for Tailwind

**Testing:**
- pytest 8.0+ - Python test runner
- pytest-asyncio 0.23+ - Async test support for Python
- svelte-check 4.2.0 - Svelte language server type checking

**Build/Dev:**
- Vite 6.3.0 - Build tool and dev server (configured in `app/vite.config.ts`)
- @sveltejs/vite-plugin-svelte 5.0.0 - Svelte compiler integration for Vite
- @sveltejs/adapter-node 5.2.0 - Production adapter for SvelteKit (Node.js server)
- @sveltejs/kit 2.21.0 - SvelteKit framework runtime
- esbuild - JavaScript bundler (dependency of Vite)

## Key Dependencies

**Critical:**
- sqlalchemy 2.0+ - Async ORM for Python (`api/core/database.py`, model definitions in `api/models/models.py`)
  - Uses `SQLAlchemy.ext.asyncio` for async support with AsyncSession
- asyncpg 0.29+ - PostgreSQL async driver for Python
  - Requires `statement_cache_size=0` in connect_args for PgBouncer Transaction mode
- pydantic v2 - Data validation and serialization (schemas in `api/schemas/`)
- pydantic-settings 2.0+ - Environment variable validation (`api/core/config.py`)

**Infrastructure:**
- fastapi[standard] 0.115+ - Includes uvicorn, starlette, etc.
- psycopg2-binary 2.9+ - PostgreSQL adapter (fallback, primary is asyncpg)
- alembic 1.13+ - Database schema migrations (`alembic.ini`, `alembic/versions/`)
- uvicorn 0.30+ - ASGI server for running FastAPI (`api.main:app`)

**Pipeline Processing:**
- pdfplumber 0.11+ - PDF text extraction (`pipeline/parser/extractor.py`)
- anthropic 0.40+ - Anthropic API client for Claude LLM (`pipeline/parser/llm_pass.py`)
- instructor[anthropic] - Structured output library wrapping Anthropic SDK
- tenacity 8.0+ - Retry/backoff library for transient failures (`pipeline/parser/llm_pass.py`)

**HTTP Client:**
- httpx 0.27+ - Async HTTP client used in:
  - `pipeline/commands/ingest.py` - Downloads PDFs from supremecourt.gov
  - API tests in `api/tests/test_*.py`

**Utilities:**
- python-dotenv 1.0+ - Environment variable loading from `.env` files (`pipeline/db.py`)

## Configuration

**Environment:**
- `.env` file (gitignored; not provided in repo)
  - Required: `DATABASE_URL` (PostgreSQL connection string with `postgresql+asyncpg://` scheme)
  - Optional: `ANTHROPIC_API_KEY` (required for pipeline parse step; optional for API)
  - Optional: `DEBUG` (FastAPI debug mode; default: False)
- `.env.example` provided as reference template

**Build:**
- `app/vite.config.ts` - Vite build configuration (minimal, delegates to SvelteKit)
- `app/svelte.config.js` - SvelteKit config with `@sveltejs/adapter-node` for production
- `app/tsconfig.json` - TypeScript compiler options (strict mode enabled)
- `app/tailwind.config.js` - Tailwind CSS content paths and theme extensions
- `app/postcss.config.js` - PostCSS configuration for Tailwind/autoprefixer
- `pytest.ini` - pytest configuration (asyncio_mode=auto, test paths)
- `alembic.ini` - Alembic migration configuration (migrations in `alembic/versions/`)

## Platform Requirements

**Development:**
- Windows 11 Pro (asyncio.WindowsSelectorEventLoopPolicy() policy set in `pipeline/__main__.py` line 28)
- Python 3.12+ installed with pip and virtual environment support
- Node.js + npm for frontend build
- PostgreSQL 16 (for database)

**Production:**
- Deployment target: Digital Ocean App Platform (per CLAUDE.md)
- PostgreSQL 16 hosted database
- PgBouncer in Transaction mode (requires asyncpg `statement_cache_size=0`)
- Node.js ASGI server (SvelteKit with `@sveltejs/adapter-node`)

---

*Stack analysis: 2026-06-15*
