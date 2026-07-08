# Codebase Structure

**Analysis Date:** 2026-07-08

## Directory Layout

```
project-root/
├── .claude/                    # Claude agent configuration (skills, agents)
├── .planning/                  # GSD planning docs, phase logs, research
│   ├── PROJECT.md              # Project charter, constraints, decisions
│   ├── STATE.md                # Current milestone/phase progress
│   ├── ROADMAP.md              # Phase breakdown and task assignments
│   ├── REQUIREMENTS.md         # Feature requirements tracking
│   ├── codebase/               # Codebase analysis documents (ARCHITECTURE.md, STRUCTURE.md, etc.)
│   ├── phases/                 # Phase-specific planning and discussion logs
│   └── spikes/                 # Spike research findings
├── alembic/                    # Database migrations (Alembic DDL)
│   ├── env.py                  # Alembic async configuration
│   ├── script.py.mako          # Migration template
│   ├── alembic.ini             # Alembic config (in root)
│   └── versions/               # Migration files (0001 through 0013+)
├── api/                        # FastAPI backend (read-only HTTP)
│   ├── __init__.py
│   ├── main.py                 # FastAPI app definition, lifespan, router inclusion
│   ├── core/                   # Core infrastructure
│   │   ├── __init__.py
│   │   ├── config.py           # Environment variables via pydantic-settings
│   │   └── database.py         # Async engine, session factory, lifespan context
│   ├── models/                 # SQLAlchemy ORM table definitions
│   │   ├── __init__.py
│   │   └── models.py           # 13 tables (roles, people, court_tenures, cases, arguments, argument_participants, utterances, speaker_alias, argument_status_log, admin_jobs, pipeline_runs, case_arguments, case_appearances)
│   ├── routers/                # FastAPI route handlers
│   │   ├── __init__.py
│   │   ├── cases.py            # GET /cases (list all)
│   │   ├── arguments.py         # GET /arguments/{id}/utterances (detail + chat)
│   │   ├── people.py           # GET /people/{id} (speaker bio)
│   │   └── admin.py            # Admin endpoints (/api/admin/jobs, /api/admin/arguments, /api/admin/people)
│   ├── services/               # Business logic layer
│   │   ├── __init__.py
│   │   ├── cases.py            # get_cases() → list dicts
│   │   ├── arguments.py         # get_argument_with_utterances() → detail + utterances
│   │   ├── people.py           # get_person() → speaker bio
│   │   ├── admin_jobs.py       # create_admin_job(), get_job_status(), advance_job_step() (P15+)
│   │   ├── admin_arguments.py  # list_arguments(), get_argument_detail(), update_argument() (P22+)
│   │   ├── admin_people.py     # list_people(), get_person_detail(), merge_preview() (P15+)
│   │   ├── speakers.py         # Speaker resolution logic (resolve step, merge search)
│   │   ├── pipeline_spawn.py   # spawn_pipeline_step() — subprocess invocation
│   │   └── spaces.py           # Digital Ocean Spaces upload/download helpers
│   ├── schemas/                # Pydantic v2 response models
│   │   ├── __init__.py
│   │   ├── cases.py            # CasesResponse, CaseItem
│   │   ├── utterance.py         # UtteranceResponse, UtterancesResponse
│   │   ├── people.py           # PersonResponse
│   │   ├── speakers.py         # SpeakerResponse (P15+)
│   │   ├── admin_jobs.py       # AdminJobResponse, FailedStepRecovery (P15+)
│   │   ├── admin_arguments.py  # ArgumentDetail, ArgumentListItem, ArgumentUpdate (P22+)
│   │   └── admin_people.py     # PersonDetail, MergePreview, RoleResponse (P15+)
│   └── tests/                  # API unit tests
│       ├── __init__.py
│       ├── conftest.py         # Pytest fixtures (async engine, test DB session)
│       ├── test_arguments.py
│       ├── test_people.py
│       ├── test_admin_jobs_*.py (multiple job-related tests)
│       ├── test_admin_people_*.py (multiple people-related tests)
│       └── test_admin_arguments_*.py (multiple arguments-related tests)
├── app/                        # SvelteKit 2.x frontend (SSR via adapter-node)
│   ├── src/
│   │   ├── app.d.ts            # TypeScript ambient types
│   │   ├── app.css             # Global Tailwind CSS (imported in +layout.svelte)
│   │   ├── hooks.server.ts     # SvelteKit server hooks (session verification on every request)
│   │   ├── lib/
│   │   │   ├── server/
│   │   │   │   └── session.ts  # Session crypto functions (signSession, verifySession)
│   │   │   └── components/     # Reusable Svelte 5 Runes components
│   │   │       ├── ChatBubble.svelte       # Individual utterance bubble
│   │   │       ├── SectionRail.svelte      # Sticky section navigator (desktop)
│   │   │       ├── MobileNavBar.svelte     # Fixed-bottom pill nav (mobile)
│   │   │       ├── StageDirection.svelte   # Stage direction text
│   │   │       ├── ArgumentDetailsCard.svelte  # Shared docket/date/question card (P22)
│   │   │       ├── RunStatusCard.svelte    # Job progress + status badge (P23)
│   │   │       ├── ResolveCard.svelte      # Speaker resolution UI (P23)
│   │   │       ├── CreatePersonPopover.svelte  # Inline person creation (P24)
│   │   │       ├── FailedStepGuidance.svelte   # Error recovery UI (P24)
│   │   │       ├── DocketPillInput.svelte  # Multi-docket input with validation
│   │   │       ├── TopNav.svelte           # Header navigation
│   │   │       ├── AdminSubNav.svelte      # Admin section navigation
│   │   │       ├── SpeakerPopover.svelte   # Speaker detail popover
│   │   │       └── *Popover.svelte (others)
│   │   └── routes/             # SvelteKit route pages (file-based routing)
│   │       ├── +layout.svelte  # Root layout (header, site nav, {@render children()})
│   │       ├── +page.svelte    # Index page (redirects to /cases)
│   │       │
│   │       ├── cases/          # /cases route group (public routes)
│   │       │   ├── +page.server.ts    # Server load: fetch /cases from FastAPI
│   │       │   ├── +page.svelte       # Case list page (CaseBrowser component)
│   │       │   └── [slug]/            # /cases/{slug} route group
│   │       │       ├── +page.server.ts      # Server load: fetch case detail
│   │       │       ├── +page.svelte         # Case detail (multi-arg picker or redirect)
│   │       │       └── arguments/
│   │       │           └── [id]/
│   │       │               ├── +page.server.ts  # Server load: fetch /arguments/{id}/utterances
│   │       │               └── +page.svelte     # Argument detail (chat view, SectionRail, MobileNavBar)
│   │       │
│   │       └── admin/          # /admin route group (protected routes)
│   │           ├── +page.server.ts    # Admin hub (logout action)
│   │           ├── +page.svelte       # Admin hub landing page
│   │           ├── +layout.svelte     # Admin layout (header, subnav)
│   │           │
│   │           ├── login/
│   │           │   ├── +page.server.ts   # Login form action (verify ADMIN_USERNAME/PASSWORD)
│   │           │   └── +page.svelte      # Login page
│   │           │
│   │           ├── pipeline/           # /admin/pipeline (job runner)
│   │           │   ├── +page.server.ts    # Load: fetch /api/admin/jobs; action: POST job
│   │           │   ├── +page.svelte       # Pipeline runner (URL vs upload mode, job list, toggle)
│   │           │   ├── +server.ts         # Form action endpoints (check-duplicate, create job)
│   │           │   ├── check-duplicate/
│   │           │   │   └── +server.ts     # Preflight check for duplicate docket+question
│   │           │   └── [job_id]/
│   │           │       ├── +page.server.ts   # Load: poll /api/admin/jobs/{job_id}
│   │           │       ├── +page.svelte      # Job detail (RunStatusCard, ResolveCard)
│   │           │       ├── +server.ts        # Resolve form action (POST /api/admin/jobs/{id}/resolve)
│   │           │       └── pdf/
│   │           │           └── +server.ts    # Serve PDF from data/ or DO Spaces
│   │           │
│   │           ├── arguments/          # /admin/arguments (argument editor)
│   │           │   ├── +page.server.ts    # Load: fetch /api/admin/arguments
│   │           │   ├── +page.svelte       # Argument list (status badges, search)
│   │           │   └── [id]/
│   │           │       ├── +page.server.ts   # Load: fetch /api/admin/arguments/{id}
│   │           │       ├── +page.svelte      # Argument editor (ArgumentDetailsCard, status log)
│   │           │       └── +server.ts        # Form actions (update metadata, publish/unpublish)
│   │           │
│   │           └── people/             # /admin/people (speaker admin)
│   │               ├── +page.server.ts    # Load: fetch /api/admin/people
│   │               ├── +page.svelte       # People list (search, role)
│   │               └── [id]/
│   │                   ├── +page.server.ts   # Load: fetch /api/admin/people/{id}
│   │                   ├── +page.svelte      # Person editor (bio, role, merge preview)
│   │                   ├── +server.ts        # Form actions (update, delete, merge)
│   │                   └── merge-preview/
│   │                       └── +server.ts    # Fetch merge preview (API call)
│   │
│   ├── svelte.config.js        # SvelteKit config (adapter: adapter-node for SSR)
│   ├── vite.config.ts          # Vite bundler config
│   ├── package.json            # Dependencies (SvelteKit, Svelte 5, Tailwind, TypeScript)
│   ├── package-lock.json       # Lockfile (npm deterministic builds)
│   ├── tsconfig.json           # TypeScript config
│   ├── tailwind.config.js      # Tailwind CSS config
│   ├── postcss.config.js       # PostCSS config (Tailwind + autoprefixer)
│   └── .svelte-kit/            # Generated SvelteKit internal files (gitignored)
│
├── data/                       # Immutable ingested PDF files
│   ├── uploads/                # Profile photos (persistent in dev; cleared in prod)
│   └── [case-slug]/
│       └── [argument_id].pdf   # Downloaded from supremecourt.gov (never modified)
│
├── pipeline/                   # Python 3.12 offline CLI (ingest, parse, resolve)
│   ├── __init__.py
│   ├── __main__.py             # CLI entry point (argparse subcommands, early-failure guard)
│   ├── db.py                   # Async session and connection pooling (get_session context manager)
│   ├── commands/               # Subcommand implementations
│   │   ├── __init__.py
│   │   ├── ingest.py           # Download PDF, create case/argument/pipeline_run, update admin_jobs
│   │   ├── parse.py            # Extract utterances via pdfplumber + state machine + LLM
│   │   ├── resolve.py          # Map speaker labels to person_id (interactive or batch)
│   │   └── seed_aliases.py     # Pre-load Justice records and speaker_alias
│   ├── parser/                 # PDF parsing modules
│   │   ├── __init__.py
│   │   ├── extractor.py        # pdfplumber text extraction, line number/header stripping
│   │   ├── state_machine.py    # Rule-based speaker/section detection
│   │   ├── cover_extractor.py  # Cover page metadata extraction (P22)
│   │   └── llm_pass.py         # Claude corrective pass via instructor
│   └── tests/                  # Pipeline unit tests
│       ├── __init__.py
│       ├── conftest.py         # Fixtures (temp PDFs, test DB)
│       ├── test_ingest.py
│       ├── test_parse.py
│       ├── test_cover_extractor.py  # Cover extraction tests (P22)
│       ├── test_pipeline_run.py
│       ├── test_resolve.py
│       ├── test_seed_aliases.py
│       └── test_ingest_startup_guard.py (early-failure guard tests)
│
├── tests/                      # Integration tests (root-level, run both API + pipeline)
│   └── __init__.py
│
├── scripts/                    # Utility scripts (not part of core pipeline)
├── memory/                     # User memory (auto-persisted across conversations)
│   └── MEMORY.md               # Known bugs, design decisions, v1.0 completion, v1.2 milestone
│
├── .env.example                # Environment variables template (copy to .env)
├── .gitignore                  # Git exclusions (node_modules, .venv, __pycache__, .env, data/uploads)
├── CLAUDE.md                   # Project instructions (tech stack, GSD workflow, architecture rules)
├── README.md                   # Project overview for GitHub
├── requirements.txt            # Python dependencies (FastAPI, SQLAlchemy, pdfplumber, etc.)
├── requirements-dev.txt        # Dev dependencies (pytest, pytest-asyncio, etc.)
├── pytest.ini                  # pytest configuration
└── alembic.ini                 # Alembic migration configuration (in root)
```

