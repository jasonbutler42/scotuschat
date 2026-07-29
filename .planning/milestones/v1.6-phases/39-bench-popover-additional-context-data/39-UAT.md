---
status: complete
phase: 39-bench-popover-additional-context-data
source: [39-01-SUMMARY.md, 39-02-SUMMARY.md, 39-03-SUMMARY.md, 39-04-SUMMARY.md, 39-05-SUMMARY.md, 39-06-SUMMARY.md, 39-07-SUMMARY.md, 39-08-SUMMARY.md, 39-09-SUMMARY.md]
started: 2026-07-28T23:26:54Z
updated: 2026-07-29T14:04:46Z
---

## Current Test

[testing complete]

## Tests

### 1. Migrations applied to real dev database
expected: `python -m alembic current` names the reason-left revision (0024) as head after `upgrade head`
result: skipped
reason: Not explicitly reported by operator (real dev DB was likely already at head from an accidental early apply during 39-02 — see STATE.md blockers).

### 2. Importer backfill + idempotency
expected: First run backfills birthdate/death date/reason and creates rows as needed; second consecutive run creates 0 people and 0 tenures
result: pass

### 3. Local stack starts and argument pages are viewable
expected: `dev-start.ps1` brings up a working stack; argument pages load and speaker avatars are clickable
result: pass

### 4. Rehnquist two-tenure card / tenure row layout (39-UAT.md gap 3 re-verify)
expected: Birth/death line, two tenure blocks (Chief 1986-2005 Died in office, Associate 1972-1986 Promoted), card fits or scrolls, tenure rows two-column matching mockup
result: pass
reported: 39-09 bundled confirmation — see note below.

### 5. Living Justice card
expected: Birth line only, no death half, no dash, no reason line on current tenure
result: pass
reported: 39-09 bundled confirmation — see note below.

### 6. Party-neutral rendering across different parties (re-verified post-39-08, the one explicitly blocking check)
expected: Identical field order, font size, and color regardless of appointing president's party — no visual difference tied to party value
result: pass
reported: "yes, all parties render identically" (39-06). Re-confirmed at 39-09 after 39-08 introduced the tenure block's first font-weight distinction — see bundled note below.

### 7. Bio clamp/toggle (3-line clamp, Read more/Show less) — genuinely new observation, never testable before 39-07 landed
expected: Long bio clips to 3 lines with a working Read more/Show less toggle; short bio shows no toggle; no bio shows no paragraph
result: pass
reported: "My testing with short and long bios looks good: everything saves and renders what was saved."

### 8. Advocate card
expected: Role pill, italic "Coming soon" descriptor line, bio if present, no tenure section
result: pass
reported: 39-09 bundled confirmation — see note below.

### 9. No extraneous fields
expected: No age, tenure-length, case-count, or "Edit person" link on any card
result: pass
reported: 39-09 bundled confirmation — see note below.

