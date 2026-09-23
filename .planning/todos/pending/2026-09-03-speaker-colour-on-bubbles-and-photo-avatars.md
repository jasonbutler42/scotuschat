---
created: 2026-09-03
kind: idea
source: operator, Phase 51 plan 51-10 Task 3 walkthrough (stop 03)
resolves_phase: null
priority: medium
audit_acknowledged:
  milestone: v1.8
  at: 2026-09-23
---

# Extend speaker colour to the bubbles, and decide what photo avatars do to identity

Operator: *"I think we need to extend the color to the bubbles so they are more inline with
the avatars or at least I'd like to test that. Especially since avatars that have an image
won't have the same effect."*

Two coupled questions, which is why they are one todo.

## 1. Colour on the bubble, not only the avatar

Today the per-speaker colour lands on the rail avatar; the bubble is neutral. Extending it —
a tint, a border, an edge — would make speaker identity legible without tracking back to the
rail. The operator wants to **test** this, not adopt it sight-unseen.

Hard constraint: **P-03**. The speaker ramp is solved to one luminance (CIE L* 78, OKLCH
chroma 0.09) precisely so no speaker reads louder than another, and the same equality must
survive whatever the bubble treatment turns out to be. A tint that is legible for one hue and
washed out for another re-introduces prominence through the back door. Any candidate needs
the same measurement the ramp itself got, across all eleven slots plus the unresolved
neutral.

## 2. Photo avatars defeat colour-as-identity

**Verified 2026-09-03:** photos render in `SpeakerPopover` only. The transcript's rail and
bubble avatars are `<div class="speaker-fill">` with initials — `git log -S"<img>"` on
`app/src/routes/arguments/[slug]/+page.svelte` returns nothing, so no `<img>` has ever
existed there. This is a missing feature, not a regression. The backend is fine end to end:
`/uploads` is mounted from `data/uploads`, and `/uploads/people/2185.webp` serves
`200 image/webp`.

So the decision is a design one, and it interacts with question 1: if a photo replaces the
coloured disc, that speaker loses the colour channel — which matters much more once colour is
also carrying meaning on the bubble. Options worth testing: a coloured ring around the photo,
a coloured bubble treatment that is independent of the avatar, or photos deliberately not
used on the transcript at all.

## Where to see it

`Sandra Day O'Connor` (person 2185) has a photo and speaks in
`/arguments/anderson-v-liberty-lobby-inc`. Open her popover to see the photo path working,
then look at her rail avatar to see the initials path.
