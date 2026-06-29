# Phase 1: Foundation + Proof of Concept - Research

**Researched:** 2026-06-11
**Domain:** PostgreSQL schema + Alembic migrations, Python pipeline CLI, FastAPI async patterns, SvelteKit 2/Svelte 5 SSR, instructor/Anthropic structured output
**Confidence:** HIGH — spike findings verified, architecture patterns confirmed against official sources

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 / D-02 / D-03 / D-04 / D-05:** Spike is complete. Deliverables available in `.claude/skills/spike-findings-scotuschat/`. Validated `ParsedUtterance` schema, rule-based parser (95% coverage), failure taxonomy (12 modes). Target model: `claude-haiku-4-5-20251001`. Full-transcript single call (no chunking needed for SCOTUS Q1 transcripts at ~40–50k tokens).
- **D-06:** No Docker. Native per-user install — Postgres portable ZIP, Python per-user, Node.js per-user. No admin rights required.
- **D-07:** Single PowerShell `.ps1` dev startup script starts all three services: Postgres, FastAPI (uvicorn), SvelteKit (vite dev).
- **D-08:** Postgres data directory lives at `/data/pgdata`, gitignored.
- **D-09:** Parse step outputs a `side` field on each utterance: enum `BENCH | ADVOCATE | UNKNOWN`. LLM assigns at parse time from raw speaker label.
- **D-10:** `side` stored in DB from Phase 1. Phase 2 may correct it but does not introduce the field.
- **D-11:** PoC case: Obergefell v. Hodges, Q1 session only (docket 14-556 consolidated, argued 2015-04-28).
- **D-12:** Obergefell exercises INFRA-02 — consolidated across 4 docket numbers: 14-556, 14-562, 14-571, 14-574.
- **D-13:** Q2 session is deferred — not part of Phase 1 PoC.
- **D-14:** Use `instructor` library wrapping the Anthropic SDK (`Mode.TOOLS`). Auto-validates against Pydantic model; retries on schema mismatch. Do NOT use raw tool_use or prompt-only JSON mode.
- **D-15:** Pipeline invoked as `python -m pipeline ingest --url ...` and `python -m pipeline parse --run-id ...`.
- **D-17:** Use final URL structure from day one: `/cases/[slug]/arguments/[id]`. Phase 1 hard-codes navigation to Obergefell.
- **D-18:** Scaffold full `routers/ / services/ / schemas/` structure in Phase 1 with `GET /arguments/{id}/utterances` as the first endpoint.

### Claude's Discretion

- CLI flag design for `python -m pipeline ingest` and `python -m pipeline parse`.
- `instructor` retry configuration (number of retries, backoff via `tenacity`).

### Deferred Ideas (OUT OF SCOPE)

- Obergefell Q2 session.
- Additional cases beyond Obergefell.
- Docker Compose setup.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Full PostgreSQL schema (10 tables) via Alembic migrations only — no `create_all` | Schema design section; Alembic async pattern |
| INFRA-02 | Schema handles consolidated arguments (multiple docket numbers per argument) | M:M case-argument join table design |
| INFRA-03 | Dev environment runs fully locally (Postgres + FastAPI + SvelteKit) | PowerShell startup script, portable Postgres pattern |
| PIPE-01 | Ingest step: download PDF URL → local file → case/argument/pipeline_run records → status `pending` | Pipeline CLI `__main__.py` pattern, httpx download |
| PIPE-02 | Raw PDFs never modified after ingest; all derived data regenerable | Immutable storage pattern, `/data/` directory |
| PIPE-03 | Parse step: pdfplumber extraction → Claude API structured output → utterance rows with `person_id=null` | Spike-validated extraction + instructor pattern |
| PIPE-04 | Parse step records `pipeline_run_id` and `strategy` on each utterance row | Schema column definition |
| PIPE-05 | Parse step classifies `is_stage_direction` at parse time | Spike state machine rule F02/F03/F05 |
| PIPE-06 | LLM failures classified transient vs. structural; max 2 retries on structural; failure reason recorded | Tenacity + instructor retry architecture |
| PIPE-10 | `pipeline_run` status state machine enforced: `pending → running → completed | failed | needs_review` | State machine pattern from ARCHITECTURE.md |
| PIPE-11 | Re-running any step produces new rows linked to new `pipeline_run_id`; prior rows preserved | `pipeline_run_id` FK design, no-delete policy |
| API-01 | `GET /arguments/{id}/utterances` returns ordered utterances with speaker attribution | FastAPI router/service/schema scaffold |
| UI-01 | Two-sided chat: Justices on bench side, advocates on advocate side | SvelteKit `side` field rendering |
| UI-02 | Each utterance bubble shows speaker name and role label | `raw_speaker_label` display (person_id null in Phase 1) |
| UI-03 | Stage directions render as distinct visual component between bubbles | `is_stage_direction` conditional rendering in Svelte 5 |

</phase_requirements>

---

## Summary

Phase 1 is a greenfield implementation of the entire project scaffold — schema, pipeline CLI, minimal API, and minimal chat UI — wired together end-to-end on a single hand-picked case. All architectural patterns must be set correctly here because Phase 2–4 depend on them without refactoring.

