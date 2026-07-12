---
phase: 24-pipeline-list-page
verified: 2026-07-07T00:00:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "All submitted docket pills are forwarded from SvelteKit to FastAPI and persisted through ingest into Argument.source_dockets — reliably, for any operator-entered docket string (CR-01)"
  gaps_remaining: []
  regressions: []
deferred: []
---

# Phase 24: Pipeline List Page Verification Report

**Phase Goal:** The pipeline list page at `/admin/pipeline/` has a free-text question number field, a docket pill/tag input consistent with Phase 23, a complete runs table, the "show incomplete only" toggle, and accurate compound status badges
**Verified:** 2026-07-07
**Status:** passed
**Re-verification:** Yes — after gap closure (Plan 24-05)

## Goal Achievement

### CR-01 Closure — Independent Verification

The prior VERIFICATION.md (superseded) found ONE Blocker: an operator-entered docket pill value beginning with `-`/`--` was forwarded unsanitized into the spawned `python -m pipeline ingest` subprocess argv, causing argparse `SystemExit` before `run_ingest()` ran, silently stranding the `admin_jobs` row at PENDING/INGEST forever (DEVNULL stdio hid the failure).

Plan 24-05 claims to close this with two independent layers. I traced both directly in the current codebase (not from SUMMARY.md or 24-REVIEW.md narration) and ran the tests myself:

**Layer 1 — API boundary guard** (`api/routers/admin.py:111-149`, `_normalize_dockets`):
- Read the live function body. A nested `_add(raw: str)` helper strips the value, and if `stripped.startswith("-")` is true, raises `HTTPException(status_code=422, detail=f"Docket value {stripped!r} cannot start with '-'.")` — confirmed present at lines 136-141.
- Confirmed `_add` is called for `primary_docket` (when truthy, line 146) and for every `d` in `source_dockets` (line 148) — both the legacy single-docket path and the multi-pill path are guarded.
- Confirmed call-site ordering: `create_job` (line 222) calls `_normalize_dockets` as the FIRST statement in the route body, strictly before either the `pdf_url is not None` branch (line 224) or the `pdf_file is not None` branch (line 236) — a rejection raises before any `jobs_service.create_job` call or `spawn_pipeline_step` call, so no partial job row or subprocess can ever be created for a rejected value.
- Confirmed `_dockets_to_ingest_args` (lines 152-163) is byte-for-byte the same as before — the fix is purely at the normalization boundary, not a patch to the consumer.
- Confirmed `question_number` cannot carry the same risk: it is typed `question_number: int = Form(1)` (line 201) — FastAPI itself 422s non-integer input before `str(question_number)` ever reaches argv.

**Layer 2 — Pipeline startup guard** (`pipeline/__main__.py:43-92, 240-258`):
- Read the live source. `_scrape_job_id(argv)` (lines 43-55) finds `--job-id` in argv and returns `int(argv[idx+1])`, guarding `ValueError`/`IndexError` → `None`.
- `_write_early_failure(job_id, message)` (lines 58-92): no-op when `job_id is None` (line 71-72); otherwise bounds the message to `message[:500]` (line 75) and runs an inner `asyncio.run(_write())` coroutine that executes `update(AdminJob).where(AdminJob.id == job_id).values(status=AdminJobStatus.FAILED, error_message=bounded_message)` — mirrors the exact FAILED-write shape used by `run_ingest`'s own except block. The whole write is wrapped in `try/except Exception` (lines 89-92) that prints a warning and swallows the error — never raises out of the guard, never masks the original `SystemExit`.
- `main()` (lines 240-258): `args = parser.parse_args()` is wrapped in `try/except SystemExit as exc`. On a truthy `exc.code` (correctly excludes the `--help`/exit-0 case), it scrapes `--job-id` and calls `_write_early_failure`, then `raise`s to re-propagate the `SystemExit` so the process still exits non-zero.
- Confirmed `pipeline_spawn.py` is byte-for-byte unchanged (`git diff --stat 5a90fb5e HEAD -- api/services/pipeline_spawn.py` shows zero diff) — still `stdout=DEVNULL, stderr=DEVNULL`, still fire-and-forget `Popen` with no `.wait()`/`.communicate()`. The guard runs entirely inside the child process, so the D-01 fire-and-forget invariant is intact.

