---
phase: 53-undetermined-speakers-marker-normalisation
plan: 05
subsystem: admin-ui
tags: [svelte, sveltekit, admin, blocker-copy, node-test]

requires:
  - phase: 53-undetermined-speakers-marker-normalisation
    provides: "plan 53-01's majority_undetermined_speaker blocker code carrying {code, count, percent} on the publish-attempt 422 (both arguments pages) and on every review-queue row via summarize_tier_blockers"
provides:
  - "app/src/lib/admin/blockerSentence.js — the one blocker-code -> operator sentence function (all six branches, incl. the D-18 majority branch), unit-tested with node --test"
  - "TierBlocker JSDoc type, imported as a TS type by all three admin +page.server.ts files"
  - "the locked D-18 sentence rendering on all three admin surfaces that show blocker codes: admin/arguments/[id], admin/arguments, admin/review"
affects: []

actuals:
  tokens: 3854
  tasks: 2
  commits: 2
  plan_head_before: e357c7cb9a6cef3c49be589c395a3c9cf15129e3
  plan_head_after: cb6f8df9b87eca0fb991e0e9f3874ce52cb9896e

tech-stack:
  added: []
  patterns:
    - "One shared blockerSentence(blocker) module (following the resetOutcome.js + reset-outcome-classifier.test.mjs precedent) replacing three verbatim-duplicated per-page functions — extraction guarantees three admin surfaces can never drift, instead of relying on a comment saying they must be kept in sync by hand."

key-files:
  created:
    - app/src/lib/admin/blockerSentence.js
    - app/tests/blocker-sentence.test.mjs
  modified:
    - app/src/routes/admin/arguments/[id]/+page.svelte
    - app/src/routes/admin/arguments/[id]/+page.server.ts
    - app/src/routes/admin/arguments/+page.svelte
    - app/src/routes/admin/arguments/+page.server.ts
    - app/src/routes/admin/review/+page.svelte
    - app/src/routes/admin/review/+page.server.ts

key-decisions:
  - "The five pre-existing branches and the unknown-code fallback were moved into the shared module with output strings byte-identical to the three duplicates they replaced — verified by re-running every pre-existing case as a literal-string node:test assertion, not by inspection."
  - "The D-18 percent branch is checked ahead of the other majority_undetermined_speaker handling: when blocker.percent is not a finite number, the branch falls through to the generic unknown-code sentence rather than inventing copy (no `undefined%` can ever render)."
  - "An unused local `type Blocker` alias inside app/src/routes/admin/arguments/+page.svelte (never referenced anywhere in that file) was left untouched — out of this task's scope per the Defect Policy's scope boundary; only the type aliases actually driving the blocker-list typing (all three +page.server.ts files) were replaced with the shared TierBlocker import, per the plan's own instruction."

requirements-completed: [SPEAKER-05]

coverage:
  - id: D1
    description: "Every admin \"why blocked\" panel renders the majority blocker as exactly `{percent}% of turns have an undetermined speaker (more than half).`, from ONE shared function, on all three surfaces (admin/arguments/[id], admin/arguments, admin/review)"
    requirement: "SPEAKER-05"
    verification:
      - kind: unit
        ref: "app/tests/blocker-sentence.test.mjs (14 cases: majority-percent-68, majority-percent-50, majority-no-percent-fallback, and all five pre-existing branches singular+plural, no_constituents, unknown-code singular+plural)"
        status: pass
      - kind: other
        ref: "grep -rn 'function blockerSentence' app/src (exactly one line, in blockerSentence.js)"
        status: pass
      - kind: other
        ref: "grep -rln \"from '$lib/admin/blockerSentence.js'\" app/src/routes/admin (all six files: three +page.svelte, three +page.server.ts)"
        status: pass
      - kind: other
        ref: "grep -rn 'majority_undetermined_speaker|undetermined speaker (more than half)' app/src/routes/arguments app/src/lib/public (empty output — no public leak)"
        status: pass
      - kind: other
        ref: "npm --prefix app run check (svelte-check: 0 errors, 32 pre-existing unrelated warnings) and npm --prefix app run build (exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A held argument (fixture 15169's 33 sentinel turns, and a real >50%-undetermined conversation imported live) shows the correct blocked-panel sentence, the same sentence in /admin/review, and the existing typed-reason override still publishes it one at a time, non-sticky"
    requirement: "SPEAKER-05"
    verification: []
    human_judgment: true
    rationale: "Requires the dev stack running, a live database reset/import, and a real browser to confirm the panel text, the review-queue row, and the publish/unpublish round trip. No Playwright MCP or browser tool was available in this execution session — deferred to the operator's eye per project_notes; not claimed as verified here."
---

# Phase 53 Plan 5: Admin Blocker Copy Summary

**One shared, unit-tested `blockerSentence(blocker)` function replaces three verbatim-duplicated copies and adds the locked D-18 majority-undetermined sentence to all three admin surfaces that show blocker codes.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-29T13:05:00Z (approximate)
- **Completed:** 2026-09-29T13:25:00Z (approximate)
- **Tasks:** 2 completed
- **Files modified:** 8 (2 created, 6 modified)