The most important technical decision to get right in Phase 1 is the database schema. The `argument ↔ case` many-to-many relationship (required by INFRA-02 for Obergefell's four consolidated dockets) must be in the initial migration. Adding M:M later requires a migration and re-ingest. The spike findings provide the complete validated `ParsedUtterance` schema and all regex patterns for the rule-based parser — the planner should treat these as locked implementation assets, not options to redesign.

The `instructor` library (D-14) wraps the Anthropic SDK and handles structured output validation via `Mode.TOOLS`, which uses Anthropic's native tool-calling API. The spike used raw `tool_use` directly; Phase 1 must switch to `instructor` for automatic Pydantic validation and retries. The two-layer retry strategy separates structural LLM validation failures (instructor handles with `max_retries`) from transient API errors (tenacity handles with exponential backoff). The Anthropic SDK has its own internal retry (default 2 retries); set `Anthropic(max_retries=0)` to avoid triple-retrying transient errors.

The `asyncpg` `statement_cache_size=0` must be in the initial `create_async_engine(connect_args=...)` call — it cannot be retrofitted after deployment behind Digital Ocean PgBouncer. The Alembic `env.py` must use the official async template (`alembic init -t async`) with `async_engine_from_config` and `asyncio.run()`. Alembic also needs a sync engine for offline mode; use `psycopg2-binary` for that path only.

**Primary recommendation:** Build in this order: schema + Alembic migrations → pipeline ingest → pipeline parse → FastAPI `GET /arguments/{id}/utterances` → SvelteKit chat view. Do not start the SvelteKit UI until the API returns real data.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Schema DDL (all 10 tables) | Alembic migration files | — | Sole DDL authority per CLAUDE.md hard constraint |
| PDF download + storage | Pipeline (CLI) | — | Offline-only; never an HTTP endpoint |
| PDF text extraction | Pipeline (CLI) | — | pdfplumber is Python-only; no browser context |
| Rule-based transcript parsing | Pipeline (CLI) | — | CPU-only, no LLM for primary parse pass |
| LLM corrective parse pass | Pipeline (CLI) via instructor | — | Offline batch; instructor + Anthropic SDK |
| `pipeline_run` state machine | Pipeline (CLI) + DB | — | State transitions at DB level using transactions |
| Read API for utterances | FastAPI (API tier) | — | Read-only; pipeline writes directly to DB |
| DB session lifecycle | FastAPI lifespan | — | `async_sessionmaker`, `expire_on_commit=False` |
| SSR data fetching | SvelteKit `+page.server.ts` | — | Server-side only; `FASTAPI_BASE_URL` never PUBLIC_ |
| Chat bubble rendering | SvelteKit `+page.svelte` | — | Client-side component after SSR hydration |
| Stage direction rendering | SvelteKit `+page.svelte` | — | Conditional on `is_stage_direction` field |
| Dev startup orchestration | PowerShell `.ps1` script | — | Starts Postgres, uvicorn, vite dev in order |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PostgreSQL | 16 (portable ZIP) | Primary data store | Locked by project stack; portable ZIP works without admin rights |
| SQLAlchemy | 2.0+ async | ORM + query builder | Official SQLAlchemy 2.0 async API; required for FastAPI async |
| asyncpg | 0.29.x | Async Postgres driver | Fastest async driver; `statement_cache_size=0` for PgBouncer compat |
| psycopg2-binary | 2.9.x | Alembic sync migrations | Alembic `env.py` offline mode requires sync driver |
| Alembic | 1.13.x+ | Schema migrations | Sole DDL authority per CLAUDE.md |
| FastAPI | 0.115.x+ | HTTP API | Pydantic v2 bundled; async-native |
| Pydantic | v2 | Schema validation | Bundled with FastAPI 0.115+; used for response models |
| instructor | latest | Structured LLM output | Wraps Anthropic SDK; `Mode.TOOLS` for Pydantic validation + retries |
| anthropic | 0.40.x+ | Claude API client | Official SDK; `AsyncAnthropic` for pipeline async calls |
| tenacity | 8.x | Retry for API errors | Exponential backoff for transient Anthropic 429/503 errors |
| pdfplumber | 0.11.x | PDF text extraction | Spike-validated; `extract_text(layout=False)` proven on 4 transcripts |
| httpx | 0.27.x | PDF download | Async HTTP; replaces `requests` for pipeline |
| python-dotenv | 1.x | `.env` loading | Local dev env vars |
| SvelteKit | 2.x | Frontend framework | Locked by project stack |
| Svelte | 5.x (Runes) | UI components | Runes system (`$state`, `$derived`, `$effect`) — no legacy stores |
| `@sveltejs/adapter-node` | latest | Node.js server target | Required for DO App Platform; produces `build/` directory |
| TypeScript | 5.x | Type safety | SvelteKit scaffolds TypeScript by default |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uvicorn | 0.30.x+ | ASGI server (dev) | `uvicorn api.main:app --reload` in dev only |
| gunicorn | 22.x | Process manager (prod) | Deferred to Phase 4/DEPLOY; not needed in Phase 1 |
| python-ulid | latest | ULID for run IDs | Sortable pipeline run identifiers; stdlib `uuid` also acceptable |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncpg | psycopg3 | psycopg3 is slower in benchmarks; asyncpg is the established default for SQLAlchemy async |
| instructor `Mode.TOOLS` | Raw `tool_use` in anthropic SDK | Raw tool_use works (spike used it) but lacks Pydantic auto-validation + retry loop |
| click (CLI) | argparse (stdlib) | Both work; click decorator API is cleaner for subcommands; argparse has no install cost |
| tenacity (external retry) | SDK internal retry only | SDK retries 2x by default; tenacity gives explicit control over retry count and wait strategy |

**Installation (Python — api + pipeline shared venv):**
```bash
pip install fastapi[standard]>=0.115
pip install sqlalchemy>=2.0
pip install asyncpg>=0.29
pip install alembic>=1.13
pip install psycopg2-binary>=2.9
pip install "instructor[anthropic]"
pip install anthropic>=0.40
pip install tenacity>=8.0
pip install pdfplumber>=0.11
pip install httpx>=0.27
pip install python-dotenv>=1.0
```

**Installation (SvelteKit):**
```bash
npx sv create app      # scaffold with Svelte 5, TypeScript, SvelteKit 2
cd app
npm install -D @sveltejs/adapter-node
```

**Version verification note:** Versions above are based on project research files (2026-06-11). [ASSUMED] for specific patch versions — verify with `pip index versions <pkg>` and `npm view <pkg> version` before locking in `requirements.txt` and `package.json`.

---

## Package Legitimacy Audit

> This is a greenfield project. All packages below are from established, long-running libraries in the Python and Node.js ecosystems. Full slopcheck was not run (tool not available in this environment); all packages are tagged `[ASSUMED]` per graceful degradation rule.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| fastapi | PyPI | 6+ yrs | 100M+/mo | github.com/fastapi/fastapi | [ASSUMED] | Approved — major web framework |
| sqlalchemy | PyPI | 15+ yrs | 100M+/mo | github.com/sqlalchemy/sqlalchemy | [ASSUMED] | Approved — industry standard |
| asyncpg | PyPI | 8+ yrs | 50M+/mo | github.com/MagicStack/asyncpg | [ASSUMED] | Approved — official async PG driver |
| alembic | PyPI | 12+ yrs | 80M+/mo | github.com/sqlalchemy/alembic | [ASSUMED] | Approved — official SQLAlchemy migrations |
| psycopg2-binary | PyPI | 10+ yrs | 80M+/mo | github.com/psycopg/psycopg2 | [ASSUMED] | Approved — standard sync PG driver |
| instructor | PyPI | 2+ yrs | 5M+/mo | github.com/567-labs/instructor | [ASSUMED] | Approved — widely used LLM structured output |
| anthropic | PyPI | 3+ yrs | 20M+/mo | github.com/anthropics/anthropic-sdk-python | [ASSUMED] | Approved — official Anthropic SDK |
| tenacity | PyPI | 8+ yrs | 50M+/mo | github.com/jd/tenacity | [ASSUMED] | Approved — standard Python retry library |
| pdfplumber | PyPI | 7+ yrs | 3M+/mo | github.com/jsvine/pdfplumber | [ASSUMED] | Approved — spike-validated on 4 SCOTUS transcripts |
| httpx | PyPI | 5+ yrs | 80M+/mo | github.com/encode/httpx | [ASSUMED] | Approved — standard async HTTP client |
| @sveltejs/adapter-node | npm | 3+ yrs | 500K+/wk | github.com/sveltejs/kit | [ASSUMED] | Approved — official SvelteKit adapter |

**Packages removed due to slopcheck [SLOP] verdict:** none

**Packages flagged as suspicious [SUS]:** none

*All packages tagged `[ASSUMED]` — slopcheck unavailable. Planner should confirm all packages are listed in project `requirements.txt` and `package.json` before any install task.*

---

## Architecture Patterns

### System Architecture Diagram

```
                    OPERATOR MACHINE (offline)
                    ┌────────────────────────────────────────────────┐
                    │  python -m pipeline ingest --url <PDF URL>     │
                    │    → httpx downloads PDF → /data/<slug>.pdf    │
                    │    → creates: case, argument, pipeline_run     │
                    │    → status: pending                           │
                    │                                                │
                    │  python -m pipeline parse --run-id <id>        │
                    │    → pdfplumber extracts pages                  │
                    │    → rule-based state machine (95% coverage)   │
                    │    → instructor + Claude (corrective pass)      │
                    │    → writes utterances (person_id=null)        │
                    │    → status: completed | failed                 │
                    └───────────────┬────────────────────────────────┘
                                    │ SQL writes (SQLAlchemy sync/asyncpg)
                                    ▼
                    ┌────────────────────────────────────────────────┐
                    │              PostgreSQL (shared)               │
                    │  Tables: cases, arguments, case_arguments,     │
                    │          argument_participants, people, roles, │
                    │          court_tenures, utterances,            │
                    │          citations, pipeline_runs              │
                    │  Schema authority: Alembic only                │
                    └───────────────┬────────────────────────────────┘
                                    │ SQL reads (async SQLAlchemy + asyncpg)
                                    ▼
                    ┌────────────────────────────────────────────────┐
                    │  FastAPI (uvicorn, dev)                        │
                    │  GET /arguments/{id}/utterances                │
                    │  lifespan: create_async_engine (pool)          │
                    │  dependency: AsyncSession per request           │
                    └───────────────┬────────────────────────────────┘
                                    │ HTTP (server-side fetch, SSR)
                                    ▼
                    ┌────────────────────────────────────────────────┐
                    │  SvelteKit (vite dev server)                   │
                    │  /cases/[slug]/arguments/[id]                  │
                    │  +page.server.ts → fetches FastAPI             │
                    │  +page.svelte → renders chat bubbles           │
                    │    bench side: BENCH utterances                │
                    │    advocate side: ADVOCATE utterances          │
                    │    stage directions: distinct component        │
                    └────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
project/
├── api/
│   ├── routers/
│   │   └── arguments.py       # GET /arguments/{id}/utterances
│   ├── services/
│   │   └── arguments.py       # query logic, ordering
│   ├── schemas/
│   │   └── utterance.py       # Pydantic response models
│   ├── models/
│   │   └── models.py          # SQLAlchemy ORM models (shared with pipeline)
│   ├── core/
│   │   ├── config.py          # pydantic-settings Settings class
│   │   └── database.py        # async engine + sessionmaker + get_db dependency
│   └── main.py                # FastAPI app, lifespan, include_router
├── pipeline/
│   ├── __main__.py            # entry point: python -m pipeline <cmd>
│   ├── commands/
│   │   ├── ingest.py          # ingest command implementation
│   │   └── parse.py           # parse command implementation
│   ├── parser/
│   │   ├── extractor.py       # pdfplumber extraction (from spike)
│   │   ├── state_machine.py   # rule-based parser (from spike)
│   │   └── llm_pass.py        # instructor corrective pass
│   └── db.py                  # sync SQLAlchemy engine for pipeline
├── app/                       # SvelteKit project root
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +layout.svelte
│   │   │   └── cases/
│   │   │       └── [slug]/
│   │   │           └── arguments/
│   │   │               └── [id]/
│   │   │                   ├── +page.server.ts
│   │   │                   └── +page.svelte
│   │   └── lib/
│   │       └── components/
│   │           ├── ChatBubble.svelte
│   │           └── StageDirection.svelte
│   ├── svelte.config.js       # adapter-node
│   └── .env                   # FASTAPI_BASE_URL=http://localhost:8000
├── alembic/
│   ├── versions/
│   │   └── 0001_initial_schema.py
│   ├── env.py                 # async template (alembic init -t async)
│   └── alembic.ini
├── data/
│   ├── pgdata/                # Postgres data dir — gitignored
│   └── pdfs/                  # downloaded PDF files — gitignored
├── scripts/
│   └── dev-start.ps1          # starts Postgres, uvicorn, vite dev
├── .env                       # DATABASE_URL, ANTHROPIC_API_KEY
└── requirements.txt
```

### Pattern 1: Alembic Async env.py (INFRA-01)

**What:** Use the official Alembic async template for `env.py` — it uses `async_engine_from_config` and `asyncio.run()` for online mode, and a plain URL for offline mode.

**When to use:** All migrations. This is the only DDL mechanism — no `Base.metadata.create_all` anywhere.

**Initialize:**
```bash
alembic init -t async alembic
```

**env.py pattern (verified from Alembic source):** [CITED: github.com/sqlalchemy/alembic/blob/main/alembic/templates/async/env.py]
```python
# alembic/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Import models so autogenerate sees the metadata
from api.models.models import Base  # CRITICAL — without this, autogenerate produces empty migrations

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**alembic.ini:** Load `sqlalchemy.url` from environment — never hardcode:
```ini
# alembic.ini
sqlalchemy.url = %(DATABASE_URL)s
```

And in `env.py` prelude:
```python
import os
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
```

### Pattern 2: FastAPI Async Engine with statement_cache_size=0 (INFRA-01, DEPLOY prep)

**What:** Create the async SQLAlchemy engine in the FastAPI lifespan event. Set `statement_cache_size=0` in `connect_args` — this is mandatory for PgBouncer Transaction mode on Digital Ocean.

**Critical:** `statement_cache_size=0` goes in `connect_args` (asyncpg connection args), NOT as a top-level engine arg. [CITED: github.com/sqlalchemy/sqlalchemy/issues/6467]

```python
# api/core/database.py
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from fastapi import FastAPI
from typing import AsyncGenerator

engine = None
AsyncSessionLocal = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine, AsyncSessionLocal
    engine = create_async_engine(
        settings.database_url,           # postgresql+asyncpg://...
        connect_args={"statement_cache_size": 0},   # REQUIRED for PgBouncer
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False,
    )
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    yield
    await engine.dispose()

# api/main.py
app = FastAPI(lifespan=lifespan)
```

**`expire_on_commit=False` is mandatory in async SQLAlchemy** — otherwise lazy-loading expired attributes after commit triggers a sync DB call and raises `MissingGreenlet`. [CITED: .planning/research/STACK.md]

**Session dependency:**
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

### Pattern 3: Pipeline State Machine (PIPE-10)

**What:** Each pipeline step atomically transitions `pipeline_run` status. Prior-run rows are never deleted until the new run is promoted.

[CITED: .planning/research/ARCHITECTURE.md]
```python
# Sync pattern (pipeline uses sync SQLAlchemy + psycopg2)
async def run_parse_step(run_id: int, session: AsyncSession):
    async with session.begin():
        run = await session.get(PipelineRun, run_id)
        if run.status not in ("pending", "failed"):
            raise StepAlreadyRunning(run_id)
        run.status = "running"
    try:
        await _do_parse_work(run_id, session)
        async with session.begin():
            run.status = "completed"
    except Exception as exc:
        async with session.begin():
            run.status = "failed"
            run.failure_reason = str(exc)
        raise
```

### Pattern 4: instructor + Anthropic Structured Output (PIPE-03, D-14)

**What:** Use `instructor.from_anthropic(anthropic.AsyncAnthropic(), mode=instructor.Mode.TOOLS)` for structured LLM output. The `Mode.TOOLS` mode uses Anthropic's tool-calling API and auto-validates output against a Pydantic model.

[CITED: python.useinstructor.com/integrations/anthropic/]
```python
import instructor
import anthropic
from pydantic import BaseModel
from typing import Optional

class ParsedUtterance(BaseModel):
    sequence: int
    raw_speaker_label: Optional[str]
    text: str
    is_stage_direction: bool
    section_hint: Optional[str]

class ParseResponse(BaseModel):
    utterances: list[ParsedUtterance]

# Initialize — disable SDK retries to avoid double-retrying
aclient = instructor.from_anthropic(
    anthropic.AsyncAnthropic(max_retries=0),   # tenacity owns transient retries
    mode=instructor.Mode.TOOLS,
)

# Call with instructor validation + its own retry on schema mismatch
async def call_llm_parse(pages_text: str) -> ParseResponse:
    return await aclient.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8192,
        max_retries=2,   # instructor retries on Pydantic validation failure only
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": pages_text}],
        response_model=ParseResponse,
    )
