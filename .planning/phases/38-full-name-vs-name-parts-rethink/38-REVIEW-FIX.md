---
phase: 38-full-name-vs-name-parts-rethink
fixed_at: 2026-07-27T17:16:08Z
review_path: .planning/phases/38-full-name-vs-name-parts-rethink/38-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 38: Code Review Fix Report

**Fixed at:** 2026-07-27T17:16:08Z
**Source review:** .planning/phases/38-full-name-vs-name-parts-rethink/38-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (CR-01, WR-01, WR-02, WR-03 — IN-01/IN-02 out of scope per fix pass instructions)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: Migration 0022's round-trip abort gate compares against the wrong string, aborting the entire migration on legacy rows with leading/trailing whitespace

**Files modified:** `alembic/versions/0022_person_name_authority.py`, `api/tests/fixtures/person_name_cases.json`
**Commit:** `46e1c29f`
**Applied fix:** The migration now computes `stripped_full_name = pre_full_name.strip()` immediately after the blank/NULL guard, and the round-trip abort check now compares `recomputed != stripped_full_name` instead of `recomputed != pre_full_name`. This matches `split_legacy_full_name`'s own round-trip definition (it bases `auto_apply` on `candidate_full_name == stripped`), so a legacy row such as `"  Clarence Thomas  "` is now correctly auto-applied instead of aborting the whole migration. The `WHERE ... AND full_name = :expected_full_name` optimistic-concurrency guard is untouched and still compares against the raw, un-stripped `pre_full_name` (correct — that's the actual on-disk value), and `full_name` itself is still never rewritten.

Added a regression fixture (`high_confidence_leading_trailing_whitespace`, `full_name: "  Clarence Thomas  "`, `expected_auto_apply: true`) to the shared `legacy_split_cases` fixture array in `person_name_cases.json`. This fixture is consumed by both `api/tests/test_person_names.py::test_legacy_split_cases` (domain-function parity) and `api/tests/test_migration_0022_person_name_authority.py::test_upgrade_backfills_confident_rows_and_flags_ambiguous_rows` (full migration integration, including the byte-for-byte `full_name` preservation assertion), so the fix is exercised at both layers without any test-file code changes being necessary.

Verified: ran `api/tests/test_person_names.py` (54 tests, all passing, including the new fixture case) in an ephemeral venv (no DB required for this file). The DB-backed migration integration test (`test_migration_0022_person_name_authority.py`) requires `TEST_DATABASE_URL` pointed at a dedicated `scotus_test` database, which was not provisioned for this fix pass (no reachable dev/test database in this sandbox) — this test is skipped without that variable set, consistent with its existing skip-guard behavior, and was not force-run against an ephemeral throwaway Postgres instance to avoid provisioning DDL infrastructure beyond the scope of this fix pass. The new fixture case was manually verified against `split_legacy_full_name`/`format_full_name` directly (confirmed `auto_apply=True`, `recomputed == stripped`) before being added.

### WR-01: `create_person_for_job`'s `PersonResponse.role_name` field has no backing attribute on `Person`, risking an unhandled `AttributeError` at response-serialization time

**Files modified:** `api/services/admin_jobs.py`
**Commit:** `8fb3b163`
**Applied fix:** Combined with WR-03 (same root cause, same function, same fix). See WR-03 below for the full description — both findings are resolved by the same edit.

### WR-02: Dead `?incomplete=1` query param link on the pipeline job detail page

**Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte`
**Commit:** `bb0dd633`
**Applied fix:** Changed the "Review people →" link from `/admin/people?incomplete=1` (a param the `+page.server.ts` load function never reads and that `list_people` has no matching filter for — silently lands on the unfiltered Bench tab) to `/admin/people?tab=bench&missing=name%20review`. This wires the CTA to the exact working "Name review" pill filter (`Person.name_needs_review.is_(True)`) that Phase 38 itself introduced (D-12/D-13) — the same mechanism the People directory's own "Name review" pill uses (`api/services/admin_people.py`'s `missing_filters["name review"]`), and the same `&`-in-href-literal pattern already used elsewhere in this codebase (`app/src/routes/admin/+page.svelte:165`, `href="/admin/people?tab=bench&tenure_gaps=1"`). This is a more precise fix than merely dropping the query string, since it lands the operator directly on the exact "needs review" view the CTA text promises, using a filter that is confirmed to exist and that applies "for either tab" per the service's own docstring.

### WR-03: `create_person_for_job` may also be missing `role_name` when `role_id` is set via `role_name` lookup

**Files modified:** `api/services/admin_jobs.py`
**Commit:** `8fb3b163`
**Applied fix:** In `create_person_for_job`, added a `role_name_value: Optional[str]` tracked alongside `role_id` resolution:
- When `body.role_name` is supplied and a `Role` is found-or-created, `role_name_value` is set to `role.name` (previously this branch resolved `role_id` but never captured the name).
- New `elif role_id is not None` branch: when `body.role_id` is supplied directly (no `role_name` lookup path), the `Role` row is fetched by id and its `name` captured into `role_name_value`.
- Before `return person`, `person.__dict__["role_name"] = role_name_value` is now always set explicitly (never left as an unset attribute), matching the exact same injection idiom already used elsewhere in this same file for `parse_stats`/`is_archived`/`source` (lines 94, 166, 225, 237, 282, 285) to avoid `PersonResponse`'s `from_attributes=True` serialization raising `AttributeError` for a declared field with no corresponding ORM attribute.

Added `from typing import Optional` to the file's import block (was not previously imported; needed for the new `role_name_value: Optional[str] = None` annotation).

This single edit resolves both WR-01 (the field is now always populated, eliminating the `AttributeError` risk regardless of whether the described Pydantic behavior is triggered in this FastAPI/Pydantic version) and WR-03 (the resolved Role's actual name is now correctly surfaced instead of silently defaulting to `None`).

Verified: `python3 -c "import ast; ast.parse(...)"` syntax check passed. Reviewed `api/tests/test_admin_jobs_phase25.py`'s existing `create_person_for_job` call sites (`test_create_person_for_job_bench_sets_is_justice_and_participant_side`, `test_create_person_for_job_advocate_sets_is_justice_false`) — none pass `role_id`/`role_name` on `body`, so `role_name_value` stays `None` in those paths and no existing assertion is affected. These tests are DB-backed (`@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")`) and were not run in this pass since no dev/test database was provisioned for this fix pass.

## Skipped Issues

None — all in-scope findings (CR-01, WR-01, WR-02, WR-03) were fixed. IN-01 and IN-02 were explicitly out of scope for this fix pass per the fix instructions (info-severity, `fix_scope: critical_warning`) and were left untouched.

---

_Fixed: 2026-07-27T17:16:08Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
