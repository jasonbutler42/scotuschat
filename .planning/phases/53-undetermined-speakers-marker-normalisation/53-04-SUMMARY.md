---
phase: 53-undetermined-speakers-marker-normalisation
plan: 04
subsystem: ui
tags: [svelte5, popover, browser-test, css, cdp, bits-ui]

requires:
  - phase: 53-undetermined-speakers-marker-normalisation
    provides: "plan 53-03's UndeterminedBubble.svelte rest state (two empty rail divs, .utterance-body class pair), and the route's existing SpeakerPopover / shared Popover.Root mechanism"
provides:
  - "D-14/SPEAKER-02: an explanation card (UndeterminedSpeakerCard.svelte) reached from either dashed '?' avatar of a Treatment D bubble, rendered inside the page's single shared Popover.Root beside the existing speaker-bio card, never a second popover instance"
  - "D-01/D-16: both avatars reveal together (never one alone) on hover, keyboard focus, or a first touch tap — one row-level CSS rule set targets both rails, making a one-sided reveal structurally impossible"
  - "D-16: the bubble body itself is inert (no handler); Escape/outside-click dismiss the card exactly like the bio card"
  - "D-15: the card's first paragraph swaps to the lost-words sentence when the activated turn's stored is_inaudible_marker fact is true, via a $derived that is re-evaluated as the reader moves between turns"
  - "D-07/PLUMBING-07: UndeterminedBubble.svelte, UndeterminedSpeakerCard.svelte, ChatBubble.svelte, StageDirection.svelte and SpeakerPopover.svelte are registered in PUBLIC_FRONTEND_PATHS, with a new all-paths-exist guard and a case-insensitive trust-vocabulary sweep"
  - "openTranscriptPage({ realPointer: true }): a shared test-harness addition that launches a real (non-headless) Chromium window, because this Chromium build's headless mode always reports (hover: hover)/(pointer: fine) as false regardless of launch flags"
affects: [verify-work, any future browser test needing real hover/pointer media-query behavior]

actuals:
  tokens: 13776
  tasks: 2
  commits: 2
  plan_head_before: c96a28fe924bd6e1f1189c009a60c1f220cf61d2
  plan_head_after: 7a97e70e473a7b0819032a0eb610cfe34aa68954

tech-stack:
  added: []
  patterns:
    - "Component-scoped <style> block as the codebase's one exception to inline styling (UndeterminedBubble.svelte) — hover/focus-within/media-query/touch-attribute reveal rules cannot be expressed as inline style=\"...\" attributes."
    - "A single row-level reveal rule set (hover, :focus-within, [data-revealed='true']) targeting both sibling avatars together, so 'never reveal one side alone' is a structural property of the CSS, not a behavioral promise each trigger has to keep independently."
    - "openTranscriptPage's realPointer option: an opt-in, backward-compatible harness parameter for tests that need genuine (hover: hover)/(pointer: fine) media-query behavior, rather than changing the shared harness's default headless launch for every caller."

key-files:
  created:
    - app/src/lib/public/UndeterminedSpeakerCard.svelte
    - app/tests/undetermined-speaker-card.browser.test.mjs
  modified:
    - app/src/lib/public/UndeterminedBubble.svelte
    - "app/src/routes/arguments/[slug]/+page.svelte"
    - app/tests/helpers/transcript-page.mjs
    - api/tests/test_trust_public_leak_ban.py
    - .planning/codebase/DESIGN-SYSTEM.md

