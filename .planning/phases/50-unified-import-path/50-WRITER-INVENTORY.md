# Phase 50 — Gated-Column Writer Inventory (D-24)

**Built:** 2026-08-26 (plan 50-07, Task 3)

D-24 closes SC-4 with an **executable behavioral gate plus a dispositioned inventory** —
never a source-text grep alone. `pipeline/tests/test_gated_column_writers.py` (shipped by
plan 50-06) is the executable half: it drives 8 real writers against a real database and
asserts on the resulting row state and `value_discrepancy` table, with a falsifiability
control (a direct ungated `UPDATE`) proving its assertions are content-dependent, not
vacuously green — see that module's own docstring and 50-06-SUMMARY.md's "Verification"
section for the hand-reversion proof. This file is the dispositioned inventory half,
extending `.planning/phases/49-review-model/deferred-items.md`'s D-35a table shape (write
path / disposition / reasoning) to every writer that can reach one of this milestone's
gated value columns:

- `ArgumentParticipant.person_id` / `.side` / `.descriptor`
- The four `Person` name-part columns (`_NAME_PART_FIELDS`: first/middle/last/suffix)
- `Argument.argued_date` / `.question_number` / `.source_docket`
- `Case.case_name` / `.docket_number`

Every row below carries an explicit Disposition and a non-empty Reason. Built by reading
each writer's source directly — the same discipline that found the two writers D-22's own
enumeration did not name (rows 12 and 13 below), and a third this plan's own inventory work
found in turn (rows 23–24, deferred rather than fixed — see Deferred Items below).

## Delegates — routes through a gate function

