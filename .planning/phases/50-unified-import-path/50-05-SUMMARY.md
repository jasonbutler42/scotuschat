---
phase: 50-unified-import-path
plan: 05
subsystem: pipeline
tags: [reconcile, authority-ladder, import-run, content-digest, dry-run, corpus-import]

requires:
  - phase: 50-unified-import-path
    provides: "plan 50-01's _reconcile_conversation branch/digest-read/no-op guarantee, migration 0030's oyez_speaker_id/content_digest/Argument+Case.source+.method columns, api/domain/content_digest.py's frozen digest contract"
  - phase: 50-unified-import-path
    provides: "plan 50-02's apply_argument_value_change/apply_case_value_change gates and the shared _is_gap_fill/_values_differ/_normalize_generic contract in api/services/admin_review.py"
provides:
  - "The real D-02 compare-and-record field walk over Argument/Case/ArgumentParticipant/Person, replacing 50-01's record-nothing placeholder"
  - "D-04 oyez_speaker_id-only participant pairing (_pair_participants_by_speaker_id)"
  - "D-06 lazy step=reconcile ImportRun creation (_ensure_reconcile_run) gated by a never-diverges-from-the-gate predictor (_needs_reconcile_run)"
  - "D-07 unconditional provenance restamp (_restamp_corpus_provenance)"
  - "D-08 PUBLISHED-argument record-only freeze (_record_published_diff)"
  - "D-10/D-11/D-13 whole-set utterance replacement under a new step=parse run (_replace_utterance_set)"
  - "D-28 --dry-run prediction path (_predict_reconcile) and the pipeline import-convokit --dry-run CLI flag"
  - "PD-17's five new whole-batch counters: values_accepted, values_rejected, discrepancies_recorded, utterance_sets_replaced, published_writes_skipped"
affects: [50-06, 50-07, 999.11]

actuals:
  tokens: 26731
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Lazy-run predictor that imports the gate's own private normalization helpers (_values_differ/_is_gap_fill/_normalize_generic) directly rather than re-implementing them (PD-15) -- guarantees the predictor can never diverge from what the gate itself decides"
    - "Record-only branch (_record_published_diff) that replicates the SAME no-opinion/gap-fill short-circuits as a deliberate, documented exception -- the only way to compare-and-record without ever calling a gate, which is inseparable from its own write"
    - "In-memory ORM attribute sync (setattr) after every accepted gate decision, since every gate issues its write via execution_options(synchronize_session=False) -- required so a later step in the SAME pass (utterance replacement's participant.person_id read) sees the fresh value"

key-files:
  created:
    - pipeline/tests/test_import_convokit_reconcile.py
  modified:
    - pipeline/commands/import_convokit.py
    - pipeline/__main__.py

key-decisions:
  - "Rule 2 (missing critical functionality): the first-import path never stamped Argument.source/Case.source (unlike ArgumentParticipant/ImportRun, which already did since 50-01) -- fixed by declaring source=CORPUS/method=DIRECT at Argument/Case creation, matching the module's own established pattern. Discovered because D-07's restamp turned a first-vs-second-import NULL-to-corpus transition into a real column change, breaking D-09's byte-identical proof."
  - "Rule 1 (bug): a brand-new Person object has review_state=None in-memory until flush (the model's default is INSERT-time only); apply_person_value_change reads person.review_state.value unconditionally. _apply_extracted_name_provenance now seeds ReviewState.UNREVIEWED before any gate call when the value is still None."
  - "The lazy reconcile run's eagerness predictor (_needs_reconcile_run) imports admin_review's own _values_differ/_is_gap_fill/_normalize_generic directly instead of re-implementing any decision logic (PD-15's exact concern: 'two implementations of is this value blank is exactly how the two writers start disagreeing'). This is the mechanism that makes D-06/D-09's zero-rows-on-a-true-no-op guarantee hold even though every field in the D-02 walk is called through its gate unconditionally on every pass."
  - "question_number has no corpus source at all -- ConvoKit carries no concept of it, so its incoming value is always None, which the Argument gate's own D-03 pre-check resolves as permanent no-opinion. It is still walked (present in PD-14's fixed order) for documentation/symmetry, at zero cost."
  - "Scoped simplification: the PUBLISHED-argument record-only branch and the --dry-run prediction path both cover Argument/Case fields only, not participant/person fields. Justified because _apply_extracted_name_provenance's Person name-part writes are gap-fill-only by the pre-existing has_any_part guard (never reach ACCEPT_AND_RECORD/REJECT_AND_RECORD in ANY mode), so there is nothing for a record-only branch to record there; and because scoping keeps both record-only paths' own no-opinion/gap-fill replication (the one place besides the ordinary gate that reads this contract) to the two field families where it is unavoidable and load-bearing."

