---
phase: 04-accessibility-hardening
reviewed: 2026-06-15T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - app/src/app.css
  - app/src/lib/components/ChatBubble.svelte
  - app/src/lib/components/StageDirection.svelte
  - app/src/lib/components/SectionRail.svelte
  - app/src/lib/components/MobileNavBar.svelte
  - app/src/routes/+layout.svelte
  - app/src/routes/cases/+page.svelte
  - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-06-15T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 4 targets accessibility hardening: ARIA roles, focus rings, semantic landmark elements, and the new `MobileNavBar` component. Most changes are correctly implemented — the focus ring CSS rule is present, landmark elements (`<main>`, `<header>`, `<nav>`) are correctly applied, ARIA attributes match the design contract, and the `#475569` color purge is complete.

One blocker exists: `MobileNavBar.svelte` has an inline `style` attribute that sets `display: flex` on the `<nav>` element, which overrides the Svelte-scoped `nav { display: none; }` stylesheet rule due to CSS specificity. The mobile nav bar will be visible at all viewport widths, breaking the `<768px`-only visibility requirement. The desktop layout will show a fixed bottom bar permanently.

Four warnings cover: missing `aria-hidden` on redundant avatar initials inside `role="article"` bubbles, missing `aria-current` on active nav buttons in both rail components, `prefers-reduced-motion` not respected in smooth-scroll handlers, and a potential crash path in `formatDate` when `argued_date` is null.

---

## Critical Issues

### CR-01: MobileNavBar CSS specificity bug — nav always visible on desktop

**File:** `app/src/lib/components/MobileNavBar.svelte:33-51` (nav element) and `73-82` (style block)

**Issue:** The `<nav>` element carries an inline `style` attribute that includes `display: flex`. Inline styles have CSS specificity of `(1,0,0,0)`, which unconditionally overrides any scoped stylesheet rule. The Svelte-compiled scoped rule `nav.svelte-xxxx { display: none; }` has specificity `(0,1,0,1)` — it loses to the inline style at every viewport width. Consequently, the `@media (max-width: 768px) { nav { display: flex; } }` rule is also redundant. The mobile nav bar renders as a fixed bottom bar on all screen sizes — desktop users see it permanently.

**Current code (lines 33-51, 73-82):**
```svelte
<nav
    aria-label="Argument sections"
    style="
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: #1e293b;
        border-top: 1px solid #334155;
        display: flex;          <!-- This inline display: flex beats the stylesheet rule -->
        flex-direction: row;
        overflow-x: auto;
        gap: 8px;
        padding: 8px 16px;
        min-height: 44px;
        align-items: center;
    "
>
...
<style>
    nav {
        display: none;          <!-- Never takes effect — specificity lost to inline style -->
    }
    @media (max-width: 768px) {
        nav {
            display: flex;      <!-- Redundant — already visible via inline style -->
        }
    }
</style>
```

**Fix:** Remove `display: flex` from the inline style attribute. Let the `<style>` block control the display property exclusively. The `flex-direction`, `overflow-x`, `gap`, `align-items` layout properties can remain in the inline style — they apply only when the element is displayed, so they cause no harm on desktop (they are ignored when `display: none`). Update the style block to restore `display: flex` in the media query.

```svelte
<nav
    aria-label="Argument sections"
    style="
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: #1e293b;
        border-top: 1px solid #334155;
        flex-direction: row;
        overflow-x: auto;
        gap: 8px;
        padding: 8px 16px;
        min-height: 44px;
        align-items: center;
    "
>
...
<style>
    nav {
        display: none;
    }
    @media (max-width: 768px) {
        nav {
            display: flex;
        }
    }
</style>
```

---

## Warnings

### WR-01: Avatar initials div not aria-hidden — redundant announcement for screen readers

**File:** `app/src/lib/components/ChatBubble.svelte:47-53`

**Issue:** The outer `<div>` carries `role="article"` and `aria-label="{isBench ? 'Bench' : 'Advocate'}: {displayName}"`. Screen readers announce the label when entering the article. Inside, the avatar `<div>` contains the initials text (`{initials}`) and the `<span>` below it contains `{displayName}`. Both are readable DOM content. A screen reader will announce: the article label ("Bench: John Roberts"), then traverse into the article and read the initials ("JR"), then read the name again ("John Roberts"). The initials are a visual affordance only — they convey no additional information to AT users and should be hidden.

**Fix:** Add `aria-hidden="true"` to the avatar initials `<div>`:
```svelte
<div
    aria-hidden="true"
    style="
        width: 32px; height: 32px; border-radius: 50%;
        background-color: {avatarBg};
        ...
    "
>{initials}</div>
```

### WR-02: SectionRail and MobileNavBar buttons have no aria-current — active state invisible to AT

**File:** `app/src/lib/components/SectionRail.svelte:35-54`, `app/src/lib/components/MobileNavBar.svelte:52-69`

**Issue:** Both navigation components use `activeSection === sec.hint` to toggle visual styles (color, font-weight, border). No `aria-current` or `aria-pressed` attribute is toggled. Screen reader users navigating the button list cannot determine which section is currently active — the active state is conveyed by color and weight alone, violating WCAG 1.3.1 (Info and Relationships) which requires that visual information also be programmatically determinable.

