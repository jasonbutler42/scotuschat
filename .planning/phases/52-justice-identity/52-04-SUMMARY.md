---
phase: 52-justice-identity
plan: 04
subsystem: identity
tags: [postgres, asyncpg, sqlalchemy, pytest, reset-to-fixture, dev-tooling]

# Dependency graph
requires:
  - phase: 52-01
    provides: "data/corpus/justice_identity_mapping.csv (114-row verified mapping), migration 0032 (people.display_name + uq_people_oyez_speaker_id partial unique index), import_justices_csv.py's oyez_speaker_id-keyed dedup"
provides:
  - "reset_to_fixture seeds the full ~116-justice bench (run_import_justices_csv) after the TRUNCATE commit and before the FIXTURE_SET reseed loop (D-16), so every dev reset leaves the People directory populated instead of empty"
  - "_require_corpus_files' pre-flight also requires the two justice CSVs, so a missing mapping raises CorpusUnavailableError before the TRUNCATE runs — an absent mapping can never leave the database empty"
  - "Both justice CSV readers open with utf-8-sig, so a BOM-prefixed operator file no longer silently yields zero mapped rows"
  - "The stale-created_at defect (2026-08-20 todo) is fixed: one extra db.commit() between the fixture-verification loop and the state-realization block closes the loop's stale open transaction, so argument_status_log.created_at stays monotonic with id"
  - "Five new tests in api/tests/test_admin_dev_routes.py pin the seeded bench's roster completeness, id uniqueness, idempotency, fail-before-destroy pre-flight, and utterance-attribution effect, all exercised against the real justice CSVs via a new _write_corpus_fixture justice_speaker_overrides parameter"
  - "Measured reset duration with the seed step included: 71.67s wall-clock (direct call), recorded for plan 52-05's AbortSignal sizing"
affects: [52-05, 54]

# Actuals (#2632) — pairs with the plan's estimate to calibrate future estimates.
actuals:
  tokens: 7075
  tasks: 3
  commits: 3
  plan_head_before: 9558a0a5f39d924f6a70ab4ba8d95f7212a59030

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Justice-bench seed insertion point: after a TRUNCATE's own commit, before the first fixture-reseed call, wrapped in the same try/except -> ResetIncompleteError shape the fixture loop already uses — reused verbatim rather than inventing a second failure-handling shape"
    - "Test-helper real-data copy-in: _write_corpus_fixture copies the real, gitignored justice CSVs into its synthetic corpus_dir (via a dedicated _require_real_justice_corpus_files skip-gate) rather than hand-building a synthetic mapping, so tests exercise the actual 116-justice/5-dual-service-justice shape"

key-files:
  created: []
  modified:
    - api/services/admin_dev.py
    - pipeline/commands/import_justices_csv.py
    - api/tests/test_admin_dev_routes.py

key-decisions:
  - "The justice seed call passes csv=None/mapping_csv=None when the resolved corpus directory is the default, letting run_import_justices_csv resolve its own module constants; when a test overrides corpus_dir, the two justice CSV paths are built from that directory instead, so the production path and the test override stay consistent without a second code path."
  - "The stale-created_at fix is a single extra db.commit() between the fixture-verification loop and the state-realization block, not a broader transaction restructuring — approve_argument/publish_argument already commit at their own end, so no further commit was needed between the per-fixture transitions themselves."
  - "Test verification of the seeded bench uses the REAL justice CSVs (copied into each test's synthetic corpus_dir) rather than a hand-built synthetic mapping, so the 116-distinct-person / 5-dual-service-justice / 114-mapped-id assertions are proven against the actual shipped data artifact, not an approximation of it."
  - "BOM tolerance (utf-8-sig) is verified structurally (grep, per the plan's own acceptance criteria) rather than with a dedicated runtime test exercising an actual BOM-prefixed file — flagged honestly in the coverage block below rather than silently marked auto-passing."

