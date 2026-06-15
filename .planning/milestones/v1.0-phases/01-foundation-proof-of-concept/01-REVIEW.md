---
phase: 01-foundation-proof-of-concept
reviewed: 2026-06-11T00:00:00Z
depth: standard
files_reviewed: 25
files_reviewed_list:
  - api/core/config.py
  - api/core/database.py
  - api/main.py
  - api/models/models.py
  - api/routers/arguments.py
  - api/schemas/utterance.py
  - api/services/arguments.py
  - api/tests/test_arguments.py
  - alembic/env.py
  - alembic/versions/0001_initial_schema.py
  - app/src/lib/components/ChatBubble.svelte
  - app/src/lib/components/StageDirection.svelte
  - app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts
  - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte
  - pipeline/__main__.py
  - pipeline/commands/ingest.py
  - pipeline/commands/parse.py
  - pipeline/db.py
  - pipeline/parser/extractor.py
  - pipeline/parser/llm_pass.py
  - pipeline/parser/state_machine.py
  - pipeline/tests/conftest.py
  - pipeline/tests/test_ingest.py
  - pipeline/tests/test_parse.py
  - pipeline/tests/test_pipeline_run.py
  - tests/test_schema.py
findings:
  critical: 5
  warning: 8
  info: 3
  total: 16
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-06-11T00:00:00Z
**Depth:** standard
**Files Reviewed:** 25
**Status:** issues_found

## Summary

Reviewed the full Phase 1 foundation across FastAPI backend, SvelteKit frontend, SQLAlchemy/Alembic schema, pipeline CLI, and all tests. The overall architecture is sound: FASTAPI_BASE_URL is correctly server-only, `statement_cache_size=0` is correctly placed in `connect_args`, Alembic is the sole DDL authority (no `create_all` calls), Svelte 5 Runes patterns are used throughout, and URL validation runs before any httpx call.

Five critical issues were found: an NPE crash when `AsyncSessionLocal` is `None` (uninitialized DB), a `null` speaker label rendered unchecked in ChatBubble, a dry-run parse path that commits an unintended status transition, a `PIPE-11 latest-run` query that uses `MAX(pipeline_run_id)` instead of `MAX(id from pipeline_runs WHERE step='parse' AND status='completed')`, and a `test_no_create_all_in_codebase` test that calls `grep` by name (fails on Windows/environments without grep on PATH). Eight warnings cover slug generation gaps, side-alignment apolitical framing asymmetry, session-scoped async engine teardown, an `os.environ["DATABASE_URL"]` hard crash in `alembic/env.py`, and several reliability/correctness edge cases in the parser and tests.

---

## Critical Issues

### CR-01: `get_db` crashes with `TypeError` when called before lifespan completes

**File:** `api/core/database.py:61`
**Issue:** `AsyncSessionLocal` is `None` at module import time and only assigned inside the `lifespan` context manager. `get_db` calls `AsyncSessionLocal()` unconditionally. If a request arrives before the lifespan startup has completed (e.g. a health-check race, test client not using `async with`, or if the engine is reused across test cases without the lifespan), Python raises `TypeError: 'NoneType' object is not callable`. The health endpoint also uses no DB, but the router wires `get_db` as a dependency on `/arguments/{id}/utterances` — any failure in the `lifespan` startup silently leaves `AsyncSessionLocal` as `None` and the first real request will crash with an opaque `TypeError` instead of a 503/500 with a meaningful message.

**Fix:**
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "Database session factory is not initialised — "
            "lifespan may not have completed startup."
        )
    async with AsyncSessionLocal() as session:
        yield session
```

---

### CR-02: `ChatBubble.svelte` renders `null` speaker label for stage-direction-like utterances

**File:** `app/src/lib/components/ChatBubble.svelte:53`
**Issue:** `utterance.raw_speaker_label` is `Optional[str]` in the API schema (null for stage directions). The `ChatBubble` component is only rendered when `utterance.is_stage_direction` is `false` (guarded in `+page.svelte:90`), but `raw_speaker_label` can still be `null` for non-stage-direction rows — for example, utterances produced by the LLM pass if the model returns `raw_speaker_label: null` on a non-stage-direction utterance, or corrupt parse output. When `utterance.raw_speaker_label` is `null`, the template renders the literal string `"null"` into the DOM, which is both a display bug and a data fidelity violation.

**Fix:**
```svelte
<span style="font-size: 13px; font-weight: 600; color: {labelColor};">
    {utterance.raw_speaker_label ?? ''}