### 10. Admin editor round-trip (39-UAT.md gap 1 re-verify)
expected: Death Date, per-tenure Reason Left, and Bio & Photo all save and persist through Save Person / reload; a Bio & Photo save leaves a previously-set Death Date untouched
result: pass
reported: (39-06) "death date saves fine. reason for leaving also saves and displays correctly. I can add more tenures and they show up as expected." (39-09) "My testing with short and long bios looks good: everything saves and renders what was saved." Independently confirmed by an agent-run Playwright script exercising the real save+reload cycle against the live dev DB (diagnostic only, not the basis for this pass — the operator's own words above are).

### 11. Reason Left dropdown exact options
expected: Dropdown offers exactly — None —, Retired, Died in office, Promoted
result: pass
reported: 39-09 bundled confirmation — see note below.

### 12. Separator dot legibility (39-UAT.md gap 2 re-verify)
expected: The `·` between birth/death dates and between president/party renders with clear, visible spacing on both sides
result: pass
reported: 39-09 bundled confirmation — see note below.

### 13. Overall visual style vs. Figma mockups (39-UAT.md gap 3 re-verify)
expected: Popover layout matches 39-UI-SPEC.md / the Figma mockups (popover - Bench.png, popover-Advocate.png)
result: pass
reported: 39-09 bundled confirmation — see note below.

### 14. Bio section scroll containment (new finding at 39-09, not on any prior list)
expected: When popover content exceeds max-height, the scrollbar renders inside the card's visible boundary
result: issue
reported: "One minor thing about the longer bios, though. The when the scrollbar appears, it's outside the popover card. I expected the bio section to expand and the scrollbar to stay inside. We may need to style the scrollbar so it's not as jarring."
severity: minor

**Note on the "39-09 bundled confirmation":** Tests 4, 5, 8, 9, 11, 12, 13 and the re-verification of test 6 were answered together, not itemized individually. The orchestrator explicitly listed the outstanding items (party-neutral re-check, the two-save-forms-don't-clobber check, and the five deliberate mockup differences) and the operator replied: "The rest of the steps all pass." No issue was reported against any of them; the only new finding volunteered was test 14 (scrollbar). Also confirmed at 39-09: "Things also work great on a mobile screen" (not one of the original 8/11 steps, an additional positive observation).

## Summary

total: 14
passed: 12
issues: 1
pending: 0
skipped: 1
blocked: 0

## Gaps

- truth: "Bio text saves and persists through the Bio & Photo card, and a saved bio's clamp/Read-more toggle can be verified against real data"
  status: resolved
  reason: "User reported: added a short bio to Felix Frankfurter, it did not show up on the card; the typed text persisted in the input until refresh, then reverted — the save silently fails while appearing to succeed."
  severity: major
  test: 10
  root_cause: "bio_text was submitted only by the photo action's form (button: Upload photo), never by the primary Save Person action; the photo action's own bio PATCH was unchecked with a discarded rejection; the Biography textarea rendered its value as child text content, so the browser's dirty-value flag kept typed text on screen after reload."
  artifacts:
    - path: "app/src/routes/admin/people/[id]/+page.svelte"
      issue: "bio textarea lived inside the photo form and was seeded as child text content"
    - path: "app/src/routes/admin/people/[id]/+page.server.ts"
      issue: "photo action performed an unchecked person PATCH that could silently fail"
  missing: []
  debug_session: ""
  resolved_by: "39-07-PLAN.md"
  resolved_date: "2026-07-29"
  resolution: "Bio moved onto the Save Person form, bound via bind:value with resync on person change/failed save, photo action's person PATCH removed entirely. Operator (39-09): \"My testing with short and long bios looks good: everything saves and renders what was saved.\""

- truth: "The separator dot (·) between birth/death dates and between president/party renders with clear, legible spacing on both sides"
  status: resolved
  reason: "User reported: 'The dot between birth and death and also between the president and their party affiliation is too small to be effective.' Confirmed by direct comparison of the operator's screenshot (bench popover.png) against the Figma mockup (popover - Bench.png) — mockup shows clearly spaced ' · ', live version renders the dot flush against adjacent text on both sides."
  severity: minor
  test: 12
  root_cause: "Svelte trims whitespace-only text at {#if} block boundaries, collapsing the separator's padding."
  artifacts:
    - path: "app/src/lib/components/SpeakerPopover.svelte"
      issue: "separator rendered as bare whitespace inside conditional blocks"
  missing: []
  debug_session: ""
  resolved_by: "39-08-PLAN.md"
  resolved_date: "2026-07-29"
  resolution: "Separator rebuilt as a {#snippet separator(pad)} span with explicit padding Svelte cannot trim. Operator (39-09): confirmed via bundled \"The rest of the steps all pass\" reply, no issue reported."

- truth: "Popover visual layout (tenure row structure, typography weight) matches the 39-UI-SPEC.md / Figma mockup contract"
  status: resolved
  reason: "User reported: 'The overall style does not look like the design in Figma.' Confirmed by direct screenshot comparison: the mockup renders each tenure as a two-column row (bold tenure title left, year range right-aligned on the same line); the live version renders a single line with an em dash ('Chief Justice — 1953-1969'), not bold, not two-column. Name/title typography also reads less prominent than the mockup. Note: both mockups show an 'Edit person' link at bottom-right — its absence in the live popover is intentional (D-17, deferred to backlog item 999.9), not part of this gap."
  severity: major
  test: 4
  root_cause: "Tenure rows rendered as a single em-dash-joined line instead of a two-column layout; no per-section hairline dividers; year-only date granularity instead of month-and-year."
  artifacts:
    - path: "app/src/lib/components/SpeakerPopover.svelte"
      issue: "tenure block layout, section dividers, and date formatting diverged from the mockup"
  missing: []
  debug_session: ""
  resolved_by: "39-08-PLAN.md"
  resolved_date: "2026-07-29"
  resolution: "Tenure rows rebuilt as two-column pairs (semibold office title left, right-aligned month-and-year range), hairline dividers added per section. Deliberately supersedes 39-UI-SPEC.md's year-only copywriting row per the mockup. Operator (39-09): confirmed via bundled \"The rest of the steps all pass\" reply, no issue reported."

- truth: "When popover content exceeds max-height, the scrollbar renders inside the card's visible boundary"
  status: failed
  reason: "User reported: 'One minor thing about the longer bios, though. The when the scrollbar appears, it's outside the popover card. I expected the bio section to expand and the scrollbar to stay inside. We may need to style the scrollbar so it's not as jarring.'"
  severity: minor
  test: 14
  root_cause: "The scrolling element is Popover.Content (app/src/routes/cases/[slug]/arguments/[id]/+page.svelte, overflow-y: auto/max-height), but the visible rounded card (background/border/border-radius) lives on an inner element inside SpeakerPopover.svelte — the scroll container's box doesn't share the card's visual boundary, so the native scrollbar renders outside it."
  artifacts:
    - path: "app/src/routes/cases/[slug]/arguments/[id]/+page.svelte"
      issue: "Popover.Content owns overflow-y/max-height but not the card's visual boundary"
    - path: "app/src/lib/components/SpeakerPopover.svelte"
      issue: "visible card styling lives on an inner element, not the scroll container"
  missing: []
  debug_session: ""
  status_note: "Not folded into this phase's gap closure per operator's own 'minor' framing — filed as .planning/todos/pending/2026-07-29-popover-scrollbar-outside-card.md instead. Does not block phase 39 completion."
