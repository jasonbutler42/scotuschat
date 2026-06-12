---
phase: 03-full-ui
plan: 04
status: complete
completed_at: 2026-06-12
---

# Plan 03-04 Summary: CSS Grid layout + SectionRail scroll-spy

## What was built

**`app/src/lib/components/SectionRail.svelte`** (new)
- Sticky left navigation rail with IntersectionObserver scroll-spy
- `$app/environment` `browser` guard — IntersectionObserver only created client-side (SSR-safe)
- `$effect` lifecycle manages observer creation and disconnect cleanup
- Active section highlighted with `#93c5fd` left border, `#e2e8f0` text, weight 600
- Inactive sections: `#94a3b8` text, transparent border, weight 400
- Clicking a section label smooth-scrolls to `section.anchorId` via `scrollIntoView({ behavior: 'smooth' })`
- Svelte 5 Runes: `$props()`, `$state`, `$effect` — no `export let`, no `$:` blocks

**`app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`** (restructured)
- Imports `SectionRail` from `$lib/components/SectionRail.svelte`
- Header max-width widened 860px → 1200px to accommodate two-column content grid
- **Speaker roster** added below docket/date subline — two-column grid (`1fr 1fr`): Bench left, Advocates right
  - Both columns use `#94a3b8` for speaker names — apolitical framing (identical treatment)
  - Column labels "Bench" / "Advocates" at 13px / weight 600 / `#475569`
  - Roster derived client-side via `$derived.by()` from `data.utterances` — no new API endpoint
- **CSS Grid content area**: `grid-template-columns: 180px 1fr` below header bar — D-01
- **Section anchors**: `id="section-{hint}-{sequence}"` on each utterance with a non-null `section_hint`
- `sectionAnchors` derived list (unique hints only, first occurrence per section) passed to `SectionRail`
- Mobile breakpoint: `@media (max-width: 768px)` hides `.nav-rail`, collapses grid to `1fr`

## Key decisions / deviations

- Section anchor IDs placed on all utterances with non-null `section_hint`, not just the first — harmless over-annotation; SectionRail only links to the first occurrence's ID (from `sectionAnchors`)
- Roster derived from utterances client-side (D-12) — no additional `/people` API call; avoids N+1 requests and new API surface
- `sectionAnchors` filters `is_stage_direction` to avoid picking a stage-direction as the first utterance of a section

## Verification results

```
python -m pytest tests/ -q:
  17 passed in 0.59s

Acceptance criteria spot-checks:
  ✓ CSS Grid: grid-template-columns: 180px 1fr in +page.svelte
  ✓ SectionRail.svelte contains browser guard from $app/environment
  ✓ IntersectionObserver created inside $effect with browser check
  ✓ Smooth scroll: scrollIntoView({ behavior: 'smooth' }) on button click
  ✓ Active section IntersectionObserver scroll-spy with rootMargin -40%/-55%
  ✓ Speaker roster: grid-template-columns: 1fr 1fr, Bench left, Advocates right
  ✓ Both roster columns use #94a3b8 (apolitical framing)
  ✓ Section anchors: id="section-{hint}-{sequence}" pattern
  ✓ Mobile: @media (max-width: 768px) hides nav-rail, grid collapses to 1fr
  ✓ No export let, no $: blocks — Svelte 5 Runes throughout
```

## key-files

created:
  - app/src/lib/components/SectionRail.svelte
modified:
  - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte
