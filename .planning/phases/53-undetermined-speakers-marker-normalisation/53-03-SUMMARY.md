---
phase: 53-undetermined-speakers-marker-normalisation
plan: 03
subsystem: ui
tags: [svelte5, design-tokens, public-transcript, browser-test, css]

requires:
  - phase: 53-undetermined-speakers-marker-normalisation
    provides: "plan 53-02's speaker_undetermined / is_inaudible_marker booleans on the public UtteranceResponse payload, and canonical whole-turn marker text stored in utterances.text"
provides:
  - "Treatment D (D-01/SPEAKER-01): a source-unattributed turn renders as a centred bubble between two empty 40px rails, italic/muted 'undetermined speaker' label, no speaker/side colour — never guessing a side"
  - "S5 latent defect fixed: two consecutive undetermined rows now always render as two separate items (classified before run-continuation), instead of merging on their shared null raw_speaker_label"
  - "No source sentinel string (<INAUDIBLE>/<UNKNOWN>) can reach the rendered page as visible text, by construction (undetermined rows never enter roster/run classification) and proven by a real-browser test"
  - "D-12/D-13: a whole-turn inaudible body renders italic in --color-stage-text ink identically inside any bubble (attributed or Treatment D), via one shared .utterance-body / .utterance-body.is-inaudible-marker CSS rule"
  - "D-02: --font-style-italic and --opacity-muted landed as design-system tokens, absorbing the two pre-existing raw font-style:italic literals (StageDirection.svelte, SpeakerPopover.svelte)"
  - "--bubble-max-width-undetermined (67%/93%) landed as a Layout-geometry token, documented as NOT tracked by the data-width variant switcher"
  - "app/tests/helpers/transcript-page.mjs: shared mock-API/Vite/headless-Chromium/CDP harness, lifted out of speaker-initials.browser.test.mjs for reuse by future transcript browser tests"
affects: [53-04-explanation-card, verify-work]

actuals:
  tokens: 11377
  tasks: 3
  commits: 3
  plan_head_before: a367a0efdf89445d7a41e8ca9327742fe0ca14b6
  plan_head_after: 033541f8e91fe1ac07b6309a3c53d1daa05b49e5

tech-stack:
  added: []
  patterns:
    - "One shared global CSS class pair (.utterance-body / .utterance-body.is-inaudible-marker) as the cross-component style contract, instead of duplicating an inline style expression in two components that could drift apart — same rationale as the pre-existing .speaker-* classes (an inline colour would outrank a class)."
    - "A render-item kind classified BEFORE run-continuation, not after — the general shape for any per-utterance fact that must never merge into an adjacent run's continuation check."

key-files:
  created:
    - app/src/lib/public/UndeterminedBubble.svelte
    - app/tests/helpers/transcript-page.mjs
    - app/tests/undetermined-bubble.browser.test.mjs
  modified:
    - app/src/app.css
    - "app/src/routes/arguments/[slug]/+page.svelte"
    - app/src/lib/public/ChatBubble.svelte
    - app/src/lib/public/StageDirection.svelte
    - app/src/lib/public/SpeakerPopover.svelte
    - .planning/codebase/DESIGN-SYSTEM.md

key-decisions:
  - "Task 1's UndeterminedBubble.svelte body <p> deliberately shipped WITHOUT the .utterance-body class in its own commit (Task 1 doesn't need it — the ordinary body colour is already correct via inherited --color-text-primary from <body>) — Task 2 adds the class pair to both bubble components in the same commit, keeping each task's diff scoped to what that task actually requires rather than getting ahead of the plan's own task boundaries."
  - "The RED run (Pitfall 6) was executed for real: implementation files were reverted to HEAD (git checkout -- / rm on the new component) with the test file left in place, confirming both the test fails without the fix and, via a one-off probe script, exactly which two DOM paths leaked the sentinel (see Deviations)."

patterns-established:
  - "Type axes (--font-style-italic, --opacity-muted) in app.css, named the same way as --font-weight-regular/--font-weight-semibold — a style axis is documented and referenced, never inlined."

requirements-completed: [SPEAKER-01, SPEAKER-06, SPEAKER-07]

