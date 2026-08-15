---
phase: 46-dev-environment-reliability
verified: 2026-08-14T21:45:00Z
status: passed
score: 20/20 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 46: Dev Environment Reliability Verification Report

**Phase Goal:** Fix the local dev setup now that Windows admin access is available (the project was previously constrained to run without it). Priority: the pytest DB-isolation bypass discovered in Phase 45 that can silently wipe the shared dev database (`.planning/todos/pending/2026-08-12-pytest-explicit-paths-bypass-db-isolation.md`). Also revisit `scripts/dev-start.ps1`, the portable-Postgres-via-pg_ctl setup, and the Windows-venv-via-WSL-interop path for a more reliable single start/stop flow.

**Verified:** 2026-08-14
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

This verification runs the codebase's own tests directly, does not rely on SUMMARY.md narration, and specifically re-checked the code-review-fix commits (`730c3571`..`3b4d7f8c`, `e36c466f`) against the D-03 goal.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | D-03/TODO-PYTEST-ISO: explicit-path pytest invocations redirect `DATABASE_URL`→`TEST_DATABASE_URL` exactly like a bare run | ✓ VERIFIED | `conftest.py` now lives at rootdir (ancestor of `tests/`, `api/tests/`, `pipeline/tests/`). Ran `./.venv/bin/python -m pytest tests/test_pytest_isolation_invocation_shapes.py -q` myself: 3 passed (bare, explicit-single-file, explicit-multi-path — the literal Phase-45 wipe shape). Independently confirmed the redirect is live: `TEST_DATABASE_URL` resolves to database `scotus_test`. |
| 2 | D-03: a DB-gated test fails loudly when `TEST_DATABASE_URL` is set but the rootdir redirect did not fire (fail-closed) | ✓ VERIFIED | Code present in `api/tests/conftest.py`/`pipeline/tests/conftest.py` (`_require_root_conftest_redirect` asserting `config._scotus_redirect_fired` and `DATABASE_URL == TEST_DATABASE_URL`). This is a state-invariant (behavior-dependent) truth; the negative path was actually exercised (not just asserted from code) during plan 46-03 Task 3: rootdir `conftest.py` renamed away, guard aborted, restored, re-passed — recorded in `46-03-SUMMARY.md` and reviewed/approved by the operator ("Approved on the row-count/fail-closed evidence"). No *automated* regression re-exercises this negative path on every future change (noted as a minor gap below, not blocking). |
| 3 | TODO-PYTEST-ISO: the dev-DB row-count tripwire arms for every invocation shape | ✓ VERIFIED | `pytest_sessionstart`/`pytest_sessionfinish` live in the same rootdir `conftest.py`, capturing `_REAL_DATABASE_URL` before any redirect. Directly exercised: ran `pytest api/tests/test_arguments.py -q` (the historically dangerous explicit-path shape) and the full suite once (`1024 passed, 5 failed [pre-existing], 6 skipped, 5 xfailed`), and queried the real dev DB myself before/after each — `people=36, arguments=4, cases=4, utterances=1001` unchanged in every case. |
| 4 | D-03: a permanent regression test fails if the sibling-conftest blind spot recurs | ✓ VERIFIED | `tests/test_pytest_isolation_invocation_shapes.py` exists, runs pytest as a real subprocess for all 3 shapes, asserts exit 0 — genuinely hermetic (uses placeholder DSNs, no real DB I/O). Passed when I ran it. |
| 5 | CR-01 (code-review fix): `clean_db`/`test_db_url` in `pipeline/tests/conftest.py` never fall back to `DATABASE_URL` and require database name `scotus_test` | ✓ VERIFIED | Read `pipeline/tests/conftest.py:36-67` — `test_db_url` now `pytest.skip()`s unless `TEST_DATABASE_URL` is set AND `make_url(url).database == "scotus_test"`, mirroring `_reset_test_db`'s pre-existing guard. Commit `730c3571`. This closes exactly the gap the reviewer found (a sibling fixture in a phase-46-touched file that could still TRUNCATE the shared dev DB). |
| 6 | CR-02 (code-review fix): `WIN_HOST_IP` is validated before use in `dev-start.sh`'s `sed`/`bash -c` sinks | ✓ VERIFIED | Read `scripts/dev-start.sh:78-97` — `resolve_win_host_ip` now regex-validates `^([0-9]{1,3}\.){3}[0-9]{1,3}$` and exits 1 on a non-IPv4 result, before either sink runs. `bash -n scripts/dev-start.sh` (implicit via prior review) confirmed syntactically valid; code matches the reviewer's prescribed fix exactly. Commit `feaf7476`. |
| 7 | WR-01 (code-review fix): the dev-DB leak tripwire watches all 10 truncated tables, not just 2 | ✓ VERIFIED | Read `conftest.py:63-103` — `_WATCHED_TABLES` now lists all 10 tables matching `pipeline/tests/conftest.py`'s TRUNCATE list; `_query_watched_table_counts` used by both `pytest_sessionstart`/`pytest_sessionfinish`. Commit `ded0c2a6`. |
| 8 | WR-02/WR-03/WR-04 (code-review fixes): host-probe correctness, configurable NAT range, deduplicated placeholder guard | ✓ VERIFIED | `scripts/dev-start.sh` now sets/reads `PROBE_HOST` (not `WIN_HOST_IP` directly) and exposes `SCOTUS_DEV_HOST_PATTERN` as an overridable env var; `tests/_db_guard.py::is_db_configured` is now the single shared placeholder check, imported by both `conftest.py` and `api/tests/conftest.py`. Commits `e63c4576`, `423f29a5`, `3b4d7f8c`. |
| 9 | D-02: Windows `postgresql-x64-18` service reachable from WSL over the resolved gateway, scoped to the WSL subnet only | ✓ VERIFIED | `46-WINDOWS-POSTGRES-SETUP.md` records `listen_addresses='*'`, a `pg_hba.conf` host rule scoped to `172.26.32.0/20`, and a Windows Firewall rule scoped to the same CIDR (not `0.0.0.0/0`). Directly ran `tests/test_wsl_postgres_reachability.py`: 2 passed. |
| 10 | D-02: both `scotus`/`scotus_test` databases at Alembic head, no `Base.metadata.create_all` | ✓ VERIFIED | Ran `./.venv/bin/python -m alembic current`: `0025 (head)`. `grep -rn 'metadata\.create_all('` across the codebase returns zero real invocations (confirmed in `deferred-items.md` and re-confirmed by my own read of `conftest.py`/pipeline conftest — no DDL calls). |
| 11 | D-01: a WSL-native Python 3.12 venv exists and is what GSD's own tooling invokes | ✓ VERIFIED | `.venv/bin/python` → `python3.12` → `/home/jason/.local/bin/python3.12`, reports `Python 3.12.13`. `.planning/config.json`'s `workflow.test_command` is `"./.venv/bin/python -m pytest"` (repo-relative, WSL-native). |
| 12 | D-01: WSL-native Node/vite (plain `ps`/`kill` can identify processes) | ✓ VERIFIED | `app/node_modules/@esbuild/` contains only `linux-x64` (no Windows binaries); `app/node_modules/.bin/vite` resolves to a real JS entrypoint under the WSL-native tree. `46-05-SUMMARY.md`'s independently-captured `ps -eo pid,pgid,cmd`/`ss -ltnp` output shows real WSL uvicorn/vite processes bound to `0.0.0.0:8000`/`*:5173`. |
| 13 | D-03: a single start/stop entry point brings up Postgres-verify → Alembic → uvicorn → vite with real health checks | ✓ VERIFIED (manual, human-witnessed) | `scripts/dev-start.sh` implements this exact order (read in full: `resolve_win_host_ip` → `sync_env_db_host` → `probe_postgres` → alembic → uvicorn/vite with `wait_for_http`). Live smoke test executed by the operator and independently re-verified by the orchestrator in `46-05-SUMMARY.md` (`curl` 200s on `/health`/`/cases`, clean `--stop` teardown, zero leftover processes). |
| 14 | D-04: repository relocated to native ext4 with byte-identical git history | ✓ VERIFIED | `findmnt -no FSTYPE --target .` → `ext4`. `git rev-parse HEAD` / `git rev-list --all --count` / `git remote get-url origin` all match `46-RELOCATION.md`'s recorded integrity table (adjusted for expected commit growth since). `git fsck --no-dangling` was clean per that record. |
| 15 | D-04: WSL-native venv/node_modules rebuilt (not copied) at the new location | ✓ VERIFIED | `.venv/bin/python3.12` shebang/symlink target is native to the new path; `app/node_modules/@esbuild` is `linux-x64` only (not a mixed-platform copy). |
| 16 | D-04: old checkout left intact as rollback path, disposition an explicit recorded decision | ✓ VERIFIED | `46-RELOCATION.md`'s "Retirement" section records option-c ("leave it in place, marked as retired") with a fresh integrity re-proof and an untracked `RETIRED-CHECKOUT.txt` marker at the old path — consistent with the `?? RETIRED-CHECKOUT.txt` entry visible in that checkout's own `git status`. |
| 17 | D-04: native inotify replaces the watcher-polling workaround | ✓ VERIFIED | `app/vite.config.ts` has no `usePolling`; `scripts/dev-start.sh` has no `WATCHFILES_FORCE_POLLING`. Reload proof recorded in `46-05-SUMMARY.md` (live CSS edit reflected via DevTools with no manual refresh). |
| 18 | D-04: the Windows-side wrapper derives its repo root from its own share-path location, not a hardcoded path | ✓ VERIFIED | Read `scripts/dev-start.ps1` in full — regex-matches its own `$PSScriptRoot` against `\\wsl.localhost\<distro>\...` / `\\wsl$\<distro>\...`, derives `$linuxRepoRoot` from the match, and shells into `wsl.exe -d $distro --cd $linuxRepoRoot -- bash ./scripts/dev-start.sh @args`. No hardcoded path. |
| 19 | Retired in-repo PostgreSQL directories (`data/pgsql`, `data/pgdata`) removed at the current repo | ✓ VERIFIED | `find . -iname pgsql -o -iname pgdata` (excluding node_modules) returns nothing at the current repository. |
| 20 | Documentation reflects exactly one setup path / one PostgreSQL story / one start command | ✓ VERIFIED | `README.md` documents WSL-native ext4, the single Windows-Postgres-service path with all 3 access gates, and `scripts/dev-start.sh` as the sole start command; no references to portable `pg_ctl`/`initdb`/`Activate.ps1` remain (confirmed via targeted greps). |

