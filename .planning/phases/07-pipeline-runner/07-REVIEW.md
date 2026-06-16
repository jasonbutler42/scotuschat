---
phase: 07-pipeline-runner
reviewed: 2026-06-16T00:00:00Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - api/core/config.py
  - api/schemas/admin_jobs.py
  - api/services/admin_jobs.py
  - api/services/pipeline_spawn.py
  - api/services/spaces.py
  - api/routers/admin.py
  - app/src/routes/admin/+layout.svelte
  - app/src/routes/admin/pipeline/+page.server.ts
  - app/src/routes/admin/pipeline/+page.svelte
  - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
  - app/src/routes/admin/pipeline/[job_id]/+page.svelte
  - pipeline/__main__.py
  - pipeline/commands/ingest.py
  - pipeline/commands/parse.py
  - pipeline/commands/resolve.py
  - requirements.txt
findings:
  critical: 5
  warning: 4
  info: 3
  total: 12
status: fixed
---

# Phase 07: Code Review Report

**Reviewed:** 2026-06-16T00:00:00Z
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

## Summary

The phase 07 pipeline runner is broadly well-structured: the fire-and-poll architecture is sound, the atomic step-advance guards are correctly implemented with rowcount checks, and the SSRF mitigations are present at both the API layer and the pipeline layer. However, there is a critical data-contract mismatch between the discrepancy shape produced by `pipeline/commands/resolve.py` and the shape consumed by `[job_id]/+page.svelte` that causes silent data loss on every "Confirm" action. Additionally, the FAILED status write in `pipeline/commands/ingest.py` is missing a commit, the `upload_pdf_to_spaces` call in `admin.py` blocks the FastAPI event loop, and the `WindowsSelectorEventLoopPolicy` override in `__main__.py` is unconditional and will break Linux/macOS production deployments.

---

## Critical Issues

