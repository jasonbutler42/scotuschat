# Design System Reference

**Rewritten:** 2026-08-28 — this file now documents the *result* of Phase 51 plan 51-03
(design tokens established as the visual foundation, D-01/D-02/D-03), not a snapshot of the
July 2026 status quo. The July 2026 version of this document made two claims that were already
stale by the time Phase 51 started: it said the project carried no Tailwind dependency (Tailwind
*was* a listed `devDependency`, just unused as utility classes — see below) and that only three
sizes and two weights were in use (nine sizes and three weights actually were, by the time this
phase began). Both claims are corrected below against the current codebase, not carried forward.

**Source of truth today:** `app/src/app.css` `:root`. As of this rewrite it declares a complete
two-layer CSS custom-property token set (14 primitives + 37 semantic names). Components still
style themselves via inline `style="..."` attributes — that mechanism is unchanged and is not
CSS-in-JS or a component-scoped `<style>` block — but as of the plan-51-09 sweep, every value
inside those `style=` attributes is a `var(--token)` reference rather than a literal. This
document exists so the token set doesn't have to be re-derived by hand; `app.css` itself remains
the actual source of truth.

**Scope:** Covers both the admin interface (`/admin/*`) and the public site
(`/arguments/**`). Both surfaces draw from the same token set — public uses the full range
(caption through display, `--space-4xl`), admin uses the small end (caption/body/heading,
`space-xs` through `space-3xl`). See `lib/primitives/`, `lib/public/`, `lib/admin/` directory
split below.

---

## Dependencies (verified against `app/package.json`, 2026-08-28)

No CSS framework, CSS-in-JS library, or utility-class framework is a dependency of this project.
`app/package.json` `devDependencies` after Phase 51 plan 51-03 Task 1: `@sveltejs/adapter-node`,
`@sveltejs/kit`, `@sveltejs/vite-plugin-svelte`, `@types/node`, `svelte`, `svelte-check`,
`typescript`, `vite`. `dependencies`: `bits-ui` (headless focus-managed primitives, used today
only by `SpeakerPopover`, per D-18).

`tailwindcss`, `@tailwindcss/typography`, `postcss`, and `autoprefixer` were removed in Phase 51
plan 51-03 (D-01): the dependency was installed and configured but used in exactly 3 places (the
three `@tailwind` directives in `app.css`) against 877 inline `style=` attributes at the time of
removal — cost with no benefit. Tailwind's `preflight` reset was load-bearing even though no
utility class was in use, so `app.css` now carries an explicit base reset (margin zeroing on
headings/`p`/`figure`/`blockquote`/`dl`/`dd`, form-control normalization, anchor color/decoration
inheritance, media element sizing) in its place.

---

## Token architecture (D-02)

Two layers, both CSS custom properties declared in `app/src/app.css` `:root`:

- **Layer 1 — primitive palette (14 tokens).** Raw hex values (`--slate-950` through
  `--red-500`). Private to the token file — never referenced directly by a component.
- **Layer 2 — semantic roles (37 tokens: 16 colour + 7 spacing + 5 size + 5 line-height + 2
  weight + 2 touch-target).** Every semantic entry is a `var(--primitive)` reference, never a
  second copy of a hex. Component code references semantic names only — `var(--color-surface)`,
  never `var(--slate-800)`.

**Why two layers, not one:** a flat single-layer set would make a future light theme a full
rewrite of every component reference. The two-layer structure makes adding a light theme later a
contained addition — a second value set aliased through the same semantic names — because the
semantic name a component references never has to change. Only dark values ship in Phase 51; the
structure is what carries the light theme later, not a half-built implementation now.

One semantic-name pair intentionally shares a primitive rather than being collapsed to one name:
`--color-accent` and `--color-side-advocate` both resolve to `--blue-300`. The overlap is
pre-existing in the codebase, not a new decision — keeping the names distinct means a future
divergence (e.g. giving advocate-side identity its own colour independent of the accent colour)
is a one-line change, not an archaeology exercise across every call site.

`--color-side-bench` used to be the second such pair, sharing `--slate-400` with
`--color-text-secondary`. **It no longer does, and the reason is a P-03 fix, not a preference:**
`--slate-400` (L\* 66.5, 5.71:1) against `--blue-300` (L\* 78.0, 8.11:1) made the advocate side
measurably brighter than the bench across 164 avatar fills — side encoded as prominence, which
P-03 forbids. Bench now resolves to `--l78-slate`, on the same L\* 78 as advocate. Any future
change that returns these two names to a shared value re-introduces that violation.

