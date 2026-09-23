---
phase: 47-provenance-foundation
reviewed: 2026-08-18T14:35:57Z
depth: standard
files_reviewed: 42
files_reviewed_list:
  - alembic/versions/0026_import_run_provenance.py
  - api/models/models.py
  - api/routers/admin.py
  - api/schemas/admin_jobs.py
  - api/schemas/utterance.py
  - api/services/admin_arguments.py
  - api/services/admin_dev.py
  - api/services/admin_jobs.py
  - api/services/arguments.py
  - pipeline/__main__.py
  - pipeline/commands/import_convokit.py
  - pipeline/commands/ingest.py
  - pipeline/commands/parse.py
  - pipeline/commands/resolve.py
  - scripts/delete_fixture_argument.py
  - conftest.py
  - pipeline/tests/conftest.py
  - api/tests/test_admin_arguments_service.py
  - api/tests/test_admin_dashboard_stats.py
  - api/tests/test_admin_dev_routes.py
  - api/tests/test_admin_jobs_phase35.py
  - api/tests/test_admin_jobs_service.py
  - api/tests/test_admin_jobs_source.py
  - api/tests/test_admin_jobs_stats.py
  - api/tests/test_argument_oyez_field.py
  - api/tests/test_arguments.py
  - api/tests/test_migration_0022_person_name_authority.py
  - api/tests/test_phase44_resolve_table_contract.py
  - api/tests/test_published_gate.py
  - api/tests/test_speakers_service.py
  - pipeline/tests/test_delete_fixture_argument.py
  - pipeline/tests/test_diff_corpus_fixture.py
  - pipeline/tests/test_import_convokit_core.py
  - pipeline/tests/test_import_convokit_utterances.py
  - pipeline/tests/test_import_justices_csv.py
  - pipeline/tests/test_import_run.py
  - pipeline/tests/test_import_run_provenance.py
  - pipeline/tests/test_ingest.py
  - pipeline/tests/test_parse.py
  - pipeline/tests/test_resolve.py
  - tests/test_models_import.py
  - tests/test_schema.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 47: Code Review Report

**Reviewed:** 2026-08-18T14:35:57Z
**Depth:** standard
**Files Reviewed:** 42
**Status:** issues_found (no BLOCKER-level findings; 2 WARNING, 3 INFO)

## Summary

Phase 47 replaces `PipelineRun`/`pipeline_runs` with `ImportRun`/`import_run`, adding
declared write-time `source`/`method`/`external_id` columns as native PostgreSQL enums, and
drops the read-time `strategy` inference. I traced every production write site
(`pipeline/commands/{ingest,parse,resolve,import_convokit}.py`) and every read site
(`api/services/arguments.py`, `admin_arguments.py`, `admin_jobs.py`, `api/routers/admin.py`)
against the 8 design invariants named in the task brief, plus the migration's DDL against the
ORM's `SAEnum` member lists, plus every listed test file's diff for silently-dropped coverage.

**All 8 invariants hold, with no counter-examples found:**

1. Provenance is declared at write time everywhere — no code path reconstructs `source`/
   `method` from `strategy`, `oyez_*`/`pdf_path` nullability, or any other proxy. Confirmed via
   targeted greps (`oyez_transcript_id is (not )?None`, `pdf_path is (not )?None`) across
   `api/` and `pipeline/` (excluding tests) — the one hit (`api/routers/admin.py:532`,
   `run.pdf_path is None`) is a 404-vs-200 branch for PDF streaming, not a provenance inference.
2. Exactly one `method` per `import_run` row in `pipeline/commands/parse.py` — `parse_method`
   is derived solely from whether the local `parse_strategy` string was flipped to
   `"llm_corrective"` inside the `try` block (i.e., whether `parse_with_llm` returned) or left
   at its initialized `"rule_based"` value (i.e., whether it raised, caught by the broad
   `except Exception`). No caller-supplied value can reach this translation (T-47-07).
3. `source`/`method` are `NOT NULL` with no `server_default` in migration 0026's
   `op.create_table("import_run", ...)`, mirrored by `SAEnum(..., nullable=False)` with no
   `default=` in the ORM — `pipeline/tests/test_import_run_provenance.py::
   test_import_run_rejects_missing_source_and_method` proves the DB itself raises
   `IntegrityError` on `flush()`, not merely an application-level check.