</span>
```

---

### CR-03: Dry-run parse path commits an in-progress status transition without completing it

**File:** `pipeline/commands/parse.py:165-168`
**Issue:** In `run_parse`, at Step 2 (line 78–80) the run's status is set to `RUNNING` and `session.flush()` is called. The function then checks `args.dry_run` at Step 6 (line 165) and returns early with `return` — never reaching Step 7 (the `COMPLETED` transition). Because `get_session()` commits on clean context-manager exit, a dry run exits the `async with get_session()` block with `status=RUNNING`, which is then committed to the database. After a dry run, the `pipeline_run` row is permanently stuck in `RUNNING` status. Subsequent re-runs check `run.status not in (PipelineRunStatus.PENDING,)` and print a misleading warning but do not block, so the damage is silent.

**Fix:** Add a status transition before the early return, or do not transition to RUNNING before knowing whether the write will be committed:
```python
if args.dry_run:
    # Reset to PENDING so the run remains re-runnable
    run.status = PipelineRunStatus.PENDING
    run.strategy = None
    print(f"Dry-run mode: {len(utterances)} utterances parsed but NOT written to DB.")
    print(f"Parse dry-run complete. strategy={run.strategy}")
    return
```
Alternatively, do not flush the `RUNNING` transition until after the dry_run check.

---

### CR-04: `PIPE-11` latest-run query uses `MAX(pipeline_run_id)` on utterances — returns wrong run when parse fails mid-write

**File:** `api/services/arguments.py:83-87`
**Issue:** The query `SELECT MAX(pipeline_run_id) FROM utterances WHERE argument_id = ?` finds the run with the highest ID that has at least one utterance row. This breaks in at least two scenarios:

1. A parse run writes some utterances before crashing (partial write). The partial run gets a higher `pipeline_run_id` and becomes "latest", surfacing incomplete data to the UI.
2. A later pipeline run for a *different* step (e.g. a future "resolve" step that also writes utterances under a new run ID) would be selected instead of the most recent parse run.

The correct source of truth is the `pipeline_runs` table, not the `utterances` table.

**Fix:**
```python
from api.models.models import PipelineRun, PipelineRunStatus

max_run_result = await db.execute(
    select(func.max(PipelineRun.id)).where(
        PipelineRun.argument_id == argument_id,
        PipelineRun.step == "parse",
        PipelineRun.status == PipelineRunStatus.COMPLETED,
    )
)
max_run_id = max_run_result.scalar_one_or_none()
```

---

### CR-05: `test_no_create_all_in_codebase` calls `grep` by name — fails on Windows and CI images without grep on PATH

**File:** `tests/test_schema.py:142-147`
**Issue:** The static analysis test calls `subprocess.run(["grep", "-r", ...])` directly. On Windows (the confirmed platform: `win32`) and on some minimal CI Docker images, `grep` is not on `PATH`. The test silently passes on failure because `subprocess.run` with `capture_output=True` doesn't raise on `FileNotFoundError` by default — wait, actually it *does* raise `FileNotFoundError` (an OSError), causing the test to error rather than pass or skip. On Windows it will raise `FileNotFoundError: [WinError 2] The system cannot find the file specified`, crashing the test suite with an error rather than a clean failure message. Even on Linux CI, this is fragile because it relies on a system binary instead of Python's own file-searching.

**Fix:** Replace the `subprocess.run(["grep", ...])` approach with a pure-Python recursive file search:
```python
import pathlib, ast

def _find_create_all(search_dirs):
    offending = []
    for d in search_dirs:
        for pyfile in pathlib.Path(d).rglob("*.py"):
            if "create_all" in pyfile.read_text(encoding="utf-8", errors="ignore"):
                offending.append(str(pyfile))
    return offending
