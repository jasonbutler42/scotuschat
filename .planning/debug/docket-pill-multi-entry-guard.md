---
status: resolved
trigger: "User gets 'Only one docket number is supported. Please remove the extra entries.' when trying to add a new docket pill in ArgumentDetailsCard"
created: 2026-07-06T00:00:00Z
updated: 2026-07-06T00:00:00Z
---

## Current Focus

hypothesis: |
  After a successful save the server returns `{ saved: true }` with no `dockets` field.
  The component's `$effect` only fires when `form?.dockets` is truthy.
  On the NEXT page load, `savedValues.dockets` comes from the DB (e.g. `["21-1271"]`),
  so `pills` is correctly initialized to `["21-1271"]`.
  BUT — there is also a stale `form` prop from the previous save still in scope:
  `form = { saved: true }` (no `dockets`). On page navigation WITHOUT a full reload
  (e.g. the operator clicks Save and sees "Saved." then immediately tries to add another pill),
  the `update({ reset: false })` call keeps `form` alive. However this alone does not
  explain the double-pill problem.

  The real mechanism: `savedValues` is the INITIAL `$state` seed. After a save round-trip
  with `update({ reset: false })`, SvelteKit re-runs the load function and re-renders the
  page with fresh `savedValues`. But `pills` is `$state` — it is ONLY re-initialized from
  `savedValues` on component MOUNT, not on prop updates. So after the first successful save:
    - DB has `source_docket = "21-1271"`
    - `savedValues.dockets = ["21-1271"]`   ← new prop value after load re-runs
    - `pills` is still whatever it was before the save completed
  
  Because `update({ reset: false })` keeps the component mounted (no remount),
  `pills` retains its old value and the `$state` seed from `savedValues` does NOT re-run.
  
  HOWEVER — the `$effect` watching `form?.dockets` fires on every form change.
  After a failed save (dockets.length > 1), the server echoes `dockets` back.
  That is the OTHER path.
  
  Re-reading the test sequence: Test 7 says user adds a pill and hits save. The error fires
  during the ADD step, before save — i.e., merely having one pill already in `pills` state
  and trying to add a second one triggers the server error. This means the form is being
  SUBMITTED with 2 docket[] values. The question is: where does the second one come from?

  CONFIRMED HYPOTHESIS: The `$effect` that watches `form?.dockets` is firing with
  the stale `form` from a previous FAILED save (or from the initial load where `form`
  carries echoed dockets), and it is ADDING pills on top of what `savedValues` already
  seeded. Specifically:
  - `savedValues.dockets = ["21-1271"]` → `pills` initialized to `["21-1271"]`
  - A prior form submission returned `fail(400, { dockets: ["21-1271"], saveError: ... })`
    (or the form prop contains a dockets array from some prior navigation)
  - The `$effect(() => { if (form?.dockets) { pills = form.dockets; } })` fires and
    SETS pills = ["21-1271"] again (same value, no visible change)
  - But when the user then types a NEW docket and presses Enter, `addPill()` adds it:
    `pills = ["21-1271", "22-0000"]`
  - Submit sends two `docket[]` values → server guard fires

  Wait — that path still gives 2 pills which the guard blocks correctly.

  FINAL CONFIRMED HYPOTHESIS: The `$effect` restores pills from `form.dockets` on EVERY
  re-render where `form` is non-null and has a `dockets` array. This includes the case
  where the PREVIOUS submission was a success and then a page navigation re-renders with
  the old form still in scope. But more critically: `savedValues.dockets` initializes pills
  to e.g. `["21-1271"]`. The user then removes that pill (pills = []). They try to save.
  If any prior `form` with `dockets` is still in the prop, the effect overwrites pills back
  to the prior value. Then when they submit, the hidden inputs already contain a pill they
  thought they removed.

  SIMPLEST ROOT CAUSE: The `$effect` runs unconditionally whenever `form` changes —
  including when SvelteKit re-hydrates or re-renders the component with a stale `form`
  prop from a prior navigation. The `pills` `$state` is initialized from `savedValues`
  on mount, but the `$effect` can OVERWRITE it whenever `form?.dockets` is truthy —
  even if that `form` is a stale failure response from a prior user action. This creates
  a double-pill scenario: savedValues seeds 1 pill, user tries to add 1 more = 2 pills,
  server guard fires.

