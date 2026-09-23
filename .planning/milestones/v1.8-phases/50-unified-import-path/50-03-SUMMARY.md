---
phase: 50-unified-import-path
plan: 03
subsystem: api
tags: [argument-approve, delete-cascade, value-discrepancy, operator-provenance, authority-ladder]

requires:
  - phase: 50-unified-import-path
    plan: "01"
    provides: "approve_argument (the argument-scoped CANDIDATE->DRAFT service function); Argument.source/.method and Case.source/.method columns (migration 0030)"
  - phase: 50-unified-import-path
    plan: "02"
    provides: "apply_argument_value_change / apply_case_value_change — the two peer authority gates this plan's round-trip test proves against a stamp this plan produces"
provides:
  - "POST /api/admin/arguments/{argument_id}/approve — the HTTP surface for 50-01's approve_argument, making a jobless corpus argument publishable end to end (D-14)"
  - "_stamp_operator_provenance (api/services/admin_arguments.py) — the only writer that makes Argument/Case authority reach OPERATOR via authority_rank (PD-08)"
  - "delete_argument gate inverted to published-only (D-25/PD-11) with a value_discrepancy cascade step + a surviving-discrepancy import_run_id NULL-out (D-26)"
affects: [50-04, 50-05, 50-06, 50-07]

actuals:
  tokens: 19715
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Unconditional provenance-restamp helper (_stamp_operator_provenance), distinct from the existing conditional backfill-only precedent in admin_jobs.py — a second write to the same field re-stamps, matching D-07's 'describes where the CURRENT value came from' rule"
    - "Nullable-FK-clear-before-delete for a cascade's own referenced rows that must survive (value_discrepancy.import_run_id NULLed before ImportRun rows for THIS argument are deleted), mirroring the pre-existing AdminJob.argument_id NULL-out pattern in the same function"

key-files:
  created: []
  modified:
    - api/routers/admin.py
    - api/services/admin_arguments.py
    - app/src/routes/admin/arguments/[id]/+page.server.ts
    - app/src/routes/admin/arguments/[id]/+page.svelte
    - api/tests/test_admin_arguments_routes.py
    - api/tests/test_admin_arguments_service.py

key-decisions:
  - "Commits grouped by architectural layer (router, service, UI) rather than one commit per plan Task — the three tasks share the same three files so heavily (admin.py and admin_arguments.py are each touched by two tasks) that a true per-task split would require hunk-level patch surgery with no functional benefit; each commit message names which task(s) it covers"
  - "Found and fixed a real FK-orphaning gap in D-26's own cascade design during test-writing, not from the plan text: a surviving value_discrepancy row (target_type=person, or another argument's participant) can reference an ImportRun that belongs to THIS argument; deleting that ImportRun without first NULLing the reference raises ForeignKeyViolation against a row the cascade must preserve. Fixed with a new step mirroring the existing AdminJob.argument_id NULL-out pattern already in the same function."

requirements-completed: []

