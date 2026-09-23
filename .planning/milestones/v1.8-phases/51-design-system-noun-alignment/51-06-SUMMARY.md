---
phase: 51-design-system-noun-alignment
plan: 06
subsystem: ui
tags: [svelte5, design-system, primitives, lucide-svelte, accessibility, typescript]

requires:
  - phase: 51-design-system-noun-alignment (plan 51-03)
    provides: the full two-layer token set in app/src/app.css that every primitive value is a var(--token) reference into
  - phase: 51-design-system-noun-alignment (plan 51-05)
    provides: the lib/primitives / lib/public / lib/admin directory split and placement rule this plan populates
provides:
  - Four shared primitives (Button, Badge, Input, Card) in app/src/lib/primitives/, token-only, surface-agnostic
  - StatCard.svelte delegating to Card (one card definition site)
  - DocketPillInput.svelte's free-text field delegating to Input
  - @lucide/svelte as the icon dependency (operator-approved substitution for the deprecated lucide-svelte D-18 named)
  - Type-enforced accessible-name contract for icon-only Button construction
  - D-18 bits-ui-vs-hand-rolled report for all four primitives
affects: [51-07, 51-08, 51-09, 51-10]

actuals:
  tokens: 7751
  tasks: 3
  commits: 4

tech-stack:
  added: ["@lucide/svelte@^1.35.0"]
  patterns:
    - "Discriminated-union prop types to make an accessibility contract a compile-time constraint (Button's IconOnlyButtonProps | TextButtonProps), not a documented convention"
    - "Primitive delegation: an existing component (StatCard, DocketPillInput) is rewritten to call the new shared primitive rather than duplicating its markup, keeping the primitive's real adoption sites as the regression backstop the Testing Policy asks for"

key-files:
  created:
    - app/src/lib/primitives/Card.svelte
    - app/src/lib/primitives/Badge.svelte
    - app/src/lib/primitives/Button.svelte
    - app/src/lib/primitives/Input.svelte
  modified:
    - app/src/lib/admin/StatCard.svelte
    - app/src/lib/admin/DocketPillInput.svelte
    - app/package.json
    - app/package-lock.json
    - .planning/phases/51-design-system-noun-alignment/51-DESIGN-DECISIONS.md
    - .planning/phases/51-design-system-noun-alignment/51-UI-SPEC.md

key-decisions:
  - "Substituted @lucide/svelte@^1.35.0 for the literal lucide-svelte D-18 named, after the Task 1 package-legitimacy gate found lucide-svelte deprecated in favor of the scoped successor package (same maintainer/repo); operator approved"
  - "Corrected a pre-existing MIT->ISC license misstatement for the lucide package in both 51-UI-SPEC.md and 51-DESIGN-DECISIONS.md's D-18 section"
  - "Button's icon-only accessible-name contract is enforced by a TypeScript discriminated union, not by runtime validation or convention -- omitting label/ariaLabel/ariaLabelledby on an icon-only Button is a compile error"
  - "All four primitives are hand-rolled, not built on bits-ui -- none opens a focus-managed overlay or roving-tabindex control, the only case D-18 reserves for the dependency"
  - "Input.svelte generalizes DocketPillInput's split invalid/descriptionId (caller-owned) + shapeError (component-owned) validation pattern into one component that supports both tracks via describedBy (pass-through) and errorMessage/errorId (self-rendered), rather than replicating the split verbatim"

requirements-completed: [DS-02, DS-03]

