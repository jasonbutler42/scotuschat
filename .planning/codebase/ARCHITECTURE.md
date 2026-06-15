# Architecture

**Analysis Date:** 2026-06-15

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SvelteKit Frontend (SSR)                           │
│                              app/src/routes/                                 │
│  ┌────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐ │
│  │  /cases (listing)  │  │ /cases/[slug] (picker)│  │ /cases/.../[id]      │ │
│  │ +page.server.ts    │  │ +page.server.ts      │  │ (argument detail)     │ │
│  │ +page.svelte       │  │ +page.svelte         │  │ +page.server.ts       │ │
│  └────────────────────┘  └──────────────────────┘  │ +page.svelte          │ │
│                                                      │ (chat view)           │ │
│                                                      └──────────────────────┘ │
│                                                                               │
│  Components (app/src/lib/components/):                                       │
│    ChatBubble.svelte → individual utterance                                 │
│    SectionRail.svelte → sticky section navigator (desktop)                  │
│    MobileNavBar.svelte → fixed-bottom pill nav (mobile)                     │
│    StageDirection.svelte → stage direction text                             │
│                                                                               │
└────────────────────────────────┬────────────────────────────────────────────┘
                                  │
                    fetch() via FASTAPI_BASE_URL
                      ($env/static/private)
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Read-only HTTP)                         │
│                             api/main.py                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────────────┐   │
│  │ /cases           │  │ /arguments/...   │  │ /people/{id}            │   │
│  │ (list endpoint)  │  │ /utterances      │  │ (speaker bio endpoint)  │   │
│  │ api/routers/     │  │ api/routers/     │  │ api/routers/people.py   │   │
│  │ cases.py         │  │ arguments.py      │  │                         │   │
│  └────────┬─────────┘  └────────┬─────────┘  └────────────┬────────────┘   │
│           │                     │                          │                 │
│           └─────────────────────┼──────────────────────────┘                 │
│                                 │                                             │
│                    api/services/ (business logic)                            │
│                  - cases.py, arguments.py, people.py                         │
│                  - Filter to latest pipeline_run (PIPE-11)                   │
│                  - Join person/role data for serialization                   │
│                                                                               │
└────────────────────────────────┬────────────────────────────────────────────┘
                                  │
                                  │ SQLAlchemy ORM async queries
                                  │ (api/core/database.py)
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│            PostgreSQL 16 Database (Read by API, Written by Pipeline)        │
│                         api/models/models.py                                 │
│                         11 tables (Alembic DDL)                              │
│                                                                               │
│  Core: roles → people → court_tenures                                       │
│  Cases: cases ↔ case_arguments ↔ arguments (M:M join)                       │
│  Speech: argument_participants, utterances (per pipeline_run_id)            │
│  Resolution: speaker_alias (raw label → person mapping)                     │
│  Audit: pipeline_runs (ingest, parse, resolve steps + status)               │
│                                                                               │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
              (Offline pipeline writes only)
                               │
                               ▼
         ┌──────────────────────────────────────────────┐
         │  Pipeline CLI (python -m pipeline)           │
         │     pipeline/__main__.py                      │
         │                                               │
         │  Subcommands:                                 │
         │  ingest   → Download PDF, create case/arg    │
         │  parse    → Extract utterances via pdfplumber│
         │  resolve  → Map speaker labels → people IDs  │
         │  seed-aliases → Pre-load Justice records     │
         │                                               │
         │  Pipeline modules:                            │
         │  commands/ → ingest, parse, resolve, seed    │
         │  parser/   → extractor, state_machine, llm   │
         │  db.py     → Async session, connection pool  │
         │                                               │
         │  Data sources:                                │
         │  pdfplumber → extract text from PDF          │
         │  instructor + Anthropic → LLM corrective     │
         │  tenacity → Retry logic for transient errors │
         │  httpx → Download PDFs from supremecourt.gov │
         └──────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **Router** | HTTP request dispatch, parameter validation, error translation | `api/routers/cases.py`, `api/routers/arguments.py`, `api/routers/people.py` |
