---
phase: 43-dev-only-reset-to-fixture
plan: 04
subsystem: ops
tags: [uat, live-verification, admin-panel, environment-gate, dev-tooling]

# Dependency graph
requires:
  - phase: 43-dev-only-reset-to-fixture
    provides: "43-01/43-02's backend reset-to-fixture endpoint and 43-03's Dev Tools admin panel section, all exercised live here for the first time against the real 900MB corpus and real dev database"
provides:
  - "Operator-confirmed live proof that Reset to Fixture produces exactly the four confirmed fixtures in four distinguishable states, through the real import-convokit path, with Phase 42's importer fixes intact"
  - "Operator-confirmed live proof that the environment gate is a fail-closed allow-list: unset value refuses (backend refuses to even start), a capitalization near-miss refuses, and only the exact value \"development\" mounts the router and renders the section"
affects: []

# Actuals (#2632)
actuals:
  tokens: 0
  tasks: 2
  commits: 0

tech-stack:
  added: []
  patterns: []

key-files:
  created:
    - .planning/phases/43-dev-only-reset-to-fixture/verify-scripts/check_counts.py
    - .planning/phases/43-dev-only-reset-to-fixture/verify-scripts/check_states.py
    - .planning/phases/43-dev-only-reset-to-fixture/verify-scripts/check_fixture_integrity.py
  modified: []

key-decisions:
  - "This plan produces no source changes (files_modified: [] in frontmatter) — both tasks are pure operator observation against a live local stack, per the plan's own threat model (T-43-19/T-43-20/T-43-21 all require human observation, not automation)"
  - "Verification helper scripts (check_counts.py, check_states.py, check_fixture_integrity.py) were added under this phase's directory rather than as raw ad-hoc shell one-liners, since the operator hit a real Python-quoting/newline-flattening failure trying to paste the plan's literal -c command into PowerShell — the scripts sidestep shell-quoting entirely by resolving DATABASE_URL the same way the running app does (api.core.config.settings)"
  - "During Task 2's live verification, a real, unrelated dev-environment bug was found and fixed (not part of this phase's scope, but blocking the checkpoint): uvicorn's --reload on Windows resolves its reload-worker subprocess via multiprocessing.spawn.get_executable(), which returns sys._base_executable (the venv's ORIGINAL base interpreter) instead of sys.executable (the venv's own copy) — the worker then can't import fastapi et al. An earlier reload-spawned worker was also left orphaned (holding port 8000 after its supervisor exited), so multiple 'restart the stack' attempts silently failed to rebind the port and kept serving stale config. Fixed for this session by running uvicorn without --reload; not a Phase 43 code change since it is a local Windows toolchain issue, not a defect in api/main.py or api/core/config.py"
  - "DEVTOOL-01 and DEVTOOL-02 are marked complete in REQUIREMENTS.md by this plan — both were deliberately left unchecked through 43-01/43-02/43-03 pending this live proof"

requirements-completed: [DEVTOOL-01, DEVTOOL-02]

coverage:
  - id: D1
    description: "Operator ran Reset to Fixture from /admin against the real corpus; database ended up with exactly the four confirmed fixtures (13015 draft/resolved, 15169 pipeline/paused-resolve, 18897 published, 22372 pipeline/running), roles untouched, each fixture paired with a non-null admin_jobs row, confirmation-then-cancel produced zero row-count change, and the complexity fixture (15169) carried Phase 42's corrected counts (480 utterances, 1 non-null section_hint, 17 argument_participants)"
    requirement: "DEVTOOL-01"
    verification:
      - kind: manual_procedural
        ref: "43-04-PLAN.md Task 1, steps 1-28 — operator ran all steps against the live dev stack and confirmed all 28 pass"
        status: pass
    human_judgment: true
    rationale: "Requires observing a running admin-panel UI, real database row counts, and real interaction states — not assertable from source"
  - id: D2
    description: "With ENVIRONMENT=production, POST /api/admin/dev/reset-to-fixture returned 404 (not 403/200) and the route was absent from openapi.json; /admin's served HTML contained no 'Dev Tools' or 'DEV ONLY' string; GET /api/admin/health still returned 200"
    requirement: "DEVTOOL-02"
    verification:
      - kind: manual_procedural
        ref: "43-04-PLAN.md Task 2, steps 1-14 — operator-confirmed frontend, orchestrator-verified backend via curl and openapi.json diff"
        status: pass
    human_judgment: true
  - id: D3
    description: "Gate is a fail-closed allow-list, not a case-insensitive block-list: an unset ENVIRONMENT value prevented API startup with a pydantic ValidationError naming the field ('Field required'), and ENVIRONMENT=Development (capital D) still produced the same 404/absent-route/absent-section refusal as production"
    requirement: "DEVTOOL-02"
    verification:
      - kind: manual_procedural
        ref: "43-04-PLAN.md Task 2, steps 15-18 — orchestrator captured the ValidationError traceback and the 404/openapi.json diff for the capitalization case directly"
        status: pass
    human_judgment: false
  - id: D4
    description: "After restoring both ENVIRONMENT values to development, the Dev Tools section rendered again, the reset endpoint returned 401 (not 404) for a bad token and reset-to-fixture reappeared in openapi.json, and the full suite passed (841 passed, 5 xfailed, 4 pre-existing/unrelated errors tracked as backlog 999.10 — same signature confirmed unrelated in every prior plan of this phase)"
    requirement: "DEVTOOL-01, DEVTOOL-02"
    verification:
      - kind: integration
        ref: "orchestrator ran ./.venv/Scripts/python.exe -m pytest -q directly after the final restore"
        status: pass
    human_judgment: false

