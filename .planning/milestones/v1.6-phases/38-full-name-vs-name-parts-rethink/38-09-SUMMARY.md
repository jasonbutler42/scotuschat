---
phase: 38-full-name-vs-name-parts-rethink
plan: 09
subsystem: ui
tags: [sveltekit, security, docket, validation, contract-test]

requires:
  - phase: 38-full-name-vs-name-parts-rethink
    provides: "api/domain/docket_values.py (DOCKET_VALUE_PATTERN/DOCKET_VALUE_MAX_LENGTH/DocketValueError/normalize_docket_value) and api/tests/fixtures/docket_value_cases.json (Plan 38-07)"
provides:
  - "app/src/lib/docketValues.ts: byte-identical TypeScript mirror of the canonical docket-value rule, with a code-to-sentence helper shared by the component and the server action"
  - "api/tests/test_docket_ui_contract.py: source-extraction contract test proving TS/Python parity without node or a DB"
  - "DocketPillInput's opt-in enforceShape prop and inline role=alert shape error, wired only into the Pipeline Runner's New Run form"
  - "SvelteKit-server re-check of every docket[] value in the pipeline action, closing the forged-hidden-input bypass"
affects: []

tech-stack:
  added: []
  patterns:
    - "Preview-only TypeScript mirror of an api/domain module (personNames.ts precedent): code-carrying error class, regex built via new RegExp() from an exported string literal, backend framed as sole authority"
    - "Source-extraction contract test (regex-extract pattern/constant from .ts source, replay through Python's re) as a node-free alternative to test_phase38_people_ui_contract.py's node-subprocess parity driver"

key-files:
  created:
    - app/src/lib/docketValues.ts
    - api/tests/test_docket_ui_contract.py
  modified:
    - app/src/lib/components/DocketPillInput.svelte
    - app/src/routes/admin/pipeline/+page.svelte
    - app/src/routes/admin/pipeline/+page.server.ts

key-decisions:
  - "Parity locked via source extraction + Python execution of the extracted rule, not a node subprocess — the existing node driver (test_phase38_people_ui_contract.py) is a known-broken pattern in this environment (Windows path/backslash mangling inside an inline JS string), and a docket rule is small enough (one anchored pattern + one integer) for source extraction to lock exactly"
  - "enforceShape defaults to false and is an additive opt-in prop; ArgumentDetailsCard.svelte (the post-ingest metadata editor) is left completely untouched and contract-tested at zero references, since its API contract has no equivalent path-hazard constraint"
  - "On a shape-error rejection, DocketPillInput preserves the attempted input value and does not add a pill; the error clears on the next input change or successful add, letting the operator correct a typo in place rather than retype it"
  - "The SvelteKit action's docket-error fail(400) never echoes the submitted value and never forwards FastAPI's 422 detail verbatim, keeping the existing T-07-13 posture; every other failure branch keeps its unmodified generic 'Could not start the run' copy"

requirements-completed: [PEOPLE-09]

coverage:
  - id: D1
    description: "app/src/lib/docketValues.ts declares a byte-identical DOCKET_VALUE_PATTERN/DOCKET_VALUE_MAX_LENGTH, a DocketValueError code-carrying class, normalizeDocketValue, and a code-to-sentence helper; parity with api/domain/docket_values.py is proven case-for-case against the shared fixture"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_docket_ui_contract.py (13 tests, all pass)"
        status: pass
    human_judgment: false
  - id: D2
    description: "DocketPillInput renders a role=alert inline shape error when enforceShape is true and an added value fails the rule, without creating a pill and without clearing the attempted input; ArgumentDetailsCard's docket pill behavior stays byte-for-byte unchanged (0 enforceShape references)"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_docket_ui_contract.py::test_docket_pill_input_renders_role_alert_shape_error, ::test_argument_details_card_does_not_reference_enforce_shape"
        status: pass
      - kind: manual_procedural
        ref: "Typing an out-of-shape docket into the Pipeline Runner's New Run docket input and pressing Enter"
        status: unknown
    human_judgment: true
    rationale: "The contract test proves the wiring (prop, role=alert element, unchanged ArgumentDetailsCard) but not the live visual/interactive behavior in a running browser — a human should confirm the inline error actually appears and the attempted text is preserved."
  - id: D3
    description: "app/src/routes/admin/pipeline/+page.server.ts re-checks every non-blank docket[] value with normalizeDocketValue before the mode split and returns fail(400) with docket-specific copy on rejection, without echoing the value or forwarding FastAPI's 422 body; every other failure branch keeps its existing generic copy"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_docket_ui_contract.py::test_pipeline_page_server_imports_and_calls_normalize_docket_value, ::test_pipeline_page_server_returns_fail_400_for_docket_error_branch, ::test_pipeline_page_server_keeps_generic_run_start_failure_copy"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-07-27
status: complete
---

# Phase 38 Plan 09: Docket-Value Operator-Facing Feedback Summary

