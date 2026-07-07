---
phase: 24-pipeline-list-page
plan: 05
subsystem: admin-pipeline-list
tags: [gap-closure, security, fastapi, pipeline-cli, tdd, argv-injection]
dependency_graph:
  requires: ["24-04"]
  provides: ["docket-argv-injection-guard", "pipeline-startup-failure-guard"]
  affects: ["api/routers/admin.py", "pipeline/__main__.py"]
tech_stack:
  added: []
  patterns:
    - "Nested _add(raw) closure inside _normalize_dockets centralizes strip/dedupe/reject logic for both primary_docket and source_dockets in one place"
    - "Startup guard wraps parser.parse_args() in try/except SystemExit inside the child process only — scrapes --job-id from sys.argv, writes a bounded best-effort FAILED status, then re-raises to preserve the non-zero exit code"
    - "Bounded diagnostic message ([:500] slice) written to error_message Text column — never echoes untrusted argv tokens, only a fixed string plus the int exit code"
key_files:
  created:
    - api/tests/test_docket_arg_safety.py
    - pipeline/tests/test_ingest_startup_guard.py
  modified:
    - api/routers/admin.py
    - pipeline/__main__.py
decisions:
  - "Rejection guard lives inside a single nested _add(raw) helper in _normalize_dockets rather than duplicating the startswith('-') check in two branches — matches the plan's exact prescribed refactor and keeps the primary_docket and source_dockets paths behaviorally identical."
  - "Startup guard only fires on a truthy non-zero SystemExit code — exit code 0 (e.g. --help, normal exit) is explicitly excluded so ordinary CLI usage is unaffected."
  - "_write_early_failure and _scrape_job_id run entirely inside the spawned child process (pipeline/__main__.py); pipeline_spawn.py and the fire-and-forget invariant (D-01) are untouched, since the parent Popen call never awaits subprocess completion."
metrics:
  duration: "~20m"
  completed: 2026-07-07
status: complete
---

# Phase 24 Plan 05: Docket Argv-Injection Guard + Pipeline Startup Failure Guard Summary

Closed CR-01 (the single Blocker from 24-VERIFICATION.md) with two independent, defense-in-depth guards: `_normalize_dockets` now rejects any `-`-prefixed docket pill value with a 422 before a job row or subprocess ever exists, and `pipeline/__main__.py` now catches argparse-level `SystemExit` and writes a bounded best-effort FAILED status so no pre-`run_ingest` crash can ever again strand an `admin_jobs` row silently at PENDING/INGEST.

## What Was Built

**Task 1 — Reject flag-like docket values at the API boundary (422), TDD RED/GREEN:**
- RED: created `api/tests/test_docket_arg_safety.py` with 5 tests (2 no-regression callable tests, 2 rejection callable tests, 1 static-analysis test); confirmed 1 failure (`DID NOT RAISE HTTPException`) before any implementation change, proving the guard did not previously exist.
- GREEN: refactored `_normalize_dockets` in `api/routers/admin.py` (lines 111-134 → expanded) into a single nested `_add(raw: str)` helper that strips, returns early on empty-or-seen, and raises `HTTPException(status_code=422, detail=f"Docket value {stripped!r} cannot start with '-'.")` when the stripped value begins with `-`. `_add` is now called for `primary_docket` (when truthy) and for each `d` in `source_dockets`, replacing the two previously-duplicated strip/dedupe blocks. Added a `T-24-08` threat-ID comment on the raise line and updated the docstring to describe the new rejection behavior and reference the Task 2 startup guard as the second defense layer.
- `_dockets_to_ingest_args` was not touched — confirmed via `git diff` showing zero changes to that function.
- All 6 tests (5 planned + the pre-existing multi-docket regression check) pass in 1.16s standalone, 1.60s combined with Task 2's suite.

