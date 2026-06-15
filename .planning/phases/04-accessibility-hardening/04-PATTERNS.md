# Phase 4: Accessibility + Hardening - Pattern Map

**Mapped:** 2026-06-15
**Files analyzed:** 8 (7 modified + 1 new)
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/src/app.css` | config | request-response | `app/src/app.css` (self) | self — surgical edit |
| `app/src/lib/components/ChatBubble.svelte` | component | request-response | `app/src/lib/components/ChatBubble.svelte` (self) | self — surgical edit |
| `app/src/lib/components/StageDirection.svelte` | component | request-response | `app/src/lib/components/StageDirection.svelte` (self) | self — surgical edit |
| `app/src/lib/components/SectionRail.svelte` | component | event-driven | `app/src/lib/components/SectionRail.svelte` (self) | self — surgical edit |
| `app/src/lib/components/MobileNavBar.svelte` | component | event-driven | `app/src/lib/components/SectionRail.svelte` | exact role + data flow |
| `app/src/routes/+layout.svelte` | component | request-response | `app/src/routes/+layout.svelte` (self) | self — surgical edit |
| `app/src/routes/cases/+page.svelte` | component | request-response | `app/src/routes/cases/+page.svelte` (self) | self — surgical edit |
| `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` | component | event-driven | `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` (self) | self — surgical edits |

---

## Pattern Assignments

### `app/src/app.css` (config, request-response)

**Change:** Remove `--color-text-sequence` variable (D-01); add global `*:focus-visible` rule (D-05–D-07).

**Current `:root` block** (lines 5–16):
```css
:root {
    --color-bg: #0f1117;
    --color-surface: #1e293b;
    --color-border: #334155;
    --color-text-primary: #e2e8f0;
    --color-text-secondary: #94a3b8;
    --color-text-advocate: #93c5fd;
    --color-text-sequence: #475569;   /* REMOVE this line — D-01 */
    --color-stage-accent: #d97706;
    --color-stage-text: #fcd34d;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
```

**Focus ring rule to add after existing `body` block** (after line 27):
```css
*:focus-visible {
    outline: 2px solid #93c5fd;
    outline-offset: 3px;
    border-radius: 4px;
}
```

**Surgical edits:**
1. Delete the `--color-text-sequence: #475569;` line (line 12).
2. Append the `*:focus-visible` block after the `body` rule.

---

### `app/src/lib/components/ChatBubble.svelte` (component, request-response)

**Changes:** Remove sequence `<span>` (D-01); fix role label color `#475569` → `#94a3b8` (D-02); add `role="article"` + `aria-label` to outer wrapper `<div>` (D-09).

**Current outer wrapper** (line 18):
```svelte
<div
    style="
        display: flex;
        justify-content: {isBench ? 'flex-start' : 'flex-end'};
    "
>
```
**Target outer wrapper** — add `role` and `aria-label`:
```svelte
<div
    role="article"
    aria-label="{isBench ? 'Bench' : 'Advocate'}: {displayName}"
    style="
        display: flex;
        justify-content: {isBench ? 'flex-start' : 'flex-end'};
    "
>
```

**Sequence `<span>` to remove entirely** (lines 52–61):
```svelte
<span
    style="
        font-size: 13px;
        color: #475569;
        font-weight: 400;
        padding-right: 4px;
    "
>
    {utterance.sequence}
</span>
```
Remove this block completely. The avatar circle and speaker name `<span>` remain.

**Role label `<span>` color fix** (line 70 — the `{#if displayRole}` inline):
```svelte
{#if displayRole}<span style="font-size: 11px; color: #475569;">{displayRole}</span>{/if}
```
Change `color: #475569` → `color: #94a3b8`:
```svelte
{#if displayRole}<span style="font-size: 11px; color: #94a3b8;">{displayRole}</span>{/if}
```

**Surgical edits (3 total, treated as one atomic task):**
1. Add `role="article"` and `aria-label` attributes to the outer `<div>` (line 18).
2. Delete the sequence number `<span>` block (lines 52–61).
3. Replace `color: #475569` with `color: #94a3b8` in the `displayRole` span (line 70).

---

### `app/src/lib/components/StageDirection.svelte` (component, request-response)

**Change:** Add `role="note"` to the outer `<div>` (D-10).

**Current outer `<div>`** (line 6):
```svelte
<div
    style="
        background-color: #1e293b;
        border-top: 1px solid #334155;
        ...
    "
>
```
**Target outer `<div>`:**
```svelte
<div
    role="note"
    style="
        background-color: #1e293b;
        border-top: 1px solid #334155;
        ...
    "
>
```

**Surgical edit:** Add `role="note"` attribute to the outer `<div>` (between line 6 `<div` and its `style=` attribute).

---

### `app/src/lib/components/SectionRail.svelte` (component, event-driven)

**Change:** Add `aria-label="Argument sections"` to the `<nav>` element (D-08, per UI-SPEC Interaction Contract).

**Current `<nav>`** (line 33):
```svelte
<nav style="position: sticky; top: 0; padding: 24px 16px; align-self: start;">
```
**Target `<nav>`:**
```svelte
<nav aria-label="Argument sections" style="position: sticky; top: 0; padding: 24px 16px; align-self: start;">
```

**Surgical edit:** Insert `aria-label="Argument sections"` attribute on the `<nav>` element.

---

### `app/src/lib/components/MobileNavBar.svelte` (component, event-driven) — NEW FILE

**Direct analog:** `app/src/lib/components/SectionRail.svelte` — identical role (section navigation), identical data flow (IntersectionObserver scroll-spy + scrollIntoView on click), identical prop shape (`sections: SectionAnchor[]`).

**Full analog source** (`SectionRail.svelte`, all 56 lines):

Script block — Runes pattern + IntersectionObserver (lines 1–31):
```svelte
<script lang="ts">
    import { browser } from '$app/environment';

    type SectionAnchor = { hint: string; label: string; anchorId: string };
    let { sections }: { sections: SectionAnchor[] } = $props();

    let activeSection = $state<string | null>(null);

    $effect(() => {
        if (!browser || sections.length === 0) return;

        const observers: IntersectionObserver[] = [];

        for (const sec of sections) {
            const el = document.getElementById(sec.anchorId);
            if (!el) continue;
            const obs = new IntersectionObserver(
                ([entry]) => {
                    if (entry.isIntersecting) {
                        activeSection = sec.hint;
                    }
                },
                { rootMargin: '-40% 0px -55% 0px', threshold: 0 }
            );
            obs.observe(el);
            observers.push(obs);
        }

        return () => observers.forEach((o) => o.disconnect());
    });
</script>
```

Button pattern — active state, scrollIntoView, label formatting (lines 34–55):
```svelte
<button
    onclick={() => document.getElementById(sec.anchorId)?.scrollIntoView({ behavior: 'smooth' })}
    style="
        background-color: {activeSection === sec.hint ? '#1e293b' : 'transparent'};
        color: {activeSection === sec.hint ? '#e2e8f0' : '#94a3b8'};
        border-left: 3px solid {activeSection === sec.hint ? '#93c5fd' : 'transparent'};
        font-weight: {activeSection === sec.hint ? 600 : 400};
    "
>
    {sec.label}
</button>
```

**MobileNavBar divergences from the analog** (per UI-SPEC D-11–D-13):

| SectionRail | MobileNavBar |
|-------------|--------------|
| `<nav style="position: sticky; top: 0; ...">` | `<nav aria-label="Argument sections" style="position: fixed; bottom: 0; left: 0; right: 0; ...">` |
| `display: block` vertical list of buttons | `display: flex; flex-direction: row; overflow-x: auto; gap: 8px; padding: 8px 16px` horizontal row |
| Button: `border-left: 3px solid` active indicator | Pill: `border-radius: 20px; padding: 6px 14px; border: 1px solid` (inactive `#334155`, active `#93c5fd`) |
| No hide condition in template | Wrap entire `<nav>` in `{#if sections.length > 0}` |
| Shown always (CSS media query hides at <768px externally) | Hidden via `display: none` in a `<style>` block at `@media (min-width: 768px)` |

**Complete MobileNavBar target structure:**
```svelte
<script lang="ts">
    import { browser } from '$app/environment';

    type SectionAnchor = { hint: string; label: string; anchorId: string };
    let { sections }: { sections: SectionAnchor[] } = $props();

    let activeSection = $state<string | null>(null);

    $effect(() => {
        if (!browser || sections.length === 0) return;

        const observers: IntersectionObserver[] = [];

        for (const sec of sections) {
            const el = document.getElementById(sec.anchorId);
            if (!el) continue;
            const obs = new IntersectionObserver(
                ([entry]) => {
                    if (entry.isIntersecting) {
                        activeSection = sec.hint;
                    }
                },
                { rootMargin: '-40% 0px -55% 0px', threshold: 0 }
            );
            obs.observe(el);
            observers.push(obs);
        }

        return () => observers.forEach((o) => o.disconnect());
    });
</script>

{#if sections.length > 0}
    <nav
        aria-label="Argument sections"
        style="
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background-color: #1e293b;
            border-top: 1px solid #334155;
            display: flex;
            flex-direction: row;
            overflow-x: auto;
            gap: 8px;
            padding: 8px 16px;
            min-height: 44px;
            align-items: center;
        "
    >
        {#each sections as sec (sec.hint)}
            <button
                onclick={() => document.getElementById(sec.anchorId)?.scrollIntoView({ behavior: 'smooth' })}
                style="
                    border-radius: 20px;
                    padding: 6px 14px;
                    font-size: 13px;
                    font-weight: {activeSection === sec.hint ? 600 : 400};
                    cursor: pointer;
                    white-space: nowrap;
                    background-color: transparent;
                    color: {activeSection === sec.hint ? '#e2e8f0' : '#94a3b8'};
                    border: 1px solid {activeSection === sec.hint ? '#93c5fd' : '#334155'};
                "
            >
                {sec.label}
            </button>
        {/each}
    </nav>
{/if}

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

### `app/src/routes/+layout.svelte` (component, request-response)

**Changes:** The outer element is already `<nav>` (not a `<div>`). Per UI-SPEC Interaction Contract, the `<nav>` receives `aria-label="Site navigation"` (D-08). There is no separate `<header>` wrapper in the layout file — the `<nav>` IS the site header bar; wrap it in `<header>` per D-08 decision.

**Current structure** (lines 6–31):
```svelte
<nav
    style="
        background-color: #0f1117;
        border-bottom: 1px solid #334155;
        padding: 12px 24px;
        display: flex;
        align-items: center;
        gap: 16px;
    "
>
    <span style="font-size: 14px; font-weight: 600; color: #94a3b8; letter-spacing: 0.05em;">
        SCOTUS CHAT
    </span>
    <a href="/cases" style="font-size: 13px; color: #93c5fd; text-decoration: none;">
        Cases
    </a>
</nav>

{@render children()}
```

**Target structure** — wrap in `<header>`, add `aria-label` to `<nav>`:
```svelte
<header>
    <nav
        aria-label="Site navigation"
        style="
            background-color: #0f1117;
            border-bottom: 1px solid #334155;
            padding: 12px 24px;
            display: flex;
            align-items: center;
            gap: 16px;
        "
    >
        <span style="font-size: 14px; font-weight: 600; color: #94a3b8; letter-spacing: 0.05em;">
            SCOTUS CHAT
        </span>
        <a href="/cases" style="font-size: 13px; color: #93c5fd; text-decoration: none;">
            Cases
        </a>
    </nav>
</header>

{@render children()}
```

**Surgical edits:**
1. Wrap `<nav>...</nav>` in `<header>...</header>`.
2. Add `aria-label="Site navigation"` to the `<nav>` element.

---

### `app/src/routes/cases/+page.svelte` (component, request-response)

**Changes:** Replace outer `<div>` with `<main>` (D-08); replace top-bar `<div>` with `<header>` (D-08).

**Current outer wrapper** (line 22):
```svelte
<div style="background-color: #0f1117; min-height: 100vh;">
```
**Target:**
```svelte
<main style="background-color: #0f1117; min-height: 100vh;">
```

**Current top-bar `<div>`** (lines 24–43):
```svelte
<div
    style="
        background-color: #1e293b;
        border-bottom: 1px solid #334155;
        padding: 16px 24px;
    "
>
    <h1 ...>Cases</h1>
</div>
```
**Target:**
```svelte
<header
    style="
        background-color: #1e293b;
        border-bottom: 1px solid #334155;
        padding: 16px 24px;
    "
>
    <h1 ...>Cases</h1>
</header>
```

**Surgical edits:**
1. Line 22: `<div style="background-color: #0f1117; min-height: 100vh;">` → `<main style="...">`; closing `</div>` (line 117) → `</main>`.
2. Lines 24–43: opening `<div style="background-color: #1e293b; ...">` → `<header style="...">` (same style string); closing `</div>` (line 43) → `</header>`.

---

### `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` (component, event-driven)

**Changes:** Replace outer `<div>` with `<main>` (D-08); replace heading-bar `<div>` with `<header>` (D-08); fix roster column header colors `#475569` → `#94a3b8` (D-03); integrate `MobileNavBar` with `sectionAnchors` prop; add `padding-bottom: 60px` to chat column `<div>` (D-11–D-13).

**Import addition** (after line 4):
```svelte
import MobileNavBar from '$lib/components/MobileNavBar.svelte';
```

**Current outer wrapper** (line 69):
```svelte
<div style="background-color: #0f1117; min-height: 100vh;">
```
**Target:**
```svelte
<main style="background-color: #0f1117; min-height: 100vh;">
```
Closing `</div>` (line 211) → `</main>`.

**Current heading-bar `<div>`** (lines 71–77):
```svelte
<div
    style="
        background-color: #1e293b;
        border-bottom: 1px solid #334155;
        padding: 16px 24px;
    "
>
```
**Target:**
```svelte
<header
    style="
        background-color: #1e293b;
        border-bottom: 1px solid #334155;
        padding: 16px 24px;
    "
>
```
Closing `</div>` (line 159) → `</header>`.

**Roster column header color fix** — two occurrences, lines 110–116 and 135–141:
```svelte
<!-- Current (both occurrences): -->
color: #475569;

<!-- Target (both occurrences): -->
color: #94a3b8;
```

**Chat column `padding-bottom` addition** (line 174):
```svelte
<!-- Current: -->
<div style="padding: 48px 24px;">

<!-- Target: -->
<div style="padding: 48px 24px 60px 24px;">
```
The `60px` bottom padding prevents the last utterance from being obscured by the fixed `MobileNavBar` on small screens. On large screens the `MobileNavBar` is hidden, making the extra padding a minor no-op (acceptable per UI-SPEC spacing exceptions).

**MobileNavBar integration** — add after the closing `</div>` of the two-column grid (after line 210, before `</main>`):
```svelte
<MobileNavBar sections={sectionAnchors} />
```

**Surgical edits (6 total, treated as grouped tasks):**
1. Line 69: `<div>` → `<main>` (outer wrapper); line 211 `</div>` → `</main>`.
2. Lines 71–77: `<div>` → `<header>` (heading bar); line 159 `</div>` → `</header>`.
3. Line 113: `color: #475569` → `color: #94a3b8` (Bench column header).
4. Line 138: `color: #475569` → `color: #94a3b8` (Advocates column header).
5. Line 174: `padding: 48px 24px` → `padding: 48px 24px 60px 24px` (chat column bottom padding).
6. Add `import MobileNavBar` + `<MobileNavBar sections={sectionAnchors} />` after the content grid closing tag.

---

## Shared Patterns

### Svelte 5 Runes — prop and state declarations
**Source:** Every existing component (e.g., `SectionRail.svelte` lines 1–7)
**Apply to:** `MobileNavBar.svelte` (new component)
```svelte
let { sections }: { sections: SectionAnchor[] } = $props();
let activeSection = $state<string | null>(null);
```
No `export let`. No `$:` reactive blocks. No legacy stores.

### browser-guard on IntersectionObserver
**Source:** `app/src/lib/components/SectionRail.svelte` lines 9–30
**Apply to:** `MobileNavBar.svelte`
```svelte
$effect(() => {
    if (!browser || sections.length === 0) return;
    // ... observer setup ...
    return () => observers.forEach((o) => o.disconnect());
});
```
`$effect` cleanup function (`return () => ...`) is mandatory for observer teardown.

### Inline styles (no Svelte `<style>` blocks for component styles)
**Source:** All existing components — `ChatBubble.svelte`, `StageDirection.svelte`, `SectionRail.svelte`
**Apply to:** `MobileNavBar.svelte`
All per-element styles use `style=""` attributes. The `<style>` block is reserved for media queries only (see argument page `<style>` block at lines 214–222).

### Media query breakpoint — 768px
**Source:** `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` lines 215–222
**Apply to:** `MobileNavBar.svelte` `<style>` block
```svelte
<style>
    @media (max-width: 768px) {
        /* show mobile element */
    }
</style>
```
`MobileNavBar` uses `max-width: 768px` to show; default is `display: none` (hidden on desktop).

### Dark palette constants
**Source:** `app/src/app.css` lines 5–16; used verbatim as hex literals throughout all components
**Apply to:** `MobileNavBar.svelte`
```
#0f1117  — page background
#1e293b  — surface (mobile nav bar background)
#334155  — border (inactive pill border, nav bar top border)
#e2e8f0  — primary text (active pill label)
#94a3b8  — muted text (inactive pill label)
#93c5fd  — accent (active pill border, focus ring)
```
All components use hex literals inline, not CSS variable references.

---

## No Analog Found

No files in Phase 4 are without analog. All 8 files have either a self-analog (surgical edit to existing file) or an exact role+data-flow match (`MobileNavBar` ↔ `SectionRail`).

---

## Metadata

**Analog search scope:** `app/src/lib/components/`, `app/src/routes/`, `app/src/app.css`
**Files read:** 8
**Pattern extraction date:** 2026-06-15