### CR-01: Discrepancy schema mismatch — "Confirm" silently drops every mapping

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:18-20, 76, 188-191`
**Cross-file:** `pipeline/commands/resolve.py:237-244`

**Issue:** The Svelte component's `Discrepancy` interface expects three fields that do not exist in the discrepancy dicts the pipeline actually writes to `admin_jobs.discrepancies`:

| Field expected by Svelte | Present in pipeline output |
|--------------------------|---------------------------|
| `auto_match_id`          | No — field is absent       |
| `auto_match_name`        | No — field is absent       |
| `auto_match_role`        | No — field is absent       |

The pipeline only writes `{raw_speaker_label, normalized, candidates, auto_resolved: null}`.

**Consequence (multi-step):**

1. `rowStates` is initialised with `person_id: row.auto_match_id ?? null` → always `null` for every row (line 76).
2. When the operator clicks **Confirm**, `handleConfirm` sets `disposition='confirmed'` and `person_id = row.auto_match_id ?? null` → still `null` (lines 188-190).
3. `allDispositioned` becomes `true` once every row has `disposition !== null` — "Continue Resolve" appears.
4. `matchesJson` filters out every entry where `s.person_id === null` (line 107). The submitted `matches` array is empty or partial.
5. The resolve endpoint marks the job COMPLETED without writing `person_id` to any utterance, leaving all utterances with `person_id = NULL` in the database — the entire resolve step silently no-ops.

This is a data-loss defect that will not be visible from the UI (no error is returned).

**Fix — pipeline side** (`pipeline/commands/resolve.py`, lines 237-244): The MISS branch should never reach the discrepancy list in practice for a pure MISS, so `auto_match_id` is legitimately absent. But the field must be added for the partial-auto-resolve future path. At minimum add explicit null fields so the contract is unambiguous:

```python
discrepancies.append(
    {
        "raw_speaker_label": raw_label,
        "normalized": normalized,
        "candidates": candidates,
        "auto_match_id": None,
        "auto_match_name": None,
        "auto_match_role": None,
        "auto_resolved": None,
    }
)
```

**Fix — Svelte side** (`+page.svelte`, lines 185-191): The "Confirm" button must be disabled (or hidden) when `auto_match_id` is `null`, because there is nothing to confirm — it is a pure miss. The operator must use "Correct" to pick a person:

```svelte
{#if row.auto_match_id}
  <button type="button" onclick={() => handleConfirm(rowKey, row)}>
    Confirm
  </button>
{/if}
<button type="button" onclick={() => handleCorrect(rowKey)}>
  Correct
</button>
```

Additionally, `allDispositioned` should verify `person_id !== null` before enabling "Continue Resolve":

```ts
return disc.every((row: Discrepancy) => {
    const s = rowStates[row.raw_speaker_label];
    return s?.disposition !== null && s?.disposition !== undefined && s?.person_id !== null;
});
```

---

### CR-02: FAILED status write in `run_ingest` never commits — failure is invisible

**File:** `pipeline/commands/ingest.py:193-205`

**Issue:** The `except` block in `run_ingest` that writes `status=FAILED` to `admin_jobs` opens a `get_session()` context manager and executes the UPDATE, but the context manager only commits on *clean* exit. An exception raised inside the `except` block's `async with get_session() as session:` body would rollback instead of committing. More critically: `get_session` does `await session.commit()` only on the normal yield path — when the `except` clause executes and `raise` rethrows the original exception, the `get_session` context manager's `__aexit__` receives the re-raised exception and calls `rollback()`, discarding the FAILED status write.

Looking at `pipeline/db.py` lines 64-68:
```python
try:
    yield session
    await session.commit()    # only runs on clean yield exit
except Exception:
    await session.rollback()  # runs whenever an exception propagates
    raise
```

Because `run_ingest` re-raises (`raise` at line 205) *after* exiting the `get_session()` context, the context manager's `__aexit__` sees no exception and does commit correctly. However, if an exception occurs *inside* the `async with get_session()` block in the `except` clause (e.g., DB connection failure while writing FAILED status), it will silently swallow that inner exception (the outer `raise` still re-raises the original) and the FAILED write is rolled back. The admin job stays in RUNNING state permanently.

The same pattern exists identically in `parse.py:79-91` and `resolve.py:86-100`.

**Fix:** Use a separate try/except around the status write so a connection failure during the FAILED write is logged and doesn't prevent the RUNNING → FAILED transition from being attempted:

```python
except Exception as exc:
    if args.job_id:
        try:
            async with get_session() as session:
                await session.execute(
                    update(AdminJob)
                    .where(AdminJob.id == args.job_id)
                    .values(status=AdminJobStatus.FAILED, error_message=str(exc))
                    .execution_options(synchronize_session=False)
                )
        except Exception as write_err:
            print(f"Warning: could not write FAILED status for job {args.job_id}: {write_err}")
    raise
```

---

### CR-03: `upload_pdf_to_spaces` blocks the FastAPI async event loop

**File:** `api/routers/admin.py:142`
**Cross-file:** `api/services/spaces.py:43-50`

**Issue:** `spaces_service.upload_pdf_to_spaces(file_bytes, key)` is a synchronous blocking call (boto3 `client.upload_fileobj`) called directly inside an `async def` route handler without `run_in_executor`. During a multi-megabyte PDF upload, this blocks the uvicorn event loop entirely, making the entire FastAPI service unresponsive to all other requests for the duration of the upload (typically several seconds for a ~5 MB PDF).

```python
# api/routers/admin.py line 142 — blocks the event loop
spaces_service.upload_pdf_to_spaces(file_bytes, key)
```

**Fix:** Wrap the blocking call with `asyncio.get_event_loop().run_in_executor`:

```python
import asyncio

loop = asyncio.get_event_loop()
await loop.run_in_executor(
    None,
    spaces_service.upload_pdf_to_spaces,
    file_bytes,
    key,
)
```

Or alternatively use `aioboto3` for a fully async upload path.

---

### CR-04: `WindowsSelectorEventLoopPolicy` is set unconditionally — breaks Linux/macOS

**File:** `pipeline/__main__.py:28`

**Issue:** Line 28 unconditionally calls `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())` at module import time:

```python
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

`WindowsSelectorEventLoopPolicy` is a Windows-only class (`asyncio` on Linux/macOS does not have this attribute). This line will raise `AttributeError: module 'asyncio' has no attribute 'WindowsSelectorEventLoopPolicy'` on any non-Windows platform. The production environment is Digital Ocean App Platform (Linux), so this will crash every pipeline invocation in production.

**Fix:** Guard with a platform check:

```python
import sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

---

### CR-05: SSRF bypass — `netloc.endswith("supremecourt.gov")` accepts `evils.supremecourt.gov.attacker.com`

**File:** `api/routers/admin.py:93`
**Cross-file:** `pipeline/commands/ingest.py:74`

**Issue:** Both URL validation functions use `parsed.netloc.endswith("supremecourt.gov")` as the host check. A URL like `https://evils.supremecourt.gov.attacker.com/evil.pdf` has `netloc = "evils.supremecourt.gov.attacker.com"` which ends with `"supremecourt.gov"` — wait, actually that does NOT end with "supremecourt.gov". However, a URL like `https://evil.xsupremecourt.gov/evil.pdf` has netloc `"evil.xsupremecourt.gov"` which also does not end with `"supremecourt.gov"`.