| **Service** | Business logic, ORM queries, filtering to latest pipeline run, data transformation to dicts | `api/services/cases.py`, `api/services/arguments.py`, `api/services/people.py` |
| **Schema** | Pydantic v2 response models, serialization from ORM rows | `api/schemas/cases.py`, `api/schemas/utterance.py`, `api/schemas/people.py` |
| **Model** | SQLAlchemy ORM table definitions, enums, constraints, indexes | `api/models/models.py` |
| **Database** | Lifespan management, async session factory, connection pooling | `api/core/database.py` |
| **Config** | Environment variables, pydantic-settings validation | `api/core/config.py` |
| **SvelteKit Routes** | SSR page load functions, data binding to pages, client-side routing | `app/src/routes/*/+page.server.ts`, `app/src/routes/**/+page.svelte` |
| **Components** | Reusable UI fragments, no data fetching | `app/src/lib/components/*.svelte` |
| **Ingest** | PDF download validation, case/argument row creation, immutable file storage | `pipeline/commands/ingest.py` |
| **Parse** | PDF text extraction, rule-based state machine, LLM corrective pass, utterance row creation | `pipeline/commands/parse.py`, `pipeline/parser/extractor.py`, `pipeline/parser/state_machine.py`, `pipeline/parser/llm_pass.py` |
| **Resolve** | Speaker label → person_id mapping, interactive alias resolution | `pipeline/commands/resolve.py` |
| **Seed Aliases** | Pre-load Justice records and speaker_alias seed data | `pipeline/commands/seed_aliases.py` |

## Pattern Overview

**Overall:** Read-only pub/sub; upstream writer (offline pipeline) → downstream reader (HTTP API)

**Key Characteristics:**
- **Pipeline is offline only.** All transcript processing happens via CLI, not HTTP endpoints. The API never triggers pipeline steps (decision from PROJECT.md Key Decisions).
- **Read-only API.** FastAPI has no POST/PUT/DELETE endpoints. Data flows one direction: pipeline writes to DB, API reads from DB.
- **Latest-run filtering (PIPE-11).** When a parse step re-runs, new utterance rows are created under a new pipeline_run_id. The API always filters to MAX(pipeline_run_id) to show only the most recent completed run. Prior rows accumulate and are never deleted.
- **Immutable PDFs.** Source transcripts are downloaded once and stored at `data/[case_slug]/[argument_id].pdf`. Re-runs of ingest skip the download if the file exists.
- **Staged resolution.** At parse time, utterance.person_id is null. The Resolve step (Phase 2) populates it. The API returns both speaker_name (from person table) and raw_speaker_label so UI doesn't break if person_id is null.
- **Apolitical framing.** Every speaker (Justice or advocate) gets identical schema treatment. Side is determined by rule-based assignment (BENCH_RE / ADVOCATE_RE patterns) during parse, not editorial categorization.

## Layers

**Frontend (SvelteKit 2.x + Svelte 5 Runes):**
- Purpose: Render oral arguments as a chat-style interface; handle client-side routing and navigation
- Location: `app/src/`
- Contains: Pages (+page.server.ts, +page.svelte), components (ChatBubble, SectionRail, MobileNavBar), layout
- Depends on: FastAPI (via fetch in +page.server.ts load functions)
- Used by: End users via web browser (read-only browsing)

**API (FastAPI 0.115+):**
- Purpose: Provide HTTP read-only endpoints for cases, arguments, utterances, and people
- Location: `api/`
- Contains: Routers (HTTP handlers), services (business logic), schemas (response models), models (ORM), core (database, config)
- Depends on: PostgreSQL 16 (via asyncpg + SQLAlchemy 2.0 async)
- Used by: SvelteKit +page.server.ts load functions; can be used by other HTTP clients

**Pipeline (Python 3.12 CLI):**
- Purpose: Ingest transcripts, parse them into utterances, resolve speaker identities, and enrich with external data
- Location: `pipeline/`
- Contains: Commands (ingest, parse, resolve, seed-aliases), parser modules (extractor, state_machine, llm_pass), tests
- Depends on: PostgreSQL 16 (direct connection via sqlalchemy + asyncpg), pdfplumber, Anthropic SDK, instructor, tenacity
- Used by: Operator only (offline CLI, never public-facing)

**Database (PostgreSQL 16):**
- Purpose: Persistent storage for cases, arguments, utterances, people, and pipeline audit trail
- Location: Schema managed by `alembic/` migrations
- Contains: 11 tables (roles, people, court_tenures, cases, arguments, case_arguments, case_appearances, argument_participants, pipeline_runs, utterances, speaker_alias)
- Accessed by: API (read-only), Pipeline (read/write)

## Data Flow

### Primary Request Path (GET /arguments/{id}/utterances)

