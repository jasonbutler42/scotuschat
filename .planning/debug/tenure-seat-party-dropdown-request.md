---
status: diagnosed
trigger: "In the person editor's Tenure Period sub-card (Bench toggle), the Seat and President's Party fields are free-text inputs. The user expected/wants them to be dropdowns instead."
created: 2026-07-09T12:15:00Z
updated: 2026-07-09T12:35:00Z
---

## Current Focus

hypothesis: CONFIRMED (mixed) — the two fields named by the user have two different histories. "President's Party" free-text is an explicit, deliberate D-16 decision (dropdowns were considered and explicitly rejected). "Seat" free-text was never decided one way or the other — it was omitted from D-18's field list (a documented oversight), later restored purely to satisfy PEDIT-09's "field must render" requirement, and the restorer chose `type="text"` by copying sibling-field styling, not per any recorded decision about Seat's input type.
test: Traced 27-CONTEXT.md decisions (D-16, D-18), 27-DISCUSSION-LOG.md, 27-05-SUMMARY.md, 27-VERIFICATION.md (Seat gap-closure), REQUIREMENTS.md PEDIT-09, models.py CourtTenure.seat column comment, and the live +page.svelte/admin_people.py code.
expecting: N/A — diagnosis only, no fix.
next_action: Return ROOT CAUSE FOUND / diagnosis to caller. No fix_and_verify (goal: find_root_cause_only).

## Symptoms

expected: User's stated expectation: "Seat and President's Party should both be dropdowns."
actual: Both fields are currently plain `<input type="text">` elements bound to `TenureRow.seat` and `TenureRow.appointing_president_party` respectively.
errors: None — cosmetic/preference request, not a functional bug. User confirmed the surrounding animation/data-preservation behavior works correctly.
reproduction: Test 2 in UAT (Phase 27, .planning/phases/27-people-admin/27-UAT.md) — /admin/people/{id}, toggle Bench, look at a Tenure Period sub-card.
started: Discovered during UAT for Phase 27 (People Admin), 2026-07-09.

## Eliminated

(none — this was a documentation/decision trace, not a hypothesis-elimination investigation)

## Evidence

- timestamp: 2026-07-09T12:18:00Z
  checked: .planning/phases/27-people-admin/27-CONTEXT.md, Decision D-16
  found: "D-16 — Tenure appointment field input types (previously blocked, now settled by mockup): Both Appointed by (e.g. 'Richard Nixon') and Appointing president's party (e.g. 'Republican') are plain free-text `<input>` fields, matching every other text field's styling — not dropdowns, not a curated president lookup."
  implication: President's Party free-text is an EXPLICIT, deliberate decision. The decision text explicitly considered and rejected dropdowns/curated lookups for this field. D-16 covers only `appointed_by` ("Appointing President") and `appointing_president_party` ("President's Party") — it says nothing about `seat`.

- timestamp: 2026-07-09T12:19:00Z
  checked: .planning/phases/27-people-admin/27-CONTEXT.md, Decision D-18
  found: "Each Tenure Period row is its own bordered sub-card (Start Date, End Date, Appointing President, President's Party, Reason Left [disabled per D-19], a 'Remove' button)... matches the mockup's nested-card treatment" — this field list does not mention Seat at all.
  implication: D-18's mockup-derived field list silently omitted Seat. This is a scoping gap in the decision record, not a decision to drop or retype Seat.

- timestamp: 2026-07-09T12:20:00Z
  checked: .planning/phases/27-people-admin/27-05-SUMMARY.md (Decisions Made section) and inline code comment at +page.svelte:506-509
  found: "`TenureRow.seat` stays in client state and the serialized `tenures` payload with no UI input for it — D-18's sub-card field list ... never mentions Seat, but Task 1 explicitly said 'drop nothing else' from the mapping, so removing the input while keeping the field prevents a silent data loss." The plan executor explicitly flagged the Seat omission as inherited from D-18, not a fresh decision.
  implication: Confirms the omission traces directly back to D-18's incomplete field list, carried forward without re-litigation during initial implementation (Plan 27-05).

- timestamp: 2026-07-09T12:21:00Z
  checked: .planning/phases/27-people-admin/27-VERIFICATION.md (initial pass note, lines 35, 118-120)
  found: "The user was asked whether this was an intentional deviation (per D-18's mockup-derived field list) or an oversight, and confirmed it was an oversight." Fix commit `34bad2c8` ("fix(27): restore Seat field to the tenure period editor (PEDIT-09 gap)") added a plain text `<input>` for Seat, styled "consistent with the other four tenure-row inputs."
  implication: The operator was consulted specifically about WHETHER Seat should exist as a field at all (oversight vs. intentional removal) — confirmed oversight. But the operator was never asked, and the record shows no discussion of, WHAT INPUT TYPE Seat should use. The fix's `type="text"` choice was the implementer's default (pattern-matching sibling fields), not a decision point put to the user.

