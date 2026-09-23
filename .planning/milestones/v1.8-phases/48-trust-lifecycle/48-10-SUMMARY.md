---
phase: 48-trust-lifecycle
plan: 10
subsystem: ui
tags: [sveltekit, svelte5-runes, fastapi, form-actions, admin, trust-tier, accessibility]

# Dependency graph
requires:
  - phase: 48-07
    provides: the two-gate publish endpoint (uncertain_tier_blocked / blank_override_reason / plain-string resolve-gate and already-published guard) that both the list and detail pages relay
  - phase: 48-08
    provides: the detail page's original publish-block-and-override UI pattern (Status card block panel, publishingState, blockerSentence) that this plan mirrors onto the list page and then had to fix
provides:
  - List-page (`/admin/arguments`) publish block/override UI at parity with the detail page, addressed to the correct row on a shared `form` prop
  - Per-row passive trust-tier badge on the list page
  - Genuine public-visibility enforcement on unpublish across all three public read paths (`get_cases`, `get_argument_with_utterances`, `get_argument_speakers`)
  - A `source`-tagged `fail()` payload convention on pages with a shared `form` prop spanning multiple actions, so an error renders in the correct UI region instead of leaking into an unrelated one
  - A keyboard-accessible, non-destructive dismiss affordance for a server-driven block panel, using a client Rune compared by reference rather than mutating shared form state
affects: [49-review-model, 51-design-system]

# Actuals (#2632)
actuals:
  tokens: 18662
  tasks: 4
  commits: 12

tech-stack:
  added: []
  patterns:
    - "`source: '<action>'` tag on every SvelteKit form-action `fail()` payload, used to route a shared `form` prop's error to the correct UI card/region when a page has more than one action returning the same `error` key"
    - "Positive ownership test (`!form.source`) for a page's default/untagged action, preferred over an ever-growing negative exclusion list as more actions are tagged"
    - "Client-side dismissal of a server-driven panel via a local Rune compared by object reference against the current `form` (not by mutating `form`, and not by a boolean flag that would need manual resetting) — a fresh action result is always a new object, so re-submission naturally un-dismisses the panel"

key-files:
  created:
    - api/tests/test_phase48_detail_publish_error_rendering_contract.py
  modified:
    - api/schemas/admin_arguments.py
    - api/services/admin_arguments.py
    - api/services/cases.py
    - api/services/arguments.py
    - api/services/speakers.py
    - api/routers/admin.py
    - app/src/routes/admin/arguments/+page.server.ts
    - app/src/routes/admin/arguments/+page.svelte
    - app/src/routes/admin/arguments/[id]/+page.server.ts
    - app/src/routes/admin/arguments/[id]/+page.svelte
    - api/tests/test_phase48_unpublish_visibility.py
    - api/tests/test_phase48_list_publish_override_ui_contract.py

key-decisions:
  - "Task 4's operator checkpoint found a REAL DEFECT (not a plan gap): the detail page's `?/publish` server action was already correct (48-08), but `+page.svelte` rendered `form?.error` in exactly one place — the case-metadata card's alert slot — so a non-overridable-gate failure (D-14) produced no visible feedback in the Status card, and could leak into an unrelated card. Fixed by tagging every publish `fail()` payload with `source: 'publish'` and rendering it, visibly and with no reason field, in the Status card."
  - "By inspection immediately after fixing publish, found the identical defect in `unpublish`'s two untagged `fail()` payloads. Fixed the same way (`source: 'unpublish'`), and widened the Status-card error condition to one guard covering both sources — placed OUTSIDE the draft/unpublished-vs-published branch so it renders next to whichever control (Publish or Unpublish) is currently visible, rather than duplicating a near-identical block per branch."
  - "Case-metadata card's exclusion changed from a negative list (`form.source !== 'publish'`) to a positive test (`!form.source`) — `?/save` is the only action returning an untagged `error`, so this stays correct if a future action is added without anyone needing to remember to extend an exclusion list."
  - "List-page block panel: added a plain-text 'Cancel' button (not an icon-only '×') to match the existing Danger Zone two-step-delete-confirm convention already established in this codebase. Dismisses the WHOLE panel (operator's stated preference — Publish can always be clicked again to bring it back), tracked via a local Rune (`dismissedForm`) compared by reference against the current `form`, so re-submitting Publish on the same row naturally un-dismisses it without extra reset logic."
  - "Detail-page Status card's 'Last published'/'Published' and 'Created' readouts switched from `formatDate` to the existing `formatDateTime` helper (no new formatter introduced) so they read consistently with the Status History list on the same card, which already shows times."
  - "The unpublish-error-rendering fix is verified by static contract test ONLY, not by a live browser walkthrough — the failure path requires the backend call itself to fail, which is not reachable from any UI state the operator can produce. The operator explicitly accepted this on the strength of the contract test alone; this is recorded, not silently upgraded to 'verified'."

