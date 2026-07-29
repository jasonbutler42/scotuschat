---
phase: 38-full-name-vs-name-parts-rethink
plan: "04"
subsystem: pipeline
tags: [name-authority, provenance, import-convokit, import-justices-csv, seed-aliases, pytest]

# Dependency graph
requires:
  - phase: 38-full-name-vs-name-parts-rethink (Plan 01)
    provides: "api/domain/person_names.py: prepare_person_name, prepare_name_provenance, split_legacy_full_name, format_full_name"
  - phase: 38-full-name-vs-name-parts-rethink (Plan 02)
    provides: "api/models/models.py: Person.name_needs_review, Person.name_extraction_metadata; alembic 0022 envelope shape"
provides:
  - "pipeline/commands/import_justices_csv.py: shared-format justice import with per-row provenance and blank-only prefill"
  - "pipeline/commands/import_convokit.py: conservative name-part extraction + persistent provenance in _resolve_person"
  - "pipeline/commands/seed_aliases.py: structured (first, middle, last, suffix) seed fixtures with no independent formatter"
affects: [38-05, 38-06, admin_people, pipeline-import]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Every pipeline person-writer now derives full_name exclusively through api.domain.person_names.prepare_person_name/format_full_name — no batch writer constructs an independently authoritative full_name string"
    - "name_extraction_metadata envelope shape is uniform across migration 0022, import_justices_csv.py, and import_convokit.py: {source, raw, confidence, reason, auto_applied}, with a per-command source tag (legacy_migration_0022 / import_justices_csv / import_convokit)"
    - "Blank-only prefill of structured name parts (D-16/T-38-11): a row that already carries a saved part is never partially clobbered; only a row missing structured data gets a confident interpretation applied, and only for the fields still blank"

key-files:
  created: []
  modified:
    - pipeline/commands/import_justices_csv.py
    - pipeline/tests/test_import_justices_csv.py
    - pipeline/commands/import_convokit.py
    - pipeline/tests/test_import_convokit_core.py
    - pipeline/commands/seed_aliases.py
    - pipeline/tests/test_seed_aliases.py

key-decisions:
  - "import_justices_csv.py: reconstruct_full_name() keeps its exact name/signature and MANUAL_NAME_OVERRIDES escape hatch but its body now delegates to prepare_person_name/format_full_name (D-03/D-05) instead of an independent local string join — preserves the existing test contract while removing the duplicate formatter"
  - "CSV columns are treated as authoritative per-column ground truth, not an inferred split — confidence is always High and auto_applied is always True in the provenance envelope this command writes, distinct from import_convokit.py's genuinely uncertain Low/Medium splits"
  - "import_justices_csv.py blank-only prefill is per-field (first_name/middle_name/last_name/name_suffix checked independently), not whole-row, because CSV columns are independent ground truth per part — an operator-added middle initial does not block filling a still-blank last_name from the same CSV row"
  - "import_convokit.py blank-only prefill mirrors migration 0022's own guard exactly: a row is only eligible for structured-part application when it currently carries NO part at all (first/middle/last/suffix all None); a row with even one saved part is left completely untouched (parts), though name_extraction_metadata is still refreshed every run"
  - "import_convokit.py's provenance raw/confidence is always derived from the Person row's OWN stored full_name (not the corpus label passed into that call), so a row matched by oyez_speaker_id whose full_name intentionally differs from the corpus's label gets an accurate envelope describing what is actually saved, not a mismatched external string"
  - "A successful confident CSV/split application also clears name_needs_review (D-12) — data now backed by authoritative or high-confidence structured parts is no longer flagged for the People directory's Name review filter"
  - "seed_aliases.py's _JUSTICES tuples are exactly the 13 (first, middle, last, suffix) values pipeline/tests/test_import_justices_csv.py's _SEEDED_JUSTICE_CASES fixture corpus already establishes, in the same order — a new no-DB-required regression in test_seed_aliases.py zips both lists and asserts derived full_name equality, tying the two import paths to one shared corpus"

requirements-completed: []  # PEOPLE-09 spans all 6 plans in this phase; not marked complete until the phase's final plan (established precedent from Plans 01/02/03)

