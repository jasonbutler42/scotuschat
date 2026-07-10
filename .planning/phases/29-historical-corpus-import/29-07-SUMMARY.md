---
phase: 29-historical-corpus-import
plan: 07
subsystem: api
tags: [pydantic, fastapi, response-schema, regression-test, corpus-import]

# Dependency graph
requires:
  - phase: 29-historical-corpus-import
    provides: import_convokit.py's _parse_argued_date producing legitimate null argued_date values for historical rows
provides:
  - ArgumentMetadataResponse.argued_date and CaseItem.argued_date accept None without a pydantic ValidationError
  - Regression tests proving GET /arguments/{id}/utterances survives a null argued_date (200, not 500)
  - Frontend parity fix: app/src/routes/cases/[slug]/+page.svelte's formatDate() now null-guards like its two siblings
affects: [29-verification, 29-review, admin-arguments, public-cases]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Optional response fields over nullable DB columns: schema field type must mirror the column's nullability, not assume the historical always-present case"

key-files:
  created:
    - api/tests/test_case_item_argued_date_optional.py
  modified:
    - api/schemas/utterance.py
    - api/schemas/cases.py
    - app/src/routes/cases/[slug]/+page.svelte
    - api/tests/test_argument_oyez_field.py

key-decisions:
  - "No service-layer change needed: api/services/arguments.py and api/services/cases.py already pass argument.argued_date through with no coercion; confirmed via git diff --stat showing zero changes to either file"
  - "New DB-gated regression test calls get_argument_with_utterances() directly (no HTTP client, no api.main import) to avoid the documented pre-existing FastAPI test lifespan/session-factory failure"
  - "CaseItem.argued_date fixed proactively even though unreachable today (get_cases() filters WHERE published_at IS NOT NULL) — avoids a second gap-closure round once a corpus-imported draft with a null argued_date is published"

patterns-established:
  - "Optional[date] = None over a nullable Date column is the correct Pydantic v2 pattern for any future response schema mirroring an Argument.argued_date-shaped column"

requirements-completed: [CORPUS-03, CORPUS-10]

coverage:
  - id: D1
    description: "ArgumentMetadataResponse and CaseItem accept argued_date=None without raising pydantic.ValidationError"
    requirement: "CORPUS-10"
    verification:
      - kind: unit
        ref: "api/tests/test_argument_oyez_field.py#test_argument_metadata_response_accepts_null_argued_date"
        status: pass
      - kind: unit
        ref: "api/tests/test_case_item_argued_date_optional.py#test_case_item_accepts_null_argued_date"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /arguments/{argument_id}/utterances returns 200 (not 500) for an Argument with a null argued_date, via the real get_argument_with_utterances -> ArgumentUtterancesResponse construction path"
    requirement: "CORPUS-03"
    verification:
      - kind: integration
        ref: "api/tests/test_argument_oyez_field.py#test_utterances_endpoint_returns_200_for_null_argued_date"
        status: unknown
    human_judgment: true
    rationale: "Test is DB-gated (skipif not _db_configured()) and, when DATABASE_URL is set, hits a documented pre-existing FastAPI test lifespan/session-factory failure in the AsyncSessionLocal fixture pattern (same root cause affecting 14 tests in test_admin_jobs_phase25.py) — unrelated to this plan's schema fix. The underlying round-trip logic was independently verified correct via a standalone script using a manually constructed engine (bypassing the broken fixture); see Issues Encountered. A human/CI environment with the lifespan bug fixed (or a future test-infra fix) should re-run this test to get an actual pass/fail status."
  - id: D3
    description: "app/src/routes/cases/[slug]/+page.svelte's formatDate() null-guards argued_date, matching its two sibling pages"
    verification:
      - kind: other
        ref: "source diff: app/src/routes/cases/[slug]/+page.svelte formatDate signature + first-line guard, byte-identical to app/src/routes/cases/+page.svelte and app/src/routes/cases/[slug]/arguments/[id]/+page.svelte"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-07-10
status: complete
---

# Phase 29 Plan 07: Widen argued_date to Optional in response schemas Summary

**ArgumentMetadataResponse and CaseItem now accept argued_date=None without a pydantic ValidationError, closing the BLOCKER gap where GET /arguments/{id}/utterances 500'd for historical corpus rows lacking a parseable transcript date.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-10T08:03:12-05:00
- **Completed:** 2026-07-10T08:06:54-05:00
- **Tasks:** 2
- **Files modified:** 5 (2 created new test file counted separately)

## Accomplishments
- `ArgumentMetadataResponse.argued_date` (api/schemas/utterance.py) and `CaseItem.argued_date` (api/schemas/cases.py) widened from bare `datetime.date` to `datetime.date | None = None`, matching the nullable `Argument.argued_date` DB column
- Confirmed (and asserted via `git diff --stat`) that no service-layer change was needed — `get_argument_with_utterances()` and `get_cases()` already pass `argued_date` straight through
- `app/src/routes/cases/[slug]/+page.svelte`'s `formatDate()` brought to parity with its two null-tolerant sibling pages
- Three new regression tests added: two DB-independent (schema-level, run with no `DATABASE_URL` set), one DB-gated (exercises the real service → response-schema construction path)

## Task Commits

Each task was committed atomically:

1. **Task 1: Widen non-optional argued_date response fields to Optional + fix frontend parity gap** - `49fde2c7` (fix)
2. **Task 2: Regression tests proving GET /arguments/{id}/utterances survives a null argued_date, and CaseItem does too** - `d47dc0a8` (test)

**Plan metadata:** (pending — see final commit below)

## Files Created/Modified
- `api/schemas/utterance.py` - `ArgumentMetadataResponse.argued_date` widened to `datetime.date | None = None`
- `api/schemas/cases.py` - `CaseItem.argued_date` widened to `datetime.date | None = None`, with a code comment noting it is not reachable today (published_at filter) but fixed proactively
- `app/src/routes/cases/[slug]/+page.svelte` - `formatDate()` now accepts `string | null | undefined` and guards with `if (!dateStr) return 'Date unknown';`
- `api/tests/test_argument_oyez_field.py` - added `test_argument_metadata_response_accepts_null_argued_date` (DB-independent) and `test_utterances_endpoint_returns_200_for_null_argued_date` (DB-gated, direct service-call path)
- `api/tests/test_case_item_argued_date_optional.py` - new file, `test_case_item_accepts_null_argued_date` (DB-independent)

## Decisions Made
- No service-layer code touched — pass-through was already correct; adding a coercion/default would have been unnecessary scope creep
- New DB-gated test calls `get_argument_with_utterances()` and constructs `ArgumentUtterancesResponse` directly rather than going through an HTTP client/`api.main`, per the plan's explicit instruction to avoid the documented pre-existing FastAPI test lifespan/session-factory failure
- `CaseItem.argued_date` fixed now (not deferred) even though currently unreachable, per the gap's own investigation mandate to grep `argued_date` across `api/` for duplicate instances of the same pattern

## Deviations from Plan

None - plan executed exactly as written. Both tasks matched their `<action>` blocks precisely; no Rule 1-4 auto-fixes were required beyond what the plan itself specified.

## Issues Encountered

- The new DB-gated test (`test_utterances_endpoint_returns_200_for_null_argued_date`) uses the same `db_session` fixture pattern the plan explicitly directed (mirroring `test_admin_jobs_phase25.py`'s `AsyncSessionLocal`-based fixture). When run with `DATABASE_URL` actually set, this fixture raises `TypeError: 'NoneType' object is not callable` because `api.core.database.AsyncSessionLocal` is only initialized inside the FastAPI `lifespan` context manager, not at import time — a documented pre-existing issue (project memory: "FastAPI test lifespan/session-factory failure (open, pre-existing, ~57 tests)") that independently affects 14 of 32 tests in `test_admin_jobs_phase25.py` itself, unrelated to this plan's changes. This is out of scope per the SCOPE BOUNDARY rule (pre-existing, not caused by this plan's edits).
  - To confirm the underlying fix and test logic are correct despite the broken fixture, I independently verified the exact same code path (create a `Case`/`Argument`/`CaseArgument` with `argued_date=None`, call `get_argument_with_utterances()`, construct `ArgumentUtterancesResponse(**result)`) using a manually constructed `create_async_engine`/`async_sessionmaker` (bypassing the lifespan-gated `AsyncSessionLocal` global) in a scratch script. Result: `PASS: argued_date None round-trips correctly, no ValidationError`, and a follow-up query confirmed zero leftover rows after rollback. This proves the schema fix and service pass-through work correctly end-to-end; only the shared test-infra fixture (not this plan's test or fix) is affected by the pre-existing bug.
  - Standalone acceptance criteria as literally specified in the plan still pass: `pytest api/tests/test_argument_oyez_field.py api/tests/test_case_item_argued_date_optional.py -v` run without `DATABASE_URL` loaded yields 3 passed, 2 skipped (both DB-gated tests correctly `skipif`-skip, matching the pre-existing sibling test's behavior in the same file).
  - This is flagged in `coverage` (D2) as `human_judgment: true` with an `unknown` verification status rather than silently marked `pass`, so `verify-work` surfaces it rather than auto-passing a test that has never actually executed its assertions in this environment.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 29-VERIFICATION.md gap #13 (29-REVIEW.md CR-01) is closed: both "missing" items (schema change, regression test) are satisfied, plus the additional CaseItem duplicate-pattern fix.
- Follow-up flagged (explicitly out of scope for this plan, per its `<objective>`): `import_convokit.py`'s `_import_conversation` creates its `PipelineRun` with `step="ingest"` (line 335), while `api/services/arguments.py`'s `get_argument_with_utterances()` filters for `PipelineRun.step == "parse"` (line 87) — meaning a corpus-imported argument's `GET /arguments/{id}/utterances` response will return `utterances: []` regardless of this plan's fix. This is a separate, previously-undiscovered defect from a different root cause and does not block this plan's specific truth (200 status + `argued_date: null`, not 500). Needs a follow-up gap/backlog item.
- Also flagged: the pre-existing FastAPI test lifespan/session-factory failure (project memory item, ~57 tests affected) blocks this plan's one DB-gated test from actually executing its assertions in a `DATABASE_URL`-configured run — logic independently verified correct via a bypass script, but the test itself will `ERROR` (not pass/fail cleanly) until that pre-existing test-infra bug is fixed. Not caused by, and out of scope for, this plan.

---
*Phase: 29-historical-corpus-import*
*Completed: 2026-07-10*

## Self-Check: PASSED

All created/modified files confirmed present on disk; all three commit hashes (49fde2c7, d47dc0a8, 5e21ab56) confirmed in git log.