```

**Two-layer retry strategy (PIPE-06):**
- **Inner layer (instructor `max_retries=2`):** Catches Pydantic schema validation failures. Feeds the validation error back to the model and retries. Max 2 retries on structural failures.
- **Outer layer (tenacity):** Catches transient API errors (HTTP 429, 503, connection timeout). Exponential backoff.

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def parse_with_retry(pages_text: str) -> ParseResponse:
    return await call_llm_parse(pages_text)
```

**Failure classification for PIPE-06:**
- `anthropic.RateLimitError` (HTTP 429) → transient → outer tenacity retry
- `anthropic.APIConnectionError` (network) → transient → outer tenacity retry
- `instructor.exceptions.InstructorRetryException` (schema mismatch persisted > max_retries) → structural → log `failure_reason`, set `pipeline_run.status = "failed"`, do NOT retry further
- `anthropic.BadRequestError` (HTTP 400, invalid prompt) → structural → fail immediately

### Pattern 5: SvelteKit Server Load Function (UI-01, UI-02, UI-03)

**What:** All FastAPI calls go through `+page.server.ts` server load functions. `FASTAPI_BASE_URL` is a server-only env var loaded from `$env/static/private` — never `PUBLIC_`.

[CITED: svelte.dev/docs/kit/$env-static-private]
```typescript
// app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts
import { FASTAPI_BASE_URL } from '$env/static/private';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
    const res = await fetch(`${FASTAPI_BASE_URL}/arguments/${params.id}/utterances`);
    if (!res.ok) throw error(res.status, 'Failed to load argument');
    const data = await res.json();
    return { utterances: data.utterances, argument_id: params.id };
};
```

