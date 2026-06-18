# Phase 7: Pipeline Runner - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-16
**Phase:** 07-pipeline-runner
**Areas discussed:** Subprocess model, Page flow & start UI, Discrepancy review UX, Client-side polling

---

## Subprocess Model

| Option | Description | Selected |
|--------|-------------|----------|
| subprocess.Popen | New OS process per step; no asyncio conflict; needs env/PATH management | ✓ |
| Import functions directly | Simpler but asyncio.run() nesting breaks inside async FastAPI handler | |
| asyncio.create_subprocess_exec | Async-native subprocess; works in event loop | |

**User's choice:** subprocess.Popen

---

| Option | Description | Selected |
|--------|-------------|----------|
| Discard (DEVNULL) | All meaningful state in DB; logs ephemeral | ✓ |
| Write to log file per job | Useful for debugging; adds file management complexity | |
| Capture stderr to error_message | Only on failure; good middle ground | |

**User's choice:** Discard — "You decide"
**Notes:** Claude's discretion on exact routing.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Polling DB | Pipeline writes final status to admin_jobs; FastAPI reads; clean decoupling | ✓ |
| Non-blocking process.poll() | Stores Popen in module-level dict; breaks on DO restart | |

**User's choice:** Polling DB

---

| Option | Description | Selected |
|--------|-------------|----------|
| Pipeline subprocess updates admin_jobs directly | Accepts --job-id; single writer | ✓ |
| FastAPI updates admin_jobs based on pipeline_runs | No pipeline changes; requires joining two tables | |

**User's choice:** Pipeline subprocess updates admin_jobs directly

---

| Option | Description | Selected |
|--------|-------------|----------|
| One subprocess per step | Easier PIPE-15 pausing; each step independent | ✓ |
| One subprocess for full run | New wrapper script; more orchestration complexity | |

**User's choice:** One subprocess per step

---

| Option | Description | Selected |
|--------|-------------|----------|
| FastAPI poll endpoint triggers step-advance | Centralized in API layer | ✓ |
| Background thread/task in FastAPI | Long-lived coroutine; doesn't survive DO restarts | |

**User's choice:** FastAPI poll endpoint (side effect of poll response)

---

| Option | Description | Selected |
|--------|-------------|----------|
| DB status guard (atomic UPDATE WHERE) | Prevents double-spawn via Postgres atomics | ✓ |
| Separate /advance endpoint | Cleaner separation but extra round-trip | |
| You decide | Leave to planner | |

**User's choice:** DB status guard

---

## Page Flow & Start UI

| Option | Description | Selected |
|--------|-------------|----------|
| Always show start form | Landing always shows New Run form; prior runs below | ✓ |
| Smart landing | Active job → status page; otherwise form | |

**User's choice:** Always show start form
**Notes:** User clarified that previous runs must still be accessible even if not the landing — listed below the form.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Below the start form on /admin/pipeline | Simple list under form; no separate route | ✓ |
| Separate /admin/pipeline/history page | Dedicated page; cleaner but adds route | |

**User's choice:** Below the start form

---

| Option | Description | Selected |
|--------|-------------|----------|
| Redirect to /admin/pipeline/[job_id] | Dedicated URL per job; supports PIPE-17 resumability | ✓ |
| Stay on /admin/pipeline, status replaces form | URL doesn't change; browser resume harder | |

**User's choice:** Redirect to /admin/pipeline/[job_id]

---

| Option | Description | Selected |
|--------|-------------|----------|
| Two-tab or toggle form | One form, two modes; only one input visible at a time | ✓ |
| Two separate inputs always visible | Both inputs shown; validation enforces exactly one filled | |

**User's choice:** Two-tab or toggle form

---

| Option | Description | Selected |
|--------|-------------|----------|
| Three step cards in a vertical stack | Ingest/Parse/Resolve cards with status badges; discrepancy inline in paused card | ✓ |
| Single progress bar with step labels | Horizontal bar; discrepancy in modal | |
| You decide | Any clear visualization within dark theme | |

**User's choice:** Three step cards in a vertical stack

---

## Discrepancy Review UX

| Option | Description | Selected |
|--------|-------------|----------|
| Table: raw label → suggested person, Confirm/Correct per row | Per-row granularity; most control | ✓ |
| One-at-a-time wizard | Lower cognitive load for large batches | |
| Bulk actions only | Fastest but no per-match control | |

**User's choice:** Table with per-row Confirm/Correct

---

| Option | Description | Selected |
|--------|-------------|----------|
| Dropdown of existing people records | Searchable select from people table | ✓ + "Add new person" |
| Text input with autocomplete | Freeform typing against people table | |
| Modal with full people directory | More screen real estate | |

**User's choice:** Dropdown of existing people + "Add new person" option
**Notes:** User specified "Add new person" must be available for first-time advocates not yet in the DB.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Name + Role only | Minimal creation; bio/photo/tenure for Phase 8 | ✓ |
| Name only | Simpler; role defaults to null | |
| Full person form inline | Overlaps Phase 8 scope | |

**User's choice:** Name + Role only

---

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit "Continue Resolve" button | Operator reviews all rows before committing | ✓ |
| Auto-advance when last row resolved | Faster but no final review moment | |

**User's choice:** Explicit "Continue Resolve" button

---

## Client-Side Polling

| Option | Description | Selected |
|--------|-------------|----------|
| setInterval + invalidateAll() | Re-runs load function; all state in page.data | ✓ |
| setInterval + client-side fetch to +server.ts | Partial update; mixes data sources | |

**User's choice:** setInterval + invalidateAll()

---

| Option | Description | Selected |
|--------|-------------|----------|
| Stop on terminal state | Stop at completed/failed/paused; resume after Continue | ✓ |
| Always poll while on page | Simpler but wastes requests on completed jobs | |

**User's choice:** Stop on terminal state

---

| Option | Description | Selected |
|--------|-------------|----------|
| GET /api/admin/jobs/{id} — full job state | One endpoint; discrepancies inline | ✓ |
| Split status + discrepancies endpoints | Smaller poll payload; more endpoints | |

**User's choice:** Single GET /api/admin/jobs/{id}

---

| Option | Description | Selected |
|--------|-------------|----------|
| Failed step card with error_message | Per-step breakdown; no retry button | ✓ |
| Generic error banner | Simple but no detail | |
| Error with Retry button | Adds retry complexity | |

**User's choice:** Failed step card with error_message inline

---

## Claude's Discretion

- stdout/stderr routing (DEVNULL vs. capture on failure)
- Exact step card visual styling within dark admin theme
- Toggle/tab styling for URL vs. file upload mode switch
- Whether "Add new person" form appears inline below dropdown or in small modal
- Whether to use `invalidateAll()` or targeted `invalidate(url)` for polling

## Deferred Ideas

None — discussion stayed within phase scope.