## Directory Purposes

**`.planning/`:**
- Purpose: GSD workflow artifacts (phases, plans, discussion logs, research spikes, codebase analysis documents)
- Contains: PROJECT.md, STATE.md, ROADMAP.md, REQUIREMENTS.md; phase-specific folders; `codebase/` folder with ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md, STACK.md, INTEGRATIONS.md
- Key files: `.planning/codebase/` is where codebase analysis documents are written

**`api/`:**
- Purpose: FastAPI read-only HTTP server with admin endpoints
- Contains: HTTP request handlers, business logic services, Pydantic response schemas, SQLAlchemy ORM models, async database configuration
- Key files: `api/main.py` (app entry point), `api/models/models.py` (all 13 table definitions), `api/core/database.py` (async setup)

**`app/`:**
- Purpose: SvelteKit 2.x frontend (SSR, Node.js deployment)
- Contains: Pages (routes), components, TypeScript types, Tailwind CSS, server hooks
- Key files: `app/src/routes/` (all pages and route groups), `app/src/lib/components/` (reusable Svelte 5 components), `svelte.config.js` (SSR adapter: adapter-node)

**`pipeline/`:**
- Purpose: Offline Python CLI for ingest, parse, resolve, seed-aliases
- Contains: Subcommands, PDF extraction, state machine, LLM integration, database operations
- Key files: `pipeline/__main__.py` (CLI dispatcher), `pipeline/commands/` (ingest, parse, resolve, seed_aliases), `pipeline/parser/` (extractor, state_machine, cover_extractor, llm_pass)

