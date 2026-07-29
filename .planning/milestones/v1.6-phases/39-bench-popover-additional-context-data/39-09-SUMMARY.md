---
phase: 39-bench-popover-additional-context-data
plan: 09
subsystem: ui
tags: [operator-checkpoint, gap-closure-verification]

requires:
  - phase: 39-bench-popover-additional-context-data
    provides: bio save fix (39-07), separator/mockup-layout fix (39-08)
provides:
  - Operator-confirmed closure of all three 39-06 UAT gaps, live on the real dev stack
affects: []

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified: []

key-decisions:
  - "Checkpoint approved — all three 39-UAT.md gaps confirmed closed by the operator on the live stack"
  - "A new minor finding (popover scroll container doesn't share the visible card's rounded boundary, so the scrollbar renders outside it) is filed as its own todo, not folded into this phase's gap closure, per the operator's own 'minor' framing"

patterns-established: []

requirements-completed: [PUB-04]

coverage:
  - id: D1
    description: "Bio & Photo save gap (39-UAT.md gap 1) closed — bio saves via Save Person and persists through reload"
    requirement: "PUB-04"
    verification:
      - kind: manual_procedural
        ref: "operator checkpoint response"
        status: pass
    human_judgment: true
    rationale: "Operator: 'My testing with short and long bios looks good: everything saves and renders what was saved.'"
  - id: D2
    description: "Separator dot spacing gap (39-UAT.md gap 2) closed"
    requirement: "PUB-04"
    verification:
      - kind: manual_procedural
        ref: "operator checkpoint response"
        status: pass
    human_judgment: true
    rationale: "Operator confirmed via bundled 'The rest of the steps all pass' reply after the orchestrator explicitly listed remaining outstanding steps; no issue reported against separator spacing."
  - id: D3
    description: "Popover style/mockup-fidelity gap (39-UAT.md gap 3) closed — two-column tenure rows, hairline dividers, month-year dates"
    requirement: "PUB-04"
    verification:
      - kind: manual_procedural
        ref: "operator checkpoint response"
        status: pass
    human_judgment: true
    rationale: "Operator confirmed via bundled 'The rest of the steps all pass' reply; no issue reported against layout/style."
  - id: D4
    description: "Party-neutral rendering re-confirmed after 39-08 introduced the tenure block's first font-weight distinction"
    requirement: "PUB-04"
    verification:
      - kind: manual_procedural
        ref: "operator checkpoint response"
        status: pass
    human_judgment: true
    rationale: "The one explicitly blocking acceptance criterion in this plan. Operator confirmed via the same bundled reply, with no apolitical-constraint violation reported."
  - id: D5
    description: "Bio clamp/toggle exercised against real data for the first time (previously blocked by the save bug)"
    requirement: "PUB-04"
    verification:
      - kind: manual_procedural
        ref: "operator checkpoint response"
        status: pass
    human_judgment: true
    rationale: "Operator: 'My testing with short and long bios looks good: everything saves and renders what was saved.' A genuinely new observation, not a re-run — 39-UAT.md test 7 was never previously testable."
  - id: D6
    description: "The two save forms (Save Person / Upload photo) do not clobber each other's fields"
    requirement: "PUB-04"
    verification:
      - kind: manual_procedural
        ref: "operator checkpoint response"
        status: pass
    human_judgment: true
    rationale: "Covered by the operator's bundled 'The rest of the steps all pass' reply."
  - id: D7
    description: "The five deliberate mockup differences (no Edit person link, advocate 'Coming soon' descriptor, blue advocate pill, larger avatar/padding, full president names) are accepted as-is"
    requirement: "PUB-04"
    verification:
      - kind: manual_procedural
        ref: "operator checkpoint response"
        status: pass
    human_judgment: true
    rationale: "Covered by the operator's bundled 'The rest of the steps all pass' reply — none flagged as wanting a change."

