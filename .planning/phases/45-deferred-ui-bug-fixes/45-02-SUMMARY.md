---
phase: 45-deferred-ui-bug-fixes
plan: 02
subsystem: ui
tags: [svelte, bits-ui, popover, css, box-model, pytest]

# Dependency graph
requires:
  - phase: 39
    provides: the widened SpeakerPopover.svelte (bio clamp, tenure list, dividers) whose field set this plan's contract test locks
provides:
  - "Popover.Content in +page.svelte owns the full visible box model (surface, border, radius, width bounds, max-height, overflow, z-index) — Task 1, committed"
  - "api/tests/test_phase45_popover_boxmodel_contract.py — 21-assertion static source contract covering single-box ownership, the nine Phase 39 regression-checklist fields, the overflow threshold's two min() branches, the border-box precision contract, and the phase prohibitions — Task 2, committed"
affects: [phase-45-bug-02-scrollbar-plan]

# Actuals (#2632)
actuals:
  tokens: 3411
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single inline style= attribute as the sole owner of an element's full visible box model (surface + border + radius + width bounds) alongside its pre-existing scroll properties (max-height/overflow-y) — no wrapper element introduced, matching bits-ui's Popover.Content style-merge behavior already proven by the pre-existing z-index/max-height/overflow-y declarations"
    - "Region-scoped absence assertions (assert against an extracted CSS-rule body or extracted tag text, never a whole file) so a legitimate occurrence elsewhere (e.g. border-radius:50% on an avatar circle) cannot make an absence gate unsatisfiable"

key-files:
  created:
    - api/tests/test_phase45_popover_boxmodel_contract.py
  modified:
    - "app/src/routes/cases/[slug]/arguments/[id]/+page.svelte"
    - app/src/lib/components/SpeakerPopover.svelte

key-decisions:
  - "D-03 implemented as specified: background-color #1e293b, border 1px solid #334155, border-radius 8px, min-width 300px, and max-width 400px moved from .popover-card onto Popover.Content's existing inline style= string, joining the pre-existing z-index/max-height/overflow-y declarations there; no wrapper element introduced."
  - "Padding stayed on .popover-card (not load-bearing for the fix, smaller diff) per 45-PATTERNS.md's recommendation — .popover-card now declares only padding: 24px and display: block."
  - "No custom scrollbar theming added — the structural relocation alone is the approved fix per 45-CONTEXT.md; the escape hatch is explicitly not exercised without operator direction, which is exactly what Task 3's checkpoint exists to gather."

patterns-established:
  - "Pattern: when relocating CSS box-model ownership between two elements in a component with no <style> block (inline style= convention), region-scope every absence assertion in the accompanying source-contract test to the specific extracted rule/tag text, not the whole file, to avoid false failures against legitimate same-named properties elsewhere (avatar border-radius, divider border-top, etc.)."

requirements-completed: []  # BUG-02 is NOT complete — Task 3 (checkpoint:human-verify, gate=blocking) is still pending operator action; do not mark complete in REQUIREMENTS.md until that checkpoint is approved.

coverage:
  - id: D1
    description: "Popover.Content owns the surface color, border, radius, width bounds, max-height, and overflow together (single-box ownership) — the scrolling element and the visually-bounded element are the same box (Task 1)"
    requirement: "BUG-02"
    verification:
      - kind: unit
        ref: "api/tests/test_phase45_popover_boxmodel_contract.py::test_popover_content_owns_full_box_model"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase45_popover_boxmodel_contract.py::test_popover_card_reduced_to_padding_and_display_only"
        status: pass
    human_judgment: false
  - id: D2
    description: "The nine UI-SPEC Regression Checklist fields (avatar/initials, name+role pill, birth/death halves, advocate descriptor, bio clamp+toggle, tenure rows, four hairline dividers, padding, width bounds) still render after the relocation, and the full Phase 39 popover contract (17 assertions) stays green (Task 2)"
    requirement: "BUG-02"
    verification:
      - kind: unit
        ref: "api/tests/test_phase45_popover_boxmodel_contract.py (field-set group, 9 tests)"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase39_popover_ui_contract.py -q (17 passed, unchanged from pre-change baseline)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The overflow threshold's two min() branches (560px and 80vh), the border-box precision contract, and the phase prohibitions (no scrollbar theming, no box-sizing override, apolitical guard, relocated colors are a token-set subset) are each asserted by a named test (Task 2)"
    requirement: "BUG-02"
    verification:
      - kind: unit
        ref: "api/tests/test_phase45_popover_boxmodel_contract.py (boundary/precision/prohibitions groups, 8 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Operator-confirmed live verification: scrollbar renders flush inside the rounded card at both threshold branches, every field renders unclipped, a short-bio popover shows no scrollbar, scrolled content does not collide with the rounded corners, interaction (Escape/outside-click/focus-trap/wheel/drag) stays intact, and the advocate popover's card boundary matches the Justice popover's (Task 3)"
    verification: []
    human_judgment: true
    rationale: "Requires a human to open a live browser popover, resize the viewport across both min() branches, visually confirm scrollbar placement relative to the rounded border, and confirm keyboard/pointer interaction — none of this is something the executor agent can fabricate or substitute with an automated check."

# Metrics
duration: ~25min
completed: 2026-08-12
status: in-progress
---

# Phase 45 Plan 02: BUG-02 popover box-model relocation Summary

**Popover.Content now owns the full visible box model (surface, border, radius, width bounds) alongside its pre-existing scroll properties, so the scrolling element and the visually-bounded card are the same box; a new 21-assertion static source contract locks single-box ownership, the full Phase 39 field set, and the overflow threshold's precision — Task 3's live operator verification is still pending.**

## Performance

