# Phase 10: Unified Navigation - Context

**Gathered:** 2026-06-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 10 delivers:

1. **`TopNav.svelte`** — a new shared component in `app/src/lib/components/` that renders the top navigation bar for both public and admin contexts
2. **Root layout update** — `app/src/routes/+layout.svelte` replaces its inline nav markup with `<TopNav variant="public" />`
3. **Admin layout update** — `app/src/routes/admin/+layout.svelte` replaces its inline nav markup with `<TopNav variant="admin" />`

Out of scope: user accounts, search, mobile nav changes (MobileNavBar is unchanged), active-link highlighting, breadcrumbs, any new admin pages.

</domain>

<decisions>
## Implementation Decisions

### Admin Link in Public Nav

- **D-01:** The public nav gains an "Admin" link pushed to the far right (margin-left: auto). It links to `/admin` and uses the same muted style as other nav links (`#94a3b8`, 13–14px, no decoration). It is visually quiet — not a primary call to action. Non-operators who click it hit the login redirect at `/admin/login`.
- **D-02:** Public nav link layout: `SCOTUS CHAT [wordmark] | Cases | [flex spacer] Admin`. Admin is right-aligned.

### Context Detection (Prop Strategy)

- **D-03:** `TopNav` accepts a single prop: `variant: 'public' | 'admin'`. Layouts pass it explicitly — the component never reads `$page.url.pathname`. This follows the existing Svelte 5 Runes `$props()` convention.
- **D-04:** Each layout file passes the prop: root layout passes `variant="public"`, admin layout passes `variant="admin"`.

### Logout Button Ownership

- **D-05:** The logout button lives **inside `TopNav`** as conditional markup guarded by `{#if variant === 'admin'}`. The component fully owns the entire nav bar. Admin layout renders simply `<TopNav variant="admin" />` with no extra markup.
- **D-06:** Logout button preserves the hover state from the current implementation (onmouseenter/onmouseleave inline JS changing color `#94a3b8 → #e2e8f0` and border `#334155 → #e2e8f0`). Matches Phase 6/7 admin UI pattern.
- **D-07:** Logout button form: `<form method="POST" action="/admin?/logout">` with `margin-left: auto` to push it right.

### Background Colors

- **D-08:** Background color is **variant-driven**: `variant='public'` → `#0f1117`; `variant='admin'` → `#1e293b`. Keeps the existing visual distinction that signals "you are in admin territory." Both are established tokens from the admin dark theme.

### Admin Nav Link Set

- **D-09:** Admin nav links: `SCOTUS CHAT [wordmark] | Pipeline Runner → /admin/pipeline | People Editor → /admin/people | [spacer] Log out [button]`. Same link set as current admin layout.
- **D-10:** Public nav link set: `SCOTUS CHAT [wordmark] | Cases → /cases | [spacer] Admin → /admin`. Admin-specific links (Pipeline Runner, People Editor) do NOT appear in the public nav.

### Claude's Discretion

- Exact font size for nav links (13px or 14px — current implementations differ slightly; pick one for consistency)
- Whether the "SCOTUS CHAT" wordmark in the public nav is a link to `/` or a plain `<span>` (current is `<span>`)
- Active-link styling (current navs have none — Claude's call whether to add subtle active state or keep stateless)
- Exact component file name: `TopNav.svelte` (follow PascalCase component convention)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Scope
- `.planning/REQUIREMENTS.md` §Navigation — NAV-01 (the single requirement this phase closes)
- `.planning/ROADMAP.md` §Phase 10 — Success criteria (3 items that must be TRUE)

### Prior Phase Foundation (MUST READ)
- `.planning/phases/09-people-data-model-migration/09-CONTEXT.md` — Admin dark theme tokens, Svelte 5 Runes patterns, `use:enhance`, form action conventions
- `.planning/STATE.md` — Accumulated context and any blockers

### Current Files Being Replaced
- `app/src/routes/+layout.svelte` — Root layout; current public nav inline markup; the `{#if !page.url.pathname.startsWith('/admin')}` guard (this guard disappears after TopNav owns context via variant prop)
- `app/src/routes/admin/+layout.svelte` — Admin layout; current admin nav with logout button; the `{#if page.url.pathname !== '/admin/login'}` guard (this guard is preserved — login page still shows no nav)

### Component Conventions
- `.planning/codebase/CONVENTIONS.md` — Svelte 5 Runes patterns (`$props()`, `$state`, `$derived`), PascalCase component naming, no data fetching in components
- `.planning/codebase/STRUCTURE.md` — `app/src/lib/components/` is where `TopNav.svelte` is created

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/src/routes/+layout.svelte` — Current public nav markup (wordmark + Cases link); extract and parameterize
- `app/src/routes/admin/+layout.svelte` — Current admin nav markup (wordmark + Pipeline Runner + People Editor + logout button); extract and parameterize
- Admin dark theme tokens already established: `#0f1117` page bg, `#1e293b` card/admin-nav bg, `#334155` border, `#94a3b8` body text, `#93c5fd` accent blue

### Established Patterns
- **Svelte 5 Runes**: `let { variant } = $props();` for TopNav props — same pattern as all other components (ChatBubble, SectionRail, MobileNavBar, StageDirection)
- **No data fetching in components**: TopNav receives all context via props — no `$page` reads, no `fetch` calls
- **Inline styles**: Current nav uses inline style strings (no Tailwind class utilities for nav). Continue this pattern or use Tailwind — Claude's discretion.
- **Login page guard**: `{#if page.url.pathname !== '/admin/login'}` in admin layout — this guard must be preserved; TopNav should not render on the login page

### Integration Points
- `app/src/routes/+layout.svelte` — Replace inline `<header>` block with `<TopNav variant="public" />`. Remove the `!page.url.pathname.startsWith('/admin')` guard (TopNav handles its own rendering per variant; admin layout has its own TopNav).
- `app/src/routes/admin/+layout.svelte` — Replace inline `<header>` block (and the entire `{#if page.url.pathname !== '/admin/login'}` guard wrapping it) with `{#if page.url.pathname !== '/admin/login'}<TopNav variant="admin" />{/if}`. The login-page suppression stays in the admin layout.
- `app/src/lib/components/TopNav.svelte` — New file; sits alongside ChatBubble.svelte, SectionRail.svelte, etc.

</code_context>

<specifics>
## Specific Ideas

- **Login page guard stays in layout, not TopNav**: The admin layout's `{#if page.url.pathname !== '/admin/login'}` wrapper should stay in `admin/+layout.svelte`, not inside the component. This keeps TopNav a dumb display component that doesn't need to know about URL state.
- **Variant-driven backgrounds**: `const bgColor = variant === 'admin' ? '#1e293b' : '#0f1117';` — single line derivation inside the component.
- **Right-aligned elements**: Both variants use `margin-left: auto` on the rightmost item (Admin link in public, logout button in admin) to push it flush right.

</specifics>

<deferred>
## Deferred Ideas

- **Active-link highlighting** (e.g., bold or accent color on the current page's nav link) — not in NAV-01 scope; could be added in a polish phase
- **Mobile nav changes** — MobileNavBar is a separate component and unchanged by this phase
- **Breadcrumbs or secondary navigation** — out of scope; not a v1.2 requirement

</deferred>

---

*Phase: 10-unified-navigation*
*Context gathered: 2026-06-22*