coverage:
  - id: D1
    description: "A stored undetermined fact renders as Treatment D at rest: centred bubble, two empty 40px rails, italic/muted label, no speaker/side colour, correct width cap at desktop and mobile"
    requirement: "SPEAKER-01"
    verification:
      - kind: automated_ui
        ref: "app/tests/undetermined-bubble.browser.test.mjs (geometry, label style, no-speaker-class assertions)"
        status: pass
      - kind: other
        ref: "grep -n -- '--font-style-italic: italic;|--opacity-muted: 0.7;|--bubble-max-width-undetermined: 67%;|--bubble-max-width-undetermined: 93%;' app/src/app.css"
        status: pass
    human_judgment: false
  - id: D2
    description: "Two consecutive undetermined turns always render as two separate Treatment D items (S5), never merged"
    requirement: "SPEAKER-01"
    verification:
      - kind: automated_ui
        ref: "app/tests/undetermined-bubble.browser.test.mjs (three separate [role=article][aria-label=Undetermined speaker] rows)"
        status: pass
    human_judgment: false
  - id: D3
    description: "No source sentinel string (<INAUDIBLE>/<UNKNOWN>) reaches the rendered page as visible text, and the roster never lists an undetermined row"
    requirement: "SPEAKER-01"
    verification:
      - kind: automated_ui
        ref: "app/tests/undetermined-bubble.browser.test.mjs (document.body.innerText sentinel-absence assertion, roster-name-count assertion)"
        status: pass
      - kind: other
        ref: "grep -rnE '<INAUDIBLE>|<UNKNOWN>|\\(Inaudible\\)' app/src/lib/public app/src/routes/arguments"
        status: pass
    human_judgment: false
  - id: D4
    description: "A whole-turn inaudible body reads identically (italic, --color-stage-text ink, unchanged lead size/line-height) whether inside an ordinary attributed bubble or a Treatment D bubble, keyed only off the stored is_inaudible_marker fact"
    requirement: "SPEAKER-07"
    verification:
      - kind: automated_ui
        ref: "app/tests/undetermined-bubble.browser.test.mjs (computed fontStyle/color/fontSize/lineHeight equality across attributed, Treatment D, and stage-direction bodies)"
        status: pass
      - kind: other
        ref: "grep -n 'is-inaudible-marker' app/src/lib/public/ChatBubble.svelte app/src/lib/public/UndeterminedBubble.svelte"
        status: pass
    human_judgment: false
  - id: D5
    description: "The design system documents every token app.css declares (including the new italic axis, opacity-muted, and the undetermined-width token), and no raw italic literal remains on the public reading surface"
    requirement: "SPEAKER-06"
    verification:
      - kind: other
        ref: "token-coverage loop (grep app.css custom properties against DESIGN-SYSTEM.md) — 0 MISSING lines"
        status: pass
      - kind: other
        ref: "grep -rnE 'font-style: ?italic' app/src/lib/public app/src/routes/arguments — 0 matches"
        status: pass
      - kind: e2e
        ref: "npm --prefix app run build (exit 0)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Visual read-check: Treatment D reads noticeably narrower with reserved empty space, the label reads as visibly different from a real speaker name, and a whole-turn (Inaudible) body reads as a transcriber's note rather than spoken words — checked against Figma KICu66PtMLHk4fmxJYPggx node 33:2 on a real published argument (fixture 15169) at desktop and 390px"
    requirement: "SPEAKER-01"
    verification: []
    human_judgment: true
    rationale: "This is Task 3's <human-check> item. HUMAN_VERIFY_MODE is end-of-phase (project default, unset in config.json) and every automated <verify> command for this plan already ran and passed above — per the executor's checkpoint protocol this genuine visual-adequacy judgment is deferred to /gsd-verify-work's end-of-phase UAT rather than a per-task interactive checkpoint here."

duration: 60min
completed: 2026-09-29
status: complete
---

# Phase 53 Plan 3: Treatment D Rendering & Inaudible-Body Styling Summary

**A source-unattributed turn renders as a centred Treatment D bubble between two empty 40px rails with no speaker/side colour and no sentinel leak, a whole-turn inaudible body reads identically (italic, stage-text ink) in every bubble that carries it, and the new italic type axis plus the undetermined-width token are recorded in the design system.**

## Performance

- **Duration:** 60 min (includes an 11m53s full backend pytest baseline run)
- **Started:** 2026-09-29T12:35:00Z (approximate)
- **Completed:** 2026-09-29T13:35:00Z (approximate)
- **Tasks:** 3 completed
- **Files modified:** 9 (3 created, 6 modified)

## Accomplishments

