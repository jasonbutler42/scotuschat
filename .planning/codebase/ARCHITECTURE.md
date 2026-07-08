<!-- refreshed: 2026-07-08 -->
# Architecture

**Analysis Date:** 2026-07-08

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                      SvelteKit Frontend (SSR via adapter-node)              │
│                              app/src/routes/                                │
│                                                                              │
│  ┌─ Public Routes ─────────────────┐  ┌──────── Admin Routes ────────────┐ │
│  │  /cases (list)                   │  │  /admin/login                    │ │
│  │  /cases/[slug] (picker)          │  │  /admin (hub)                    │ │
│  │  /cases/[slug]/arguments/[id]    │  │  /admin/pipeline (jobs list)     │ │
│  │  (chat/argument detail)          │  │  /admin/pipeline/[job_id] (detail)
│  │                                   │  │  /admin/arguments (list)         │ │
│  └─────────────────────────────────┘  │  /admin/arguments/[id] (edit)    │ │
│                                        │  /admin/people (list)            │ │
│                                        │  /admin/people/[id] (edit)       │ │
│                                        └─────────────────────────────────┘ │
│                                                                              │
│  Reusable Components (app/src/lib/components/):                             │
│    ChatBubble.svelte → individual utterance                                │
│    SectionRail.svelte → sticky section navigator (desktop)                 │
│    MobileNavBar.svelte → fixed-bottom pill nav (mobile)                    │
│    StageDirection.svelte → stage direction text                            │
│    ArgumentDetailsCard.svelte → shared docket/date/question card (P22)     │
│    RunStatusCard.svelte → job progress + status badge (P23)                │
│    ResolveCard.svelte → speaker resolution UI (P23)                        │
│    CreatePersonPopover.svelte → inline person creation (P24)               │
│    FailedStepGuidance.svelte → error recovery UI (P24)                     │
│                                                                              │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                 fetch() via FASTAPI_BASE_URL ($env/static/private)
                 X-Admin-Token header for /api/admin/* routes
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 FastAPI Backend (Read-only HTTP API)                        │
│                            api/main.py                                      │
│                                                                              │
│  ┌──────────────── Public Routers ─────────────────┐                        │
│  │  GET /cases                                      │                        │
│  │  GET /cases/{slug}/arguments/{id}/utterances    │                        │
│  │  GET /people/{id}                               │                        │
│  │    (api/routers/cases.py, arguments.py,         │                        │
│  │     people.py)                                   │                        │
│  └────────────────────────────────────────────────┘                        │
│                                                                              │
│  ┌──────────────── Admin Routers (Protected) ─────────────────┐             │
│  │  POST /api/admin/jobs (create pipeline job)                │             │
│  │  GET /api/admin/jobs (list all jobs)                       │             │
│  │  GET /api/admin/jobs/{job_id} (poll status)                │             │
│  │  POST /api/admin/jobs/{job_id}/resolve (confirm speakers)  │             │
│  │  POST /api/admin/jobs/{job_id}/people (create person)      │             │
│  │  GET /api/admin/arguments (list all args)                  │             │
│  │  GET /api/admin/arguments/{id} (detail + status log)       │             │
│  │  PATCH /api/admin/arguments/{id} (update dockets/dates)    │             │
│  │  PUT /api/admin/arguments/{id}/status (publish/unpublish)  │             │
│  │  GET /api/admin/people (list all speakers)                 │             │
│  │  GET /api/admin/people/{id} (detail)                       │             │
│  │  PATCH /api/admin/people/{id} (update bio)                 │             │
│  │    (api/routers/admin.py)                                  │             │
│  └────────────────────────────────────────────────┘             │
│                     │                                             │
│                     ▼                                             │
│    ┌─── api/services (business logic) ───┐                      │
│    │  - cases.py                          │                      │
│    │  - arguments.py                      │                      │
│    │  - people.py                         │                      │
│    │  - admin_jobs.py (job creation,      │                      │
│    │    status polling, step transition)  │                      │
│    │  - admin_arguments.py (list, detail, │                      │
│    │    status update, freeze-on-publish) │                      │
│    │  - admin_people.py (list, detail,    │                      │
│    │    merge, search)                    │                      │
│    │  - speakers.py (resolution logic)    │                      │
│    │  - pipeline_spawn.py (subprocess     │                      │
│    │    invocation for ingest/parse/      │                      │
│    │    resolve)                          │                      │
│    │  - spaces.py (DO Spaces upload)      │                      │
│    └────────────────────────────────────┘                        │
│                     │                                             │
│                     ▼                                             │
│    api/schemas/ (Pydantic v2 response models)                   │
│    - CasesResponse, CaseItem                                     │
│    - UtteranceResponse (with person, role, side)                │
│    - AdminJobResponse (status, current_step, error)             │
│    - ArgumentDetail (consolidated dockets, status, log)         │
│    - PersonDetail (full speaker profile)                        │
│                                                                  │
└─────────────────────────────┬──────────────────────────────────┘
                              │
              SQLAlchemy 2.0 async queries (api/core/database.py)
              AsyncSession, async_sessionmaker, lifespan context
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│            PostgreSQL 16 Database (Read by API, Written by Pipeline)        │
│                         api/models/models.py                                │
│                    13 tables (Alembic DDL authority)                         │
│                                                                              │
│  Core Domain:                                                                │
│    roles → people → court_tenures (Justice metadata)                        │
│    cases ↔ case_arguments ↔ arguments (M:M join, consolidated dockets)     │
│    argument_participants, utterances (per pipeline_run_id)                  │
│    argument_status_log (audit trail of status transitions — P22)            │
│    speaker_alias (raw label → person mapping)                              │
│                                                                              │
│  Admin/Pipeline:                                                             │
│    admin_jobs (operator-initiated jobs, status tracking)                    │
│    pipeline_runs (ingest, parse, resolve step records)                      │
│                                                                              │
│  Argument Status Enum (Phase 22):                                            │
│    PIPELINE (raw, pre-published)                                             │
│    DRAFT (operator has drafted but not yet published)                        │
│    PUBLISHED (publicly visible)                                              │
│    UNPUBLISHED (operator has unpublished)                                    │
│                                                                              │
└──────────────────────────┬──────────────────────────────────────────────────┘
                           │
        (Offline pipeline writes only — never HTTP-triggered)
                           │
                           ▼
      ┌────────────────────────────────────────────────────────┐
      │  Pipeline CLI (python -m pipeline <command>)           │
      │     pipeline/__main__.py                               │
      │                                                         │
      │  Subcommands:                                           │
      │  ingest   → Download PDF, create case/arg/job row     │
      │  parse    → Extract utterances via pdfplumber+        │
      │             state machine + LLM corrective            │
      │  resolve  → Map speaker labels → people IDs           │
      │             (interactive or batch via admin)          │
      │  seed-aliases → Pre-load Justice records              │
      │                                                         │
      │  Modules:                                              │
      │  commands/ → ingest, parse, resolve, seed_aliases     │
      │  parser/   → extractor, state_machine, llm_pass       │
      │  db.py     → Async session for pipeline               │
      │                                                         │
      │  Integrations:                                          │
      │  pdfplumber → extract text from PDF                    │
      │  instructor + Anthropic → LLM corrective pass          │
      │  tenacity → Retry logic for transient errors           │
      │  httpx → Download PDFs from supremecourt.gov           │
      └────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **Public Router** | HTTP request dispatch (cases, arguments, people), parameter validation | `api/routers/cases.py`, `api/routers/arguments.py`, `api/routers/people.py` |
| **Admin Router** | HTTP request dispatch (jobs, arguments, people admin), X-Admin-Token verification | `api/routers/admin.py` |
| **Service (public)** | Business logic for read-only queries, filtering to latest pipeline_run | `api/services/cases.py`, `api/services/arguments.py`, `api/services/people.py` |
| **Service (admin)** | Job creation/polling, argument status lifecycle, speaker resolution, merge preview | `api/services/admin_jobs.py`, `api/services/admin_arguments.py`, `api/services/admin_people.py` |
| **Service (pipeline)** | Subprocess spawning, job status updates to admin_jobs table | `api/services/pipeline_spawn.py` |
| **Schema** | Pydantic v2 response models, serialization from ORM rows | `api/schemas/` (*.py files) |
| **Model** | SQLAlchemy 2.0 ORM table definitions, enums, constraints, indexes | `api/models/models.py` |
| **Admin UI** | Job creation form, pipeline runner, job detail view, resolve UI | `app/src/routes/admin/pipeline/`, `app/src/routes/admin/arguments/`, `app/src/routes/admin/people/` |
| **Admin Components** | Reusable UI fragments for job cards, docket inputs, status displays | `app/src/lib/components/{ArgumentDetailsCard,RunStatusCard,ResolveCard,etc.}.svelte` |

## Pattern Overview

**Overall:** Multi-tier read-only HTTP API with offline Python CLI pipeline. Admin UI creates jobs; pipeline writes directly to DB; API queries latest data.

**Key Characteristics:**
- Strict separation: FastAPI reads only; pipeline writes only
- Job-driven pipeline: Admin creates AdminJob row; subprocess reads it and updates status
- Status immutable: ArgumentStatusLog records all transitions; Argument.status reflects current
- Schema authority: Alembic only; no Base.metadata.create_all()
- Async throughout: SQLAlchemy 2.0 AsyncSession, asyncpg, lifespan context manager

## Layers

**SvelteKit Frontend (SSR via adapter-node):**
- Purpose: Public read-only chat interface + admin operator UI
- Location: `app/src/routes/`
- Contains: Pages (route files), server load functions, form actions, components
- Depends on: FastAPI backend (via `$env/static/private` FASTAPI_BASE_URL)
- Used by: Browser (public users, admin operators)

**FastAPI API Server:**
- Purpose: HTTP gateway to PostgreSQL data; spawns pipeline subprocesses
- Location: `api/`
- Contains: Routes, services, schemas, models, database configuration
- Depends on: PostgreSQL, Anthropic API (for LLM corrective parsing)
- Used by: SvelteKit frontend, internal admin job polling

**Pipeline CLI:**
- Purpose: Offline ingestion, parsing, resolution of SCOTUS transcripts
- Location: `pipeline/`
- Contains: Subcommands, PDF extraction, state machine, LLM integration
- Depends on: PostgreSQL (direct writes), pdfplumber, Anthropic API
- Used by: Admin UI (via `api/services/pipeline_spawn.py`), operators (manual invocation)

**PostgreSQL Database:**
- Purpose: System of record for all cases, arguments, utterances, speaker metadata
- Location: N/A (remote managed DB or Docker container in dev)
- Contains: 13 tables across domain, admin, and pipeline concerns
- Depends on: Alembic migrations (DDL authority)
- Used by: FastAPI (read), Pipeline (write)

## Data Flow

### Primary Public Request Path (Read Chat)

1. Browser requests GET `/cases/[slug]/arguments/[id]` → SvelteKit `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts`
2. Server load function calls FastAPI `/arguments/{id}/utterances` via fetch (FASTAPI_BASE_URL)
3. FastAPI routes to `api/routers/arguments.py:get_argument_utterances()`
4. Router calls `api/services/arguments.py:get_argument_with_utterances(db, argument_id)`
5. Service queries `utterances` table filtered by latest `pipeline_run_id`, joins `people` for speaker names
6. Service returns dict; router wraps in Pydantic `UtterancesResponse` schema
7. SvelteKit receives JSON, renders `+page.svelte` (ChatBubble components, SectionRail, MobileNavBar)

### Admin Job Pipeline Request Path (Ingest)

1. Operator submits form on `/admin/pipeline` → SvelteKit form action posts to `+page.server.ts`
2. Form action calls POST `/api/admin/jobs` with pdf_url/dockets/question
3. FastAPI routes to `api/routers/admin.py:create_job()` (X-Admin-Token protected)
4. Router calls `api/services/admin_jobs.py:create_admin_job()` → inserts AdminJob row with status=pending
5. Service calls `api/services/pipeline_spawn.py:spawn_pipeline_step()` → subprocess `python -m pipeline ingest --job-id {job_id}`
6. Pipeline subprocess (running independently) calls `pipeline/commands/ingest.py:run_ingest(args)`
7. Ingest command updates AdminJob.status to running/completed/failed in PostgreSQL
8. Meanwhile, SvelteKit polls GET `/api/admin/jobs/{job_id}` every 1s; service detects status=completed
9. Admin service calls `spawn_pipeline_step()` again with --job-id for the parse step
10. Loop continues until all steps (ingest → parse → resolve) complete

### Argument Status Lifecycle (Phase 22)

1. Argument created during ingest → status=PIPELINE, ArgumentStatusLog written with row
2. Operator edits /admin/arguments/{id}, marks as Draft → PATCH triggers service
3. Service updates Argument.status=DRAFT, inserts ArgumentStatusLog row with DRAFT, returns OK
4. Operator clicks Publish → PUT triggers service, checks Argument.resolved_at IS NOT NULL (gate)
5. If gate passes: update Argument.status=PUBLISHED, insert ArgumentStatusLog row with PUBLISHED
6. If gate fails: return 422 error (pre-condition failed)
7. Operator can Unpublish → update Argument.status=UNPUBLISHED, insert ArgumentStatusLog row
8. GET /api/admin/arguments/{id} returns ArgumentDetail with status field + status_log array

**State Management:**
- Frontend: SvelteKit +page.server.ts uses load functions (server-cached data)
- Backend: Stateless FastAPI; state in PostgreSQL only
- Admin jobs: Polled via `/api/admin/jobs/{job_id}`; client-side `setInterval` invalidates SvelteKit load

## Key Abstractions

**AdminJob:**
- Purpose: Represents a single operator-initiated pipeline run (ingest + parse + resolve)
- Examples: `api/models/models.py:AdminJob`, `api/schemas/admin_jobs.py:AdminJobResponse`
- Pattern: Create → wait for status=running → poll every 1s → check if step changed → spawn next step

**Argument + ArgumentStatusLog:**
- Purpose: Argument represents a single oral hearing; ArgumentStatusLog is an audit trail
- Examples: `api/models/models.py:Argument`, `api/models/models.py:ArgumentStatusLog`
- Pattern: Insert log row every time status changes; latest log row = current status (or read Argument.status directly)

**Pipeline Run:**
- Purpose: Represents a single execution of ingest/parse/resolve (may be re-run multiple times)
- Examples: `api/models/models.py:PipelineRun`
- Pattern: Each run gets a unique pipeline_run_id; utterances link to it; old runs never deleted until promoted

**Speaker Alias:**
- Purpose: Maps raw transcript speaker labels (e.g., "Justice Sotomayor") to resolved Person records
- Examples: `api/models/models.py:SpeakerAlias`
- Pattern: Resolve step consults alias table; if not found, prompts operator interactively

## Entry Points

**API:**
- Location: `api/main.py`
- Triggers: Server startup (uvicorn)
- Responsibilities: FastAPI app creation, lifespan context manager (engine init), router inclusion

**Frontend:**
- Location: `app/src/routes/+layout.svelte` (root layout)
- Triggers: Browser navigation to any route
- Responsibilities: Root layout wrapper, session check via `hooks.server.ts`, nav UI

**Pipeline:**
- Location: `pipeline/__main__.py`
- Triggers: Subprocess invocation (admin UI or manual)
- Responsibilities: argparse subcommand dispatch (ingest, parse, resolve, seed-aliases)

## Architectural Constraints

- **Threading:** Event-driven async (FastAPI uvicorn workers, asyncpg connections); pipeline runs are separate processes
- **Global state:** Database engine + session factory initialized in FastAPI lifespan context manager; module-level globals in `api/core/database.py`
- **Circular imports:** None known; services layer avoids importing routes; routes import services cleanly
- **Immutable data:** Raw PDFs never modified after ingest; derived utterance rows can be regenerated (new pipeline_run_id)
- **DDL authority:** Alembic migrations only; no schema.create_all() anywhere in codebase
- **Admin token security:** X-Admin-Token header (Phase 5 legacy); session cookie (Phase 6+); never logged or echoed

## Anti-Patterns

### Pipeline Steps Exposed as HTTP Endpoints

**What happens:** Older iterations considered POST /parse, POST /resolve endpoints

**Why it's wrong:** Creates state confusion (API can't guarantee atomicity); breaks offline-first design; couples frontend to pipeline internals; makes testing harder

**Do this instead:** All pipeline steps are CLI commands only; admin UI creates job row, FastAPI spawns subprocess; subprocess updates job status directly to DB

### Base.metadata.create_all() for Schema Initialization

**What happens:** Some ORMs call this on startup to auto-create tables

**Why it's wrong:** CLAUDE.md forbids this; Alembic is sole DDL authority; auto-creation would skip migrations and break schema versioning

**Do this instead:** Always use `alembic upgrade head` to initialize/migrate schema; Alembic is the only way to change it

### Storing Full Speaker Label in Utterance Rows

**What happens:** Redundantly storing both raw_speaker_label and person_id

**Why it's wrong:** Wastes space; makes debugging harder; if person_id changes, utterance becomes inconsistent

**Do this instead:** Store raw_speaker_label for audit trail; join to SpeakerAlias at query time to resolve; person_id populated at resolve-step time

## Error Handling

**Strategy:** Graceful degradation for transient errors; structured logging for pipeline failures

**Patterns:**
- API returns HTTP 400/422 for validation errors; 404 for not found; 500 for server errors
- Pipeline uses tenacity for exponential backoff on LLM API calls
- Pipeline gracefully degrades: if LLM corrective pass fails, rule-based output is returned
- Admin job failures write bounded error message to AdminJob.error_message (500-char limit)

## Cross-Cutting Concerns

**Logging:**
- Frontend: console.log/error; SvelteKit dev mode shows request logs
- Backend: Uvicorn access logs; SQLAlchemy echo when DEBUG=true; pipeline stderr
- Admin jobs: error_message stored in DB and displayed in UI

**Validation:**
- Pydantic v2 for request/response schemas
- Pipeline parse state machine validates utterance structure before LLM pass
- Docket number normalization in multiple places (ingest, arguments service)

**Authentication:**
- SvelteKit: HMAC-SHA256 session cookie (verify via timingSafeEqual constant-time)
- FastAPI: X-Admin-Token header (legacy Phase 5); session cookie (Phase 6+)
- Never log or echo token values in any response

---

*Architecture analysis: 2026-07-08*
