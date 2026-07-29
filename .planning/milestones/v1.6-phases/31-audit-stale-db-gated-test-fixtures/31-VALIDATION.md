---
phase: 31
slug: audit-stale-db-gated-test-fixtures
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-14
audited: 2026-07-14
requirements_covered: [TEST-01, TEST-02]
requirements_missing: []
---

# Phase 31 — Validation Strategy

> Retroactively reconstructed Nyquist validation contract from the eight executed plans, summaries, and the current test suite.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pytest.ini` |
| **Python environment** | `.venv/Scripts/python.exe` (Windows) |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest api/tests/test_isolation_survives_inner_commit.py pipeline/tests/test_ingest.py pipeline/tests/test_parse.py pipeline/tests/test_resolve.py pipeline/tests/test_seed_aliases.py pipeline/tests/test_pipeline_run.py -q` |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest -q` |
| **Current full-suite result** | `446 passed, 5 xfailed` |
| **Measured runtime** | 70.76 seconds on 2026-07-14 |

---

## Sampling Rate

- **After isolation or fixture changes:** Run the targeted isolation and affected fixture tests.
- **After each plan wave:** Run `.\.venv\Scripts\python.exe -m pytest -q`.
- **Before `$gsd-verify-work`:** Full suite must be green and the session-finish leak hook must report no shared-dev-DB row drift.
- **Max measured feedback latency:** approximately 71 seconds for the full suite.

---

## Requirement Coverage

| Requirement | Covered Behavior | Automated Evidence | Status |
|-------------|------------------|--------------------|--------|
| TEST-01 | Tests are isolated from the shared dev database; inner commits remain inside `scotus_test`; full-suite execution leaves shared `people` and `arguments` counts unchanged. | `api/tests/test_isolation_survives_inner_commit.py`, root `tests/conftest.py` session leak hooks, and `.\.venv\Scripts\python.exe -m pytest -q` | ✅ green |
| TEST-02 | Previously stale API and pipeline DB fixtures match the current schema and execute without NOT NULL or enum drift failures. | Target suites from Plans 31-05 and 31-06 plus `.\.venv\Scripts\python.exe -m pytest -q` | ✅ green |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 31-01-01 | 01 | 1 | TEST-01 | static + integration | Python AST parse; `.env.example` TEST_DATABASE_URL check | ✅ | ✅ green |
| 31-01-02 | 01 | 1 | TEST-01 | collection + integration | conftest AST parse; pipeline collection | ✅ | ✅ green |
| 31-02-01 | 02 | 1 | TEST-01 | static | root conftest AST parse | ✅ | ✅ green |
| 31-02-02 | 02 | 1 | TEST-01 | integration | leak-hook structure check; full pytest suite | ✅ | ✅ green |
| 31-03-01 | 03 | 1 | TEST-01, TEST-02 | collection | API conftest structure check; API collection | ✅ | ✅ green |
| 31-03-02 | 03 | 1 | TEST-02 | static + collection | removed local fixtures; API collection | ✅ | ✅ green |
| 31-03-03 | 03 | 1 | TEST-02 | static + collection | single shared fixture check; API collection | ✅ | ✅ green |
| 31-04-01 | 04 | 1 | TEST-01 | static | cleanup script parse and detection-query checks | ✅ | ✅ green |
| 31-04-02 | 04 | 1 | TEST-01 | static | execute-gate and destructive-DDL exclusion checks | ✅ | ✅ green |
| 31-05-01 | 05 | 1 | TEST-02 | integration | five targeted API DB-fixture test files | ✅ | ✅ green |
| 31-06-01 | 06 | 1 | TEST-02 | integration | five targeted pipeline DB-fixture test files | ✅ | ✅ green |
| 31-07-01 | 07 | 1 | TEST-01 | regression | `api/tests/test_isolation_survives_inner_commit.py` | ✅ | ✅ green |
| 31-07-02 | 07 | 1 | TEST-01, TEST-02 | acceptance | `.\.venv\Scripts\python.exe -m pytest -q` | ✅ | ✅ green |
| 31-08-01 | 08 | 1 | TEST-01 | safe operational probe | cleanup script dry-run | ✅ | ✅ green |
| 31-08-02 | 08 | 1 | TEST-01 | operator-gated acceptance | authorized cleanup, `import-justices`, then full suite | ✅ | ✅ complete |

All fifteen tasks have an automated command or, for the destructive cleanup, an automated command behind an explicit operator authorization checkpoint.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No missing test stubs, fixtures, framework installation, or generated test files are required.

---

## Manual-Only Verifications

All ongoing phase behaviors have automated verification. Plan 31-08's destructive shared-database cleanup required operator authorization, was completed during execution, and is not an outstanding manual-only validation gap.

---

## Validation Audit 2026-07-14

| Metric | Count |
|--------|-------|
| Requirements audited | 2 |
| Tasks audited | 15 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Automated requirements | 2 |
| Manual-only requirements | 0 |

Current verification: `.\.venv\Scripts\python.exe -m pytest -q` → **446 passed, 5 xfailed in 70.76 seconds**. The five xfails are documented unimplemented stubs and do not represent Phase 31 schema-drift or isolation failures.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verification or an explicit operator-gated command.
- [x] Sampling continuity: no three consecutive tasks lack automated verification.
- [x] Existing infrastructure covers all references; no Wave 0 gaps remain.
- [x] No watch-mode flags are used.
- [x] Full-suite feedback latency is under 90 seconds in the current environment.
- [x] `nyquist_compliant: true` is set in frontmatter.

**Approval:** approved 2026-07-14
