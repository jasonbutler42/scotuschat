# Plan 14-03 Summary — SvelteKit popover wiring

## Outcome: COMPLETE

All four tasks completed. Speaker popover card is fully functional.

## What Was Built

- `SpeakerPopover.svelte` — card component rendering photo/initials, name, role, tenure rows, and appointing president
- `ChatBubble.svelte` — avatar div converted to conditional `<button>` that calls `onAvatarClick`
- `+page.svelte` — shared `Popover.Root` at page level; `speakersMap` derived from server-loaded speakers; popover wired to both utterance avatars and header roster

## Bugs Fixed During Verification

**Stale pycache (pre-verify):** uvicorn was serving old bytecode without the speakers route. Fix: clear `api/**/__pycache__` before restarting after adding new modules.

**Popover anchor wrong (discovered during verify):** Two bugs with the same root cause — bits-ui `Popover.Content` had no anchor reference.

- *Header roster (Popover.Trigger):* bits-ui toggle handler fired after our `onclick` set `isPopoverOpen = true`, saw it already open, and toggled it closed → appeared to do nothing.
- *Utterance avatars (plain button):* No `Popover.Trigger` meant no anchor for bits-ui → content rendered at document origin (top of screen).

Fix: removed all `Popover.Trigger` from roster; added `customAnchor={currentAnchor}` to `Popover.Content`; updated `onAvatarClick(personId, anchor: HTMLElement)` to accept the clicked element; both callers pass `e.currentTarget`.

## Commits

- `722f372` — create SpeakerPopover.svelte
- `89a9915` — ChatBubble avatar div → conditional button
- `d19959d` — wire +page.svelte (Popover.Root, speakersMap, roster avatars, onAvatarClick)
- `b2fa0a9` — fix popover anchor (customAnchor prop + plain buttons)

## Verification Results

| Check | Result |
|-------|--------|
| `curl /arguments/3/speakers` returns JSON array | PASS |
| Utterance avatar click → popover at correct position | PASS |
| Header roster avatar click → popover at correct position | PASS |
| Escape closes popover, focus returns to button | PASS |
| Advocate avatar → name + role only (no tenure/president) | PASS |
| Tab to button, Enter opens, Escape closes | PASS |
| Photos absent (no photo_url in DB) → initials circles | PASS (expected) |

## Known Post-Phase Issues

- Page title bug on admin/people pages (argument name appearing) — deferred; investigate separately
