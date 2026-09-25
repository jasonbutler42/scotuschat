---
id: SEED-003
status: dormant
planted: 2026-09-25
planted_during: 52-justice-identity
trigger_when: next milestone planning (/gsd-new-milestone scan), and any phase that touches transcript avatars, speaker bubbles, or the speaker card (Phase 54.1 first)
scope: small–medium — CSS/markup in the transcript route, ChatBubble and SpeakerPopover; no schema
---

# SEED-003: Gold standard for speaker identity in the transcript — ring avatars + 3px bubble edge

## Status of this decision

**The operator named this the end goal on 2026-09-25.** Which milestone it lands in is undecided.
It is recorded here so that no phase quietly ships something that drifts away from it. When a phase
touches transcript avatars, bubbles, or the speaker card, build toward this target, or say
explicitly why that phase stops short.

## The target

**Figma:** file `KICu66PtMLHk4fmxJYPggx` (SCOTUS Chat Design System), page *Speaker Popover
Exploration*, **Board 05, option B** (node `62:78`). The avatar treatment alone is Board 04
variant 4 (node `59:2`, marked CHOSEN). Both boards use a real excerpt: *Anderson v. Liberty Lobby*,
No. 84-1602, utterances 30–37, verbatim.

Two parts, one idea. **The per-argument speaker colour is the identity carrier. It appears as a line,
never as a filled mass, and it appears identically for every speaker.**

### 1. Avatars — same ring for everyone (Board 04 variant 4)

- Every avatar has a **2px ring in the speaker's per-argument colour, drawn outside** the circle.
- Inside the ring: the **portrait** if one exists, otherwise **initials in the speaker colour on
  `--color-bg`**. The filled speaker-colour disc is retired on both sides.
- Applies at every size: 32px transcript rail, 32px case-header roster, 60px popover, 80px person page.
- The initials fallback is the same treatment for an advocate (no portrait data exists) and for a
  justice whose portrait is missing or fails to load.

### 2. Bubbles — 3px edge on the avatar side (Board 05 option B)

- A **3px speaker-colour edge on the side facing the avatar**: left for bench turns, right for advocate
  turns. Drawn inside the bubble.
- **No other border.** The bubble fill stays `--color-surface`; separation from the page comes from
  the fill against `--color-bg`.
- The name label keeps the speaker colour, as shipped.
- The edge visually links each avatar to its bubble, and it echoes the "3px left border" of the v1.0
  transcript contract (noted on the Public page's `arguments-transcript` frame).

## Why this, and not the alternatives that were mocked

- **Why ring avatars:** Board 04 showed that portraits dropped into the rail with no ring nearly
  vanish on `--color-bg`. They also let the saturated filled advocate discs become the most prominent
  marks in the transcript. A ring on everyone gives both sides the same visual weight. It changes no
  source pixels, which the portrait spec forbids.
- **Why the 3px edge over a full coloured border (A) or an 8% tint (C):** every option adds colour in
  proportion to bubble size. Bubble size is faithful (it is how long someone spoke), but colour makes
  long turns more conspicuous. That is the "amplified is not legal" line in the apolitical constraint
  (CLAUDE.md; SEED-002 has the full doctrine). A tint scales with area and amplifies most. B scales
  only with bubble height and carries the least added mass. Tinted-fill contrast was measured at about
  10:1 body / 6.8:1 name label; not a blocker, just not needed.
- **Uniformity check:** colour comes from the per-argument assignment, never from role or side. Bench
  and advocate get the identical ring and the identical edge. Only the side the edge sits on differs,
  and that side already follows the shipped bench-left / advocate-right layout.

## What it supersedes (when it lands)

- The filled `.speaker-fill` initials disc in the transcript rail, case-header roster and
  `SpeakerPopover.svelte`.
- The bubble's neutral 1px `--color-border` outline.
- **Phase 54.1 success criterion 1** currently says a justice without a portrait renders "the existing
  coloured-initials fallback". If 54.1 adopts the avatar half of this seed, that wording needs to change
  to the ring fallback. That is a scope decision for the operator at 54.1 planning, not something to
  edit silently.

## Prerequisites and open items

- **Portraits in the rail** depend on Phase 54.1 ingesting the portrait set
  (`/home/jason/scotuschat/person-photos`, keyed by `oyez_speaker_id`).
- **Harlan attribution must be resolved first.** The corpus credits `j__john_m_harlan` (the elder,
  died 1911) with 803 utterances across 48 cases from 1955–1964, e.g. *Escobedo v. Illinois*. Those
  are Harlan II. Phase 52 D-01 maps that id to the elder, so the rail would show the elder's portrait
  beside every one of those turns. This contradicts D-01's "do not re-open" and needs an operator
  ruling: one person with two corpus ids, versus a remap at resolve time.
- **Palette:** the ring and edge use the existing 11-colour `--color-speaker-*` / L78 palette. The
  palette was tuned for filled discs and name text. Confirm the 2px ring and 3px edge read clearly on
  `--color-bg` / `--color-surface` for all 11 hues. The mocks used 7 and all read.
- **Mobile:** not mocked at 375px. Check the right-side advocate edge next to the avatar at phone width.
- **Frontend verification is by eye or a real browser only** (Testing Policy). No source-text contract
  tests for this.

## Breadcrumbs

- `app/src/routes/arguments/[slug]/+page.svelte` — rail avatar slots (`.speaker-fill`, ~lines 325–364,
  507–516) and the sticky run-level avatar (D-19 Style B2).
- `app/src/lib/public/SpeakerPopover.svelte` — 60px avatar and initials fallback.
- `app/src/app.css` — `--color-speaker-*` palette and `.speaker-*` classes.
- `.planning/notes/bio-card-figma-brief.md`, `.planning/notes/person-photo-asset-spec.md`,
  `.planning/notes/person-photo-delivery-validation.md`.
- Figma boards 00–05 on the Speaker Popover Exploration page (rationale, nine cases, person page, rail
  variants, bubble variants).
