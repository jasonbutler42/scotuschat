---
phase: 47-provenance-foundation
plan: 03
subsystem: api
tags: [fastapi, sqlalchemy, provenance, read-path, pydantic]

# Dependency graph
requires:
  - "import_run table + import_source/import_method PG enum types (migration 0026, 47-01)"
  - "ImportRun/ImportSource/ImportMethod/ImportRunStatus ORM classes (47-01)"
provides:
  - "Public FastAPI read path (api/services/arguments.py) resolving the latest completed parse run via MAX(ImportRun.id), filtered on ImportRun.step and ImportRunStatus.COMPLETED"
  - "Admin delete cascade (api/services/admin_arguments.py) and PDF-streaming lookup (api/routers/admin.py) converted to ImportRun"
  - "Corpus-vs-pdf Source tag (api/services/admin_jobs.py) derived from the declared ImportRun.source == ImportSource.CORPUS enum comparison, replacing the PIPELINE_RUN_STRATEGY string hack"
  - "Public UtteranceResponse contract carrying import_run_id and no strategy/source/method/external_id field"
  - "The whole api package importable again against the import_run schema (api.main imports cleanly)"
affects: [47-04, 47-05, 47-06]

# Actuals (#2632)
actuals:
  tokens: 4950
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "exists() subquery (not join) for a 1:many Argument->ImportRun derived boolean flag, to avoid duplicate parent rows -- unchanged shape, just the compared column moved from a strategy string to a declared source enum"

key-files:
  created: []
  modified:
    - api/services/arguments.py
    - api/services/admin_arguments.py
    - api/routers/admin.py
    - api/services/admin_jobs.py
    - api/schemas/admin_jobs.py
    - api/schemas/utterance.py
    - pipeline/commands/import_convokit.py

key-decisions: []

patterns-established: []

requirements-completed: [PROV-03, PROV-04]

coverage:
  - id: D13
    description: "Public utterance read path selects the latest completed parse run deterministically by MAX(import_run.id), unchanged step/status semantics"
    requirement: "PROV-01"
    verification:
      - kind: static
        ref: "grep -c func.max(ImportRun.id) / ImportRun.step==\"parse\" / ImportRunStatus.COMPLETED in api/services/arguments.py"
        status: pass
      - kind: integration
        ref: "./.venv/bin/python -c \"import api.services.arguments, api.services.admin_arguments, api.routers.admin\""
        status: pass
    human_judgment: false
  - id: D14
    description: "Corpus-vs-pdf Source tag derived from ImportRun.source == ImportSource.CORPUS at both call sites (get_job, list_jobs); PIPELINE_RUN_STRATEGY deleted repo-wide"
    requirement: "PROV-03"
    verification:
      - kind: static
        ref: "grep -c 'ImportRun.source == ImportSource.CORPUS' api/services/admin_jobs.py (returns 2)"
        status: pass
      - kind: static
        ref: "grep -rc PIPELINE_RUN_STRATEGY api/ pipeline/ --include=*.py (returns 0 across all files)"
        status: pass
      - kind: integration
        ref: "./.venv/bin/python -m pytest pipeline/tests/test_import_run_provenance.py -x -q -- 12 passed"
        status: pass
    human_judgment: false
  - id: D15
    description: "Public UtteranceResponse carries import_run_id, no strategy/source/method/external_id field; FastAPI app imports cleanly; no frontend file needed modification"
    requirement: "PROV-04"
    verification:
      - kind: static
        ref: "grep -c import_run_id: int / pipeline_run_id / oyez_transcript_id / '^ *(strategy|source|method|external_id):' in api/schemas/utterance.py"
        status: pass
      - kind: integration
        ref: "./.venv/bin/python -c \"import api.main\""
        status: pass
      - kind: static
        ref: "grep -rn pipeline_run_id app/src (no matches)"
        status: pass
    human_judgment: false
  - id: D16
    description: "tests/test_pytest_isolation_invocation_shapes.py (D-03 regression, CLAUDE.md-named) -- 2 of 3 parametrized invocation shapes now pass"
    verification:
      - kind: integration
        ref: "tests/test_pytest_isolation_invocation_shapes.py::test_pytest_isolation_fires_for_every_invocation_shape[explicit-single-file] and [explicit-multi-path-phase45-wipe-shape]"
        status: pass
      - kind: integration
        ref: "tests/test_pytest_isolation_invocation_shapes.py::test_pytest_isolation_fires_for_every_invocation_shape[bare-testpaths-driven]"
        status: fail
    human_judgment: true
    rationale: "The bare-testpaths-driven shape does a full-tree pytest collection; it now fails for a DIFFERENT reason than 47-01 logged (WINDOWS.md #3, marked fixed here) -- api/tests/test_admin_dev_routes.py and four pipeline/tests/test_{delete_fixture_argument,diff_corpus_fixture,import_convokit_core,import_convokit_utterances}.py files reference PipelineRun directly in their own test bodies, not transitively via this plan's production files. All five are outside this plan's files_modified list and are 47-04/47-05's scoped test-suite conversion work. Logged as WINDOWS.md #4."

