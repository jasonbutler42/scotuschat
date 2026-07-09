---
status: diagnosed
trigger: |
  DATA_START
  Investigate a Svelte 5 runes bug reported during UAT for Phase 27 (people-admin).
  Symptom: On the admin person-detail page, navigating/interacting causes the browser
  console to show repeated "updated at" effect reruns, then:
  "Uncaught (in promise) Svelte error: effect_update_depth_exceeded — Maximum update
  depth exceeded. This typically indicates that an effect reads and writes the same
  piece of state."
  Site also feels "crazy slow" (3-5s between click and navigation) — likely same loop
  pegging the main thread.
  Stack trace clues: $effect at +page.svelte:132:42, 133:14, 134:44 (inside Array.map
  at line 134, referenced again at line 142:9). Throws effect_update_depth_exceeded.
  Suspected regression from CR-01/CR-02 data-preservation fix (27-10).
  DATA_END
created: 2026-07-09T00:00:00Z
updated: 2026-07-09T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED — see Resolution.root_cause
test: Read app/src/routes/admin/people/[id]/+page.svelte lines 125-150; git show b02a2681 diff
expecting: n/a (diagnosis complete, goal: find_root_cause_only — fix not applied)
next_action: Hand off to fix plan. Proposed minimal fix documented in Resolution.fix (NOT YET APPLIED).

reasoning_checkpoint:
  hypothesis: "The person-id-change reset $effect (app/src/routes/admin/people/[id]/+page.svelte, lines 125-150) causes effect_update_depth_exceeded because inside the effect, the map callback at line 142 does `_key: nextKey++`, which both READS the $state variable `nextKey` (to compute the key) and WRITES it (increment) synchronously during the effect's own execution — after `nextKey = 1` (line 133) already wrote it once. Because `nextKey` is $state and is read during this same effect run, Svelte registers it as a tracked dependency; because the effect's own execution also mutates that dependency, Svelte reschedules the effect to rerun, which repeats the same read+write, forming an infinite loop until Svelte's internal max-rerun guard throws effect_update_depth_exceeded."
  confirming_evidence:
    - "Direct code read: lines 133-149 show `nextKey = 1;` followed by `.map((t) => ({ _key: nextKey++, ... }))` — nextKey is read (nextKey++) and written inside the same $effect body, only when tenureRows.length > 0 (i.e., a person with at least one tenure row, matching the Justice/CR-01/CR-02 UAT test case)."
    - "git show b02a2681 confirms this exact block (nextKey = 1; tenureRows = (...).map(...)) was newly added by the CR-02 fix — it did not exist in the effect before 27-10, and the bug was reported as a fresh regression right after that commit."
    - "The identical `nextKey++` pattern exists at the top-level script initializer (lines 54-73) and is safe there — because that code runs once during component init, NOT inside $effect, so it isn't tracked/re-triggered by Svelte's reactivity system. Moving the same code inside $effect (verbatim, per the plan's explicit 'mirror the initializer' instruction) is what introduces the self-referential dependency."
    - "Codebase convention check: every other $effect in this codebase that resets local $state from a prop (e.g. app/src/routes/admin/pipeline/[job_id]/+page.svelte:78 `$effect(() => { liveJob = data.job; });`) is write-only against the $state it assigns — it never reads back the same $state variable it just wrote in the same effect run. The new nextKey logic breaks that established convention."
  falsification_test: "If the loop were NOT caused by nextKey's read+write, then removing only the `nextKey = 1; tenureRows = (...).map(...)` block (added by b02a2681) while keeping the rest of the effect (data.person.id, mergeTargetId/mergePreview/mergeError/mergeLoading/isJustice/birthdate resets) unchanged would still exhibit the infinite-loop console spam. Reverting to the pre-b02a2681 effect body (git show b02a2681^:app/src/routes/admin/people/[id]/+page.svelte) is the direct falsification check — that prior version has no such reported bug in Phase 27's UAT history, corroborating that this exact added block is the cause."
  fix_rationale: "The fix must stop `nextKey` ($state) from being read during the effect's own synchronous execution while it's also being written in that same run. Using a plain local (non-reactive) counter variable to compute `_key` values, then writing the final count to `nextKey` exactly once at the end of the effect, preserves identical output values (same _key sequence, same final nextKey) while eliminating the read+write-of-same-dependency cycle. This addresses the root cause directly (the reactive read/write cycle) rather than a symptom (e.g. suppressing the error or debouncing the effect)."
  blind_spots: "Have not yet run the app in a browser to watch the actual console output and confirm rerun count / timing (no live repro executed — this is a static code-reading diagnosis, consistent with goal: find_root_cause_only / diagnosis-only mode requested by the caller). Have not confirmed there isn't a second, independent contributor to 'crazy slow site-wide' beyond this one effect (e.g. the poll effect in pipeline/[job_id]/+page.svelte) — but the reported error is specific to the person-detail page and the stack trace line numbers match this file exactly, so a second contributor is unlikely to be in scope for this specific symptom."

