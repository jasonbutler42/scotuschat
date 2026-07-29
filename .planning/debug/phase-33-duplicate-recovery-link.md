---
status: resolved
phase: 33
slug: phase-33-duplicate-recovery-link
created: 2026-07-14
goal: find_root_cause_only
resolved_by: "Plan 33-04 (33-04-PLAN.md / 33-04-SUMMARY.md), commit ce6eb651, 2026-07-14 (same day)"
---

**Stale-record correction (2026-07-29):** This session's goal was `find_root_cause_only`, so its `status` was never going to flip to reflect a fix even though one landed the same day via Plan 33-04. Reconciled during Phase 40.1's cleanup — see `.planning/phases/40.1-sanitize-docket-input-to-close-path-traversal-arbitrary-file/40.1-SUMMARY.md`. Fix: `api/routers/admin.py`'s duplicate payload builders no longer include link-oriented wording; `ArgumentDetailsCard.svelte` remains sole owner of the actionable link label. Verified via `api/tests/test_question_number_nullable.py::test_duplicate_message_and_component_compose_one_recovery_phrase` and `33-UAT.md` Test 1 (flipped to `pass`).

# Phase 33 Duplicate Recovery Link

## Symptoms

- Expected one inline duplicate alert containing one recovery link on both admin routes.
- Actual alert ends with `Open conflicting argument. Open conflicting argument.`
- Metadata retention, focus, numeric target, new-tab behavior, and opener isolation pass UAT.

## Current Focus

Root cause confirmed. No implementation files modified.

## Evidence

- Repository HEAD is the expected base `bea0300d475582cdb82335bc0b9417bd0527a61a`.
- Backend duplicate messages already include the sentence `Open conflicting argument.`
- `ArgumentDetailsCard.svelte` also contains literal recovery-link text `Open conflicting argument`.
- `api/routers/admin.py:1112-1114` and `:1138-1139` include `Open conflicting argument.` in both pre-check and raced-constraint payload messages.
- Both SvelteKit actions validate and forward the complete backend `detail` object as `form.conflict`; neither adds copy.
- `ArgumentDetailsCard.svelte:251-257` renders `form.conflict.message` verbatim and immediately appends a link labeled `Open conflicting argument`.
- Both reported routes use this shared card, explaining identical reproduction on both pages without two alert branches.
- The backend route test locks the actionable sentence into the API message (`api/tests/test_admin_arguments_routes.py:37`).
- The frontend source-contract test asserts one alert and safe link attributes but never asserts the composed alert text or counts the recovery phrase (`api/tests/test_question_number_nullable.py:69-80`).
- Git blame attributes both message rendering and link label to Phase 33 commit `de3084fd`; this is a single cross-layer composition defect introduced with duplicate recovery UI.

## Hypotheses

1. **Confirmed:** The component renders the backend-provided actionable message verbatim and appends a separately rendered link with the same phrase.
2. **Eliminated:** Both route server actions append recovery copy independently; they pass the validated detail object unchanged.
3. **Eliminated:** Two alert/link branches render simultaneously; the component contains one `role="alert"` and one conflict branch.

## Eliminated

- Route-specific duplication: both routes converge on the same component and unchanged conflict shape.
- Double alert rendering: source and tests confirm one alert element.

## Reasoning Checkpoint

```yaml
reasoning_checkpoint:
  hypothesis: "The API message already contains the recovery phrase, and the shared Svelte component renders that message before appending a link with the identical phrase, producing two copies on every valid duplicate conflict."
  confirming_evidence:
    - "api/routers/admin.py includes the phrase in both duplicate payload construction paths."
    - "ArgumentDetailsCard.svelte prints form.conflict.message and then renders the identically labeled link."
    - "Both route actions forward the validated conflict object unchanged, matching two-route UAT reproduction."
  falsification_test: "The hypothesis would be false if either route transformed the message, if the backend message omitted the phrase, or if the component did not render both the message and link; direct source inspection shows all three contrary observations."
  fix_rationale: "Establish one owner for recovery copy: keep the message factual and let the component own the actionable linked phrase, or otherwise remove the component's duplicate literal while retaining an accessible link. Add an assertion on composed alert copy so the phrase occurs exactly once."
  blind_spots: "No browser DOM snapshot was captured locally; the user's two-route UAT supplies runtime confirmation. Other API consumers of the message should be checked before changing the backend contract."
```

## Root Cause

The duplicate recovery contract has two owners for the same actionable copy. FastAPI returns a `message` ending in `Open conflicting argument.`, while the shared Svelte card treats that message as lead-in text and appends an anchor labeled `Open conflicting argument`. Existing tests verify each layer independently but not their composed visible text, so both contracts passed while producing the duplicate sentence.

## Suggested Fix Direction

Choose a single owner for the action phrase. Prefer a factual backend message without link-oriented copy and retain the component-owned accessible anchor, updating the exact backend contract tests and adding a frontend/composition regression that proves the visible recovery phrase occurs once. Check any non-Svelte consumers before changing the message contract.