**`data/`:**
- Purpose: Immutable ingested PDF files + uploads directory
- Contains: Subdirectories per case slug, one PDF per argument file; profile photos in `data/uploads/`
- Key constraint: Never modified after creation; ingest skips download if file exists (idempotency)

**`alembic/`:**
- Purpose: Database schema management via migrations
- Contains: Migration files (0001_initial_schema.py through 0013_add_argument_status_log.py), env.py (async setup), alembic.ini (config)
- Key files: `alembic/versions/` (migration history), `alembic/env.py` (async config)

**`tests/` (root level):**
- Purpose: Integration tests spanning API + pipeline
- Contains: Test files that need both api and pipeline modules
- Separate from: `api/tests/` (unit tests for API only), `pipeline/tests/` (unit tests for pipeline only)

## Key File Locations

**Entry Points:**
- API: `api/main.py` (FastAPI app instance, invoked as `uvicorn api.main:app --reload --port 8000`)
- Frontend: `app/src/routes/+layout.svelte` (root layout), then route-specific +page.svelte files
- Pipeline: `pipeline/__main__.py` (CLI dispatcher, invoked as `python -m pipeline <command>`)

**Configuration:**
- API settings: `api/core/config.py` (pydantic-settings from .env)
- Database: `api/core/database.py` (async engine, session factory, lifespan)
- Database schema: `alembic/` (migrations), `api/models/models.py` (ORM definitions)
- SvelteKit: `app/svelte.config.js`, `app/vite.config.ts`, `app/tsconfig.json`
- Tailwind: `app/tailwind.config.js`, `app/postcss.config.js`
- Environment: `.env` (not committed), `.env.example` (template)

