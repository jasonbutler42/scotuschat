---
created: 2026-08-31
kind: improvement
source: operator, after a week of using the switcher during design review
resolves_phase: null
priority: low
---

# Harden the variant switcher into something permanent

Operator, 2026-08-31: *"I want to eventually harden it into something more permanent but
it's PERFECT for where I am in the design and build."*

**Do not act on this yet.** It is filed to stop the switcher being either forgotten or
prematurely productionised. It is currently doing its job exactly as built.

## What it is now

`app/src/lib/public/VariantSwitcher.svelte`, added in `563003c84`. A fixed pill at the top
right of the transcript that toggles two axes — colour (per-speaker / warm-cool / two-colour)
and width (100 / 94 / 88%) — by writing `data-*` attributes on `<html>`. Every axis is a pure
token redefinition in `app.css`; the component contains no design decisions of its own. State
lives in the URL (`?c=&w=`) so a variant is a shareable link, applied via `replaceState` so
switching never re-runs load or loses scroll position.

## What "harden" would have to decide

The current build is deliberately a design instrument. Turning it into a product feature is
not a refactor — it is answering questions the instrument version got to dodge:

1. **Who is it for?** Right now: the operator and testers. As a feature it becomes the
   deferred reader-facing style switcher ([[2026-08-28-transcript-style-switcher]]), whose
   two hypotheses are still unverified. Do not harden the mechanism before deciding whether
   the feature is wanted — hardening a control nobody keeps is the expensive mistake here.
2. **Does a chosen variant persist?** URL-only is right for handing someone a link and wrong
   for a reader who wants their preference remembered. Those are different products.
   `localStorage` and URL both existing means deciding which wins on conflict.
3. **Is it gated?** It currently renders unconditionally on the transcript route. A feature
   needs a deliberate answer about whether every visitor sees it; an instrument does not.
4. **Which axes survive?** Some exist purely to settle a question and should be deleted once
   settled — the colour axis in particular, once per-speaker colour is confirmed. A permanent
   switcher offering a variant nobody should choose is worse than no switcher. Axes worth
   considering that were *not* built: bubble chrome (border/flat/no-bubble), type size, line
   height, avatar rail on/off. The first and last test structural questions rather than
   preferences.
5. **Does it become the vehicle for the call view?** [[SEED-002-scotus-teams-video-call-presentation]]
   is scoped as a second *view* of an argument, and the switcher's URL-addressable
   presentation state is the natural mechanism to reach it — but a view is a much bigger unit
   than one of these axes, and the component would need to grow a concept it does not have.

## Why it is cheap to leave alone

Nothing depends on it. It reads no data, owns no state beyond two attributes, and deleting
it would leave the transcript rendering its shipped defaults. That is the property worth
preserving through any hardening: the switcher must stay removable.

Related: [[2026-08-29-bionic-reading-investigation]] — the axis that would break the
"variants are only token redefinitions" contract, since prefix-bolding needs markup.
