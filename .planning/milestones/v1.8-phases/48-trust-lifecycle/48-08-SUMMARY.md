---
phase: 48-trust-lifecycle
plan: 08
subsystem: ui
tags: [sveltekit, svelte5, form-actions, trust-tier, publish-gate, static-contract]

requires:
  - phase: 48-trust-lifecycle
    plan: 07
    provides: "publish_argument's two-gate publish, the structured 422 codes uncertain_tier_blocked/blank_override_reason, and trust_tier/StatusLogEntry audit fields on the admin detail contract"
provides:
  - "The admin argument-detail publish action branches on the server's structured 422 detail (uncertain_tier_blocked / blank_override_reason / plain-string) instead of returning one generic error"
  - "A block-reason panel on the Status card showing the tier and one actionable, count-bearing sentence per blocker code (blockerSentence), with an override_reason textarea that re-submits ?/publish"
  - "Status history renders override_reason and trust_tier_at_transition for any log entry that carries them"
  - "The candidate born state gets its own badge label instead of falling through to the retired 'Pipeline' one"
  - "api/tests/test_phase48_publish_override_ui_contract.py — a static source contract locking all of the above (Node-free, always runs)"
affects: ["49 (review queue) — inherits the working publishBlocked/blockers/blockMessage payload shape and blockerSentence pattern for its own UI"]

actuals:
  tokens: 5592
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "The SvelteKit server action parses the 422 body's detail field and branches on detail.code; it never re-implements a gate, only relays the server's decision (mirrors the codebase's standing 'client disabled state is defense-in-depth only' rule from D-17)"
    - "A plain-string detail (the non-overridable resolve gate, or the already-published guard) takes the existing form?.error path with no publishBlocked flag, so the page structurally cannot offer an override field for a gate that doesn't accept one"

key-files:
  created:
    - api/tests/test_phase48_publish_override_ui_contract.py
  modified:
    - app/src/routes/admin/arguments/[id]/+page.server.ts
    - app/src/routes/admin/arguments/[id]/+page.svelte

key-decisions:
  - "Reused the sibling test_phase45_popover_boxmodel_contract.py / test_phase39_popover_ui_contract.py static-source-contract shape (file read + regex assertions, ROOT/path constants, no Node runtime) since this repo has no frontend test framework and Node is not guaranteed to be on PATH in every pytest invocation."

requirements-completed: [TRUST-04, TRUST-05]

coverage:
  - id: D1
    description: "A blocked publish (uncertain_tier_blocked) renders the tier and one human sentence per blocker code with its count via blockerSentence, not a bare tier name."
    requirement: "TRUST-04"
    verification:
      - kind: other
        ref: "api/tests/test_phase48_publish_override_ui_contract.py (blockerSentence maps all four codes; publishBlocked panel assertions)"
        status: pass
      - kind: manual_procedural
        ref: "Operator browser walkthrough step 4 (approved)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The override_reason textarea re-submits the same ?/publish action; a whitespace-only reason is rejected server-side and rendered distinctly from the original block; a real reason publishes and is not sticky across a subsequent unpublish/republish."
    requirement: "TRUST-05"
    verification:
      - kind: other
        ref: "api/tests/test_phase48_publish_override_ui_contract.py (override_reason textarea inside a ?/publish form guarded by form?.publishBlocked)"
        status: pass
      - kind: manual_procedural
        ref: "Operator browser walkthrough steps 5-7 (approved)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The non-overridable resolved_at gate (D-14) renders a message with NO override field offered, distinguishing it from the overridable trust gate."
    requirement: "TRUST-04"
    verification:
      - kind: other
        ref: "api/tests/test_phase48_publish_override_ui_contract.py (plain-string detail branch sets no publishBlocked / no reason field)"
        status: pass
      - kind: manual_procedural
        ref: "unknown"
        status: unknown
    human_judgment: true
    rationale: "Operator browser walkthrough step 8 was NOT executed — no argument whose resolve step never ran was available in the seeded fixture set. The D-14 must-have is satisfied in code and locked by the static contract test (D3's `other` entry), but the live-browser rendering of this exact branch is unverified. Tracked as WINDOWS.md entry #8 (kind=unrun-verify, status=open AS OF THIS WRITING). Do not auto-pass this row from the `other` evidence alone — a human must confirm once a resolve-incomplete fixture exists. CORRECTION 2026-08-21: WINDOWS.md entry #8 was marked fixed on 2026-08-20 and the check itself was confirmed live at 48-UAT.md test 6 — the operator forced the resolve-incomplete state via manual SQL and verified both gate branches render as specified. The status=open reference above is stale; the deliverable is verified."
  - id: D4
    description: "The candidate born state renders its own badge label instead of falling through to the retired 'Pipeline' label."
    verification:
      - kind: other
        ref: "api/tests/test_phase48_publish_override_ui_contract.py (no retired 'pipeline' literal remains in +page.svelte)"
        status: pass
    human_judgment: false
  - id: D5
    description: "The Publish control's visibility rule (draft or unpublished only) is unchanged, and no new component/screen/design-system import was introduced."
    verification:
      - kind: other
        ref: "api/tests/test_phase48_publish_override_ui_contract.py (visibility-rule grep, component-import-count grep)"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-08-19
