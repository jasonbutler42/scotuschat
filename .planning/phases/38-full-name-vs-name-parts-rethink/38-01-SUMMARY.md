---
phase: 38-full-name-vs-name-parts-rethink
plan: "01"
subsystem: api
tags: [domain-model, validation, name-parsing, pytest, pure-python]

# Dependency graph
requires: []
provides:
  - "api/domain/person_names.py: normalize_name_part, format_full_name, prepare_person_name"
  - "api/domain/person_names.py: prepare_name_provenance ({value, raw, confidence} envelope validation)"
  - "api/domain/person_names.py: split_legacy_full_name (conservative legacy Full Name splitter)"
  - "api/tests/fixtures/person_name_cases.json shared fixture data for Python/TypeScript parity"
affects: [38-02, 38-03, 38-04, 38-05, 38-06, admin_people, admin_jobs, pipeline-import, alembic-migration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dependency-light domain module (no FastAPI/SQLAlchemy/Alembic imports) importable from services, pipeline commands, tests, and Alembic revisions alike"
    - "PersonNameError carries a stable machine-readable `.code` attribute so callers/tests branch on codes, not message text"
    - "Fixture-first contract testing: shared JSON fixture drives both current pytest suite and a future TypeScript parity mirror"

key-files:
  created:
    - api/domain/__init__.py
    - api/domain/person_names.py
    - api/tests/fixtures/person_name_cases.json
    - api/tests/test_person_names.py
  modified: []

key-decisions:
  - "PersonNameError(code, message) gives every validation failure a stable machine-readable code (at_least_one_required, length_exceeded, full_name_length_exceeded, invalid_confidence, provenance_value_length_exceeded, provenance_raw_length_exceeded) rather than message-string matching"
  - "Confidence literals are canonical Title-case (High/Medium/Low) matching D-22's UI-facing wording exactly; prepare_name_provenance accepts case-insensitive input and normalizes to that canonical form"
  - "split_legacy_full_name distinguishes Medium (structurally plausible split that fails exact round-trip, e.g. irregular whitespace) from Low (structurally ambiguous shape: single-part, particle, >3 tokens, inverted punctuation order, or a suffix-like token without a leading comma) — auto_apply is true only for High"
  - "A suffix token is only ever split off when it follows a comma (the canonical D-05 shape); the same literal appearing without a comma (e.g. \"John Roberts Jr.\") is treated as an order/punctuation ambiguity, never guessed"
  - "Deferred split_legacy_full_name/SplitResult out of the Task 2 commit (it was a stub in the first draft) so every intermediate task commit leaves api/tests/test_person_names.py fully green rather than carrying a known-future-red across commits"

patterns-established:
  - "Fixture parts that need to test length-bound validation use a {\"repeat_char\": ..., \"length\": ...} spec resolved by the test helper, instead of embedding 150+ character literals in JSON"

requirements-completed: []  # PEOPLE-09 spans all 6 plans in this phase; not marked complete until the phase's final plan (established precedent: Phase 37/PEOPLE-08 was marked complete only at 37-05)

coverage:
  - id: D1
    description: "Canonical First Middle Last, Suffix formatter handles first-only/last-only names, omits blank Middle/Suffix cleanly, and preserves authored capitalization/punctuation (initials, hyphens, apostrophes, particles, compound values, suffix spelling)"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_person_names.py#test_format_cases (12 fixture cases)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Whitespace-only normalization (trim + collapse) with blank-to-null mapping, and deterministic column-bound validation errors instead of silent truncation for first/middle/last/suffix and the derived full_name compatibility value"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_person_names.py#test_normalization_cases (5 fixture cases)"
        status: pass
      - kind: unit
        ref: "api/tests/test_person_names.py#test_invalid_cases_are_deterministic_domain_errors (6 fixture cases)"
        status: pass
      - kind: unit
        ref: "api/tests/test_person_names.py#test_invalid_length_is_never_silently_truncated"
        status: pass
    human_judgment: false
  - id: D3
    description: "prepare_person_name enforces the first-or-last minimum-data invariant (D-09) as one shared derivation rule usable by every future write path"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_person_names.py#test_invalid_cases_are_deterministic_domain_errors[blank_first_and_last_rejected]"
        status: pass
    human_judgment: false
  - id: D4
    description: "prepare_name_provenance validates the {value, raw, confidence} extraction envelope: case-insensitive High/Medium/Low confidence normalized to canonical casing, bounded value/raw lengths, raw text preserved exactly apart from length, null value/raw permitted"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_person_names.py#test_provenance_confidence_normalizes_case_insensitively"
        status: pass
      - kind: unit
        ref: "api/tests/test_person_names.py#test_provenance_rejects_invalid_confidence_label"
        status: pass
      - kind: unit
        ref: "api/tests/test_person_names.py#test_provenance_rejects_oversized_value"
        status: pass
      - kind: unit
        ref: "api/tests/test_person_names.py#test_provenance_rejects_oversized_raw"
        status: pass
      - kind: unit
        ref: "api/tests/test_person_names.py#test_provenance_preserves_raw_text_exactly_apart_from_length"
        status: pass
    human_judgment: false
  - id: D5
    description: "split_legacy_full_name auto-applies only a High-confidence, round-trip-exact 2/3-token split with an optional comma-led recognized suffix, derived from real repository justice names; every ambiguous shape (single-part, particle, >3-token compound, inverted punctuation order, suffix-without-comma, whitespace round-trip mismatch) preserves the original and returns auto_apply=False with a reason"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_person_names.py#test_legacy_split_cases (11 fixture cases)"
        status: pass
      - kind: unit
        ref: "api/tests/test_person_names.py#test_legacy_split_is_idempotent"
        status: pass
      - kind: unit
        ref: "api/tests/test_person_names.py#test_legacy_split_auto_apply_only_true_for_high_confidence"
        status: pass
    human_judgment: false

duration: 17min
completed: 2026-07-22
status: complete
---

# Phase 38 Plan 01: Person Name Domain Contract Summary

**Pure Python domain module (api/domain/person_names.py) implementing canonical First Middle Last, Suffix formatting, whitespace-only normalization with column-bound validation, provenance envelope validation, and a conservative fixture-driven legacy Full Name splitter — zero new dependencies, zero app/database initialization.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-07-22T15:17:25Z
- **Completed:** 2026-07-22T15:34:18Z
- **Tasks:** 3
- **Files modified:** 4 (all created)

## Accomplishments
- Canonical formatter (`format_full_name`) and full write-path contract (`prepare_person_name`) covering first-only, last-only, suffix-with-comma, and authored-punctuation-preservation cases, backed by 12 fixture cases derived from real `pipeline/commands/seed_aliases.py` justice names
- Deterministic, code-carrying `PersonNameError` for every validation failure (minimum-data, column-bound, provenance) instead of silent truncation or bare `ValueError`
- `prepare_name_provenance` envelope validator for the `{value, raw, confidence}` extraction-provenance contract (D-18/D-22), with case-insensitive confidence input normalized to canonical `High`/`Medium`/`Low`
- `split_legacy_full_name`: a pure, idempotent, conservative splitter that auto-applies only exact-round-trip 2/3-token splits and explicitly flags every other shape (single-part, particle, compound, punctuation/order, near-miss whitespace) for human review rather than guessing

## Task Commits

Each task was committed atomically (TDD RED/GREEN across three tasks):

1. **Task 1: Lock canonical formatter and validation fixtures** - `86633ff9` (test) — shared JSON fixtures + failing test suite (RED: `ModuleNotFoundError` for the not-yet-created module)
2. **Task 2: Implement shared name preparation contract** - `4a37e024` (feat) — `normalize_name_part`/`format_full_name`/`prepare_person_name`/`prepare_name_provenance`; all 35 in-scope tests pass
3. **Task 3: Define conservative legacy split confidence** - `2ce07c54` (feat) — `split_legacy_full_name`/`SplitResult` plus 11 new fixture cases and idempotency tests; all 53 tests pass

**Plan metadata:** (final docs commit recorded below in state update)

## Files Created/Modified
- `api/domain/__init__.py` - empty package marker
- `api/domain/person_names.py` - normalize_name_part, format_full_name, prepare_person_name, PreparedPersonName, prepare_name_provenance, NameProvenance, split_legacy_full_name, SplitResult, PersonNameError
- `api/tests/fixtures/person_name_cases.json` - format_cases (12), normalization_cases (5), invalid_cases (6), legacy_split_cases (11), plus column-bound metadata for future TypeScript parity mirror
- `api/tests/test_person_names.py` - 53 tests covering all of the above

## Decisions Made
- `PersonNameError` carries a stable `.code` string (e.g. `length_exceeded`, `invalid_confidence`) so both this suite and future consumers (Pydantic schemas, services) can branch deterministically without parsing message text.
- Confidence bands are stored/returned as canonical Title-case (`High`/`Medium`/`Low`) matching D-22's exact UI wording; input to `prepare_name_provenance` is accepted case-insensitively for caller convenience.
- The splitter treats a near-miss round-trip failure (e.g. `"John  Roberts"` with irregular whitespace) as `Medium` confidence — distinct from the `Low` band used for structurally ambiguous shapes (particles, >3 tokens, inverted punctuation, suffix without a comma). This gives the future migration/UI a meaningful three-way signal rather than a binary confident/not-confident split.
- A suffix token (`Jr.`, `Sr.`, `II`, `III`, `IV`) is only ever recognized as a suffix when it follows a comma — the same literal appearing without a comma is flagged as an order/punctuation ambiguity rather than silently reinterpreted as a suffix, protecting against the "round-trips but semantically wrong" failure mode (e.g. `"John Roberts Jr."` would otherwise mis-split `Jr.` into the `last_name` slot).
- Deferred adding `split_legacy_full_name` to `api/domain/person_names.py` until Task 3 (Task 2's first draft included a `NotImplementedError` stub plus the Task-3-scoped tests already in the file from Task 1's fixture pass); removed both mid-Task-2 so the Task 2 commit's test run is 100% green rather than carrying known-future-failing tests forward. This is a self-correction of my own drafting, not a plan deviation — no rule-tracked auto-fix needed.

## Deviations from Plan

None - plan executed exactly as written. (See "Decisions Made" above for one internal drafting correction that kept intermediate commits green; it did not change scope, behavior, or test coverage relative to the plan.)

## Issues Encountered
- This Linux/WSL execution environment has no pre-existing Python virtual environment matching the project's Windows-oriented `.venv` (`Scripts/` layout, no `pytest` installed). Created a scratch venv (`python3.12 -m venv`) and installed the project's own already-declared `requirements-dev.txt` test dependencies (`pytest`, `pytest-asyncio`, `python-dotenv`, `python-dateutil`) to run the suite — no new project dependency was added to `requirements.txt`/`requirements-dev.txt`, and no database/app initialization was required (verified: `api/tests/conftest.py`'s DB-gated fixture no-ops when `DATABASE_URL` is unset).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `api/domain/person_names.py` is ready for 38-02 (schema/service adoption), 38-03+ (pipeline/import adoption), and the Alembic migration plan to import directly — it has zero FastAPI/SQLAlchemy dependencies so it is safe to call from a migration's `upgrade()`.
- The shared JSON fixture (`api/tests/fixtures/person_name_cases.json`) is ready to be mirrored by a future `app/src/lib/personNames.ts` parity test suite (not part of this plan).
- No blockers. `split_legacy_full_name`'s particle/suffix/token-count rules are intentionally conservative and scoped to the patterns proven against real repository justice names; any legacy row shape outside those patterns is safely preserved and flagged for review rather than guessed, per D-11/D-12.

---
*Phase: 38-full-name-vs-name-parts-rethink*
*Completed: 2026-07-22*

## Self-Check: PASSED

- FOUND: api/domain/person_names.py
- FOUND: api/tests/fixtures/person_name_cases.json
- FOUND: api/tests/test_person_names.py
- FOUND commit: 86633ff9 (Task 1)
- FOUND commit: 4a37e024 (Task 2)
- FOUND commit: 2ce07c54 (Task 3)
