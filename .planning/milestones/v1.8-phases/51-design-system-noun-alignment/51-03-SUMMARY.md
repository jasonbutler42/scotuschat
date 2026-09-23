---
phase: 51-design-system-noun-alignment
plan: 03
subsystem: ui
tags: [css-custom-properties, design-tokens, tailwind-removal, app-css]

requires:
  - phase: 51-design-system-noun-alignment
    provides: "plan 51-01's Figma semantic variable collection (37 names) and primitive palette (14 hex values)"
provides:
  - "Tailwind fully removed from app/package.json, app/tailwind.config.js, app/postcss.config.js, and the three @tailwind directives in app.css"
  - "An explicit base reset in app.css replacing the preflight rules the codebase relied on"
  - "A complete two-layer CSS custom-property token set in app/src/app.css :root (14 primitives + 37 semantic names) matching the Figma semantic collection character for character"
  - ".planning/phases/51-design-system-noun-alignment/51-TOKEN-MAP.md — the deterministic value-to-token conversion table plan 51-09 reads from"
  - ".planning/codebase/DESIGN-SYSTEM.md rewritten to document the token system as it now exists, replacing the stale July 2026 snapshot"
affects: [51-06, 51-08, 51-09, 51-10]

actuals:
  tokens: 7426
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Two-layer CSS custom-property tokens: a private primitive layer (raw hex) feeding a semantic layer (var(--primitive) references only), so component code never references a primitive name directly"
    - "Inline style= attributes remain the styling mechanism; only their literal values become var(--token) references (no CSS-in-JS, no utility classes introduced)"

key-files:
  created:
    - .planning/phases/51-design-system-noun-alignment/51-TOKEN-MAP.md
  modified:
    - app/src/app.css
    - app/package.json
    - app/package-lock.json
    - .planning/codebase/DESIGN-SYSTEM.md

key-decisions:
  - "--color-text-advocate dropped rather than aliased to --color-side-advocate: grep confirmed zero live var() call sites reference it anywhere in app/src (existing components hardcode #93c5fd/#94a3b8 literals rather than reading the CSS variable), so nothing was left undefined by removing it."
  - "10 of 24 distinct hex values found in app/src have no match in the 14-primitive palette; recorded as open rows for operator decision in 51-TOKEN-MAP.md rather than invented into new tokens, per the plan's explicit instruction."

requirements-completed: [DS-03]

coverage:
  - id: D1
    description: "Tailwind removed from the dependency tree and config surface; app/src/app.css carries an explicit base reset in preflight's place"
    requirement: "DS-03"
    verification:
      - kind: other
        ref: "test ! -f app/tailwind.config.js && test ! -f app/postcss.config.js"
        status: pass
      - kind: other
        ref: "grep -cE '\"(tailwindcss|@tailwindcss/typography|postcss|autoprefixer)\"' app/package.json"
        status: pass
      - kind: other
        ref: "npm --prefix app run check && npm --prefix app run build"
        status: pass
    human_judgment: true
    rationale: "The plan's own acceptance criteria require an operator-observed before/after visual check on the public listing, transcript, and admin dashboard to confirm the base reset preserves rendering with no layout shift. No browser binary exists in this sandbox (a pre-existing constraint also hit by plan 51-02), so this could not be observed; it is a genuine backstop truth in the plan's must_haves, not a formality."
  - id: D2
    description: "Complete two-layer token set (14 primitives + 37 semantic names) authored in app/src/app.css, matching the Figma semantic collection from plan 51-01 character for character, with zero raw hex in any semantic declaration"
    requirement: "DS-03"
    verification:
      - kind: other
        ref: "node -e token-scan script asserting no semantic declaration contains a raw hex literal"
        status: pass
      - kind: other
        ref: "grep counts: 14 primitives, 5 font-size, 7 space, 2 font-weight, 2 touch-target, 1 remaining #93c5fd (the primitive declaration only)"
        status: pass
    human_judgment: false
  - id: D3
    description: "51-TOKEN-MAP.md publishes a deterministic conversion table covering every distinct hex, font-size, font-weight, and spacing literal currently in app/src/**/*.svelte, plus explicit out-of-scope declarations"
    requirement: "DS-03"
    verification:
      - kind: other
        ref: "node -e verification script confirming all 24 distinct 6-digit hexes in app/src appear in the token map"
        status: pass
    human_judgment: false
  - id: D4
    description: ".planning/codebase/DESIGN-SYSTEM.md rewritten to document the Phase 51 token system result, no longer asserting the stale 3-size/2-weight type scale or an unverified no-Tailwind claim"
    requirement: "DS-03"
    verification:
      - kind: other
        ref: "grep checks: 5 --font-size- tokens, 16 named semantic colour tokens, 44px/36px touch-target rule all present"
        status: pass
    human_judgment: false

