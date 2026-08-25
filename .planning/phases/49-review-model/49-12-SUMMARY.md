---
phase: 49-review-model
plan: 12
subsystem: ui
tags: [svelte, css-flexbox, pytest-source-contract, playwright, narrow-viewport]

requires:
  - phase: 49-review-model (plan 08)
    provides: three horizontal-overflow containment fixes (queue tables, status segment group, dashboard grid) on /admin/review and /admin
provides:
  - AdminSubNav.svelte and TopNav.svelte no longer produce an unescaped display:flex row at 375px
  - A computed page-chrome sweep (api/tests/test_phase49_nav_narrow_viewport_contract.py) that discovers chrome components structurally instead of by hand-enumeration
  - A re-runnable operator audit script (app/scripts/narrow-viewport-audit.mjs, npm run audit:viewport) that measures real page-level scroll, not just chrome-component declarations
affects: [51-design-system]

actuals:
  tokens: 10232
  tasks: 4
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Computed-set regression gate: enumerate chrome files structurally (transitively-imported +layout.svelte components UNION first-tag-<nav> components) rather than hand-listing them, with a non-degeneracy guard that fails (not passes vacuously) if the computed set collapses"
    - "Source-text-vs-behavioural-evidence separation stated in the artifact's own docstring, not just in prose docs"

key-files:
  created:
    - api/tests/test_phase49_nav_narrow_viewport_contract.py
    - app/scripts/narrow-viewport-audit.mjs
  modified:
    - app/src/lib/components/AdminSubNav.svelte
    - app/src/lib/components/TopNav.svelte
    - app/package.json
    - .planning/phases/49-review-model/49-UAT.md

key-decisions:
  - "D-49-12-a: flex-wrap over container-scroll for AdminSubNav — five independent links with no shared border geometry wrap cleanly, and a nav's destinations should stay visible, not hide behind a scroll gesture"
  - "D-49-12-b: kept margin-left:auto on the logout form — under flex-wrap it resolves within whichever line the form lands on, keeping Log out flush right at every width"
  - "D-49-12-c: TopNav brought into sweep compliance even though it was never observed causing page scroll (zero pixels of slack at 375px) — sweep MEMBERSHIP decides, not judgement, so the near-miss the sweep found on its first run was not exempted"
  - "D-49-12-c (operator, 2026-08-25): promoted the Task 1 browser measurement into a permanent, re-runnable operator tool (app/scripts/narrow-viewport-audit.mjs) — a TOOL, not a gate; no dependency added, nothing in api/tests imports it"

requirements-completed: [REVIEW-03]

coverage:
  - id: D1
    description: "AdminSubNav no longer causes page-level horizontal scroll at 375px on any of six admin routes; 1280px sub-nav geometry is unchanged"
    requirement: "REVIEW-03"
    verification:
      - kind: e2e
        ref: "live headless-chromium measurement, Task 1 — document.scrollWidth vs clientWidth on /admin, /admin/review, /admin/pipeline, /admin/help (375px, before/after) and /admin (1280px, before/after)"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_nav_narrow_viewport_contract.py::test_no_chrome_component_has_an_unescaped_flex_row_at_narrow_viewport"
        status: pass
    human_judgment: false
  - id: D2
    description: "A computed chrome-set sweep that discovers a fifth unfixed nav (TopNav) without anyone naming it in advance, and cannot pass vacuously if the walker degrades"
    requirement: "REVIEW-03"
    verification:
      - kind: unit
        ref: "api/tests/test_phase49_nav_narrow_viewport_contract.py::test_walker_discovers_the_three_known_chrome_components, ::test_non_degeneracy_guard_rejects_an_artificially_emptied_chrome_set, ::test_non_degeneracy_guard_passes_on_the_real_walker"
        status: pass
    human_judgment: false
  - id: D3
    description: "A re-runnable operator audit script measuring real page-level scroll (not chrome-component declarations), correctly reporting SKIPPED (never PASS) on an unauthenticated admin route, and naming offending elements on overflow"
    verification:
      - kind: other
        ref: "manual invocation: npm run audit:viewport at 375px and 1280px against the live dev server, plus an unauthenticated-profile run confirming SKIPPED not PASS — full output quoted below"
        status: pass
    human_judgment: false

