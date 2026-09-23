---
phase: 51-design-system-noun-alignment
plan: 05
subsystem: ui
tags: [svelte, sveltekit, component-library, refactor]

requires:
  - phase: 51-02
    provides: "the relocated public route tree (app/src/routes/arguments/**) that Task 1's import updates target"
provides:
  - "app/src/lib/public/ (5 components: ChatBubble, StageDirection, SectionRail, SpeakerPopover, MobileNavBar)"
  - "app/src/lib/admin/ (9 components: AdminSubNav, ArgumentDetailsCard, CopyableExtractedValue, CreatePersonPopover, DocketPillInput, FailedStepGuidance, ResolveCard, RunStatusCard, StatCard)"
  - "app/src/lib/README.md — the placement rule for all four lib/ locations"
  - "app/src/lib/components/ slimmed to TopNav.svelte only (cross-surface app shell)"
affects: [51-06, 51-07, 51-08, 51-09, 51-10]

actuals:
  tokens: 3218
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "lib/ directory split by render surface (primitives/public/admin/components) — see app/src/lib/README.md"

key-files:
  created:
    - app/src/lib/README.md
  modified:
    - app/src/routes/arguments/[slug]/+page.svelte
    - app/src/routes/admin/+layout.svelte
    - app/src/routes/admin/+page.svelte
    - app/src/routes/admin/arguments/[id]/+page.svelte
    - app/src/routes/admin/people/[id]/+page.svelte
    - app/src/routes/admin/pipeline/+page.svelte
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte
    - app/tests/fixtures/copyable-extracted-value-main.ts

key-decisions:
  - "TopNav.svelte stays in lib/components/ as the sole cross-surface app-shell component (imported by both routes/+layout.svelte and routes/admin/+layout.svelte); MobileNavBar.svelte moved to lib/public/ despite its cross-surface-sounding name, confirmed by grep to be imported only by the transcript page — both facts confirmed against the live import graph, not assumed from the plan text."

requirements-completed: []  # DS-02 stays blocked — shared with sibling plan 51-06, which has not yet produced its SUMMARY (requirements.ready-ids confirms 0/1 ready)

coverage:
  - id: D1
    description: "The 14 components split into lib/public/ (5) and lib/admin/ (9), with lib/components/ slimmed to the sole cross-surface component (TopNav.svelte), and every import site across the app updated to match."
    verification:
      - kind: other
        ref: "npm --prefix app run check (0 errors, 809 files)"
        status: pass
      - kind: other
        ref: "npm --prefix app run build (green)"
        status: pass
      - kind: other
        ref: "grep -rnE \"from '\\$lib/components/\" app/src | grep -v TopNav (no matches)"
        status: pass
      - kind: other
        ref: "grep -rn 'lib/components/' api pipeline tests app/tests app/scripts (no matches)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The relocation is behaviour-neutral: every changed line across the two move commits is an import path, git history follows every rename, and the full backend suite plus the frontend build stay green."
    verification:
      - kind: other
        ref: "git diff -M HEAD~2 -- app/src ':!app/src/lib/README.md' | grep '^[+-]' | grep -v '^[+-][+-]' | grep -vc \"lib/\\(public\\|admin\\|components\\)/\" == 0"
        status: pass
      - kind: unit
        ref: "pytest api/tests tests pipeline/tests -q — 1378 passed, 5 xfailed, 0 failed"
        status: pass
      - kind: other
        ref: "git log --follow --oneline -- app/src/lib/public/ChatBubble.svelte (11 lines, history followed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The public transcript page and the admin dashboard render unchanged after the move (real-browser visual check)."
    verification: []
    human_judgment: true
    rationale: "No Chromium/Edge binary in this sandbox — the same pre-existing constraint plans 51-02 and 51-03 both hit. All four app/tests/*.browser.test.mjs fail-closed on the missing binary rather than exercising a real page. npm run check and npm run build both being green is the strongest available signal for an import-only rename (an unresolved import fails the build), but rendered output was not observed. Logged to WINDOWS.md as an unrun-verify item."

