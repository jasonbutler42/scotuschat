---
phase: 34-blank-case-name-docket-validation
verified: 2026-07-14T19:11:55Z
status: passed
score: 9/10 must-haves verified
behavior_unverified: 1
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 7/10
  gaps_closed:

    - "CR-01: Corrected native Case fields now clear stale required state before later collision or generic failures render."
    - "WR-01: The invalid-submit, correction, server-required, collision, and generic lifecycle now has a real Edge/CDP regression against the actual Svelte route."
  gaps_remaining: []
  regressions: []
behavior_unverified_items:

  - truth: "An editable empty docket-pill collection is canceled client-side and focuses the visible invalid pill input on both metadata surfaces while readonly behavior remains unchanged."
    test: "Remove all docket pills in the argument editor and pipeline job metadata forms, submit, and inspect request cancellation, attempted empty state, focus, border, outline, and readonly behavior."
    expected: "No request is sent; exact required copy appears; empty pills stay empty; the visible pill input receives focus with invalid ARIA/border styling; readonly cards do not gain required behavior."
    why_human: "The implementation is present and wired, but no component/browser test executes the custom-control cancellation and focus transition on both consumers."
human_verification:

  - test: "Exercise single-field and combined native Case validation in a browser."
    expected: "No browser bubble appears; exact applicable copy renders in the existing alert; ARIA and red borders match only current invalid controls; focus lands on the sole invalid field or case name first when both are blank."
    why_human: "The Edge regression covers the combined-invalid lifecycle, but the planner-deferred single-field visual and native-bubble checks remain manual."

  - test: "Exercise empty docket-pill submission on both editable metadata surfaces and inspect readonly mode."
    expected: "The request is canceled; exact inline copy appears; empty attempted state is preserved; focus-visible outline and invalid border appear on the pill input; readonly behavior is unchanged."
    why_human: "No executable test drives the custom pill component's cancellation/focus transition on both consumers."

  - test: "Repeat invalid Case submission, correction, then a collision or generic failure in the operator UI."
    expected: "Required copy, invalid ARIA, red borders, and required-field focus do not recur; only the actual later error remains visible and understandable."
    why_human: "The automated Edge regression proves the DOM state transition, while the plan retains a final operator-facing clarity/flow check."
---

# Phase 34: Blank case_name/docket_number Validation Verification Report

**Phase Goal:** Prevent blank required case and docket values from corrupting public slugs or deduplication keys, with authoritative validation and recoverable admin UI feedback.
**Verified:** 2026-07-14T19:11:55Z
**Status:** `human_needed`
**Re-verification:** Yes — after Plan 34-04 gap closure

