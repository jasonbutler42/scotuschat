---
phase: 49-review-model
plan: 08
subsystem: ui
tags: [svelte, admin, css-grid, overflow, responsive, source-contract-tests]

requires:
  - phase: 49-review-model plan 07
    provides: "operator-copy rename ('constituent' -> 'participant') and argumentEditLabel() on app/src/routes/admin/review/+page.svelte, which this plan's line-number-independent re-location had to account for"
provides:
  - "Three overflow-x: auto containers on /admin/review (both queue tables + the status segment group) so wide content scrolls locally instead of pushing the page body sideways at 375px"
  - "An auto-fit StatCard grid track floor on /admin that reflows to two columns at 375px while still filling exactly five tracks at the 812px desktop content width, byte-identical to the prior fixed-column rendering"
  - "An executable _tracks_that_fit arithmetic gate proving UAT sub-items 5 and 7 hold simultaneously, so a future floor/gap change that breaks either fails a test instead of surfacing in a browser"
affects: [49-09, 49-10, phase-50]

actuals:
  tokens: 5736
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Container-scroll-not-body-scroll: an overflow-x: auto wrapper around genuinely-wide content, never truncation, when body-level horizontal scroll must be prevented under an inline-style-only constraint"
    - "min-width: 0 on a flex item that must be allowed to shrink below its content's min-content size before overflow-x: auto can engage"
    - "repeat(auto-fit, minmax(<floor>px, 1fr)) as a media-query-free responsive grid track definition, with the floor chosen so exactly N tracks fill the widest expected container"

key-files:
  created: []
  modified:
    - app/src/routes/admin/review/+page.svelte
    - app/src/routes/admin/+page.svelte
    - api/tests/test_phase49_review_ui_contract.py
    - .planning/phases/49-review-model/49-UAT.md
    - .planning/phases/49-review-model/49-VERIFICATION.md

key-decisions:
  - "Fixed all THREE horizontal-overflow causes, not the two named in the original UAT diagnosis — the status segment group's ~480px min-content width (five 44px-min-height buttons, no flex-wrap) was found during this plan's planning stage and overflows independently of the two queue tables."
  - "Resolved the UAT sub-item 5 vs. sub-item 7 conflict by dissolving it rather than picking a winner: a 120px auto-fit track floor fills exactly five tracks at the 812px desktop content width (136.8px per card, byte-identical to the old fixed repeat(5, 1fr)) and reflows to two tracks at the 327px 375px-viewport inner width — encoded as an executable _tracks_that_fit arithmetic test, not a comment."
  - "One test in each task's RED-phase trio (test_no_truncation_or_media_query_introduced_on_the_review_page in Task 1; test_dashboard_grid_uses_no_media_query_and_no_class_attribute in Task 2) is a negative-space regression guard that trivially passes both before and after the edit, because the patterns it forbids were never introduced. Documented explicitly rather than reported as red-then-green, matching the plan's own precedent for test_dashboard_has_five_column_grid_and_five_statcards (a rewrite, not a new gate)."
  - "G-49-5a marked status: resolved (structural closure only, matching the phase's existing G-49-9a/G-49-4a/G-49-4b convention of marking resolved on source-contract evidence with the visual re-check tracked separately) — the browser pass could not be run in this sandbox (denied .env access for ADMIN_USERNAME/ADMIN_PASSWORD/SESSION_SECRET, unchanged since 49-01/49-03/49-05)."

patterns-established:
  - "Negative-space RED-phase tests (assertions that a forbidden pattern was NOT introduced) cannot be observed RED before the edit that would introduce the risk — document this explicitly per-test rather than force a false red-then-green narrative."

requirements-completed: [REVIEW-03]