key-decisions:
  - "openTranscriptPage gained an opt-in realPointer option rather than changing the shared harness's default launch mode — measured that this Chromium build's headless mode (new or old, with or without --ozone-platform=x11) always reports hover:none/pointer:coarse with no CDP override, so a hover test genuinely needs a real window; every other existing browser test stays headless and unaffected."
  - "The touch test tries Input.synthesizeTapGesture first (delivers real pointerdown/pointerup with pointerType 'touch', so the reveal works) and falls back to Emulation.setTouchEmulationEnabled + Input.dispatchTouchEvent only if the card never opens — measured that synthesizeTapGesture never synthesizes the browser's compatibility click event a real touchscreen tap produces, so avatar activation (onclick) never fires through it alone on this Chromium build."
  - "Enter-key button activation in CDP requires the sequence rawKeyDown -> char (text/unmodifiedText '\\r', windowsVirtualKeyCode 13) -> keyUp on this Chromium build — a plain keyDown+keyUp pair reaches the page's own keydown/keyup listeners but never triggers the browser's native 'Enter activates a focused button' default action. Fixed in the test's CDP dispatch, not the component."
  - "UndeterminedSpeakerCard's inaudibleBody prop and $derived paragraph1 were introduced in Task 2 only — Task 1 shipped the card with a plain PARAGRAPH_1_ORDINARY reference, per the plan's own task boundary, so Task 2's diff is the D-15 swap and nothing else."

patterns-established:
  - "A component's own onpointerup/onclick handlers rely on Svelte 5's delegated-event mount, which measurably takes ~1.8s to attach on this host after the SSR-rendered markup is first visible — any browser test dispatching input events (click, tap, or otherwise) immediately after a role/DOM-count check must retry, not assume hydration is already complete."

requirements-completed: [SPEAKER-02, SPEAKER-01]

coverage:
  - id: D1
    description: "At rest both dashed '?' avatars are invisible (opacity 0) but present as focusable, aria-labelled buttons in the DOM/tab order; hovering the Treatment D row reveals both together (never one alone), and moving the mouse away returns both to invisible"
    requirement: "SPEAKER-02"
    verification:
      - kind: automated_ui
        ref: "app/tests/undetermined-speaker-card.browser.test.mjs (rest-state, hover-reveal, and other-row-unaffected assertions)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Clicking either avatar opens the explanation card (title + three fixed D-14 paragraphs) inside the page's single shared Popover.Root, anchored nearer the activated side; Escape dismisses; the bubble body itself opens nothing; the popover switches cleanly between the explanation card and the ordinary speaker-bio card in either direction"
    requirement: "SPEAKER-02"
    verification:
      - kind: automated_ui
        ref: "app/tests/undetermined-speaker-card.browser.test.mjs (activation/anchoring, Escape, bubble-body-inert, and popover-mode-switching assertions)"
        status: pass
      - kind: other
        ref: "grep -c 'Popover.Root' 'app/src/routes/arguments/[slug]/+page.svelte' == 3 (unchanged from before this plan — still one instance)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Focusing either avatar via keyboard reveals both together (:focus-within, outside the hover media query); Enter on the focused avatar opens the card"
    requirement: "SPEAKER-02"
    verification:
      - kind: automated_ui
        ref: "app/tests/undetermined-speaker-card.browser.test.mjs (keyboard focus + Enter assertions)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The explanation card's first paragraph swaps to the D-15 lost-words sentence when the activated turn's stored is_inaudible_marker fact is true, and reverts to the ordinary sentence when a different (non-marker) turn's avatar is activated next — keyed off the stored fact only"
    requirement: "SPEAKER-02"
    verification:
      - kind: automated_ui
        ref: "app/tests/undetermined-speaker-card.browser.test.mjs (D-15 swap assertions across two undetermined rows)"
        status: pass
    human_judgment: false
  - id: D5
    description: "On a touch pointer, a first tap anywhere on the row reveals both avatars and opens nothing (and does not reveal a different bubble's avatars); a second, separate tap on either avatar opens the card"
    requirement: "SPEAKER-02"
    verification:
      - kind: automated_ui
        ref: "app/tests/undetermined-speaker-card.browser.test.mjs ('touch: a first tap reveals both avatars...' test, its own page)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The five public components this phase touched are registered in the leak-ban's PUBLIC_FRONTEND_PATHS, every registered path exists, and no registered public file contains trust_tier, review_state or provisional"
    requirement: "SPEAKER-01"
    verification:
      - kind: unit
        ref: "api/tests/test_trust_public_leak_ban.py::test_public_frontend_paths_all_exist"
        status: pass
      - kind: unit
        ref: "api/tests/test_trust_public_leak_ban.py::test_public_frontend_pages_never_reference_trust_vocabulary"
        status: pass
      - kind: other
        ref: "grep -c 'UndeterminedBubble.svelte\\|UndeterminedSpeakerCard.svelte' api/tests/test_trust_public_leak_ban.py == 5"
        status: pass
    human_judgment: false
  - id: D7
    description: "Visual read-check: the card matches Figma node 33:62 (divider placement between title and paragraphs), the rest/hover/tap states match the approved mockup on both desktop and a real phone/touch device, and a whole-turn (Inaudible) turn's card reads the D-15 sentence — checked against fixture 15169 (after 53-05's own human-check) on a real device"
    requirement: "SPEAKER-02"
    verification: []
    human_judgment: true
    rationale: "This is Task 2's <human-check> item. HUMAN_VERIFY_MODE is end-of-phase (project default) and every automated <verify> command for this plan already ran and passed — per the executor's checkpoint protocol this genuine visual/device-fidelity judgment is deferred to /gsd-verify-work's end-of-phase UAT rather than a per-task interactive checkpoint here, matching 53-03's own D6 precedent."