duration: ~35min
completed: 2026-08-17
status: complete
---

# Phase 47 Plan 03: API Read Layer Provenance Conversion Summary

**The FastAPI read layer (public utterance path, admin delete cascade, PDF streaming, and the admin job Source tag) now runs entirely on `ImportRun`/`ImportSource`, retiring the `PipelineRun` model and the `strategy == "convokit_import"` string-equality hack in favor of a declared `ImportRun.source == ImportSource.CORPUS` enum comparison; the public utterance contract carries `import_run_id` with no provenance field exposed.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-08-17T21:31Z
- **Tasks:** 3/3
- **Files modified:** 7

## Accomplishments

- `api/services/arguments.py`: `get_argument_with_utterances` resolves the latest completed parse run via `select(func.max(ImportRun.id)).where(ImportRun.argument_id == argument_id, ImportRun.step == "parse", ImportRun.status == ImportRunStatus.COMPLETED)`, unchanged from the prior `PipelineRun` selection semantics (PROV-01's `MAX(id)` deterministic tiebreak preserved, not weakened to `created_at`). Utterances filtered by `Utterance.import_run_id == max_run_id`. `oyez_transcript_id` serialization untouched.
- `api/services/admin_arguments.py`: `delete_argument`'s FK-ordered cascade still deletes `Utterance` rows before `ImportRun` rows (load-bearing ordering, renamed comments to name `import_run`). Confirmed the cascade still omits `argument_status_log` — this is a pre-existing gap (STATE.md-tracked), not introduced or fixed here, per the plan's explicit instruction not to touch it in this plan.
- `api/routers/admin.py`: the disk-backed PDF-streaming lookup now does `select(ImportRun).where(ImportRun.id == run_id)`; surrounding docstrings/comments (run-id re-derivation note, cascade-order note, PDF source note) renamed to `import_run`. No `source`/`method`/`external_id` field added to any response model.
- `api/services/admin_jobs.py`: `get_job`'s and `list_jobs`'s corpus-vs-pdf derivations both now compare `ImportRun.source == ImportSource.CORPUS` (still via `exists()`, not a join — `Argument -> ImportRun` remains 1:many, so a join would duplicate `AdminJob` rows). `get_run_id_for_step`'s `order_by(ImportRun.created_at.desc()).limit(1)` semantics are byte-for-byte unchanged, per the `<scope_fence>` — the `created_at` tie case remains a known, deliberately-deferred edge (recorded as a `backstop` truth in 47-03-PLAN.md's `must_haves`; the one-line fix for the later "Path rework" phase is adding `ImportRun.id.desc()` as a secondary sort key). Every remaining `PipelineRun`/`pipeline_run` identifier in this file renamed to `ImportRun`/`import_run`.
- `api/schemas/admin_jobs.py`: the comment describing the `exists()` source derivation renamed to name the declared `ImportRun.source` column.
- `pipeline/commands/import_convokit.py`: deleted the `PIPELINE_RUN_STRATEGY = "convokit_import"` module constant and its D-09 comment block — both of its consumers (`admin_jobs.py`'s two `exists()` derivations) were converted in the same commit, so no dead code remains.
- `api/schemas/utterance.py`: `UtteranceResponse.strategy` deleted (the backing `Utterance.strategy` column no longer exists, so `from_attributes=True` would have raised `AttributeError`); `pipeline_run_id: int` renamed to `import_run_id: int`. No `source`/`method`/`external_id` field added — provenance stays operator-facing lineage per the apolitical framing hard constraint (T-47-04's `mitigate` disposition). `ArgumentMetadataResponse.oyez_transcript_id` is unchanged. Confirmed by reading `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` that its `is_corpus_sourced` derivation reads only `data.argument.oyez_transcript_id` — no per-utterance provenance or `strategy`/`pipeline_run_id` field is consumed anywhere in `app/src`. No frontend file was modified.
- The entire `api` package imports cleanly against the new schema: `./.venv/bin/python -c "import api.main"` exits 0.

## Task Commits

Each task was committed atomically:

1. **Task 1: Convert the public read path, delete cascade, and PDF streaming lookup** — `726fe89bb` (feat)
2. **Task 2: Replace the strategy string hack with the declared ImportRun.source** — `e954f6e2a` (feat)
3. **Task 3: Update the public utterance response contract** — `fd1aceda1` (feat)

## Files Created/Modified

- `api/services/arguments.py` — `PipelineRun`/`PipelineRunStatus` → `ImportRun`/`ImportRunStatus`; `Utterance.pipeline_run_id` → `import_run_id`; docstrings renamed
- `api/services/admin_arguments.py` — `delete_argument`'s cascade renamed to `ImportRun`; ordering comment restated for `import_run`
- `api/routers/admin.py` — PDF-streaming lookup and surrounding docstrings renamed to `ImportRun`/`import_run`
- `api/services/admin_jobs.py` — both corpus-vs-pdf `exists()` derivations rewritten on `ImportRun.source == ImportSource.CORPUS`; `PIPELINE_RUN_STRATEGY` import removed; `get_run_id_for_step` and all remaining identifiers renamed, ordering/step semantics unchanged
- `api/schemas/admin_jobs.py` — comment renamed to describe the declared `source` column
- `api/schemas/utterance.py` — `strategy` field deleted, `pipeline_run_id` renamed to `import_run_id`
- `pipeline/commands/import_convokit.py` — `PIPELINE_RUN_STRATEGY` constant and its D-09 comment block deleted

## Decisions Made

None — this plan implements 47-01's operator-resolved native-enum decision and the `<scope_fence>`'s locked D-04 boundary (per-step `import_run` grain, `admin_jobs` untouched beyond the mechanical rename); no new architectural decisions were needed.

## Deviations from Plan

### Auto-fixed Issues

None requiring a Rule 1-3 fix beyond the plan's own task sequencing. One sequencing note, not a deviation from the plan's content:

**Task 1's own `<verify>` command (`import api.services.arguments, api.services.admin_arguments, api.routers.admin`) cannot pass until Task 2 also lands within this same plan.** `api/routers/admin.py` does `from api.services import admin_jobs as jobs_service` at module level, and `admin_jobs.py` (Task 2's target file) still imported the retired `PipelineRun` symbol at the time Task 1's code was written. Both tasks' code edits were made in sequence, then both tasks' `<verify>` commands were re-run together and confirmed passing before either task's files were staged/committed — Task 1's files were committed first (all of Task 1's own acceptance-criteria greps and the full three-module import check pass on the post-Task-2 tree), followed by Task 2's files as a separate commit. This mirrors the same cross-file import-chain pattern 47-01 encountered and is not a change to either task's scoped content — no file outside each task's own `<files>` list was touched to make this work.

