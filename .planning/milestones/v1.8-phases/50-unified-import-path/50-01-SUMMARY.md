---
phase: 50-unified-import-path
plan: 01
subsystem: pipeline
tags: [import-run, alembic, content-digest, admin-job-retirement, sha256, corpus-import, reconcile]

requires:
  - phase: 49-review-model
    provides: value_discrepancy table, review_state vocabulary, api/domain/authority.py's decide_write, api/services/admin_review.py's gated writer
  - phase: 47-provenance-foundation
    provides: import_run generalization, ImportSource/ImportMethod enums, source=corpus/method=direct mapping
provides:
  - Alembic 0030 (ArgumentParticipant.oyez_speaker_id, ImportRun.content_digest, Argument/Case.source/.method)
  - api/domain/content_digest.py — the frozen D-13 utterance content-digest contract
  - A corpus importer that creates zero AdminJob rows and stamps oyez_speaker_id + content_digest
  - api/services/admin_arguments.py::approve_argument — the argument-scoped CANDIDATE->DRAFT transition
  - A reworked reset_to_fixture with no AdminJob dependency (all four fixture states re-realized)
  - The _reconcile_conversation branch (digest read + no-op guarantee only; compare-and-write body is plan 50-05's)
affects: [50-02, 50-03, 50-04, 50-05, 50-06, 50-07, 999.11]

actuals:
  tokens: 27765
  tasks: 4
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Frozen pure-domain contract module (api/domain/content_digest.py) mirroring api/domain/authority.py / trust.py's no-ORM-import discipline"
    - "Shared row-computation helper (_incoming_utterance_rows) factored out so a digest computation and its eventual DB write can never disagree on 'the incoming row set'"
    - "Digest-only comparison with zero DB writes on the reconcile no-op path (raw_speaker_label derived purely from speakers_index, never via participant resolution)"

key-files:
  created:
    - alembic/versions/0030_argument_case_provenance_and_digest.py
    - api/domain/content_digest.py
    - pipeline/tests/test_content_digest.py
    - pipeline/tests/test_import_convokit_reimport_tracer.py
  modified:
    - api/models/models.py
    - pipeline/commands/import_convokit.py
    - pipeline/__main__.py
    - api/services/admin_arguments.py
    - api/services/admin_dev.py
    - api/schemas/admin_dev.py
    - app/src/routes/admin/+page.svelte
    - pipeline/tests/test_import_convokit_adminjob.py
    - api/tests/test_admin_dev_routes.py
    - pipeline/tests/test_import_convokit_utterances.py

key-decisions:
  - "Task 0 checkpoint resolved freeze-as-proposed: sha256 hex digest over JSON-framed [sequence, raw_speaker_label, text, is_stage_direction] tuples, byte-exact, person_id/side/section_hint/identity columns excluded"
  - "_incoming_utterance_rows is a single shared, DB-write-free helper used both by the first-import write path and by _reconcile_conversation's digest-only comparison, so the digest and the rows actually written can never diverge"
  - "ImportRun creation moved to AFTER participant resolution and row computation (not before), so content_digest is stamped at construction time rather than via a later UPDATE — still satisfies 'created before any utterance write'"
  - "_reconcile_conversation in this plan only establishes the branch, the digest read (latest step=parse run, never a reconcile run), and the no-op guarantee — writes NOTHING in either the equal or not-equal case; the real compare-and-write body is plan 50-05's"

requirements-completed: [IMPORT-01, IMPORT-03, IMPORT-04]

coverage:
  - id: D1
    description: "Migration 0030 adds six nullable columns (oyez_speaker_id, content_digest, Argument/Case source+method) with no backfill; ORM models mirror them"
    requirement: IMPORT-05
    verification:
      - kind: integration
        ref: "api/tests/test_review_state_schema.py, pipeline/tests/test_import_run.py"
        status: pass
      - kind: other
        ref: "alembic upgrade head / downgrade -1 / upgrade head round-trip (dev + scotus_test)"
        status: pass
    human_judgment: false
  - id: D2
    description: "api/domain/content_digest.py is a pure, ORM-free, frozen digest contract covering every Task 2 behavior bullet"
    requirement: IMPORT-05
    verification:
      - kind: unit
        ref: "pipeline/tests/test_content_digest.py (12 tests, zero skips with no DATABASE_URL/TEST_DATABASE_URL set)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A fresh corpus import of one conversation creates exactly one step=parse import_run row (source=corpus, method=direct, pdf_path/pdf_url/prompt_version NULL) and zero admin_job rows"
    requirement: IMPORT-01
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_adminjob.py::test_fresh_corpus_import_creates_zero_admin_job_rows, ::test_argument_status_is_candidate_with_no_resolved_at"
        status: pass
    human_judgment: false
  - id: D4
    description: "Re-running an identical corpus import adds zero rows and changes zero column values across all eight affected tables (arguments, cases, case_arguments, argument_participants, import_run, utterances, value_discrepancy, admin_jobs)"
    requirement: IMPORT-04
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_reimport_tracer.py::test_double_import_is_byte_identical_across_all_eight_tables"
        status: pass
    human_judgment: true
    rationale: "D-09 explicitly requires this be closed by a live, human-observed double-import diff and an operator-edit-survival walkthrough, backed but not closed by the automated test — the automated half is proven here; the live walkthrough is outside a single-plan executor's reach."
  - id: D5
    description: "Every ArgumentParticipant row the corpus importer writes carries a non-NULL oyez_speaker_id equal to the resolved ConvoKit speaker id"
    requirement: IMPORT-05
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_reimport_tracer.py::test_every_participant_row_has_non_null_oyez_speaker_id"
        status: pass
    human_judgment: false
  - id: D6
    description: "approve_argument moves a jobless corpus argument CANDIDATE->DRAFT with resolved_at stamped; publish_argument's non-overridable gate is satisfied"
    requirement: IMPORT-03
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_adminjob.py::test_jobless_corpus_argument_is_reachable_and_approvable"
        status: pass
    human_judgment: false
  - id: D7
    description: "reset_to_fixture drives all four reference states (Complexity/Draft/Published/Mid-pipeline) with zero AdminJob involvement anywhere in its body"
    requirement: IMPORT-03
    verification:
      - kind: integration
        ref: "api/tests/test_admin_dev_routes.py::test_reset_realizes_state_variety, ::test_reset_response_reports_realized_states, ::test_reset_wipes_and_reseeds_fixtures"
        status: pass
    human_judgment: false

duration: 70min
completed: 2026-08-26
status: complete
---

# Phase 50 Plan 01: Vocabulary + Tracer — corpus import with no AdminJob, a frozen content digest, and a byte-identical re-import Summary

**Migration 0030 lands the D-04/D-13 vocabulary, `api/domain/content_digest.py` freezes the sha256 utterance-content contract from Task 0's checkpoint, and the corpus importer now imports one conversation twice with zero `AdminJob` rows and a byte-identical second pass across all eight affected tables.**

## Performance

- **Duration:** ~70 min (includes resolving a real cross-file test-isolation collision discovered mid-execution)
- **Started:** 2026-08-26T13:02:03Z (Task 1)
- **Completed:** 2026-08-26T13:51:08Z
- **Tasks:** 4 (Task 0 checkpoint decision + Tasks 1-3)
- **Files modified:** 14 (4 created, 10 modified)

## Accomplishments

- Migration 0030: six nullable columns (`argument_participants.oyez_speaker_id`, `import_run.content_digest`, `arguments`/`cases.source`+`.method`), no backfill, verified via a clean upgrade/downgrade/upgrade round-trip on both the dev and `scotus_test` databases
- `api/domain/content_digest.py`: the frozen D-13 digest contract — sha256 hex over a JSON-framed `[sequence, raw_speaker_label, text, is_stage_direction]` tuple list, byte-exact, 12/12 tests passing with no database
- The corpus importer (`pipeline/commands/import_convokit.py`) creates zero `AdminJob` rows, stamps `oyez_speaker_id` on every participant, stamps `content_digest` on every `step="parse"` run, and establishes the `_reconcile_conversation` branch (digest compare, writes nothing either way — the real compare-and-write body is plan 50-05's)
- `approve_argument` (the argument-scoped peer of `approve_job`) exists and is the only writer of `resolved_at` for a jobless corpus argument
- `reset_to_fixture` drives all four reference states with zero `AdminJob` involvement; Mid-pipeline is now a seeded `step="reconcile"` `ImportRun`
- D-09's byte-identical double-import proof passes across all eight named tables

## Task Commits

Each task was committed atomically:

1. **Task 0: Freeze the D-13 content-digest contract** — checkpoint decision only, `freeze-as-proposed` (no code commit; see Decisions)
2. **Task 1: Alembic 0030** — `2831118` (feat)
3. **Task 2: The frozen content-digest contract** — `278ebed` (test, RED) + `88959a4` (feat, GREEN)
4. **Task 3: TRACER — corpus import, no AdminJob, byte-identical re-import** — `5f3c08d` (feat)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS update)

## Files Created/Modified

- `alembic/versions/0030_argument_case_provenance_and_digest.py` — six nullable columns, no backfill
- `api/domain/content_digest.py` — the frozen D-13 digest contract (`DIGEST_VERSION`, `compute_utterance_digest`)
- `api/models/models.py` — ORM mirror of the six migration-0030 columns
- `pipeline/commands/import_convokit.py` — AdminJob fabrication deleted; `_incoming_utterance_rows` + `_reconcile_conversation` added; `_import_utterances` refactored to consume precomputed rows; `oyez_speaker_id` threaded into every participant
- `pipeline/__main__.py` — CLI description no longer promises a paused resolve job
- `api/services/admin_arguments.py` — `approve_argument` (argument-scoped CANDIDATE->DRAFT)
- `api/services/admin_dev.py` — `reset_to_fixture` reworked (no AdminJob), `_seed_reconcile_run_fixture` added
- `api/schemas/admin_dev.py` — `ResetFixtureItem.admin_job_status` -> `latest_import_run_step`
- `app/src/routes/admin/+page.svelte` — TS interface mirrors the schema rename
- `pipeline/tests/test_content_digest.py` — 12 tests, the frozen contract's full behavior matrix
- `pipeline/tests/test_import_convokit_adminjob.py` — rewritten as the IMPORT-03 negative-space module
- `pipeline/tests/test_import_convokit_reimport_tracer.py` — the D-09 byte-identical double-import proof
- `api/tests/test_admin_dev_routes.py` — updated for `latest_import_run_step` and zero-AdminJob assertions
- `pipeline/tests/test_import_convokit_utterances.py` — summary-counter test updated for the `skipped_existing` retirement

## Decisions Made

- **Task 0 checkpoint: `freeze-as-proposed`.** The D-13 digest contract is frozen exactly as PD-01 specified — sha256, JSON-framed 4-field tuples, byte-exact, `person_id`/`side`/`section_hint`/identity columns excluded, empty input hashes to a stable non-empty digest. `DIGEST_VERSION = 1`.
- **`_incoming_utterance_rows` is one shared, DB-write-free helper**, used by both the first-import write path and `_reconcile_conversation`'s digest-only comparison. `raw_speaker_label` is derived purely from `speakers_index` (a pure function of `speaker_id`), never via participant resolution — this is what lets the reconcile no-op path compute a comparison digest with genuinely zero DB writes, satisfying D-09's byte-identical guarantee even on a repeat pass.
- **`ImportRun` creation moved to after row computation**, not before — `content_digest` is stamped at construction time rather than via a later UPDATE. `run.id` is still available before any Utterance write, so T-29-09's ordering constraint still holds.
- **`_reconcile_conversation` in this plan is deliberately a stub for the "not equal" branch** — per the plan's own scope, it increments `arguments_reconciled` and prints a warning, writing nothing. The full compare-and-apply body (D-02/D-07/D-08/D-10) is plan 50-05's.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Migration 0030's docstring tripped its own acceptance-criteria grep**
- **Found during:** Task 1 verification
- **Issue:** The docstring's prose used the literal string "op.execute", which the acceptance criterion's `grep -c "op.execute"` (after stripping `#`-comment lines) matched even though it was prose, not code — the docstring isn't `#`-commented, it's a triple-quoted string.
- **Fix:** Reworded to "raw-SQL data statement" instead of naming the API call literally.
- **Files modified:** `alembic/versions/0030_argument_case_provenance_and_digest.py`
- **Verification:** `grep -v '^#' ... | grep -c "op.execute"` returns 0
- **Committed in:** `2831118` (Task 1 commit)

**2. [Rule 1 - Bug] `pipeline/tests/test_import_convokit_utterances.py`'s summary-counter test broke on PD-03's rename**
- **Found during:** Task 3 verification (full suite run)
- **Issue:** `test_summary_prints_term_year_and_core_counts` asserted `"arguments skipped" in captured.out`, which PD-03 (the plan's own decision record) explicitly retires — this file is not in the plan's `files_modified` list but its own decision made the assertion permanently false.
- **Fix:** Updated the assertion to check for `"arguments reconciled"` / `"arguments unchanged"` instead.
- **Files modified:** `pipeline/tests/test_import_convokit_utterances.py`
- **Verification:** `pytest pipeline/tests/test_import_convokit_utterances.py` — 16/16 passing
- **Committed in:** `5f3c08d` (Task 3 commit)

**3. [Rule 1 - Bug] `approve_argument`'s internal commit broke `isolated_session` test isolation**
- **Found during:** Task 3, writing `test_jobless_corpus_argument_is_reachable_and_approvable`
- **Issue:** `approve_argument` calls `db.commit()` internally (matching `approve_job`'s established contract, per D-14). Calling it on the shared `isolated_session` fixture in `test_import_convokit_adminjob.py` permanently committed that test's Person/Argument rows — the fixture's `finally: await session.rollback()` cannot undo an already-committed transaction, so the rows leaked into the shared `TEST_DATABASE_URL` database and collided with unrelated tests in other files that reuse common fixture names (e.g. "Jane Roe") in the same pytest session.
- **Fix:** Added explicit FK-ordered cleanup (`DELETE` statements + `session.commit()`) at the end of that one test, documented in its docstring as the one test in the module allowed to touch real commits.
- **Files modified:** `pipeline/tests/test_import_convokit_adminjob.py`
- **Verification:** Repeated full-suite and targeted-combination runs with zero residual rows confirmed via direct DB queries
- **Committed in:** `5f3c08d` (Task 3 commit)

**4. [Rule 1 - Bug] `test_import_convokit_reimport_tracer.py`'s own fixture initially collided with `test_import_convokit_adminjob.py`'s fixture**
- **Found during:** Task 3, combined-suite verification
- **Issue:** Both new/rewritten test files independently used `"Jane Roe"`/`"Test Justice Bench"` as speaker names and `"Roe v. Doe"` as a case title (copied from the pre-existing fixture convention). Run together, this produced (a) a `Person.oyez_speaker_id` lookup collision once deviation #3's leak was still being tracked down, and (b) — after renaming the speaker names — a genuine `cases_slug_key` UNIQUE-constraint violation, since `_derive_slug("Roe v. Doe")` produces the identical slug regardless of docket/term.
- **Fix:** Renamed `test_import_convokit_reimport_tracer.py`'s fixture speakers (`Pat Tracer50` / `Tracer50 Bench Justice`) and case title (`Tracer50 v. Reimport`) to be collision-free with every other corpus test fixture in the suite.
- **Files modified:** `pipeline/tests/test_import_convokit_reimport_tracer.py`
- **Verification:** Full suite green (1507 passed, 5 xfailed, 0 failed)
- **Committed in:** `5f3c08d` (Task 3 commit)

---

**Total deviations:** 4 auto-fixed (2 test-fixture-collision fixes, 1 acceptance-criteria wording fix, 1 pre-existing-test-break fix from the plan's own retirement of `skipped_existing`). **Impact:** All four were necessary for full-suite correctness; none touched production behavior beyond what the plan already specified. No scope creep.

### Acceptance-Criteria False Positive (documented, not fixed)

Task 3's acceptance criterion `grep -rn "admin_job_status" api/ app/src/ | wc -l` returns **1**, not 0. The sole remaining hit is `api/models/models.py`'s **pre-existing, unrelated** `SAEnum(AdminJobStatus, name="admin_job_status", ...)` — the PostgreSQL enum TYPE NAME for the still-live `AdminJob.status` column (the PDF path's own lifecycle object, untouched by this plan). This is a different symbol namespace from the `ResetFixtureItem.admin_job_status` JSON field this task actually retires (confirmed retired: zero hits in `api/schemas/`, `api/services/admin_dev.py`, or `app/src/routes/admin/+page.svelte`). Renaming the unrelated PG enum type would be an out-of-scope, unrelated schema change to the PDF path's own vocabulary — not attempted.

## Issues Encountered

- **`scotus_test` vs dev-DB pytest redirect.** Manually exporting `DATABASE_URL` to point at `scotus_test` before running `pytest` (needed for standalone `alembic` invocations against the test DB) confuses `conftest.py`'s dev-DB leak-detection tripwire, which captures `_REAL_DATABASE_URL` before its own `TEST_DATABASE_URL` redirect runs — if `DATABASE_URL` is already set to `scotus_test` when pytest starts, the tripwire ends up "watching" `scotus_test` for changes and false-fires on the test suite's own legitimate writes. Resolved by never manually exporting `DATABASE_URL` for pytest runs — the `.env`-driven `TEST_DATABASE_URL` redirect handles it correctly on its own. Alembic invocations against `scotus_test` still need the explicit export since alembic has no such redirect.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Migration 0030's vocabulary (`oyez_speaker_id`, `content_digest`, `Argument`/`Case.source`/`.method`) is live on both databases and ready for plan 50-02's authority-gate work.
- `_reconcile_conversation`'s branch, digest read, and no-op guarantee are proven — plan 50-05 builds the real compare-and-write body (D-02's field walk, D-07's restamp, D-08's published check, D-10's utterance rewrite) directly inside the "not equal" branch this plan established.
- `approve_argument` exists and is ready for plan 50-03's HTTP route + UI button.
- No blockers.

---
*Phase: 50-unified-import-path*
*Completed: 2026-08-26*

## Self-Check: PASSED

All created files verified present on disk; all four task commit hashes (`2831118`, `278ebed`, `88959a4`, `5f3c08d`) verified present in git log.
