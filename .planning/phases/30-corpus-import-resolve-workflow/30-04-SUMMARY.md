---
phase: 30-corpus-import-resolve-workflow
plan: 04
subsystem: database
tags: [postgres, alembic-free-data-fix, convokit, admin-jobs, operator-runbook]

# Dependency graph
requires:
  - phase: 30-corpus-import-resolve-workflow (30-01)
    provides: import_convokit.py writes Argument.status=PIPELINE and inserts a paired PAUSED/RESOLVE AdminJob per conversation
  - phase: 30-corpus-import-resolve-workflow (30-03)
    provides: Source column (PDF | Corpus tag) on /admin/pipeline/ list, previously unverifiable against real corpus AdminJob rows
provides:
  - term-1955 corpus batch (163 arguments) wiped and re-imported through the 30-01-patched path; now status=PIPELINE with paired paused/resolve AdminJobs
  - Closes the D-02 stored-data gap — previously-stuck term-1955 arguments are now reviewable in the Resolve UI and eligible for the publish flow
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified: []

key-decisions:
  - "No committed migration/backfill script added (D-02) — fix delivered entirely as an ad hoc, FK-safe scoped wipe SQL transaction plus a re-run of the existing idempotent import CLI (import-justices, import-convokit --term 1955)."
  - "Mid-execution blocker (duplicate 'Ketanji Brown Jackson' Person row causing MultipleResultsFound in import-justices) was diagnosed as pre-existing test-data leakage into the shared dev DB from an unrelated root cause (999.17 lifespan-bug fix work), not a defect in this plan's wipe scope. Resolved with its own scoped, verified DELETE (18 leaked Person rows + 15 zero-content synthetic Argument chains removed, the one legitimate Ketanji Brown Jackson Person row with a real court_tenures record preserved) and escalated as ROADMAP.md backlog Phase 999.19 rather than folded into this plan's scope."

requirements-completed: [PJOB-20]

coverage:
  - id: D1
    description: "Scoped FK-safe wipe of all convokit_import-linked term-1955 arguments, followed by re-running import-justices + import-convokit --term 1955, producing status=PIPELINE arguments each paired with a PAUSED/RESOLVE AdminJob"
    requirement: PJOB-20
    verification:
      - kind: manual_procedural
        ref: "Operator ran the runbook SQL (Step 1 SELECT review, Step 2 transactional DELETE, COMMIT) then `python -m pipeline import-justices` and `python -m pipeline import-convokit --term 1955` against the dev DB; import-convokit reported 163 arguments created, 0 skipped, 29913 utterances created, 761 stage-direction utterances, 1191 people matched, 0 docket/question conflicts"
        status: pass
    human_judgment: true
    rationale: "Destructive ad hoc DELETE against the live database (T-30-07) — the plan requires a blocking human checkpoint that is never auto-approved; the executor does not run the wipe/import commands itself."
  - id: D2
    description: "Re-imported term-1955 batch verified reviewable and publishable: all corpus arguments status=pipeline with paired paused/resolve AdminJobs, ResolveCard renders editable with Confirm/Change/Create-person affordances, one full resolve-to-approve round-trip completed"
    requirement: PJOB-20
    verification:
      - kind: manual_procedural
        ref: "Operator confirmed via SQL that all term-1955 corpus arguments are status='pipeline' with a paired admin_jobs row (status='paused', current_step='resolve'); visually confirmed /admin/pipeline/ shows the Corpus tag; opened a job and confirmed ResolveCard renders Side select / Title input as editable controls with Confirm/Change/Create-person affordances; completed one resolve-then-approve round-trip"
        status: pass
    human_judgment: true
    rationale: "Visual/functional UI verification of ResolveCard rendering and a live resolve-to-approve round-trip requires human judgment; user replied 'approved'."

# Metrics
duration: N/A (operator-executed checkpoints; no autonomous task time)
completed: 2026-07-10
status: complete
---

# Phase 30 Plan 04: Corpus Wipe-and-Rerun Operator Runbook Summary

**Term-1955 corpus batch (163 arguments) wiped via a scoped FK-safe transaction and re-imported through the 30-01-patched path, landing at status=PIPELINE with paired paused/resolve AdminJobs — closing the D-02 stored-data gap that left the batch permanently unpublishable and unreviewable.**

## Performance

- **Duration:** N/A — this plan is an operator runbook (D-02); both tasks are checkpoints executed by the operator/orchestrator outside the executor's autonomous task time.
- **Started:** 2026-07-10
- **Completed:** 2026-07-10T22:08:55Z
- **Tasks:** 2 (both checkpoint: 1 human-action, 1 human-verify)
- **Files modified:** 0 (files_modified: [] per plan frontmatter — no committed code; D-02)

## Accomplishments
- Operator ran the FK-safe, corpus-scoped wipe (SELECT review → single BEGIN/COMMIT transaction deleting `admin_jobs` → `argument_status_log` → `utterances` → `argument_participants` → `case_arguments` → `pipeline_runs` → `arguments`, scoped strictly to `PipelineRun.strategy = 'convokit_import'`) against the dev DB, then re-ran `python -m pipeline import-justices` and `python -m pipeline import-convokit --term 1955`.
- Re-import succeeded: `import-justices` was fully idempotent (0 created, 0 upgraded — already correct); `import-convokit --term 1955` created 163 arguments, 0 skipped, 29913 utterances (761 stage-direction), 0 people created, 1191 people matched (reused), 0 speakers flagged, 0 docket/question conflicts, 122 unattributed speakers skipped.
- DB verification confirmed all 163 term-1955 corpus arguments are now `status='pipeline'` with a paired `admin_jobs` row (`status='paused'`, `current_step='resolve'`) — exactly the target state the plan's `must_haves.truths` require.
- User visually verified `/admin/pipeline/` now shows the Corpus tag on these jobs, opened one job's detail page and confirmed the ResolveCard renders editable (Side select / Title input as live controls, Confirm/Change/Create-person affordances instead of "—"), and completed one full resolve-then-approve round-trip — proving the previously-unreachable publish gate is now reachable for corpus arguments. User replied "approved".