| # | Writer (file::function) | Columns reached | Disposition | Reason |
|---|---|---|---|---|
| 1 | `api/services/admin_arguments.py::update_participant_side` | `ArgumentParticipant.side`/`.descriptor` | delegates | Calls `apply_participant_value_change` twice (side always; descriptor only off-BENCH, RESOLVE-13). Phase 49's original tracer conversion. |
| 2 | `api/services/admin_arguments.py::update_argument` | `Argument.argued_date`, `Case.case_name`/`.docket_number` | delegates (operator-stamp variant, PD-08) | Writes the value directly (operator-facing editor; the value always wins, so there is nothing for a compare gate to decide), then calls `_stamp_operator_provenance(model=Argument\|Case, ...)` — the ONLY place that makes `authority_rank`'s `operator` rung reachable on these two tables, since neither carries `review_state`. Plan 50-03. |
| 3 | `api/services/admin_arguments.py::update_argument_metadata` | `Argument.source_docket`/`.question_number`, `Case.case_name` | delegates (operator-stamp variant, PD-08) | Same `_stamp_operator_provenance` mechanism as row 2, scoped to exactly the two `Argument` fields this function's `<action>` named (`argued_date` deliberately excluded from the stamp at this call site — documented inline). Plan 50-03. |
| 4 | `api/services/admin_jobs.py::resolve_job` | `ArgumentParticipant.person_id` | delegates | Calls `apply_participant_value_change`. Phase 49 D-35a "defence in depth" lock (see `deferred-items.md`). |
| 5 | `api/services/admin_jobs.py::update_resolve_row_for_job` | `ArgumentParticipant.side`/`.descriptor` | delegates | Calls `apply_participant_value_change`. |
| 6 | `api/services/admin_jobs.py::create_person_for_job` | `ArgumentParticipant.person_id`/`.side` | delegates | Calls `apply_participant_value_change` twice, only when `raw_speaker_label` is set (participant already exists to attach to). |
| 7 | `api/services/admin_people.py::update_person` | `Person` name parts | delegates | Calls `apply_person_value_change` per name part. The operator-facing People-directory editor. |
| 8 | `pipeline/commands/resolve.py::_apply_resolved_person_ids` | `ArgumentParticipant.person_id` | delegates | Per-row `apply_participant_value_change` call replacing the former bulk `UPDATE` (plan 50-06, Task 1). **D-22's enumeration did not name this writer** — found ungated during plan 50-05's research, fixed by plan 50-06. Covered by `test_gated_column_writers.py::test_resolve_writer_rejects_lower_authority_person_id`, whose falsifiability was hand-verified (50-06-SUMMARY.md). |
| 9 | `pipeline/commands/parse.py::_write_cover_metadata_through_gate` | `Argument.argued_date`, `Case.case_name` | delegates | Calls `apply_argument_value_change`/`apply_case_value_change` (Blocks A/B). Replaces a formerly-unconditional overwrite (plan 50-06, Task 2) — the unconditional lead-`Case.case_name` clobber (T-50-20) is gone. |
| 10 | `pipeline/commands/parse.py::_run_parse_inner` (Block D, inline) | `Argument.source_docket` | delegates (structurally gap-fill-only) | Calls `apply_argument_value_change`, but only reachable when `argument_row.source_docket is None` — the pre-existing "only if currently NULL" guard is UNCHANGED (a source-inspection regression test asserts the exact literal Python conditional). Can never reach `REJECT_AND_RECORD` through this call site; documented in the code, the D-24 test's own docstring, and 50-06-SUMMARY.md. |
| 11 | `pipeline/commands/import_justices_csv.py::run_import_justices_csv` (UPDATE branch) | `Person` name parts | delegates | Four explicit `apply_person_value_change` calls (`incoming_source="seed"`), replacing the former blank-only-prefill writer (plan 50-06, Task 3). |
| 12 | `pipeline/commands/import_convokit.py::_reconcile_conversation` | `Argument.argued_date`/`.question_number`/`.source_docket`, lead `Case.case_name`/`.docket_number`, each paired `ArgumentParticipant.person_id`/`.side`/`.descriptor`, each paired participant's `Person` name parts | delegates | The full D-02 compare-and-record field walk, calling all four gates in PD-14's fixed order on every reconcile pass (plan 50-05). Replaces plan 50-01's record-nothing skip-existing placeholder. |
| 13 | `pipeline/commands/import_convokit.py::_apply_extracted_name_provenance` | `Person` name parts | delegates (structurally gap-fill-only) | Calls `apply_person_value_change`, gated by a pre-existing `has_any_part` guard that never reaches `ACCEPT_AND_RECORD`/`REJECT_AND_RECORD` in ANY mode (documented in the function's own docstring). **D-22's enumeration did not name this writer either** — found ungated during plan 50-05's own research and fixed in the same plan. Covered by `test_gated_column_writers.py::test_import_convokit_name_provenance_writer_gap_fills_blank_person`. |

## N/A — create, not overwrite

| # | Writer (file::function) | Columns reached | Disposition | Reason |
|---|---|---|---|---|
| 14 | `pipeline/commands/parse.py::_run_parse_inner` (Step 7b, `ArgumentParticipant` seeding) | `ArgumentParticipant.side` (initial value) | N/A — create, not overwrite | Select-before-insert: only labels NOT already present get a new row (`new_rows = [(lbl, side) for lbl, side in participant_labels if lbl not in existing]`). A pre-existing (possibly operator-edited) row is never touched by this block. The code's own PD-20 comment states this explicitly. |
| 15 | `pipeline/commands/import_justices_csv.py::run_import_justices_csv` (CREATE branch) | `Person` name parts (initial value) | N/A — create, not overwrite | A brand-new `Person` row has no stored value to arbitrate against. |
| 16 | `pipeline/commands/import_convokit.py::_import_conversation` / `_get_or_create_case` / first-import participant creation | `Argument`/`Case`/`ArgumentParticipant` initial values | N/A — create, not overwrite | First-import row construction. Reconcile (row 12) is the writer that governs every SUBSEQUENT pass over the same row. |

## N/A — no authority column

| # | Writer (file::function) | Columns reached | Disposition | Reason |
|---|---|---|---|---|
| 17 | `pipeline/commands/resolve.py` (Step 5, `Utterance.person_id` bulk `UPDATE`) | `Utterance.person_id` | N/A — no authority column | `Utterance` carries no `source`/`method`/`review_state` of its own — provenance is inherited from the parent `ImportRun`. Deliberately kept as a bulk statement and annotated with a PD-19 comment in the code (plan 50-06). |
| 18 | `api/services/trust.py::recompute_argument_tier` | `Argument.trust_tier` | N/A — no authority column | A derived/materialized rollup, not an authored value with provenance to arbitrate. |
| 19 | `pipeline/commands/parse.py` (`Argument.cover_metadata` unconditional write) | `Argument.cover_metadata` | N/A — no authority column | Raw cover-extractor output, stored for display/audit only — not one of the gated compare-set columns. |
| 20 | `api/services/admin_arguments.py::publish_argument`/`unpublish_argument`, `api/services/admin_jobs.py::approve_job` | `Argument.status`/`.published_at`/`.resolved_at` | N/A — no authority column | Lifecycle/state-machine columns, not value columns with source/method provenance to compare. |

## N/A — review metadata only

| # | Writer (file::function) | Columns reached | Disposition | Reason |
|---|---|---|---|---|
| 21 | `api/services/admin_review.py::resolve_participant_review` | `ArgumentParticipant.review_state` | N/A — review metadata only | Confirm / confirm-unattributable / reflag — never a value column. |
| 22 | `api/services/admin_review.py::resolve_person_review` | `Person.review_state` | N/A — review metadata only | Same three actions, People-tab. |

## Deferred items (found ungated during this inventory, not fixed by this plan)

| # | Writer (file::function) | Columns reached | Disposition | Reason |
|---|---|---|---|---|
| 23 | `pipeline/commands/parse.py::_update_participant_sides` | `ArgumentParticipant.side` | **UNGATED — defect, deferred** | Direct ORM attribute assignment (`p.side = ...`) from a TOC-derived label map, on EVERY parse pass, with no `apply_participant_value_change` call, no `review_state` check, no provenance stamp. Since `ArgumentParticipant` rows persist across re-parses, a re-parse can silently overwrite a participant an operator already reassigned via the gated `update_participant_side` route (row 1). Not named by D-22's enumeration, not touched by plan 50-06's `parse.py` conversion (which covered Blocks A/B/D only). See `.planning/phases/49-review-model/deferred-items.md`'s "D-24 writer inventory (50-07)" section for the full finding and why it is not fixed here (out of scope for this plan; needs its own per-row-gate conversion and tests). |
| 24 | `pipeline/commands/parse.py::_update_participant_descriptors` | `ArgumentParticipant.descriptor` | **UNGATED — defect, deferred** | Same defect, same mechanism, `.descriptor` instead of `.side`. Same deferred-items.md entry. |

Rows 23–24 are deliberately NOT one of the four dispositions above — forcing a genuine
ungated writer into "N/A" would misrepresent it. They are recorded here, in the open
deferred-items.md item, and are explicitly NOT auto-fixed by this plan: `pipeline/commands/
parse.py` is not in plan 50-07's `files_modified`, and a correct fix needs a real per-row
gate conversion (mirroring row 8's `resolve.py` shape) plus its own test coverage — the same
"new decision, not a bug fix" reasoning this file's very first deferred item used for a
sibling gap in this same module's history.

## D-18 closure (no-op)

Phase 49's deferred `admin_jobs.discrepancies` item (the legacy JSONB blob, distinct from
the `value_discrepancy` table above) closes as a **no-op**: the corpus write at
`import_convokit.py:~640` disappeared with the `AdminJob` it used to attach to (plan 50-01,
D-18) — corpus arguments mint no `AdminJob` at all as of this phase, leaving the blob
PDF-only by construction. Nothing to migrate, rename, or retire.

## Falsifiability control

`pipeline/tests/test_gated_column_writers.py::test_control_direct_ungated_update_changes_
value_with_no_discrepancy_recorded` performs a direct, ungated `update(...)` against a real
fixture and asserts it DOES change the value and records NO discrepancy — the shape every
OTHER test in that module would start matching if its own named writer regressed to a
direct `UPDATE`. Hand-verified for one real writer: `resolve.py`'s `_apply_resolved_person_
ids` (row 8) was temporarily reverted to a direct `update()`, its named test failed as
expected, and the writer was restored (see 50-06-SUMMARY.md's "Verification" section for
the full record).