1. **User opens argument page** → SvelteKit routes to `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts`
2. **Server-side load function fetches utterances** → `+page.server.ts` calls `fetch(FASTAPI_BASE_URL/arguments/{id}/utterances)` (line 6)
3. **FastAPI router handles request** → `api/routers/arguments.py` @router.get("/{argument_id}/utterances") (line 21-38)
4. **Router calls service layer** → `api/services/arguments.py` get_argument_with_utterances() (line 23-124)
5. **Service queries latest pipeline run** → SELECT MAX(pipeline_run_id) WHERE step='parse' AND status='COMPLETED' (line 84-91, PIPE-11 policy)
6. **Service fetches utterances + speaker data** → JOIN utterances → people → roles, filter by max_run_id, order by sequence (line 99-120)
7. **Service builds dict response** → Return {"argument": {...}, "utterances": [...]} (line 118)
8. **Router serializes to Pydantic model** → `api/schemas/utterance.py` ArgumentUtterancesResponse (line 51-60)
9. **SvelteKit receives JSON** → `+page.server.ts` returns data (line 9-13)
10. **Component renders chat bubbles** → `+page.svelte` maps utterances → ChatBubble.svelte (line 1-68)
11. **SectionRail updates on scroll** → IntersectionObserver triggers activeSection update (line 9-30 in SectionRail.svelte)

### Secondary Flow: Cases List (GET /cases)

1. **User opens /cases page** → `app/src/routes/cases/+page.server.ts` calls `fetch(FASTAPI_BASE_URL/cases)` (line 6)
2. **FastAPI router dispatches** → `api/routers/cases.py` @router.get("", response_model=CasesResponse) (line 20)
3. **Service queries all cases** → `api/services/cases.py` get_cases() → SELECT cases JOIN case_arguments (WHERE is_lead=TRUE) JOIN arguments ORDER BY argued_date DESC (line 20-49)
4. **Response includes argument_id** → Each case card can link directly to `/cases/{slug}` (line 95 in +page.svelte)
5. **Multi-argument handler** → If case.question_number !== 1, /cases/{slug} page redirects to single-argument or shows picker (D-09 design decision)

### Pipeline Ingest → Parse → Resolve Flow

1. **Operator runs ingest command** → `python -m pipeline ingest --url ... --case-name ... --argued-date ...` (pipeline/__main__.py line 45-89)
2. **Ingest validates URL** → _validate_url() checks https:// + supremecourt.gov (pipeline/commands/ingest.py line 35-55)
3. **Ingest downloads PDF** → httpx.get() saves to `data/{slug}/{argument_id}.pdf` (immutable, never overwritten)
4. **Ingest creates DB rows** → Case, Argument, CaseArgument (M:M), PipelineRun (status=COMPLETED, step=ingest) (pipeline/commands/ingest.py line 72-)
5. **Operator runs parse** → `python -m pipeline parse --run-id {ingest_run_id}` (pipeline/__main__.py line 93-111)
6. **Parse loads PipelineRun** → Gets pdf_path from source ingest row (pipeline/commands/parse.py line 75)
7. **Parse extracts pages** → pdfplumber.open(pdf_path) → extract_pages() strips headers, page numbers, line numbers (pipeline/parser/extractor.py line 62-89)
8. **Parse runs state machine** → Rule-based parser splits text on speaker labels (BENCH_RE, ADVOCATE_RE patterns) → list of ParsedUtterance objects (pipeline/parser/state_machine.py)
9. **Parse runs LLM corrective** → Optional Claude pass via instructor to fix edge cases; falls back to rule-based output on failure (pipeline/parser/llm_pass.py)
10. **Parse creates utterance rows** → One row per utterance, linked to new PipelineRun.id, side/section_hint/raw_speaker_label set, person_id=NULL (pipeline/commands/parse.py line 80-120)
11. **Operator runs resolve** → `python -m pipeline resolve --run-id {parse_run_id}` (pipeline/__main__.py line 115-129)
12. **Resolve looks up speaker_alias** → For each raw_speaker_label, query speaker_alias table for matching person_id (pipeline/commands/resolve.py)
13. **Resolve prompts operator** → If alias not found, ask operator to select from people table (interactive CLI)
14. **Resolve updates utterances** → UPDATE utterances SET person_id={selected} WHERE raw_speaker_label={label} AND pipeline_run_id={run_id}

