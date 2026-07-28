---
phase: 38-full-name-vs-name-parts-rethink
plan: 08
subsystem: pipeline
tags: [security, path-traversal, docket, ingest, pathlib]

requires:
  - phase: 38-full-name-vs-name-parts-rethink
    provides: "api/domain/docket_values.py: canonical DOCKET_VALUE_PATTERN/DOCKET_VALUE_MAX_LENGTH/DocketValueError/normalize_docket_value contract (Plan 38-07)"
provides:
  - "pipeline/commands/ingest.py::_validate_docket_value(): second, independent enforcement point for the G-38-6 docket-value rule, covering the direct-CLI path that bypasses FastAPI entirely"
  - "Resolved-path containment assertion on pdf_path, defense-in-depth even if the character rule is ever bypassed"
affects: [38-09-operator-facing-feedback]

tech-stack:
  added: []
  patterns:
    - "Two-layer defense-in-depth guard: delegate to the shared canonical rule (normalize_docket_value) THEN independently re-assert the structural invariant (no separator, no traversal segment, single non-absolute PurePath component) so the local check stays meaningful even if the shared rule is ever weakened"
    - "Resolved-path containment assertion (resolve both dir and joined path, compare parent) as a second, unconditional backstop after any docket-derived filename join — placed before any read/write branch"

key-files:
  created: []
  modified:
    - pipeline/commands/ingest.py
    - pipeline/tests/test_ingest.py

key-decisions:
  - "Used pathlib.PurePath (not the module's Path, which existing DB-dependent tests patch to a data/pdfs-specific mock) for the structural is_absolute()/parts check inside _validate_docket_value — keeps the guard's own I/O-free path parsing decoupled from the mocked Path used for file writes"
  - "Guard runs on every docket in all_dockets (primary and consolidated), including the synthetic job-{id} docket generated when the operator supplies none — no special-case exemption, since the synthetic value already conforms and skipping it would be an unjustified carve-out in the guard"
  - "Raises plain ValueError, not a new exception type, so run_ingest's existing except-handler continues to record AdminJobStatus.FAILED with a readable error_message"
  - "Fixed the pre-existing _make_mock_path test helper to mock .resolve() on both the mocked pdf_dir and the joined pdf_path — required so the new containment assertion doesn't break the 3 existing DB-dependent tests that patch Path module-wide"

requirements-completed: [PEOPLE-09]

coverage:
  - id: D1
    description: "pipeline/commands/ingest.py validates every operator-supplied docket value (primary and consolidated) before it reaches pdf_filename or case_slug construction, raising ValueError on any path separator, traversal segment, absolute path, or over-length value"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_ingest.py::test_docket_guard_rejects_path_hazards (8 parametrized cases, all pass)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Resolved-path containment assertion ensures pdf_path's resolved parent always equals the resolved data/pdfs directory, placed before any read/write branch (existing-file skip, local-file copy, Spaces download, HTTP download)"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_ingest.py::test_docket_containment_rejects_traversal_join, test_docket_containment_rejects_absolute_join"
        status: pass
    human_judgment: false
  - id: D3
    description: "Real docket shapes (22-915, 14-556, 1955-71, 22O141, job-1120, bananas) continue to pass the guard unchanged; all 58 pre-existing data/pdfs filenames verified to satisfy the guard with no rename required"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_ingest.py::test_docket_guard_accepts_real_shapes (6 cases, all pass)"
        status: pass
      - kind: other
        ref: "Manual scan of all 58 files in data/pdfs against _validate_docket_value — 0 failures"
        status: pass
    human_judgment: false
  - id: D4
    description: "Static asserts prove the guard call and containment assertion stay wired into _run_ingest_inner's executed code path, failing loudly if a future refactor removes either"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_ingest.py::test_docket_guard_invoked_inside_run_ingest_inner, test_containment_assertion_present_inside_run_ingest_inner"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-07-28
status: complete
---

# Phase 38 Plan 08: Pipeline-Side Docket Path Guard + Containment Assertion Summary

