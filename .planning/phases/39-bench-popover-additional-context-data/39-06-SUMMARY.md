---
phase: 39-bench-popover-additional-context-data
plan: 06
subsystem: ui
tags: [svelte, fastapi, alembic, operator-checkpoint]

requires:
  - phase: 39-bench-popover-additional-context-data
    provides: reason_left/death_date/bio_text plumbing (39-01), CSV backfill (39-02), admin editor inputs (39-03), widened speaker contract (39-04), rebuilt popover UI (39-05)
provides:
  - Operator-verified state of the live stack after Phase 39's five code plans
affects: [39-gap-closure]

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified: []

key-decisions:
  - "Checkpoint NOT approved — operator found real defects; phase does not complete from this plan"

patterns-established: []

requirements-completed: []

coverage:
  - id: D1
    description: "Migrations 0023/0024 applied to the real dev database"
    requirement: "PUB-04"
    verification:
      - kind: manual_procedural
        ref: "operator checkpoint response"
        status: unknown
    human_judgment: true
    rationale: "Operator's response did not explicitly report the alembic current/upgrade output; not confirmed either way."
  - id: D2
    description: "import-justices backfill + idempotency on the real dev database"
    requirement: "PUB-04"
    verification:
      - kind: manual_procedural
        ref: "operator checkpoint response"
        status: pass
    human_judgment: true
    rationale: "Operator confirmed second consecutive run created 0 tenures (idempotency holds). First run created 1 tenure, which is expected pre-existing importer behavior for a not-yet-present row, not a regression."
  - id: D3
    description: "Death Date and Reason Left round-trip through the admin editor; multi-tenure add works"
    requirement: "PUB-04"
    verification:
      - kind: manual_procedural
        ref: "operator checkpoint response"
        status: pass
    human_judgment: true
    rationale: "Operator explicitly confirmed: 'death date saves fine', 'reason for leaving also saves and displays correctly', 'I can add more tenures and they show up as expected.'"
  - id: D4
    description: "Popover renders birth/death line and per-tenure appointing-president/party/reason lines with neutral, party-independent styling"
    requirement: "PUB-04"
    verification:
      - kind: manual_procedural
        ref: "operator checkpoint response"
        status: fail
    human_judgment: true
    rationale: "Operator reported the separator dot between birth/death dates and between president/party is rendered too small to be effective, and that overall popover styling does not match the Figma mockups (popover - Bench.png / popover-Advocate.png) — confirmed by direct comparison against the operator-supplied screenshot (bench popover.png). Step 6 (identical treatment across party values) — the single explicitly blocking acceptance criterion in this plan — was not addressed either way in the operator's response and needs explicit confirmation before this item can be closed."
  - id: D5
    description: "Bio text saves and round-trips through the Bio & Photo card"
    requirement: "PUB-04"
    verification:
      - kind: manual_procedural
        ref: "operator checkpoint response"
        status: fail
    human_judgment: true
    rationale: "Operator reported adding a bio to Felix Frankfurter did not persist — the input visually retained the typed text until a page refresh, then reverted, meaning the save silently failed while appearing to succeed. Root cause not yet investigated; may be a pre-existing bug or a regression from 39-03's admin editor changes."

duration: ~25min (checkpoint prep + operator live-stack session)
completed: 2026-07-28
status: gaps_found
---

# Phase 39: Bench popover additional context data — Plan 06 Summary

**Checkpoint not approved: operator found a real styling regression (separator dot, overall Figma mismatch) and a silent Bio save failure; two items pass, one is unconfirmed either way.**

## Performance