coverage:
  - id: D1
    description: "Card and Badge primitives extracted, token-only, StatCard delegates to Card with a live render path on the admin dashboard"
    requirement: "DS-02"
    verification:
      - kind: other
        ref: "npm --prefix app run check (0 errors, 37 baseline warnings unchanged)"
        status: pass
      - kind: other
        ref: "npm --prefix app run build"
        status: pass
      - kind: other
        ref: "node -e raw-hex/font-size sweep over Card.svelte, Badge.svelte"
        status: pass
      - kind: other
        ref: "grep -c 'lib/public|lib/admin' Card.svelte Badge.svelte == 0"
        status: pass
      - kind: other
        ref: "deliberate temporary <Badge /> (no label) -> tsc error 'Property label is missing... required in type BadgeProps', then reverted"
        status: pass
    human_judgment: true
    rationale: "The admin dashboard's stat cards rendering visually unchanged after the Card delegation needs a real browser -- no Chromium/Edge binary in this sandbox (same constraint as every prior plan in this phase). npm check/build green is the strongest available automated signal for a pure-delegation refactor; the visual claim itself is unverified here."
  - id: D2
    description: "Button and Input primitives extracted, token-only, with a type-enforced icon-only accessible-name contract; DocketPillInput's free-text field adopts Input; D-18 bits-ui report recorded"
    requirement: "DS-02"
    verification:
      - kind: other
        ref: "npm --prefix app run check (0 errors, 37 baseline warnings unchanged)"
        status: pass
      - kind: other
        ref: "npm --prefix app run build"
        status: pass
      - kind: other
        ref: "node -e raw-hex/font-size sweep over Button.svelte, Input.svelte"
        status: pass
      - kind: other
        ref: "grep -c 'title=' Button.svelte == 0"
        status: pass
      - kind: other
        ref: "deliberate temporary <Button icon={X} /> (no accessible name) -> tsc error 'Property children is missing... required in type TextButtonProps', then reverted; valid icon+label/ariaLabel/ariaLabelledby/children/loading/dense constructions all typecheck clean"
        status: pass
      - kind: e2e
        ref: "app/tests/case-required-recovery.browser.test.mjs"
        status: unknown
    human_judgment: true
    rationale: "case-required-recovery.browser.test.mjs cannot run in this sandbox (no Chromium/Edge binary) -- confirmed via a real run, which fails at its own fail-closed browser-presence assertion. Separately, reading the test showed it drives admin/arguments/[id]'s own docket_number field, NOT DocketPillInput's free-text field the Input primitive was adopted into, so it would not have proven the adoption even if it could run. The pipeline page's docket entry field (placeholder, focus ring, invalid-state error text) after the Input adoption needs an operator visual check in a real browser."
  - id: D3
    description: "Icon dependency installed under the package-legitimacy gate (Task 1): @lucide/svelte substituted for the deprecated lucide-svelte D-18 named, operator-approved, install diff adds exactly one dependency"
    requirement: "DS-02"
    verification:
      - kind: other
        ref: "npm --prefix app install @lucide/svelte@^1.35.0; git diff app/package.json shows exactly one line added"
        status: pass
      - kind: other
        ref: "git diff app/package-lock.json shows exactly one new node_modules/@lucide/svelte entry with no dependencies key and license ISC; esbuild count unchanged (2) before/after, confirming it is a pre-existing vite transitive, not newly introduced"
        status: pass
    human_judgment: false
  - id: D4
    description: "51-DESIGN-DECISIONS.md gains the D-18 substitution amendment and the D-18 bits-ui-vs-hand-rolled report, appended (never rewritten); all four pre-existing decisions (D-16, D-18, E4, D-19) confirmed still present before every commit"
    requirement: ""
    verification:
      - kind: other
        ref: "grep -c for 'Term-row variant (D-16)', 'Icon library (D-18)', 'Button loading variant (UI-SPEC E4)', 'Transcript style (D-19' == 1 each, checked before every commit in this plan"
        status: pass
    human_judgment: false

duration: 46min
completed: 2026-08-28
status: complete
---

# Phase 51 Plan 06: Shared Primitives Summary

**Extracted Button, Badge, Input, and Card into `lib/primitives/`, generalized from the codebase's existing card and validated-input patterns rather than authored greenfield, with Button's icon-only accessible-name contract enforced by a TypeScript discriminated union rather than a runtime check or a comment.**

## Performance

- **Duration:** 46 min (checkpoint wait excluded)
- **Started:** 2026-08-28T16:xx (context load)
- **Completed:** 2026-08-28T17:37Z
- **Tasks:** 3 (1 checkpoint + 2 auto)
- **Files modified:** 10

## Accomplishments