duration: 95min
completed: 2026-09-29
status: complete
---

# Phase 53 Plan 4: Undetermined-Speaker Explanation Card & Interaction Summary

**Hover, keyboard focus and touch all reveal Treatment D's two dashed avatars together (never one alone), and either opens a D-14/D-15 explanation card inside the route's single shared Popover.Root — with the touch/keyboard CDP dispatch quirks this Chromium build required, measured and fixed in the tests rather than assumed.**

## Performance

- **Duration:** 95 min (includes a ~15 min full backend pytest baseline run)
- **Started:** 2026-09-29T13:36:00Z (approximate)
- **Completed:** 2026-09-29T15:04:00Z (approximate)
- **Tasks:** 2 completed
- **Files modified:** 7 (2 created, 5 modified)

## Accomplishments

- `UndeterminedBubble.svelte` gained an `onAvatarActivate(anchor, inaudibleBody)` prop and one `<button class="undetermined-avatar">` per rail (a dashed 32px "?" circle, neutral tokens only, no speaker/side colour), revealed together by a component-scoped `<style>` block's row-level rule set: `@media (hover: hover) .undetermined-row:hover`, `.undetermined-row:focus-within`, and `.undetermined-row[data-revealed='true']` — one shared selector family per trigger, so a one-sided reveal is structurally impossible rather than merely avoided by care.
- `UndeterminedSpeakerCard.svelte` (new): title + three fixed D-14 paragraphs in the `.popover-card` shape (`--space-xl` padding, per-paragraph section dividers), with an `inaudibleBody?: boolean` prop whose `$derived` paragraph1 swaps in the D-15 lost-words sentence — never a `const`, since the route reuses one card instance as the reader moves between turns.
- `+page.svelte` gained `popoverMode: 'speaker' | 'undetermined'` and `onUndeterminedAvatarClick(anchor, inaudibleBody)`, wiring both avatar buttons into the page's existing single `Popover.Root` beside the unchanged `SpeakerPopover` branch — no second popover instance (`Popover.Root` grep count unchanged at 3).
- `UndeterminedBubble.svelte` also gained per-instance `revealed` state (reset by an `$effect` keyed on `utterance.id`, mirroring `SpeakerPopover`'s `showInitials` reset) and an `onpointerup` handler that sets it on `event.pointerType === 'touch'`, rendered as `data-revealed` — the touch reveal mechanism, independent of hover/focus.
- `api/tests/test_trust_public_leak_ban.py` (D-07/PLUMBING-07): registered the five public components this phase's plans added or touched (`UndeterminedBubble.svelte`, `UndeterminedSpeakerCard.svelte`, `ChatBubble.svelte`, `StageDirection.svelte`, `SpeakerPopover.svelte`) in `PUBLIC_FRONTEND_PATHS` — previously that list only tracked route/page files plus `TermRow.svelte`. Added `test_public_frontend_paths_all_exist` (closes a real vacuous-pass gap: the two pre-existing path sweeps both `continue` silently past a missing path) and `test_public_frontend_pages_never_reference_trust_vocabulary` (a case-insensitive structural sweep for `trust_tier`/`review_state`/`provisional` — the Testing Policy's one permitted static-source-text exception).
- `app/tests/undetermined-speaker-card.browser.test.mjs` (new): a real-Chromium test proving hover/click/keyboard/D-15 behavior (one `test()`, real windowed browser via the new `realPointer: true` harness option) plus a second, separately-paged `test()` for the two-stage touch reveal-then-activate — 2 tests, both green, alongside the pre-existing 12.
- `app/tests/helpers/transcript-page.mjs` gained an opt-in `realPointer` option to `openTranscriptPage()`: measured that this Chromium build's headless mode (new or old, with or without `--ozone-platform=x11`) always reports `(hover: hover)`/`(pointer: fine)` as `false` with no CDP override existing to change that, so a genuine hover test needs a real window against `$DISPLAY`. Default `false` — every pre-existing caller (4 other browser test files) is unaffected.

