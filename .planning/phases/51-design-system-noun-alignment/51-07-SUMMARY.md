---
phase: 51-design-system-noun-alignment
plan: 07
subsystem: ui
tags: [svelte5, runes, design-tokens, transcript, sticky-scroll, apolitical-framing]

requires:
  - phase: 51-design-system-noun-alignment
    provides: "app.css two-layer token set (plan 51-03), lib/public/ directory split (plan 51-05), D-19 transcript-style decision + amendments (plan 51-01/checkpoint)"
provides:
  - "app/src/lib/types/speaker.ts — single TenureRow/SpeakerDetail declaration site"
  - "Token-only lib/public/ component layer (ChatBubble, StageDirection, SectionRail, SpeakerPopover, MobileNavBar)"
  - "D-19 Style B2 transcript reading layer: run grouping, sticky outside-rail avatar, 6/2px corner rounding"
affects: ["51-08 (term listing, shares the token set)", "51-09 (repo-wide sweep — this plan's lib/public/ + route are already clean, do not re-touch)", "51-10 (phase-wide inventory rollup)"]

actuals:
  tokens: 13142
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Run grouping before layout: group consecutive same-speaker utterances into a run object via $derived.by BEFORE rendering, then lay the run out — corner rounding and the sticky rail slot both key off run position, not per-utterance state."
    - "Sticky-avatar-parked-at-bottom: flex-column rail with justify-content:flex-end plus position:sticky;bottom on the (single, run-level) avatar child — the standard technique for an element that both rests at a container's bottom when short and travels/pins when the container is tall."
    - "CSS `order` for side-dependent visual reordering instead of `flex-direction:row-reverse` + duplicated markup — one literal DOM order (rail, then bubble stack), order flips per bench/advocate."

key-files:
  created:
    - app/src/lib/types/speaker.ts
  modified:
    - app/src/lib/public/ChatBubble.svelte
    - app/src/lib/public/StageDirection.svelte
    - app/src/lib/public/SectionRail.svelte
    - app/src/lib/public/SpeakerPopover.svelte
    - app/src/lib/public/MobileNavBar.svelte
    - app/src/routes/arguments/[slug]/+page.svelte
    - app/tests/tenure-public-title.browser.test.mjs

key-decisions:
  - "Bio clamp+expand (Phase 45 BUG-02's -webkit-line-clamp:3 + 'Read more' toggle) removed from SpeakerPopover.svelte — P-06 bans truncating popover content; bio now always renders in full."
  - "Side-colour ternary in SpeakerPopover.svelte resolved via a named function, not an inline quoted-string ternary, so the collapsed IN-02 duplicate cannot silently reappear as a renamed copy."
  - "Stage directions always terminate a run and are never grouped into one, even if the same speaker resumes after — kept the grouping algorithm simple and matches 'belongs to neither side.'"
  - "ChatBubble bubble-to-bubble gap within a run: --space-xs (4px); between runs/stage directions: --space-xl (32px, exact token match to the pre-existing different-speaker gap) — the D-19 'larger step at a speaker change' requirement."

requirements-completed: [DS-02, DS-03]

coverage:
  - id: D1
    description: "Speaker types and side colour each have exactly one declaration/computation site (IN-02/IN-03 closed)."
    requirement: DS-02
    verification:
      - kind: other
        ref: "grep -c 'interface TenureRow|interface SpeakerDetail' on SpeakerPopover.svelte and the transcript route, both 0"
        status: pass
      - kind: other
        ref: "grep -oE \"isBench \\? '[^']+' : '[^']+'\" app/src/lib/public/SpeakerPopover.svelte | wc -l == 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "lib/public/ (5 components) and the transcript route contain zero raw hex, zero numeric font-size, zero -webkit-line-clamp/ellipsis, zero font-weight:500, zero svelte/store imports."
    requirement: DS-03
    verification:
      - kind: other
        ref: "boundary-anchored hex grep + literal plan greps over app/src/lib/public/*.svelte and the route file — see 'Check artifact' note below"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-19 Style B2 transcript reading layer: run grouping computed before layout, one sticky outside-rail avatar per run, 6/2px corner rounding by run position, bench-left/advocate-right preserved, identical typography both sides."
    requirement: DS-02
    verification:
      - kind: other
        ref: "Live SSR smoke test via real vite dev server + mock API + curl (see Deviations/verification note) — 2 role=article runs, 1 role=note stage direction, correct 6/2px radii per position, correct section-anchor id, live position:sticky declaration all present in rendered HTML"
        status: pass
    human_judgment: true
    rationale: "Sticky-scroll behavior over real distance, the Figma frame comparison, and the Justice/advocate visual-weight side-by-side are all operator-eye checks — no browser tool available to this executor. SSR structural proof is strong but not a substitute for watching it scroll."
  - id: D4
    description: "Transcript route: no top-level `data` capture (landmine audit), no derived per-speaker statistic, no truncation."
    requirement: DS-03
    verification:
      - kind: other
        ref: "grep for top-level const-off-data (0 matches); manual classification of every .length occurrence in the diff (none render as visible content)"
        status: pass
    human_judgment: false