**TypeScript mirror of the Phase 38-07 canonical docket rule (`app/src/lib/docketValues.ts`), an opt-in inline `role="alert"` shape error in `DocketPillInput` used only by the Pipeline Runner, and a SvelteKit-server re-check in `+page.server.ts` that rejects a forged `docket[]` value before FastAPI is ever called — closing item 3 of UAT gap G-38-6's `missing` list.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-27T19:28:00-05:00
- **Completed:** 2026-07-27T19:33:09-05:00
- **Tasks:** 3
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments

- New `app/src/lib/docketValues.ts`: byte-identical mirror of `api/domain/docket_values.py`'s `DOCKET_VALUE_PATTERN` (`^[A-Za-z0-9][A-Za-z0-9_-]*$`) and `DOCKET_VALUE_MAX_LENGTH` (64), a `DocketValueError` code-carrying class, `normalizeDocketValue()` enforcing the same blank → length → pattern check ordering, and a `docketValueErrorMessage()` helper mapping each code to the shared operator-facing sentence
- New `api/tests/test_docket_ui_contract.py`: locks TS/Python parity by extracting the pattern literal and max-length constant from `docketValues.ts` via anchored regexes, then replaying every case in `api/tests/fixtures/docket_value_cases.json` through both the extracted rule (via Python's `re`) and the real `normalize_docket_value` — no node subprocess, no DB, passes with no `DATABASE_URL` set
- `DocketPillInput.svelte` gains an opt-in `enforceShape` prop (default `false`); when true, `addPill` runs newly typed values through `normalizeDocketValue`, rendering a `role="alert"` inline error (composed with, not replacing, the caller-driven `invalid`/`descriptionId` contract via `aria-invalid`/`aria-describedby`) without creating a pill or clearing the input on rejection — the operator can correct the value in place. Existing D-04 silent empty/duplicate rejection is preserved even in `enforceShape` mode. `initialValues` and already-rendered pills are never re-validated.
- `app/src/routes/admin/pipeline/+page.svelte`'s New Run `DocketPillInput` opts into `enforceShape`; `ArgumentDetailsCard.svelte` is untouched (contract-tested at 0 `enforceShape` references)
- `app/src/routes/admin/pipeline/+page.server.ts`'s default action now re-checks every non-blank `docket[]` value with `normalizeDocketValue` before the `mode === 'url'`/upload split, returning `fail(400, { error: ... })` with docket-specific copy (never echoing the value or forwarding FastAPI's 422 body, per the existing T-07-13 posture) and pushing the normalized value into `dockets`; every other failure branch keeps its pre-existing generic "Could not start the run" copy unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: TypeScript mirror of the docket rule, parity-locked to the shared fixture** - `eec7cdf6` (feat)
2. **Task 2: Inline shape error in DocketPillInput, opted into by the Pipeline Runner only** - `ab291c2a` (feat)
3. **Task 3: SvelteKit action re-check with accurate operator copy** - `d3fa326f` (feat)

## Files Created/Modified

- `app/src/lib/docketValues.ts` - TypeScript mirror of the canonical docket-value rule (pattern, max length, error class, normalizer, code-to-sentence helper)
- `api/tests/test_docket_ui_contract.py` - Source-extraction contract test proving TS/Python parity plus wiring asserts across all three tasks
- `app/src/lib/components/DocketPillInput.svelte` - `enforceShape` opt-in prop, inline `role="alert"` shape error, composed `aria-invalid`/`aria-describedby`
- `app/src/routes/admin/pipeline/+page.svelte` - Passes `enforceShape` to the New Run form's `DocketPillInput`
- `app/src/routes/admin/pipeline/+page.server.ts` - Re-checks every docket value server-side with docket-specific `fail(400)` copy

## Decisions Made

- Parity locked via source extraction + Python execution of the extracted rule, not a node subprocess, avoiding the known-broken Windows-path node driver pattern in this environment
- `enforceShape` is an additive, opt-in prop defaulting to `false`; `ArgumentDetailsCard.svelte` stays completely untouched
- Shape-error rejection preserves the attempted input value and does not clear it, matching the attempted-value-preservation behavior already established on the people editor (38-UAT Test 2)
- The SvelteKit action's docket-error message never echoes the submitted value or forwards FastAPI's 422 detail verbatim, keeping the T-07-13 posture intact

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three layers of the G-38-6 fix are now in place: FastAPI boundary (38-07), pipeline-side guard (38-08), and operator-facing feedback (38-09, this plan).
- Plan 38-10 (or phase verification) can proceed to close out Phase 38.
- No blockers.

---
*Phase: 38-full-name-vs-name-parts-rethink*
*Completed: 2026-07-27*

## Self-Check: PASSED

All 6 created/modified files found on disk; all 3 task commit hashes (`eec7cdf6`, `ab291c2a`, `d3fa326f`) found in git log.