```

---

## Warnings

### WR-01: `alembic/env.py` crashes with `KeyError` when `DATABASE_URL` is absent from environment

**File:** `alembic/env.py:24`
**Issue:** `config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])` uses subscript access, which raises `KeyError: 'DATABASE_URL'` if the variable is not set — including in CI environments that only set it for specific test jobs, or when a developer runs `alembic history` or `alembic current` without a `.env` file present. `load_dotenv()` on line 20 only helps when a `.env` file exists; it does not populate the env if the file is absent.

**Fix:**
```python
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    raise RuntimeError(
        "DATABASE_URL must be set in the environment or .env file before running Alembic."
    )
config.set_main_option("sqlalchemy.url", db_url)
```

---

### WR-02: `ChatBubble` uses different visual alignment for BENCH vs ADVOCATE — violates apolitical framing hard constraint

**File:** `app/src/lib/components/ChatBubble.svelte:4-12`
**Issue:** CLAUDE.md states: "Every speaker (Justice or advocate) gets identical schema, depth, and treatment." The comment on line 5 acknowledges this ("identical backgrounds") but the implementation then gives BENCH `flex-end` (right-aligned) and ADVOCATE/UNKNOWN `flex-start` (left-aligned) — two visually distinct positions. Position/alignment is a form of visual treatment that distinguishes Justices from advocates. This is not identical treatment; it creates an implicit hierarchy or differentiation between the two sides. The comment claims "identical backgrounds" as the equalizer, but background is only one of several visual dimensions.

**Fix:** If the product intent is a chat-style layout with two sides (which is reasonable for readability), the apolitical constraint language in CLAUDE.md needs to be updated to reflect that positional differentiation is intentional and acceptable, OR the layout must be changed to render all utterances at the same horizontal position. The current implementation contradicts the stated hard constraint as written. At minimum, this ambiguity must be resolved before Phase 2 ships the UI.

---

### WR-03: `pipeline/db.py` creates a new engine and disposes it on every `get_session()` call

**File:** `pipeline/db.py:61-71`
**Issue:** `get_engine()` creates a brand-new `AsyncEngine` on every call (line 61 inside `get_session`). The engine is then disposed in the `finally` block (line 71). In `run_parse`, `get_session()` is called once, but `run_ingest` calls it once as well. Across multiple pipeline invocations in a single process — or if a future refactor calls `get_session()` more than once per command — a new connection pool is created and destroyed each time. While not a crash today, it also means `pool_size=2` is meaningless (the pool is always fresh) and the overhead of pool creation/teardown accumulates. More importantly, if `session.commit()` raises after `yield`, the `finally` block calls `engine.dispose()` while the session error is propagating — this is correct but the interaction between rollback (line 68), re-raise (line 69), and dispose (line 71) should be verified to not swallow the original exception under cancellation.

**Fix:** Lift engine creation to module-level (lazy singleton), similar to the FastAPI `lifespan` pattern:
```python
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            os.environ["DATABASE_URL"],
            connect_args={"statement_cache_size": 0},
            pool_size=2,
            echo=False,
        )
    return _engine
```
Then remove `await engine.dispose()` from the per-session `finally` block; dispose once at process exit if needed.

---

### WR-04: `_derive_slug` in `ingest.py` produces collision-prone slugs and does not handle special characters

**File:** `pipeline/commands/ingest.py:58-69`
**Issue:** The slug derivation strips only spaces, dots, and commas. Characters like `'` (apostrophe), `&`, `v.` (in "v." which becomes "v" after dot stripping, but "v" alone is not a separator), `;`, `/`, and unicode accents are passed through unchanged into the slug. For example:
- `"McDonald's Corp. v. City of Chicago"` → `"mcdonald's-corp-v-city-of-chicago"` (apostrophe in URL)
- `"United States v. O'Brien"` → `"united-states-v-o'brien"` (same)
- Multiple cases with similar names could produce duplicate slugs that violate the `UNIQUE` constraint on `cases.slug`, causing an unhandled `IntegrityError` during ingest.

