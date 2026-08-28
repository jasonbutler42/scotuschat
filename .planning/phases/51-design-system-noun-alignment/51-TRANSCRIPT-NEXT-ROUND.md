---
created: 2026-08-28
status: open — for discussion after /clear
source: operator, from a zoomed screenshot of the live transcript on iPhone
binds: plan 51-07 follow-up (transcript reading layer, D-19 Style B2)
---

# Transcript — next round of operator feedback

Captured verbatim-in-substance and parked. **Not yet acted on.** Read this plus
`51-DESIGN-DECISIONS.md` §§ "Transcript style (D-19…)" and "D-19 amendments"
before doing anything.

---

## 1. DEFECT — bench/advocate margin asymmetry (fix, not a design question)

Operator: *"Notice the discrepancy between in the margins between bench and
advocate? Bench is wider. Make that the same as for advocate."*

**Target: bench matches advocate — i.e. tighten bench to the advocate value.**
Advocate is the correct one; do not loosen advocate to match bench.

From the operator's zoomed screenshot (~3.4x CSS scale), measuring the
horizontal gap between the avatar and its own bubble:

| side | gap in screenshot px | ≈ CSS px |
|---|---|---|
| bench (WB, avatar left) | ~40 | **~12** |
| advocate (DB, avatar right) | ~15 | **~4** |

`--transcript-rail-gap` is `--space-xs` (4px) on mobile, so **advocate is
rendering the intended value and bench is roughly 3x it.**

Not yet root-caused. Prime suspect: the avatar's horizontal placement *inside*
the 40px rail column differs by side. The rail is
`display:flex; flex-direction:column` with no `align-items`, so children default
to `stretch`; the avatar `<button>` centres a 32px circle in that stretched box,
which *should* leave 4px on each side symmetrically. Something is breaking that
symmetry — possibly the `order` swap, possibly the button's own box.

**Verify with Playwright, not by eye** — this is exactly the class the automated
signals miss. See [[playwright-mcp-is-the-missing-browser]] in memory:
`browser_resize(390,844)` then `getBoundingClientRect()` on avatar vs bubble for
both a `Bench:` and an `Advocate:` row, and compare the two gaps directly.

---

## 2. EXPLORATION — speaker colour differentiation (operator wants options, not a decision)

Operator's framing: *"One other thing telegram does that lets them get away with
using more horizontal space is that they color code you vs other speakers. That
makes sense when only one person is on the advocate side but I want to explore
that."*

The connection to measure is the point: colour-coding is what lets Telegram push
bubbles wider without losing at-a-glance "who is speaking", because hue does the
work that whitespace was doing. If we can encode speaker identity in colour, we
may be able to reclaim the ~4 remaining characters per line that the 88% cap is
currently spending on opposite-side breathing room.

Two ideas to **either explore or shoot down** — operator explicitly invited
either answer:

**Idea 1 — two colours/treatments differentiating bench vs advocate.**

**Idea 2 — random colour treatment per speaker.** Operator: *"They wouldn't even
need to be consistent from argument to argument; just varied within an
argument."*

### Hard constraint that governs both — read before proposing anything

P-03 / the UI-SPEC cross-cutting rule: *side may be encoded as a neutral factual
attribute; it may never be encoded as importance.* Justices and advocates must
carry identical type size, weight and emphasis. Colour is currently doing exactly
this correctly — `--color-side-bench` and `--color-side-advocate` differ in hue,
not in weight or prominence.

Specific risks to address for each idea rather than hand-wave:

- **Idea 1** is closest to what already ships (avatar fill + speaker-label
  colour already differ by side). The open question is whether to extend it to
  the *bubble* — a bubble-fill difference is a much larger visual weight signal
  than a label colour, and one side reading as "louder" would fail P-03. Any
  proposal needs a contrast/luminance argument, not just a hue choice.
