---
phase: 34-blank-case-name-docket-validation
reviewed: 2026-07-14T18:34:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - api/schemas/admin_arguments.py
  - api/services/admin_arguments.py
  - api/tests/test_admin_arguments_service.py
  - api/tests/test_admin_arguments_routes.py
  - app/src/routes/admin/arguments/[id]/+page.server.ts
  - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
  - api/tests/test_question_number_nullable.py
  - app/src/routes/admin/arguments/[id]/+page.svelte
  - app/src/lib/components/ArgumentDetailsCard.svelte
  - app/src/lib/components/DocketPillInput.svelte
findings:
  critical: 1
  warning: 1
  info: 0
  total: 2
status: issues_found
---

# Phase 34: Code Review Report

**Reviewed:** 2026-07-14T18:34:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

The API-boundary validation and structured location parsing are coherent, but the native Case form keeps client validation flags after the inputs become valid. That stale state produces false required feedback after a later non-required failure. The source-contract tests do not exercise this state transition and therefore allow the defect to pass.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Corrected Case fields retain stale required state across later submissions

**File:** `app/src/routes/admin/arguments/[id]/+page.svelte:14-17,25-30,149-157`

**Issue:** `nativeCaseNameRequired` and `nativeDocketRequired` are set only by `invalid` events. Once either becomes `true`, correcting the field means the browser no longer emits an `invalid` event, and the enhanced submission path never clears or recomputes the native flags. If that corrected submission then fails for a slug collision, docket collision, network error, or another generic server error, `caseNameRequired`/`docketRequired` remain true, so the UI continues to show a false required message, red border, and invalid ARIA state. The required branch also visually takes precedence over the actual server error. This violates the phase requirement that corrected attempts expose the applicable failure and can misdirect the operator indefinitely until a successful redirect.

**Fix:** Recompute or clear the native flags at the start of every enhanced submission, which only runs after native constraint validation has passed. For example:

```svelte
use:enhance={() => {
  nativeCaseNameRequired = false;
  nativeDocketRequired = false;
  savingState = true;
  // existing callback
}}
```

Alternatively, clear each flag on input when its control becomes valid, while preserving the ordered scan in `handleCaseInvalid`.

## Warnings

### WR-01: Source-text assertions do not cover validation-state recovery

**File:** `api/tests/test_question_number_nullable.py:69-84`

**Issue:** The Case form regression test checks only that selected source fragments exist and appear in a particular order. It never executes the state sequence “invalid submit → correct field → non-required action failure,” so it passes while CR-01 is present. These assertions also cannot prove that Svelte reactivity updates the rendered alert, ARIA attributes, or focus target.

**Fix:** Add a component/browser test that submits with both Case fields blank, corrects them, forces a generic or collision failure, and verifies that required copy and invalid ARIA state are cleared while the actual failure remains visible. Retain the source checks only for contracts that cannot yet be exercised by the available runner.

---

_Reviewed: 2026-07-14T18:34:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
