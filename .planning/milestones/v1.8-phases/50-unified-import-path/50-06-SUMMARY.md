---
phase: 50-unified-import-path
plan: 06
subsystem: pipeline
tags: [authority-ladder, resolve, parse, import-justices, behavioral-gate, d-24]

requires:
  - phase: 50-unified-import-path
    plan: "01"
    provides: "Alembic 0030's Argument/Case source/method columns, api.domain.authority.decide_write (frozen Phase 49 ladder)"
  - phase: 50-unified-import-path
    plan: "02"
    provides: "apply_argument_value_change/apply_case_value_change (the two new peer gates) and the existing apply_participant_value_change/apply_person_value_change gates with their PD-13 gap-fill scope guard"
  - phase: 50-unified-import-path
    plan: "05"
    provides: "the corpus reconcile pass (_reconcile_conversation) as the delegation shape this plan copies, and _apply_extracted_name_provenance as the not-quite-gap-fill-only precedent this plan's import_justices_csv conversion mirrors"
provides:
  - "resolve.py's Step 5 bulk ArgumentParticipant.person_id UPDATE replaced by _apply_resolved_person_ids, a per-row apply_participant_value_change gate call"
  - "parse.py's argued_date/case_name/source_docket cover-metadata writes routed through apply_argument_value_change/apply_case_value_change via _write_cover_metadata_through_gate (argued_date/case_name) and an inline gate call (source_docket)"
  - "import_justices_csv.py's four blank-only Person name-part assignments replaced by four apply_person_value_change calls (incoming_source=seed)"
  - "pipeline/tests/test_gated_column_writers.py — the D-24 executable behavioral gate, 8 real-writer tests plus a falsifiability control"
affects: [50-07]

actuals:
  tokens: 21258
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Per-row gate replacing a bulk UPDATE: SELECT the matching rows first (a bulk statement's WHERE scoping becomes the SELECT's WHERE scoping), then call the gate once per row — established by resolve.py's _apply_resolved_person_ids, matching admin_jobs.py's pre-existing single-row gate-call shape"
    - "Provenance read off the run row's own .value strings, never hardcoded — every converted writer in this plan passes incoming_source/incoming_method derived from its own ImportRun (or, for import_justices_csv, a literal ImportSource.SEED.value with no ImportRun at all), so a rule_based and an llm_corrective run — or a seed import and a corpus import — are separately distinguishable at the gate"
    - "A writer whose only reachable authority state is gap-fill (parse.py's source_docket, kept behind its pre-existing 'only if currently NULL' guard for a hard source-inspection test reason; import_convokit's name-provenance prefill, gated by its own has_any_part check) is still routed through the real gate and still gets its own named D-24 test — proving the writer's OWN reachable behavior rather than a scenario it structurally cannot reach"
    - "Explicit, unrolled per-field gate calls (not a loop over a tuple of fields) when an acceptance criterion requires a literal source-text count of the gate function's call sites — a loop satisfies the runtime behavior but not a grep-based acceptance check counting occurrences of the call expression itself"

key-files:
  created:
    - pipeline/tests/test_gated_column_writers.py
  modified:
    - pipeline/commands/resolve.py
    - pipeline/commands/parse.py
    - pipeline/commands/import_justices_csv.py
    - pipeline/tests/test_resolve.py
    - pipeline/tests/test_parse.py
    - pipeline/tests/test_import_justices_csv.py

key-decisions:
  - "parse.py Block D (source_docket) keeps its exact pre-existing conditional structure — including the literal Python expression `argument_row.source_docket is None` — because a pre-existing source-inspection regression test (test_parse_docket_fill_uses_pair_precheck_and_named_race_classification) asserts that exact substring is present in _run_parse_inner's source. This means the source_docket writer can only ever reach the gate's gap-fill path, never REJECT_AND_RECORD, through its real call site — documented explicitly in both the code and the D-24 test rather than silently narrowed."
  - "parse.py Blocks A (argued_date) and B (case_name) have NO such outer null-guard in the pre-existing code, so removing their WHERE-clause .is_(None) predicates and routing through the gate gives them the FULL disagreement-detection path (gap-fill AND reject-and-record), matching the plan's <behavior> bullets for those two fields specifically."
  - "import_justices_csv.py's four gate calls are four explicit, unrolled call expressions rather than a loop over (field, value) tuples — the plan's acceptance criterion requires the literal string 'apply_person_value_change(' to appear at least 4 times in the file; a loop produces the correct runtime behavior but only one literal occurrence, which would fail that grep."
  - "The D-24 gate module tests each writer's ACTUALLY REACHABLE authority states, not a fixed template of 'higher authority always rejects.' Two writers (parse.py's source_docket, import_convokit's name-provenance prefill) are structurally gap-fill-only by design from prior phases/this-plan's own literal-source constraint — their D-24 tests prove real-writer gap-fill correctness (write + zero discrepancy) instead of a REJECT_AND_RECORD scenario neither writer's call site can ever produce. This is stated explicitly in each test's own docstring rather than silently substituting a misleading assertion."