- Four primitives (`Button`, `Badge`, `Input`, `Card`) in `app/src/lib/primitives/`, filenames matching the Figma `Primitives` frame names character for character, every value a `var(--token)` reference, no primitive importing from `lib/public` or `lib/admin`.
- `StatCard.svelte` now delegates to `Card` — the card surface/border/radius/padding pattern has exactly one definition site, with `Card` getting a live render path on the admin dashboard.
- `DocketPillInput.svelte`'s free-text entry field now renders through `Input`, adopting its touch-target sizing while keeping `DocketPillInput`'s external prop shape (`invalid`, `descriptionId`) and behavior unchanged.
- Package-legitimacy gate (T-51-SC) caught a real defect in D-18's own recorded decision before it landed: `lucide-svelte` is deprecated in favor of the scoped `@lucide/svelte` successor. Operator approved the substitution; `@lucide/svelte@^1.35.0` installed, adding exactly one dependency with zero transitive deps.
- Every icon-only `Button` construction without a `label`/`ariaLabel`/`ariaLabelledby` is a TypeScript compile error — proven live with a deliberate temporary violation, not asserted.
- D-18's bits-ui-vs-hand-rolled report recorded: all four primitives are hand-rolled (none needed focus management, keyboard navigation, or ARIA state genuinely hard enough to justify the dependency).

## Task Commits

Each task was committed atomically:

1. **Task 1: Package legitimacy gate — the icon library, before any install** — checkpoint reached, presented to operator, resumed with approval; `chore(51-06): install @lucide/svelte, operator-approved D-18 substitution` — `0f075113e`
2. **Task 2: `Card` and `Badge` — extract the two container primitives** — `feat(51-06): extract Card and Badge primitives, StatCard delegates` — `5f9901310`
3. **Task 3: `Button` and `Input`, plus the D-18 bits-ui report** — `feat(51-06): extract Button and Input primitives, D-18 bits-ui report` — `ec7164f64`

**Plan metadata:** (this commit, made after this SUMMARY)

## Files Created/Modified

- `app/src/lib/primitives/Card.svelte` - generalized from StatCard's existing card pattern; optional title, optional children snippet
- `app/src/lib/primitives/Badge.svelte` - required `label` prop (type error if omitted); `tone` selects one of five admin lifecycle tokens or neutral
- `app/src/lib/primitives/Button.svelte` - variant/dense/loading, icon-only accessible-name enforced by a discriminated union prop type
- `app/src/lib/primitives/Input.svelte` - `invalid`/`descriptionId`/`role="alert"` contract copied from DocketPillInput, generalized to support both a caller-owned and a self-rendered error track
- `app/src/lib/admin/StatCard.svelte` - now delegates to `Card`, public prop shape unchanged
- `app/src/lib/admin/DocketPillInput.svelte` - free-text field now delegates to `Input`; dead `describedByIds` derivation removed
- `app/package.json`, `app/package-lock.json` - `@lucide/svelte@^1.35.0` added (one dependency, zero transitive)
- `.planning/phases/51-design-system-noun-alignment/51-DESIGN-DECISIONS.md` - D-18 substitution amendment + D-18 bits-ui report appended; MIT->ISC correction made in place
- `.planning/phases/51-design-system-noun-alignment/51-UI-SPEC.md` - MIT->ISC correction made in place, `@lucide/svelte` substitution noted

## Decisions Made

