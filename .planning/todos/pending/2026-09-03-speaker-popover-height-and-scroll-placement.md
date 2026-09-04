---
created: 2026-09-03
kind: defect
source: operator, Phase 51 plan 51-10 Task 3 walkthrough (stop 01)
resolves_phase: null
priority: medium
---

# Speaker popover: max height too large, placement drifts on scroll

Operator, walking the transcript: *"The speaker popover max height is pretty big and the
placement gets weird if you scroll. NOT a show stopper but it does need to be addressed."*

Two distinct problems in one component (`app/src/lib/public/SpeakerPopover.svelte` and its
anchoring in `app/src/routes/arguments/[slug]/+page.svelte`):

1. **Height.** The card is tall enough to be awkward. It carries an avatar row, name, office
   pill, tenure rows, and a bio — worth checking which of those actually earn their space at
   375px, and whether the bio needs a cap with the full text reachable elsewhere.
2. **Placement on scroll.** The anchor and the card come apart when the page scrolls. This is
   the class of bug that reads as "positioned wrong" while actually being a positioning
   *strategy* problem — fixed vs absolute vs anchored, and what it is anchored to.

## How to reproduce

Any published argument, e.g. `/arguments/anderson-v-liberty-lobby-inc`. Open a speaker
popover, then scroll the transcript underneath it. Worse at 375px.

## Notes for whoever picks this up

Verify with `document.elementFromPoint()` and `getBoundingClientRect()` on the card against
its anchor at several scroll offsets, not by eye alone — the Phase 51 sticky-avatar defect
was exactly a case where correct position and zero visibility were indistinguishable.
