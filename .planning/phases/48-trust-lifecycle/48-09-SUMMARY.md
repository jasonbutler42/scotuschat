---
phase: 48-trust-lifecycle
plan: 09
subsystem: database
tags: [postgresql, sqlalchemy, pytest, trust-tier, evidence, audit-log-ordering]

# Dependency graph
requires:
  - phase: 48-trust-lifecycle
    plan: "01"
    provides: "api.domain.trust.derive_tier/floor_tier and the recompute_argument_tier service this plan's zero-drift proof exercises against live data"
  - phase: 48-trust-lifecycle
    plan: "02"
    provides: "the delete_argument -> argument_status_log cascade fix (D-22), traced in this plan's requirement-traceability table"
  - phase: 48-trust-lifecycle
    plan: "07"
    provides: "the two-gate publish gate and get_argument_detail's trust_tier/status_log fields, whose ordering this plan found and fixed a bug in"
  - phase: 48-trust-lifecycle
    plan: "10"
    provides: "the completed UI surface (list + detail pages) this plan's operator walkthrough exercised live"
provides:
  - "48-EVIDENCE.md — the phase's evidence-of-record: live reseed transcript, zero-drift proof (recompute-trust --all, 4 scanned / 0 changed, twice), full-suite gate (1209 passed / 5 xfailed / 0 failed / 0 skipped), completeness greps, Wave 0 confirmation, TRUST-01..05/D-22/D-23 traceability table, two findings, and a recorded operator sign-off"
  - "get_argument_detail's Status History query now orders by ArgumentStatusLog.id ASC (not created_at ASC) — id is the only monotonic, transaction-timing-independent key for an append-only audit log"
  - "A regression test constructing an explicit created_at/insertion-order skew, locking the id-primary ordering"
  - "api.domain.trust's derive_tier rule 3 (operator+manual -> VERIFIED) is now an operator-confirmed derivation rule, closing plan 48-01's flagged assumption"
  - "Two new recorded open items: the corpus-fixture UNCERTAIN reading (Finding 1, not a defect) and the requested Resolve-card editability-scope widening (operator observation, deliberately deferred)"
affects: [49-review-model]

# Actuals (#2632)
actuals:
  tokens: 10018
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "id-primary ordering for append-only audit-log tables: PostgreSQL's now()/CURRENT_TIMESTAMP (and any server_default=func.now() column) reflects the enclosing TRANSACTION's start time, not per-statement wall-clock time, so a writer that reuses one long-lived session/transaction across several later writes can produce a created_at value that is chronologically EARLIER than a row inserted before it. An auto-increment primary key (id) is the only column guaranteed monotonic with true insertion order regardless of transaction timing; any append-only log table's canonical-order query should sort by id primarily, using created_at only as a display/secondary field, never as the primary sort key."
    - "Explicit-skew regression test for ordering bugs: rather than depending on reset/import timing to reproduce a timestamp anomaly, construct the skew directly (raw UPDATE on created_at after insertion) so the regression test is deterministic and independent of any particular writer's transaction behavior."

key-files:
  created:
    - .planning/phases/48-trust-lifecycle/48-EVIDENCE.md
  modified:
    - api/services/admin_arguments.py
    - api/tests/test_admin_arguments_service.py
    - api/domain/trust.py