duration: ~45min
completed: 2026-08-28
status: complete
---

# Phase 51 Plan 07: Transcript Reading Polish + Duplication Cleanup Summary

**D-19 Style B2 transcript redesign — run-grouped utterances, one sticky outside-rail avatar per run, 6/2px corner rounding — plus a full token conversion of `lib/public/` and closure of the IN-02/IN-03 speaker-popover duplication debt.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-08-28T18:10Z
- **Tasks:** 3
- **Files modified:** 8 (1 created, 7 modified)

## Accomplishments

- **Closed the folded duplication todo (IN-02/IN-03).** `app/src/lib/types/speaker.ts` is now the single declaration site for `TenureRow`/`SpeakerDetail`, imported by `SpeakerPopover.svelte` and the transcript route. `SpeakerPopover.svelte`'s duplicated `avatarBg`/`sideColor` (two variables computing the identical `isBench ? '#94a3b8' : '#93c5fd'` expression) collapsed into one `resolveSideColor()` call site.
- **`lib/public/` is now token-only.** All five components (`ChatBubble`, `StageDirection`, `SectionRail`, `SpeakerPopover`, `MobileNavBar`) reference `var(--token)` for every colour, size, weight, and scale-mapped spacing value. The transcript route's remaining 24 inline style attributes are converted too, including promoting the case-name headline to the Display step (32px/600) per D-09.
- **D-19 Style B2 shipped**: run grouping (`$derived.by`, consecutive same-speaker utterances grouped before layout — the structural unit D-19 requires), one sticky avatar per run in a 40px outside rail (`position:sticky;bottom:var(--space-sm)`, flex-column + `justify-content:flex-end` so it rests at the bottom of a short run and travels/pins for a tall one), and the 6/2px corner-rounding table (single/first/middle/last) driven by a new `position` prop on `ChatBubble`. Bench stays left, advocate stays right (D-05, unrevised); both sides carry identical Lead (18/400/1.6) type — only the neutral speaker-label/avatar colour differs (P-03).
- **P-06 compliance found and fixed**: `SpeakerPopover.svelte`'s bio text used a 3-line `-webkit-line-clamp` collapsed state with a "Read more" toggle (the Phase 45 BUG-02 fix). This is exactly the truncation pattern P-06 bans for popover content. Removed — bio now always renders in full; the popover simply grows taller for a long bio.
- **Landmine audit (Task 3):** every read of `data` in the transcript route was audited. `data` stays a `let` destructure of `$props()`; **zero top-level `const` captures off `data` were found** — `roster`, `sectionAnchors`, and the new `renderItems` (run grouping) all already use `$derived`/`$derived.by`. Nothing needed converting.

## Task Commits

1. **Task 1: Close the folded duplication todo** — `65e9bc5fa` (refactor)
2. **Task 2: Convert lib/public/ onto tokens + reading polish** — `a737f7d76` (feat)
3. **Task 3: Convert the transcript route + run grouping + sticky rail** — `5de8946e9` (feat)

_Task 2 and Task 3 are code-interdependent (see Deviations) — both were implemented before either was verified, then split into two commits by file ownership as planned._

## Files Created/Modified

