---
phase: 36-click-to-copy-extracted-values-design-pattern
verified: 2026-07-15T17:20:00Z
status: gaps_found
score: 7/9 must-haves verified
behavior_unverified: 1
overrides_applied: 0
gaps:
  - truth: "Repeated copy activation restarts one full 1500ms success interval for the newest attempt"
    status: failed
    reason: "Concurrent clipboard promises can each schedule a reset timer; only the last timer handle is retained, so an earlier untracked timer can clear the newest success state before its full interval elapses."
    artifacts:
      - path: "app/src/lib/components/CopyableExtractedValue.svelte"
        issue: "copyValue clears only an already-created timer before awaiting writeText and has no attempt-generation guard."
    missing:
      - "Add a monotonically increasing attempt token or serialize activations so only the newest attempt can update feedback and own the single reset timer."
      - "Invalidate pending attempts during component destruction."
  - truth: "Local feedback always describes the value currently displayed by the reused component instance"
    status: failed
    reason: "Reactive value/copyLabel changes do not reset state or invalidate pending copy work, so a newly rendered value can inherit Copied or Couldn't copy. from the prior value."
    artifacts:
      - path: "app/src/lib/components/CopyableExtractedValue.svelte"
        issue: "No value/copyLabel-keyed effect clears resetTimer, invalidates outstanding attempts, and returns state to idle."
    missing:
      - "Reset local feedback and invalidate pending work when value or copyLabel changes."
behavior_unverified_items:
  - truth: "Clipboard rejection shows local fixed failure feedback and a later successful retry clears it"
    test: "Force navigator.clipboard.writeText to reject, verify Couldn't copy. is local, then restore success and retry the same control."
    expected: "The control shows only Couldn't copy. after rejection; a successful retry replaces it with Copied without exposing the raw exception."
    why_human: "The code path is present but no frontend behavioral test exercises it, and Chrome localhost continued allowing writes during operator UAT despite clipboard permission being blocked."
---

# Phase 36: Click-to-copy Extracted Values Design Pattern Verification Report

**Phase Goal:** Whenever a value has been extracted from a source PDF, use one consistent click-to-copy pattern on pipeline and argument-editor pages, including individual dockets; disable copying for N/A and provide an icon and tooltip.
**Verified:** 2026-07-15T17:20:00Z
**Status:** gaps_found
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | Every eligible pipeline-run extracted display uses the click-to-copy affordance. | VERIFIED | `pipeline/[job_id]/+page.svelte` imports the shared component and uses it for case name, formatted argued date, primary docket, and question number; `ResolveCard.svelte` uses it for editable title hints. Counts and non-editable title rows remain intentionally plain under D-13. |
| 2 | Every eligible argument-editor display, including each individual docket, uses the identical affordance. | VERIFIED | `ArgumentDetailsCard.svelte` renders one shared component per docket and shared controls for question/date; `arguments/[id]/+page.svelte` uses it for editable speaker title hints. Operator UAT confirmed docket text and icon both copy the individual visible docket. |
| 3 | Missing values remain visible and cannot be copied or tab-focused. | VERIFIED | The shared component derives empty input to `N/A`, renders a native disabled button, supplies `Nothing extracted to copy.`, and omits the icon per the operator-approved Phase 36 change. Operator UAT confirmed the N/A item is skipped by Tab, retains its tooltip, and has no copy icon. |
| 4 | One reusable component owns clipboard, icon, disabled, tooltip, and local feedback behavior. | VERIFIED | All five consumers import `CopyableExtractedValue.svelte`; no consumer contains its own clipboard call or timer. Repository search finds the only `navigator.clipboard.writeText` call in the shared component. |
| 5 | The exact displayed string is copied and each docket copies only itself. | VERIFIED | The component renders and writes the same `value` prop. Callers pass final strings; argued dates are formatted before the component. Operator UAT confirmed visible/copied docket equality and `04/26/2010` display, while `Use extracted` correctly fills the native date control without autosave. |
| 6 | Field-specific tooltip, native keyboard activation, visible focus, responsive wrapping, and noninteractive count exclusions work. | VERIFIED | Native button semantics, `title={copyLabel}`, 36px minimum height, wrapping styles, and decorative SVG are centralized. Operator UAT confirmed Enter, Space, focus outline, tooltip, narrow layout, and plain count readouts. |
| 7 | Repeated activation restarts a full 1500ms success interval for the newest copy. | FAILED | Lines 20-32 clear only a timer that already exists, then await clipboard work. Two in-flight attempts can create two timers while retaining only one handle; an older timer can reset newer feedback early. Manual UAT passed the ordinary fast-click case but cannot prove promise-order safety. |
| 8 | Local feedback cannot survive a change to the displayed value. | FAILED | `value` is reactive, but no effect resets `state`/`resetTimer` or invalidates an outstanding promise when the value or label changes. A reused instance can falsely show feedback belonging to its prior payload. |
| 9 | Clipboard rejection is local, fixed-copy, and recoverable on retry. | PRESENT_BEHAVIOR_UNVERIFIED | The catch branch renders fixed `Couldn't copy.` with `role=alert`, and success changes state to copied. There is no behavioral frontend test; Chrome localhost would not deny the API during UAT even with Clipboard blocked. |