**Task 2 — Startup guard writes best-effort FAILED on pre-run_ingest exit, TDD RED/GREEN:**
- RED: created `pipeline/tests/test_ingest_startup_guard.py` with 6 tests (2 static-analysis, 2 behavioral for `_write_early_failure`/`_scrape_job_id` presence, 2 direct behavioral calls); confirmed collection failed with `ImportError: cannot import name '_scrape_job_id'` before any implementation change.
- GREEN: added three imports to `pipeline/__main__.py` mirrored from `pipeline/commands/ingest.py` (`from sqlalchemy import update`; `from api.models.models import AdminJob, AdminJobStatus`; `from pipeline.db import get_session`). Added `_scrape_job_id(argv: list[str]) -> int | None` (finds `--job-id`, returns `int(argv[idx+1])`, guards `ValueError`/`IndexError`) and `_write_early_failure(job_id: int | None, message: str) -> None` (no-op when `job_id is None`; otherwise slices `message[:500]`, runs an inner `asyncio.run(...)` coroutine that opens `async with get_session()` and executes the same `update(AdminJob).values(status=AdminJobStatus.FAILED, error_message=...)` shape as `ingest.py:201-218`; wraps the whole write in `try/except Exception` that prints a warning and swallows the error).
- Wrapped `args = parser.parse_args()` in `main()` with `try/except SystemExit as exc`: on a truthy `exc.code` (non-zero — excludes `--help`/exit 0), scrapes `_scrape_job_id(sys.argv[1:])`, calls `_write_early_failure(job_id, f"Pipeline failed at argument parsing (exit {exc.code}). Argv rejected before ingest logic ran.")`, then `raise`s to re-propagate the SystemExit so the process still exits non-zero.
- `pipeline_spawn.py` was not touched — confirmed via `git diff --stat` showing no changes to that file. The guard runs entirely inside the child process (`pipeline/__main__.main()`); the parent's `Popen` call in `spawn_pipeline_step` never awaits subprocess completion, so the fire-and-forget invariant (D-01) is intact.
- All 5 tests pass in 1.03s standalone.

## Verification Results

- `.\.venv\Scripts\python.exe -m pytest api/tests/test_docket_arg_safety.py -x -q`: **6 passed in 1.16s** (plan specified 5; a 6th no-regression multi-value test was included and also passes).
- `.\.venv\Scripts\python.exe -m pytest pipeline/tests/test_ingest_startup_guard.py -x -q`: **5 passed in 1.03s** (plan specified 4 behaviors; `_scrape_job_id` absent/present split into 2 discrete tests, both pass).
- Combined run: `.\.venv\Scripts\python.exe -m pytest api/tests/test_docket_arg_safety.py pipeline/tests/test_ingest_startup_guard.py -x -q` — **11 passed in 1.60s**, no `DATABASE_URL` set.
- Regression guard: `.\.venv\Scripts\python.exe -m pytest tests/test_admin_router.py -q` — **11 passed in 1.08s** (pre-existing suite unaffected).
- `git diff api/services/pipeline_spawn.py` — empty (file byte-for-byte unchanged).
- `git diff api/routers/admin.py` shows `_dockets_to_ingest_args` (lines 137-148 pre-change) has zero diff lines — unchanged.
- `ast.parse` syntax check on both modified Python files — both pass.
- Smoke import: `import pipeline.__main__ as m; m._scrape_job_id(['x','--job-id','3'])` → `3` — confirms no circular-import regression from adding `api.models.models`/`pipeline.db` imports to `pipeline/__main__.py`.
- TDD gate sequence confirmed in `git log`: `test(24-05)` commit precedes each corresponding `feat(24-05)` commit for both Task 1 and Task 2.

## Deviations from Plan

None — plan executed exactly as written. Both tasks followed the plan's `<action>` blocks precisely: the `_add` helper shape, the `T-24-08` comment convention, the try/except `SystemExit` wrapping, and the `[:500]` message bound all match the plan's exact prescribed code shapes.

## Known Stubs

None.

## Threat Flags

None — this plan closes the three STRIDE threats (T-24-08 tampering, T-24-09 DoS, T-24-10 information disclosure) already registered in its own `<threat_model>` section; no new trust boundaries or attack surface were introduced. `_write_early_failure` and `_scrape_job_id` only ever read/write the integer `job_id` and a fixed diagnostic string — no operator-supplied argv token is echoed into `error_message`, consistent with the T-24-10 mitigation plan.

## Self-Check: PASSED

- FOUND: api/tests/test_docket_arg_safety.py
- FOUND: pipeline/tests/test_ingest_startup_guard.py
- FOUND: api/routers/admin.py
- FOUND: pipeline/__main__.py
- FOUND commit: 2e91ceb1 (test(24-05): add failing test for docket argv-injection rejection guard)
- FOUND commit: 5756fcb8 (feat(24-05): reject flag-like docket values at the API boundary (422))
- FOUND commit: 85df02e1 (test(24-05): add failing test for pipeline __main__ startup guard)
- FOUND commit: 35caff28 (feat(24-05): startup guard writes best-effort FAILED on pre-run_ingest exit)
