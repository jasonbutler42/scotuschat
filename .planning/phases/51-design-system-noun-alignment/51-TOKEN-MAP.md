---
phase: 51-design-system-noun-alignment
plan: 03
type: token-map
created: 2026-08-28
---

# Phase 51 — Value-to-Token Map

Deterministic conversion table for the plan-51-09 sweep. Every distinct literal currently
present in `app/src/**/*.svelte` is accounted for below — mapped to exactly one token, flagged
as an open row for operator decision, or named as explicitly out of scope. Nothing is silently
rounded or invented.

Inventory taken 2026-08-28 via:
```
grep -ohE '#[0-9a-fA-F]{6}' app/src -r --include=*.svelte | sort | uniq -c | sort -rn
grep -ohE 'font-size: *[0-9]+px' app/src -r --include=*.svelte | sort | uniq -c | sort -rn
grep -ohE '(padding|margin|gap|row-gap|column-gap)(-[a-z]+)?: *[0-9]+px' app/src -r --include=*.svelte
```

---

## 1. Colour

24 distinct six-digit hex values exist in `app/src/**/*.svelte` today. 14 have an existing
semantic role (matching `51-UI-SPEC.md`'s primitive-palette table exactly); the remaining 10
have no semantic role and are recorded as open rows rather than invented into new tokens.

### Mapped (14)

| Hex | Frequency | Token | Notes |
|---|---|---|---|
| `#94a3b8` | 275 | `var(--color-text-secondary)` (default) / `var(--color-side-bench)` (transcript speaker components only) | **Ambiguous — default + exception.** Everywhere outside `ChatBubble.svelte`/`SpeakerPopover.svelte`/`SectionRail.svelte`'s speaker-identity markup, this is field-label/meta/secondary text and maps to `--color-text-secondary`. Inside a transcript speaker component, when the value is coloring the bench side of a bench/advocate distinction, it maps to `--color-side-bench`. |
| `#334155` | 236 | `var(--color-border)` | Card/input borders, table dividers, header bottom-border. |
| `#e2e8f0` | 205 | `var(--color-text-primary)` | Headings, body copy, input values. |
| `#1e293b` | 113 | `var(--color-surface)` | Cards, header bar, nav, table row default background. |
| `#93c5fd` | 107 | `var(--color-accent)` (default) / `var(--color-side-advocate)` (transcript speaker components only) | **Ambiguous — default + exception.** Everywhere outside the same transcript speaker components named above, this is a primary action / link / focus-ring use and maps to `--color-accent`. Inside a transcript speaker component, when the value is coloring the advocate side, it maps to `--color-side-advocate`. |
| `#0f1117` | 90 | `var(--color-bg)` | Page background. |
| `#ef4444` | 54 | `var(--color-destructive)` | Delete buttons/borders, error text — never anything else. |
| `#cbd5e1` | 22 | `var(--color-status-archived)` | Archived pipeline-run badge (admin only). |
| `#fbbf24` | 19 | `var(--color-status-warning)` | "Missing tenure" and similar attention-needed inline warnings (admin only). |
| `#4ade80` | 19 | `var(--color-status-published)` | Published status badge (admin only). |
| `#fb923c` | 13 | `var(--color-status-unpublished)` | Unpublished status badge (admin only). |
| `#a78bfa` | 7 | `var(--color-status-draft)` | Draft status badge (admin only). |
| `#fcd34d` | 1 | `var(--color-stage-text)` | Stage-direction body text only. |
| `#d97706` | 1 | `var(--color-stage-accent)` | Stage-direction bracketed text (e.g. `[Laughter]`) only. |

### Unmapped — open rows for operator decision (10)

None of these 10 hexes appear in `51-UI-SPEC.md`'s primitive-palette table. The sweep in plan
51-09 must report each occurrence rather than silently assigning it to the nearest-looking
token. Do not invent a 15th primitive to cover these without an operator decision.

| Hex | Frequency | Notes |
|---|---|---|
| `#64748b` | 6 | Not in the primitive palette. Visually a slate mid-tone between `--slate-700` (#334155) and `--slate-400` (#94a3b8) — needs a real site-by-site look, not a guess. |
| `#f59e0b` | 4 | Not in the primitive palette. Close to `--amber-600` (#d97706) but not identical. |
| `#facc15` | 3 | Not in the primitive palette. Close to `--amber-300`/`--amber-400` but not identical. |
| `#f87171` | 3 | Not in the primitive palette. A lighter red than `--red-500` (#ef4444) — could be a hover/lighter-destructive state, needs confirmation. |
| `#38bdf8` | 3 | Not in the primitive palette. A sky-blue distinct from `--blue-300` (#93c5fd). |
| `#34d399` | 3 | Not in the primitive palette. A green distinct from `--green-400` (#4ade80). |
| `#e879f9` | 2 | Not in the primitive palette. A fuchsia/magenta with no existing semantic analog. |
| `#475569` | 2 | Not in the primitive palette. Per `PROJECT.md`'s Phase 4 history this hex was previously "eliminated" from speaker-side differentiation for apolitical-framing reasons — its 2 remaining occurrences need to be checked to confirm they are NOT re-encoding speaker importance before being assigned a token (P-03). |
| `#2dd4bf` | 2 | Not in the primitive palette. A teal with no existing semantic analog. |
| `#fb7185` | 1 | Not in the primitive palette. A rose/pink distinct from `--red-500`. |

---

## 2. Type

Applicable only inside a `font-size:` declaration (and its matching `font-weight:` where noted).
All nine sizes currently in use, left-hand side first:

| Today | Collapses to |
|---|---|
| 11px | `var(--font-size-caption)` |
| 12px | `var(--font-size-caption)` |
| 13px | `var(--font-size-caption)` |
| 14px | `var(--font-size-caption)` |
| 16px | `var(--font-size-body)` |
| 18px | `var(--font-size-lead)` |
| 20px | `var(--font-size-heading)` |
| 28px | `var(--font-size-display)` |
| 32px | `var(--font-size-display)` |

Weights:

| Today | Collapses to |
|---|---|
| 400 | `var(--font-weight-regular)` |
| 600 | `var(--font-weight-semibold)` |
| 500 (2 sites, both `ResolveCard.svelte` — lines ~1295 and ~1427) | `var(--font-weight-semibold)`, **and flagged for operator sight-check.** 500 may have been a deliberate mid-weight distinct from 600; if the operator disagrees on sight, it becomes a D-08 surfaced artifact, not a silent revert. |

---

## 3. Spacing

Applicable only inside `padding`, `padding-*`, `margin`, `margin-*`, `gap`, `row-gap`, and
`column-gap` declarations.

### Mapped to the 7-step scale

| Today | Collapses to |
|---|---|
| 4px | `var(--space-xs)` |
| 8px | `var(--space-sm)` |
| 12px | `var(--space-md)` |
| 16px | `var(--space-lg)` |
| 24px | `var(--space-xl)` |
| 32px | `var(--space-2xl)` |
| 48px | `var(--space-3xl)` |
| — (0 occurrences today) | `var(--space-4xl)` (64px) — reserved per D-09 for the redesigned public reading surfaces; not required by any existing site. |

> **Amended 2026-09-01.** 12px was originally recorded below as a residual to report and
> never round. The conversion then found it at 153 sites — second only to 8px and ahead
> of 16px — which is not drift but a step the scale had no name for. It was added, and
> the names from `md` up shifted one place. The residual table below is left as written
> so the reasoning that led here is still legible; only the 12px row is now closed.

### Residuals — not on the scale, unmapped

| Today | Frequency | Notes |
|---|---|---|
| 2px | 25 | Sub-4px fine adjustment (e.g. border widths expressed via padding compensation). Report each site during the sweep; do not round up to `--space-xs`. |
| 6px | 15 | Between `--space-xs` (4px) and `--space-sm` (8px). Report, do not round. |
| ~~12px~~ | 153 | **CLOSED 2026-09-01 — promoted to `--space-md`.** Was: between `--space-sm` and the then-`--space-md` (16px), the single most common residual. |
| 20px | 5 | Between `--space-lg` (16px) and `--space-xl` (24px) under the amended names. Report, do not round. |

---

## 4. Out of scope for automatic conversion

The plan-51-09 script must NOT touch these declarations. They are layout values, not scale
values — mapping them onto a spacing or type token would change what they mean, not just how
they're named.

- `border-radius`
- `grid-template-columns`
- `width`, `min-width`, `max-width`
- `height`, `min-height` (except where `min-height` is literally the 44px/36px touch-target
  guarantee — those convert to `var(--touch-target)` / `var(--touch-target-dense)`, per
  `51-UI-SPEC.md`'s Spacing Scale exceptions clause, but a `min-height` used for any other
  layout purpose stays untouched)
- `flex-basis`
- `line-height` numerics that are not one of the five type-scale line-height tokens (e.g. a
  one-off `line-height: 1` on an icon wrapper)
- Any `px` value that appears inside a `calc()` expression

---

## Summary counts

- 24 distinct hex values found; 14 mapped, 10 open rows.
- 9 distinct font-size values found; all 9 mapped (11/12/13/14 → caption).
- 3 distinct font-weight values found; 400 and 600 mapped directly, 500 mapped with a
  sight-check flag.
- 10 distinct spacing-property px values found; 6 mapped to the 7-step scale (including the
  currently-unused 64px reservation), 4 are residuals reported unmapped.