## Task Commits

1. **Task 1: Hover an undetermined bubble, both dashed avatars appear, and either opens the explanation card** - `fce91862c` (feat)
2. **Task 2: Keyboard, touch and a lost-words turn each reach the right card; the new public files join the leak ban** - `7a97e70e4` (feat)

**Plan metadata:** committed alongside this SUMMARY (see below)

_Both tasks carry `tdd="true"`, but `workflow.tdd_mode` is `false` in this project's config (matching 53-01/53-02/53-03's precedent) — see "TDD Gate Compliance" below._

## Files Created/Modified

- `app/src/lib/public/UndeterminedSpeakerCard.svelte` - the D-14/D-15 explanation card
- `app/tests/undetermined-speaker-card.browser.test.mjs` - real-browser proof for both tasks
- `app/src/lib/public/UndeterminedBubble.svelte` - avatar buttons, reveal CSS, touch/keyboard state
- `app/src/routes/arguments/[slug]/+page.svelte` - `popoverMode`, `onUndeterminedAvatarClick`, card wiring
- `app/tests/helpers/transcript-page.mjs` - `realPointer` harness option
- `api/tests/test_trust_public_leak_ban.py` - five new registered public files, two new tests
- `.planning/codebase/DESIGN-SYSTEM.md` - the component-scoped `<style>` exception, `UndeterminedSpeakerCard` in the public component list

## Decisions Made