**Score:** 20/20 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `conftest.py` (root) | rootdir redirect + fail-closed sentinel + full-table tripwire | ✓ VERIFIED | Read in full; matches all 46-01/WR-01 must-haves |
| `tests/test_pytest_isolation_invocation_shapes.py` | subprocess regression test, 3 shapes | ✓ VERIFIED | 3 passed when run |
| `api/tests/test_db_isolation_probe.py` | fail-closed sentinel probe | ✓ VERIFIED | passed when run |
| `pipeline/tests/test_db_isolation_probe.py` | fail-closed sentinel probe | ✓ VERIFIED | passed when run |
| `tests/_db_guard.py` | shared placeholder-DSN guard (WR-04) | ✓ VERIFIED | imported by `conftest.py` and `api/tests/conftest.py` |
| `pipeline/tests/conftest.py` | `test_db_url` hard-guarded to `scotus_test` only (CR-01) | ✓ VERIFIED | Read in full |
| `scripts/dev-start.sh` | WSL-native start/stop, IP-validated, PROBE_HOST-correct | ✓ VERIFIED | Read in full; executable (100755), tracked |
| `scripts/dev-start.ps1` | thin share-path-aware wrapper | ✓ VERIFIED | Read in full |
| `app/vite.config.ts` | explicit server block, no polling workaround | ✓ VERIFIED | Read in full |
| `tests/test_wsl_postgres_reachability.py` | live reachability + drift negative control | ✓ VERIFIED | 2 passed when run |
| `.env.example` | WSL-host-IP convention documented, no literal address | ✓ VERIFIED | present, referenced by README |
| `.planning/phases/.../46-WINDOWS-POSTGRES-SETUP.md` | Windows-side config evidence | ✓ VERIFIED | present, read in full |
| `.planning/config.json` | `workflow.test_command` → WSL-native venv | ✓ VERIFIED | confirmed `./.venv/bin/python -m pytest` |
| `README.md` | single documented setup path | ✓ VERIFIED | read relevant sections |
| `.planning/phases/.../46-RELOCATION.md` | relocation + retirement evidence | ✓ VERIFIED | read in full |
| `.planning/phases/.../46-VALIDATION.md` | validated, nyquist_compliant true | ✓ VERIFIED | frontmatter confirms both |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| root `conftest.py` location | pytest rootdir (`pytest.ini`) | ancestor-of-testpaths mechanics | ✓ WIRED | `pytest.ini` still declares `testpaths = tests pipeline/tests api/tests`; `conftest.py` sits beside it |
| `config._scotus_redirect_fired` sentinel | fail-closed assertions in both sibling conftests | `pytestconfig` fixture param | ✓ WIRED | both `api/tests/conftest.py` and `pipeline/tests/conftest.py` assert on it |
| `_REAL_DATABASE_URL` | `pytest_sessionstart`/`pytest_sessionfinish` tripwire | module-level capture before redirect | ✓ WIRED | confirmed live: dev-DB counts checked directly, unchanged across all runs |
| `ip route show default` gateway | `.env`'s `DATABASE_URL`/`TEST_DATABASE_URL` host | `dev-start.sh`'s `sync_env_db_host`/`sed` | ✓ WIRED | validated shape-checked before use (CR-02); reachability test passed |
| `pipeline/tests/conftest.py`'s `test_db_url` | `engine`/`async_session`/`clean_db` | fixture chaining | ✓ WIRED | all three build on `test_db_url`'s guarded return value (CR-01) |
| `scripts/dev-start.ps1` | `scripts/dev-start.sh` | `wsl.exe -d $distro --cd $linuxRepoRoot -- bash ./scripts/dev-start.sh` | ✓ WIRED | read in full |
| README's startup section | `scripts/dev-start.sh` | doc references the actual script name | ✓ WIRED | confirmed via grep |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Isolation fires for all 3 invocation shapes | `pytest tests/test_pytest_isolation_invocation_shapes.py -q` | 3 passed | ✓ PASS |
| WSL→Windows Postgres reachability | `pytest tests/test_wsl_postgres_reachability.py -q` | 2 passed | ✓ PASS |
| Fail-closed sentinel probes | `pytest api/tests/test_db_isolation_probe.py pipeline/tests/test_db_isolation_probe.py -q` | 2 passed | ✓ PASS |
| Historically-dangerous explicit-path invocation does not touch dev DB | `pytest api/tests/test_arguments.py -q` + row-count query before/after | 5 passed; `people/arguments/cases/utterances` byte-identical before and after | ✓ PASS |
| Full suite (run once, per verifier constraints) leaves dev DB untouched | `pytest -q` + row-count query before/after | `1024 passed, 5 failed (pre-existing), 6 skipped, 5 xfailed`; dev-DB counts unchanged | ✓ PASS |
| Alembic head on dev DB | `alembic current` | `0025 (head)` | ✓ PASS |
| Repository on ext4 | `findmnt -no FSTYPE --target .` | `ext4` | ✓ PASS |
| `dev-start.sh` executable and tracked | `git ls-files -s scripts/dev-start.sh` | `100755` | ✓ PASS |

