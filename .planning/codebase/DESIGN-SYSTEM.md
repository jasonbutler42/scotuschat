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
(caption through display, `--space-3xl`), admin uses the small end (caption/body/heading,
`space-xs` through `space-2xl`). See `lib/primitives/`, `lib/public/`, `lib/admin/` directory
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

Two semantic-name pairs intentionally share a primitive rather than being collapsed to one name:
`--color-accent` and `--color-side-advocate` both resolve to `--blue-300`, and
`--color-side-bench` and `--color-text-secondary` both resolve to `--slate-400`. The overlap is
pre-existing in the codebase, not a new decision — keeping the names distinct means a future
divergence (e.g. giving advocate-side identity its own colour independent of the accent colour)
is a one-line change, not an archaeology exercise across every call site.

## Colors

### Primitive palette (14)

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

### Semantic roles — the 60/30/10 split

| Role | Token | Usage |
|---|---|---|
| Dominant (60%) | `--color-bg` (`var(--slate-950)`) | Page background, everywhere. |
| Secondary (30%) | `--color-surface` (`var(--slate-800)`) | Cards, header bar, nav, table row default background. |
| Accent (10%) | `--color-accent` (`var(--blue-300)`) | Primary CTA buttons/borders (Save, Publish, Create), all inline/nav links, `:focus-visible` outline, active-tab indicator. **Never** status badges, table headers, muted text, or general emphasis — this discipline is pre-existing and must survive every future conversion. |
| Destructive | `--color-destructive` (`var(--red-500)`) | Delete buttons/borders, error text/messages, delete-confirmation copy — never anything else. |

### Additional semantic roles (16 colour tokens total, outside the 60/30/10 split but required)

| Token | Value | Usage |
|---|---|---|
| `--color-border` | `var(--slate-700)` | Card/input borders, table dividers, header bottom-border. |
| `--color-text-primary` | `var(--slate-300)` | Headings, body copy, input values. |
| `--color-text-secondary` | `var(--slate-400)` | Field labels, meta/secondary text, table header text. |
| `--color-side-bench` | `var(--slate-400)` | Bench/justice avatar fill + side indicator only. |
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

## Spacing

Seven steps, all multiples of 4px:

| Token | Value | Usage |
|---|---|---|
| `--space-xs` | 4px | Gap between pills/chips/badges; tight inline flex gaps. |
| `--space-sm` | 8px | Label-to-input gap; gap between inline buttons; table cell horizontal padding. |
| `--space-md` | 16px | Field-to-field vertical margin within a card; margin between stacked cards. |
| `--space-lg` | 24px | Card internal padding; heading-to-content margin. |
| `--space-xl` | 32px | Layout gaps between major page regions. |
| `--space-2xl` | 48px | Page content top/bottom padding. |
| `--space-3xl` | 64px | Page-level spacing for the largest public reading surfaces (reserved for the redesigned public listing/transcript vertical rhythm; not required for admin). |

**Touch targets:** `--touch-target` (44px, WCAG 2.1 AA) applies to buttons and inputs generally.
`--touch-target-dense` (36px) is the sole exception, for compact per-row inline buttons inside
dense admin tables. This exception is carried forward unchanged from the pre-token system — no
future conversion may introduce a touch target below either of these two named values (P-05).

## Component directory split (D-17)

One token set, two component layers, per the Figma page structure (D-06):

- `app/src/lib/primitives/` — shared, tokens-only components with no public/admin opinion:
  `Button`, `Badge`, `Input`, `Card`.
- `app/src/lib/public/` — reading-optimized components (wider measure, larger type, more air):
  `ChatBubble`, `StageDirection`, `SectionRail`, `TermRow`, etc.
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

---

*This is a living snapshot, not a locked spec — update it if a future phase changes the token
set. As of 2026-08-28 it documents the state after Phase 51 plan 51-03 (token authoring); the
conversion sweep that drives every remaining inline-style literal onto these tokens is plan
51-09's scope, tracked in `51-TOKEN-MAP.md`.*