coverage:
  - id: D1
    description: "POST /api/admin/arguments/{argument_id}/approve exists, inherits router-level auth (no per-route dependency), returns 404/422/200 in the documented order, and an end-to-end approve-then-publish of a jobless CANDIDATE argument succeeds with admin_jobs row count unchanged"
    requirement: IMPORT-03
    verification:
      - kind: integration
        ref: "api/tests/test_admin_arguments_routes.py::test_approve_argument_wrong_token_returns_401, ::test_approve_argument_404_for_unknown_id, ::test_approve_argument_candidate_returns_200_and_stamps_resolved_at, ::test_approve_argument_draft_returns_422, ::test_approve_argument_published_returns_422, ::test_approve_then_publish_jobless_candidate_argument_returns_200_from_both"
        status: pass
    human_judgment: false
  - id: D2
    description: "update_argument and update_argument_metadata stamp Argument.source=operator/method=manual and lead Case.source=operator/method=manual on the fields they write, proved by a round-trip where a disagreeing corpus write via apply_argument_value_change is REJECT_AND_RECORD against the operator-stamped value"
    requirement: IMPORT-05
    verification:
      - kind: integration
        ref: "api/tests/test_admin_arguments_service.py::test_update_argument_stamps_operator_provenance_on_argued_date_write, ::test_update_argument_stamps_case_provenance_only_on_case_name_write, ::test_update_argument_metadata_stamps_operator_provenance_on_question_number_write, ::test_update_argument_metadata_stamps_operator_provenance_on_source_docket_write, ::test_update_argument_call_with_no_fields_leaves_provenance_unchanged, ::test_operator_stamped_argument_value_rejects_disagreeing_corpus_write"
        status: pass
    human_judgment: false
  - id: D3
    description: "delete_argument's gate is a single published-only refusal — CANDIDATE, DRAFT, and UNPUBLISHED all delete; PUBLISHED is the only refusal"
    requirement: IMPORT-03
    verification:
      - kind: integration
        ref: "api/tests/test_admin_arguments_service.py::test_delete_argument_gate_keys_on_published, ::test_delete_argument_returns_true_for_unpublished, ::test_delete_argument_returns_true_for_pipeline_legacy_status, ::test_delete_argument_returns_true_for_candidate, ::test_delete_argument_returns_false_for_published; api/tests/test_admin_arguments_routes.py::test_delete_argument_returns_409_for_published, ::test_delete_argument_returns_200_for_unpublished_and_candidate"
        status: pass
    human_judgment: false
  - id: D4
    description: "Deleting an argument carrying value_discrepancy rows at all three scopes (argument, exclusively-led case, participant) succeeds with no ForeignKeyViolation and leaves zero rows for those targets; a different argument's participant discrepancy, a person-scoped discrepancy, and a shared-lead-case discrepancy all survive untouched"
    requirement: IMPORT-05
    verification:
      - kind: integration
        ref: "api/tests/test_admin_arguments_service.py::test_delete_argument_carrying_all_three_discrepancy_scopes_at_once_succeeds, ::test_delete_argument_with_argument_scoped_discrepancy_succeeds_and_leaves_zero_rows, ::test_delete_argument_with_participant_scoped_discrepancy_succeeds_and_leaves_zero_rows, ::test_delete_argument_with_import_run_referencing_discrepancy_raises_no_fk_violation, ::test_delete_argument_does_not_delete_other_arguments_participant_or_person_discrepancies, ::test_delete_argument_does_not_delete_shared_lead_case_discrepancy_of_another_argument"
        status: pass
    human_judgment: false

duration: 100min
completed: 2026-08-26
status: complete
---

# Phase 50 Plan 03: Argument-Scoped Approve, Operator Provenance Stamping, and Delete-Cascade Fix Summary

**A new `POST /arguments/{id}/approve` route makes a jobless corpus argument publishable end to end; `update_argument`/`update_argument_metadata` now stamp `Argument`/`Case` rows as `operator`-authored so a disagreeing re-import is rejected-and-recorded, not silently overwritten; and `delete_argument`'s gate is inverted to published-only with a `value_discrepancy` cascade fix that closes a real `ForeignKeyViolation` this task's own tests found live.**

## Performance

- **Duration:** ~100 min
- **Tasks:** 3
- **Files modified:** 6 (0 created, 6 modified)

## Accomplishments

