# Architecture Patterns

**Domain:** Python data pipeline + FastAPI API + SvelteKit frontend + PostgreSQL
**Project:** SCOTUS Chat — oral arguments as a chat interface
**Researched:** 2026-06-11
**Confidence:** HIGH (stack is well-documented; patterns verified against official sources)

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     OFFLINE PIPELINE                            │
│  (runs on developer machine / CI; never serves live requests)   │
│                                                                 │
│  CLI entrypoint                                                 │
│    └─ Step 1: Ingest   (download PDF, create pipeline_run)      │
│    └─ Step 2: Parse    (LLM extracts utterances)                │
│    └─ Step 3: Resolve  (LLM matches speakers to people records) │
│    └─ Step 4: Enrich   (bio/photo from Oyez, FJC, scotus.gov)   │
│    └─ Step 5: Extract  (LLM pulls citations as raw strings)     │
│                                                                 │
│  Database access: psycopg3 sync ConnectionPool                  │
│  LLM calls: anthropic SDK + instructor + tenacity               │
└───────────────────────────┬─────────────────────────────────────┘
                            │ writes structured rows
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     POSTGRESQL (shared)                         │
│  Managed by Alembic (single source of schema truth)             │
│  Hosted on Digital Ocean Managed Postgres                       │
│                                                                 │
│  Tables: cases, arguments, pipeline_runs, utterances,           │
│          people, bios, citations, speaker_resolution_log        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ reads (read-only queries)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FASTAPI (read-only API)                     │
│  Digital Ocean App Platform                                     │
│                                                                 │
│  Startup: create AsyncEngine + async_sessionmaker via lifespan  │
│  Deps:    AsyncSession injected per-request                     │
│  Routes:  /cases, /arguments/{id}, /utterances/{arg_id},        │
│           /people/{id}  — all GET, no writes                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP (server-side fetch during SSR,
                            │        direct fetch in browser)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SVELTEKIT FRONTEND                          │
│  Digital Ocean App Platform (or Static Pages)                   │
│                                                                 │
│  +page.server.ts load functions → fetch FastAPI on SSR          │
│  Client-side navigation → fetch FastAPI directly                │
│  No +server.ts API routes needed for initial build              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

### 1. Offline Pipeline

**Responsibility:** Transform raw PDFs into structured database rows. Has no network listener and is never invoked by the live application. The pipeline owns all write access to utterances, citations, and speaker resolution data.

**Communicates with:**
- PostgreSQL (psycopg3 sync pool — pipeline is a CLI process, not an async server)
- Claude API (via anthropic SDK)
- External enrichment APIs (Oyez, FJC, supremecourt.gov — HTTP calls only)
- Local filesystem (PDF storage)

**Does NOT communicate with:** FastAPI. The pipeline and the API are decoupled at the database layer. The pipeline runs offline; its work is visible to the API only after rows are committed.

**Key invariant:** Each pipeline step reads its own input from DB rows written by the prior step (using `pipeline_run_id` as the linking key). Steps are independently re-runnable. A step never reads from another step's in-memory state.

---

### 2. FastAPI Backend

**Responsibility:** Serve the structured data the pipeline produced. Read-only in the initial build — it queries PostgreSQL and serializes results as JSON. Owns no business logic beyond query shaping and serialization.

**Communicates with:**
- PostgreSQL (SQLAlchemy async + asyncpg pool via lifespan context manager)
- SvelteKit frontend (HTTP)

**Does NOT communicate with:** the pipeline, the Claude API, or external enrichment sources. If later a write API is needed (e.g., admin promotion of a pipeline run), it should go through the same async session pattern with an explicit transaction per operation.

---

### 3. SvelteKit Frontend

**Responsibility:** Render the chat-style UI. Fetches all data from FastAPI. Has no direct database access.

**Communicates with:** FastAPI (HTTP GET requests, both SSR and client-side)

---

## Data Flow: PDF to Utterances on Screen

