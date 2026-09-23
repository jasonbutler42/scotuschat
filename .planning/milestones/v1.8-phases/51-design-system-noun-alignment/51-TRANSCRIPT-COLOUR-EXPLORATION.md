---
created: 2026-08-28
status: open — operator decision required on §3
answers: 51-TRANSCRIPT-NEXT-ROUND.md item 2
binds: D-02 (two-layer tokens), D-19 (Style B2), P-03 (side ≠ importance)
---

# Transcript — speaker colour differentiation

Item 1 of `51-TRANSCRIPT-NEXT-ROUND.md` is fixed and committed (`22ab9a5f3`).
This document answers item 2.

All numbers below are Playwright measurements at 390×844 against
`anderson-v-liberty-lobby-inc`, not estimates. Colour maths is CIE L\* and
WCAG contrast, computed, not eyeballed.

---

## 1. The premise does not survive measurement

The framing was: *colour-coding is what lets Telegram push bubbles wider, so
if we encode speaker identity in colour we can reclaim the ~4 characters the
88% cap spends on opposite-side breathing room.*

The 88% cap is not spending anything on breathing room. It never was.

| `--bubble-max-width` | bench bubble | advocate bubble | **edge offset between sides** | avg chars/line |
|---|---|---|---|---|
| 88% (current) | 52 → 329.2 | 45.8 → 323.0 | **6.2px** | 25.3 |
| 100% | 52 → 367.0 | 8.0 → 323.0 | **44px** | 31.3 |

At 88% a bench bubble and an advocate bubble occupy *the same horizontal band*
— they differ by 6.2px on each edge, which is invisible. The 44px rail already
consumed the offset; capping both stacks at 88% then narrows both sides by the
same amount and creates no differential at all.

So the cap is costing **6 characters per line (−19%)** and buying **nothing**.

Worse for the premise: going to 100% *increases* the side signal, from 6.2px to
the full 44px, because the bubble edges finally coincide with the stack edges
and the rail offset becomes visible on both sides. Screenshots in
`.playwright-mcp/width-88.png` and `width-100.png`.

**Conclusion: the width change stands on its own and needs no colour work.
Set `--bubble-max-width: 100%` at the mobile breakpoint.** That is a separate,
independently-justified change, and it should not be held hostage to the colour
decision.

The Telegram comparison also doesn't hold up on inspection. Telegram's
two-colour scheme is *self vs. other* — one of the two parties is the reader.
There is no reader in a transcript, so the mechanism doesn't transfer. What
actually lets Telegram run tight is the tail (explicitly out of scope) and the
absence of an avatar rail in 1:1 chats. In *group* chats — the structurally
analogous case — Telegram shows avatars, colours the **sender name** from a
fixed per-sender palette, and gets no extra width from it.

---

## 2. A defect found while measuring: the current side colours are not equal weight

P-03 requires side to be a neutral factual attribute, never importance. The
existing tokens fail that on luminance:

| token | value | CIE L\* | contrast vs `--color-surface` |
|---|---|---|---|
| `--color-side-bench` | `--slate-400` `#94a3b8` | 66.5 | 5.71 : 1 |
| `--color-side-advocate` | `--blue-300` `#93c5fd` | **78.0** | **8.11 : 1** |

An 11.5-point L\* gap and 1.42× the contrast. The advocate side is measurably
brighter, and it is brighter on the avatar fill — ~800px² per avatar, 164
avatars on this page — not just on a text label. Bench is also the only
*achromatic* one, which reads as the unmarked/default case against a chromatic
advocate.

This is owed regardless of which option below is chosen. Every option fixes it.

---

## 3. Three options — operator's call

A palette solved at **CIE L\* = 78 for every slot** (matching the existing
`--blue-300`), OKLCH chroma 0.09, hue-only variation. Every slot lands at
8.06–8.15 : 1 against `--color-surface` and 10.40–10.52 : 1 against
`--color-bg` — within 1% of each other. That equality is the P-03 argument,
and it is constructed, not hoped for.

| slot | hue° | hex | L\* | vs surface |
|---|---|---|---|---|
| blue | 250 | `#94c6f9` | 78.2 | 8.15 |
| cyan | 210 | `#73cede` | 77.9 | 8.09 |
| teal | 175 | `#7bd1ba` | 78.1 | 8.13 |
| green | 145 | `#99ce9a` | 78.0 | 8.12 |
| yellow-green | 115 | `#bdc783` | 78.1 | 8.12 |
| amber | 85 | `#dcbe7d` | 78.2 | 8.15 |
| orange | 55 | `#f1b48b` | 78.0 | 8.11 |
| red | 25 | `#f9aea7` | 78.0 | 8.11 |
| pink | 355 | `#f4acc7` | 77.8 | 8.06 |
| violet | 310 | `#d6b4f0` | 78.0 | 8.11 |
| indigo | 280 | `#b6bcfc` | 77.8 | 8.07 |
| slate (neutral) | 250 @ C 0.015 | `#b5c3d1` | 78.0 | 8.14 |