The 5 pre-existing full-suite failures (`test_no_create_all_in_codebase` false positive; 4 parametrized `test_resolve_row_update_accepts_each_dropdown_value_and_coerces_enum` cases) are documented in `deferred-items.md`, predate Phase 46 (authored Phase 22/Phase 44), and are unrelated to any D-01..D-04 change — confirmed byte-identical to the pre-fix baseline recorded in `46-REVIEW-FIX.md`.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| D-01 | 46-02, 46-04, 46-05, 46-06 | WSL-native Python/Node processes | ✓ SATISFIED | `.venv`, `node_modules`, `dev-start.sh`, `config.json` all confirmed |
| D-02 | 46-02, 46-03, 46-04, 46-06 | Windows Postgres 18 service, scoped WSL reachability | ✓ SATISFIED | `46-WINDOWS-POSTGRES-SETUP.md`, `test_wsl_postgres_reachability.py` (ran, passed) |
| D-03 | 46-01, 46-03, 46-05, 46-06 | pytest DB-isolation bypass fixed unconditionally; single start/stop entry point | ✓ SATISFIED | isolation tests ran and passed; direct row-count proof before/after explicit-path and full-suite runs; `dev-start.sh` read and confirmed |
| D-04 | 46-04, 46-05, 46-06 | Repository relocated to ext4, native inotify | ✓ SATISFIED | `findmnt` confirms ext4; git integrity confirmed; `vite.config.ts`/`dev-start.sh` confirmed free of polling workarounds |
| Folded todo `2026-08-12-pytest-explicit-paths-bypass-db-isolation.md` | 46-01 | The priority data-loss bug | ✓ SATISFIED (functionally) | Fix verified behaviorally (see truths 1-4 above). **Note:** the todo file itself is still physically located under `.planning/todos/pending/` rather than moved to `.planning/todos/completed/` — a housekeeping gap, not a functional one (see Gaps Summary). |