## Colors

### Primitive palette — base (14)

| Primitive | Hex |
|---|---|
| `--slate-950` | `#0f1117` |
| `--slate-800` | `#1e293b` |
| `--slate-700` | `#334155` |
| `--slate-400` | `#94a3b8` |
| `--slate-300` | `#e2e8f0` |
| `--slate-200` | `#cbd5e1` |
| `--blue-300` | `#93c5fd` |
| `--amber-600` | `#d97706` |
| `--amber-400` | `#fbbf24` |
| `--amber-300` | `#fcd34d` |
| `--green-400` | `#4ade80` |
| `--violet-400` | `#a78bfa` |
| `--orange-400` | `#fb923c` |
| `--red-500` | `#ef4444` |

### Admin lifecycle primitives (9)

Carried over verbatim from the badge helpers they used to be hardcoded in — D-08 was a refactor,
not a redesign. Unlike the speaker ramp below these need not sit at one luminance: P-03 governs
how *speakers* are treated, and a pipeline state is not a speaker.

| Primitive | Hex |
|---|---|
| `--sky-400` | `#38bdf8` |
| `--emerald-400` | `#34d399` |
| `--yellow-400` | `#facc15` |
| `--red-400` | `#f87171` |
| `--teal-400` | `#2dd4bf` |
| `--fuchsia-400` | `#e879f9` |
| `--rose-400` | `#fb7185` |
| `--slate-600` | `#475569` |
| `--slate-500` | `#64748b` |

### Per-speaker ramp primitives (12)

**Every entry is solved to CIE L\* 78 at OKLCH chroma 0.09, so they vary in hue and in nothing
else** — 8.06–8.15:1 against `--color-surface` and 10.40–10.52:1 against `--color-bg`, within 1%
of each other. That equality is not decoration; it is what makes a per-speaker palette legal
under P-03, because no speaker may read as louder than any other. The L\* is in the name so a
thirteenth entry cannot be added casually: solve it to 78 or it does not belong here.
`--l78-blue` is within 0.2 L\* of `--blue-300`, so the advocate side keeps the colour it shipped.

| Primitive | Hex |
|---|---|
| `--l78-blue` | `#94c6f9` |
| `--l78-orange` | `#f1b48b` |
| `--l78-teal` | `#7bd1ba` |
| `--l78-pink` | `#f4acc7` |
| `--l78-yellow-green` | `#bdc783` |
| `--l78-indigo` | `#b6bcfc` |
| `--l78-red` | `#f9aea7` |
| `--l78-cyan` | `#73cede` |
| `--l78-amber` | `#dcbe7d` |
| `--l78-violet` | `#d6b4f0` |
| `--l78-green` | `#99ce9a` |
| `--l78-slate` | `#b5c3d1` |

### Semantic roles — the 60/30/10 split

| Role | Token | Usage |
|---|---|---|
| Dominant (60%) | `--color-bg` (`var(--slate-950)`) | Page background, everywhere. |
| Secondary (30%) | `--color-surface` (`var(--slate-800)`) | Cards, header bar, nav, table row default background. |
| Accent (10%) | `--color-accent` (`var(--blue-300)`) | Primary CTA buttons/borders (Save, Publish, Create), all inline/nav links, `:focus-visible` outline, active-tab indicator. **Never** status badges, table headers, muted text, or general emphasis — this discipline is pre-existing and must survive every future conversion. |
| Destructive | `--color-destructive` (`var(--red-500)`) | Delete buttons/borders, error text/messages, delete-confirmation copy — never anything else. |

### Additional semantic roles (7) — outside the 60/30/10 split but required

| Token | Value | Usage |
|---|---|---|
| `--color-border` | `var(--slate-700)` | Card/input borders, table dividers, header bottom-border. |
| `--color-text-primary` | `var(--slate-300)` | Headings, body copy, input values. |
| `--color-text-secondary` | `var(--slate-400)` | Field labels, meta/secondary text, table header text. |
| `--color-side-bench` | `var(--l78-slate)` | Bench/justice avatar fill + side indicator only. On the L\* 78 ramp so it cannot read dimmer than the advocate side (P-03) — see the note above. |
| `--color-side-advocate` | `var(--blue-300)` | Advocate avatar fill + side indicator only. |
| `--color-stage-accent` | `var(--amber-600)` | Stage-direction bracketed text (e.g. `[Laughter]`) only. |
| `--color-stage-text` | `var(--amber-300)` | Stage-direction body text only. |

