---
phase: 44-resolve-table-rework
plan: 01
subsystem: api
tags: [alembic, sqlalchemy, pydantic, fastapi, sveltekit, svelte5]

# Dependency graph
requires: []
provides:
  - "ArgumentParticipant.descriptor ORM column at Alembic head 0025 (renamed from .title)"
  - "descriptor/descriptor_hint field names across ResolveRowUpdate, ResolveRow, ParticipantSideUpdate, SpeakerRow"
  - "Both descriptor write paths (job-scoped resolve row, argument-editor participant) working end to end under the new name"
  - "pipeline/commands/parse.py _update_participant_descriptors TOC-subtitle writer"
  - "api/tests/test_phase44_descriptor_rename.py pure static source contract guarding the rename"
affects: [44-02, 44-03, 44-04]

# Actuals (#2632)
actuals:
  tokens: 17150
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Alembic op.alter_column(..., new_column_name=...) for a true in-place column rename (no add/drop-column, no data-copy)"
    - "Pure static source-contract test (no DB gate, Path.rglob sweep) to make a full-stack rename residual-name-proof"

key-files:
  created:
    - alembic/versions/0025_rename_participant_title_to_descriptor.py
    - api/tests/test_phase44_descriptor_rename.py
    - .planning/phases/44-resolve-table-rework/deferred-items.md
  modified:
    - api/models/models.py
    - api/schemas/admin_jobs.py
    - api/schemas/admin_people.py
    - api/schemas/admin_arguments.py
    - api/services/admin_jobs.py
    - api/services/admin_people.py
    - api/services/admin_arguments.py
    - api/routers/admin.py
    - pipeline/commands/parse.py
    - scripts/diff_corpus_fixture.py
    - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
    - app/src/routes/admin/arguments/[id]/+page.server.ts
    - app/src/routes/admin/arguments/[id]/+page.svelte
    - app/src/lib/components/ResolveCard.svelte
    - api/tests/test_admin_jobs_phase25.py
    - api/tests/test_admin_people_phase25.py
    - api/tests/test_admin_arguments_service.py
    - api/tests/test_admin_arguments_routes.py
    - api/tests/test_phase38_extracted_value_contract.py

key-decisions:
  - "Task 1 and Task 2's overlapping files (api/services/admin_arguments.py, api/routers/admin.py) were edited together before either commit was made; the resulting task-attributed diffs were staged by final file state rather than hunk-split, so each file's cumulative rename (ORM-read-only in Task 1's design, full wire-contract in Task 2's) landed across the two commits as documented in each commit message rather than as two perfectly hunk-isolated diffs. No behavioral difference — same end state either way."
  - "RESOLVE-04 is NOT marked complete in REQUIREMENTS.md — the phase-wide coverage audit (44-01-PLAN.md) assigns this plan only the backend rename; the 'always renders / shows an en dash for Bench rows' UI behavior is Plan 44-02's job. Marking it complete now would be premature."

requirements-completed: []

