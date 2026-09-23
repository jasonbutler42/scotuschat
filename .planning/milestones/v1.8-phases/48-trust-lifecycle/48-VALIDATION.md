---
phase: 48
slug: trust-lifecycle
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-18
---

# Phase 48 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (`asyncio_mode = auto`) |
| **Config file** | `pytest.ini` (`testpaths = tests pipeline/tests api/tests`, `pythonpath = .`) |
| **Quick run command** | `./.venv/bin/python -m pytest <task's test module> -q` |
| **Full suite command** | `./.venv/bin/python -m pytest` |
| **Estimated runtime** | ~120 seconds (full suite; 1049 passed / 5 xfailed at the 2026-08-18 baseline) |

DB-gated tests run against `scotus_test` via `TEST_DATABASE_URL`; the repository-root
`conftest.py` fails any run that changes shared-dev-DB row counts (CLAUDE.md invariant,
regression-locked by `tests/test_pytest_isolation_invocation_shapes.py`).

---

## Sampling Rate

- **After every task commit:** Run `./.venv/bin/python -m pytest <that task's test module> -q`
- **After every plan wave:** Run `./.venv/bin/python -m pytest api/tests pipeline/tests -q`
- **Before `/gsd-verify-work`:** Full suite must be green (`./.venv/bin/python -m pytest`), plus the
  live D-09/D-21 vehicle: `reset_to_fixture` → `pipeline recompute-trust --all` → assert 0 rows changed
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | TRUST-01 | — | N/A | unit | `./.venv/bin/python -m pytest api/tests/test_trust_domain.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | TRUST-02 | — | N/A | unit + integration | `./.venv/bin/python -m pytest api/tests/test_trust_recompute.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | TRUST-03 | — | N/A | integration | `./.venv/bin/python -m pytest pipeline/tests/test_import_convokit_core.py -x` | ✅ | ⬜ pending |
| TBD | TBD | TBD | TRUST-04 | T-48-PUBGATE | Publish hard-blocked while any UNCERTAIN element remains; `resolved_at IS NULL` stays separately non-overridable | integration | `./.venv/bin/python -m pytest api/tests/test_published_gate.py -x` | ✅ | ⬜ pending |
| TBD | TBD | TBD | TRUST-05 | T-48-REASON | Whitespace-only `override_reason` rejected server-side, independent of the UI | integration | `./.venv/bin/python -m pytest api/tests/test_admin_arguments_routes.py -x` | ✅ | ⬜ pending |
| TBD | TBD | TBD | D-22 (carried defect) | — | N/A | integration | `./.venv/bin/python -m pytest api/tests/test_admin_arguments_service.py -x` | ✅ | ⬜ pending |
| TBD | TBD | TBD | D-23 (public-leak ban) | T-48-LEAK | No public response body contains `trust_tier` | contract | `./.venv/bin/python -m pytest api/tests/test_arguments.py -x` | ✅ | ⬜ pending |

*Task IDs, plan numbers, and waves are filled in by `/gsd-validate-phase` once PLAN.md files exist.*

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `api/tests/test_trust_domain.py` — pure unit coverage for `derive_tier` / `floor_tier`, including
      the empty-list UNCERTAIN base case (no DB; fastest feedback loop)
- [ ] `api/tests/test_trust_recompute.py` — DB-gated coverage of `recompute_argument_tier` against
      `TEST_DATABASE_URL`: every tier combination D-21 requires, the NULL `person_id` UNCERTAIN case,
      and the stage-direction exclusion
- [ ] A DB-gated regression test proving `delete_argument` fails with `ForeignKeyViolation` before the
      D-22 fix and passes after (failing-then-passing, per D-22)
- [ ] Framework install: none — pytest / pytest-asyncio already configured

*No shared-fixture gaps beyond the above — the rootdir `conftest.py` DB-redirect already covers every
new test file under `api/tests/` and `pipeline/tests/`.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `reset_to_fixture` → `pipeline recompute-trust --all` reports 0 rows changed | TRUST-01, TRUST-02 (D-09 / D-21) | Drives four fixtures through real service calls against the dev DB; deliberately not run under `TEST_DATABASE_URL` isolation | Reseed via `reset_to_fixture`, then run `pipeline recompute-trust --all` and assert it reports zero rows changed — a non-zero count means a writer path skipped its in-transaction recompute |
| Admin argument detail page shows the block reason and the override prompt | TRUST-04, TRUST-05 | Browser-only UI affordance on `/admin/arguments/[id]` | Open a candidate argument carrying an UNCERTAIN element, attempt publish, confirm the block reason renders and the override prompt requires a non-empty reason before submit |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