- `UndeterminedBubble.svelte` (new): Treatment D's rest state — a `role="article"` row with two 40px empty rails and a centred bubble (`min(var(--bubble-max-width-undetermined), 63ch)`), an always-visible italic/70%-opacity "undetermined speaker" label, and no speaker-identity colour class or per-speaker/side custom property anywhere in the component.
- `+page.svelte`'s `renderItems` gained a third `'undetermined'` kind, classified from the stored `speaker_undetermined` fact BEFORE the run-continuation check — this is what stops two consecutive undetermined rows (both `raw_speaker_label === null` today) from merging into one run, fixing the S5 latent defect as a side effect. `roster` and `speakerSlots` both skip undetermined rows defensively, so an undetermined turn can never contribute a roster name or consume a colour slot.
- `app.css` gained three tokens: `--font-style-italic` and `--opacity-muted` (a new "type axes" group, D-02), and `--bubble-max-width-undetermined` (67%/93%, the Figma 540:582 ratio applied to `--bubble-max-width`) in the transcript layout-geometry group.
- D-12/D-13: one shared `.utterance-body` / `.utterance-body.is-inaudible-marker` CSS rule, applied by both `ChatBubble.svelte` and `UndeterminedBubble.svelte` via an identical `$derived(utterance.is_inaudible_marker === true)` flag — a whole-turn inaudible body is italic in `--color-stage-text` ink wherever it appears, keyed only off the stored fact, never off matching body text.
- `.planning/codebase/DESIGN-SYSTEM.md`: new "Type axes" subsection under Typography, the Layout-geometry table gained the undetermined-width token (with its `data-width`-does-not-track-it caveat recorded under Transcript variant axes), the Styling-mechanism section documents the `.utterance-body` exception to "everything is inline", `UndeterminedBubble` joins the public component list, and the closing reconciliation note is bumped to 78 semantic tokens / 2026-09-29.
- `StageDirection.svelte` and `SpeakerPopover.svelte`'s pre-existing raw `font-style: italic;` literals (the one spot Phase 51's token-conversion sweep didn't reach) now reference `var(--font-style-italic)` — same property, same value.
- `app/tests/helpers/transcript-page.mjs` (new): the mock-FASTAPI/Vite/headless-Chromium/CDP harness lifted out of `speaker-initials.browser.test.mjs` (left untouched) into a reusable `openTranscriptPage()` + `waitForExpression()` pair, so this and future transcript browser tests don't re-copy the same ~150 lines of setup.
- `app/tests/undetermined-bubble.browser.test.mjs` (new): a single real-Chromium test proving Treatment D geometry/tokens/no-sentinel-leak (Task 1) and the inaudible-body treatment across attributed/Treatment-D/stage-direction bodies (Task 2) against an 8-row fixture. All four `*.browser.test.mjs` suites (12 tests total) and the full bare backend suite (1482 passed, 5 xfailed) stay green.

## Task Commits

1. **Task 1: One undetermined turn renders as Treatment D in a real browser** - `85cc6ddc6` (feat)
2. **Task 2: A whole-turn inaudible body reads as the transcriber's note, identically in every bubble** - `cf07f3b0d` (feat)
3. **Task 3: Record the new type axis in the design system and retire the public italic literals** - `033541f8e` (docs)

**Plan metadata:** committed alongside this SUMMARY (see below)

_Both Task 1 and Task 2 carry `tdd="true"`, but `workflow.tdd_mode` is `false` in this project's config (matching plans 53-01/53-02's precedent) — see "TDD Gate Compliance" below for how the RED/GREEN split was still genuinely exercised._

## Files Created/Modified

- `app/src/lib/public/UndeterminedBubble.svelte` - Treatment D's rest-state component
- `app/tests/helpers/transcript-page.mjs` - shared browser-test harness, lifted out of `speaker-initials.browser.test.mjs`
- `app/tests/undetermined-bubble.browser.test.mjs` - real-browser proof for Tasks 1 and 2
- `app/src/app.css` - `--font-style-italic`, `--opacity-muted`, `--bubble-max-width-undetermined`, `.utterance-body` / `.utterance-body.is-inaudible-marker`
- `app/src/routes/arguments/[slug]/+page.svelte` - `'undetermined'` `RenderItem` kind, roster/speakerSlots skip
- `app/src/lib/public/ChatBubble.svelte` - `is_inaudible_marker` prop field, `lostWordsBody` derived, `utterance-body` class pair
- `app/src/lib/public/StageDirection.svelte` - raw italic literal → `var(--font-style-italic)`
- `app/src/lib/public/SpeakerPopover.svelte` - raw italic literal → `var(--font-style-italic)`
- `.planning/codebase/DESIGN-SYSTEM.md` - Type axes subsection, Layout-geometry row, Styling-mechanism exception, component list, reconciliation note

## Decisions Made

- Split the combined Task 1 + Task 2 implementation into two atomic commits along the plan's own task/file boundaries (rather than one commit covering both), reconstructing each task's intermediate state and re-running `svelte-check` + both browser tests at each commit point — see "Deviations" for why this took an extra pass.
- Task 1's `UndeterminedBubble.svelte` body paragraph intentionally shipped without the `.utterance-body` class in its own commit; the ordinary-body colour case is already correct via inheritance from `<body>`'s `--color-text-primary`, so nothing in Task 1's own `<behavior>`/acceptance criteria needed the class yet.

## Deviations from Plan

