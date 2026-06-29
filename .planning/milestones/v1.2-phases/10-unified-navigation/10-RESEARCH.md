# Phase 10: Unified Navigation — Research

**Researched:** 2026-06-22
**Domain:** SvelteKit 2.x layout refactor — Svelte 5 Runes shared component extraction
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Public nav gains an "Admin" link pushed to far right (margin-left: auto). Links to `/admin`, muted style (`#94a3b8`, 14px, no decoration). Non-operators who click it hit the login redirect at `/admin/login`.
- **D-02:** Public nav link layout: `SCOTUS CHAT [wordmark] | Cases | [flex spacer] Admin`. Admin is right-aligned.
- **D-03:** `TopNav` accepts a single prop: `variant: 'public' | 'admin'`. Layouts pass it explicitly — the component never reads `$page.url.pathname`.
- **D-04:** Root layout passes `variant="public"`, admin layout passes `variant="admin"`.
- **D-05:** Logout button lives inside `TopNav` as conditional markup guarded by `{#if variant === 'admin'}`. Component fully owns the entire nav bar.
- **D-06:** Logout button preserves inline `onmouseenter`/`onmouseleave` hover (color `#94a3b8 → #e2e8f0`, border `#334155 → #e2e8f0`).
- **D-07:** Logout button form: `<form method="POST" action="/admin?/logout">` with `margin-left: auto`.
- **D-08:** Background is variant-driven: `variant='public'` → `#0f1117`; `variant='admin'` → `#1e293b`.
- **D-09:** Admin nav links: `SCOTUS CHAT | Pipeline Runner → /admin/pipeline | People Editor → /admin/people | [spacer] Log out`.
- **D-10:** Public nav links: `SCOTUS CHAT | Cases → /cases | [spacer] Admin → /admin`.

### Claude's Discretion

- Exact font size for nav links: standardized to **14px** for all links across both variants (UI-SPEC resolved this — admin nav already used 14px throughout; public nav "Cases" link was 13px — standardized up).
- "SCOTUS CHAT" wordmark: **plain `<span>`** in both variants (not a link). Matches current behavior; argument chat pages are primary content.
- Active-link styling: **none added**. Both current navs have none; deferred per CONTEXT.md.
- Component file name: `TopNav.svelte` (PascalCase, follows existing convention).

### Deferred Ideas (OUT OF SCOPE)

- Active-link highlighting (bold or accent color on current page's nav link) — not in NAV-01 scope
- Mobile nav changes — MobileNavBar is a separate component, unchanged by this phase
- Breadcrumbs or secondary navigation — out of scope; not a v1.2 requirement

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NAV-01 | Admin and public pages share the same top navigation component, with links to both the public case list and the admin area visible from either view | All decisions locked in CONTEXT.md; TopNav.svelte creation + layout updates directly close this requirement |

</phase_requirements>

---

## Summary

Phase 10 is a pure Svelte 5 frontend refactor. There are no new packages, no backend changes, no database changes, and no new routes. The deliverable is three file edits: create `app/src/lib/components/TopNav.svelte`, update `app/src/routes/+layout.svelte`, and update `app/src/routes/admin/+layout.svelte`.

The existing nav markup in both layout files is nearly complete source material — the component is built by extracting that markup, parameterizing it via a `variant` prop, and wiring both layouts to the new component. All design decisions are locked in CONTEXT.md and codified in the UI-SPEC. No external research is needed for this phase beyond what is already in the project artifacts.

The single non-obvious concern is **guard placement**: the root layout's `{#if !page.url.pathname.startsWith('/admin')}` guard disappears entirely (admin pages now use their own layout's `<TopNav variant="admin" />`), while the admin layout's `{#if page.url.pathname !== '/admin/login'}` guard is preserved in the layout — not moved into TopNav. TopNav must remain a stateless display component that never reads `$page`.

**Primary recommendation:** Extract nav markup from both layouts into a single `TopNav.svelte` component with a `variant: 'public' | 'admin'` prop, following the exact `$props()` pattern used by all existing components. Three file edits, no new dependencies.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Nav component rendering | Browser / Client (SSR) | — | Svelte layout component; renders on server during SSR, hydrates on client |
| Context detection (public vs. admin) | Frontend Server (SSR) — Layout | — | Layouts own the variant prop decision; TopNav is a dumb display component |
| Login page suppression | Frontend Server (SSR) — Admin Layout | — | Guard stays in `admin/+layout.svelte`, not in TopNav (TopNav has no URL awareness) |
| Logout action | API / Backend — SvelteKit action | — | `<form method="POST" action="/admin?/logout">` targets named action in `admin/+page.server.ts` |

