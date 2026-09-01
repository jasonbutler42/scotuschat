---
phase: 51-design-system-noun-alignment
plan: 09
subsystem: ui
tags: [design-tokens, codemod, svelte, admin, spacing-scale, d-04, d-08]

requires:
  - phase: 51-design-system-noun-alignment
    provides: "plan 51-03's 51-TOKEN-MAP.md (the conversion specification); plan 51-06's lib/primitives/Badge.svelte; plan 51-07's token-converted lib/public/ pattern; app/src/app.css's two-layer token architecture (D-02)"
provides:
  - "app/scripts/tokenize-styles.mjs — a committed, unit-tested, idempotent literal-to-token codemod"
  - "app/scripts/tokenize-styles.test.mjs — 26 node --test cases covering every rule and three real regressions"
  - "app/package.json tokens:convert script"
  - "Zero mapped hex, zero numeric font-size, zero numeric font-weight in any .svelte under app/src"
  - ".planning/phases/51-design-system-noun-alignment/51-ADMIN-ARTIFACTS.md — the D-08 artifact report awaiting operator rulings in 51-10"
  - "An eight-step spacing scale with 12px added and the names shifted up"
affects: [51-10-operator-rulings, future-admin-work, design-system-maintenance]

actuals:
  tokens: 92638
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Report-then-apply codemod: the script's report mode is the authoritative review surface, so a 22-file conversion is reviewed as one mapping table plus a diff of hunks rather than as 22 hand edits."
    - "Unmapped means reported, never rounded. A value the specification does not cover is left byte-identical and surfaced for a decision — rounding to the nearest step is how a design system acquires decisions nobody made."
    - "Pixel-equivalence proof for a token rename: resolve every declaration to px before and after and compare (file, property, resolved-px) buckets. Proves a rename is a no-op across surfaces a browser cannot reach (admin is behind auth)."

key-files:
  created:
    - app/scripts/tokenize-styles.mjs
    - app/scripts/tokenize-styles.test.mjs
    - .planning/phases/51-design-system-noun-alignment/51-ADMIN-ARTIFACTS.md
  modified:
    - app/src/app.css
    - app/package.json
    - app/src/lib/components/TopNav.svelte
    - app/src/lib/admin/ (9 components)
    - app/src/routes/admin/ (11 routes)
    - app/src/routes/attributions/+page.svelte
    - .planning/codebase/DESIGN-SYSTEM.md
    - .planning/phases/51-design-system-noun-alignment/51-TOKEN-MAP.md

key-decisions:
  - "The script's script-block reach is narrower than 'never touch it': it rewrites only string literals that are themselves styling — a bare mapped hex, or a string that parses as a CSS declaration list. Several admin screens build style strings in TypeScript and the phase gate counts those, but surrounding code is never touched."
  - "Numerals inside a Svelte {...} expression are JavaScript and are never rewritten. Colour is exempt from that mask because a hex inside an expression is always quoted, so a quoted var() stays valid in both languages."
  - "12px was promoted to --space-md and every name from md up shifted one step. Operator's call, taken on evidence: 153 of its 154 sites were admin, second only to 8px and ahead of 16px."
  - "A density token was considered and rejected on evidence: admin uses 16px 150 times ALONGSIDE 12px 153 times, so they are distinct steps rather than one compressed into the other. Remapping 16->12 for admin would have flattened 150 deliberate decisions to fix 153 others."
  - "The 10 unmapped colours were left in place. The token map forbids inventing tokens for them without a decision, so the phase gate's 'zero hex' criterion cannot be met until the operator rules in 51-10 — a conflict resolved in favour of the map's prohibition."

patterns-established:
  - "Pattern: a value shift disguised as a rename must land atomically. Redefining --space-* alone would have tightened the whole UI one step with a green typecheck, a green build and 1,348 green tests — so the redefinition and all 695 reference remaps ship in one commit, in a single simultaneous pass."
  - "Pattern: string-literal scanning needs a tokenizer, not a regex. An apostrophe in a code comment pairs with the next quote in real code and misaligns every span after it."

requirements-completed: [DS-02, DS-03]

