# Phase 39: Bench popover — additional context data for Justices - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-21
**Phase:** 39-bench-popover-additional-context-data
**Areas discussed:** Mockup review (bench + advocate cards), Reason for leaving, Editor wiring, Party affiliation exposure, Historical data backfill, Bio text, Location/descriptor, Edit link

---

## Initial area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Reason for leaving | Free text vs. constrained enum; auto-derive vs. manual | ✓ |
| Editor wiring | Activate disabled Death Date / Reason Left inputs or not | ✓ |
| Party affiliation exposure | Reverses T-14-02 public-API exclusion; confirm apolitical presentation | ✓ |
| Historical data backfill | Build capability only, or also backfill real historical data | ✓ |

**User's choice:** All four selected, plus free text: "I have mockups so let's talk about this first."

---

## Mockup review

User pasted two mockup images (bench/Justice card for William H. Rehnquist; advocate card for James Bopp Jr.) rather than pointing to a file/Figma link.

**Findings surfaced against current schema/code:**
- Bio/narrative paragraph shown on the Justice card — `Person.bio_text` exists in the DB but has never been displayed in the popover.
- "Location" field on the advocate card ("Dallas, Texas") — no such field exists in the DB at all.
- "Edit person" link on both cards — no admin-edit affordance exists on the public popover today; overlaps with deferred backlog item `999.9`.

### Bio text

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, include it | Display bio_text in the popover (clamped), for both bench and advocate speakers | ✓ |
| Yes, Justices only | Display only on the bench card | |
| No, defer it | Keep bio_text out of this phase | |

**User's choice:** "Yes, include it" (both bench and advocate).

### Location / descriptor

| Option | Description | Selected |
|--------|-------------|----------|
| No, out of scope | Recommended — defer to its own phase | |
| Yes, include it | Add a real location field to Person | |

**User's choice:** Free text — clarified this isn't a "location" field at all; it's a general advocate descriptor/title line (sometimes just a location, sometimes a full title+employer+location) that follows an advocate's name in the transcript. No such field/extraction exists today. **This mockup depicts a future state.** Directive: use placeholder/dummy text for this UI slot now; wire real data in a future phase. User also flagged this as their general approach going forward: mockups may depict future state beyond a phase's actual scope, and Claude should keep flagging things that look out of scope rather than assuming everything shown is in-bounds.

### Edit link

| Option | Description | Selected |
|--------|-------------|----------|
| Defer to 999.9 | Recommended — leave out of Phase 39 entirely | ✓ (with addition) |
| Include simple link | Add a plain admin-only link in this phase | |

**User's choice:** "Keep it deferred but make a note in 999.9 to reference these mockups." A note was added to `.planning/phases/999.9-edit-affordance-on-utterances-and-speaker-popover/NOTES.md`.

---

## Reason for leaving

### Field shape

| Option | Description | Selected |
|--------|-------------|----------|
| Constrained enum | death/retirement/promotion, matches Phase 37 precedent — recommended | ✓ |
| Free text | Matches the original disabled input's type="text" shape | |

**User's choice:** Constrained enum.

### Auto-derivation

**User's question (not a straight option pick):** "I believe the reason left is part of the corpus data, so I don't expect there to be many manual edits, but can you confirm that the data exists?"

**Investigation result:** Confirmed — `data/corpus/supreme_court_justices_sections.csv` has a `Reason Left` column for all 126 rows with exactly the vocabulary needed: `Retired` (58), `Died` (51), `Promoted to Chief Justice` (3), `Still in Office` (9), blank (2). `import_justices_csv.py` currently doesn't read this column (or `Birthdate`/`Death Date`, also present in the same CSV). This resolved the auto-derivation question: no inference logic needed — it's authoritative source data, imported directly.

### Enum values (follow-up after the CSV finding)

| Option | Description | Selected |
|--------|-------------|----------|
| Exactly 3: retired/died/promoted | Matches CSV vocabulary exactly — recommended | ✓ |
| Add resigned/other | For future flexibility | |

**User's choice:** Exactly 3 values. Notes: even Fortas's 1969 scandal-resignation is classified `Retired` in the source data — the vocabulary genuinely doesn't distinguish resignation from ordinary retirement.

---

## Historical data backfill

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, extend + backfill nulls | Add 3 CSV columns to the importer; backfill existing rows only where currently null — recommended | ✓ |
| New rows only, no backfill | Only populate for justices imported for the first time going forward | |

**User's choice:** Yes, extend + backfill nulls. Mirrors the established Phase 38 D-16 "never overwrite an operator value" pattern.

---

## Editor wiring

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, activate both | Wire Death Date + Reason Left (now a dropdown) into the save flow — recommended | ✓ |
| Keep disabled/read-only | This phase only adds DB fields + public display | |

**User's choice:** Yes, activate both.

---

## Party affiliation exposure

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, reverse it | Show appointing president's party publicly, neutral/identical treatment | ✓ |
| No, keep excluded | Keep party admin-only | |

**User's choice:** "Yes, include it, but this is not the Justice's party affiliation, this is the party affiliation of the appointing president." (Confirms the field itself — `CourtTenure.appointing_president_party` — was already correctly modeling the president's party, not the Justice's; the clarification was about wording, not a schema change.)

---

## Bio clamp interaction

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed clamp, no expand | Simple truncation, matches mockup visually | |
| Click-to-expand | Read-more affordance to reveal full bio_text | ✓ |

**User's choice:** Click-to-expand.

---

## Claude's Discretion

- Exact enum constant names / migration mechanics for the reason-left field.
- Exact display wording per reason value (e.g. "Died in office", "Promoted", "Retired" equivalent).
- Exact bio-text clamp length/line-count and click-to-expand interaction details.
- Exact popover layout for the expanded per-tenure data (deferred to `/gsd-ui-phase` — this phase has a UI hint set).
- Exact placeholder copy/positioning for the advocate descriptor slot.

## Deferred Ideas

- Advocate descriptor/title real data + extraction pipeline — placeholder UI only this phase; future phase wires real data.
- "Edit person" link on the popover — belongs to backlog item `999.9`; a mockup-reference note was added there during this discussion.