**State Management:**
- **Pipeline state:** PipelineRun.status tracks step progress (pending → running → completed/failed). No global state; each run is independent.
- **API session state:** Lifespan context manager (api/core/database.py line 28-49) creates one async engine per app startup. AsyncSessionLocal is module-global but lazily initialized inside lifespan.
- **Frontend reactive state:** SvelteKit data prop, Svelte 5 Runes ($props, $derived, $state). No stores; page load via +page.server.ts only. MobileNavBar uses $state for activeSection. SectionRail derives activeSection via IntersectionObserver.

## Key Abstractions

**Utterance:**
- Purpose: Represents one turn of speech or a stage direction (e.g., "(Laughter.)")
- Examples: `api/models/models.py` Utterance class (line 222-246), `api/schemas/utterance.py` UtteranceResponse (line 22-38)
- Pattern: ORM table → Pydantic response; person_id initially null, populated by Resolve step. side (BENCH/ADVOCATE/UNKNOWN) assigned at parse time via rule-based matching.

**Case:**
- Purpose: Represents one docket number (one row per docket). Multiple dockets may be consolidated (e.g., Obergefell 14-556/562/571/574).
- Examples: `api/models/models.py` Case class (line 107-116)
- Pattern: slug is derived from case_name (lowercase, hyphens), used as URL parameter. Lead docket marked via CaseArgument.is_lead=TRUE.

**Argument:**
- Purpose: Represents one hearing session (one row per hearing date, indexed by question_number for multi-argument cases)
- Examples: `api/models/models.py` Argument class (line 124-131)
- Pattern: Many cases link to one argument via case_arguments M:M join. Utterances and PipelineRuns belong to arguments, not cases.

**Person + Role:**
- Purpose: Every speaker (Justice, advocate, amicus) is a Person with an optional Role (e.g., "Associate Justice", "Petitioner's Counsel")
- Examples: `api/models/models.py` Person (line 75-81), Role (line 62-66), CourtTenure (line 89-96)
- Pattern: Court tenures track seat + dates to handle Justice transitions. Identical schema for all speaker types (apolitical framing).

**PipelineRun:**
- Purpose: Audit trail for each pipeline step invocation. Captures step name (ingest/parse/resolve), status, timestamps, PDF path, failure reasons.
- Examples: `api/models/models.py` PipelineRun (line 193-210)
- Pattern: Re-running a step creates a new row. Prior rows never deleted until new run is promoted. Utterances linked to pipeline_run_id for reproducibility.

**SpeakerAlias:**
- Purpose: Maps normalized speaker labels (from transcripts) to resolved person_id. Seeded with Justice names; populated by Resolve step for advocates.
- Examples: `api/models/models.py` SpeakerAlias (line 256-263)
- Pattern: Lookup table for deterministic speaker resolution. Supports multiple labels mapping to same person (e.g., "Chief Justice Roberts" → person_id=1, "Roberts" → person_id=1).

## Entry Points

**API Server:**
- Location: `api/main.py` (line 1-33)
- Triggers: `uvicorn api.main:app --reload --port 8000` (command line, not programmatic)
- Responsibilities: Define FastAPI app, attach lifespan handler, include routers for cases/arguments/people

**SvelteKit Frontend:**
- Location: `app/src/routes/+layout.svelte` (line 1-35), then route-specific pages
- Triggers: Browser HTTP requests (SPA-style routing)
- Responsibilities: Render layout, handle SSR via +page.server.ts load functions, compose components

**Pipeline CLI:**
- Location: `pipeline/__main__.py` (line 36-159)
- Triggers: `python -m pipeline <command> [args]` (operator invocation)
- Responsibilities: Parse subcommand arguments, dispatch to command functions (run_ingest, run_parse, run_resolve, run_seed_aliases)

## Architectural Constraints

- **Threading:** Single-threaded event loop (asyncio). FastAPI handles requests concurrently via async/await. Pipeline commands are synchronous-blocking at the CLI level but use async internally for DB operations (asyncio.run()).
- **Global state:** 
  - `api/core/database.py`: Module-level `engine` and `AsyncSessionLocal` initialized inside lifespan context manager (line 28-49). Accessed by `get_db()` dependency.
  - `api/core/config.py`: Module-level `settings` object created at import time (line 28), read-only after that.
  - No singletons or circular imports in production code (tests excluded).