**Second, independent layer of the G-38-6 fix: `pipeline/commands/ingest.py` now validates every docket-derived filename and slug component itself, plus asserts the resolved PDF write path stays inside `data/pdfs`, closing the direct-CLI bypass of the Plan 38-07 API-boundary check.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-28T00:04:00Z (approx)
- **Completed:** 2026-07-28T00:24:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- New `_validate_docket_value(docket, context)` helper in `pipeline/commands/ingest.py`: delegates to `api.domain.docket_values.normalize_docket_value` for the one shared canonical rule, then independently re-asserts the structural invariant (no `/` or `\`, no `..` segment, `PurePath(value)` is a single non-absolute component) — the part that stays meaningful even if the shared pattern is ever loosened or bypassed
- Guard wired into Step 3 (before `pdf_filename` is built from `primary_docket`) and Step 5 (before `case_slug` is built from every docket in `all_dockets`, both primary and consolidated branches) — closes the same path-hazard class as Plan 38-07's API boundary but for the direct CLI invocation path that bypasses FastAPI entirely
- Resolved-path containment assertion added immediately after `pdf_path = pdf_dir / pdf_filename`: resolves both `pdf_dir` and `pdf_path` and raises `ValueError` when `pdf_path`'s resolved parent is not the resolved `pdf_dir`, placed before `pdf_path.exists()` so no download/copy branch can escape `data/pdfs` even if the character rule were bypassed
- 18 new no-DB unit tests in `pipeline/tests/test_ingest.py`: 8 parametrized path-hazard rejections (POSIX absolute, Windows drive, traversal, bare `..`, forward slash, backslash, double quote, over-`DOCKET_VALUE_MAX_LENGTH`), 6 no-regression passes for real docket shapes plus the synthetic `job-{id}` fallback, 2 filesystem-read-only containment tests replicating the module's join, and 2 `inspect.getsource(_run_ingest_inner)` static wiring proofs
- All 3 pre-existing DB-dependent ingest tests (`test_ingest_creates_pipeline_run`, `test_consolidated_dockets`, `test_ingest_idempotent`) kept passing by fixing their shared `_make_mock_path` test helper to also mock `.resolve()` on both the mocked `pdf_dir` and the joined `pdf_path`
- Manually verified all 58 existing filenames in `data/pdfs/` satisfy the guard unchanged — no rename or re-ingest required

## Task Commits

Each task was committed atomically:

1. **Task 1: Guard docket-derived path and slug construction, and assert PDF write containment** - `6d2e911f` (feat)
2. **Task 2: No-DB unit tests for the pipeline-side guard and containment assertion** - `d63e867c` (test)

## Files Created/Modified

- `pipeline/commands/ingest.py` - Added `_validate_docket_value()` (second enforcement point for G-38-6), wired it into Step 3 (`primary_docket` before `pdf_filename`) and Step 5 (every docket in `all_dockets` before `case_slug`), and added a resolved-path containment assertion after `pdf_path` construction, before any read/write branch
- `pipeline/tests/test_ingest.py` - Added 18 no-DB unit tests covering the guard and containment assertion; fixed the pre-existing `_make_mock_path` helper's `.resolve()` mocking so the 3 existing DB-dependent tests keep passing under the new containment check

## Decisions Made

- Used `pathlib.PurePath` (not the module-level `Path`, which the 3 existing DB-dependent tests patch to a `data/pdfs`-specific mock) for `_validate_docket_value`'s structural `is_absolute()`/`parts` check — decouples the guard's I/O-free path parsing from the mocked `Path` used for the actual file write, avoiding a collision where the mock's fixed return value would make every `Path(docket)` call resolve to the same mocked directory regardless of `docket`
- The guard runs on every docket in `all_dockets` uniformly, including the synthetic `job-{id}` docket generated when the operator supplies none — no special-case exemption; it already conforms, so exempting it would be an unjustified carve-out
- Raises plain `ValueError` (not a new exception type) so `run_ingest`'s existing except-handler continues to record `AdminJobStatus.FAILED` with a readable `error_message`, matching the plan's explicit instruction not to introduce a bespoke exception type
- Did not sanitize or rewrite hazardous docket values into a "safe" filename — silently renaming would desynchronize the on-disk filename from `Argument.source_docket` and break the documented PDF immutability/idempotency contract; a hazardous value fails loudly instead

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Fixed pre-existing test mock incompatibility with the new containment assertion**
- **Found during:** Task 1 verification (`pytest pipeline/tests/test_ingest.py`)
- **Issue:** The 3 pre-existing DB-dependent tests (`test_ingest_creates_pipeline_run`, `test_consolidated_dockets`, `test_ingest_idempotent`) patch `pipeline.commands.ingest.Path` module-wide via their shared `_make_mock_path` helper. The new containment assertion calls `.resolve()` on both `pdf_dir` and `pdf_path`; against the unmodified mock, both calls returned unrelated auto-generated `MagicMock` objects that could never compare equal, making every one of those 3 tests fail with the new "not contained within" `ValueError` regardless of correct production behavior.
- **Fix:** Updated `_make_mock_path` in `pipeline/tests/test_ingest.py` to explicitly mock `.resolve()` on both the mocked `pdf_dir` (returns a real resolved path under `tmp_path`) and the mocked `pdf_path` (returns that same resolved directory joined with a fixed filename), so `resolved_pdf_path.parent == resolved_pdf_dir` holds under the mock exactly as it does in real filesystem behavior.
- **Files modified:** `pipeline/tests/test_ingest.py` (helper function only — no existing test function's body, assertions, or ordering were touched)
- **Verification:** All 28 tests in `pipeline/tests/test_ingest.py` pass, including the 3 previously-passing DB-dependent tests unchanged in behavior/assertions.
- **Committed in:** `d63e867c` (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking issue)
**Impact on plan:** Necessary to keep pre-existing tests green after adding the new containment assertion the plan required; no scope creep — only the shared mock helper's `.resolve()` behavior was extended, no existing test function was modified or reordered.

## Issues Encountered

None beyond the mock-incompatibility deviation documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 38-09 (operator-facing feedback / TypeScript mirror) can proceed — the pipeline-side second enforcement layer is now in place alongside the Plan 38-07 API boundary, matching the codebase's established two-layer SSRF pattern.
- `data/pdfs/` requires no changes — all 58 existing filenames verified to satisfy the new guard.
- No blockers.

---
*Phase: 38-full-name-vs-name-parts-rethink*
*Completed: 2026-07-28*

## Self-Check: PASSED

All 2 created/modified files found on disk (`pipeline/commands/ingest.py`, `pipeline/tests/test_ingest.py`); both task commit hashes (`6d2e911f`, `d63e867c`) found in git log.
