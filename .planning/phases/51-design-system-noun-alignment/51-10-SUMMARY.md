---
phase: 51-design-system-noun-alignment
plan: 10
subsystem: ui
tags: [design-tokens, admin, badge-primitive, design-system-doc, browser-tests, operator-walkthrough, d-01, d-02, d-03, d-04]

requires:
  - phase: 51-design-system-noun-alignment
    provides: "plan 51-09's 51-ADMIN-ARTIFACTS.md (the D-08 artifact report awaiting rulings); plan 51-06's lib/primitives/Badge.svelte; plan 51-03's app/src/app.css two-layer token architecture; plan 51-02's amended success criteria"
provides:
  - "Every tier/review/status/run-state badge in the admin UI rendered by lib/primitives/Badge.svelte — no per-file style builders remain"
  - "BadgeTone extended with `running` and `failed`; Badge gains an optional `leading` snippet and `ariaLabel`"
  - "TONE_COLOR exported from badge-tone.ts so non-badge surfaces colour-match without a second copy of the vocabulary"
  - "admin/help styled the way every other screen is — no page-level style constants built as strings in a script block"
  - ".planning/codebase/DESIGN-SYSTEM.md reconciled bidirectionally against app/src/app.css (35 primitives, 75 semantic tokens)"
  - "app/tests/helpers/browser-executable.mjs and paths.mjs — one browser resolver and cwd-independent paths for every browser harness"
  - "A real-browser P-06 test pinning long-case-name behaviour on the public listing"
  - "Five todos in .planning/todos/pending/ carrying every walkthrough finding not fixed here"
affects: [phase-52, design-system-maintenance, future-admin-work, pdf-route-when-promoted]

actuals:
  tasks: 3
  commits: 12

tech-stack:
  added: []
  patterns:
    - "Domain vocabulary as a typed union, shape in one primitive: a screen maps its own domain value to a `BadgeTone` and owns nothing else. A tone that does not exist is a compile error rather than a badge that renders in the fallback colour."
    - "Colour-match without being the component: the step card's 3px border-left is not a badge and cannot render as one, so it reads the same exported TONE_COLOR table the badge does. A card and the badge on it cannot disagree by construction."
    - "Prove a refactor is a no-op by measuring both sides: computed styles and getBoundingClientRect for every element, against the committed version served from the same dev server with the change stashed. Byte-identical declarations are the intent; identical rendered geometry is the evidence."
    - "A bidirectional doc-to-code contract is mechanical, so check values as well as names. A name-only diff passed DESIGN-SYSTEM.md while one row carried a value a P-03 fix had superseded."
    - "Assert rendered geometry, not source text. The new P-06 test was verified to fail — adding `text-overflow: ellipsis` turned it red and left its six siblings green."

key-files:
  created:
    - app/tests/helpers/browser-executable.mjs
    - app/tests/helpers/paths.mjs
    - .planning/todos/pending/2026-09-03-speaker-popover-height-and-scroll-placement.md
    - .planning/todos/pending/2026-09-03-transcript-nav-return-to-top-segment.md
    - .planning/todos/pending/2026-09-03-speaker-colour-on-bubbles-and-photo-avatars.md
    - .planning/todos/pending/2026-09-03-dense-admin-tables-at-mobile-widths.md
    - .planning/todos/pending/2026-09-03-consolidated-dockets-unreachable-without-pdf-path.md
  modified:
    - app/src/lib/primitives/Badge.svelte
    - app/src/lib/primitives/badge-tone.ts
    - app/src/lib/admin/RunStatusCard.svelte
    - app/src/routes/admin/arguments/+page.svelte
    - app/src/routes/admin/arguments/[id]/+page.svelte
    - app/src/routes/admin/help/+page.svelte
    - app/src/routes/admin/pipeline/+page.svelte
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte
    - app/src/routes/admin/review/+page.svelte
    - app/tests/arguments-listing.browser.test.mjs
    - app/tests/case-required-recovery.browser.test.mjs
    - app/tests/tenure-public-title.browser.test.mjs
    - .planning/codebase/DESIGN-SYSTEM.md
    - .planning/phases/51-design-system-noun-alignment/51-ADMIN-ARTIFACTS.md
  deleted:
    - app/tests/tenure-office.browser.test.mjs

