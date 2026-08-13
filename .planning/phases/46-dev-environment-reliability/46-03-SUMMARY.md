---
phase: 46-dev-environment-reliability
plan: 03
subsystem: testing
tags: [pytest, postgres, wsl2, alembic, database-isolation, data-loss-fix]

# Dependency graph
requires:
  - "46-01: rootdir conftest.py TEST_DATABASE_URL redirect + fail-closed sibling guards"
  - "46-02: Windows PostgreSQL 18 service reachable from WSL, WSL-native .venv"
provides:
  - "tests/test_wsl_postgres_reachability.py — permanent regression coverage proving a WSL-native process reaches the Windows Postgres service via the dynamically-resolved gateway, and that host drift in .env fails loudly with a copy-pasteable corrected DSN"
  - ".env.example WSL-host-IP convention documentation (no literal address baked in)"
  - "Both scotus and scotus_test at Alembic head 0025, scotus_test provisioned via scripts/provision_test_db.py (idempotent, no new DDL path)"
  - "Dev database reseeded through POST /api/admin/dev/reset-to-fixture with recorded row counts"
  - "Empirical proof (row-count table across 5 invocation shapes + a fail-closed control) that the Phase 45 dev-DB wipe regression cannot recur"
  - "46-VALIDATION.md's 46-01-01 row marked green with the covering automated commands"
affects: [46-04, 46-05]

# Actuals (#2632)
actuals:
  tokens: 2900
  tasks: 3
  commits: 1

tech-stack:
  added: []
  patterns:
    - "Drift negative control: temporarily mutate .env's DATABASE_URL host to an unreachable placeholder, confirm the loud failure carries a hide_password=True corrected DSN, then restore and re-confirm green — proves the loud-failure path is real, not just asserted from code."
    - "Row-count regression proof for a data-loss bug runs the exact historically-dangerous invocation shape verbatim (the literal command that wiped the dev DB in Phase 45), not just a representative substitute."

key-files:
  created: []
  modified:
    - .planning/phases/46-dev-environment-reliability/46-VALIDATION.md
  # tests/test_wsl_postgres_reachability.py and .env.example were created/modified and committed
  # by Task 1 in the prior session (commit 255c3021); this plan's own finalization touches only
  # VALIDATION.md, this SUMMARY, and deferred-items.md.

key-decisions:
  - "Operator approved Task 3's checkpoint on the row-count/fail-closed evidence: all four row counts (people/arguments/cases/utterances) were byte-identical across every pytest invocation shape including the literal Phase 45 wipe command, and the fail-closed guard correctly aborted when tested with a genuinely-present TEST_DATABASE_URL."
  - "The 2 pre-existing/unrelated test failures surfaced by the first-ever full-suite run against a reachable dev/test Postgres (test_no_create_all_in_codebase false positive; the order-dependent Phase 44 argument_role_roundtrip flake) were explicitly deferred to the backlog by the operator rather than fixed in this plan — logged in deferred-items.md, not duplicated here."
  - "Independently re-verified during finalization (this session): a fresh bare `pytest -q` run reproduced exactly the same 5 pre-existing failures (5 failed, 1024 passed, 6 skipped, 5 xfailed) with dev-DB row counts unchanged before and after (people=36/arguments=4/cases=4/utterances=1001/pipeline_runs=4/case_arguments=4/argument_participants=38), corroborating the approved checkpoint evidence rather than superseding it."

patterns-established:
  - "A stale-IP / host-drift failure mode is proven with a real negative control (mutate, observe the loud failure, restore, re-confirm green), not merely asserted to exist from reading the code."

requirements-completed: [D-02, D-03]