**Core Logic:**
- API routers: `api/routers/` (cases.py, arguments.py, people.py, admin.py)
- API services: `api/services/` (cases.py, arguments.py, people.py, admin_jobs.py, admin_arguments.py, admin_people.py, speakers.py, pipeline_spawn.py, spaces.py)
- API schemas: `api/schemas/` (Pydantic response models)
- API models: `api/models/models.py` (13 SQLAlchemy ORM tables)
- Pipeline ingest: `pipeline/commands/ingest.py`
- Pipeline parse: `pipeline/commands/parse.py`, `pipeline/parser/` (extractor, state_machine, cover_extractor, llm_pass)
- Pipeline resolve: `pipeline/commands/resolve.py`

**Admin UI:**
- Pipeline runner: `app/src/routes/admin/pipeline/` (+page.server.ts, +page.svelte, +server.ts, [job_id]/, check-duplicate/, pdf/)
- Arguments editor: `app/src/routes/admin/arguments/` (+page.server.ts, +page.svelte, [id]/)
- People admin: `app/src/routes/admin/people/` (+page.server.ts, +page.svelte, [id]/)
- Admin components: `app/src/lib/components/` (ArgumentDetailsCard, RunStatusCard, ResolveCard, CreatePersonPopover, FailedStepGuidance, etc.)