coverage:
  - id: D1
    description: "Justice CSV import derives full_name through the shared prepare_person_name/format_full_name helper (not an independent reconstruction), reproducing all 13 existing seed_aliases.py literals byte-for-byte including suffix comma behavior, while retaining MANUAL_NAME_OVERRIDES as an explicit escape hatch"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_justices_csv.py::test_reconstruct_full_name_matches_seed_aliases_literal (13 parametrized cases) + test_reconstruct_full_name_all_13_seeded_justices_reproduced"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every CSV-processed row (new or matched-existing) writes a name_extraction_metadata provenance envelope {source, raw, confidence, reason, auto_applied} — always High confidence / auto_applied True since CSV columns are structured ground truth — and clears name_needs_review"
    requirement: "PEOPLE-09"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py::test_new_person_gets_structured_parts_and_provenance, test_rerun_refreshes_provenance_metadata_on_second_run (real scotus_test DB)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A matched existing justice row never has an operator-edited structured part overwritten by a rerun; any part still blank on that row is filled from the authoritative CSV row (per-field blank-only prefill)"
    requirement: "PEOPLE-09"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py::test_rerun_preserves_operator_edited_parts_blank_only_prefill (real scotus_test DB)"
        status: pass
    human_judgment: false
  - id: D4
    description: "ConvoKit import resolves a brand-new speaker's full_name through the shared conservative split_legacy_full_name splitter: an unambiguous two-token name gets High-confidence structured parts applied and is not flagged for review; a structurally ambiguous name (single token) records its Low-confidence interpretation as provenance without guessing structured parts, and IS flagged name_needs_review"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_brand_new_speaker_confident_split_gets_parts_and_high_provenance, test_brand_new_speaker_ambiguous_name_gets_provenance_without_parts (real scotus_test DB)"
        status: pass
    human_judgment: false
  - id: D5
    description: "A Person row an operator has already given structured parts is matched (by full_name or by oyez_speaker_id) and reimported without those parts ever being overwritten — only name_extraction_metadata refreshes; a row with no saved parts at all gets a confident split's parts prefilled on the same reimport path; Oyez-ID-first resolution, exact-name fallback, and full_name-never-touched-on-match all remain unchanged from pre-Phase-38 behavior"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py::test_matched_person_with_operator_edited_parts_never_overwritten, test_matched_person_with_blank_parts_gets_confident_prefill_on_reimport, test_oyez_id_matched_person_metadata_refreshes_full_name_never_touched, test_existing_oyez_speaker_id_match_reuses_person_no_new_row, test_full_name_only_match_backfills_oyez_speaker_id (real scotus_test DB)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Alias seed fixtures author explicit structured (first, middle, last, suffix) parts instead of a hand-typed full_name literal per justice; full_name is derived at seed time through the shared prepare_person_name helper; every alias label string and the existing select-before-insert idempotency for roles/people/aliases are preserved unchanged"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_seed_aliases.py::test_seed_justices_have_no_independent_formatter (zips seed_aliases._JUSTICES against test_import_justices_csv._SEEDED_JUSTICE_CASES, 13 entries)"
        status: pass
      - kind: manual_procedural
        ref: "Ad hoc two-run invocation of run_seed_aliases against the real scotus_test DB during plan execution — confirmed 13 people created with correct structured parts on run 1, then 0 new people/aliases on run 2 (idempotent)"
        status: pass
    human_judgment: false

duration: ~50min
completed: 2026-07-27
status: complete
---

# Phase 38 Plan 04: Pipeline/Import Name Authority Adoption Summary

**All three batch person-writers (justice CSV import, ConvoKit corpus import, and alias seeds) now derive `full_name` exclusively through the shared `api.domain.person_names` contract, write a uniform `name_extraction_metadata` provenance envelope, and apply blank-only prefill so no import path can silently overwrite an operator-authored or previously-confident name part.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-07-27
- **Tasks:** 3
- **Files modified:** 6 (0 created, 6 modified)

## Accomplishments