requirements-completed: [JUSTICE-04]

coverage:
  - id: D1
    description: "reset_to_fixture seeds the full justice bench after the TRUNCATE commit and before the first FIXTURE_SET import (D-16 insertion point)"
    requirement: JUSTICE-04
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_seeds_full_justice_roster"
        status: pass
      - kind: other
        ref: "grep -n 'run_import_justices_csv' api/services/admin_dev.py — call site is between the TRUNCATE line and the FIXTURE_SET loop line"
        status: pass
    human_judgment: false
  - id: D2
    description: "A missing justice CSV raises CorpusUnavailableError before the TRUNCATE runs — an absent mapping can never leave the database empty"
    requirement: JUSTICE-04
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_missing_justice_csv_raises_before_truncate"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both justice CSV readers are BOM-tolerant (utf-8-sig)"
    verification:
      - kind: other
        ref: "grep -c 'utf-8-sig' pipeline/commands/import_justices_csv.py -> 2"
        status: pass
    human_judgment: true
    rationale: "Verified structurally only (both readers open utf-8-sig); no runtime test exercises an actual BOM-prefixed CSV file, so a human/future test could still add one."
  - id: D4
    description: "The justice seed is idempotent — two resets in a row leave the same seeded-bench count and the same non-null oyez_speaker_id set"
    requirement: JUSTICE-04
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_justice_seed_is_idempotent"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every seeded justice's oyez_speaker_id is unique and the non-null set matches the verified mapping CSV's 114 ids exactly (2 unmapped: Barrett, Jackson)"
    requirement: JUSTICE-04
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_seeded_oyez_ids_unique_and_match_mapping"
        status: pass
    human_judgment: false
  - id: D6
    description: "argument_status_log.created_at stays monotonic with id for every seeded argument after a reset (2026-08-20 stale-timestamp todo, fixed)"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_status_log_created_at_monotonic_with_id"
        status: pass
    human_judgment: false
  - id: D7
    description: "speaker_alias rows remain deliberately un-restored by this reset (pre-existing, out-of-scope behavior left untouched)"
    verification:
      - kind: other
        ref: "git diff -U0 -- api/services/admin_dev.py | grep -c '^+.*speaker_alias' -> 0"
        status: pass
    human_judgment: false
  - id: D8
    description: "The reset's new duration (with the justice seed step) is a measured number, carried forward to plan 52-05 and Phase 54 — no tier-recompute optimization attempted (D-17 out of scope)"
    verification:
      - kind: other
        ref: "one-off measurement script: reset_to_fixture(corpus_dir=None) against the real corpus and the dev database -> 71.67s wall-clock"
        status: pass
    human_judgment: true
    rationale: "A recorded measurement, not a pass/fail assertion; 52-05 needs a human/planning decision to size its AbortSignal against this number."
  - id: D9
    description: "A seeded justice's utterance speaker_name resolves to the corpus display form (display_name) through the real reset path; an advocate's is unaffected — Success Criterion 2 proven end-to-end rather than via a hand-built fixture"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py#test_reset_justice_utterance_speaker_name_uses_corpus_display_form"
        status: pass
    human_judgment: false

duration: 43min
completed: 2026-09-25
status: complete
---

# Phase 52 Plan 04: Justice Identity — Seeded Bench Through Reset Summary

**`reset_to_fixture` now seeds the ~116-justice bench between its TRUNCATE and fixture reseed, refuses before the TRUNCATE when a justice CSV is missing, and no longer writes stale `argument_status_log` timestamps — measured at 71.67s wall-clock with the seed step included.**

## Performance

- **Duration:** 43 min (estimated — start time not explicitly logged; based on commit timestamps and observed activity, see Issues Encountered)
- **Started:** ~2026-09-25T13:00:00Z (estimated)
- **Completed:** 2026-09-25T13:41:04Z
- **Tasks:** 3
- **Files modified:** 3 (plus 1 new deferred-items.md)