status: complete
---

# Phase 48 Plan 08: Publish Block-Reason Panel and Override Prompt Summary

**A branching SvelteKit publish action that surfaces the server's structured block reason (tier + per-blocker counts) and relays a deliberate operator override, with a static contract test locking the behavior since this repo has no frontend test framework.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3/3 complete
- **Files modified:** 3 (2 modified, 1 created)

## Accomplishments

- `app/src/routes/admin/arguments/[id]/+page.server.ts`'s `publish` action now reads `override_reason` from the submitted form data, posts it as a JSON body only when non-empty (submitting the untrimmed value so the server's `.strip()` stays the single authority per D-17), and parses the 422 response's `detail` field to branch three ways: `uncertain_tier_blocked` → `fail(422, { publishBlocked: true, trustTier, blockers, blockMessage })`; `blank_override_reason` → the same plus `overrideReasonRequired: true`; a plain-string `detail` (the non-overridable resolve gate or the already-published guard) → `fail(422, { error: detail })` with no `publishBlocked` flag, so no override field is ever offered for a gate that doesn't accept one. The module's local `ArgumentDetail`/`StatusLogEntry` types gained `trust_tier`/`override_reason`/`trust_tier_at_transition`, and a `Blocker` type was added.
- `app/src/routes/admin/arguments/[id]/+page.svelte` gained a `blockerSentence(code, count)` helper mapping all four server-side blocker codes (`unresolved_utterance_speaker`, `unresolved_participant`, `llm_corrective_utterance`, `no_constituents`) to an operator-readable, count-bearing sentence, with a fallback for any future unrecognized code. A block panel renders inside the Status card when `form?.publishBlocked`, showing the tier, the server's own message, one sentence per blocker, a distinct message when `form?.overrideReasonRequired`, and a second `?/publish` form with a `required` (defense-in-depth only) `override_reason` textarea. The Status history list now renders `override_reason`/`trust_tier_at_transition` for any log entry carrying them. `badgeStyle`/`badgeLabel` gained an explicit `candidate` branch (both `?? 'pipeline'` fallbacks became `?? 'candidate'`), replacing the retired born-state literal.
- `api/tests/test_phase48_publish_override_ui_contract.py` (new, 12 tests) locks all of the above via static source assertions (file read + regex, mirroring `test_phase45_popover_boxmodel_contract.py`'s pattern) — no Node runtime required, so the test never skips.
- The publish visibility rule (`status === 'draft' || status === 'unpublished'`) and the Danger Zone/unpublish form were left untouched, per D-02 and the plan's prohibitions. No new component import or design-system dependency was added.

## Task Commits

Each task was committed atomically:

1. **Task 1: Branch the publish action on the structured 422 and relay the override** - `cb5c86802` (feat)
2. **Task 2: Block-reason panel and override prompt on the Status card** - `be308e3d2` (feat)
3. **Task 3: Contract test, then operator verification in a browser** - `9e9ee02d6` (test)

**Plan metadata:** (this commit) — `docs(48-08): complete plan`

## Files Created/Modified

- `app/src/routes/admin/arguments/[id]/+page.server.ts` - Branching publish action, extended local types (Task 1)
- `app/src/routes/admin/arguments/[id]/+page.svelte` - Block panel, `blockerSentence`, Status history rendering, `candidate` badge branch (Task 2)
- `api/tests/test_phase48_publish_override_ui_contract.py` - Static source contract, 12 tests, 0 skipped (Task 3)

## Decisions Made

- Followed the plan's static-source-contract pattern (established by `test_phase45_popover_boxmodel_contract.py` / `test_phase39_popover_ui_contract.py`) rather than introducing a Node-based frontend test runner — consistent with the flagged assumption that `npm run check` requires `node` on PATH, which is not guaranteed for every pytest invocation.
- No architectural deviations; implementation followed the plan's task actions as written.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None during the automated tasks. See "Verification" below for the one operator-verification gap.

## Verification

- `./.venv/bin/python -m pytest api/tests/test_phase48_publish_override_ui_contract.py -q` — **12 passed, 0 skipped.**
- `cd app && npm run check` — **0 errors, 36 warnings** (all pre-existing across the codebase; none newly introduced by this plan's edits beyond one pre-existing warning at `+page.svelte:119:5` that predates this plan).
- `./.venv/bin/python -m pytest api/tests pipeline/tests tests -q` — **1178 passed, 5 xfailed, 0 failed** (up from the 1166 passed / 5 xfailed baseline this plan inherited from 48-07 — the 12 new contract tests account for the delta; the 5 xfailed are the pre-existing, unrelated Phase 31 stubs).

### Operator browser walkthrough (Task 3 checkpoint) — **APPROVED, with one gap**

Steps 1-7 of the 8-step walkthrough were executed live by the operator and **all PASSED**:

1. Reseed + Complexity fixture Resolve card confirmed EDITABLE.
2. `/admin/arguments/{id}` for an uncertain-tier argument loads without error, badge correct.
3. Argument was in a publishable state (draft/unpublished).
4. Publish blocked; page showed the tier and a specific, count-bearing sentence naming what dragged it down — not a bare tier name, not the old generic "Try again" text.
5. Whitespace-only override reason rejected server-side; page rendered that rejection distinctly from the original block; argument did not publish.
6. A real reason published the argument; Status history showed the transition with the reason and the tier at that moment.
7. Unpublish → Publish again with no reason → blocked again (override is not sticky, D-16).

**Step 8 was NOT executed.** The operator had no available argument whose resolve step never ran, so the non-overridable `resolved_at` gate (D-14) rendering with NO override field offered could not be confirmed live in a browser. This is **already recorded** by the orchestrator as `.planning/WINDOWS.md` entry #8 (`kind: unrun-verify`, `phase: 48`, `status: open` as of this writing) — no duplicate entry was added here. **CORRECTION 2026-08-21:** entry #8 was marked `fixed` on 2026-08-20, and the browser check was confirmed live during Phase 48 UAT (48-UAT.md test 6): the operator forced the resolve-incomplete state via manual SQL and verified that the non-overridable `resolved_at` gate renders with NO override field, visibly distinct from the overridable UNCERTAIN trust gate. The `status: open` reference above is stale — this is no longer an open item. The D-14 must-have IS satisfied in code (the plain-string `detail` branch sets no `publishBlocked` flag) and IS covered by the static contract test's plain-string-detail assertions, but that coverage is static/structural only — it was never confirmed by observing the page render in a real browser. This gap is honestly recorded in the `coverage:` block above (D3) rather than claimed as verified.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 49's review queue can reuse the working `publishBlocked`/`trustTier`/`blockers`/`blockMessage` payload shape and the `blockerSentence` mapping pattern without re-deriving either.
- The one open item is the unverified D-14 browser rendering (WINDOWS.md #8) — re-verify when a resolve-incomplete fixture exists, naturally at Phase 49 or whenever such a fixture is next seeded.
- Full suite (`api/tests pipeline/tests tests`): 1178 passed, 5 xfailed, 0 failed — clean full-suite gate, no regressions introduced.
- Plan 48-09 (Wave 5: live fixture reseed, zero-drift proof, full-suite gate, requirement traceability, operator sign-off) is next.

## Self-Check: PASSED

- FOUND: app/src/routes/admin/arguments/[id]/+page.server.ts (modified)
- FOUND: app/src/routes/admin/arguments/[id]/+page.svelte (modified)
- FOUND: api/tests/test_phase48_publish_override_ui_contract.py (created)
- FOUND commit: cb5c86802
- FOUND commit: be308e3d2
- FOUND commit: 9e9ee02d6

---
*Phase: 48-trust-lifecycle*
*Completed: 2026-08-19*