**Fix:**
```python
import re

def _derive_slug(case_name: str) -> str:
    slug = case_name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)   # strip all non-alphanum except spaces/hyphens
    slug = re.sub(r"\s+", "-", slug.strip())     # spaces → hyphens
    slug = re.sub(r"-{2,}", "-", slug)           # collapse double hyphens
    return slug
```

---

### WR-05: Ingest does not check for duplicate `Argument` rows — re-running ingest for the same date/question creates a second `Argument` row

**File:** `pipeline/commands/ingest.py:158-164`
**Issue:** The ingest command is documented as idempotent (and `test_ingest_idempotent` verifies Case deduplication), but the `Argument` row creation at lines 158–164 is not guarded by a pre-existing check. Every call to `run_ingest` with the same `--argued-date` and `--question` creates a new `Argument` row unconditionally. This means re-running ingest produces duplicate arguments for the same hearing, which then each get their own `CaseArgument` links (which *are* deduplication-checked, but the new argument.id means the `WHERE CaseArgument.argument_id == argument.id` check always returns None, so new links are always created). The net result: two Argument rows exist for the same hearing, and the API might serve utterances from either one.

**Fix:** Add a deduplication check on `(argued_date, question_number)` before creating the Argument row:
```python
existing_arg_result = await session.execute(
    select(Argument).where(
        Argument.argued_date == date.fromisoformat(args.argued_date),
        Argument.question_number == args.question,
    )
)
argument = existing_arg_result.scalar_one_or_none()
if argument is None:
    argument = Argument(
        argued_date=date.fromisoformat(args.argued_date),
        question_number=args.question,
    )
    session.add(argument)
    await session.flush()
```

---

### WR-06: Inline stage-direction handling in the state machine drops the first continuation segment when `current_text_parts` is empty

**File:** `pipeline/parser/state_machine.py:340-355`
**Issue:** In the continuation line branch (lines 338–355), when an inline stage direction is found in a continuation line, the code does `current_text_parts.append(segments[0][0])` then calls `flush()`. If `current_text_parts` was empty before this append (i.e. the previous speaker turn had no body text yet — just a label line with no rest), the segment text is appended and then immediately flushed. However, `flush()` uses `" ".join(p for p in current_text_parts if p)` which produces just `segments[0][0]` as the utterance text. After flush, `current_speaker` is set to `None`. Then the loop over `segments[1:]` tries to restore the speaker via `utterances[-1]["raw_speaker_label"]` (line 352). If the flush just appended an utterance, `utterances[-1]` is the stage direction's preceding speech — this is the correct speaker. But if the flush found nothing (all empty parts), it returns early and `current_speaker` remains `None`. The subsequent `current_text_parts = [seg_text]` at line 354 sets text with no speaker, which on the next `flush()` emits an utterance with `raw_speaker_label=None` and `is_stage_direction=False` — a corrupt row that will be inserted into the DB.

**Fix:** Capture `current_speaker` before calling `flush()` and restore it after:
```python
saved_speaker = current_speaker
flush()
for seg_text, is_stage in segments[1:]:
    if not seg_text.strip():
        continue
    if is_stage:
        emit_stage(seg_text)
    else:
        current_speaker = saved_speaker
        current_text_parts = [seg_text]
```

---

### WR-07: `conftest.py` session-scoped `engine` fixture is never disposed — connection pool leaks across the test session

**File:** `pipeline/tests/conftest.py:55-70`
**Issue:** The `engine` fixture has `scope="session"` and creates an `AsyncEngine`, but there is no `yield`/teardown — it returns the engine directly with `return`. The engine's connection pool is never disposed after all tests complete. On asyncpg this typically means the event loop closes while connections are still open, producing `asyncpg: connection is closed` warnings or errors in teardown. With `scope="session"` the fixture cannot use `yield` inside a coroutine without `@pytest_asyncio.fixture(scope="session")`. The `async_session` fixture (function-scoped) rolls back but the engine's pool remains open.

