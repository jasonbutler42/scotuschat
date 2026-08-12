---
created: 2026-07-29T14:04:46.000Z
title: Popover scrollbar renders outside the card's visible boundary on long content
area: ui
resolves_phase: 45
files:

  - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte
  - app/src/lib/components/SpeakerPopover.svelte

---

## Problem

Discovered during Phase 39's 39-09 operator checkpoint. When a Justice's popover content (e.g. a long bio, expanded via Read more) exceeds the card's max-height, the scrollbar that appears renders outside the visible rounded card boundary rather than staying flush against it. Operator's own words: "The when the scrollbar appears, it's outside the popover card. I expected the bio section to expand and the scrollbar to stay inside. We may need to style the scrollbar so it's not as jarring."

This is a styling/boundary-alignment issue, not a functional one — content does not escape the card or get truncated; the max-height/overflow backstop from Phase 39's 39-05 plan works correctly in that sense.

Root cause (diagnosed 2026-07-29): the scrolling element is `Popover.Content` in `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` (`style="z-index: 50; max-height: min(560px, 80vh); overflow-y: auto;"`), but the visible rounded card — background, border, border-radius — lives on an inner element inside `SpeakerPopover.svelte`. Since the element that scrolls isn't the element with the visual boundary, the browser's native scrollbar renders at the edge of the (invisible, likely larger) `Popover.Content` box instead of flush against the card.

## Solution

TBD — not implemented. Likely approaches:
- Move the card's visual styling (background/border/border-radius) onto `Popover.Content` itself (or a wrapper that exactly matches its box), so the scroll container and the visible card share the same boundary.
- And/or apply custom scrollbar styling (`::-webkit-scrollbar` / `scrollbar-width`/`scrollbar-color`) so it reads as an intentional part of the card rather than a jarring browser-default bar, per the operator's own suggestion.
