---
phase: 01-foundation-proof-of-concept
plan: 03
subsystem: pipeline
tags: [python, sqlalchemy, asyncpg, httpx, pytest, argparse, ssrf-mitigation]

# Dependency graph
requires:
  - phase: 01-foundation-proof-of-concept/01-01
    provides: Python scaffold, requirements.txt, pipeline/__init__.py
  - phase: 01-foundation-proof-of-concept/01-02
    provides: SQLAlchemy ORM models (api/models/models.py), Alembic migrations

provides:
  - pipeline/db.py — async SQLAlchemy engine with statement_cache_size=0 in connect_args
  - pipeline/__main__.py — python -m pipeline CLI entry point (ingest + parse subcommands)
  - pipeline/commands/ingest.py — SSRF-validated PDF download + case/argument/pipeline_run DB records
  - pipeline/commands/parse.py — parse command stub (implemented in Plan 04)
  - pipeline/tests/conftest.py — async session fixture (no create_all)
  - pipeline/tests/test_ingest.py — URL validation tests + DB-dependent ingest tests
  - tests/conftest.py — root-level conftest with load_dotenv
  - data/pdfs/.gitkeep + data/pdfs/.gitignore — immutable PDF storage directory

affects:
  - 01-foundation-proof-of-concept/01-04 (parse command consumes pipeline_run rows from ingest)
  - 01-foundation-proof-of-concept/01-05 (FastAPI reads cases/arguments created by ingest)

# Tech tracking
tech-stack:
  added:
    - httpx (async HTTP client for PDF download)
    - python-dotenv (DATABASE_URL loading in pipeline CLI)
    - pytest-asyncio (async test support for DB fixtures)
  patterns:
    - Lazy engine creation: get_engine() called inside asyncio.run() coroutines, not at import time
    - SSRF mitigation: _validate_url() called before any httpx call (urlparse netloc endswith check)
    - Idempotent ingest: SELECT-first pattern for Case rows; CaseArgument existence check before insert
    - Immutable PDF storage: pdf_path.write_bytes() only when file does not already exist
    - connect_args={"statement_cache_size": 0} — mandatory in connect_args (not top-level) for asyncpg/PgBouncer

