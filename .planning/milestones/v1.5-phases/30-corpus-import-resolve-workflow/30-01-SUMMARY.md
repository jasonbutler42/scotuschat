---
phase: 30-corpus-import-resolve-workflow
plan: 01
subsystem: pipeline
tags: [sqlalchemy, admin-jobs, corpus-import, resolve-workflow, convokit]

# Dependency graph
requires:
  - phase: 29-historical-corpus-import
    provides: import_convokit.py's Case/Argument/CaseArgument/PipelineRun/ArgumentParticipant/Utterance write path
provides:
  - Corpus-imported Argument rows created at status=PIPELINE (not DRAFT), making them editable via the existing Resolve card
  - A paired AdminJob(status=PAUSED, current_step=RESOLVE) row per corpus-imported argument, with HIT-shaped discrepancies
  - _build_discrepancies() helper producing ResolveCard-compatible discrepancy dicts from ArgumentParticipant rows
affects: [30-corpus-import-resolve-workflow remaining plans (admin_jobs.py source field, pipeline list UI Source column)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Producer-side pipeline fix: reuse existing resolve/approve service functions unchanged by making the producer (import_convokit.py) write the exact row shapes those functions already expect (status=PIPELINE, paired PAUSED/RESOLVE AdminJob with HIT-shaped discrepancies)"
    - "AdminJob creation via direct session.add() construction (not admin_jobs.py's create_job() helper) to preserve per-conversation transactional atomicity"

key-files:
  created:
    - pipeline/tests/test_import_convokit_adminjob.py
  modified:
    - pipeline/commands/import_convokit.py
    - pipeline/tests/test_import_convokit_core.py

key-decisions:
  - "Argument.status write flipped from DRAFT to PIPELINE in _import_conversation (D-06 superseded per 30-RESEARCH.md Pitfall 1) -- every read path gating Resolve-card editability keys on status==PIPELINE, so DRAFT left every corpus argument permanently read-only"
  - "AdminJob insertion placed immediately after _import_utterances returns (not earlier) -- bench Justice participants are only discovered while streaming utterances, and both the advocates loop and _import_utterances write into the same resolved_participants dict by reference"
  - "_build_discrepancies() built from ArgumentParticipant rows (not resolve.py's raw-label loop) -- mirrors resolve.py's exact 7-key HIT shape so ResolveCard.svelte's Action column renders unmodified for corpus jobs"
  - "No separate commit/flush added for the AdminJob insert -- get_session()'s context manager already commits the whole per-conversation transaction atomically on clean exit"
  - "No second AdminJob-specific idempotency select added -- the existing oyez_transcript_id early-return at the top of _import_conversation already prevents a re-run from reaching the AdminJob insertion"
  - "Updated two pre-existing test_import_convokit_core.py assertions from ArgumentStatusEnum.DRAFT to PIPELINE (lines asserting the actual write-path output), since this plan's Task 1 change is the intended, designed effect on that write path -- not a regression"

requirements-completed: [PJOB-02, PJOB-14, PJOB-15, PJOB-18, PJOB-19, PJOB-20, PJOB-21]

coverage:
  - id: D1
    description: "Corpus-imported Argument rows are created with status=PIPELINE instead of DRAFT, making the Resolve card editable"
    requirement: "PJOB-02"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_adminjob.py#test_argument_status_is_pipeline_not_draft"
        status: pass
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_core.py#test_creates_case_argument_caseargument_pipelinerun_entities"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every corpus-imported argument gets exactly one paired AdminJob row (PAUSED/RESOLVE) created in the same per-conversation transaction"
    requirement: "PJOB-14"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_adminjob.py#test_exactly_one_paused_resolve_adminjob_created"
        status: pass
    human_judgment: false
  - id: D3
    description: "The paired AdminJob's discrepancies JSONB holds one HIT-shaped dict per already-resolved ArgumentParticipant (7 keys, auto_resolved=True, candidates=[])"
    requirement: "PJOB-15"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_adminjob.py#test_discrepancies_are_hit_shaped_for_advocate_and_bench"
        status: pass
    human_judgment: false
  - id: D4
    description: "Re-running an already-imported conversation creates no duplicate AdminJob row"
    requirement: "PJOB-18"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_import_convokit_adminjob.py#test_reimport_same_conversation_creates_no_additional_adminjob"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-10
status: complete
---

# Phase 30 Plan 01: Corpus Import Write-Path Fix Summary

**Corpus-imported arguments now start at `status=PIPELINE` (not `DRAFT`) and are paired with a HIT-shaped `PAUSED`/`RESOLVE` `AdminJob`, making the existing resolve→approve→publish workflow reachable for the ~7,800 historical corpus arguments for the first time.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-10T20:22:43Z
- **Completed:** 2026-07-10T20:34:00Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- `Argument` rows written by `import_convokit.py` now carry `status=ArgumentStatusEnum.PIPELINE` instead of `DRAFT`, unblocking every read path (`list_resolve_rows_for_job`'s `editable` flag, `update_resolve_row_for_job`'s guard, job-detail page's `readonlyMode`) that gates on that status
- New `_build_discrepancies()` helper produces one HIT-shaped dict (7 keys: `raw_speaker_label`, `normalized`, `candidates`, `auto_match_id`, `auto_match_name`, `auto_match_role`, `auto_resolved`) per already-resolved `ArgumentParticipant`, mirroring `resolve.py`'s exact discrepancy shape
- `_import_conversation` now inserts a paired `AdminJob(status=PAUSED, current_step=RESOLVE, argument_id=..., discrepancies=...)` immediately after `_import_utterances` returns, in the same atomic per-conversation transaction, with no second commit/flush and no reuse of `admin_jobs.create_job()`
- New DB-gated test file (`test_import_convokit_adminjob.py`, 4 tests) proves status/pairing/discrepancy-shape/idempotency; two pre-existing `test_import_convokit_core.py` assertions updated from `DRAFT` to `PIPELINE` to match the intended write-path change

## Task Commits

Each task was committed atomically:

1. **Task 1: Add imports, flip Argument.status to PIPELINE, and add the _build_discrepancies helper** - `68cdc9b2` (feat)
2. **Task 2: Insert the paired AdminJob row at the end of _import_conversation** - `f5f045fb` (feat)

## Files Created/Modified
- `pipeline/commands/import_convokit.py` - Added `AdminJob`/`AdminJobStatus`/`AdminJobStep`/`normalize_label` imports; flipped `Argument.status` to `PIPELINE`; added `_build_discrepancies()` helper; inserted paired `AdminJob` creation at the end of `_import_conversation`
- `pipeline/tests/test_import_convokit_adminjob.py` - New DB-gated test file (isolated per-test session fixture) asserting status=PIPELINE, single PAUSED/RESOLVE AdminJob, HIT-shaped non-empty discrepancies covering both advocate (advocates-loop) and bench (utterance-stream) resolution paths, and re-import idempotency
- `pipeline/tests/test_import_convokit_core.py` - Updated two pre-existing assertions from `ArgumentStatusEnum.DRAFT` to `ArgumentStatusEnum.PIPELINE` on the actual corpus-import write path (unrelated fixture-setup uses of `DRAFT` for simulated PDF-pipeline rows were left unchanged)

## Decisions Made
- See `key-decisions` in frontmatter above. No architectural changes; this is a producer-side-only fix reusing `resolve_job()`/`approve_job()`/`update_resolve_row_for_job` completely unmodified, per the plan's explicit scope boundary.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated two pre-existing test assertions that hard-coded the old DRAFT status**
- **Found during:** Task 2 (running the plan's own regression-check command against `test_import_convokit_core.py`)
- **Issue:** `test_creates_case_argument_caseargument_pipelinerun_entities` and `test_malformed_conversation_flagged_not_aborting_term` both asserted `argument.status == ArgumentStatusEnum.DRAFT` on the argument actually created by the corpus-import write path Task 1 intentionally changed to `PIPELINE`. Left unfixed, these two tests would fail permanently, contradicting the plan's own acceptance criterion that these tests "still pass."
- **Fix:** Updated both assertions to `ArgumentStatusEnum.PIPELINE` with a comment referencing the Phase 30 supersession of D-06. Three other `DRAFT` occurrences in the same file (constructing standalone `Argument` fixtures to simulate PDF-pipeline rows in unrelated idempotency/docket-conflict tests) were left untouched since they don't exercise the corpus-import write path.
- **Files modified:** `pipeline/tests/test_import_convokit_core.py`
- **Verification:** `python -m pytest pipeline/tests/test_import_convokit_core.py pipeline/tests/test_import_convokit_utterances.py -q` → 30 passed
- **Committed in:** `f5f045fb` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug fix in test assertions)
**Impact on plan:** Direct, intended consequence of the plan's own Task 1 change; no scope creep. Both fixed assertions are in the acceptance-criteria's own named regression-check test file.

## Issues Encountered
None beyond the deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Corpus-imported arguments are now reachable via the existing admin Resolve card, exactly like PDF-pipeline arguments — an operator can resolve→approve→publish any of the ~7,800 historical arguments through the unchanged admin UI
- Remaining Phase 30 work (per 30-PATTERNS.md): `api/services/admin_jobs.py`'s `source` field derivation (`list_jobs`/`get_job`), the `AdminJobResponse.source` schema field, and the pipeline list page's "Source" column — none of this plan's scope, none blocking
- No blockers identified

---
*Phase: 30-corpus-import-resolve-workflow*
*Completed: 2026-07-10*

## Self-Check: PASSED

All created/modified files confirmed present; both task commits (`68cdc9b2`, `f5f045fb`) confirmed in git log.
