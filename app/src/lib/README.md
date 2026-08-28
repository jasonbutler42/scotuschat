# `app/src/lib/` placement rule

Four locations, each with one job. When adding a new component, find its row
below and put the file there — no archaeology required.

| Location | Holds | Rule |
|---|---|---|
| `lib/primitives/` | Surface-agnostic building blocks with no domain knowledge (`Button`, `Badge`, `Input`, `Card`). | A primitive never imports from `lib/public/` or `lib/admin/`. |
| `lib/public/` | Components rendered only on the public site. | Reading-optimised: wider measure, larger type, more air. |
| `lib/admin/` | Components rendered only inside `/admin`. | Density-optimised. May reference admin-only lifecycle/status vocabulary; public components may not. |
| `lib/components/` | Cross-surface app shell only — a component imported by BOTH the root layout and the admin layout. Currently `TopNav.svelte` alone. | If a second cross-surface component appears, it joins this directory under the same rule. Confirm cross-surface status by grepping actual import sites, not by name — a component whose name sounds shared may still be public-only (e.g. `MobileNavBar.svelte`, which only the transcript page imports). |

## Figma correspondence (D-06)

The Figma file mirrors this layout page-for-page, and a component's Figma
frame name equals its file name:

| Figma page | Code destination |
|---|---|
| `Tokens` | `app.css :root` |
| `Primitives` | `lib/primitives/` |
| `Public` | `lib/public/` |
| `Admin` | `lib/admin/` |
