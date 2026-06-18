---
phase: 07-pipeline-runner
verified: 2026-06-17T00:00:00Z
status: verified
score: 18/18
overrides_applied: 0
note: "human_needed resolved 2026-06-18 — 18/18 truths verified code-level; behavioral UX gaps (discrepancy HIT rows, typeahead, add-person) confirmed fixed by 07-07 human verification (all 5 checks approved 2026-06-17); cases-premature-visibility confirmed fixed by 07-08 migration; Phase 8 completed 10/10 UAT pass providing end-to-end confirmation"
human_verification:
  - test: "Live polling step cards advance Ingest→Parse→Resolve without page reload"
    expected: "Three step cards update every 2.5s; Ingest completes, Parse card transitions to Running, then Resolve"
    why_human: "Requires a running FastAPI server, a running pipeline subprocess, and a live DB — cannot verify setInterval behavior programmatically"
  - test: "Resolve pauses and discrepancy table renders correctly for both HIT and MISS rows"
    expected: "When resolve pauses, all speaker labels appear — HIT rows show 'Auto-matched' with auto_match_name and Confirm button; MISS rows show candidates dropdown"
    why_human: "Requires a real pipeline run to produce a paused job with discrepancies JSONB in the DB; UI rendering of HIT vs MISS row distinction requires browser"
  - test: "Confirm button records auto_match_id; Override button resets the row to Confirm+Correct state"
    expected: "Clicking Confirm on a HIT row shows '✓ Confirmed {name}' and Override button; Override returns to initial state with Confirm+Correct buttons"
    why_human: "Client-side rowStates interaction — requires browser rendering"
  - test: "Typeahead correction dropdown filters candidates as operator types"
    expected: "Clicking Correct opens text input with datalist; typing filters candidates; selecting one freezes row as '✓ Corrected'; Override appears"
    why_human: "Datalist/combobox interaction requires browser"
  - test: "Add new person flow: fill name+role → Save person → person auto-selected in row without page refresh"
    expected: "Selecting '— Add new person —' reveals inline form; Save person creates person via addPerson action with x-sveltekit-action header; person appears in dropdown and is auto-selected; form dismisses"
    why_human: "Requires live FastAPI call and correct SvelteKit envelope parsing; browser interaction required"
  - test: "Continue Resolve disables button immediately and transitions Resolve card away from paused"
    expected: "Clicking Continue Resolve: button text becomes 'Submitting…' with real disabled attribute before network request fires; on success Resolve card transitions from 'Needs review'; polling restarts"
    why_human: "use:enhance synchronous callback timing requires browser observation; transition of card state after invalidateAll requires live reload"
  - test: "Failed job shows verbatim error_message and no retry button"
    expected: "error_message rendered in monospace pre-wrap exactly as stored; 'Start a new run' link present; no retry button"
    why_human: "Requires a failed pipeline job in the DB; UI rendering verification requires browser"
  - test: "Closing and reopening the job URL renders job exactly where it paused (PIPE-17 resumability)"
    expected: "SSR load fetches current job state; paused job shows discrepancy table again; polling does not start for paused status"
    why_human: "Requires browser navigation to a paused job URL; SSR render correctness requires actual HTTP request"
---

# Phase 07: Pipeline Runner Verification Report