coverage:
  - id: D1
    description: "A committed, idempotent codemod converts literal style values to token references per 51-TOKEN-MAP.md"
    requirement: DS-03
    verification:
      - kind: unit
        ref: "app/scripts/tokenize-styles.test.mjs (26 cases, node --test)"
      - kind: other
        ref: "second `node scripts/tokenize-styles.mjs --apply src` run reports 'files changed: 0' — idempotency proven on the real codebase, not only fixtures"
  - id: D2
    description: "No mapped hex, numeric font-size, or numeric font-weight remains in any .svelte file under app/src"
    requirement: DS-03
    verification:
      - kind: other
        ref: "structural absence sweep over the computed file set: 0 mapped hex, 0 `font-size: <digit>`, 0 `font-weight: 400|500|600`"
  - id: D3
    description: "The D-08 artifact report lists every surviving visual/UX artifact for operator judgment"
    requirement: DS-02
    verification:
      - kind: manual_procedural
        ref: ".planning/phases/51-design-system-noun-alignment/51-ADMIN-ARTIFACTS.md — sections A-E, ruling columns empty pending 51-10"
  - id: D4
    description: "The spacing scale gains a 12px step with every reference remapped and no rendered change"
    verification:
      - kind: other
        ref: "resolved-px comparison across all spacing declarations: 409 (file, property, resolved-px) buckets before and after, 0 changed"
      - kind: automated_ui
        ref: "playwright: transcript at 390x844 re-measures identically — bench/advocate gap 4/4, outer inset 8/8, bubble 315px"
---

## Accomplishments

- **Built `tokenize-styles.mjs`**, a report-then-apply codemod implementing 51-TOKEN-MAP.md and nothing beyond it, with 26 unit tests and idempotency proven on the real codebase.
- **Converted 1,566 literals across 22 `.svelte` files.** Zero mapped hex, zero numeric `font-size`, zero numeric `font-weight` remain anywhere under `app/src`.
- **Wrote `51-ADMIN-ARTIFACTS.md`**, the D-08 report: two coherent admin colour scales that want tokens, the spacing residuals, the two `font-weight: 500` sites, and four structural artifacts including `tierBadgeStyle` duplicated verbatim across three files.
- **Added 12px to the spacing scale** at the operator's direction, shifting the names up so the t-shirt sequence stays intact, and remapped all 695 references atomically.
- **Closed the token map's P-03 question on `#475569`**: both surviving sites colour a record's `review_state`, not a speaker side, so it is safe to tokenise.

## Deviations from plan

- **The plan's zero-hex acceptance criterion is not met, and cannot be.** It requires `grep` for hex to return no files, but 29 occurrences of the token map's 10 open rows remain — and the map explicitly forbids assigning them without an operator decision. The prohibition wins; the gate closes when 51-10 rules. Recorded as section A of the artifact report.
- **The script does reach into script blocks**, contrary to the plan's description of it. Several admin screens build style strings in TypeScript, and the plan's own acceptance criteria count those literals. Reach is confined to string literals that are themselves styling.
- **The five real-browser tests were not run.** The Playwright Chromium in this environment cannot load `libnspr4.so`. They are outstanding, not green. Public surfaces were checked through a working browser instead; the eleven admin screens remain for the operator's eye in 51-10.
- **Plan 51-09 was executed inline rather than by a spawned executor**, and the spacing-scale change was added mid-plan at the operator's direction.

## Defects found and fixed

Three, each pinned by a test that now guards it:

1. **Numerals inside a Svelte expression were rewritten as if they were CSS.** `font-weight: {mode === 'url' ? 600 : 400}` became `{... ? var(--x) : var(--y)}` — invalid JavaScript, caught by typecheck. Expression spans are now masked for the numeric rules.
2. **A regex cannot scan for string literals.** The apostrophe in `// migration 0029's fold` paired with the next quote in real code and misaligned every span after it, silently skipping whole files. Replaced with a state machine that understands comments. The source tree was reset and the conversion redone cleanly, because this class of bug can corrupt as easily as it can skip.
3. **The bare-hex rule was too broad in markup** and rewrote a `title="#334155"` attribute. Now confined to Svelte `{...}` expression spans.

## Verification

| Gate | Result |
|---|---|
| `node --test app/scripts/tokenize-styles.test.mjs` | 26 passed |
| `npm --prefix app run check` | 0 errors |
| `npm --prefix app run build` | green |
| `pytest api/tests tests pipeline/tests -q` | 1348 passed, 5 xfailed |
| Script idempotency on real codebase | second apply: 0 files changed |
| Spacing pixel-equivalence | 409 buckets before/after, 0 changed |
| Five `app/tests/*.browser.test.mjs` | **NOT RUN** — Chromium cannot load `libnspr4.so` |

## For 51-10

`51-ADMIN-ARTIFACTS.md` carries the rulings. B-01 is already closed. The three that need real judgment: the two admin colour scales (A-01…A-08), whether `.pill`'s `#f59e0b` is its own thing (A-10), and the long-text behaviour in dense tables at 375px (D-04), which was deliberately preserved unchanged and never inspected.
