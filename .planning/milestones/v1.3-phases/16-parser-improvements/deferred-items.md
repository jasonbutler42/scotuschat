# Deferred Items — Phase 16

## Pre-existing issue (out of scope)

**File:** `pipeline/tests/test_parse.py::test_run_id_strategy`
**Discovered during:** Task 2 (16-01)
**Issue:** Test creates `argparse.Namespace(run_id=..., dry_run=False)` without setting `job_id`,
but `_run_parse_inner` accesses `args.job_id` unconditionally. Causes `AttributeError` on test run.
**Status:** Pre-existing — failing before Phase 16 changes. Not caused by 16-01 edits.
**Resolution:** Fix in a separate task: either set `job_id=None` in the test Namespace, or
add a `getattr(args, 'job_id', None)` guard in `_run_parse_inner` / `run_parse`.