Note `blue 250 → #94c6f9` is within 0.2 L\* of the shipped `--blue-300`. The
ramp is an **extension of the existing token**, not a replacement for it — the
advocate side keeps the colour you have been looking at.

### Option A — per-speaker hue, side kept as a hue family
`.playwright-mcp/variant-A.png`

Bench draws from the warm arc (amber, orange, red, pink, violet); advocates
from the cool arc (blue, teal, cyan). Each speaker is individually
identifiable **and** side survives in colour.

- **For:** solves the real problem — five justices currently share one colour,
  so the sticky avatar's whole job (re-identification during scroll) is served
  only by 2-letter initials. Keeps the bench/advocate colour axis you have now.
- **Against:** warm-for-bench carries connotation. At equal L\* and chroma it is
  defensible as a neutral factual attribute, but "the justices are the hot
  colours" is a reading someone could make, and the apolitical constraint is a
  hard one. Swapping the arcs (cool bench / warm advocates) inverts the
  association you already ship.

### Option B — per-speaker hue, no side family
`.playwright-mcp/variant-B.png`

Hues assigned around the wheel by roster index, ignoring side. Side is carried
by position alone (alignment + rail side + the 44px offset).

- **For:** the most defensible under P-03, and arguably *more* apolitical than
  what ships today: it stops making bench-vs-advocate the primary colour axis
  and treats every speaker as a peer with their own hue — which is exactly the
  "identical schema, depth, and treatment" rule. No connotation to argue about.
- **Against:** loses side-from-colour. Your one constant across the project is
  bench on one side, advocates on the other — that constraint is about
  *position*, and position is untouched, but colour would no longer reinforce
  it. At 100% width the 44px offset carries it well (see §1); at 88% it would
  not.

### Option C — keep two colours, fix the luminance only
`.playwright-mcp/variant-C.png`

`--color-side-bench` → `#b5c3d1` (slate at L\* 78). Advocate unchanged.
Shoots down Idea 2 entirely; fixes §2.

- **For:** smallest change, zero new architecture, zero new risk. Looks like
  what ships today.
- **Against:** leaves five justices sharing one colour. Doesn't help
  re-identification at all.

---

## 4. Implementation notes that apply to A and B

**Determinism, not randomness.** Your framing was *"they wouldn't even need to
be consistent from argument to argument; just varied within an argument."* Do
not implement that with an RNG or a hash — `ChatBubble` is keyed by
`u.sequence` and reused across navigation, so a random assignment would produce
the same class of stale-value bug as the prop-capture defect. Assign
`slot = index in the argument's speaker roster` (the route already builds that
roster for the header). Deterministic within a page load, stable across
re-render and navigation, varied within an argument, free to differ between
arguments — exactly what you asked for, with no randomness anywhere.

**Token architecture (D-02).** A *fixed, finite* palette is expressible as
static tokens: 11 `primitive` entries feeding `--color-speaker-1 … -n` semantic
roles. A *generated* palette could not be, and that would have been a real
argument against Idea 2 — adopting a fixed ramp is what removes it.

**Unresolved speakers** (`person_id` null) get a dedicated
`--color-speaker-unresolved` neutral, not a palette slot. Different kind of
thing; should look like one.

**Colour is redundant, never the carrier.** Initials are inside every avatar
and the name is on the first bubble of every run. That is the honest
colour-blind-safety answer: at 11 hues and one L\*, some pairs will collapse
under deuteranopia, and it doesn't matter because hue is an accelerator, not
the identifier.

**Where the colour goes: avatar fill + speaker-name label only.**

**Not the bubble fill — recommend rejecting that outright.** It is the largest
visual-weight channel on the page (~277px × N per bubble vs. a 14px label), and
the two sides are not symmetric in the data: bench utterances are short
interjections, advocate utterances run thousands of characters. Even at equal
per-pixel weight, a tinted advocate fill would dominate total page area. That
is the P-03 failure mode, and it is not hypothetical. A 2–3px coloured hairline
on the bubble's own side is the middle option if the label proves too subtle.

---

## 5. Recommendation

1. **`--bubble-max-width: 100%` on mobile.** Independently justified by §1.
   +6 chars/line and a 7× stronger side signal. Do this whatever else happens.
2. **Fix the luminance imbalance in §2.** Owed under P-03 either way.
3. **On colour: Option B**, applied to avatar fill and speaker-name label only.
   It fixes the five-justices-one-colour problem, it is the cleanest read of
   P-03, and §1 shows position now carries side on its own — which is what made
   Option B's one real cost affordable.

If the bench/advocate colour axis is something you want to keep visible, Option
A is the fallback and everything in §4 applies unchanged.