duration: 45min
completed: 2026-08-28
status: complete
---

# Phase 51 Plan 05: Component Directory Split Summary

**Split the flat `app/src/lib/components/` (15 files) into `lib/public/` (5) and `lib/admin/` (9), with `lib/components/` slimmed to the one genuinely cross-surface component (`TopNav.svelte`), as a pure git-mv rename with zero behavioural change.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-08-28T15:35:00Z
- **Completed:** 2026-08-28T16:20:00Z
- **Tasks:** 3
- **Files modified:** 23 (14 moved + README created + 8 import-line edits)

## Accomplishments
- `app/src/lib/README.md` written first, stating the placement rule for all four `lib/` locations (`primitives/`, `public/`, `admin/`, `components/`) plus the Figma page-to-directory correspondence from D-06.
- Five public components (`ChatBubble`, `StageDirection`, `SectionRail`, `SpeakerPopover`, `MobileNavBar`) moved via `git mv` into `app/src/lib/public/`; the transcript page's five imports updated to match.
- Nine admin components (`AdminSubNav`, `ArgumentDetailsCard`, `CopyableExtractedValue`, `CreatePersonPopover`, `DocketPillInput`, `FailedStepGuidance`, `ResolveCard`, `RunStatusCard`, `StatCard`) moved via `git mv` into `app/src/lib/admin/`; the six admin route/layout files and the three intra-set sibling imports (`ResolveCard`→`CopyableExtractedValue`/`CreatePersonPopover`, `ArgumentDetailsCard`→`CopyableExtractedValue`/`DocketPillInput`, `DocketPillInput`→`CopyableExtractedValue`) all updated.
- `app/src/lib/components/` now holds exactly `TopNav.svelte` — confirmed cross-surface (imported by both `routes/+layout.svelte` and `routes/admin/+layout.svelte`) by grep before the move, not assumed.
- Mechanically proved the move is behaviour-neutral: every added/removed line across the two move commits is an import path (`git diff -M HEAD~2` filtered to non-`lib/{public,admin,components}/` lines returns 0).
- Full verification: `npm --prefix app run check` (0 errors), `npm --prefix app run build` (green), `pytest api/tests tests pipeline/tests -q` (1378 passed, 5 xfailed, 0 failed — matches the pre-plan baseline exactly).

## Task Commits

Each task was committed atomically:

1. **Task 1: Establish the placement rule and move the public components** - `37569fe77` (feat)
2. **Task 2: Move the admin components** - `6fed9adc2` (feat)
3. **Task 3: Prove the move was behaviour-neutral** - no commit (verification-only task, no files modified)

**Plan metadata:** committed alongside this SUMMARY.

