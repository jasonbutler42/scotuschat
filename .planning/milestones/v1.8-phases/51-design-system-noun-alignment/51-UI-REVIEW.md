# Phase 51 — UI Review

**Audited:** 2026-09-04  
**Baseline:** 51-UI-SPEC.md design contract  
**Screenshots:** Not captured (no browser available in sandbox environment; code-only audit)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Copywriting contract followed on public surfaces; one admin helper has generic error message |
| 2. Visuals | 4/4 | Clear focal points, proper icon accessibility patterns, visual hierarchy intact across all surfaces |
| 3. Color | 4/4 | Two-layer token architecture verified; 60/30/10 split maintained; apolitical constraint held; status colors properly gated to admin |
| 4. Typography | 3/4 | Five semantic type steps and two weights achieved; four numeric font-weight values in admin template expressions violate token contract |
| 5. Spacing | 4/4 | All spacing uses token scale; no arbitrary values; consistent application across public and admin layers |
| 6. Experience Design | 3/4 | Loading, error, and empty states present; accessible-name contract enforced on icon buttons; VariantSwitcher overlay conflicts at 375px noted |

**Overall: 21/24**

---

## Top 3 Priority Fixes

1. **Numeric font-weight values in template expressions** — Violates design contract D-01/D-04 (all inline styles must use tokens) — Four instances in `app/src/lib/admin/ResolveCard.svelte` (lines 888, 905) and `app/src/routes/admin/pipeline/+page.svelte` (lines 246, 264) use `{benchActive ? 600 : 400}` instead of `var(--font-weight-semibold)` / `var(--font-weight-regular)`. Replace with conditional token references: `{benchActive ? 'var(--font-weight-semibold)' : 'var(--font-weight-regular)'}`

2. **VariantSwitcher fixed overlay z-index conflicts at mobile** — The floating "Style" pill at `position: fixed; top: var(--space-sm); right: var(--space-sm); z-index: 60` visually overlaps the fixed `MobileNavBar` top-nav links ("Attributions" and "Admin") at 375px viewport. Consider repositioning to avoid the overlap (e.g., `bottom` anchor instead of `top`, or dynamically adjusting z-index/position on small viewports). Noted as open observation in already-verified section.

3. **Generic error message in CreatePersonPopover** — The error copy at `app/src/lib/admin/CreatePersonPopover.svelte:137` reads "Could not create person. Please try again." — a generic fallback phrase not matching the specificity of other error messaging on admin screens. Align with the error-state contract if this is a public-facing user action, or document why a fallback is appropriate here.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Verified against UI-SPEC Copywriting Contract:**

| Element | Expected | Actual | Status |
|---------|----------|--------|--------|
| Empty state heading | "No arguments published yet" | ✓ `app/src/routes/arguments/+page.svelte:49` | PASS |
| Empty state body | "Check back soon — new oral arguments are added regularly." | ✓ `app/src/routes/arguments/+page.svelte:60` | PASS |
| Error state (public) | "Unable to load arguments right now. Try refreshing the page." | ✓ `app/src/routes/arguments/+error.svelte:63` | PASS |
| Destructive confirmation | "Delete argument: This action cannot be undone." | Verified in admin code | PASS |
| Term-scoped empty | "No arguments published for October Term {year} yet." | Implemented in term-detail route | PASS |

**Defect found:** `app/src/lib/admin/CreatePersonPopover.svelte:137` uses a generic "Could not create person. Please try again." message instead of a specific context-aware message. Severity: WARNING — this is admin-only and not on the public path, but it degrades the consistency of error messaging across the application.

**Assessment:** Public copywriting is contract-compliant; admin has one generic fallback. Score reflects minor inconsistency, not a contract violation on the primary (public) surfaces.

---

### Pillar 2: Visuals (4/4)

**Focal points verified from Figma deliverable (51-01 coverage D7):**

- `/arguments` (term index) — Primary: term identifier ("October Term 2019"); Secondary: argument count per term; Deliberately quiet: nav chrome
- `/arguments/term/{year}` — Primary: case name on each row; Secondary: argued date, then docket; Deliberately quiet: row affordances
- `/arguments/{slug}` (transcript) — Primary: utterance text (D-09 reading-layer redesign); Secondary: speaker identity at turn change; Deliberately quiet: section rail, nav

**Icon accessibility verified:**
- `app/src/lib/primitives/Button.svelte` enforces type-level accessible-name contract — icon-only controls (`{ icon: LucideIcon; children?: never }`) require one of `label`, `ariaLabel`, or `ariaLabelledby`, making it a compile error to omit. Icons carry `aria-hidden="true"` when named via text/aria paths.
- Accessible names present via visible labels (preferred) or `aria-label` where space constraints require icon-only treatment.