---

## Standard Stack

### Core

No new packages required. This phase uses only what is already installed.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SvelteKit | 2.x (installed) | Layout system, file-based routing | Project stack |
| Svelte 5 | 5.x (installed) | Runes component model (`$props()`, `$state`, `$derived`) | Project stack |

[VERIFIED: project codebase — `app/package.json` and existing components confirm Svelte 5 Runes already in use]

### Supporting

None — no supporting libraries needed beyond existing stack.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline styles (current pattern) | Tailwind CSS classes | Tailwind is installed but nav uses inline styles throughout. CONTEXT.md says "Continue this pattern" — maintain consistency. |
| `variant` prop | `$page.url.pathname` read inside component | CONTEXT.md D-03 forbids URL reads inside TopNav — prop is the locked approach. |

**Installation:** No new packages to install.

---

## Package Legitimacy Audit

No external packages are added by this phase. This section is not applicable.

---

## Architecture Patterns

### System Architecture Diagram

```
Root layout (+layout.svelte)
  │  variant="public"
  └──► TopNav.svelte
         │  {#if variant === 'public'}
         │    <span>SCOTUS CHAT</span>
         │    <a href="/cases">Cases</a>
         │    <a href="/admin" style="margin-left:auto">Admin</a>
         └──

Admin layout (admin/+layout.svelte)
  │  {#if page.url.pathname !== '/admin/login'}   ← guard stays in layout
  │    variant="admin"
  └──► TopNav.svelte
         │  {#if variant === 'admin'}
         │    <span>SCOTUS CHAT</span>
         │    <a href="/admin/pipeline">Pipeline Runner</a>
         │    <a href="/admin/people">People Editor</a>
         │    <form action="/admin?/logout" style="margin-left:auto">
         │      <button>Log out</button>
         └──
```

Data flow: layout decides `variant` → passes to TopNav → TopNav renders appropriate markup. No data fetching, no state, no side effects.

### Recommended Project Structure

No new directories. New file:

```
app/src/
├── lib/
│   └── components/
│       ├── ChatBubble.svelte        (existing)
│       ├── MobileNavBar.svelte      (existing)
│       ├── SectionRail.svelte       (existing)
│       ├── StageDirection.svelte    (existing)
│       └── TopNav.svelte            ← NEW
└── routes/
    ├── +layout.svelte               (EDIT: replace inline header with <TopNav variant="public" />)
    └── admin/
        └── +layout.svelte           (EDIT: replace inline header with {#if guard}<TopNav variant="admin" />{/if})
```

### Pattern 1: Svelte 5 Runes Props

**What:** All components declare props via `$props()` destructuring with explicit TypeScript type annotation.
**When to use:** Every component that receives data from its parent — this is the only supported props pattern in Svelte 5.

```typescript
// Source: app/src/lib/components/ChatBubble.svelte (verified in codebase)
// and app/src/lib/components/MobileNavBar.svelte
let { utterance } = $props();

// TopNav.svelte — apply this pattern:
let { variant }: { variant: 'public' | 'admin' } = $props();
```

[VERIFIED: project codebase — all four existing components use this pattern]

### Pattern 2: Variant-Driven Derived Value

**What:** A single `const` derives a display value from the variant prop. No `$state`, no reactivity needed — the variant prop does not change after mount.
**When to use:** When component appearance depends on a prop that is set once at render time.

```typescript
// Inside TopNav.svelte <script>
const bgColor = variant === 'admin' ? '#1e293b' : '#0f1117';
```

[VERIFIED: project codebase — matches CONTEXT.md "Specific Ideas" section verbatim]

### Pattern 3: Inline Hover State via Svelte 5 Event Handlers

**What:** Direct style mutation in `onmouseenter`/`onmouseleave` inline handlers. No `$state` needed because this is ephemeral interaction state that does not need to survive beyond the event.
**When to use:** Simple two-state hover effects on a single element where reactivity would be overkill.

```typescript
// Source: app/src/routes/admin/+layout.svelte (existing logout button — carry verbatim)
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
```

[VERIFIED: project codebase — `app/src/routes/admin/+layout.svelte` lines 58–67]

### Pattern 4: Layout Component Import

**What:** Import a shared component in a layout file and pass a literal prop value.
**When to use:** Layouts that need a shared chrome element.

