# Phase 52 — Deferred Items

## Out-of-scope full-suite failure observed during 52-04 execution

**Test:** `api/tests/test_public_arguments_listing.py::test_term_detail_consolidated_docket_contributes_one_row`

**When observed:** 2026-09-25, during 52-04's plan-level `pytest -q` verification
(1 failed, 1393 passed, 5 xfailed).

**Evidence it's pre-existing and unrelated to 52-04's changes:**
- The file is `api/tests/test_public_arguments_listing.py` — public arguments listing,
  no relation to `admin_dev.py`, `import_justices_csv.py`, or justice identity.
- The test passes in isolation (`pytest api/tests/test_public_arguments_listing.py::test_term_detail_consolidated_docket_contributes_one_row` → 1 passed).
- It only fails as part of a full-suite run, with a symptom (`[29185, 29013] == [29185]`
  — one extra argument id in the term's listing) consistent with the test's own random
  year selection (`year = 1920 + (uuid.uuid4().int % 100)`) colliding with data left
  behind by another test's argument for the same year, in the shared TEST_DATABASE_URL
  database.

**Action:** Not fixed — out of scope per the Scope Boundary rule (CLAUDE.md Defect
Policy governs *what* gets fixed silently; the executor's own scope boundary governs
*where*: "do not auto-fix pre-existing issues unrelated to current task"). Logged here
for the operator/a future phase to investigate the year-collision test-isolation gap.
