---
created: 2026-08-29
kind: investigation
source: operator, while specifying the reading-layer variant switcher
resolves_phase: null
priority: low
---

# Investigate bionic reading as a reading-layer option

Operator raised this while asking whether the variant switcher should carry a
font axis: *"if we do this for real instead of just for testing, font would be a
very real thing. I'm talking about bionic reading. I know there's a licensing
cost but I think they have deals for non-profits."*

Filed to investigate, not to schedule. Font was explicitly deprioritised for the
switcher's first cut; this is the reason to come back to it.

## What it is

Bolding the leading characters of each word ("fixation points") on the theory
that the eye completes the rest, so the reader's fixations get shorter. Renders
as `**Sup**reme **Co**urt`.

## The three questions, in the order they should be answered

**1. Does it work?** Answer this BEFORE the licensing question, because a
negative answer makes the licensing question moot. This is the part most likely
to be assumed rather than checked. As of the last time I have reliable
information, the published evidence was **not** favourable: multiple controlled
studies found no significant improvement in reading speed versus plain text, and
at least some found it slower. The distinction that matters for this project is
**preference vs. performance** — subjective reports of reduced effort (notably
from some dyslexic readers) can be real even where speed does not improve. Since
a founding purpose here is reading *ease*, a preference-only benefit might still
be the right thing to ship. But that should be a decision made knowingly, not by
assuming a speed claim that the literature does not support.

Note this is exactly what the variant switcher now makes testable in-house: a
bionic axis alongside the existing ones would let the same readers compare
directly, on real transcripts, without any licensing commitment.

**2. What does it actually cost, and is a licence even required?** Two separable
things get conflated:
- **"Bionic Reading"** is a trademarked product from a Swiss company with a
  commercial API/SDK and paid licensing. Verify current terms and the
  non-profit/educational arrangement at the source — my information on their
  pricing is not current enough to plan against, and this project's status
  (personal, non-commercial, public-domain source material) may or may not
  qualify.
- **Prefix-bolding as a technique** is implemented by several open-source
  libraries (e.g. `text-vide` on npm) that do not use the brand or the API.
  Whether that route is clear depends on the patent position in the relevant
  jurisdiction, not on the trademark — the trademark only stops you calling it
  "Bionic Reading". Worth a real answer before assuming the free route is safe.

**3. What would it cost us to build?** Low, and lower than it looks:
- It is a pure render-time transform on `utterance.text` — split into words,
  wrap a prefix of each in `<b>`. Nothing is stored, so **raw PDFs and derived
  rows are untouched** and the transform is regenerable/reversible by definition.
- It slots straight into the variant switcher as a third axis. The switcher's
  contract is "a variant is nothing but a token redefinition", and this would be
  the first axis to break it — bolding needs markup, not CSS. Decide whether to
  widen that contract or give this axis its own mechanism.

## Constraints it must satisfy

- **P-03 / apolitical:** the transform must apply identically to every speaker.
  It is presentational and speaker-blind, so this is easy to satisfy — but it
  must not become configurable per side or per speaker.
- **Not derived insight.** Prefix-bolding is typography, not summarisation,
  sentiment or emphasis-of-meaning. It stays on the right side of the
  no-derived-insight constraint precisely because the rule is mechanical and
  content-blind. If any variant of it ever selected words by *importance*, that
  would cross the line.
- **Measure.** Bolding changes glyph widths and therefore line breaking. The
  characters-per-line numbers in `51-TRANSCRIPT-COLOUR-EXPLORATION.md` were
  measured on regular weight and would need re-measuring under this axis.
- **Screen readers and copy/paste.** `<b>` mid-word splits text nodes. Verify
  that selecting and copying a passage yields clean text and that assistive tech
  does not read the fragments separately.

## Where to pick this up

`app/src/lib/public/VariantSwitcher.svelte` — the axis list is a single array;
`app/src/lib/public/ChatBubble.svelte` — where the utterance text renders.
Related: [[2026-08-28-transcript-style-switcher]].