coverage:
  - id: D1
    description: "Every row in 51-ADMIN-ARTIFACTS.md carries an operator ruling, and every fix-now ruling is applied"
    requirement: DS-02
    verification:
      - kind: manual_procedural
        ref: "51-ADMIN-ARTIFACTS.md ruling table — D-01, D-02, D-03, D-04 all ruled `fix now`, all four applied in commits 226a3581d, 888ab25b7, fea0a49aa"
        status: pass
    human_judgment: true
    rationale: "The rulings are the operator's product judgment on surfaced artifacts; only he can say a row is ruled."
  - id: D2
    description: "Every admin badge renders through the shared primitive; no per-file badge style builder survives"
    requirement: DS-02
    verification:
      - kind: other
        ref: "structural absence sweep over app/src: zero `badgeStyle`/`tierBadgeStyle`/`reviewBadgeStyle`/`statusBadgeStyle`/`BADGE_COLOR` definitions outside lib/primitives/"
        status: pass
      - kind: automated_ui
        ref: "playwright: /admin/help renders 12 badges across all three vocabularies with 12 distinct colours, border matching text, 0.14 tint composited, uniform 26px height; /admin/pipeline renders all six run states with no badge overflowing its td"
        status: pass
    human_judgment: false
  - id: D3
    description: "admin/help styles the way every other screen does, with no rendered change"
    requirement: DS-02
    verification:
      - kind: automated_ui
        ref: "playwright A/B against the committed version on the same dev server: computed styles and getBoundingClientRect for all four cards, headings and body paragraphs identical, including each card's vertical offset and the 2938px document height"
        status: pass
    human_judgment: false
  - id: D4
    description: "DESIGN-SYSTEM.md describes the token set app/src/app.css actually declares, in both directions"
    requirement: DS-03
    verification:
      - kind: other
        ref: "bidirectional set diff: 75/75 semantic names, 35/35 primitive names, 69/69 documented values match the CSS exactly, zero tokens named in the doc that the CSS does not declare"
        status: pass
    human_judgment: false
  - id: D5
    description: "Long text on the public listing is not truncated, clipped or ellipsised, and the docket stays visible (P-06)"
    requirement: DS-04
    verification:
      - kind: automated_ui
        ref: "app/tests/arguments-listing.browser.test.mjs test 7 — 375px viewport, asserts rendered geometry; verified to fail when `text-overflow: ellipsis` is introduced"
        status: pass
      - kind: manual_procedural
        ref: "operator walkthrough 2026-09-03 against a real 164-character corpus case (argument 1841) at 375px and 1280px"
        status: pass
    human_judgment: true
    rationale: "The automated test pins non-truncation; whether the wrapped result reads well beside a 31-character neighbour is taste, and the operator confirmed it."
  - id: D6
    description: "The public path reads as intended end to end at 375px and 1280px, and the apolitical prohibitions hold on every public screen"
    requirement: DS-01
    verification:
      - kind: manual_procedural
        ref: "operator walkthrough 2026-09-03: /arguments -> term -> argument -> speaker popover -> full scroll, at both viewports; P-01..P-06 sweep on every public screen"
        status: pass
    human_judgment: true
    rationale: "Focal points, typographic parity between a Justice and an advocate turn, and the absence of editorial prominence are judgments about what the page communicates. No automated check substitutes for the operator's eye here, and the Testing Policy says so explicitly."
  - id: D7
    description: "All eleven admin screens behave as before the conversion, with the Task 1 rulings landed as agreed"
    requirement: DS-02
    verification:
      - kind: manual_procedural
        ref: "operator walkthrough 2026-09-03: ten screens walked; /admin/pipeline shows its empty state because the fixture seeds ImportRuns and deliberately no AdminJob, so no job-detail screen exists to walk"
        status: pass
      - kind: automated_ui
        ref: "playwright: /admin/arguments/1841 renders consolidated dockets [84-1494, 84-1495] from seeded non-lead rows — the render path Phase 51 shipped"
        status: pass
    human_judgment: true
    rationale: "The badge weight change (regular -> semibold) and the new tinted fills are visual changes across every admin screen. Accepting them is the operator's call and cannot be automated."
  - id: D8
    description: "The shipped surfaces match the Figma file's Public, Primitives and Admin pages, or the drift is ruled"
    requirement: DS-03
    verification:
      - kind: manual_procedural
        ref: "operator compared all three pages against the shipped surfaces on 2026-09-03 and reported no drift"
        status: pass
    human_judgment: true
    rationale: "Comparing a design file to a running app is not mechanisable; D-06's name-matching rule exists because drift noticed and not written down is the failure."
  - id: D9
    description: "The real-browser suite runs and is green"
    verification:
      - kind: automated_ui
        ref: "`node --test --test-concurrency=1 app/tests/*.browser.test.mjs` — 10 tests, 10 pass, 0 fail"
        status: pass
      - kind: other
        ref: "svelte-check 0 errors (33 warnings, unchanged from baseline); production build clean"
        status: pass
    human_judgment: false