- timestamp: 2026-07-09T12:22:00Z
  checked: .planning/REQUIREMENTS.md, PEDIT-09 (locked requirement, predates Phase 27)
  found: "Tenure rows each contain: Seat (Chief / Associate), Appointed by, Appointing president's party, Start date, End date — add / remove rows as before." Marked [x] Complete, mapped to Phase 27.
  implication: The requirement's own parenthetical "(Chief / Associate)" suggests the requirement author's mental model of Seat as a small enum — but the requirement only mandates the field exists and what it conceptually represents, not its HTML input type. No REQUIREMENTS.md language anywhere mandates or forbids a dropdown for Seat.

- timestamp: 2026-07-09T12:23:00Z
  checked: api/models/models.py, CourtTenure.seat column (line 133)
  found: "seat = Column(String(100))  # e.g. \"Associate Justice Seat 3\"" — a free-form VARCHAR(100), with the inline comment's own example showing a numbered-seat value, not just "Chief"/"Associate".
  implication: The actual data model contradicts REQUIREMENTS.md's "(Chief / Associate)" parenthetical — real seat values include historically-numbered seats (e.g. "Associate Justice Seat 3"), which is a much larger and less stable value space than a 2-option Chief/Associate toggle. This is a substantive fact relevant to any future dropdown decision (a curated Seat dropdown would need a maintained seat-number list, structurally similar to the "curated president lookup" that D-16 explicitly rejected for president name) — but it is evidence about design tradeoffs, not evidence of any decision having been made.

- timestamp: 2026-07-09T12:24:00Z
  checked: .planning/phases/27-people-admin/27-DISCUSSION-LOG.md (grep for "seat"/"dropdown"/"free text")
  found: Line 119: "Role is not needed at all... and listed new desired per-tenure fields: start date, end date, appointed by, president's party, and a new 'reason tenure term ending' field." Line 167: "Tenure appointment field input types: both Appointed by and Appointing president's party are plain free text (D-16)." No mention of "seat" or "dropdown" anywhere else in the discussion log.
  implication: Confirms the only input-type discussion the operator ever had was about `appointed_by`/`appointing_president_party` (D-16's subject). Seat's input type was never raised as a topic in discussion at all — not even to be rejected.

- timestamp: 2026-07-09T12:25:00Z
  checked: app/src/routes/admin/people/[id]/+page.svelte (live code, lines 503-585) and api/schemas/admin_people.py (TenureRow, lines 27-39)
  found: Seat renders as `<input id="tenure-seat-{row._key}" type="text" bind:value={row.seat} .../>` (lines 517-521); President's Party renders as `<input id="tenure-party-{row._key}" type="text" bind:value={row.appointing_president_party} .../>` (lines 579-583). `TenureRow` in the Pydantic schema types both as `Optional[str]`, with an explicit docstring: "Phase 27 additions: appointed_by and appointing_president_party are free-text, per-row appointment fields (D-16)."
  implication: Confirms current shipped state matches the symptom exactly. The schema docstring itself cites D-16 by name for `appointing_president_party` — direct code-level confirmation that this field's free-text-ness is a traced, intentional decision. No equivalent citation exists anywhere for `seat`.

## Resolution

root_cause: |
  Two distinct histories collapsed into one user complaint:

  1. **President's Party (`appointing_president_party`) is free-text by EXPLICIT, deliberate decision (D-16, 27-CONTEXT.md).** During Phase 27 discussion, the operator's mockup review explicitly settled this "previously blocked" question: "Both Appointed by ... and Appointing president's party ... are plain free-text `<input>` fields ... not dropdowns, not a curated president lookup." A dropdown was considered by name and rejected. This is documented, cited in the Pydantic schema's own docstring, and carried through implementation faithfully. Changing it now is a reversal of a locked decision, not a bug fix.

  2. **Seat (`seat`) is free-text with NO explicit decision behind it either way.** D-18's mockup-derived sub-card field list omitted Seat entirely (an acknowledged gap, not a deliberate exclusion — the operator confirmed during phase verification this was "an oversight," not an intentional D-18 deviation). The field was later restored (commit `34bad2c8`) solely to satisfy PEDIT-09's requirement that the field render at all; the fix author chose `type="text"` purely by visual/structural pattern-matching against the sibling fields (Start Date/End Date/Appointing President/President's Party), not from any recorded deliberation about Seat's ideal input type. Seat's input type was never raised as a topic in 27-DISCUSSION-LOG.md, 27-CONTEXT.md, or 27-UI-SPEC.md at any point.

  A relevant fact for any future dropdown decision on Seat specifically: `CourtTenure.seat` is a free-form `VARCHAR(100)` whose own model comment gives the example `"Associate Justice Seat 3"` — real seat values are not a clean 2-value Chief/Associate enum (as REQUIREMENTS.md's PEDIT-09 parenthetical implies), which means a Seat dropdown would need a maintained, curated seat list — structurally the same kind of "curated lookup" that D-16 explicitly rejected for president names (for different reasons: unbounded historical values, not stable to enumerate). This is evidence relevant to a future design discussion, not evidence that a decision was already made.
fix: (not applicable — goal: find_root_cause_only)
verification: (not applicable — goal: find_root_cause_only)
files_changed: []