```svelte
<!-- app/src/routes/+layout.svelte after refactor -->
<script lang="ts">
    import '../app.css';
    import TopNav from '$lib/components/TopNav.svelte';
    let { children } = $props();
</script>

<TopNav variant="public" />
{@render children()}
```

[VERIFIED: project codebase — `$lib` alias resolves to `src/lib/` per `app/tsconfig.json` and existing import patterns in page files]

### Anti-Patterns to Avoid

- **Reading `$page` inside TopNav:** CONTEXT.md D-03 locks this out. TopNav must be a stateless display component. The `$page` import from `$app/state` must NOT appear in `TopNav.svelte`.
- **Moving the login guard into TopNav:** CONTEXT.md "Specific Ideas" explicitly says the guard stays in `admin/+layout.svelte`. Moving it would make TopNav aware of URL state.
- **Removing the root layout's admin guard without replacing it:** The root layout currently has `{#if !page.url.pathname.startsWith('/admin')}` to prevent double nav on admin pages. After the refactor, admin pages use `admin/+layout.svelte` which has its own `<TopNav variant="admin" />`. The root layout's guard must be removed AND the `$page` import removed (it becomes unused). Leaving the guard in place would silently suppress the public nav on admin pages.
- **Using `$state` for variant-derived values:** `bgColor` is a constant derived from props — use a plain `const`, not `$state`. Using `$state` for immutable derived values is an anti-pattern in Svelte 5 Runes.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Right-aligning the last nav item | Custom flexbox wrapper with absolute positioning | `margin-left: auto` on the rightmost element | Already the pattern in both existing navs; simpler and robust |
| Variant detection | URL-reading logic inside component | `variant` prop passed from layout | Locked by CONTEXT.md D-03; avoids coupling component to router |
| Hover state | `$state` + `$derived` reactive variable | Inline `onmouseenter`/`onmouseleave` style mutation | Matches existing admin layout pattern exactly; no reactive overhead needed |

---

## Runtime State Inventory

Step 2.5 SKIPPED — this is a greenfield component creation + markup extraction, not a rename/refactor of stored identifiers. No runtime state is affected (no database tables, no stored keys, no OS registrations).

---

## Common Pitfalls

### Pitfall 1: Stale `$page` Import in Root Layout

**What goes wrong:** After removing the `{#if !page.url.pathname.startsWith('/admin')}` guard from `+layout.svelte`, the `page` import from `$app/state` becomes unused. If left in place, `svelte-check` will warn. TypeScript strict mode is enabled.
**Why it happens:** The import was only needed for the guard condition.
**How to avoid:** Remove the `import { page } from '$app/state'` line when removing the guard. The layout still needs `let { children } = $props()` and the `import '../app.css'` — keep those.
**Warning signs:** `svelte-check` output showing unused import warning.

### Pitfall 2: Double Nav on Admin Pages

**What goes wrong:** If the root layout's guard is removed but the root layout still renders `<TopNav variant="public" />`, admin pages will show both the public nav (from root layout) and the admin nav (from admin layout) stacked.
**Why it happens:** SvelteKit layout nesting means the root layout renders for all routes, including admin routes.
**How to avoid:** The root layout's guard (`{#if !page.url.pathname.startsWith('/admin')}`) was preventing double nav. After the refactor, the admin layout has its own `<TopNav variant="admin" />`, so the root layout's nav must not also render on admin pages. Solution: the root layout simply renders `<TopNav variant="public" />` with no guard — this is correct because SvelteKit only applies the root layout's content in the `{@render children()}` slot for the admin sub-layout. The root layout's TopNav renders on public routes; the admin layout's TopNav renders on admin routes. They do not stack.

Actually the correct mental model: in SvelteKit, layouts at different levels are independent. `app/src/routes/+layout.svelte` renders for all routes, but `app/src/routes/admin/+layout.svelte` is nested inside it. The root layout's `{@render children()}` call renders the admin layout, which renders `<TopNav variant="admin" />`. So the root layout would also render `<TopNav variant="public" />` — resulting in two navbars on admin pages.

**Correct approach:** The root layout needs to remain guard-aware, OR the admin layout is structured differently. Looking at the CONTEXT.md canonical guidance: "Remove the `!page.url.pathname.startsWith('/admin')` guard (TopNav handles its own rendering per variant; admin layout has its own TopNav)." This implies the guard IS removed. But the root layout's `<TopNav variant="public" />` would then render on admin pages too.