The deterministic phase blocker is closed. Backend validation still enforces PIPE-28 before service writes, and the actual Svelte route now clears stale native-only required state at the valid enhanced-submit boundary. A real Edge/CDP regression proves the previously missing lifecycle. The only behavior-dependent truth without executable coverage is the custom docket-pill cancellation/focus path on both editable consumers, so the phase routes to final human UAT rather than another gap plan.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | Blank/whitespace `ArgumentUpdate.case_name` and `docket_number` values are rejected before service execution. | ✓ VERIFIED | `api/schemas/admin_arguments.py:225-233` rejects null/non-string/empty-after-strip values; route regressions prove standard 422 and no service call. |
| 2 | Omitted PATCH fields remain omitted and leave stored values unchanged. | ✓ VERIFIED | Optional defaults and `model_fields_set` tests preserve omission; services retain omission-sensitive writes. |
| 3 | Metadata `case_name`, singular `source_docket`, and empty/all-blank `source_dockets` are rejected. | ✓ VERIFIED | `MetadataUpdate` scalar/list validators at `api/schemas/admin_arguments.py:261-287` reject explicit clearing. |
| 4 | Mixed docket arrays trim, drop blanks, de-duplicate in first-seen order, and select index zero canonically. | ✓ VERIFIED | Normalized schema output flows directly to `source_dockets` and `source_docket = body.source_dockets[0]` at service lines 863-866; service tests cover ordering/precedence. |
| 5 | Slug and docket/docket-normalized fields cannot be written as empty strings through either save service. | ✓ VERIFIED | Invalid request models cannot reach writes; direct service consumption is covered; full suite evidence is 483 passed, 5 xfailed. |
| 6 | Both native Case inputs carry required defense-in-depth and conditional accessible invalid state. | ✓ VERIFIED | `+page.svelte:173,205` has both `required` attributes; conditional ARIA, alert associations, and error borders remain wired. |
| 7 | Both SvelteKit action owners derive required failures from shape-checked `detail[].loc`, not message text, and preserve attempts. | ✓ VERIFIED | Unknown-safe parsers and complete `attemptedValues` spreads exist in both action files; focused contracts passed 10/10. |
| 8 | Empty editable docket pills are blocked client-side and server-required failures target the visible input without changing readonly behavior. | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | `ArgumentDetailsCard.svelte:86-100` wires `hasPills()`, `cancel()`, tick/focus, and server-required focus; `DocketPillInput.svelte:121-122` wires ARIA. No behavioral test executes this on both consumers. |
| 9 | Native Case invalid submission accumulates both fields and focuses case name before docket. | ✓ VERIFIED | The Edge/CDP regression submits both fields blank and asserts no PATCH, exact ordered messages, both ARIA/borders, and case-name focus. |
| 10 | Corrected native Case fields clear required state so later server-required, collision, and generic failures remain distinct. | ✓ VERIFIED | `+page.svelte:150-151` clears both native flags before saving; the Edge/CDP test exercises current structured-required state followed by collision and generic results and asserts stale state does not recur. |

**Score:** 9/10 truths verified; 1 present and wired but behaviorally unverified.

### Required Artifacts

| Artifact | Status | Details |
|---|---|---|
| `api/schemas/admin_arguments.py` | ✓ VERIFIED | Substantive scalar/collection validators preserve omission and reject explicit clearing. |
| `api/services/admin_arguments.py` | ✓ VERIFIED | Consumes validated normalized fields and deterministically selects the canonical docket. |
| Backend service/route tests | ✓ VERIFIED | Exercise normalization, omission, structured 422 locations, pre-service rejection, and safe writes. |
| Both SvelteKit action owners | ✓ VERIFIED | Required-location parsing and presence-preserving attempts are substantive and wired. |
| `app/src/routes/admin/arguments/[id]/+page.svelte` | ✓ VERIFIED | Native validation, exact feedback, valid-submit reset, ARIA, borders, and focus are wired and browser-tested. |
| `ArgumentDetailsCard.svelte` / `DocketPillInput.svelte` | ⚠️ WIRED, BEHAVIOR UNVERIFIED | Custom-control cancellation/focus implementation is substantive; executable transition coverage is absent. |
| `app/tests/case-required-recovery.browser.test.mjs` | ✓ VERIFIED | Authenticates through the real login action and drives the actual Svelte route with isolated mock API/Edge/CDP lifecycle. |
| `api/tests/test_question_number_nullable.py` | ✓ VERIFIED (supplemental) | Ten focused contracts pass, including reset-before-saving ordering; no longer the sole lifecycle evidence. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| Pydantic request schemas | save services | typed normalized request models | ✓ WIRED | FastAPI parses models before service invocation; services consume validated fields. |
| FastAPI 422 response | SvelteKit failure flags | shape-checked terminal `loc` fields | ✓ WIRED | Both action parsers accumulate stable field identifiers and ignore `msg`. |
| Failure attempted values | native/custom controls | property-presence restoration | ✓ WIRED | Blank strings and `dockets: []` remain meaningful failed state. |
| `ArgumentDetailsCard` | `DocketPillInput` | invalid/description props plus imperative focus/hasPills API | ✓ WIRED | Parent cancellation/focus calls and child ARIA APIs are connected. |
| Native Case validity | later enhanced failure state | synchronous native-flag reset before saving, then SvelteKit update | ✓ WIRED + TESTED | Edge/CDP lifecycle regression closes prior CR-01. |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Produces Real Data | Status |
|---|---|---|---|---|
| Case form | `data.argument`, SvelteKit `form` | authenticated page load and named save action | Yes; saved values plus presence-preserved attempts | ✓ FLOWING |
| Argument details card | `savedValues`, `form.dockets` | argument/pipeline page loads and metadata actions | Yes; real backend detail plus failed attempts | ✓ FLOWING |
| Required error flags | `form.caseNameRequired`, `form.docketRequired` | parsed FastAPI structured 422 response | Yes; terminal Pydantic locations | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Evidence / Command | Result | Status |
|---|---|---|---|
| Actual invalid → correction → later-failure lifecycle | `node --test app/tests/case-required-recovery.browser.test.mjs` | 1 passed (provided execution evidence) | ✓ PASS |
| Focused action/component contracts | `.\.venv\Scripts\python.exe -m pytest api/tests/test_question_number_nullable.py -q` | 10 passed in verifier process | ✓ PASS |
| Svelte diagnostics | `npm run check` | 0 errors, 16 pre-existing warnings (provided execution evidence) | ✓ PASS |
| Full configured regression | `.\.venv\Scripts\python.exe -m pytest -q` | 483 passed, 5 xfailed (orchestrator evidence) | ✓ PASS |