```
1. Developer runs: python -m pipeline ingest --url <scotus.gov PDF URL>
   → Downloads PDF, stores locally
   → Creates: case record (if new), argument record, pipeline_run record (status=running)

2. Step 2 (Parse):
   → Extracts raw text from PDF (pdfminer.six or pypdf)
   → Chunks text if > threshold (see LLM Chunking section)
   → Sends chunks to Claude with structured output schema
   → Inserts utterance rows (linked to pipeline_run_id, with raw_speaker_name)

3. Step 3 (Resolve):
   → Queries utterances for this pipeline_run_id
   → Sends raw_speaker_name list + case metadata to Claude
   → Claude returns speaker→person_id mappings
   → Updates utterances with resolved person_id
   → Creates/updates people rows as needed
   → Logs resolution decisions in speaker_resolution_log

4. Step 4 (Enrich):
   → Queries people without complete bios
   → Calls Oyez API, FJC API, supremecourt.gov
   → Inserts/updates bio, photo_url, tenure data

5. Step 5 (Citations):
   → Queries utterances for this pipeline_run_id
   → Sends utterance text batches to Claude
   → Claude returns citation strings per utterance
   → Inserts citation rows (raw text only, no resolution)

6. Pipeline marks pipeline_run as status=completed

7. User visits /arguments/[id] in browser
   → SvelteKit +page.server.ts load function fires on server
   → Calls FastAPI: GET /utterances/{argument_id}
   → FastAPI queries PostgreSQL (joins utterances, people, bios)
   → Returns JSON
   → SvelteKit renders HTML with utterances as chat bubbles
   → Page hydrates; subsequent navigations use client-side fetch to same FastAPI endpoints
```

---

## Pipeline/API Database Sharing Strategy

### The Core Rule: Segregated Access, Shared Schema

The pipeline and API share one PostgreSQL instance but use different connection strategies suited to their runtime model:

| Layer | Driver | Pool Type | Rationale |
|-------|--------|-----------|-----------|
| Pipeline (CLI) | psycopg3 sync | `ConnectionPool` (psycopg_pool) | CLI is synchronous; no event loop overhead needed |
| FastAPI | asyncpg via SQLAlchemy 2.0 async | `AsyncEngine` pool (built-in) | FastAPI is async; blocking DB calls would starve the event loop |

Neither layer needs to know about the other's connections. PostgreSQL serializes concurrent access naturally through its MVCC model.

### Schema Authority: Alembic

Alembic is the single migration authority. Both the pipeline and FastAPI import from the same `models.py` (SQLAlchemy declarative base). Migration files live in `db/migrations/`. The pipeline runs `alembic upgrade head` before any step if desired, or migrations are applied separately before deployment.

**Critical:** Never let the pipeline or FastAPI auto-create tables (`Base.metadata.create_all`). Only Alembic touches DDL. This ensures the shared schema stays version-controlled and auditable.

### Preventing Schema Drift

```
project/
├── db/
│   ├── models.py          ← shared SQLAlchemy models
│   ├── migrations/        ← Alembic migration files
│   └── alembic.ini
├── pipeline/
│   └── steps/             ← imports from db.models
└── api/
    └── routes/            ← imports from db.models
```

---

## Pipeline Run State Management

### State Machine

```
        ┌──────────┐
        │ pending  │  (created on ingest, before step starts)
        └────┬─────┘
             │ step begins
             ▼
        ┌──────────┐
        │ running  │  (set atomically at step start)
        └────┬─────┘
             │
       ┌─────┴──────┐
       ▼            ▼
 ┌──────────┐  ┌──────────┐
 │completed │  │  failed  │
 └──────────┘  └──────────┘
```

### Implementation Pattern

Each step follows this exact pattern:

```python
def run_step(pipeline_run_id: int, conn: Connection) -> None:
    # 1. Assert expected prior state (idempotency guard)
    with conn.transaction():
        run = fetch_pipeline_run(conn, pipeline_run_id)
        if run.status not in ("pending", "failed"):
            raise StepAlreadyCompleted(pipeline_run_id)
        set_pipeline_run_status(conn, pipeline_run_id, "running")

    # 2. Do the work (outside the guard transaction)
    try:
        perform_work(conn, pipeline_run_id)

        # 3. Mark complete
        with conn.transaction():
            set_pipeline_run_status(conn, pipeline_run_id, "completed")

    except Exception as exc:
        with conn.transaction():
            set_pipeline_run_status(conn, pipeline_run_id, "failed", error=str(exc))
        raise
```