test: "Trace what form.dockets contains when the user tries to add a second pill after a fresh page load showing one pre-populated pill"
expecting: "form.dockets is non-null (carried from prior save failure) and equals the pre-existing pill array, causing pills to be correct count — but the user already has pills from savedValues AND the $effect is not the issue here"
next_action: "Re-read the component mount logic. pills = $state(savedValues.dockets ?? []). On a fresh page load with no prior form, form=null, effect does not fire. User sees 1 pill from savedValues. User types a new docket, presses Enter → addPill() adds it → pills=['21-1271','22-0000'] → submit → guard fires. THIS IS THE CORRECT BEHAVIOR — only 1 docket is supported by the DB column. The bug is not a false positive in the guard; the guard is working as designed. The bug is that the UI allows adding a second pill when the schema only supports one."

## Symptoms

expected: "Add a docket pill (e.g. '21-1271'), click Save, reload the page — the pill is pre-populated. Then add another pill — should work OR UI should prevent it."
actual: "After reload with 1 pre-populated pill, trying to add a second pill shows server error: 'Only one docket number is supported. Please remove the extra entries.'"
errors: "Only one docket number is supported. Please remove the extra entries."
reproduction: "Have a job with one saved docket. Load the page. See 1 pre-populated pill. Type another docket and press Enter to add. Click Save. Error appears."
started: "Phase 23 CR-02 code review fix (commit ee7fc92a)"

## Eliminated

- hypothesis: "$effect overwrites pills with stale form.dockets on re-render causing phantom double-pills"
  evidence: "The $effect only fires when form?.dockets is set. On a fresh load after save, form=null, so effect does not fire. Pills are correctly set to [savedDocket] from savedValues init."
  timestamp: "2026-07-06"

## Evidence

- timestamp: "2026-07-06"
  checked: "ArgumentDetailsCard.svelte addPill() logic"
  found: "addPill() correctly deduplicates (if v && !pills.includes(v)). It does NOT limit to 1 pill. The frontend has no max-pills guard."
  implication: "The frontend allows adding pill #2. The server-side guard (CR-02, dockets.length > 1) then fires and rejects the save."

- timestamp: "2026-07-06"
  checked: "+page.server.ts saveJobMetadata action lines 374–379"
  found: "Guard: if (dockets.length > 1) return fail(400, { saveError: 'Only one docket number is supported...', dockets })"
  implication: "This guard was added as CR-02 in commit ee7fc92a. It correctly enforces the DB constraint. But the frontend offers no corresponding UX constraint — the pill widget allows adding a second pill freely."

- timestamp: "2026-07-06"
  checked: "load() function lines 122–128"
  found: "savedValues.dockets = argument.source_docket ? [argument.source_docket] : []. Always 0 or 1 pill from DB."
  implication: "After a fresh load with a saved docket, user sees exactly 1 pill. Adding another makes 2 → triggers guard."

- timestamp: "2026-07-06"
  checked: "23-REVIEW-FIX.md CR-02 description"
  found: "CR-02 added the server guard. The review notes that source_docket is a single string column. But no corresponding frontend constraint was added to prevent adding more than 1 pill."
  implication: "The fix was incomplete: backend rejects >1 docket but frontend still allows the user to create that invalid state."

## Resolution

root_cause: "The CR-02 code review fix (commit ee7fc92a) added a server-side guard rejecting >1 docket pill but did not add a corresponding frontend constraint in ArgumentDetailsCard.addPill() to prevent adding a second pill when one already exists — the UI freely allows building a 2-pill state that the server will always reject."
fix: "Add a max-pills guard in addPill(): if pills.length >= 1 return early (silently or with inline message). Alternatively, disable the docket input entirely when pills.length >= 1 to give clear UX feedback."
verification: ""
files_changed:
  - app/src/lib/components/ArgumentDetailsCard.svelte