Re-reading CONTEXT.md Integration Points more carefully: "Replace inline `<header>` block with `<TopNav variant="public" />`. Remove the `!page.url.pathname.startsWith('/admin')` guard." The intent is that the guard is removed because the admin sub-layout manages its own nav separately. In SvelteKit, nested layouts render inside the parent's `{@render children()}`. The parent's `<TopNav variant="public" />` would appear above the admin layout's content.

**Resolution:** The root layout still needs some form of guard or the public TopNav will appear on admin pages. The CONTEXT.md statement "TopNav handles its own rendering per variant; admin layout has its own TopNav" may mean the guard should move — keeping `{#if !page.url.pathname.startsWith('/admin')}` around `<TopNav variant="public" />` in the root layout is the safe approach, with the `$page` import retained for that purpose. Alternatively, if the project's SvelteKit config uses layout groups or reset layouts, the admin layout may fully replace rather than extend the root layout — verify this in `admin/+layout.svelte` and the route structure before removing the guard.

**Warning signs:** Admin pages showing two nav bars stacked. Check this immediately after implementation.

### Pitfall 3: Missing `import` in Layout After Adding TopNav

**What goes wrong:** Svelte components must be imported before use. `<TopNav variant="public" />` in `+layout.svelte` without `import TopNav from '$lib/components/TopNav.svelte'` causes a build error.
**Why it happens:** Easy to omit when doing a quick markup swap.
**How to avoid:** Add the import in the `<script lang="ts">` block of each layout file.
**Warning signs:** SvelteKit build error or `svelte-check` "cannot find name 'TopNav'" error.

### Pitfall 4: Logout Button Losing Touch Target Size

**What goes wrong:** The logout button has `min-height: 44px` for WCAG 2.5.5 compliance. If this is omitted when copying the button markup into TopNav, the button shrinks on mobile.
**Why it happens:** The spec is easy to miss when transcribing inline styles.
**How to avoid:** Carry the full button style block verbatim from `admin/+layout.svelte` lines 45–68.
**Warning signs:** Logout button appears visually smaller than before.

---

## Code Examples

Verified patterns from existing codebase:

### Complete TopNav.svelte Structure

```svelte
<!-- Source: extracted and parameterized from app/src/routes/+layout.svelte
     and app/src/routes/admin/+layout.svelte -->
<script lang="ts">
    let { variant }: { variant: 'public' | 'admin' } = $props();
    const bgColor = variant === 'admin' ? '#1e293b' : '#0f1117';
</script>

<header>
    <nav
        aria-label={variant === 'admin' ? 'Admin navigation' : 'Site navigation'}
        style="
            background-color: {bgColor};
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

        {#if variant === 'public'}
            <a href="/cases" style="font-size: 14px; color: #93c5fd; text-decoration: none;">
                Cases
            </a>
            <a
                href="/admin"
                style="font-size: 14px; color: #94a3b8; text-decoration: none; margin-left: auto;"
            >
                Admin
            </a>
        {:else}
            <a href="/admin/pipeline" style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;">
                Pipeline Runner
            </a>
            <a href="/admin/people" style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;">
                People Editor
            </a>
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
        {/if}
    </nav>
</header>
```

### Root Layout After Refactor

The critical question is whether to keep the admin guard. See Pitfall 2. The planner must resolve this: either keep the `$page` guard or verify that SvelteKit's nested layout system prevents the double-nav problem without it. Based on the codebase's current pattern (guard exists) and CONTEXT.md guidance (remove it), the planner should test the SvelteKit layout behavior and keep the guard if double-nav occurs.

```svelte
<!-- app/src/routes/+layout.svelte — safe version keeping admin guard -->
<script lang="ts">
    import '../app.css';
    import { page } from '$app/state';
    import TopNav from '$lib/components/TopNav.svelte';
    let { children } = $props();
</script>

{#if !page.url.pathname.startsWith('/admin')}
    <TopNav variant="public" />
{/if}

{@render children()}
```

### Admin Layout After Refactor