**Svelte 5 Runes component (no legacy stores):**
```svelte
<!-- ChatBubble.svelte -->
<script lang="ts">
  let { utterance } = $props();
</script>

<div class="bubble {utterance.side.toLowerCase()}">
  <span class="speaker">{utterance.raw_speaker_label}</span>
  <p>{utterance.text}</p>
</div>
```

**Note:** Runes (`$props`, `$state`, `$derived`) work in `.svelte` component files. `+page.server.ts` is NOT a Svelte file and does not use runes — it is plain TypeScript. [CITED: github.com/sveltejs/kit/issues/13269]

### Pattern 6: Pipeline CLI `__main__.py` (D-15)

**What:** Enable `python -m pipeline <command>` invocation using a `__main__.py` entry point with `argparse` subcommands.

```python
# pipeline/__main__.py
import argparse
import asyncio
from pipeline.commands.ingest import run_ingest
from pipeline.commands.parse import run_parse

def main():
    parser = argparse.ArgumentParser(prog="pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    # ingest subcommand
    ingest_p = sub.add_parser("ingest", help="Download PDF and create pipeline records")
    ingest_p.add_argument("--url", required=True, help="URL of the transcript PDF")
    ingest_p.add_argument("--dockets", nargs="+", default=[],
                          help="Consolidated docket numbers (e.g. 14-562 14-571 14-574)")
    ingest_p.add_argument("--case-name", required=True, help="Human-readable case name")
    ingest_p.add_argument("--argued-date", required=True, help="Argument date YYYY-MM-DD")

    # parse subcommand
    parse_p = sub.add_parser("parse", help="Parse transcript into utterances")
    parse_p.add_argument("--run-id", required=True, type=int, help="pipeline_run.id from ingest step")
    parse_p.add_argument("--dry-run", action="store_true", help="Parse but do not write to DB")

    args = parser.parse_args()

    if args.command == "ingest":
        asyncio.run(run_ingest(args))
    elif args.command == "parse":
        asyncio.run(run_parse(args))

if __name__ == "__main__":
    main()
```

**Usage (D-15):**
```bash
python -m pipeline ingest \
  --url "https://www.supremecourt.gov/oral_arguments/argument_transcripts/2014/14-556q1_l5gm.pdf" \
  --dockets 14-562 14-571 14-574 \
  --case-name "Obergefell v. Hodges" \
  --argued-date 2015-04-28

python -m pipeline parse --run-id 1
```

### Anti-Patterns to Avoid

- **`Base.metadata.create_all()` anywhere in codebase.** Hard constraint from CLAUDE.md. If it appears anywhere — in tests, in startup code, in a conftest — it is wrong.
- **`statement_cache_size=0` passed as top-level engine arg** (not in `connect_args`). It silently has no effect. Must be `connect_args={"statement_cache_size": 0}`.
- **Using `PUBLIC_FASTAPI_BASE_URL` in SvelteKit.** The FastAPI URL must be server-only. Any `PUBLIC_` prefix exposes it to the browser bundle.
- **Running all parse pages through the LLM.** The rule-based state machine handles 95% of SCOTUS content. The LLM is a corrective pass (called once on the full text), not called per-page.
- **Sharing one `AsyncSession` across pipeline steps.** Each pipeline step opens and closes its own session. Long-lived idle sessions block PostgreSQL VACUUM.
- **Using `@app.on_event("startup")`** — deprecated. Use `lifespan` context manager.
- **Retrying structural LLM failures** (Pydantic schema mismatch that persists after `max_retries=2` instructor retries) with the transient-error outer tenacity loop. They are separate failure modes. Structural → log + fail; transient → retry with backoff.
- **Using `expire_on_commit=True`** (the default) in async SQLAlchemy. Causes `MissingGreenlet` errors on any attribute access after `session.commit()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured LLM output with Pydantic validation | Custom JSON parsing + manual retry | `instructor` + `Mode.TOOLS` | Handles schema mismatch detection, validation feedback loop, retry orchestration |
| PDF text extraction from SCOTUS transcripts | Regex-based raw byte parsing | `pdfplumber` with `extract_text(layout=False)` | Spike-validated; handles Alderson and Heritage formats identically |
| Async exponential backoff | Custom `asyncio.sleep` loop | `tenacity` `@retry` decorator | Handles jitter, max delay cap, attempt counting, reraise semantics |
| Database migrations | Manual `ALTER TABLE` SQL | Alembic | CLAUDE.md hard constraint; autogenerate, version control, rollback |
| HTTP PDF download with redirect following | Custom `urllib` handler | `httpx` | Async-native, follows redirects, handles SSL, timeout config |
| Async PostgreSQL connection pool | Manual `asyncpg` pool | SQLAlchemy `create_async_engine` pool | Handles PgBouncer reconnect, pre-ping, overflow |
| Environment config loading | `os.environ.get` calls scattered | `pydantic-settings` `Settings` class | Validates env vars at startup; IDE type-checking |

**Key insight:** The rule-based parse state machine from the spike is the core engine — do not redesign it. Copy it directly from `sources/002-parse-prompt-schema/parse.py` with the F04 fix applied (add `ON BEHALF OF` to `TOC_SECTION_RE`). The LLM pass via instructor is an additional corrective layer on top, not a replacement.

---

## Full Database Schema

This is the full 10-table schema required by INFRA-01 and INFRA-02. All tables must be in the initial Alembic migration.

### Core Design Decisions

**M:M case-argument relationship (INFRA-02):** A single `argument` row represents one hearing session. Multiple `case` rows can be associated with one argument (consolidated dockets). This uses a `case_arguments` join table — NOT a `case_id` foreign key on `argument`.

**`side` on utterances (D-09 / D-10):** Each utterance stores `side` as an enum (`BENCH | ADVOCATE | UNKNOWN`). Assigned at parse time from raw speaker label. Phase 2 may correct it but does not introduce it.

**`person_id` nullable on utterances:** At parse time, `person_id = NULL`. Phase 2 (Resolve) populates it.

**`pipeline_run_id` on utterances (PIPE-04, PIPE-11):** Every utterance row links to the pipeline run that produced it. Re-running produces new rows under a new `pipeline_run_id`.

### SQLAlchemy ORM Models (summary)

```python
# api/models/models.py
import enum
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, Date, DateTime,
    ForeignKey, UniqueConstraint, Index, Enum as SAEnum, func
)
from sqlalchemy.orm import DeclarativeBase, relationship

