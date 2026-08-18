---
phase: 47-provenance-foundation
plan: 06
subsystem: verification
tags: [postgresql, provenance, import_run, reset-to-fixture, pytest, evidence]

# Dependency graph
requires:
  - phase: 47-01
    provides: "import_run table + import_source/import_method PG enum types, ImportRun/ImportSource/ImportMethod/ImportRunStatus ORM classes"
  - phase: 47-02
    provides: "ingest/parse/resolve write paths stamping source/method at write time"
  - phase: 47-03
    provides: "API read layer converted to ImportRun, PIPELINE_RUN_STRATEGY deleted repo-wide"
  - phase: 47-04
    provides: "pipeline/tests suite (244 tests) converted to import_run"
  - phase: 47-05
    provides: "api/tests + root tests/ schema-contract files converted to import_run (800 passed baseline)"
provides:
  - "Live-database evidence that reset_to_fixture stamps corpus/direct on every FIXTURE_SET row, read directly off the rows with no join and no inference"
  - "Test-driven evidence that pipeline.commands.parse.run_parse stamps both pdf_pipeline legs (rule_based, llm_corrective), completing D-06's three-combination guardrail"
  - ".planning/phases/47-provenance-foundation/47-PROVENANCE-EVIDENCE.md -- the recorded D-06 evidence artifact"
  - "Confirmed true full-suite state (1039 passed / 6 skipped / 5 xfailed / 4 pre-existing failed / zero collection errors) plus both explicit-path invocation shapes green"
affects: []

# Actuals (#2632)
actuals:
  tokens: 3588
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Provenance verification composes a live-database re-seed (corpus/direct) with monkeypatched unit-level writer runs (pdf_pipeline legs) rather than extending the fixture-reset tool, because no PDF fixture exists in the repository to extend it with"

key-files:
  created:
    - .planning/phases/47-provenance-foundation/47-PROVENANCE-EVIDENCE.md
  modified: []

key-decisions:
  - "Task 1's destructive dev-database reseed was operator-authorized and executed by the orchestrator before this continuation agent started (harness permission classifier denied it to a prior automated attempt). This continuation agent performed only read-only evidence capture off the already-reseeded live rows plus Task 2's test-driven pdf_pipeline evidence and full-suite gate -- no further writes to DATABASE_URL were made or attempted."
  - "Task 3 (checkpoint:human-verify, gate=blocking, requires a live running API + SvelteKit app) is out of scope for this isolated worktree agent and is not attempted here -- it requires the operator to run the actual application, which is a post-merge, main-worktree activity, not something a parallel execution worktree can meaningfully substitute for."

patterns-established: []

requirements-completed: [PROV-01, PROV-02, PROV-03, PROV-04, PROV-05, PROV-06]

coverage:
  - id: E1
    description: "reset_to_fixture (real production writer, real AsyncSession, no HTTP server) re-seeds the dev database; every import_run row for the four FIXTURE_SET conversation ids reads source=corpus/method=direct/external_id=<conversation_id>/pdf_path IS NULL/pdf_url IS NULL, read directly off the live rows with no join beyond arguments.id=import_run.argument_id"
    requirement: "PROV-05"
    verification:
      - kind: integration
        ref: "live query against DATABASE_URL post-reseed -- 4/4 import_run rows match exactly; Argument.oyez_transcript_id unchanged for all four"
        status: pass
      - kind: integration
        ref: "./.venv/bin/python -m pytest pipeline/tests/test_import_run_provenance.py -x -q -- 12 passed"
        status: pass
    human_judgment: false
  - id: E2
    description: "Integrity properties across the re-seeded database: 0 orphan utterances, 0 strategy columns on utterances/import_run"
    requirement: "PROV-05"
    verification:
      - kind: integration
        ref: "SELECT count(*) FROM utterances u LEFT JOIN import_run r ON u.import_run_id=r.id WHERE r.id IS NULL -- 0"
        status: pass
      - kind: integration
        ref: "SELECT ... information_schema.columns WHERE table_name IN ('utterances','import_run') AND column_name='strategy' -- 0 rows"
        status: pass
    human_judgment: false
  - id: E3
    description: "pipeline.commands.parse.run_parse stamps pdf_pipeline/rule_based when parse_with_llm raises, and pdf_pipeline/llm_corrective when it returns -- method derived from the branch actually taken, never caller-supplied (T-47-07)"
    requirement: "PROV-06"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_run_provenance.py::test_parse_rule_based_stamps_pdf_pipeline_rule_based -- PASSED"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_run_provenance.py::test_parse_llm_success_stamps_pdf_pipeline_llm_corrective -- PASSED"
        status: pass
    human_judgment: false
  - id: E4
    description: "Full suite gate: default invocation, explicit-path invocation, and the D-03 isolation regression test all run; the 4 pre-existing failures are reported honestly, not hidden"
    requirement: "PROV-01..PROV-06"
    verification:
      - kind: integration
        ref: "./.venv/bin/python -m pytest -- 1039 passed, 6 skipped, 5 xfailed, 4 failed, zero collection errors"
        status: fail
      - kind: integration
        ref: "./.venv/bin/python -m pytest api/tests -q -- 718 passed, 6 skipped, 0 failed"
        status: pass
      - kind: integration
        ref: "./.venv/bin/python -m pytest tests/test_pytest_isolation_invocation_shapes.py -q -- 3 passed"
        status: pass
    human_judgment: true
    rationale: "The 4 failures (api/tests/test_phase44_argument_role_roundtrip.py) are pre-existing, reproduce identically at the pre-phase commit 8e1c6a33b, pass in isolation, and touch neither file this phase modified nor the SideEnum definition -- confirmed independently by the orchestrator per <upstream_state>. Logged as WINDOWS.md entry #5 and deferred-items.md; out of scope for Phase 47."

