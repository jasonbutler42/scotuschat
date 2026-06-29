# Phase 10: Unified Navigation - Pattern Map

**Mapped:** 2026-06-22
**Files analyzed:** 3 (1 new, 2 modified)
**Analogs found:** 3 / 3

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/src/lib/components/TopNav.svelte` | component | request-response (SSR render, no data fetch) | `app/src/lib/components/MobileNavBar.svelte` | role-match (nav component, inline styles, variant-driven markup) |
| `app/src/routes/+layout.svelte` | layout | request-response | `app/src/routes/admin/+layout.svelte` | exact (same file type, same pattern: script + page guard + children render) |
| `app/src/routes/admin/+layout.svelte` | layout | request-response | `app/src/routes/+layout.svelte` | exact (symmetric — both are layout files with page guard and children render) |

---

## Pattern Assignments

### `app/src/lib/components/TopNav.svelte` (component, request-response)

**Analog:** `app/src/lib/components/MobileNavBar.svelte` (nav component; inline styles; conditional markup driven by prop)
**Secondary analog:** `app/src/lib/components/ChatBubble.svelte` (prop-derived const pattern; no $state for derived display values)

**Imports pattern** — from `app/src/lib/components/ChatBubble.svelte` lines 1–2, `app/src/lib/components/MobileNavBar.svelte` lines 1–5:
```svelte
<script lang="ts">
    // No imports needed — TopNav has no external dependencies.
    // ChatBubble pattern: no imports at all when no utilities are needed.
    // MobileNavBar imports '$app/environment' for browser guard — TopNav does NOT need this.
</script>
```

**Props declaration pattern** — from `app/src/lib/components/MobileNavBar.svelte` lines 3–5:
```svelte
<script lang="ts">
    type SectionAnchor = { hint: string; label: string; anchorId: string };
    let { sections }: { sections: SectionAnchor[] } = $props();
```
Apply to TopNav as:
```svelte
<script lang="ts">
    let { variant }: { variant: 'public' | 'admin' } = $props();
```

**Prop-derived const pattern (no $state)** — from `app/src/lib/components/ChatBubble.svelte` lines 4–9:
```svelte
    const isBench = utterance.side === 'BENCH';
    const labelColor = isBench ? '#94a3b8' : '#93c5fd';
    const avatarBg = isBench ? '#94a3b8' : '#93c5fd';
```
Apply to TopNav as:
```svelte
    const bgColor = variant === 'admin' ? '#1e293b' : '#0f1117';
```
Rule: prop-derived display values use plain `const`, never `$state`. The variant prop does not change after mount.

**Nav markup with inline styles** — from `app/src/routes/admin/+layout.svelte` lines 8–33 (the full nav block, verbatim source material):
```svelte
<header>
    <nav
        aria-label="Admin navigation"
        style="
            background-color: #1e293b;
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
        <a href="/admin/pipeline" style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;">
            Pipeline Runner
        </a>
        <a href="/admin/people" style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;">
            People Editor
        </a>
        <form method="POST" action="/admin?/logout" style="margin-left: auto;">
            ...
        </form>
    </nav>
</header>
```

**Logout button hover pattern** — from `app/src/routes/admin/+layout.svelte` lines 44–71 (carry verbatim, including `min-height: 44px` for WCAG 2.5.5):
```svelte
<form method="POST" action="/admin?/logout" style="margin-left: auto;">
    <button
        type="submit"
        style="
            min-height: 44px;
            font-size: 14px;
            font-weight: 400;
            color: #94a3b8;
            background: transparent;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 8px 16px;
            cursor: pointer;
        "
        onmouseenter={(e) => {
            const btn = e.currentTarget as HTMLButtonElement;
            btn.style.color = '#e2e8f0';
            btn.style.borderColor = '#e2e8f0';
        }}
        onmouseleave={(e) => {
            const btn = e.currentTarget as HTMLButtonElement;
            btn.style.color = '#94a3b8';
            btn.style.borderColor = '#334155';
        }}
    >
        Log out
    </button>