requirements-completed: [IMPORT-05]

coverage:
  - id: D1
    description: "resolve.py's bulk ArgumentParticipant.person_id UPDATE is replaced by a per-row apply_participant_value_change call; the Utterance.person_id bulk UPDATE stays deliberately ungated (PD-19, annotated) and still runs"
    requirement: IMPORT-05
    verification:
      - kind: integration
        ref: "pipeline/tests/test_resolve.py::test_resolve_alias_hit_on_null_person_id_writes_no_discrepancy, ::test_resolve_alias_hit_operator_edited_participant_survives, ::test_resolve_alias_hit_matching_existing_person_id_no_discrepancy, ::test_resolve_utterance_bulk_update_still_runs, ::test_resolve_n_labels_issues_gate_calls_not_bulk_statement, ::test_resolve_outcome_gate_unchanged_paused_on_miss_completed_on_hit"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_gated_column_writers.py::test_resolve_writer_rejects_lower_authority_person_id"
        status: pass
    human_judgment: false
  - id: D2
    description: "parse.py's argued_date, lead-case case_name, and source_docket writes route through apply_argument_value_change/apply_case_value_change with the run's own declared source/method; the previously unconditional lead-Case case_name overwrite is gone"
    requirement: IMPORT-05
    verification:
      - kind: integration
        ref: "pipeline/tests/test_parse.py::test_argued_date_gap_fill_writes_no_discrepancy, ::test_argued_date_disagreement_rejected_and_recorded_rule_based, ::test_argued_date_disagreement_records_llm_corrective_method, ::test_case_name_disagreement_no_longer_overwrites_corpus_value, ::test_seeded_participant_carries_pdf_pipeline_source_and_method"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_gated_column_writers.py::test_parse_argued_date_writer_rejects_lower_authority, ::test_parse_case_name_writer_rejects_lower_authority, ::test_parse_source_docket_writer_gap_fills_into_null_column"
        status: pass
    human_judgment: false
  - id: D3
    description: "import_justices_csv.py's blank-only Person name-part prefill routes through apply_person_value_change with incoming_source=seed; a fresh justice seed still produces zero value_discrepancy rows and idempotent reruns create no new discrepancies"
    requirement: IMPORT-05
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_justices_csv.py::test_rerun_upgrade_fills_all_blank_name_parts, ::test_rerun_last_name_operator_edited_to_different_value_survives, ::test_seed_idempotent_second_run_creates_no_new_discrepancies, ::test_rerun_preserves_operator_edited_parts_blank_only_prefill (updated fixture, see Deviations)"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_gated_column_writers.py::test_import_justices_csv_writer_rejects_lower_authority_last_name"
        status: pass
    human_judgment: false
  - id: D4
    description: "The D-24 executable behavioral gate (test_gated_column_writers.py) exercises real writes against a real database for every converted writer plus import_convokit's corpus reconcile pass and name-provenance prefill, and includes a falsifiability control (a direct ungated UPDATE) proving the gate's assertions are content-dependent — demonstrated by hand for resolve.py's writer"
    requirement: IMPORT-05
    verification:
      - kind: integration
        ref: "pipeline/tests/test_gated_column_writers.py (8 tests: corpus reconcile, resolve.py, parse.py x3, import_justices_csv, import_convokit name-provenance, control)"
        status: pass
      - kind: other
        ref: "manual: resolve.py's _apply_resolved_person_ids temporarily reverted to a direct update(ArgumentParticipant).values(person_id=...) statement; test_resolve_writer_rejects_lower_authority_person_id failed as expected (AssertionError: operator assignment must survive byte-identical); writer restored via file backup/diff-verified-identical; full test_gated_column_writers.py suite re-run green afterward"
        status: pass
    human_judgment: false