duration: 2d
completed: 2026-09-03
status: complete
---

# Plan 51-10 — Operator rulings, the artifacts they ruled, and the walkthrough

Closes Phase 51. Three tasks: get the operator's ruling on every surfaced admin
artifact, apply the rulings, and walk the whole thing in a real browser.

## Accomplishments

**Every artifact ruled and every fix-now ruling applied.** D-01/D-03 folded all
badge rendering into `lib/primitives/Badge.svelte` — six files carried their own
style builders, and `admin/help`'s own comment admitted its copies were "copied
verbatim from admin/arguments". A sweep for per-file badge style builders now
returns nothing. D-02 removed the three page-level style constants `admin/help`
built as strings in its script block, the only instance of that mechanism in a
codebase of eleven admin screens and nine admin components. D-04 was already
done at plan open.

**DESIGN-SYSTEM.md now describes the tokens that exist.** It documented 38 of 75
semantic tokens. Four whole families were missing, each load-bearing: the
per-speaker ramp and its L\* 78 equality constraint (which is what makes a
per-speaker palette legal under P-03, and lived only in a CSS comment), the side
families, both admin lifecycle scales, and the transcript reading-layer geometry.

**The browser suite went from unrunnable to green.** It had never run on this
machine. Two causes wore one symptom: the host had no NSS libraries, and — after
that was fixed — every harness probed three fixed system paths and never looked
at the Playwright-managed Chromium that actually works.

**The operator walked it.** Public path at both viewports, empty and error
states, the apolitical sweep, ten admin screens, and the Figma comparison.

## Deviations from plan

**The walkthrough's fixture gaps were closed by importing from the corpus, not
by building a PDF fixture.** The plan assumed a consolidated case with a long
name would be available. None was: the fixture set's longest name is 50
characters and it is not published, and no fixture carries consolidated dockets.
Rather than build a PDF fixture — explicitly deprioritized work under the
2026-08-18 corpus-first decision, and the blocking gap recorded in Phase 999.11 —
`import-convokit --conversation-id 19018` brought in a real 164-character case in
term 1985. Publishing it also produced the plural count form, which no
combination of the original four fixtures could ever show, because each sits in
a different term.

**Argument 1841 published over the trust gate.** Its tier is `uncertain`, so
publishing required an override reason. That is the overridable gate working as
designed, and it left the fixture set with something it never had: a
published-with-override argument whose blocked-publish panel and status-log audit
trail are visible on the admin detail page.