class Base(DeclarativeBase):
    pass

class SideEnum(str, enum.Enum):
    BENCH = "BENCH"
    ADVOCATE = "ADVOCATE"
    UNKNOWN = "UNKNOWN"

class PipelineRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)   # "Associate Justice", "Petitioner's Counsel"

class Person(Base):
    __tablename__ = "people"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(300), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)

class CourtTenure(Base):
    __tablename__ = "court_tenures"
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    seat = Column(String(100))                                # e.g. "Associate Justice Seat 3"
    start_date = Column(Date)
    end_date = Column(Date, nullable=True)                    # null = active

class Case(Base):
    __tablename__ = "cases"
    id = Column(Integer, primary_key=True)
    docket_number = Column(String(50), nullable=False, unique=True)  # "14-556"
    docket_number_norm = Column(String(50), nullable=False)          # normalized form
    case_name = Column(String(500), nullable=False)
    term_year = Column(Integer, nullable=False)
    slug = Column(String(200), nullable=False, unique=True)          # URL slug

class Argument(Base):
    __tablename__ = "arguments"
    id = Column(Integer, primary_key=True)
    argued_date = Column(Date, nullable=False)
    question_number = Column(Integer, nullable=False, default=1)     # Q1 or Q2
    # cases linked via case_arguments join table

class CaseArgument(Base):
    """M:M join table — one argument can cover multiple consolidated cases (INFRA-02)."""
    __tablename__ = "case_arguments"
    case_id = Column(Integer, ForeignKey("cases.id"), primary_key=True)
    argument_id = Column(Integer, ForeignKey("arguments.id"), primary_key=True)
    is_lead = Column(Boolean, nullable=False, default=False)  # True for lead docket (14-556)

class CaseAppearance(Base):
    """Which people appeared in which cases (counsel of record etc.)."""
    __tablename__ = "case_appearances"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)

class ArgumentParticipant(Base):
    """Which people spoke in which arguments (populated at parse time from raw labels)."""
    __tablename__ = "argument_participants"
    id = Column(Integer, primary_key=True)
    argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=False)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=True)   # null until resolved
    raw_speaker_label = Column(String(200), nullable=False)
    side = Column(SAEnum(SideEnum), nullable=False)

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    id = Column(Integer, primary_key=True)
    argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=False)
    step = Column(String(50), nullable=False)                 # "ingest", "parse", "resolve"
    status = Column(SAEnum(PipelineRunStatus), nullable=False, default=PipelineRunStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    pdf_path = Column(String(500), nullable=True)             # local path to immutable PDF
    pdf_url = Column(String(1000), nullable=True)             # original download URL
    strategy = Column(String(100), nullable=True)             # "rule_based", "llm_corrective"
    prompt_version = Column(String(50), nullable=True)        # for schema version tracking

class Utterance(Base):
    __tablename__ = "utterances"
    id = Column(BigInteger, primary_key=True)
    argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=False)
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    raw_speaker_label = Column(String(200), nullable=True)    # None for stage directions
    text = Column(Text, nullable=False)
    is_stage_direction = Column(Boolean, nullable=False, default=False)
    section_hint = Column(String(50), nullable=True)          # "petitioner"|"respondent"|"rebuttal"|"amicus"
    side = Column(SAEnum(SideEnum), nullable=False, default=SideEnum.UNKNOWN)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=True)  # null at parse time
    strategy = Column(String(100), nullable=False)             # PIPE-04: "rule_based" | "llm_corrective"

    __table_args__ = (
        UniqueConstraint("argument_id", "pipeline_run_id", "sequence",
                         name="uq_utterance_arg_run_seq"),
        Index("ix_utterances_argument_id", "argument_id"),
        Index("ix_utterances_pipeline_run_id", "pipeline_run_id"),
    )

class Citation(Base):
    __tablename__ = "citations"
    id = Column(Integer, primary_key=True)
    utterance_id = Column(BigInteger, ForeignKey("utterances.id"), nullable=False)
    raw_text = Column(Text, nullable=False)
    resolved_case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)  # always null in v1
