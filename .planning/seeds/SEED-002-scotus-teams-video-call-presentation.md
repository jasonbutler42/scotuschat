---
id: SEED-002
status: dormant
planted: 2026-08-29
planted_during: 51-design-system-noun-alignment
trigger_when: next milestone planning (/gsd-new-milestone scan)
scope: large — sibling project, not a phase of scotuschat
---

# SEED-002: "SCOTUS Teams" — oral arguments presented as a video call

## The idea, as the operator framed it

Oyez already has the audio synchronised to the written transcript. Use that data
to build an interface that looks like a **video call**: multiple windows, one per
participant, and whoever is speaking takes centre stage. Oyez's own listening
experience already uses an almost identical pattern — theirs just doesn't look
like a Teams call.

**The operator's argument for why it belongs in this family:** *"you aren't
changing the content at all, you're just presenting it in a different format."*

That is exactly right, and it is the load-bearing reason this is a sibling of
scotuschat rather than an unrelated product. The whole apolitical constraint —
identical schema, depth and treatment for every speaker; no derived insight, no
summaries, no sentiment, no statistics — survives a presentation change
untouched, because a presentation change adds no claims. Chat bubbles and a call
grid are two renderings of the same unmodified record.

## Provenance worth noting

This idea came from **showing the work to someone else**. It arrived in the same
conversation as the variant switcher, which was built so that people other than
the operator could react to the reading layer. The switcher's payoff showed up
before the switcher had been used. Worth remembering when weighing how much
outside exposure is worth on a project with an audience of one.

## Why it is a sibling, not a feature of scotuschat

Different medium (audio-led rather than text-led), a different core data
dependency (timing alignment), and different failure modes (buffering, drift,
autoplay policy). Folding it into scotuschat would compromise a read-only text
experience that is deliberately quiet and offline-friendly. Build it as its own
thing that reuses the pipeline.

## What is reusable

The expensive half is already built: ingest, parse, resolve, person resolution
and identity, speaker photos (`photo_url_full` with an initials fallback), side
classification, and run grouping (consecutive-utterance grouping — the same
structural unit a call UI needs to decide when to switch the active tile).

What is NOT reusable: everything about playback, timing, and synchronisation.

## The three things to answer before committing

**1. Licensing — this is the one that can kill it.** The app already carries
*"Historical transcript imported from Oyez.org via Cornell ConvoKit (CC BY-NC
4.0)."* Non-commercial only, and that governs the text we already use. The audio
side is a **separate and unresolved** question with three distinct layers that
must not be conflated:
- The **recordings** are US government works and are almost certainly public
  domain.
- Oyez's **hosting/delivery** of them carries whatever terms Oyez attaches.
- The **alignment data** — the timings that map audio to transcript — is Oyez's
  own work product, and it is the single thing this project cannot build
  cheaply itself. It is both the most valuable input and the most likely to be
  restricted.

Get a real answer on layer three first. Everything else is wasted effort if the
timings are not usable.

**2. The P-03 problem, which is subtler here than it looks.** A call UI puts the
active speaker centre stage — that is a prominence signal, which is the exact
thing P-03 forbids encoding. The defensible reading is that it is *factual and
transient*: the person is in fact speaking, and the emphasis rotates to whoever
speaks next, the same logic that already justifies the sticky rail avatar. So
the mechanism is probably fine. **The risk lives in the static properties
instead**, and those need to be decided deliberately:
- Tile **order** must not encode seniority, side, or importance.
- Tile **size** must be identical when nobody is speaking.
- No participant may be permanently larger, centred, or first.

**3. Photo coverage will be lopsided, and it matters more here.** Justices have
good portrait coverage; advocates almost certainly do not. In scotuschat that
degrades to a 32px initials circle and is barely noticeable. In a grid of
face-sized tiles, a bench of photographs facing a row of initials-blanks reads
as a status difference — which is a P-03 failure produced by nothing but data
coverage. Audit advocate photo coverage early; it may force a deliberate choice
to use initials for *everyone*.

## Why it might be worth more than it looks

The deferred reader-facing style switcher
([[2026-08-28-transcript-style-switcher]]) rests on two unverified hypotheses:
that different readers want different visuals, and that matching a familiar
interface increases engagement and discovery. This is the second hypothesis at
full strength — a video-call metaphor is far more familiar to far more people
than any chat client, and the material is inherently a conversation between
identifiable people. If the hypothesis is true anywhere, it is true here.

Related: [[2026-08-29-bionic-reading-investigation]] — same family of question
(presentation-only changes in service of accessibility and engagement).
