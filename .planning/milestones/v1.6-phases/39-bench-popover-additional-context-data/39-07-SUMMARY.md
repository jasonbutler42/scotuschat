---
phase: 39-bench-popover-additional-context-data
plan: 07
subsystem: ui
tags: [sveltekit, svelte5-runes, admin-editor, form-actions, gap-closure]

# Dependency graph
requires:
  - phase: 39-bench-popover-additional-context-data
    provides: "Plan 39-03's death_date/reason_left wiring into the same save action and fail() restore objects this plan extends; api/services/admin_people.py's model_fields_set-guarded bio_text write (pre-existing, untouched)"
provides:
  - "app/src/routes/admin/people/[id]/+page.svelte: Biography card outside the photo form, its textarea cross-form-associated with save-form via bind:value={bioText}"
  - "app/src/routes/admin/people/[id]/+page.server.ts: save action reads/forwards bio_text (presence-guarded conditional spread) and restores it in all five fail() calls; photo action performs no person PATCH at all"
  - "api/tests/test_phase39_bio_save_contract.py: 11-test pure-Python source-contract regression suite (no DB) pinning bio-field ownership"
affects: [39-08, 39-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-form field association via the `form` attribute (already used by the Person Type card's hidden inputs) extended to a genuinely operator-visible textarea, not just hidden inputs"
    - "Presence-guarded conditional spread (...(submitted ? { field } : {})) for a field whose card might not always be mounted, distinct from birthdate/death_date's always-present hidden-input pattern which needs no such guard"

key-files:
  created:
    - api/tests/test_phase39_bio_save_contract.py
  modified:
    - "app/src/routes/admin/people/[id]/+page.svelte"
    - "app/src/routes/admin/people/[id]/+page.server.ts"
    - api/tests/test_admin_people.py

key-decisions:
  - "Split the plan's two tasks into two atomic commits by temporarily reverting Task 2's edits after both were drafted together, verifying Task 1 alone, committing, then reapplying Task 2 and verifying/committing separately -- preserves per-task traceability without redoing analysis work"
  - "Updated api/tests/test_admin_people.py's docstring/comments describing 'the Bio+Photo form (photo action)' to describe the new ownership (bio_text now sent by Save Person) -- documentation-accuracy only, the test's actual PATCH assertions were already action-agnostic and needed no behavior change"

requirements-completed: [PUB-04]

coverage:
  - id: D1
    description: "The Biography textarea associates with save-form (form=\"save-form\") and sits outside the photo form as a sibling, not a child, so Save Person's PATCH carries bio_text"
    requirement: "PUB-04"
    verification:
      - kind: unit
        ref: "api/tests/test_phase39_bio_save_contract.py::test_bio_textarea_is_associated_with_save_form"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase39_bio_save_contract.py::test_biography_card_sits_outside_the_photo_form"
        status: pass
    human_judgment: false
  - id: D2
    description: "The save action reads bio_text with a presence guard and forwards it as a conditional spread (absent field never blanks a stored bio); the photo action performs no person PATCH at all"
    requirement: "PUB-04"
    verification:
      - kind: unit
        ref: "api/tests/test_phase39_bio_save_contract.py::test_save_action_forwards_the_bio"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase39_bio_save_contract.py::test_save_action_bio_is_a_conditional_spread"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase39_bio_save_contract.py::test_photo_action_performs_no_person_patch"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase39_bio_save_contract.py::test_photo_action_still_uploads_photos"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase39_bio_save_contract.py::test_no_stale_bio_ownership_language_in_server_file"
        status: pass
    human_judgment: false
  - id: D3
    description: "The textarea is bound (bind:value={bioText}), not seeded as child text content; bioText resyncs on person-id change and restores on a failed save via !== undefined so an intentionally cleared bio restores empty, not stale"
    requirement: "PUB-04"
    verification:
      - kind: unit
        ref: "api/tests/test_phase39_bio_save_contract.py::test_bio_textarea_is_bound_not_seeded"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase39_bio_save_contract.py::test_person_change_reset_covers_the_bio"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase39_bio_save_contract.py::test_failed_save_restore_covers_the_bio"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase39_bio_save_contract.py::test_every_failed_save_restores_the_bio"
        status: pass
    human_judgment: false
  - id: D4
    description: "A live round-trip -- type a bio, click Save Person, reload, confirm it persists and displays on the public popover -- actually works end to end"
    verification: []
    human_judgment: true
    rationale: "This WSL session cannot reach the real dev database or drive the browser (documented WSL/Windows split). The live operator checkpoint is explicitly deferred to Plan 39-09 per this plan's own <verification> section; this plan's evidence is the source-contract test suite plus static grep/verify gates, not a live round-trip."

duration: ~50min
completed: 2026-07-28
status: complete
---

# Phase 39 Plan 07: Bio save gap closure Summary

**Moved bio_text ownership from the photo action to the save action so the primary Save Person button now saves the whole person atomically, including the bio -- closing 39-UAT.md gap 1/test 10.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-07-28
- **Tasks:** 2 completed
- **Files modified:** 4 (1 new file)

## Accomplishments
- Confirmed the plan's diagnosis against the current file state before editing: `bio_text` was submitted only by the `photo` action (whose only button is "Upload photo"), the `save` action's PATCH body deliberately omitted it, the `photo` action's own bio PATCH was unchecked and its rejection discarded (`.catch(() => {})`), and the Biography `<textarea>` rendered its stored value as child text content — all four defects matched the plan's stated root cause exactly, with no additional cause found.
- `app/src/routes/admin/people/[id]/+page.svelte`: closed the `?/photo` form immediately after the Photo card so the Biography card is now a sibling below it, not a child; the bio `<textarea>` carries `form="save-form"` (the same cross-form idiom the Person Type card's hidden inputs already use) plus a new `bioText` `$state` bound via `bind:value`; a "Saved with Save Person." hint line sits under the Bio label.
- `app/src/routes/admin/people/[id]/+page.server.ts`: the `save` action now reads `bio_text` with a presence guard (`formData.has('bio_text')`) and forwards it via a conditional spread (`...(bioTextSubmitted ? { bio_text } : {})`) so an absent field can never blank a stored bio; every one of the five `fail()` restore objects now also carries `bio_text`. The `photo` action no longer PATCHes the person at all — the unchecked request, its local `bio_text` read, and the discarded rejection handler are gone; it only forwards the photo upload.
- `api/tests/test_phase39_bio_save_contract.py`: new 11-test pure-Python source-contract module (no DB, no `_db_configured` gate, no `node` subprocess) following `test_phase38_people_ui_contract.py`'s `ROOT`/`_source(path)` idiom, with slicing helpers scoping assertions to the `save` and `photo` action bodies independently.
- `api/tests/test_admin_people.py`: updated the stale "Bio+Photo form ('photo' action)" docstring/comments in `test_update_person_partial_patch_does_not_wipe_other_fields` to describe the new ownership — the test's actual PATCH assertions (an API-level CR-01 regression, independent of which SvelteKit action sends them) needed no behavior change.

## Task Commits

Each task was committed atomically:

1. **Task 1: Move bio_text onto the Save Person path, end to end** - `98bae58c` (feat)
2. **Task 2: Make the textarea show persisted state, and never lose a typed bio on a failed save** - `ede9c606` (fix)

## Files Created/Modified
- `api/tests/test_phase39_bio_save_contract.py` - 11 pure-Python source-contract tests (7 from Task 1, 4 from Task 2)
- `app/src/routes/admin/people/[id]/+page.svelte` - Biography card moved outside the photo form; textarea gets `form="save-form"` + `bind:value={bioText}`; `bioText` `$state` declared, resynced on person change, restored on failed save; hint copy added
- `app/src/routes/admin/people/[id]/+page.server.ts` - `save` action reads/forwards `bio_text` (presence-guarded conditional spread) and restores it in all 5 `fail()` calls; `photo` action's person PATCH, its local `bio_text` read, and its `.catch()` deleted entirely; docstrings rewritten to state the new ownership
- `api/tests/test_admin_people.py` - stale form-ownership docstring/comments corrected (no assertion changes)

## Decisions Made
- Split what was drafted as one combined edit pass into two atomic per-task commits: after implementing both tasks' code changes together, I temporarily reverted Task 2's specific additions (the `bioText` state, its two `$effect` wire-ups, the `bind:value` textarea change, the fifth-field addition to the 5 `fail()` objects, and tests 8-11), re-verified Task 1's 7 tests and acceptance gates in isolation, committed, then reapplied Task 2's changes, re-verified all 11 tests and gates, and committed separately. This preserved the plan's one-commit-per-task structure without discarding any analysis or re-doing the diagnosis.
- Updated `api/tests/test_admin_people.py`'s docstring describing which SvelteKit form/action sends which fields, since Task 1 changed that ownership and the old comment now described the opposite of reality. The test's own PATCH-body assertions were already written directly against the API (not through the SvelteKit route) and needed no functional change — this is a documentation-accuracy fix, not new test coverage, matching the file's inclusion in the plan's `files_modified` frontmatter list even though neither task's `<files>` tag named it explicitly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Documentation accuracy] Corrected stale form-ownership comments in `api/tests/test_admin_people.py`**
- **Found during:** Task 1 (reviewing the plan's `files_modified` frontmatter, which lists this file though neither task's `<files>` tag does)
- **Issue:** The test's docstring and two inline comments described "the Bio+Photo form ('photo' action)" as the sender of `bio_text` — now backwards, since Task 1 moved that ownership to the `save` action / Save Person form.
- **Fix:** Reworded the docstring and both inline comments to state the new ownership, without touching any assertion or PATCH body in the test.
- **Files modified:** api/tests/test_admin_people.py
- **Verification:** Full test file still passes (part of the 767-passed full-suite run below); no assertion text changed.
- **Committed in:** `98bae58c` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1, documentation accuracy only)
**Impact on plan:** No functional scope creep — the fix was a comment/docstring correction in a file the plan's own frontmatter already listed as in scope, with zero change to test behavior or assertions.

## Issues Encountered

- **The Task 1 `<verify>` gate `! grep -q "Non-critical" '…/+page.server.ts'` does not pass on the whole file, but the reason is a pre-existing, out-of-scope match, not a regression.** The `load` function's merge-picker people-list fetch has carried a `// Non-critical — degrade gracefully; merge picker will be empty` comment since before this plan (an unrelated read-only fetch, not a write). This plan's actual target — the comment describing the `photo` action's unchecked, discarded-rejection **write** — is gone (confirmed via the narrower, in-scope check: `grep -n -i "non-critical\|best-effort" +page.server.ts` returns exactly one hit, at the pre-existing `load`-function line, none in either action). Per the executor's scope boundary ("only auto-fix issues directly caused by the current task's changes; pre-existing... out of scope, do not fix them"), this unrelated comment was left untouched. The substantive truth this gate exists to protect — "no code path discards submitted bio text without saying so" — holds: no comment anywhere in the file now describes an ignored write.
- Confirmed the true pre-Plan-07 `npm run check` baseline was **0 errors, 34 warnings** (from Plan 39-05's SUMMARY, the most recent recorded baseline before this plan, superseding the older 39-03 baseline of the same count). This plan's post-task run is **0 errors, 36 warnings** (804 files, 10 files with problems) — a +2 delta fully attributable to the one new `bioText = $state<string>(form?.bio_text ?? data.person.bio_text ?? '')` declaration Task 2 adds, which triggers Svelte 5's `state_referenced_locally` lint exactly once per `form`/`data` reference (2 warnings), the identical lint pattern already firing for every other prop-seeded `$state` on this same page (`isJustice`, `birthdate`, `deathDate`, the four name-part fields, `tenureRows` — 8 pre-existing occurrences of the same idiom, 16 of the 34 baseline warnings). No new error, no new warning category.
- WSL/Windows split (per project memory): all pytest runs used `./.venv/Scripts/python.exe -m pytest` with no explicit test path, letting `tests/conftest.py` load first and redirect to the isolated test database, per the documented safe-invocation pattern from Plan 39-03.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The RED run (before any edit) failed 6 of 7 Task 1 assertions — `test_bio_textarea_is_associated_with_save_form`, `test_biography_card_sits_outside_the_photo_form`, `test_save_action_forwards_the_bio`, `test_save_action_bio_is_a_conditional_spread`, `test_photo_action_performs_no_person_patch`, and `test_no_stale_bio_ownership_language_in_server_file` all failed pre-edit; only `test_photo_action_still_uploads_photos` passed (the photo upload behavior this plan does not change). This is the evidence the new test suite actually pins the defect described in 39-UAT.md gap 1.
- `grep -c 'form="save-form"'` on the svelte file: 7 (pre-task) → 8 (post-task), exactly +1 for the textarea's new association.
- `grep -c "method: 'PATCH'"` on the server file: 2 (pre-task) → 1 (post-task) — the photo action's PATCH is gone, only the save action's remains.
- Full suite (`pytest`, no explicit path, from repo root): 767 passed, 5 xfailed, 4 errors (all four are the pre-existing `test_phase38_people_ui_contract.py` Windows-path node-driver failures documented in 38-UAT.md/STATE.md — not this plan's regression), 12 warnings (pre-existing Alembic deprecation notices, unrelated).
- `cd app && npm run check`: 0 errors, 36 warnings (804 files, 10 files with problems) — see Issues Encountered for the +2 delta explanation.
- Plan 39-09's live operator checkpoint still needs to confirm the actual round-trip on the real dev DB/browser (this WSL session cannot drive either): type a bio, click Save Person, reload, confirm it persists and now displays on the public bench popover with a working clamp/Read-more toggle (39-06's test 7 was blocked on exactly this gap).
- `api/services/admin_people.py`, `api/schemas/admin_people.py`, and every FastAPI route were confirmed untouched, per the plan's explicit scope — the defect was fully contained to the two SvelteKit route files.

## Self-Check: PASSED

All 4 modified/created files confirmed present on disk with expected content (`api/tests/test_phase39_bio_save_contract.py`, `app/src/routes/admin/people/[id]/+page.svelte`, `app/src/routes/admin/people/[id]/+page.server.ts`, `api/tests/test_admin_people.py`); both commits (`98bae58c`, `ede9c606`) confirmed present in `git log --oneline`.

---
*Phase: 39-bench-popover-additional-context-data*
*Completed: 2026-07-28*
