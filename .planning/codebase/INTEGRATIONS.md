# External Integrations

**Analysis Date:** 2026-06-15

## APIs & External Services

**Anthropic Claude LLM:**
- Service: Claude (Haiku and other models via Anthropic API)
- What it's used for: LLM-based corrective parsing pass for SCOTUS transcript utterance extraction in parse step
  - Model target: `claude-haiku-4-5-20251001` (specified in `pipeline/parser/llm_pass.py` D-04)
  - Uses tool-calling (instructor.Mode.TOOLS) for structured output
  - Full transcript processed in single call (~40-50k tokens for SCOTUS Q1, no chunking)
- SDK/Client: `anthropic` 0.40+, `instructor[anthropic]` for structured output
- Auth: `ANTHROPIC_API_KEY` env var loaded in `api/core/config.py`
- Location: `pipeline/parser/llm_pass.py` (ParsedUtterance schema, SYSTEM_PROMPT, parse_with_llm function)

**Supreme Court Official Website:**
- Service: supremecourt.gov PDF download
- What it's used for: Source of transcript PDFs (immutable, read-only)
- HTTP Method: GET via `httpx` async client
- Auth: None (public URLs)
- Security: SSRF validation in `pipeline/commands/ingest.py` _validate_url() — only https://...supremecourt.gov/... URLs accepted
- Location: `pipeline/commands/ingest.py` run_ingest() function (lines 72+)

## Data Storage

**Databases:**
- PostgreSQL 16 (system of record per CLAUDE.md)
  - Connection: `DATABASE_URL` env var in format `postgresql+asyncpg://user:pass@host/db`
  - Client: SQLAlchemy 2.0+ async ORM via asyncpg driver
  - Location: `api/core/database.py` (async engine setup, AsyncSessionLocal session factory)

**File Storage:**
- Local filesystem only
  - PDFs stored in `/data/` directory (immutable after ingest)
  - Path: `pipeline_run.pdf_path` column stores relative path to downloaded PDF
  - No cloud storage integration (reads from local disk in parse/resolve steps)

**Caching:**
- None detected

## Authentication & Identity

**Auth Provider:**
- None (API is read-only, no user authentication)
- FastAPI app in `api/main.py` has `/health` liveness probe but no auth requirements

**Frontend Auth:**
- None required (website is read-only display of transcripts)
- All API calls from SvelteKit server load functions (`+page.server.ts`) use `FASTAPI_BASE_URL` private env var
- No user login or credentials involved

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry, DataDog, etc.)

**Logs:**
- FastAPI SQL echo logging available when `DEBUG=true` env var set (configured in `api/core/config.py`)
- Structured logging not implemented; standard Python logging would be used by dependencies

**Database Diagnostics:**
- asyncpg `pool_pre_ping=True` enabled for connection health checks (`api/core/database.py` line 41)

## CI/CD & Deployment

**Hosting:**
- Digital Ocean App Platform (per CLAUDE.md)
- PgBouncer in Transaction mode (requires asyncpg `statement_cache_size=0` setting in connect_args)

**CI Pipeline:**
- None detected (no GitHub Actions, GitLab CI, Jenkins, etc. in repo)

## Environment Configuration

**Required env vars:**
- `DATABASE_URL` - PostgreSQL connection string (format: `postgresql+asyncpg://user:pass@host:port/dbname`)
  - Must include asyncpg in scheme; asyncpg config `statement_cache_size=0` hardcoded in connect_args for PgBouncer compatibility
- `ANTHROPIC_API_KEY` - Required only for pipeline parse step; optional for API server (`api/core/config.py` default="")

**Optional env vars:**
- `DEBUG` - Enable SQLAlchemy SQL echo logging (default: False)

**Secrets location:**
- `.env` file (gitignored, not in repository)
- SvelteKit private env vars: Files in `.env.local` or `.env` in `/app` directory
- Frontend public vars: Accessed via `$env/static/private` in SvelteKit server functions

## Webhooks & Callbacks

**Incoming:**
- None detected (API is read-only)

**Outgoing:**
- None detected (no callbacks to external systems)

## Database Integration Points

**API ↔ Database:**
- Async SQLAlchemy session injected via FastAPI Depends:
  - `api/core/database.py` get_db() function yields AsyncSession
  - Used by all routers: `api/routers/arguments.py`, `api/routers/cases.py`, `api/routers/people.py`
  - Models in `api/models/models.py` (11 tables total)

**Pipeline ↔ Database:**
- Direct async SQLAlchemy connections in pipeline commands:
  - `pipeline/db.py` get_session() async context manager
  - Used by: ingest, parse, resolve, seed_aliases commands
  - Direct SQL inserts/updates via sqlalchemy.select() and session.execute()

## Data Flow Architecture

```
supremecourt.gov (PDF URLs)
        ↓ (httpx download)
pipeline/commands/ingest.py
        ↓ (creates rows)
PostgreSQL: cases, arguments, case_arguments, pipeline_runs
        ↓
pipeline/commands/parse.py (reads PDF from /data/)
        ↓ (pdfplumber + rule-based state machine)
pipeline/parser/extractor.py + state_machine.py
        ↓ (calls Anthropic Claude for correction)
pipeline/parser/llm_pass.py (instructor + anthropic SDK)
        ↓ (instructor validates ParsedUtterance schema)
PostgreSQL: utterances, argument_participants
        ↓
pipeline/commands/resolve.py (maps speaker_alias)
        ↓ (updates utterance.person_id)
PostgreSQL: speaker_alias, utterances (person_id column)
        ↓
FastAPI read-only API
        ↓ (httpx from SvelteKit server functions)
SvelteKit frontend (+page.server.ts load functions)
        ↓
Browser (read-only chat-style display)
```

## Critical Configuration Notes

**PgBouncer Transaction Mode:**
- `asyncpg` requires `statement_cache_size=0` in `create_async_engine()` connect_args (not top-level kwarg)
- Hardcoded in `api/core/database.py` line 38 for Digital Ocean compatibility
- SQLAlchemy bug reference gh#6467 — top-level kwarg silently ignored

**Async Context Manager:**
- FastAPI lifespan handler creates engine on startup, disposes on shutdown
- Module-level globals `engine` and `AsyncSessionLocal` initialized inside lifespan context
- Avoids requiring DATABASE_URL at import time (important for test discovery)

**Windows Event Loop Policy:**
- asyncpg incompatible with Windows ProactorEventLoop (Python 3.8+ default)
- `pipeline/__main__.py` line 28 sets `asyncio.WindowsSelectorEventLoopPolicy()`

---

*Integration audit: 2026-06-15*
