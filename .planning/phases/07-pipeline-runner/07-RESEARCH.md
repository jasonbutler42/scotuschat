# Phase 7: Pipeline Runner — Research

**Researched:** 2026-06-16
**Domain:** FastAPI subprocess orchestration, SvelteKit polling UI, DO Spaces file storage, SQLAlchemy atomic guards
**Confidence:** MEDIUM (architecture is well-constrained by context decisions; subprocess/polling patterns verified via official docs and live search)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Subprocess Model**
- D-01: Pipeline steps via `subprocess.Popen` — one OS process per step (`python -m pipeline ingest ...`, etc.). Not `asyncio.create_subprocess_exec`, not direct function import.
- D-02: Each subprocess accepts `--job-id {admin_job_id}` and writes its own status, `current_step`, and `discrepancies` to `admin_jobs`. FastAPI is a reader, not writer, for progress.
- D-03: Subprocess stdout/stderr discarded (DEVNULL). All meaningful state goes to DB. Failures captured in `error_message` column.
- D-04: One subprocess per step (three spawns per full run). FastAPI simply doesn't spawn the next step when discrepancies exist.
- D-05: FastAPI poll endpoint (`GET /api/admin/jobs/{id}`) triggers step-advance as a side effect. Atomic guard: `UPDATE admin_jobs SET status='running', current_step='parse' WHERE id={job_id} AND current_step='ingest' AND status='completed'` — if 0 rows updated, skip spawn.
- D-06: Single poll target: `GET /api/admin/jobs/{id}` returns the full `admin_jobs` row.

**Page Flow**
- D-07: `/admin/pipeline` always lands on the New Run start form. Previous runs listed below.
- D-08: Start form **redirects to** `/admin/pipeline/[job_id]` after submission.
- D-09: Start form uses two-tab/toggle UI — "Enter URL" and "Upload file" modes.
- D-10: Status page shows three step cards (Ingest → Parse → Resolve) in a vertical stack.

**Discrepancy Review**
- D-11: Resolve step card renders inline review table with Confirm/Correct buttons.
- D-12: Correct opens a searchable dropdown of all existing people + "Add new person" option.
- D-13: "Add new person" is name + role only (bio/photo/tenure dates are Phase 8).
- D-14: "Continue Resolve" button appears after all rows are dispositioned. No auto-advance.

**Client-Side Polling**
- D-15: Status page uses `setInterval` (2.5s) + `invalidateAll()` inside a Svelte 5 `$effect`.
- D-16: Polling stops when `admin_jobs.status` reaches `completed`, `failed`, or `paused`.
- D-17: Failed state shows red badge + `error_message` inline. No retry button.

### Claude's Discretion
- Exact visual styling of step cards, badges, and discrepancy table (within dark admin theme)
- "Add new person" inline below dropdown vs. small modal
- Exact toggle/tab styling for URL vs. file upload mode switch
- DEVNULL routing specifics
- Whether `invalidateAll()` or targeted `invalidate(url)` — either is fine

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-12 | Operator can start a new pipeline run by entering a transcript PDF URL | URL-input form action → `POST /api/admin/jobs` → redirect to job page |
| PIPE-13 | Operator can start a new pipeline run by uploading a local PDF file | File upload via `multipart/form-data` form action → boto3 upload to DO Spaces → `POST /api/admin/jobs` |
| PIPE-14 | Running pipeline displays step status (Ingest/Parse/Resolve) and auto-advances | `setInterval` + `invalidateAll()` in `$effect`; poll endpoint spawns next step as side effect |
| PIPE-15 | Pipeline pauses after resolve step when discrepancies exist | FastAPI skips spawn if `discrepancies` JSONB is non-empty; sets status=paused |
| PIPE-16 | Operator can confirm/correct alias matches; confirmed matches saved to speaker_alias | `POST /api/admin/jobs/{id}/resolve` writes confirmed aliases, marks job completed |
| PIPE-17 | Job state persisted to DB so operator can close browser and resume | `admin_jobs` table (already in migration 0003); job URL `/admin/pipeline/[job_id]` is stable |
</phase_requirements>

---

## Summary

Phase 7 orchestrates the full pipeline run lifecycle in the browser. The architecture is a **fire-and-poll** pattern: the operator submits a form, FastAPI creates an `admin_jobs` row and immediately spawns the ingest subprocess via `subprocess.Popen`, then returns `job_id` and redirects the browser to the status page. The status page polls `GET /api/admin/jobs/{id}` every 2.5 seconds; the poll endpoint is the only place that decides whether to spawn the next subprocess (using an atomic UPDATE guard to prevent double-spawn races). All state lives in the `admin_jobs` DB row.

The three pipeline subprocesses (`python -m pipeline ingest/parse/resolve`) each accept a `--job-id` flag and write their own progress directly to `admin_jobs`. FastAPI never awaits a subprocess — it merely reads DB state and conditionally spawns the next step. Resolve's behavior changes in Phase 7: instead of prompting in the terminal, it writes `discrepancies` JSONB to `admin_jobs` and exits with `status=paused`. The browser then renders the review UI.

