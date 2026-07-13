# Deferred Items — Phase 31

Out-of-scope discoveries logged during plan execution. Not fixed as part of
the plan that discovered them (per executor scope-boundary rules) — tracked
here for a future fix.

## Plan 31-04

### `admin_arguments.py::delete_argument` omits `argument_status_log` from its FK cascade

- **Found during:** Task 2 (Add gated deletion path with safety guards)
- **File:** `api/services/admin_arguments.py` (function `delete_argument`, ~line 723)
- **Issue:** The function's documented FK-ordered cascade (Utterances →
  PipelineRuns → ArgumentParticipants → CaseArguments → NULL
  `AdminJob.argument_id` → Argument) does not delete `argument_status_log`
  rows before deleting the `arguments` row. `argument_status_log.argument_id`
  is a `NOT NULL` FK to `arguments.id` with no `ondelete` clause (plain
  `sa.ForeignKey("arguments.id")` in migration `0012_unpublished_enum_and_status_log.py`),
  which defaults to `RESTRICT`/`NO ACTION` in PostgreSQL. Every DRAFT
  argument has at least one `argument_status_log` row (written by
  `approve_job` at creation — `api/services/admin_jobs.py:589`), so any call
  to `delete_argument` on a DRAFT argument that has been approved through the
  normal job flow should raise a `ForeignKeyViolation`, not succeed silently.
- **Why not fixed here:** `api/services/admin_arguments.py` is not in this
  plan's `files_modified` (`scripts/cleanup_leaked_test_rows.py` only) —
  out of scope per the executor's scope-boundary rule. `scripts/cleanup_leaked_test_rows.py`
  itself deletes `argument_status_log` rows before deleting the `arguments`
  row in its own cascade, so this script is unaffected.
- **Suggested fix:** Add a `delete(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == argument_id)`
  step to `delete_argument`'s cascade, ordered anywhere before the final
  `Argument` delete (no other FK depends on `argument_status_log`).
- **Status:** Not reproduced against a live admin-created DRAFT argument in
  this session (would require exercising `create_person_for_job`/`approve_job`
  end-to-end); flagged from static FK/migration analysis. Recommend a
  regression test (`test_admin_arguments_service.py`) asserting delete
  succeeds for a DRAFT argument that has at least one status log row.