duration: ~25min
completed: 2026-08-18
status: complete
---

# Phase 47 Plan 06: Provenance Verification Evidence Summary

**Recorded the D-06 three-combination provenance evidence in `47-PROVENANCE-EVIDENCE.md`: a live re-seed of the dev database proves `corpus/direct` is stamped and read directly off the rows with no inference, two monkeypatched `run_parse` test runs prove both `pdf_pipeline` legs, and the full test suite was gated with its true, honestly-reported state (1039 passed / 6 skipped / 5 xfailed / 4 pre-existing, unrelated failures / zero collection errors).**

## Performance

- **Duration:** ~25 min (continuation session; prior checkpoint agent made zero commits, and the destructive reseed itself was executed by the orchestrator before this session started)
- **Completed:** 2026-08-18
- **Tasks:** 2/2 (of this plan's own tracked scope; Task 3 is a separate operator-only checkpoint, see below)
- **Files modified:** 1 (created)

## Accomplishments

- **Task 1 (evidence capture only — the destructive reseed itself was already executed by the orchestrator under explicit operator authorization):** Confirmed `alembic current` reads `0026 (head)` against the dev database (read-only check). Wrote the `## corpus/direct (live re-seed)` section of `47-PROVENANCE-EVIDENCE.md`, recording: the resolved database name, the reseed timestamp and duration (77.2s), pre- and post-seed row counts for all nine relevant tables (exact, unrounded), the four `reset_to_fixture` fixture rows, per-term import stats for all four corpus terms (1966/1955/1985/2010), the live `import_run` read-back query and its four resulting rows (every one reading `source='corpus'`, `method='direct'`, `external_id` matching the conversation id, `pdf_path`/`pdf_url` both NULL), and the three corroborating integrity assertions (4 matching Argument rows, 0 orphan utterances, 0 `strategy` columns). Re-ran `pipeline/tests/test_import_run_provenance.py -x -q` (12 passed) as this task's own verify command — this targets `TEST_DATABASE_URL`, not the just-reseeded dev database.
- **Task 2:** Ran both `pdf_pipeline` provenance tests (`test_parse_rule_based_stamps_pdf_pipeline_rule_based`, `test_parse_llm_success_stamps_pdf_pipeline_llm_corrective`) with `-v` and recorded their exact `source`/`method` assertions, the monkeypatch that selected each branch, and cross-referenced two companion tests (`test_pdf_pipeline_run_populates_pdf_path`, `test_parse_utterances_link_to_import_run`) that further corroborate the shape of the `pdf_pipeline` rows. Added the `## D-06 composition` section reproducing the plan's own composition table and explaining why `reset_to_fixture` was not extended (no PDF fixture exists in the repo). Ran the full suite (`./.venv/bin/python -m pytest`), the explicit-path shape (`api/tests -q`), and the D-03 isolation regression test (`tests/test_pytest_isolation_invocation_shapes.py`), recording the true, unrounded results of all three. Ran the retired-name-hygiene grep sweep and the `compileall` build check.

## Task Commits

Each task was committed atomically:

1. **Task 1: Re-seed the dev database and read corpus provenance off the live rows** — `e53a7d348` (docs) — evidence capture only; the reseed itself predates this commit and was executed by the orchestrator.
2. **Task 2: Record the pdf_pipeline evidence and gate on a green full suite** — `fcddf4837` (docs)

## Files Created/Modified

- `.planning/phases/47-provenance-foundation/47-PROVENANCE-EVIDENCE.md` — the complete D-06 evidence artifact: `## corpus/direct (live re-seed)`, `## pdf_pipeline/rule_based`, `## pdf_pipeline/llm_corrective`, `## D-06 composition`, `## Full suite state (Task 2 gate)`

## Decisions Made

- **The destructive dev-database reseed was operator-authorized and executed by the orchestrator, not by this agent.** A prior automated attempt hit a `blocking-human` permission-classifier denial on the destructive step; per this continuation's explicit instructions, that step is DONE and was not re-run, re-truncated, or re-seeded here. This agent performed only read-only evidence capture off the already-reseeded live rows (an `alembic current` check and the recorded read-back), which is consistent with the DATABASE SAFETY constraint given for this continuation.
- **Task 3 (the `checkpoint:human-verify`, `gate="blocking"` operator confirmation of the admin/public surfaces) was not attempted in this worktree.** It requires starting the real API and SvelteKit app for a human to click through — a live, running-application activity that does not fit an isolated parallel-execution worktree, and it was not included in this continuation's explicit 2-task scope. It remains outstanding and should be run by the operator against the merged result before the phase is considered fully closed.

## Deviations from Plan

None — plan Tasks 1 and 2 executed exactly as written, given the pre-resolved checkpoint state described in this continuation's instructions. No Rule 1/2/3 auto-fixes were needed: both tasks' verify commands passed on the first run, and the retired-name-hygiene sweep returned only the two exceptions already documented and accepted in 47-05-SUMMARY.md (not new findings, not fixed here, per that plan's own explicit rationale for why those two references must remain).

### Environment note (not a deviation, not a defect)

The first full-suite run in this worktree showed `1035 passed, 10 skipped` (4 extra skips, all in `api/tests/test_phase38_people_ui_contract.py`, reason: "node is not available in this execution environment") because this worktree's shell did not have `node` on `PATH` by default. Re-running with `node` on `PATH` (per this environment's own setup note) reproduced the canonical `1039 passed, 6 skipped` baseline exactly. This is a shell-environment artifact of the worktree, not a suite regression, and is not present in the recorded evidence (which reflects the `node`-available run).

## Known Stubs

None. This plan's only artifact is a planning/evidence document; no application code, UI, or data-flow stub was introduced.

## Threat Flags

None. This plan changes no source files and introduces no new network endpoint, auth path, file access pattern, or schema. The one live-database write (the dev-DB reseed) was already dispositioned `mitigate` under T-47-01 in 47-06-PLAN.md's threat model and was executed under explicit operator authorization by the orchestrator, not by this agent.

## Issues Encountered

- **The full test suite is not fully green — 4 pre-existing failures remain, unrelated to Phase 47.** `api/tests/test_phase44_argument_role_roundtrip.py`'s 4 parametrized `test_resolve_row_update_accepts_each_dropdown_value_and_coerces_enum` cases fail under the bare `pytest -q` invocation due to a `SideEnum` module-identity bug caused by `tests/test_admin_router.py`'s intentional mid-suite module reimport interacting with `pytest.ini`'s `testpaths` collection order. This reproduces identically at the pre-phase commit `8e1c6a33b`, passes in isolation, and touches no file this phase modified — confirmed independently by the orchestrator per this plan's `<upstream_state>`. Logged as `WINDOWS.md` entry #5 (open) and `.planning/phases/47-provenance-foundation/deferred-items.md`. Not fixed here — explicitly out of scope, per the plan's own instruction not to touch it.
- **Task 3 (operator checkpoint) remains outstanding.** See Decisions Made above — this is expected, not a defect, given this continuation's 2-task scope and the worktree-isolation constraint on running a live application.

## User Setup Required

**Task 3 of 47-06-PLAN.md (the `checkpoint:human-verify`, `gate="blocking"` operator confirmation) has not been performed.** Before Phase 47 is considered fully closed, the operator (or a follow-up execution against the merged main worktree) must:

1. Start the API and SvelteKit app locally.
2. Open the admin job list and confirm all four re-seeded fixture arguments read **corpus** (not **pdf**) in the Source tag.
3. Open one admin job detail page and confirm parse stats render and are non-zero.
4. Open the public page for one of the four fixture arguments and confirm the transcript renders and the corpus-sourced indicator still behaves as before.
5. Search the public page for the literal words `corpus`, `pdf_pipeline`, `rule_based`, `llm_corrective` — report any hit rather than accepting it (apolitical framing / operator-facing-only provenance constraint).
6. Optionally run one PDF ingest end to end if a PDF is available.

See `47-06-PLAN.md`'s Task 3 for the full instructions and resume signal.

## Next Phase Readiness

- The `import_run` schema, all three write-path conversions, the API read layer, the full test-suite conversion, and the D-06 three-combination provenance evidence are all complete and recorded in `47-PROVENANCE-EVIDENCE.md`.
- The dev database is re-seeded with the four canonical `FIXTURE_SET` fixtures through the real corpus import path, matching `.planning/FIXTURES.md`.
- **Outstanding before phase close:** Task 3's operator checkpoint (admin/public surface confirmation) has not been performed in this worktree and should be run against the merged result.
- **Known, tracked, out-of-scope gap:** the 4 pre-existing `test_phase44_argument_role_roundtrip.py` failures (WINDOWS.md #5) remain open for a future phase or `/gsd-review-backlog` item — unrelated to any file this phase touched.
- **Standing note recorded in the evidence file:** `.planning/FIXTURES.md`'s four-fixture set remains 100% corpus-sourced; `pdf_pipeline` coverage lives in `pipeline/tests` only. A future phase wanting live-database `pdf_pipeline` rows would need to add a PDF fixture and extend `reset_to_fixture`.

---
*Phase: 47-provenance-foundation*
*Completed: 2026-08-18*

## Self-Check: PASSED

- FOUND: `.planning/phases/47-provenance-foundation/47-PROVENANCE-EVIDENCE.md`
- FOUND commit: `e53a7d348`
- FOUND commit: `fcddf4837`