duration: ~70min
completed: 2026-08-25
status: complete
---

# Phase 49 Plan 12: Close G-49-5c (AdminSubNav flex-wrap) + computed chrome sweep Summary

**Closed the fourth and last cause of admin-page horizontal scroll at 375px — `AdminSubNav.svelte`'s unescaped `display:flex` row — with one `flex-wrap: wrap` declaration, replaced the class of hand-enumerated regression gate that missed it with a computed chrome-set sweep that found and closed a second near-miss (TopNav) unprompted, and shipped a re-runnable operator audit script per an in-session operator decision (D-49-12-c).**

## Performance

- **Duration:** ~70 min
- **Tasks:** 4 (1, 2, 2b, 3)
- **Files modified:** 6 (2 Svelte components, 1 new pytest module, 1 new script, package.json, 49-UAT.md)

## Accomplishments

- `AdminSubNav.svelte` and `TopNav.svelte` each gained one `flex-wrap: wrap` declaration — the only source change either file needed
- New `api/tests/test_phase49_nav_narrow_viewport_contract.py`: a chrome-set walker that COMPUTES page chrome (not a hand-picked list), a whitespace-insensitive detector, a non-degeneracy guard, and a permanent regression fixture on the historical pre-fix AdminSubNav declaration set
- New `app/scripts/narrow-viewport-audit.mjs` (`npm run audit:viewport`): a re-runnable, dependency-free operator tool measuring real page-level scroll and naming offending elements
- G-49-5c flipped to `resolved` in 49-UAT.md, with a new appended section separating MEASURED (real browser numbers) from ASSERTED-ONLY (structural)
- Two new, out-of-scope findings surfaced and recorded (not fixed): `/admin/arguments` and `/admin/people` each independently overflow at 375px via an unwrapped `<table>`

## Task Commits

1. **Task 1: Measure the overflow in a real browser, fix AdminSubNav, measure again** - `73d0b7a32` (fix)
2. **Task 2: A computed chrome sweep that fails on an unfixed component nobody named** - `6c844e10d` (feat)
2b. **Task 2b: Commit the narrow-viewport audit as a re-runnable operator tool** - `30f879ee2` (feat)
3. **Task 3: Record what was measured, separately from what was asserted** - `fc7bf0281` (docs)

(Task 2b's insertion into the plan itself was pre-committed as `714cc095d` before this execution began, per the orchestrator's amendment.)

## Files Created/Modified

- `app/src/lib/components/AdminSubNav.svelte` - added `flex-wrap: wrap;` to the `<nav>` inline style (one line; nothing else changed)
- `app/src/lib/components/TopNav.svelte` - added `flex-wrap: wrap;` to the `<nav>` inline style (one line; nothing else changed)
- `api/tests/test_phase49_nav_narrow_viewport_contract.py` - new: chrome-set walker, detector, per-tag collector, non-degeneracy guard, live sweep, detector unit tests
- `app/scripts/narrow-viewport-audit.mjs` - new: operator tool, resolves chromium/playwright-core at runtime, measures scrollWidth vs clientWidth per route
- `app/package.json` - added `"audit:viewport": "node scripts/narrow-viewport-audit.mjs"`; no dependency added
- `.planning/phases/49-review-model/49-UAT.md` - G-49-5c flipped to `resolved`; new appended "Third live pass" section

## Decisions Made

- D-49-12-a — `flex-wrap: wrap`, not container scroll, for AdminSubNav (five independent links, no shared border geometry to protect; a nav should not hide destinations behind a scroll gesture)
- D-49-12-b — kept `margin-left: auto` on the logout form (resolves within its wrapped line, stays flush right at every width)
- D-49-12-c — TopNav brought into compliance by sweep membership, not because it was observed causing scroll (it was not — zero pixels of slack at 375px)
- D-49-12-c (operator) — promoted the browser measurement into a committed, re-runnable script; explicitly a tool, never a gate

## Assertion-by-assertion RED/GREEN record

**Task 1 (browser measurement, not a pytest assertion):** RED confirmed — before the fix, six admin routes at 375px measured `scrollWidth 423 vs clientWidth 375` on five of six (`/admin`, `/admin/review`, `/admin/people`, `/admin/pipeline`, `/admin/help`) and `680 vs 375` on `/admin/arguments` (separate cause, see below). GREEN confirmed after the fix — see numbers below.

