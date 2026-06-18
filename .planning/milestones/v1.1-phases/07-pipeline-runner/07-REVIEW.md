---
phase: 07-pipeline-runner
reviewed: 2026-06-17T15:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - alembic/versions/0004_add_arguments_resolved_at.py
  - api/core/config.py
  - api/models/models.py
  - api/routers/admin.py
  - api/schemas/admin_jobs.py
  - api/services/admin_jobs.py
  - api/services/cases.py
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
findings:
  critical: 5
  warning: 8
  info: 4
  total: 17
status: issues_found
---

# Phase 07: Code Review Report (Full Scope)

**Reviewed:** 2026-06-17T15:00:00Z
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

This review covers all 18 files in the Phase 7 pipeline-runner implementation — 10 files not
covered in the prior round-3 review plus the 8 files reviewed in that round. Prior-round findings
that remain unresolved are carried forward with their original IDs.

Five critical issues were found. The most impactful (CR-01, carried from round 3) is that
`pipeline/commands/resolve.py` appends HIT rows alongside MISS rows into the `discrepancies`
list, making the "all labels auto-resolved → COMPLETED" path permanently dead code for any
transcript with utterances. A second critical (CR-02, carried) is that `resolve_job` in
`admin_jobs.py` does not guard against being called on a non-PAUSED job — a double-submit or
stale-browser POST will re-apply alias writes and overwrite `resolved_at`. CR-03 and CR-04
(carried) are frontend bugs: `continueSubmitting` is never reset on success, and `rowStates`
never evicts stale keys. A new critical (CR-05) was found in `pipeline/commands/parse.py`:
when `--dry-run` is set, the code returns early inside the `async with get_session()` block
after setting `run.status = PENDING`, which commits a live PipelineRun row with status=PENDING
and strategy=None to the database — contradicting the docstring claim that dry-run "does not
write to DB".

Four files are clean: `api/core/config.py`, `api/schemas/admin_jobs.py`,
`api/services/cases.py`, `app/src/routes/admin/+layout.svelte`.

---

## Critical Issues

### CR-01: HIT rows appended to `discrepancies` — COMPLETED path is dead code

**File:** `pipeline/commands/resolve.py:243–253, 299–326, 350–386`

**Issue:** Both HIT labels (alias found, lines 243–253) and MISS labels (no alias, lines
269–279) are appended to the `discrepancies` list. Because HITs are included, `discrepancies`
is non-empty for any transcript that has utterances. The branch at line 299
(`if discrepancies:`) therefore always fires, which sets
`resolve_run.status = PipelineRunStatus.NEEDS_REVIEW` and — in job-driven mode — writes all
rows to `admin_jobs.discrepancies` and sets `status=PAUSED`.

Consequences:

1. **Dead code (line 371):** `if not discrepancies and args.job_id:` — the block that marks the
   `AdminJob` COMPLETED and stamps `arguments.resolved_at` — can never execute for a real
   transcript. Cases are permanently invisible in `/cases/` even after full auto-resolve.

2. **Dead code (line 325):** `resolve_run.status = PipelineRunStatus.COMPLETED` is never
   reached for a real transcript.

3. **Incorrect behavior:** Every job-driven resolve — including runs where every alias matched —
   unconditionally PAUSEs the job and forces an unnecessary browser confirmation round-trip.

4. **Direct CLI mode (lines 307–321):** The MISS-only print block iterates the entire
   `discrepancies` list including HITs and reports them all as "unresolved labels".

**Fix:** Maintain a separate `misses` list for MISS labels and key the branching gate on it,
while still writing the full `discrepancies` list (HITs + MISSes) to the JSONB column so the
browser can show auto-resolved labels for confirmation:

```python
discrepancies: list[dict] = []   # ALL rows for browser UI (HITs + MISSes)
misses: list[str] = []           # raw labels with no alias — gate for PAUSED vs COMPLETED

# HIT branch — append to discrepancies only:
discrepancies.append({..., "auto_resolved": True})

# MISS branch — append to both:
misses.append(raw_label)
discrepancies.append({..., "auto_resolved": None})

# Step 6 gate — keyed on misses, not discrepancies:
if misses:
    resolve_run.status = PipelineRunStatus.NEEDS_REVIEW
    ...
    if args.job_id:
        # write full discrepancies JSONB (HITs + MISSes)
        ...
    else:
        for label in misses:   # CLI: print only MISSes
            print(f"  - {label!r}")
else:
    resolve_run.status = PipelineRunStatus.COMPLETED
    ...
```