Uploaded PDFs (PIPE-13) cannot be stored on the DO App Platform container filesystem (ephemeral). They must be uploaded to DigitalOcean Spaces via boto3 (S3-compatible), with the object key stored in `admin_jobs.spaces_key`. `boto3` is not currently in `requirements.txt` and must be added.

**Primary recommendation:** Implement in four sequential work streams: (1) API routes + Pydantic schemas for job CRUD, (2) pipeline subprocess modifications (`--job-id` flag + DB writes), (3) DO Spaces upload utility, (4) SvelteKit pages (start form + status page).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Create admin_jobs row | API / Backend | — | DB write; FastAPI has the DB session |
| Spawn pipeline subprocess | API / Backend | — | Only the server process can spawn OS processes |
| Read job state for poll | API / Backend | — | DB read; returns full admin_jobs row as JSON |
| Atomic step-advance guard | API / Backend | — | UPDATE WHERE guard must be in DB layer, not client |
| Write step progress + discrepancies | Pipeline CLI | — | Subprocess writes directly to DB (D-02); FastAPI does not write progress |
| Confirm/correct aliases | API / Backend | — | Writes to speaker_alias; needs DB session |
| Create new person during review | API / Backend | — | Writes to people table |
| File upload (PDF → Spaces) | API / Backend | — | SvelteKit forwards bytes; FastAPI performs boto3 upload (or SvelteKit page.server.ts can call boto3 via a server-side fetch to FastAPI) |
| Start form rendering | Frontend (SvelteKit SSR) | — | Standard SvelteKit form action |
| Polling + step card rendering | Browser / Client | — | `setInterval` + `invalidateAll()` is client-only |
| Session auth guard | Frontend Server (hooks) | — | `hooks.server.ts` is the sole auth checkpoint (Phase 6) |

**Note on file upload tier:** The SvelteKit `+page.server.ts` receives the multipart upload and then calls `POST /api/admin/jobs` with the file bytes. FastAPI performs the boto3 upload and creates the job row. This keeps storage credentials on the FastAPI side where `api/core/config.py` already manages env vars. [ASSUMED]

---

## Standard Stack

### Core (no new packages for API/SvelteKit side)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115+ (pinned in requirements.txt) | API routes for job CRUD | Already in stack |
| SQLAlchemy 2.0 async | 2.0+ (pinned) | DB reads/writes for admin_jobs | Already in stack |
| SvelteKit | 2.21.0 (package.json) | Frontend pages and form actions | Already in stack |
| Svelte 5 | 5.30.0 (package.json) | Runes — `$effect`, `$state`, `$props` | Already in stack |
| subprocess (stdlib) | Python 3.14 stdlib | Spawn pipeline steps | Decision D-01; no external dep needed |

### New Package Required

| Library | Version | Purpose | Why Needed |
|---------|---------|---------|------------|
| boto3 | latest stable | Upload PDFs to DigitalOcean Spaces | PIPE-13: DO App Platform filesystem is ephemeral; boto3 is the S3-compatible client for Spaces [ASSUMED — not yet in requirements.txt] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `$app/navigation` | SvelteKit stdlib | `invalidateAll()` for polling re-trigger | In status page `$effect` only; client-side |
| Pydantic v2 BaseModel | 2.x (pinned) | Request/response schemas for new endpoints | Standard FastAPI pattern already used |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `subprocess.Popen` | `asyncio.create_subprocess_exec` | Asyncio subprocess requires running event loop + nesting risks — D-01 explicitly rejected this |
| `setInterval` + `invalidateAll()` | SSE / WebSocket | SSE is structurally difficult under PgBouncer transaction mode (explicitly out of scope in REQUIREMENTS.md) |
| boto3 | httpx + Spaces HTTP API directly | boto3 abstracts auth/signing; direct HTTP requires manual request signing |
| File upload → FastAPI → Spaces | File upload → SvelteKit server → Spaces directly | FastAPI keeps all storage creds in one config module; consistent with existing `api/core/config.py` pattern |

**Installation (new packages only):**
```bash
pip install boto3
```
Then add `boto3>=1.34` to `requirements.txt`.

---

## Package Legitimacy Audit

> boto3 is the only new package proposed for this phase.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| boto3 | PyPI | ~10 yrs | Hundreds of millions/month | github.com/boto/boto3 | OK | Approved |

boto3 is the official AWS SDK for Python, maintained by Amazon Web Services. It is the standard client for all S3-compatible object storage. [ASSUMED — not run through formal gsd-tools legitimacy check due to tool unavailability, but overwhelming public evidence of legitimacy.]

**Packages removed due to SLOP verdict:** None
**Packages flagged as suspicious:** None

---

## Architecture Patterns

### System Architecture Diagram