4. `Argument.oyez_transcript_id` is untouched — same column, same dedup query
   (`find_argument_by_pair`/idempotency check in `import_convokit.py`), same public API field
   in `api/schemas/utterance.py`'s `ArgumentMetadataResponse`. `import_run.external_id` is a
   pure addition (confirmed by the live-evidence readback in `47-PROVENANCE-EVIDENCE.md`,
   where `external_id` and `oyez_transcript_id` both equal the same conversation id).
5. `api/schemas/utterance.py`'s public `UtteranceResponse` carries only `import_run_id` — no
   `source`/`method`/`external_id`/`strategy` field exists on it at all, and
   `api/tests/test_arguments.py` now asserts all four are absent from the serialized response
   (strengthened, not weakened, coverage). `api/services/arguments.py`'s read path filters on
   `ImportRun.step`/`ImportRunStatus.COMPLETED` exactly as the old `PipelineRun` query did.
6. No `Base.metadata.create_all` anywhere in the reviewed files (grep-confirmed); Alembic
   migration 0026 is the only DDL for this phase's schema change.
7. `connect_args={"statement_cache_size": 0}` is untouched in both `api/core/database.py` and
   `pipeline/db.py` (not part of this phase's diff, verified unaffected).
8. Migration 0026's `down_revision = "0025"` chains correctly; the two new `CREATE TYPE`
   statements are DO-block-guarded via a `pg_type` existence check (idempotency pattern
   matching migration 0003); the ORM's `ImportSource`/`ImportMethod` enum member lists
   (`operator/corpus/pdf_pipeline/seed`, `manual/direct/normalized/rule_based/llm_corrective`)
   match the DDL's `CREATE TYPE ... AS ENUM (...)` labels exactly, position-for-position — no
   drift. The `utterances` FK repoint and `strategy` drop are ordered correctly (FK constraint
   dropped before the table it references is dropped; index/column renamed before the new FK is
   created), and `downgrade()` mirrors the original migration 0001 `pipeline_runs` table shape
   byte-for-byte (same columns, same nullability), reversibility having actually been exercised
   against `scotus_test` per `47-01-SUMMARY.md`.

I also diffed every listed test file against its pre-phase version. Every `PipelineRun`/
`strategy=`-referencing assertion was translated to its `ImportRun`/`source=`/`method=`
equivalent — I did not find a single case of an assertion being deleted rather than translated.
Several files (`test_arguments.py`, `tests/test_models_import.py`, `tests/test_schema.py`) gained
*new* standing assertions (provenance-leak negative checks, enum exhaustiveness guards, live
schema absence checks) beyond what existed before the phase.

The two WARNING-level findings below are process/completeness gaps the phase's own summary
documents already flag as open, not confirmed defects — I re-verified the higher-risk half of
each with a static grep and found no evidence of an actual leak or regression, but neither has
been closed out with a live end-to-end check yet.

## Warnings

### WR-01: Task 3 (operator live-verification checkpoint) not yet performed

**File:** `.planning/phases/47-provenance-foundation/47-06-SUMMARY.md:159-170` (process artifact,
not source, but gates whether this phase's production-facing surfaces have been confirmed clean)
**Issue:** 47-06-PLAN.md's Task 3 — starting the real API + SvelteKit app and manually
confirming (a) the admin job list/detail correctly show "corpus" vs "pdf", and (b) the public
argument page never renders the literal strings `corpus`, `pdf_pipeline`, `rule_based`, or
`llm_corrective` anywhere — is explicitly recorded as **not attempted** in this worktree. I
independently re-ran the static half of that check (`grep -rln "rule_based\|llm_corrective\|
pdf_pipeline\b" app/src` → no matches; `api/schemas/utterance.py` confirmed field-clean), which
reduces risk, but a static grep cannot substitute for the live click-through the plan itself
calls `gate="blocking"`. Shipping this phase without that checkpoint means the apolitical-framing
hard constraint (CLAUDE.md) has not been end-to-end verified on a running instance, only on the
serialized schema.
**Fix:** Run 47-06-PLAN.md's Task 3 checklist (steps 1-6 in the summary's "User Setup Required"
section) against the merged main worktree before considering Phase 47 closed, and record the
result (even if trivially "no hits") in the evidence file or STATE.md.

### WR-02: `pipeline/commands/parse.py::_fail_run` is dead code inherited by this phase

**File:** `pipeline/commands/parse.py:562-578`
**Issue:** `_fail_run` (renamed from a pre-existing `PipelineRun`-typed helper by this phase's
mechanical identifier rename) transitions a run to `FAILED` and records `failure_reason`, but no
call site anywhere in this file (or the repo) invokes it — confirmed via
`grep -rn "_fail_run" --include=*.py .` returning only its own `async def` line. This predates
Phase 47 (the removal of its call sites happened in an earlier commit, not this phase's diff —
`git log -p` shows the calls were already gone before `8e1c6a33b`), so it is not a new defect
introduced here, but the phase's own rename touched this function's signature (`PipelineRun` →
`ImportRun`) and its docstring without noticing it is unreachable. Left as-is, a future reader
may assume failures are recorded here when they are not — nothing in `run_parse`'s current
`try/except` (in `run_parse`, not `_run_parse_inner`) calls `_fail_run`; a raised exception is
only ever surfaced by updating `AdminJob.status`, never `ImportRun.status`/`failure_reason`, for
a job-driven run's `ImportRun` row.
**Fix:** Either wire `_fail_run` into `run_parse`'s outer `except Exception` handler (so a failed
parse run also gets `ImportRun.status = FAILED` / `failure_reason` set, not just the paired
`AdminJob`), or delete the function if the design intent has genuinely moved to
`AdminJob.error_message` only. Since this is pre-existing and out of this phase's stated scope,
raising it here as a flag for a follow-up rather than blocking this phase's merge.