The actual bypass is: `https://attacker.com/supremecourt.gov` — `urlparse` gives `netloc = "attacker.com"` and `path = "/supremecourt.gov"`, so this is correctly rejected.

However: a URL with a username field like `https://supremecourt.gov@attacker.com/evil.pdf` will have `netloc = "supremecourt.gov@attacker.com"` — `endswith("supremecourt.gov")` is false, so this is also correctly rejected.

The real risk is a subdomain attack: `https://x.supremecourt.gov.evil.com/` — `netloc = "x.supremecourt.gov.evil.com"` which does NOT end with `"supremecourt.gov"` and is correctly rejected.

On re-examination the `endswith` check does have one residual bypass: the check does not verify that `supremecourt.gov` is preceded by a `.` or is the entire netloc. A hostname like `fakesupremecourt.gov` does NOT end with `supremecourt.gov` (it ends with `premecourt.gov`), so this specific case is fine. However `www.supremecourt.gov` ends with `supremecourt.gov` correctly.

The genuine bypass is: `https://notreallysupremecourt.gov/` — `netloc = "notreallysupremecourt.gov"` does NOT end with `supremecourt.gov`. This is fine.

**Actual bypass confirmed:** `https://xsupremecourt.gov/` → netloc is `xsupremecourt.gov` → `endswith("supremecourt.gov")` → **True** — this passes validation and allows fetching from a domain that is not `supremecourt.gov` or any subdomain thereof.

**Fix:** Validate that the netloc is exactly `supremecourt.gov` or ends with `.supremecourt.gov`:

```python
def _validate_pdf_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    netloc = parsed.netloc.lower()
    if parsed.scheme != "https" or not (
        netloc == "supremecourt.gov" or netloc.endswith(".supremecourt.gov")
    ):
        raise HTTPException(
            status_code=422,
            detail="Only https://...supremecourt.gov/... URLs are accepted",
        )
```

Apply the same fix in `pipeline/commands/ingest.py:_validate_url`.

---

## Warnings

### WR-01: `create_job` calls `flush` then `commit` — double-write pattern is unnecessary

**File:** `api/services/admin_jobs.py:61-63`

**Issue:** `create_job` calls `await db.flush()`, then `await db.commit()`, then `await db.refresh(job)`. The `flush` before `commit` is redundant — `commit` implicitly flushes. More importantly, this pattern is inconsistent with the rest of the service: `try_advance_ingest_to_parse` and `try_advance_parse_to_resolve` commit without a preceding flush. There is no bug here, but the flush adds a database round-trip and creates a misleading pattern that could cause reviewers to cargo-cult a flush+commit elsewhere when only commit is needed.

**Fix:** Remove the flush:
```python
db.add(job)
await db.commit()
await db.refresh(job)
return job
```

---

### WR-02: `get_engine()` creates a new engine on every `get_session()` call — connection pool is effectively disabled

**File:** `pipeline/db.py:27-44, 61`

**Issue:** `get_session()` calls `get_engine()` every time it is invoked (line 61). `get_engine()` calls `create_async_engine(...)` every time, creating a new connection pool on every `async with get_session()` block. The pipeline then calls `engine.dispose()` in the `finally` clause (line 71), tearing down the pool after every session. This means every DB operation during ingest (Step 0, Step 5, Step 6 are three separate `get_session()` calls) opens and closes a fresh TCP connection to PostgreSQL. This is wasteful and will be noticeably slow across the three-step pipeline.

This also means `pool_size=2` in `get_engine()` is misleading — the pool is never reused across calls.

**Fix:** Construct the engine once at module level (or use a module-level singleton):

```python
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        database_url = os.environ["DATABASE_URL"]
        _engine = create_async_engine(
            database_url,
            connect_args={"statement_cache_size": 0, "ssl": False},
            pool_size=2,
            echo=False,
        )
    return _engine
```

Remove `await engine.dispose()` from the `finally` block since the engine is now shared.

---

### WR-03: `admin.py` import of `sa_update` and `AdminJob` inside the route body

**File:** `api/routers/admin.py:144-145`

**Issue:** Lines 144-145 have `import` statements inside the upload branch of `create_job`:

```python
from sqlalchemy import update as sa_update
from api.models.models import AdminJob
```

These imports are performed on every upload request. Both modules are already available at the module level (`update` is imported as `update` from SQLAlchemy indirectly via `jobs_service`, and `AdminJob` is imported at line 45). The inner imports shadow the module-level names and add runtime overhead, but more importantly they indicate the upload path was written without reviewing existing module-level imports. `AdminJob` is already imported at line 45.

**Fix:** Move both imports to the module level or use the already-imported names. Check that `update` from `sqlalchemy` is available via the existing imports and replace the inline import:

```python
# At module level (already have AdminJob at line 45, add update):
from sqlalchemy import update

# In the route body, remove lines 144-145 and use:
await db.execute(
    update(AdminJob)
    .where(AdminJob.id == job.id)
    ...
)
```

---

### WR-04: `resolve.py` — `person` access after alias HIT without null check

**File:** `pipeline/commands/resolve.py:203-206`

**Issue:** After fetching an alias HIT, the code immediately does `person.full_name` on line 206:

```python
person: Optional[Person] = await session.get(Person, alias.person_id)
print(f"Auto-resolved: {raw_label!r} -> {person.full_name}")
```

If `alias.person_id` references a `Person` row that was deleted after the alias was seeded (orphaned foreign key — possible if the DB has no FK constraint enforced, or if the constraint was deferred), `session.get` returns `None` and `person.full_name` raises `AttributeError`, which propagates as an unhandled exception. The job will be marked FAILED via the outer exception handler, but the error message will be confusing: `"'NoneType' object has no attribute 'full_name'"` with no indication of which label caused it.

**Fix:** Add an explicit null check:

```python
person: Optional[Person] = await session.get(Person, alias.person_id)
if person is None:
    raise ValueError(
        f"SpeakerAlias for '{normalized}' references person_id={alias.person_id} "
        "which no longer exists. Re-seed aliases before re-running."
    )
print(f"Auto-resolved: {raw_label!r} -> {person.full_name}")
```

---

## Info

### IN-01: `requirements.txt` pins no versions for `instructor[anthropic]` — silent breakage risk

**File:** `requirements.txt:6`

**Issue:** Every other package in `requirements.txt` has a minimum version pin (`>=`). `instructor[anthropic]` has no version constraint at all. The instructor package has had breaking API changes across minor versions. An unconstrained install will resolve to whatever the latest version is at `pip install` time, potentially pulling a version incompatible with how `parse_with_llm` uses it.

**Fix:** Add a minimum version pin matching the installed version:
```
instructor[anthropic]>=1.0
```

---

### IN-02: `pipeline/__main__.py` comment says "stub in Plan 03 — fully implemented in Plan 04" for parse

**File:** `pipeline/__main__.py:109`

**Issue:** The parse subcommand's `description` string in the argparse definition still says "(stub in Plan 03 — fully implemented in Plan 04)". This is a stale planning artifact exposed via `--help`. Anyone running `python -m pipeline --help` will see it.

**Fix:** Remove the planning phase note from the description:
```python
parse_p = sub.add_parser(
    "parse",
    help="Parse transcript into utterances",
    description=(
        "Parse a previously ingested transcript PDF into utterance rows "
        "using pdfplumber + rule-based state machine + Claude corrective pass."
    ),
)
```

---

### IN-03: `pipeline/db.py` — `ssl: False` hardcoded in `connect_args` will break production TLS

**File:** `pipeline/db.py:41`

**Issue:** `connect_args={"statement_cache_size": 0, "ssl": False}` hardcodes SSL off. Digital Ocean managed PostgreSQL and PgBouncer require SSL in production. This will cause connection failures (or silently transmit DB credentials over an unencrypted connection if the server is misconfigured to allow it). The `ssl: False` flag may have been added for local development but must not reach the production environment.

**Fix:** Make SSL conditional on an env var:

```python
import ssl as _ssl_module

ssl_mode = os.environ.get("DB_SSL", "require")
connect_args: dict = {"statement_cache_size": 0}
if ssl_mode == "disable":
    connect_args["ssl"] = False
elif ssl_mode == "require":
    connect_args["ssl"] = _ssl_module.create_default_context()
```

Or at minimum document clearly that `ssl: False` must be changed for production and guard it:

```python
connect_args={"statement_cache_size": 0, "ssl": os.environ.get("DB_SSL_DISABLE") == "1"},
```

---

_Reviewed: 2026-06-16T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