key-decisions:
  - "Fixed the Status History display-ordering bug (Finding 2's first half) discovered during this plan's own live evidence-gathering, under explicit operator/coordinator direction mid-plan: api/services/admin_arguments.py's get_argument_detail now orders argument_status_log by id ASC only. Confirmed RED against the pre-fix created_at-first ordering (assertion failed, returned draft-before-candidate) before restoring the fix and confirming GREEN — a genuine regression-test discipline, not an assumed fix."
  - "Did NOT touch reset_to_fixture's underlying session/transaction reuse (the root cause of the stale created_at/resolved_at VALUES themselves) — explicitly out of scope per operator direction (dev-only tool; filed as a separate todo by the orchestrator: .planning/todos/pending/2026-08-20-reset-to-fixture-stale-created-at-timestamps.md). The display fix corrects how existing data is ORDERED; it does not correct what value is STORED."
  - "Checked two other created_at-first queries (admin_jobs.py's list_jobs and get_run_id_for_step) for the same shape and did NOT change either — list_jobs orders distinct AdminJob entities each normally created in separate transactions (different failure-mode exposure than a single entity's append-only log), and get_run_id_for_step's ImportRun writes run as separate CLI-subprocess transactions with no live reproduction of the defect today. Recorded as follow-up candidates rather than fixed speculatively, per the explicit instruction to fix only the same one-line shape with a clearly-demonstrated defect."
  - "Finding 1 (15169 and 22372 read trust_tier=uncertain, not trusted, contradicting the plan's own must-have) is recorded as NOT a Phase 48 code defect. derive_tier/floor_tier/recompute_argument_tier are all working exactly as D-07/D-11/D-12 specify; the plan's assumption ('corpus import mints a Person for every corpus speaker') does not hold against ConvoKit's own unattributed-speaker sentinel rows (pipeline/commands/import_convokit.py:1043-1150, pre-existing since Phase 29). The zero-drift proof (4 scanned, 0 changed, twice) held regardless — the tier is stable and correctly derived from real constituent data, just not the tier the plan expected for these two fixtures."
  - "derive_tier's rule 3 (source=operator, method=manual -> VERIFIED) — flagged as a planner assumption in plan 48-01 pending operator confirmation — was CONFIRMED by the operator on 2026-08-21 at this plan's Task 3 checkpoint. api/domain/trust.py's module and function docstrings updated to record the confirmation (wording only; derivation logic unchanged and re-verified unchanged via the full Wave 0 suite)."
  - "Operator requested widening Resolve-card editability from CANDIDATE-only to {candidate, draft, unpublished} (published stays read-only), observed live at the Task 3 checkpoint (step 2). Recorded as a new, detailed open item in 48-EVIDENCE.md and a standalone todo, deliberately NOT implemented in this plan — it is a design-scope change to a documented, deliberate pre-existing invariant (api/services/admin_dev.py's fixture comments), not a bug, and it has real cross-cutting consequences (recompute_argument_tier coverage on newly-reachable write paths, several non-editability CANDIDATE-only guards in admin_jobs.py that must NOT be touched by any future mechanical fix)."

patterns-established:
  - "id-primary ordering for append-only audit-log tables (see tech-stack.patterns above) — the canonical fix pattern for any future table exhibiting the same func.now()-transaction-start-time hazard."

requirements-completed: [TRUST-01, TRUST-02, TRUST-03, TRUST-04, TRUST-05]