---

**Total deviations:** 0 content deviations (1 sequencing note, see above).

## Verification Performed

Plan-level `<verification>` block, all items:

- `./.venv/bin/python -c "import api.main"` — exits 0 (entire FastAPI app imports against the new schema)
- `python3 -m compileall -q api` — exits 0
- `grep -rn "PipelineRun\|PipelineRunStatus\|pipeline_run_id\|PIPELINE_RUN_STRATEGY" api/ --include=*.py | grep -v /tests/` — no matches
- `grep -rn "pipeline_run_id" app/src` — no matches
- `./.venv/bin/python -m pytest pipeline/tests/test_import_run_provenance.py -x -q` — **12 passed**

Every task-level `<acceptance_criteria>` grep (Task 1: 3 files × 2 negative greps + 4 positive greps + cascade-order check; Task 2: 5 checks; Task 3: 5 checks) was run individually and passed — see `coverage` D13-D15 above for the representative subset.

**The one high-value check named in `<upstream_state>`:** `tests/test_pytest_isolation_invocation_shapes.py` (D-03 regression test, CLAUDE.md-named) was run explicitly, per-parametrization:

- `[explicit-single-file]` — **passed**
- `[explicit-multi-path-phase45-wipe-shape]` — **passed**
- `[bare-testpaths-driven]` — **still fails**, but for a narrower reason than before this plan. It does a full-tree pytest collection; collection now errors only on modules this plan's `files_modified` does not include: `api/tests/test_admin_dev_routes.py` (constructs `PipelineRun` directly at line 331) and four `pipeline/tests/test_{delete_fixture_argument,diff_corpus_fixture,import_convokit_core,import_convokit_utterances}.py` files (import `PipelineRun` from `api.models.models` in their own test bodies). All five are explicitly 47-04/47-05's scoped test-suite conversion work. `api/tests/test_docket_arg_safety.py` — the other module 47-01-SUMMARY.md named as blocked — now collects cleanly (confirmed via `--collect-only`), proving the prediction that converting `api/routers/admin.py` would unblock it.

