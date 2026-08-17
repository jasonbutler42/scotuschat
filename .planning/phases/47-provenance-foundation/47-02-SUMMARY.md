---
phase: 47-provenance-foundation
plan: 02
subsystem: pipeline
tags: [provenance, ingest, parse, resolve, postgresql, sqlalchemy]

# Dependency graph
requires:
  - "import_run table + import_source/import_method PG enum types (migration 0026, 47-01)"
  - "ImportRun/ImportSource/ImportMethod/ImportRunStatus ORM classes (47-01)"
provides:
  - "Ingest write path stamping source=pdf_pipeline/method=normalized with pdf_path/pdf_url populated"
  - "Resolve write path stamping source=pdf_pipeline/method=normalized"
  - "Parse write path stamping source=pdf_pipeline plus exactly one of rule_based/llm_corrective, decided by whether the LLM pass returned or raised"
  - "pipeline/tests/test_import_run_provenance.py -- 12 passing tests proving all three D-06 combinations (corpus/direct from 47-01, pdf_pipeline/rule_based and pdf_pipeline/llm_corrective added here)"
affects: [47-03, 47-04, 47-05, 47-06]

# Actuals (#2632)
actuals:
  tokens: 6250
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Provenance method/source derived from the actual code branch taken (parse_with_llm returned vs raised), never from a caller-supplied argument -- T-47-07"

key-files:
  created: []
  modified:
    - pipeline/commands/ingest.py
    - pipeline/commands/resolve.py
    - pipeline/commands/parse.py
    - pipeline/__main__.py
    - pipeline/tests/test_import_run_provenance.py

key-decisions: []

patterns-established:
  - "Local branch-tracking string (parse_strategy) is retained unchanged for control flow; translation onto the closed ImportMethod vocabulary happens once, at the ImportRun construction site -- keeps the vocabulary mapping in one place per writer (RESEARCH.md Pattern 2)."

requirements-completed: [PROV-01, PROV-02, PROV-03, PROV-05, PROV-06]

coverage:
  - id: D6
    description: "Ingest stamps source=pdf_pipeline/method=normalized; pdf_path/pdf_url populated"
    requirement: "PROV-06"
    verification:
      - kind: static
        ref: "grep -c ImportSource.PDF_PIPELINE / ImportMethod.NORMALIZED / pdf_path=str(pdf_path) in pipeline/commands/ingest.py"
        status: pass
    human_judgment: false
  - id: D7
    description: "Resolve stamps source=pdf_pipeline/method=normalized; still refuses a non-parse source run"
    requirement: "PROV-01/PROV-02"
    verification:
      - kind: static
        ref: "grep -c ImportSource.PDF_PIPELINE / ImportMethod.NORMALIZED in pipeline/commands/resolve.py"
        status: pass
    human_judgment: false
  - id: D8
    description: "Parse stamps source=pdf_pipeline plus exactly one of rule_based/llm_corrective, derived from whether parse_with_llm returned or raised (T-47-07), never caller-supplied"
    requirement: "PROV-01/PROV-03"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_run_provenance.py#test_parse_rule_based_stamps_pdf_pipeline_rule_based"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_run_provenance.py#test_parse_llm_success_stamps_pdf_pipeline_llm_corrective"
        status: pass
    human_judgment: false
  - id: D9
    description: "Utterances link via import_run_id with no per-row strategy column"
    requirement: "PROV-05"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_run_provenance.py#test_parse_utterances_link_to_import_run"
        status: pass
    human_judgment: false
  - id: D10
    description: "pdf_path carries forward from the source ingest run on pdf_pipeline parse rows; external_id stays NULL"
    requirement: "PROV-06"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_run_provenance.py#test_pdf_pipeline_run_populates_pdf_path"
        status: pass
    human_judgment: false
  - id: D11
    description: "All three D-06 combinations (corpus/direct, pdf_pipeline/rule_based, pdf_pipeline/llm_corrective) reachable from code within one transaction"
    requirement: "PROV-01"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_run_provenance.py#test_d06_all_three_combinations_present"
        status: pass
    human_judgment: false
  - id: D12
    description: "No live Anthropic API call from the test suite"
    requirement: "T-47-08"
    verification:
      - kind: static
        ref: "grep -c anthropic pipeline/tests/test_import_run_provenance.py returns 0"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-08-17