</form>
```
Note: Uses `onmouseenter`/`onmouseleave` (Svelte 5 attribute syntax), NOT `on:mouseenter`/`on:mouseleave` (Svelte 4 directive syntax).

**Conditional markup pattern** — from `app/src/lib/components/MobileNavBar.svelte` lines 33–76:
```svelte
{#if sections.length > 0}
    <nav ...>
        {#each sections as sec (sec.hint)}
            <button ...>{sec.label}</button>
        {/each}
    </nav>
{/if}
```
Apply to TopNav as:
```svelte
{#if variant === 'public'}
    <!-- public links -->
{:else}
    <!-- admin links -->
{/if}
```

**Public nav source markup** — from `app/src/routes/+layout.svelte` lines 8–34 (the full current public nav block):
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
        <a
            href="/cases"
            style="
                font-size: 13px;
                color: #93c5fd;
                text-decoration: none;
            "
        >
            Cases
        </a>
    </nav>
</header>
```
Note: The Cases link uses `13px` currently. RESEARCH.md resolves this to `14px` for standardization. The Admin link (D-01/D-02) is new markup — no current analog; add with `margin-left: auto` and `color: #94a3b8`.

---

### `app/src/routes/+layout.svelte` (layout, request-response)

**Analog:** `app/src/routes/admin/+layout.svelte` (symmetric layout; same script block pattern, same children render)

**Current file** (lines 1–38, read in full above) — this file is being edited, not replaced. The transformation is:
1. Add `import TopNav from '$lib/components/TopNav.svelte';` to script block
2. Keep `import { page } from '$app/state';` — the admin guard `{#if !page.url.pathname.startsWith('/admin')}` is preserved (see RESEARCH.md Pitfall 2 and Open Question 1)
3. Replace inline `<header>...</header>` block with `<TopNav variant="public" />`

**Script block pattern** — from `app/src/routes/+layout.svelte` lines 1–5 (current):
```svelte
<script lang="ts">
    import '../app.css';
    import { page } from '$app/state';
    let { children } = $props();
</script>
```
After edit:
```svelte
<script lang="ts">
    import '../app.css';
    import { page } from '$app/state';
    import TopNav from '$lib/components/TopNav.svelte';
    let { children } = $props();
</script>
```

**Guard + component usage pattern** — from `app/src/routes/+layout.svelte` lines 7–37 (current inline nav replaced):
```svelte
{#if !page.url.pathname.startsWith('/admin')}
    <TopNav variant="public" />
{/if}

{@render children()}
```

**`$lib` alias import pattern** — from `app/src/routes/admin/+layout.svelte` line 2 (existing CSS import shows path convention):
```svelte
import '../../app.css';
```
The `$lib` alias resolves to `src/lib/` — `import TopNav from '$lib/components/TopNav.svelte'` follows the established alias pattern used throughout page files in the project.

---

### `app/src/routes/admin/+layout.svelte` (layout, request-response)

**Analog:** `app/src/routes/+layout.svelte` (symmetric; same pattern)

**Current file** (lines 1–77, read in full above) — transformation:
1. Add `import TopNav from '$lib/components/TopNav.svelte';` to script block
2. Keep `import { page } from '$app/state';` — the login guard `{#if page.url.pathname !== '/admin/login'}` is preserved in this layout (per CONTEXT.md "Specific Ideas")
3. Replace inline `<header>...</header>` block with `<TopNav variant="admin" />`

**Script block pattern** — from `app/src/routes/admin/+layout.svelte` lines 1–5 (current):
```svelte
<script lang="ts">
    import '../../app.css';
    import { page } from '$app/state';
    let { children } = $props();
</script>
```
After edit:
```svelte
<script lang="ts">
    import '../../app.css';
    import { page } from '$app/state';
    import TopNav from '$lib/components/TopNav.svelte';
    let { children } = $props();
</script>
```

**Guard + component usage pattern** — from `app/src/routes/admin/+layout.svelte` lines 7–74 (current guard preserved, inner block replaced):
```svelte
{#if page.url.pathname !== '/admin/login'}
    <TopNav variant="admin" />
{/if}

{@render children()}
```

---

## Shared Patterns

### Svelte 5 Runes Props
**Source:** `app/src/lib/components/MobileNavBar.svelte` lines 3–5; `app/src/lib/components/ChatBubble.svelte` line 2
**Apply to:** `TopNav.svelte`
```svelte
let { variant }: { variant: 'public' | 'admin' } = $props();
```
- Always use `$props()` destructuring with inline TypeScript type annotation
- Never use `export let` (Svelte 4 legacy syntax)

### Prop-Derived Constants (no $state)
**Source:** `app/src/lib/components/ChatBubble.svelte` lines 4–9
**Apply to:** `TopNav.svelte`
```typescript
const bgColor = variant === 'admin' ? '#1e293b' : '#0f1117';
```
- Values derived from props that do not change after mount use plain `const`, never `$state`

### Inline Style Strings
**Source:** `app/src/routes/admin/+layout.svelte` lines 9–18; `app/src/lib/components/MobileNavBar.svelte` lines 37–50
**Apply to:** `TopNav.svelte` nav and button elements
```svelte
style="
    background-color: {bgColor};
    border-bottom: 1px solid #334155;
    padding: 12px 24px;
    display: flex;
    align-items: center;
    gap: 16px;
"
```
- Multi-line inline style strings with template literal interpolation for dynamic values
- No Tailwind utility classes on nav elements (existing nav markup uses inline styles throughout)

### Design Tokens (established, do not deviate)
**Source:** `app/src/routes/admin/+layout.svelte` (verified)
**Apply to:** All markup in `TopNav.svelte`

| Token | Value | Usage |
|-------|-------|-------|
| Admin nav bg | `#1e293b` | `variant='admin'` background |
| Public nav bg | `#0f1117` | `variant='public'` background |
| Border | `#334155` | Nav border-bottom, button border |
| Body text / muted links | `#94a3b8` | Wordmark, admin links, logout button |
| Accent blue | `#93c5fd` | Public Cases link |
| Hover text | `#e2e8f0` | Logout button hover color |

### Svelte 5 Event Handler Syntax
**Source:** `app/src/routes/admin/+layout.svelte` lines 58–67
**Apply to:** Logout button in `TopNav.svelte`
```svelte
onmouseenter={(e) => { ... }}
onmouseleave={(e) => { ... }}
```
- Use attribute-style handlers (`onmouseenter`), NOT Svelte 4 directive syntax (`on:mouseenter`)

### Layout Children Render
**Source:** `app/src/routes/+layout.svelte` line 37; `app/src/routes/admin/+layout.svelte` line 76
**Apply to:** Both layout files after edit
```svelte
{@render children()}
```
- `children` is always declared via `let { children } = $props();` in layout script block
- `{@render children()}` is always the last line in layout template

---

## No Analog Found

All three files have sufficient analogs. No file lacks a match.

---

## Critical Implementation Notes for Planner

1. **Root layout guard preserved:** Keep `{#if !page.url.pathname.startsWith('/admin')}` around `<TopNav variant="public" />` in `+layout.svelte`. Do NOT remove it — SvelteKit nested layouts cause double-nav if the root layout renders TopNav unconditionally on admin routes. The `$page` import stays.

2. **Admin layout guard preserved in layout, not moved into TopNav:** The `{#if page.url.pathname !== '/admin/login'}` guard stays in `admin/+layout.svelte`, wrapping `<TopNav variant="admin" />`. TopNav must not read `$page` or any URL state.

3. **Font size standardization:** Public nav `Cases` link currently uses `13px` (line 26 of `+layout.svelte`). TopNav uses `14px` for all links across both variants (resolved by RESEARCH.md).

4. **`min-height: 44px` on logout button is non-negotiable:** WCAG 2.5.5 touch target. Carry from `admin/+layout.svelte` line 48 verbatim.

5. **New Admin link in public nav:** No current analog in codebase — new markup. Style matches muted admin links: `font-size: 14px; color: #94a3b8; text-decoration: none; margin-left: auto;`.

---

## Metadata

**Analog search scope:** `app/src/lib/components/`, `app/src/routes/`, `app/src/routes/admin/`
**Files read:** 4 (both layout files, MobileNavBar.svelte, ChatBubble.svelte)
**Pattern extraction date:** 2026-06-22
