---
phase: 07-pipeline-runner
reviewed: 2026-06-17T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - alembic/versions/0003_add_admin_jobs.py
  - api/core/config.py
  - api/routers/admin.py
  - api/schemas/admin_jobs.py
  - api/services/admin_jobs.py
  - api/services/pipeline_spawn.py
  - api/services/spaces.py
  - app/src/routes/admin/+layout.svelte
  - app/src/routes/admin/pipeline/+page.server.ts
  - app/src/routes/admin/pipeline/+page.svelte
  - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
  - app/src/routes/admin/pipeline/[job_id]/+page.svelte
  - pipeline/__main__.py
  - pipeline/commands/ingest.py
  - pipeline/commands/parse.py
  - pipeline/commands/resolve.py
  - pipeline/db.py
  - requirements.txt
findings:
  critical: 3
  warning: 7
  info: 3
  total: 13
status: issues_found
---

# Phase 07: Code Review Report (Round 2)

**Reviewed:** 2026-06-17T00:00:00Z
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

This is a second-pass review against the current source files after the round-1 fixes (marked `status: fixed` in the prior review). The round-1 critical issues — platform guard for `WindowsSelectorEventLoopPolicy`, SSRF `.endswith` bypass, and blocking `upload_pdf_to_spaces` without an executor — are all correctly resolved in the current code.

Three new blockers were found. The most impactful is in `pipeline/commands/resolve.py`: HIT rows (auto-resolved aliases) are appended to the `discrepancies` list alongside MISS rows, making the `if not discrepancies` COMPLETED path permanently unreachable. Every job-driven resolve will unconditionally PAUSE — even when every speaker label was auto-resolved. The second blocker is a hardcoded `"ssl": False` in `pipeline/db.py` that will break SSL connections to Digital Ocean's managed PostgreSQL in production (this was noted as IN-03 in the prior review but was not fixed). The third blocker is that the direct CLI resolve path prints all items in `discrepancies` — including HITs — as "unresolved labels", which would mislead operators running the legacy CLI after the resolve.py redesign.

---

## Critical Issues

### CR-01: HIT rows appended to `discrepancies` — COMPLETED path is dead code; every resolve unconditionally PAUSEs

**File:** `pipeline/commands/resolve.py:239-249, 295-326, 346-374`

**Issue:** Both HIT labels (alias found) and MISS labels (no alias) are appended to the `discrepancies` list. The HIT branch at lines 239-249 appends a dict with `"auto_resolved": True`; the MISS branch at lines 265-275 appends one with `"auto_resolved": None`. Because `discrepancies` is always non-empty for any transcript containing utterances, the branching logic at line 295 (`if discrepancies:`) always evaluates `True`. Consequences:

1. **Dead code — line 366:** `if not discrepancies and args.job_id:` (the "mark AdminJob COMPLETED when all labels auto-resolved" block) can never execute for a real transcript.
2. **Dead code — line 321:** `resolve_run.status = PipelineRunStatus.COMPLETED` at line 321 (inside `else:` after `if discrepancies:`) can never be reached for a real transcript.
3. **Incorrect behavior:** Every job-driven resolve — including ones where every alias matched — sets `status=PAUSED` and writes all rows (including confirmed HITs) to `admin_jobs.discrepancies`. The operator is forced to manually review every run in the browser regardless of alias coverage.
4. **Direct CLI also broken:** When `args.job_id` is `None`, the `else:` block at line 307 prints the full `discrepancies` list as "N unresolved label(s):" — see CR-03.

The docstring at line 13 says "If all labels auto-resolved: mark AdminJob COMPLETED." The implementation contradicts this. The fix is to maintain a separate list for misses-only.

**Fix:** Separate the two lists:

```python
discrepancies: list[dict] = []   # MISS rows only — need operator input
# (for HIT rows, resolved_map already tracks the outcome)

# In the HIT branch — remove the discrepancies.append(); instead only update resolved_map:
resolved_map[raw_label] = person_id
# Optionally collect HITs in a separate list for the JSONB record if the UI
# needs to display auto-confirmed labels, but do NOT add them to discrepancies.

# In the MISS branch — append to discrepancies as before.

# Step 6 branching is now semantically correct:
if discrepancies:
    # Some labels unresolved — PAUSED for operator review
    resolve_run.status = PipelineRunStatus.NEEDS_REVIEW
    ...
else:
    # All labels auto-resolved — COMPLETED
    resolve_run.status = PipelineRunStatus.COMPLETED
    ...
```

