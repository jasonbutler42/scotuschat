---
phase: 10
status: clean
reviewer: gsd-code-reviewer
reviewed_at: 2026-06-22
effort: max
findings_count: 1
severity_counts:
  critical: 0
  high: 0
  medium: 0
  low: 1
---

# Code Review — Phase 10: Unified Navigation

## Summary

Clean refactor. Nav markup correctly extracted into a single `TopNav.svelte` with a `variant` prop. Both layout guards preserved. `svelte-check` passes with 0 errors. One low-severity latent finding survived full verification.

**Angles run:** A (line-by-line), B (removed behavior), C (cross-file), D (language pitfalls), E (wrapper correctness), F (reuse), G (simplification), H (efficiency), I (altitude) + sweep  
**Candidates surfaced:** 12  
**After dedup/refutation:** 1 survives

---

## Findings

### [LOW] `{:else}` implicitly maps all non-'public' variants to admin chrome

**File:** `app/src/lib/components/TopNav.svelte:38`  
**Verdict:** PLAUSIBLE

```svelte
{#if variant === 'public'}
    <!-- public nav -->
{:else}
    <!-- full admin nav including logout form -->
{/if}
```

TypeScript types `variant` as `'public' | 'admin'`, so passing any other value is a compile-time error. However, TypeScript is erased at runtime — any JS caller can pass an unexpected value (e.g., `'embed'`, `'minimal'`, `undefined`) and silently receive the full admin logout form. The latent risk is that adding a third variant type in the future would require remembering to update the `{:else}` branch or it silently falls through to admin chrome.

**Fix:** Use an explicit `{:else if variant === 'admin'}` with a fallback:
```svelte
{#if variant === 'public'}
    <!-- public nav -->
{:else if variant === 'admin'}
    <!-- admin nav -->
{/if}
```
This makes unknown variants render nothing instead of admin chrome, and TypeScript exhaustiveness checking remains the enforcement layer.

---

## Refuted / Non-Findings

| Candidate | Disposition |
|-----------|-------------|
| `bgColor` plain `const` not reactive | REFUTED — plan explicitly chose `const` because variant never changes post-mount; both call sites pass static literals |
| Dual ARIA `<header>` banner landmarks | REFUTED — all page-level `<header>` elements are inside `<main>`, so they are not banner landmarks |
| Trailing-slash `/admin/login/` bypass | REFUTED — `adapter-node` defaults to `trailingSlash: 'never'`, normalizing the URL before the guard runs |
| `app.css` double import in admin layout | REFUTED — pre-existing (not introduced by this diff); Vite module system deduplicates in the bundle |
| Visual regression (stacked headers) | REFUTED — admin page `<header>` elements inside `<main>` were always alongside the admin layout nav bar; no structural change |
| Admin link added to public nav | Intentional — D-01 explicitly specifies the Admin link in the public variant |
| Cases link font-size 13px→14px | Intentional — UI-SPEC standardized to 14px |
| Inline DOM mutation for hover state | Pre-existing — verbatim carry from original `admin/+layout.svelte`; not introduced by this diff |