Also update the post-session block (lines 350–386) to gate on `misses` rather than
`discrepancies`, and on the COMPLETED path (lines 371–386) write `discrepancies` to
`admin_jobs` for the browser to show the confirmed auto-matches.

---

### CR-02: `resolve_job` does not verify PAUSED state before writing aliases

**File:** `api/services/admin_jobs.py:182–287`

**Issue:** `resolve_job` validates that the job exists (line 199) and that all `person_id`s
are valid (lines 201–210), but does not check that `job.status == AdminJobStatus.PAUSED` before
writing `SpeakerAlias` rows, updating `Utterance.person_id`, updating
`ArgumentParticipant.person_id`, and stamping `arguments.resolved_at`.

Two concrete failure modes:

1. **Double-submit:** An operator double-clicks "Continue Resolve." The first POST marks the job
   COMPLETED. The second POST re-applies all alias writes and overwrites `resolved_at` with a
   new timestamp (non-idempotent).

2. **Wrong-state call:** A POST to `/api/admin/jobs/{id}/resolve` on a FAILED or COMPLETED job
   executes all alias writes and the `resolved_at` stamp unconditionally.

**Fix:** Add a state check immediately after loading the job:

```python
if job.status != AdminJobStatus.PAUSED:
    raise ValueError(
        f"AdminJob {job_id} is not PAUSED (current status: {job.status.value!r}); "
        "resolve can only be applied to a paused job."
    )
```

The router at `admin.py:249–252` already catches `ValueError` and re-raises as HTTP 422, so no
router changes are required.

---

### CR-03: `continueSubmitting` is never reset on successful resolve submit

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:660–672`

**Issue:** The `use:enhance` callback for the "Continue Resolve" form sets
`continueSubmitting = true` on submit (line 661). On failure it resets to `false` (line 664).
On success it calls `await update({ reset: false })` but never resets `continueSubmitting`.
The button stays disabled and reads "Submitting…" indefinitely if the server-side state
transition has not occurred before the next render cycle. The expected recovery is that
`invalidateAll` (called by `update()`) re-fetches the job and changes `data.job.status` from
`'paused'` to `'running'`, hiding the form block. This race is narrow but real.

**Fix:** Reset `continueSubmitting` in the success branch before calling `update`:

```typescript
return async ({ result, update }) => {
    if (result.type === 'failure') {
        continueSubmitting = false;
        await update();
    } else {
        continueSubmitting = false;   // reset before update so re-render sees correct state
        await update({ reset: false });
    }
};
```

---

### CR-04: `rowStates` never evicts stale keys — operator can submit outdated mappings

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:74–93`

**Issue:** The `$effect` that initialises `rowStates` skips any `raw_speaker_label` already
present in `rowStates` (line 77: `if (!(row.raw_speaker_label in rowStates))`). This is correct
to preserve in-progress dispositions during polling. However, if the server returns a different
discrepancy set — for example after the operator navigated away, the job was retried, or a new
resolve run was spawned — `rowStates` retains entries for labels that no longer exist in the
new set. The `matchesJson` builder (line 108) iterates `data.job.discrepancies` so it excludes
stale keys from the submitted payload, but `allDispositioned` also iterates
`data.job.discrepancies` — meaning new labels added by a retry may arrive undispositioned while
stale `rowStates` keys linger silently.

There is no epoch/version guard so the client cannot distinguish state from a prior resolve
attempt.

**Fix:** Evict stale keys when the server returns a new discrepancy set:

```typescript
$effect(() => {
    const disc = data.job.discrepancies;
    if (!disc) return;
    const incomingKeys = new Set(disc.map(r => r.raw_speaker_label));
    for (const key of Object.keys(rowStates)) {
        if (!incomingKeys.has(key)) {
            delete rowStates[key];
        }
    }
    for (const row of disc) {
        if (!(row.raw_speaker_label in rowStates)) {
            const isHit = row.auto_resolved === true;
            rowStates[row.raw_speaker_label] = {
                person_id: row.auto_match_id ?? null,
                disposition: isHit ? 'confirmed' : null,
                correcting: false,
                addingPerson: false,
                extraCandidates: [],
                submittingNewPerson: false,
                newPersonName: '',
                newPersonRole: '',
                newPersonError: null,
            };
        }
    }
});
```

---

### CR-05: `--dry-run` early return inside session block persists a PipelineRun row

**File:** `pipeline/commands/parse.py:223–228`

**Issue:** The dry-run path (line 223) is reached inside the `async with get_session() as
session:` block (opened at line 115). Before returning, it sets:

```python
run.status = PipelineRunStatus.PENDING
run.strategy = None
```

Then returns. The `get_session()` context manager commits on a clean `__aexit__`, so this
commits a `PipelineRun` row with `step="parse"`, `status=PENDING`, `strategy=None` to the
database. The docstring says dry-run "does not write to DB" — this claim is false. A dangling
PENDING pipeline_run row is now visible in `pipeline_runs` and can interfere with subsequent
`get_run_id_for_step` lookups (which order by `created_at.desc()` and take the first row) if
the dangling row is the most recent.

**Fix:** Exit the session without flushing or committing on dry-run — do not add `run` to the
session at all when `args.dry_run` is set, or check `dry_run` before opening the session:

```python
# Option A — check before session open:
async with get_session() as session:
    source_run = await session.get(PipelineRun, args.run_id)
    if source_run is None:
        raise ValueError(f"No pipeline_run with id={args.run_id}")
    # ... extract pages and parse ...
    if args.dry_run:
        print(f"Dry-run mode: {len(utterances)} utterances parsed but NOT written to DB.")
        return   # exit WITHOUT adding the PipelineRun; session commits nothing meaningful

    # Non-dry-run: create and persist the PipelineRun
    run = PipelineRun(...)
    session.add(run)
    ...
```

---

## Warnings

### WR-01: `asyncio.get_event_loop()` deprecated in Python 3.10+

**File:** `api/routers/admin.py:148`

**Issue:** Inside an `async def` FastAPI route handler there is always a running event loop.
`asyncio.get_event_loop()` is deprecated in Python 3.10+ and raises `DeprecationWarning` in
3.10–3.11; in Python 3.12 it raises `RuntimeError` when called from a coroutine that is already
running on a loop. This was flagged in the prior round review (WR-01) and has not been fixed.

**Fix:**
```python
# Replace line 148:
loop = asyncio.get_event_loop()
# with:
loop = asyncio.get_running_loop()
```

---

### WR-02: `create_person_for_job` accepts `job_id` but never validates it

**File:** `api/services/admin_jobs.py:327–358`

**Issue:** The `job_id: int` parameter is accepted but the function body never uses it. No
check verifies that the `AdminJob` exists or is in PAUSED state. A POST to
`/api/admin/jobs/99999/people` with a non-existent `job_id` creates a `Person` row
unconditionally. This was flagged in the prior round review (WR-05) and has not been fixed.

Additionally, the router at `admin.py:283` does not wrap the call in `try/except ValueError`,
so if a guard check is added, unhandled `ValueError` would produce an HTTP 500 rather than 422.

**Fix (service layer):**
```python
async def create_person_for_job(db, job_id, body):
    job = await get_job(db, job_id)
    if job is None:
        raise ValueError(f"AdminJob {job_id} not found")
    if job.status != AdminJobStatus.PAUSED:
        raise ValueError(
            f"AdminJob {job_id} is not PAUSED (status: {job.status.value!r})"
        )
    # ... rest unchanged
```

**Fix (router):** Wrap the `create_person_for_job` call in `try/except ValueError` mirroring
the `resolve_job` pattern at lines 249–252.

---

### WR-03: `stepStatus` returns all `'pending'` when job fails with `current_step=null`

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:134–148`

**Issue:** When a job fails before any step writes `current_step` (e.g., the subprocess exits
before Step 0), `job.current_step` is `null`. In `stepStatus`:

```typescript
const current = job.current_step?.toLowerCase() as StepName; // undefined
const currentIdx = STEP_ORDER.indexOf(current);              // -1
```

The three `status === 'failed'` branches all miss (`undefined !== step`,
`N < -1` is false, `0 > -1` is true for every step), so all three cards return `'pending'`.
The operator sees three Pending cards for a failed job with no indication of which step failed.
The error panel at the bottom still renders — but the step cards are misleading.

**Fix:**
```typescript
function stepStatus(step: StepName, job: Job): string {
    const current = job.current_step?.toLowerCase() as StepName | undefined;
    const currentIdx = current !== undefined ? STEP_ORDER.indexOf(current) : -1;
    const thisIdx = STEP_ORDER.indexOf(step);

    if (job.status === 'completed') return 'completed';
    if (job.status === 'failed') {
        if (currentIdx === -1) return step === STEP_ORDER[0] ? 'failed' : 'pending';
        if (step === current) return 'failed';
        return thisIdx < currentIdx ? 'completed' : 'pending';
    }
    if (job.status === 'paused' && step === 'resolve') return 'paused';
    if (job.status === 'paused') return thisIdx < currentIdx ? 'completed' : 'pending';
    if (thisIdx < currentIdx) return 'completed';
    if (thisIdx === currentIdx) return job.status === 'running' ? 'running' : 'pending';
    return 'pending';
}
```

---

### WR-04: `pdf_file.content_type` is client-supplied — magic-bytes check is missing

**File:** `api/routers/admin.py:139`

**Issue:** `pdf_file.content_type` is the value from the multipart `Content-Type` field set
by the HTTP client. Any client can set `Content-Type: application/pdf` while uploading an
arbitrary payload. T-07-04 requires content validation; the current check does not satisfy it.
This was flagged in the prior round review (WR-06) and has not been fixed.

**Fix:** Read the first 4 bytes and check for the PDF magic signature:
```python
header = await pdf_file.read(4)
await pdf_file.seek(0)
if header != b'%PDF':
    raise HTTPException(status_code=422, detail="Uploaded file must be a PDF.")
