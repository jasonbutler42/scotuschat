---
phase: 48-trust-lifecycle
plan: 04
subsystem: api
tags: [sqlalchemy, postgresql, pytest, trust-tier, argument-status, admin-jobs]

requires:
  - phase: 48-trust-lifecycle
    plan: 01
    provides: "ArgumentStatusEnum.CANDIDATE, Argument.trust_tier column, and the non-committing api.services.trust.recompute_argument_tier(db, argument_id) helper"
provides:
  - "Every admin-side PIPELINE->CANDIDATE editability guard swapped (list_jobs, approve_job, get_job_readiness, update_resolve_row_for_job, list_resolve_rows_for_job) plus the ninth TypeScript readonlyMode guard on the job detail page"
  - "recompute_argument_tier wired into all four admin_jobs writer paths (resolve_job, approve_job, update_resolve_row_for_job, create_person_for_job), each call strictly before that function's own commit"
  - "Six DB-gated regression tests locking both the vocabulary swap and the recompute wiring in api/tests/test_admin_jobs_service.py"
affects: ["48-05 (pipeline/commands/import_convokit.py's remaining birth-write scope: ArgumentStatusLog write + recompute call)", "48-06 (publish gate consumes the now-correctly-recomputed tier)", "48-09 (recompute-trust --all zero-rows-changed verification depends on every writer, including these four, stamping correctly)"]

actuals:
  tokens: 13450
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "recompute_argument_tier called before the writer's own db.commit() in every one of the four admin_jobs writers, verified programmatically via AST + the existing _service_function_source_lines helper rather than by eye"
    - "DB-gated regression tests re-read committed state from a fresh AsyncSessionLocal() rather than asserting against an in-session object, matching api/tests/test_trust_recompute.py's shape"

key-files:
  created: []
  modified:
    - api/services/admin_jobs.py
    - api/services/admin_people.py
    - api/schemas/admin_people.py
    - api/services/admin_dev.py
    - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
    - api/tests/test_admin_jobs_service.py
    - api/tests/test_admin_jobs_list.py
    - api/tests/test_admin_jobs_phase25.py
    - api/tests/test_phase44_argument_role_roundtrip.py
    - api/tests/test_admin_dev_routes.py
    - pipeline/commands/import_convokit.py
    - pipeline/tests/test_import_convokit_core.py
    - pipeline/tests/test_import_convokit_adminjob.py

key-decisions:
  - "Rule 3 blocking-issue fix: pipeline/commands/import_convokit.py's explicit status=ArgumentStatusEnum.PIPELINE birth-write kwarg (48-05's declared scope) does not inherit the model-default change from 48-01, so leaving it untouched made every guard swap in this plan regress the corpus-import-to-approve workflow (approve_job now rejects a PIPELINE-born argument). Flipped this one kwarg to CANDIDATE to keep the guard swap internally consistent; the rest of 48-05's birth-write scope (ArgumentStatusLog write, recompute call, full docstring rewrite) is untouched. Recorded in .planning/WINDOWS.md (kind=deviation) so 48-05's executor knows this line is already done."
  - "That fix rippled into several test files outside this plan's declared file list (test_admin_jobs_list.py, test_admin_jobs_phase25.py, test_phase44_argument_role_roundtrip.py, test_admin_dev_routes.py, pipeline/tests/test_import_convokit_core.py, test_import_convokit_adminjob.py) which hardcoded PIPELINE as the live 'freshly created' state to exercise the exact guards this plan swapped. Updated them to CANDIDATE (Rule 1 — the guard swap made their fixture assumption a bug); left every genuine dead-value regression fixture (e.g. test_admin_jobs_service.py:154, test_delete_argument_returns_false_for_pipeline) untouched."
  - "Renamed test_approve_job_accepts_freshly_created_argument_and_rejects_second_call to test_approve_job_accepts_freshly_created_candidate_and_rejects_second_call so the plan's own acceptance-criteria grep (-k 'candidate or editable', expects 3+) matches all three vocabulary-block tests it names — a plan-authoring inconsistency between the action text's test name and its own filter, corrected without changing test behavior."
  - "Task 3's tests were written after Tasks 1-2's implementation already existed (both committed first), so no RED-then-GREEN split was performed — see TDD Gate Compliance note below, following the same precedent as 48-01 Plan's Task 3."