- **`@lucide/svelte` substituted for `lucide-svelte`** (operator-approved 2026-08-28): the package D-18 recorded is deprecated; its own npm listing says "Please use `@lucide/svelte` instead." Same maintainer, same repository, actively maintained, clean `svelte ^5` peer range vs. the deprecated package's `^5.0.0-next.42` prerelease range. Recorded in full in `51-DESIGN-DECISIONS.md`'s D-18 amendment section.
- **MIT->ISC license correction**: both `51-UI-SPEC.md` and the original D-18 section misstated the license as MIT; the actual license (both packages) is ISC. Corrected in place — a one-word factual fix, not a rewrite.
- **All four primitives hand-rolled, not `bits-ui`**: none opens a focus-managed overlay or roving-tabindex control. Recorded as the D-18 report.
- **`Button`'s accessible-name contract enforced by a discriminated union type** rather than a runtime assertion: `IconOnlyButtonProps` requires one of `label`/`ariaLabel`/`ariaLabelledby`; `TextButtonProps` requires visible `children`. Chose this over a runtime `console.warn`/throw because the plan explicitly asked for the omission to be "impossible to construct," which a type error satisfies more strongly than a runtime check that only fires when the component actually mounts.
- **`Input`'s error-rendering split** (`describedBy` for a caller-owned external alert vs. `errorMessage`/`errorId` for a self-rendered one) generalizes rather than literally replicates `DocketPillInput`'s two-track pattern, because `DocketPillInput` is a compound pill-list widget with an externally-owned validation state for one track and an internally-owned one for the other, while `Input` is a general-purpose standalone control that needs to support both call shapes depending on the caller. `DocketPillInput`'s own adoption of `Input` below exercises both tracks simultaneously, proving the generalization is behavior-preserving.
- **Both variant-color choices (primary/destructive = border+text in the semantic color, neutral = border+text in `--color-text-secondary`, all backgrounds transparent)** are a fresh design decision for this new primitive, not a literal copy of the codebase's several inconsistent existing ad hoc button styles (some use `background-color: var(--color-surface)` with `color: var(--color-text-primary)` even on an accent-bordered button; others use `background: transparent`). Chose the border+text-in-semantic-color, transparent-background shape because it most directly matches the plan's own literal spec ("primary: accent border and text") and stays visually consistent across all three variants.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical, surfaced via Task 1's own gate] Deprecated package substituted before install**
- **Found during:** Task 1 (package legitimacy gate)
- **Issue:** D-18 recorded `lucide-svelte`, which is deprecated in favor of the scoped `@lucide/svelte` successor
- **Fix:** Gathered evidence (deprecation notice, publish dates, download counts, repository match, peer-range staleness), presented to operator, installed `@lucide/svelte@^1.35.0` on approval
- **Files modified:** `app/package.json`, `app/package-lock.json`, `.planning/phases/51-design-system-noun-alignment/51-DESIGN-DECISIONS.md`
- **Verification:** `git diff app/package.json` shows exactly one dependency added; `npm view @lucide/svelte deprecated` returns nothing (not deprecated)
- **Committed in:** `0f075113e`

**2. [Rule 1 - Bug] MIT->ISC license misstatement corrected**
- **Found during:** Task 1, at the operator's direction after independent verification
- **Issue:** Both `51-UI-SPEC.md` and the original D-18 section stated the lucide package's license as MIT; it is actually ISC
- **Fix:** Corrected the word in place in both files, with an inline note pointing to the amendment section for the audit trail
- **Files modified:** `.planning/phases/51-design-system-noun-alignment/51-UI-SPEC.md`, `.planning/phases/51-design-system-noun-alignment/51-DESIGN-DECISIONS.md`
- **Verification:** `npm view @lucide/svelte license` / `npm view lucide-svelte license` both return `ISC`; lockfile entry confirms `"license": "ISC"`
- **Committed in:** `0f075113e`

**3. [Rule 3 - Blocking, acceptance-criteria literal grep] Comment wording adjusted to keep the "no lib/public or lib/admin import" grep honest**
- **Found during:** Task 2 and Task 3, running the plan's own acceptance-criteria grep
- **Issue:** The plan's acceptance criterion is `grep -c 'lib/public\|lib/admin' <primitive> == 0`. Explanatory comments inside the primitives that referenced "`$lib/public` or `$lib/admin`" in prose (documenting the surface-agnostic rule) tripped the same literal-substring grep, even though there was no actual import.
- **Fix:** Reworded the comments to describe the constraint without using the literal path substrings (e.g. "the public or admin component directories" instead of "`$lib/public`/`$lib/admin`").
- **Files modified:** `app/src/lib/primitives/Card.svelte`, `app/src/lib/primitives/Badge.svelte`, `app/src/lib/primitives/Input.svelte`
- **Verification:** `grep -c 'lib/public\|lib/admin' <file>` returns `0` for all four primitives after the reword
- **Committed in:** `5f9901310`, `ec7164f64`