**Testing:**
- API unit tests: `api/tests/` (test_arguments.py, test_people.py, test_admin_jobs_*.py, test_admin_people_*.py, test_admin_arguments_*.py)
- Pipeline unit tests: `pipeline/tests/` (test_ingest.py, test_parse.py, test_cover_extractor.py, test_resolve.py, test_seed_aliases.py, etc.)
- Integration tests: `tests/` (root level, if needed)
- Fixtures: `pipeline/tests/conftest.py`, `api/tests/conftest.py`
- Config: `pytest.ini` (root level)

## Naming Conventions

**Files:**
- Python files: `snake_case.py` (e.g., `get_cases.py`, `ingest.py`, `admin_jobs.py`)
- Svelte components: `PascalCase.svelte` (e.g., `ChatBubble.svelte`, `ArgumentDetailsCard.svelte`)
- TypeScript files: `snake_case.ts` or `PascalCase.ts` depending on export (e.g., `+page.server.ts`, `+server.ts`, `app.d.ts`)
- Config files: lowercase with dots (e.g., `svelte.config.js`, `vite.config.ts`, `tsconfig.json`)
- Migration files: `NNNN_description.py` (e.g., `0001_initial_schema.py`, `0013_add_argument_status_log.py`)

**Directories:**
- Python packages: `snake_case/` (e.g., `api/`, `pipeline/`, `models/`, `routers/`)
- SvelteKit routes: `[brackets]` for dynamic segments (e.g., `[slug]`, `[id]`, `[job_id]`)
- Component directories: `components/` (lowercase, plural)
- Utilities: `lib/` (SvelteKit convention for shared code)

**Python Classes:**
- ORM models: `PascalCase` (e.g., `Case`, `Argument`, `Utterance`, `ArgumentStatusLog`)
- Enums: `PascalCase` (e.g., `SideEnum`, `PipelineRunStatus`, `ArgumentStatusEnum`, `AdminJobStatus`)
- Pydantic models: `PascalCase` (e.g., `UtteranceResponse`, `AdminJobResponse`, `ArgumentDetail`)
- Services: `snake_case` functions in `snake_case.py` files (e.g., `get_cases()`, `create_admin_job()`)

**Database:**
- Tables: `snake_case` (e.g., `cases`, `arguments`, `utterances`, `argument_status_log`, `admin_jobs`)
- Columns: `snake_case` (e.g., `docket_number`, `argued_date`, `is_stage_direction`, `created_at`)
- Enum types (PG native): `snake_case` with lowercase values (e.g., `argument_status` with "pipeline", "draft", "published", "unpublished")
- Enums (SideEnum): `UPPERCASE` values (BENCH, ADVOCATE, UNKNOWN, PETITIONER, RESPONDENT, AMICUS)

## Where to Add New Code

**New Feature (e.g., "Add citations table"):**
- Schema: `alembic/versions/NNNN_add_citations.py` (new migration file)
- ORM: Add class to `api/models/models.py`
- Service: Create `api/services/citations.py` with query functions
- Router: Create `api/routers/citations.py` with @router endpoints (or extend admin.py if admin-only)
- Schema: Create `api/schemas/citations.py` with Pydantic models
- Frontend: Create `app/src/routes/citations/` with +page.server.ts, +page.svelte (or add to admin routes if admin-only)
- Tests: Add `api/tests/test_citations.py` and/or `pipeline/tests/` if pipeline step involved

**New Admin UI Component:**
- Implementation: `app/src/lib/components/NewComponentName.svelte` (Svelte 5 Runes pattern)
- Usage: Import in the page that needs it (e.g., `app/src/routes/admin/pipeline/[job_id]/+page.svelte`)
- Props: Explicitly typed with JSDoc comments

**New Admin Page Route:**
- Page file: `app/src/routes/admin/section/+page.svelte`
- Server load: `app/src/routes/admin/section/+page.server.ts` (call FastAPI endpoint)
- Form action: `app/src/routes/admin/section/+server.ts` if mutations needed (POST/PATCH/DELETE)
- Detail page: `app/src/routes/admin/section/[id]/+page.svelte` (if needed)

**New Pipeline Step:**
- Command: `pipeline/commands/new_step.py` (subcommand function)
- Update: `pipeline/__main__.py` to add argparse subcommand
- Database: Extend AdminJobStep enum in `api/models/models.py` if step is job-tracked
- Admin UI: Update job detail page to display new step in RunStatusCard