requirements-completed: [TRUST-02, TRUST-03]

coverage:
  - id: D1
    description: "Every production comparison against the retired ArgumentStatusEnum.PIPELINE member in api/ and app/src now compares against CANDIDATE; surviving references are the enum declaration and deliberate dead-value test fixtures."
    requirement: "TRUST-03"
    verification:
      - kind: other
        ref: "grep -rn \"ArgumentStatusEnum\\.PIPELINE\" api/ pipeline/ scripts/ --include=*.py | grep -v /tests/ | grep -v models.py | grep -v comment -> empty; grep -rnE \"status *[!=]== *'pipeline'\" app/src -> empty"
        status: pass
    human_judgment: false
  - id: D2
    description: "update_resolve_row_for_job accepts an edit on a freshly-created (candidate) argument and rejects one once the argument has left that state, with an error message naming the born state."
    requirement: "TRUST-03"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_jobs_service.py::test_update_resolve_row_accepts_candidate_and_rejects_draft"
        status: pass
    human_judgment: false
  - id: D3
    description: "list_resolve_rows_for_job reports editable=True for a freshly-created argument and editable=False once approved; the job detail page's readonlyMode TypeScript literal (a ninth guard site outside 48-RESEARCH.md's Python-only inventory) was also swapped."
    requirement: "TRUST-03"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_jobs_service.py::test_list_resolve_rows_editable_flag_tracks_candidate_state"
        status: pass
      - kind: other
        ref: "grep -n candidate app/src/routes/admin/pipeline/[job_id]/+page.server.ts"
        status: pass
    human_judgment: false
  - id: D4
    description: "approve_job's double-approve guard is swapped, not removed: a freshly-created argument approves once and a second approve raises ValueError naming the already-DRAFT state."
    requirement: "TRUST-03"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_jobs_service.py::test_approve_job_accepts_freshly_created_candidate_and_rejects_second_call"
        status: pass
    human_judgment: false
  - id: D5
    description: "All four admin_jobs writers (resolve_job, approve_job, update_resolve_row_for_job, create_person_for_job) call recompute_argument_tier before their own commit, verified by AST source-order inspection, not by eye; resolve_job calls it exactly once for the whole match batch, not once per match."
    requirement: "TRUST-02"
    verification:
      - kind: other
        ref: "AST checks in this session: recompute_argument_tier present in all four function bodies; source-line index of recompute_argument_tier < db.commit in each; resolve_job's body contains exactly one recompute_argument_tier call"
        status: pass
    human_judgment: false
  - id: D6
    description: "approve_job on a fully-resolved corpus/direct argument stamps trust_tier='trusted' (not the 'uncertain' server default); resolve_job filling the last NULL person_id moves the tier from uncertain to trusted in the same transaction as the person_id writes; a repeated writer call with no constituent change leaves the tier unchanged (idempotence/adjacency edge)."
    requirement: "TRUST-02"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_jobs_service.py::test_approve_job_stamps_trust_tier, test_resolve_job_recomputes_tier_when_last_speaker_resolves, test_repeated_writer_call_leaves_tier_unchanged"
        status: pass
    human_judgment: false
  - id: D7
    description: "Candidates remain hard-excluded from /admin/arguments with no code change (D-04) — list_arguments/get_argument_stats keep their positive DRAFT/PUBLISHED/UNPUBLISHED allow-list."
    requirement: "TRUST-03"
    verification:
      - kind: other
        ref: "Read api/services/admin_arguments.py this session — list_arguments/get_argument_stats' in_([DRAFT, PUBLISHED, UNPUBLISHED]) allow-list untouched by this plan"
        status: pass
    human_judgment: false

duration: ~50min
completed: 2026-08-19
status: complete
---

# Phase 48 Plan 04: Retire PIPELINE Vocabulary & Wire Trust-Tier Recompute Summary