No orphaned requirements found — REQUIREMENTS.md has no phase-46-specific entries (this phase's requirement IDs come from `46-CONTEXT.md` decisions, as the phase task itself notes), and all 4 decision IDs plus the folded todo are covered by at least one plan's `requirements:` frontmatter.

### Anti-Patterns Found

No blocking anti-patterns (no unresolved `TBD`/`FIXME`/`XXX`, no stub returns, no placeholder implementations) in any file this phase modified. The only `PLACEHOLDER`-matching hits are legitimate identifier names (`_PLACEHOLDER_DATABASE_URL` constants used intentionally in the isolation regression tests), not debt markers.

**Minor, non-blocking observations (informational, not gaps against any must-have):**

1. **A cross-plan documentation commitment appears unfulfilled.** `46-05-SUMMARY.md` explicitly flagged the "orphaned Windows-native `node.exe` intercepting `localhost:5173`" gotcha (Bug 2) as "flagged prominently for plan 46-06's README rewrite to surface in its troubleshooting section." `46-06-SUMMARY.md`'s Task 1 added four new troubleshooting bullets (NAT gateway drift, the three-gate Postgres diagnosis, reload/HMR not firing, Windows-mounted-drive root cause) but none of them describes this specific "browser and WSL curl disagree because a stale Windows-side node.exe is still holding the port" scenario — confirmed absent via `grep -i "netstat\|node\.exe\|forwarding relay\|stale content" README.md` (no matches). This does not map to any must-have truth in the plan frontmatters, so it does not affect the pass/fail determination, but it is a real, specific documentation gap a future operator could hit again.
2. **The folded todo `2026-08-12-pytest-explicit-paths-bypass-db-isolation.md` was never moved from `.planning/todos/pending/` to `.planning/todos/completed/`**, even though its underlying bug is fixed and behaviorally proven. This repository has an established `pending/`→`completed/` convention (6 other items already in `completed/`). Purely a bookkeeping item.
3. **The fail-closed negative path (D-03 truth #2) has no permanent automated regression test** — it was proven once, manually, during plan 46-03's execution (rootdir conftest renamed away, guard aborted, restored) and operator-approved, but no test file re-exercises this specific negative case on every future run. The three isolation test files that do exist (`test_pytest_isolation_invocation_shapes.py` + the two probes) all prove the *positive* path (redirect fires correctly), not the *negative* one (redirect absent → loud failure). Low risk in practice since a removed/renamed rootdir `conftest.py` would also break every other test that depends on `load_dotenv()`/the DB redirect, making the failure obvious immediately — but it is not a dedicated regression test.

None of these three items block phase-goal achievement; they are recorded for completeness per the adversarial-verification mandate, not as reasons to fail the phase.

### Human Verification Required

None. All must-haves that require human judgment (the live start/stop smoke test, the HMR/reload proof, the pre-relocation-checkout retirement decision) were already discharged by a human (the operator) during execution and independently cross-verified by the orchestrator with concrete `ps`/`ss`/`curl` evidence captured in `46-05-SUMMARY.md` and `46-RELOCATION.md` — this verification pass re-confirmed the artifacts and mechanisms those checkpoints depended on are still present and correct on disk, and additionally re-ran the automated regression suite directly rather than trusting the SUMMARY narration.

### Gaps Summary

No gaps found against any must-have truth, artifact, or key link across all 6 plans (46-01 through 46-06) or the code-review-fix cycle (`46-REVIEW.md`/`46-REVIEW-FIX.md`). All 6 code-review findings in scope (2 critical, 4 warning) were independently re-read in the actual source files and confirmed fixed exactly as `46-REVIEW-FIX.md` describes — not merely trusted from that document. The phase's priority goal (the pytest DB-isolation bypass) was verified with direct behavioral evidence obtained by this verifier: dev-database row counts queried before and after (a) the exact historically-dangerous explicit-path invocation and (b) a full 1024-test suite run, both showing zero drift. Three minor, non-blocking observations are recorded above for completeness (a documentation gap, a todo-file bookkeeping gap, and a missing automated negative-path regression test) — none of these were declared as must-haves by any plan and none constitute a functional defect in the delivered fix.

---

_Verified: 2026-08-14T21:45:00Z_
_Verifier: Claude (gsd-verifier)_