If the UI design requires operators to confirm auto-matches before the job advances (a valid design choice), the condition for PAUSED vs. COMPLETED should be `any(not d.get("auto_resolved") for d in discrepancies)`, not `bool(discrepancies)`.

---

### CR-02: `"ssl": False` hardcoded in pipeline engine — breaks production SSL connections

**File:** `pipeline/db.py:49`

**Issue:** `connect_args={"statement_cache_size": 0, "ssl": False}` unconditionally disables TLS for every asyncpg connection made by any pipeline subprocess. Digital Ocean managed PostgreSQL requires SSL; without it, connections will be refused. The FastAPI engine (`api/core/database.py:38`) does not have this flag — only the pipeline is affected. This means every pipeline step (ingest, parse, resolve) will fail to connect to the database in production.

This was flagged as IN-03 in the prior review and was not fixed.

**Fix:** Remove `"ssl": False` or make it conditional on a local-dev environment variable:

```python
connect_args: dict = {"statement_cache_size": 0}
# Only disable SSL for local development. DO managed PostgreSQL requires SSL.
if os.environ.get("DB_SSL_DISABLE", "").lower() in ("1", "true"):
    connect_args["ssl"] = False

_engine = create_async_engine(
    database_url,
    connect_args=connect_args,
    pool_size=2,
    echo=False,
)
```

---

### CR-03: Direct CLI resolve prints HIT rows as "unresolved labels"

**File:** `pipeline/commands/resolve.py:307-317`

**Issue:** This is the direct CLI manifestation of the same bug as CR-01. When `args.job_id is None` (legacy direct CLI use) and `discrepancies` is non-empty — which it always is for any transcript — the code at line 307-317 prints the full list under the header "N unresolved label(s):" and sets `resolve_run.status = NEEDS_REVIEW`. Since HITs are in the list, every successful resolve prints every speaker label as if it needs remediation, and the PipelineRun row is set to `NEEDS_REVIEW` instead of `COMPLETED`.

An operator running `python -m pipeline resolve --run-id X` on a fully-seeded transcript would see all Justice names reported as "unresolved" and conclude the run failed, even though all utterances were correctly resolved.

**Fix:** After applying the CR-01 fix (separate `discrepancies` from HIT tracking), the direct CLI print block will only iterate over genuine misses:

```python
if discrepancies:   # now only contains MISSes
    print(f"\n{len(discrepancies)} unresolved label(s):")
    for d in discrepancies:
        print(f"  - {d['raw_speaker_label']!r} (normalized: {d['normalized']!r})")
    print("Resolve run status set to needs_review. Seed aliases for these labels and re-run.")
```

---

## Warnings

### WR-01: `asyncio.get_event_loop()` is deprecated in Python 3.10+ — should be `get_running_loop()`

**File:** `api/routers/admin.py:148`

**Issue:** The round-1 fix correctly moved the `upload_pdf_to_spaces` call into `run_in_executor`, but the event loop is obtained via the deprecated `asyncio.get_event_loop()`. Inside a FastAPI async route handler there is always a running event loop; the correct call is `asyncio.get_running_loop()`. In Python 3.10+, calling `get_event_loop()` when there is no current event loop emits a `DeprecationWarning`; in Python 3.12+ it can raise `RuntimeError` under some configurations.

**Fix:**
```python
# Line 148 — replace:
loop = asyncio.get_event_loop()
# with:
loop = asyncio.get_running_loop()
```

---