- **Circular imports:** None detected. Import order: config → database → models → routers/services → main. Pipeline imports are separate.
- **PgBouncer compatibility:** asyncpg requires `statement_cache_size=0` in connect_args (not top-level), mandatory for Digital Ocean App Platform Transaction mode (api/core/database.py line 38).
- **Database transactions:** Async sessions use `expire_on_commit=False` to prevent MissingGreenlet errors when accessing ORM attributes after commit (api/core/database.py line 46).
- **Re-running safety:** Pipeline steps are idempotent by design. Parse re-runs create new utterance rows under new pipeline_run_id; prior rows are never deleted. API filters to MAX(pipeline_run_id) to surface latest only (PIPE-11 policy).
- **Apolitical schema:** Every speaker uses identical models, schemas, and response formats. Side is assigned via rule-based matching, not editorial input. No derived statistics, summaries, or sentiment analysis.

## Anti-Patterns

### Exposing Pipeline as HTTP Endpoints

**What happens:** A developer adds POST /pipeline/parse endpoint to trigger parse from the web UI.

**Why it's wrong:** Violates architecture decision (PROJECT.md Key Decisions). Pipeline is offline-only by design to keep the app server simple and audit-trail explicit.

**Do this instead:** Operator runs CLI commands on a scheduled task or manual invocation. If async triggering is needed, use a job queue (future consideration, not in v1).

### Storing Passwords or Secrets in Models

**What happens:** A Person.password or Argument.api_key column is added to store credentials.

**Why it's wrong:** Violates PCI/security constraints. Credentials belong in .env or Key Vault, never in database rows.

**Do this instead:** Use environment variables (api/core/config.py pattern) or secrets management system (future).

### Deleting Old Pipeline Runs

**What happens:** After a new parse run completes, prior utterance rows are deleted to "clean up".

**Why it's wrong:** Loses audit trail. Re-running parse produces new rows, but users may want to compare results or revert to prior run.

**Do this instead:** Keep all rows indefinitely. Promote new runs explicitly (future feature). Query always filters to latest (PIPE-11).

### Mutating Raw PDFs

**What happens:** After ingest, the PDF in data/ is edited, updated, or overwritten.

**Why it's wrong:** Source transcripts are historical documents. Derived data (utterances) can be regenerated from source, but if source is corrupted, lineage is lost.

**Do this instead:** PDFs are immutable. Never modify after ingest. If correction needed, re-download and ingest as new run.

### Using Server-Only Env Vars in PUBLIC_ Prefix

**What happens:** FASTAPI_BASE_URL is named PUBLIC_FASTAPI_BASE_URL and exposed to client code.

**Why it's wrong:** If the API is internal-only (future consideration), the URL leaks architecture details and enables SSRF if not validated.

**Do this instead:** Use $env/static/private in +page.server.ts only. Never prefix with PUBLIC_ (api/routers/arguments.py line 1, +page.server.ts line 1).

## Error Handling

**Strategy:** Fail fast with explicit errors. No silent fallbacks except LLM corrective pass (which gracefully degrades to rule-based output).

**Patterns:**
- **API errors:** HTTPException(status_code, detail) raised from routers; FastAPI serializes to JSON (api/routers/arguments.py line 37)
- **URL validation:** _validate_url() raises ValueError before any network call; caught by caller and logged (pipeline/commands/ingest.py line 35-55)
- **LLM failures:** Parse step catches Instructor/API exceptions, logs failure_reason, sets PipelineRun.status=failed; does NOT retry at parse layer (tenacity is outer wrapper in CLI) (pipeline/commands/parse.py line 20-21)
- **Database constraints:** Unique constraints (e.g., docket_number, slug, normalized_label in speaker_alias) enforced at schema level; caller must handle IntegrityError if data duplicates occur

## Cross-Cutting Concerns

**Logging:** 
- API: FastAPI built-in logging (DEBUG mode enables SQLAlchemy SQL echo)
- Pipeline: Print statements to stdout; structured logging not implemented in v1
- Frontend: Browser console (no structured logging in v1)

**Validation:**
- API: Pydantic v2 on request/response models (api/schemas/*.py)
- Pipeline: argparse for CLI arguments; SQL constraints for data integrity (e.g., foreign keys, unique constraints in api/models/models.py)
- Frontend: SvelteKit type checking via TypeScript; no client-side validation form builder in v1 (pages are read-only)

**Authentication:**
- API: No auth in v1 (read-only public endpoint assumption)
- Pipeline: No auth (operator CLI, runs on trusted machine)
- Frontend: No auth required (public browsing)

---

*Architecture analysis: 2026-06-15*
