# External Integrations

**Analysis Date:** 2026-07-08

## APIs & External Services

**Anthropic / Claude LLM:**
- Claude 3.5 Haiku (model: `claude-haiku-4-5-20251001`) - Structured output parsing of SCOTUS transcripts
  - SDK: `anthropic` 0.40+
  - Auth: `ANTHROPIC_API_KEY` environment variable
  - Used by: `pipeline/parser/llm_pass.py` (corrective parse pass)

**SCOTUS Website:**
- supremecourt.gov - PDF transcript source
  - Client: `httpx` 0.27+
  - URL validation: SSRF mitigation — https only
  - Used by: `pipeline/commands/ingest.py`

## Data Storage

**Databases:**
- PostgreSQL 16 - System of record (13 tables after phase 22)
  - Connection: `DATABASE_URL` env var
  - Client: SQLAlchemy 2.0 AsyncSession via `api/core/database.py`
  - Migrations: Alembic 1.13+ (sole DDL authority)
  - Special config: `statement_cache_size=0` in connect_args for DO PgBouncer Transaction mode

**File Storage:**
- Local filesystem (`data/uploads/`) - Profile photos (persistent in dev)
- Local filesystem (`data/`) - Immutable ingested PDFs (organized by case slug)
- Digital Ocean Spaces (S3-compatible) - Optional phase 6+ for file uploads
  - Client: `boto3` 1.34+
  - Env vars: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, DO_SPACES_BUCKET, DO_SPACES_ENDPOINT, DO_SPACES_REGION

**Caching:**
- None configured (read-only API; caching deferred to CDN layer if needed)

## Authentication & Identity

**Custom Implementation (SvelteKit Admin Auth):**
- Session cookie (HMAC-SHA256)
- Cookie name: `scotus_admin_session`
- Credentials: `ADMIN_USERNAME`, `ADMIN_PASSWORD` env vars (plain text comparison via timingSafeEqual)
- Session validation: `verifySession()` in `app/src/hooks.server.ts`
- Session implementation: `app/src/lib/server/session.ts` (signSession, verifySession)

**API Token (Legacy, Phase 5):**
- `ADMIN_TOKEN` env var header (`X-Admin-Token`)
- Used by: `/api/admin/*` endpoints for server-to-server calls (SvelteKit → FastAPI)

## Monitoring & Observability

**Error Tracking:**
- None configured (manual logging only)

**Logs:**
- Uvicorn console output
- SQLAlchemy SQL echo (when DEBUG=true in api/core/config.py)
- Pipeline stderr/stdout (subprocess output captured by admin job status)

## CI/CD & Deployment

**Hosting:**
- Digital Ocean App Platform
  - FastAPI service: Python 3.12, `uvicorn api.main:app --port 8080`
  - SvelteKit service: Node.js, `npm run build && node build/index.js`

**Environment Vars (Production):**
- FastAPI service: DATABASE_URL, ANTHROPIC_API_KEY, ADMIN_TOKEN, DEBUG (false)
- SvelteKit service: ADMIN_TOKEN (for client-side fetches), SESSION_SECRET, ADMIN_USERNAME, ADMIN_PASSWORD, FASTAPI_BASE_URL (server-only env var in $env/static/private)
- Both services: AWS_* and DO_SPACES_* (if file uploads enabled)

## Webhooks & Callbacks

**Incoming:** None

**Outgoing:** None (polling only via `/api/admin/jobs/{job_id}` for job status during pipeline runs)

## Admin Job Pipeline Pattern

**Architecture (per CLAUDE.md):**
- FastAPI read-only; pipeline writes directly to PostgreSQL
- Pipeline steps: CLI commands only, never HTTP endpoints
- Re-run creates new `pipeline_run_id`; prior rows kept until promoted
- Admin subprocess invoked with `--job-id` flag; pipeline writes job status to `admin_jobs` table
- Job states: pending → running → completed/failed/needs_review
- Job steps: ingest → parse → resolve

**Frontend/Backend Interaction:**
- SvelteKit calls FastAPI `/api/admin/jobs` to create job (POST)
- SvelteKit polls `/api/admin/jobs/{job_id}` to check status (GET)
- FastAPI spawns subprocess via `api/services/pipeline_spawn.py:spawn_pipeline_step()`
- Pipeline subprocess updates `admin_jobs.status` and `admin_jobs.error_message` on completion

---

*Integration audit: 2026-07-08*
