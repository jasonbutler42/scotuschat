---
phase: 36-click-to-copy-extracted-values-design-pattern
reviewed: 2026-07-15T16:38:21Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - app/src/lib/components/CopyableExtractedValue.svelte
  - app/src/lib/components/ArgumentDetailsCard.svelte
  - app/src/lib/components/ResolveCard.svelte
  - app/src/routes/admin/arguments/[id]/+page.svelte
  - app/src/routes/admin/pipeline/[job_id]/+page.svelte
  - CLAUDE.md
findings:
  critical: 1
  warning: 1
  info: 0
  total: 2
status: issues_found
---

# Phase 36: Code Review Report

**Reviewed:** 2026-07-15T16:38:21Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

The shared component and all five consumers were reviewed against the Phase 36 plans, context, UAT changes, and the explicit Phase 38 presentation boundary. The consumer wiring is consistent, but the component's asynchronous state machine does not actually guarantee the repeated-activation timing contract and can retain feedback after its displayed value changes.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Concurrent copy attempts can shorten the latest success interval

**File:** `app/src/lib/components/CopyableExtractedValue.svelte:17-35`

**Issue:** Every activation clears only an already-created timeout and then awaits `writeText`. Two rapid activations can therefore both be awaiting before either creates a timeout. Each completion creates its own timeout, but only the last handle is retained in `resetTimer`; the earlier timeout remains live and can reset `state` before 1,500ms has elapsed from the latest successful activation. Promise completion order is not guaranteed, so the implementation violates D-07 under the exact repeated-click scenario the phase requires.

**Fix:** Assign a monotonically increasing attempt token before awaiting. After `writeText` settles, update feedback and schedule/reset the timer only if that attempt is still current. Invalidate the token on destruction and on relevant prop changes. Alternatively serialize activations, while still restarting a single timer after the newest successful request.

## Warnings

### WR-01: Feedback state survives a displayed-value change

**File:** `app/src/lib/components/CopyableExtractedValue.svelte:11-15`

**Issue:** `value` is reactive, but `state` and `resetTimer` are never reset when `value` changes. Svelte may reuse the component instance when route data, polling data, or an unkeyed list updates. In that case a newly displayed extracted value can immediately inherit `Copied` or `Couldn't copy.` from the prior value even though the operator never attempted to copy the new value. That makes local feedback falsely describe a different payload.

**Fix:** Add an effect keyed to `value` (and preferably `copyLabel`) that invalidates outstanding attempts, clears the timer, and returns `state` to `idle`. Keep teardown centralized so the same reset logic is used by prop changes and `onDestroy`.

---

_Reviewed: 2026-07-15T16:38:21Z_
_Reviewer: generic-agent workaround (gsd-code-reviewer role preamble)_
_Depth: standard_
