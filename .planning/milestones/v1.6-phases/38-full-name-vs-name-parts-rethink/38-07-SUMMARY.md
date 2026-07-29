---
phase: 38-full-name-vs-name-parts-rethink
plan: 07
subsystem: api
tags: [fastapi, security, path-traversal, docket, validation]

requires:
  - phase: 38-full-name-vs-name-parts-rethink
    provides: "api/domain/person_names.py structural precedent (pure domain module, code-carrying error class)"
provides:
  - "api/domain/docket_values.py: canonical DOCKET_VALUE_PATTERN/DOCKET_VALUE_MAX_LENGTH/DocketValueError/normalize_docket_value contract"
  - "Shared Python/TypeScript accept/reject fixture (docket_value_cases.json) for Plan 38-09's TypeScript mirror"
  - "422 rejection of path-hazard/over-length docket values at the create_job boundary, closing G-38-6"
affects: [38-08-pipeline-side-hardening, 38-09-operator-facing-feedback]

tech-stack:
  added: []
  patterns:
    - "Pure, dependency-light api/domain module with a code-carrying error class (mirrors api/domain/person_names.py's PersonNameError.code pattern)"
    - "Two-layer defense at a route boundary (route-level guard + pipeline-side guard), mirroring the existing _validate_pdf_url (route) + _validate_url (pipeline) SSRF pair"

key-files:
  created:
    - api/domain/docket_values.py
    - api/tests/fixtures/docket_value_cases.json
    - api/tests/test_docket_values.py
  modified:
    - api/routers/admin.py
    - api/tests/test_docket_arg_safety.py

key-decisions:
  - "Character allow-list (^[A-Za-z0-9][A-Za-z0-9_-]*$) plus a 64-char cap, not a strict SCOTUS docket-shape regex — a strict shape regex would reject real accepted shapes (bare numbers like '71', ConvoKit historical shapes like '1955-71', synthetic 'job-{id}' dockets, and pre-existing operator-created files like 'bananas-q1.pdf')"
  - "Check ordering is a hard determinism contract: blank check, then length check, then pattern check — this is why the 68-char UAT-reported quoted string resolves to length_exceeded rather than invalid_characters"
  - "The T-24-08 leading-hyphen argv guard stays in place unmodified and runs first; the new domain-rule check is additive, not a replacement, even though the domain rule independently subsumes the same input class"
  - "ArgumentUpdate.docket_number and MetadataUpdate.source_docket (post-ingest metadata edit paths) are intentionally NOT tightened — neither ever constructs a filesystem path, and tightening them would reject already-persisted historical-importer docket values"

requirements-completed: [PEOPLE-09]

coverage:
  - id: D1
    description: "api/domain/docket_values.py exports DOCKET_VALUE_PATTERN, DOCKET_VALUE_MAX_LENGTH, DocketValueError, normalize_docket_value with no FastAPI/SQLAlchemy imports"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_docket_values.py (32 tests, all pass)"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /api/admin/jobs rejects docket values with path separators, traversal segments, absolute/drive-letter prefixes, quotes, whitespace, NUL, or over-length input with 422, before any AdminJob row or ingest subprocess is created"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_docket_arg_safety.py (13 tests, all pass, including the verbatim UAT-reported string and the 6 pre-existing argv-guard tests unchanged)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Real docket shapes (22-915, 14-556, 71, 1955-71, 22O141, 23A994, job-1120, 14-556-TEST-SEED, bananas) continue to normalize unchanged"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_docket_values.py::test_valid_cases_normalize_as_expected (11 fixture cases)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-28
status: complete
---

# Phase 38 Plan 07: Canonical Docket-Value Rule + create_job Boundary Enforcement Summary

**Closed the authenticated-admin arbitrary-file-write primitive (G-38-6) by adding a single canonical `normalize_docket_value` allow-list/length-cap rule in `api/domain/docket_values.py` and wiring it into `_normalize_dockets` so a hostile or malformed docket value now gets a 422 before any `AdminJob` row or ingest subprocess exists.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-27T23:53:00Z
- **Completed:** 2026-07-28T00:13:00Z
- **Tasks:** 2
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments

- New `api/domain/docket_values.py`: a pure domain module (no FastAPI/SQLAlchemy imports) exporting `DOCKET_VALUE_MAX_LENGTH` (64), `DOCKET_VALUE_PATTERN` (`^[A-Za-z0-9][A-Za-z0-9_-]*$` as a plain string literal for the future TypeScript mirror), `DOCKET_VALUE_ECHO_LIMIT` (32), `DocketValueError` (code-carrying, mirrors `PersonNameError`), and `normalize_docket_value()` enforcing blank-check → length-check → pattern-check in that deterministic order
- Shared `api/tests/fixtures/docket_value_cases.json` covering every real docket shape (dash-numbered, bare number, historical corpus shapes, original-jurisdiction/application letter suffixes, synthetic `job-{id}`, seed-test dockets, underscore shapes, free-text placeholders) plus every path-hazard/quote/whitespace/NUL rejection case, including the verbatim 68-character UAT-reported string
- `api/tests/test_docket_values.py`: 32 tests driving every fixture case plus two constructed length-boundary tests derived directly from `DOCKET_VALUE_MAX_LENGTH` (never hand-counted), a fixture/module-agreement check (pattern and max_length), and bounded-echo enforcement tests
- Wired `normalize_docket_value` into `_normalize_dockets` in `api/routers/admin.py`: every stripped docket value now passes through the domain rule after the pre-existing T-24-08 leading-hyphen check, translating `DocketValueError` into a `422 HTTPException`
- Extended `api/tests/test_docket_arg_safety.py` with 7 new tests (double-quote, POSIX-absolute-path, Windows-drive-path, traversal, over-length, verbatim UAT string, well-formed multi-docket regression) plus a static wiring-proof test; all 6 pre-existing argv-guard tests kept unchanged and still pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Canonical docket-value rule + shared fixture + unit tests** - `b4c20657` (feat)
2. **Task 2: Enforce the rule at the create_job boundary in _normalize_dockets** - `106c2c6f` (feat)

## Files Created/Modified

- `api/domain/docket_values.py` - Canonical docket-value validation module (pure, no FastAPI/SQLAlchemy imports)
- `api/tests/fixtures/docket_value_cases.json` - Shared Python/TypeScript accept/reject fixture
- `api/tests/test_docket_values.py` - 32 unit tests driving the fixture plus constructed boundary/bounded-echo tests
- `api/routers/admin.py` - `_normalize_dockets` now calls `normalize_docket_value`, translating `DocketValueError` to a 422; docstring records both guards and the scope boundary excluding `ArgumentUpdate.docket_number`/`MetadataUpdate.source_docket`
- `api/tests/test_docket_arg_safety.py` - 7 new boundary tests plus a static wiring-proof test; 6 pre-existing tests unchanged

## Decisions Made

- Character allow-list plus length cap chosen over a strict SCOTUS docket-shape regex, because the rest of the system (ConvoKit importer, synthetic job dockets, existing `data/pdfs/` files) already accepts and stores shapes a strict regex would reject
- Check ordering (blank → length → pattern) is a hard determinism contract the fixture and the reported UAT case both depend on
- T-24-08's leading-hyphen argv guard is preserved literally unmodified and runs before the new domain-rule check, even though the domain rule independently subsumes the same class of value
- `ArgumentUpdate.docket_number`/`MetadataUpdate.source_docket` intentionally left untouched — out of scope because they never construct a filesystem path

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 38-08 (pipeline-side independent hardening of `pipeline/commands/ingest.py`'s filename construction) can now build on `api/domain/docket_values.py` as the shared canonical rule, or implement its own defense-in-depth layer per the two-layer `_validate_pdf_url`/`_validate_url` pattern referenced in this plan's docstrings.
- Plan 38-09 (operator-facing feedback / TypeScript mirror) has `DOCKET_VALUE_PATTERN` as a byte-identical string literal and `docket_value_cases.json` ready to consume for parity testing.
- No blockers.

---
*Phase: 38-full-name-vs-name-parts-rethink*
*Completed: 2026-07-28*

## Self-Check: PASSED

All 6 created/modified files found on disk; all 3 task/summary commit hashes (`b4c20657`, `106c2c6f`, `7d8ac543`) found in git log.