coverage:
  - id: D1
    description: "Both /admin/review queue tables and the status segment group are each wrapped in their own overflow-x: auto container, with white-space: nowrap cells and the no-truncation rule (49-UI-SPEC E1/E2) left fully intact"
    requirement: REVIEW-03
    verification:
      - kind: unit
        ref: "api/tests/test_phase49_review_ui_contract.py#test_both_queue_tables_are_wrapped_in_an_overflow_container"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_review_ui_contract.py#test_status_segment_group_can_shrink_and_scroll"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_review_ui_contract.py#test_no_truncation_or_media_query_introduced_on_the_review_page"
        status: pass
    human_judgment: true
    rationale: "Source-contract tests only prove the wrapper markup exists in the .svelte source text, not that a browser actually contains the overflow at 375px and never truncates. This sandbox could not authenticate to /admin/** (denied .env access) to run the browser pass — see Task 3's human-check items 1-3, recorded NOT OBSERVED."
  - id: D2
    description: "Dashboard StatCard grid reflows to two tracks at 375px and still fills exactly five tracks at the 812px desktop content width, at the same 136.8px per-card width as before this plan"
    requirement: REVIEW-03
    verification:
      - kind: unit
        ref: "api/tests/test_phase49_review_ui_contract.py#test_dashboard_grid_track_floor_fits_five_cards_at_desktop_and_reflows_at_375px"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_review_ui_contract.py#test_dashboard_grid_uses_no_media_query_and_no_class_attribute"
        status: pass
    human_judgment: true
    rationale: "The arithmetic gate proves the CSS Grid auto-fit track count formula holds at the two named widths, not that a real browser renders it that way. Same credential-access blocker as D1 — see Task 3's human-check items 4-5, recorded NOT OBSERVED."
  - id: D3
    description: "G-49-5a's three-cause resolution and the G-49-9a re-check attempt recorded in 49-UAT.md / 49-VERIFICATION.md, with structural and visual closure kept as separate claims"
    verification: []
    human_judgment: true
    rationale: "This is a documentation-only deliverable whose entire purpose is to route the remaining visual confirmation to a human — it cannot self-verify."

duration: ~55min
completed: 2026-08-24
status: complete
---

# Phase 49 Plan 08: Narrow-viewport horizontal-scroll containment (G-49-5a) Summary

**Contained three independent horizontal-overflow causes on `/admin/review` and `/admin` with `overflow-x: auto` wrappers and an auto-fit grid track floor — no truncation, no media query, and the desktop five-StatCard row provably unchanged.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3 completed
- **Files modified:** 5 (2 `.svelte`, 1 test module, 2 planning docs)

## Accomplishments

- Wrapped both `/admin/review` queue tables and the five-segment status filter control in their own `overflow-x: auto` containers, so wide content scrolls locally instead of the page body scrolling sideways at 375px. `white-space: nowrap` cells, columns, and the no-truncation rule (49-UI-SPEC E1/E2) are untouched.
- Found and fixed a **third** overflow cause not in the original UAT diagnosis: the status segment group (`All`/`Candidate`/`Draft`/`Published`/`Unpublished`) has a ~480px min-content width that overflowed the page's 327px inner width at 375px independently of the two tables. Fixed with `min-width: 0` on an outer wrapper (load-bearing against the flex `min-width: auto` default) plus `width: max-content` on an inner group, preserving the segmented control's one-sided border-radius/border-left shape.
- Replaced the dashboard's fixed `grid-template-columns: repeat(5, 1fr)` with `repeat(auto-fit, minmax(120px, 1fr))`. The 120px floor is arithmetically chosen so five tracks still fill the 812px desktop content width at the identical 136.8px per-card width as before (UAT sub-item 5 preserved, not traded for sub-item 7), while reflowing to two tracks at the 327px 375px-viewport inner width.
- Added an executable `_tracks_that_fit` arithmetic gate (`api/tests/test_phase49_review_ui_contract.py`) so a future floor or gap change that breaks either UAT sub-item 5 or 7 fails a test instead of surfacing in a browser weeks later.
- Recorded G-49-5a as structurally resolved in `49-UAT.md` (all three causes named) while explicitly keeping the visual browser confirmation as a separate, still-outstanding claim — consistent with non-negotiable #4.

