# Phase 4: Accessibility + Hardening - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 4 hardens accessibility across the full UI surface. Every page must pass WCAG 2.1 AA color contrast (4.5:1), be fully keyboard navigable, carry semantic HTML landmarks, convey speaker side to assistive technology, and provide visible focus indicators on all interactive elements. A sticky mobile section nav is added to complete the experience on narrow screens.

**Phase 4 deliverables:**
1. Color contrast fixes — remove sequence numbers; fix `#475569` role labels + roster headers → `#94a3b8`
2. Global focus ring — `*:focus-visible` in `app.css` with `#93c5fd` ring, `border-radius: 4px`, `outline-offset: 3px`
3. Semantic HTML landmarks — `<header>` + `<main>` on every page
4. ChatBubble screen-reader semantics — `role="article"` + `aria-label="Bench: [Name]"` / `aria-label="Advocate: [Name]"` per bubble
5. Mobile section nav — fixed-bottom horizontal sticky pill row at `<768px` breakpoint, matching the desktop SectionRail behavior

**Requirements addressed:** A11Y-01, A11Y-02, A11Y-03, A11Y-04

</domain>

<decisions>
## Implementation Decisions

### Color Contrast (A11Y-01)
- **D-01:** Sequence numbers (`#475569`, 13px) in `ChatBubble.svelte` are **removed entirely** — the utterance order is self-evident from chat flow. Remove the sequence `<span>` element from the bubble header row. Also remove the `--color-text-sequence: #475569` CSS variable from `app.css`.
- **D-02:** Role labels in `ChatBubble.svelte` (`#475569`, 11px) → change to `#94a3b8`. Already used for speaker names and subline text; passes 4.5:1 on `#1e293b` (~5.9:1 ratio).
- **D-03:** Roster column headers ("Bench" / "Advocates") in the argument `+page.svelte` (`#475569`, 13px 600 weight) → change to `#94a3b8`. Same rationale as D-02.
- **D-04:** All other color combinations verified passing — no other contrast failures. (`#e2e8f0` on `#0f1117` ≈15.7:1, `#94a3b8` on `#1e293b` ≈5.9:1, `#93c5fd` on `#1e293b` ≈8.3:1, `#fcd34d` on `#1e293b` ≈9.4:1, avatar initials `#0f1117` on `#94a3b8` ≈8.3:1.)

### Focus Indicators (A11Y-02)
- **D-05:** Focus styles are defined **globally in `app.css`** — a single `*:focus-visible` rule covers all current and future interactive elements automatically.
- **D-06:** Focus ring color: **`#93c5fd`** (advocate blue). Already in palette for links and advocate labels. Passes 4.5:1 on both backgrounds (`#0f1117` ≈11.6:1, `#1e293b` ≈8.3:1).
- **D-07:** Focus ring: `outline: 2px solid #93c5fd; outline-offset: 3px; border-radius: 4px`. The `border-radius: 4px` matches the `SectionRail` button shape — visually cohesive, not a browser-default rectangle.

### Semantic HTML (A11Y-02 / A11Y-03)
- **D-08:** Add `<header>` and `<main>` landmarks to every page — replace the outermost content `<div>` with `<main>`, and the top-bar `<div>` with `<header>`. Apply to: `+layout.svelte` global nav, `cases/+page.svelte`, `cases/[slug]/arguments/[id]/+page.svelte`.
- **D-09:** Each `ChatBubble.svelte` wrapper gets `role="article"` + `aria-label="Bench: [displayName]"` or `aria-label="Advocate: [displayName]"` (derived from `isBench`). Screen readers announce the side and speaker name as the article label, then read the text content inside. Satisfies A11Y-03 for assistive technology users — speaker side is not color-only.
- **D-10:** `StageDirection.svelte` gets `role="note"` to distinguish it semantically from utterance articles. No aria-label needed — text content is self-explanatory.

### Mobile Section Navigation
- **D-11:** At `<768px` (same breakpoint as the sidebar hide), show a **fixed-bottom horizontal sticky pill row** showing the detected sections (Petitioner / Respondent / Rebuttal / Amicus). Clicking a pill smooth-scrolls to that section anchor (same `scrollIntoView` behavior as the desktop SectionRail).
- **D-12:** The mobile pill row is fixed to the **bottom of the viewport** — thumb-reachable on phones, doesn't obscure the argument header or first utterances on load.
- **D-13:** Mobile pill row is a new component (`MobileNavBar.svelte` or inline in the argument page). It uses the same `sectionAnchors` and `activeSection` logic already computed for `SectionRail`. Active section highlights its pill (same active styling pattern as the desktop rail). Hide entirely when no sections are detected (no anchors available).

### Claude's Discretion
- Exact CSS property order and specificity in `app.css` for the global `*:focus-visible` rule — planner manages the file.
- Whether to add `aria-label` to the `<nav>` in `+layout.svelte` (e.g., `aria-label="Site navigation"`) and the `SectionRail` `<nav>` (e.g., `aria-label="Argument sections"`) — minor enhancement, planner may add.
- Mobile pill row visual treatment — pill shape, active background, font size — should match the dark palette (`#1e293b` background, `#e2e8f0` / `#94a3b8` text, active accent `#93c5fd`).
- Whether the mobile nav bar adds bottom padding to the chat column so the last utterance isn't hidden behind it.
- `role="note"` for `StageDirection` is a suggestion — planner can substitute `aria-label="Stage direction"` on the existing div if `role="note"` is not semantically accurate.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Definition
- `.planning/PROJECT.md` — Apolitical framing hard constraint (identical treatment for all speakers — informs D-09 aria-label parity)
- `.planning/REQUIREMENTS.md` — A11Y-01 through A11Y-04 (all Phase 4 requirements)
- `.planning/ROADMAP.md` — Phase 4 goal, success criteria (4 items), "UI hint: yes"