duration: 130min
completed: 2026-08-26
status: complete
---

# Phase 50 Plan 06: The D-22 Delegation Sweep's Remaining Three Writers, Closed With an Executable D-24 Gate Summary

**resolve.py, parse.py, and import_justices_csv.py now delegate every gated-column write to `api.services.admin_review`'s authority gates, and SC-4 closes with an 8-test real-writer behavioral gate module — not a source-text grep — including a hand-verified falsifiability demonstration.**

## Performance

- **Duration:** ~130 min
- **Tasks:** 3 (resolve.py; parse.py; import_justices_csv.py + the D-24 gate)
- **Files modified:** 7 (1 created, 6 modified)

## Accomplishments

- `resolve.py`'s Step 5 bulk `ArgumentParticipant.person_id` UPDATE is now `_apply_resolved_person_ids`, a per-row `apply_participant_value_change` gate call — an operator's own reassignment survives a disagreeing alias HIT instead of being silently overwritten (T-50-21). The `Utterance.person_id` bulk UPDATE is deliberately kept ungated and annotated (PD-19, no authority column to arbitrate against).
- `parse.py`'s `argued_date`/`case_name`/`source_docket` cover-metadata writes now go through `apply_argument_value_change`/`apply_case_value_change`, carrying the parse run's own declared `source`/`method` — the unconditional lead-`Case.case_name` overwrite is gone (T-50-20); a PDF cover extraction can no longer clobber a corpus- or operator-authored case name. Newly seeded `ArgumentParticipant` rows carry `source=pdf_pipeline` and the run's method (PD-20).
- `import_justices_csv.py`'s four blank-only `Person` name-part assignments are now four explicit `apply_person_value_change` calls (`incoming_source=seed`, ranked with `corpus` per `authority_rank` rule 3) — the common blank-fill case is unchanged in effect (PD-13 gap-fill), and an operator-edited part now genuinely refuses a disagreeing CSV value and records a discrepancy, rather than relying on "the column happens to be non-`None`" as an implicit (and incomplete) authority signal.
- `pipeline/tests/test_gated_column_writers.py` (new): the D-24 executable behavioral gate. 8 named test functions — one per covered writer (corpus reconcile pass, resolve.py, parse.py's argued_date/case_name/source_docket, import_justices_csv, import_convokit's name-provenance prefill) plus a falsifiability control that performs a direct ungated `UPDATE` and asserts it DOES change the value and records NO discrepancy. Verified by hand that reverting a real writer (resolve.py's `_apply_resolved_person_ids`) to a direct UPDATE makes its named test fail — see Verification below.
- 23 new tests across `test_resolve.py` (+6), `test_parse.py` (+5), `test_import_justices_csv.py` (+4 new, 1 fixture updated), `test_gated_column_writers.py` (+8, new file). Full suite: 1618 passed, 5 xfailed, 0 failed (baseline was 1596/5/0).

## Task Commits

Each task was committed atomically:

1. **Task 1: resolve.py — the bulk person_id UPDATE becomes a per-row gate call** — `68d3b4ca4` (feat)
2. **Task 2: parse.py — cover-metadata writes route through the Argument and Case gates** — `9d9ed4f83` (feat)
3. **Task 3: import_justices_csv delegation, and the D-24 executable behavioral gate** — `1439c37fc` (feat)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS update)

## Files Created/Modified

- `pipeline/commands/resolve.py` — `_apply_resolved_person_ids` (new helper), Step 5 rewired to call it, PD-19 comment on the ungated `Utterance` bulk UPDATE
- `pipeline/commands/parse.py` — `_write_cover_metadata_through_gate` (new helper, Blocks A/B); Block D's write call swapped for `apply_argument_value_change` in place (collision check/`IntegrityError` handling untouched); `ArgumentParticipant` seeding stamps `source`/`method`
- `pipeline/commands/import_justices_csv.py` — four explicit `apply_person_value_change` calls replacing the blank-only assignments; PD-20 comment on the ungated CREATE branch
- `pipeline/tests/test_resolve.py` — 6 new DB-backed integration tests
- `pipeline/tests/test_parse.py` — 5 new DB-backed integration tests
- `pipeline/tests/test_import_justices_csv.py` — 4 new tests; one pre-existing test's fixture updated (see Deviations)
- `pipeline/tests/test_gated_column_writers.py` (new) — the D-24 gate module, 8 tests