- `app/src/lib/types/speaker.ts` — new. Single `TenureRow`/`SpeakerDetail` declaration site.
- `app/src/lib/public/ChatBubble.svelte` — avatar removed (moved to the route's rail); new `position`/`showSpeakerName` props drive corner radius and the once-per-run name header; token-only.
- `app/src/lib/public/StageDirection.svelte` — token-only; margin-top/bottom now `var(--space-2xl)` (48px exact match).
- `app/src/lib/public/SectionRail.svelte` — token-only; behavior (IntersectionObserver scroll-spy) unchanged.
- `app/src/lib/public/MobileNavBar.svelte` — token-only; behavior unchanged.
- `app/src/lib/public/SpeakerPopover.svelte` — types imported from the shared module; side colour collapsed to one site; token-only; bio clamp/expand removed (P-06).
- `app/src/routes/arguments/[slug]/+page.svelte` — run grouping (`renderItems` via `$derived.by`), sticky rail avatar per run, corner-position classification, token-only, case-name promoted to Display.
- `app/tests/tenure-public-title.browser.test.mjs` — fixed a pre-existing selector bug (see Deviations).
- `.planning/todos/pending/2026-08-12-speaker-popover-frontend-duplication-cleanup.md` → `.planning/todos/completed/` with a Resolution section.

## Decisions Made

- Bio clamp+expand removed rather than adapted (e.g. into a scrollable-but-uncapped box) — P-06's literal ban on "line clamp" and "fixed-height-plus-hidden-overflow" is satisfied most conservatively by not capping height at all. If a very long bio ever visually strains the popover's positioning, that is new, separate work for a future phase, not a truncation regression.
- Turn-gap values: `--space-xs` (4px) within a run, `--space-xl` (32px, exact match to the prior different-speaker gap) between runs/stage directions — a deliberate redesign choice under D-19's "larger step at a speaker change" instruction, not a mechanical carry-forward of the old per-utterance 24px/32px pair (which no longer applies once same-speaker utterances are grouped into one run).
- Bubble padding `var(--space-sm) var(--space-md)` (8/16) replaces the old residual 12px — a deliberate redesign choice (not a silent rounding) since this plan is a genuine visual redesign, not the mechanical plan-51-09 sweep the TOKEN-MAP was written for.
- Reading-column measure: `max-width: min(72%, 68ch)` on each bubble — adds an explicit `ch`-based cap alongside the pre-existing 72% so a bubble's line length stays bounded even inside a very wide content column, per Task 2's "Measure" instruction.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing critical] Removed the P-06-violating bio clamp+expand affordance**
- **Found during:** Task 2
- **Issue:** `SpeakerPopover.svelte`'s bio paragraph used `-webkit-line-clamp:3` + a "Read more" toggle (Phase 45 BUG-02's fix for a different problem — the card blowing out its own boundary). This plan's own hard prohibition P-06 ("no ellipsis overflow, no line clamp... popover content") bans exactly this pattern, and Task 2's acceptance criteria explicitly grep for `-webkit-line-clamp` across `lib/public/`.
- **Fix:** Removed the clamp, the `bioExpanded`/`bioOverflows`/`bioEl` state, the `$effect` measuring overflow, and the toggle button. Bio now always renders in full.
- **Files modified:** `app/src/lib/public/SpeakerPopover.svelte`
- **Verification:** `grep -rIcE "text-overflow: *ellipsis|-webkit-line-clamp" app/src/lib/public/` → 0 across all five files.
- **Committed in:** `a737f7d76`