**Fix:** Add `aria-current={activeSection === sec.hint ? 'true' : undefined}` to each button in both components. Using `undefined` (rather than `'false'`) avoids emitting the attribute when inactive, which is the correct pattern for `aria-current` used as a location indicator.

```svelte
<!-- SectionRail.svelte button -->
<button
    aria-current={activeSection === sec.hint ? 'true' : undefined}
    onclick={() => document.getElementById(sec.anchorId)?.scrollIntoView({ behavior: 'smooth' })}
    style="..."
>
    {sec.label}
</button>

<!-- MobileNavBar.svelte button — identical fix -->
<button
    aria-current={activeSection === sec.hint ? 'true' : undefined}
    onclick={() => document.getElementById(sec.anchorId)?.scrollIntoView({ behavior: 'smooth' })}
    style="..."
>
    {sec.label}
</button>
```

### WR-03: smooth scrollIntoView ignores prefers-reduced-motion

**File:** `app/src/lib/components/SectionRail.svelte:36`, `app/src/lib/components/MobileNavBar.svelte:54`

**Issue:** Both `onclick` handlers call `scrollIntoView({ behavior: 'smooth' })` unconditionally. Users who have set `prefers-reduced-motion: reduce` in their OS accessibility settings receive animated scroll regardless of their preference. WCAG 2.3.3 (Animation from Interactions) requires that motion triggered by interaction can be disabled.

**Fix:** Check the media query before choosing scroll behavior:
```svelte
onclick={() => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    document.getElementById(sec.anchorId)?.scrollIntoView({
        behavior: reducedMotion ? 'instant' : 'smooth'
    });
}}
```
Apply identically in both `SectionRail.svelte` and `MobileNavBar.svelte`.

### WR-04: formatDate does not guard against null/undefined argued_date

**File:** `app/src/routes/cases/+page.svelte:11-18`, `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte:16-23`

**Issue:** `formatDate(dateStr: string)` concatenates `dateStr + 'T00:00:00'`. If the API returns `null` or `undefined` for `argued_date` (a legitimate state for un-argued cases or data gaps), `dateStr` is coerced to the string `"null"` or `"undefined"`, producing `new Date("nullT00:00:00")` which is an `Invalid Date`. `Intl.DateTimeFormat.format(Invalid Date)` returns the literal string `"Invalid Date"` in Chromium-based browsers. This produces a visible data corruption string in the UI without throwing or logging an error, making it hard to detect.

**Fix:** Add a null guard at the start of `formatDate`:
```typescript
function formatDate(dateStr: string | null | undefined): string {
    if (!dateStr) return 'Date unknown';
    const date = new Date(dateStr + 'T00:00:00');
    return new Intl.DateTimeFormat('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric'
    }).format(date);
}
```
Apply the identical fix in both files.

---

## Info

### IN-01: ChatBubble utterance prop is untyped

**File:** `app/src/lib/components/ChatBubble.svelte:2`

**Issue:** `let { utterance } = $props();` has no TypeScript type annotation. The script block accesses `utterance.side`, `utterance.speaker_name`, `utterance.raw_speaker_label`, `utterance.speaker_role`, and `utterance.text`. Without a type, TypeScript cannot catch property name typos or API shape changes at compile time. Same issue applies to `StageDirection.svelte:2`.

**Fix:** Define a local type or import the shared utterance type from the API layer:
```typescript
type Utterance = {
    side: 'BENCH' | 'ADVOCATE' | 'UNKNOWN';
    speaker_name: string | null;
    raw_speaker_label: string | null;
    speaker_role: string | null;
    text: string;
    sequence: number;
    is_stage_direction: boolean;
    section_hint: string | null;
};
let { utterance }: { utterance: Utterance } = $props();
```

### IN-02: app.css has inconsistent indentation on --color-stage-accent

**File:** `app/src/app.css:12`

**Issue:** The `:root` block uses tab indentation for all CSS custom properties except `--color-stage-accent`, which has no leading whitespace (it starts at column 0). This is a cosmetic inconsistency that may indicate a copy-paste error during Phase 4 editing.

**Current:**
```css
:root {
    --color-bg: #0f1117;
    --color-surface: #1e293b;
    --color-border: #334155;
    --color-text-primary: #e2e8f0;
    --color-text-secondary: #94a3b8;
    --color-text-advocate: #93c5fd;
--color-stage-accent: #d97706;   /* <-- no indentation */
    --color-stage-text: #fcd34d;
    font-family: ...;
}
```

**Fix:** Add consistent leading tab to `--color-stage-accent: #d97706;`.

### IN-03: aria-label on ChatBubble degrades for UNKNOWN-side utterances with no speaker name

**File:** `app/src/lib/components/ChatBubble.svelte:20`

**Issue:** When `utterance.side` is `'UNKNOWN'` and `displayName` is `''`, the `aria-label` becomes `"Advocate: "` — a label with a trailing colon-space and no name. This is not a crash, but it provides no useful identification to screen reader users. The side mapping also silently equates `UNKNOWN` to `Advocate` in the label text, which could be confusing.

**Fix:** Handle the empty-name case in the aria-label:
```svelte
aria-label="{isBench ? 'Bench' : 'Advocate'}: {displayName || 'Unknown speaker'}"
```
This ensures screen readers always receive a meaningful label.

---

_Reviewed: 2026-06-15T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