**Visual hierarchy:**
- Typography: Lead (18px/400) reserved for public reading surfaces per D-09; Heading (20px/600) for sectional emphasis; Caption/Body for supplementary content.
- Color hierarchy: accent (10%) reserved for primary CTAs and links; surface (30%) for cards/backgrounds; text-primary/secondary for reading hierarchy.
- D-19 transcript redesign: bench left-aligned, advocate right-aligned with identical typography (both 18px/400) — side identity encoded by position and avatar colour, never by prominence.

**Assessment:** No visual hierarchy violations found. Focal points are clear and intentional. Icon accessibility contract is enforced by type system, eliminating the risk of unlabeled icons.

---

### Pillar 3: Color (4/4)

**Two-layer token architecture verified (51-01 coverage D2):**

- **Layer 1 (Primitives):** 35 raw hex values declared in `app/src/app.css`, never referenced directly by components (private to layer 2).
- **Layer 2 (Semantic roles):** 75 semantic tokens declared in `app/src/app.css :root`, every component reference uses semantic names only (verified by grep: 0 hardcoded hex/rgb in `.svelte` files).

**60/30/10 split verified:**
- Dominant (60%): `--color-bg` (`#0f1117`) — page background, universal.
- Secondary (30%): `--color-surface` (`#1e293b`) — cards, header, nav, table rows.
- Accent (10%): `--color-accent` (`#93c5fd`) — Primary CTA buttons, all inline/nav links, focus-visible outlines, active-tab indicators. **Never** applied to status badges, table headers, or general emphasis (verified by `51-DESIGN-DECISIONS.md` D-01 sweep: banned-hits 0).

**Admin-only lifecycle colors:**
- Status badges: `--color-status-published`, `--color-status-draft`, `--color-status-unpublished`, `--color-status-warning`, `--color-status-archived`.
- Trust tier: `--color-tier-verified`, `--color-tier-trusted`, `--color-tier-provisional`, `--color-tier-uncertain`.
- Review state: `--color-review-unreviewed`, `--color-review-needs-review`, `--color-review-confirmed`, `--color-review-edited`, `--color-review-discrepancy`, `--color-review-unknown`.
- **All admin-only colors are properly gated:** enforced by `api/tests/test_trust_public_leak_ban.py` (structural absence sweep); zero admin colors reach any public response model.

**Apolitical constraint (P-01, P-03) verified:**
- **P-01 derived-statistic ban:** 51-01 coverage D8 swept every TEXT node across all Figma pages → banned-hits: 0 (no utterance count, speaking time, duration, "most active," ranking, or sentiment anywhere).
- **P-03 equal-luminance rule:** Bench and advocate avatars both solved to CIE L* 78 (within 1% of each other); identical perceived brightness ensures neither side reads as more prominent. `--color-side-bench` moved from `--slate-400` (L* 66.5, brighter) to `--l78-slate` (L* 78.0) to achieve parity.

**Assessment:** No color contract violations. Token architecture is sound, status colors are properly sequestered, and the apolitical constraint is structurally enforced.

---

### Pillar 4: Typography (3/4)

**Type scale verified (5 semantic steps, 2 weights):**

| Role | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| Caption | 14px | 400 | 1.4 | Labels, meta, admin dense text |
| Body | 16px | 400 | 1.5 | Paragraph copy, form text |
| Lead | 18px | 400 | 1.6 | Public reading surfaces (transcript, term list) |
| Heading | 20px | 600 | 1.2 | Section headings |
| Display | 32px | 600 | 1.2 | Page-level titles (argument case name) |

**Weights:** Exactly two — `--font-weight-regular` (400) and `--font-weight-semibold` (600). No 500 exists at phase end (verified by grep: 0 instances of `font-weight-500` or numeric 500 in component styling).

**Defect found: Numeric font-weight values in template expressions**

Four instances violate the design contract (D-01: "zero inline styles remain"; D-04: "convert every inline style... to tokens"):

1. `app/src/lib/admin/ResolveCard.svelte:888` — `font-weight: {benchActive ? 600 : 400};`
2. `app/src/lib/admin/ResolveCard.svelte:905` — `font-weight: {advocateActive ? 600 : 400};`
3. `app/src/routes/admin/pipeline/+page.svelte:246` — `font-weight: {mode === 'url' ? 600 : 400};`
4. `app/src/routes/admin/pipeline/+page.svelte:264` — `font-weight: {mode === 'upload' ? 600 : 400};`

**Correct form:**
```svelte
font-weight: {benchActive ? 'var(--font-weight-semibold)' : 'var(--font-weight-regular)'};
```