**Task 2, `api/tests/test_phase49_nav_narrow_viewport_contract.py` (10 tests):**

| Test | RED-then-GREEN or GREEN-from-start |
|---|---|
| `test_detector_flags_the_historical_pre_fix_admin_subnav_declaration_set` | GREEN from the start — a permanent fixture proof, not a live-red gate |
| `test_detector_clears_the_same_set_once_flex_wrap_is_added` | GREEN from the start |
| `test_detector_accepts_overflow_x_auto_as_an_escape` | GREEN from the start |
| `test_detector_accepts_position_fixed_with_left_and_right_as_an_escape` | GREEN from the start |
| `test_detector_ignores_missing_whitespace_after_the_colon` | GREEN from the start |
| `test_detector_returns_none_when_display_flex_is_entirely_absent` | GREEN from the start |
| `test_walker_discovers_the_three_known_chrome_components` | GREEN from the start (AdminSubNav was already fixed by Task 1 at this point) |
| `test_non_degeneracy_guard_passes_on_the_real_walker` | GREEN from the start |
| `test_non_degeneracy_guard_rejects_an_artificially_emptied_chrome_set` | GREEN from the start (proof-of-the-guard test using an artificial empty set) |
| `test_no_chrome_component_has_an_unescaped_flex_row_at_narrow_viewport` | **RED before TopNav's fix, GREEN after.** |

**The load-bearing RED, quoted verbatim** (module run against `TopNav.svelte` BEFORE any edit to it):

```
AssertionError: unescaped display:flex chrome row(s) found:
  TopNav.svelte:<nav> — display:flex with no escape found (missing all of: flex-wrap: wrap|wrap-reverse; overflow-x: auto|scroll; position: fixed with left + right)
assert not ['TopNav.svelte:<nav> — display:flex with no escape found (missing all of: flex-wrap: wrap|wrap-reverse; overflow-x: auto|scroll; position: fixed with left + right)']
```

After adding `flex-wrap: wrap` to TopNav's `<nav>`: `10 passed in 4.25s`.

**Non-degeneracy guard proven to fail (not pass vacuously):** the import-detection regex was temporarily corrupted (replaced with a string that matches nothing), the module re-run, and three tests failed as expected:

```
AssertionError: chrome-set walker failed to discover: ['TopNav.svelte'] — the sweep would silently skip these components
```

(`test_walker_discovers_the_three_known_chrome_components`, `test_non_degeneracy_guard_passes_on_the_real_walker`, and `test_no_chrome_component_has_an_unescaped_flex_row_at_narrow_viewport` all failed — the sweep did NOT pass vacuously.) The module was then restored byte-for-byte from a pre-edit backup and re-verified at `10 passed`.

## Measured numbers (verbatim, Task 1)

**375px, before the AdminSubNav fix** (scrollWidth / clientWidth):
- `/admin`: 423 / 375
- `/admin/review`: 423 / 375
- `/admin/arguments`: 680 / 375 (separate, pre-existing cause — see Known Issues below)
- `/admin/people`: 423 / 375
- `/admin/pipeline`: 423 / 375
- `/admin/help`: 423 / 375