```
Operator Browser
    │
    ├─[POST /admin/pipeline form action]──► SvelteKit +page.server.ts
    │                                            │ request.formData()
    │                                            │ (URL string OR file bytes)
    │                                            ▼
    │                                      FastAPI POST /api/admin/jobs
    │                                            │
    │                              ┌─────────────┼──────────────────────┐
    │                              │             │                      │
    │                        [URL mode]    [Upload mode]                │
    │                              │       boto3.upload_fileobj         │
    │                              │       → DO Spaces (S3)             │
    │                              │       spaces_key stored            │
    │                              └─────────────┤                      │
    │                                            │                      │
    │                                     AdminJob created              │
    │                                     (status=pending)             │
    │                                            │                      │
    │                                     subprocess.Popen              │
    │                                     python -m pipeline ingest     │
    │                                     --job-id {id} ...             │
    │                                            │                      │
    │                                      202 {job_id}                 │
    │                                            │
    ├─[redirect to /admin/pipeline/{job_id}]◄────┘
    │
    │  Status Page (SSR on load)
    │  +page.server.ts load: GET /api/admin/jobs/{id}
    │  renders step cards with initial state
    │
    │  [Client hydrates — $effect starts polling]
    │
    ├─[setInterval 2500ms → invalidateAll()]
    │                                            │
    │                                      FastAPI GET /api/admin/jobs/{id}
    │                                            │
    │                                      Reads admin_jobs row
    │                                            │
    │                                      If current_step=ingest AND status=completed:
    │                                        atomic UPDATE guard
    │                                        → if 0 rows: skip (already spawned)
    │                                        → if 1 row: subprocess.Popen parse --job-id
    │                                            │
    │                                      If current_step=parse AND status=completed:
    │                                        spawn resolve subprocess
    │                                            │
    │                                      If status=paused (resolve found discrepancies):
    │                                        return job row with discrepancies JSONB
    │                                        → $effect sees terminal state, stops polling
    │                                        → Resolve card renders inline review table
    │
    │  [Operator clicks "Continue Resolve"]
    │
    ├─[POST /api/admin/jobs/{id}/resolve]───────►
    │                                            │
    │                                      Writes speaker_alias rows
    │                                      Marks job status=completed
    │                                      Returns updated job row
    │
    └─[Page navigates / polling resumes briefly until completed]

Pipeline Subprocess (separate OS process)
    python -m pipeline ingest --job-id {id} --url ... / --spaces-key ...
        │
        ├─ Updates admin_jobs: status=running, current_step=ingest
        ├─ Downloads PDF (URL) or reads from Spaces (upload)
        ├─ Creates argument/case/pipeline_run rows
        ├─ Updates admin_jobs: status=completed, argument_id={id}
        └─ Exits

    python -m pipeline parse --job-id {id} --run-id {pipeline_run_id}
        ├─ Updates admin_jobs: status=running
        ├─ pdfplumber + LLM corrective pass
        ├─ Writes utterance rows
        └─ Updates admin_jobs: status=completed

    python -m pipeline resolve --job-id {id} --run-id {pipeline_run_id}
        ├─ Updates admin_jobs: status=running
        ├─ Alias lookup for each label
        ├─ If all auto-resolved: Updates admin_jobs: status=completed
        └─ If misses: Writes discrepancies JSONB, Updates admin_jobs: status=paused, exits
```

### Recommended Project Structure (new files only)

```
api/
├── routers/
│   └── admin.py              # ADD: POST /jobs, GET /jobs/{id}, GET /jobs, POST /jobs/{id}/resolve
├── schemas/
│   └── admin_jobs.py         # NEW: AdminJobCreate, AdminJobResponse, ResolveRequest schemas
├── services/
│   └── admin_jobs.py         # NEW: create_job, get_job, list_jobs, resolve_job service fns
│   └── spaces.py             # NEW: upload_to_spaces(file_bytes, key) → spaces_key

pipeline/
├── __main__.py               # MODIFY: add --job-id to ingest/parse/resolve subparsers
├── commands/
│   ├── ingest.py             # MODIFY: accept --job-id; write admin_jobs status
│   ├── parse.py              # MODIFY: accept --job-id; write admin_jobs status
│   └── resolve.py            # MODIFY: accept --job-id; write discrepancies instead of prompting

app/src/routes/admin/
├── +layout.svelte            # MODIFY: "Pipeline Runner" placeholder → real <a> link
├── pipeline/
│   ├── +page.svelte          # NEW: start form (URL/upload tabs) + history table
│   ├── +page.server.ts       # NEW: load recent jobs + default action (create job + redirect)
│   └── [job_id]/
│       ├── +page.svelte      # NEW: step cards + polling $effect + discrepancy review UI
│       └── +page.server.ts   # NEW: load job state; POST resolve action
```

### Pattern 1: Svelte 5 `$effect` Polling

**What:** Client-side polling that re-runs the server load function every 2.5 seconds while job is active.
**When to use:** Status page only; must be client-only (invalidateAll cannot run on server).

```typescript
// Source: https://svelte.dev/docs/svelte/$effect (verified via WebFetch)
// In /admin/pipeline/[job_id]/+page.svelte

import { invalidateAll } from '$app/navigation';

let { data } = $props();

// Terminal states where polling should stop
const TERMINAL = new Set(['completed', 'failed', 'paused']);

$effect(() => {
  // If job is already in a terminal state on mount, don't start polling
  if (TERMINAL.has(data.job.status)) return;

  const interval = setInterval(async () => {
    await invalidateAll();
  }, 2500);

  return () => clearInterval(interval);
});

// After operator clicks "Continue Resolve", polling resumes:
// The action returns updated data, status changes from 'paused' to 'running',
// the $effect re-runs because data.job.status changed, interval restarts.
```