## Accomplishments

- `app/src/lib/admin/blockerSentence.js`: one exported `blockerSentence(blocker: TierBlocker)` function, following the `resetOutcome.js` JSDoc-typed pure-module convention. Carries the five pre-existing blocker-code branches, the unknown-code fallback, and the new `majority_undetermined_speaker` branch that renders the locked D-18 template (`"{percent}% of turns have an undetermined speaker (more than half)."`) whenever `percent` is a finite number, falling back to the generic fallback otherwise.
- `app/tests/blocker-sentence.test.mjs`: 14 `node:test` cases, one per `<behavior>` line in the plan, asserting literal expected strings.
- All three admin surfaces — `admin/arguments/[id]/+page.svelte`, `admin/arguments/+page.svelte`, `admin/review/+page.svelte` — now import and call the shared function, passing the whole blocker object (`blockerSentence(b)` / `blockerSentence(blocker)`) instead of `blockerSentence(code, count)`. All three `+page.server.ts` files import the shared `TierBlocker` JSDoc type (via `allowJs`/`checkJs`) instead of declaring their own local `Blocker`/`TierBlocker` alias.
- Confirmed no public leak: `grep -rn "majority_undetermined_speaker|undetermined speaker (more than half)" app/src/routes/arguments app/src/lib/public` returns nothing.

## Task Commits

1. **Task 1: A blocked publish on the argument detail page states the undetermined share** - `3333d7026` (feat) — tracer task, verified end-to-end (node --test + svelte-check both green) before expanding to Task 2, per the tracer feedback gate.
2. **Task 2: The arguments list and the review queue say the same sentence from the same function** - `cb6f8df9b` (feat)

**Plan metadata:** committed alongside this SUMMARY (see below)

_Both tasks carry `tdd="true"`, but `workflow.tdd_mode` is `false` in this project's `.planning/config.json` (same precedent as plans 53-01/53-02), so the formal RED→GREEN→REFACTOR gate is not enforced this phase. Tests were authored directly from the plan's `<behavior>` list alongside the implementation and verified passing before each commit._

## Files Created/Modified

- `app/src/lib/admin/blockerSentence.js` - the one blocker-code -> sentence function, incl. the D-18 majority branch and the `TierBlocker` JSDoc type
- `app/tests/blocker-sentence.test.mjs` - 14 `node:test` cases covering every branch
- `app/src/routes/admin/arguments/[id]/+page.svelte` - local helper deleted, imports and calls the shared function
- `app/src/routes/admin/arguments/[id]/+page.server.ts` - local `Blocker` type replaced by the shared `TierBlocker` import
- `app/src/routes/admin/arguments/+page.svelte` - local helper deleted, imports and calls the shared function
- `app/src/routes/admin/arguments/+page.server.ts` - local `Blocker` type replaced by the shared `TierBlocker` import
- `app/src/routes/admin/review/+page.svelte` - local helper deleted, imports and calls the shared function
- `app/src/routes/admin/review/+page.server.ts` - local `TierBlocker` type replaced by the shared import

## Decisions Made

- Extraction (not three parallel edits) was already Claude's discretion per the plan's own `<objective>` — implemented exactly as directed, verified the three prior copies really did hash identically before replacing them.
- Left an unused local `type Blocker` alias in `admin/arguments/+page.svelte` untouched (never referenced in that file) — out of scope per the Defect Policy's scope boundary; the plan's own instruction only named the `+page.server.ts` type aliases for replacement.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. `svelte-check` reports 0 errors; the 32 warnings present both before and after this plan's changes are pre-existing, unrelated `state_referenced_locally` / a11y warnings in other files (confirmed via `git show HEAD` on the pre-change file content), out of this plan's scope.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All SPEAKER-01…08 requirements now have their frontend/backend halves in place across plans 53-01 through 53-05.
- **Human-check outstanding** (Task 2's `<human-check>`): requires the dev stack running, a live Reset-to-Fixture and a live `import-convokit` run, and visual confirmation in a real browser of the blocked-panel sentence, the review-queue row, and the publish/unpublish round trip. No browser tool was available in this execution session — this is harvested into the phase UAT batch per the plan's own `<verification>` note, not silently skipped.
- No blockers for phase completion pending that human-check.

## Self-Check: PASSED

- `app/src/lib/admin/blockerSentence.js` (`blockerSentence`, `TierBlocker`) — FOUND
- `app/tests/blocker-sentence.test.mjs` — FOUND
- Commit `3333d7026` — FOUND in `git log --oneline --all`
- Commit `cb6f8df9b` — FOUND in `git log --oneline --all`
- All plan-level `<verification>` commands re-run and passing: `node --test app/tests/blocker-sentence.test.mjs` → 14 pass, 0 fail; `npm --prefix app run check` → 0 errors; `npm --prefix app run build` → exit 0

---
*Phase: 53-undetermined-speakers-marker-normalisation*
*Completed: 2026-09-29*