## Decisions Made

- **parse.py's Block D (`source_docket`) keeps its exact pre-existing "only if currently NULL" gate**, including the literal Python conditional a pre-existing source-inspection test asserts verbatim (`test_parse_docket_fill_uses_pair_precheck_and_named_race_classification` checks `"argument_row.source_docket is None" in inspect.getsource(_run_parse_inner)`). This means `source_docket`'s write can only ever reach the gate's gap-fill path in production — never `REJECT_AND_RECORD` — which is documented explicitly in the code, the D-24 test's own docstring, and this summary rather than silently narrowed or misrepresented as fully gated.
- **parse.py's Blocks A (`argued_date`) and B (`case_name`) have no such outer guard**, so they get the FULL gate treatment (gap-fill AND reject-and-record), matching the plan's `<behavior>` bullets exactly.
- **`import_justices_csv.py`'s four gate calls are unrolled, not looped** — the plan's acceptance criterion requires the literal substring `apply_person_value_change(` to appear at least 4 times in the file; a `for` loop over `(field, value)` tuples produces identical runtime behavior but only one literal call-site occurrence, which fails that specific grep-based check.
- **The D-24 gate module tests each writer's actually-reachable authority states**, not a uniform template. Two writers (`parse.py`'s `source_docket`, `import_convokit`'s name-provenance prefill) are structurally gap-fill-only by design (one from this plan's own literal-source constraint, one from a prior-phase `has_any_part` guard documented in that function's own docstring) — their D-24 tests prove real-writer gap-fill correctness instead of asserting a `REJECT_AND_RECORD` scenario neither call site can ever produce.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug / test-fixture correction] `test_rerun_preserves_operator_edited_parts_blank_only_prefill` no longer represented a coherent state under the new authority model**
- **Found during:** Task 3, running `pipeline/tests/test_import_justices_csv.py` after converting the four blank-only assignments to gate calls.
- **Issue:** The pre-existing fixture set `Person.first_name = "OperatorEdited"` (a non-`None` value) with NO `review_state` set (defaulting to `UNREVIEWED`), and left `middle_name`/`last_name` blank. Under the OLD blank-only-prefill writer, ANY non-`None` column value was implicitly protected regardless of provenance — this fixture's `first_name` survived purely because it wasn't `None`. Under the new gate, protection is carried by `review_state` (D-22: "operator authority is carried entirely by review_state," not by a bare non-`None` value). With `review_state=UNREVIEWED`, `first_name`'s existing authority reads as `UNKNOWN` — strictly LOWER than the incoming `seed`-ranked CSV value's `CORPUS` rank — so the gate would `ACCEPT_AND_RECORD` (overwrite "OperatorEdited" with "Testcase" from the CSV), failing the test's core assertion that the value survives.
- **Fix:** Updated the fixture to set `review_state=ReviewState.OPERATOR_EDITED` on the `Person`, matching this same file's own `test_rerun_preserves_operator_review_state` precedent for representing genuine operator authority. This surfaced a SECOND, subtler issue: `review_state` is a single PERSON-level column, not per-field — once `first_name` was authored by an "operator," the gate reads ALL FOUR name parts on that row as `OPERATOR` authority (per `authority_rank`'s rule 1, which does not take a field argument), which ALSO blocked the CSV's legitimate blank-fill of `middle_name`/`last_name` (PD-13's gap-fill guard explicitly excludes `OPERATOR`-authority rows by design — see 50-02-SUMMARY.md's own documented deviation). The test's original assertions expected `middle_name`/`last_name` to be prefilled from blank — no longer achievable while `first_name` is simultaneously protected on the same row. Split the scenario: `middle_name`/`last_name` are now pre-populated in the fixture to match the CSV (a no-op, not a gap-fill), and a NEW dedicated test (`test_rerun_upgrade_fills_all_blank_name_parts`) covers the genuinely-blank-row prefill case on its own, `UNREVIEWED` fixture — satisfying the plan's own `<behavior>` bullet without conflating two authority states that can no longer coexist on one row under the new model.
- **Files modified:** `pipeline/tests/test_import_justices_csv.py`
- **Verification:** All 39 tests in the file pass; the updated test's docstring documents the reasoning inline; the new test's discrepancy-count assertion (`zero discrepancy rows` for an all-blank prefill) independently proves PD-13's gap-fill path still works correctly.
- **Committed in:** `1439c37fc` (Task 3 commit)