Key properties:
- Status is updated atomically with a transaction
- A `running` step cannot be re-entered without manual reset (prevents double-processing)
- `failed` steps can be retried (re-enter from `failed → running`)
- Old rows are preserved; re-runs create a new `pipeline_run_id` linked to the same argument

### Advisory Lock (Optional, for distributed/CI use)

If multiple developers or CI runners might trigger the same pipeline step simultaneously, use a PostgreSQL advisory lock keyed on `(namespace_int, pipeline_run_id)` before the state check. This adds a hard mutual exclusion layer on top of the optimistic state check.

```python
# Lock namespace 1001 = pipeline step mutex
conn.execute("SELECT pg_advisory_xact_lock(1001, %s)", [pipeline_run_id])
```

Transaction-level advisory locks (`pg_advisory_xact_lock`) auto-release on commit/rollback, so no cleanup code is needed.

---

## LLM Integration: Structured Output and Reliability

### Library Stack

```
anthropic SDK          ← official Anthropic Python client
instructor             ← wraps anthropic, adds Pydantic validation + auto-retry
tenacity               ← exponential backoff for rate limits and transient failures
```

### Pydantic Output Models Per Step

Each LLM step defines an explicit Pydantic model for its output. Claude returns structured JSON that instructor validates; on validation failure, instructor retries automatically (up to a configured max).

```python
class ParsedUtterance(BaseModel):
    speaker_raw: str
    text: str
    is_stage_direction: bool
    sequence: int

class ParseResponse(BaseModel):
    utterances: list[ParsedUtterance]
```

### Retry Strategy

```python
@retry(
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APITimeoutError)),
    reraise=True
)
def call_claude(client, prompt, response_model):
    return client.messages.parse(...)
```

Pydantic validation failures (malformed JSON, missing fields) are handled by instructor's internal retry loop. Rate limit / timeout errors are handled by tenacity's outer retry loop. These are distinct failure modes and should be handled by separate mechanisms.

### Idempotency Key Pattern

Before making any LLM call, store an idempotency key derived from the input content hash + step name. If a key already exists in the DB, return the cached result without calling the API. This prevents duplicate charges and duplicate rows if the pipeline crashes mid-step.

```python
content_hash = hashlib.sha256(chunk_text.encode()).hexdigest()
key = f"parse:{pipeline_run_id}:{content_hash}"
```

---

## LLM Chunking for Large Transcripts

### Context Window Reality

Claude (Sonnet/Opus) supports 200K tokens. A SCOTUS oral argument transcript is typically 40-80 pages of text — roughly 20,000 to 40,000 tokens after PDF extraction. This fits comfortably in a single Claude context window.

**For the parse step, a single-call strategy is preferred:**
- Send the entire transcript text in one API call
- Ask Claude to return a list of utterance objects as structured JSON
- Avoids speaker continuity problems that arise when a single utterance spans chunk boundaries

### When Chunking Is Required

Chunking becomes necessary only if:
1. A single transcript exceeds ~150K tokens (leaves room for system prompt + output)
2. The structured output JSON itself becomes very large (instructor has streaming support)

### Chunking Strategy When Needed

For unusually long transcripts, chunk by natural speaker boundary rather than fixed token count:

```
Strategy: Boundary-aware chunking
1. Split on double newlines (paragraph breaks)
2. Accumulate paragraphs until threshold (e.g., 80K tokens)
3. When adding next paragraph would exceed threshold, finalize chunk
4. Add a 2-paragraph overlap to the next chunk to preserve speaker context
5. Tag each chunk with its position (chunk_index, is_first, is_last)
6. Include a system prompt note: "This is chunk N of M. Prior speakers: [last 3]"
7. After all chunks processed, merge and de-duplicate on sequence number
```

**Anti-pattern to avoid:** Fixed-token splitting with no regard for sentence or speaker boundaries. This causes utterances to be split mid-sentence and confuses speaker attribution. The "lost in the middle" problem is real — information buried in the middle of a long context receives less attention from the model.

### Step-Specific Chunking Needs

| Step | Typical input size | Chunking needed? |
|------|--------------------|-----------------|
| Parse | 20-40K tokens/transcript | Rarely — single call preferred |
| Resolve | Small (speaker name list + metadata) | Never |
| Enrich | External API calls, not LLM | N/A |
| Citations | Utterance batches, 1-2K tokens each | Batch by utterance, not by chunk |

