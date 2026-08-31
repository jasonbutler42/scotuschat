---
spike: "004"
name: argument-as-a-call
type: design
validates: "Given one argument rendered as a call in two arrangements — a uniform Teams-style grid and a courtroom layout — then which arrangement readers prefer, and whether either can present speaker prominence without asserting a conclusion the apolitical constraint forbids"
verdict: OPEN — awaiting user testing
related: ["SEED-002-scotus-teams-video-call-presentation"]
tags: [design, mockup, presentation, seed-002, p-03, apolitical]
---

# Spike 004: An argument as a call

A design spike, not a parse spike. It exists to be shown to people, which is the only
way the question it asks gets answered.

## What This Validates

[[SEED-002-scotus-teams-video-call-presentation]] proposes presenting an oral argument as a
video call — a second view of the same record, alongside the chat transcript. Two things had
to be seen before that could be judged, and neither could be settled by argument:

1. **Which arrangement is right.** A uniform grid is the familiar thing and the reason the
   idea appeals. But a grid erases the bench/advocate asymmetry that is the one constant
   across this whole project. A courtroom arrangement keeps it, at the cost of the
   familiarity that motivated the idea.
2. **Whether the format can stay inside P-03.** A call view communicates who dominated
   without computing it. That was ruled acceptable (see below), but the ruling has a
   boundary, and the boundary is easier to judge against something rendered.

## How to Run

```
# No build step, no server, no dependencies — the data is inlined.
open .planning/spikes/004-argument-as-a-call/viewer.html
```

`data.json` is the same window, kept separately so it can be regenerated. It is already
inlined into `viewer.html`; editing it alone changes nothing.

Also published as a private artifact for showing to people:
<https://claude.ai/code/artifact/ce5c5849-174f-482b-baa9-1893abcefbd4>

## The data

Anderson v. Liberty Lobby, Inc. (No. 84-1602, argued 1985-12-03) — the rebuttal, turns
134–152. Chosen because it is the densest stretch of speaker changes in the only published
argument in the dev DB: six speakers alternating, both advocates, four justices.

Speakers, sides, order and transcript text are the real record, pulled from
`/arguments/by-slug/anderson-v-liberty-lobby-inc/utterances`. Colours are the seven
first-appearance slot assignments the live transcript makes, so the mockup and the product
cannot disagree.

**Timings are synthetic and labelled as such on the page.** Durations are estimated at ~14
characters/second, not taken from Oyez's alignment — whether that alignment data can be
licensed is the open question SEED-002 says to answer first, and this spike deliberately
does not depend on it. The estimate is strictly proportional to text length, so the *ratio*
between speakers stays honest at every playback speed even though the absolute times are
invented.

## What the constraints forced

- **No speaking-time meter.** In this window one advocate holds ~64% of the floor, and
  playing either arrangement makes that unmistakable. That is intended: the operator's
  ruling of 2026-08-29 is that the project may never *tell* a reader who dominated, but may
  present faithfully and let them conclude it themselves. What is forbidden is amplifying —
  no tile scaled by cumulative talk time, no reordering by participation, no "most active"
  badge. If a design makes the disparity easier to read than it was in the room, it has
  crossed the line.
- **Emphasis is transient, never structural.** Every tile is identical in size and weight
  when nobody is speaking. Active-speaker highlight is a fact about the present moment and
  it moves on.
- **Initials for everyone, not photographs.** Justices have good portrait coverage and
  advocates do not; at tile size a bench of faces opposite a row of blanks would read as a
  status difference produced by nothing but data coverage.
- **Tile order is first appearance, not seniority.** The real bench is seated by seniority
  and reproducing that would be faithful, but that data is not here and inventing a seating
  chart would be fabrication. The arc tests the geometry, not the seats.
- **The grid is capped at four columns.** Seven participants at six-across left one tile
  stranded on its own row, which reads as an odd one out — the exact impression the layout
  must not create.

## Findings so far (author's, not tested)

The courtroom arrangement carries more than expected for one hairline rule and a gap: it
says what kind of proceeding this is, which the grid does not. Seven equal tiles could be
any meeting. The familiarity argument for the grid is real but thinner than it sounded.

The courtroom layout is also the more defensible of the two under the operator's own ruling:
fixed positions reflecting where people sat are a fact about the room, whereas any uniform
grid invites the question of what its order means.

**None of this is the answer.** The spike exists to be shown to people, and the author's
read is the hypothesis under test, not the result.

## Notes for whoever picks this up

- The bench arc is `nth-child` translateY offsets. They must be neutralised below 520px,
  where the row wraps and the offsets land on the wrong tiles — and the override needs
  `:nth-child(n)` purely to match specificity, since a media query adds none of its own.
- The mic level meter animates only under `.is-playing`. A CSS animation does not stop when
  a JS clock does, so without that gate a paused call kept showing someone mid-sentence.
- The caption tracks the *turn*, not the speaker. Keying it on the speaker name strands it
  on an earlier turn whenever someone holds the floor across consecutive turns — which, in
  this window, is most of it.