## Accomplishments
- `reset_to_fixture` calls `run_import_justices_csv` immediately after the TRUNCATE's commit and before the `FIXTURE_SET` reseed loop (D-16), so `import_convokit::_resolve_person`'s `oyez_speaker_id` lookup hits on its first key for every seeded-justice utterance in a real-corpus reset, and the admin People directory shows the full bench after every reset instead of an empty list (Success Criterion 3)
- `_require_corpus_files`'s pre-flight now also requires the two justice CSVs (importing the path constants from `pipeline.commands.import_justices_csv` rather than re-typing filenames), so a missing mapping raises `CorpusUnavailableError` **before** the TRUNCATE runs — proven by a pre-seeded `people` row surviving the raise, not merely by the exception type
- Both justice CSV readers (`_load_justice_mapping`, `_iter_csv_rows`) open with `encoding="utf-8-sig"`, so a BOM-prefixed operator-supplied file no longer silently yields zero mapped rows
- Fixed the transaction-start timestamp skew this function has always written (2026-08-20 todo): one extra `await db.commit()` between the fixture-verification loop and the state-realization block closes the loop's own long-open read transaction, so `approve_argument`/`publish_argument`'s writes get a fresh `now()` at the real transition time instead of the loop's stale transaction-start time — `argument_status_log.created_at` is now monotonic with `id`
- Six new tests in `api/tests/test_admin_dev_routes.py`: one pinning the stale-timestamp fix, and five pinning the seeded bench's roster completeness (116 distinct people, 5 dual-service justices with both `court_tenures` rows), id uniqueness/mapping-match, idempotency, the fail-before-destroy pre-flight, and the utterance-attribution effect (`speaker_name` resolves to `display_name` for a seeded justice) — all exercised against the **real** justice CSVs, copied into each test's synthetic corpus dir by an extended `_write_corpus_fixture`
- Measured: one direct end-to-end `reset_to_fixture` call against the real corpus and the dev database completed in **71.67s** wall-clock, including the new justice seed step — well under (not within 20% of) undici's 300s `headersTimeout`, and inside the module's own pre-existing 80-120s estimate for the four-fixture reseed alone

## Task Commits

Each task was committed atomically:

1. **Task 1: Seed the bench between the TRUNCATE and the fixture reseed** - `6552d02b7` (feat)
2. **Task 2: Fix the transaction-start timestamp skew this function has always written** - `90e10b23b` (fix)
3. **Task 3: Pin the seeded bench end to end and record the new reset duration** - `46d52751e` (test)

## Files Created/Modified
- `api/services/admin_dev.py` — justice seed insertion (D-16), `_require_corpus_files` extension, stale-`created_at` commit-boundary fix, updated NOT-ATOMIC/performance-note docstrings
- `pipeline/commands/import_justices_csv.py` — `utf-8-sig` on both CSV readers (BOM tolerance)
- `api/tests/test_admin_dev_routes.py` — `_write_corpus_fixture` copies the real justice CSVs + gained a `justice_speaker_overrides` parameter, `_require_real_justice_corpus_files` skip-gate, 6 new tests
- `.planning/phases/52-justice-identity/deferred-items.md` — new; logs one out-of-scope pre-existing flaky test observed during full-suite verification

## Decisions Made
See `key-decisions` in frontmatter.

## Deviations from Plan