- `POST /api/admin/arguments/{argument_id}/approve` (D-14): argument-scoped CANDIDATE→DRAFT transition inheriting router-level auth, mapped 404/422/200 in the documented order, proven end-to-end against a jobless CANDIDATE argument (approve then publish, both 200, `admin_jobs` row count unchanged).
- `_stamp_operator_provenance` (PD-08): the only writer that makes `Argument`/`Case`'s five compare-set columns reach `AuthorityRank.OPERATOR`. Called from `update_argument` (argued_date → Argument; case_name/docket_number → the lead Case only) and `update_argument_metadata` (question_number/source_docket → Argument only, per this task's scoped call-site list — `argued_date` writes via the metadata path are deliberately not stamped, matching both the plan's action text and its acceptance-criteria call-site count).
- `delete_argument`'s gate inverted from DRAFT-only to a single published-only refusal (D-25/PD-11) — CANDIDATE, DRAFT, and UNPUBLISHED are all now deletable.
- A new cascade step (D-26) deletes `value_discrepancy` rows scoped to this argument's own row, its lead case (only when this argument is the case's *exclusive* lead), and its participants, before `ImportRun` rows are deleted — closing the latent `ForeignKeyViolation` D-26 named. A follow-up step this task's own testing surfaced NULLs `import_run_id` on any *surviving* discrepancy row that still points at one of this argument's `ImportRun` rows (e.g. a `target_type="person"` row, or another argument's participant row) — see Deviations.
- Route, router, and delete-UI copy updated to name "published" (not "drafts") as the only blocked state.

## Task Commits

Commits are grouped by architectural layer (router / service / UI) rather than strictly one-per-Task, since admin.py and admin_arguments.py are each touched by two of the three plan Tasks — see Decisions Made.

1. **Router layer (Task 1 + Task 3's route-facing half)** — `ba28eb405` (feat): approve route, delete-route 409 copy, route/e2e tests.
2. **Service layer (Task 2 + Task 3's service-facing half)** — `aac68499c` (feat): `_stamp_operator_provenance`, `delete_argument` gate + cascade fix, service tests.
3. **UI layer (Task 3's frontend half)** — `ff974d65c` (fix): `can_delete` derivation, Danger Zone copy.

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS update)

## Files Created/Modified

- `api/routers/admin.py` — new `POST /arguments/{argument_id}/approve` route; delete route's 409 detail/docstring reworded to published-only
- `api/services/admin_arguments.py` — `_stamp_operator_provenance` helper + two call sites in `update_argument`, one in `update_argument_metadata`; `delete_argument`'s gate inverted and its cascade gains the `value_discrepancy` delete step + the surviving-row `import_run_id` NULL-out step
- `app/src/routes/admin/arguments/[id]/+page.server.ts` — `can_delete` now `status !== 'published'`; `?/delete` action's 409 copy reworded
- `app/src/routes/admin/arguments/[id]/+page.svelte` — Danger Zone disabled-state tooltip reworded
- `api/tests/test_admin_arguments_routes.py` — approve-route auth/404/422/200/e2e tests; DELETE tests updated for the published-only gate
- `api/tests/test_admin_arguments_service.py` — provenance-stamp tests + round-trip; delete-gate structural test rewritten; six new D-26 discrepancy-cascade tests; one pre-existing AsyncMock-driven test's assertion index adjusted for the new provenance-stamp `db.execute` call (see Deviations)

## Decisions Made

- **Commit grouping by layer, not strict per-Task** — see key-decisions in frontmatter. Every task's own acceptance criteria are independently verified regardless of which commit carries the change.
- **`update_argument_metadata` does not stamp provenance when it writes `argued_date`** — only `question_number`/`source_docket` trigger the stamp there, exactly as the plan's action text and its "at least 4 `_stamp_operator_provenance(` occurrences" acceptance criterion (1 definition + exactly 3 call sites) specify. This is a known, plan-authored scope line, not an oversight — recorded here in case a future plan needs to close the gap.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `delete_argument`'s D-26 cascade could still raise `ForeignKeyViolation` for a surviving `value_discrepancy` row**
- **Found during:** Task 3, writing `test_delete_argument_does_not_delete_other_arguments_participant_or_person_discrepancies` — the test failed with a real `ForeignKeyViolationError` on `DELETE FROM import_run`, not an asserted claim.
- **Issue:** D-26 requires that a `target_type="person"` (or a different argument's participant) `value_discrepancy` row survive a delete untouched. But that surviving row's `import_run_id` can legitimately point at one of *this* argument's own `ImportRun` rows — a `Person` is shared across every argument they appear in, so a person-scoped discrepancy can be attributed to any argument's reconcile/resolve pass, including the one being deleted. The plan's own cascade (delete `value_discrepancy` in three scopes, then delete `ImportRun`) left that surviving row's FK dangling into a row about to be deleted.
- **Fix:** Added a new step between the scoped `value_discrepancy` delete and the `ImportRun` delete: select this argument's own `ImportRun` ids, and `UPDATE value_discrepancy SET import_run_id = NULL WHERE import_run_id IN (...)`. Every row that should have been deleted already was, in the prior step — anything still referencing one of these `ImportRun` ids at this point is, by construction, a row the cascade must preserve. Mirrors the pre-existing `AdminJob.argument_id` NULL-out pattern already in the same function (`import_run_id` is nullable).
- **Files modified:** `api/services/admin_arguments.py`
- **Verification:** `test_delete_argument_does_not_delete_other_arguments_participant_or_person_discrepancies` and the new `test_delete_argument_does_not_delete_shared_lead_case_discrepancy_of_another_argument` both pass; full suite green.
- **Committed in:** `aac68499c`

**2. [Rule 1 - Bug] `test_delete_argument_gate_keys_on_published`'s own docstring line tripped its own substring search**
- **Found during:** Task 3 verification — the structural gate test failed because `func_body.find("if argument.status")` matched a docstring prose line ("Returns True on success, False if argument.status == PUBLISHED") that appears earlier in the function's source than the real `if argument.status == ArgumentStatusEnum.PUBLISHED:` gate line.
- **Fix:** Reworded the docstring to "Returns True on success, False when the current status is PUBLISHED" — no functional change, prose only.
- **Files modified:** `api/services/admin_arguments.py`
- **Verification:** `test_delete_argument_gate_keys_on_published` passes.
- **Committed in:** `aac68499c`

**3. [Rule 1 - Bug] A pre-existing AsyncMock-driven test's fixed `db.execute` call-count assumption broke under the new provenance-stamp call**
- **Found during:** Task 2 implementation — `test_metadata_array_writes_normalized_list_and_canonical_first_value` drives `update_argument_metadata` against an `AsyncMock` with a fixed `side_effect` list and reads `db.execute.await_args_list[-1]` as "the update statement." Adding `_stamp_operator_provenance`'s own `db.execute` call after the values-update makes that call the new *last* one.
- **Fix:** Added one more `MagicMock()` to the fixed `side_effect` list and changed the assertion to read `await_args_list[-2]` (documented inline).
- **Files modified:** `api/tests/test_admin_arguments_service.py`
- **Verification:** Test passes; no other AsyncMock-driven `update_argument`/`update_argument_metadata` test in the suite depended on the old call count (confirmed by grep before editing).
- **Committed in:** `aac68499c`

---

**Total deviations:** 3 auto-fixed (2 Rule 1 bug fixes necessary for correctness — one closing a real, test-discovered FK-orphaning gap in the plan's own cascade design; one a self-tripping test fix — and 1 Rule 1 pre-existing-test-adjustment forced by the plan's own new call site). **Impact:** All three were necessary for full-suite correctness; none touched production behavior beyond what the plan specified except the FK-orphaning fix, which closes a defect the plan's own D-26 decision named as its motivating class of bug but whose fix (as literally specified) did not fully close. No scope creep.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The argument-scoped approve route is live and ready for plan 50-04's `/admin/review` Approve action button.
- `_stamp_operator_provenance` is the established pattern for any future `Argument`/`Case` writer; plan 50-05's reconcile compare-and-write body should call the same helper on its own `ACCEPT`/`ACCEPT_AND_RECORD` writes if it writes any of the five gated columns directly (it more likely calls `apply_argument_value_change`/`apply_case_value_change` from plan 50-02, which do not themselves stamp — worth confirming at 50-05 plan time whether the reconcile writer needs its own stamp call or whether D-07's restamp-to-corpus is the only provenance write it performs).
- `delete_argument`'s D-26 cascade (including the import_run_id NULL-out fix) is complete and independently tested at all three discrepancy scopes plus the shared-lead-case and cross-argument survival cases.
- No blockers.

---
*Phase: 50-unified-import-path*
*Completed: 2026-08-26*

## Self-Check: PASSED

All modified files verified present on disk with the expected content; all three commit hashes (`ba28eb405`, `aac68499c`, `ff974d65c`) verified present in git log; full suite re-run in foreground: 1554 passed, 5 xfailed, 0 failed (up from 1535/5/0 baseline).