**Phase Goal:** Pipeline Runner — an operator-only admin UI that drives the existing offline pipeline (ingest, parse, resolve) end-to-end via a web interface, with live step-progress polling, discrepancy review when resolve pauses, and resumability.
**Verified:** 2026-06-17T00:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | boto3 import succeeds at API startup | VERIFIED | `requirements.txt` line 14: `boto3>=1.34`; `api/services/spaces.py` imports boto3 at module level; `api/core/config.py` has five optional DO Spaces fields |
| 2 | AdminJobResponse can be constructed from an AdminJob ORM row | VERIFIED | `api/schemas/admin_jobs.py` lines 17–31: `model_config = {"from_attributes": True}` on `AdminJobResponse` |
| 3 | Atomic advance guard returns True once and False the second time for same transition | VERIFIED | `api/services/admin_jobs.py` lines 99–110 and 119–130: `update(AdminJob).where(step+status).values(...).execution_options(synchronize_session=False)` returns `result.rowcount == 1`; no RETURNING clause |
| 4 | spawn_pipeline_step launches a detached subprocess using sys.executable and returns immediately | VERIFIED | `api/services/pipeline_spawn.py` lines 19–41: uses `sys.executable`, `subprocess.DEVNULL`, `CREATE_NEW_PROCESS_GROUP` (win32) / `start_new_session=True` (posix); no `.wait()` or `.communicate()` |
| 5 | get_run_id_for_step returns most recent pipeline_run id for (argument_id, step) — enabling PIPE-17 | VERIFIED | `api/services/admin_jobs.py` lines 138–171: queries `PipelineRun` filtering on `.argument_id` and `.step`, ordered by `created_at.desc()`, limit 1 |
| 6 | POST /api/admin/jobs with valid supremecourt.gov url creates job and spawns ingest, returning 202 | VERIFIED | `api/routers/admin.py` lines 112–135: `@router.post("/jobs", status_code=202)`; calls `_validate_pdf_url`, `create_job`, `spawn_pipeline_step("ingest", ...)` |
| 7 | POST /api/admin/jobs with non-supremecourt.gov URL returns 422 and creates no job | VERIFIED | `api/routers/admin.py` lines 83–103: `_validate_pdf_url` raises `HTTPException(422)` before `create_job` is called |
| 8 | GET /api/admin/jobs/{id} poll endpoint spawns next step once via atomic guards, re-derives run-id (PIPE-17) | VERIFIED | `api/routers/admin.py` lines 182–233: calls `try_advance_ingest_to_parse` / `try_advance_parse_to_resolve`; only spawns when guard returns True; calls `get_run_id_for_step(db, job_id, "ingest")` and `get_run_id_for_step(db, job_id, "parse")` before spawning |
| 9 | GET /api/admin/jobs/{id} does NOT advance a paused/failed/completed job | VERIFIED | `api/routers/admin.py` lines 207–231: advance branches only fire on INGEST/COMPLETED and PARSE/COMPLETED; comment confirms PAUSED/FAILED/COMPLETED are terminal |
| 10 | Each pipeline subcommand accepts --job-id; backward compatible when absent | VERIFIED | `pipeline/__main__.py` lines 103–108 (ingest), 133–138 (parse), 158–163 (resolve): all add `--job-id` with `required=False, default=None` |
| 11 | When --job-id set, ingest/parse/resolve write their own status to admin_jobs | VERIFIED | `pipeline/commands/ingest.py`: RUNNING/COMPLETED+argument_id/FAILED writes confirmed by grep; `pipeline/commands/parse.py`: RUNNING/COMPLETED/FAILED confirmed; `pipeline/commands/resolve.py`: RUNNING/PAUSED+discrepancies/COMPLETED/FAILED confirmed |
| 12 | Resolve no longer prompts terminal on alias misses; writes discrepancies JSONB + pauses | VERIFIED | `pipeline/commands/resolve.py`: `_prompt_operator` not found in file (grep confirmed absence); `AdminJobStatus.PAUSED` at line 352; `discrepancies=discrepancies` at line 353 |
| 13 | HIT rows appended to discrepancies with auto_resolved=True (Plan 06 gap closure) | VERIFIED | `pipeline/commands/resolve.py` lines 239–249: HIT branch appends dict with `"auto_resolved": True`, `auto_match_id`, `auto_match_name`, `auto_match_role` after utterance update |
| 14 | Pipeline Runner nav link is a real link to /admin/pipeline | VERIFIED | `app/src/routes/admin/+layout.svelte` line 28–33: `<a href="/admin/pipeline">Pipeline Runner</a>`; People Editor remains `aria-disabled="true"` span |
| 15 | Operator can create a job by URL or file upload; lands on job status page | VERIFIED | `app/src/routes/admin/pipeline/+page.server.ts`: `actions.default` branches on mode (url/upload); URL mode posts FormData to FastAPI; upload mode appends File and forwards; both `throw redirect(303, /admin/pipeline/${id})` on success |
| 16 | Three step cards poll every 2.5s; stop on terminal states | VERIFIED (code) | `app/src/routes/admin/pipeline/[job_id]/+page.svelte` lines 39–48: `$effect` with `TERMINAL = new Set(['completed','failed','paused'])`; `setInterval(2500ms, invalidateAll)`; returns `clearInterval` cleanup — behavioral correctness needs human |
| 17 | Discrepancy review renders Confirm/Correct/Override per row; Continue Resolve posts matches via use:enhance | VERIFIED (code) | `+page.svelte` lines 553–618: Confirm button (HIT rows only), Correct button, Override button resets disposition; lines 631–673: resolve form with `use:enhance` callback that sets `continueSubmitting=true` synchronously — behavioral correctness needs human |
| 18 | PersonResponse includes role_name; addPerson envelope parsed correctly via x-sveltekit-action header | VERIFIED | `api/schemas/admin_jobs.py` line 61: `role_name: Optional[str] = None` on `PersonResponse`; `+page.svelte` lines 238–242: `headers: { 'x-sveltekit-action': 'true' }` on addPerson fetch |