## Files Created/Modified
- `app/src/lib/README.md` - the four-location placement rule + Figma correspondence
- `app/src/lib/public/{ChatBubble,StageDirection,SectionRail,SpeakerPopover,MobileNavBar}.svelte` - moved from `lib/components/`, no content change beyond sibling import paths (none of these five import each other)
- `app/src/lib/admin/{AdminSubNav,ArgumentDetailsCard,CopyableExtractedValue,CreatePersonPopover,DocketPillInput,FailedStepGuidance,ResolveCard,RunStatusCard,StatCard}.svelte` - moved from `lib/components/`; `ResolveCard`, `ArgumentDetailsCard`, `DocketPillInput` each had 1-2 sibling import lines updated to `$lib/admin/`
- `app/src/routes/arguments/[slug]/+page.svelte` - 5 import lines updated to `$lib/public/`
- `app/src/routes/admin/+layout.svelte` - `AdminSubNav` import updated to `$lib/admin/`; `TopNav` import unchanged (stays in `lib/components/`)
- `app/src/routes/admin/+page.svelte` - `StatCard` import updated
- `app/src/routes/admin/arguments/[id]/+page.svelte` - `ArgumentDetailsCard`, `CopyableExtractedValue` imports updated
- `app/src/routes/admin/people/[id]/+page.svelte` - `CopyableExtractedValue` import updated
- `app/src/routes/admin/pipeline/+page.svelte` - `DocketPillInput` import updated
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` - 5 import lines updated
- `app/tests/fixtures/copyable-extracted-value-main.ts` - a stale `lib/components/CopyableExtractedValue.svelte` reference found by the plan's required whole-repo grep, updated to `lib/admin/`

## Moved Files (old path -> new path)

| # | Old path | New path |
|---|---|---|
| 1 | `app/src/lib/components/ChatBubble.svelte` | `app/src/lib/public/ChatBubble.svelte` |
| 2 | `app/src/lib/components/StageDirection.svelte` | `app/src/lib/public/StageDirection.svelte` |
| 3 | `app/src/lib/components/SectionRail.svelte` | `app/src/lib/public/SectionRail.svelte` |
| 4 | `app/src/lib/components/SpeakerPopover.svelte` | `app/src/lib/public/SpeakerPopover.svelte` |
| 5 | `app/src/lib/components/MobileNavBar.svelte` | `app/src/lib/public/MobileNavBar.svelte` |
| 6 | `app/src/lib/components/AdminSubNav.svelte` | `app/src/lib/admin/AdminSubNav.svelte` |
| 7 | `app/src/lib/components/ArgumentDetailsCard.svelte` | `app/src/lib/admin/ArgumentDetailsCard.svelte` |
| 8 | `app/src/lib/components/CopyableExtractedValue.svelte` | `app/src/lib/admin/CopyableExtractedValue.svelte` |
| 9 | `app/src/lib/components/CreatePersonPopover.svelte` | `app/src/lib/admin/CreatePersonPopover.svelte` |
| 10 | `app/src/lib/components/DocketPillInput.svelte` | `app/src/lib/admin/DocketPillInput.svelte` |
| 11 | `app/src/lib/components/FailedStepGuidance.svelte` | `app/src/lib/admin/FailedStepGuidance.svelte` |
| 12 | `app/src/lib/components/ResolveCard.svelte` | `app/src/lib/admin/ResolveCard.svelte` |
| 13 | `app/src/lib/components/RunStatusCard.svelte` | `app/src/lib/admin/RunStatusCard.svelte` |
| 14 | `app/src/lib/components/StatCard.svelte` | `app/src/lib/admin/StatCard.svelte` |
| — | `app/src/lib/components/TopNav.svelte` | unchanged — sole cross-surface app-shell component |

`git diff -M --stat` confirms all 14 as renames with 100% (or near-100%, for the three files with a sibling-import-line edit) similarity when the diff pathspec spans both the source and destination directories.

## Decisions Made
- **`MobileNavBar.svelte` moved to `lib/public/`, not `lib/components/`**, despite the name suggesting cross-surface reach — confirmed by grep that its only import site is the public transcript page (plan's flagged assumption, verified true).
- **`TopNav.svelte` is the only component retained in `lib/components/`** — confirmed by grep that it is the only component imported by both `routes/+layout.svelte` and `routes/admin/+layout.svelte` (plan's flagged assumption, verified true; no second cross-surface component was found).
- **DS-02 not marked complete** — `requirements.ready-ids` reports it blocked because a sibling plan in this phase (51-06, which creates `lib/primitives/`) also declares DS-02 and has not yet produced a SUMMARY. Correct per the shared-ID gate (#2388); DS-02 will mark complete once 51-06 finishes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale `lib/components/CopyableExtractedValue.svelte` reference in a test fixture**
- **Found during:** Task 2 (the plan's own required whole-repository grep, scoped beyond `app/src`)
- **Issue:** `app/tests/fixtures/copyable-extracted-value-main.ts` imported `CopyableExtractedValue` from its pre-move path; left unfixed, this fixture (used by `app/tests/copyable-extracted-value.browser.test.mjs`) would fail to resolve once the component moved.
- **Fix:** Updated the one import line to `../../src/lib/admin/CopyableExtractedValue.svelte`.
- **Files modified:** `app/tests/fixtures/copyable-extracted-value-main.ts`
- **Verification:** `grep -rn 'lib/components/' api pipeline tests app/tests app/scripts` returns no matches after the fix; `npm --prefix app run build` stays green.
- **Committed in:** `6fed9adc2` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix, in-scope per the task's own explicit instruction to grep and fix live references outside `app/src`)
**Impact on plan:** No scope creep — the plan's Task 2 action text explicitly requires this whole-repository grep and fix. Zero behavioural change to the fixture's own test logic; only the import path changed.

## Issues Encountered
- The plan's literal Task-1 acceptance-criteria command, `git diff -M --stat HEAD~1 -- app/src/lib/public`, reports the five moved files as full-file adds rather than renames, because restricting the diff pathspec to only the destination directory hides the delete side of the rename from git's `-M` detector. Widening the pathspec to `app/src/lib` (or omitting the pathspec) correctly shows all files as renames with 0 changed lines. This is a verification-command scoping quirk in the plan text, not a defect in the move itself — `git log --follow --oneline` (11 lines, >1) and the commit's own "rename ... (100%)" output both independently confirm history was preserved. No code or process change needed; noting it here so a future reader isn't confused by the literal command.
- All four `app/tests/*.browser.test.mjs` real-browser tests could not run to completion: no Chromium/Edge binary exists in this sandbox (pre-existing constraint, also hit by plans 51-02 and 51-03). `copyable-extracted-value.browser.test.mjs` and `case-required-recovery.browser.test.mjs` each fail-closed with "Microsoft Edge or Google Chrome must be installed"; `tenure-public-title.browser.test.mjs` fails the same way. `tenure-office.browser.test.mjs` ran 9/11 non-browser-dependent sub-tests successfully (all pass) with 2 pre-existing, browser-independent failures against a stale assertion predating Phase 38 (last touched Phase 37, per this plan's own hazard notes) — unrelated to this plan's changes.
- `gsd-tools windows append` failed for all four attempted ledger entries (the deviation fix + three unrun-verify browser items) with `Ledger counts disagree with entries: frontmatter open/waived/fixed/total=23/0/8/31 but entries yield 21/0/10/31` — a pre-existing `.planning/WINDOWS.md` frontmatter/entries count mismatch unrelated to this plan's changes (last touched 2026-08-26, before this plan started). Per protocol the ledger is best-effort/optional; not fixed here (out of this plan's scope) but recorded so a future ledger-repair pass has the pointer.

## Threat Flags

None — this plan's own threat register (T-51-05-01/02/03, T-51-SC) was fully addressed: placement was decided by actual import sites (grep-verified, not name-guessed), `git mv` preserved history so the diff is auditable, the build/check/test gates all ran, and no package was installed.

## Next Phase Readiness
- `app/src/lib/public/`, `app/src/lib/admin/`, and the slimmed `app/src/lib/components/` are all in place with unambiguous ownership for plan 51-09's inline-style-to-token conversion sweep.
- `app/src/lib/primitives/` does not exist yet — that is plan 51-06's job, per this phase's wave ordering. This plan did not create or touch it.
- No Tailwind utility classes were found on any of the 14 moved components (`grep -lE` for common utility-class patterns across `lib/public/*.svelte lib/admin/*.svelte` returns no matches) — nothing to flag forward to plan 51-09 on that front.
- Blocker for a human: the four real-browser tests and the visual "renders unchanged" backstop truth were not observed this session (no Chromium binary). `npm run check` + `npm run build` both green is the strongest available proxy for an import-only rename.

## Self-Check: PASSED

- `app/src/lib/README.md` — FOUND
- `app/src/lib/public/ChatBubble.svelte` — FOUND
- `app/src/lib/admin/ResolveCard.svelte` — FOUND
- `app/src/lib/components/TopNav.svelte` — FOUND
- Commit `37569fe77` (Task 1) — FOUND in `git log --oneline --all`
- Commit `6fed9adc2` (Task 2) — FOUND in `git log --oneline --all`

---
*Phase: 51-design-system-noun-alignment*
*Completed: 2026-08-28*
