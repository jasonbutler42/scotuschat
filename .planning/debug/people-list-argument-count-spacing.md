---
status: resolved
trigger: "people-list-argument-count-spacing — On the Advocate tab of /admin/people, the table's Argument count and Missing fields columns visually run together with too little spacing — headers render as 'Argument countMissing fields' with no gap."
created: 2026-07-09T12:15:00Z
updated: 2026-07-12T00:00:00Z
goal: find_root_cause_only
resolved_by: "commit b9ee6eac (fix(27-07): add horizontal gutter padding to people-table middle columns) — all Bench/Advocate middle-column headers and cells now use padding: 8px 8px / 12px 8px. Verified in code 2026-07-12."
---

## Current Focus

hypothesis: CONFIRMED — see Resolution below
test: n/a (find_root_cause_only mode)
expecting: n/a
next_action: none — return ROOT CAUSE FOUND to caller

## Symptoms

expected: Adequate visual spacing between the Argument count value/header and the Missing fields pills/header in the Advocate-tab table on /admin/people.
actual: User reported "functional pass but the table spacing between argument count and missing fields is too tight" and provided a screenshot showing "Argument countMissing fields" running together as one string with the numeric count sitting immediately adjacent to the first pill with no visible gutter.
errors: None reported.
reproduction: Test 1 in UAT (Phase 27, .planning/phases/27-people-admin/27-UAT.md) — visit /admin/people, switch to Advocate tab.
started: Discovered during UAT for Phase 27 (People Admin), 2026-07-09.

## Eliminated

(none — root cause found via direct source read on first pass, no false hypotheses generated)

## Evidence

- timestamp: 2026-07-09T12:20:00Z
  checked: app/src/routes/admin/people/+page.svelte, Advocate-tab `<th>` for "Argument count" (lines ~224-236) and `<th>` for "Missing fields" (lines ~237-248)
  found: "Argument count" `<th>` uses `text-align: right; padding: 8px 0;` and "Missing fields" `<th>` uses `text-align: left; padding: 8px 0;`. CSS shorthand `8px 0` = padding-top/bottom 8px, padding-left/right **0**. The table itself has `border-collapse: collapse`, so there is no browser default cell-spacing fallback.
  implication: The two adjacent header cells have zero horizontal padding on the exact side that faces each other, and their text-align values push each header's text flush against that shared, zero-padding boundary. Nothing in the CSS creates a gutter between them.

- timestamp: 2026-07-09T12:22:00Z
  checked: Same file, Advocate-tab body `<td>` for argument count (lines ~292-300, `text-align: right; padding: 12px 0;`) and `<td>` for missing-fields pills (lines ~302-308, `padding: 12px 0;`, pills rendered in a `display:flex; gap:4px` span)
  found: Same zero-horizontal-padding pattern in the body rows. The `gap: 4px` flex rule only applies *between pills within* the Missing-fields cell — it does nothing to separate the cell from the Argument-count column to its left.
  implication: Body rows reproduce the exact same mechanism as the header — right-aligned numeric value directly abuts the left-aligned first pill, with 0px of padding from either side. Matches the user's report of "the numeric count sitting immediately adjacent to the first pill."

- timestamp: 2026-07-09T12:28:00Z
  checked: Sibling table in app/src/routes/admin/arguments/+page.svelte (same codebase, same visual system) for the established table-column padding convention
  found: The arguments-list table's *middle* columns (Case Title, Docket, Argued, Created) all use `padding: 8px 8px` (8px horizontal gutter on both sides). Only the table's outermost columns (first: Status, last: Publish) use `padding: 8px 0` — which is safe there because those columns sit flush against the table's own left/right edge, not against a neighboring column.
  implication: The codebase convention is unambiguous: any column that has a neighbor on both sides needs horizontal padding (typically `8px 8px` for headers, and the equivalent for body cells) to create a gutter. In the people-admin Advocate table, "Argument count" and "Missing fields" are BOTH middle columns (each has a neighbor on both sides) but both were coded with the "edge column" padding pattern (`8px 0` / `12px 0`) instead of the "middle column" pattern. This is the deviation that produces the reported bug — almost certainly a copy-paste carry-over from the Name column's edge-column styling when the Advocate-tab columns were added in Phase 27.

- timestamp: 2026-07-09T12:30:00Z
  checked: Bench-tab columns in the same file (Tenure coverage, Tenure gap — also middle columns using `padding: 8px 0`)
  found: Bench tab has the identical zero-horizontal-padding defect on its own middle columns, but both "Tenure coverage" and "Tenure gap" are `text-align: left`, so each column's text starts flush at its own left edge and the *visual* run-together effect is masked by whatever natural column width exists past the text. It is latent there, not visibly reported.
  implication: The root cause is not unique to the Advocate tab's specific columns — it's the general missing-horizontal-padding pattern applied to every middle column in this table. It is only *visibly* broken on the Advocate tab because "Argument count" (right-aligned) and "Missing fields" (left-aligned) are the one adjacent pair whose alignments both point at the same zero-padding shared boundary, making the gap literally 0px instead of merely "tight."

## Resolution

root_cause: >
  In app/src/routes/admin/people/+page.svelte, the Advocate-tab table's "Argument count"
  `<th>`/`<td>` (text-align: right) and "Missing fields" `<th>`/`<td>` (text-align: left) are
  both middle columns (each has a neighboring column on both sides) but were styled with the
  "edge column" padding shorthand `padding: 8px 0` (header) / `padding: 12px 0` (body) — i.e.
  zero horizontal padding — instead of the codebase's established middle-column convention of
  `padding: 8px 8px` / `padding: {v}px 8px` (seen in the sibling admin/arguments table). Because
  the table also has `border-collapse: collapse` (no fallback cell-spacing), and because
  "Argument count" is right-aligned while "Missing fields" is left-aligned, both columns' text
  is pushed flush against the exact same shared cell boundary with 0px of padding on either
  side — causing the header text and the body values/pills to visually merge with no gap, as
  reported ("Argument countMissing fields", pill touching the count).
fix: (not applied — find_root_cause_only mode)
verification: (not applicable — diagnosis only)
files_changed: []