```svelte
<!-- app/src/routes/admin/+layout.svelte -->
<script lang="ts">
    import '../../app.css';
    import { page } from '$app/state';
    import TopNav from '$lib/components/TopNav.svelte';
    let { children } = $props();
</script>

{#if page.url.pathname !== '/admin/login'}
    <TopNav variant="admin" />
{/if}

{@render children()}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Svelte legacy stores (`$store` syntax) | Svelte 5 Runes (`$props()`, `$state`, `$derived`) | Svelte 5 (project already uses Runes) | Must use Runes in TopNav — no legacy stores |
| `on:mouseenter` event directive | `onmouseenter` handler attribute | Svelte 5 | Both existing layouts already use the new syntax; TopNav must use `onmouseenter` not `on:mouseenter` |

**Deprecated/outdated:**
- `on:click`, `on:mouseenter` etc. (Svelte 4 event directives): Replaced by `onclick`, `onmouseenter` attributes in Svelte 5. The existing codebase already uses Svelte 5 syntax — confirm this is maintained in TopNav.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | SvelteKit nested layouts render the root layout's content (including any TopNav) above the admin layout's content, causing a double-nav problem if the admin guard is removed from root layout | Common Pitfalls — Pitfall 2, Code Examples | If wrong: root layout guard can be removed safely and the layout structure is cleaner than documented |
| A2 | The `$page` import is only used for the admin guard in root layout — removing the guard means removing the import | Common Pitfalls — Pitfall 1 | Low risk — easy to verify with svelte-check |

**Note on A1:** CONTEXT.md says to remove the guard, but the SvelteKit layout nesting behavior makes this risky without verification. The research recommends keeping the guard as a safe default and testing the no-guard approach. The planner should add a verification step.

---

## Open Questions

1. **Should the root layout's admin guard be removed?**
   - What we know: CONTEXT.md says to remove it. SvelteKit nested layout nesting means root layout renders for all routes.
   - What's unclear: Does SvelteKit's layout nesting cause the root layout's `<TopNav variant="public" />` to appear on admin pages if the guard is removed? In SvelteKit, a child layout is rendered inside the parent's `{@render children()}` slot, so the parent's nav would appear above the child layout. This would cause double nav.
   - Recommendation: Keep the guard (`{#if !page.url.pathname.startsWith('/admin')}`) in the root layout as shown in the Code Examples above. This matches the current approach and is the safe choice. The CONTEXT.md statement "TopNav handles its own rendering per variant" is better interpreted as "TopNav handles rendering its own markup given a variant" — not that it somehow prevents parent layout markup from appearing.

2. **Font size — Cases link in public nav**
   - What we know: UI-SPEC resolves this to 14px for standardization. The current public nav uses 13px.
   - What's unclear: Nothing — UI-SPEC has made the call.
   - Recommendation: Use 14px in TopNav for the Cases link. This is already resolved by the UI-SPEC.

---

## Environment Availability

Step 2.6 SKIPPED — this phase is purely frontend code changes with no external tool dependencies. No new CLIs, services, runtimes, or external dependencies beyond what is already running.

---

## Validation Architecture

`nyquist_validation` is explicitly set to `false` in `.planning/config.json`. This section is skipped per config.

---

## Security Domain

This phase has no authentication changes, no new data-handling surfaces, no new API endpoints, and no user input beyond the logout form POST (unchanged from current implementation). The logout form POST to `/admin?/logout` is pre-existing and unchanged.

**ASVS scope:** No new ASVS categories are introduced by this phase. The logout form preserves SvelteKit's built-in CSRF protection (same form, same action target). No security review required beyond confirming the logout action is unchanged.

**Apolitical constraint:** Navigation links reference admin tools and public case list — no editorial content, no derived insights, no statistics. The "Admin" link in public nav is a navigation affordance, not content. Apolitical framing constraint is not implicated.

---

## Sources

### Primary (HIGH confidence)
- `app/src/routes/+layout.svelte` — current public nav markup, exact styles, font sizes, guard condition
- `app/src/routes/admin/+layout.svelte` — current admin nav markup, logout button with hover handlers, login guard condition
- `app/src/lib/components/ChatBubble.svelte` — canonical `$props()` pattern, inline style conventions
- `.planning/phases/10-unified-navigation/10-CONTEXT.md` — all locked decisions D-01 through D-10
- `.planning/phases/10-unified-navigation/10-UI-SPEC.md` — typography, color, spacing, copywriting contracts

### Secondary (MEDIUM confidence)
- `.planning/codebase/CONVENTIONS.md` — Svelte 5 Runes patterns, PascalCase naming, no data fetching in components
- `.planning/codebase/STRUCTURE.md` — component directory location, layout nesting

### Tertiary (LOW confidence)
- None — all claims verified against project codebase directly.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all verified against installed codebase
- Architecture: HIGH — all decisions locked in CONTEXT.md; current files read directly
- Pitfalls: HIGH for Pitfall 1, 3, 4 (verified from codebase); MEDIUM for Pitfall 2 (SvelteKit layout nesting behavior — see Assumptions Log A1)

**Research date:** 2026-06-22
**Valid until:** 2026-07-22 (stable domain — SvelteKit layout behavior does not change between minor versions)