```

---

## Common Pitfalls

### Pitfall 1: `statement_cache_size=0` in wrong place

**What goes wrong:** Setting `statement_cache_size=0` as a top-level engine keyword arg (not in `connect_args`) has no effect. asyncpg prepared statements still run. Behind PgBouncer Transaction mode, queries fail intermittently with `prepared statement "..." does not exist`.

**Why it happens:** SQLAlchemy has its own `statement_cache_size` (query compilation cache) that is separate from asyncpg's prepared statement cache. They are different settings with similar names.

**How to avoid:** Always use `connect_args={"statement_cache_size": 0}`.

**Warning signs:** Intermittent `PreparedStatementError` on production DO deployment that do not appear in local dev (local dev uses direct Postgres, not PgBouncer).

---

### Pitfall 2: Alembic autogenerate produces empty migrations

**What goes wrong:** Running `alembic revision --autogenerate` produces a migration with empty `upgrade()` and `downgrade()` functions — the schema is not detected.

**Why it happens:** The SQLAlchemy models are not imported before `target_metadata = Base.metadata` is evaluated. `Base.metadata.tables` is an empty dict if no model modules have been imported.

**How to avoid:** In `alembic/env.py`, explicitly import all model modules before the `target_metadata` assignment:
```python
from api.models.models import Base  # imports all Table objects into Base.metadata
target_metadata = Base.metadata
```

**Warning signs:** `alembic revision --autogenerate -m "init"` produces an empty `upgrade()` with no `op.create_table()` calls.

---

### Pitfall 3: Section hint cascade in parser

**What goes wrong:** After a section transition marker (e.g., "REBUTTAL ARGUMENT OF MR. SMITH"), every subsequent utterance gets `section_hint = "rebuttal"` instead of just the first one.

**Why it happens (F02 from spike):** Using a single `section_hint` variable that is set on the TOC marker and never cleared. The hint must be consumed on the first speaker flush after the marker, then cleared.

**How to avoid:** Use two separate variables as specified in the spike:
- `pending_section_hint`: set when TOC marker is detected
- `current_section_hint`: consumed from `pending_section_hint` at the start of each new speaker turn, cleared after flush

**Warning signs:** `section_hint_count` in QA stats is much larger than the number of section transitions (should be 1–3 for a typical argument, not 30+).

---

### Pitfall 4: instructor double-retry with SDK internal retry

**What goes wrong:** The Anthropic Python SDK retries 2x on 429 and 503 by default. Wrapping those calls with a tenacity `@retry` means a single transient error causes up to 6 total API calls (2 tenacity × 3 SDK attempts).

**How to avoid:** Disable SDK retries with `anthropic.AsyncAnthropic(max_retries=0)` and let tenacity own all transient error retries.

**Warning signs:** Parse step takes 3–4× longer than expected on rate-limit errors; API usage shows 3–6× more calls than expected for a failed parse.

---

### Pitfall 5: `ON BEHALF OF` treated as speaker label (F04)

**What goes wrong:** The Obergefell transcript contains "ON BEHALF OF PETITIONERS ON QUESTION 1" as a section announcement. If `TOC_SECTION_RE` does not cover this variant, it gets appended to the previous speaker's utterance (sequence 2 in the Obergefell spike result shows this).

**How to avoid:** Add `ON\s+BEHALF\s+OF` to `TOC_SECTION_RE` as specified in the spike skill:
```python
TOC_SECTION_RE = re.compile(
    r"^(?:ORAL\s+ARGUMENT\s+OF|REBUTTAL\s+ARGUMENT\s+(?:OF)?|REBUTTAL\s+ARGUMENT\s*:?"
    r"|ON\s+BEHALF\s+OF)"
    r"(?:\s+.*)?$",
    re.IGNORECASE,
)
```

**Warning signs:** Utterance sequence 2 in Obergefell contains "ON BEHALF OF PETITIONERS ON QUESTION 1" appended to Chief Justice Roberts' text. Check the first few utterances.

---

### Pitfall 6: Missing unique constraint on `case_arguments` leads to duplicate consolidated dockets

**What goes wrong:** Running ingest twice for the same argument creates duplicate rows in `case_arguments`, producing duplicate case records for the consolidated dockets (14-562, 14-571, 14-574).

**How to avoid:** The `case_arguments` composite primary key `(case_id, argument_id)` prevents duplicates. The `cases.docket_number` column has a `UNIQUE` constraint. The ingest step must use `INSERT ... ON CONFLICT DO NOTHING` (or `merge`) for idempotency.

---

### Pitfall 7: SvelteKit `+page.server.ts` uses absolute URL without fallback

**What goes wrong:** If `FASTAPI_BASE_URL` is not set in the `.env` file, `$env/static/private` returns an empty string, making the fetch URL `undefined/arguments/1/utterances`.

**How to avoid:** Validate `FASTAPI_BASE_URL` at startup using a `pydantic-settings` Settings class equivalent in SvelteKit (or a server-side validation hook). Fail loudly at startup if the var is missing.

---

## Code Examples

### PDF Extraction (from spike — copy exactly)

[CITED: .claude/skills/spike-findings-scotuschat/references/pdf-extraction.md]
```python
import pdfplumber
import re
from pathlib import Path

LINE_NUM_RE = re.compile(r"^\s{0,3}(\d{1,2})\s")
HEADER_RE = re.compile(
    r"^(?:Official|ALDERSON|Heritage|HERITAGE|Alderson|www\.|http|\(202\)|\d{3,4}\s+L\s+Street)",
    re.IGNORECASE,
)
PAGE_NUM_RE = re.compile(r"^\d+$")
WORD_INDEX_RE = re.compile(r"^\w[\w\s,'.\-]{0,30}\s+\[\d+\]\s+\d+:\d+")

def _is_word_index_page(raw_text: str) -> bool:
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    hits = sum(1 for l in lines if WORD_INDEX_RE.match(l))
    return hits >= 3

def strip_line_number(line: str) -> str:
    m = LINE_NUM_RE.match(line)
    return line[m.end() - 1:].strip() if m else line.strip()

def extract_pages(pdf_path: Path) -> list[str]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(3, len(pdf.pages)):          # skip first 3: cover, caption, TOC
            raw = pdf.pages[i].extract_text(layout=False) or ""
            if _is_word_index_page(raw):             # stop at word index
                break
            lines = []
            for raw_line in raw.split("\n"):
                line = strip_line_number(raw_line)
                if HEADER_RE.match(line) or PAGE_NUM_RE.match(line):
                    continue
                lines.append(line)
            pages.append("\n".join(lines))
    return pages

def normalize_text(text: str) -> str:
    return text.replace("­", "--").strip()   # soft hyphen → double dash (F11)
```

### Side Assignment from Raw Speaker Label (D-09)

```python
from enum import Enum
import re

class Side(str, Enum):
    BENCH = "BENCH"
    ADVOCATE = "ADVOCATE"
    UNKNOWN = "UNKNOWN"

BENCH_RE = re.compile(r"^(?:CHIEF\s+JUSTICE|JUSTICE\s+|QUESTION)", re.IGNORECASE)
ADVOCATE_RE = re.compile(r"^(?:MR\.|MS\.|MRS\.|GENERAL\s+)", re.IGNORECASE)

def assign_side(raw_speaker_label: str | None, is_stage_direction: bool) -> Side:
    if is_stage_direction or raw_speaker_label is None:
        return Side.UNKNOWN
    if BENCH_RE.match(raw_speaker_label):
        return Side.BENCH
    if ADVOCATE_RE.match(raw_speaker_label):
        return Side.ADVOCATE
    return Side.UNKNOWN
```

### FastAPI Router Pattern (D-18)

```python
# api/routers/arguments.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.core.database import get_db
from api.services import arguments as argument_service
from api.schemas.utterance import UtteranceResponse, ArgumentUtterancesResponse

router = APIRouter(prefix="/arguments", tags=["arguments"])

@router.get("/{argument_id}/utterances", response_model=ArgumentUtterancesResponse)
async def get_utterances(argument_id: int, db: AsyncSession = Depends(get_db)):
    utterances = await argument_service.get_utterances_for_argument(db, argument_id)
    if not utterances:
        raise HTTPException(status_code=404, detail="Argument not found")
    return ArgumentUtterancesResponse(utterances=utterances)
```

### Dev Startup Script (D-07, INFRA-03)

```powershell
# scripts/dev-start.ps1
# Starts PostgreSQL portable, uvicorn, and SvelteKit vite dev server