**Swapped every admin-side PIPELINE->CANDIDATE editability guard (five Python comparisons, one TypeScript literal) and wired `recompute_argument_tier` into all four `admin_jobs` writer paths, each call verified programmatically to sit before that writer's own commit.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 3/3 complete
- **Files modified:** 13 (2 production API files beyond the plan's declared scope required updating due to a genuine cross-plan sequencing gap — see Deviations)

## Accomplishments
- `api/services/admin_jobs.py` — `list_jobs`, `approve_job`, `get_job_readiness`, `update_resolve_row_for_job` all compare against `ArgumentStatusEnum.CANDIDATE` instead of the retired `PIPELINE` member; docstrings and the resolve-row error message corrected to name the new born state.
- `api/services/admin_people.py::list_resolve_rows_for_job` and `api/schemas/admin_people.py`'s `editable` field docstring likewise corrected.
- `api/services/admin_dev.py`'s `reset_to_fixture` per-fixture comments renamed (comment-only, no executable change).
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts`'s `readonlyMode` literal swapped from `'pipeline'` to `'candidate'` — the ninth guard site, outside 48-RESEARCH.md's Python-only inventory, that would otherwise have rendered the Resolve card read-only on every freshly imported job's detail page.
- `recompute_argument_tier` imported and called in `resolve_job` (once per batch), `approve_job`, `update_resolve_row_for_job`, and `create_person_for_job` — every call sits strictly before that function's own `db.commit()`, verified via AST inspection using the same `_service_function_source_lines` helper `test_published_gate.py` already defines.
- Six new DB-gated regression tests in `api/tests/test_admin_jobs_service.py` lock both the vocabulary swap and the recompute wiring; each re-reads state from a fresh session and tears down its seeded rows (including `resolve_job`'s `SpeakerAlias` upsert) in FK order inside a `finally` block.
- Completeness grep across `api/`, `pipeline/`, `scripts/` (Python) and `app/src` (TypeScript) confirms no live comparison against the retired `PIPELINE` state remains.
- Full suite: 1136 passed, 5 xfailed, 1 known-expected failure (`test_admin_detail_contract_does_declare_trust_tier`, tracked since 48-03, resolves at 48-07), 0 new/unexpected failures.

## Task Commits

Each task was committed atomically:

1. **Task 1: Retire the old born-state vocabulary at every production guard site** - `2aa53b16f` (feat)
2. **Task 2: Wire in-transaction recompute into all four admin_jobs writer paths** - `eaadc2483` (feat)
3. **Task 3: DB-gated regression coverage for the vocabulary swap and the recompute wiring** - `0f976f191` (test)

**Plan metadata:** (this commit) — `docs(48-04): complete plan`

## Files Created/Modified
- `api/services/admin_jobs.py` - Five `PIPELINE`->`CANDIDATE` guard swaps + `recompute_argument_tier` wired into `resolve_job`/`approve_job`/`update_resolve_row_for_job`/`create_person_for_job` (Tasks 1-2)
- `api/services/admin_people.py` - `list_resolve_rows_for_job`'s `editable` guard swapped (Task 1)
- `api/schemas/admin_people.py` - `editable` field docstring corrected (Task 1)
- `api/services/admin_dev.py` - `reset_to_fixture` comments renamed, no executable change (Task 1)
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` - `readonlyMode` literal swapped (Task 1)
- `api/tests/test_admin_jobs_service.py` - Six new DB-gated tests (Task 3) plus two pre-existing PIPELINE-fixture tests updated to CANDIDATE (Task 1 deviation)
- `pipeline/commands/import_convokit.py` - Birth-write `status=` kwarg flipped to `CANDIDATE` (Task 1 deviation, Rule 3 — see below)
- `api/tests/test_admin_jobs_list.py`, `api/tests/test_admin_jobs_phase25.py`, `api/tests/test_phase44_argument_role_roundtrip.py`, `api/tests/test_admin_dev_routes.py`, `pipeline/tests/test_import_convokit_core.py`, `pipeline/tests/test_import_convokit_adminjob.py` - PIPELINE-as-live-state test fixtures/source-guard assertions updated to CANDIDATE (Task 1 deviation)

## Decisions Made
- See `key-decisions` in frontmatter for the full reasoning on the Rule 3 blocking-issue fix to `pipeline/commands/import_convokit.py` and its test-file ripple, the acceptance-criteria-driven test rename, and the TDD sequencing note.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `pipeline/commands/import_convokit.py`'s birth-write status kwarg still said PIPELINE**
- **Found during:** Task 1's own `<verify>` run (`pytest api/tests/test_admin_jobs_service.py api/tests/test_admin_jobs_list.py api/tests/test_admin_people.py api/tests/test_admin_dev_routes.py`) — 9 failures.
- **Issue:** `import_convokit.py:515` passes `status=ArgumentStatusEnum.PIPELINE` explicitly; this kwarg does not inherit 48-01's changed model default. This file/edit is plan 48-05's declared scope (its Task 1 flips this exact kwarg alongside a new `ArgumentStatusLog` birth-write and a `recompute_argument_tier` call). Because 48-04 executes before 48-05 in this sequential run, every corpus-import-created fixture (used by `api/services/admin_dev.py::reset_to_fixture`, which the failing tests exercise) was still born `PIPELINE`, and this plan's `approve_job`/`update_resolve_row_for_job` guard swap (now requiring `CANDIDATE`) rejected it — a genuine regression of the corpus-import-to-approve workflow, not a pre-existing failure.
- **Fix:** Flipped only the one status kwarg (`PIPELINE` -> `CANDIDATE`) and its adjacent comment in `import_convokit.py`. Left the rest of 48-05's declared scope for that file (the `ArgumentStatusLog` birth-write, the `recompute_argument_tier` call, and the full docstring rewrite) untouched — those are additive TRUST-02/03 features, not required to make this plan's guard swap internally consistent.
- **Files modified:** `pipeline/commands/import_convokit.py`.
- **Verification:** Full suite re-run green (1136 passed / 5 xfailed / 1 known-expected failure) after the ripple fixes below.
- **Committed in:** `2aa53b16f` (Task 1 commit).

**2. [Rule 1 - Bug] Test fixtures across six files hardcoded PIPELINE as the live "freshly created" state**
- **Found during:** Re-running the full suite after fix #1 above — 15 failures across `api/tests/test_admin_jobs_phase25.py` (7), `api/tests/test_phase44_argument_role_roundtrip.py` (4), `api/tests/test_admin_dev_routes.py` (2), `pipeline/tests/test_import_convokit_core.py` (2), `pipeline/tests/test_import_convokit_adminjob.py` (1, plus `test_admin_jobs_service.py`/`test_admin_jobs_list.py` caught directly by Task 1's own scoped verify command).
- **Issue:** These tests seed `Argument(status=ArgumentStatusEnum.PIPELINE, ...)` (or assert source-level guard bodies contain the literal `"ArgumentStatusEnum.PIPELINE"`) specifically to exercise `approve_job`/`update_resolve_row_for_job`/`get_job_readiness`/corpus-import birth as "the currently-editable state" — not as deliberate dead-value regression fixtures. Once the guard swap and the birth-write flip landed, these assertions became stale/wrong, not merely a cosmetic miss.
- **Fix:** Swapped `ArgumentStatusEnum.PIPELINE` -> `ArgumentStatusEnum.CANDIDATE` (and corrected adjacent docstrings/assertion messages naming the state) in all six files. Left every genuine dead-value fixture untouched (e.g. `test_admin_jobs_service.py:154`'s `delete_job` test, which doesn't exercise any status guard).
- **Files modified:** `api/tests/test_admin_jobs_list.py`, `api/tests/test_admin_jobs_phase25.py`, `api/tests/test_phase44_argument_role_roundtrip.py`, `api/tests/test_admin_dev_routes.py`, `pipeline/tests/test_import_convokit_core.py`, `pipeline/tests/test_import_convokit_adminjob.py`.
- **Verification:** `./.venv/bin/python -m pytest api/tests pipeline/tests tests -q` → 1136 passed, 5 xfailed, 1 known-expected failure (`test_admin_detail_contract_does_declare_trust_tier`), 0 unexpected.
- **Committed in:** `2aa53b16f` (Task 1 commit).

**3. [Rule 1 - Plan-authoring correction] Test name didn't match its own acceptance-criteria grep filter**
- **Found during:** Task 3, verifying acceptance criterion `pytest ... -k "candidate or editable" ... reports 3 or more tests`.
- **Issue:** The plan's action text names three vocabulary-block tests, but `test_approve_job_accepts_freshly_created_argument_and_rejects_second_call` contains neither "candidate" nor "editable", so the criterion's own `-k` filter matched only 2 of the 3 tests it was written to count.
- **Fix:** Renamed to `test_approve_job_accepts_freshly_created_candidate_and_rejects_second_call` — no behavior change, just makes the plan's own filter match all three tests it names.
- **Files modified:** `api/tests/test_admin_jobs_service.py`.
- **Verification:** `pytest api/tests/test_admin_jobs_service.py -q -k "candidate or editable"` → 3 passed.
- **Committed in:** `0f976f191` (Task 3 commit).

---

**Total deviations:** 3 auto-fixed (1 Rule 3 blocking-issue fix with a documented cross-plan scope note, 1 Rule 1 test-fixture-vocabulary fix spanning 6 files, 1 Rule 1 plan-authoring correction).
**Impact on plan:** No architectural change and no scope creep into 48-05's additive TRUST-02/03 work (the `ArgumentStatusLog` birth-write and its own `recompute_argument_tier` call remain fully 48-05's to land). The `pipeline/commands/import_convokit.py` touch is recorded in `.planning/WINDOWS.md` (kind=deviation, phase 48) so 48-05's executor is not surprised to find that one line already flipped.

