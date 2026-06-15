# Phase 4: Accessibility + Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-15
**Phase:** 4-Accessibility + Hardening
**Areas discussed:** Secondary text colors, Focus indicator design, Semantic HTML scope, Mobile section nav

---

## Secondary text colors

### Q1: Sequence numbers — decorative or informational?

| Option | Description | Selected |
|--------|-------------|----------|
| Decorative — hide from a11y tree | Add aria-hidden="true" to the sequence span. Keep #475569 color (decorative elements exempt from contrast rules). | |
| Informational — fix contrast | Treat as real content. Fix #475569 → #94a3b8 (~5.9:1 on #1e293b). | |
| Remove sequence numbers | Delete the number from the UI entirely. The chat flow is self-evident; the number adds noise. | ✓ |

**User's choice:** Remove sequence numbers  
**Notes:** Flow order is self-evident from the chat layout. Sequence numbers add visual noise without navigation value.

---

### Q2: Role labels and roster headers — fix contrast?

| Option | Description | Selected |
|--------|-------------|----------|
| #94a3b8 for both | Already used for muted text; passes 4.5:1 on #1e293b (~5.9:1). Consistent with palette. | ✓ |
| #64748b for both | One step darker than current. Still fails (~3.25:1) — not a valid fix. | |
| Keep #475569 — treat as decorative | Add aria-hidden. Not ideal since role labels and headers carry real meaning. | |

**User's choice:** #94a3b8 for both  
**Notes:** Role labels (11px) in ChatBubble and roster headers ("Bench"/"Advocates", 13px 600) both fixed to #94a3b8.

---

## Focus indicator design

### Q1: Where should focus styles be defined?

| Option | Description | Selected |
|--------|-------------|----------|
| Global in app.css | One *:focus-visible rule covers all interactive elements automatically. | ✓ |
| Per-component inline styles | Each component handles its own :focus-visible. More control, more work. | |

**User's choice:** Global in app.css

---

### Q2: Focus ring color?

| Option | Description | Selected |
|--------|-------------|----------|
| #93c5fd — advocate blue | Already in palette for links and advocate labels. Passes 4.5:1 on both backgrounds. | ✓ |
| #e2e8f0 — near-white | Maximum contrast (15.7:1 on #0f1117). Visible but less cohesive. | |
| You decide | Let the planner pick a passing focus ring color. | |

**User's choice:** #93c5fd — advocate blue

---

### Q3: Focus ring border-radius on SectionRail buttons?

| Option | Description | Selected |
|--------|-------------|----------|
| Match border-radius: 4px | Follows the rounded shape of the active button. Feels intentional. | ✓ |
| Standard rectangle outline | Browser default shape. No extra CSS beyond the global rule. | |

**User's choice:** Match border-radius: 4px  
**Notes:** CSS rule: `outline: 2px solid #93c5fd; outline-offset: 3px; border-radius: 4px`

---

## Semantic HTML scope

### Q1: Page-level landmarks?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — add <main> and <header> | Replace outermost content <div> with <main>, top-bar div with <header>. | ✓ |
| No — keep all divs | WCAG 2.1 AA doesn't mandate landmark elements. | |

**User's choice:** Yes — add `<main>` and `<header>`

---

### Q2: ARIA labels per chat bubble?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — aria-label per bubble | aria-label="Bench: Justice Kagan" on each bubble wrapper. | ✓ |
| No — layout position is sufficient | A11Y-03 is about visual display; screen reader semantics out of scope. | |
| Partial — aria-label on avatar circle only | Small semantic boost without restructuring the bubble. | |

**User's choice:** Yes — aria-label per bubble  
**Notes:** Satisfies A11Y-03 for assistive technology users — side is not color-only.

---

### Q3: Bubble aria-label format?

| Option | Description | Selected |
|--------|-------------|----------|
| role='article' + aria-label on wrapper | Each ChatBubble gets role="article" aria-label="Bench/Advocate: [Name]". | ✓ |
| Visually-hidden <span> inline | Add <span class='sr-only'>Bench:</span> before speaker name. Simpler. | |
| You decide | Leave exact implementation to planner. | |

**User's choice:** role='article' + aria-label on wrapper

---

## Mobile section nav

### Q1: Add mobile section nav in Phase 4?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep deferred — not an A11Y req | A11Y-01–04 don't require mobile section nav. Defer to a future UI phase. | |
| Add it — horizontal sticky pill row on mobile | Below 768px, show a horizontal sticky strip of section pill buttons. | ✓ |

**User's choice:** Add it — horizontal sticky pill row on mobile

---

### Q2: Where does the pill row appear?

| Option | Description | Selected |
|--------|-------------|----------|
| Bottom of viewport | Fixed to the bottom like a mobile tab bar. Easy thumb reach. | ✓ |
| Top — below the header bar | Sticky below the argument header. Visible immediately but takes vertical space. | |

**User's choice:** Bottom of viewport

---

## Claude's Discretion

- Exact CSS property order and specificity in `app.css` for the `*:focus-visible` rule
- Whether to add `aria-label` to `<nav>` elements (site nav and section rail nav) for additional screen reader disambiguation
- Mobile pill row visual treatment — pill shape, spacing, active background (should match dark palette)
- Whether the chat column adds `padding-bottom` to prevent content hiding behind the fixed mobile nav bar
- `role="note"` for `StageDirection.svelte` — planner may substitute `aria-label="Stage direction"` on the existing div if the note role is not semantically accurate

## Deferred Ideas

- **Skip-to-content link** — a "Skip to main content" anchor. Not required by A11Y-01–04 but a natural future addition.
- **High-contrast mode manual testing** — visual verification in Windows High Contrast Mode / macOS Increase Contrast. Left to human UAT; not covered by automated contrast checks.
- **`photo_url` avatar alt text** — when ENRICH-01 is implemented and photo_url is populated, the `<img>` will need `alt` text. An accessibility concern for a future enrichment phase.