$REPO_ROOT = Split-Path -Parent $PSScriptRoot
$PGDATA = "$REPO_ROOT\data\pgdata"
$PGBIN = "$REPO_ROOT\data\pgsql\bin"        # adjust to your Postgres portable location

# 1. Start Postgres if not running
if (-not (& "$PGBIN\pg_ctl" status -D $PGDATA 2>$null | Select-String "server is running")) {
    Write-Host "Starting PostgreSQL..."
    & "$PGBIN\pg_ctl" start -D $PGDATA -l "$PGDATA\logfile"
    Start-Sleep -Seconds 2
}

# 2. Run migrations
Push-Location $REPO_ROOT
Write-Host "Running Alembic migrations..."
alembic upgrade head

# 3. Start FastAPI in background
Write-Host "Starting FastAPI (uvicorn)..."
$apiJob = Start-Job -ScriptBlock {
    Set-Location $using:REPO_ROOT
    uvicorn api.main:app --reload --port 8000
}

# 4. Start SvelteKit dev server in background
Write-Host "Starting SvelteKit dev server..."
$appJob = Start-Job -ScriptBlock {
    Set-Location "$using:REPO_ROOT\app"
    npm run dev
}

Pop-Location
Write-Host "Services started. FastAPI: http://localhost:8000 | SvelteKit: http://localhost:5173"
Write-Host "Press Ctrl+C to stop."