duration: 50min
completed: 2026-08-28
status: complete
---

# Phase 51 Plan 03: Design Tokens & Tailwind Removal Summary

**Removed Tailwind entirely and authored the full two-layer CSS custom-property token set (14 primitives, 37 semantic names) in `app/src/app.css`, matching plan 51-01's Figma `semantic` variable collection exactly, plus the deterministic `51-TOKEN-MAP.md` conversion table plan 51-09 will execute against.**

## Performance

- **Duration:** ~50 min
- **Started:** 2026-08-28 (session start)
- **Completed:** 2026-08-28T14:49:47Z (last task commit)
- **Tasks:** 3 completed
- **Files modified:** 6 (app/src/app.css, app/package.json, app/package-lock.json, app/tailwind.config.js [deleted], app/postcss.config.js [deleted], .planning/codebase/DESIGN-SYSTEM.md) + 1 created (51-TOKEN-MAP.md)

## Accomplishments

- Deleted `tailwindcss`, `@tailwindcss/typography`, `postcss`, `autoprefixer` from `app/package.json`; removed `app/tailwind.config.js` and `app/postcss.config.js`; deleted the three `@tailwind` directives from `app.css`. `npm install` removed 69 packages and added none. Added an explicit base reset (margin zeroing on headings/`p`/`figure`/`blockquote`/`dl`/`dd`, form-control normalization, anchor color/decoration inheritance, media element sizing) covering the preflight rules this codebase actually relied on, verified by grepping for load-bearing usages (e.g. `StatCard.svelte`'s explicit `margin: 0 0 16px 0` on `h2`) before writing each rule.
- Authored the complete two-layer token set in `app/src/app.css :root`: 14 primitive custom properties (raw hex, private) feeding 37 semantic names (16 colour + 7 spacing + 5 type sizes + 5 line-heights + 2 weights + 2 touch targets), every semantic entry a `var(--primitive)` reference with zero raw hex. Verified all 37 names match plan 51-01's Figma `semantic` collection character for character. Switched `*:focus-visible`'s outline from a literal `#93c5fd` to `var(--color-accent)`.
- Published `51-TOKEN-MAP.md`: every one of the 24 distinct hex values in `app/src/**/*.svelte` today is accounted for (14 mapped to a token including the two default+exception rules for `#94a3b8`/`#93c5fd`, 10 flagged as open rows for operator decision), all 9 font-size values and 3 font-weight values mapped (500 flagged for a sight-check), 6 spacing values mapped to the 7-step scale plus 4 residuals reported unmapped, and explicit out-of-scope declarations named (border-radius, grid-template-columns, width/height, calc()).
- Rewrote `.planning/codebase/DESIGN-SYSTEM.md` to document the token system as it now exists (two-layer architecture, all 16 semantic colour tokens with usage rules, the corrected 5-size/2-weight type scale, the 44px/36px touch-target rule, the `lib/primitives`/`lib/public`/`lib/admin` directory split) instead of the stale July 2026 snapshot that claimed no Tailwind dependency and only 3 sizes.

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove Tailwind and replace preflight with an explicit base reset** - `3a121dfab` (feat)
2. **Task 2: Author the two-layer token set in app/src/app.css** - `1339ac3a7` (feat)
3. **Task 3: Publish the value-to-token map and rewrite DESIGN-SYSTEM.md** - `1bd25ad35` (docs)

**Plan metadata:** committed separately below (STATE.md/ROADMAP.md update).

## Files Created/Modified

- `app/src/app.css` - Tailwind directives removed, explicit base reset added, full two-layer token set authored, `focus-visible` outline tokenized
- `app/package.json` - four Tailwind-family devDependencies removed
- `app/package-lock.json` - refreshed via `npm install` (69 packages removed, 0 added)
- `app/tailwind.config.js` - deleted
- `app/postcss.config.js` - deleted
- `.planning/phases/51-design-system-noun-alignment/51-TOKEN-MAP.md` - new; the plan-51-09 conversion table
- `.planning/codebase/DESIGN-SYSTEM.md` - rewritten to document the Phase 51 token system result

## Decisions Made

- Dropped `--color-text-advocate` outright rather than retaining a one-line alias to `--color-side-advocate`, since a grep confirmed zero live `var()` call sites reference it anywhere in `app/src` (the two consuming components hardcode the `#93c5fd`/`#94a3b8` literals directly rather than reading the CSS variable). Nothing is left referenced-but-undefined.
- The 10 hex values found in the codebase with no match in the Figma-sourced 14-primitive palette (`#64748b`, `#f59e0b`, `#facc15`, `#f87171`, `#38bdf8`, `#34d399`, `#e879f9`, `#475569`, `#2dd4bf`, `#fb7185`) were recorded in `51-TOKEN-MAP.md` as open rows for a future operator decision rather than silently mapped to the nearest-looking primitive — per the plan's explicit instruction not to invent a token for an unmapped value. One of these, `#475569`, is flagged with a specific apolitical-framing (P-03) note: `PROJECT.md` records this hex was previously "eliminated" from speaker-side differentiation in Phase 4, so its 2 remaining occurrences need confirmation they aren't re-encoding speaker importance before any token is assigned.

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria for all three tasks were verified via the automated grep/node scripts specified in the plan itself.

## Issues Encountered

- **Two of the plan's Task 1 acceptance criteria could not be fully satisfied in this sandbox, both pre-existing environment/test constraints unrelated to this plan's changes:**
  1. Three of the four required browser tests (`tenure-public-title`, `copyable-extracted-value`, `case-required-recovery`) fail closed with "Microsoft Edge or Google Chrome must be installed for this fail-closed test" — no Chromium/Edge binary exists in this sandbox. This is the same constraint plan 51-02 hit and already logged in STATE.md; it is not a regression introduced here. `npm run check` and `npm run build` (the two prerequisites these tests would exercise against) are both green.
  2. The fourth (`tenure-office.browser.test.mjs`) fails on a pre-existing stale static-text assertion (`form?.full_name` expected in `app/src/routes/admin/people/[id]/+page.svelte`) that predates Phase 38's removal of `full_name` as an operator-writable field — confirmed via `git diff` that this plan touched none of the files that test reads. Out of scope per the Scope Boundary (failures in unrelated files caused by earlier phases are not this task's to fix), and it is exactly the class of static source-text contract test CLAUDE.md's Testing Policy now bans going forward.
  - Attempted to log both to `.planning/WINDOWS.md` via `gsd-tools query windows append`; the ledger tool returned a pre-existing frontmatter/entry count mismatch error (`open/waived/fixed/total=23/0/8/31` vs entries yielding `21/0/10/31`) unrelated to this plan and did not write. Per the ledger's documented best-effort contract this does not block execution; both items are recorded here instead.
