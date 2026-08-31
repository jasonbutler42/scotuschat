---
id: SEED-002
status: dormant
planted: 2026-08-29
planted_during: 51-design-system-noun-alignment
trigger_when: next milestone planning (/gsd-new-milestone scan)
scope: medium — a second VIEW inside scotuschat, not a separate project
---

# SEED-002: "SCOTUS Teams" — an argument presented as a video call

## The idea, as the operator framed it

Oyez already has the audio synchronised to the written transcript. Use that data
to present an argument as a **video call**: multiple windows, one per
participant, and whoever is speaking takes centre stage. Oyez's own listening
experience already uses an almost identical pattern — theirs just doesn't look
like a Teams call.

**The operator's argument for why it belongs in this family:** *"you aren't
changing the content at all, you're just presenting it in a different format."*

That is the load-bearing point. The apolitical constraint — identical schema,
depth and treatment for every speaker; no derived insight, no summaries, no
sentiment, no statistics — survives a presentation change untouched, because a
presentation change asserts nothing new. Chat bubbles and a call grid are two
renderings of the same unmodified record.

## Scope was revised down on 2026-08-29: this is a VIEW, not a sibling project

Initially captured as a separate project with its own constraints. The operator
corrected that in the same conversation: *"this could absolutely just be another
view for one of the arguments. You could read it as a chat or listen to it as a
video call."*

That is the better framing, and it is cheaper on every axis:

- **The groundwork already exists.** D-19 required the renderer to separate run
  grouping from presentation precisely so a later style became a rendering
  variant rather than a rewrite. Runs are also exactly the unit a call UI needs
  to decide when the active tile changes.
- **It de-risks the licensing problem** (below) from fatal to survivable. As a
  standalone project, unusable alignment data kills the whole thing. As a view,
  it just doesn't ship, and nothing else is affected.
- **It is a better product than either half.** Switching between reading and
  listening on the *same* argument is something Oyez does not do well, and it is
  only possible if both live in one place.
- The URL-addressable presentation state built for the variant switcher
  (`app/src/lib/public/VariantSwitcher.svelte`) is the right mechanism to reach
  it, though a view is a bigger unit than one of that component's axes.

**Consequence — graceful degradation becomes a hard requirement.** Audio
alignment is a dependency of one view only, and coverage across ~7,800 imported
arguments will not be uniform. The argument page must be fully usable without
it, and the call view must be offered only where the timings actually exist.
Never a dead control, never an empty player.

## Pitfall 1 — the call view LEAKS "screen time", and that is accepted

A call grid does not need to compute a speaking-time statistic in order to
communicate one. Tile prominence over time *is* a speaking-time visualisation.
Watch fifty minutes and you come away with a vivid impression of who dominated
and who sat silent — the kind of impression the apolitical constraint exists to
stop the project from manufacturing.

**Operator's ruling, 2026-08-29 — this is accepted, deliberately:**

> *"I love the potential insight of 'screen time' — who dominates a conversation
> is not something I want to* tell *someone but I'm very okay letting them
> experience for themselves and come to that conclusion on their own."*

The line this draws is **assert vs. infer**: the project may not make the claim;
the reader is free to reach it. That is a sharpening of "non-editorial", not a
loosening of it. It also matches existing precedent — `appointing_president_party`
was admitted in Phase 39 on the same reasoning: factual, unaggregated, rendered
identically for every entry, with the interpretation left to the reader.

**The corollary that keeps this honest.** The ruling licenses *faithful*
rendering — the call view shows what happened, at real duration, with every tile
treated identically. It does **not** license amplifying the disparity. A design
that scaled tile size by cumulative speaking time, ranked or reordered tiles by
participation, or persisted a "most active" emphasis would be asserting through
visual encoding while claiming to be neutral. Render the record at fidelity;
never editorialise the rendering. If a future design makes the disparity *easier
to read than it was in the room*, it has crossed the line.