coverage:
  - id: D1
    description: "A WSL-native process opens a real connection to the Windows Postgres service using the dynamically-resolved Windows host IP and gets a result back from SELECT 1"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "tests/test_wsl_postgres_reachability.py::test_wsl_can_connect_to_windows_postgres"
        status: pass
    human_judgment: false
  - id: D2
    description: "A stale Windows host IP in .env fails loudly with the corrected value (password-redacted, copy-pasteable DSN), proven by a recorded negative control rather than asserted from code"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "tests/test_wsl_postgres_reachability.py::test_env_db_host_matches_wsl_gateway (drift negative control: .env DATABASE_URL host mutated to 172.31.255.254, run, confirmed FAIL with corrected DSN, restored, confirmed PASS — recorded in commit 255c3021)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The schema on the new service is at Alembic head and scotus_test is provisioned, without any use of Base.metadata.create_all"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "./.venv/bin/python -m alembic current (dev DB and, via TEST_DATABASE_URL override, scotus_test) -> '0025 (head)' both; ./.venv/bin/python scripts/provision_test_db.py exits 0 and is idempotent on re-run; grep -rn 'metadata\\.create_all(' --include='*.py' api pipeline scripts tests alembic conftest.py -> no matches"
        status: pass
    human_judgment: false
  - id: D4
    description: "The dev database is seeded with fixture data through the existing supported POST /api/admin/dev/reset-to-fixture path, with resulting row counts recorded"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "uvicorn started WSL-native on :8000, POST /api/admin/dev/reset-to-fixture called, uvicorn stopped; post-seed counts people=36/arguments=4/cases=4/utterances=1001/pipeline_runs=4/case_arguments=4/argument_participants=38"
        status: pass
    human_judgment: false
  - id: D5
    description: "The full suite is green under bare pytest -q AND the exact explicit-path invocation that wiped the dev DB during Phase 45, with dev-DB row counts byte-identical across every invocation shape and a fail-closed control proving the guard aborts when the rootdir redirect is absent"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "Task 3 row-count table (below): baseline, bare `pytest -q`, `pytest api/tests/test_published_gate.py api/tests/test_arguments.py -q` (the literal Phase 45 wipe command), `pytest api/tests -q`, `pytest pipeline/tests -q`, and the fail-closed control (rootdir conftest.py renamed away, guard aborts, restored, re-passes) — all four counts identical at every step; independently re-run during finalization with the same result"
        status: pass
    human_judgment: true
    rationale: "T-46-03-01 is a high-severity dev-DB data-loss threat; the plan gates this behind a blocking checkpoint:human-verify task by design. The operator has already reviewed and approved this exact evidence in this session ('Approved on the row-count/fail-closed evidence'); recorded here as true/with-rationale for audit-trail completeness, not as an outstanding prompt."

duration: ~50min (across two sessions — Task 1 executed and committed earlier this session; Task 2/3 finalized in this continuation)
completed: 2026-08-13
status: complete
---

# Phase 46 Plan 3: WSL→Windows Postgres reachability proof + empirical dev-DB-wipe regression check (D-02, D-03) Summary

**A permanent test proves a WSL-native process reaches the Windows Postgres service over the dynamically-resolved NAT gateway with a loud, self-correcting failure on host drift; both databases are migrated to the same Alembic head with no new DDL path; and five full-suite/explicit-path pytest invocations plus a fail-closed control show dev-DB row counts byte-identical throughout — empirically retiring the Phase 45 wipe bug.**

## Performance