coverage:
  - id: D1
    description: "Live reseed through the real service functions (run_import_convokit, approve_job, publish_argument) drives all four fixtures to their target states, and recompute-trust --all reports 4 scanned / 0 changed, twice in a row — the phase's central falsifiable zero-drift claim."
    requirement: "TRUST-02"
    verification:
      - kind: other
        ref: "./.venv/bin/python -m pipeline recompute-trust --all (48-EVIDENCE.md §4, run twice)"
        status: pass
      - kind: integration
        ref: "api/tests/test_trust_recompute.py (18 passed)"
        status: pass
    human_judgment: true
    rationale: "must_haves' own verification: backstop truth — a zero-changed result is only as strong as the scanned count being right, which no automated check can independently prove enumerated the correct rows. The operator confirmed this live at Task 3 checkpoint step 5 (scanned=4 matching the fixture count)."
  - id: D2
    description: "The Complexity and Mid-pipeline fixtures are born at status=candidate with exactly one born-state argument_status_log row each, oldest by construction; the Draft and Published fixtures show the birth transition as their oldest status-log entry after the id-ordering fix."
    requirement: "TRUST-03"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_core.py (39 passed)"
        status: pass
      - kind: other
        ref: "48-EVIDENCE.md §3 fixture state table (direct DB query, post-reseed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The two-gate publish (non-overridable resolved_at gate, then the overridable UNCERTAIN trust gate with a required, permanently-logged, non-sticky reason) is proven both by pytest and by the live Published fixture reaching published through the real service."
    requirement: "TRUST-04"
    verification:
      - kind: integration
        ref: "api/tests/test_published_gate.py (31 passed)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Operator override path (required non-blank reason, structured 422 codes, audit-row contents) proven at the route level; the admin detail contract's trust_tier exposure is confirmed live on the Draft/Published fixtures without any leak onto public responses."
    requirement: "TRUST-05"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_arguments_routes.py (29 passed)"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 checkpoint step 4 (operator browser walkthrough) — Published fixture publicly visible with no trust/tier/provenance on the page"
        status: pass
    human_judgment: false
  - id: D5
    description: "delete_argument's argument_status_log cascade fix (D-22, carried defect) and the public trust-tier leak ban (D-23) both re-confirmed green at phase close."
    verification:
      - kind: integration
        ref: "api/tests/test_admin_arguments_service.py::test_delete_argument_cascades_argument_status_log, ::test_delete_argument_cascades_multiple_status_log_rows (2 passed); api/tests/test_trust_public_leak_ban.py (11 passed)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full-suite phase gate: 1209 passed / 5 xfailed / 0 failed / 0 skipped (up from the 2026-08-18 baseline of 1049); build (compileall) clean; frontend check (npm run check) 0 errors / 36 pre-existing warnings; both PIPELINE-born-state completeness greps empty; 32 deliberate test-fixture references confirmed still present for the retired enum value."
    verification:
      - kind: other
        ref: "./.venv/bin/python -m pytest (48-EVIDENCE.md §6a, second/final run); python3 -m compileall -q pipeline api scripts tests alembic; cd app && npm run check"
        status: pass
    human_judgment: false
  - id: D7
    description: "Status History display-ordering bug found via this plan's own live evidence-gathering (Finding 2, first half): get_argument_detail's argument_status_log query ordered by created_at first, which can invert insertion order for any writer batching a later write into a transaction opened earlier by an unrelated read. Fixed to order by id ASC; regression test confirmed RED against the old ordering and GREEN against the fix; operator re-confirmed correct rendering live at Task 3 checkpoint step 3."
    verification:
      - kind: integration
        ref: "api/tests/test_admin_arguments_service.py::test_get_argument_detail_status_log_orders_by_id_not_created_at"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 checkpoint step 3 (operator browser walkthrough, confirmed after commit 1b7564a78)"
        status: pass
    human_judgment: false
  - id: D8
    description: "Finding 1: two of the four live corpus fixtures (15169, 22372) read trust_tier=uncertain rather than trusted, contradicting this plan's own stated must-have. Investigated and traced to ConvoKit's genuine unattributed-speaker sentinel rows in the real corpus data — derive_tier/floor_tier/recompute_argument_tier are all working correctly; the plan's 'corpus mints a Person for every speaker' assumption does not hold universally. Not a Phase 48 code defect. Accepted by the operator as an open item at Task 3 checkpoint step 6."
    verification: []
    human_judgment: true
    rationale: "A policy/expectation judgment (is an UNCERTAIN reading on real corpus data acceptable, or does it indicate a defect?), not something any automated check can adjudicate. The operator's acceptance at the Task 3 checkpoint is the closing evidence, recorded verbatim in 48-EVIDENCE.md §8."
  - id: D9
    description: "derive_tier's rule 3 (source=operator, method=manual -> VERIFIED), flagged as a planner assumption pending operator confirmation since plan 48-01, was confirmed by the operator on 2026-08-21 at this plan's Task 3 checkpoint. api/domain/trust.py's docstrings updated to record the confirmation; derivation logic unchanged."
    requirement: "TRUST-01"
    verification: []
    human_judgment: true
    rationale: "A policy confirmation of an unreachable-today derivation rule requires the operator's own judgment call, not an automated check — this is exactly the flagged assumption plan 48-01 deferred to this checkpoint."
  - id: D10
    description: "Operator-requested widening of Resolve-card editability scope (editable in candidate/draft/unpublished, read-only only when published) observed live at Task 3 checkpoint step 2. Recorded in full (current-rule sites, requested rule, two critical caveats about non-editability CANDIDATE-only guards and recompute coverage on newly-reachable write paths, and the pre-existing-invariant note) as a new open item and a standalone todo. Deliberately NOT implemented in this plan."
    verification: []
    human_judgment: true
    rationale: "A design-scope change to a deliberate, documented pre-existing invariant, requiring its own discussion/plan cycle — not something this evidence-and-closeout plan is scoped to implement or that any automated check could validate."