# Keep running, show output
try {
    while ($true) {
        Receive-Job $apiJob, $appJob
        Start-Sleep -Seconds 1
    }
} finally {
    Stop-Job $apiJob, $appJob
    Remove-Job $apiJob, $appJob
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI 0.93+ | Deprecated event hooks; use lifespan |
| `instructor.patch(client)` | `instructor.from_anthropic(client)` or `instructor.from_provider(...)` | instructor v1.0 (Apr 2024) | Old patch API still works but deprecated |
| Svelte stores (`writable`, `readable`) | Svelte 5 Runes (`$state`, `$derived`, `$effect`) | Svelte 5.0 (Oct 2024) | Runes are compile-time; no stores needed for component state |
| `npm create svelte@latest` | `npx sv create` (official Svelte CLI) | 2024 | New sv CLI replaces older create-svelte |
| psycopg2 for both sync and async | asyncpg for async, psycopg2 for Alembic only | SQLAlchemy 2.0 | asyncpg is significantly faster for async paths |

**Deprecated/outdated:**
- `Base.metadata.create_all()`: Never acceptable in this project — Alembic is sole DDL authority
- `instructor.patch()`: Works but deprecated since instructor v1.0; use `from_anthropic()` or `from_provider()`
- Svelte 4 `$store` syntax in `.svelte` files: Use `$state` rune instead

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `instructor.from_anthropic(AsyncAnthropic(max_retries=0), mode=Mode.TOOLS)` is the correct async constructor | Pattern 4 | If API changed, planner must check `instructor[anthropic]` docs at time of execution |
| A2 | `claude-haiku-4-5-20251001` is valid model name for Anthropic API at execution time | Standard Stack | Model IDs may have changed; verify against Anthropic API console |
| A3 | Obergefell Q1 PDF is already downloaded at `.planning/spikes/001-pdf-text-extraction/pdfs/obergefell-14-556-q1.pdf` | Environment Availability | If file moved, ingest step needs original URL: `https://www.supremecourt.gov/oral_arguments/argument_transcripts/2014/14-556q1_l5gm.pdf` |
| A4 | `npx sv create` is the correct SvelteKit 2 scaffold command | Standard Stack | If CLI changed, check `svelte.dev/docs/kit/creating-a-project` |
| A5 | All package versions listed in Standard Stack are current stable releases | Standard Stack | Verify with `pip index versions` and `npm view <pkg> version` before writing requirements.txt |
| A6 | `$env/static/private` in SvelteKit 2 requires vars to be present at build time (static), not runtime | Pattern 5 | If vars are only available at runtime, must use `$env/dynamic/private` instead |

**If this table is empty:** N/A — assumptions present above.

---

## Open Questions

1. **Pipeline uses sync or async SQLAlchemy?**
   - What we know: The pipeline is a CLI process, not an async server. ARCHITECTURE.md suggests psycopg3 sync pool for the pipeline. But the decision to use asyncpg for FastAPI and `sqlalchemy.async` is clear.
   - What's unclear: Should the pipeline itself use async SQLAlchemy (matching the models) or a separate sync engine? Using async in a CLI requires `asyncio.run()` wrappers.
   - Recommendation: Use async SQLAlchemy with `asyncio.run()` in the pipeline CLI entry points. This allows the pipeline and FastAPI to share the same `models.py` without duplicating engine setup. The `async_sessionmaker` pattern works in both contexts.

2. **Instructor `max_retries` parameter location**
   - What we know: The `create()` method accepts `max_retries: int = 1` (default). The `from_anthropic()` constructor's `max_retries` param behavior was not fully confirmed.
   - What's unclear: Whether `max_retries` on `from_anthropic()` constructor vs. per-call `create(max_retries=2)` behaves differently.
   - Recommendation: Pass `max_retries=2` on each `create()` call for explicit per-call control. Set `Anthropic(max_retries=0)` to disable SDK-level retries. Verify at implementation time.

3. **`side` field assignment: parser or LLM?**
   - What we know: D-09 says "LLM assigns side at parse time based on the raw speaker label." The spike's `ParsedUtterance` schema does NOT include a `side` field. The rule-based parser also does not assign `side`.
   - What's unclear: Whether the LLM is asked to assign `side` as part of the `ParsedUtterance` output, or if `side` is a post-processing step applied deterministically from the label.
   - Recommendation: Assign `side` deterministically from `raw_speaker_label` using the `assign_side()` function in the Code Examples section — it is fully rule-based and highly accurate for SCOTUS labels. The pattern is: `JUSTICE.*|CHIEF JUSTICE.*|QUESTION` → BENCH; `MR.|MS.|MRS.|GENERAL` → ADVOCATE. No LLM needed for this assignment. This is simpler, cheaper, and more reliable than asking the LLM.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Pipeline, FastAPI | [ASSUMED ✓] | 3.12.x | Python 3.11 acceptable |
| Node.js 20+ | SvelteKit | [ASSUMED ✓] | 20.x | Node.js 18 LTS acceptable |
| PostgreSQL (portable) | All DB operations | ✗ confirmed present | — | Must set up; instructions in Pattern 6 |
| Anthropic API key | Parse step | Not checked | — | Required; set in `.env` as `ANTHROPIC_API_KEY` |
| PDF file (Obergefell Q1) | Ingest smoke test | ✓ | — | `.planning/spikes/001-pdf-text-extraction/pdfs/obergefell-14-556-q1.pdf` |
| `pip` / venv | Python deps | [ASSUMED ✓] | — | — |
| `npm` | SvelteKit deps | [ASSUMED ✓] | — | — |

**Missing dependencies with no fallback:**
- PostgreSQL portable ZIP: Must be downloaded and extracted before running dev startup script. Operator must run `initdb` to create the data directory at `data/pgdata`.
- Anthropic API key: Must be in `.env` before the parse step can run.

**Missing dependencies with fallback:**
- None critical for Phase 1 beyond Postgres and Anthropic key.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pytest.ini` or `pyproject.toml [tool.pytest.ini_options]` — Wave 0 gap |
| Quick run command | `pytest pipeline/tests/ -x -q` |
| Full suite command | `pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | All 10 tables exist after migration | smoke | `alembic upgrade head && pytest tests/test_schema.py -x` | ❌ Wave 0 |
| INFRA-02 | `case_arguments` M:M row created for consolidated dockets | unit | `pytest tests/test_ingest.py::test_consolidated_dockets -x` | ❌ Wave 0 |
| PIPE-01 | Ingest creates case, argument, pipeline_run records | unit | `pytest pipeline/tests/test_ingest.py -x` | ❌ Wave 0 |
| PIPE-03 | Parse produces correct utterance rows | unit | `pytest pipeline/tests/test_parse.py -x` | ❌ Wave 0 |
| PIPE-04 | Every utterance has pipeline_run_id and strategy | unit | `pytest pipeline/tests/test_parse.py::test_run_id_strategy -x` | ❌ Wave 0 |
| PIPE-05 | Stage directions classified correctly (Obergefell has 8) | unit | `pytest pipeline/tests/test_parse.py::test_stage_directions -x` | ❌ Wave 0 |
| PIPE-06 | Structural failure (bad schema) recorded, not retried > 2x | unit | `pytest pipeline/tests/test_parse.py::test_llm_failure_modes -x` | ❌ Wave 0 |
| PIPE-10 | Status transitions: pending→running→completed | unit | `pytest pipeline/tests/test_pipeline_run.py::test_state_machine -x` | ❌ Wave 0 |
| PIPE-11 | Re-run creates new rows, old rows preserved | unit | `pytest pipeline/tests/test_pipeline_run.py::test_rerun -x` | ❌ Wave 0 |
| API-01 | `GET /arguments/{id}/utterances` returns ordered utterances | integration | `pytest api/tests/test_arguments.py -x` | ❌ Wave 0 |
| UI-01/02/03 | Chat renders with correct sides + stage directions | manual | `npm run dev` → browser inspection | manual only |

### Sampling Rate

- **Per task commit:** `pytest pipeline/tests/ -x -q`
- **Per wave merge:** `pytest -x -q`
- **Phase gate:** Full suite green + manual browser verification of Obergefell chat view

### Wave 0 Gaps

- [ ] `tests/test_schema.py` — verifies all 10 tables exist after migration
- [ ] `pipeline/tests/test_ingest.py` — ingest command unit tests
- [ ] `pipeline/tests/test_parse.py` — parser unit tests (state machine, stage dirs, section hints)
- [ ] `pipeline/tests/test_pipeline_run.py` — state machine and re-run behavior
- [ ] `api/tests/test_arguments.py` — endpoint integration tests
- [ ] `pytest.ini` or `pyproject.toml [tool.pytest.ini_options]` — test runner config
- [ ] `conftest.py` — shared fixtures (test DB, async session, factory functions)
- [ ] Framework install: `pip install pytest pytest-asyncio httpx` (httpx for FastAPI TestClient async)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No user auth in Phase 1 (read-only, no accounts) |
| V3 Session Management | No | No sessions; server load functions are stateless |
| V4 Access Control | No | Pipeline is operator-local; API is read-only with no auth in Phase 1 |
| V5 Input Validation | Yes | Pydantic v2 on all FastAPI responses; instructor validates LLM output |
| V6 Cryptography | No | No secrets stored in DB; API key in `.env` only |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via argument ID path param | Tampering | SQLAlchemy ORM parameterizes all queries automatically |
| SSRF via PDF download URL | Elevation | Ingest step downloads only `supremecourt.gov` PDFs; validate URL scheme and host before httpx call |
| LLM prompt injection via transcript content | Spoofing | Transcript text is pre-cleaned before LLM; instructor schema validation rejects malformed output |
| `ANTHROPIC_API_KEY` leaked in repo | Info Disclosure | Key in `.env` only; `.env` is gitignored; never hardcode in source |
| `PUBLIC_` SvelteKit env var exposes internal URL | Info Disclosure | `FASTAPI_BASE_URL` must use `$env/static/private` — never `$env/static/public` |

---

## Sources

### Primary (HIGH confidence)
- `.claude/skills/spike-findings-scotuschat/SKILL.md` — spike requirements and validated patterns
- `.claude/skills/spike-findings-scotuschat/references/pdf-extraction.md` — pdfplumber extraction (tested on 4 transcripts)
- `.claude/skills/spike-findings-scotuschat/references/parse-utterances.md` — full parser with regex patterns, failure taxonomy
- `.claude/skills/spike-findings-scotuschat/sources/002-parse-prompt-schema/parse.py` — complete working parser implementation
- `.planning/research/STACK.md` — technology stack (verified against official sources 2026-06-11)
- `.planning/research/ARCHITECTURE.md` — architecture patterns (verified against official sources 2026-06-11)
- `.planning/research/PITFALLS.md` — domain pitfalls (researched 2026-06-11)
- CLAUDE.md — hard constraints (Alembic-only DDL, asyncpg `statement_cache_size=0`, pipeline offline-only)
- [github.com/sqlalchemy/alembic/blob/main/alembic/templates/async/env.py](https://github.com/sqlalchemy/alembic/blob/main/alembic/templates/async/env.py) — official async env.py template
- [fastapi.tiangolo.com/advanced/events/](https://fastapi.tiangolo.com/advanced/events/) — FastAPI lifespan pattern

### Secondary (MEDIUM confidence)
- [python.useinstructor.com/integrations/anthropic/](https://python.useinstructor.com/integrations/anthropic/) — instructor + Anthropic integration (from_provider, Mode.TOOLS, async)
- [python.useinstructor.com/concepts/retrying/](https://python.useinstructor.com/concepts/retrying/) — instructor retry + tenacity combined pattern
- [github.com/sqlalchemy/sqlalchemy/issues/6467](https://github.com/sqlalchemy/sqlalchemy/issues/6467) — `statement_cache_size=0` in `connect_args` (confirmed required)
- [svelte.dev/docs/kit/$env-static-private](https://svelte.dev/docs/$env-static-private) — SvelteKit server-only env vars

### Tertiary (LOW confidence — needs validation at execution time)
- Model name `claude-haiku-4-5-20251001` — verify against Anthropic API console at implementation time
- Exact instructor constructor signature for `from_anthropic` — verify against installed package docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages from prior project research + official sources
- Schema design: HIGH — 10-table schema derived from REQUIREMENTS.md + spike findings; M:M design confirmed necessary for INFRA-02
- Parse pipeline patterns: HIGH — spike-validated implementation with working code
- instructor/Anthropic patterns: MEDIUM — API verified through docs but exact constructor parameters should be confirmed at implementation time
- SvelteKit patterns: HIGH — confirmed against official svelte.dev docs
- Pitfalls: HIGH — drawn from spike findings (empirically verified) + prior research

**Research date:** 2026-06-11
**Valid until:** 2026-09-11 (90 days — stable stack with slow-moving official libs; instructor and Anthropic model names change faster, re-verify those)
