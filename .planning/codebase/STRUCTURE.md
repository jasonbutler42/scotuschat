# Codebase Structure

**Analysis Date:** 2026-06-15

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
│   └── versions/               # Migration files
│       ├── 0001_initial_schema.py
│       └── 0002_add_speaker_alias.py
├── api/                        # FastAPI backend (read-only HTTP)
│   ├── __init__.py
│   ├── main.py                 # FastAPI app definition, lifespan, router inclusion
│   ├── core/                   # Core infrastructure
│   │   ├── __init__.py
│   │   ├── config.py           # Environment variables via pydantic-settings
│   │   └── database.py         # Async engine, session factory, lifespan context
│   ├── models/                 # SQLAlchemy ORM table definitions
│   │   ├── __init__.py
│   │   └── models.py           # 11 tables (roles, people, court_tenures, cases, etc.)
│   ├── routers/                # FastAPI route handlers
│   │   ├── __init__.py
│   │   ├── cases.py            # GET /cases (list all)
│   │   ├── arguments.py         # GET /arguments/{id}/utterances (detail + chat)
│   │   └── people.py           # GET /people/{id} (speaker bio)
│   ├── services/               # Business logic layer
│   │   ├── __init__.py
│   │   ├── cases.py            # get_cases() → list dicts
│   │   ├── arguments.py         # get_argument_with_utterances() → detail + utterances
│   │   └── people.py           # get_person() → speaker bio
│   ├── schemas/                # Pydantic v2 response models
│   │   ├── __init__.py
│   │   ├── cases.py            # CasesResponse, CaseItem
│   │   ├── utterance.py         # UtterancesResponse, UtteranceResponse
│   │   └── people.py           # PersonResponse
│   └── tests/                  # API unit tests
│       ├── __init__.py
│       ├── test_arguments.py
│       ├── test_people.py
│       └── conftest.py
├── app/                        # SvelteKit 2.x frontend (SSR via adapter-node)
│   ├── src/
│   │   ├── app.d.ts            # TypeScript ambient types
│   │   ├── app.css             # Global Tailwind CSS (imported in +layout.svelte)
│   │   ├── lib/
│   │   │   └── components/     # Reusable Svelte 5 Runes components
│   │   │       ├── ChatBubble.svelte       # Individual utterance bubble (left=bench, right=advocate)
│   │   │       ├── SectionRail.svelte      # Sticky section navigator (desktop, sticky top)
│   │   │       ├── MobileNavBar.svelte     # Fixed-bottom pill nav (mobile, hidden desktop)
│   │   │       └── StageDirection.svelte   # Stage direction text (e.g. "(Laughter.)")
│   │   └── routes/             # SvelteKit route pages (file-based routing)
│   │       ├── +layout.svelte  # Root layout (header, site nav, {@render children()})
│   │       └── cases/          # /cases route group
│   │           ├── +page.server.ts    # Server load: fetch /cases from FastAPI
│   │           ├── +page.svelte       # Case list page
│   │           └── [slug]/            # /cases/{slug} route group
│   │               ├── +page.server.ts      # Server load: fetch case detail, handle redirect for single arg
│   │               ├── +page.svelte         # Case detail page (multi-arg picker or redirect)
│   │               └── arguments/
│   │                   └── [id]/
│   │                       ├── +page.server.ts  # Server load: fetch /arguments/{id}/utterances
│   │                       └── +page.svelte     # Argument detail (chat view, SectionRail, MobileNavBar)
│   ├── svelte.config.js        # SvelteKit config (adapter: adapter-node for SSR)
│   ├── package.json            # Dependencies (SvelteKit, Svelte 5, Tailwind, TypeScript)
│   ├── tsconfig.json           # TypeScript config
│   ├── vite.config.ts          # Vite bundler config
│   └── .svelte-kit/            # Generated SvelteKit internal files (gitignored)
├── data/                       # Immutable ingested PDF files
│   └── [case-slug]/
│       └── [argument_id].pdf   # Downloaded from supremecourt.gov (never modified)
├── pipeline/                   # Python 3.12 offline CLI (ingest, parse, resolve)
│   ├── __init__.py
│   ├── __main__.py             # CLI entry point (argparse subcommands)
│   ├── db.py                   # Async session and connection pooling
│   ├── commands/               # Subcommand implementations
│   │   ├── __init__.py
│   │   ├── ingest.py           # Download PDF, create case/argument/pipeline_run
│   │   ├── parse.py            # Extract utterances via pdfplumber + state machine + LLM
│   │   ├── resolve.py          # Map speaker labels to person_id (interactive)
│   │   └── seed_aliases.py     # Pre-load Justice records and speaker_alias
│   ├── parser/                 # PDF parsing modules
│   │   ├── __init__.py
│   │   ├── extractor.py        # pdfplumber text extraction, line number/header stripping
│   │   ├── state_machine.py    # Rule-based speaker/section detection
│   │   └── llm_pass.py         # Claude corrective pass via instructor
│   └── tests/                  # Pipeline unit tests
│       ├── __init__.py
│       ├── conftest.py         # Fixtures
│       ├── test_ingest.py
│       ├── test_parse.py
│       ├── test_pipeline_run.py
│       ├── test_resolve.py
│       └── test_seed_aliases.py
├── tests/                      # Integration tests (root-level, run both API + pipeline)
│   └── __init__.py
├── scripts/                    # Utility scripts (not part of core pipeline)
├── memory/                     # User memory (auto-persisted across conversations)
│   └── MEMORY.md               # Known bugs, design decisions
├── .env.example                # Environment variables template (copy to .env)
├── .gitignore                  # Git exclusions (node_modules, .venv, __pycache__, .env)
├── CLAUDE.md                   # Project instructions (tech stack, GSD workflow, architecture rules)
├── README.md                   # (if present) Project overview for GitHub
├── requirements.txt            # Python dependencies (FastAPI, SQLAlchemy, pdfplumber, etc.)
├── requirements-dev.txt        # Dev dependencies (pytest, etc.)
├── pytest.ini                  # pytest configuration
└── alembic.ini                 # Alembic migration configuration (in root)
```

## Directory Purposes

**`.planning/`:**
- Purpose: GSD workflow artifacts (phases, plans, discussion logs, research spikes, codebase analysis documents)
- Contains: PROJECT.md, STATE.md, ROADMAP.md, REQUIREMENTS.md; phase-specific folders (01-foundation-proof-of-concept, etc.); codebase/ folder with ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md
- Key files: `.planning/codebase/` is where codebase analysis documents are written

**`api/`:**
- Purpose: FastAPI read-only HTTP server
- Contains: HTTP request handlers, business logic services, Pydantic response schemas, SQLAlchemy ORM models, async database configuration
- Key files: `api/main.py` (app entry point), `api/models/models.py` (all 11 table definitions), `api/core/database.py` (async setup)

**`app/`:**
- Purpose: SvelteKit 2.x frontend (SSR, Node.js deployment)
- Contains: Pages (routes), components, TypeScript types, Tailwind CSS
- Key files: `app/src/routes/` (all pages), `app/src/lib/components/` (reusable components), `svelte.config.js` (SSR adapter: adapter-node)

**`pipeline/`:**
- Purpose: Offline Python CLI for ingest, parse, resolve
- Contains: Subcommands, PDF extraction, state machine, LLM integration
- Key files: `pipeline/__main__.py` (CLI dispatcher), `pipeline/commands/` (ingest, parse, resolve, seed_aliases), `pipeline/parser/` (extractor, state_machine, llm_pass)

**`data/`:**
- Purpose: Immutable ingested PDF files, organized by case slug
- Contains: Subdirectories per case, one PDF per argument file
- Key constraint: Never modified after creation; ingest skips download if file exists (idempotency)

**`alembic/`:**
- Purpose: Database schema management via migrations
- Contains: Migration files (0001_initial_schema.py, 0002_add_speaker_alias.py), env.py (async setup), alembic.ini (config)
- Key files: `alembic/versions/` (migration history), `alembic/env.py` (async config), `alembic.ini` (connection settings)

**`tests/` (root level):**
- Purpose: Integration tests spanning API + pipeline
- Contains: Test files that may need both api and pipeline modules
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
- Environment: `.env` (not committed), `.env.example` (template)

**Core Logic:**
- API routers: `api/routers/` (cases.py, arguments.py, people.py)
- API services: `api/services/` (business logic, ORM queries)
- API schemas: `api/schemas/` (Pydantic response models)
- API models: `api/models/models.py` (11 SQLAlchemy ORM tables)
- Pipeline ingest: `pipeline/commands/ingest.py`
- Pipeline parse: `pipeline/commands/parse.py`, `pipeline/parser/` (extractor, state_machine, llm_pass)
- Pipeline resolve: `pipeline/commands/resolve.py`

**Testing:**
- API unit tests: `api/tests/` (test_arguments.py, test_people.py)
- Pipeline unit tests: `pipeline/tests/` (test_ingest.py, test_parse.py, test_resolve.py, etc.)
- Integration tests: `tests/` (root level, if needed)
- Fixtures: `pipeline/tests/conftest.py`, `api/tests/conftest.py`
- Config: `pytest.ini` (root level)

## Naming Conventions

**Files:**
- Python files: `snake_case.py` (e.g., `get_cases.py`, `ingest.py`)
- Svelte components: `PascalCase.svelte` (e.g., `ChatBubble.svelte`, `SectionRail.svelte`)
- TypeScript files: `snake_case.ts` or `PascalCase.ts` depending on export (e.g., `+page.server.ts`, `app.d.ts`)
- Config files: lowercase with dots (e.g., `svelte.config.js`, `vite.config.ts`, `tsconfig.json`)
- Migration files: `NNNN_description.py` (e.g., `0001_initial_schema.py`)

**Directories:**
- Python packages: `snake_case/` (e.g., `api/`, `pipeline/`, `models/`, `routers/`)
- SvelteKit routes: `[brackets]` for dynamic segments (e.g., `[slug]`, `[id]`)
- Component directories: `components/` (lowercase, plural)
- Utilities: `lib/` (SvelteKit convention for shared code)

**Python Classes:**
- ORM models: `PascalCase` (e.g., `Case`, `Argument`, `Utterance`, `Person`)
- Enums: `PascalCase` (e.g., `SideEnum`, `PipelineRunStatus`)
- Pydantic models: `PascalCase` (e.g., `UtteranceResponse`, `CaseItem`)
- Services: `snake_case` functions in `snake_case.py` files (e.g., `get_cases()`, `get_argument_with_utterances()`)

**Database:**
- Tables: `snake_case` (e.g., `cases`, `arguments`, `utterances`, `pipeline_runs`)
- Columns: `snake_case` (e.g., `docket_number`, `argued_date`, `is_stage_direction`)
- Enum types (PG native): `snake_case` with lowercase values (e.g., `PipelineRunStatus` with "pending", "running", "completed")
- Enums (SideEnum): `UPPERCASE` values (BENCH, ADVOCATE, UNKNOWN) to match raw transcript labels

## Where to Add New Code

**New Feature (e.g., "Add citations table"):**
- Schema: `alembic/versions/NNNN_add_citations.py` (new migration file)
- ORM: Add class to `api/models/models.py`
- Service: Create `api/services/citations.py` with query functions
- Router: Create `api/routers/citations.py` with @router endpoints
- Schema: Create `api/schemas/citations.py` with Pydantic models
- Frontend: Create `app/src/routes/citations/` with +page.server.ts, +page.svelte
- Tests: Add `api/tests/test_citations.py` and/or `pipeline/tests/` if pipeline step involved

**New Component/Module:**
- Reusable component: `app/src/lib/components/NewComponent.svelte` (Svelte 5 Runes pattern)
- Utility function: `app/src/lib/utils.ts` (if utilities directory exists, else inline in +page.svelte)
- Backend service: `api/services/new_feature.py` (business logic functions)
- Pipeline step: `pipeline/commands/new_step.py` (subcommand function, update `pipeline/__main__.py` to wire it in)

**Bug Fix:**
- Implementation: Fix the bug in its source file (no special directory)
- Tests: Add regression test in existing test file or new test file in `api/tests/` or `pipeline/tests/`
- Migration: If schema change required, create new alembic migration

**Utilities/Helpers:**
- Shared API utilities: `api/core/utils.py` (if not already in core/)
- Shared pipeline utilities: `pipeline/utils.py` (if not already modularized)
- Shared frontend utilities: `app/src/lib/utils.ts` (if not already modularized)
- Date formatting: Already in `+page.svelte` files (formatDate function); could be extracted to `app/src/lib/utils.ts` if reused

**Tests:**
- API unit test: `api/tests/test_module.py` (mirrors production file structure)
- Pipeline unit test: `pipeline/tests/test_command.py` or `pipeline/tests/test_parser.py`
- Integration test: `tests/test_feature.py` (root-level tests directory)

## Special Directories

**`data/`:**
- Purpose: Immutable ingested PDF files
- Generated: Yes (created by ingest command)
- Committed: No (.gitignore entries prevent commit)
- Structure: `data/{case-slug}/{argument_id}.pdf`
- Safety: Ingest skips download if file already exists (idempotent). Files are never deleted or modified after creation.

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

**Frontend Routing:**
- Server-side data loading in `+page.server.ts` only (load functions)
- Client-side fetch via `fetch(FASTAPI_BASE_URL/...)` with FASTAPI_BASE_URL from `$env/static/private`
- Never use PUBLIC_ prefix for FASTAPI_BASE_URL (security: server-only env var)
- SvelteKit type-safe routing via route parameters in filenames

**Components:**
- All Svelte components use Svelte 5 Runes ($props(), $derived(), $state())
- No legacy stores or reactive statements ($: blocks)
- Props explicitly typed and documented
- No data fetching in components (only in +page.server.ts)

**Pipeline:**
- All database operations async (asyncio.run() at CLI boundary)
- State machine produces list of named tuples or dataclasses (not ORM rows)
- LLM failures gracefully degrade to rule-based output (no hard failure)
- Each command is re-runnable and idempotent (safe to re-run)

**Database:**
- Alembic is sole DDL authority (never call Base.metadata.create_all())
- All migrations hand-written (not autogenerated) for explicit dependency ordering
- Enums use SQLAlchemy SAEnum type (mapped to PG native enum types)
- Foreign keys always created (no soft references except citations, which are future)

---

*Structure analysis: 2026-06-15*