**375px, after the AdminSubNav fix:**
- `/admin`: 375 / 375
- `/admin/review`: 375 / 375
- `/admin/arguments`: 680 / 375 (unchanged — unrelated cause)
- `/admin/people`: 403 / 375 (a second, independent overflow, previously masked by the sub-nav's larger 423 — see Known Issues)
- `/admin/pipeline`: 375 / 375
- `/admin/help`: 375 / 375

**1280px `/admin` sub-nav geometry, before and after — IDENTICAL:**
- `navHeight`: 69 (both)
- logout form `left` / `right`: 1169.609375 / 1256 (both)
- page `scrollWidth == clientWidth == 1280` (both)

## Task 2b — audit script output (quoted verbatim)

`npm run audit:viewport` at 375px against the live dev server (authenticated profile):

```
Using chromium: /home/jason/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome (via ~/.cache/ms-playwright/chromium-1228)

Narrow-viewport audit — 375px viewport, base http://localhost:5173

PASS     /  (scrollWidth 375 <= clientWidth 375)
PASS     /cases  (scrollWidth 375 <= clientWidth 375)
PASS     /admin  (scrollWidth 375 <= clientWidth 375)
PASS     /admin/review  (scrollWidth 375 <= clientWidth 375)
OVERFLOW /admin/arguments  (scrollWidth 680 > clientWidth 375)
           <table> right=679.95  "StatusCase TitleDocketArguedCreatedPubli"
           <thead> right=679.95  "StatusCase TitleDocketArguedCreatedPubli"
           <tr> right=679.95  "StatusCase TitleDocketArguedCreatedPubli"
           <th> right=679.95  "Publish"
           <tbody> right=679.95  "Published TrustedAnderson v. Liberty Lob"
OVERFLOW /admin/people  (scrollWidth 403 > clientWidth 375)
           <table> right=402.94  "NameTenure coverage Tenure gapMissing fi"
           <thead> right=402.94  "NameTenure coverage Tenure gapMissing fi"
           <tr> right=402.94  "NameTenure coverage Tenure gapMissing fi"
           <th> right=402.94  ""
           <tbody> right=402.94  "Samuel A. Alito, Jr.JusticeNo tenure ⚠ G"
PASS     /admin/help  (scrollWidth 375 <= clientWidth 375)
```

`npm run audit:viewport --width 1280` — clean pass on all seven routes:

```
PASS     /  (scrollWidth 1280 <= clientWidth 1280)
PASS     /cases  (scrollWidth 1280 <= clientWidth 1280)
PASS     /admin  (scrollWidth 1280 <= clientWidth 1280)
PASS     /admin/review  (scrollWidth 1280 <= clientWidth 1280)
PASS     /admin/arguments  (scrollWidth 1280 <= clientWidth 1280)
PASS     /admin/people  (scrollWidth 1280 <= clientWidth 1280)
PASS     /admin/help  (scrollWidth 1280 <= clientWidth 1280)
```

Unauthenticated-profile run (fresh, non-authenticated profile dir) — confirms SKIPPED, never PASS:

```
SKIPPED  /admin  (redirected to /admin/login (not authenticated))
PASS     /cases  (scrollWidth 375 <= clientWidth 375)
```

`app/package.json` verified: `audit:viewport` script present; neither `playwright`, `playwright-core`, nor `@playwright/test` appears in `dependencies` or `devDependencies`.

## Deviations from Plan

### Auto-fixed / substituted, all pre-declared or scope-preserving

**1. [Environment substitution, not a Rule 1-4 deviation] Playwright MCP tool unavailable to this executor; used direct `node` + `playwright-core` against a profile copy instead**
- **Found during:** Task 1, before any measurement
- **Issue:** This executor (a spawned subagent) has no MCP tool access — only Read/Write/Edit/Bash/Skill. The `.mcp.json`-configured Playwright MCP server process was ALSO already running and held the `.playwright-profile` singleton lock, so even a direct browser launch against the real profile path failed (`Failed to create a ProcessSingleton`).
- **Fix:** Copied `.playwright-profile` to a scratch directory (cookies/session state only — no credential was ever read, typed, or echoed, satisfying T-49-12-creds) and launched `playwright-core`'s `chromium.launchPersistentContext` against the copy, using the exact chromium executable and `LD_LIBRARY_PATH` the plan specified. This reused the SAME authenticated session (confirmed: measured 423 matches the operator's own 49-UAT.md reading exactly) without ever touching the live MCP server's process or profile.
- **Files modified:** None (measurement-only; scratch scripts lived outside the repo)
- **Verification:** `finalUrl` on every admin route was the route itself, never `/admin/login` — confirms authentication succeeded via the reused profile
- **Documented:** Also recorded in 49-UAT.md's G-49-5c `missing:` list for full transparency

