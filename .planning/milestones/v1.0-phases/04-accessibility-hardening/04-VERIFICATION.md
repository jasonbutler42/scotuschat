---
phase: 04-accessibility-hardening
verified: 2026-06-15T12:00:00Z
status: passed
score: 15/15 must-haves verified
overrides_applied: 2
overrides:
  - must_have: "Screen-reader walkthrough (NVDA/JAWS/VoiceOver): every chat bubble announced as 'Bench: [Name]' or 'Advocate: [Name]' in article context; stage directions announced as notes."
    reason: "NOT VERIFIED — human verification waived by operator decision, not executed and not a pass. No assistive technology has ever been run against this codebase. The underlying ARIA markup was verified statically (this phase's 15/15 must-haves) but no announcement has been heard. Risk accepted: an AT-only regression in speaker-side announcement would be invisible to the suite."
    accepted_by: "operator (2026-08-18, /gsd-audit-uat — instructed to skip the outstanding human UAT items and prepare for Phase 48)"
    accepted_at: "2026-08-18"
  - must_have: "axe-core or WAVE scan of the rendered argument view: zero contrast violations, zero landmark-structure errors."
    reason: "NOT VERIFIED — human verification waived by operator decision, not executed and not a pass. No automated accessibility scan has ever been run against the rendered DOM. Contrast ratios were only ever checked by reading hex tokens in source. Risk accepted: WCAG 2.1 AA contrast/landmark conformance for this phase is asserted, not measured."
    accepted_by: "operator (2026-08-18, /gsd-audit-uat — instructed to skip the outstanding human UAT items and prepare for Phase 48)"
    accepted_at: "2026-08-18"
re_verification:
  previous_status: gaps_found
  previous_score: 13/15
  gaps_closed:
    - "On viewports < 768px a fixed-bottom pill row appears with all detected sections"
    - "Mobile nav disappears entirely when no sections are detected"
  gaps_remaining: []
  regressions: []
human_verification: []
human_verification_waived:
  - test: "Navigate the argument view with a screen reader (NVDA/JAWS on Windows; VoiceOver on Mac). Move cursor through chat bubbles. Confirm each bubble is announced as 'Bench: [Name]' or 'Advocate: [Name]' in article context. Confirm stage directions are announced as notes."
    expected: "Screen reader announces speaker side and name for every bubble; stage directions are announced as notes, not articles."
    why_human: "Screen reader virtual cursor behavior cannot be verified without an AT running."
    outcome: waived
  - test: "Run axe-core or WAVE accessibility checker against the rendered argument view in a browser."
    expected: "Zero contrast violations; zero landmark structure errors."
    why_human: "Automated contrast tools require the rendered DOM with computed CSS, not static source."
    outcome: waived
---

# Phase 4: Accessibility + Hardening — Verification Report (Re-verification)

**Phase Goal:** WCAG 2.1 AA accessibility compliance — correct ARIA semantics, keyboard focus visibility, screen-reader landmark structure, and mobile section navigation for the argument view.
**Verified:** 2026-06-15T12:00:00Z
**Status:** passed (2 human items waived — see Audit Closure below)
**Re-verification:** Yes — after CR-01 bug fix (removed `display: flex` from MobileNavBar.svelte `<nav>` inline style)

---

## Step 0: Previous Verification

Previous VERIFICATION.md found with `status: gaps_found`, `score: 13/15`. Two BLOCKER gaps identified, both rooted in CR-01 (inline `display: flex` overriding `nav { display: none; }` stylesheet rule).

**Re-verification mode:** Full 3-level check on the two previously-failed items; quick regression check on the 13 previously-passing items.

---

## CR-01 Fix Verification

**Claim:** `display: flex` was removed from the MobileNavBar.svelte `<nav>` inline style. The `<style>` block now controls display via `nav { display: none; }` and `@media (max-width: 768px) { nav { display: flex; } }`.