**Broken-windows ledger:** WINDOWS.md entry #3 (logged by 47-01, describing the `api.routers.admin` → `PipelineRun` transitive-import cause) marked `fixed` — that specific cause no longer exists. A new entry #4 was appended describing the narrower remaining cause (the five test-body-only files above), open, owned by 47-04/47-05.

**Test modules verified by this plan (scoped, per `<upstream_state>`'s instruction not to gate on the whole suite):**
- `pipeline/tests/test_import_run_provenance.py` — 12/12 passed (unchanged from 47-02; re-run to confirm this plan's changes did not regress it)
- `tests/test_pytest_isolation_invocation_shapes.py` — 2/3 parametrizations passed (see above)
- `api/tests/test_docket_arg_safety.py` — collects cleanly (14 tests collected), confirming the upstream prediction

**Test modules confirmed still RED, explicitly out of this plan's scope (owned by 47-04/47-05):**
- `api/tests/test_admin_dev_routes.py` — direct `PipelineRun` construction in its own test body
- `pipeline/tests/test_delete_fixture_argument.py`, `test_diff_corpus_fixture.py`, `test_import_convokit_core.py`, `test_import_convokit_utterances.py` — direct `PipelineRun` imports in their own test bodies
- The bulk of `api/tests/` and `pipeline/tests/` more broadly (per `<upstream_state>` and this plan's own `<verification>` note: "47-04 and 47-05 own the test-suite conversion and 47-06 owns the full-suite gate")

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The entire `api` package now imports cleanly against the `import_run` schema; the public read path, admin delete cascade, PDF streaming lookup, and admin job Source tag are all converted. 47-04 and 47-05 can now convert the remaining test-suite consumers without any further production-code schema or query changes from this plan's files.
- `PIPELINE_RUN_STRATEGY` no longer exists anywhere in the repository (production or otherwise) — its only remaining references were in the five test files named above, which import it transitively via `PipelineRun`, not the retired constant itself.
- **Known gap for 47-04/47-05 to inherit:** `api/tests/test_admin_dev_routes.py` and the four `pipeline/tests/test_{delete_fixture_argument,diff_corpus_fixture,import_convokit_core,import_convokit_utterances}.py` files still construct/import `PipelineRun` directly in their own test bodies and will need the same `PipelineRun` → `ImportRun` conversion (plus, where applicable, `strategy=` → `source=`/`method=` stamping) that 47-01/47-02 already applied to production code.
- **Known gap for the "Path rework" phase (D-04, out of this plan's scope):** `get_run_id_for_step`'s `order_by(ImportRun.created_at.desc()).limit(1)` has no secondary sort key, so two `import_run` rows for the same `(argument_id, step)` sharing an identical `created_at` resolve to an arbitrary (but valid) row. The one-line fix is adding `ImportRun.id.desc()` as a secondary key; deferred per the `<scope_fence>`.
- **Pre-existing, unrelated gap confirmed still present (not touched, not newly introduced):** `delete_argument`'s cascade still does not delete `argument_status_log` rows before deleting the `Argument` row. This is the same gap STATE.md already tracks from an earlier phase; this plan's task instructions explicitly said not to fix it here.

---
*Phase: 47-provenance-foundation*
*Completed: 2026-08-17*