**One test retired rather than repaired.** `tenure-office.browser.test.mjs`
launched no browser despite the name and regex-matched source text — the pattern
the Testing Policy bans. Retired at the operator's ruling.

## Defects found and fixed

- Two badge render sites were losing a live affordance under the naive
  conversion: the pipeline step badge carries an animated spinner and an
  accessible name. `Badge` gained an optional `leading` snippet and `ariaLabel`
  rather than dropping them.
- `tenure-public-title.browser.test.mjs` asserted a year-only tenure range that
  plan 39-08 deliberately replaced with month + year on 2026-07-28. The
  expectation was authored in 37-04 and `git log -S` shows no commit ever updated
  it — 39-08 should have retired it in the same commit and could not, because no
  browser was ever found to run the test.
- `case-required-recovery.browser.test.mjs` waited a fixed 500ms for hydration
  before submitting. That is a race: `invalid` fires once, and if it fires before
  Svelte attaches `oninvalid`, nothing re-fires it. The app was verified correct
  by driving it directly; the sleep was replaced with re-submitting until the
  alert renders.
- `DESIGN-SYSTEM.md` recorded `--color-side-bench` as `var(--slate-400)` in both
  the role table and the two-layer prose, describing it as a deliberate shared
  primitive. It resolves to `var(--l78-slate)`, moved there because the old value
  made the advocate side measurably brighter than the bench across 164 avatar
  fills — a P-03 violation. The document was describing the state that fix
  superseded, and describing it as intentional.
- `arguments-listing` test 1 hardcoded `/2 arguments/` instead of reading the
  constant that feeds the fixture it asserts against.

## Verification

The four Phase 51 success criteria, as amended by plan 51-02:

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | `/arguments`, `/arguments/term/{year}`, `/arguments/{slug}` resolve; `/cases` gone | **Met** | All three 200; `/cases` 404 on app and API; no `app/src/routes/cases` directory |
| 2 | Reused UI extracted into a shared component library | **Met** | `lib/primitives/` (Button, Badge, Card, Input, badge-tone.ts) and `lib/public/` (7 components); every admin badge routes through `Badge` |
| 3 | Design tokens established as the visual foundation | **Met** | 35 primitives + 75 semantic tokens, two-layer; zero hex literals in `app/src`; DESIGN-SYSTEM.md reconciled both directions |
| 4 | Arguments listing style decided and implemented | **Met** | Operator walked it at 375px and 1280px; long-name behaviour now pinned by a real browser test |

Browser suite 10/10. `svelte-check` 0 errors, 33 warnings unchanged from
baseline. Production build clean.

## Carried forward

Five todos in `.planning/todos/pending/`, none blocking:

- `2026-09-03-speaker-popover-height-and-scroll-placement` — the card is too tall
  and drifts when the transcript scrolls under it.
- `2026-09-03-transcript-nav-return-to-top-segment` — a rail affordance for
  returning to the head of a long argument; the label is unsettled.
- `2026-09-03-speaker-colour-on-bubbles-and-photo-avatars` — extend the
  per-speaker colour to the bubbles, and decide what a photo avatar does to
  colour-as-identity. Includes the correction that photos are not broken: they
  render in `SpeakerPopover` and the transcript avatars have never had an `<img>`
  at all.
- `2026-09-03-dense-admin-tables-at-mobile-widths` — accepted for now.
- `2026-09-03-consolidated-dockets-unreachable-without-pdf-path` — the reachability
  chain, written down so it is not re-derived.

**Not automated, deliberately:** Justice/advocate typographic parity (P-03) is
measurable — computed size, weight, and the L\* of both turns — and was left
un-pinned because what the assertion should claim needs a decision before it is
written into a test. Everything else the walkthrough covered that could be
mechanised, was.

**Environment note:** two non-lead `CaseArgument` rows were seeded on argument
1841 to exercise the consolidated-docket render path. They are dev-only and
disappear on the next `reset-to-fixture`.