**Key constraint:** `invalidateAll()` is imported from `$app/navigation` — this module is browser-only. The `$effect` itself only runs on the client (effects do not run during SSR). [VERIFIED: svelte.dev/docs]

### Pattern 2: FastAPI Subprocess Spawn (Fire-and-Forget)

**What:** Spawn pipeline subprocess from within an async FastAPI endpoint, returning immediately.
**When to use:** `POST /api/admin/jobs` and step-advance side effect in `GET /api/admin/jobs/{id}`.

```python
# Source: Python docs subprocess.html (verified via WebFetch) + D-01/D-03 decisions
import subprocess
import sys

def spawn_pipeline_step(
    step: str,
    job_id: int,
    extra_args: list[str],
) -> None:
    """
    Spawn a pipeline step as a detached subprocess.
    stdout/stderr discarded per D-03. All state goes to DB.
    """
    cmd = [sys.executable, "-m", "pipeline", step, "--job-id", str(job_id)] + extra_args

    kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    # Windows: CREATE_NEW_PROCESS_GROUP detaches from parent console
    # POSIX: start_new_session achieves the same isolation
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    subprocess.Popen(cmd, **kwargs)
    # Popen returns immediately — subprocess runs independently
    # Python's _cleanup() reaps zombie children on next Popen() call
```

**Critical:** Do NOT call `.wait()` or `.communicate()` — that would block the FastAPI event loop thread. [ASSUMED — fire-and-forget is the correct pattern; subprocess module docs confirm Popen returns immediately]

### Pattern 3: Atomic Step-Advance Guard

**What:** Prevent double-spawn when two poll requests arrive simultaneously.
**When to use:** Inside `GET /api/admin/jobs/{id}` before any subprocess spawn.

```python
# Source: SQLAlchemy 2.0 docs + asyncpg rowcount support [ASSUMED from research]
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.models import AdminJob, AdminJobStatus, AdminJobStep

async def try_advance_to_parse(db: AsyncSession, job_id: int) -> bool:
    """
    Atomically advance job from ingest→parse.
    Returns True if this request won the race and should spawn parse subprocess.
    Returns False if another request already advanced (0 rows updated).
    """
    result = await db.execute(
        update(AdminJob)
        .where(
            AdminJob.id == job_id,
            AdminJob.current_step == AdminJobStep.INGEST,
            AdminJob.status == AdminJobStatus.COMPLETED,
        )
        .values(
            status=AdminJobStatus.RUNNING,
            current_step=AdminJobStep.PARSE,
        )
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return result.rowcount == 1  # True = won the race; False = already spawned
```