This ensures the token contract is complete — all values (including conditional branches) flow through the semantic layer, making future theme changes (e.g., adding a light theme) a matter of adding a second value set to the variables, not hunting for hardcoded numbers.

**Note:** These instances are in admin-only files and do not reach public surfaces. They are deviations from the stated design contract, not contract violations on the public side.

**Assessment:** Public type scale is contract-compliant. Admin has four numeric values that should be tokenized for consistency. Score reflects the deviation without downgrading public compliance.

---

### Pillar 5: Spacing (4/4)

**Spacing scale verified (8 semantic steps, all multiples of 4px):**

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | 4px | Tight inline gaps, badge margins |
| `--space-sm` | 8px | Label-to-input, button gaps, table padding |
| `--space-md` | 12px | Dense admin row padding (added 2026-09-01, load-bearing — 153 uses in codebase) |
| `--space-lg` | 16px | Field-to-field spacing, bubble padding |
| `--space-xl` | 24px | Card internal padding, heading-to-content |
| `--space-2xl` | 32px | Page region gaps, same-speaker utterance gap |
| `--space-3xl` | 48px | Page top/bottom padding |
| `--space-4xl` | 64px | Reading-surface measure (reserved for redesigned public) |

**Touch targets (exceptions to standard spacing):**
- `--touch-target` (44px) — Default for buttons, inputs (WCAG 2.1 AA).
- `--touch-target-dense` (36px) — Dense admin table rows only; never introduced in public.

**Verification:**
- Zero arbitrary spacing values (`[..px]`, `[..rem]`) found (verified by grep: 0 matches).
- All spacing in `lib/public/`, `lib/admin/`, and `lib/primitives/` uses token references.
- Spacing remapped on 2026-09-01 when 12px (`--space-md`) was added; all 695 references verified to be pixel-identical after remapping (DESIGN-SYSTEM.md reconciliation pass).

**Assessment:** Spacing contract fully met. No violations. Scale is consistent and applied uniformly across all components.

---

### Pillar 6: Experience Design (3/4)

**State coverage:**

| State | Implementation | Status |
|-------|---|---|
| Loading (API/SSR) | Server-rendered via `+page.server.ts`; no client skeleton/spinner on listing pages (E1/E2 explicit per UI-SPEC). Admin pipeline steps render `pending` and `running` badges via `RunStatusCard`. Button loading variant (E4 decision) ships on shared primitive with spinner from `@lucide/svelte`. | ✓ PASS |
| Error | Fetch/404 errors render UI-SPEC copy ("Unable to load arguments right now. Try refreshing the page."). Admin form errors display via `form?.error` with field-level validation messages. Popovers and admin flows have error guards. | ✓ PASS |
| Empty | Public listing: "No arguments published yet" + "Check back soon...". Term detail: "No arguments published for October Term {year} yet." Admin tables: empty-state messages when no rows (verified by grep: `data.incompletePeople.length === 0`, etc.). | ✓ PASS |
| Disabled | Buttons disable when `loading` or `disabled` prop set. Form submit states managed via `saveSubmitting`, `deleteSubmitting` flags. Touch targets respect accessibility minimums (44px default, 36px dense admin only). | ✓ PASS |
| Confirmation | Destructive actions carry confirmation dialogs (delete operations guard with "Delete argument: This action cannot be undone." per UI-SPEC). | ✓ PASS |
| Accessible Names | Icon-only controls enforced by type system: `Button` requires `label`, `ariaLabel`, or `ariaLabelledby` when `icon` is present and `children` is absent. Compile-time guarantee; `title` never used as substitute. | ✓ PASS |

**Defect found: VariantSwitcher overlay positioning at 375px**

The floating "Style" pill (floating button in VariantSwitcher.svelte lines 101–114) is positioned `position: fixed; top: var(--space-sm); right: var(--space-sm); z-index: 60`. On 375px mobile viewport, the MobileNavBar (fixed at bottom with z-index likely overlapping) and the top-nav links (Attributions, Admin in TopNav.svelte) are obscured or occluded by the switcher when it expands.

**Already-verified observation:** Noted in the UAT section as an open, intentional observation (VariantSwitcher is a testing instrument, not a product feature, per the source comment).

**Consequence:** Users on mobile cannot reliably access the Attributions and Admin links when the VariantSwitcher is open. This is acceptable for a test instrument but would need repositioning for production use.

**Assessment:** Core experience patterns (loading, error, empty, disabled, confirmation, accessible names) are all implemented correctly. One open observation about the testing instrument's overlay does not warrant a lower score on the production-use pillar, as it is explicitly a non-product testing tool.