- **Tasks:** 2 of 3 completed (Task 1 and Task 2 committed; Task 3 is a `checkpoint:human-verify` with `gate="blocking"`, awaiting operator action)
- **Files modified:** 3 (`app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`, `app/src/lib/components/SpeakerPopover.svelte`, `api/tests/test_phase45_popover_boxmodel_contract.py`)

## Accomplishments

- **Task 1:** Extended `Popover.Content`'s existing inline `style=` attribute in `+page.svelte` to add `background-color: #1e293b`, `border: 1px solid #334155`, `border-radius: 8px`, `min-width: 300px`, and `max-width: 400px` alongside the pre-existing `z-index: 50`, `max-height: min(560px, 80vh)`, and `overflow-y: auto`. Reduced `.popover-card` in `SpeakerPopover.svelte` to `padding: 24px` and `display: block` only. Created `api/tests/test_phase45_popover_boxmodel_contract.py` with `ROOT`/`POPOVER_PATH`/`PAGE_PATH`/`APP_CSS_PATH` constants, `_source()`, `_css_rule_body()`, and `_popover_content_tag()` helpers, and 4 tests locking single-box ownership, the region-scoped absence of the five relocated declarations from `.popover-card`, the absence of scrollbar theming, and the absence of a `box-sizing` override.
- **Task 2:** Extended the contract module with 17 more tests: a field-set group (9 tests, one per UI-SPEC Regression Checklist bullet — avatar/initials, name+role pill, birth/death independent halves, advocate descriptor, bio clamp+both toggle labels, tenure office/second row, exactly 4 hairline dividers, card padding, width bounds on the tag), a boundary group (3 tests — the two-branch `min()` form with both `560px` and `80vh` operands, the scrolling (not clipping) overflow value, and co-location of scroll+boundary declarations in one tag), a precision group (2 tests — the global border-box rule unchanged, no `box-sizing` override on either the tag or the card rule body), and a prohibitions group (3 tests — apolitical guard, no scrollbar-hiding declaration, relocated colors are a subset of the documented token set). Module now has 21 tests total.

## Task Commits

Each task was committed atomically:

1. **Task 1: Relocate the card box model onto the scrolling element and lock it with a contract test** - `a064ab13` (feat)
2. **Task 2: Lock the Phase 39 field set and the overflow boundary/precision contract** - `bac9173e` (test)

**Task 3 (checkpoint:human-verify, gate="blocking") has NOT been executed or approved.** It requires an operator to drive a live browser session across two viewport heights and report what the scrollbar looks like relative to the card border. See the CHECKPOINT REACHED message returned alongside this plan's execution for the exact verification steps.

## Files Created/Modified

- `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` - `Popover.Content`'s inline `style=` now owns the full box model (surface, border, radius, width bounds, max-height, overflow, z-index)
- `app/src/lib/components/SpeakerPopover.svelte` - `.popover-card` reduced to `padding: 24px; display: block;` only
- `api/tests/test_phase45_popover_boxmodel_contract.py` - new 21-test static source-contract module (no frontend test framework in this repo, per the same rationale `test_phase39_popover_ui_contract.py` states)

## Decisions Made

- D-03 implemented exactly as specified in 45-CONTEXT.md and 45-UI-SPEC.md's Box-Model Contract table — no deviation from the documented owner-before/owner-after mapping.
- Padding left on `.popover-card` (the smaller diff, matching 45-PATTERNS.md's recommendation) rather than moved up to `Popover.Content`.
- No custom scrollbar theming added — the structural fix alone is the approved approach; Task 3's checkpoint step 5 explicitly asks the operator whether the escape hatch (moving padding onto the boundary-owning element) is needed, rather than pre-emptively applying it.

## Deviations from Plan

None — plan executed exactly as written for Tasks 1 and 2.

## Issues Encountered

- `./.venv/Scripts/python.exe -m pytest api/tests -q` (Task 2's full-suite acceptance criterion) reproduces **12 failed, 574 passed, 128 skipped, 4 errors** on this checkout, all in files this plan never touches: `test_admin_dev_routes.py` (7 failures — DB-state/unique-constraint pollution when run as part of the full suite; all pass in isolation), `test_speakers_service.py` (5 failures — same full-suite-only pollution pattern; 19 passed / 5 skipped in isolation), and `test_phase38_people_ui_contract.py` (4 errors — a Node.js subprocess dependency for `personnames.ts` fixture matching, unrelated to Svelte/CSS). This exact failure/error signature (same file names, same counts) was already identified and documented as pre-existing/environmental in `45-01-SUMMARY.md`'s "Verification Results" section before this plan's Task 1 commit landed — confirming it is not caused by this plan's changes. Per the Scope Boundary rule, these are out of scope (pre-existing, unrelated files) and were not touched. This plan's own required verification — `api/tests/test_phase45_popover_boxmodel_contract.py` (21 passed) and `api/tests/test_phase39_popover_ui_contract.py` (17 passed, unchanged baseline) — is fully green.

## Next Phase Readiness

- Tasks 1 and 2 are complete, committed, and independently verified via targeted pytest runs and the plan's literal acceptance-criteria greps.
- Task 3 (checkpoint:human-verify, `gate="blocking"`) is outstanding — a human operator must open a published argument's speaker popover, confirm the scrollbar renders flush inside the rounded card at both `min()` threshold branches, confirm every Phase 39 field still renders, confirm short-bio and advocate-popover behavior, and confirm interaction (Escape/outside-click/focus-trap/wheel/drag) before this plan is fully complete and BUG-02 can be checked off in REQUIREMENTS.md.

---
*Phase: 45-deferred-ui-bug-fixes*
*Completed: 2026-08-12 (Tasks 1-2; Task 3 pending)*