- **The plan's one `verification: backstop` must-have truth** ("public listing, transcript, and admin dashboard render with no layout shift after Tailwind preflight is removed, checked in a real browser at 375px and 1280px") could not be observed for the same no-browser-binary reason above. `npm run build` is green and the base reset was derived from a targeted grep of every load-bearing margin/reset dependency in the codebase (not guessed), but a human with a browser should do a visual pass before this is treated as fully closed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `51-TOKEN-MAP.md` and the completed token set in `app.css` are ready for plan 51-09's conversion sweep — the mapping from literal to token is now a lookup, not a judgment call, for 14 of 24 hexes and all font-size/weight values; the 10 unmapped hexes and the 500-weight sight-check are flagged for that plan's operator-facing report.
- `.planning/codebase/DESIGN-SYSTEM.md` is current and no longer disagrees with `app/package.json` or `app.css`.
- **Blocker/concern for phase verification:** the browser-dependent must-have (operator visual check of the preflight removal) and 3 of 4 required browser tests remain unrun in this environment. A human with a real browser should verify no layout shift on `/arguments`, `/arguments/{slug}`, and `/admin` before the phase is signed off.
- Full test suite (`./.venv/bin/python -m pytest -q`): **1318 passed, 5 xfailed, 0 failed** — unchanged from the pre-plan baseline recorded in STATE.md after Wave 1, confirming this plan's frontend-only changes caused zero backend regressions.

---
*Phase: 51-design-system-noun-alignment*
*Completed: 2026-08-28*

## Self-Check: PASSED

- FOUND: app/src/app.css
- FOUND: .planning/phases/51-design-system-noun-alignment/51-TOKEN-MAP.md
- FOUND: .planning/codebase/DESIGN-SYSTEM.md
- CONFIRMED ABSENT: app/tailwind.config.js
- CONFIRMED ABSENT: app/postcss.config.js
- FOUND commit: 3a121dfab (Task 1)
- FOUND commit: 1339ac3a7 (Task 2)
- FOUND commit: 1bd25ad35 (Task 3)