**Fix:**
```python
@pytest_asyncio.fixture(scope="session")
async def engine(test_db_url: str):
    eng = create_async_engine(
        test_db_url,
        connect_args={"statement_cache_size": 0},
        pool_size=2,
        echo=False,
    )
    yield eng
    await eng.dispose()
```
Note: this requires `pytest-asyncio` in `asyncio_mode="auto"` or explicit marking, and `@pytest_asyncio.fixture` instead of `@pytest.fixture` for async fixtures.

---

### WR-08: `test_llm_failure_modes` constructs `anthropic.RateLimitError` with `response=None` — constructor signature is not stable across SDK versions

**File:** `pipeline/tests/test_parse.py:291-294`
**Issue:** `anthropic.RateLimitError("Rate limited", response=None, body={...})` passes `response=None`. The Anthropic Python SDK's `APIStatusError` subclasses require a `httpx.Response` object for `response`, not `None`. In some SDK versions this will fail at construction time with a `TypeError` or `AttributeError` when the error object tries to access `response.status_code`. The test could raise during its own setup rather than testing the retry behavior, causing a false pass (the `pytest.raises(anthropic.RateLimitError)` block might catch the construction error rather than the retry-exhausted error).

**Fix:** Use `unittest.mock.MagicMock` for the response object:
```python
from unittest.mock import MagicMock
fake_response = MagicMock()
fake_response.status_code = 429
raise anthropic.RateLimitError(
    "Rate limited",
    response=fake_response,
    body={"error": {"type": "rate_limit_error"}},
)
```

---

## Info

### IN-01: `normalize_text` in `extractor.py` is defined but never called in the pipeline

**File:** `pipeline/parser/extractor.py:92-99`
**Issue:** `normalize_text` (which replaces soft hyphens with `--`) is defined but there are no call sites anywhere in the pipeline. The parse command, state machine, and LLM pass all operate on raw `extract_pages` output without invoking this normalization. Soft hyphen corruption (F11 from spike failure taxonomy) will therefore affect production data silently.

**Fix:** Call `normalize_text` on each page string after extraction in `extract_pages`, or at the point of writing utterance text to the DB in `run_parse`. The simplest fix is in `extract_pages`:
```python
pages.append(normalize_text("\n".join(lines)))
```

---

### IN-02: `+page.server.ts` builds FastAPI URL via string interpolation without validating `params.id`

**File:** `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts:6`
**Issue:** `params.id` is a URL path segment from the SvelteKit route. Although FastAPI will reject non-integer values with 422, the fetch call constructs the URL as a raw string: `` `${FASTAPI_BASE_URL}/arguments/${params.id}/utterances` ``. SvelteKit's dynamic route `[id]` can contain arbitrary characters including path traversal sequences (e.g. `../../../etc`). While the FastAPI int coercion mitigates most injection, constructing URLs from unvalidated route params is a pattern that warrants explicit sanitization, especially since `FASTAPI_BASE_URL` is internal.

**Fix:** Validate that `params.id` is a non-negative integer before building the URL:
```typescript
const argumentId = parseInt(params.id, 10);
if (isNaN(argumentId) || argumentId <= 0) {
    throw error(400, 'Invalid argument ID');
}
const res = await fetch(`${FASTAPI_BASE_URL}/arguments/${argumentId}/utterances`);
```

---

### IN-03: `_derive_slug` for consolidated dockets uses the raw docket string in the slug, which contains a hyphen already

**File:** `pipeline/commands/ingest.py:142-143`
**Issue:** Consolidated docket slugs are formed as `f"{base_slug}-{docket}"`, e.g. `"obergefell-v-hodges-14-562"`. The docket `"14-562"` already contains a hyphen, so the slug reads `...-14-562` which is URL-safe. However, this design means the slug encodes the docket number directly. If a future operator reuses the same `--case-name` with a different `--primary-docket` (e.g., a different consolidated case with the same human name), the base slug will collide on the `cases.slug` UNIQUE constraint. This is a latent data integrity issue rather than an immediate crash, but it will surface as an unhandled `IntegrityError` during ingest.

**Fix:** Include the primary docket in the base slug to make it unique per docket group:
```python
base_slug = f"{_derive_slug(args.case_name)}-{args.primary_docket.replace('/', '-')}"
```

---

_Reviewed: 2026-06-11T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