### Hard Constraints
- `CLAUDE.md` — Apolitical framing (every speaker identical schema/treatment), SvelteKit Runes only (`$props()`, `$state()`, `$derived()` — no legacy stores), no `PUBLIC_` env var prefix

### Existing Code to Read Before Planning
- `app/src/lib/components/ChatBubble.svelte` — receives the sequence number removal (D-01), role label color fix (D-02), and role/aria-label additions (D-09)
- `app/src/lib/components/SectionRail.svelte` — desktop nav rail; mobile nav mirrors its section data and active-state logic
- `app/src/lib/components/StageDirection.svelte` — receives `role="note"` (D-10)
- `app/src/routes/+layout.svelte` — global nav; receives `<header>` landmark (D-08)
- `app/src/routes/cases/+page.svelte` — case list page; receives `<header>` + `<main>` (D-08)
- `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` — argument view; receives `<header>` + `<main>` (D-08), roster header color fix (D-03), mobile nav (D-11–13)
- `app/src/app.css` — global focus ring added here (D-05–07); `--color-text-sequence` variable removed (D-01)

### Prior Phase Decisions That Apply
- `.planning/phases/03-full-ui/03-CONTEXT.md` — D-05 (bench LEFT / advocate RIGHT), D-08 (bench `#94a3b8` / advocate `#93c5fd`), D-03 (768px mobile breakpoint, SectionRail hidden below it)
- `.planning/phases/01-foundation-proof-of-concept/01-CONTEXT.md` — D-01 (Svelte 5 Runes exclusively)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SectionRail.svelte` — `sections` prop, `activeSection` scroll-spy via `IntersectionObserver`, `scrollIntoView` on click. Mobile nav bar uses identical logic — either extract a shared hook or duplicate the observer setup.
- `$derived` / `$derived.by()` for `sectionAnchors` and `roster` in the argument page — mobile nav consumes `sectionAnchors` directly, no new data needed.
- Dark palette constants already established: `#0f1117` (page bg), `#1e293b` (surface), `#334155` (border), `#e2e8f0` (body text), `#94a3b8` (muted), `#93c5fd` (accent/advocate blue).

### Established Patterns
- **Svelte 5 Runes:** `$props()`, `$state()`, `$derived()`, `$effect()` — no `export let`, no `$:` reactive blocks, no legacy stores.
- **Inline styles:** All current styling uses inline `style=""` attributes (no Svelte `<style>` blocks except for media queries). New components follow this pattern. The global `app.css` is the exception — that's where the focus ring rule lives.
- **Media query breakpoints:** The `<style>` block at the bottom of the argument page uses `@media (max-width: 768px)` for the CSS grid override. Mobile nav bar uses the same breakpoint.
- **`$effect` for browser-only code:** `SectionRail` wraps the `IntersectionObserver` setup in `$effect(() => { if (!browser) return; ... })`. New mobile nav component must follow the same pattern.

### Integration Points
- `app/src/app.css` — single entry point for the global focus ring rule. Keep it minimal; don't put component-specific styles here.
- `ChatBubble.svelte` — three changes in one component (remove sequence span, fix role label color, add role/aria-label). Planner should treat as one atomic task.
- Mobile nav bar integrates with the argument page's `sectionAnchors` derived value — passed as a prop, same as `SectionRail`.

</code_context>

<specifics>
## Specific Ideas

- The global focus rule: `*:focus-visible { outline: 2px solid #93c5fd; outline-offset: 3px; border-radius: 4px; }` — modern browsers (Chrome 94+, Firefox 83+, Safari 16+) support `outline` following `border-radius`, so this produces a rounded ring on buttons without additional CSS.
- Mobile section pills: same `section_hint` values as the desktop rail (lowercase from parse step: `petitioner`, `respondent`, `rebuttal`, `amicus`). Display in title case. Active pill gets a distinct background or border accent — consistent with the SectionRail active state (`border-left: 3px solid #93c5fd`).
- For the mobile pill row, the argument page chat column should add `padding-bottom: ~60px` so the last utterance is not hidden behind the fixed bar.
- `aria-label` on `ChatBubble` outer wrapper: `aria-label="{isBench ? 'Bench' : 'Advocate'}: {displayName}"`. The role label (if present) can be omitted from the aria-label — it's already in the text content inside the article.
- The `<nav aria-label="Argument sections">` on `SectionRail` would make screen readers distinguish this nav from the global site nav in `+layout.svelte`. Planner may add `aria-label="Site navigation"` to the layout nav as well.

</specifics>

<deferred>
## Deferred Ideas

- **`photo_url` avatars** — enrichment pipeline (ENRICH-01) still deferred to v2. Phase 4 avatars remain initials-only. When photo_url is populated, the `<img>` element will need `alt` text (person's name) — an accessibility concern for a future phase.
- **Skip-to-content link** — a "Skip to main content" anchor at the top of the page is a common keyboard-navigation enhancement (WCAG 2.4.1). Not strictly required for the current A11Y-01–04 requirements, but a natural addition if a future hardening pass is done.
- **High-contrast mode testing** — A11Y-03 requires the UI to "remain clear when viewed in a single-color or high-contrast display mode." Automated contrast checks (A11Y-01) cover standard rendering; manual verification in Windows High Contrast Mode or macOS Increase Contrast is left to human UAT.
- **Obergefell Q2 loading** — deferred from Phase 3. Not part of Phase 4 scope.

</deferred>

---

*Phase: 4-Accessibility + Hardening*
*Context gathered: 2026-06-15*