---

## Files Audited

**Public Components (`lib/public/`):**
- `ChatBubble.svelte` — D-19 run-grouped utterance bubbles, 6/2px corner rounding, token-only styling
- `StageDirection.svelte` — Stage directions with amber tokens, no ellipsis
- `SectionRail.svelte` — Section navigation, token-only
- `SpeakerPopover.svelte` — Speaker detail card, token-only, bio always full (no line-clamp)
- `MobileNavBar.svelte` — Mobile navigation, token-only
- `TermRow.svelte` — Term list rows (case name + date + docket), token-only, no truncation

**Admin Components (`lib/admin/`):**
- `ResolveCard.svelte` — Argument-resolution editor; contains two numeric font-weight instances (lines 888, 905)
- `Badge.svelte` / `badge-tone.ts` — Centralized badge rendering, all admin status/tier/review colors
- `RunStatusCard.svelte` — Pipeline job status, token-driven
- Other admin surfaces: Routes and components verified to use tokens; no per-file badge/status style builders remain

**Primitives (`lib/primitives/`):**
- `Button.svelte` — Accessible-name contract enforced; loading variant present; token-only
- `Badge.svelte` — All admin colors flow through tone vocabulary; token-only
- `Input.svelte` — Validation error state via `role="alert"`; token-only
- `Card.svelte` — Container primitive; token-only

**Routes (`routes/`):
- `/arguments/+page.svelte` — Term index, empty/error states with correct copy
- `/arguments/term/[year]/+page.svelte` — Term detail, Variant A (minimal row) implemented
- `/arguments/[slug]/+page.svelte` — Transcript with D-19 Style B2 (run grouping, sticky avatar), token-only
- `/arguments/+error.svelte` — Error-state copy, contract-verified
- Admin routes: All verified to use tokens post-conversion

**Supporting Files:**
- `app/src/app.css` — Token source of truth: 35 primitives + 75 semantic tokens, reconciled against DESIGN-SYSTEM.md (verified bidirectionally on 2026-09-03)
- `app/src/lib/types/speaker.ts` — Single declaration site for TenureRow/SpeakerDetail (IN-02/IN-03 closure)
- `.planning/codebase/DESIGN-SYSTEM.md` — Reconciled snapshot, 75/75 semantic tokens + 35/35 primitives documented and verified

**Test Coverage:**
- `app/tests/arguments-listing.browser.test.mjs` — Real-browser test pinning long-case-name non-truncation (P-06)
- `app/tests/*.browser.test.mjs` — Suite: 10 tests, 10 passing (per plan 51-10 verification)

**Verification Artifacts:**
- `51-UI-SPEC.md` — Design contract (baseline for this audit)
- `51-DESIGN-DECISIONS.md` — D-16/D-18/D-19/E4 rulings and Figma deliverable URL
- `51-ADMIN-ARTIFACTS.md` — D-08 refactor findings, all artifacts ruled by operator

---

## Registry Safety Audit

**No shadcn or third-party component registries used on this project.**

- `components.json` does not exist (`test -f app/components.json` → not found)
- UI-SPEC §Registry Safety explicitly states: "No third-party shadcn-style registry blocks are declared or planned for this phase"
- Only external dependency for components: `bits-ui` (pre-existing, used only by `SpeakerPopover` for focus management; not a registry import)
- All primitives hand-rolled: `Button`, `Badge`, `Input`, `Card`
- Icon library: `@lucide/svelte` (installed as direct dependency, not via registry; see D-18 amendment for package-legitimacy gate)

**Registry audit: Not applicable — zero third-party registry blocks.**

---

## Summary

**Phase 51 design system and noun-alignment audit results:**

- **Public surfaces (primary focus):** Audit-clean. Copywriting contract followed exactly; typography and color contract fully met; no ellipsis/truncation on public paths; apolitical constraint structurally enforced.
- **Admin surfaces (secondary focus):** Functionally correct; four numeric font-weight values in template expressions are technical debt (all conditional style branches should use token references for design-to-code consistency), not functional defects.
- **Testing infrastructure:** Real-browser suite green (10/10 pass); no contract tests for frontend behavior (per CLAUDE.md Testing Policy); key assertion (long-case-name non-truncation) pinned by actual Playwright test, not source text.
- **One open observation (test instrument, not product):** VariantSwitcher floating pill overlaps mobile nav at 375px; acceptable for a testing-only tool.

**Recommendation:** Fix the three priority items (numeric font-weights, VariantSwitcher z-index conflict for clarity, generic error message consistency) before any subsequent phases that touch admin surfaces or expand the public listing. No blockers for Phase 52.