### Admin-only lifecycle status colors (5) — never rendered on the public site

| Token | Value | Usage |
|---|---|---|
| `--color-status-published` | `var(--green-400)` | Published status badge (admin only). |
| `--color-status-draft` | `var(--violet-400)` | Draft status badge (admin only). |
| `--color-status-unpublished` | `var(--orange-400)` | Unpublished status badge (admin only). |
| `--color-status-warning` | `var(--amber-400)` | "Missing tenure" and similar attention-needed inline warnings (admin only). |
| `--color-status-archived` | `var(--slate-200)` | Archived pipeline-run badge (admin only). |

None of the five status colors, and no trust-tier concept from Phases 48/49, may reach the
public site. Public shows published-or-not, nothing more — enforced by
`api/tests/test_trust_public_leak_ban.py`. Status colors are never reused for non-status meaning
and are never applied to non-admin surfaces.

### Speaker identity slots (12)

Assigned by the speaker's index in an argument's roster — **not** by side, **not** by a hash, and
**not** randomly (see the route's `speakerColor`). Ordered so consecutive slots sit far apart in
hue, because consecutive slots go to speakers who alternate on screen.

| Token | Value | Usage |
|---|---|---|
| `--color-speaker-1` | `var(--l78-blue)` | Roster slot 1. |
| `--color-speaker-2` | `var(--l78-orange)` | Roster slot 2. |
| `--color-speaker-3` | `var(--l78-teal)` | Roster slot 3. |
| `--color-speaker-4` | `var(--l78-pink)` | Roster slot 4. |
| `--color-speaker-5` | `var(--l78-yellow-green)` | Roster slot 5. |
| `--color-speaker-6` | `var(--l78-indigo)` | Roster slot 6. |
| `--color-speaker-7` | `var(--l78-red)` | Roster slot 7. |
| `--color-speaker-8` | `var(--l78-cyan)` | Roster slot 8. |
| `--color-speaker-9` | `var(--l78-amber)` | Roster slot 9. |
| `--color-speaker-10` | `var(--l78-violet)` | Roster slot 10. |
| `--color-speaker-11` | `var(--l78-green)` | Roster slot 11. |
| `--color-speaker-unresolved` | `var(--slate-400)` | A speaker the resolve step could not identify. Its own neutral rather than a slot, because an unidentified speaker is a different *kind* of thing from an identified one. |

### Side-family slots (10)

The alternative palette in which hue still varies per speaker, but the two sides draw from
opposite arcs of the wheel so side survives in colour. Same L\* 78 ramp, so the P-03 equality
holds here too. Reachable only through the variant switcher (see *Transcript variant axes*).

| Token | Value | Usage |
|---|---|---|
| `--color-bench-1` | `var(--l78-amber)` | Bench family, slot 1. |
| `--color-bench-2` | `var(--l78-orange)` | Bench family, slot 2. |
| `--color-bench-3` | `var(--l78-red)` | Bench family, slot 3. |
| `--color-bench-4` | `var(--l78-pink)` | Bench family, slot 4. |
| `--color-bench-5` | `var(--l78-violet)` | Bench family, slot 5. |
| `--color-bench-6` | `var(--l78-yellow-green)` | Bench family, slot 6. |
| `--color-advocate-1` | `var(--l78-blue)` | Advocate family, slot 1. |
| `--color-advocate-2` | `var(--l78-teal)` | Advocate family, slot 2. |
| `--color-advocate-3` | `var(--l78-cyan)` | Advocate family, slot 3. |
| `--color-advocate-4` | `var(--l78-green)` | Advocate family, slot 4. |

### Trust tier and review state (10) — admin only

The two admin lifecycle scales the D-04 conversion surfaced (`51-ADMIN-ARTIFACTS.md` A-01…A-08,
ruled 2026-09-01). Admin-only, exactly like `--color-status-*`, and covered by the same P-04 ban
on reaching a public surface. Consumed through `lib/primitives/Badge.svelte`, whose `BadgeTone`
union is the typed vocabulary for these values.

| Token | Value | Usage |
|---|---|---|
| `--color-tier-verified` | `var(--sky-400)` | Trust tier: verified. |
| `--color-tier-trusted` | `var(--emerald-400)` | Trust tier: trusted. |
| `--color-tier-provisional` | `var(--yellow-400)` | Trust tier: provisional. |
| `--color-tier-uncertain` | `var(--red-400)` | Trust tier: uncertain. |
| `--color-review-unreviewed` | `var(--slate-600)` | Review state: unreviewed. |
| `--color-review-needs-review` | `var(--color-status-warning)` | Review state: needs review. Deliberately an alias of the status warning colour — the two mean the same thing to the eye. |
| `--color-review-confirmed` | `var(--teal-400)` | Review state: operator confirmed. |
| `--color-review-edited` | `var(--fuchsia-400)` | Review state: operator edited. |
| `--color-review-discrepancy` | `var(--rose-400)` | Review state: discrepancy. |
| `--color-review-unknown` | `var(--slate-500)` | The fallback branch of a review badge — a state the UI does not recognise. Its own role rather than a reuse of `--color-text-secondary`, because A-09 was exactly the artifact of one value doing both jobs. |

## Typography

Exactly **five semantic steps** and **two weights** — collapsed from the nine raw sizes (11, 12,
13, 14, 16, 18, 20, 28, 32px) and three weights (400/500/600) that had drifted into use by the
time Phase 51 started. There is no `--font-weight-500` token; there is to be no 500 anywhere at
phase end.

| Role | Token | Size | Weight | Line height |
|---|---|---|---|---|
| Caption | `--font-size-caption` / `--line-height-caption` | 14px | `--font-weight-regular` (400) | 1.4 |
| Body | `--font-size-body` / `--line-height-body` | 16px | `--font-weight-regular` (400) | 1.5 |
| Lead | `--font-size-lead` / `--line-height-lead` | 18px | `--font-weight-regular` (400) | 1.6 |
| Heading | `--font-size-heading` / `--line-height-heading` | 20px | `--font-weight-semibold` (600) | 1.2 |
| Display | `--font-size-display` / `--line-height-display` | 32px | `--font-weight-semibold` (600) | 1.2 |

Lead (18px) is reserved for the redesigned public reading layer — transcript utterance body text
and term-list case names. Display (32px) is page-level titles only. Admin draws from the small
end of the scale (caption/body/heading); public draws from the full range.

Font family: `system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`, declared
once in `app/src/app.css` on `:root`, inherited everywhere via `font-family: inherit`.

## Type axes

Two style-axis tokens, added Phase 53 (D-02), following the same "named axis" pattern as the two
`--font-weight-*` tokens above — a component references the axis, never a raw literal:

| Token | Value | Usage |
|---|---|---|
| `--font-style-italic` | `italic` | The "undetermined speaker" bubble label (D-02); the whole-turn inaudible-marker body inside any bubble (D-12/D-13, via `.utterance-body.is-inaudible-marker` — see Styling mechanism below); `StageDirection.svelte`'s room-event body; the advocate `SpeakerPopover` "Coming soon" placeholder. The last two are Phase 51-09-sweep raw `font-style: italic;` literals this phase converts to the token in the same pass — same property, same value, a pixel no-op. |
| `--opacity-muted` | `0.7` | Reduced-emphasis label text — currently exactly one call site, the "undetermined speaker" label (D-02). A named semantic rather than an inline `0.7`, so a future second use references the same value instead of guessing a new one. |

Admin-surface italic literals predate this axis and are out of this phase's scope (unconverted).

## Spacing

Eight steps, all multiples of 4px:

| Token | Value | Usage |
|---|---|---|
| `--space-xs` | 4px | Gap between pills/chips/badges; tight inline flex gaps. |
| `--space-sm` | 8px | Label-to-input gap; gap between inline buttons; table cell horizontal padding. |
| `--space-md` | 12px | Dense padding on admin rows, cells and badges. Added 2026-09-01 — the D-04 conversion found this value in use 153 times, second only to 8px and ahead of 16px, so it was a load-bearing step the scale had no name for. |
| `--space-lg` | 16px | Field-to-field vertical margin within a card; margin between stacked cards. |
| `--space-xl` | 24px | Card internal padding; heading-to-content margin. |
| `--space-2xl` | 32px | Layout gaps between major page regions. |
| `--space-3xl` | 48px | Page content top/bottom padding. |
| `--space-4xl` | 64px | Page-level spacing for the largest public reading surfaces (reserved for the redesigned public listing/transcript vertical rhythm; not required for admin). |

> **The names shifted up on 2026-09-01 when 12px joined the scale.** Every name from
> `md` upward now denotes the value one step below what it used to: old `md` (16px) is
> now `lg`, old `lg` (24px) is now `xl`, and so on. All 695 references in `app/src` were
> remapped in the same commit, and the change was verified to be a pixel-level no-op —
> 409 (file, property, resolved-px) buckets before and after, none changed. Any planning
> document written before that date names the OLD values; read those with care.

**Touch targets:** `--touch-target` (44px, WCAG 2.1 AA) applies to buttons and inputs generally.
`--touch-target-dense` (36px) is the sole exception, for compact per-row inline buttons inside
dense admin tables. This exception is carried forward unchanged from the pre-token system — no
future conversion may introduce a touch target below either of these two named values (P-05).

## Layout geometry (6)

Tokens rather than literals because **measure** — characters per line — is what D-09 actually
cares about, and measure is the product of these four values, not of the type size. At 390px the
desktop values yielded 17 characters per line; comfortable sustained reading is 45–75, and the
operator's reference layout achieves ~35 on the same class of device. The gap was entirely width
allocation, so these tighten on mobile and the type size is left alone.

| Token | Desktop | ≤768px | Usage |
|---|---|---|---|
| `--transcript-pad-x` | `var(--space-xl)` (24px) | `var(--space-sm)` (8px) | Transcript reading-layer horizontal padding. |
| `--transcript-rail-gap` | `var(--space-sm)` (8px) | `var(--space-xs)` (4px) | Gap between the speaker rail and the bubble stack. |
| `--bubble-max-width` | `72%` | `100%` | Bubble cap. At 100% the bubble edges coincide with the stack edges and the rail's offset becomes visible on both edges — the sides read *further* apart, not closer. |
| `--bubble-max-width-undetermined` | `67%` | `93%` | Added Phase 53 (D-01/SPEAKER-01): Treatment D's own bubble cap, `--bubble-max-width` (72%/100%) x 0.928 (the Figma 540:582 ratio), rounded — expressed as `min(var(--bubble-max-width-undetermined), 63ch)` (68ch x 0.928 ≈ 63.1, rounded), the same `min(percentage, ch-cap)` shape as `--bubble-max-width`'s own `68ch` cap. See Transcript variant axes below: `data-width` does **not** redefine this token. |
| `--bubble-pad-x` | `var(--space-lg)` (16px) | `var(--space-sm)` (8px) | Bubble internal horizontal padding. |
| `--sticky-bottom-inset` | `var(--space-sm)` (8px) | `calc(var(--touch-target) + var(--space-sm))` (52px) | How far above the viewport bottom a bottom-anchored sticky element must park to stay visible. Below 768px `MobileNavBar` is `position: fixed; bottom: 0` with an **opaque** background, so anything parked at a plain `--space-sm` is painted underneath it and silently disappears — which is not a sticky failure but reads exactly like one. Consumed by the transcript's sticky rail avatar (D-19). |

> The ≤768px column is a single `@media (max-width: 768px)` block that redefines these five on
> `:root`. Keep that breakpoint in step with `MobileNavBar.svelte`'s own `@media` rule — if the
> bar's visibility threshold or height changes, this must follow.

## Transcript variant axes

An operator-facing switcher (`VariantSwitcher.svelte`) applies data attributes to `<html>`.
Deliberately plain attribute selectors on `:root`, so every axis is independent and composable,
and so **a variant is provably nothing but a redefinition of tokens** — if a variant ever needed
a component change, it would not belong here.

| Attribute | Values | Effect |
|---|---|---|
| `data-colour` | *(unset)* / `family` / `side` | Chooses which of three per-row candidate colours paints. |
| `data-width` | *(unset)* / `88` / `94` / `100` | Redefines `--bubble-max-width`. Applied at every viewport, not just mobile, so the control always does something visible. **Does not** redefine `--bubble-max-width-undetermined` (Phase 53) — under a width variant, Treatment D's ratio to a standard bubble no longer tracks the 0.928 Figma derivation. Recorded here as a known gap, adjustable if a real-browser check under a width variant reads wrong. |

Each speaker-bearing row declares three candidate colours as custom properties — `--speaker-color`
(per speaker, side-blind), `--family-color` (per speaker, opposite hue arcs per side) and
`--side-color` (two colours by side) — and the active variant decides which one paints, through
the `.speaker-fill` / `.speaker-ink` / `.speaker-stroke` classes.

**That decision has to be a rule, not a custom-property indirection.** A declaration like
`--fill: var(--speaker-color)` at `:root` is substituted where it is *declared*, not where it is
*used*, so it resolves against a `--speaker-color` that does not exist at `:root` and inherits
down as invalid. The class rules also mean the painted elements must **not** carry an inline
`background-color` or `color`, which would outrank them.

## Component directory split (D-17)

One token set, two component layers, per the Figma page structure (D-06):

- `app/src/lib/primitives/` — shared, tokens-only components with no public/admin opinion:
  `Button`, `Badge`, `Input`, `Card`.
- `app/src/lib/public/` — reading-optimized components (wider measure, larger type, more air):
  `ChatBubble`, `StageDirection`, `SectionRail`, `TermRow`, `UndeterminedBubble` (Phase 53 — Treatment
  D, the source-unattributed-turn rest state), etc.
- `app/src/lib/admin/` — density-optimized components for the operator surfaces.

One source of truth (the token set above), two expressions of it — public and admin can feel
different from each other without maintaining a second palette.

## Styling mechanism

Inline `style="..."` attributes remain the styling mechanism for this codebase — there is no
component-scoped `<style>` convention in wide use, no CSS-in-JS, and (as of Phase 51 D-01) no
utility-class framework. What changes across Phase 51 is only the *values* inside those
attributes: `style="background-color: #1e293b;"` becomes
`style="background-color: var(--color-surface);"`. The mechanism itself — a plain inline `style`
attribute on the element — is unchanged.

**Exception: `.utterance-body` / `.utterance-body.is-inaudible-marker` (Phase 53, D-12/D-13).**
A global class pair in `app/src/app.css`, sitting beside the `.speaker-fill` / `.speaker-ink` /
`.speaker-stroke` rules for the same reason those are classes rather than inline values: an
element's inline `color` would outrank a class rule, so the one property that must be identical
across two independent components (`ChatBubble.svelte`'s and `UndeterminedBubble.svelte`'s body
`<p>`) has to live in a shared class, not be copy-pasted into two `style=` attributes that could
drift apart. `.utterance-body` sets the ordinary ink (`--color-text-primary`) and style (`normal`);
`.utterance-body.is-inaudible-marker` overrides both to `--color-stage-text` /
`--font-style-italic` when the row's stored `is_inaudible_marker` fact is true. Everything else
about the body paragraph (size, weight, line height, margin) stays inline, unchanged.

---

*This is a living snapshot, not a locked spec — update it if a future phase changes the token
set. Reconciled against `app/src/app.css` on 2026-09-29 (Phase 53 plan 53-03, adding
`--font-style-italic`, `--opacity-muted`, and `--bubble-max-width-undetermined` — D-02/SPEAKER-01):
**35 primitives and 78 semantic tokens**, every one of them documented above, and no token named
here that the CSS does not declare.*

**How to re-check this document.** The contract is bidirectional and mechanical — every token
name in `app/src/app.css` appears here, and every token named here exists in the CSS. Extract the
custom-property declarations from the CSS (the primitive layer above the "Layer 2" comment, the
semantic layer below it) and the custom-property mentions from this file, then diff the two sets.
Check values as well as names — a name-only diff passed this document while one row carried a
superseded value. Four strings here are prose rather than references and are expected in that
diff: `var(--token)` and `var(--primitive)` in the token-architecture section, the wildcard
`--color-status-*`, the hypothetical `--fill:` in the variant-axes explanation, and the sentence
stating that no `--font-weight-500` token exists. The three per-row custom properties `--speaker-color`,
`--family-color` and `--side-color` are declared on transcript rows rather than at `:root`, so
they are documented here but will not appear in a `:root` extraction.

*Drift found and closed on 2026-09-03: 37 semantic tokens and 21 primitives were in the CSS with
no entry here — the whole per-speaker ramp, the side families, both admin lifecycle scales, and
the transcript reading-layer geometry. The Spacing section also said "seven steps" while listing
eight, `--space-md` having joined the scale on 2026-09-01. One documented **value** was wrong
where the name was right: `--color-side-bench` was recorded as `var(--slate-400)` in both the
role table and the two-layer prose, but it resolves to `var(--l78-slate)` — moved there because
the old value made the advocate side measurably brighter than the bench, a P-03 violation. No
token named here is absent from the CSS.*
