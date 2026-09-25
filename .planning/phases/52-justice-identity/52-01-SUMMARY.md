---
phase: 52-justice-identity
plan: 01
subsystem: identity
tags: [postgres, partial-unique-index, sqlalchemy, alembic, pytest, oyez, dedup]

# Dependency graph
requires: []
provides:
  - "data/corpus/justice_identity_mapping.csv — 114-row verified mapping (oyez_speaker_id, corpus_display_name, first_name, middle_name, last_name, name_suffix), zero unmapped ids either direction"
  - "Migration 0032: people.display_name (nullable String(300)) + partial unique index uq_people_oyez_speaker_id on people(oyez_speaker_id) WHERE oyez_speaker_id IS NOT NULL"
  - "pipeline/commands/import_justices_csv.py dedups mapped justices on oyez_speaker_id (fallback: full_name for unmapped D-04 rows), writes oyez_speaker_id + display_name from the mapping, no derivation rule anywhere in the path"
  - "api/services/arguments.py speaker_name = COALESCE(Person.display_name, Person.full_name)"
  - "apply_person_value_change no longer performs a redundant write on a byte-identical trivial-agreement rerun"
  - "pipeline/tests/test_justice_identity_mapping.py — permanent regression suite pinning the mapping artifact's coverage and structural shape"
affects: [52-02, 52-03, 52-04, 52-05, 54.1]

# Actuals (#2632)
actuals:
  tokens: 17056
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SQLAlchemy/Alembic partial unique index via op.create_index(..., unique=True, postgresql_where=sa.text(...)) — first use in this repo's 32+ migrations"
    - "Mapping-CSV-as-join-key pattern: a verified data artifact (gitignored, alongside its source CSV) supersedes a name-string dedup key without touching the source file"
    - "Trivial-ACCEPT no-write gate: an authority-ladder ACCEPT decision reached via decide_write's bare-ACCEPT path (values_differ=False) performs no DB write, since decide_write only returns ACCEPT_AND_RECORD when a write is actually needed"

key-files:
  created:
    - data/corpus/justice_identity_mapping.csv (untracked, gitignored — data artifact)
    - alembic/versions/0032_person_display_name_and_oyez_unique.py
    - pipeline/tests/test_justice_identity_resolution.py
    - pipeline/tests/test_justice_identity_mapping.py
  modified:
    - api/models/models.py
    - api/services/arguments.py
    - pipeline/commands/import_justices_csv.py
    - pipeline/tests/test_import_justices_csv.py
    - api/services/admin_review.py
    - api/tests/test_authority_matrix.py

key-decisions:
  - "oyez_speaker_id is promoted from an unused nullable side-column to the primary identity key for every corpus-resolved person; full_name string equality is demoted to the fallback branch used only for unmapped rows (D-04's Barrett/Jackson)."
  - "display_name is written by plain assignment, never routed through apply_person_value_change's authority ladder — D-09 keeps it off PersonUpdate's allow-list, so no operator edit can ever exist for the ladder to arbitrate against (RESEARCH.md Pitfall 2, resolved explicitly rather than silently copying the name-part ladder shape)."
  - "The 4 rows the draft flagged as needing the operator (the two Harlans, Salmon P. Chase, Henry Brockholst Livingston) were typed in directly per D-01's tenure-date evidence, not resolved by any matching logic."
  - "Structural test reconstructs corpus_display_name from name parts using the SAME middle-initial-abbreviation rule the design note measured at 88% accuracy and rejected as a source of truth — reused here only as a verifier of the hand-verified artifact, gated by a named 7-row (D-02) + 1-row (D-01 Livingston) exception set, never as a generator."
  - "apply_person_value_change's ACCEPT path now skips its update() write when values_differ is False, since decide_write only ever returns bare ACCEPT for a byte-identical trivial agreement (Task 2's trivial-ACCEPT provenance restamp fix, scoped to the one caller import_justices_csv.py's reseed actually exercises)."

patterns-established:
  - "Justice identity mapping CSV is the join-key source of truth: a data artifact (data/corpus/justice_identity_mapping.csv) joins the source tenure CSV to the corpus by verified oyez_speaker_id, never by name-string matching."

requirements-completed: [JUSTICE-01, JUSTICE-02, JUSTICE-03, JUSTICE-05]