status: complete
---

# Phase 47 Plan 02: Ingest/Parse/Resolve Provenance Stamping Summary

**Ingest, parse, and resolve now each declare `source`/`method` at `ImportRun` row-creation time; parse's method is derived from whether the LLM corrective pass returned or raised, never from a caller-supplied value; 12 tests (7 from 47-01 + 5 new) prove all three D-06 provenance combinations end-to-end.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-08-17T21:18Z
- **Tasks:** 3/3
- **Files modified:** 5 (0 created, 5 modified)

## Accomplishments

- `pipeline/commands/ingest.py`: `ImportRun` construction now declares `source=ImportSource.PDF_PIPELINE`, `method=ImportMethod.NORMALIZED` — ingest's `normalize_docket_value` + `docket_number_norm` + `_derive_slug` are deterministic transforms, matching the vocabulary's own definition of `normalized`. `pdf_path`/`pdf_url` remain populated (PROV-06 positive half). Trailing print and every remaining `PipelineRun`/`pipeline_run` identifier retired.
- `pipeline/commands/resolve.py`: the resolve-step `ImportRun` construction declares the same `source=ImportSource.PDF_PIPELINE`, `method=ImportMethod.NORMALIZED` pair — resolve is deterministic `normalize_label` + alias-table lookup, no LLM. Docstring/print `pipeline_run` mentions retired to `import_run`. The "NEVER mutate parse_run.status" invariant was left untouched.
- `pipeline/commands/parse.py`: kept the existing `parse_strategy` local-string branch logic (LLM pass runs unconditionally; success — not failure — flips the value) structurally intact, and added a single translation point at the `ImportRun` construction site: `parse_method = ImportMethod.LLM_CORRECTIVE if parse_strategy == "llm_corrective" else ImportMethod.RULE_BASED`. This satisfies T-47-07 — the stamped method is derived from the branch actually taken, never from a caller-supplied argument. Dropped the retired `strategy=` kwarg from both the run and `Utterance` construction; utterances now link via `import_run_id` only. Completion log now reports `run.method.value`.
- `pipeline/__main__.py`: retired the last `PipelineRun` mention (import-convokit subcommand help text) plus the remaining lowercase `pipeline_run` prose in docstrings/help strings, for consistency with the retired-name-hygiene note.
- `pipeline/tests/test_import_run_provenance.py`: extended (not duplicated) with 5 new tests covering both `pdf_pipeline` legs of D-06 — `test_parse_rule_based_stamps_pdf_pipeline_rule_based`, `test_parse_llm_success_stamps_pdf_pipeline_llm_corrective`, `test_parse_utterances_link_to_import_run`, `test_pdf_pipeline_run_populates_pdf_path`, and `test_d06_all_three_combinations_present` (drives one corpus import plus both parse branches in a single transaction and asserts all three `(source, method)` pairs are present). No test imports `anthropic` or calls the live API — `parse_with_llm` is monkeypatched in every leg (T-47-08).

## Task Commits

Each task was committed atomically:

1. **Task 1: Ingest and resolve stamp pdf_pipeline / normalized** — `4d469ba0d` (feat)
2. **Task 2: Parse stamps pdf_pipeline with rule_based or llm_corrective and drops the utterance strategy** — `c6e868249` (feat)
3. **Task 3: Prove the two pdf_pipeline legs of the D-06 guardrail** — `40d9491d6` (test)

## Files Created/Modified