**2. [Rule 1 — Bug] Fixed a false-positive-triggering own comment and confirmed the `{#each` grep artifact is pre-existing**
- **Found during:** Task 1/2
- **Issue:** The Task 1 acceptance criterion `grep -oE "isBench \? '[^']+' : '[^']+'"` initially matched my own explanatory comment (which literally spelled out the banned pattern in prose), and the Task 2/3 hex-literal grep (`#[0-9a-fA-F]{3,8}`) matches `{#each` (Svelte's each-block syntax: `#`+`e`,`a`,`c` are all valid hex digits, `h` breaks the match at exactly 3 chars — `#eac`). The `{#each` false positive is pre-existing Svelte template syntax already present in the original, untouched files, not something this plan introduced.
- **Fix:** Reworded the comment to avoid the literal substring. For the `{#each` artifact, ran a boundary-anchored grep (`#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?\b|#[0-9a-fA-F]{3}\b`) confirming **zero real hex literals** remain anywhere in `lib/public/` or the route.
- **Files modified:** `app/src/lib/public/SpeakerPopover.svelte` (comment only)
- **Verification:** Boundary-anchored grep, 0 matches, both files.
- **Committed in:** `65e9bc5fa`, `a737f7d76`

**3. [Rule 1 — Bug] Fixed a pre-existing, stale selector in `tenure-public-title.browser.test.mjs`**
- **Found during:** Task 3 (the required re-read of this test)
- **Issue:** The test's `openPopoverAndReadTenureLine` queried `.popover-card p` and asserted the tenure office title and its date range appeared as a single combined `<p>` string (`'Chief Justice — 2005–present'`). The actual markup — in both the pre-existing file and unchanged by this plan's token conversion — renders the office title and the range as two separate `<span>` elements in a flex row, never inside a `<p>`. This selector could never have matched since whichever pass introduced the two-column tenure layout (before this phase); the test has been silently vacuous (`chiefParagraphs` would only ever contain `['Fixture Chief']`, length 1, failing the length-2 `deepEqual` immediately) for as long as no browser has been available to run it.
- **Fix:** Query the actual elements (`.popover-card p` for the name, `.popover-card span` for the office title + range — deterministic for this fixture, which has no role pill, birth/death line, or appointed_by/reason_left row). Assertion strength unchanged: still proves the formal "Chief Justice"/"Associate Justice" title renders, still rejects the raw canonical value and the generic "Justice" fallback.
- **Files modified:** `app/tests/tenure-public-title.browser.test.mjs`
- **Verification:** Could not run to completion in this sandbox (no browser — see Issues Encountered), but the fix was reasoned against the actual live-rendered SSR HTML (see next item) and the exact markup this plan's own ChatBubble/SpeakerPopover changes produce.
- **Committed in:** `5de8946e9`

**4. [Rule 3 — Blocking, cross-task coupling] Task 2 and Task 3 were implemented together, then split into two commits**
- **Found during:** Task 2, after committing `ChatBubble.svelte`'s new `position`/`showSpeakerName` prop contract (avatar removed) and running `npm run check`
- **Issue:** D-19's run-grouping/sticky-rail redesign is stated at the plan level, not scoped cleanly to one task — `ChatBubble.svelte`'s new props are meaningless without the route computing runs and passing them, and the route can't compute runs without `ChatBubble`'s new contract existing. Running Task 2's own `npm run check` before touching the route produced a real, expected type error (`onAvatarClick does not exist in type '$$ComponentProps'`) — not a defect, but an artifact of the plan splitting one coherent redesign across two task boundaries.
- **Fix:** Implemented both tasks' code before running any verification, verified the whole working tree (`npm run check`/`build`/live SSR smoke test) once both were code-complete, then committed by file ownership: the five `lib/public/` components as Task 2's commit, the route + test file as Task 3's commit. Both commits individually diff-reviewable; the intermediate broken state never existed on disk as a commit.
- **Files modified:** (see Task 2/3 commits above)
- **Verification:** `npm run check`/`build` both exit 0 against the final tree; see coverage D3 for the live SSR proof.
- **Committed in:** `a737f7d76`, `5de8946e9`

---

**Total deviations:** 4 auto-fixed (1 missing-critical, 2 bugs, 1 blocking/cross-task-coupling).
**Impact on plan:** All four were necessary for correctness or for the plan's own hard constraints (P-06); none expanded scope beyond what D-19/DS-02/DS-03 already required.

## Issues Encountered

**No headless browser in this sandbox** (same constraint every prior plan in this phase hit — no `/usr/bin/microsoft-edge`, `google-chrome`, or `chromium`). Concretely:

- `node --test app/tests/tenure-public-title.browser.test.mjs` fails fail-closed on its own browser-presence assertion (`AssertionError: Microsoft Edge or Google Chrome must be installed for this fail-closed test`). This is NOT a code defect and is NOT reported as passing.
- `node --test app/tests/tenure-office.browser.test.mjs` — **unrelated, pre-existing** (confirmed via `git diff --name-only`, this plan touches zero files under `admin/people/`): 9/11 pass, 2 fail (`failed save rehydrates all submitted profile and tenure edits`, `server-failure restoration keeps Office selection and unrelated edits local`), both against `app/src/routes/admin/people/[id]/+page.svelte`. Per this plan's own dispatch instructions, this is a known, out-of-scope, stale assertion predating Phase 38 — not touched.

**Compensating verification performed instead:** a real vite dev server was started against a hand-built mock FASTAPI backend (4 utterances: two by the same bench speaker forming a run, one stage direction, one advocate utterance forming a single-utterance run) and the SSR HTML fetched via `curl`. Confirmed in the live-rendered output:
- Exactly 2 `role="article"` elements (one bench run, one advocate run) and 1 `role="note"` (the stage direction).
- Correct `aria-label`s: `"Bench: Fixture Chief"`, `"Advocate: Fixture Advocate"`, `"View Fixture Chief details"`, `"View Fixture Advocate details"`.
- Correct D-19 corner radii: `6px 6px 2px 2px` (first bubble of the 2-utterance run), `2px 2px 6px 6px` (last bubble), `6px 6px 6px 6px` (the single-utterance advocate run).
- `id="section-opening-0"` present on the correct utterance's wrapper.
- A live `position: sticky;` declaration present on the rail avatar wrapper.
- No unresolved `undefined` anywhere in the output, no vite console errors/warnings.

**Sticky-avatar ancestor `overflow` audit** (required by the hazard notes — sticky fails silently, this is a real audit not a formality). Walked every level from the sticky avatar wrapper up to the document root:

| Level | Element | `overflow` set? |
|---|---|---|
| 1 | avatar wrapper (`position: sticky`) | no |
| 2 | rail column (flex column, `justify-content:flex-end`) | no |
| 3 | run row (`role="article"`, flex row) | no |
| 4 | per-item margin wrapper (`{#each renderItems}`) | no |
| 5 | chat column (`padding: var(--space-2xl) var(--space-lg)`) | no |
| 6 | `.content-grid` (CSS Grid) | no |
| 7 | `<main>` | no |
| 8 | `<body>`/`<html>` (`app.css`) | no (confirmed by reading `app.css` in full — no `overflow` rule anywhere in the base reset) |

No `overflow: hidden|clip|scroll|auto` on any ancestor. The rail column genuinely stretches to the run's full height via the row's `align-items: stretch` (default, set explicitly) plus the bubble-stack column's `flex: 1 1 auto`.

**What is genuinely NOT verified (operator UAT items, not claimed as passing):**
1. The sticky-avatar scroll behavior over a real, long (multi-screen) utterance — the SSR proof above confirms the CSS declaration and structural correctness, but only a real scrolling browser can confirm the described Telegram-style travel/pin/park behavior.
2. Comparison against the `transcript-style-B2-selected` / `arguments-transcript` Figma frame at 375px and 1280px (Figma MCP unavailable to this subagent per the dispatch instructions).
3. Side-by-side visual confirmation that a Justice turn and an advocate turn carry identical size/weight/emphasis (code-level guarantee confirmed by inspection — both use identical `var(--font-size-lead)`/`var(--font-weight-regular)` tokens regardless of side — but not eyeballed).
4. A full-length (~90 min) argument scrolled end to end for section-rail behavior and scroll smoothness.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `lib/public/` and the transcript route are fully token-converted; plan 51-09's repo-wide sweep should skip these files (already clean) rather than re-touch them.
- DS-02 and DS-03 requirements are marked complete by this plan's frontmatter, but both are phase-wide requirements shared with other plans in this phase (51-08, 51-09) — the shared-ID gate holds them at `Pending` until every declaring plan finishes.
- **Blocker/concern for the operator:** items 1–4 under "What is genuinely NOT verified" above need a real browser session before this can be considered visually signed off, consistent with every other frontend plan in this phase.

---
*Phase: 51-design-system-noun-alignment*
*Completed: 2026-08-28*

## Self-Check: PASSED

- FOUND: `app/src/lib/types/speaker.ts`
- FOUND: `app/src/lib/public/ChatBubble.svelte`
- FOUND: `app/src/routes/arguments/[slug]/+page.svelte`
- FOUND: `.planning/todos/completed/2026-08-12-speaker-popover-frontend-duplication-cleanup.md`
- FOUND commit `65e9bc5fa` (Task 1)
- FOUND commit `a737f7d76` (Task 2)
- FOUND commit `5de8946e9` (Task 3)
