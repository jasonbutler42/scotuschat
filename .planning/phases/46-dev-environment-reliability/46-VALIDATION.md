---
phase: 46
slug: dev-environment-reliability
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 46-01-01 | TBD | 1 | D-03 (pytest isolation) | T-46-01 | `TEST_DATABASE_URL` redirect fires regardless of invocation shape (bare, explicit single file, explicit subset) | integration | subprocess-based test invoking pytest 3 ways, asserting `DATABASE_URL` resolves to the test DB each time | ❌ W0 | ⬜ pending |
| 46-01-02 | TBD | 1 | D-02 (WSL→Windows Postgres reachable) | T-46-02 | WSL-native process opens a real DB connection to the Windows Postgres service via the dynamically-resolved host IP | integration | small pytest/asyncpg test running `SELECT 1` against the resolved host | ❌ W0 | ⬜ pending |
| 46-01-03 | TBD | 1 | D-03 (single start/stop entry point) | — | Script starts Postgres-verify → alembic → uvicorn → vite in order; health checks pass; SIGINT/SIGTERM cleanly stops both processes | manual/smoke | Manual: run script, curl both health endpoints, Ctrl+C, verify both PIDs gone (`ps aux \| grep -E 'uvicorn\|vite'`) | ❌ W0 (no automated coverage appropriate) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] New test file (name TBD by planner, e.g. `tests/test_pytest_isolation_invocation_shapes.py`) — subprocess-based test asserting the `TEST_DATABASE_URL` redirect fires for all three invocation shapes (bare, explicit single file, explicit multi-path)
- [ ] Small integration test asserting a live WSL→Windows-Postgres connection succeeds using the dynamically-resolved host IP (guards D-02's networking setup, not just D-03's redirect fix)

*No pytest-based coverage is appropriate for the start/stop script itself — this is an intentional manual-only verification item, not a gap to fill with an inappropriate test.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Single start/stop entry point brings up Postgres-verify, alembic, uvicorn, vite with real health checks and clean teardown | D-03 | Orchestration of OS processes/services is not naturally unit-testable; no automated framework covers "did this shell script correctly manage OS processes" | Run the new start script, curl `http://localhost:8000/docs` and `http://localhost:5173`, confirm both return 200; send SIGINT/Ctrl+C; confirm both PIDs are gone via `ps aux \| grep -E 'uvicorn\|vite'` |
| Windows Postgres 18 service reachable from WSL after `listen_addresses`/`pg_hba.conf`/Firewall changes | D-02 | Requires Windows-side admin action (service config, firewall rule) this phase's automated tests cannot perform | From a Windows admin shell: verify `postgresql.conf`, `pg_hba.conf`, and an inbound Firewall rule for TCP 5432 scoped to the WSL subnet; then from WSL, TCP-probe the resolved host IP on port 5432 and confirm a real DB connection succeeds |
| Repeated dev-DB wipe regression (the priority bug) does not recur | D-03 (folded todo) | The actual regression is "does explicit-path pytest still hit the live dev DB," which is best proven empirically against real dev-DB row counts, not just asserted from code | Seed the dev DB via `POST /api/admin/dev/reset-to-fixture`, note row counts, run `pytest api/tests/test_published_gate.py api/tests/test_arguments.py -q`, confirm dev-DB row counts are unchanged afterward |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