For citations, process utterances in batches of 20-50 per LLM call rather than one utterance at a time. This reduces API call count significantly while keeping each call well within context limits.

---

## FastAPI Connection Pooling

### Async Pattern via SQLAlchemy 2.0 Lifespan

```python
# api/db.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from contextlib import asynccontextmanager

engine = None
SessionLocal = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine, SessionLocal
    engine = create_async_engine(
        settings.DATABASE_URL,           # postgresql+asyncpg://...
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,              # detect stale connections
    )
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    yield
    await engine.dispose()

# Dependency
async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
```

**pool_size guidance for Digital Ocean Managed Postgres:**
- Default max connections: 25 (smallest plan), 97 (basic plan)
- FastAPI workers: 1-2 on App Platform starter tier
- pool_size=10, max_overflow=10 is safe for starter; adjust up with plan size
- Enable `pool_pre_ping=True` — DO Managed Postgres drops idle connections after 5 minutes

### Pipeline Connection (Synchronous)

```python
# pipeline/db.py
from psycopg_pool import ConnectionPool

pool = ConnectionPool(conninfo=settings.DATABASE_URL, min_size=1, max_size=5)

# Context manager usage per step
with pool.connection() as conn:
    run_step(pipeline_run_id, conn)
```

The pipeline runs as a short-lived CLI process. A pool of 1-5 connections is more than sufficient. The pipeline should close the pool when the process exits.

---

## SvelteKit-FastAPI Data Fetching

### Recommended Pattern: Server Load Functions

Use `+page.server.ts` as the primary data fetching mechanism. This is the right default because:

1. The FastAPI base URL is a secret (backend URL should not be exposed in browser JavaScript)
2. SSR gives immediate HTML without a client-side fetch waterfall
3. SvelteKit's internal fetch optimization skips the HTTP round-trip during SSR when fetching the same-origin API routes, but since FastAPI is a separate service, the fetch does make a network call — keep this in mind for latency

```typescript
// routes/arguments/[id]/+page.server.ts
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
    const response = await fetch(`${FASTAPI_BASE_URL}/arguments/${params.id}/utterances`);
    if (!response.ok) throw error(response.status);
    const data = await response.json();
    return { utterances: data.utterances, argument: data.argument };
};
```

### When to Use +server.ts API Routes (SvelteKit BFF Layer)

Add a SvelteKit API route only when:
- You need to aggregate multiple FastAPI calls into one frontend request
- You need to add caching (e.g., `Cache-Control` headers for static case data)
- A future feature requires authentication and you want to hide tokens from the browser

For the initial build, server load functions are sufficient. A BFF (Backend for Frontend) API route layer is a later optimization, not a day-one requirement.

### Environment Variable Strategy

```
FASTAPI_BASE_URL=http://api:8000   ← used in +page.server.ts (server side only)
PUBLIC_APP_NAME=SCOTUS Chat        ← PUBLIC_ prefix exposes to browser
```

Never expose the FastAPI URL in `PUBLIC_` variables — it would appear in client-side JS bundles.

---

## Suggested Build Order

The dependency graph drives this ordering:

```
1. Database schema + migrations (Alembic)
   ← everything depends on this; nothing else can start

2. Pipeline Step 1: Ingest
   ← establishes the pipeline_run state machine; proves DB writes work

3. Pipeline Step 2: Parse (LLM utterance extraction)
   ← the core value; validates LLM integration and chunking strategy

4. FastAPI read routes for utterances + arguments
   ← need parsed data to develop against; API and pipeline can now be tested together

5. SvelteKit chat UI (consumes FastAPI)
   ← needs API working first; can use mock data for early component work

6. Pipeline Step 3: Resolve (speaker → people matching)
   ← depends on utterances existing; enriches UI with real names

7. Pipeline Step 4: Enrich (bio/photo)
   ← depends on people records from Step 3

8. Pipeline Step 5: Citations (raw text extraction)
   ← last because it's display-only and schema-safe to defer

9. End-to-end: run full pipeline on 2-3 real cases, verify UI renders correctly
```