### Probe Execution

No phase-specific probe scripts were declared; not applicable.

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|---|---|---|---|---|
| PIPE-28 | 34-01 through 34-04 | Clearing case name or docket is rejected instead of corrupting slug/dedup state. | ✓ SATISFIED | Authoritative schema validation, safe service writes, direct-route tests, required UI defenses, and recovery lifecycle coverage. |

No orphaned Phase 34 requirement exists; `REQUIREMENTS.md` maps only PIPE-28 to this phase.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `app/tests/case-required-recovery.browser.test.mjs` | 180-211 | Spawn errors/premature exits are not raced against readiness | Advisory warning | A blocked/corrupt browser installation can fail less directly and delay deterministic cleanup; updated code review reports 0 critical and 1 warning. This does not invalidate the passing lifecycle behavior or PIPE-28. |

No blocker debt markers, stubs, hollow artifacts, or unresolved high-severity threat mitigations were found.

## Human Verification Required

### 1. Single and Combined Native Case Validation

**Test:** Submit with only case name blank, only docket blank, and both blank; also exercise the server-required recovery path.
**Expected:** Exact applicable copy appears in the existing alert without a native bubble; current invalid controls alone carry ARIA/red borders; focus follows field order; attempted values remain visible.
**Why human:** The automated browser lifecycle covers combined invalid state, but not every planner-deferred single-field visual case.

### 2. Empty Docket Pills on Both Editable Surfaces

**Test:** Remove all pills and submit in the argument editor and pipeline job metadata forms; inspect readonly mode too.
**Expected:** No request is sent, exact inline copy appears, empty state persists, focus/outline/red border target the pill input, and readonly behavior remains unchanged.
**Why human:** No executable browser/component test drives this state transition on both consumers.

### 3. Operator-Facing Recovery Clarity

**Test:** Submit both Case fields blank, correct them, then force a collision or generic failure.
**Expected:** Required feedback and focus do not recur; only the actual later error remains clear and visible.
**Why human:** Automated DOM assertions pass, while the plan explicitly retains a final user-flow clarity check.

## Gaps Summary

No implementation gaps remain. Prior CR-01 and WR-01 are closed. The phase awaits three end-of-phase UAT checks, centered on the one remaining behavior-unverified custom docket-pill transition.

## Next Action

Run Phase 34 conversational/browser UAT. If the three checks pass, Phase 34 can be marked complete without another gap-closure plan.

---

_Verified: 2026-07-14T19:11:55Z_
_Verifier: Codex (gsd-verifier)_