## RED-phase evidence (both tasks)

**Task 1** — three assertions authored before the source edit. Ran `./.venv/bin/python -m pytest api/tests/test_phase49_review_ui_contract.py -q` and observed:

- `test_both_queue_tables_are_wrapped_in_an_overflow_container` — **FAILED**, quoted message:
  ```
  assert REVIEW_SOURCE.count("overflow-x: auto") == 3
  E       assert 0 == 3
  ```
- `test_status_segment_group_can_shrink_and_scroll` — **FAILED**, quoted message:
  ```
  assert "min-width: 0" in REVIEW_SOURCE
  E       assert 'min-width: 0' in '<script lang="ts">\n...'
  ```
  (i.e. the substring was absent from the full source, as expected before the wrapper existed)
- `test_no_truncation_or_media_query_introduced_on_the_review_page` — **PASSED at RED time**, and could not have been otherwise: it is a negative-space assertion (`"text-overflow" not in`, `"overflow: hidden" not in`, `"@media" not in`, `"class=" not in`), all of which were already true before any edit — confirmed independently by `grep -n 'class="\|overflow: hidden\|@media\|text-overflow'` returning nothing. This test is a standing regression guard re-asserted at the point of change, not a new gate that can be observed transitioning from red to green. Documented here rather than misreported as red-then-green.

After the edit: `19 passed` (module total, up from 17 pre-edit).

**Task 2** — helper, constants, and two new tests authored before the grid edit. Observed:

- `test_dashboard_grid_track_floor_fits_five_cards_at_desktop_and_reflows_at_375px` — **FAILED**, quoted message:
  ```
  AssertionError: expected a `repeat(auto-fit, minmax(<n>px, 1fr))` grid-template-columns pattern in the dashboard source — none found
  assert None
  ```
- `test_dashboard_has_five_column_grid_and_five_statcards` (rewritten) — also failed at this point, but **not as a red gate**: the rewrite's new assertion (`"grid-template-columns: repeat(5, 1fr)" not in dashboard_source`) fails only because the OLD literal this plan's own edit deletes was still present pre-edit. This is exactly the plan's own documented exception ("this task's edit deletes the literal it currently keys on, so it is a rewrite, not a new gate") — reported here as such, not as red-then-green.
- `test_dashboard_grid_uses_no_media_query_and_no_class_attribute` — **PASSED at RED time** (same negative-space reasoning as Task 1's third test: no `@media` or `class=` existed in the dashboard source before or after this plan's edit).

After the edit: `21 passed` (module total).

## Recomputed grid arithmetic (Task 2, non-negotiable #3)

Re-verified against source rather than trusting the plan's numbers:

- `app/src/routes/admin/+page.svelte` content region: `max-width: 860px; margin: 0 auto; padding: 48px 24px;` — confirmed unchanged, matching the plan's assumption exactly.
- Desktop inner width: `860 - 2×24 = 812px`. Five tracks at a 120px floor and 32px gap need `5×120 + 4×32 = 728px` — fits, with `44px` to spare (as `auto-fit` overflow headroom, not extra per-card width).
- With exactly five `<StatCard>` children, all five tracks fill and stretch to `1fr`: `(812 - 4×32) / 5 = 136.8px` per card — **identical** to the prior fixed `repeat(5, 1fr)` rendering. No desktop change.
- 375px viewport inner width: `375 - 2×24 = 327px`. `⌊(327 + 32) / (120 + 32)⌋ = ⌊359/152⌋ = 2` tracks, each `(327 - 32) / 2 = 147.5px` — wider than the 120px floor, no overflow.
- No recomputation was needed — the plan's numbers matched source exactly.

## Task Commits