duration: ~15h wall-clock (spanning the operator's travel schedule; active verification time was short)
completed: 2026-07-29
status: complete
---

# Phase 39: Bench popover additional context data — Plan 09 Summary

**Checkpoint approved: all three 39-06 UAT gaps confirmed closed on the live stack, party-neutral rendering holds after the restyle, one new minor finding filed separately.**

## Performance

- **Duration:** ~15h wall-clock (operator was traveling; verification happened across several short exchanges)
- **Completed:** 2026-07-29T14:04:46Z
- **Tasks:** 1 (checkpoint:human-verify) — approved
- **Files modified:** 0 (this plan produces no code artifacts, per its own scope)

## Operator Verification Results

An unusual wrinkle: the operator was traveling and could not reach the local Windows dev machine directly. A temporary Cloudflare quick tunnel was set up (torn down afterward — see Issues Encountered) to expose the local dev stack, and the operator verified everything through that tunnel from a remote device, including confirming the responsive/mobile experience works well as a bonus finding not on any checklist.

| # | Check | Result |
|---|-------|--------|
| 1 | Bio saves via Save Person, persists through reload (gap 1) | **Pass** — "My testing with short and long bios looks good: everything saves and renders what was saved." |
| 2 | Bio appears on the public popover | **Pass** — same quote as above |
| 3 | Read more / Show less toggle exercised against real long-bio data (genuinely new — previously blocked) | **Pass** — same quote as above |
| 4 | Separator spacing clear (gap 2) | **Pass** — bundled confirmation, see note |
| 5 | Tenure rows match mockup layout, hairline dividers, month-year dates (gap 3) | **Pass** — bundled confirmation, see note |
| 6 | Party-neutral rendering re-confirmed (the one explicitly blocking check) | **Pass** — bundled confirmation, see note |
| 7 | Photo save and Person save don't clobber each other's fields | **Pass** — bundled confirmation, see note |
| 8 | Five deliberate mockup differences accepted | **Pass** — bundled confirmation, see note |
| — | Mobile experience (bonus, not on the checklist) | **Pass** — "Things also work great on a mobile screen" |
| — | New finding: popover scrollbar renders outside the card's visible boundary on long content | **Issue, minor** — filed as a new todo, not folded into this checkpoint |

**Note on "bundled confirmation":** After the operator's first message covered the bio-related steps, the orchestrator explicitly re-listed the remaining outstanding items (party-neutral re-check, the two-save-forms check, the five deliberate differences) and asked for confirmation. The operator replied: "The rest of the steps all pass." This is a single reply covering multiple items rather than an individual answer per step — recorded here exactly as given, per this plan's own prohibition against inferring an unanswered step as a pass. No issue was reported against any of the bundled items.

## New Finding: Popover Scroll Containment

The operator reported: "One minor thing about the longer bios, though. The when the scrollbar appears, it's outside the popover card. I expected the bio section to expand and the scrollbar to stay inside. We may need to style the scrollbar so it's not as jarring."

Root cause (diagnosed by the orchestrator via direct code inspection): the scrolling element is `Popover.Content` in `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` (`overflow-y: auto`, `max-height: min(560px, 80vh)`), but the visible rounded card — background, border, border-radius — lives on an inner element inside `SpeakerPopover.svelte`. Since the scroll container isn't the element with the visual boundary, the browser's native scrollbar renders at the edge of the (invisible) outer box rather than flush against the card. This is a gap in 39-05's original scroll-backstop work (the max-height/overflow behavior itself works correctly — content never escapes or gets truncated, per the operator's own framing of this as a styling issue, not a functional one).

Per the operator's explicit "minor" characterization and this project's established precedent (39-06 filed the unrelated unpublished-argument bug as a todo rather than reopening the phase), this is filed as `.planning/todos/pending/2026-07-29-popover-scrollbar-outside-card.md` rather than triggering another `--gaps` round. It does not block phase 39 completion.

## Decisions Made

- All three original UAT gaps are marked `status: resolved` in `39-UAT.md` with `resolved_by`/`resolved_date`/`resolution` fields, per this project's established convention (see Phase 38's `G-38-6`).
- The scrollbar finding is a new todo, not a phase-39 gap, since it's unrelated to any of the three original defects and the operator characterized it as minor/optional polish.

## Deviations from Plan

None — plan executed as specified. The plan's own prohibitions were honored: no step is marked passed without an operator statement behind it (bundled confirmations are recorded as bundled, not inflated into individually-itemized answers), and the checkpoint was not approved on the basis of any code read, test run, or agent-generated screenshot alone — every pass above traces to the operator's own words.

## Issues Encountered

The operator was traveling and could not reach the local dev machine. The orchestrator diagnosed and fixed an unrelated infrastructure issue along the way: the dev server (running continuously since the previous evening through many file changes) had a stale client-side route manifest, causing `/admin/people/{id}` to intermittently hydrate into the wrong route component (looking like a blank "create new person" form). Restarting the dev server resolved it. A temporary Cloudflare quick tunnel was used to give the operator remote access; it was set up with the operator's explicit informed consent (including the real dev DB and admin routes being reachable while active) and is torn down after this checkpoint, with the temporary `app/vite.config.ts` `allowedHosts: true` change reverted.

## Next Phase Readiness

Phase 39 is ready for `/gsd-verify-work 39` / phase completion. No open gaps remain in `39-UAT.md`. One new minor finding is tracked separately as a todo and does not block completion.

---
*Phase: 39-bench-popover-additional-context-data*
*Completed: 2026-07-29*