## Symptoms

expected: >
  Navigating to /admin/people/[id] (or between person-detail pages, e.g. after a
  merge redirect) should mount/reset the editor's local $state cleanly, with the
  person-id-change $effect running once per navigation and settling.
actual: >
  The $effect at +page.svelte:125-150 reruns repeatedly ("updated at" effect
  reruns visible in console), then throws
  "Uncaught (in promise) Svelte error: effect_update_depth_exceeded — Maximum
  update depth exceeded. This typically indicates that an effect reads and
  writes the same piece of state." Site-wide interactions feel "crazy slow"
  (3-5s between click and navigation), consistent with the infinite effect loop
  pegging the main thread before Svelte's guard trips.
errors: |
  Uncaught (in promise) Svelte error: effect_update_depth_exceeded
  Maximum update depth exceeded. This typically indicates that an effect reads
  and writes the same piece of state.
reproduction: >
  Open /admin/people/[id] for a person who has at least one CourtTenure row
  (e.g. a Justice). The person-id-change reset $effect runs on mount and on any
  data.person.id change (including post-merge soft-navigation redirects). Because
  tenureRows.length > 0 causes the .map callback (line 142) to execute at least
  once, nextKey++ is read+written inside the effect, triggering the loop. (On a
  person with zero tenure rows, .map's callback never runs, so the loop would not
  trigger — this likely explains why the bug wasn't caught by CR-01/CR-02's
  structural-only automated checks, which per 27-10-SUMMARY.md deferred the live
  click-through round-trip to this UAT retest.)
started: >
  Introduced by commit b02a2681 "fix(27-10): reset tenureRows/nextKey on
  person-id-change effect (CR-02)", part of Phase 27 Plan 10 gap-closure
  (2026-07-09), landed immediately before this UAT retest.

## Eliminated

- hypothesis: "isJustice/birthdate assignments inside the same effect (lines 131-132) cause the loop"
  evidence: "Both are write-only within the effect — the right-hand sides read `data.person.is_justice`/`data.person.birthdate` (props, not the local $state vars being assigned), and neither `isJustice` nor `birthdate` is read anywhere else inside the effect body. No self-referential read+write on these two variables."
  timestamp: 2026-07-09T00:00:00Z

- hypothesis: "tenureRows itself (the array $state) is read+written causing the loop"
  evidence: "tenureRows is only ever assigned (write) inside this effect; the effect never reads the current value of `tenureRows` during its own execution. The read+write conflict is specifically on `nextKey`, not `tenureRows`."
  timestamp: 2026-07-09T00:00:00Z

## Evidence

- timestamp: 2026-07-09T00:00:00Z
  checked: "app/src/routes/admin/people/[id]/+page.svelte lines 1-178 (full script block)"
  found: >
    Person-id-change reset $effect spans lines 125-150. Lines 126-133 write-only
    reset mergeTargetId/mergePreview/mergeError/mergeLoading/isJustice/birthdate/
    nextKey. Lines 134-149 recompute tenureRows via `.map()`, and inside that
    map callback (line 142) `_key: nextKey++` both reads and writes the $state
    variable `nextKey` set on line 133 just prior.
  implication: >
    This is the exact self-referential read+write Svelte's error message
    describes ("an effect reads and writes the same piece of state").

- timestamp: 2026-07-09T00:00:00Z
  checked: "git show b02a2681 -- app/src/routes/admin/people/[id]/+page.svelte"
  found: >
    Confirms the entire `nextKey = 1; tenureRows = (...).map(...)` block (lines
    133-149) was net-new, added by the CR-02 gap-closure fix, inserted directly
    into the pre-existing effect right after the isJustice/birthdate reset lines.
  implication: >
    Confirms this is a regression introduced by the CR-01/CR-02 fix (27-10),
    exactly as the caller suspected — not a pre-existing bug.