file_bytes = await pdf_file.read()
```

---

### WR-05: `resolve_job` broadens Utterance UPDATE to all parse runs when `parse_run_id` is None

**File:** `api/services/admin_jobs.py:242–255`

**Issue:** `parse_run_id` is fetched at line 214. At line 247 the code conditionally appends
`Utterance.pipeline_run_id == parse_run_id` to the WHERE clause only when non-null. If
`parse_run_id` is None, the UPDATE targets every Utterance row for the argument that matches
the raw label — including rows from prior parse runs — violating the "prior rows are not
deleted until the new run is promoted" invariant.

In practice `parse_run_id` should be non-null when `resolve_job` is called, but the None path
is a latent data-corruption risk.

**Fix:** Treat a missing `parse_run_id` as an error:
```python
parse_run_id = await get_run_id_for_step(db, job_id, "parse")
if parse_run_id is None:
    raise ValueError(
        f"No parse pipeline_run found for AdminJob {job_id}. "
        "Cannot scope utterance updates without a parse run id."
    )
```

---

### WR-06: Orphaned job row created if DO Spaces upload fails in upload mode

**File:** `api/routers/admin.py:145–165`

**Issue:** In the file-upload branch, `create_job` is called first (line 145), writing a
`AdminJob` row to the database. The DO Spaces upload is performed next (lines 149–154). If the
upload raises an exception (network error, invalid credentials, bucket not configured), the
exception propagates to the FastAPI exception handler — but the `AdminJob` row created at line
145 has already been committed (`create_job` calls `await db.commit()` at line 64 of
`admin_jobs.py`). The orphaned job row has no `spaces_key`, `status=PENDING`, and no subprocess
running for it. It will persist in the job history with no way to progress or be cleaned up.

**Fix:** Wrap the upload call in a try/except that marks the job FAILED before re-raising:
```python
job = await jobs_service.create_job(db, spaces_key=None)
key = f"uploads/{job.id}.pdf"
file_bytes = await pdf_file.read()
loop = asyncio.get_running_loop()
try:
    await loop.run_in_executor(None, spaces_service.upload_pdf_to_spaces, file_bytes, key)