See `key-decisions` in frontmatter — all four are test/harness-environment findings (measured, not assumed) plus the Task-1/Task-2 boundary on `UndeterminedSpeakerCard`'s D-15 swap.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `openTranscriptPage()` needed a real (non-headless) browser mode to prove hover behavior**
- **Found during:** Task 1, writing the browser test's first assertion (`matchMedia('(hover: hover)').matches`)
- **Issue:** The plan's own `<behavior>` requires asserting `hover: hover` is `true` "so a hover-media miss is diagnosable rather than a silent reveal failure downstream." Against the shared harness's existing `--headless=new` launch, this assertion failed — measured directly (ad hoc CDP probes against this exact Chromium binary) that headless mode, in every combination tried (`--headless=new`, `--headless=old`, with and without `--ozone-platform=x11`, with or without `$DISPLAY` set), always reports `(hover: hover)`/`(pointer: fine)` as `false`. Only a real (non-headless) window against a real `$DISPLAY` (WSLg's `:0` on this host) reports `true`.
- **Fix:** Added an opt-in `realPointer` option to `openTranscriptPage()` (default `false`, so the four pre-existing browser test files keep their exact current headless behavior). When `true`, the launch omits `--headless=new` and adds `--window-position=-32000,-32000` to keep the window off the visible desktop; throws loudly if `$DISPLAY` is unset rather than silently falling back to headless (which would make the hover assertion pass for the wrong reason).
- **Files modified:** `app/tests/helpers/transcript-page.mjs`, `app/tests/undetermined-speaker-card.browser.test.mjs`
- **Verification:** The hover/click/keyboard test passes with `realPointer: true`; the pre-existing `undetermined-bubble.browser.test.mjs` and `speaker-initials.browser.test.mjs` still pass unmodified (headless, default `realPointer: false`).
- **Committed in:** `fce91862c` (Task 1 commit)

**2. [Rule 1 - Bug] CDP `Input.dispatchKeyEvent` needs a specific event sequence to activate a focused `<button>` on Enter**
- **Found during:** Task 2, keyboard focus + Enter assertion
- **Issue:** A plain `keyDown` + `keyUp` pair (matching the pattern already used for Escape elsewhere in this file) reaches the page's own `keydown`/`keyup` listeners but never triggers the browser's native "Enter activates a focused button" default action — no `click` event fires. Measured directly: a minimal test page confirmed `keydown`/`keyup` alone produce no `click`, while `rawKeyDown` → `char` (with `text`/`unmodifiedText: '\r'`, `windowsVirtualKeyCode: 13`) → `keyUp` produces `keydown`, `keypress`, `click`, `keyup` in that order.
- **Fix:** The test's Enter dispatch now sends `rawKeyDown` → `char` → `keyUp` with `windowsVirtualKeyCode: 13`.
- **Files modified:** `app/tests/undetermined-speaker-card.browser.test.mjs`
- **Verification:** The keyboard assertion passes; the card opens and shows the expected paragraph.
- **Committed in:** `7a97e70e4` (Task 2 commit)

**3. [Rule 1 - Bug] `Input.synthesizeTapGesture` does not synthesize a compatibility `click` event on this Chromium build**
- **Found during:** Task 2, touch test's second tap (avatar activation)
- **Issue:** `Input.synthesizeTapGesture({ gestureSourceType: 'touch' })` reliably dispatches real `pointerdown`/`pointerup` with `pointerType === 'touch'` (so the row's own reveal handler fires correctly), but — measured directly — never synthesizes the compatibility `click` event a real touchscreen tap produces, so the avatar's `onclick` activation never fires through it alone.
- **Fix:** The touch test tries `synthesizeTapGesture` first (per the plan's own instruction), and falls back to `Emulation.setTouchEmulationEnabled({ enabled: true, configuration: 'mobile' })` + `Input.dispatchTouchEvent` — confirmed via direct probe to produce both the reveal and the `click` — if the card never opens after several retries. The mechanism actually used is logged via `console.log` (visible in this SUMMARY's test-output capture: `mechanism used: Emulation.setTouchEmulationEnabled + Input.dispatchTouchEvent`).
- **Files modified:** `app/tests/undetermined-speaker-card.browser.test.mjs`
- **Verification:** The touch test passes end to end (reveal, non-leak to the other bubble, and card activation).
- **Committed in:** `7a97e70e4` (Task 2 commit)

**4. [Rule 1 - Bug] A single click/tap immediately after the initial DOM-count check races Svelte 5's delegated-event hydration**
- **Found during:** Task 2, debugging why an isolated single tap/click never registered
- **Issue:** Svelte 5 attaches delegated `onclick`/`onpointerup` handlers via a symbol keyed on the element (`element[event_symbol]`), set only once the component's own client-side mount function runs — measured at ~1.8s after the SSR-rendered markup is first visible (`document.querySelectorAll('[role="article"]').length >= N` becoming true) on this host. Task 1's existing `clickUntilEffect` retry helper already accounted for this for mouse clicks; the new touch test's first single-shot tap did not.
- **Fix:** The touch test's first tap now retries (up to 40 times, 100ms apart) until `data-revealed` flips, exactly mirroring `clickUntilEffect`'s pattern.
- **Files modified:** `app/tests/undetermined-speaker-card.browser.test.mjs`
- **Verification:** The touch test's first-tap assertion passes reliably.
- **Committed in:** `7a97e70e4` (Task 2 commit)

---

**Total deviations:** 4 auto-fixed (1 blocking test-infrastructure gap, 3 bugs — all in test/CDP dispatch code, none in the shipped component or route code).
**Impact on plan:** All four were necessary to make the plan's own `<behavior>`/`<verify>` requirements provable at all on this host; none touched `UndeterminedBubble.svelte`, `UndeterminedSpeakerCard.svelte` or `+page.svelte`'s actual behavior. No scope creep.

## TDD Gate Compliance

Both tasks carry `tdd="true"`, but `workflow.tdd_mode` is `false` in this project's `.planning/config.json` (same precedent as plans 53-01/53-02/53-03), so the formal `test(...)` → `feat(...)` → `refactor(...)` commit-per-phase gate is not enforced. Task 1's RED phase was genuinely exercised: the new browser test was run against the unmodified `UndeterminedBubble.svelte`/`+page.svelte` first and failed for the expected reason (`expected exactly 2 undetermined avatars, got 0`) before any implementation landed; it then passed after the implementation, verified against every `<verify>`/acceptance-criteria command before the single `feat(53-04):` commit. Task 2's additions (keyboard, touch, D-15, leak-ban registration) were implemented and verified together, then committed as one `feat(53-04):` commit. No `test(...)`/`feat(...)` commit pair was expected, and none was claimed.

## Issues Encountered

None beyond the four deviations documented above (all resolved in-flight, before any commit landed). The `scotus_test` DB-tombstone risk and the "advance-plan ignores wave order" STATE.md quirk (both noted in project memory) did not need handling — the full bare pytest run (1484 passed, 5 xfailed, 891.27s) reflects only this plan's two new leak-ban tests added to the 53-03 baseline (1482 passed, 5 xfailed).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All five of Phase 53's plans (53-01, 53-02, 53-03, 53-04, 53-05) are now summarized. SPEAKER-01 (shared-declared across 53-02/53-03/53-04) and SPEAKER-02 (declared only here) are both ready to mark `Complete` in `REQUIREMENTS.md` once this plan's `update_requirements` step runs.
- Task 2's `<human-check>` (visual/device fidelity against Figma node `33:62` and fixture 15169, desktop + real touch device) is recorded above as a `human_judgment: true` coverage entry (D7), deferred to `/gsd-verify-work`'s end-of-phase UAT per this project's default `human_verify_mode: end-of-phase` — not yet performed by a human. 53-03's own D6 human-check (Treatment D's rest-state visual read) is still outstanding from that plan too; both should be reviewed together at end-of-phase UAT since they cover the same fixture/argument view.
- No blockers. This is the last outstanding plan in Phase 53 — the phase is ready for `/gsd-verify-work` once the orchestrator confirms.

## Self-Check: PASSED

- `app/src/lib/public/UndeterminedSpeakerCard.svelte` — FOUND
- `app/tests/undetermined-speaker-card.browser.test.mjs` — FOUND
- `app/src/lib/public/UndeterminedBubble.svelte` — FOUND (modified)
- `app/tests/helpers/transcript-page.mjs` — FOUND (modified)
- `api/tests/test_trust_public_leak_ban.py` — FOUND (modified)
- Commit `fce91862c` — FOUND in `git log --oneline --all`
- Commit `7a97e70e4` — FOUND in `git log --oneline --all`
- All plan-level `<verification>` commands re-run and passing: `npm --prefix app run check` → 0 errors, 32 pre-existing warnings (none in files this plan touched); `npm --prefix app run build` → exit 0; `node --test --test-concurrency=1 app/tests/undetermined-speaker-card.browser.test.mjs app/tests/undetermined-bubble.browser.test.mjs` → 3 tests, 3 pass, 0 fail; `pytest api/tests/test_trust_public_leak_ban.py -q` → 112 passed; bare `./.venv/bin/python -m pytest -q` → 1484 passed, 5 xfailed, 0 failed (891.27s)

---
*Phase: 53-undetermined-speakers-marker-normalisation*
*Completed: 2026-09-29*