### WR-02: `stepStatus` returns `'pending'` for all steps when `current_step` is null and `status` is `'failed'`

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:130-144`

**Issue:** When a job fails before any step sets `current_step` (e.g., the spawned ingest subprocess fails before executing Step 0), `job.current_step` is `null`. This makes `current` equal to `undefined` and `currentIdx` equal to `-1`. The conditions at lines 136-138:

```typescript
if (job.status === 'failed' && step === current) return 'failed';  // undefined !== any step
if (job.status === 'failed' && thisIdx < currentIdx) return 'completed';  // N < -1 is always false
if (job.status === 'failed' && thisIdx > currentIdx) return 'pending';    // 0 > -1 → true for all
```

The third condition matches for every step, returning `'pending'`. All three step cards show as "Pending" for a failed job. The operator sees no indication that the job failed or which step was active at failure.

**Fix:**
```typescript
function stepStatus(step: StepName, job: Job): string {
    const current = job.current_step?.toLowerCase() as StepName | undefined;
    const currentIdx = current !== undefined ? STEP_ORDER.indexOf(current) : -1;
    const thisIdx = STEP_ORDER.indexOf(step);

    if (job.status === 'completed') return 'completed';
    if (job.status === 'failed') {
        // If failed before any step ran, mark the first step as failed
        if (currentIdx === -1) return step === STEP_ORDER[0] ? 'failed' : 'pending';
        if (step === current) return 'failed';
        if (thisIdx < currentIdx) return 'completed';
        return 'pending';
    }
    if (job.status === 'paused' && step === 'resolve') return 'paused';
    if (job.status === 'paused' && thisIdx < currentIdx) return 'completed';
    if (job.status === 'paused' && thisIdx > currentIdx) return 'pending';
    if (thisIdx < currentIdx) return 'completed';
    if (thisIdx === currentIdx) return job.status === 'running' ? 'running' : 'pending';
    return 'pending';
}
```

---

### WR-03: `upload_pdf_to_spaces` has no guard against empty credentials — boto3 error is cryptic

**File:** `api/services/spaces.py:37-50`

**Issue:** When DO Spaces credentials are not configured (`do_spaces_bucket`, `do_spaces_endpoint`, or `aws_access_key_id` are empty strings — their defaults), `client.upload_fileobj(bytes, "", key)` either throws a confusing `ParamValidationError("Invalid bucket name ''")` or attempts to connect to AWS S3 with empty credentials. Neither error gives the operator an actionable message. The URL-only mode intentionally leaves these fields empty, but the upload path (PIPE-13) requires them.

**Fix:** Guard at the entry point of `upload_pdf_to_spaces`:

```python
def upload_pdf_to_spaces(file_bytes: bytes, key: str) -> str:
    if not settings.do_spaces_bucket or not settings.do_spaces_endpoint:
        raise RuntimeError(
            "DO Spaces credentials are not configured. "
            "Set DO_SPACES_BUCKET, DO_SPACES_ENDPOINT, AWS_ACCESS_KEY_ID, "
            "and AWS_SECRET_ACCESS_KEY in the FastAPI service environment."
        )
    client = get_spaces_client()
    client.upload_fileobj(
        io.BytesIO(file_bytes),
        settings.do_spaces_bucket,
        key,
        ExtraArgs={"ContentType": "application/pdf"},
    )
    return key
```

---

### WR-04: `resolve_job` issues a redundant DB query via `get_run_id_for_step`

**File:** `api/services/admin_jobs.py:195-211`

**Issue:** `resolve_job` calls `get_job(db, job_id)` at line 195 to load the job, then calls `get_run_id_for_step(db, job_id, "parse")` at line 211. `get_run_id_for_step` internally calls `get_job(db, job_id)` again at line 158 to read `job.argument_id`. This produces two `SELECT * FROM admin_jobs WHERE id = ?` round-trips when one is sufficient.

**Fix:** Inline the argument_id lookup directly using the already-loaded `job`:

```python
# After loading job at line 195, replace the get_run_id_for_step call:
if job.argument_id is not None:
    result = await db.execute(
        select(PipelineRun.id)
        .where(PipelineRun.argument_id == job.argument_id, PipelineRun.step == "parse")
        .order_by(PipelineRun.created_at.desc())
        .limit(1)
    )
    parse_run_id = result.scalar_one_or_none()
else:
    parse_run_id = None
```

---

### WR-05: `create_person_for_job` accepts `job_id` but never validates the job exists or is in PAUSED state

**File:** `api/services/admin_jobs.py:284-315`

**Issue:** The `job_id` parameter is accepted but not used — no check that the job exists or is in the correct state before creating a Person row. A caller can POST to `/api/admin/jobs/999999/people` with a non-existent job ID and a new `Person` record will be created in the database with no job association. In a multi-user admin scenario this creates orphaned person records.

**Fix:**
```python
async def create_person_for_job(db: AsyncSession, job_id: int, body: PersonCreate) -> Person:
    job = await get_job(db, job_id)
    if job is None:
        raise ValueError(f"AdminJob {job_id} not found")
    if job.status != AdminJobStatus.PAUSED:
        raise ValueError(
            f"AdminJob {job_id} is not in PAUSED state "
            f"(current status: {job.status.value}); cannot add person inline."
        )
    # ... rest of the function unchanged