**Score:** 18/18 truths verified (code-level)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/schemas/admin_jobs.py` | 6 Pydantic schemas with from_attributes on response models | VERIFIED | All 6 classes present; `from_attributes` on AdminJobResponse and PersonResponse; ResolveMatch/ResolveRequest wired correctly |
| `api/services/spaces.py` | upload_pdf_to_spaces via boto3 S3 client | VERIFIED | `upload_fileobj` present at line 44; `ContentType: application/pdf`; imports `settings` from `api.core.config` |
| `api/services/pipeline_spawn.py` | spawn_pipeline_step detached Popen with DEVNULL | VERIFIED | `sys.executable`, `DEVNULL`, `CREATE_NEW_PROCESS_GROUP`, `start_new_session`; no `.wait()`/`.communicate()` |
| `api/services/admin_jobs.py` | 8 service functions, atomic guards, run-id lookup, resolve | VERIFIED | All 8 functions present; 8x `synchronize_session=False`; rowcount guard no RETURNING; normalize_label imported from pipeline |
| `api/core/config.py` | Five optional DO Spaces settings fields | VERIFIED | Lines 43–47: `aws_access_key_id`, `aws_secret_access_key`, `do_spaces_bucket`, `do_spaces_endpoint`, `do_spaces_region` all `= ""`; deployment tier note in comment block |
| `api/routers/admin.py` | 5 job routes + _validate_pdf_url | VERIFIED | POST /jobs (202), GET /jobs, GET /jobs/{id}, POST /jobs/{id}/resolve, POST /jobs/{id}/people all present; `_validate_pdf_url` with supremecourt.gov check |
| `pipeline/__main__.py` | --job-id on all 3 subparsers; --spaces-key on ingest | VERIFIED | --job-id on ingest/parse/resolve; --spaces-key on ingest; WindowsSelectorEventLoopPolicy intact |
| `pipeline/commands/resolve.py` | Discrepancy-pause exit; HIT rows in discrepancies with auto_resolved=True | VERIFIED | `AdminJobStatus.PAUSED` at line 352; HIT branch appends to discrepancies; `_prompt_operator` absent from file |
| `app/src/routes/admin/+layout.svelte` | Pipeline Runner as real link | VERIFIED | `<a href="/admin/pipeline">` present; People Editor is `aria-disabled` span |
| `app/src/routes/admin/pipeline/+page.server.ts` | load + default action (create job + redirect) | VERIFIED | load fetches GET /api/admin/jobs with X-Admin-Token; action branches url/upload; throws redirect(303) on success |
| `app/src/routes/admin/pipeline/+page.svelte` | ModeToggle, URL/file inputs, Start Run, HistoryTable, empty state | VERIFIED | multipart/form-data; aria-pressed on mode toggle; "No runs yet" empty state; "Start Run" button with min-height 44px; StatusBadge with UI-SPEC colors |
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | load + named actions resolve + addPerson | VERIFIED | load fetches job-by-id, throws error(404); actions.resolve POSTs matches with Content-Type json; actions.addPerson POSTs to people endpoint; named actions (no default) |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | Polling effect, 3 StepCards, DiscrepancyTable, Override, use:enhance, error panel | VERIFIED | invalidateAll + setInterval 2500ms in $effect; terminal guard; Override button at line 555; use:enhance at line 634; x-sveltekit-action header; error panel verbatim at line 693 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `api/services/spaces.py` | `api/core/config.py settings` | `settings.do_spaces_*` | VERIFIED | `spaces.py` imports `settings` from `api.core.config`; uses `settings.do_spaces_region`, `.do_spaces_endpoint`, etc. |
| `api/services/admin_jobs.py` | AdminJob ORM model | `update(AdminJob)` | VERIFIED | Multiple `update(AdminJob)` calls in try_advance_*, resolve_job |
| `api/routers/admin.py GET /jobs/{id}` | `try_advance_* + spawn_pipeline_step` | step-advance side effect | VERIFIED | Lines 211–228: advance guards called; spawn fired when guard returns True |
| `api/routers/admin.py GET /jobs/{id}` | `get_run_id_for_step` | resumable --run-id lookup (PIPE-17) | VERIFIED | Lines 213 and 225: `get_run_id_for_step(db, job_id, "ingest")` and `"parse"` both present |
| `api/routers/admin.py POST /jobs` | `upload_pdf_to_spaces` | upload mode | VERIFIED | Line 153: `spaces_service.upload_pdf_to_spaces(file_bytes, key)` in upload branch |
| `app/src/routes/admin/pipeline/+page.server.ts` | FastAPI POST /api/admin/jobs | fetch with X-Admin-Token | VERIFIED | Lines 42–48 and 77–83: `X-Admin-Token: ADMIN_TOKEN` header on both branches |
| `app/src/routes/admin/+layout.svelte` | `/admin/pipeline` | anchor href | VERIFIED | `href="/admin/pipeline"` at line 29 |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | `+page.server.ts load via invalidateAll` | setInterval 2500ms in effect | VERIFIED (code) | `setInterval` at line 43; behavioral verification needs human |
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts resolve action` | FastAPI POST /api/admin/jobs/{id}/resolve | fetch with X-Admin-Token | VERIFIED | Lines 43–50: correct endpoint, JSON body, X-Admin-Token, Content-Type json |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | `?/addPerson via fetch` | x-sveltekit-action header returns JSON envelope | VERIFIED | Line 240: `headers: { 'x-sveltekit-action': 'true' }`; line 243: `const envelope = await res.json()`; line 252: `envelope?.data?.person` |
| `pipeline/commands/resolve.py` | `admin_jobs.discrepancies JSONB` | HIT rows with auto_resolved=True | VERIFIED | Lines 239–249: dict with `"auto_resolved": True` appended to discrepancies list in HIT branch |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `app/src/routes/admin/pipeline/+page.svelte` | `data.jobs` | `+page.server.ts load` fetches `GET /api/admin/jobs` → `list_jobs(db, limit=10)` → DB select | Yes — SQL SELECT on AdminJob table, ordered by created_at desc | FLOWING |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | `data.job` | `+page.server.ts load` fetches `GET /api/admin/jobs/{id}` → `get_job(db, job_id)` → DB select | Yes — SQL SELECT on AdminJob by pk | FLOWING |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | `data.job.discrepancies` | Written by `pipeline/commands/resolve.py` post-session block — `update(AdminJob).values(discrepancies=discrepancies)` | Yes — real discrepancy dicts from alias table lookup | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `api/services/pipeline_spawn.py` module imports without error | Module structure check (grep for sys.executable, DEVNULL) | Both present; no .wait/.communicate | PASS |
| `api/schemas/admin_jobs.py` contains from_attributes | grep `from_attributes` | Line 31: `model_config = {"from_attributes": True}` | PASS |
| `pipeline/commands/resolve.py` has no _prompt_operator | grep `_prompt_operator` | Not found | PASS |
| `pipeline/__main__.py` WindowsSelectorEventLoopPolicy intact | grep | Line 31 confirmed | PASS |
| `api/services/admin_jobs.py` synchronize_session=False count >= 3 | grep count | 8 occurrences | PASS |
| `api/services/admin_jobs.py` rowcount == 1 without RETURNING | grep `rowcount == 1` and absence of `returning(` | rowcount == 1 at lines 110, 130; no RETURNING clause | PASS |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` no legacy Svelte syntax | grep `export let`, `$:`, store imports | No matches | PASS |
| `app/src/routes/admin/pipeline/+page.svelte` no legacy Svelte syntax | grep `export let`, `$:`, store imports | No matches | PASS |

Note: Full integration behavioral checks (running server, subprocess spawning, DB writes, polling in browser) are routed to human verification below.

### Probe Execution

No `scripts/*/tests/probe-*.sh` files found for this phase. Phase does not declare probes in PLAN frontmatter.

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| PIPE-12 | 07-01, 07-02, 07-04 | Operator can start a new pipeline run by entering a transcript PDF URL | SATISFIED | `_validate_pdf_url` + `create_job` + `spawn_pipeline_step("ingest")` in POST /api/admin/jobs URL branch; `/admin/pipeline` start page URL input with mode='url' form action |
| PIPE-13 | 07-01, 07-02, 07-04 | Operator can start a new pipeline run by uploading a local PDF file | SATISFIED | Upload branch in POST /api/admin/jobs: validates content_type, uploads to DO Spaces via `upload_pdf_to_spaces`, spawns ingest with --spaces-key; `+page.svelte` has file input mode with multipart/form-data |
| PIPE-14 | 07-02, 07-03, 07-05 | Running pipeline displays step status and auto-advances when each step completes | SATISFIED (code) | GET /api/admin/jobs/{id} poll endpoint advances INGEST→PARSE→RESOLVE via atomic guards; `+page.svelte` polls 2.5s via setInterval; StepCards render per stepStatus() helper — live behavior needs human verification |
| PIPE-15 | 07-03, 07-05, 07-06 | Pipeline pauses after resolve when discrepancies exist and displays them for review | SATISFIED (code) | `resolve.py` writes `status=PAUSED, discrepancies=...` on miss or HIT rows; DiscrepancyTable renders in Resolve card when `data.job.status === 'paused'` — UI rendering needs human verification |
| PIPE-16 | 07-02, 07-05, 07-06 | Operator can confirm or correct speaker alias matches; confirmed matches saved to alias table | SATISFIED (code) | `resolve_job` service upserts SpeakerAlias; `+page.svelte` Confirm/Correct/Override buttons; `use:enhance` on resolve form POSTs matches; `+page.server.ts resolve action` calls `/resolve` endpoint — end-to-end write flow needs human verification |
| PIPE-17 | 07-01, 07-02, 07-03, 07-05 | Pipeline job state persisted to DB; operator can close browser and resume | SATISFIED | `get_run_id_for_step` re-derives run-id from pipeline_runs on every poll (no cached state); SSR load in `[job_id]/+page.server.ts` always fetches current job state; paused job stays paused on reload; polling $effect stops on terminal states |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| No debt markers (TBD/FIXME/XXX) found in any modified file | — | — | — | — |

Scanned files: `api/schemas/admin_jobs.py`, `api/services/spaces.py`, `api/services/pipeline_spawn.py`, `api/services/admin_jobs.py`, `api/core/config.py`, `api/routers/admin.py`, `pipeline/__main__.py`, `pipeline/commands/ingest.py`, `pipeline/commands/parse.py`, `pipeline/commands/resolve.py`, `app/src/routes/admin/+layout.svelte`, `app/src/routes/admin/pipeline/+page.server.ts`, `app/src/routes/admin/pipeline/+page.svelte`, `app/src/routes/admin/pipeline/[job_id]/+page.server.ts`, `app/src/routes/admin/pipeline/[job_id]/+page.svelte`.

No `TBD`, `FIXME`, or `XXX` markers found. The 07-06-SUMMARY.md notes one known limitation: `role_name` will be `None` for newly created persons in the dropdown because `api/routers/admin.py` `create_person_for_job` route does not do a Role join — the field is in the schema contract but unpopulated. This is documented as acceptable for gap closure and affects display only.

### Human Verification Required

### 1. Live Polling Step Advancement (PIPE-14)

**Test:** Start a new job via URL mode. Observe the /admin/pipeline/{id} status page. Watch step cards without reloading the page.
**Expected:** Ingest card transitions Running → Completed, Parse card transitions Pending → Running → Completed, Resolve card transitions Pending → Running. Cards update without page reload, approximately every 2.5 seconds.
**Why human:** Requires a running FastAPI server, a running pipeline subprocess writing status to the DB, and a browser to observe the setInterval polling behavior.

### 2. Resolve Pauses and Discrepancy Table Renders (PIPE-15)

**Test:** Run a pipeline job where resolve encounters alias misses (or alias HITs after Plan 06). Observe the Resolve card when the job reaches paused status.
**Expected:** Resolve card shows "Needs review" badge. A table appears below with columns "Raw label", "Resolved as", "Action". All speaker labels appear — HIT rows show the auto-matched name with a Confirm button; MISS rows show a dash with Correct button and candidates dropdown.
**Why human:** Requires a real pipeline run producing discrepancies JSONB in the DB; rendering of HIT vs MISS row distinction requires browser.

### 3. Confirm and Override Flow (PIPE-16)

**Test:** On a paused job with HIT rows, click Confirm on one row. Then click Override on the same row.
**Expected:** After Confirm: row shows "✓ Confirmed {name} ({role})" and an Override button appears. After Override: row returns to initial state showing Confirm+Correct buttons; Continue Resolve button disappears (allDispositioned becomes false).
**Why human:** Client-side rowStates reactive state; requires browser.

### 4. Typeahead Correction Dropdown (PIPE-16)

**Test:** Click Correct on any row. Type a partial name in the input.
**Expected:** Text input appears with datalist; typing filters the candidates list to matching options; selecting a candidate name freezes the row as "✓ Corrected {name}"; Override button appears.
**Why human:** Datalist combobox behavior is browser-native; filtering requires typed input.

### 5. Add New Person Inline (PIPE-16)

**Test:** Click Correct on a row, then select "— Add new person —" from the typeahead. Fill in a full name and role. Click Save person.
**Expected:** Form dismisses. The new person appears auto-selected in the row as "✓ Corrected {name}". No page refresh. The person is immediately available in that row's dropdown (via extraCandidates).
**Why human:** Requires live FastAPI POST /api/admin/jobs/{id}/people; correct SvelteKit envelope parsing (x-sveltekit-action header) must return person object; client-side extraCandidates update requires browser.

### 6. Continue Resolve Disables Button and Transitions State (PIPE-16)

**Test:** On a paused job with all rows dispositioned, click Continue Resolve.
**Expected:** Button text immediately changes to "Submitting…" and receives the real `disabled` attribute before the network request completes. On success: Resolve card transitions away from "Needs review"; polling restarts (the $effect re-evaluates because status changes from paused to running/completed).
**Why human:** use:enhance synchronous callback timing — button disable before network request — requires browser observation; state transition after invalidateAll requires live reload.

### 7. Failed Job Error Panel (PIPE-14)

**Test:** Create a job that will fail (e.g., invalid PDF content or intentional pipeline error). Observe the status page after failure.
**Expected:** Failed Resolve card with red badge. Error panel below with heading "This run failed." and the verbatim error_message in monospace font. "Start a new run" link to /admin/pipeline. No retry button visible.
**Why human:** Requires a failed pipeline job in the DB; verbatim rendering of error_message requires browser.

### 8. Browser Close and Resume (PIPE-17)

**Test:** Start a job. Wait for it to reach PAUSED state. Close the browser tab. Reopen /admin/pipeline/{id}.
**Expected:** Page SSR-loads the job in its paused state. Discrepancy table shows exactly as before. Polling does not start (paused is a terminal state). The operator can complete review from where they left off.
**Why human:** Requires actual browser navigation; SSR rendering of paused state on re-load requires live HTTP request.

## Gaps Summary

No gaps found. All 18 must-have truths verified against actual codebase artifacts (code-level). All 6 requirement IDs (PIPE-12 through PIPE-17) are satisfied by the implementation.

The human verification items above are behavioral end-to-end checks that require a live running system and cannot be verified by static code analysis. These are correctness confirmations, not gap indicators — the code paths exist and are substantive. Code-level confidence in the implementation is high.

**One known limitation (not a blocker):** The `role_name` field in `PersonResponse` will be `None` for newly created persons shown in the discrepancy dropdown because `api/routers/admin.py` `create_person_for_job` route does not join on the Role table. The schema contract is correct; the service does set `role_id`; but the response model's `from_attributes` reads from the ORM `Person` object which has no `role_name` attribute. The operator sees the name without role label — display-only limitation. Noted in 07-06-SUMMARY.md as a known limitation acceptable for gap closure.

---

_Verified: 2026-06-17T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