None — plan executed exactly as written. (One defect, the transaction-start `created_at` skew, was explicitly named as Claude's-to-fix by the plan itself — Task 2 — and is not a deviation from it.)

## Issues Encountered

**Start time not explicitly logged.** The `record_start_time` step's timestamp capture was not run before the first tool call in this session; `duration`/`Started` above are estimated backward from the first task commit's timestamp (`6552d02b7` at `2026-09-25T08:18:03-05:00`) and the volume of required-reading work observed before it, not measured directly. `Completed` is the last task commit's real timestamp. This does not affect the plan's substantive output.

**Interleaved editing required task-boundary reconstruction before committing.** Tasks 1-3's code edits were made in one continuous pass before any commit existed. Per the atomic-per-task-commit requirement, each task's file changes were then isolated (temporarily reverting Task 2/3-only hunks, verifying Task 1's own `<verify>` in that reduced state, committing, then re-applying Task 2's hunk and re-verifying, committing, then re-applying Task 3's remaining hunks and re-verifying) so each of the three commits above reflects exactly its own task's `<files>` and passes its own task's `<verify>` in isolation — not a post-hoc relabeling of one combined diff.

**One pre-existing flaky full-suite failure observed, confirmed unrelated.** The first `pytest -q` full-suite run (before Task 3's commit) showed `1393 passed, 1 failed, 5 xfailed`: `api/tests/test_public_arguments_listing.py::test_term_detail_consolidated_docket_contributes_one_row`, a random-year (`1920 + uuid4().int % 100`) test-data collision, unrelated to this plan's files. It passed in isolation and on a full clean re-run (`1394 passed, 5 xfailed, 0 failed`). Logged to `.planning/phases/52-justice-identity/deferred-items.md` per the Scope Boundary rule (not fixed — out of scope). An attempt to also record it in the cross-phase `.planning/WINDOWS.md` ledger via `gsd_run windows append` failed with a pre-existing frontmatter/entry count mismatch in that ledger (unrelated to this plan); per the ledger's documented best-effort contract, this was not retried or repaired.

## User Setup Required

None beyond what plan 52-04's own `user_setup` already named as satisfied: `data/corpus/` already held `supreme_court_justices_sections.csv` and `justice_identity_mapping.csv` (produced by plan 52-01) on this machine, confirmed present before Task 1 began and used directly by all measurement/verification steps.

## Next Phase Readiness

- The justice bench now survives every `reset_to_fixture` call, with the pre-flight refusing before any destructive statement when the mapping is absent, and the stale-`created_at` defect fixed — Success Criterion 3, JUSTICE-04, and the folded stale-timestamp todo are all closed.
- **Measured reset duration for plan 52-05's `AbortSignal` sizing: 71.67s wall-clock**, measured via a direct async call to `reset_to_fixture(corpus_dir=None)` against the real corpus and the dev database — bypassing the HTTP layer (auth middleware, uvicorn, FastAPI's own connection pool sizing). This is a **methodology caveat, not a final number**: plan 52-05 should treat 71.67s as a floor and may want to also measure through the actual `POST /api/admin/dev/reset-to-fixture` HTTP endpoint (the real path its `AbortSignal` will time) before finalizing the timeout value, since HTTP-layer overhead is not included here. It is well under (not within 20%) of undici's 300s `headersTimeout`.
- No blockers. The one out-of-scope flaky test noted above is pre-existing and confirmed unrelated by isolation + clean-rerun evidence.

---
*Phase: 52-justice-identity*
*Completed: 2026-09-25*

## Self-Check: PASSED

All modified files verified present on disk (`api/services/admin_dev.py`,
`pipeline/commands/import_justices_csv.py`, `api/tests/test_admin_dev_routes.py`,
`.planning/phases/52-justice-identity/deferred-items.md`). All three task commits
(`6552d02b7`, `90e10b23b`, `46d52751e`) verified present in `git log`. All
acceptance criteria re-run and passing at each task's own checkpoint (Task 1: 9/9
tests, Task 2: 10/10 tests, Task 3: 15/15 tests, none skipped). Plan-level
`<verification>` re-run: `pytest -q` → 1394 passed, 5 xfailed, 0 failed (clean
re-run after diagnosing one unrelated flaky failure on the first pass); a direct
real-corpus reset against the dev database confirmed zero duplicate
`oyez_speaker_id` rows and the Byron White dual-name-form row via SQL query;
measured reset duration (71.67s) recorded above and in the module docstring.