patterns-established:
  - "`source` discriminator on shared-`form` pages: tag every action's `fail()` payload with its own action name so the page's error-rendering regions can each claim only their own action's errors, using a positive test for whichever action owns the untagged default."
  - "Reference-equality dismissal Rune: `let dismissedX = $state<unknown>(null)` compared as `form !== dismissedX`, set via `dismissedX = form` on Cancel — dismisses the CURRENT result without needing to track which row/id it belonged to, because SvelteKit's `form` prop is always a fresh object per action result."

requirements-completed: [TRUST-04, TRUST-05]

coverage:
  - id: D1
    description: "List-page (/admin/arguments) publish block/override UI at parity with the detail page — tier, server message, per-blocker breakdown, override reason field, addressed to the correct row"
    requirement: "TRUST-05"
    verification:
      - kind: other
        ref: "api/tests/test_phase48_list_publish_override_ui_contract.py (20 tests)"
        status: pass
      - kind: manual_procedural
        ref: "48-10 Task 4 checkpoint steps 1-6, 8 (operator browser walkthrough, prior session)"
        status: pass
    human_judgment: true
    rationale: "must_haves includes a verification: backstop truth (block-reason wording reads clearly to a real operator) that no automated check in this repo can confirm."
  - id: D2
    description: "Passive per-row trust-tier badge on the list page, never wired to any control, Publish button never disabled by tier"
    requirement: "TRUST-05"
    verification:
      - kind: other
        ref: "api/tests/test_phase48_list_publish_override_ui_contract.py::test_passive_tier_badge_renders_per_row, ::test_publish_button_never_disabled_based_on_tier_or_block_state"
        status: pass
    human_judgment: false
  - id: D3
    description: "Unpublish genuinely hides an argument from all three public read paths (get_cases, get_argument_with_utterances, get_argument_speakers)"
    requirement: "TRUST-04"
    verification:
      - kind: integration
        ref: "api/tests/test_phase48_unpublish_visibility.py"
        status: pass
      - kind: manual_procedural
        ref: "48-10 Task 4 checkpoint step 7 (operator browser walkthrough, prior session)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Detail-page publish-error rendering defect (found live at the Task 4 checkpoint): non-overridable resolve-gate / already-published errors now render visibly in the Status card, next to the Publish button, with no reason field; no longer leak into the case-metadata card"
    requirement: "TRUST-05"
    verification:
      - kind: other
        ref: "api/tests/test_phase48_detail_publish_error_rendering_contract.py (publish-scoped tests)"
        status: pass
      - kind: manual_procedural
        ref: "48-10 Task 4 re-verification, this session — operator confirmed live in the browser"
        status: pass
    human_judgment: true
    rationale: "The original defect was found by a human in a browser, not by any automated check; the fix's acceptance is likewise the operator's own live re-verification, recorded verbatim rather than inferred from tests."
  - id: D5
    description: "Detail-page unpublish-error rendering fix (same defect, found by inspection): unpublish fail() payloads tagged source:'unpublish'; case-metadata card's exclusion widened via a positive !form.source test so it excludes errors from ANY tagged action, not just publish"
    requirement: "TRUST-05"
    verification:
      - kind: other
        ref: "api/tests/test_phase48_detail_publish_error_rendering_contract.py (unpublish-scoped tests)"
        status: pass
    human_judgment: true
    rationale: "Explicitly accepted by the operator on the strength of the static contract test alone, NOT observed live — the unpublish failure path requires the backend call itself to fail, which is not reachable from any UI state the operator can produce. This is a deliberate, recorded acceptance, not an automatic pass."
  - id: D6
    description: "Two operator-requested UI polish items: Status card date readouts now show time (formatDateTime, matching Status History), and the list-page block panel gained a keyboard-accessible Cancel affordance that dismisses the whole panel without publishing or losing row identity"
    verification:
      - kind: other
        ref: "cd app && npm run check (0 errors); api/tests/test_phase48_list_publish_override_ui_contract.py::test_block_panel_* (4 new tests)"
        status: pass
    human_judgment: true
    rationale: "Implemented per the operator's explicit written specification (button choice, whole-panel-vs-textarea dismissal, positive-exclusion preference) and proven by static contract + npm check, but not re-walked live in a fresh browser session before this SUMMARY was written — flagged so a future reader does not assume a live pass that did not happen."