1. **Task 1: /admin/review — three overflow containers, no truncation, no media query** - `58147e602` (fix)
2. **Task 2: Dashboard StatCard grid — auto-fit tracks plus an executable track-fit gate** - `faa299a3c` (fix)
3. **Task 3: G-49-5a/G-49-9a UAT record update (no application code)** - `fae386261` (docs)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `app/src/routes/admin/review/+page.svelte` — three `overflow-x: auto` containment wrappers (Arguments table, People table, status segment group), plus `min-width: 0`/`width: max-content` on the status group
- `app/src/routes/admin/+page.svelte` — `grid-template-columns` changed from `repeat(5, 1fr)` to `repeat(auto-fit, minmax(120px, 1fr))`, with the arithmetic recorded in a source comment
- `api/tests/test_phase49_review_ui_contract.py` — three new Task 1 assertions, a rewritten five-column test plus two new Task 2 assertions (`_tracks_that_fit` helper, arithmetic gate, no-media-query guard)
- `.planning/phases/49-review-model/49-UAT.md` — G-49-5a marked resolved (three causes), test 5's sub-item 5/6/7 notes updated, G-49-9a re-check attempt recorded
- `.planning/phases/49-review-model/49-VERIFICATION.md` — human_verification item 2 annotated with the structural-vs-visual distinction; item 1 (WR-01) untouched

## Decisions Made