- **Idea 2** must not produce a palette where some speakers read as more
  prominent than others — random hues at equal luminance/saturation is the
  defensible version; random hues at varying lightness is not. Also needs:
  determinism within a page load (the same speaker cannot change colour on
  re-render or navigation — note `ChatBubble` is keyed by `u.sequence` and
  reused), a legibility floor against `--color-surface`, and a colour-blind-safe
  spread. And it must degrade: an unresolved speaker (`person_id` null) needs a
  defined treatment.
- **Both** interact with D-02's two-layer token architecture. New colours must
  enter as `primitive` entries feeding named `semantic` roles, never as raw hex
  in a component. If a generated/random palette can't be expressed as static
  tokens, say so plainly — that is a real argument against Idea 2.
- **Both** must stay clear of the apolitical constraint's spirit: nothing may
  make one speaker class scan as more significant. A per-speaker palette is
  arguably *more* neutral than a two-colour side split, since it stops encoding
  the bench/advocate distinction as the primary visual axis. Worth raising.

### Also worth putting on the table

Whether colour differentiation would let the mobile `--bubble-max-width` go from
88% toward 100%, recovering ~4 characters per line. That is the actual payoff and
should be quantified with Playwright before/after, not asserted.

### Explicitly out of scope

The Telegram speech-bubble tail. Operator: *"I think that's too whimsical for
this project so ignore it."* Already honoured; do not reintroduce it. (Note it is
also what lets Telegram run a tighter avatar gap than we can — the tail visually
connects bubble to avatar.)

---

## State at the time this was parked

**Committed:**
- `1a94f5920` — advocate bubbles stranded from their avatar (86px → 8px); sticky
  avatar hidden behind the opaque fixed `MobileNavBar` (`--sticky-bottom-inset`).
- `59167733e` — five prop-captured `const`s in `ChatBubble` converted to
  `$derived`.

**Uncommitted, deliberately:**
- The measure work: `--transcript-pad-x`, `--transcript-rail-gap`,
  `--bubble-max-width`, `--bubble-pad-x` in `app.css` (mobile overrides under the
  same 768px breakpoint `MobileNavBar` uses), consumed by the route and
  `ChatBubble`. Took measure from **17 → 26 characters/line** in Chromium/Linux
  (expect ~30 on iOS, where `system-ui` resolves to the narrower SF Pro).
  Held back because item 1 above may change these values.
- `app/vite.config.ts` — `allowedHosts: ['.trycloudflare.com']` gated behind
  `DEV_TUNNEL=1`. **Revert when tunnel testing ends.**

**Type size: settled, do not revisit without new information.** Measured
18px → 26 chars, 17px → 27, 16px → 29. Dropping 18→16 costs 11% of the type for
3 characters. Type was never the lever; width allocation was. Telegram runs 17pt
and gets ~35 because of layout, not type size.

**Live stack:** `scripts/dev-start.sh` running (uvicorn :8000, vite :5173),
cloudflared quick tunnel at `https://put-uni-grain-grocery.trycloudflare.com`.
Both die with the session; the tunnel hostname is not stable across restarts.

**Phase 51 progress:** 8/10 plans complete through Wave 4. Plans **51-09**
(token conversion sweep across ~25 admin files + the D-08 surfaced-artifact
register) and **51-10** (operator rulings + end-to-end walkthrough) are parked
pending this transcript work, because 51-09 rewrites inline styles broadly and
would churn what is being reviewed.

**Only one published argument exists** in the dev DB (`Anderson v. Liberty
Lobby, Inc.`, term 1985, 157 utterances, longest 4,125 chars). It has **zero
multi-utterance runs**, so the D-19 run-grouping and 2px grouped-corner rules are
correct but *dormant* and cannot be visually verified against this data. They
first become visible when the deferred paragraph-splitting work lands — see
`.planning/todos/pending/2026-08-28-transcript-long-utterance-paragraph-splitting.md`.
