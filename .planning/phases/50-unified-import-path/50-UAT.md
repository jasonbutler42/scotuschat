---
status: complete
phase: 50-unified-import-path
source: 50-01-SUMMARY.md, 50-02-SUMMARY.md, 50-03-SUMMARY.md, 50-04-SUMMARY.md, 50-05-SUMMARY.md, 50-06-SUMMARY.md, 50-07-SUMMARY.md
started: 2026-08-27T02:06:11Z
updated: 2026-08-27T12:09:57Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running API/app process. From a clean start, `alembic upgrade head` applies migration 0030 without error, the FastAPI server boots, the SvelteKit app boots, and a primary read (an argument page or /admin/review) returns live data.
result: pass
source: live-verified (2026-08-26 session)
observed: |
  alembic current/heads both 0030; `alembic upgrade head` a clean no-op. All six
  migration-0030 columns present (arguments.source/method, cases.source/method,
  import_run.content_digest, argument_participants.oyez_speaker_id). uvicorn booted
  clean, /health 200, /openapi.json 200. SvelteKit dev booted; /cases 200 and
  /cases/archawski-v-hanioti redirected to its argument page and rendered 334KB of
  live data.
coverage_id: injected (migration 0030 shipped this phase)

### 2. D-09 live double-import diff + operator-edit survival
expected: Live walkthrough on the dev DB: reset_to_fixture -> corpus import -> snapshot all eight affected tables -> byte-identical re-import -> diff shows zero new rows and zero changed column values; then edit a value as operator -> re-import with a disagreeing corpus value -> the operator value survives and a value_discrepancy row is recorded.
result: issue
resolution: "Both gaps (G-50-2a, G-50-2b) FIXED 2026-08-27; re-verified live — an operator case_name edit now holds source=operator across three consecutive re-imports, and D-09's byte-identical invariant still holds across all eight tables."
source: live-verified (2026-08-26 session)
reported: "D-09 first half PASSES: reset_to_fixture -> re-import of all four fixtures -> snapshot diff was byte-identical across all eight tables (0 new rows, 0 changed values). Second half FAILS on provenance: the operator value survives, but operator AUTHORITY does not."
severity: major
observed: |
  PASS legs: byte-identical double-import proven live (snap A == snap B, all 8
  tables). admin_jobs stayed at 0 rows (D-14/D-19). Published fixture 18897 logged
  "1 published writes skipped" (D-08). Lazy step=reconcile run created only when
  there was something to record (D-06). --dry-run predicted the real pass exactly
  (1 rejected / 1 recorded both times) and was labelled DRY RUN (D-28).
  FAIL legs: two defects, see Gaps G-50-2a and G-50-2b.
coverage_id: 50-01 D4, 50-05 D8 (WINDOWS.md #31)

### 3. /admin/review argument- and case-level discrepancy render
expected: An argument whose own value, or whose lead case's value, disagrees shows a Discrepancy badge on its collapsed /admin/review row and a stored/incoming detail block at the top of its expanded panel, styled identically to a participant-level discrepancy. No truncation of a discrepancy value at 1280px or at narrow viewports.
result: pass
source: live-verified (2026-08-26 session, Playwright)
observed: |
  Discrepancy badge renders on the collapsed row beside the case name for all three
  queued arguments (argument-level and lead-case-level). Expanded panel leads with
  the stored/incoming block, styled identically to the participant-level treatment.
  A two-field case renders both pairs. At 1280x900 no truncation; at 390x844 no text
  clipping (scrollWidth == clientWidth) and no page-level horizontal scroll.
  NOTE: the panel faithfully renders whatever provenance the row carries -- which is
  how G-50-2a is visible in the UI as "(corpus/direct)" on an operator-typed value.
  That is a data defect, not a render defect; the render leg passes.
coverage_id: 50-04 D1 (WINDOWS.md #30)

### 4. Argument-scoped Approve action end to end
expected: A CANDIDATE argument's expanded /admin/review panel shows 'Approve — move to Draft'. Clicking it posts to the argument-scoped approve route, the row's status then reads Draft, the Approve button is gone, the active tab/filter survives the redirect, and the argument can then be published.
result: issue
resolution: "G-50-4a FIXED 2026-08-27; re-verified live — the post-approve URL keeps all four filter axes and the Candidate filter stays pressed."
source: live-verified (2026-08-26 session, Playwright)
reported: "Approve itself works end to end, but the operator's tab and status filter are dropped on the post-approve redirect -- the exact leg WINDOWS.md #30 flagged."
severity: minor
observed: |
  PASS legs: 'Approve -- move to Draft' present on CANDIDATE rows only; clicking it
  moved the row Candidate -> Draft; the button disappeared post-transition; it is the
  only new per-argument action. Candidate -> Draft -> Published proven end to end
  (argument 1814 published 200). Argument 1813 was correctly refused with
  uncertain_tier_blocked (25 unresolved speakers) -- the documented D-14/D-17 gate,
  not a defect.
  FAIL leg: filter/tab survival -- see Gap G-50-4a.
coverage_id: 50-04 D2 (WINDOWS.md #30)

### 5. Migration 0030 adds six nullable columns (oyez_speaker_id, content_digest, Argument/Case source+method) with no backfill; ORM models mirror them
expected: Migration 0030 adds six nullable columns (oyez_speaker_id, content_digest, Argument/Case source+method) with no backfill; ORM models mirror them
result: pass
source: automated
coverage_id: 50-01 D1
requirement: IMPORT-05
verification: api/tests/test_review_state_schema.py, pipeline/tests/test_import_run.py; alembic upgrade head / downgrade -1 / upgrade head round-trip (dev + scotus_test)

### 6. api/domain/content_digest.py is a pure, ORM-free, frozen digest contract covering every Task 2 behavior bullet
expected: api/domain/content_digest.py is a pure, ORM-free, frozen digest contract covering every Task 2 behavior bullet
result: pass
source: automated
coverage_id: 50-01 D2
requirement: IMPORT-05
verification: pipeline/tests/test_content_digest.py (12 tests, zero skips with no DATABASE_URL/TEST_DATABASE_URL set)

### 7. A fresh corpus import of one conversation creates exactly one step=parse import_run row (source=corpus, method=direct, pdf_path/pdf_url/prompt_version NULL) and zero admin_job rows
expected: A fresh corpus import of one conversation creates exactly one step=parse import_run row (source=corpus, method=direct, pdf_path/pdf_url/prompt_version NULL) and zero admin_job rows
result: pass
source: automated
coverage_id: 50-01 D3
requirement: IMPORT-01
verification: pipeline/tests/test_import_convokit_adminjob.py::test_fresh_corpus_import_creates_zero_admin_job_rows, ::test_argument_status_is_candidate_with_no_resolved_at

### 8. Every ArgumentParticipant row the corpus importer writes carries a non-NULL oyez_speaker_id equal to the resolved ConvoKit speaker id
expected: Every ArgumentParticipant row the corpus importer writes carries a non-NULL oyez_speaker_id equal to the resolved ConvoKit speaker id
result: pass
source: automated
coverage_id: 50-01 D5
requirement: IMPORT-05
verification: pipeline/tests/test_import_convokit_reimport_tracer.py::test_every_participant_row_has_non_null_oyez_speaker_id

### 9. approve_argument moves a jobless corpus argument CANDIDATE->DRAFT with resolved_at stamped; publish_argument's non-overridable gate is satisfied
expected: approve_argument moves a jobless corpus argument CANDIDATE->DRAFT with resolved_at stamped; publish_argument's non-overridable gate is satisfied
result: pass
source: automated
coverage_id: 50-01 D6
requirement: IMPORT-03
verification: pipeline/tests/test_import_convokit_adminjob.py::test_jobless_corpus_argument_is_reachable_and_approvable

### 10. reset_to_fixture drives all four reference states (Complexity/Draft/Published/Mid-pipeline) with zero AdminJob involvement anywhere in its body
expected: reset_to_fixture drives all four reference states (Complexity/Draft/Published/Mid-pipeline) with zero AdminJob involvement anywhere in its body
result: pass
source: automated
coverage_id: 50-01 D7
requirement: IMPORT-03
verification: api/tests/test_admin_dev_routes.py::test_reset_realizes_state_variety, ::test_reset_response_reports_realized_states, ::test_reset_wipes_and_reseeds_fixtures

### 11. apply_argument_value_change and apply_case_value_change exist as true peers of apply_participant_value_change/apply_person_value_change, both routing every decision through the single api.domain.authority.decide_write — no second ladder implementation anywhere
expected: apply_argument_value_change and apply_case_value_change exist as true peers of apply_participant_value_change/apply_person_value_change, both routing every decision through the single api.domain.authority.decide_write — no second ladder implementation anywhere
result: pass
source: automated
coverage_id: 50-02 D1
requirement: IMPORT-05
verification: api/tests/test_argument_authority_gate.py (22 tests: 11 <behavior> bullets x Argument/Case); grep -c 'decide_write(' api/services/admin_review.py == 4; grep -rn 'def authority_rank|def decide_write' --include=*.py . | wc -l == 2

### 12. Equal-rank disagreement (including NULL-provenance fail-closed) is always REJECT_AND_RECORD except the OPERATOR/OPERATOR carve-out; a blank incoming value against a populated stored value is a no-opinion no-op; a blank stored value receiving a non-blank incoming value is a gap-fill (write, no record) in all four gate functions
expected: Equal-rank disagreement (including NULL-provenance fail-closed) is always REJECT_AND_RECORD except the OPERATOR/OPERATOR carve-out; a blank incoming value against a populated stored value is a no-opinion no-op; a blank stored value receiving a non-blank incoming value is a gap-fill (write, no record) in all four gate functions
result: pass
source: automated
coverage_id: 50-02 D2
requirement: IMPORT-05
verification: api/tests/test_argument_authority_gate.py::test_argument_null_provenance_populated_value_fails_closed_on_differing_incoming, ::test_case_null_provenance_populated_value_fails_closed_on_differing_incoming, ::test_argument_blank_incoming_against_populated_stored_is_no_opinion, ::test_argument_blank_stored_receiving_non_blank_incoming_is_gap_fill_no_discrepancy; api/tests/test_authority_matrix.py::test_apply_participant_value_change_person_id_null_gap_fill_accepts_no_discrepancy, ::test_apply_person_value_change_blank_name_parts_gap_fill_accepts_no_discrepancy

### 13. An open value_discrepancy on an argument's own row (target_type=argument) or its lead case (target_type=case) pulls the argument into /admin/review exactly once, carried on argument_discrepancies, and get_review_queue_stats's count agrees with the list
expected: An open value_discrepancy on an argument's own row (target_type=argument) or its lead case (target_type=case) pulls the argument into /admin/review exactly once, carried on argument_discrepancies, and get_review_queue_stats's count agrees with the list
result: pass
source: automated
coverage_id: 50-02 D3
requirement: IMPORT-05
verification: api/tests/test_admin_review_service.py::test_argument_level_discrepancy_alone_includes_argument_once_with_detail, ::test_lead_case_discrepancy_alone_includes_argument_once_with_detail, ::test_argument_satisfying_participant_leg_and_argument_leg_appears_once, ::test_stats_argument_count_matches_list_count_across_participant_argument_and_both_legs

### 14. The full regression suite (existing apply_participant_value_change/apply_person_value_change behavior, review-queue tests, everything else in the repo) stays green with the PD-13 change applied — no test needed editing to accommodate PD-13 because the scope guard avoided the flip in the first place
expected: The full regression suite (existing apply_participant_value_change/apply_person_value_change behavior, review-queue tests, everything else in the repo) stays green with the PD-13 change applied — no test needed editing to accommodate PD-13 because the scope guard avoided the flip in the first place
result: pass
source: automated
coverage_id: 50-02 D4
requirement: IMPORT-05
verification: ./.venv/bin/python -m pytest -q (foreground, full run)

### 15. POST /api/admin/arguments/{argument_id}/approve exists, inherits router-level auth (no per-route dependency), returns 404/422/200 in the documented order, and an end-to-end approve-then-publish of a jobless CANDIDATE argument succeeds with admin_jobs row count unchanged
expected: POST /api/admin/arguments/{argument_id}/approve exists, inherits router-level auth (no per-route dependency), returns 404/422/200 in the documented order, and an end-to-end approve-then-publish of a jobless CANDIDATE argument succeeds with admin_jobs row count unchanged
result: pass
source: automated
coverage_id: 50-03 D1
requirement: IMPORT-03
verification: api/tests/test_admin_arguments_routes.py::test_approve_argument_wrong_token_returns_401, ::test_approve_argument_404_for_unknown_id, ::test_approve_argument_candidate_returns_200_and_stamps_resolved_at, ::test_approve_argument_draft_returns_422, ::test_approve_argument_published_returns_422, ::test_approve_then_publish_jobless_candidate_argument_returns_200_from_both

### 16. update_argument and update_argument_metadata stamp Argument.source=operator/method=manual and lead Case.source=operator/method=manual on the fields they write, proved by a round-trip where a disagreeing corpus write via apply_argument_value_change is REJECT_AND_RECORD against the operator-stamped value
expected: update_argument and update_argument_metadata stamp Argument.source=operator/method=manual and lead Case.source=operator/method=manual on the fields they write, proved by a round-trip where a disagreeing corpus write via apply_argument_value_change is REJECT_AND_RECORD against the operator-stamped value
result: pass
source: automated
coverage_id: 50-03 D2
requirement: IMPORT-05
verification: api/tests/test_admin_arguments_service.py::test_update_argument_stamps_operator_provenance_on_argued_date_write, ::test_update_argument_stamps_case_provenance_only_on_case_name_write, ::test_update_argument_metadata_stamps_operator_provenance_on_question_number_write, ::test_update_argument_metadata_stamps_operator_provenance_on_source_docket_write, ::test_update_argument_call_with_no_fields_leaves_provenance_unchanged, ::test_operator_stamped_argument_value_rejects_disagreeing_corpus_write

### 17. delete_argument's gate is a single published-only refusal — CANDIDATE, DRAFT, and UNPUBLISHED all delete; PUBLISHED is the only refusal
expected: delete_argument's gate is a single published-only refusal — CANDIDATE, DRAFT, and UNPUBLISHED all delete; PUBLISHED is the only refusal
result: pass
source: automated
coverage_id: 50-03 D3
requirement: IMPORT-03
verification: api/tests/test_admin_arguments_service.py::test_delete_argument_gate_keys_on_published, ::test_delete_argument_returns_true_for_unpublished, ::test_delete_argument_returns_true_for_pipeline_legacy_status, ::test_delete_argument_returns_true_for_candidate, ::test_delete_argument_returns_false_for_published; api/tests/test_admin_arguments_routes.py::test_delete_argument_returns_409_for_published, ::test_delete_argument_returns_200_for_unpublished_and_candidate

### 18. Deleting an argument carrying value_discrepancy rows at all three scopes (argument, exclusively-led case, participant) succeeds with no ForeignKeyViolation and leaves zero rows for those targets; a different argument's participant discrepancy, a person-scoped discrepancy, and a shared-lead-case discrepancy all survive untouched
expected: Deleting an argument carrying value_discrepancy rows at all three scopes (argument, exclusively-led case, participant) succeeds with no ForeignKeyViolation and leaves zero rows for those targets; a different argument's participant discrepancy, a person-scoped discrepancy, and a shared-lead-case discrepancy all survive untouched
result: pass
source: automated
coverage_id: 50-03 D4
requirement: IMPORT-05
verification: api/tests/test_admin_arguments_service.py::test_delete_argument_carrying_all_three_discrepancy_scopes_at_once_succeeds, ::test_delete_argument_with_argument_scoped_discrepancy_succeeds_and_leaves_zero_rows, ::test_delete_argument_with_participant_scoped_discrepancy_succeeds_and_leaves_zero_rows, ::test_delete_argument_with_import_run_referencing_discrepancy_raises_no_fk_violation, ::test_delete_argument_does_not_delete_other_arguments_participant_or_person_discrepancies, ::test_delete_argument_does_not_delete_shared_lead_case_discrepancy_of_another_argument

### 19. No new class attribute, style block, media query, or truncation is introduced on the page; the full regression suite stays green
expected: No new class attribute, style block, media query, or truncation is introduced on the page; the full regression suite stays green
result: pass
source: automated
coverage_id: 50-04 D3
requirement: IMPORT-05
verification: grep -c 'class=' / 'text-overflow' / '@media' == 0 (test_no_class_attribute_anywhere_inline_styles_only, test_no_truncation_or_media_query_introduced_on_the_review_page); npx svelte-check --threshold error == 0 errors; ./.venv/bin/python -m pytest -q == 1561 passed, 5 xfailed, 0 failed (was 1554/5/0; +7 is exactly the new contract-test assertions, zero regressions)

### 20. The D-02 field walk (Argument.argued_date/question_number/source_docket, lead Case.case_name/docket_number, each paired participant's person_id/side/descriptor, each paired participant's Person name-parts) runs through the Phase 49/50-02 authority gates on every reconcile pass, in PD-14's fixed order
expected: The D-02 field walk (Argument.argued_date/question_number/source_docket, lead Case.case_name/docket_number, each paired participant's person_id/side/descriptor, each paired participant's Person name-parts) runs through the Phase 49/50-02 authority gates on every reconcile pass, in PD-14's fixed order
result: pass
source: automated
coverage_id: 50-05 D1
requirement: IMPORT-05
verification: pipeline/tests/test_import_convokit_reconcile.py::test_identical_reimport_every_field_accept_or_no_opinion_zero_rows, ::test_corpus_value_differing_from_stored_corpus_value_rejected_and_recorded, ::test_corpus_value_differing_from_pdf_pipeline_value_accepted_and_restamped, ::test_operator_edited_participant_value_survives_reimport, ::test_operator_stamped_argued_date_survives_reimport, ::test_accepted_participant_overwrite_leaves_review_state_unchanged

### 21. D-04 participant pairing uses ArgumentParticipant.oyez_speaker_id only -- never raw_speaker_label, never a Person lookup; a stored row with NULL oyez_speaker_id or one the corpus no longer mentions is left entirely alone
expected: D-04 participant pairing uses ArgumentParticipant.oyez_speaker_id only -- never raw_speaker_label, never a Person lookup; a stored row with NULL oyez_speaker_id or one the corpus no longer mentions is left entirely alone
result: pass
source: automated
coverage_id: 50-05 D2
requirement: IMPORT-05
verification: pipeline/tests/test_import_convokit_reconcile.py::test_participant_paired_by_oyez_speaker_id_never_raw_label, ::test_participant_paired_by_oyez_speaker_id_survives_label_change, ::test_participant_with_null_oyez_speaker_id_never_paired_or_written, ::test_unmentioned_stored_participant_untouched_no_discrepancy, ::test_new_corpus_speaker_creates_new_participant_row

### 22. D-06's lazy step=reconcile ImportRun is minted only when a field genuinely needs to write or record -- a true no-op reconcile pass (byte-identical re-import) adds zero import_run rows, and every discrepancy from one pass shares the same run id
expected: D-06's lazy step=reconcile ImportRun is minted only when a field genuinely needs to write or record -- a true no-op reconcile pass (byte-identical re-import) adds zero import_run rows, and every discrepancy from one pass shares the same run id
result: pass
source: automated
coverage_id: 50-05 D3
requirement: IMPORT-04
verification: pipeline/tests/test_import_convokit_reconcile.py::test_no_op_pass_creates_zero_import_run_rows, ::test_lazy_reconcile_run_minted_once_and_reused_across_records, ::test_two_identical_reconcile_passes_over_disagreement_are_deterministic; pipeline/tests/test_import_convokit_reimport_tracer.py::test_double_import_is_byte_identical_across_all_eight_tables (still passing after this plan's field walk was added to the no-op path)

### 23. D-07's unconditional provenance restamp (source=corpus/method=direct) fires on every accepted overwrite, including a row that already carried a source, without flipping review_state
expected: D-07's unconditional provenance restamp (source=corpus/method=direct) fires on every accepted overwrite, including a row that already carried a source, without flipping review_state
result: pass
source: automated
coverage_id: 50-05 D4
requirement: IMPORT-05
verification: pipeline/tests/test_import_convokit_reconcile.py::test_corpus_value_differing_from_pdf_pipeline_value_accepted_and_restamped, ::test_accepted_participant_overwrite_leaves_review_state_unchanged, ::test_participant_paired_by_oyez_speaker_id_survives_label_change

### 24. D-08's PUBLISHED-argument freeze: the pass compares and records but writes zero value columns; published_writes_skipped increments exactly once per pass unconditionally
expected: D-08's PUBLISHED-argument freeze: the pass compares and records but writes zero value columns; published_writes_skipped increments exactly once per pass unconditionally
result: pass
source: automated
coverage_id: 50-05 D5
requirement: IMPORT-04
verification: pipeline/tests/test_import_convokit_reconcile.py::test_published_argument_records_disagreement_without_writing, ::test_published_argument_writes_skipped_even_with_no_disagreement, ::test_published_argument_utterance_replacement_skipped

### 25. D-10/D-11/D-13 whole-set utterance replacement: a changed transcript mints a NEW step=parse/COMPLETED run in the same transaction as its full row set, prior rows retained, person ids sourced from the POST-reconcile participant state, a mid-write failure leaves no zero-row run, and an empty-incoming-vs-non-empty-stored set is refused outright
expected: D-10/D-11/D-13 whole-set utterance replacement: a changed transcript mints a NEW step=parse/COMPLETED run in the same transaction as its full row set, prior rows retained, person ids sourced from the POST-reconcile participant state, a mid-write failure leaves no zero-row run, and an empty-incoming-vs-non-empty-stored set is refused outright
result: pass
source: automated
coverage_id: 50-05 D6
requirement: IMPORT-04
verification: pipeline/tests/test_import_convokit_reconcile.py::test_identical_utterance_set_produces_no_new_run_or_rows, ::test_changed_transcript_text_triggers_full_replacement_new_run, ::test_get_argument_with_utterances_returns_exactly_new_run_rows, ::test_operator_reassigned_participant_person_id_on_replacement_rows, ::test_forced_mid_write_failure_leaves_no_zero_row_parse_run, ::test_empty_incoming_against_nonempty_stored_refuses_replacement

### 26. --dry-run reports every decision (values accepted/rejected, discrepancies, utterance replacement) while touching zero rows across every affected table, using a separate prediction path that never calls a gate or api.domain.authority.decide_write outside dry-run mode; every printed summary block is labeled DRY RUN
expected: --dry-run reports every decision (values accepted/rejected, discrepancies, utterance replacement) while touching zero rows across every affected table, using a separate prediction path that never calls a gate or api.domain.authority.decide_write outside dry-run mode; every printed summary block is labeled DRY RUN
result: pass
source: automated
coverage_id: 50-05 D7
requirement: IMPORT-01
verification: pipeline/tests/test_import_convokit_reconcile.py::test_dry_run_disagreeing_argument_touches_zero_rows, ::test_dry_run_utterance_replacement_predicted_without_writing, ::test_decide_write_direct_call_unreachable_when_not_dry_run, ::test_dry_run_summary_labeled_distinctly, ::test_dry_run_flag_registered_on_cli

### 27. resolve.py's bulk ArgumentParticipant.person_id UPDATE is replaced by a per-row apply_participant_value_change call; the Utterance.person_id bulk UPDATE stays deliberately ungated (PD-19, annotated) and still runs
expected: resolve.py's bulk ArgumentParticipant.person_id UPDATE is replaced by a per-row apply_participant_value_change call; the Utterance.person_id bulk UPDATE stays deliberately ungated (PD-19, annotated) and still runs
result: pass
source: automated
coverage_id: 50-06 D1
requirement: IMPORT-05
verification: pipeline/tests/test_resolve.py::test_resolve_alias_hit_on_null_person_id_writes_no_discrepancy, ::test_resolve_alias_hit_operator_edited_participant_survives, ::test_resolve_alias_hit_matching_existing_person_id_no_discrepancy, ::test_resolve_utterance_bulk_update_still_runs, ::test_resolve_n_labels_issues_gate_calls_not_bulk_statement, ::test_resolve_outcome_gate_unchanged_paused_on_miss_completed_on_hit; pipeline/tests/test_gated_column_writers.py::test_resolve_writer_rejects_lower_authority_person_id

### 28. parse.py's argued_date, lead-case case_name, and source_docket writes route through apply_argument_value_change/apply_case_value_change with the run's own declared source/method; the previously unconditional lead-Case case_name overwrite is gone
expected: parse.py's argued_date, lead-case case_name, and source_docket writes route through apply_argument_value_change/apply_case_value_change with the run's own declared source/method; the previously unconditional lead-Case case_name overwrite is gone
result: pass
source: automated
coverage_id: 50-06 D2
requirement: IMPORT-05
verification: pipeline/tests/test_parse.py::test_argued_date_gap_fill_writes_no_discrepancy, ::test_argued_date_disagreement_rejected_and_recorded_rule_based, ::test_argued_date_disagreement_records_llm_corrective_method, ::test_case_name_disagreement_no_longer_overwrites_corpus_value, ::test_seeded_participant_carries_pdf_pipeline_source_and_method; pipeline/tests/test_gated_column_writers.py::test_parse_argued_date_writer_rejects_lower_authority, ::test_parse_case_name_writer_rejects_lower_authority, ::test_parse_source_docket_writer_gap_fills_into_null_column

### 29. import_justices_csv.py's blank-only Person name-part prefill routes through apply_person_value_change with incoming_source=seed; a fresh justice seed still produces zero value_discrepancy rows and idempotent reruns create no new discrepancies
expected: import_justices_csv.py's blank-only Person name-part prefill routes through apply_person_value_change with incoming_source=seed; a fresh justice seed still produces zero value_discrepancy rows and idempotent reruns create no new discrepancies
result: pass
source: automated
coverage_id: 50-06 D3
requirement: IMPORT-05
verification: pipeline/tests/test_import_justices_csv.py::test_rerun_upgrade_fills_all_blank_name_parts, ::test_rerun_last_name_operator_edited_to_different_value_survives, ::test_seed_idempotent_second_run_creates_no_new_discrepancies, ::test_rerun_preserves_operator_edited_parts_blank_only_prefill (updated fixture, see Deviations); pipeline/tests/test_gated_column_writers.py::test_import_justices_csv_writer_rejects_lower_authority_last_name

### 30. The D-24 executable behavioral gate (test_gated_column_writers.py) exercises real writes against a real database for every converted writer plus import_convokit's corpus reconcile pass and name-provenance prefill, and includes a falsifiability control (a direct ungated UPDATE) proving the gate's assertions are content-dependent — demonstrated by hand for resolve.py's writer
expected: The D-24 executable behavioral gate (test_gated_column_writers.py) exercises real writes against a real database for every converted writer plus import_convokit's corpus reconcile pass and name-provenance prefill, and includes a falsifiability control (a direct ungated UPDATE) proving the gate's assertions are content-dependent — demonstrated by hand for resolve.py's writer
result: pass
source: automated
coverage_id: 50-06 D4
requirement: IMPORT-05
verification: pipeline/tests/test_gated_column_writers.py (8 tests: corpus reconcile, resolve.py, parse.py x3, import_justices_csv, import_convokit name-provenance, control); manual: resolve.py's _apply_resolved_person_ids temporarily reverted to a direct update(ArgumentParticipant).values(person_id=...) statement; test_resolve_writer_rejects_lower_authority_person_id failed as expected (AssertionError: operator assignment must survive byte-identical); writer restored via file backup/diff-verified-identical; full test_gated_column_writers.py suite re-run green afterward

### 31. python -m pipeline prune-runs reclaims superseded ImportRun/Utterance rows deliberately and offline; the served run (api/services/arguments.py's exact MAX(ImportRun.id) select shape) is never a candidate; a run with an OPEN value_discrepancy row is refused under every flag combination; a run with only RESOLVED rows is refused by default and removed under --include-resolved-discrepancies; --dry-run reports without writing
expected: python -m pipeline prune-runs reclaims superseded ImportRun/Utterance rows deliberately and offline; the served run (api/services/arguments.py's exact MAX(ImportRun.id) select shape) is never a candidate; a run with an OPEN value_discrepancy row is refused under every flag combination; a run with only RESOLVED rows is refused by default and removed under --include-resolved-discrepancies; --dry-run reports without writing
result: pass
source: automated
coverage_id: 50-07 D1
requirement: IMPORT-04
verification: pipeline/tests/test_prune_runs.py (18 tests: single/three-run scenarios, get_argument_with_utterances parity, open/resolved discrepancy handling under every flag combination, reconcile-run pruning, dry-run totals parity, --all batch totals, FK delete ordering, zero-run no-op, unknown-argument-id ValueError, direct _prunable_run_ids unit coverage, CLI --help/no-flag)

### 32. The public-leak ban is extended to content_digest, oyez_speaker_id, argument_discrepancies, and PD-17's six reconcile batch-counter names, with the module's false-green-guard convention extended in the same pass (a genuine Pydantic-layer proof for argument_discrepancies, an honest ORM-layer proof for the two keys nothing yet exposes)
expected: The public-leak ban is extended to content_digest, oyez_speaker_id, argument_discrepancies, and PD-17's six reconcile batch-counter names, with the module's false-green-guard convention extended in the same pass (a genuine Pydantic-layer proof for argument_discrepancies, an honest ORM-layer proof for the two keys nothing yet exposes)
result: pass
source: automated
coverage_id: 50-07 D2
requirement: IMPORT-05
verification: api/tests/test_trust_public_leak_ban.py (parametrized Test 1 over every public-reachable model x BANNED_KEYS; test_review_queue_argument_item_does_declare_argument_discrepancies; test_content_digest_and_oyez_speaker_id_exist_at_the_orm_layer_not_yet_any_schema; test_banned_keys_include_phase_50_vocabulary; test_public_response_models_never_declare_reconcile_counter_names; test_public_frontend_pages_never_reference_reconcile_counter_names)

### 33. /admin/pipeline is honestly narrowed to PDF-only (D-19): a one-line page note points to /admin/arguments and /admin/review, and both is_corpus EXISTS-subquery derivation sites in admin_jobs.py carry a comment recording the corpus branch is unreachable by construction as of Phase 50, citing 999.11
expected: /admin/pipeline is honestly narrowed to PDF-only (D-19): a one-line page note points to /admin/arguments and /admin/review, and both is_corpus EXISTS-subquery derivation sites in admin_jobs.py carry a comment recording the corpus branch is unreachable by construction as of Phase 50, citing 999.11
result: pass
source: automated
coverage_id: 50-07 D3
requirement: IMPORT-03
verification: cd app && npx --no-install svelte-check --threshold error (0 errors); pipeline/tests/test_import_convokit_adminjob.py (fresh corpus import produces zero admin_job rows, pre-existing from plan 50-01, re-verified green here)

### 34. D-24's dispositioned writer inventory (50-WRITER-INVENTORY.md): 24 rows across four dispositions covering every writer that can reach a gated ArgumentParticipant/Person/Argument/Case column, naming the two writers D-22's enumeration missed (found+fixed by plans 50-05/50-06) and D-18's no-op closure, pairing plan 50-06's executable test_gated_column_writers.py gate
expected: D-24's dispositioned writer inventory (50-WRITER-INVENTORY.md): 24 rows across four dispositions covering every writer that can reach a gated ArgumentParticipant/Person/Argument/Case column, naming the two writers D-22's enumeration missed (found+fixed by plans 50-05/50-06) and D-18's no-op closure, pairing plan 50-06's executable test_gated_column_writers.py gate
result: pass
source: automated
coverage_id: 50-07 D4
requirement: IMPORT-05
verification: manual table-completeness check: `awk -F'|' 'NR>2 && NF>3 {if ($4~/^[[:space:]]*$/||$5~/^[[:space:]]*$/) print}' 50-WRITER-INVENTORY.md` prints nothing (no blank Disposition/Reason cell); 24 data rows counted via `grep -c '^| [0-9]* |'`

### 35. D-23's closure: deferred-items.md's Person-scoped Status:open line is flipped to closed, recording the operator's no-Person-level-published-lock answer with its three reasons, the date 2026-08-25, and a 50-CONTEXT.md citation, in the SAME commit as the writer inventory (Phase 40.1 lesson)
expected: D-23's closure: deferred-items.md's Person-scoped Status:open line is flipped to closed, recording the operator's no-Person-level-published-lock answer with its three reasons, the date 2026-08-25, and a 50-CONTEXT.md citation, in the SAME commit as the writer inventory (Phase 40.1 lesson)
result: pass
source: automated
coverage_id: 50-07 D5
requirement: IMPORT-05
verification: grep -q 'awaiting the operator' deferred-items.md (absent, confirmed); grep -rn 'Person-level published lock|person_published_lock' api/ app/src/ (zero hits — zero implementation); git log confirms both edits landed in commit ef3ec8bf8

## Summary

total: 35
passed: 33
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-50-2a
  status_note: FIXED 2026-08-27
  truth: "An operator edit to Case.case_name reaches OPERATOR authority, so a disagreeing corpus re-import is REJECT_AND_RECORD on authority grounds and the audit row attributes the stored value to the operator."
  status: resolved
  reason: "update_argument_metadata writes Case.case_name without calling _stamp_operator_provenance, while update_argument does. Live: case 733 edited via PATCH /api/admin/arguments/1813/metadata stayed source=corpus/method=direct; case 734 edited via PATCH /api/admin/arguments/1814 became source=operator/method=manual. Same column, same operator intent, two different authority outcomes. The value still survived the re-import, but only by the corpus==corpus equal-rank tie, and value_discrepancy row 16 misattributes the human's value as existing_source='corpus' -- which /admin/review then renders to the operator as '(corpus/direct)'."
  severity: major
  test: 2
  artifacts:
    - path: "api/services/admin_arguments.py"
      issue: "update_argument_metadata step (d), lines 1396-1404: the update(Case).values(case_name=...) write has no _stamp_operator_provenance(db, model=Case, row_id=lead_ca.case_id) companion. Compare update_argument at lines 648-673, which sets case_provenance_dirty and stamps."
  missing:
    - "Call _stamp_operator_provenance(db, model=Case, row_id=lead_ca.case_id) after the case_name write in update_argument_metadata."
    - "Regression test asserting both operator routes leave cases.source='operator' after a case_name edit."
  resolved_by: "api/services/admin_arguments.py — _stamp_operator_provenance on update_argument_metadata's lead-Case write"
  resolved_at: 2026-08-27
  fix: "Added the missing _stamp_operator_provenance(db, model=Case, row_id=lead_ca.case_id) after step (d)'s update(Case).values(case_name=...), matching update_argument's own case_name write. The three AsyncMock db.execute-sequence tests the docstring warns about are unaffected — none of them passes case_name, so the new call never fires for them (verified: 85 passed)."
  fix_tests:
    - "test_update_argument_metadata_stamps_case_provenance_on_case_name_write"
    - "test_both_operator_routes_onto_case_name_agree_on_authority — parity guard, asserts both routes land on AuthorityRank.OPERATOR"
  falsifiability: "Verified 2026-08-27 by removing the stamp call and confirming both tests fail (AuthorityRank.UNKNOWN != OPERATOR)."

- gap_id: G-50-2b
  status_note: FIXED 2026-08-27
  truth: "Operator authority on Argument/Case is durable -- once an operator edit is stamped, a corpus reconcile pass cannot silently demote the row below the OPERATOR rung."
  status: resolved
  reason: "_restamp_corpus_provenance is a ROW-level update (source=corpus/method=direct on the whole row) fired from a PER-FIELD decision. Argument and Case have no review_state column, so source is the only carrier of operator authority (per _stamp_operator_provenance's own docstring). Live proof: case 734 was stamped operator/manual; on re-import case_name was REJECT_AND_RECORD but the sibling docket_number agreed and returned ACCEPT, firing the row-level restamp -- reverting the whole row to corpus/direct. Discrepancy row 17 (first re-import) records existing_source='operator'; row 18 (second re-import, no further operator action) records existing_source='corpus'. Control case 736, where BOTH compare fields disagreed so neither returned ACCEPT, kept source=operator across the same re-import -- isolating the cause."
  severity: major
  test: 2
  artifacts:
    - path: "pipeline/commands/import_convokit.py"
      issue: "_restamp_corpus_provenance (lines 919-940) updates the entire row's source/method; call sites at 1053 (Argument), 1087 (Case), 1150/1169/1185 (ArgumentParticipant) fire it on a single field's ACCEPT decision."
  missing:
    - "Make provenance demotion field-aware, or suppress the restamp for a row that has any REJECT_AND_RECORD decision on the same pass."
    - "Test: operator-edit field A, leave field B agreeing, re-import, assert the row still reads source='operator' and the discrepancy row records existing_source='operator' on every subsequent pass."
  notes: "ArgumentParticipant and Person are NOT exposed -- their operator authority is carried by review_state, which this helper deliberately does not touch. Argument and Case are the two affected tables."
  resolved_by: "pipeline/commands/import_convokit.py — _row_should_restamp predicate + one restamp decision per row"
  resolved_at: 2026-08-27
  fix: "Added _row_should_restamp(decisions): a row is demoted to corpus/direct only when its COMPLETE compare-set walk accepted at least one write AND rejected nothing. All three call sites (Argument, Case, ArgumentParticipant) now accumulate per-field decisions across the whole walk and restamp once at the end, instead of firing per accepted field. Fail-closed in the same spirit as authority_rank rule 6: a row still holding an outranking stored value is never demoted."
  fix_tests:
    - "test_case_rejected_field_is_not_demoted_by_an_agreeing_sibling — the exact live scenario"
    - "test_case_operator_authority_is_durable_across_repeated_reimports — the row-18 symptom, 3 passes"
    - "test_argument_rejected_field_is_not_demoted_by_an_agreeing_sibling"
    - "test_participant_rejected_field_is_not_demoted_by_an_agreeing_sibling"
    - "test_case_clean_accepting_walk_still_restamps — over-correction guard, D-07 preserved"
    - "test_row_should_restamp_* — 3 unit tests on the predicate"
    - "test_every_restamp_call_site_is_gated_on_the_row_level_predicate — structural guard"
  falsifiability: "Verified 2026-08-27 by restoring the per-field restamp in the Case walk and confirming the two behavioral tests AND the structural guard fail; the structural guard was strengthened after a first version passed under the reverted code."

- gap_id: G-50-4a
  status_note: FIXED 2026-08-27
  truth: "Approving an argument from /admin/review preserves the operator's tab and status filter across the post-action redirect."
  status: resolved
  reason: "Live: with the Candidate filter active (URL ?tab=arguments&status=candidate), clicking Approve landed on /admin/review?/approve with the filter reset to All and all 5 rows showing. The approve action does redirect(303, url.pathname + url.search), but inside a SvelteKit form action url.search is the action query '?/approve', never the page's filter query -- because every form on the page declares a bare action=\"?/name\", which replaces the query string rather than extending it. The action's own docstring claims it 'Preserves the current filter/tab query string ... so approving does not silently drop the operator's tab and filter selection'; it does not."
  severity: minor
  test: 4
  artifacts:
    - path: "app/src/routes/admin/review/+page.server.ts"
      issue: "approve action line 257 (and confirm/confirmUnattributable/reflag at 214, 229, 241) redirect to url.pathname + url.search, which resolves to '?/approve' inside a form action."
    - path: "app/src/routes/admin/review/+page.svelte"
      issue: "All six forms (lines 561, 570, 583, 619, 667, 681) use action=\"?/name\", replacing the page query string. The filter/tab params never reach the action."
  missing:
    - "Carry tab/status into the form action (hidden inputs, or action={`?${$page.url.searchParams}&/approve`}) and redirect using those values."
    - "Test asserting the post-approve redirect URL retains tab and status."
  notes: "Pre-existing across all four review actions, not introduced by Phase 50 -- but Phase 50's approve action inherited it, and this is exactly the leg WINDOWS.md #30 named as unverified."
  resolved_by: "app/src/routes/admin/review/+page.svelte (actionUrl) + +page.server.ts (filterRedirect)"
  resolved_at: 2026-08-27
  fix: "Two halves. Client: a $derived filterQuery over all four axes (tab/status/tier/review_state) and an actionUrl(name) helper; all six forms now declare action={actionUrl('...')} instead of a bare action=\"?/name\", so the filter query actually reaches the server action. $derived rather than a const off `data` — each action redirects and the load re-runs, and a captured const would freeze the action URLs (this codebase's stale-prop-capture class). Server: a filterRedirect(url) helper strips SvelteKit's own action key (the param whose name starts with '/') so the redirect target is a clean linkable filter URL; all four actions now redirect through it."
  fix_tests:
    - "test_no_review_form_declares_a_bare_action_query — the defect shape itself"
    - "test_every_review_form_action_carries_the_live_filter_query"
    - "test_action_url_helper_builds_from_the_live_filter_state — asserts $derived, and all four axes"
    - "test_every_server_action_redirects_through_the_filter_preserving_helper"
    - "test_filter_redirect_strips_sveltekits_own_action_key"
    - "test_approve_form_posts_to_the_approve_action / _guarded_by_candidate_status_condition — updated to the new shape"
  fix_tests_caveat: "These are source-grep contract tests: they pin the SHAPE, not the runtime behaviour. Per this project's documented $state-proxy-vs-grep trap, a green grep test has masked a fully broken control on this very screen before. The behavioural proof is the live Playwright walkthrough below."
  live_verification: "2026-08-27, Playwright: with ?tab=arguments&status=candidate active, the approve form's action attribute read '?tab=arguments&status=candidate&/approve' and the post-approve URL was '?tab=arguments&status=candidate' with the Candidate filter still pressed (was '?/approve' with the filter reset to All). Re-checked with all four axes set (status+tier+review_state) — all preserved, no '&/approve' residue."
  live_verification_gap: "The People-tab confirm/reflag actions were NOT exercised live — no actionable People rows existed under the filters tried. They share the same actionUrl helper and the same filterRedirect, so they are covered by construction and by the contract tests, but not by a live click."
  falsifiability: "Verified 2026-08-27 by reverting each half independently: the client half alone fails 3 tests, the server half alone fails 1."