duration: ~3h (including live-environment debugging of an unrelated Windows/uvicorn/venv toolchain issue)
completed: 2026-07-31
status: complete
---

# Phase 43: Dev-Only Reset to Fixture Summary

**Operator-confirmed, live proof against the real corpus and real dev database: Reset to Fixture produces exactly the four confirmed fixtures in four distinguishable states, and the environment gate is a genuine fail-closed allow-list — demonstrated by actually attempting the production refusal, an unset value, and a capitalization near-miss, not asserted from the code.**

## Performance

- **Duration:** ~3h (most of it debugging an unrelated local dev-environment issue that blocked verification, not the phase's own code)
- **Completed:** 2026-07-31
- **Tasks:** 2/2 (both `checkpoint:human-verify`, blocking gates)
- **Files modified:** 0 (this plan is pure live verification; see `key-files.created` for the verification helper scripts added to support it)

## Accomplishments

- **Task 1 (28/28 steps passed):** Operator ran Reset to Fixture from the live `/admin` page against the real ~900MB ConvoKit corpus and the real local dev database. Confirmed: the confirm-then-cancel step produced zero database change; the real reset produced exactly `arguments=4` (oyez_transcript_id 13015, 15169, 18897, 22372) with `roles` untouched; the four fixtures landed in four distinct, expected states (13015 draft/resolved, 15169 pipeline/paused-resolve, 18897 published, 22372 pipeline/running), each paired with a non-null `admin_jobs` row; the complexity fixture (15169) carried Phase 42's corrected counts exactly (480 utterances, 1 non-null `section_hint`, 17 `argument_participants`); and the complexity fixture's Resolve card was editable afterward.
- **Task 2 (24/24 steps passed):** With `ENVIRONMENT=production` in both `.env` files, the backend genuinely un-mounted the route (404, absent from `openapi.json`, confirmed via `curl` — not asserted) while `/api/admin/health` still returned 200, and `/admin`'s served HTML contained no trace of "Dev Tools" or "DEV ONLY" in view-source. An unset `ENVIRONMENT` value prevented the API from starting at all (pydantic `ValidationError: environment / Field required`) — a stronger fail-closed proof than a mere refusal. A capitalization near-miss (`Development`) produced the identical 404/absent-route/absent-section refusal, proving the check is an exact-match allow-list. After restoring both values to `development`, the section and endpoint worked again and the full suite passed (841 passed, 5 xfailed, 4 pre-existing/unrelated errors — backlog item 999.10).
- **Unplanned but necessary:** diagnosed and worked around a real Windows/uvicorn/venv toolchain bug that was blocking every verification attempt — `uvicorn --reload`'s reload-worker subprocess resolution picks the venv's *base* interpreter instead of its own, and an earlier reload-spawned worker had been orphaned (silently holding port 8000 after its supervisor exited), so repeated "restart the stack" attempts kept talking to stale config. Fixed for this session by running both servers without `--reload`. This is a local dev-environment issue, not a Phase 43 code defect — no source change was made in response to it.

## Task Commits

No source commits — this plan is pure live verification with no code changes (`files_modified: []` per plan frontmatter). Tracking updates only:

1. **Task 1: Reset the real dev database from /admin** — operator-verified, no commit (verification-only)
2. **Task 2: Prove the production refusal** — operator- and orchestrator-verified, no commit (verification-only)

**Plan metadata:** tracking commit follows this SUMMARY (docs: complete plan)

## Deviations

- **Rule 1 (auto-fixed, out of plan scope):** the uvicorn `--reload`/venv interpreter bug above blocked Task 1 and Task 2 entirely until resolved. Fixed by running uvicorn without `--reload` for this session rather than touching any project source — not a code change, so no commit.
- Added three verification helper scripts (`verify-scripts/*.py`) not specified in the plan, because the plan's literal multi-line `python -c "..."` commands for steps 2/21/22/24 do not survive being pasted into PowerShell (Python's indentation-sensitive syntax breaks when newlines get flattened by the terminal). The scripts are functionally identical to the plan's inline commands and resolve `DATABASE_URL` the same way the running app does.

## Requirements Traceability

- **DEVTOOL-01**: ✅ Complete — live-demonstrated by Task 1
- **DEVTOOL-02**: ✅ Complete — live-demonstrated by Task 2 (production refusal, unset-value refusal, and capitalization near-miss all attempted and confirmed, not asserted from source)