key-files:
  created:
    - pipeline/db.py
    - pipeline/__main__.py
    - pipeline/commands/__init__.py
    - pipeline/commands/ingest.py
    - pipeline/commands/parse.py
    - pipeline/tests/conftest.py
    - pipeline/tests/test_ingest.py
    - tests/conftest.py
    - data/pdfs/.gitkeep
    - data/pdfs/.gitignore
  modified:
    - .gitignore (data/pdfs/ → data/pdfs/*.pdf to allow .gitkeep tracking)

key-decisions:
  - "SSRF mitigation: _validate_url() is a standalone synchronous function, called first in run_ingest before any I/O — enables unit testing without a DB"
  - "Engine created lazily inside coroutines (not at module import) — prevents DATABASE_URL errors during test collection when env var is absent"
  - "get_session() async context manager commits on clean exit, rolls back on exception — single clean pattern for all pipeline steps"
  - "parse.py stub created in Plan 03 to satisfy __main__.py import; full implementation in Plan 04"
  - "data/pdfs/.gitignore pattern: move parent .gitignore rule from 'data/pdfs/' directory-level to 'data/pdfs/*.pdf' file-level, enabling .gitkeep tracking"
  - "PipelineRun.status set directly to COMPLETED for ingest (synchronous operation — no pending→running transition needed)"

patterns-established:
  - "Pipeline CLI pattern: python -m pipeline <subcommand> using argparse in __main__.py; asyncio.run(run_<cmd>(args)) in main()"
  - "SSRF guard: _validate_url(url) must be the first call in any function that accepts a URL parameter"
  - "Test isolation: async_session fixture rolls back after each test; no truncation needed for most tests"
  - "DB-skip pattern: test_db_url fixture calls pytest.skip() when DATABASE_URL absent; all DB tests skip gracefully"

requirements-completed: [PIPE-01, PIPE-02]

# Metrics
duration: 45min
completed: 2026-06-11
---

# Phase 1 Plan 03: Pipeline Ingest Command Summary

**Async pipeline CLI (python -m pipeline ingest) with SSRF-validated PDF download, immutable storage, and idempotent case/argument/case_arguments/pipeline_run DB record creation**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-06-11T00:00:00Z
- **Completed:** 2026-06-11
- **Tasks:** 4
- **Files created:** 10 | **Files modified:** 1

## Accomplishments

- pipeline/db.py: async engine factory with mandatory `connect_args={"statement_cache_size": 0}` for PgBouncer compatibility, expire_on_commit=False, lazy creation pattern
- pipeline/commands/ingest.py: SSRF mitigation (_validate_url validates scheme=https and netloc endswith "supremecourt.gov" before any httpx call), idempotent Case rows, M:M CaseArgument join for Obergefell's 4 consolidated dockets, PipelineRunStatus.COMPLETED on successful ingest
- pipeline/__main__.py: argparse CLI with ingest (--url, --primary-docket, --dockets, --case-name, --argued-date, --question) and parse (--run-id, --dry-run) subcommands
- pipeline/tests/test_ingest.py: 9 tests including 6 URL validation tests (no DB needed) + 3 DB-dependent tests with graceful skip

## Task Commits

Each task was committed atomically:

1. **Task 1: Pipeline database module (pipeline/db.py)** - feat(01-03): add async SQLAlchemy engine with statement_cache_size=0
2. **Task 2: Pipeline __main__.py entry point** - feat(01-03): add argparse CLI entry point with ingest and parse subcommands
3. **Task 3: Pipeline ingest command** - feat(01-03): add ingest command with SSRF validation, PDF download, DB records
4. **Task 4: Test infrastructure and ingest unit tests** - feat(01-03): add conftest.py fixtures and ingest unit tests

**Plan metadata:** docs(01-03): complete pipeline ingest plan

## Files Created/Modified

- `pipeline/db.py` — Async engine factory; statement_cache_size=0 in connect_args; get_session() context manager
- `pipeline/__main__.py` — argparse CLI entry point; ingest and parse subcommands
- `pipeline/commands/__init__.py` — empty package marker
- `pipeline/commands/ingest.py` — SSRF URL validation; PDF download (idempotent); Case/Argument/CaseArgument/PipelineRun DB records
- `pipeline/commands/parse.py` — stub (to satisfy __main__.py import; full impl in Plan 04)
- `pipeline/tests/conftest.py` — test_db_url, engine, async_session, clean_db fixtures; no create_all
- `pipeline/tests/test_ingest.py` — 9 tests: 6 URL validation (no DB) + 3 DB-dependent with skip
- `tests/conftest.py` — root-level load_dotenv stub
- `data/pdfs/.gitkeep` — ensures data/pdfs/ directory is tracked in git
- `data/pdfs/.gitignore` — ignores *.pdf files (immutable; not tracked in git)
- `.gitignore` (modified) — changed data/pdfs/ directory-level ignore to data/pdfs/*.pdf file-level to allow .gitkeep

## Decisions Made

- **SSRF validation as standalone function:** `_validate_url()` is a synchronous standalone function, not inlined in `run_ingest`. This allows URL validation tests to run without any async setup or DB — they call `_validate_url()` directly.
- **Lazy engine creation:** `get_engine()` creates the engine inside the coroutine (not at import time). This prevents `KeyError: DATABASE_URL` during pytest collection when .env is not set.
- **PipelineRunStatus.COMPLETED for ingest:** Ingest is a synchronous operation (download + DB writes in one session). Status goes directly to COMPLETED — no `pending → running` transition. The state machine pattern from RESEARCH.md Pattern 3 is used by the parse step (Plan 04) where async work needs intermediate status tracking.
- **parse.py stub in Plan 03:** `__main__.py` imports `run_parse` from `pipeline.commands.parse`. A minimal stub was created to satisfy the import without blocking `python -m pipeline --help` until Plan 04.
- **.gitignore pattern change:** Root .gitignore had `data/pdfs/` (directory-level ignore). Changed to `data/pdfs/*.pdf` (file-level) so `data/pdfs/.gitkeep` and `data/pdfs/.gitignore` can be tracked. This is semantically equivalent for PDF files.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] parse.py stub created alongside ingest**
- **Found during:** Task 2 (pipeline/__main__.py)
- **Issue:** `__main__.py` imports `from pipeline.commands.parse import run_parse`. Without this file, `python -m pipeline --help` fails with ImportError. The plan listed `parse.py` as a Task 4 dependency, but it's a Task 2 import dependency.
- **Fix:** Created `pipeline/commands/parse.py` with a stub `run_parse()` that prints a "not yet implemented" message. Plan 04 replaces this with the full implementation.
- **Files modified:** pipeline/commands/parse.py (new)
- **Verification:** `python -m pipeline --help` exits 0 showing both subcommands

**2. [Rule 1 - Bug] .gitignore updated to allow .gitkeep tracking**
- **Found during:** Task 3 (data/pdfs/.gitkeep)
- **Issue:** Root .gitignore had `data/pdfs/` which ignores the entire directory including `.gitkeep` and `.gitignore`. Git cannot track `.gitkeep` when the parent directory is ignored.
- **Fix:** Changed `data/pdfs/` to `data/pdfs/*.pdf` in root .gitignore. Created `data/pdfs/.gitignore` with `*.pdf` as the canonical ignore rule for PDF files.
- **Files modified:** .gitignore, data/pdfs/.gitignore (new)
- **Verification:** `git status` would show data/pdfs/.gitkeep and data/pdfs/.gitignore as new tracked files

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug)
**Impact on plan:** Both deviations are minor and necessary. No scope creep. parse.py stub is explicitly described as "stub OK in this plan" in the task description.

## Issues Encountered

None - plan executed as specified.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: ssrf-mitigated | pipeline/commands/ingest.py | SSRF mitigation T-03-01 implemented: _validate_url() validates scheme=https AND netloc endswith "supremecourt.gov" before any httpx call |

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| run_parse() stub | pipeline/commands/parse.py | Returns "not yet implemented" message. Full implementation in Plan 04 (pipeline parse step). |

## User Setup Required

None - no external service configuration required beyond DATABASE_URL in .env (already required from Plan 01).

## Next Phase Readiness

- Plan 04 (pipeline parse step) can now extend `pipeline/commands/parse.py` with the full pdfplumber + state machine + instructor implementation
- Plan 04 should import `get_session` from `pipeline/db.py` using the same pattern as ingest
- URL validation pattern from `_validate_url()` is reusable if parse step ever accepts a URL input
- DB-dependent tests in test_ingest.py require `alembic upgrade head` to have been run against the test database before they will pass

---
*Phase: 01-foundation-proof-of-concept*
*Completed: 2026-06-11*

## Self-Check

Files created/verified:
- pipeline/db.py: created ✓
- pipeline/__main__.py: created ✓
- pipeline/commands/__init__.py: created ✓
- pipeline/commands/ingest.py: created ✓
- pipeline/commands/parse.py: created ✓
- pipeline/tests/conftest.py: created ✓
- pipeline/tests/test_ingest.py: created ✓
- tests/conftest.py: created ✓
- data/pdfs/.gitkeep: created ✓
- data/pdfs/.gitignore: created ✓
- .gitignore: modified ✓

Key string verification:
- pipeline/db.py contains "statement_cache_size" in connect_args dict: ✓
- pipeline/db.py contains "expire_on_commit=False": ✓
- pipeline/db.py contains "load_dotenv": ✓
- pipeline/commands/ingest.py contains "supremecourt.gov" check before httpx: ✓
- pipeline/commands/ingest.py contains "follow_redirects=True": ✓
- pipeline/commands/ingest.py contains "PipelineRunStatus.COMPLETED": ✓
- pipeline/commands/ingest.py contains "from api.models.models import": ✓
- pipeline/commands/ingest.py contains "pdf_path.write_bytes": ✓
- pipeline/tests/conftest.py contains "statement_cache_size": ✓
- pipeline/tests/conftest.py contains "pytest.skip": ✓
- No .create_all() calls in pipeline/ production code: ✓
- test_ingest.py contains all 5 required test functions: ✓

## Self-Check: PASSED