**Important:** The `rowcount` attribute on CursorResult from asyncpg is reliable for UPDATE statements (asyncpg supports `supports_sane_rowcount`). Do not use RETURNING with this guard — RETURNING nullifies rowcount. [ASSUMED — verified via SQLAlchemy GitHub discussion #6167]

### Pattern 4: SvelteKit File Upload Action

**What:** Accept multipart/form-data PDF upload in a SvelteKit form action.
**When to use:** Start form when "Upload file" tab is active.

```typescript
// Source: https://www.okupter.com/blog/sveltekit-file-upload (verified via WebFetch)
// In /admin/pipeline/+page.server.ts

export const actions: Actions = {
  default: async ({ request, fetch }) => {
    const formData = await request.formData();
    const mode = formData.get('mode') as string; // 'url' or 'upload'

    if (mode === 'url') {
      const pdfUrl = formData.get('pdf_url') as string;
      // forward to FastAPI POST /api/admin/jobs with { pdf_url }
      const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Admin-Token': ADMIN_TOKEN },
        body: JSON.stringify({ pdf_url: pdfUrl }),
      });
      const { id } = await res.json();
      redirect(303, `/admin/pipeline/${id}`);
    } else {
      // File upload mode
      const file = formData.get('pdf_file') as File;
      const bytes = await file.arrayBuffer();
      // Forward bytes to FastAPI as multipart OR as base64
      // FastAPI performs boto3 upload → returns spaces_key + job_id
      // ... (implementation detail — see pitfall 3 re: forwarding approach)
      redirect(303, `/admin/pipeline/${id}`);
    }
  }
};
```

**Note:** The SvelteKit form must include `enctype="multipart/form-data"` on the `<form>` element for file upload to work. [VERIFIED: svelte.dev/docs/kit/form-actions]

### Pattern 5: Pipeline Subprocess DB Writes

**What:** Each subprocess writes its own progress to `admin_jobs` using the shared `pipeline/db.py` session.
**When to use:** Inside `pipeline/commands/ingest.py`, `parse.py`, `resolve.py` (modified).

```python
# Inside run_ingest(args) — after accepting --job-id arg
async with get_session() as session:
    # Update job: mark running
    await session.execute(
        update(AdminJob)
        .where(AdminJob.id == args.job_id)
        .values(status=AdminJobStatus.RUNNING, current_step=AdminJobStep.INGEST)
        .execution_options(synchronize_session=False)
    )

# ... do ingest work ...

async with get_session() as session:
    # Update job: mark completed, set argument_id
    await session.execute(
        update(AdminJob)
        .where(AdminJob.id == args.job_id)
        .values(
            status=AdminJobStatus.COMPLETED,
            argument_id=argument.id,
        )
        .execution_options(synchronize_session=False)
    )

# On exception:
async with get_session() as session:
    await session.execute(
        update(AdminJob)
        .where(AdminJob.id == args.job_id)
        .values(status=AdminJobStatus.FAILED, error_message=str(exc))
        .execution_options(synchronize_session=False)
    )
```

### Pattern 6: Resolve Discrepancy Output (D-02 / D-04 / PIPE-15)

**What:** Modified resolve command writes discrepancies to DB instead of prompting in terminal.
**When to use:** Phase 7 replace of the interactive `_prompt_operator()` loop.

```python
# In pipeline/commands/resolve.py (modified)
# When an alias MISS is found, instead of prompting:

discrepancies = []
for raw_label in alias_miss_labels:
    # Fetch candidate people for this label
    candidates = await _fetch_people_for_label(session, raw_label)
    discrepancies.append({
        "raw_speaker_label": raw_label,
        "normalized": normalize_label(raw_label),
        "candidates": [{"id": p.id, "full_name": p.full_name, "role_name": role} for p, role in candidates],
        # auto_resolved will be None for misses
        "auto_resolved": None,
    })

if discrepancies:
    # Write discrepancies and pause — operator reviews in browser
    async with get_session() as session:
        await session.execute(
            update(AdminJob)
            .where(AdminJob.id == args.job_id)
            .values(
                status=AdminJobStatus.PAUSED,
                discrepancies=discrepancies,
            )
            .execution_options(synchronize_session=False)
        )
    return  # Exit — FastAPI won't spawn next step; operator reviews

# All resolved (no misses):
async with get_session() as session:
    await session.execute(
        update(AdminJob)
        .where(AdminJob.id == args.job_id)
        .values(status=AdminJobStatus.COMPLETED)
        .execution_options(synchronize_session=False)
    )
```

### Anti-Patterns to Avoid

- **Awaiting subprocess completion:** Never call `.wait()` or `.communicate()` on the spawned Popen — blocks the FastAPI event loop.
- **Writing job progress from FastAPI:** FastAPI must only READ `admin_jobs` progress. Only pipeline subprocesses write step progress (D-02).
- **Calling `invalidateAll()` on the server:** It cannot be called during SSR — it must be inside `$effect` (client-only).
- **Using `if status == 'paused': spawn_resolve()`:** The poll endpoint should NOT re-spawn resolve after it has paused. Paused is a terminal state for polling. Only "Continue Resolve" action can advance from paused.
- **Storing PDF bytes in `admin_jobs`:** DO App Platform container filesystem is ephemeral. Always use DO Spaces for file persistence.
- **Double-migration for admin_jobs:** Migration 0003 already contains all columns. Do NOT create migration 0004 for this table (D-01 from Phase 5 context).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| S3-compatible file upload | Custom HTTP signing | `boto3` S3 client with `endpoint_url` | Request signing (SigV4) is complex and error-prone |
| Atomic double-spawn guard | Application-level lock/flag | `UPDATE ... WHERE ... AND status=X` rowcount check | DB atomicity is the only reliable distributed lock here |
| Poll state management | Component-level `$state` fetched separately | `invalidateAll()` + `+page.server.ts` load return | SvelteKit's load function is already the "server state" — no need for a separate fetch layer |
| Session auth check | Re-implementing cookie check in each admin route | Existing `hooks.server.ts` guard (Phase 6) | Already covers all `/admin/*` routes |

**Key insight:** The pattern is intentionally simple: one DB table, one poll endpoint, no in-memory state. Complexity that looks necessary (websockets, task queue, server-sent events) is explicitly out of scope.

---

## Common Pitfalls

### Pitfall 1: `X-Admin-Token` header on SvelteKit → FastAPI calls

**What goes wrong:** The SvelteKit `+page.server.ts` calls FastAPI but omits the `X-Admin-Token` header, getting 401.
**Why it happens:** Phase 6 auth is a SvelteKit session cookie, but the FastAPI router still uses `verify_admin_token` (X-Admin-Token) for server-to-server calls (D-11 in Phase 6 context).
**How to avoid:** All `fetch()` calls from `+page.server.ts` to FastAPI must include `X-Admin-Token: ${ADMIN_TOKEN}` header. Import `ADMIN_TOKEN` from `$env/static/private`.
**Warning signs:** 401 responses from FastAPI on pipeline job endpoints.

### Pitfall 2: `invalidateAll()` called during SSR

**What goes wrong:** Importing `invalidateAll` at module level or calling it outside `$effect` throws a runtime error during server-side rendering.
**Why it happens:** `$app/navigation` functions are browser-only. SSR cannot navigate.
**How to avoid:** Keep `invalidateAll()` call inside `$effect` body. `$effect` does not run on the server.
**Warning signs:** `Cannot call invalidateAll() on the server` error in console.

### Pitfall 3: Forwarding large PDF from SvelteKit to FastAPI

**What goes wrong:** SvelteKit `+page.server.ts` tries to proxy the raw multipart body to FastAPI but hits the `BODY_SIZE_LIMIT` (default 512KB) — real SCOTUS PDFs are 3–10 MB.
**Why it happens:** SvelteKit has a body size limit configurable via env var `BODY_SIZE_LIMIT`.
**How to avoid:** Set `BODY_SIZE_LIMIT=10M` in the SvelteKit environment (already identified as a known blocker in STATE.md). When forwarding to FastAPI, use `fetch` with a `FormData` body containing the file bytes, or send as `application/octet-stream` + separate metadata fields.
**Warning signs:** 413 Payload Too Large from SvelteKit before request reaches FastAPI.

### Pitfall 4: Double-spawn from concurrent poll requests

**What goes wrong:** Two simultaneous poll requests both see `status='completed'` for ingest and both spawn parse subprocesses. Two parse processes run concurrently, creating duplicate utterance rows.
**Why it happens:** FastAPI is async — multiple requests can interleave between the DB read and the spawn.
**How to avoid:** Atomic UPDATE guard (Pattern 3 above). The WHERE clause `AND status='completed' AND current_step='ingest'` ensures only one UPDATE wins; `rowcount == 0` means skip spawn. [ASSUMED — this is the pattern specified in D-05]
**Warning signs:** Duplicate utterance rows with same argument_id and different pipeline_run_ids in the parse step.

### Pitfall 5: Resolve command exits after writing discrepancies but job remains `paused` forever

**What goes wrong:** Resolve sets `status=paused` and exits. If the "Continue Resolve" endpoint receives bad data (e.g., a person_id that doesn't exist), it returns an error but doesn't reset status — the job is stuck in `paused`.
**Why it happens:** No recovery path from a failed "Continue Resolve" action.
**How to avoid:** The `POST /api/admin/jobs/{id}/resolve` endpoint must validate all person_ids exist BEFORE writing any aliases. If validation fails, return 422 without changing job status (operator can retry). [ASSUMED]
**Warning signs:** Job stuck in `paused` with no UI to correct it.

### Pitfall 6: boto3 not in requirements.txt

**What goes wrong:** `import boto3` in `api/services/spaces.py` raises `ModuleNotFoundError` at import time.
**Why it happens:** `boto3` is referenced in STATE.md and the context decisions but is NOT in the current `requirements.txt`.
**How to avoid:** Add `boto3>=1.34` to `requirements.txt` in this phase. Verify with `pip show boto3` after install.
**Warning signs:** `ModuleNotFoundError: No module named 'boto3'` on API startup.

### Pitfall 7: Pipeline subprocess spawned with wrong Python interpreter

**What goes wrong:** `subprocess.Popen(["python", "-m", "pipeline", ...])` uses the system Python, not the venv Python. The venv packages (pdfplumber, anthropic, sqlalchemy) are not found.
**Why it happens:** `python` on PATH may not be the venv interpreter.
**How to avoid:** Use `sys.executable` to get the current interpreter path: `subprocess.Popen([sys.executable, "-m", "pipeline", ...], ...)`. [VERIFIED: Python subprocess docs recommend sys.executable for spawning same-interpreter subprocesses]
**Warning signs:** `ModuleNotFoundError` in subprocess (not visible at runtime since stderr is DEVNULL — only visible if job transitions to `failed` with error_message).

### Pitfall 8: `updated_at` not updating on pipeline subprocess writes

**What goes wrong:** The `admin_jobs.updated_at` column doesn't change when the subprocess updates status, so polling-based "last updated" displays are stale.
**Why it happens:** `updated_at` uses SQLAlchemy's `onupdate=func.now()` — but this only fires via ORM-level UPDATE, not raw `.execute(update(...).values(...))` calls from the pipeline subprocess.
**How to avoid:** The migration 0003 already includes a PostgreSQL `BEFORE UPDATE` trigger (`trg_admin_jobs_updated_at`) that sets `updated_at = NOW()` regardless of how the UPDATE is issued. No code change needed. This is already handled.
**Warning signs:** (Not applicable — already handled by DB trigger.)

---

## Code Examples

### DO Spaces Upload via boto3

```python
# Source: https://www.digitalocean.com/community/questions/... (verified via WebFetch)
# api/services/spaces.py

import boto3
from api.core.config import settings

def get_spaces_client():
    session = boto3.session.Session()
    return session.client(
        's3',
        region_name=settings.do_spaces_region,       # e.g. "nyc3"
        endpoint_url=settings.do_spaces_endpoint,    # e.g. "https://nyc3.digitaloceanspaces.com"
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )

def upload_pdf_to_spaces(file_bytes: bytes, key: str) -> str:
    """Upload PDF bytes to DO Spaces, return the spaces_key."""
    import io
    client = get_spaces_client()
    client.upload_fileobj(
        io.BytesIO(file_bytes),
        settings.do_spaces_bucket,
        key,
        ExtraArgs={'ContentType': 'application/pdf'},
    )
    return key
```

### Pydantic Schemas for Admin Job Endpoints

```python
# api/schemas/admin_jobs.py [ASSUMED structure based on existing schema patterns]
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel
from api.models.models import AdminJobStatus, AdminJobStep

class AdminJobCreateURL(BaseModel):
    pdf_url: str

class AdminJobResponse(BaseModel):
    id: int
    status: AdminJobStatus
    current_step: Optional[AdminJobStep] = None
    argument_id: Optional[int] = None
    pdf_url: Optional[str] = None
    spaces_key: Optional[str] = None
    discrepancies: Optional[Any] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class ResolveMatch(BaseModel):
    raw_speaker_label: str
    person_id: int           # confirmed or corrected person_id

class ResolveRequest(BaseModel):
    matches: list[ResolveMatch]

class PersonCreate(BaseModel):
    full_name: str
    role_id: Optional[int] = None  # may be new role created client-side
```

### FastAPI Admin Route Skeleton

```python
# api/routers/admin.py additions [ASSUMED — follows existing people.py pattern]
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from api.core.database import get_db
from api.schemas.admin_jobs import AdminJobResponse, ResolveRequest

@router.post("/jobs", response_model=AdminJobResponse, status_code=202)
async def create_job(
    pdf_url: Optional[str] = Form(None),
    pdf_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    """Create a new pipeline job and spawn ingest subprocess."""
    ...

@router.get("/jobs/{job_id}", response_model=AdminJobResponse)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    """Poll job state; triggers step-advance as side effect."""
    ...

@router.get("/jobs", response_model=list[AdminJobResponse])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
) -> list[AdminJobResponse]:
    """List most recent 10 jobs for history table."""
    ...

@router.post("/jobs/{job_id}/resolve", response_model=AdminJobResponse)
async def resolve_job(
    job_id: int,
    body: ResolveRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    """Write confirmed alias matches and mark job completed."""
    ...

@router.post("/jobs/{job_id}/people", response_model=PersonResponse, status_code=201)
async def create_person_for_job(
    job_id: int,
    body: PersonCreate,
    db: AsyncSession = Depends(get_db),
) -> PersonResponse:
    """Create a new person record during discrepancy review (D-13)."""
    ...
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `export let x` in Svelte | `let x = $props()` in Svelte 5 Runes | Svelte 5 (project uses exclusively) | Runes are the project standard — never use legacy syntax |
| `onMount` + `onDestroy` for setInterval | `$effect` returning cleanup fn | Svelte 5 | `$effect` is the canonical pattern; no lifecycle imports needed |
| `throw redirect()` in SvelteKit 1 actions | `redirect()` without throw in SvelteKit 2 | SvelteKit 2.0 | Either works in SvelteKit 2 per docs; project already uses `throw redirect` (login action) — stay consistent |
| `asyncio.create_subprocess_exec` | `subprocess.Popen` (D-01 decision) | Phase 7 decision | Avoids asyncio nesting; one OS process per step |

**Deprecated/outdated:**
- `export let` Svelte syntax: Project explicitly prohibits it. Use `$props()`.
- `$:` reactive statements: Project prohibits. Use `$derived` or `$effect`.
- `Base.metadata.create_all()`: CLAUDE.md hard constraint. Never call this.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | boto3 is not in requirements.txt and must be added | Standard Stack / Pitfall 6 | Low risk — verified by reading requirements.txt directly |
| A2 | boto3 legitimacy (described as official AWS SDK) | Package Legitimacy Audit | Very low — overwhelming public evidence; formal legitimacy check not run |
| A3 | `result.rowcount` is reliable for UPDATE with asyncpg | Pattern 3 | Medium — if rowcount returns -1, double-spawn guard fails silently; test this pattern explicitly |
| A4 | SvelteKit form can forward file bytes to FastAPI via fetch FormData | Pattern 4 | Medium — large PDFs may hit BODY_SIZE_LIMIT at SvelteKit edge; set BODY_SIZE_LIMIT=10M |
| A5 | `CREATE_NEW_PROCESS_GROUP` on Windows prevents zombie subprocess | Pattern 2 | Low risk — Python's internal `_cleanup()` also reaps zombies; this is belt-and-suspenders |
| A6 | Pydantic schemas for admin_jobs (structure) | Code Examples | Low — follows existing project schema patterns; exact field names may differ |
| A7 | DO Spaces region env var naming convention (`do_spaces_region`, etc.) | Code Examples | Low — exact env var names must be added to `api/core/config.py` Settings class |

---

## Open Questions

1. **How should file bytes be forwarded from SvelteKit to FastAPI?**
   - What we know: SvelteKit `+page.server.ts` receives the `File` object via `request.formData()`. FastAPI can accept `UploadFile` directly.
   - What's unclear: Whether SvelteKit should call FastAPI with a multipart body or first convert to base64/bytes and send JSON.
   - Recommendation: Send as multipart `FormData` from SvelteKit server to FastAPI using `fetch` with a `FormData` body — this is the natural mapping and avoids base64 overhead for 3–10 MB PDFs. Verify `BODY_SIZE_LIMIT=10M` is set before testing.

2. **What is the ingest subprocess's `--url` or `--spaces-key` argument shape for uploaded files?**
   - What we know: Current `run_ingest(args)` accepts `--url` (must be a supremecourt.gov HTTPS URL). For uploads, the PDF comes from Spaces (not a URL).
   - What's unclear: Whether the ingest command needs a new `--spaces-key` flag (reads from Spaces) or whether FastAPI downloads the file from Spaces and provides a local temp path.
   - Recommendation: Add `--spaces-key` flag to the ingest command so it can fetch the file from Spaces itself. This keeps the subprocess self-contained and avoids FastAPI holding large file bytes in memory.

3. **Does the poll endpoint need rate limiting?**
   - What we know: The operator runs one or two jobs per month, single user. No external traffic.
   - What's unclear: Whether 2.5s polling from a single admin user warrants any protection.
   - Recommendation: No rate limiting needed for v1.1. The `verify_admin_token` dependency already gates all admin routes.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | Pipeline subprocesses | ✓ | 3.14.4 (detected) | — |
| Node.js | SvelteKit build/dev | ✓ | v24.15.0 (detected) | — |
| PostgreSQL | DB layer | ✓ (assumed local dev) | 16 (per project spec) | — |
| boto3 | DO Spaces upload (PIPE-13) | ✗ | Not installed | Must add to requirements.txt |
| DO Spaces credentials | PIPE-13 file upload | Unknown | — | Phase 7 cannot implement PIPE-13 without `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `DO_SPACES_BUCKET`, `DO_SPACES_ENDPOINT` env vars |

**Missing dependencies with no fallback:**
- `boto3` — must be added to `requirements.txt` before PIPE-13 can be implemented
- DO Spaces env vars — operator must configure before first file upload; URL-mode (PIPE-12) works without them

**Missing dependencies with fallback:**
- If DO Spaces credentials are absent, the URL-mode path (PIPE-12) still works end-to-end. File upload (PIPE-13) requires credentials.

---

## Security Domain

> `security_enforcement` is not explicitly disabled in config.json; treating as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | SvelteKit session cookie (Phase 6 `hooks.server.ts`) — already in place |
| V3 Session Management | Yes | 24h expiry HMAC cookie — already in place |
| V4 Access Control | Yes | All `/api/admin/*` routes behind `verify_admin_token` dependency |
| V5 Input Validation | Yes | FastAPI Pydantic v2 schemas validate all request bodies; `pdf_url` must be validated against supremecourt.gov domain before any HTTP fetch |
| V6 Cryptography | No | No new crypto — existing session HMAC unchanged |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSRF via pdf_url | Spoofing/Elevation | `_validate_url()` in `pipeline/commands/ingest.py` already enforces `https://...supremecourt.gov/...` — ensure this validation runs before any subprocess is spawned, not just inside subprocess |
| Command injection via form fields | Tampering | All subprocess args are typed (int job_id, str url) — never pass raw form input as shell args; `shell=False` (default) prevents shell injection |
| File upload of non-PDF | Tampering | Validate `content_type == 'application/pdf'` and file extension on the FastAPI `UploadFile` |
| Unauthenticated job creation | Elevation | `verify_admin_token` dependency on router covers all routes including new job endpoints |
| Admin token in response | Information Disclosure | `verify_admin_token` already logs/returns only the string "Unauthorized" — never echo token |

**SSRF Note:** The URL validation currently lives inside `pipeline/commands/ingest.py`. For Phase 7, the FastAPI `POST /api/admin/jobs` endpoint should also validate the URL before creating the job row and spawning the subprocess — defense in depth.

---

## Validation Architecture

> `workflow.nyquist_validation` is explicitly `false` in `.planning/config.json` — this section is omitted per spec.

---

## Sources

### Primary (MEDIUM confidence)
- [svelte.dev/docs/svelte/$effect](https://svelte.dev/docs/svelte/$effect) — `$effect` cleanup pattern, setInterval usage
- [svelte.dev/docs/kit/form-actions](https://svelte.dev/docs/kit/form-actions) — file upload, redirect after POST
- [svelte.dev/tutorial/kit/invalidate-all](https://svelte.dev/tutorial/kit/invalidate-all) — invalidateAll() behavior vs invalidate()
- [docs.python.org/3/library/subprocess.html](https://docs.python.org/3/library/subprocess.html) — Popen DEVNULL, start_new_session, CREATE_NEW_PROCESS_GROUP
- [digitalocean.com community docs](https://www.digitalocean.com/community/questions/how-to-upload-an-object-to-digital-ocean-spaces-using-python-boto3-library) — boto3 + DO Spaces upload pattern

### Secondary (LOW confidence)
- [docs.sqlalchemy.org/en/21/tutorial/data_update.html](https://docs.sqlalchemy.org/en/21/tutorial/data_update.html) — rowcount on UPDATE
- [github.com/sqlalchemy/sqlalchemy/discussions/6167](https://github.com/sqlalchemy/sqlalchemy/discussions/6167) — rowcount with async sessions
- WebSearch results for FastAPI fire-and-forget subprocess pattern
- WebSearch results for boto3 DO Spaces upload examples

### Tertiary (training knowledge, tagged ASSUMED)
- Pydantic v2 schema structure for admin_jobs
- DO Spaces env var naming conventions
- FastAPI UploadFile for multipart handling

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — all packages except boto3 already in project; boto3 verified as not in requirements.txt
- Architecture: HIGH — all architectural decisions are locked in 07-CONTEXT.md; no ambiguity
- Subprocess/polling patterns: MEDIUM — verified via official Python docs and SvelteKit docs
- boto3 DO Spaces pattern: MEDIUM — verified via DigitalOcean official community docs
- Atomic rowcount guard: LOW — logic is sound but asyncpg rowcount reliability needs explicit testing

**Research date:** 2026-06-16
**Valid until:** 2026-07-16 (stable tech stack — 30 days)