**Score:** 7/9 truths verified (1 present but behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `app/src/lib/components/CopyableExtractedValue.svelte` | Shared clipboard state machine and UI | PARTIAL | Exists, substantive, and consumed everywhere, but its asynchronous state machine has CR-01 and WR-01 correctness gaps. The artifact helper's "Missing export: [default]" is a Svelte false positive; `.svelte` components are default-imported by all consumers without an explicit script export. |
| `app/src/lib/components/ArgumentDetailsCard.svelte` | Docket, question, and date adoption | VERIFIED | Shared control is used for all hints; UAT approved MM/DD/YYYY display, N/A icon removal, and `Use extracted`. |
| `app/src/lib/components/ResolveCard.svelte` | Editable resolve-title adoption | VERIFIED | Shared component appears only in the editable title branch. |
| `app/src/routes/admin/arguments/[id]/+page.svelte` | Speaker-title adoption | VERIFIED | Shared title-hint control wired into the argument editor. |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | Eligible parsed-output adoption | VERIFIED | All four eligible parsed outputs use the shared primitive; count readouts remain plain. |
| `CLAUDE.md` | Durable D-13 convention | VERIFIED | Architecture rule 4 records extracted-plus-editable as the default and read-only extraction as excluded. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `ArgumentDetailsCard.svelte` | `CopyableExtractedValue.svelte` | Import plus per-field/per-docket instances | WIRED | Each docket receives its own component instance; question and formatted date use text variant. |
| `ResolveCard.svelte` | `CopyableExtractedValue.svelte` | Editable title branch | WIRED | `row.title_hint` flows directly to the component. |
| Argument editor page | `CopyableExtractedValue.svelte` | Speaker title hint | WIRED | `speaker.title_hint` flows directly to the component. |
| Pipeline job page | `CopyableExtractedValue.svelte` | Four parsed-output values | WIRED | Real `liveJob.parse_stats` fields flow into the component, with final date/string formatting at the caller. |
| `CopyableExtractedValue.svelte` | Browser clipboard | `navigator.clipboard.writeText(value)` | PARTIAL | Correct payload and explicit activation, but overlapping asynchronous attempts are not ordered. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `ArgumentDetailsCard.svelte` | `hints.dockets`, `question_number`, `argued_date` | Page server data passed by both pipeline and argument-editor consumers | Yes | VERIFIED |
| `ResolveCard.svelte` | `row.title_hint` | `resolveRows` server payload | Yes | VERIFIED |
| Argument editor page | `speaker.title_hint` | Loaded speaker form data | Yes | VERIFIED |
| Pipeline job page | `liveJob.parse_stats` | Loaded/polled pipeline job payload | Yes | VERIFIED |

### Behavioral Spot-Checks

| Behavior | Evidence | Result | Status |
|---|---|---|---|
| Static frontend correctness | `npm run check` | Passed during execution/fix rounds | PASS |
| Production compilation | `npm run build` | Passed during execution/fix rounds | PASS |
| Full project regression | Python suite | 492 passed, 5 expected xfails outside restricted token | PASS |
| Browser interaction matrix | Operator UAT | Docket copy/paste, mouse/text/icon activation, keyboard, focus, repeated ordinary click, disabled N/A, tooltip, responsive wrapping, date formatting, and Use extracted passed | PASS WITH LIMITATIONS |
| Concurrent promise ordering | Code trace at component lines 17-35 | Older completion timer can reset newer state | FAIL |
| Prop-change feedback reset | Code trace at component lines 11-15 and 38-40 | No reset/invalidation exists | FAIL |

### Probe Execution

No phase probes were declared; probe execution was not applicable.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| UX-01 | 36-01, 36-02 | Consistent reusable click-to-copy across eligible pipeline and argument-editor extracted values, disabled for N/A | BLOCKED | Surface coverage and shared wiring are complete, but the shared state machine does not meet its required repeated-activation/local-feedback correctness contract. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `CopyableExtractedValue.svelte` | 17-35 | Concurrent async attempts without generation/ordering guard | BLOCKER | Latest success feedback can be shortened by an older attempt's untracked timer. |
| `CopyableExtractedValue.svelte` | 11-15 | Reactive payload with non-reactive feedback lifecycle | BLOCKER | A changed value can inherit feedback for the previous clipboard payload. |

### Human Verification Status

The operator completed the blocking browser UAT and approved the final Phase 36 boundary. Two limitations remain documented: no populated title-hint fixture was available, and Chrome localhost would not reject clipboard writes even after Clipboard permission was blocked. The latter leaves the rejection/retry truth behavior-unverified; it is not the cause of the `gaps_found` status.

Phase 38's stacked confidence/raw-source presentation is intentionally outside Phase 36 and is not a gap here.

### Gaps Summary

Surface coverage, reusable-component adoption, exact visible-value copying, disabled N/A behavior, accessibility, date formatting, and the `Use extracted` bridge all meet the approved Phase 36 contract. The phase cannot pass yet because the one shared component does not safely order overlapping clipboard attempts and does not reset feedback when its reactive payload changes. Both gaps are localized to `CopyableExtractedValue.svelte` and should be closed together with focused component-level behavioral tests for rapid out-of-order completion, prop changes during pending/success/error states, timer cleanup, rejection, and recovery.

---

_Verified: 2026-07-15T17:20:00Z_
_Verifier: generic-agent workaround (gsd-verifier role preamble)_