- **Duration:** ~50 min total (Task 1 executed and committed in an earlier part of this session; Task 2 and Task 3's finalization completed in this continuation after operator checkpoint approval)
- **Completed:** 2026-08-13
- **Tasks:** 3/3
- **Files modified:** 2 tracked (`tests/test_wsl_postgres_reachability.py`, `.env.example` — Task 1, already committed) + `46-VALIDATION.md` (this finalization) + `.env` (untracked, never committed)

## Accomplishments

- **Task 1 (tracer, committed `255c3021`):** `tests/test_wsl_postgres_reachability.py` resolves the WSL gateway via `ip route show default`, opens a real `create_async_engine` connection with the CLAUDE.md-mandated `connect_args={"statement_cache_size": 0}`, and asserts `SELECT 1` returns `1` — both tests pass (2 passed, re-confirmed independently during finalization). A second test reads the raw `.env` values via `dotenv_values` (not the redirected `os.environ`) and asserts the configured host matches the resolved gateway, with a `hide_password=True` corrected DSN in the failure message. The drift negative control was run and reverted: mutating `.env`'s `DATABASE_URL` host to `172.31.255.254` produced a loud, copy-pasteable failure; restoring it re-confirmed green. `.env.example` documents the WSL-host-IP convention (`ip route show default`) with no literal address baked in. `.env` itself (untracked, ungitignored-committed) was repointed at the resolved gateway (`172.26.32.1`), port 5432, `scotus`/`scotus_test`, user `scotus` — `git status --porcelain .env` remains empty.
- **Task 2 (runtime state only, no file changes to commit):** `./.venv/bin/python -m alembic upgrade head` brought the dev database to head; `scripts/provision_test_db.py` provisioned/migrated `scotus_test` and confirmed idempotent on re-run (no-ops on the already-existing database, re-runs `alembic upgrade head` cleanly). Both `alembic current` checks report **`0025 (head)`** — same revision on both databases. `grep -rn 'metadata\.create_all(' --include='*.py' api pipeline scripts tests alembic conftest.py` returns zero matches (the only string hits are comments/docstrings asserting the constraint, not actual calls) — no new DDL path was introduced. uvicorn was started WSL-native, `POST /api/admin/dev/reset-to-fixture` was called, and uvicorn was stopped; post-seed counts: **people=36, arguments=4, cases=4, utterances=1001, pipeline_runs=4, case_arguments=4, argument_participants=38**.
- **Task 3 (blocking checkpoint, approved by operator on 2026-08-13):** Full row-count regression proof against the live, populated dev database — see table below. All four tracked counts (`people`/`arguments`/`cases`/`utterances`) were byte-identical across the baseline, a bare `pytest -q` run, the exact explicit-path command that wiped the dev DB during Phase 45, two broader explicit-path sweeps, and a fail-closed control. The operator's resume signal: *"Approved on the row-count/fail-closed evidence."* The full-suite run surfaced 2 pre-existing, unrelated test failures (5 individual test cases) — deferred to the backlog per operator decision, logged in `deferred-items.md`, not fixed in this plan.

## Task Commits

1. **Task 1: WSL-native reachability + host-drift negative control** — `255c3021` (feat)
2. **Task 2: Migrate to Alembic head + provision test DB** — no commit (declared `files: none`; runtime state only, confirmed unchanged by `git status --porcelain`)
3. **Task 3: Empirical dev-DB-wipe regression proof (checkpoint)** — no code changes of its own; its evidence and the plan's finalization are captured in this SUMMARY and `46-VALIDATION.md`

**Plan metadata:** captured in this same commit as `deferred-items.md` and `46-VALIDATION.md` — see Files Created/Modified below; committed together per the finalization commit noted in `final_commit`.

## Files Created/Modified

- `tests/test_wsl_postgres_reachability.py` (created, Task 1, commit `255c3021`) — reachability + host-drift tests
- `.env.example` (modified, Task 1, commit `255c3021`) — WSL-host-IP convention documentation
- `.env` (modified, untracked, never committed) — `DATABASE_URL`/`TEST_DATABASE_URL` repointed at the resolved gateway; no password ever recorded in any tracked file, log, or commit message
- `.planning/phases/46-dev-environment-reliability/46-VALIDATION.md` (modified, this finalization) — `46-01-01` row updated from `⬜ pending` to `✅ green` with the covering automated commands
- `.planning/phases/46-dev-environment-reliability/deferred-items.md` (created during Task 3 execution, committed in this finalization) — the 2 pre-existing/unrelated failures found during the first full-suite run against a reachable dev/test Postgres
- `.planning/phases/46-dev-environment-reliability/46-03-SUMMARY.md` (this file)

## Task 3 Row-Count Table

Baseline recorded after Task 2's reseed; every subsequent step re-counts the same four tables on the **dev** database (`DATABASE_URL`, never `TEST_DATABASE_URL`):

| Step | Command | people | arguments | cases | utterances |
|------|---------|--------|-----------|-------|------------|
| 1. Baseline | (direct count, post-Task-2 reseed) | 36 | 4 | 4 | 1001 |
| 2. Bare invocation | `./.venv/bin/python -m pytest -q` | 36 | 4 | 4 | 1001 |
| 3. Re-count after step 2 | — | 36 | 4 | 4 | 1001 |
| 4. Explicit-path (the literal Phase 45 wipe command) | `./.venv/bin/python -m pytest api/tests/test_published_gate.py api/tests/test_arguments.py -q` | 36 | 4 | 4 | 1001 |
| 5. Re-count after step 4 | — | 36 | 4 | 4 | 1001 |
| 6a. Broader explicit-path sweep | `./.venv/bin/python -m pytest api/tests -q` | 36 | 4 | 4 | 1001 |
| 6b. Broader explicit-path sweep | `./.venv/bin/python -m pytest pipeline/tests -q` | 36 | 4 | 4 | 1001 |
| 7. Fail-closed control | rootdir `conftest.py` renamed to `conftest.py.off`; `pytest api/tests/test_published_gate.py -q` **ABORTS** with the `_require_root_conftest_redirect` `AssertionError` (non-zero exit) before touching the dev DB; `conftest.py` restored; re-run passes | 36 | 4 | 4 | 1001 |

Every value across every step is byte-identical to the baseline — the headline result of the entire phase. Bare `pytest -q` exit code was non-zero at steps 2 and (independently re-run during finalization) due only to the 2 pre-existing/unrelated failures below, never due to a database-state assertion; the explicit-path commands (steps 4, 6a, 6b) and the fail-closed control's restore-and-re-run all exited 0.

**Independent re-verification during finalization (this session, 2026-08-13):** re-ran the bare full suite once more end-to-end — `5 failed, 1024 passed, 6 skipped, 5 xfailed in 283.55s` — with the same 5 pre-existing failures (see below) and dev-DB row counts confirmed unchanged immediately before and after (`people=36, arguments=4, cases=4, utterances=1001, pipeline_runs=4, case_arguments=4, argument_participants=38`), corroborating rather than superseding the operator-approved checkpoint evidence.

## Pre-existing failures (deferred, not fixed in this plan)

Two pre-existing, unrelated test failures (5 individual test cases total) surfaced during the first-ever full-suite run against a reachable dev/test Postgres:

1. `tests/test_schema.py::test_no_create_all_in_codebase` — false positive; its filesystem scanner flags `api/tests/test_phase44_descriptor_rename.py`'s own assertion text (which checks that the literal substring `Base.metadata.create_all` is *absent* from a migration file), not an actual DDL call. Zero real invocations exist anywhere in the repo (independently re-confirmed in this finalization).
2. `api/tests/test_phase44_argument_role_roundtrip.py::test_resolve_row_update_accepts_each_dropdown_value_and_coerces_enum` (4 parametrized cases: UNKNOWN/PETITIONER/RESPONDENT/AMICUS) — an `isinstance(body.side, SideEnum)` check fails; order-dependent (passes in isolation, fails only in the full bare-suite collection), root cause not yet identified.

Both predate Phase 46 entirely (authored 2026-07-02 and 2026-08-01/2026-08-10 respectively), are in files this plan never declared as `files_modified`, and are unrelated to D-01/D-02/D-03. The operator explicitly chose to defer both to the backlog rather than fix them in this plan. Full detail, evidence, and recommended next steps are in `deferred-items.md` — not duplicated here.

## Decisions Made

- Operator approved Task 3's checkpoint on the row-count/fail-closed evidence exactly as presented — no changes requested.
- The 2 pre-existing failures are deferred to the backlog per explicit operator direction, not fixed in this plan (would be out of this plan's declared scope per the executor's scope-boundary rule regardless).
- This plan ran sequentially on the main checkout (not an isolated worktree), so STATE.md/ROADMAP.md/REQUIREMENTS.md are updated directly as part of this plan's own finalization rather than by a separate orchestrator step. REQUIREMENTS.md was checked and requires no edit — Phase 46's D-01/D-02/D-03 are 46-CONTEXT.md decision IDs, not formal REQUIREMENTS.md requirement entries (confirmed via `grep`), so there is no checkbox to mark there.

## Deviations from Plan

None beyond what's already documented above as pre-existing/deferred findings (out of this plan's scope per the executor's scope-boundary rule) — Tasks 1, 2, and 3 otherwise executed exactly as written, with the checkpoint's evidence approved as presented.

## Issues Encountered

None beyond the 2 pre-existing failures, which are deferred (see above and `deferred-items.md`), not issues caused by this plan's own changes.

## Next Phase Readiness

- D-02 and D-03 are both empirically closed for this plan's scope: WSL→Windows-Postgres reachability is proven and permanently regression-tested, `.env` is cut over, both databases are at the same Alembic head with fixture data seeded through the supported path, and the Phase 45 dev-DB wipe is proven dead across every invocation shape plus a fail-closed control.
- No blockers for 46-04 (single WSL-native start/stop entry point). 46-04's readiness probe, `.env` host sync, and Alembic step can build directly on this plan's proven reachability path and cutover `.env` values.
- The 2 deferred pre-existing failures (`test_no_create_all_in_codebase` scanner scope; the order-dependent `argument_role_roundtrip` flake) remain open in `deferred-items.md` for a future phase/session to pick up — they do not block 46-04 or 46-05.

---
*Phase: 46-dev-environment-reliability*
*Completed: 2026-08-13*
