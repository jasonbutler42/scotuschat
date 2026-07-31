---
phase: 43
slug: dev-only-reset-to-fixture
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-31
---

# Phase 43 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (`asyncio_mode = auto`) [VERIFIED: pytest.ini] |
| **Config file** | `pytest.ini` (project root) |
| **Quick run command** | `./.venv/Scripts/python.exe -m pytest api/tests/test_admin_dev_routes.py -x` (new file; matches `workflow.test_command` in `.planning/config.json`) |
| **Full suite command** | `./.venv/Scripts/python.exe -m pytest` |
| **Estimated runtime** | Not measured this research pass — new integration tests hit the real/test Postgres via `TEST_DATABASE_URL`, expect low tens of seconds, not minutes |

**Environment note (carried from RESEARCH.md / project memory):** Use `./.venv/Scripts/python.exe` via WSL interop to reach the real Postgres first; ephemeral `pgserver` only as fallback. Any DB-touching test/verification task in this phase's plans must run against `TEST_DATABASE_URL` (the `scotus_test` database) — never the shared dev DB. Phase 31's `pytest_sessionfinish` row-count guard already fails any run that changes shared-dev-DB row counts, so a test that accidentally calls `reset_to_fixture` against the wrong database will be caught, but tests should be written to use `TEST_DATABASE_URL` explicitly rather than relying on that guard as the primary safety net.

---

## Sampling Rate

- **After every task commit:** Run `./.venv/Scripts/python.exe -m pytest api/tests/test_admin_dev_routes.py -x`
- **After every plan wave:** Run `./.venv/Scripts/python.exe -m pytest`
- **Before `/gsd-verify-work`:** Full suite must be green, run against `scotus_test` (never the shared dev DB)
- **Max feedback latency:** Not measured — flag if any single test file exceeds ~30s during execution

---

## Per-Task Verification Map

*Populated once PLAN.md tasks exist (planner assigns Task IDs). Interim requirement-level mapping from RESEARCH.md's Validation Architecture section stands in until then.*

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEVTOOL-01 | Reset wipes all named tables and reseeds exactly the 4 fixtures + their people | integration | `pytest api/tests/test_admin_dev_routes.py::test_reset_wipes_and_reseeds_fixtures -x` (against `scotus_test` via `TEST_DATABASE_URL`) | ❌ Wave 0 |
| DEVTOOL-01 | Draft/Published/Mid-pipeline fixtures land in their labeled state after reset | integration | `pytest api/tests/test_admin_dev_routes.py::test_reset_realizes_state_variety -x` | ❌ Wave 0 |
| DEVTOOL-02 | Reset endpoint is absent (404, not 403) when `environment != "development"` | unit (module re-import) | `pytest tests/test_admin_dev_router_gate.py::test_dev_router_absent_outside_development -x` | ❌ Wave 0 |
| DEVTOOL-02 | Dev Tools section is absent from `/admin` HTML response when `environment != "development"` | integration (SvelteKit) | `npm run test -- admin-dev-tools-visibility` (or manual UAT if no frontend test harness exists for `/admin` today — verify at plan time) | ❌ Wave 0 (frontend test harness for `/admin` not yet confirmed to exist) |
| DEVTOOL-01 | Confirm/Cancel two-step dialog states behave per 43-UI-SPEC.md | manual UAT | n/a (visual/interaction) | manual-only |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `api/tests/test_admin_dev_routes.py` — new file, covers DEVTOOL-01 (reset behavior) and the auth-still-required check on the new router
- [ ] `tests/test_admin_dev_router_gate.py` — new file (root-level `tests/`, matching where `test_admin_router.py`'s re-import smoke test already lives), covers DEVTOOL-02's route-absence behavior via the module re-import technique
- [ ] Confirm whether a frontend test harness exists for `/admin` pages at all (none found under `app/tests/` for `/admin` specifically during research — verify at plan time before committing to an automated frontend test for the Dev Tools section's visibility gate; manual UAT is an acceptable fallback for DEVTOOL-02's frontend half)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| Confirm/Cancel two-step dialog states (copy, button order, wipe summary) match 43-UI-SPEC.md | DEVTOOL-01 | Visual/interaction behavior on `/admin` — not meaningfully assertable via backend integration test alone | Open `/admin` in a development-environment build, trigger "Reset to Fixture," confirm the dialog states exactly what will be wiped, cancel once to confirm no side effects, then confirm and observe the running/success states per 43-UI-SPEC.md |
| Dev Tools section is visually absent (not just gated) on `/admin` in a production-like build | DEVTOOL-02 | Confirms the server-side omission (D-07) end-to-end in a rendered page, not just at the load-function/unit level | Build/run the frontend with `environment` unset or non-development, load `/admin`, confirm the Dev Tools section is entirely absent from the rendered HTML (view-source, not just visually hidden) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