---

**Total deviations:** 1 (a test-fixture correction, not a production-code bug). **Impact:** The fixture change makes the test accurately represent operator authority under the new, plan-mandated authority model — it does not weaken any assertion; the protected value's survival is still asserted byte-for-byte, and the split-out blank-fill test adds coverage the original single test could not honestly provide once `first_name` was genuinely operator-protected. No scope creep — confined to the one file already in `files_modified`.

## Issues Encountered

None beyond the deviation documented above.

## Verification

- `./.venv/bin/python -m pytest pipeline/tests/test_resolve.py pipeline/tests/test_parse.py pipeline/tests/test_import_justices_csv.py pipeline/tests/test_gated_column_writers.py -q` — 68 passed, 3 xfailed (0 failed)
- `./.venv/bin/python -m pytest` (full suite, foreground) — **1618 passed, 5 xfailed, 0 failed** (baseline was 1596 passed, 5 xfailed, 0 failed — the +22 delta is this plan's new tests, zero regressions)
- **Falsifiability demonstration (required by the plan's own acceptance criteria):** `resolve.py`'s `_apply_resolved_person_ids` was temporarily reverted to a direct `update(ArgumentParticipant).values(person_id=...)` statement (backed up first via file copy). `test_gated_column_writers.py::test_resolve_writer_rejects_lower_authority_person_id` FAILED as expected (`AssertionError: operator assignment must survive byte-identical`), proving the gate module's assertions are genuinely content-dependent, not vacuously green. The writer was then restored from the backup and verified byte-identical via `diff` before re-running the full gate module green.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Every pipeline writer named by D-22's enumeration (`import_convokit`, `import_justices`, `parse.py`, `resolve.py`) now delegates to `api.services.admin_review`'s gates, plus the two ungated writers 50-05's research found that D-22's own enumeration did not name (`resolve.py`'s bulk `person_id` UPDATE, closed by this plan; `import_convokit`'s `_apply_extracted_name_provenance`, closed by plan 50-05).
- SC-4 is closed by an executable behavioral gate (`test_gated_column_writers.py`) plus a dispositioned inventory — plan 50-07 owns writing that inventory (the dispositioned write-path table extending 49-11's shape), which can now cite this plan's gate module and the two structurally-gap-fill-only writers (`parse.py`'s `source_docket`, `import_convokit`'s name-provenance prefill) as PROVEN-gap-fill-only, not merely asserted.
- No blockers for plan 50-07.

---
*Phase: 50-unified-import-path*
*Completed: 2026-08-26*

## Self-Check: PASSED

All created/modified files verified present on disk (`pipeline/commands/resolve.py`, `pipeline/commands/parse.py`, `pipeline/commands/import_justices_csv.py`, `pipeline/tests/test_resolve.py`, `pipeline/tests/test_parse.py`, `pipeline/tests/test_import_justices_csv.py`, `pipeline/tests/test_gated_column_writers.py`). All three task commit hashes (`68d3b4ca4`, `9d9ed4f83`, `1439c37fc`) verified present in git log. All plan-level `<acceptance_criteria>` re-verified passing: `_apply_resolved_person_ids(` and `apply_participant_value_change(` present in resolve.py; zero `update(ArgumentParticipant)` statements set `person_id=`; `update(Utterance)` count ≥1; `apply_argument_value_change(`/`apply_case_value_change(` present in parse.py; zero `update(Case)`/`update(Argument)` statements set `case_name=`/`argued_date=`/`source_docket=`; `cover_metadata=cover_meta_json` count is 1; `ArgumentParticipant(` construction includes `source=`/`method=`; `apply_person_value_change(` count is 4 in import_justices_csv.py; zero direct `person.first_name|middle_name|last_name|name_suffix =` assignments; `test_gated_column_writers.py` exists with 8 test functions (≥6 required). Full suite re-run in foreground: 1618 passed, 5 xfailed, 0 failed.