- **Duration:** ~25 min (agent checkpoint prep + operator's live-stack verification session)
- **Completed:** 2026-07-28T23:26:54Z
- **Tasks:** 1 (checkpoint:human-verify) — not approved
- **Files modified:** 0 (this plan produces no code artifacts, per its own scope)

## Accomplishments

This plan has no code accomplishments of its own — it is the live-stack verification gate for the five code plans (39-01 through 39-05). Its purpose was to confirm those plans' work on the real dev database and a running browser session.

## Operator Verification Results

| # | Check | Result |
|---|-------|--------|
| 1 | Migrations applied to real dev DB | Not explicitly confirmed — no `alembic current`/`upgrade` output reported |
| 2 | Importer backfill + idempotency | **Pass** — first run created 1 tenure (expected, pre-existing importer behavior), second run created 0 (idempotency holds) |
| 4-5 | Popover data display (Rehnquist / living Justice) | Not explicitly confirmed individually — see styling findings below |
| 6 | Party-neutral treatment (**the one explicitly blocking check**) | **Not addressed in operator's response — needs explicit confirmation** |
| 7 | Bio clamp/toggle | Blocked — could not be meaningfully checked because the underlying bio save is broken (see D5 below) |
| 8-9 | Advocate card / no extra fields | Not explicitly confirmed |
| 10 | Editor round-trip: Death Date | **Pass** — "death date saves fine" |
| 10 | Editor round-trip: Reason Left | **Pass** — "reason for leaving also saves and displays correctly" |
| 10 | Editor round-trip: multi-tenure add | **Pass** — "I can add more tenures and they show up as expected" |
| 10 | Editor round-trip: Bio & Photo save | **Fail** — bio text does not persist; input shows the typed value until refresh, then reverts |
| 11 | Reason Left dropdown values | Not explicitly confirmed |

## New Defects Found (not on the original 11-step list)

1. **Separator dot too small.** The `·` between the birth and death dates, and between the appointing president's name and party, renders with no visible spacing and is hard to read. Confirmed by direct comparison: operator's screenshot (`bench popover.png`) shows `b. Mar 19, 1891·d. Jul 9, 1974` and `Dwight D. Eisenhower· Republican` with the dot flush against adjacent text; the target mockup (`popover - Bench.png`) shows clearly spaced ` · ` on both sides.

2. **Overall style diverges from the Figma mockups.** Comparing the same two images: the mockup renders each tenure as a two-column row (bold tenure title left, year range right-aligned on the same line — e.g. "Chief Justice" / "Sep 1986 – Sep 2005"), while the live popover renders a single line "Chief Justice — 1953–1969" with an em dash, not bold, not two-column. Name/title typography also reads noticeably less prominent in the live version than the mockup.

   Note: both mockups show an "Edit person" link at the bottom right. This is **intentionally absent** in Phase 39's scope (D-17, deferred to backlog item 999.9) — its absence in the live popover is correct, not a defect.

3. **Bio & Photo save silently fails.** Operator: "I added a short bio to Felix Frankfurter but it did not show up on the card. Turns out, it didn't actually save, but the text I entered persisted in the box until I hit refresh." The input field misleadingly retains the typed value, masking the failed save until a reload. Root cause not yet investigated — could be a pre-existing bug in the Bio & Photo action, or a regression introduced by 39-03's changes to the same admin editor files.

## Out-of-Scope Defect Found (NOT part of Phase 39 gap closure)

**Unpublished argument still visible in the `/cases/` list and directly accessible by URL.** This is a publish/visibility-control bug unrelated to Phase 39's popover/context-data work — it existed before this phase and is not touched by any of the five code plans. Filed separately as `.planning/todos/pending/2026-07-28-unpublished-argument-visible-in-cases-list.md` rather than folded into this phase's gap closure.

## Decisions Made

- Checkpoint is NOT approved. Plan 39-06 and Phase 39 remain incomplete pending gap closure.
- The out-of-scope publish-visibility bug is tracked as a new todo, not a Phase 39 gap — it's unrelated to this phase's requirement (PUB-04) or any file this phase touched.

## Deviations from Plan

None — plan executed as specified (checkpoint prep + relay of operator's live findings). The plan's own prohibition ("MUST NOT approve this checkpoint on the basis of a code read alone") was honored: no step above is marked pass without an explicit operator statement, and the styling defects were confirmed by direct screenshot comparison, not assumption.

## Issues Encountered

Operator's response covered some but not all of the 11 numbered steps explicitly. Step 6 (party-neutral treatment) — the one check the plan calls out as blocking rather than cosmetic — was not addressed either way and is called out above as needing explicit follow-up before this checkpoint can close.

## Next Phase Readiness

Not ready to close. Recommended path:
1. Operator confirms step 6 (party-neutral treatment) explicitly.
2. `/gsd-plan-phase 39 --gaps` to create fix plans for: separator-dot spacing, tenure-row layout matching the Figma mockups, and the Bio & Photo save bug.
3. Re-run this checkpoint after gap-closure plans land.

---
*Phase: 39-bench-popover-additional-context-data*
*Completed: 2026-07-28*