coverage:
  - id: D1
    description: "Alembic migration 0025 renames argument_participants.title to .descriptor in place (no add/drop-column, no data-copy), applied to the dev DB (head 0025)"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_descriptor_rename.py#test_migration_0025_renames_in_place"
        status: pass
      - kind: other
        ref: "./.venv/Scripts/python.exe -m alembic current (reports 0025)"
        status: pass
    human_judgment: false
  - id: D2
    description: "ArgumentParticipant.descriptor ORM column declared; office_title/reason_left_title formal-office vocabulary untouched"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_descriptor_rename.py#test_models_declares_descriptor_column"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_descriptor_rename.py#test_office_title_vocabulary_untouched"
        status: pass
    human_judgment: false
  - id: D3
    description: "Job-scoped resolve-row descriptor write path (ResolveRowUpdate.descriptor -> update_resolve_row_for_job -> list_resolve_rows_for_job -> SvelteKit saveResolveRow -> ResolveCard.svelte) works end to end, and PJOB-15 bench-force (descriptor forced NULL when side==BENCH) survives the rename"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_jobs_phase25.py#test_update_resolve_row_advocate_descriptor_persists_bench_descriptor_forced_null"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_people_phase25.py#test_bench_row_descriptor_null_advocate_row_descriptor_present"
        status: pass
    human_judgment: false
  - id: D4
    description: "Argument-editor descriptor write path (ParticipantSideUpdate.descriptor -> update_participant_side -> PATCH /arguments/{id}/participants/{id}) round-trips correctly"
    verification:
      - kind: integration
        ref: "api/tests/test_admin_arguments_service.py#test_update_participant_side_persists_descriptor_for_advocate"
        status: pass
      - kind: integration
        ref: "api/tests/test_admin_arguments_routes.py#test_update_participant_route_persists_descriptor_for_advocate"
        status: pass
    human_judgment: false
  - id: D5
    description: "ResolveRowUpdate and ParticipantSideUpdate mass-assignment guards (T-25-15, T-26-04) and the WR-03 500-char cap survive the rename, asserted structurally via model_fields"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_descriptor_rename.py#test_resolve_row_update_guard_and_length_cap_survive"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_descriptor_rename.py#test_participant_side_update_guard_survives"
        status: pass
    human_judgment: false
  - id: D6
    description: "No file under api/, pipeline/, scripts/, or app/src/ references title_hint any more; every former title_hint site reads descriptor_hint"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_descriptor_rename.py#test_no_residual_title_hint_anywhere"
        status: pass
    human_judgment: false
  - id: D7
    description: "pipeline/commands/parse.py still writes the TOC subtitle for matched advocates and leaves unmatched participants at NULL, now via descriptor (_update_participant_descriptors)"
    verification:
      - kind: other
        ref: "python3 -m compileall -q pipeline api scripts tests alembic (exit 0); grep -c 'async def _update_participant_descriptors' pipeline/commands/parse.py == 1"
        status: pass
    human_judgment: false

duration: 36min
completed: 2026-08-01
status: complete
---

# Phase 44 Plan 01: Descriptor Rename Summary

**Full-stack rename of `ArgumentParticipant.title` to `.descriptor` (and `title_hint` to `descriptor_hint`) — new Alembic migration 0025, ORM, Pydantic schemas, services, routers, the pipeline TOC-subtitle writer, both SvelteKit consumers, all affected tests, and a new pure-source residual-name contract test.**

## Performance

- **Duration:** 36 min
- **Started:** 2026-08-01T17:17:00Z (approx., per STATE.md session marker)
- **Completed:** 2026-08-01T17:53:45Z
- **Tasks:** 3
- **Files modified:** 19 (2 new: migration + contract test; 1 new non-code: deferred-items.md)

## Accomplishments

- New Alembic migration `0025_rename_participant_title_to_descriptor.py` — a true in-place `op.alter_column(..., new_column_name=...)` rename, symmetric upgrade/downgrade, no add/drop-column, no data-copy step. Applied to the dev DB; `alembic current` confirms head `0025`.
- `ArgumentParticipant.descriptor` ORM column declared identically (`String(500), nullable=True`) to the old `.title`; `office_title()`/`reason_left_title()` (the unrelated formal-office-title vocabulary) left completely untouched, confirmed by both a grep-based acceptance check and a structural test.
- Both descriptor write paths work end to end under the new name:
  - Job-scoped resolve-row path: `ResolveRowUpdate.descriptor` -> `update_resolve_row_for_job` -> `list_resolve_rows_for_job` -> SvelteKit `saveResolveRow` -> `ResolveCard.svelte`. The PJOB-15 bench-force (`descriptor` forced `NULL` server-side whenever `side == BENCH`) survives byte-for-byte.
  - Argument-editor path: `ParticipantSideUpdate.descriptor` -> `update_participant_side` -> `PATCH /api/admin/arguments/{id}/participants/{pid}` -> the edit page's Speakers section.