**Why this order:**
- Schema first prevents circular refactoring of models
- Parse before API means the API has real data to serve (not just empty tables)
- UI after API prevents the SvelteKit developer from needing mock servers
- Enrich after Resolve because you can't enrich a person who hasn't been identified yet
- Citations last because they are display-only with no downstream dependencies in the initial build

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Pipeline Calling FastAPI

The pipeline must write to the database directly. Routing pipeline writes through the FastAPI HTTP layer adds unnecessary latency, couples two components that should be independent, and risks data integrity issues if the API layer adds validation logic that was not designed for batch ingest.

### Anti-Pattern 2: FastAPI Making Write Calls During Live Requests

The API is read-only in the initial build. Do not add a "trigger pipeline" endpoint that initiates LLM processing during a user's HTTP request. Pipeline processing is slow (seconds to minutes per transcript); it must remain an offline batch job.

### Anti-Pattern 3: Sharing a Single SQLAlchemy Session Across Pipeline Steps

Each pipeline step should open and close its own database connection/session. Sharing a long-lived session across steps creates the risk of uncommitted transactions blocking the API's reads (PostgreSQL MVCC means readers don't block writers, but long idle transactions do hold back `VACUUM` and can cause bloat on managed Postgres).

### Anti-Pattern 4: Storing Full Transcript Text in the DB as a Single Blob

Store PDF path (or object storage key) on the `pipeline_run` record. Do not store the raw extracted text as a column. It is large (100+ KB), never queried, and already available from the immutable source PDF. If reprocessing is needed, re-extract from the PDF.

### Anti-Pattern 5: Calling Claude Once Per Utterance for Citation Extraction

SCOTUS arguments contain 200-500 utterances per case. One LLM call per utterance would mean 200-500 API calls, each with a round-trip overhead and per-call base token cost. Batch 20-50 utterances per call instead.

### Anti-Pattern 6: Using `PUBLIC_FASTAPI_BASE_URL` in SvelteKit

The FastAPI base URL (internal Docker/App Platform service URL) must not be exposed to browsers. It is a server-side secret. Use an unprefixed environment variable consumed only in `+page.server.ts` and server-side hooks.

---

## Scalability Considerations

| Concern | Current (handful of cases) | Later (all SCOTUS cases, ~100/year) |
|---------|---------------------------|--------------------------------------|
| DB size | Trivial — hundreds of rows | Still small — ~2M utterances/decade is modest for Postgres |
| Pipeline throughput | Serial is fine | Parallelize step execution per argument via subprocess or a task queue (Celery/arq) |
| API read performance | No indexing needed initially | Add indexes on `argument_id`, `person_id`, `pipeline_run_id` when query plans show seq scans |
| LLM cost | Low (handful of cases) | Budget $5-10/case at Claude Sonnet pricing; 100 cases/year = ~$500-1000/year |
| Frontend caching | None needed | Cache case/argument lists with `Cache-Control: max-age=3600`; utterances are static once processed |

---

## Sources

- [SvelteKit Load Functions — Official Docs](https://svelte.dev/docs/kit/load)
- [FastAPI + SQLAlchemy 2.0 Async Patterns](https://dev-faizan.medium.com/fastapi-sqlalchemy-2-0-modern-async-database-patterns-7879d39b6843)
- [psycopg3 Connection Pool Documentation](https://www.psycopg.org/psycopg3/docs/advanced/pool.html)
- [PostgreSQL Advisory Locks — Official Docs](https://www.postgresql.org/docs/current/explicit-locking.html)
- [Instructor — Structured Outputs for Claude](https://python.useinstructor.com/integrations/anthropic/)
- [Idempotency in LLM Pipelines](https://tianpan.co/blog/2026-04-20-idempotency-llm-pipelines/)
- [Chunking Strategies for LLM Applications](https://www.pinecone.io/learn/chunking-strategies/)
- [FastAPI Async Connection Pooling](https://blog.poespas.me/posts/2024/08/08/fastapi-async-connection-pooling/)
- [SvelteKit Server-Only Load vs API Routes](https://teta.so/blog/sveltekit-load-functions-server-universal)
- [Alembic + FastAPI Migration Patterns](https://adex.ltd/database-migrations-with-alembic-and-fastapi-a-comprehensive-guide-using-poetry)