## TDD Gate Compliance

Task 3 carries `tdd="true"`, but Tasks 1-2 (the guard swap and the recompute wiring) were already implemented and committed before Task 3 began — there was no unimplemented behavior left to drive a RED-then-GREEN cycle against. Writing the six regression tests here is backfilled coverage for already-correct, already-verified behavior, not a strict TDD cycle. This follows the same precedent 48-01 Plan's Task 3 (DB-gated recompute coverage, also `tdd="true"`, also written after Task 1's tracer implementation already existed) established in this same phase. All six tests pass on first run against the existing implementation; none was observed failing pre-implementation, so no fail-fast investigation was triggered.

## Issues Encountered

- Two test-teardown ordering bugs surfaced while writing Task 3's new tests, both fixed inline before commit: (1) `_teardown_rows` initially deleted only explicitly-passed `ArgumentStatusLog` ids, missing the row `approve_job` writes as a side effect — fixed by also deleting by `argument_id` via a bulk `delete()`. (2) `test_resolve_job_recomputes_tier_when_last_speaker_resolves`'s cleanup deleted the seeded `Person` row before the `SpeakerAlias` row `resolve_job` upserts (which FKs to `Person`) — fixed by reordering the `finally` block to delete the alias first.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 48-05 (corpus import / PDF ingest birth-write + recompute wiring) can proceed; its `import_convokit.py` status-kwarg edit will find the line already at `CANDIDATE` (see Deviations #1) and should treat that specific line as already-done rather than re-apply it — the `ArgumentStatusLog` birth-write and `recompute_argument_tier` call at the end of `_import_conversation` remain fully its scope.
- Plan 48-06 (publish gate) can rely on `arguments.trust_tier` being correctly recomputed by every `admin_jobs` writer path before it reads the tier to decide whether to block a publish attempt.
- Plan 48-09's `recompute-trust --all` zero-rows-changed verification now has four more correctly-wired writer paths to be silent against.
- Full suite baseline for subsequent plans: 1136 passed, 5 xfailed, 1 known-expected failure (`test_trust_public_leak_ban.py::test_admin_detail_contract_does_declare_trust_tier`, resolves at 48-07), 0 unexpected.

## Self-Check: PASSED

- FOUND: api/services/admin_jobs.py
- FOUND: api/services/admin_people.py
- FOUND: api/schemas/admin_people.py
- FOUND: api/services/admin_dev.py
- FOUND: app/src/routes/admin/pipeline/[job_id]/+page.server.ts
- FOUND: api/tests/test_admin_jobs_service.py
- FOUND: pipeline/commands/import_convokit.py
- FOUND commit: 2aa53b16f
- FOUND commit: eaadc2483
- FOUND commit: 0f976f191

---
*Phase: 48-trust-lifecycle*
*Completed: 2026-08-19*