duration: "~2h active work across 3 sessions (2026-08-19T19:10 to 2026-08-20T11:43 elapsed, including an overnight pause at the Task 4 checkpoint awaiting operator browser verification)"
completed: 2026-08-20
status: complete
---

# Phase 48 Plan 10: Trust Lifecycle — List-Page Publish Parity, Unpublish Visibility Fix, and Two Checkpoint-Found Defects Summary

**List-page publish block/override/tier-badge parity with the detail page, a genuine three-path unpublish visibility fix, and two real UI defects found live at the Task 4 checkpoint (a shared-`form` error-routing bug affecting both publish and unpublish) — fixed, locked with contract tests, and re-verified by the operator.**

## Performance

- **Duration:** ~2h active work across 3 sessions; elapsed wall-clock spans an overnight checkpoint pause (2026-08-19T19:10 → 2026-08-20T11:43)
- **Tasks:** 4 (all complete) + 3 follow-up fix rounds folded into Task 4 before acceptance
- **Files modified:** 18 across all rounds (12 commits)

## Accomplishments

- List page (`/admin/arguments`) now surfaces a blocked publish exactly as the detail page does — tier, server message, per-blocker breakdown, blank-reason distinction, and a visible non-overridable-gate error — addressed to the correct row via `form.argumentId`, with a passive per-row trust-tier badge and the Publish button never disabled by tier (operator-rejected alternative, structurally enforced).
- Unpublishing an argument now genuinely removes it from all three public read paths (`get_cases`, `get_argument_with_utterances`, `get_argument_speakers`), not just the two the originating todo named, proven by a regression test that failed before the fix.
- **Real defect found at the Task 4 operator checkpoint (step 9), not a plan gap:** the detail page's Status card never rendered `form?.error` at all, and the case-metadata card's alert slot could leak an unrelated action's error into it. Fixed for `publish` first (operator-verified live), then found and fixed for `unpublish` by inspection (verified by contract test only — the failure path isn't reachable from the UI).
- Two operator-requested polish items folded in before close: Status card date readouts now show time (matching Status History's existing format), and the list-page block panel gained a keyboard-accessible "Cancel" affordance that dismisses the whole panel without publishing or losing the row's identity.

## Task Commits

Each task was committed atomically; the checkpoint-driven fix rounds each got their own fix/test commit pair:

1. **Task 1: List-page publish block, override, and per-row tier badge** - `9f224111b` (feat)
2. **Task 2: Full blocker breakdown, blank-reason distinction, visible non-overridable errors (list page)** - `446eb0465` (feat)
3. **Task 3: Unpublish hides argument from all three public read paths** - `ca08b3fde` (test, RED+GREEN combined per prior session's commit)
4. **Task 4: Static source contract for the list-page publish override UI** - `b12d51eff` (test)
5. **Checkpoint fix round 1a — detail-page publish errors now render in the Status card** - `db70eb359` (fix)
6. **Checkpoint fix round 1b — lock publish-error rendering** - `6b6975243` (test)
7. **Checkpoint fix round 2a — detail-page unpublish errors also stop leaking into the case-metadata card** - `3c3fcc179` (fix)
8. **Checkpoint fix round 2b — extend contract to cover unpublish** - `939edea1f` (test)
9. **Polish item 1 — Status card dates now show time** - `fd26bdfc7` (fix)
10. **Polish item 2a — keyboard-accessible Cancel affordance on the list-page block panel** - `3622b053b` (feat)
11. **Polish item 2b — extend list-page contract test for the Cancel affordance** - `f57003610` (test)

**Plan metadata:** (this commit)

## Files Created/Modified

- `api/schemas/admin_arguments.py` - `ArgumentListItem.trust_tier` (admin-only field)
- `api/services/admin_arguments.py` - `list_arguments` selects and returns `trust_tier`
- `app/src/routes/admin/arguments/+page.server.ts` - `publish`/`unpublish` actions: per-row `argumentId` addressing, structured/plain-string branching, `override_reason` relay
- `app/src/routes/admin/arguments/+page.svelte` - tier badge, block panel with per-blocker breakdown, row-scoped visible error, Cancel affordance with `dismissedForm` Rune
- `api/services/cases.py`, `api/services/arguments.py`, `api/services/speakers.py` - additional `status == PUBLISHED` gate alongside the pre-existing `published_at` predicate (kept verbatim, not replaced)
- `api/routers/admin.py` - corrected `unpublish_argument` docstring (no longer claims `published_at` is cleared)
- `app/src/routes/admin/arguments/[id]/+page.server.ts` - `publish`/`unpublish` actions tagged with `source: 'publish'` / `source: 'unpublish'` on every `fail()` payload
- `app/src/routes/admin/arguments/[id]/+page.svelte` - case-metadata alert uses positive `!form.source` exclusion; Status card renders a widened publish/unpublish error block; `formatDateTime` for both date readouts
- `api/tests/test_phase48_unpublish_visibility.py` (new) - regression test for the three-path visibility fix
- `api/tests/test_phase48_list_publish_override_ui_contract.py` - static contract for the list page, extended twice (Cancel affordance)
- `api/tests/test_phase48_detail_publish_error_rendering_contract.py` (new) - static contract locking both the publish- and unpublish-error rendering fixes

## Decisions Made

See `key-decisions` in frontmatter. Summarized:
- `source`-tagged `fail()` payloads + positive `!form.source` ownership test for the default action, to route errors correctly on a page where multiple actions share one `form` prop.
- Widened (not duplicated) the Status-card error block to cover both `publish` and `unpublish` sources, placed outside the draft/unpublished-vs-published branch.
- Plain-text "Cancel" (not an icon-only "×") on the list page, matching the existing Danger Zone convention; dismisses the whole block panel, tracked via a reference-compared local Rune, never by mutating shared `form` state.
- Reused `formatDateTime` for the Status card's date readouts rather than introducing a third formatter.

## Deviations from Plan

### Auto-fixed Issues (Rule 1 — bugs found via the plan's own checkpoint)

**1. [Rule 1 - Bug] Detail-page Status card never rendered publish errors; case-metadata card could leak them**
- **Found during:** Task 4's operator checkpoint, step 9 (the plan's own optional bonus step — attempted, and it surfaced a real defect neither 48-08 nor this plan's earlier tasks had caught)
- **Issue:** `?/publish`'s server action (`[id]/+page.server.ts`, correct since 48-08) returned `fail(422, { error: detail })` for the non-overridable resolve gate and the already-published guard, but `+page.svelte` rendered `form?.error` in exactly one place — the unrelated case-metadata card's alert slot. Clicking Publish on a resolve-incomplete argument showed nothing at all where the operator was looking (the Status card).
- **Fix:** Tagged every `publish` action `fail()` payload with `source: 'publish'`; gated the case-metadata alert on `form.source !== 'publish'` (later widened, see #2); added a visible `role="alert"` message in the Status card, next to the Publish button, with no reason field (D-14: not overridable).
- **Files modified:** `app/src/routes/admin/arguments/[id]/+page.server.ts`, `app/src/routes/admin/arguments/[id]/+page.svelte`
- **Verification:** `api/tests/test_phase48_detail_publish_error_rendering_contract.py` (new module, confirmed to fail against the pre-fix markup before committing); operator re-verified live in the browser (this session).
- **Committed in:** `db70eb359` (fix), `6b6975243` (test)

**2. [Rule 1 - Bug] Detail-page unpublish errors had the identical defect**
- **Found during:** Inspection immediately after fixing #1, at the coordinator's direction — not independently discovered by the operator.
- **Issue:** `unpublish`'s two `fail()` payloads were untagged, so `form.source !== 'publish'` still let an unpublish failure render in the case-metadata card.
- **Fix:** Tagged both `unpublish` `fail()` payloads with `source: 'unpublish'`. Switched the case-metadata exclusion from the negative `!== 'publish'` to a positive `!form.source` test (robust to a future fourth action being added without anyone remembering to extend an exclusion list). Widened the Status-card error block to `form.source === 'publish' || form.source === 'unpublish'` and moved it outside the draft/unpublished-vs-published branch so it renders next to whichever control (Publish or Unpublish) is currently visible.
- **Files modified:** `app/src/routes/admin/arguments/[id]/+page.server.ts`, `app/src/routes/admin/arguments/[id]/+page.svelte`
- **Verification:** `api/tests/test_phase48_detail_publish_error_rendering_contract.py` extended (confirmed new/changed assertions fail against the pre-fix markup before committing). **NOT independently live-verified** — the unpublish failure path requires the backend call itself to fail, which the operator cannot trigger from any reachable UI state. The operator explicitly accepted this fix on the strength of the contract test alone; this is recorded as such, not as "verified."
- **Committed in:** `3c3fcc179` (fix), `939edea1f` (test)

### Operator-requested polish (not defects — folded in before close)

**3. Status card date readouts now show time**
- The bare-date "Last published"/"Published" and "Created" readouts read as inconsistent next to the Status History list on the same card, which already shows times. Swapped both to the existing `formatDateTime` helper; no new formatter introduced; labels unchanged (the "Created" mislabel on `resolved_at` is a separate, already-tracked todo, deliberately out of scope here).
- **Committed in:** `fd26bdfc7`

**4. List-page block panel gained a Cancel affordance**
- No prior way to dismiss the override-reason panel short of reloading. Added a plain-text "Cancel" button (matching the Danger Zone's existing two-step-confirm convention), dismissing the whole panel via a local `dismissedForm` Rune compared by reference against the current `form` — re-submitting Publish on the same row naturally un-dismisses it, and only one row's panel can ever be visible at a time so dismissal cannot leak across rows.
- **Committed in:** `3622b053b` (feat), `f57003610` (test)

---

**Total deviations:** 2 auto-fixed bugs (Rule 1, both found via the plan's own checkpoint mechanism — one live, one by inspection) + 2 operator-requested polish items (not defects).
**Impact on plan:** Both bugs were genuine regressions the plan's checkpoint was designed to catch — this is exactly the case for keeping such checkpoints and their WINDOWS.md entries open rather than waving them through. No scope creep beyond what the operator explicitly directed.

## Issues Encountered

- An inline code comment temporarily pushed a `following = body[idx : idx + N]` fixed-window assertion in a **pre-existing sibling contract test** (`test_phase48_publish_override_ui_contract.py`) out of range. Shortened the comment (kept the essential cross-reference) rather than widening a pre-existing test's window, to avoid touching a file outside this round's stated scope; confirmed the sibling test still passes unmodified.
- The Edit tool wrote `app/src/routes/admin/arguments/+page.svelte`'s working-tree bytes as CRLF for one edit; investigated and confirmed the committed git blob is LF (the repo's `.gitattributes` `text=auto eol=lf` normalizes at `git add` time), so no actual line-ending drift landed in history — `git status`/`git diff` both show the file clean against HEAD.

## WINDOWS.md Ledger

**Entry #8 marked `fixed`** (`gsd-tools windows fixed 8`): "48-08 checkpoint step 8 not executed... the non-overridable resolved_at gate (D-14) rendering with NO override field offered is unverified in a browser." This entry stayed open across two checkpoints (48-08's original pause and this plan's Task 4) precisely because the deferred verification was never rubber-stamped — and when it was finally exercised live in this plan's Task 4 checkpoint (an operator manually nulled `resolved_at` on a DRAFT/unpublished fixture row and attempted Publish through the detail page), **it surfaced the real defect documented above**, not a false alarm. The gate rendering with no override field is now confirmed live in a browser on both the list and detail pages. This is the textbook case for why an unrun-verify window is left open rather than waved through: the deferred check was the thing that caught the bug.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 48's trust-lifecycle work (TRUST-04, TRUST-05) is now complete, including the gap-closure and checkpoint-found-defect fixes this plan absorbed.
- 48-09 (live fixture reseed, zero-drift proof, full-suite gate, requirement traceability, operator sign-off) remains the phase's final plan.
- Argument 1780 was deliberately left in its operator-set state (`status = unpublished`, `resolved_at = NULL`) throughout this plan's execution per explicit instruction — the operator will restore it themselves; no `reset_to_fixture` was run.
- The `source`-tag pattern and the reference-compared dismissal-Rune pattern established here are reusable for any future admin page with more than one form action sharing a `form` prop (candidate for Phase 51's design-system work).

---
*Phase: 48-trust-lifecycle*
*Completed: 2026-08-20*