## Info

### IN-01: Closed-vocabulary members `operator`/`seed`/`manual` are unused by any writer

**File:** `api/models/models.py:54-66`, `alembic/versions/0026_import_run_provenance.py:62-72`
**Issue:** `ImportSource.OPERATOR`, `ImportSource.SEED`, and `ImportMethod.MANUAL` are defined in
both the ORM enum and the native PG `CREATE TYPE` statement, but no production write site in this
diff (`ingest.py`, `parse.py`, `resolve.py`, `import_convokit.py`) ever constructs an `ImportRun`
with any of these three values. This is confirmed intentional forward-provisioning per
`47-01-SUMMARY.md`'s "Task 1" decision note (operator-approved), not an oversight — but since a
PostgreSQL enum value can never be dropped once created (the migration's own docstring says so),
it's worth a standing note that these three values are speculative schema surface with zero
current test coverage of round-tripping them through a real writer.
**Fix:** No action required now; when a future phase introduces an operator-manual-entry or
seed-data writer, add a `pipeline/tests/test_import_run_provenance.py`-style test proving that
combination round-trips, mirroring the existing three-combination guardrail.

### IN-02: `tests/test_schema.py`'s `EXPECTED_TABLES` is missing `admin_jobs` (pre-existing, not this phase's regression)

**File:** `tests/test_schema.py:53-65`
**Issue:** `EXPECTED_TABLES` lists 12 table names; `api/models/models.py` defines 13
(`admin_jobs` is absent from the set). This is a pre-existing gap unrelated to the
`pipeline_runs → import_run` rename this phase made to that same set (the rename itself is
correct) — `admin_jobs` was never added to this constant in an earlier phase. Noted here only
because this file was in-scope for this review and the gap sits directly next to code this
phase touched.
**Fix:** Add `"admin_jobs"` to `EXPECTED_TABLES` in a follow-up (outside this phase's scope).

### IN-03: `_write_corpus_fixture`'s helper duplication between two test files is now three-way

**File:** `pipeline/tests/test_import_run_provenance.py:53-142`
**Issue:** The file's own header comment explains that `_write_corpus_fixture`/`_args`/
`_make_session_cm` were copied (not imported) from `test_import_convokit_core.py` because, at
the time 47-01/47-02 were written, that module's top-level import was broken mid-phase. That
constraint no longer holds — `test_import_convokit_core.py` now imports cleanly against
`ImportRun` (confirmed by this review and by `47-04-SUMMARY.md`) — so the duplication is now a
maintenance-only artifact: a future fixture-shape change to one copy will not automatically
apply to the other.
**Fix:** Non-blocking; consider extracting the three helpers to a shared
`pipeline/tests/_corpus_fixtures.py` (or importing from `test_import_convokit_core.py` now that
the historical import-order hazard is resolved) in a future cleanup pass, not this phase.

---

_Reviewed: 2026-08-18T14:35:57Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