- `pipeline/commands/parse.py`'s TOC-subtitle writer renamed to `_update_participant_descriptors` (parameter `descriptors_map`), still writing matched advocates' descriptors and leaving unmatched participants `NULL` (D-11 invariant unchanged). The upstream TOC vocabulary (`advocate_titles`, `cover_extractor.py`'s `_parse_toc_titles`) was deliberately left alone — it's a distinct, upstream concept.
- All five existing test files re-pointed at the renamed fields (constructor keywords, attribute assertions, projection-dict keys, JSON body keys, test function names) — no test dropped, no assertion weakened, same collected test count (35) for `test_admin_jobs_phase25.py`.
- New `api/tests/test_phase44_descriptor_rename.py`: a pure static source contract (no DB gate) that structurally guards the whole rename — migration shape, model column declaration, office-title vocabulary survival, a full `Path.rglob` sweep for zero residual `title_hint` under `api/`, `pipeline/`, `scripts/`, `app/src/`, and `model_fields`-based mass-assignment-guard equality checks on both schemas.

## Task Commits

Each task was committed atomically:

1. **Task 1: Descriptor rename end-to-end — migration, ORM, and the job-scoped resolve-row path** - `c9e5b274` (feat)
2. **Task 2: Extend the rename to the argument-editor write path and the diff-report label** - `cfd17de6` (feat)
3. **Task 3: Re-point every test assertion at the renamed fields and add the residual-name contract** - `03b23566` (test)

_Note: Tasks 1 and 2 both touch `api/services/admin_arguments.py` and `api/routers/admin.py` (Task 1 renamed only the ORM-attribute reads on those files per the plan's explicit split so nothing 500s mid-sequence; Task 2 completed the wire-contract rename on the same files). Both tasks' edits to those two files were made before either was committed, so the staged diffs were split by final content per task's designated scope rather than by git hunk — see Deviations below._

## Files Created/Modified

- `alembic/versions/0025_rename_participant_title_to_descriptor.py` - New migration, revision 0025, down_revision 0024, symmetric in-place rename
- `api/models/models.py` - `ArgumentParticipant.descriptor` column (office_title/reason_left_title untouched)
- `api/schemas/admin_jobs.py` - `ResolveRowUpdate.descriptor` (WR-03 500-char cap preserved)
- `api/schemas/admin_people.py` - `ResolveRow.descriptor`/`.descriptor_hint`
- `api/schemas/admin_arguments.py` - `ParticipantSideUpdate.descriptor`, `SpeakerRow.descriptor`/`.descriptor_hint`
- `api/services/admin_jobs.py` - `update_resolve_row_for_job` renamed, PJOB-15 force preserved
- `api/services/admin_people.py` - `list_resolve_rows_for_job` projection renamed, `office_title` import/usage intact
- `api/services/admin_arguments.py` - `list_argument_speakers` projection and `update_participant_side` renamed
- `api/routers/admin.py` - both resolve-rows handlers and the argument-editor PATCH handler renamed
- `pipeline/commands/parse.py` - `_update_participant_descriptors` (was `_update_participant_titles`)
- `scripts/diff_corpus_fixture.py` - upstream-missing report row now names `ArgumentParticipant.descriptor`
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` - `ResolveRow` interface, `saveResolveRow` form field/PATCH body key
- `app/src/routes/admin/arguments/[id]/+page.server.ts` - `SpeakerRow` interface, `updateParticipantSide` form field/PATCH body key
- `app/src/routes/admin/arguments/[id]/+page.svelte` - participants-table input, `CopyableExtractedValue` props/copyLabel ("Case title" and `<title>` untouched)
- `app/src/lib/components/ResolveCard.svelte` - `ResolveRow` interface, Title-column input/value/hint (header text and conditional structure untouched — 44-02 through 44-04 rework those)
- `api/tests/test_admin_jobs_phase25.py`, `test_admin_people_phase25.py`, `test_admin_arguments_service.py`, `test_admin_arguments_routes.py` - re-pointed at renamed fields/functions
- `api/tests/test_phase38_extracted_value_contract.py` - both stacked-provenance consumer tests re-pointed
- `api/tests/test_phase44_descriptor_rename.py` - new residual-name source contract
- `.planning/phases/44-resolve-table-rework/deferred-items.md` - new, logs two out-of-scope pre-existing issues found during verification (see below)

## Decisions Made

- **Task 1/Task 2 file-overlap commit granularity:** `api/services/admin_arguments.py` and `api/routers/admin.py` are named in both tasks' `<files>` lists. Both tasks' edits were applied to the working tree before either commit, so the two commits' diffs on these two files reflect final per-task scope (Task 1 = ORM-attribute-read renames only; Task 2 = full wire-contract rename) documented in each commit message, rather than perfectly git-hunk-isolated partial diffs. No behavioral difference in the end state; flagged here for commit-history transparency.
- **RESOLVE-04 left un-checked in REQUIREMENTS.md.** The phase-wide Source Coverage Audit in `44-01-PLAN.md` explicitly splits RESOLVE-04 across two plans: this plan (44-01) does the rename, plan 44-02 makes the Descriptor column "always render" (showing an en dash on Bench rows instead of disappearing). Marking the requirement complete after only the rename half would misrepresent state; it stays open until 44-02 lands.
- **Pre-existing environment issues logged, not fixed** (out of this task's scope boundary): a WSL/Windows path-concatenation bug in `test_phase38_people_ui_contract.py`'s Node-subprocess fixture path (unrelated file, last touched Phase 38), and a full-suite-invocation quirk where `pytest api/tests -q` alone doesn't trigger `tests/conftest.py`'s `TEST_DATABASE_URL` redirect (causing collisions against the real dev DB in unrelated tests). Both logged to `.planning/phases/44-resolve-table-rework/deferred-items.md`. Confirmed via isolated re-runs that neither is caused by this plan's changes — running the suite via `pytest tests/conftest.py api/tests -q` (forcing the redirect) produces 542 passed, 0 failed, with the same 4 pre-existing Node-subprocess errors.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `down_revision` type annotation to match acceptance criteria**
- **Found during:** Task 1 (writing the migration)
- **Issue:** Initially wrote `down_revision: Union[str, None] = "0024"` (matching migrations 0013/0024's style), but the plan's own acceptance criteria requires the literal string `down_revision: str = "0024"` (matching migration 0021's style, the plan's named analog).
- **Fix:** Changed the type annotation to `str` to match the acceptance criterion exactly.
- **Files modified:** `alembic/versions/0025_rename_participant_title_to_descriptor.py`
- **Verification:** `grep -c 'down_revision: str = "0024"'` returns 1.
- **Committed in:** `c9e5b274` (Task 1 commit)

**2. [Rule 1 - Bug] Removed a stray `title_hint`/`ArgumentParticipant.title` reference from a docstring I had just written**
- **Found during:** Task 2 (writing `api/schemas/admin_arguments.py`'s module docstring)
- **Issue:** My own added "Phase 44 additions" docstring paragraph referenced the pre-rename names (`title/title_hint`, `ArgumentParticipant.title`) to explain what was renamed, which would have made Task 2's own acceptance criterion ("0 title_hint matches outside api/tests/") fail against my own new text.
- **Fix:** Reworded the paragraph to describe the rename without naming the old fields literally.
- **Files modified:** `api/schemas/admin_arguments.py`
- **Verification:** `grep -rc 'title_hint' api/ pipeline/ scripts/ app/src/` shows 0 matches outside `api/tests/`.
- **Committed in:** `cfd17de6` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — self-caught formatting/consistency bugs, no scope creep).
**Impact on plan:** Both fixes were necessary for the plan's own acceptance criteria to pass exactly as written. No design decisions were revisited.

## Issues Encountered

None beyond the two auto-fixed items above and the two out-of-scope pre-existing environment issues logged to `deferred-items.md` (neither caused by, nor fixable within, this plan's scope).

## User Setup Required

None - no external service configuration required. The Alembic migration was applied directly to the existing dev database as part of Task 1 (`alembic upgrade head`), per the plan's own instruction that a passing build/type-check is not proof the migration ran — it was independently confirmed via `alembic current` reporting `0025`.

## Next Phase Readiness

- Plan 44-02 can proceed: the `descriptor`/`descriptor_hint` field names are now stable everywhere (backend and both SvelteKit consumers), so 44-02's Resolve-table column rework (5-column layout, Resolved As consolidation, always-rendered Descriptor cell) can build directly on top without touching the underlying wire contract again.
- Plans 44-03 and 44-04 similarly inherit a stable `descriptor` name for the segmented Bench/Advocate toggle, Argument Role controls, and the "Imported:" hint rework.
- No blockers. The two logged deferred items (Node-subprocess path bug, full-suite invocation quirk) are pre-existing and unrelated to any file this plan touches — they do not block subsequent Phase 44 plans.

---
*Phase: 44-resolve-table-rework*
*Completed: 2026-08-01*

## Self-Check: PASSED

- FOUND: `alembic/versions/0025_rename_participant_title_to_descriptor.py`
- FOUND: `api/tests/test_phase44_descriptor_rename.py`
- FOUND: `.planning/phases/44-resolve-table-rework/44-01-SUMMARY.md`
- FOUND: `.planning/phases/44-resolve-table-rework/deferred-items.md`
- FOUND: commit `c9e5b274` (Task 1)
- FOUND: commit `cfd17de6` (Task 2)
- FOUND: commit `03b23566` (Task 3)
- FOUND: commit `32cd81db` (SUMMARY.md/deferred-items.md)