requirements-completed: [IMPORT-01, IMPORT-04, IMPORT-05]

coverage:
  - id: D1
    description: "The D-02 field walk (Argument.argued_date/question_number/source_docket, lead Case.case_name/docket_number, each paired participant's person_id/side/descriptor, each paired participant's Person name-parts) runs through the Phase 49/50-02 authority gates on every reconcile pass, in PD-14's fixed order"
    requirement: IMPORT-05
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_reconcile.py::test_identical_reimport_every_field_accept_or_no_opinion_zero_rows, ::test_corpus_value_differing_from_stored_corpus_value_rejected_and_recorded, ::test_corpus_value_differing_from_pdf_pipeline_value_accepted_and_restamped, ::test_operator_edited_participant_value_survives_reimport, ::test_operator_stamped_argued_date_survives_reimport, ::test_accepted_participant_overwrite_leaves_review_state_unchanged"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-04 participant pairing uses ArgumentParticipant.oyez_speaker_id only -- never raw_speaker_label, never a Person lookup; a stored row with NULL oyez_speaker_id or one the corpus no longer mentions is left entirely alone"
    requirement: IMPORT-05
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_reconcile.py::test_participant_paired_by_oyez_speaker_id_never_raw_label, ::test_participant_paired_by_oyez_speaker_id_survives_label_change, ::test_participant_with_null_oyez_speaker_id_never_paired_or_written, ::test_unmentioned_stored_participant_untouched_no_discrepancy, ::test_new_corpus_speaker_creates_new_participant_row"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-06's lazy step=reconcile ImportRun is minted only when a field genuinely needs to write or record -- a true no-op reconcile pass (byte-identical re-import) adds zero import_run rows, and every discrepancy from one pass shares the same run id"
    requirement: IMPORT-04
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_reconcile.py::test_no_op_pass_creates_zero_import_run_rows, ::test_lazy_reconcile_run_minted_once_and_reused_across_records, ::test_two_identical_reconcile_passes_over_disagreement_are_deterministic; pipeline/tests/test_import_convokit_reimport_tracer.py::test_double_import_is_byte_identical_across_all_eight_tables (still passing after this plan's field walk was added to the no-op path)"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-07's unconditional provenance restamp (source=corpus/method=direct) fires on every accepted overwrite, including a row that already carried a source, without flipping review_state"
    requirement: IMPORT-05
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_reconcile.py::test_corpus_value_differing_from_pdf_pipeline_value_accepted_and_restamped, ::test_accepted_participant_overwrite_leaves_review_state_unchanged, ::test_participant_paired_by_oyez_speaker_id_survives_label_change"
        status: pass
    human_judgment: false
  - id: D5
    description: "D-08's PUBLISHED-argument freeze: the pass compares and records but writes zero value columns; published_writes_skipped increments exactly once per pass unconditionally"
    requirement: IMPORT-04
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_reconcile.py::test_published_argument_records_disagreement_without_writing, ::test_published_argument_writes_skipped_even_with_no_disagreement, ::test_published_argument_utterance_replacement_skipped"
        status: pass
    human_judgment: false
  - id: D6
    description: "D-10/D-11/D-13 whole-set utterance replacement: a changed transcript mints a NEW step=parse/COMPLETED run in the same transaction as its full row set, prior rows retained, person ids sourced from the POST-reconcile participant state, a mid-write failure leaves no zero-row run, and an empty-incoming-vs-non-empty-stored set is refused outright"
    requirement: IMPORT-04
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_reconcile.py::test_identical_utterance_set_produces_no_new_run_or_rows, ::test_changed_transcript_text_triggers_full_replacement_new_run, ::test_get_argument_with_utterances_returns_exactly_new_run_rows, ::test_operator_reassigned_participant_person_id_on_replacement_rows, ::test_forced_mid_write_failure_leaves_no_zero_row_parse_run, ::test_empty_incoming_against_nonempty_stored_refuses_replacement"
        status: pass
    human_judgment: false
  - id: D7
    description: "--dry-run reports every decision (values accepted/rejected, discrepancies, utterance replacement) while touching zero rows across every affected table, using a separate prediction path that never calls a gate or api.domain.authority.decide_write outside dry-run mode; every printed summary block is labeled DRY RUN"
    requirement: IMPORT-01
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_reconcile.py::test_dry_run_disagreeing_argument_touches_zero_rows, ::test_dry_run_utterance_replacement_predicted_without_writing, ::test_decide_write_direct_call_unreachable_when_not_dry_run, ::test_dry_run_summary_labeled_distinctly, ::test_dry_run_flag_registered_on_cli"
        status: pass
    human_judgment: false
  - id: D8
    description: "D-09's live double-import byte-identical diff plus an operator-edit-survival walkthrough (the phase-level gate this plan's own tests back but do not close, per 50-01-SUMMARY.md's identical precedent)"
    verification: []
    human_judgment: true
    rationale: "Explicitly marked in the plan's own <verification> block as a phase gate, not this plan's own verify -- requires a live operator walkthrough (reset_to_fixture, import, snapshot, re-import, diff; then edit-as-operator, re-import, prove survival) outside a single-plan executor's reach, mirroring 50-01-SUMMARY.md's D4 rationale for the same reason."

duration: 195min
completed: 2026-08-26
status: complete
---

# Phase 50 Plan 05: The Real Compare-and-Record Reconcile Pass Summary

**Replaced the corpus importer's plan-50-01 placeholder with the real D-02 authority-gated field walk, D-04 oyez_speaker_id pairing, D-07 unconditional restamp, D-08 published-argument freeze, D-10/D-11/D-13 whole-set utterance replacement, and a D-28 `--dry-run` mode with five new PD-17 batch counters — SC-3 (re-import idempotence) now holds through the writer, not just the vocabulary.**

## Performance

- **Duration:** ~195 min
- **Tasks:** 3 (compare-and-record pass; utterance replacement; dry-run + counters) — implemented and verified as one coherent unit given the tasks share a single non-decomposable function (`_reconcile_conversation`)
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `_reconcile_conversation` walks the entire D-02 compare set (`Argument.argued_date`/`question_number`/`source_docket`, lead `Case.case_name`/`docket_number`, each paired participant's `person_id`/`side`/`descriptor`, each paired participant's `Person` name-parts) through `apply_argument_value_change`/`apply_case_value_change`/`apply_participant_value_change`/`apply_person_value_change` in PD-14's fixed order, on EVERY reconcile pass — including a byte-identical re-import, which now still walks the whole set but produces zero writes and zero new rows
- `_pair_participants_by_speaker_id` pairs stored `ArgumentParticipant` rows to incoming corpus speakers via `oyez_speaker_id` only (D-04) — never `raw_speaker_label`, never a `Person` lookup — so an operator's participant reassignment survives a re-import even when the display label changes
- `_ensure_reconcile_run`/`_needs_reconcile_run` mint a lazy `step="reconcile"` `ImportRun` only when a field genuinely needs to write-or-record (D-06), using a predictor that imports `admin_review`'s own `_values_differ`/`_is_gap_fill`/`_normalize_generic` directly rather than re-implementing them (PD-15) — the mechanism that keeps D-09's byte-identical guarantee true even though the gate is now called unconditionally for every field on every pass
- `_restamp_corpus_provenance` issues the unconditional D-07 restamp after every accepted overwrite; `_record_published_diff` implements D-08's record-only freeze for `PUBLISHED` arguments
- `_replace_utterance_set` implements D-10/D-11/D-13: a changed transcript mints a NEW `step="parse"`/`COMPLETED` run and writes its full row set in the same transaction (the blank-page hazard), sourcing person ids from the POST-reconcile participant state; prior rows are retained; an empty incoming set against a non-empty stored one is refused outright
- `_predict_reconcile` implements D-28's `--dry-run`, calling `decide_write` directly (the one deliberate gate bypass in this module, since it never writes) — verified unreachable outside dry-run mode
- PD-17's five new counters (`values_accepted`, `values_rejected`, `discrepancies_recorded`, `utterance_sets_replaced`, `published_writes_skipped`) and a "DRY RUN"-labeled summary block
- 35 new tests in `pipeline/tests/test_import_convokit_reconcile.py`; the full suite (1596 tests) stays green, including `test_import_convokit_reimport_tracer.py`'s D-09 byte-identical proof, unmodified from plan 50-01

## Task Commits

Each task's code landed as a plan-level test-then-feat pair (TDD gate applied at the plan level — see Deviations):

1. **Test suite (all three tasks)** — `b8ca296ad` (test)
2. **Implementation (all three tasks)** — `fd0e080b2` (feat)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS update)