except Exception as exc:
    await db.execute(
        update(AdminJob)
        .where(AdminJob.id == job.id)
        .values(status=AdminJobStatus.FAILED, error_message=f"Spaces upload failed: {exc}")
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    raise HTTPException(status_code=502, detail="File upload failed. Please try again.") from exc
```

---

### WR-07: `if args.job_id:` truthy check silently skips writes when `job_id=0`

**File:** `pipeline/commands/ingest.py:196, 219, 388` | `pipeline/commands/parse.py:80, 103, 264` | `pipeline/commands/resolve.py:90, 113, 305, 350, 371`

**Issue:** All job-driven guard branches use the truthy idiom `if args.job_id:`. PostgreSQL
serial PKs start at 1 so `job_id=0` cannot occur in production, but in automated tests that
use mocked IDs of 0, all DB status writes are silently skipped without any error or warning.
`if args.job_id is not None:` is the correct guard and is unambiguous about intent. This was
flagged in the prior round review (IN-02) for `resolve.py` only; the same pattern exists in
`ingest.py` and `parse.py`.

**Fix:** Replace all occurrences of `if args.job_id:` in all three pipeline command files with
`if args.job_id is not None:` (11 locations total).

---

### WR-08: `getRowCandidates` called twice per correcting-row render cycle

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:417–435`

**Issue:** When a row is in correcting mode, the template calls `getRowCandidates(row, rowKey)`
twice per render: once inside the `oninput` closure (line 418) and once as the `{#each}` source
for the `<datalist>` (line 431). Each call rebuilds the full merged + deduped array from
`data.people`, `row.candidates`, and `rowStates[label].extraCandidates`. For a large people
roster with multiple correcting rows open simultaneously, this doubles array construction work
on every keystroke.

**Fix:** Capture in a template constant:
```svelte
{@const candidates = getRowCandidates(row, rowKey)}
<input list={listId} ... oninput={(e) => {
    const val = (e.target as HTMLInputElement).value;
    const match = candidates.find(c => {
        const display = c.role_name ? `${c.full_name} (${c.role_name})` : c.full_name;
        return display === val;
    });
    if (match) handleSelectPerson(rowKey, match.id.toString());
    else if (val === '— Add new person —') handleSelectPerson(rowKey, '__add_new__');
}} />
<datalist id={listId}>
    {#each candidates as candidate (candidate.id)}
        <option value={...}></option>
    {/each}
</datalist>
```

---

## Info

### IN-01: `PersonResponse.role_name` is always `null` from `create_person_for_job`

**File:** `api/services/admin_jobs.py:353–358`, `api/routers/admin.py:283`, `api/schemas/admin_jobs.py:61`

**Issue:** `create_person_for_job` returns a `Person` ORM object. FastAPI serializes it via
`response_model=PersonResponse` which has `from_attributes=True`. `PersonResponse` declares
`role_name: Optional[str] = None`, but `Person` has no `role_name` column — only `role_id`.
Pydantic v2 silently defaults the missing attribute to `None`, so `PersonResponse.role_name` is
always `null` in the API response regardless of whether a role was assigned.

The server action in `+page.server.ts` (lines 120–123) works around this by enriching with the
form's `role_name` value. This is a valid workaround but couples the fix to client logic.

**Fix (service layer):** Return a `PersonResponse` dict rather than a bare ORM object:
```python
return PersonResponse(
    id=person.id,
    full_name=person.full_name,
    role_id=person.role_id,
    role_name=body.role_name if body.role_name and person.role_id else None,
)
```

---

### IN-02: No file-size limit enforced on PDF upload

**File:** `api/routers/admin.py:147`

**Issue:** `await pdf_file.read()` at line 147 reads the entire upload into memory with no
size cap. A 500 MB file would be fully buffered into the FastAPI process before the Spaces
upload begins. The SvelteKit side is bounded by `BODY_SIZE_LIMIT=10M` (documented in
`+page.server.ts`), but a direct API call bypasses that limit entirely.

**Suggestion:** Add a size guard after reading:
```python
MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MB
file_bytes = await pdf_file.read(MAX_PDF_BYTES + 1)
if len(file_bytes) > MAX_PDF_BYTES:
    raise HTTPException(status_code=413, detail="PDF must be 50 MB or smaller.")
```

---

### IN-03: `alembic/versions/0004` adds no index on `arguments.resolved_at`

**File:** `alembic/versions/0004_add_arguments_resolved_at.py:29–33`

**Issue:** `api/services/cases.py:34` filters `WHERE argument.resolved_at IS NOT NULL` on every
`/cases/` page load. The migration adds the column but no index. For a large archive of
arguments this results in a full table scan on every request.

**Suggestion:** Add a partial index covering only non-null rows:
```python
def upgrade() -> None:
    op.add_column(
        "arguments",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_arguments_resolved_at",
        "arguments",
        ["resolved_at"],
        postgresql_where=sa.text("resolved_at IS NOT NULL"),
    )
```

---

### IN-04: `console.error` calls in production load function leak internal URLs

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:34, 39`

**Issue:** Lines 34 and 39 log `peopleLoadError` (which includes the raw FastAPI HTTP status
code or error message) to the server console. In a production DO App Platform deployment,
console output is visible in application logs accessible to anyone with platform access. The
messages include `FASTAPI_BASE_URL` + endpoint path information and HTTP status codes.

This is a minor operational concern — the admin pages are already auth-gated, and the data
being logged is low-sensitivity — but internal service URLs should not be logged in plaintext
in a deployable server component.

**Suggestion:** Remove the `FASTAPI_BASE_URL` portion of the log message or replace the
`console.error` with a structured log that omits the URL:
```typescript
console.error('[load] people fetch failed, status:', peopleRes.status);
```

---

_Reviewed: 2026-06-17T15:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