**Bug Fix:**
- Implementation: Fix the bug in its source file (no special directory)
- Tests: Add regression test in existing test file or new test file in `api/tests/` or `pipeline/tests/`
- Migration: If schema change required, create new alembic migration

**Utilities/Helpers:**
- Shared API utilities: `api/core/utils.py` (if not already in core/) or extend existing util file
- Shared pipeline utilities: `pipeline/utils.py` (if not already modularized)
- Shared frontend utilities: `app/src/lib/utils.ts` (if not already modularized)
- Frontend hooks: `app/src/lib/hooks/` (if multiple custom hooks needed; else inline in pages)

**Tests:**
- API unit test: `api/tests/test_module.py` (mirrors production file structure)
- Pipeline unit test: `pipeline/tests/test_command.py` or `pipeline/tests/test_parser.py`
- Integration test: `tests/test_feature.py` (root-level tests directory)

## Special Directories

**`data/`:**
- Purpose: Immutable ingested PDF files + uploads
- Generated: Yes (created by ingest command and file uploads)
- Committed: No (.gitignore entries prevent commit)
- Structure: `data/{case-slug}/{argument_id}.pdf` for PDFs; `data/uploads/{filename}` for photos
- Safety: Ingest skips download if file already exists (idempotent). Files are never deleted or modified after creation.

**`data/uploads/`:**
- Purpose: Profile photos for speakers
- Generated: Yes (uploaded via SvelteKit form action)
- Committed: No (.gitignore)
- Persistence: Persisted in dev; may be cleared in prod (non-critical cache)

**`.svelte-kit/`:**
- Purpose: SvelteKit build artifacts and generated types
- Generated: Yes (by `svelte-kit sync` and build)
- Committed: No (.gitignore)
- Never edit manually — regenerated on build

**`.venv/`:**
- Purpose: Python virtual environment
- Generated: Yes (by `python -m venv .venv`)
- Committed: No (.gitignore)
- Activate before running pipeline: `.venv/Scripts/activate` (Windows) or `source .venv/bin/activate` (macOS/Linux)

**`node_modules/`:**
- Purpose: npm dependencies for frontend
- Generated: Yes (by `npm install`)
- Committed: No (.gitignore)
- Lockfile committed: `app/package-lock.json` (deterministic builds)

**`__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes (by Python interpreter)
- Committed: No (.gitignore)
- Safe to delete (regenerated on next run)

**`.pytest_cache/`:**
- Purpose: pytest cache (fixture definitions, test collection)
- Generated: Yes (by pytest)
- Committed: No (.gitignore)
- Safe to delete (regenerated on next run)

## Key Implicit Conventions (from codebase analysis)

**API Services:**
- All services in `api/services/` return plain Python dicts or lists of dicts (not ORM objects)
- Router calls service, then passes dict through Pydantic response_model (schema separation)
- All queries use SQLAlchemy 2.0 async pattern (select(), await db.execute())
- All update() statements include .execution_options(synchronize_session=False)

**Frontend Routing:**
- Server-side data loading in `+page.server.ts` only (load functions)
- Client-side fetch via `fetch(FASTAPI_BASE_URL/...)` with FASTAPI_BASE_URL from `$env/static/private`
- Never use PUBLIC_ prefix for FASTAPI_BASE_URL (security: server-only env var)
- SvelteKit type-safe routing via route parameters in filenames
- Admin pages all protected by session verification in hooks.server.ts

**Components:**
- All Svelte components use Svelte 5 Runes ($props(), $derived(), $state())
- No legacy stores or reactive statements ($: blocks)
- Props explicitly typed and documented in JSDoc
- No data fetching in components (only in +page.server.ts)

**Pipeline:**
- All database operations async (asyncio.run() at CLI boundary)
- State machine produces list of named tuples or dataclasses (not ORM rows)
- LLM failures gracefully degrade to rule-based output (no hard failure)
- Each command is re-runnable and idempotent (safe to re-run)
- Subprocess job status written to admin_jobs table (not stdout)

**Database:**
- Alembic is sole DDL authority (never call Base.metadata.create_all())
- All migrations hand-written (not autogenerated) for explicit dependency ordering
- Enums use SQLAlchemy SAEnum type (mapped to PG native enum types)
- Foreign keys always created (no soft references except citations, which are future)
- ArgumentStatusLog inserted every time Argument.status changes (audit trail)

---

*Structure analysis: 2026-07-08*