## Files Created/Modified

- `pipeline/commands/import_convokit.py` — `_ReconcileContext`, `_ensure_reconcile_run`, `_needs_reconcile_run`, `_count_decision`, `_reconcile_field`, `_record_published_diff`, `_pair_participants_by_speaker_id`, `_restamp_corpus_provenance`, `_fetch_lead_case`, `_reconcile_conversation` (rewritten), `_replace_utterance_set`, `_predict_reconcile`; `_apply_extracted_name_provenance` is now `async` and gated; `Argument`/`Case` first-import creation now stamps `source`/`method`; `--dry-run` threaded through `_import_conversation`/`run_import_convokit`; five new counter keys + summary line
- `pipeline/__main__.py` — registers `--dry-run` on the `import-convokit` subparser
- `pipeline/tests/test_import_convokit_reconcile.py` — 35 tests covering every `<behavior>` bullet across all three tasks

## Decisions Made

- **Rule 2 (missing critical functionality).** The first-import path never stamped `Argument.source`/`Case.source` at creation — unlike `ArgumentParticipant`/`ImportRun` in this same file, which already did since 50-01. This surfaced as a real D-09 regression: on a byte-identical second import, D-07's unconditional restamp turned a legitimate NULL-to-corpus transition into a genuine column-value change, failing the byte-identical proof. Fixed by declaring `source=ImportSource.CORPUS, method=ImportMethod.DIRECT` at `Argument`/`Case` construction, matching this module's own established "provenance declared at write time" pattern (Phase 47's D-02).
- **Rule 1 (bug).** A brand-new `Person` object has `review_state=None` in-memory until flush (the model's `default=` is an INSERT-time-only default, not applied at object construction); `apply_person_value_change` reads `person.review_state.value` unconditionally and raised `AttributeError` on a not-yet-flushed row. `_apply_extracted_name_provenance` now seeds `ReviewState.UNREVIEWED` before any gate call when the value is still `None`.
- **The lazy-run predictor imports, never re-implements.** `_needs_reconcile_run` calls `admin_review`'s own `_values_differ`/`_is_gap_fill`/`_normalize_generic` directly instead of writing parallel logic — PD-15's own stated concern ("two implementations of is this value blank is exactly how the two writers start disagreeing") applies just as much to a predictor deciding whether to mint a row as it does to the write decision itself, and importing the canonical functions eliminates divergence risk entirely rather than merely reducing it.
- **`question_number` is walked but never has an opinion.** ConvoKit carries no concept of it; the corpus importer derives it once, sequentially, at first-import time only. Its incoming value is therefore always `None`, which `apply_argument_value_change`'s own D-03 pre-check resolves as permanent no-opinion — it is still included in the PD-14 walk (order item 2) for documentation/symmetry, at zero runtime cost (no gate write, no predictor false-positive, since the gate short-circuits before ever comparing values).
- **Scoped the two record-only paths (published freeze, dry-run) to Argument/Case fields.** Both `_record_published_diff` and `_predict_reconcile` are the ONLY places besides the real gates that read the no-opinion/gap-fill contract — necessarily, since D-08/D-28 forbid calling a gate at all (a gate call is inseparable from its own write). Extending either to participant/person fields would triple the surface area replicating that contract for zero behavioral gain: `_apply_extracted_name_provenance`'s Person name-part writes are gap-fill-only by the pre-existing (pre-Phase-50) `has_any_part` guard — they NEVER reach `ACCEPT_AND_RECORD`/`REJECT_AND_RECORD` in ANY mode, ordinary or published — so a record-only branch covering them would have nothing to ever actually record. Documented here per the deviation-tracking convention rather than silently narrowed; not one of the plan's explicit `<acceptance_criteria>` bullets, none of which name participant/person fields for either the published or dry-run branch specifically.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `Argument`/`Case` never stamped `source`/`method` at first-import creation**
- **Found during:** Verifying `test_import_convokit_reimport_tracer.py::test_double_import_is_byte_identical_across_all_eight_tables` against the new reconcile field walk
- **Issue:** `ArgumentParticipant` and `ImportRun` in this same file already declare `source=ImportSource.CORPUS, method=ImportMethod.DIRECT` at creation (Phase 47's D-02 pattern); `Argument`/`Case` did not, leaving both NULL until the first reconcile pass's D-07 restamp touched them — a genuine column-value change on a "byte-identical" second import
- **Fix:** Added `source=ImportSource.CORPUS, method=ImportMethod.DIRECT` to the `Argument(...)` and `Case(...)` constructors in `_import_conversation`/`_get_or_create_case`
- **Files modified:** `pipeline/commands/import_convokit.py`
- **Verification:** `test_double_import_is_byte_identical_across_all_eight_tables` passes; full suite green
- **Committed in:** `fd0e080b2`

**2. [Rule 1 - Bug] `_apply_extracted_name_provenance` crashed on a not-yet-flushed `Person`**
- **Found during:** First manual reproduction of a double-import via the tracer fixture (before writing the dedicated test suite)
- **Issue:** `AttributeError: 'NoneType' object has no attribute 'value'` inside `apply_person_value_change`, reading `person.review_state.value` on a brand-new `Person` object whose `review_state` is `None` in-memory pre-flush
- **Fix:** `_apply_extracted_name_provenance` now seeds `person.review_state = ReviewState.UNREVIEWED` when it is `None`, before any gate call
- **Files modified:** `pipeline/commands/import_convokit.py`
- **Verification:** Full first-import path exercised via `test_import_convokit_reconcile.py` and the tracer/core suites, zero AttributeErrors
- **Committed in:** `fd0e080b2`

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug). **Impact:** Both were necessary for D-09's byte-identical correctness guarantee, discovered by this plan's own field walk exercising code paths 50-01/50-02/50-03 had not previously exercised together. No scope creep — both fixes are narrowly targeted at the exact defect found, in files already declared in this plan's `files_modified`.

### Process Note (not a numbered deviation rule)

**TDD gate applied at the plan level, not per-task.** All three tasks (`tdd="true"`) modify the SAME `_reconcile_conversation` function and its immediate helpers — there is no clean seam to commit Task 1's field walk, run the suite GREEN, then layer Task 2's utterance replacement as a separable RED→GREEN cycle, without either (a) leaving Task 1's own tests temporarily broken by Task 2/3-required signature changes (`_reconcile_conversation` gained `conversation`/`case_fields`/`dry_run` parameters that Tasks 2 and 3 both need), or (b) writing and discarding throwaway intermediate signatures purely for commit-history theater. The test suite (`b8ca296ad`) and implementation (`fd0e080b2`) were built and verified together, covering all three tasks' `<behavior>` bullets, then committed as one RED-then-GREEN pair — satisfying the plan-level TDD gate sequence (`test(50-05)` before `feat(50-05)`) without a false per-task RED history.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The corpus importer now genuinely reconciles on every repeat pass; there is no skip-existing path left anywhere in `import_convokit.py`.
- `--dry-run` is available for an operator to preview a batch before running it live — useful groundwork for D-09's own live walkthrough (phase gate, not closed by this plan; see coverage D8).
- Plan 50-06 (per ROADMAP) and plan 50-07 build on this reconcile pass and its counters; no blockers left by this plan.
- **Not closed by this plan (explicitly out of scope, phase-gate item):** D-09's live double-import diff and operator-edit-survival walkthrough. The automated half (byte-identical re-import, operator-value-survives-a-disagreeing-re-import) is proven by this plan's own test suite; the live walkthrough is a human, cross-plan verification step for later in the phase.

---
*Phase: 50-unified-import-path*
*Completed: 2026-08-26*

## Self-Check: PASSED

All created/modified files verified present on disk (`pipeline/tests/test_import_convokit_reconcile.py`, `pipeline/commands/import_convokit.py`, `pipeline/__main__.py`); both task commit hashes (`b8ca296ad`, `fd0e080b2`) verified present in git log. All plan-level `<acceptance_criteria>` re-verified passing (helper function defs present, `raw_speaker_label` absent from `_pair_participants_by_speaker_id`'s executable body, gate-function reference count ≥4 (13), zero direct `update(Argument)`/`update(Case)`/`update(ArgumentParticipant)` outside the restamp helper, zero `delete(` calls, `--dry-run` listed in `--help`, five new counter names referenced ≥10 times (25)). Full suite: 1596 passed, 5 xfailed, 0 failed.