duration: "~1h active work across 2 sessions (2026-08-20T12:26 to 2026-08-21T09:23 elapsed, including an overnight pause at the Task 3 checkpoint awaiting operator sign-off)"
completed: 2026-08-21
status: complete
---

# Phase 48 Plan 09: Live Fixture Reseed, Zero-Drift Proof, Full-Suite Gate, and Operator Sign-Off Summary

**Live-data evidence and phase close-out: a real four-fixture corpus reseed proves `recompute-trust --all` changes 0 of 4 arguments twice in a row, the full suite grew to 1209 passed / 0 failed / 0 skipped, a genuine display-ordering bug this plan's own evidence-gathering surfaced was found, root-caused, fixed, and regression-tested before sign-off, and the operator closed out plan 48-01's flagged `derive_tier` assumption while opening one new, fully-scoped follow-up item.**

## Performance

- **Duration:** ~1h active work across 2 sessions (2026-08-20T12:26 → 2026-08-21T09:23 elapsed, including an overnight pause at the Task 3 checkpoint awaiting operator sign-off)
- **Tasks:** 3/3 complete (plus one coordinator-directed fix round folded into Task 3 before sign-off)
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- `48-EVIDENCE.md` created: the phase's evidence-of-record. Live reseed through the real service functions (`run_import_convokit`, `approve_job`, `publish_argument`) lands all four fixtures at their target states; `recompute-trust --all` reports **4 scanned, 0 changed** — twice in a row — the phase's central, falsifiable proof that every writer path stamps `trust_tier` correctly at write time.
- Full-suite phase gate: **1209 passed, 5 xfailed, 0 failed, 0 skipped** (baseline was 1049 at 2026-08-18; 1208 immediately before this plan's own fix added one more test). Build (`compileall`) clean. `npm run check`: 0 errors, 36 pre-existing warnings (unchanged). Both completeness greps for the retired `PIPELINE` born state return empty; 32 deliberate test-fixture references confirmed still present. TRUST-01 through TRUST-05, D-22, and D-23 all traced to a named, green, runnable check.
- **Genuine bug found via this plan's own live evidence-gathering, fixed under explicit operator/coordinator direction, before sign-off:** `get_argument_detail`'s Status History query ordered `argument_status_log` by `created_at ASC` first. Because PostgreSQL's `now()`/`server_default=func.now()` reflects the enclosing *transaction's* start time rather than per-statement wall-clock time, a writer that reuses one long-lived session/transaction (`reset_to_fixture`'s fixture-verification loop is the live case that surfaced it) can produce a `created_at` value chronologically *earlier* than a row inserted before it — inverting the operator-facing display. Fixed to order by `id ASC` (the only monotonic, transaction-timing-independent key); a regression test constructing the exact skew explicitly was confirmed RED against the old ordering and GREEN against the fix, and the operator re-confirmed correct rendering live.
- Two additional research findings recorded honestly rather than smoothed over: (1) two of the four live corpus fixtures read `trust_tier=uncertain` rather than the plan's expected `trusted`, traced to ConvoKit's own genuine unattributed-speaker rows — not a Phase 48 defect, and the plan's underlying assumption was wrong, not the code; (2) the underlying stale-timestamp *storage* cause in `reset_to_fixture` (as opposed to its display-ordering symptom, which is fixed) remains open by explicit operator direction and is tracked as a separate dev-only todo.
- Operator sign-off obtained: all 7 verification steps passed, including confirming `derive_tier`'s rule 3 (`operator`+`manual` → `VERIFIED`) — closing plan 48-01's flagged assumption — and a new, fully-scoped open item (Resolve-card editability widening) recorded for future planning rather than implemented here.

## Task Commits

1. **Task 1: Live reseed and the zero-drift proof** + **Task 2: Phase gate (full suite, completeness greps, requirement traceability)** — `48fc00e66` (docs) — both tasks write the single evidence file, committed together.
2. **Task 3, fix round (coordinator-directed): Status History `id`-ordering fix + regression test** — `1b7564a78` (fix)
3. **Task 3: Operator sign-off recorded; `derive_tier` rule 3 confirmed** — `f9bcbed90` (docs)

**Plan metadata:** (this commit) — `docs(48-09): complete plan`

## Files Created/Modified

- `.planning/phases/48-trust-lifecycle/48-EVIDENCE.md` (new) — environment record, reseed transcript, fixture state table, zero-drift proof (×2), two findings, full-suite/build/frontend gate results, completeness greps, Wave 0 confirmation, requirement traceability table, open items (including the two new ones from the Task 3 checkpoint), and the recorded operator sign-off.
- `api/services/admin_arguments.py` — `get_argument_detail`'s status-log query now orders by `ArgumentStatusLog.id.asc()` only (was `created_at.asc(), id.asc()`); explanatory comment added.
- `api/tests/test_admin_arguments_service.py` — new regression test `test_get_argument_detail_status_log_orders_by_id_not_created_at`, constructing an explicit `created_at`/insertion-order skew.
- `api/domain/trust.py` — module and function docstrings updated to record rule 3's operator confirmation (2026-08-21); derivation logic unchanged, re-verified unchanged via the full Wave 0 suite (62 passed).

## Decisions Made

See `key-decisions` in frontmatter. Summarized:
- Fixed the Status History `created_at`-first ordering bug (found via this plan's own live evidence-gathering) under explicit direction, with full RED→GREEN regression-test discipline; did not touch `reset_to_fixture`'s underlying transaction-reuse root cause (dev-only, out of scope, filed separately).
- Checked two other `created_at`-first queries in `admin_jobs.py` for the same shape; left both unchanged and recorded as follow-up candidates rather than fixed speculatively.
- Recorded Finding 1 (two corpus fixtures reading `uncertain`) as a plan-assumption error, not a code defect — `derive_tier` is correct.
- Recorded the operator's confirmation of `derive_tier` rule 3, closing plan 48-01's flagged assumption.
- Recorded, but deliberately did not implement, the operator's requested widening of Resolve-card editability scope — a design-scope change requiring its own future plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug, found via this plan's own live evidence-gathering] Status History displayed the wrong order for a multi-transition argument**
- **Found during:** Task 1/2's live reseed and fixture-state query — the Draft fixture's `argument_status_log` rows sorted by the plan's own mandated `created_at ASC, id ASC` inverted the born-state-first invariant.
- **Issue:** `get_argument_detail`'s status-log query (`api/services/admin_arguments.py:~448`) used `created_at` as the primary sort key. PostgreSQL's `now()` reflects transaction-start time, not per-statement time; `reset_to_fixture` reuses one long-lived session across its per-fixture verification loop, so the first write on that session after the loop (the Draft fixture's `approve_job` call) got a stale, transaction-start `created_at`/`resolved_at` — chronologically earlier than the fixture's own already-committed birth log.
- **Fix:** Changed the ordering to `ArgumentStatusLog.id.asc()` only. Added a regression test constructing the exact skew explicitly (independent of any reset timing), confirmed RED against the old ordering, restored the fix, confirmed GREEN. Checked two structurally similar queries in `admin_jobs.py` and left them unchanged (not clearly the same defect — see key-decisions). Did not touch `reset_to_fixture` itself (separate, dev-only root cause, filed as its own todo).
- **Files modified:** `api/services/admin_arguments.py`, `api/tests/test_admin_arguments_service.py`
- **Verification:** `./.venv/bin/python -m pytest api/tests/test_admin_arguments_service.py::test_get_argument_detail_status_log_orders_by_id_not_created_at` (RED then GREEN); full suite re-run clean (1209 passed); operator re-confirmed live at the Task 3 checkpoint.
- **Committed in:** `1b7564a78` (fix)

---

**Total deviations:** 1 auto-fixed (Rule 1, found via this plan's own live verification and fixed under explicit direction).
**Impact on plan:** A genuine, previously-invisible display bug caught exactly because this plan ran real evidence-gathering against real data rather than trusting the plan's own assumptions — the textbook case for why the live-vehicle half of D-21's verification split exists. No scope creep: the fix is one query's sort order plus its regression test; the underlying dev-only root cause was explicitly left for separate follow-up.

## Issues Encountered

- Cleaning up a leftover test row from an intentional RED-verification run (reverting the fix, running the test to confirm it failed, then restoring the fix) required a small standalone script against `TEST_DATABASE_URL` rather than the app's own `AsyncSessionLocal` (which is only initialized under FastAPI's lifespan, unavailable outside a pytest run). No lasting effect — confirmed clean before proceeding.
- The full suite ran markedly slower this session (~240-325s) than 48-VALIDATION.md's ~120s estimate; not investigated further since it did not affect correctness, and both runs completed and reported cleanly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Phase 48 (Trust & Lifecycle) is now COMPLETE.** All five requirements (TRUST-01 through TRUST-05) are traced to named, green, automated checks, plus the D-22 carried-defect fix and the D-23 public-leak-ban contract. The live corpus-born happy path is proven end to end on real data with a zero-drift result, and the operator has signed off on all seven live-verification steps.
- Three of this phase's defects were found by **operator browser testing**, not by the automated suite: the silent list-page 422 swallow (48-10), the unpublish/public-visibility gap across three read paths (48-10), and the shared-`form` error-routing bug on the detail page affecting both publish and unpublish (48-10). The suite grew from 1114 (pre-phase) to 1209 (this plan's final count) tests across the phase and passed clean over all three fixes — worth stating plainly rather than implying the automated suite alone caught everything.
- The unpublish-error-rendering fix (48-10) remains verified by static contract test only, never observed live — the failure path requires the backend call itself to fail, which is not reachable from any UI state the operator can produce. Recorded, not upgraded to "verified."
- Two open items now carry forward as explicit, standalone todos rather than being folded into this closeout: `.planning/todos/pending/2026-08-20-reset-to-fixture-stale-created-at-timestamps.md` (the underlying stale-value root cause in `reset_to_fixture`, dev-only) and `.planning/todos/pending/2026-08-21-widen-participant-editability-to-all-unpublished-states.md` (the operator-requested Resolve-card editability widening).
- 14-UAT Test 8 and 26-UAT Test 26 remain open, but this plan's Finding 1 shows the reason D-21 gave for not closing them (corpus import supposedly mints a Person for every speaker) does not fully hold — worth a look before assuming new fixture work is required.
- Phase 49 (review model) inherits a working `trust_tier` field, a correctly-ordered Status History, and a confirmed `derive_tier` rule set with no outstanding flagged assumptions.

---
*Phase: 48-trust-lifecycle*
*Completed: 2026-08-21*