## Pitfall 2 — the metaphor may fight the material

A Teams call is synchronous, symmetric and many-to-many: equal tiles in a grid,
turn-taking negotiated. An oral argument is none of those. It is structurally
asymmetric — one advocate at a lectern being questioned by nine justices from a
bench. The operator's one constant across this entire project is that the bench
sits on one side and advocates on the other, and **a uniform tile grid erases
exactly that.** The call metaphor may therefore be *less* faithful to the
proceeding than the chat layout already is.

**The fork worth exploring at mockup time:** lay the tiles out asymmetrically —
bench in an arc, advocate facing them — and it stops being a Teams call and
becomes a courtroom arrangement. That keeps the spatial truth and dodges the
flattening problem, at the cost of the familiarity that motivated the idea in
the first place. Mock both; the choice between them is the real design question,
not the chrome.

Note this interacts with Pitfall 1's corollary: a courtroom arrangement gives
tiles *fixed* positions reflecting where people actually sat, which is more
defensible than any layout that could be read as ranking.

## Resolved — "static images of dead people" is not a problem

Raised as a concern (most tiles would be still photographs of justices who died
decades ago, so a "video" call with no video). **Operator's answer, accepted:**
that is what every corporate call looks like now — cameras off, a grid of static
headshots with the speaker highlighted. The metaphor survives because the
familiar version of it is already static.

## Pitfall 3 — advocate photo coverage will be lopsided

Justices have good portrait coverage; advocates almost certainly do not. In the
chat view this degrades to a 32px initials circle and is barely noticeable. In a
grid of face-sized tiles, a bench of photographs facing a row of
initials-placeholders reads as a status difference — a P-03 failure produced by
nothing but data coverage. Audit advocate photo coverage early; it may force a
deliberate choice to use initials for *everyone*, which the existing
`photo_url_full` → initials fallback already supports.

## Pitfall 4 — static tile properties are where P-03 actually bites

Centre-stage-when-speaking is factual and transient, and rotates to whoever
speaks next — the same reasoning that already justifies the sticky rail avatar.
The mechanism is fine. The risk is in the properties that *don't* change:

- Tile **order** must not encode seniority, side, or importance.
- Tile **size** must be identical when nobody is speaking.
- No participant may be permanently larger, centred, or first.

## The one thing to answer before building: the alignment timings

The app already carries *"Historical transcript imported from Oyez.org via
Cornell ConvoKit (CC BY-NC 4.0)"*, and PROJECT.md records the NonCommercial
finding from Phase 29. The audio side has three layers that must not be
conflated:

- The **recordings** are US government works, almost certainly public domain.
- Oyez's **hosting/delivery** carries whatever terms Oyez attaches.
- The **alignment data** — the timings mapping audio to transcript — is Oyez's
  own work product. It is the one input this project cannot cheaply rebuild, and
  the most likely to be restricted.

Forced alignment with a Whisper-class model is a feasible fallback, but it
produces **derived data with an error rate**, which is a line this project has
been careful about. It would need its own decision, not an assumption.

## What to do first, and it costs nothing

**Done, 2026-08-31 — see [[004-argument-as-a-call]]** (`.planning/spikes/`), which
mocks both arrangements against the real rebuttal of this argument, playable, with
synthetic timings so it engages no licensing question. Still unshown to anyone; the
answer is not in yet.

Do not build it. Mock **one frozen moment** of one argument, two ways — grid and
courtroom arrangement — and show them to people alongside Oyez's own player. No
audio, no timings, no licensing question engaged. That tests the actual
hypothesis (that a familiar interface increases engagement — the second of the
two unverified hypotheses behind [[2026-08-28-transcript-style-switcher]]) for
free, and this idea arrived *from* showing work to someone else, which is
evidence the method works.

Related: [[2026-08-29-bionic-reading-investigation]] — same family of question,
presentation-only changes in service of engagement and reading ease.
