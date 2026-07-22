---
phase: 38-full-name-vs-name-parts-rethink
plan: "05"
subsystem: ui
tags: [svelte5, sveltekit, clipboard, extracted-value, docket-pill, accessibility]

# Dependency graph
requires:
  - phase: 36-click-to-copy-extracted-values-design-pattern
    provides: "CopyableExtractedValue clipboard state machine, disabled N/A, accessibility contract"
provides:
  - "CopyableExtractedValue optional stacked two-line provenance mode (confidence + raw) layered on the Phase 36 primitive"
  - "DocketPillInput typed per-pill provenance support ({value, confidence, raw}) alongside backward-compatible plain-string pills"
  - "ResolveCard title hint, argument-editor speaker title hint, and pipeline job detail case name/argued date/docket/question number wired to the stacked contract"
  - "Static source-contract regression suite (api/tests/test_phase38_extracted_value_contract.py) for the Svelte-only extracted-value/docket-pill contract"
affects: [38-06-people-editor-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Optional-prop stacked mode: a shared component gains a richer rendering path gated on whether the caller passes new optional props at all (even null), guaranteeing every existing caller that omits them is byte-for-byte unaffected"
    - "Data-boundary confidence fallback: legacy fields with no independently stored confidence/raw are adapted at the Svelte call site with an explicit qualitative fallback (Medium) and the field's own extracted text as its raw source, never a fabricated percentage"

key-files:
  created:
    - api/tests/test_phase38_extracted_value_contract.py
  modified:
    - app/src/lib/components/CopyableExtractedValue.svelte
    - app/src/lib/components/DocketPillInput.svelte
    - app/src/lib/components/ResolveCard.svelte
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte
    - app/src/routes/admin/arguments/[id]/+page.svelte

key-decisions:
  - "Stacked provenance mode activates only when a caller supplies confidence and/or raw (even null); omitting both keeps every current value-only/pill consumer (ArgumentDetailsCard.svelte, pipeline list/create page) byte-for-byte unchanged and out of this plan's scope"
  - "Legacy metadata with no independently stored raw/confidence (title_hint, case_name, argued_date, primary_docket, question_number) is adapted at the Svelte call-site boundary: confidence=\"Medium\" as an explicit qualitative fallback, raw = the same extracted field the interpreted value came from (argued date is the one field where raw genuinely differs -- exact ISO string vs. formatted display)"
  - "DocketPillInput's Docket Pill provenance states are additive: only pills whose entry carries confidence/raw route through the shared CopyableExtractedValue primitive; plain-string entries (100% of current real callers) keep the pre-existing plain-span markup exactly, so ArgumentDetailsCard.svelte and the pipeline create-job page remain unaffected without being touched"
  - "copyLabel strings for the three converted consumers are unchanged (\"Copy title\", \"Copy case name\", etc.) rather than adopting the \"Copy extracted {field}\" phrasing from 38-UI-SPEC's copywriting table -- that phrasing is reserved for the new name-part fields shipped in Plan 38-06, not these pre-existing fields"

patterns-established:
  - "Static Python source-contract tests (Path.read_text + substring/regex assertions) are the established way to regression-test Svelte component contracts when no frontend test harness exists -- following test_admin_jobs_phase35_frontend.py precedent"

requirements-completed: [PEOPLE-09]

coverage:
  - id: D1
    description: "CopyableExtractedValue gains an optional two-line stacked provenance mode (Extracted: {value} / {Band} confidence · Raw: {raw}) while every existing value-only/pill consumer renders unchanged"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_phase38_extracted_value_contract.py (10 tests covering stacked-mode gating, confidence validation/fallback, provenance-line omission, legacy-branch preservation, no {@html}, clipboard-value-only, generation invalidation)"
        status: pass
      - kind: other
        ref: "npm run check (svelte-check --tsconfig ./tsconfig.json) -- 0 errors"
        status: pass
    human_judgment: true
    rationale: "The plan's own <verification> section requires browser UAT (narrow/wide widths, keyboard copy, N/A, success/error, mixed confidence, long raw text) against 38-FIGMA.md; no browser tool is available in this execution environment, so visual/interaction confirmation must come from a human."
  - id: D2
    description: "DocketPillInput accepts optional per-pill provenance ({value, confidence, raw}) rendered through the shared primitive with editable-only remove, while 100% of current plain-string callers keep byte-identical markup/behavior"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_phase38_extracted_value_contract.py (5 tests covering backward-compatible types, provenance-map construction, shared-primitive usage, editable-only remove, preserved form serialization/public API)"
        status: pass
      - kind: other
        ref: "npm run check -- 0 errors"
        status: pass
    human_judgment: true
    rationale: "38-FIGMA.md component set 3:140 / review sheet 3:2 define visual states (mixed-confidence groups, long-raw wrapping, copy/copied) that require browser/visual comparison against the approved Figma component; not verifiable via static source contract alone."
  - id: D3
    description: "ResolveCard title hint, argument-editor speaker title hint, and pipeline job detail case name/argued date/docket/question number all pass interpreted value + confidence + exact raw source to the shared component, replacing the old caller-owned Extracted: prefix"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_phase38_extracted_value_contract.py (6 tests enumerating every CopyableExtractedValue call site in the three converted files, asserting confidence+raw presence, exact-ISO raw for argued date, and no fabricated percentages)"
        status: pass
      - kind: other
        ref: "npm run check -- 0 errors"
        status: pass
    human_judgment: true
    rationale: "Visual placement of the new two-line stacked hint inside the Resolve table, argument editor, and pipeline job detail cards requires human confirmation the layout reads correctly at both narrow and wide widths, per the plan's browser-UAT verification requirement."

duration: 40min
completed: 2026-07-22
status: complete
---

# Phase 38 Plan 05: Global Extracted-Value Evolution + Docket Pill Provenance Summary

**Extended the Phase 36 `CopyableExtractedValue` component with an optional two-line stacked provenance mode (interpreted value / confidence / exact raw source) and wired it into `DocketPillInput`, `ResolveCard`, the pipeline job detail page, and the argument editor's speaker title hint, without regressing any existing value-only/pill consumer.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 3 completed (2 TDD, 1 non-TDD)
- **Files modified:** 5 (2 shared components, 3 consumers) + 1 new test file

## Accomplishments

- `CopyableExtractedValue.svelte` now renders `Extracted: {value}` / `{High|Medium|Low} confidence · Raw: {raw}` whenever a caller supplies `confidence` and/or `raw`, while every consumer that omits both props (`ArgumentDetailsCard.svelte`, the pipeline create-job page) keeps rendering exactly as before Phase 38
- Confidence is runtime-validated against `High`/`Medium`/`Low` only, with a `Low` fallback for empty interpretations (per 38-UI-SPEC's raw-without-interpretation rule) and a `Medium` fallback for any unrecognized input — never a fabricated percentage
- `DocketPillInput.svelte` accepts either plain strings (unchanged) or a typed `{value, confidence, raw}` entry per pill; provenance-bearing pills route through the shared primitive (stacked confidence/raw + copy) inside the pill's own chrome, while remove stays editable-mode-only for both kinds
- `ResolveCard.svelte`'s title hint, the argument editor's speaker title hint, and the pipeline job detail page's case name/argued date/docket/question number readouts all now pass interpreted value + confidence + exact raw source — argued date is the one field where raw (exact ISO string) genuinely differs from the formatted display value
- A new static source-contract test suite (`api/tests/test_phase38_extracted_value_contract.py`, 21 tests) locks the whole contract using the established Phase 35 pattern (`Path.read_text` + substring/regex assertions), since no Svelte component test harness exists in this repo

## Task Commits

Each task was committed atomically, with Tasks 1 and 2 following the full RED→GREEN TDD cycle (RED confirmed by temporarily restoring each original file and re-running pytest before restoring the new implementation):

1. **Task 1: Extend the copy primitive with stacked provenance**
   - `160cd080` test(38-05): add failing stacked-provenance contract for CopyableExtractedValue (RED — 8/10 new assertions failed against the pre-Phase-38 component)
   - `9dd2409d` feat(38-05): extend CopyableExtractedValue with stacked provenance rendering (GREEN — 10/10 pass)
2. **Task 2: Implement approved Docket Pill provenance states**
   - `5324a739` test(38-05): add failing Docket Pill provenance contract for DocketPillInput (RED — 4/15 new assertions failed against the pre-Phase-38 component)
   - `1cf0a315` feat(38-05): implement Docket Pill provenance states (GREEN — 15/15 pass)
3. **Task 3: Convert every current editable-destination consumer** (auto, no TDD gate)
   - `39b90557` feat(38-05): wire stacked extracted-value contract into resolve/pipeline/argument consumers (21/21 pass)
   - `f7a7521f` fix(38-05): normalize line endings back to LF after Task 3 edit (Rule 1 self-fix — see Deviations)

## Files Created/Modified

- `app/src/lib/components/CopyableExtractedValue.svelte` — optional `confidence`/`raw` props gate a two-line stacked render path; legacy single-line path untouched
- `app/src/lib/components/DocketPillInput.svelte` — `DocketPillValue = string | DocketProvenance` union; provenance pills render via the shared primitive, plain-string pills keep exact legacy markup
- `app/src/lib/components/ResolveCard.svelte` — title hint now passes `confidence="Medium" raw={row.title_hint}`
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — case name/argued date/docket/question number readouts pass confidence + raw (argued date's raw is the exact ISO string, not the formatted display)
- `app/src/routes/admin/arguments/[id]/+page.svelte` — speaker title hint now passes `confidence="Medium" raw={speaker.title_hint}`
- `api/tests/test_phase38_extracted_value_contract.py` (new) — 21 static source-contract tests across all five files above

## Decisions Made

See `key-decisions` in frontmatter. In summary: stacked mode is strictly opt-in per caller (prop presence, not a global flag); legacy fields without independently stored raw/confidence get an explicit "Medium" fallback and reuse their own extracted text as raw (never a fabricated percentage); Docket Pill provenance is purely additive so no currently-untouched consumer file needed modification; copyLabel strings for these pre-existing fields are unchanged (the "Copy extracted {field}" phrasing is reserved for Plan 38-06's new name-part fields).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a self-introduced CRLF line-ending regression**
- **Found during:** Task 3, immediately after committing `39b90557`
- **Issue:** Editing `ResolveCard.svelte` and `app/src/routes/admin/arguments/[id]/+page.svelte` via the Edit tool round-tripped their line endings from LF to CRLF, producing a ~1,400-line noise diff in each file even though the actual content change was a few lines. Confirmed via `git diff` against the last real pre-session commit that no textual content was lost or altered beyond the intended edit — purely a line-ending representation change.
- **Fix:** Normalized both files back to LF (matching every other file this plan touches and the majority convention in `app/src/`) via a direct byte-level `\r\n` → `\n` replace, re-verified the diff against the pre-Task-3 commit showed only the intended content change, and re-ran the full contract test suite + `npm run check` to confirm no regression.
- **Files modified:** `app/src/lib/components/ResolveCard.svelte`, `app/src/routes/admin/arguments/[id]/+page.svelte`
- **Verification:** `api/tests/test_phase38_extracted_value_contract.py` (21/21 pass), `npm run check` (0 errors, unchanged from before the fix)
- **Committed in:** `f7a7521f`

---

**Total deviations:** 1 auto-fixed (Rule 1 — self-introduced bug, not present in the plan or pre-existing codebase)
**Impact on plan:** No scope creep; purely a whitespace-representation correction with zero textual content change beyond this plan's own intended edits.

## Issues Encountered

- **No Python test runner available in the sandboxed execution environment.** The repository's committed `.venv` is Windows-only (`Scripts/python.exe`, no Linux `bin/`), and the system Python 3 has no `pip` module and no `venv` package installable without sudo. Worked around by provisioning an ephemeral ad-hoc Python 3.12 environment via `uv venv` (ephemeral, not part of the repo/commits) and installing only `pytest`+`pytest-asyncio` — sufficient because `api/tests/test_phase38_extracted_value_contract.py` is a pure static source-contract test with no FastAPI/SQLAlchemy/DB imports, and `api/tests/conftest.py`'s only autouse fixture no-ops when `DATABASE_URL` is unset. All 21 contract tests ran and passed against this ephemeral interpreter; the RED/GREEN cycle for Tasks 1 and 2 was verified the same way.
- **`npm run check` initially failed with `Cannot find module @rollup/rollup-linux-x64-gnu`** — a known npm optional-dependency bug (linked directly in the error message) where a lockfile generated on Windows omits the Linux-native optional binary from a fresh `node_modules` install on this platform. Confirmed the package was already recorded in `app/package-lock.json` (not a new/unknown dependency) and ran `npm install --no-save` inside `app/`, which restored the missing platform binary without modifying `package.json` or `package-lock.json` (confirmed via `git status`/`git diff` showing no changes to either file). `npm run check` then completed cleanly: 802 files, 0 errors, 19 pre-existing warnings (the same `state_referenced_locally`/a11y warning classes already present across `ArgumentDetailsCard.svelte`, `ChatBubble.svelte`, `SpeakerPopover.svelte`, and several `admin/people`/`admin/pipeline` pages before this plan — one new instance of the same accepted pattern appears in `DocketPillInput.svelte` for the same "capture prop into `$state` once at mount" idiom already used one line above it).
- Both of the above are execution-environment gaps (this sandbox differs from the Windows/PowerShell environment the plan's `<verify>` commands were authored for), not defects in the plan or the implementation. No app dependency, lockfile, or production code was changed to work around them.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The shared `CopyableExtractedValue` and `DocketPillInput` components now expose the full Phase 38 stacked-provenance contract (optional `confidence`/`raw` props; typed per-pill provenance) that Plan 38-06 (people editor UI) needs for per-name-part extracted hints — 38-06 can pass `confidence`/`raw` directly without any further component changes.
- **Browser/visual UAT is still required** for all three deliverables in this plan (per the plan's own `<verification>` section: narrow/wide widths, keyboard copy, N/A, success/error, mixed confidence, long raw text against `38-FIGMA.md`) — no browser tool was available in this execution to perform that confirmation. See `coverage` entries D1–D3 (`human_judgment: true`) in this file's frontmatter.
- `ArgumentDetailsCard.svelte` and the pipeline create-job page's docket input remain on the pre-Phase-38 (non-stacked) `CopyableExtractedValue`/`DocketPillInput` usage — this is consistent with this plan's and Phase 38's own file scope (neither file appears in any 38-01 through 38-06 plan's `files_modified`), not an oversight, but should be confirmed as an intentional scope boundary rather than a gap when Phase 38 is verified as a whole.

## Self-Check: PASSED

All 5 modified files, the new test file, and this SUMMARY.md exist on disk. All 6 task commits (`160cd080`, `9dd2409d`, `5324a739`, `1cf0a315`, `39b90557`, `f7a7521f`) are present in `git log --oneline --all`.

---
*Phase: 38-full-name-vs-name-parts-rethink*
*Completed: 2026-07-22*
