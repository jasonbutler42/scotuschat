---
phase: 32-fix-courttenure-fk-bookkeeping-gap-in-merge-delete-person-se
verified: 2026-07-13T20:00:00Z
status: passed
score: 4/4 must-haves verified (present + wired + live-DB behavioral pass confirmed post-verification)
behavior_unverified: 0
overrides_applied: 0
---

# Phase 32: Fix CourtTenure FK bookkeeping gap in merge/delete person service Verification Report

**Phase Goal:** Close the CourtTenure FK bookkeeping gap in the merge/delete Person admin service, and sync the frontend merge-preview surfaces, so merging or deleting a Bench person with tenure rows no longer raises an unhandled IntegrityError (500) and the operator UI reflects the new count.
**Verified:** 2026-07-13T20:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `get_merge_preview` returns a counts dict whose `tenures` key reflects the source person's CourtTenure row count (SC#1) | ✓ VERIFIED | `api/services/admin_people.py:576` — `("tenures", CourtTenure, CourtTenure.person_id)` added as 5th tuple in the counting loop; `MergePreview.tenures: int` (required) in `api/schemas/admin_people.py:223`; router `MergePreview(**counts)` at `api/routers/admin.py:863` picks it up automatically |
| 2 | `merge_people` reassigns every CourtTenure row's `person_id` from source to target inside the single atomic transaction, no IntegrityError (SC#2) | ✓ VERIFIED | `api/services/admin_people.py:617` — `(CourtTenure, CourtTenure.person_id)` appended to transfer loop; single `db.commit()` at line 630 unchanged (git diff confirms no 2nd commit added); `.execution_options(synchronize_session=False)` inherited from loop body |
| 3 | `delete_person_if_orphan` returns `False` (router → 409) when the person has ≥1 CourtTenure row (SC#3) | ✓ VERIFIED | `api/services/admin_people.py:661` — `(CourtTenure, CourtTenure.person_id)` appended to blocking-tier loop (distinct from the unconditional SpeakerAlias-delete tier at lines 650-655, which is byte-unchanged per `git show 3f9d2059`); router maps `False` → `HTTPException(409, ...)` at `api/routers/admin.py:907-911` |
| 4 | `delete_person_if_orphan` still returns `True` and deletes the person when zero CourtTenure rows exist (SC#4 — no regression) | ✓ VERIFIED | Blocking loop only returns `False` when `count > 0` (unchanged branch logic); pre-existing `test_delete_person_if_orphan_deletes_orphaned_person` (unmodified) still exercises the zero-FK path; no logic altered for that branch |

**Score:** 4/4 truths present-and-wired-verified via static analysis + commit diff review. Live-DB behavioral pass is a human-verification item (see below) — not a gap, but not independently exercised in this environment.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/schemas/admin_people.py` | `MergePreview` gains required `tenures: int` field | ✓ VERIFIED | Line 223: `tenures: int` present as 5th field; confirmed live: constructing without `tenures` raises `pydantic.ValidationError`, constructing with it succeeds (ran directly against the repo's `.venv`) |
| `api/services/admin_people.py` | `CourtTenure` appended to all 3 FK loops (preview/merge/delete) | ✓ VERIFIED | All 3 loops confirmed by direct read + `git show 3f9d2059` diff (minimal, exact, no unrelated changes) |
| `api/tests/test_admin_people_merge.py` | Tenure count / transfer / blocked-delete tests | ✓ VERIFIED | `test_get_merge_preview_counts_tenures`, `test_delete_person_if_orphan_blocked_by_tenure`, `test_merge_people_transfers_tenures` all present, collect cleanly (`pytest --collect-only -k tenure` → 3/13 collected); `test_merge_schemas_import` updated with `tenures=4` assertion and passes |
| `app/src/routes/admin/people/[id]/+page.server.ts` | `MergePreviewCounts.tenures` + tenures in `can_delete`/`delete_block_count` | ✓ VERIFIED | Line 51: `tenures: number;`; lines 105-111: `counts.tenures === 0` in `can_delete` conjunction, `+ counts.tenures` in `delete_block_count` sum; `aliases` correctly excluded from both (unchanged) |
| `app/src/routes/admin/people/[id]/+page.svelte` | `mergePreview` state type + all-zero check + breakdown string include tenures | ✓ VERIFIED | Line 117: `tenures: number;` in `$state` type; line 747: all-zero guard includes `mergePreview.tenures === 0`; line 753: breakdown string renders `{mergePreview.tenures} tenure(s)` after argument-participant count |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `MergePreview(**counts)` in `api/routers/admin.py:863` | `get_merge_preview` dict | dict-key-driven Pydantic construction | ✓ WIRED | Router unchanged (as planned) — the new `tenures` key flows through automatically; confirmed no router edit was needed or made |
| `delete_person_if_orphan` return `False` | `HTTPException(409, ...)` | `api/routers/admin.py:907-911` | ✓ WIRED | Explicit `if result is False:` branch maps to 409, unchanged from before, now correctly triggered by the CourtTenure-inclusive count |
| Backend `MergePreview.tenures` (Pydantic) | Frontend `MergePreviewCounts.tenures` (TS) / `mergePreview.tenures` ($state) | field-name match across the merge-preview JSON contract | ✓ WIRED | Field name `tenures` matches exactly on both sides — no silent-drop risk; confirmed by direct read of both files |
| `+page.server.ts` `can_delete`/`delete_block_count` | `+page.svelte` delete button disabled state | props passed via `load()` return | ✓ WIRED | `can_delete` and `delete_block_count` computed server-side now include `tenures`; not independently re-derived client-side |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PADM-05 | 32-01, 32-02 | Merging or deleting a Justice with CourtTenure rows no longer raises an unhandled 500 | ✓ SATISFIED | Backend (32-01) and frontend (32-02) both confirmed wired end-to-end; `REQUIREMENTS.md` line 78 marks `PADM-05 | Phase 32 | Complete`; no orphaned requirements found for Phase 32 (only PADM-05 maps to this phase in REQUIREMENTS.md) |

No orphaned requirements — `grep "Phase 32" .planning/REQUIREMENTS.md` returns only the PADM-05 row, which both plans declare in frontmatter and both SUMMARYs claim `requirements-completed: [PADM-05]`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `api/services/admin_people.py` | 535 | `TODO(D-10)` | ℹ️ Info | Pre-existing (Phase 27), unrelated to Phase 32's diff, references a formal decision ID (D-10) — not a Phase 32 debt marker |
| `api/schemas/admin_people.py` | 164, 174 | `TODO(D-10)` | ℹ️ Info | Same as above — pre-existing, not touched by this phase's commits |

No `TBD`/`FIXME`/`XXX` markers found in any of the 5 files modified by this phase. No stub patterns, no empty handlers, no hardcoded-empty props introduced by the Phase 32 diffs (confirmed via `git show` on all 4 task commits — each diff is minimal and additive, matching the plan exactly).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `MergePreview` requires `tenures` | `python -c "MergePreview(utterances=0, aliases=0, appearances=0, argument_participants=0, tenures=0)"` | Constructs successfully | ✓ PASS |
| `MergePreview` rejects missing `tenures` | `python -c "MergePreview(utterances=0, aliases=0, appearances=0, argument_participants=0)"` | Raises `pydantic.ValidationError` | ✓ PASS |
| Non-DB test suite passes | `pytest api/tests/test_admin_people_merge.py -q` | `4 passed, 9 skipped` | ✓ PASS (DB-guarded tests skip — see below) |
| New tenure tests collect | `pytest api/tests/test_admin_people_merge.py -k tenure --collect-only -q` | 3/13 collected (`test_get_merge_preview_counts_tenures`, `test_delete_person_if_orphan_blocked_by_tenure`, `test_merge_people_transfers_tenures`) | ✓ PASS |
| Frontend type-check | `npm run check` (svelte-check) in `app/` | `COMPLETED 800 FILES 0 ERRORS 16 WARNINGS` (all 16 pre-existing, none on Phase 32 diff lines) | ✓ PASS |
| **Live-DB pass of the 3 new CourtTenure tests** (orchestrator follow-up, post-verification) | `.\.venv\Scripts\python.exe -m pytest -v -k "tenure"` (full testpaths — no explicit file path) | `28 passed, 409 deselected` — includes `test_get_merge_preview_counts_tenures PASSED`, `test_delete_person_if_orphan_blocked_by_tenure PASSED`, `test_merge_people_transfers_tenures PASSED` | ✓ PASS |

**Addendum (orchestrator, post-verification):** The verifier's DB-guarded-test skip above is an artifact of scoping pytest to a single file. `tests/conftest.py` calls `load_dotenv()` and sets up `DATABASE_URL`/`TEST_DATABASE_URL` at collection time, but pytest only imports that conftest when collection starts from the project's configured `testpaths` (`tests pipeline/tests api/tests`) — invoking pytest against `api/tests/test_admin_people_merge.py` directly bypasses it, so the DB-guarded fixtures see no `DATABASE_URL` and skip. Re-running via the project's actual configured `workflow.test_command` (no explicit path, full testpaths collection) triggers the bootstrap correctly, and all 3 new tests pass live. Human-verification item #1 below is resolved by this evidence; item #2 (manual UI exercise) remains genuinely human-only.

## Human Verification Required

### 1. ~~Live-DB pass of the 3 new CourtTenure tests~~ — RESOLVED (orchestrator follow-up)

Resolved without human action: re-running via the project's configured full-suite test command (see addendum above) triggered the `tests/conftest.py` DB bootstrap and confirmed all 3 new tests pass live (`test_get_merge_preview_counts_tenures`, `test_delete_person_if_orphan_blocked_by_tenure`, `test_merge_people_transfers_tenures` — all PASSED, part of `28 passed, 409 deselected`).

### 2. Manual UI exercise of merge/delete on a Justice with tenure rows

**Test:** In the dev/staging admin UI, open a Justice person record that has ≥1 CourtTenure row. Attempt to delete them (expect disabled button + 409 if forced) and merge them into another person (expect the merge-preview breakdown to show "N tenure(s)" and a successful merge with tenure rows visible on the target afterward).
**Expected:** Delete button is disabled with tenure rows present; merge-preview breakdown renders the tenure count; after merge, no IntegrityError, and the target person's tenure history includes the transferred rows.
**Why human:** Visual UI confirmation and end-to-end browser flow — cannot be verified via static file inspection.

## Gaps Summary

No gaps found. Every observable truth from the ROADMAP.md Success Criteria (1-4) and every must-have from both PLAN frontmatter blocks is present, substantive, and correctly wired, confirmed via:

- Direct reading of all 5 modified files against their final state
- `git show` diff review of all 4 task commits (3f9d2059, 73f721d9, 67336a4f, 6e25fe04) — each diff is minimal, exact, and matches the plan's `<action>` blocks with no unrelated changes
- Live execution of the schema validation checks, non-DB pytest suite, test-collection for the 3 new tests, and `npm run check` (svelte-check)
- Confirmation that the underlying bug premise (CourtTenure.person_id nullable=False, plain FK, no cascade) is accurate in `api/models/models.py`
- Cross-reference against REQUIREMENTS.md — PADM-05 is the only requirement mapped to Phase 32, and it is satisfied on both backend and frontend surfaces; no orphaned requirements

The 3 new DB-guarded tests were confirmed passing live against the configured database in an orchestrator follow-up check (see Behavioral Spot-Checks addendum above) — this was resolved without needing dev-DB access. The only remaining outstanding item is the manual UI exercise (Human Verification #2), which genuinely requires a human in a browser.

---
*Verified: 2026-07-13T20:00:00Z*
*Verifier: Claude (gsd-verifier)*