**2. [Rule 1 — accidental self-collision, caught and fixed] Duplicate concurrent pytest invocations from this executor's own background-command handling**
- **Found during:** Task 1/3 full-suite verification attempts
- **Issue:** Several of my own `Bash` calls that exceeded the 120s foreground timeout were auto-backgrounded, and in three separate instances a SECOND copy of the same command was later replayed by the harness, producing two or three of my OWN full-suite `pytest api/tests -q` processes running concurrently against the same physical test database (a known sandbox characteristic — `TEST_DATABASE_URL` and `DATABASE_URL` resolve to the same physical Postgres DB here, documented in STATE.md's 49-06 close-out notes). This produced spurious count-mismatch and `DeadlockDetectedError`-shaped failures unrelated to any code change.
- **Fix:** Identified and killed the stray duplicate processes (verified each was my own invocation via command-line inspection before killing any), then re-ran a single clean full-suite pass.
- **Files modified:** None
- **Verification:** The final clean single-instance run passed 1150/1150 with zero failures.

**3. [Documented finding, correctly NOT auto-fixed — Rule scope boundary] Two new, unrelated overflow causes discovered on `/admin/arguments` and `/admin/people`**
- **Found during:** Task 1 (browser measurement) and reconfirmed via Task 2b's audit script
- **Issue:** Both pages contain an unwrapped `<table>` with no `overflow-x` container, causing independent horizontal page scroll at 375px (`/admin/arguments`: 680 vs 375; `/admin/people`: 403 vs 375, previously masked by the larger sub-nav overflow).
- **Fix:** NOT applied — out of scope per this plan's `files_modified` (neither page's `+page.svelte` is listed) and per the SCOPE BOUNDARY rule (pre-existing issues in unrelated files). Recorded as new findings in 49-UAT.md's G-49-5c `missing:` list and in `.planning/WINDOWS.md` (entries 26 and 27, kind `deviation`, status `open`) for a future plan or `/gsd-review-backlog`.
- **Files modified:** None (documentation only: 49-UAT.md, WINDOWS.md)

**A concurrent sibling agent (49-11) was also executing during this session** (per the plan's own explicit note) — its in-progress, uncommitted `api/tests/test_phase49_argument_lock_contract.py` produced 11 failures in one interim full-suite run while it was mid-flight; these cleared entirely once 49-11's work landed and are visible in the final clean 1150-pass run. No file in that plan's territory (`update_argument`, `update_argument_metadata`, `resolve_job`, `create_person_for_job`, the Case/Argument-Details cards, or the `readonly is always false here` comment) was touched by this plan.

---

**Total deviations:** 1 environment substitution (documented, not a correctness change), 1 self-caused-and-self-fixed test-execution artifact, 2 new out-of-scope findings recorded (not fixed).
**Impact on plan:** None of these affected the shipped fix's correctness. No scope creep — the two new findings were explicitly left unfixed.

## Issues Encountered

- The live `.playwright-profile` was locked by an already-running `@playwright/mcp` server process throughout this session (see Deviation 1) — resolved via a profile copy, never by touching the live session.
- Full-suite pytest runs are unreliable when run concurrently with another process against this sandbox's shared physical test/dev database — resolved by killing stray duplicate processes and re-running once cleanly. No other issues.

## User Setup Required

None - no external service configuration required. `app/scripts/narrow-viewport-audit.mjs` requires the operator to have previously run `npx playwright install` (Chromium already present in this environment at `~/.cache/ms-playwright/chromium-1228`), which was already true before this plan.

## Next Phase Readiness

- G-49-5c is closed — this was the last open gap in Phase 49 (`gap_ids: [G-49-5c]`, the only plan claiming it).
- Two new, unrelated overflow findings on `/admin/arguments` and `/admin/people` are recorded (WINDOWS.md #26/#27) and left open — natural candidates for a Phase 51 (design system) cleanup pass or `/gsd-review-backlog`, since they are cosmetic/minor and independent of any Phase 49 review-model logic.
- The full `api/tests` suite is green at 1150 passed, 0 failed (clean, single-process run), up from the 1123 baseline recorded at the start of this session.

## Self-Check: PASSED

All created/modified files confirmed present on disk (AdminSubNav.svelte, TopNav.svelte,
test_phase49_nav_narrow_viewport_contract.py, narrow-viewport-audit.mjs, package.json,
49-UAT.md, this SUMMARY). All 5 referenced commit hashes (73d0b7a32, 6c844e10d, 30f879ee2,
fc7bf0281, 714cc095d) confirmed present in git log.

---
*Phase: 49-review-model*
*Completed: 2026-08-25*