- `pipeline/commands/import_justices_csv.py`: `reconstruct_full_name()` now delegates to `prepare_person_name`/`format_full_name` (D-03/D-05) instead of an independent local join, while keeping its exact name/signature and the `MANUAL_NAME_OVERRIDES` escape hatch — every one of the 13 existing `seed_aliases.py` literals still reconstructs byte-for-byte. Every processed row (new or matched-existing) writes a `name_extraction_metadata` envelope (`source="import_justices_csv"`, `confidence="High"`, `auto_applied=True`) and gets per-field blank-only prefill: an operator-edited part is never overwritten, but any still-blank part is filled from the CSV row; a successful pass also clears `name_needs_review`.
- `pipeline/commands/import_convokit.py`: a new `_apply_extracted_name_provenance` helper runs inside `_resolve_person` for every resolution path (brand-new, oyez_speaker_id-matched, full_name-only-matched), reusing the same pure `split_legacy_full_name` splitter migration 0022 already uses. Structured parts are only ever written when a row currently has **no** saved part at all, and only for a High-confidence, round-trip-exact split; an ambiguous/uncertain interpretation is still recorded in the provenance envelope (Low/Medium) so an operator can see what the extractor thought it saw, and the row is flagged `name_needs_review`. `name_extraction_metadata` is unconditionally refreshed on every resolution, matched or new. Oyez-ID-first resolution, the exact-name fallback, and "`full_name` is never rewritten on a matched path" are all unchanged.
- `pipeline/commands/seed_aliases.py`: `_JUSTICES` now authors explicit `(first, middle, last, suffix)` tuples — the exact same 13 values `pipeline/tests/test_import_justices_csv.py`'s `_SEEDED_JUSTICE_CASES` fixture corpus already establishes — and derives `full_name` at seed time through the same shared helper. Every alias label string and the existing select-before-insert idempotency for roles/people/aliases are unchanged.
- Added 13 new regression tests across the three test files (3 for justice CSV provenance/blank-prefill/refresh, 5 for ConvoKit confident/ambiguous extraction and operator-edit-preservation, 1 no-DB-required corpus-tie-in for seeds — plus supporting fixture data), all following an explicit RED (revert command file, confirm new tests fail) → GREEN (restore implementation, confirm pass) cycle before committing each task.
- Full regression run: `pipeline/tests/` (161 passed, 5 pre-existing xfailed) and `api/tests/` (403 passed) both green with the ephemeral `scotus_test` Postgres instance at Alembic head (`0022`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Route justice import through the shared contract** - `8273f639` (feat)
2. **Task 2: Add conservative ConvoKit name-part extraction** - `ab44b595` (feat)
3. **Task 3: Convert alias seeds to structured fixtures** - `d9404c2d` (feat)

_Note: each commit bundles the task's implementation change together with its own new/updated regression tests — RED/GREEN verification (via a temporary `git checkout -- <file>` revert, confirming the new assertions fail, then restoring the implementation) was performed locally before staging, per this task's `tdd="true"` requirement, but is not split into separate `test(...)`/`feat(...)` commits._

## Files Created/Modified

- `pipeline/commands/import_justices_csv.py` - shared-format full_name derivation, per-row provenance envelope, per-field blank-only prefill
- `pipeline/tests/test_import_justices_csv.py` - new-row provenance, operator-edit preservation, provenance-refresh-on-rerun tests
- `pipeline/commands/import_convokit.py` - `_apply_extracted_name_provenance` helper wired into every `_resolve_person` path
- `pipeline/tests/test_import_convokit_core.py` - confident/ambiguous split provenance, operator-edit preservation, blank-row confident prefill, oyez-ID-match metadata-refresh-without-touching-full_name tests
- `pipeline/commands/seed_aliases.py` - structured `(first, middle, last, suffix)` seed tuples, `full_name` derived via `prepare_person_name`
- `pipeline/tests/test_seed_aliases.py` - shared-fixture-corpus regression tying seed derivation to the CSV importer's own test data

## Decisions Made

- `reconstruct_full_name()` keeps its exact public signature/name (rather than being deleted) so the six existing byte-for-byte parity tests in `test_import_justices_csv.py` continue to pass unchanged, while its internal implementation is fully replaced with the shared helper — satisfies "replace local reconstruction" without an unnecessary breaking rename.
- CSV columns are always-High-confidence, `auto_applied=True` provenance (never Low/Medium) because they are structured, per-column ground truth, not an inferred split — this is intentionally different from `import_convokit.py`'s genuinely uncertain `split_legacy_full_name` output.
- `import_justices_csv.py`'s blank-only prefill is **per-field** (each of first/middle/last/suffix checked independently) because CSV columns are independent ground truth per part; `import_convokit.py`'s blank-only prefill is **whole-row** (mirrors migration 0022's "any existing part blocks the whole row" guard exactly) because a single derived split's parts are not independently trustworthy pieces of the same ground truth the way CSV columns are.
- `import_convokit.py`'s provenance `raw`/`confidence` is derived from the Person row's own currently-stored `full_name`, not the corpus label passed into that call — this matters specifically for the oyez_speaker_id-matched path, where the corpus's label for a given speaker id can legitimately differ from what's actually saved on that Person.
- A successful confident application (CSV or ConvoKit) also clears `name_needs_review` — consistent with `api/services/admin_people.py`'s existing "an authoritative edit clears the review flag" precedent (Plan 03), generalized here to "an authoritative/confident pipeline write clears it too."

## Deviations from Plan

None — plan executed as written. All three tasks' `<behavior>`/`<action>` requirements (shared derivation, per-row/per-part provenance envelopes, blank-only prefill preserving operator edits, byte-for-byte reproduction, stable IDs/idempotency, no independent formatters) were implemented directly per the plan; no unplanned bugs, missing critical functionality, or blocking issues were encountered.

## Issues Encountered

- **This Linux/WSL sandbox has no system-wide `pip`/`ensurepip`** (`ModuleNotFoundError: No module named 'pip'`), matching the environmental constraint Plans 01/02 already documented. Resolution: reused an already-provisioned scratch venv (`/tmp/.../scratchpad/venv38`) that already had `pytest`, `sqlalchemy`, `asyncpg`, `alembic`, and `pgserver` available (evidently left over from this same session's earlier 38-02/38-03 tooling setup), and reused the already-running, already-migrated (`alembic head = 0022`) ephemeral `scotus_test` Postgres instance at `/tmp/.../scratchpad/pgdata` (socket `/run/user/1000/python_PostgresServer/5d1d87a29b`) rather than provisioning a second redundant instance. No project dependency was added; no data or credentials from any real database were read, written, or exposed. This ephemeral instance is session-local scratch tooling, not part of the repository or any persisted environment.
- `api/tests/` initially showed 4 unrelated failures (`ConnectionRefusedError` on `127.0.0.1:5432`) when only `TEST_DATABASE_URL` was exported — traced to `api/tests/conftest.py` reading `DATABASE_URL` directly (not `TEST_DATABASE_URL`) for a few tests. Setting `DATABASE_URL` to the same ephemeral instance's URL resolved this; confirmed via isolated reruns that this was purely an environment-variable naming difference between `pipeline/tests/` and `api/tests/` conftest conventions, not a regression caused by this plan's changes.

## User Setup Required

None — no external service configuration required. The ephemeral PostgreSQL instance used to verify this plan's changes is session-local scratch tooling (not part of the repository or any persisted environment); a developer running these commands against their own `scotus_test` database (per `scripts/dev-start.ps1`) needs no additional setup beyond what Phase 38 (Plan 02's migration 0022) already establishes.

## Next Phase Readiness

- Every batch/seed person-writer in the codebase (API services from Plan 03, and now all three pipeline import/seed paths from this plan) derives `full_name` through the one shared `api.domain.person_names.prepare_person_name` contract — no remaining independently authoritative full_name formatter exists anywhere in the codebase.
- `name_extraction_metadata` and `name_needs_review` are now populated/maintained consistently by the legacy migration (Plan 02), the API/service layer (Plan 03), and every pipeline import path (this plan) — ready for Plan 05's People directory `Name review` filter and the shared extracted-value UI to surface this data without any format-shape surprises across sources.
- No blockers. All three focused import/seed test suites (`test_import_justices_csv.py`, `test_import_convokit_core.py` + `test_import_convokit_adminjob.py`, `test_seed_aliases.py`) pass, along with the full `pipeline/tests/` and `api/tests/` regression suites, confirming this plan's changes are additive and non-breaking.

---
*Phase: 38-full-name-vs-name-parts-rethink*
*Completed: 2026-07-27*

## Self-Check: PASSED

- FOUND: pipeline/commands/import_justices_csv.py
- FOUND: pipeline/tests/test_import_justices_csv.py
- FOUND: pipeline/commands/import_convokit.py
- FOUND: pipeline/tests/test_import_convokit_core.py
- FOUND: pipeline/commands/seed_aliases.py
- FOUND: pipeline/tests/test_seed_aliases.py
- FOUND commit: 8273f639 (Task 1)
- FOUND commit: ab44b595 (Task 2)
- FOUND commit: d9404c2d (Task 3)