coverage:
  - id: D1
    description: "Verified 114-row justice identity mapping artifact (D-06/D-07/D-08 shape), zero unmapped ids either direction"
    requirement: JUSTICE-01
    verification:
      - kind: integration
        ref: "pipeline/tests/test_justice_identity_mapping.py#test_coverage_matches_speakers_json_exactly"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_justice_identity_mapping.py#test_row_count_is_114_and_every_id_unique"
        status: pass
      - kind: other
        ref: "grep -c 'confidence' data/corpus/justice_identity_mapping.csv -> 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "Migration 0032 — nullable people.display_name + partial unique index uq_people_oyez_speaker_id, reversible in both directions"
    requirement: JUSTICE-05
    verification:
      - kind: other
        ref: "./.venv/bin/alembic upgrade head && ./.venv/bin/alembic downgrade -1 && ./.venv/bin/alembic upgrade head"
        status: pass
      - kind: manual_procedural
        ref: "psql information_schema.columns / pg_indexes check for display_name + uq_people_oyez_speaker_id WHERE (oyez_speaker_id IS NOT NULL)"
        status: pass
    human_judgment: false
  - id: D3
    description: "import_justices_csv dedups mapped justices on oyez_speaker_id, unmapped rows fall back to full_name, no derivation rule anywhere in the path"
    requirement: JUSTICE-02
    verification:
      - kind: integration
        ref: "pipeline/tests/test_justice_identity_resolution.py#test_import_creates_person_with_mapped_identity"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_justice_identity_resolution.py#test_rerun_creates_no_second_white_row"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_justice_identity_resolution.py#test_existing_person_with_id_but_different_full_name_is_upgraded"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py#test_unmapped_row_dedups_on_full_name_fallback_across_rerun"
        status: pass
    human_judgment: false
  - id: D4
    description: "speaker_name projects COALESCE(display_name, full_name) — corpus form for a justice, unchanged full_name for an advocate"
    requirement: JUSTICE-03
    verification:
      - kind: integration
        ref: "pipeline/tests/test_justice_identity_resolution.py#test_speaker_name_coalesces_display_name_then_full_name"
        status: pass
    human_judgment: false
  - id: D5
    description: "Postgres itself refuses a second row with a duplicate oyez_speaker_id, while tolerating multiple NULLs"
    requirement: JUSTICE-05
    verification:
      - kind: integration
        ref: "pipeline/tests/test_justice_identity_resolution.py#test_duplicate_oyez_speaker_id_raises_integrity_error"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_justice_identity_resolution.py#test_multiple_null_oyez_speaker_id_rows_coexist"
        status: pass
    human_judgment: false
  - id: D6
    description: "Existing importer test suite (42 tests) converges onto the new oyez_speaker_id dedup key; superseded-behavior audit found nothing to retire"
    requirement: JUSTICE-02
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py (full module)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Trivial-ACCEPT provenance restamp gated on _values_differ; operator-confirmed row survives a byte-identical reseed"
    verification:
      - kind: integration
        ref: "api/tests/test_authority_matrix.py#test_apply_person_value_change_operator_confirmed_row_survives_identical_reseed"
        status: pass
    human_judgment: false
  - id: D8
    description: "Permanent structural + coverage regression test for the mapping artifact, with a named 7-row D-02 + 1-row D-01 exception set and Holmes's D-05 suffix disagreement pinned by name"
    requirement: JUSTICE-01
    verification:
      - kind: integration
        ref: "pipeline/tests/test_justice_identity_mapping.py (full module, 7 tests)"
        status: pass
      - kind: manual_procedural
        ref: "Deliberate oyez_speaker_id typo in the real mapping CSV made the coverage test fail naming the offending id; reverted"
        status: pass
    human_judgment: false

duration: 46min
completed: 2026-09-25
status: complete
---

# Phase 52 Plan 01: Justice Identity — oyez_speaker_id Join Summary

**Justice identity dedup flips from `Person.full_name` string matching to a verified `oyez_speaker_id` join, enforced by a Postgres partial unique index, proven end-to-end on Byron R. White before the full 114-row mapping and importer conversion.**

## Performance

- **Duration:** 46 min
- **Started:** 2026-09-25T10:55:33Z
- **Completed:** 2026-09-25T11:41:16Z
- **Tasks:** 3
- **Files modified:** 9 (4 created, 5 modified; `data/corpus/justice_identity_mapping.csv` also created but intentionally untracked)

