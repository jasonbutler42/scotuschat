# External Integrations

**Analysis Date:** 2026-07-02

## APIs & External Services

**Anthropic / Claude LLM:**
- Claude 3.5 Haiku (model: `claude-haiku-4-5-20251001`) - Structured output parsing of SCOTUS transcripts
  - SDK: `anthropic` 0.40+
  - Auth: `ANTHROPIC_API_KEY` environment variable
  - Used by: `pipeline/parser/llm_pass.py`

**SCOTUS Website:**
- supremecourt.gov - PDF transcript source
  - Client: `httpx` 0.27+
  - URL validation: SSRF mitigation — https only
  - Used by: `pipeline/commands/ingest.py`

## Data Storage

**Databases:**
- PostgreSQL 16 - System of record
  - Connection: `DATABASE_URL` env var
  - Client: SQLAlchemy 2.0 AsyncSession via `api/core/database.py`
  - Migrations: Alembic 1.13+
  - Special config: `statement_cache_size=0` in connect_args for DO PgBouncer

**File Storage:**
- Local filesystem (`data/uploads/`) - Profile photos and PDFs
- Digital Ocean Spaces (S3-compatible) - Optional Phase 6+
  - Client: `boto3` 1.34+
  - Env vars: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, DO_SPACES_BUCKET, DO_SPACES_ENDPOINT, DO_SPACES_REGION

## Authentication & Identity

**Custom Implementation:**
- SvelteKit session cookie (HMAC-SHA256)
- Cookie name: `scotus_admin_session`
- Credentials: `ADMIN_USERNAME`, `ADMIN_PASSWORD` env vars (plain text comparison)
- Session validation: `verifySession()` in `hooks.server.ts`

**API Token:**
- `ADMIN_TOKEN` env var (required, no default)
- Bearer token for `/admin/pipeline` endpoints

## Monitoring & Observability

**Error Tracking:** None configured
**Logs:** Uvicorn console, SQLAlchemy echo (DEBUG=true), Pipeline stderr

## CI/CD & Deployment

**Hosting:** Digital Ocean App Platform
- FastAPI service: Python 3.12, `uvicorn api.main:app`
- SvelteKit service: Node.js, adapter-node

**Environment Vars:**
- Production: DATABASE_URL, ANTHROPIC_API_KEY, ADMIN_TOKEN, SESSION_SECRET, ADMIN_USERNAME, ADMIN_PASSWORD
- Optional: AWS_* and DO_SPACES_* for file uploads

## Webhooks & Callbacks

**Incoming:** None
**Outgoing:** None (polling only: `/admin/pipeline/{job_id}`)

## Pipeline Pattern

**Architecture (CLAUDE.md):**
- FastAPI read-only; pipeline writes directly to PostgreSQL
- Pipeline steps: CLI commands only, never HTTP endpoints
- Re-run creates new `pipeline_run_id`; prior rows kept until promoted
- Admin subprocess invokes with `--job-id`; pipeline writes job status to `admin_jobs` table

---

*Integration audit: 2026-07-02*