**Evidence from codebase (MobileNavBar.svelte lines 34-49):**

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
```

`display: flex` is absent from the inline style. The only `display: flex` in the file is at line 78 inside the media query rule: `@media (max-width: 768px) { nav { display: flex; } }`.

**Style block (lines 72-81):**

```css
nav { display: none; }
@media (max-width: 768px) { nav { display: flex; } }
```

CR-01 is **resolved**. The stylesheet rules now have uncontested specificity — `nav { display: none; }` fires on all viewports; the media query overrides to `display: flex` at `<768px`.

---

## Step 3: Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| T-01 | All text passes 4.5:1 contrast — #94a3b8 role labels on #1e293b, #475569 purged site-wide | VERIFIED | `grep -r "#475569" app/src/` — no matches. Role label span in ChatBubble.svelte line 62 uses `color: #94a3b8`. Bench/Advocates headers in +page.svelte lines 114, 140 use `color: #94a3b8`. |
| T-02 | A focused link or button shows a visible 2px solid #93c5fd outline with 3px offset | VERIFIED | app.css lines 28-32: `*:focus-visible { outline: 2px solid #93c5fd; outline-offset: 3px; border-radius: 4px; }` — present and correct. |
| T-03 | Sequence numbers (#475569, 13px) are gone — utterances show avatar + name only | VERIFIED | ChatBubble.svelte: no `utterance.sequence` render. Comment on line 38 reads "Bubble header row: avatar circle + speaker label" (sequence reference removed). No `#475569` present. |
| T-04 | Screen readers announce each ChatBubble as an article with the speaker side and name | VERIFIED | ChatBubble.svelte lines 19-20: `role="article"` and `aria-label="{isBench ? 'Bench' : 'Advocate'}: {displayName}"` on outer div. |
| T-05 | Screen readers distinguish stage directions from speech bubbles via role=note | VERIFIED | StageDirection.svelte line 7: `role="note"` on outer div. No other role attributes present. |
| T-06 | SectionRail nav is labelled 'Argument sections' for screen readers | VERIFIED | SectionRail.svelte line 33: `<nav aria-label="Argument sections" ...>`. |
| T-07 | Every page has a `<header>` landmark (global nav bar) and a `<main>` landmark (page content) | VERIFIED | +layout.svelte line 6: `<header>` wraps `<nav aria-label="Site navigation">`. cases/+page.svelte lines 22, 24: `<main>` outer and `<header>` top-bar. arguments/[id]/+page.svelte lines 70, 72: `<main>` and `<header>`. |
| T-08 | Screen readers distinguish site nav from argument section nav via distinct aria-labels | VERIFIED | +layout.svelte nav: `aria-label="Site navigation"`. MobileNavBar.svelte nav: `aria-label="Argument sections"`. SectionRail.svelte nav: `aria-label="Argument sections"`. Labels are distinct between site nav and section nav. |
| T-09 | On viewports < 768px a fixed-bottom pill row appears with all detected sections | VERIFIED | CR-01 fixed. MobileNavBar.svelte: `nav { display: none; }` in stylesheet (line 73); `@media (max-width: 768px) { nav { display: flex; } }` (line 76). Inline style on `<nav>` contains no `display` property. Stylesheet now has uncontested control. `{#if sections.length > 0}` guard (line 33) ensures pills only render when sections exist. `position: fixed; bottom: 0; left: 0; right: 0;` present in inline style (lines 37-40). |
| T-10 | Active section pill highlights with a #93c5fd border; inactive pills use #334155 border | VERIFIED | MobileNavBar.svelte line 62: `border: 1px solid {activeSection === sec.hint ? '#93c5fd' : '#334155'}` — correct colors wired to IntersectionObserver `activeSection` state. |
| T-11 | Tapping a mobile nav pill smooth-scrolls to that section anchor | VERIFIED | MobileNavBar.svelte line 53: `onclick={() => document.getElementById(sec.anchorId)?.scrollIntoView({ behavior: 'smooth' })}` — same pattern as SectionRail; correctly wired. |
| T-12 | Mobile nav disappears entirely when no sections are detected | VERIFIED | CR-01 fixed. When `sections.length === 0`, the `{#if sections.length > 0}` guard (line 33) prevents the `<nav>` from rendering at all. When sections are present, `nav { display: none; }` hides the bar on desktop; `@media (max-width: 768px)` shows it on mobile only. Both conditions now function correctly. |
| T-13 | Chat column bottom padding is 60px, preventing last utterance from hiding behind mobile nav bar | VERIFIED | arguments/[id]/+page.svelte line 175: `<div style="padding: 48px 24px 60px 24px;">` — correct. |
| T-14 | Roster column headers ('Bench' / 'Advocates') use color: #94a3b8 — #475569 is gone site-wide | VERIFIED | arguments/[id]/+page.svelte lines 114, 140: `color: #94a3b8` on Bench and Advocates headers. `grep -r "#475569" app/src/` returns no matches. |
| T-15 | Keyboard Tab on the argument page reaches mobile nav pill buttons on narrow viewports | VERIFIED (code) / UNCERTAIN (runtime) | Pill buttons are native `<button>` elements — inherently keyboard focusable. Global `*:focus-visible` rule applies. With CR-01 fixed, buttons are only in the DOM when `sections.length > 0` and only visible at `<768px` via CSS — they remain in the tab order even when `display: none` at desktop widths (standard browser behavior: `display: none` removes from tab order). Human verification required to confirm focus traversal in a live browser at mobile viewport. |

**Score: 15/15 truths verified**

---

## Step 4: Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/src/app.css` | Global focus ring + sequence variable removed | VERIFIED | `*:focus-visible { outline: 2px solid #93c5fd; outline-offset: 3px; border-radius: 4px; }` at lines 28-32. `--color-text-sequence` absent. `#475569` absent. |
| `app/src/lib/components/ChatBubble.svelte` | role=article + aria-label, sequence span removed, role label color fixed | VERIFIED | `role="article"` line 19; `aria-label` line 20 (interpolated from `isBench`/`displayName`); no `utterance.sequence`; role label uses `color: #94a3b8` (line 62). |
| `app/src/lib/components/StageDirection.svelte` | role=note on outer div | VERIFIED | Line 7: `role="note"` on outer div. No other roles. |
| `app/src/lib/components/SectionRail.svelte` | aria-label on nav | VERIFIED | Line 33: `<nav aria-label="Argument sections" ...>`. IntersectionObserver and smooth-scroll unchanged. |
| `app/src/lib/components/MobileNavBar.svelte` | Fixed-bottom pill row, <768px only, scroll-spy active state | VERIFIED | `position: fixed; bottom: 0;` in inline style. `nav { display: none; }` in stylesheet — no inline `display` override. `@media (max-width: 768px) { nav { display: flex; } }` is now the sole display controller. IntersectionObserver scroll-spy wired. `{#if sections.length > 0}` guard present. |
| `app/src/routes/+layout.svelte` | `<header>` wrapper + aria-label on site nav | VERIFIED | Line 6: `<header>` wraps `<nav aria-label="Site navigation">`. |
| `app/src/routes/cases/+page.svelte` | `<main>` + `<header>` landmarks | VERIFIED | Line 22: `<main ...>`. Line 24: `<header ...>`. Both correct. |
| `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` | `<main>` + `<header>`, roster color fix, MobileNavBar integration, 60px chat padding | VERIFIED | Line 70: `<main>`. Line 72: `<header>`. Lines 114, 140: `color: #94a3b8`. Line 175: `60px` bottom padding. Line 212: `<MobileNavBar sections={sectionAnchors} />`. |

---

## Step 5: Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/src/app.css` | All focusable elements site-wide | `*:focus-visible` selector | WIRED | Lines 28-32: rule present, applied globally. |
| `ChatBubble.svelte` | Screen reader virtual cursor | `role="article"` + `aria-label` | WIRED | Both attributes on outer div; `aria-label` interpolates live `isBench` and `displayName` values. |
| `arguments/[id]/+page.svelte` | `MobileNavBar.svelte` | `import + sections={sectionAnchors}` prop | WIRED | Import line 5; `<MobileNavBar sections={sectionAnchors} />` line 212; `sectionAnchors` is a `$derived` value from real utterance data. |
| `MobileNavBar.svelte` | Section anchor DOM elements | `document.getElementById(sec.anchorId)?.scrollIntoView` | WIRED | Line 53: same pattern as SectionRail. |
| `MobileNavBar.svelte` style block | Desktop hide / mobile show | `nav { display: none; }` + `@media (max-width: 768px)` | WIRED | CR-01 resolved. No inline `display` on `<nav>`. Stylesheet rule fires correctly; media query overrides at `<768px`. |

---

## Step 6: Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| A11Y-01 | 04-01, 04-02 | All UI passes WCAG 2.1 AA color contrast (4.5:1 minimum) | PARTIAL — human needed | `#475569` eliminated; contrast-compliant colors applied (`#94a3b8` on `#1e293b` verified at 4.5:1). Focus ring present. Full AA compliance in all rendered states requires automated contrast tool against live DOM. |
| A11Y-02 | 04-01, 04-02 | All UI is fully keyboard navigable | PARTIAL — human needed | Global focus ring in CSS. Native `<button>` and `<a>` elements throughout. MobileNavBar pills keyboard-reachable. CR-01 fixed — mobile bar no longer interferes with desktop keyboard flow. Runtime tab-order verification needed. |
| A11Y-03 | 04-01, 04-02 | Speaker side differentiation relies on layout position, not color alone | VERIFIED | ChatBubble alignment: `justify-content: {isBench ? 'flex-start' : 'flex-end'}`. `role="article"` + `aria-label` announces side programmatically. Position is primary differentiator. |
| A11Y-04 | 04-02 | Focus is visibly managed for any overlays or interactive elements | PARTIAL — human needed | No overlays in current UI. Focus ring CSS is global. No modal dialogs or focus traps. Human verification needed to confirm focus behavior after nav interactions in a live browser. |

No orphaned requirements — all four A11Y IDs from REQUIREMENTS.md Phase 4 mapping claimed in PLAN frontmatter.

---

## Step 7: Anti-Pattern Scan

Files modified by this phase: `app/src/app.css`, `app/src/lib/components/ChatBubble.svelte`, `app/src/lib/components/StageDirection.svelte`, `app/src/lib/components/SectionRail.svelte`, `app/src/lib/components/MobileNavBar.svelte`, `app/src/routes/+layout.svelte`, `app/src/routes/cases/+page.svelte`, `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/src/app.css` | 12 | `--color-stage-accent: #d97706;` has no leading whitespace (column-0 indentation inconsistency) | INFO | Cosmetic — pre-existing, not introduced by Phase 4. |

No `TBD`, `FIXME`, or `XXX` debt markers found in any phase-modified file.

No `display: flex` in MobileNavBar.svelte inline `<nav>` style — CR-01 blocker resolved.

---

## Step 7b: Behavioral Spot-Checks

| Behavior | Check | Result | Status |
|----------|-------|--------|--------|
| `#475569` absent from entire app/src tree | `grep -r "#475569" app/src/` | No matches | PASS |
| `*:focus-visible` rule present | app.css lines 28-32 | `outline: 2px solid #93c5fd; outline-offset: 3px; border-radius: 4px` | PASS |
| `role="article"` on ChatBubble | ChatBubble.svelte line 19 | Present | PASS |
| `role="note"` on StageDirection | StageDirection.svelte line 7 | Present | PASS |
| `aria-label="Argument sections"` on SectionRail nav | SectionRail.svelte line 33 | Present | PASS |
| MobileNavBar display control | Inline `<nav>` style — no `display` property; `nav { display: none; }` in stylesheet; media query at line 76 | Stylesheet controls display exclusively — CR-01 resolved | PASS |
| Chat column bottom padding | arguments/[id]/+page.svelte line 175 | `padding: 48px 24px 60px 24px` | PASS |
| MobileNavBar `position: fixed` | MobileNavBar.svelte lines 37-40 | `position: fixed; bottom: 0; left: 0; right: 0;` | PASS |
| `PUBLIC_` env vars absent | `grep -r "PUBLIC_" app/src/` | No matches | PASS |

---

## Step 7c: Probe Execution

No probe scripts exist or were declared for this phase. Phase 4 contains no migration, CLI, or data pipeline steps. Step 7c: SKIPPED (no runnable probes).

---

## Step 8: Human Verification Required

All five items below require a live browser. The two BLOCKER gaps from the prior verification are now resolved at the code level; these items confirm runtime behavior.

### 1. Mobile nav visibility at narrow viewport

**Test:** Open the argument view in a browser. Resize the viewport to 500px width (< 768px). Confirm the fixed bottom pill nav bar appears. Resize to 1200px width (desktop). Confirm the pill nav bar is not visible.
**Expected:** Pill nav visible only at < 768px; absent on desktop.
**Why human:** CSS media-query behavior requires a live browser at specific viewport widths.

### 2. Keyboard focus ring visible on interactive elements

**Test:** Open any page. Press Tab repeatedly. Confirm every focused link, button, and interactive element shows a visible 2px blue outline (#93c5fd) with 3px offset.
**Expected:** All focusable elements show the focus ring; no element is skipped or shows the browser default.
**Why human:** Focus ring visibility and traversal order cannot be fully verified by static analysis.

### 3. Screen reader announcement of ChatBubble

**Test:** Navigate the argument view with a screen reader (NVDA/JAWS on Windows; VoiceOver on Mac). Move cursor through chat bubbles. Confirm each bubble is announced as "Bench: [Name]" or "Advocate: [Name]" in article context. Confirm stage directions are announced as notes.
**Expected:** Screen reader announces speaker side and name for every bubble; stage directions are announced as notes, not articles.
**Why human:** Screen reader virtual cursor behavior cannot be verified without an AT running.

### 4. Section nav scroll behavior

**Test:** Open the argument view with detected sections. Click a section pill in the SectionRail (desktop) or MobileNavBar (mobile, < 768px). Confirm smooth-scroll to the correct anchor. Confirm active state (blue border) updates via scroll-spy as the user scrolls past section anchors.
**Expected:** Pills highlight the current section; clicking scrolls to it; active state updates automatically.
**Why human:** IntersectionObserver scroll-spy and smooth-scroll behavior requires a live browser.

### 5. WCAG contrast — full automated scan

**Test:** Run axe-core or WAVE accessibility checker against the rendered argument view in a browser.
**Expected:** Zero contrast violations; zero landmark structure errors.
**Why human:** Automated contrast tools require the rendered DOM with computed CSS, not static source.

---

## Gaps Summary

No gaps. All 15 must-haves are verified at the code level.

The two previously-blocked truths (T-09, T-12) are now VERIFIED:

- **T-09 resolved:** `display: flex` removed from MobileNavBar.svelte `<nav>` inline style. The `<style>` block's `nav { display: none; }` now has uncontested control. The `@media (max-width: 768px) { nav { display: flex; } }` rule fires exclusively at mobile widths.
- **T-12 resolved:** The `{#if sections.length > 0}` guard was already correctly implemented. With the display bug fixed, the visibility contract is now whole: the nav is absent from the DOM when no sections exist, and hidden by CSS at desktop widths when sections do exist.

Five human verification items remain. (Reduced to two on 2026-08-18 — see Audit Closure below.) These are behavioral/runtime checks that require a live browser — they were present in the prior verification and have not changed in scope.

---

_Verified: 2026-06-15T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: CR-01 bug fix — removed `display: flex` from MobileNavBar.svelte `<nav>` inline style_

---

## Audit Closure — 2026-08-18 (cross-phase UAT audit)

`status` stays `human_needed`: this phase is the ONE audited phase with genuinely
outstanding human verification. Three of the original five `human_verification`
items were executed and passed — they are removed from the array above and
recorded here — leaving two that have never been run.

**Closed (were items 1, 2 and 4):**

| Original item | Closed by |
|---------------|-----------|
| Pill nav visible only below 768px | `04-UAT.md` Tests 4–5 ("Mobile Nav Hidden on Desktop", "Mobile Nav Visible on Narrow Viewport") — pass |
| Tab focus ring, 2px #93c5fd with 3px offset | `04-UAT.md` Test 1 "Keyboard Focus Ring" — pass |
| Section pill click → smooth scroll + scroll-spy active state | `04-UAT.md` Tests 6 and 8 ("Mobile Nav Pill Scroll", "SectionRail Active Section Highlight") — pass |

`04-UAT.md` is `status: passed`, total 8, passed 8, skipped 0.

**Still outstanding (the two items retained above):**

1. Screen-reader walkthrough (NVDA/JAWS/VoiceOver) — each chat bubble announced as
   "Bench: [Name]" / "Advocate: [Name]" in article context, stage directions as notes.
2. axe-core or WAVE scan of the rendered argument view — zero contrast violations,
   zero landmark-structure errors.

Neither was ever run, and neither is covered by any later phase's UAT. Both are
carried in STATE.md and are the top two entries of the human test plan in
`.planning/notes/2026-08-18-uat-audit-closure.md`. Note the accessibility surface
has changed substantially since 2026-06-15 (Phases 14, 38, 39, 45 all touched the
popover and argument view), so these should be run against current `main`, not
treated as a formality.

---

## Human Verification Waived — 2026-08-18

The operator elected to skip the two remaining human UAT items and move to Phase 48. Recorded via
this file's `overrides` block — the project's existing mechanism for a must-have the operator accepts
without it being verified as written (the same shape Phase 45 used) — so `status: passed` never
implies these two were checked.

**What is now asserted rather than measured:**

- No assistive technology has ever been run against the argument view. The ARIA markup was verified
  statically; no announcement has been heard.
- No axe-core/WAVE scan has ever been run. Contrast was checked by reading hex tokens in source, not
  by measuring the rendered DOM.

This is a real, accepted risk for a phase whose stated goal is WCAG 2.1 AA compliance, and it is
carried forward in STATE.md rather than closed silently. Phases 14, 38, 39 and 45 have all touched
the popover and argument view since 2026-06-15, so the surface these checks would cover is not the
surface they were written against.

The cheapest way to retire the risk properly is to make it automatic rather than human: an axe-core
assertion in a Playwright/Vitest browser test would cover the second item permanently and needs no
operator time. Worth considering when Phase 51 (Design System & Noun Alignment) reworks this UI.