## Accomplishments
- Verified 114-row `data/corpus/justice_identity_mapping.csv`, joining every corpus `j__`-prefixed speaker id to explicit CSV name parts (not a reconstructed `full_name` string), with zero unmapped ids either direction
- Migration 0032: nullable `people.display_name` + the first `postgresql_where` partial unique index in this repo's migration history, making a duplicate justice row structurally impossible while tolerating D-04's NULL-`oyez_speaker_id` rows (Barrett, Jackson)
- `import_justices_csv` dedup key flipped from `full_name` equality to `oyez_speaker_id`-from-mapping, with the legacy full_name lookup demoted to the fallback branch for unmapped rows — no derivation rule anywhere in the path
- `speaker_name` now `COALESCE(Person.display_name, Person.full_name)`, so utterance attribution reads the corpus form for a justice and the unchanged form for an advocate
- Converged 9 pre-existing "person to upgrade" fixtures in `test_import_justices_csv.py` onto the real id-keyed dedup path (previously all fictional names silently exercised only the fallback branch) and added the missing-mapping / empty-mapping pre-flight tests
- Gated `apply_person_value_change`'s trivial-ACCEPT write so a byte-identical reseed performs no redundant DB write
- Permanent `pipeline/tests/test_justice_identity_mapping.py` pinning coverage, structural agreement, row count, header shape, and Holmes's lone D-05 suffix disagreement — verified by hand that a deliberate id typo fails loudly naming the offending id

## Task Commits

Each task was committed atomically:

1. **Task 1: One justice resolves end to end — mapping, migration, importer, attribution** - `829942a3f` (feat)
2. **Task 2: Converge the importer's existing test suite and its provenance restamp onto the new key** - `c8b636bd2` (test)
3. **Task 3: Pin the mapping artifact with a permanent structural and coverage test** - `70e31f1d0` (test)

_Task 1 was `type="tracer"` — the tracer feedback gate (re-running its `<verify>` end-to-end) passed before Task 2/3 began; no checkpoint was needed since the run is interactive/end-of-phase with an automated-only `<verify>`._

## Files Created/Modified
- `data/corpus/justice_identity_mapping.csv` - the verified 114-row mapping (gitignored, intentionally untracked)
- `alembic/versions/0032_person_display_name_and_oyez_unique.py` - `people.display_name` column + `uq_people_oyez_speaker_id` partial unique index
- `api/models/models.py` - `Person.display_name` ORM column
- `pipeline/commands/import_justices_csv.py` - mapping load, `oyez_speaker_id`-keyed dedup, `display_name`/`oyez_speaker_id` writes, updated docstring
- `api/services/arguments.py` - `speaker_name` COALESCE
- `pipeline/tests/test_justice_identity_resolution.py` - new, pins the 5 Task 1 behavior cases end-to-end for `j__byron_r_white`
- `pipeline/tests/test_import_justices_csv.py` - 9 fixtures converged onto id-keyed dedup, 3 new tests (unmapped fallback, missing-mapping, empty-mapping)
- `api/services/admin_review.py` - `apply_person_value_change` no-op-write gate
- `api/tests/test_authority_matrix.py` - operator-confirmed-survives-reseed regression test
- `pipeline/tests/test_justice_identity_mapping.py` - new, permanent structural/coverage regression suite

## Decisions Made
See `key-decisions` in frontmatter. The most consequential: `oyez_speaker_id` is now the primary identity key (promote, not add-alongside) — `full_name` string equality is demoted to the fallback used only when a CSV row has no mapping entry, matching `import_convokit::_resolve_person`'s existing id-first preference order exactly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added structural verification against the source CSV, beyond the plan's literal id-vs-name-parts check**
- **Found during:** Task 3
- **Issue:** The plan's `<behavior>` bullet for "Structural agreement (D-02)" literally describes only an oyez_speaker_id-slug-vs-first/last-name check, but CONTEXT.md's own D-02 description and the module docstring instruction ("cite the ROADMAP note that the first-initial rule was rejected at 88% accuracy") only make sense against a corpus_display_name reconstruction check — the same middle-initial-abbreviation rule the design note measured and rejected as a generator. Implementing only the narrower literal check would have made the 7-name D-02 allow-list vacuous (every one of the 114 rows already passes the narrow id-vs-name-parts check).
- **Fix:** Implemented both: the narrow id-vs-first/last-name check (holds for all 114 rows, no exceptions needed) AND a separate corpus_display_name-reconstruction check (full or middle-initial-abbreviated form), gated by the named 7-row D-02 + 1-row D-01 (Livingston) exception set — verified computationally against the real 114-row mapping that this exact exception set is necessary and sufficient (zero other rows fail either check).
- **Files modified:** pipeline/tests/test_justice_identity_mapping.py
- **Verification:** All 7 tests pass; the deliberate-typo hand-check (acceptance criterion) confirms the coverage test's failure message names the offending id.
- **Committed in:** 70e31f1d0 (Task 3 commit)