See `key-decisions` in frontmatter. The most consequential: the UAT-reported "sub-item 5 vs. sub-item 7" conflict is dissolved (not adjudicated) by choosing a 120px auto-fit floor, which the plan's own planner_decisions arithmetic predicted and this execution confirmed against live source without needing recomputation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Comment wording accidentally inflated grep-counted literals**
- **Found during:** Task 1, first verification pass
- **Issue:** Explanatory comments placed on the new overflow wrappers used the literal phrases `overflow-x: auto` and `white-space: nowrap` in prose, which inflated `grep -c` counts used by both the plan's own `<verify>` commands and the new tests' `REVIEW_SOURCE.count(...)` assertions (`overflow-x: auto` briefly counted 5 instead of 3; `white-space: nowrap` briefly counted 13 instead of 12).
- **Fix:** Reworded the comments to describe the same behavior without repeating the literal CSS declaration strings (e.g., "horizontal-scroll declaration below" instead of "overflow-x: auto below", "twelve no-wrap cells" instead of "twelve white-space: nowrap cells").
- **Files modified:** `app/src/routes/admin/review/+page.svelte`
- **Verification:** `grep -c 'overflow-x: auto'` → 3, `grep -c 'white-space: nowrap'` → 12 (both match the pre-edit baseline / plan's exact-count requirement)
- **Committed in:** `58147e602` (part of Task 1's commit — caught before commit, no separate fix commit needed)

---

**Total deviations:** 1 auto-fixed (Rule 1). **Impact on plan:** Cosmetic-only; no scope creep, no behavior change. Caught during the plan's own verification step before the task commit.

## Issues Encountered

**Verify-command mismatch found in Task 3, not fixed (out of this plan's file-ownership scope):** the plan's Task 3 `<verify>` command `grep -c 'margin: 6px' 'app/src/routes/cases/[slug]/arguments/[id]/+page.svelte'` returns `0`, not the expected non-zero count. The actual source at both G-49-9a fix sites in that file uses `margin:6px` (no space) inside a combined inline-style string, not `margin: 6px` (with space) — confirmed present via `grep -c 'margin:6px'` → `2`. `app/src/lib/components/ChatBubble.svelte` does use the spaced form (`margin: 6px` → `1`). This is a verify-command/actual-formatting mismatch, not a missing fix: all three G-49-9a sites (bench avatar, advocate avatar, ChatBubble) still carry the margin fix from commit `690d51e20`. No code was changed to "fix" this, since `arguments/[id]/+page.svelte` is on 49-09's exclusive file list (per non-negotiable #6) and the fix itself is present and correct — only the plan's literal grep pattern didn't anticipate that file's no-space style.

## Structural closure vs. visual closure (non-negotiable #4)

**Closed by green automated assertions (structural only):**
- Both `/admin/review` queue tables and the status segment group are wrapped in `overflow-x: auto` containers (source-contract tests green).
- The dashboard grid's `auto-fit` track floor provably yields 5 filled tracks at 812px and reflows to ≤2 tracks at 327px, per the `_tracks_that_fit` arithmetic gate.
- No truncation (`text-overflow`, `overflow: hidden`), no `@media`, no `class=` was introduced on either page.
- `npm --prefix app run check` reports 0 errors (same 37 pre-existing warnings as before this plan, none new, none touching the edited pages).

**Still awaiting an operator's eyes (NOT observed — this sandbox denies `.env` read access for `ADMIN_USERNAME`/`ADMIN_PASSWORD`/`SESSION_SECRET`, unchanged since 49-01/49-03/49-05):**
- Task 3 human-check items 1-3: at 375px, confirm neither queue table's page nor the status filter row scrolls the page body, and that expanded-row details/discrepancy values/action buttons remain fully reachable and untruncated.
- Task 3 human-check item 4: at 375px, confirm the dashboard page itself doesn't scroll sideways and the five StatCards visibly reflow into two columns.
- Task 3 human-check item 5: at normal desktop width, confirm all five StatCards are still in ONE row with even gaps, unchanged from before this plan (the arithmetic says they will be; no eyes have confirmed it).
- Task 3 human-check item 6 (UAT sub-item 5.6): StatCard singular ("1 item needs review") and zero-state ("No items need review", non-link) copy at queue totals of exactly 1 and exactly 0 — still NOT OBSERVED, same reason as the original UAT session (queue had 2+) plus the new credential blocker.
- Task 3 human-check item 7 (G-49-9a re-check): visual alignment of the unresolved-speaker avatar and name text on the Complexity fixture's argument-edit page and its published chat page. The three fix sites were confirmed present by grep (see Issues Encountered above) but not re-observed visually.

None of the above was marked observed, pass, or resolved-by-eye anywhere in `49-UAT.md` or `49-VERIFICATION.md` — every one is recorded as outstanding with the credential-access reason, per non-negotiable #4.

## User Setup Required

None — no external service configuration required. The unresolved browser-verification items above require an operator with access to `/admin/**` credentials (`ADMIN_USERNAME`/`ADMIN_PASSWORD`/`SESSION_SECRET`), not a new service.

## Next Phase Readiness

- G-49-5a is structurally closed; only the visual confirmation (Task 3's 7 human-check items) remains, and it is explicitly not conflated with the structural closure above.
- `app/src/routes/admin/review/+page.svelte` and `api/tests/test_phase49_review_ui_contract.py` were the two files this plan shared with `49-07`'s wave-1 work; both were re-located by content (not stale line numbers) before editing, and no `49-07` content was touched or reverted.
- Files explicitly NOT touched, per non-negotiable #6: `app/src/lib/components/CreatePersonPopover.svelte`, `app/src/routes/admin/arguments/[id]/+page.svelte`, `api/services/admin_arguments.py`, `api/tests/test_phase49_participant_side_contract.py`, `api/tests/test_admin_arguments_service.py` — confirmed by `git status`/`git diff` before commit that none of these appear in this plan's changeset.
- Full `api/tests` suite: **1094 passed**, 0 failed, 0 skipped, 12 warnings (pre-existing Alembic deprecation warnings, unrelated to this plan) — up from the 1089-passed baseline stated in this plan's prompt, an increase of 5 tests (Task 1 net +3, Task 2 net +2 — the five-column test was rewritten in place, not added).
- `npm --prefix app run check`: 812 files, 0 errors, 37 warnings (unchanged from before this plan; none in the two edited pages).

---
*Phase: 49-review-model*
*Completed: 2026-08-24*

## Self-Check: PASSED

All 6 claimed files exist on disk (verified with `[ -f ... ]`) and all 3 claimed commit hashes (`58147e602`, `faa299a3c`, `fae386261`) are found in `git log --oneline --all`.
