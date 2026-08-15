---
phase: 46
slug: dev-environment-reliability
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-12
---

# Phase 46 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.0 with pytest-asyncio>=0.23 |
| **Config file** | `pytest.ini` (repo root) |
| **Quick run command** | `pytest -q` |
| **Full suite command** | `pytest -q` (testpaths already covers `tests pipeline/tests api/tests`) |
| **Estimated runtime** | ~30-60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest -q` (bare) — must stay green
- **After every plan wave:** Run `pytest -q` full suite, PLUS a manual explicit-path invocation (`pytest api/tests/test_arguments.py -q`) with dev-DB row counts checked before/after — this is the actual regression check for the priority bug (D-03) and cannot be fully automated inside the same pytest process being tested
- **Before `/gsd-verify-work`:** Full suite must be green under BOTH bare and explicit-path invocation shapes
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 46-01-01 | 46-03 | 1 | D-03 (pytest isolation) | T-46-01 | `TEST_DATABASE_URL` redirect fires regardless of invocation shape (bare, explicit single file, explicit subset); dev-DB row counts unchanged across a bare run, the literal Phase 45 wipe command, and two broader explicit-path sweeps; fail-closed guard aborts when the rootdir redirect is absent | integration | 46-03 Task 3: `./.venv/bin/python -m pytest -q`; `./.venv/bin/python -m pytest api/tests/test_published_gate.py api/tests/test_arguments.py -q`; `./.venv/bin/python -m pytest api/tests -q`; `./.venv/bin/python -m pytest pipeline/tests -q` — each re-counting `people`/`arguments`/`cases`/`utterances`, all byte-identical to baseline; fail-closed control with rootdir `conftest.py` renamed away | ✅ | ✅ green |
| 46-01-02 | 46-03 | 1 | D-02 (WSL→Windows Postgres reachable) | T-46-02 | WSL-native process opens a real DB connection to the Windows Postgres service via the dynamically-resolved host IP | integration | `tests/test_wsl_postgres_reachability.py::test_wsl_can_connect_to_windows_postgres` (opens a real `create_async_engine` connection with `connect_args={"statement_cache_size": 0}` and asserts `SELECT 1` returns `1`); `tests/test_wsl_postgres_reachability.py::test_env_db_host_matches_wsl_gateway` (drift negative control, proven via a recorded mutate/observe-failure/restore cycle in 46-03-SUMMARY.md) | ✅ | ✅ green |
| 46-01-03 | 46-05 | 5 | D-03 (single start/stop entry point) | — | Script starts Postgres-verify → alembic → uvicorn → vite in order; health checks pass; SIGINT/SIGTERM cleanly stops both processes | manual/smoke | Covering checkpoint: plan 46-05 Task 3 (`checkpoint:human-verify`, `gate="blocking"`) — operator ran the live stack; orchestrator independently captured `ps -eo pid,pgid,cmd` and `ss -ltnp` showing real WSL-native `uvicorn`/`vite` processes bound to `0.0.0.0:8000`/`*:5173`, `curl` returning `200` on `/health` and `/cases`, and `./scripts/dev-start.sh --stop` cleanly terminating both process groups (46-05-SUMMARY.md, "Task 3: Live Smoke Test — Approved") | ❌ W0 (no automated coverage appropriate) | ✅ green |
| 46-01-04 | 46-04 | 4 | D-04 (repository relocated to native ext4) | T-46-04-01, T-46-04-02 | The working repository lives on ext4 with provably identical git history (same HEAD, same total commit count, clean `git fsck`, intact `origin`), both secret files byte-identical and owner-only, and the full stack — migrations, WSL→Windows Postgres reachability, pytest isolation, full suite, frontend build — proved working from the new location with the dev database unchanged | integration | `findmnt -no FSTYPE --target <new path>` = `ext4`; HEAD SHA and `rev-list --all --count` parity against the pre-relocation checkout; `git fsck --no-dangling`; `cmp -s` on both env files; `./.venv/bin/python -m pytest tests/test_wsl_postgres_reachability.py tests/test_pytest_isolation_invocation_shapes.py -q` from the new root (46-RELOCATION.md integrity table + Rebuilt toolchain section) | ✅ (reuses 46-01/46-03 test files) | ✅ green |
| 46-01-05 | 46-05 | 5 | D-04 (native inotify replaces the watcher workaround) | — | A save from a WSL-connected editor triggers frontend HMR and an API reloader restart with no watcher-polling option configured anywhere; a save from a Windows-native editor through the share path does not, confirming the mechanism rather than luck | manual/smoke | Manual (plan 46-05 Task 3): operator edited `app/src/app.css` from the WSL-connected editor with the stack up and confirmed via browser DevTools that the change applied live with no manual refresh (46-05-SUMMARY.md, "Reload proof (D-04)"); plus `grep -q 'usePolling' app/vite.config.ts` and `grep -q 'FORCE_POLLING' scripts/dev-start.sh` both failing (confirmed absent) | ❌ W0 (no automated coverage appropriate — this is an OS-level notification-delivery property) | ✅ green |

*Status legend: ⬜=not yet run, ✅=green, ❌=red, ⚠️=flaky*

---

## Wave 0 Requirements

- [x] New test file: `tests/test_pytest_isolation_invocation_shapes.py` — subprocess-based test asserting the `TEST_DATABASE_URL` redirect fires for all three invocation shapes (bare, explicit single file, explicit multi-path) (plan 46-01)
- [x] Small integration test: `tests/test_wsl_postgres_reachability.py` — asserts a live WSL→Windows-Postgres connection succeeds using the dynamically-resolved host IP, guarding D-02's networking setup (plan 46-03)

*No pytest-based coverage is appropriate for the start/stop script itself — this is an intentional manual-only verification item, not a gap to fill with an inappropriate test.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Discharged By | Evidence |
|----------|-------------|------------|-------------------|----------------|----------|
| Single start/stop entry point brings up Postgres-verify, alembic, uvicorn, vite with real health checks and clean teardown | D-03 | Orchestration of OS processes/services is not naturally unit-testable; no automated framework covers "did this shell script correctly manage OS processes" | Run the new start script, curl `http://localhost:8000/docs` and `http://localhost:5173`, confirm both return 200; send SIGINT/Ctrl+C; confirm both PIDs are gone via `ps aux \| grep -E 'uvicorn\|vite'` | Plan 46-05, Task 3 (`checkpoint:human-verify`) | `46-05-SUMMARY.md`, "Task 3: Live Smoke Test — Approved" |
| Windows Postgres 18 service reachable from WSL after `listen_addresses`/`pg_hba.conf`/Firewall changes | D-02 | Requires Windows-side admin action (service config, firewall rule) this phase's automated tests cannot perform | From a Windows admin shell: verify `postgresql.conf`, `pg_hba.conf`, and an inbound Firewall rule for TCP 5432 scoped to the WSL subnet; then from WSL, TCP-probe the resolved host IP on port 5432 and confirm a real DB connection succeeds | Plan 46-02, Task 1 (`checkpoint:human-action`) | `46-WINDOWS-POSTGRES-SETUP.md` |
| Repeated dev-DB wipe regression (the priority bug) does not recur | D-03 (folded todo) | The actual regression is "does explicit-path pytest still hit the live dev DB," which is best proven empirically against real dev-DB row counts, not just asserted from code | Seed the dev DB via `POST /api/admin/dev/reset-to-fixture`, note row counts, run `pytest api/tests/test_published_gate.py api/tests/test_arguments.py -q`, confirm dev-DB row counts are unchanged afterward | Plan 46-03, Task 3 (`checkpoint:human-verify`) | `46-03-SUMMARY.md`, "Task 3 Row-Count Table" |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-14