---

**Total deviations:** 3 auto-fixed (1 Rule 2 missing-critical, 1 Rule 1 bug, 1 Rule 3 blocking)
**Impact on plan:** All three necessary for correctness of the decision record and the plan's own literal acceptance gate. No scope creep — the license correction was operator-directed and the comment reword touched only prose, not behavior.

## Issues Encountered

- `app/tests/case-required-recovery.browser.test.mjs` cannot run in this sandbox — confirmed by actually running it: it fails at its own fail-closed assertion ("Microsoft Edge or Google Chrome must be installed for this fail-closed test"), same environmental constraint every prior plan in this phase has hit. Separately, and independent of the browser constraint: reading the test's markup targets (`getElementById('docket_number')`) showed it exercises `admin/arguments/[id]/+page.svelte`'s own plain `Case docket number` field, not `DocketPillInput`'s free-text pill-entry field (`id="docket-input"`) that `Input` was adopted into — so even a working browser would not have exercised this plan's own `Input` adoption. This matches the plan's own contingency instruction ("say so in the summary and fall back to an operator visual check ... rather than claiming coverage that does not exist").
- Attempted to log the above as `WINDOWS.md` unrun-verify entries via `gsd-tools query windows.append` (three entries: the browser test itself, the admin dashboard visual check, the pipeline page docket field visual check). All three calls failed with a pre-existing ledger error unrelated to this plan: `Ledger counts disagree with entries: frontmatter open/waived/fixed/total=23/0/8/31 but entries yield 21/0/10/31`. This drift predates this plan (no prior commit in this session touched `WINDOWS.md`); per the ledger's documented best-effort contract, recording here in the SUMMARY substitutes for the ledger entry rather than blocking this plan on fixing an unrelated pre-existing count mismatch.
- No Chromium/Edge binary in this sandbox (same constraint as plans 51-02 through 51-05) — the admin dashboard's stat-card visual check after the `Card` delegation, and the pipeline page's docket field visual check after the `Input` adoption, are both unobserved and need an operator pass in a real browser.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `lib/primitives/` is populated with all four D-17 primitives, unblocking plan 51-08 (`TermRow.svelte` on `Card`) and plan 51-09 (admin status pills on `Badge`, plus the residual public-leak audit for `--color-status-*`).
- `@lucide/svelte` is installed and proven to import individually (tree-shaking preserved) via `LoaderCircle` and `X` in the typecheck probes this plan ran and reverted.
- **Open for a human:** three real-browser checks (the admin dashboard's stat cards, the pipeline page's docket field, and `case-required-recovery.browser.test.mjs` itself) were not observed this session — no Chromium/Edge binary available. `npm run check`/`npm run build` both green, and the full bare `pytest -q` suite (1378 passed, 5 xfailed, 0 failed — unchanged from the 51-05 baseline, as expected for a frontend-only plan) are the strongest available automated signals.
- WINDOWS.md has a pre-existing frontmatter/body count drift (`23/0/8/31` vs `21/0/10/31`) that blocked this plan's attempt to append its three unrun-verify entries there. Worth a look before the next plan in this phase tries to append to that ledger.

---
*Phase: 51-design-system-noun-alignment*
*Completed: 2026-08-28*

## Self-Check: PASSED

All key files confirmed on disk (`find` / `[ -f ]`): `app/src/lib/primitives/{Card,Badge,Button,Input}.svelte`, `app/src/lib/admin/{StatCard,DocketPillInput}.svelte`, this SUMMARY. All three task commit hashes (`0f075113e`, `5f9901310`, `ec7164f64`) confirmed present in `git log --oneline --all`. All four `51-DESIGN-DECISIONS.md` decisions (D-16, D-18, E4, D-19) re-confirmed present before this commit. `npm --prefix app run check` and `npm --prefix app run build` both green; bare `pytest -q` 1378 passed / 5 xfailed / 0 failed.
