# Design System Reference

**Extracted:** 2026-07-08
**Purpose:** Quick reference for the current admin UI's visual language — colors, spacing, typography. Written up ahead of a future phase that will formalize this in Figma. Nothing here is a new decision; it's a snapshot of what's already live in the codebase.

**Source of truth today:** There is no central stylesheet, theme file, or design-token file. Every value below is copied from inline `style="..."` attributes scattered across the Svelte components (mainly `app/src/routes/admin/**/*.svelte` and shared components in `app/src/lib/components/`). This doc exists so that source of truth doesn't have to be re-derived by hand every time it's needed — it is not itself the source of truth, the components are.

**Scope:** Covers the admin interface only (`/admin/*`). The public-facing site (`/cases/`, `/arguments/`) shares the same color palette but hasn't been separately audited here.

---

## Colors

| Role | Hex | Where it's used |
|---|---|---|
| Page background | `#0f1117` | `<main>` background on every admin page |
| Card / header background | `#1e293b` | Card containers, page header bar, table row default background, badge backgrounds |
| Border | `#334155` | Card borders, input borders, table row dividers, header bottom-border |
| Primary text | `#e2e8f0` | Headings, body copy, input values |
| Muted text | `#94a3b8` | Field labels, secondary/meta text, table header text, "N/A" hint values |
| Accent | `#93c5fd` | Primary CTA buttons/borders (Save, Publish, Create), all links, focus states |
| Success / Published | `#4ade80` | Published status badge, "Saved." success messages |
| Draft | `#a78bfa` | Draft status badge |
| Unpublished | `#fb923c` | Unpublished status badge |
| Warning | `#fbbf24` | "Missing tenure" text, other attention-needed inline warnings |
| Archived | `#cbd5e1` | Archived pipeline-run badge (distinct from muted-text grey) |
| Destructive | `#ef4444` | Delete buttons/borders, error text, delete-confirmation copy |

Accent (`#93c5fd`) is reserved for primary actions and navigation — never used on status badges, table headers, or muted text. Status colors (Draft/Published/Unpublished/Archived/Warning/Destructive) are never reused for anything except their specific status meaning, to keep them scannable at a glance.

## Typography

Only three sizes and two weights appear anywhere in the admin UI:

| Role | Size | Weight | Line height |
|---|---|---|---|
| Heading (card `<h2>`) | 20px | 600 | 1.2 |
| Sub-heading (`<h3>`) | 16px | 400 | 1.2 |
| Body | 16px | 400 | 1.5 |
| Label / meta | 14px | 400 | 1.4 (chips/labels) or 1.5 (paragraph-style meta text) |

Font family: `system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`, declared once in `app/src/app.css`, inherited everywhere via `font-family: inherit`.

## Spacing

Values are consistently multiples of 4px:

| Token | Value | Usage |
|---|---|---|
| xs | 4px | Gap between pills/chips; tight inline flex gaps |
| sm | 8px | Label-to-input gap; gap between inline buttons; table cell horizontal padding |
| md | 16px | Field-to-field vertical margin within a card; margin between stacked cards |
| lg | 24px | Card internal padding; heading-to-content margin |
| 2xl | 48px | Page content top/bottom padding |

Touch targets: buttons and submit inputs are `min-height: 44px` (WCAG 2.1 AA), except compact per-row inline buttons inside dense tables, which use `min-height: 36px`.

## Component conventions

- No component library or icon library — every element is plain HTML with inline styles. The one exception is `bits-ui` (headless primitives), used only for the speaker popover.
- No shadcn, no `components.json`, no Tailwind — this is a hand-rolled system, consistently applied since Phase 5.
- Cards: `background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;` — this exact combination appears on every card in the admin UI.
- Buttons follow two visual patterns: filled/bordered accent (`border: 1px solid #93c5fd`, transparent background) for primary actions, and plain muted-border for secondary/cancel actions.

---

*This is a living snapshot, not a locked spec — update it if a future phase changes the palette or introduces new tokens. When the Figma phase happens, this file is the starting checklist of values to bring in.*
