---
phase: 07-pipeline-runner
reviewed: 2026-06-17T12:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
  - app/src/routes/admin/pipeline/[job_id]/+page.svelte
  - api/routers/admin.py
  - api/services/admin_jobs.py
  - api/services/cases.py
  - api/models/models.py
  - alembic/versions/0004_add_arguments_resolved_at.py
  - pipeline/commands/resolve.py
findings:
  critical: 4
  warning: 6
  info: 3
  total: 13
status: issues_found
---

# Phase 07: Code Review Report (Round 3 — gap-closure scope)

**Reviewed:** 2026-06-17T12:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

This review covers the 8 files modified or introduced in the gap-closure plans (07-07 / 07-08):
the `[job_id]` detail page (server + client), the admin router and service, the cases service,
the ORM models, the migration for `resolved_at`, and the resolve pipeline command.

Four critical issues were found. The most impactful is that `pipeline/commands/resolve.py` still
appends HIT rows (auto-resolved aliases) to the `discrepancies` list alongside MISS rows — the
"all labels auto-resolved → mark COMPLETED" path (line 371) is permanently dead code for any
transcript with utterances. This was identified in the previous round-2 review (CR-01) and has
not been fixed. The second critical issue is that `resolve_job` in `admin_jobs.py` applies alias
writes and stamps `resolved_at` without first verifying the job is in PAUSED state — a double
POST or a stale browser can corrupt utterance data and make an already-completed argument
invisible by overwriting a non-null `resolved_at` with a new timestamp. The third and fourth
critical issues are in `+page.svelte`: `continueSubmitting` is never reset to `false` after a
successful resolve submit (the button is permanently stuck as "Submitting…" if the polling
`invalidateAll` doesn't change `data.job.status` in time), and `rowStates` initialisation never
evicts stale rows when the server returns a different discrepancy set after a retry (operator
can submit an out-of-date mapping).

---

## Critical Issues

### CR-01: HIT rows appended to `discrepancies` — COMPLETED path is unreachable dead code

**File:** `pipeline/commands/resolve.py:243–253, 299–326, 350–386`

**Issue:** Both HIT labels (alias found, lines 243–253) and MISS labels (no alias, lines
269–279) are appended to the `discrepancies` list. Because HITs are included, `discrepancies`
is non-empty for any transcript that contains any utterances. The branching at line 299
(`if discrepancies:`) therefore always fires, setting
`resolve_run.status = PipelineRunStatus.NEEDS_REVIEW` and — for the job-driven path — writing
all rows to `admin_jobs.discrepancies` and setting `status=PAUSED`.

Consequences:

1. **Dead code (line 371):** `if not discrepancies and args.job_id:` — the block that marks the
   `AdminJob` COMPLETED and stamps `arguments.resolved_at` — can never execute for a real
   transcript. Cases are permanently invisible in `/cases/` even after full auto-resolve.

2. **Dead code (line 325):** `resolve_run.status = PipelineRunStatus.COMPLETED` (the `else:`
   branch of `if discrepancies:`) is never reached for a real transcript.

3. **Incorrect behavior:** Every job-driven resolve — including runs where every alias matched —
   unconditionally PAUSEs the job and forces an unnecessary browser confirmation round-trip.

4. **Direct CLI (lines 307–321):** When `args.job_id is None`, the MISS-only print block
   iterates the entire `discrepancies` list including HITs and prints all of them as "unresolved
   labels", misleading operators.

This was flagged in the prior round-2 review (CR-01) and has not been fixed.

**Fix:** Maintain separate lists for HITs and MISSes. For the job-driven path, the JSONB payload
written to `admin_jobs.discrepancies` can contain HITs (so the browser can show them for
confirmation), but the branching gate should be based on whether any MISSes exist:

```python
discrepancies: list[dict] = []   # ALL rows shown in browser (HITs + MISSes)
misses: list[str] = []           # raw labels with no alias — gate for PAUSED vs COMPLETED

# HIT branch: append to discrepancies (for UI), do NOT add to misses
discrepancies.append({..., "auto_resolved": True})

# MISS branch: append to both
misses.append(raw_label)
discrepancies.append({..., "auto_resolved": None})

# Step 6 gate — keyed on misses, not discrepancies:
if misses:
    resolve_run.status = PipelineRunStatus.NEEDS_REVIEW
    ...
    if args.job_id:
        # write discrepancies JSONB (contains HITs + MISSes for browser UI)
        ...
    else:
        # CLI: print only MISSes
        for label in misses:
            print(f"  - {label!r}")
else:
    # All auto-resolved
    resolve_run.status = PipelineRunStatus.COMPLETED
    ...
```

---

### CR-02: `resolve_job` does not verify the job is PAUSED before writing aliases

**File:** `api/services/admin_jobs.py:182–287`

**Issue:** `resolve_job` validates that the job exists (line 199) and that all `person_id`s
are valid (lines 201–210), but does not check that `job.status == AdminJobStatus.PAUSED` before
writing `SpeakerAlias` rows, updating `Utterance.person_id`, updating
`ArgumentParticipant.person_id`, and stamping `arguments.resolved_at`.

Two concrete failure modes:

1. **Double-submit:** An operator double-clicks "Continue Resolve." The first POST wins and
   marks the job COMPLETED. The second POST re-applies all alias writes (idempotent in practice
   but generates spurious DB round-trips) and overwrites `resolved_at` with a new timestamp
   (non-idempotent).

2. **Wrong-state call:** A caller POSTs to `/api/admin/jobs/{id}/resolve` on a FAILED or
   COMPLETED job. All alias writes and the `resolved_at` stamp execute unconditionally.

**Fix:** Add a state check at the top of `resolve_job`, after loading the job:

```python
job = await get_job(db, job_id)
if job is None:
    raise ValueError(f"AdminJob {job_id} not found")
if job.status != AdminJobStatus.PAUSED:
    raise ValueError(
        f"AdminJob {job_id} is not PAUSED (current status: {job.status.value!r}); "
        "resolve can only be applied to a paused job."
    )
```

The router already catches `ValueError` and re-raises as HTTP 422 (line 249–252 of `admin.py`),
so no router changes are required.

---

### CR-03: `continueSubmitting` is never reset to `false` on successful resolve

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:660–672`

**Issue:** The `use:enhance` callback for the "Continue Resolve" form sets
`continueSubmitting = true` on submit (line 661). On failure it resets to `false` (line 664).
On success it calls `await update({ reset: false })` (line 669) — but never resets
`continueSubmitting`. The button stays disabled and reads "Submitting…" indefinitely.

The expected recovery path is that `invalidateAll` (called by `update()`) triggers a re-fetch
that changes `data.job.status` from `'paused'` to `'running'`, which hides the entire form
block (the `{#if data.job.status === 'paused' && allDispositioned}` condition at line 656).
This works if polling is fast and the server-side state transitions before the next render.

However, if the FastAPI state machine has not yet advanced (race on the first poll after
submit), the form block re-renders while `data.job.status` is still `'paused'` —
and the button is permanently stuck because `continueSubmitting` is a `$state` variable
that survived the `update({ reset: false })` call.

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

### CR-04: `rowStates` initialisation never evicts stale rows — operator can submit stale data

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:74–93`

**Issue:** The `$effect` that initialises `rowStates` (line 74) skips any
`raw_speaker_label` already present in `rowStates`:

```typescript
if (!(row.raw_speaker_label in rowStates)) {
    // initialise ...
}
```

This is correct to prevent wiping in-progress dispositions during polling. However, it creates
a correctness problem if the server returns a *different* set of discrepancies from what was
originally loaded — for example, if the operator navigated away and back, a new resolve run was
spawned, or the job was retried. In that case, `rowStates` may contain entries for
`raw_speaker_label`s that no longer exist in the new discrepancy list, and the
`matchesJson` derived value (line 108) will include those stale mappings in the form payload
submitted to the server.

The `matchesJson` builder (line 108–118) iterates `data.job.discrepancies` so it only
includes currently-visible rows — but `allDispositioned` (line 98–105) also iterates
`data.job.discrepancies`. If the new discrepancy set contains a row not yet in `rowStates`
(the new label added by a retry), the `$effect` initialises it, but stale keys in `rowStates`
from the prior run are never cleaned up. For a re-resolved job, the prior stale state is visible
to `allDispositioned` checks.

The deeper issue: there is no version/epoch guard in `rowStates` so the client can never
distinguish "this state belongs to this resolve attempt" from "state from a prior attempt."

**Fix:** Reset `rowStates` when the set of `raw_speaker_label`s changes:

```typescript
$effect(() => {
    const disc = data.job.discrepancies;
    if (!disc) return;

    const incomingKeys = new Set(disc.map(r => r.raw_speaker_label));

    // Evict stale keys no longer present in server data
    for (const key of Object.keys(rowStates)) {
        if (!incomingKeys.has(key)) {
            delete rowStates[key];
        }
    }

    // Initialise new rows
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

## Warnings

### WR-01: `asyncio.get_event_loop()` deprecated in Python 3.10+ — use `get_running_loop()`

**File:** `api/routers/admin.py:148`

**Issue:** Inside an `async def` FastAPI route handler there is always a running event loop.
`asyncio.get_event_loop()` is deprecated in Python 3.10+ and in Python 3.12 raises
`DeprecationWarning`; in some configurations it can raise `RuntimeError`. This was flagged in
the prior round-2 review (WR-01) and has not been fixed.

**Fix:**
```python
# line 148 — replace:
loop = asyncio.get_event_loop()
# with:
loop = asyncio.get_running_loop()
```

---

### WR-02: `create_person_for_job` accepts `job_id` but never uses it — no existence check

**File:** `api/services/admin_jobs.py:327–358`

**Issue:** The `job_id: int` parameter is accepted but unused in the function body. No check
that the `AdminJob` exists or is in PAUSED state is performed. A POST to
`/api/admin/jobs/99999/people` with a non-existent `job_id` will create a `Person` row with no
error. This was flagged in the prior round-2 review (WR-05) and has not been fixed.

**Fix:**
```python
async def create_person_for_job(
    db: AsyncSession,
    job_id: int,
    body: PersonCreate,
) -> Person:
    job = await get_job(db, job_id)
    if job is None:
        raise ValueError(f"AdminJob {job_id} not found")
    if job.status != AdminJobStatus.PAUSED:
        raise ValueError(
            f"AdminJob {job_id} is not PAUSED (status: {job.status.value!r})"
        )
    # ... rest unchanged
```

The router at `admin.py:283` does not currently wrap this call in `try/except ValueError`,
so the fix also requires updating the route to catch `ValueError` and re-raise as HTTP 422,
mirroring the `resolve_job` pattern at lines 249–252.

---

### WR-03: `stepStatus` returns all `'pending'` for `status='failed'` + `current_step=null`

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:134–148`

**Issue:** When a job fails before any step writes `current_step` (e.g., the spawned subprocess
exits before Step 0 of `resolve.py`), `job.current_step` is `null`. This makes `current` equal
to `undefined` and `currentIdx` equal to `-1`. The three `job.status === 'failed'` branches:

```typescript
if (job.status === 'failed' && step === current) return 'failed';   // undefined !== step
if (job.status === 'failed' && thisIdx < currentIdx) return 'completed'; // N < -1 → false
if (job.status === 'failed' && thisIdx > currentIdx) return 'pending';   // 0 > -1 → true
```

The third branch fires for every step, returning `'pending'` for all. The operator sees three
"Pending" cards for a failed job with no indication of failure — the error panel at the bottom
still renders (lines 703–731), but the step cards are misleading.

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

### WR-04: `pdf_file.content_type` is client-supplied — not a reliable security control

**File:** `api/routers/admin.py:139`

**Issue:** `pdf_file.content_type` is the `Content-Type` from the multipart submission set by
the HTTP client. Any client can send `Content-Type: application/pdf` while uploading an
arbitrary payload. T-07-04 calls out content validation as a security requirement; the current
check does not satisfy it. This was flagged in the prior round-2 review (WR-06) and has not
been fixed.

**Fix:** Check the PDF magic bytes server-side:
```python
header = await pdf_file.read(4)
await pdf_file.seek(0)
if header != b'%PDF':
    raise HTTPException(status_code=422, detail="Uploaded file must be a PDF.")
file_bytes = await pdf_file.read()
```

---

### WR-05: `resolve_job` does not scope Utterance UPDATE to the active parse run when `parse_run_id` is None

**File:** `api/services/admin_jobs.py:242–255`

**Issue:** `parse_run_id` is fetched at line 214 and used to scope the `Utterance` UPDATE at
line 247 (`if parse_run_id is not None`). If `parse_run_id` is `None` — which can happen when
`get_run_id_for_step` finds no `PipelineRun` row for the argument — the condition at line 247
falls through to a WHERE clause that omits the `pipeline_run_id` filter:

```python
utterance_where = [
    Utterance.argument_id == job.argument_id,
    Utterance.raw_speaker_label == match.raw_speaker_label,
]
if parse_run_id is not None:
    utterance_where.append(Utterance.pipeline_run_id == parse_run_id)
```

Without the `pipeline_run_id` filter, the UPDATE targets **all** Utterance rows for
the argument that match the raw label — including rows from prior parse runs. This violates
the "prior rows are not deleted until the new run is promoted" invariant stated in CLAUDE.md
and in the `PipelineRun` table comment.

In practice `parse_run_id` should always be non-null when `resolve_job` is called (the resolve
step only runs after parse completes), but the None branch is a latent data-corruption path.

**Fix:** Treat a missing `parse_run_id` as an error condition rather than silently broadening
the UPDATE:

```python
parse_run_id = await get_run_id_for_step(db, job_id, "parse")
if parse_run_id is None:
    raise ValueError(
        f"No parse pipeline_run found for AdminJob {job_id}. "
        "Cannot scope utterance updates without a parse run id."
    )
```

---

### WR-06: `getRowCandidates` called twice per correcting-row render cycle

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:417–435`

**Issue:** When a row is in correcting mode (`s?.correcting === true`), the template calls
`getRowCandidates(row, rowKey)` twice per render: once inside the `oninput` closure (line 418)
and once as the `{#each}` source for the `<datalist>` (line 431). Each call rebuilds the
full merged+deduped array from `data.people`, `row.candidates`, and
`rowStates[label].extraCandidates`. For a large people roster (hundreds of entries) and
multiple correcting rows open simultaneously, this doubles the array construction cost on
every keystroke.

**Fix:** Capture the result in a template constant above the input:

```svelte
{@const candidates = getRowCandidates(row, rowKey)}
<input
    list={listId}
    ...
    oninput={(e) => {
        const val = (e.target as HTMLInputElement).value;
        const match = candidates.find(c => {
            const display = c.role_name ? `${c.full_name} (${c.role_name})` : c.full_name;
            return display === val;
        });
        ...
    }}
/>
<datalist id={listId}>
    {#each candidates as candidate (candidate.id)}
        ...
    {/each}
</datalist>
```

---

## Info

### IN-01: `PersonResponse.role_name` always `null` from `create_person_for_job`

**File:** `api/services/admin_jobs.py:353–358`, `api/routers/admin.py:283`, `api/schemas/admin_jobs.py:61`

**Issue:** `create_person_for_job` returns a `Person` ORM object. FastAPI serializes it via
`response_model=PersonResponse` which has `from_attributes=True`. `PersonResponse` declares
`role_name: Optional[str] = None`. The `Person` ORM model has no `role_name` column — only
`role_id`. Pydantic v2 silently defaults missing optional attributes to `None`, so
`PersonResponse.role_name` is always `null` in the API response regardless of whether a role
was assigned.

The server action in `+page.server.ts` (lines 120–123) papers over this by enriching with the
form's `role_name` value:
```typescript
const enrichedPerson = { ...person, role_name: person.role_name ?? (role_name.trim() || null) };
```
This is a workable workaround but couples the fix to client logic rather than fixing the source.

The root cause is that `create_person_for_job` returns the bare `Person` rather than
a dict that also includes the resolved `role_name`. Compare with `list_people` (lines 306–319)
which correctly JOINs `Role` and returns `role_name`.

**Fix (service layer):** After creating the person, return a dict matching `PersonResponse`:
```python
return PersonResponse(
    id=person.id,
    full_name=person.full_name,
    role_id=person.role_id,
    role_name=body.role_name if body.role_name and person.role_id else None,
)
```
Or re-query with a JOIN to get the canonical role_name from the DB.

---

### IN-02: `if args.job_id:` truthy check skips writes if `job_id=0`

**File:** `pipeline/commands/resolve.py:90, 113, 305, 350, 371`

**Issue:** All job-driven guard branches use `if args.job_id:` (truthy int check). PostgreSQL
serial PKs start at 1 so `job_id=0` cannot occur in production, but in automated tests using
mocked IDs of 0, all DB status writes are silently skipped without error. The correct guard is
`if args.job_id is not None:`. This was flagged in the prior round-2 review (IN-02) and has not
been fixed in `resolve.py`.

**Fix:** Replace all 5 occurrences of `if args.job_id:` in `resolve.py` with
`if args.job_id is not None:`.

---

### IN-03: `alembic/versions/0004` migration adds no index on `arguments.resolved_at`

**File:** `alembic/versions/0004_add_arguments_resolved_at.py:29–33`

**Issue:** `cases.py` line 34 filters `WHERE argument.resolved_at IS NOT NULL`. The migration
adds the column but no index. For a small dataset this is inconsequential; for a large archive
of arguments a full table scan on every `/cases/` page load is unnecessary.

**Suggestion:** Consider adding an index if the table is expected to grow:
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
This is a partial index so it only covers the non-null rows that the query actually
needs to find.

---

_Reviewed: 2026-06-17T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