## Task Commits

Both tasks were checkpoints with no committed code (D-02, files_modified: []):

1. **Task 1: Operator performs the scoped wipe and re-import of the term-1955 batch** - checkpoint:human-action, no code change; operator ran the runbook SQL + CLI commands directly against the dev DB and replied "done" after resolving the mid-execution test-data-leakage blocker (see Deviations below).
2. **Task 2: Verify the re-imported term-1955 batch is reviewable and publishable** - checkpoint:human-verify, no code change; user completed the SQL + UI verification steps and replied "approved".

**Plan metadata:** (this commit) — docs: complete plan

## Files Created/Modified
None — this plan is an operator runbook only (D-02); no source files were created or modified.

## Decisions Made
- No committed migration/backfill script (D-02 upheld) — the fix is entirely the ad hoc scoped wipe SQL plus a re-run of the existing idempotent import CLI.
- The mid-execution `MultipleResultsFound` blocker was resolved as its own scoped, verified DELETE (distinct from this plan's convokit_import-scoped wipe) rather than folded into this plan's runbook, and escalated to ROADMAP.md backlog Phase 999.19 for the underlying root-cause fix (dedicated test DB / savepoint-based test isolation for tests that call commit-invoking service functions).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pre-existing test-data leakage blocked `import-justices` mid-runbook; resolved with a separate scoped DELETE**
- **Found during:** Task 1 (operator wipe + re-import)
- **Issue:** After the term-1955 corpus wipe completed cleanly, `python -m pipeline import-justices` failed with `sqlalchemy.exc.MultipleResultsFound` on a duplicate `Person.full_name = 'Ketanji Brown Jackson'` lookup (`pipeline/commands/import_justices_csv.py:182`). This was unrelated to the plan's own convokit_import-scoped wipe predicate, which never touches `Person` rows.
- **Root cause:** Earlier full-suite pytest runs (part of the Phase 30 Wave 1 lifespan/session-factory bug fix — see backlog Phase 999.17, now fixed) exercised DB-gated tests whose fixtures roll back the test's own writes but do NOT undo commits made internally by production service functions those tests call (e.g. `create_person_for_job`). Three full-suite runs left 18 leaked `Person` rows (three duplicate "Ketanji Brown Jackson" rows plus synthetic test names) and 15 fully-synthetic `Argument` rows (no docket, no argued_date, no utterances, no pipeline_runs) in the shared dev database.
- **Fix:** A separate, scoped, verified DELETE — confirmed each of the 18 extra `Person` rows and 15 `Argument` rows was zero-content synthetic test data before removing them, preserving the one legitimate "Ketanji Brown Jackson" `Person` row (the one with a real `court_tenures` record). This is a stopgap cleanup, not a fix for the underlying test-isolation gap.
- **Files modified:** None (data-only DB cleanup; no source files touched).
- **Verification:** After cleanup, `import-justices` ran cleanly (0 created, 0 upgraded — idempotent) and `import-convokit --term 1955` completed with the expected counts (see Accomplishments).
- **Escalated to:** ROADMAP.md backlog Phase 999.19 ("Audit ~28 stale DB-gated test fixtures + fix real data leakage into the shared dev DB") already captures this exact incident in full detail (added 2026-07-10, escalated 2026-07-10 during this plan's execution) — the underlying test-isolation defect needs its own investigation/fix (dedicated test DB, autouse snapshot/restore fixture, or savepoint-based nesting), tracked there rather than in this plan's scope.

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking, resolved via a separate scoped DELETE; root cause escalated to backlog rather than fixed in-plan since it is out of this plan's file/data scope).
**Impact on plan:** None on this plan's own deliverable — the term-1955 wipe-and-rerun completed exactly per the runbook once the unrelated blocker was cleared. No scope creep: the underlying test-isolation defect was deliberately NOT fixed here and instead tracked as its own backlog item.

## Issues Encountered
- Mid-execution `MultipleResultsFound` in `import-justices` — see Deviations above. Resolved by a scoped DELETE of leaked test data; import re-run succeeded cleanly afterward.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 30 is now complete (4/4 plans). The D-02 stored-data gap is closed: all term-1955 corpus arguments are `status=PIPELINE` with paired paused/resolve AdminJobs, visible in `/admin/pipeline/` with the Corpus source tag, editable via ResolveCard, and demonstrably resolve→approve→publish-eligible.
- Backlog Phase 999.19 (test-data leakage into the shared dev DB) remains open and should be prioritized before the next full pytest suite run touches DB-gated tests that call commit-invoking service functions, to avoid repeating this incident against future corpus batches or other shared-DB workflows.

---
*Phase: 30-corpus-import-resolve-workflow*
*Completed: 2026-07-10*

## Self-Check: PASSED
- FOUND: .planning/phases/30-corpus-import-resolve-workflow/30-04-SUMMARY.md
- N/A: No code commits to verify — both tasks were checkpoints (files_modified: [] per plan frontmatter, D-02 operator runbook)