**2. [Rule 1 - Bug] Added a source-CSV cross-reference test the plan's `<behavior>` list didn't separately enumerate**
- **Found during:** Task 3
- **Issue:** The coverage and structural checks as specified only compare the mapping against itself and against speakers.json — neither would catch a hand-edit typo in the mapping's own `first_name`/`middle_name`/`last_name`/`name_suffix` columns that still happens to pass the narrow id-vs-parts check (e.g. swapping two justices' middle names). The plan's own `<read_first>` names `supreme_court_justices_sections.csv` as something "the structural assertion joins against," implying this cross-reference was intended.
- **Fix:** Added `test_name_parts_correspond_to_source_csv_rows`, asserting every mapping row's name-part tuple is an actual row in the source CSV (parsed with the same two-section logic `import_justices_csv.py::_iter_csv_rows` uses).
- **Files modified:** pipeline/tests/test_justice_identity_mapping.py
- **Verification:** Test passes against the real mapping; strengthens the "permanent regression test" goal the plan's own action text states.
- **Committed in:** 70e31f1d0 (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1/2 — correctness/missing-critical, both confined to the new permanent test module). **Impact on plan:** Both strengthen the regression test's actual catching power without changing any shipped runtime code path. No scope creep — no other file was touched beyond what the plan named.

## Issues Encountered

**Untracked files not created by this execution.** During Task 2, two untracked todo files appeared in `.planning/todos/pending/` (`2026-09-25-harlan-i-carries-harlan-ii-utterances.md`, `2026-09-25-harlan-ii-stray-2003-utterance.md`) documenting a genuine pre-existing upstream (Oyez/ConvoKit) data defect: 803 utterances dated 1955–1970 are attributed to `j__john_m_harlan` (Harlan I, died 1911) instead of `j__john_m_harlan2` (Harlan II), plus one stray 2003 utterance on Harlan II. These were not created by this executor — no command run during this plan wrote to `.planning/todos/`. They are out of scope for this plan (not in `files_modified`) and were left untouched, uncommitted. Flagging here per the "verify agent compliance" discipline: they represent real, substantive findings (not noise) and should be triaged by the operator or a future phase — they are pre-existing corpus data errors, not introduced by this plan, and Phase 52's own scope explicitly excludes any backfill/correction of historical corpus data beyond the identity join itself.

## User Setup Required
**A one-time local-file precondition, already satisfied.** The plan's `user_setup` names `data/corpus/supreme_court_justices_sections.csv` and `data/corpus/speakers.json` as operator-supplied gitignored inputs this plan's mapping artifact is built from and verified against. Both were present on this machine at execution time (verified before Task 1 began) — no action needed.

## Next Phase Readiness
- The `oyez_speaker_id` join, the partial unique index, and the verified mapping artifact are all in place — Plans 52-02 through 52-05 (admin read-only fields, avatar initials, reset-to-fixture seeding, D-14/D-15 UI-SPEC amendment) can build on this without re-deriving any of it.
- `import_convokit::_resolve_person` needed no change and none was made — confirmed unchanged (`git diff --name-only -- pipeline/commands/import_convokit.py` prints nothing).
- No blockers. The two out-of-scope todo files noted above (Harlan I/II utterance misattribution) are a known, pre-existing corpus data issue for the operator to triage separately — not a blocker to this plan or to 52-02+.

---
*Phase: 52-justice-identity*
*Completed: 2026-09-25*

## Self-Check: PASSED

All created files verified present on disk (`data/corpus/justice_identity_mapping.csv`,
`alembic/versions/0032_person_display_name_and_oyez_unique.py`,
`pipeline/tests/test_justice_identity_resolution.py`,
`pipeline/tests/test_justice_identity_mapping.py`). All three task commits
(`829942a3f`, `c8b636bd2`, `70e31f1d0`) verified present in `git log`. All
acceptance criteria re-run and passing (Task 1: 13/13, Task 2: 5/5, Task 3:
5/5). Plan-level `<verification>` re-run: `pytest -q` → 1366 passed, 5
xfailed; `pytest pipeline/tests/ -q` → 378 passed, 5 xfailed; migration
0032 downgrade/upgrade round-trips cleanly; `git status --porcelain
data/corpus/` empty.