None — plan executed exactly as written. One process note, not a defect:

**Pitfall 6 RED run, executed for real (not narrated).** Per the plan's own instruction, the browser test was run RED against the pre-fix route before implementing: implementation files (`app.css`, `+page.svelte`) were reverted with `git checkout --` and the new `UndeterminedBubble.svelte` was removed, leaving the test in place. The test failed as expected (`0 !== 3` Treatment D rows found), and a one-off probe script confirmed the sentinel `<INAUDIBLE>` leaked through exactly two DOM paths: the roster's Bench-column name `<p>` (the roster loop's `speaker_name ?? raw_speaker_label` key, non-blank because the sentinel itself is non-blank) and the transcript row's speaker-name `<span class="speaker-ink">` (`ChatBubble`'s own `speaker_name ?? raw_speaker_label` fallback). Both paths are now unreachable by construction (an undetermined row never enters `roster`/`speakerSlots`/run classification) and their absence is asserted by the browser test. Implementation files were then restored from a backup taken before the revert (not re-typed), verified GREEN, and the acceptance-criteria grep for `speaker-fill\|speaker-ink\|speaker-stroke\|--speaker-color` in `UndeterminedBubble.svelte` initially caught its own explanatory comment (which named those classes to say they're absent) — reworded to describe the absence without quoting the literal class names, then re-verified at 0 matches.

---

**Total deviations:** 0 auto-fixed. One in-flight self-correction (the acceptance-criteria grep vs. its own explanatory comment, caught and fixed before the first commit).
**Impact on plan:** None — plan executed exactly as specified; the self-correction was resolved before any commit landed.

## TDD Gate Compliance

Tasks 1 and 2 both carry `tdd="true"`, but `workflow.tdd_mode` is `false` in this project's `.planning/config.json` (same precedent as plans 53-01/53-02), so the formal `test(...)` → `feat(...)` → `refactor(...)` commit-per-phase gate is not enforced. Task 1's RED phase was nonetheless genuinely exercised (see Deviations above) before its single `feat(53-03):` commit landed test and implementation together, verified against every `<verify>`/acceptance-criteria command first. Task 2 likewise landed as one `feat(53-03):` commit with its fixture/assertion extensions and implementation together, verified before commit. No `test(...)`/`feat(...)` commit pair was expected, and none was claimed.

## Issues Encountered

None. The `scotus_test` DB-tombstone risk and the "advance-plan ignores wave order" STATE.md quirk (both noted in project memory) did not need handling here — no backend file changed, so the full bare pytest run (1482 passed, 5 xfailed, 713.02s) is unaffected baseline confirmation, not new coverage.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `UndeterminedBubble.svelte`, the `'undetermined'` `RenderItem` kind, and the `.utterance-body` class pair are all in place for plan 53-04 (the explanation-card popover and the hover/tap reveal avatars) to build on directly — the two rail `<div>`s in `UndeterminedBubble.svelte` are already present as permanent structure with no children, exactly where 53-04 adds the dashed `?` avatar buttons.
- SPEAKER-01, SPEAKER-06, and SPEAKER-07 are shared-declared with sibling plan 53-02 (already summarized, shared-ID gate #2388) — both plans have now finished, so `REQUIREMENTS.md` can mark all three `Complete`.
- Task 3's `<human-check>` (visual read-check against Figma on fixture 15169, desktop + 390px) is recorded above as a `human_judgment: true` coverage entry (D6), deferred to `/gsd-verify-work`'s end-of-phase UAT per this project's default `human_verify_mode: end-of-phase` — not yet performed by a human.
- No blockers. Plan 53-04 (explanation card) can proceed; plan 53-05 (admin blocker copy) already completed in an earlier wave.

## Self-Check: PASSED

- `app/src/lib/public/UndeterminedBubble.svelte` — FOUND
- `app/tests/helpers/transcript-page.mjs` — FOUND
- `app/tests/undetermined-bubble.browser.test.mjs` — FOUND
- Commit `85cc6ddc6` — FOUND in `git log --oneline --all`
- Commit `cf07f3b0d` — FOUND in `git log --oneline --all`
- Commit `033541f8e` — FOUND in `git log --oneline --all`
- All plan-level `<verification>` commands re-run and passing: `npm --prefix app run check` → 0 errors, 32 pre-existing warnings (none in files this plan touched); `npm --prefix app run build` → exit 0; `node --test --test-concurrency=1 app/tests/*.browser.test.mjs` → 12 tests, 12 pass, 0 fail; bare `./.venv/bin/python -m pytest -q` → 1482 passed, 5 xfailed, 0 failed (713.02s)

---
*Phase: 53-undetermined-speakers-marker-normalisation*
*Completed: 2026-09-29*