**Bypass-path check (independent, not just trusting the review's claim):**
- `rerun_job` (`admin.py:936-969`): reads `new_job.source_dockets` from an already-created `AdminJob` row (line 962, `_dockets_to_ingest_args(new_job.source_dockets or [])`). Since `admin_jobs.source_dockets` is only ever written at job-creation time through `_normalize_dockets`'s guarded path (confirmed via grep — no other write site to `AdminJob.source_dockets` exists), no raw unvalidated operator string can re-enter argv through rerun.
- `update_argument_metadata` / `MetadataUpdate.source_dockets` (`api/services/admin_arguments.py:512-558`): confirmed via direct read that this path writes only to `Argument.source_dockets` (line 558), a column `spawn_pipeline_step` never reads and that has no relationship to the `AdminJob` row or its argv construction. No injection surface here.

**Test execution (run directly by me, not accepted from SUMMARY.md):**

```
.\.venv\Scripts\python.exe -m pytest api/tests/test_docket_arg_safety.py pipeline/tests/test_ingest_startup_guard.py -v
→ 11 passed in 1.26s

.\.venv\Scripts\python.exe -m pytest tests/test_admin_router.py -v
→ 11 passed in 0.93s
```

**Conclusion: CR-01 is closed.** Both guards exist, are correctly wired ahead of job creation and subprocess spawn respectively, have no bypass path, and are proven by tests I ran myself.

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Operator can type any free text into the question number field when starting a run (not constrained to a dropdown) | ✓ VERIFIED | `app/src/routes/admin/pipeline/+page.svelte:352-354` — `<input type="text" name="question_number" id="question_number">`; no `<select>` element found anywhere in the file (regression-checked, unchanged since prior verification). |
| 2 | Operator can add multiple docket numbers as pills and remove individual pills before submitting — matching the Phase 23 component behavior | ✓ VERIFIED | UI mechanics unchanged and previously confirmed (`DocketPillInput.svelte` add/remove, shared with `ArgumentDetailsCard.svelte`). The previously-unresolved persistence defect (CR-01) is now closed per the detailed trace above — pills submitted end-to-end are either normalized and persisted successfully, or rejected with an immediate 422 before any job/subprocess exists; no silent-stuck-job failure mode remains. |
| 3 | Runs table shows all pipeline runs, not just recent ones | ✓ VERIFIED | `api/services/admin_jobs.py:204-227` `list_jobs()` — confirmed via direct read: `query = select(AdminJob)`, optional `.where()` filter for `incomplete=True`, `.order_by(AdminJob.created_at.desc())`, no `.limit()` call anywhere in the function. |
| 4 | "Show incomplete only" toggle is present and functional | ✓ VERIFIED | `+page.svelte:457-459` — `role="switch"`, `aria-checked={incomplete}`, `aria-label="Show incomplete only"`; `incomplete = $derived(data.incomplete ?? false)` (line 13); `goto('/admin/pipeline?incomplete=1')` (line 19). Backend filter unchanged (`admin_jobs.py:215-218`). |
| 5 | Status badges display compound labels (e.g., "Parse · Running", "Resolve · Needs Review", "Completed") that accurately reflect current stage and status | ✓ VERIFIED | `+page.svelte:122-141` `badgeLabel(status, currentStep)` — `statusLabels`/`stepLabels` maps, returns bare status when `status === 'completed'` or no `currentStep`, otherwise `stepLabel + ' · ' + statusLabel`. Called at line 625 `{badgeLabel(job.status, job.current_step)}`. |

**Score:** 5/5 truths verified (up from 4/5 — CR-01 closure resolves the previously partial truth #2).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/routers/admin.py` `_normalize_dockets` | Rejects `-`-prefixed docket values with HTTPException 422 | ✓ VERIFIED | Confirmed via direct read, lines 111-149; nested `_add()` helper guards both `primary_docket` and `source_dockets` |
| `pipeline/__main__.py` `_write_early_failure` / `_scrape_job_id` | Startup guard writes best-effort FAILED on pre-run_ingest SystemExit | ✓ VERIFIED | Confirmed via direct read, lines 43-92 (helpers) and 240-258 (guard in `main()`) |
| `api/tests/test_docket_arg_safety.py` | 5+ tests proving the rejection guard | ✓ VERIFIED | Read file; 6 tests present, all pass when run directly (1.26s combined with Task 2's suite) |
| `pipeline/tests/test_ingest_startup_guard.py` | 4+ tests proving the startup guard | ✓ VERIFIED | Read file; 5 tests present, all pass when run directly |
| `api/services/pipeline_spawn.py` | Unchanged — fire-and-forget invariant intact | ✓ VERIFIED | `git diff --stat 5a90fb5e HEAD -- api/services/pipeline_spawn.py` → zero diff |
| `api/services/admin_jobs.py` `list_jobs()` | No `.limit()` clause | ✓ VERIFIED (regression) | Confirmed via direct read |
| `app/src/routes/admin/pipeline/+page.svelte` | Free-text question, DocketPillInput, compound badge, toggle | ✓ VERIFIED (regression) | Confirmed via direct read |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `_normalize_dockets` rejection raise | `create_job` route body | Called as first statement, before both `pdf_url`/`pdf_file` branches | ✓ WIRED | `admin.py:222` precedes lines 224/236 — no job row or subprocess can be created for a rejected value |
| `pipeline __main__.main()` `parser.parse_args()` | `_write_early_failure` | `try/except SystemExit` wrapping, `_scrape_job_id(sys.argv[1:])` | ✓ WIRED | `__main__.py:240-258`; re-raises after the best-effort write so exit code is preserved |
| `rerun_job` | `_dockets_to_ingest_args` | Reads already-normalized `AdminJob.source_dockets` | ✓ WIRED, NO BYPASS | `admin.py:962` — no raw operator string re-enters unvalidated |
| `update_argument_metadata` (`MetadataUpdate.source_dockets`) | `Argument.source_dockets` | ORM PATCH | ✓ ISOLATED, NO BYPASS | Writes only `Argument.source_dockets`, never read by `spawn_pipeline_step` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Docket argv-injection guard + startup guard tests | `pytest api/tests/test_docket_arg_safety.py pipeline/tests/test_ingest_startup_guard.py -v` | 11 passed in 1.26s | ✓ PASS |
| Adjacent regression suite (admin router) | `pytest tests/test_admin_router.py -v` | 11 passed in 0.93s | ✓ PASS |
| Pre-existing suite failures confirmed pre-existing (not phase-24 regressions) | Ran `tests/test_models_import.py` + `pipeline/tests/test_ingest.py` at HEAD and at commit `5a90fb5e` (pre-Plan-24-05, review commit) | Identical 6 failures at both commits: `test_all_tables_count`, `test_expected_table_names`, `test_side_enum_values`, `test_ingest_creates_pipeline_run`, `test_consolidated_dockets`, `test_ingest_idempotent` (all `AttributeError: 'Namespace' object has no attribute 'job_id'` or table/enum count mismatches) | ✓ CONFIRMED PRE-EXISTING |
| `list_jobs()` has no `.limit()` clause | Direct read of `api/services/admin_jobs.py:204-227` | No `.limit()` call found | ✓ PASS |

Note on the `async_session_factory` ImportError mentioned in the task prompt: confirmed via grep that this symbol is referenced only in `api/tests/test_admin_jobs_list.py` and `api/tests/test_admin_jobs_stats.py` (lines 49/51 in each), neither of which is a file this phase touched or a file in the Plan 24-05 gap-closure scope. Full collection (`pytest --collect-only -q`) succeeds with 233 tests collected — no collection-time ImportError blocks the suite; the failures the task prompt describes surface at test-execution time in files outside this phase's scope, consistent with the "pre-existing drift" characterization.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PLIST-01 | 24-04 | Question number free text | ✓ SATISFIED | `<input type="text" name="question_number">`, no dropdown |
| PLIST-02 | 24-02, 24-03, 24-04, 24-05 | Docket pill/tag UI, multi-docket, add/remove, reliable persistence | ✓ SATISFIED | Pill UI mechanics confirmed; CR-01 persistence defect closed by Plan 24-05's two independently-verified guards |
| PLIST-03 | 24-01 | Runs table shows all runs | ✓ SATISFIED | `list_jobs()` has no limit; confirmed via direct read |
| PLIST-04 | 24-04 | Show incomplete only toggle retained | ✓ SATISFIED | Toggle present, wired, backend filter unchanged |
| PLIST-05 | 24-04 | Compound status badges | ✓ SATISFIED | `badgeLabel()` compound logic matches spec |

No orphaned requirements — all five PLIST-* IDs mapped to Phase 24 in REQUIREMENTS.md (lines 118-122) are marked "Complete" and are claimed by at least one plan's frontmatter `requirements` field.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/src/routes/admin/pipeline/+page.server.ts` | 82-85, 124-126 | New 422 docket-rejection detail message is swallowed by a generic error string (`'Could not start the run. Check the URL and try again.'`) regardless of the actual failure cause | ⚠️ Warning (24-REVIEW.md WR-01, not a phase-goal blocker) | An operator who triggers the new CR-01 guard (types `--dockets` into a pill) gets a job that correctly fails to start (no more silent hang — the core defect is fixed), but is told to "check the URL," which is misleading. Quality/UX issue, not a correctness defect against the 5 success criteria. |
| `app/src/lib/components/ArgumentDetailsCard.svelte` | 89 | `{#key effectiveDockets.join('')}` — theoretical low-probability key collision across distinct docket arrays | ⚠️ Warning (24-REVIEW.md WR-02) | Pre-existing, unrelated to CR-01 closure; does not affect this phase's success criteria |
| `app/src/routes/admin/pipeline/+page.svelte` | 351-367 | `question_number` free-text field has no client-side numeric validation | ⚠️ Warning (24-REVIEW.md WR-03) | Pre-existing; round-trips to a 422 with the same generic message as WR-01 |
| `pipeline/tests/test_ingest_startup_guard.py` / `api/tests/test_docket_arg_safety.py` | various | Static "source contains substring" assertions are weaker than an executable end-to-end integration test (no test actually spawns the subprocess and asserts a real DB row transitions to FAILED) | ⚠️ Warning (24-REVIEW.md WR-05) | The behavioral+static combination I verified directly (reading the guard code plus running the callable tests) is sufficient to confirm the guard logic is correct and present; a true subprocess-level integration test would add further confidence but its absence does not leave CR-01 unverified — the logic was read and traced by hand at every call site. |

No `TODO`/`FIXME`/`XXX`/`TBD` debt markers found in any file modified by Plan 24-05 (`api/routers/admin.py`, `pipeline/__main__.py`, and the two new test files).

### Human Verification Required

None required for phase-goal achievement. All 5 success criteria are deterministically verified by direct source inspection and test execution; CR-01 closure is deterministically confirmed (guard logic present, correctly ordered, no bypass path, tests pass).

**Optional quality follow-up (not blocking):** WR-01 (generic error message swallowing the new specific 422 detail) is a UX quality issue an operator would notice in practice — recommend a follow-up todo/backlog item to surface the FastAPI `detail` field on 422 responses, but this does not affect whether Phase 24's goal is achieved.

### Gaps Summary

None. The single Blocker (CR-01) from the previous verification pass is closed, verified independently against the live codebase (not from SUMMARY.md or REVIEW.md narration alone): both guards were read line-by-line, their call-site ordering was traced, bypass paths (`rerun_job`, `update_argument_metadata`) were checked and confirmed clean, and both new test suites (11 tests) plus the adjacent regression suite (11 tests) were executed directly by the verifier and pass. The task prompt's claim that broader pre-existing test-suite failures are unrelated to this phase was independently checked (not accepted uncritically) by diffing the failure set between HEAD and the pre-Plan-24-05 commit `5a90fb5e` — the failure set is byte-for-byte identical, confirming these are pre-existing and out of scope for Phase 24.

All 5 phase success criteria hold. Phase 24 goal is achieved.

---

_Verified: 2026-07-07_
_Verifier: Claude (gsd-verifier)_