- `pipeline/commands/ingest.py` — `ImportRun` stamps `source=pdf_pipeline`/`method=normalized`; `PipelineRun`/`pipeline_run` retired
- `pipeline/commands/resolve.py` — resolve `ImportRun` stamps the same pair; docstring/print prose retired
- `pipeline/commands/parse.py` — parse `ImportRun` stamps `source=pdf_pipeline` plus one of `rule_based`/`llm_corrective`; utterances link via `import_run_id` with no `strategy`
- `pipeline/__main__.py` — last `PipelineRun`/`pipeline_run` mentions retired from help text and docstrings
- `pipeline/tests/test_import_run_provenance.py` — 5 new tests (12 total in file) proving all three D-06 combinations

## Decisions Made

None — this plan implements 47-01's operator-resolved native-enum decision; no new architectural decisions were needed.

## Deviations from Plan

None — plan executed exactly as written. `pipeline/commands/resolve.py` had already been converted to `ImportRun`/`ImportRunStatus` identifiers by 47-01's Rule 3 auto-fix, so Task 1's identifier-rename sub-steps for that file were already satisfied; only the `source=`/`method=` stamping (this plan's actual scoped work) and the remaining lowercase `pipeline_run` docstring/print prose needed changes.

## Verification Performed

Scoped to this plan's own files, per the plan's `<intermediate_state_note>` — the full suite and `api/tests` remain RED pending 47-03/47-04/47-05/47-06:

- `./.venv/bin/python -m pytest pipeline/tests/test_import_run_provenance.py -x -q` → **12 passed** (7 from 47-01 + 5 new)
- `./.venv/bin/python -m pytest pipeline/tests/test_import_run_provenance.py -q --collect-only` → 12 tests collected
- `python3 -m compileall -q pipeline` → clean, no errors
- `grep -rn "PipelineRun\|PipelineRunStatus" pipeline/commands/ pipeline/__main__.py` → no matches
- `grep -rn "strategy=" pipeline/commands/parse.py` → no matches
- `./.venv/bin/python -m pytest pipeline/tests/test_ingest_startup_guard.py -q` → **5 passed** (unblocked by this plan's `pipeline/__main__.py` conversion — it imports `pipeline/__main__.py` transitively and was RED at collection before this plan per the upstream-state note)
- `./.venv/bin/python -m pytest pipeline/tests/test_parse.py -q` → **6 passed, 2 failed** — the 2 failures (`test_run_id_strategy`, `test_parse_preserves_operator_docket_when_extracted_pair_conflicts`) are `ImportError: cannot import name 'PipelineRun'` from a function-local import inside the test itself; both tests are explicitly plan 47-04's scoped conversion work (this plan's `files_modified` does not include `test_parse.py`, `test_ingest.py`, or `test_resolve.py`), matching 47-01-PLAN.md's `<intermediate_state_note>` exactly.

**Remaining RED, explicitly out of this plan's scope (owned by later plans in wave 2/3):**
- `api/routers/admin.py` and the API/service layer (`api.services.*`) — 47-03
- `pipeline/tests/test_parse.py`, `test_ingest.py`, `test_resolve.py` (their own `PipelineRun`-referencing test bodies) — 47-04/47-05
- `tests/test_pytest_isolation_invocation_shapes.py` and any full-suite run — 47-06

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All three PDF-lifecycle write paths (`ingest`, `parse`, `resolve`) now declare provenance at row-creation time, matching the corpus path 47-01 already proved. PROV-05's "every import path stamps provenance at write time" is now literally true for all three combinations, not just one.
- 47-03 (API read layer) can build directly on these writers without further schema or writer changes.
- 47-06's full-suite gate inherits a smaller RED surface: only `api.services`-dependent modules (47-03's scope) and the three `test_{ingest,parse,resolve}.py` files' own `PipelineRun`-referencing test bodies (47-04/47-05's scope) remain.

---
*Phase: 47-provenance-foundation*
*Completed: 2026-08-17*

## Self-Check: PASSED

- FOUND: `.planning/phases/47-provenance-foundation/47-02-SUMMARY.md`
- FOUND commit: `4d469ba0d`
- FOUND commit: `c6e868249`
- FOUND commit: `40d9491d6`