- timestamp: 2026-07-09T00:00:00Z
  checked: "Top-of-script tenureRows/nextKey initializer, lines 54-73 (same .map/nextKey++ shape)"
  found: >
    Identical `nextKey++` pattern exists here but runs once during component
    script initialization — NOT inside $effect — so Svelte's dependency tracker
    never observes it as a tracked read/write pair; it's ordinary imperative
    code, safe.
  implication: >
    The bug is specifically about relocating this snippet into a reactive
    $effect body, not about the snippet's logic in isolation. 27-10-SUMMARY.md's
    own decision note ("mirrors the top-of-script initializer's map callback
    verbatim... rather than extracting a shared helper") explains why the
    faithful copy-paste carried the nextKey++ idiom into a context where it
    behaves differently.

- timestamp: 2026-07-09T00:00:00Z
  checked: "grep for other $effect usages across app/src for established reset-effect convention"
  found: >
    Every other reset-style $effect in this codebase (e.g.
    app/src/routes/admin/pipeline/[job_id]/+page.svelte:78
    `$effect(() => { liveJob = data.job; });`) is write-only against the local
    $state it assigns; none read back the same $state variable they just wrote
    within the same synchronous effect run. No existing use of `untrack()`
    anywhere in app/src.
  implication: >
    The established codebase convention for these reset effects is "read props,
    write local $state, never read that local $state back in the same run."
    The minimal fix should restore that convention (local plain-variable
    counter) rather than introduce a new primitivo (`untrack`) not used
    elsewhere in this file/codebase.

## Resolution

root_cause: >
  In app/src/routes/admin/people/[id]/+page.svelte, the person-id-change reset
  $effect (lines 125-150) was extended by commit b02a2681 (CR-02 fix, Phase
  27-10) to re-derive `tenureRows` and `nextKey` on every person-id change. The
  added code sets `nextKey = 1;` (line 133) and then, inside the `.map()`
  callback that rebuilds `tenureRows` (line 134), computes each row's `_key` via
  `nextKey++` (line 142). Because `nextKey` is a `$state` variable, and this
  read-then-write happens synchronously inside the $effect's own body, Svelte's
  reactivity system tracks `nextKey` as a dependency of the effect AND observes
  the effect mutating that same dependency during its own run. This is the
  literal condition the runtime error names: "an effect reads and writes the
  same piece of state." Each run re-triggers another run, forming an infinite
  loop that pegs the main thread (explaining the "crazy slow" 3-5s click-to-nav
  lag) until Svelte's internal max-reruns guard trips and throws
  `effect_update_depth_exceeded`. This only manifests when the person being
  viewed has at least one tenure row (so `.map`'s callback actually executes at
  least once) — consistent with 27-10-SUMMARY.md deferring the live click-through
  round-trip check (which would have caught this) to this UAT retest.
fix: >
  PROPOSED, NOT YET APPLIED (diagnosis-only per instructions). Replace the
  reactive `nextKey` read+write inside the effect with a local, non-reactive
  counter, and write to the $state `nextKey` exactly once, after the loop
  completes (write-only, matching this codebase's established reset-effect
  convention — see Evidence). No new imports, no `untrack()`, no shared helper
  function — minimal, in-place restructuring of the existing block.

  Before (lines 133-149, from commit b02a2681):

      nextKey = 1;
      tenureRows = (data.person.tenures ?? []).map(
          (t: {
              seat: string | null;
              start_date: string | null;
              end_date: string | null;
              appointed_by: string | null;
              appointing_president_party: string | null;
          }) => ({
              _key: nextKey++,
              seat: t.seat ?? '',
              start_date: t.start_date ?? '',
              end_date: t.end_date ?? '',
              appointed_by: t.appointed_by ?? '',
              appointing_president_party: t.appointing_president_party ?? '',
          })
      );

  After (proposed):

      let resetKey = 1;
      tenureRows = (data.person.tenures ?? []).map(
          (t: {
              seat: string | null;
              start_date: string | null;
              end_date: string | null;
              appointed_by: string | null;
              appointing_president_party: string | null;
          }) => ({
              _key: resetKey++,
              seat: t.seat ?? '',
              start_date: t.start_date ?? '',
              end_date: t.end_date ?? '',
              appointed_by: t.appointed_by ?? '',
              appointing_president_party: t.appointing_president_party ?? '',
          })
      );
      nextKey = resetKey;

  `resetKey` is a plain local `let` (not `$state`), so incrementing it inside
  the map callback is not tracked by Svelte's reactivity system at all — it
  behaves exactly like the safe top-of-script initializer (lines 54-73).
  `nextKey` ($state) is now only ever WRITTEN inside this effect, never READ,
  restoring this codebase's existing write-only reset-effect convention (e.g.
  pipeline/[job_id]/+page.svelte:78) and eliminating the self-referential
  dependency that caused the infinite loop.
verification: >
  NOT YET PERFORMED (fix not applied). Recommended verification for the fix
  plan/execution stage:
    1. Apply the proposed change to lines 133-149.
    2. Open /admin/people/[id] for an existing Justice with >=1 tenure row —
       confirm no console errors/effect-rerun spam, and navigation feels
       responsive (no 3-5s lag).
    3. Re-run the CR-01/CR-02 regression check this bug was found during:
       toggle Bench -> Advocate -> Save Person -> reload — tenure rows and
       birthdate must still be preserved (CR-01 unaffected: this fix does not
       touch the hidden-input relocation from commit bbc135b9).
    4. Re-run the CR-02 check: merge person A into person B, landing on
       /admin/people/{B} via soft-navigation redirect -> confirm tenureRows/
       nextKey re-derive to B's own tenures (not stale A data) -> Save Person ->
       reload -> B's tenures are B's own. This fix preserves that exact
       behavior (same final `tenureRows`/`nextKey` values), only changing how
       the intermediate counter is computed.
    5. svelte-check should remain at the existing 0 errors / 16 warnings
       baseline (per 27-10-SUMMARY.md).
files_changed: []
