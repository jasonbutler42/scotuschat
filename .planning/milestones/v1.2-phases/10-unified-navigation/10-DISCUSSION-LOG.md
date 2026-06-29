# Phase 10: Unified Navigation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-22
**Phase:** 10-unified-navigation
**Areas discussed:** Admin link in public nav, Context detection strategy, Logout button ownership, Background color unification

---

## Admin Link in Public Nav

**Q1: How should the admin link appear in the public nav?**

| Option | Description | Selected |
|--------|-------------|----------|
| Small quiet link | Muted /admin link at far right, same style as other nav links (#94a3b8). Not emphasized. | ✓ |
| Labeled 'Admin' link, same weight as Cases | Equal visual weight as 'Cases' link. Obvious to all visitors. | |
| You decide | Leave placement and styling to Claude's discretion. | |

**Q2: What label should the admin link use?**

| Option | Description | Selected |
|--------|-------------|----------|
| Labeled 'Admin' | Clear, honest label. Operators find it; non-operators hit login redirect. | ✓ |
| Labeled '⚙ Admin' or icon-only | Gear icon or small icon + text. Slightly more subtle. | |
| You decide | Leave label to Claude's discretion. | |

**Q3: Where should the admin link sit?**

| Option | Description | Selected |
|--------|-------------|----------|
| Far right, after Cases | Wordmark — Cases — ··· Admin (pushed right with margin-left: auto). | ✓ |
| Immediately after Cases | Wordmark — Cases — Admin. Inline with main nav items. | |

**Notes:** Admin link is quiet and honest — operators can find it, non-operators who click it hit the login page. Right-aligned placement keeps it visually separate from the primary "Cases" link.

---

## Context Detection Strategy

**Q1: How should TopNav know its context?**

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit prop from layout | Each layout passes variant='admin' or variant='public'. Component never inspects the URL. | ✓ |
| URL detection inside the component | TopNav reads $page.url.pathname internally. Layouts pass nothing special. | |

**Q2: What should the prop look like?**

| Option | Description | Selected |
|--------|-------------|----------|
| variant: 'public' \| 'admin' | String union type. Readable, matches codebase conventions. | ✓ |
| isAdmin: boolean | Boolean flag. Simpler but less extensible. | |
| You decide | Leave prop shape to Claude's discretion. | |

**Notes:** Explicit prop keeps TopNav a dumb display component. No hidden URL-reading magic. Follows $props() convention established across all existing Svelte components.

---

## Logout Button Ownership

**Q1: Where does the logout button live?**

| Option | Description | Selected |
|--------|-------------|----------|
| Inside TopNav as conditional markup | When variant='admin', TopNav renders logout inline. Layouts just render <TopNav variant="admin" />. | ✓ |
| Slot/child passed from admin layout | TopNav exposes a right-side slot; admin layout passes in the logout button. | |
| Stays in admin/+layout.svelte alongside TopNav | Admin layout renders TopNav + its own logout outside the component. | |

**Q2: Keep the hover state on the logout button?**

| Option | Description | Selected |
|--------|-------------|----------|
| Keep the hover state | Copy onmouseenter/onmouseleave inline JS as-is. Established admin UI pattern. | ✓ |
| Remove hover state | Static button. Simpler markup. | |
| You decide | Leave hover behavior to Claude's discretion. | |

**Notes:** TopNav fully owns the nav bar. Clean usage from layout. Hover state preserved for consistency with Phase 6/7 admin UI.

---

## Background Color Unification

**Q1: Keep distinct backgrounds or unify?**

| Option | Description | Selected |
|--------|-------------|----------|
| Keep distinct backgrounds via variant | variant='public' → #0f1117; variant='admin' → #1e293b. Visual admin-context signal. | ✓ |
| Unify to one color | Pick one color for both. Stronger visual unity, loses admin signal. | |
| You decide | Leave color decision to Claude's discretion. | |

**Q2: Should admin nav links appear in the public nav?**

| Option | Description | Selected |
|--------|-------------|----------|
| Public shows only Cases + Admin link | Context-appropriate link sets per variant. | ✓ |
| Public shows all links including Pipeline Runner and People Editor | Consistent link set everywhere; admin links redirect non-operators to login. | |

**Notes:** Distinct backgrounds give subtle "you are in admin" signal. Each variant renders its own appropriate link set.

---

## Claude's Discretion

- Exact font size for nav links (13px vs 14px — current implementations differ; pick one)
- Whether "SCOTUS CHAT" wordmark is a link to `/` or a plain `<span>`
- Active-link styling (current navs have none — Claude decides whether to add or keep stateless)
- Exact component file name: `TopNav.svelte` (PascalCase convention)
- Whether inline styles or Tailwind classes are used in the component

## Deferred Ideas

- **Active-link highlighting** — not in NAV-01 scope; future polish phase
- **Mobile nav changes** — MobileNavBar is unchanged by this phase
- **Breadcrumbs or secondary navigation** — out of scope for v1.2
