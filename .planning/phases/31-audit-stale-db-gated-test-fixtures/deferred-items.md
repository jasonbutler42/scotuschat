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

## Plan 31-05

### `api/core/config.py::Settings` crashed on every DB-gated test (blocking, auto-fixed — not deferred)

- **Found during:** Task 1, initial verification run.
- **Issue:** `Settings` (pydantic-settings, `env_file=".env"`) reads the whole
  `.env` file directly regardless of `os.environ`/`load_dotenv()`. Once
  Plan 31-01/02 added `TEST_DATABASE_URL` to `.env`, every `Settings()`
  construction raised `pydantic_core.ValidationError: test_database_url ...
  Extra inputs are not permitted` — this crashed `_api_lifespan` (autouse) for
  every single api/tests test, DB-gated or not, across the whole api/tests
  suite, not just this plan's 5 files.
- **Fix:** Added `test_database_url: str = ""` to `Settings` (declared, unused
  by the running API — solely so `Settings()` doesn't choke on the extra
  `.env` key). Rule 3 (blocking issue) — noted here rather than under a
  separate heading only because it explains why the remaining findings below
  were only now able to surface (this fix is applied, not deferred; see
  SUMMARY.md for the commit).

### Out-of-scope test files, now able to execute for the first time, have their own genuine failures

- **Found during:** Task 1, full-suite regression check (`pytest` with no
  path args) after the config.py fix above unblocked every DB-gated test in
  the repo.
- **Files (none are in this plan's `files_modified`):**
  - `api/tests/test_argument_oyez_field.py::test_utterances_payload_includes_oyez_transcript_id`
    — 404 (owned by Plan 31-06 per its `files_modified` list)
  - `api/tests/test_people.py::test_get_person` — 404 (owned by Plan 31-06)
  - `pipeline/tests/test_ingest.py::test_ingest_creates_pipeline_run`,
    `test_consolidated_dockets`, `test_ingest_idempotent` — `AttributeError`
  - `pipeline/tests/test_parse.py::test_run_id_strategy`,
    `test_llm_failure_modes`, `test_section_hint_not_cascade` — `AttributeError`/`AssertionError`
  - `pipeline/tests/test_pipeline_run.py::test_state_machine`,
    `test_rerun_creates_new_rows` — `RuntimeError`/`sqlalchemy` interface error
  - `pipeline/tests/test_resolve.py::test_resolve_alias_hit`,
    `test_resolve_interactive_prompt`, `test_resolve_interrupt_sets_needs_review`,
    `test_resolve_resumes_after_interrupt` — `Failed: not implemented` / `AttributeError`
  - `pipeline/tests/test_seed_aliases.py::test_seed_creates_justices`,
    `test_seed_idempotent` — `Failed: not implemented`
- **Why not fixed here:** All of the above live outside this plan's 5
  `files_modified` (`test_admin_arguments_service.py`, `test_admin_jobs_phase25.py`,
  `test_admin_jobs_service.py`, `test_admin_jobs_stats.py`, `test_arguments.py`).
  `test_argument_oyez_field.py`/`test_people.py` are explicitly assigned to
  Plan 31-06; the `pipeline/tests` files are pipeline-side fixtures outside
  this api-side plan's remit entirely. These tests were previously
  effectively unreachable (the config.py crash above made every DB-gated
  test error before reaching its own logic) — the crash's fix is what
  surfaced them for the first time as genuinely-executing failures, matching
  this phase's premise ("silently no-op'd before the 999.17 lifespan fix").
- **Suggested next step:** Confirm Plan 31-06/31-07 (or whichever plan owns
  `pipeline/tests`) picks these up; do not assume they are already tracked
  just because they're now visible.
