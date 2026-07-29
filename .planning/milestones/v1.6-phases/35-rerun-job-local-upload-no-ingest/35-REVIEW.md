---
phase: 35-rerun-job-local-upload-no-ingest
reviewed: 2026-07-15T03:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - api/routers/admin.py
  - api/services/admin_jobs.py
  - api/schemas/admin_jobs.py
  - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
  - api/tests/test_admin_jobs_phase35_frontend.py
  - api/tests/test_admin_jobs_phase35.py
  - api/tests/test_admin_jobs_phase25.py
findings:
  critical: 0
  warning: 2
  info: 0
  total: 2
status: issues_found
---

# Phase 35: Code Review Report

**Reviewed:** 2026-07-15T03:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

The production capability removal is narrowly implemented: the backend route, service seam, and SvelteKit action are absent while the neighboring creation, recovery, authentication, history, and PDF-delivery contracts remain intact. Two test-reliability defects weaken the regression evidence: the central route-absence test is unnecessarily skipped without a database, and a failed create-route assertion can leave committed database state behind.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: The primary removal regression is skipped when no database is configured

**File:** `api/tests/test_admin_jobs_phase35.py:29-34`
**Issue:** The authenticated retired-route test is guarded by `_db_configured()`, but an unmatched FastAPI route is resolved before any database dependency is invoked. This makes the phase's central removal proof disappear in environments that intentionally run database-free API contract tests, even though the test itself does not need a database. A later accidental reintroduction of the route could therefore go undetected in those runs.
**Fix:** Remove the `@pytest.mark.skipif(not _db_configured(), ...)` decorator from `test_authenticated_retired_rerun_route_returns_framework_404`. Keep the valid admin header so the test continues to distinguish the intended authenticated contract.

### WR-02: A failed create-route assertion leaks a committed AdminJob row

**File:** `api/tests/test_admin_jobs_phase35.py:79-91`
**Issue:** The ordinary-create request commits an `AdminJob`, but cleanup is not protected by `try/finally`. If the status, response parsing, or spawn-argument assertion fails, execution never reaches lines 87-91. The leaked row can contaminate later count/order/history tests and make failures order-dependent, especially in the shared configured test database used by this module.
**Fix:** Capture `job_id` after the response is known to contain it, then wrap all subsequent assertions in `try` and perform deletion in `finally`. For failures before `job_id` is available, query and clean up using a unique source value created specifically for this test, or use a fixture that records and always deletes created job IDs.

---

_Reviewed: 2026-07-15T03:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