```

The router should then map this `ValueError` to HTTP 422:
```python
try:
    person = await jobs_service.create_person_for_job(db, job_id, body)
except ValueError as exc:
    raise HTTPException(status_code=422, detail=str(exc)) from exc
```

---

### WR-06: `pdf_file.content_type` is client-supplied — magic-byte check would be more reliable

**File:** `api/routers/admin.py:139`

**Issue:** `pdf_file.content_type` is the `Content-Type` field from the multipart form submission, which the HTTP client sets. A client can send `content_type="application/pdf"` while uploading an arbitrary file (executable, HTML, etc.). The check is therefore a weak client-side assertion, not a server-side validation. For an operator-only admin tool the practical risk is low, but T-07-04 calls this out as a security requirement and the current check does not meet it.

**Fix:** Read the first four bytes and check for the PDF magic number:
```python
header = await pdf_file.read(4)
await pdf_file.seek(0)
if header != b'%PDF':
    raise HTTPException(status_code=422, detail="Uploaded file must be a PDF.")
file_bytes = await pdf_file.read()
```
(`UploadFile.seek()` is available in Starlette/FastAPI 0.100+.)

---

### WR-07: `async_sessionmaker` recreated on every `get_session()` call in `pipeline/db.py`

**File:** `pipeline/db.py:71`

**Issue:** `async_sessionmaker(engine, expire_on_commit=False)` is called inside `get_session()` each time it is invoked. The `get_engine()` singleton comment explains the engine is shared to avoid new connection pools — but the factory is not. While creating a `async_sessionmaker` is inexpensive, it is inconsistent with the stated design intent and misleads future readers about ownership of the pool.

**Fix:** Cache the factory alongside the engine:
```python
_engine = None
_session_factory = None

def get_engine():
    global _engine, _session_factory
    if _engine is None:
        database_url = os.environ["DATABASE_URL"]
        _engine = create_async_engine(...)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    get_engine()  # ensure factory is initialised
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

---

## Info

### IN-01: Multiple `# type: ignore[return-value]` suppressions mask service/schema return-type mismatch

**File:** `api/routers/admin.py:135, 165, 179, 233, 253, 270`

**Issue:** Six return sites suppress `return-value` mypy errors because service functions return `AdminJob` (ORM model) but router return types are declared as `AdminJobResponse` (Pydantic schema). FastAPI coerces the ORM object via `from_attributes=True` at serialization time so there is no runtime error — but the type ignores mask a real static type mismatch and will confuse future readers.

**Fix:** Either annotate service functions to return `AdminJobResponse` directly, or accept the `AdminJob` return type in the router with an explicit conversion hint. The cleanest path is to remove the ignores and let FastAPI's coercion be the documented behavior:
```python
# Remove: # type: ignore[return-value]
# FastAPI coerces AdminJob -> AdminJobResponse via response_model + from_attributes=True
return job
```

---

### IN-02: `if args.job_id:` truthy check silently skips DB writes if `job_id=0`

**Files:** `pipeline/commands/ingest.py:196, 219, 388`, `pipeline/commands/parse.py:80, 103, 264`, `pipeline/commands/resolve.py:89, 112, 301, 346, 366`

**Issue:** All job-driven guard branches use `if args.job_id:` (truthy check on `int | None`). If `job_id=0` were passed (not a valid PostgreSQL serial PK, but possible in unit tests with mocked IDs), all DB status writes would be silently skipped without error. The correct guard for "was this argument provided" is `if args.job_id is not None:`.

**Fix:** Replace all 9 occurrences of `if args.job_id:` with `if args.job_id is not None:` across `ingest.py`, `parse.py`, and `resolve.py`.

---

### IN-03: Stale planning-phase note in parse subparser `description`

**File:** `pipeline/__main__.py:111-113`

**Issue:** The parse subparser's `description` string still reads "(stub in Plan 03 — fully implemented in Plan 04)". This planning artifact is user-visible via `python -m pipeline parse --help`.

**Fix:**
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

_Reviewed: 2026-06-17T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
