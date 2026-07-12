---
phase: 27-people-admin
verified: 2026-07-09T19:00:00Z
status: human_needed
score: 5/5 roadmap success criteria structurally verified
behavior_unverified: 1
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: "5/5 roadmap success criteria verified"
  gaps_closed:
    - "Blocking regression that prevented ANY UAT retest attempt: the `effect_update_depth_exceeded` infinite-loop on `/admin/people/[id]` (introduced by 27-10's CR-02 fix, commit b02a2681) is fixed by gap-closure plan 27-11 (commit 9651e27c). The person-id-change reset `$effect`'s `nextKey` $state variable is now written exactly once (`nextKey = resetKey;`, line 150), after a local non-reactive `resetKey` counter computes all intermediate `_key` values inside the `tenureRows` `.map()` callback (line 142) — the effect no longer reads `nextKey` during its own execution, eliminating the self-referential dependency Svelte's reactivity system was tracking."
  gaps_remaining: []
  regressions: []
gaps: []
deferred: []
behavior_unverified_items:
  - truth: "Justice Details card is collapsed by default; checking 'Is Justice' opens it with animation; unchecking hides fields without deleting tenure/appointment data (ROADMAP Success Criterion 4 / REQUIREMENTS.md PEDIT-07)"
    test: "(a) Open an existing Justice with >=1 tenure row and a birthdate, click 'Advocate', click 'Save Person', reload the page — confirm tenure rows and birthdate are unchanged, AND confirm no console errors / no effect_update_depth_exceeded / no navigation lag. (b) Merge person A into person B (redirects to /admin/people/{B}); on that page click 'Save Person' without further edits, reload — confirm B's tenure rows are B's own, not A's stale pre-merge rows. (c) As a smoke test independent of (a)/(b): simply open /admin/people/{id} for any Justice with >=1 tenure row and watch the browser console/network tab for a few seconds — confirm no repeated 'updated at' effect-rerun spam and no thrown Svelte error."
    expected: "In (a), the PATCH body's `tenures` array and `birthdate` field carry the Justice's real, unchanged values (not `[]`/`null`), the DB still shows the original tenure rows and birthdate after reload, and the page remains responsive throughout (no 3-5s lag, no thrown error). In (b), B's tenure rows after reload match B's own pre-merge tenures (or B's tenures plus any legitimately transferred from A via the merge's FK-transfer, not A's raw `tenureRows` array). In (c), the page settles after one effect run with no error."
    why_human: "This is a state-transition / data-preservation invariant (toggle-then-save, merge-then-save) plus a runtime reactivity-loop invariant (effect settles after one run), both of which only a live browser session can prove. Static/structural checks (grep for input position, input-name uniqueness, the write-only nextKey pattern, svelte-check) prove the code is present and correctly wired — reconfirmed in this pass, including the 27-11 fix — but cannot execute the runtime data flow or observe the Svelte reactivity scheduler settling. No unit/component/e2e test in the codebase exercises any of these three paths (confirmed via `find` for test/spec files in `app/` — none exist); 27-REVIEW.md's WR-07 finding explicitly notes this same gap in automated coverage. This is the exact test that was attempted in the 4th UAT retest and blocked by the now-fixed infinite loop before it could complete — it has not yet been re-attempted."
human_verification:
  - test: "Person-detail page loads without the effect_update_depth_exceeded loop (smoke test, unblocks everything else below)."
    expected: "Opening /admin/people/{id} for a Justice with >=1 tenure row shows no repeated 'updated at' console spam, no thrown 'Uncaught (in promise) Svelte error: effect_update_depth_exceeded', and normal click-to-navigation responsiveness (not the previously-reported 3-5s lag)."
    why_human: "This is exactly the runtime behavior a live browser session exercises that static analysis cannot: the debug session's own 'blind spot' note stated 'have not yet run the app in a browser to watch the actual console output' — this pass's structural re-trace (below) gives high confidence the fix is correct, but only a live reload proves the scheduler actually settles."
  - test: "CR-01 data-preservation round-trip: open an existing Justice with tenure rows + birthdate, click 'Advocate', click 'Save Person', reload."
    expected: "Tenure rows and birthdate are unchanged after reload (not wiped)."
    why_human: "State-transition/data-integrity invariant; requires a live browser + backend round-trip. No automated test exists. This is UAT Test 1, which failed on the (now-fixed) infinite loop before the actual save/reload could be observed — it has not yet been cleanly re-attempted."
  - test: "CR-02 data-preservation round-trip: merge person A into person B (redirects to /admin/people/{B}); on that page click 'Save Person' with no further edits, reload."
    expected: "B's tenure rows after reload are B's own (not A's stale pre-merge tenureRows array)."
    why_human: "State-transition/data-integrity invariant across a soft-navigation redirect; requires a live browser + backend round-trip. No automated test exists. This is UAT Test 2, blocked (not attempted) in the 4th retest."
  - test: "Bench/Advocate slide-reveal animation and visual token compliance re-check."
    expected: "Slide transition still animates smoothly (not fade/snap); colors/spacing still match DESIGN-SYSTEM.md tokens; toggling Advocate→Bench→Advocate still preserves in-progress tenure edits."
    why_human: "Animation fidelity is not type-checkable. This is UAT Test 3, blocked (not attempted) in the 4th retest."
  - test: "Column spacing visual re-check (27-07 fix, carried forward)."
    expected: "A clear horizontal gutter between Tenure coverage/Tenure gap (Bench tab) and Argument count/Missing fields (Advocate tab) columns."
    why_human: "Visual gutter perception cannot be assessed by grep/svelte-check. This is UAT Test 4, blocked (not attempted) in the 4th retest."
  - test: "President's Party dropdown round-trip (27-09 fix, carried forward)."
    expected: "Selected party persists across save/reload; any legacy out-of-list stored value still displays selected (not reset to blank) on load."
    why_human: "Full click-through round-trip cannot be exercised by static checks alone. This is UAT Test 5, blocked (not attempted) in the 4th retest."
  - test: "Create-person name-parts persistence, full click-through (27-08 fix, carried forward)."
    expected: "All four name-part fields (first/middle/last/suffix) show the submitted values when reopening the newly created person's editor."
    why_human: "Automated coverage proves each layer independently but not the full browser click-through flow. This is UAT Test 6, blocked (not attempted) in the 4th retest."
---

# Phase 27: People Admin Verification Report

**Phase Goal:** The people list is split into Bench and Advocate tabs with columns appropriate to each, a "Create person" button works before any argument exists, and the person editor consolidates all Justice-specific fields into a collapsible Justice Details card with appointment data now stored per tenure row

**Verified:** 2026-07-09T19:00:00Z
**Status:** human_needed
**Re-verification:** Yes — fifth phase-level verification pass. Prior pass (2026-07-09T15:10:00Z) found all 5 ROADMAP Success Criteria structurally verified but routed to `human_needed` pending a live UAT retest of the CR-01/CR-02 data-preservation fixes (27-10). That retest was attempted (`27-UAT.md`, 4th pass) and hit a NEW blocker on the very first test: a Svelte 5 `effect_update_depth_exceeded` infinite loop, diagnosed in `.planning/debug/person-detail-effect-loop.md` and fixed by gap-closure plan 27-11 (commit `9651e27c`). This pass independently re-traces the 27-11 fix against the live codebase (not merely re-reading 27-11-SUMMARY.md's or 27-REVIEW.md's narratives), confirms it is structurally correct and does not weaken CR-01/CR-02, and re-checks all other Success Criteria for regressions.

> **Why this pass does not reach `passed`.** The 27-11 fix removes the *blocker* that prevented the 4th UAT retest from being attempted at all — it does not, by itself, constitute the live-browser proof that Truth 4/PEDIT-07's data-preservation invariant holds. That proof requires a human to actually redo the round-trip clicks (UAT Tests 1-6) now that the page no longer throws. This pass's job was to determine whether the codebase now *supports* re-attempting that UAT retest — it does — and to keep Truth 4 correctly classified as behavior-unverified until that retest actually runs and passes.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria — the non-negotiable contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | People list titled "People", has Bench/Advocate tabs; Bench columns include tenure coverage + gap indicator; Advocate columns include argument count | ✓ VERIFIED | Unchanged since pass 4; not touched by 27-11 (single-file change confined to `[id]/+page.svelte`). `git log` shows no commits touching `app/src/routes/admin/people/+page.svelte` since the pass-4 baseline. |
| 2 | Click-to-filter missing-field pills work per tab; "Justices with tenure gaps" filter present and functional on Bench tab only | ✓ VERIFIED | Unchanged; not touched by 27-11. |
| 3 | "Create person" button navigates to a blank person editor — operator can create a Justice before any argument is uploaded | ✓ VERIFIED | Unchanged; not touched by 27-11 (`/admin/people/new` route untouched). |
| 4 | Justice Details card is collapsed by default; checking "Is Justice" opens it with animation; unchecking hides fields **without deleting tenure/appointment data** | ⚠️ **PRESENT_BEHAVIOR_UNVERIFIED** | Animation/collapse mechanism unchanged (`transition:slide` count = 1, line 503). The data-preservation defect (CR-01/CR-02) remains structurally fixed from pass 4 (re-confirmed below), AND the regression that blocked the 4th UAT retest from even attempting to observe this behavior (`effect_update_depth_exceeded`) is now structurally fixed (see Key Link Verification). This truth asserts a runtime state-transition invariant with no automated test coverage — presence + wiring is necessary but not sufficient, so it remains routed to human verification rather than marked VERIFIED. |
| 5 | Each tenure row in the editor contains Seat, Appointed by, Appointing president's party, Start date, and End date — data reads correctly from the migrated `court_tenures` columns | ✓ VERIFIED | Unchanged since pass 4; not touched by 27-11. |

**Score:** 5/5 roadmap Success Criteria structurally verified (1 of the 5 — Truth 4 — has its data-preservation clause, and its now-unblocked UAT retest, present/wired-but-behaviorally-unverified pending a live re-run; see `behavior_unverified_items`)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/src/routes/admin/people/[id]/+page.svelte` (person-id-change reset `$effect` — the `nextKey` self-referential read+write, 27-11's target) | The `nextKey` $state variable is written exactly once, after the `tenureRows` `.map()` completes, using a local non-reactive `resetKey` counter for intermediate reads | ✓ **VERIFIED** | Re-read lines 125-151 directly (not the debug session's cited line numbers, which had drifted per the plan's own instruction to confirm by content). Confirmed: line 133 `let resetKey = 1;` (plain local, not `$state`); line 142 `_key: resetKey++` inside the `.map()` callback; line 150 `nextKey = resetKey;` — the ONLY appearance of `nextKey` as an assignment target inside this effect, and it is never read back afterward within the same effect body. Grep gates from 27-11-PLAN.md's acceptance criteria all pass: `nextKey = 1;` count = 0, `nextKey = resetKey;` count = 1, `let resetKey = 1;` count = 1, `resetKey++` count = 1, `nextKey++` count = 2 (both remaining occurrences are the top-of-script initializer, line 65, and `addTenureRow`, line 77 — both run outside `$effect` and are unaffected, exactly as the plan required). |
| `app/src/routes/admin/people/[id]/+page.svelte` (CR-01 hidden inputs — must remain untouched by 27-11) | `birthdate`/`tenures` hidden inputs stay outside `{#if isJustice}` | ✓ **VERIFIED (unchanged)** | Lines 499-500 (`name="birthdate"`, `name="tenures"`, both `form="save-form"`) still directly precede `{#if isJustice}` (line 502) — confirmed byte-for-byte unaffected by the 27-11 diff (`git show 9651e27c` touches only lines 133/142/150-151, a 5-line diff: 3 insertions, 2 deletions). |
| Git commit history | 27-11's fix commit + summary commit exist with diffs matching the plan's stated scope | ✓ **VERIFIED** | `git show --stat 9651e27c` confirms 1 file changed (`app/src/routes/admin/people/[id]/+page.svelte`), 3 insertions / 2 deletions — a minimal, single-effect-scoped diff, matching 27-11-SUMMARY.md's claim exactly. `git show --stat bbd792fc` confirms the summary-only follow-up commit. Both present in `git log`, directly after `27-10`'s `b02a2681`/`bbc135b9`. |
| `svelte-check` baseline | 0 errors / 16 warnings, unchanged from pass 4 | ✓ **VERIFIED** | `cd app && npm run check` → `COMPLETED 797 FILES 0 ERRORS 16 WARNINGS 10 FILES_WITH_PROBLEMS` — identical to the pass-4 and pre-27-10 baseline. The two warnings on `[id]/+page.svelte` (lines 46, 47) are the pre-existing `data` state-referenced-locally warnings, unrelated to this fix. |
| `.planning/phases/27-people-admin/27-REVIEW.md` (updated re-verification of 27-11) | Confirms the 27-11 fix is correct and does not regress CR-01/CR-02; 0 new Critical findings attributable to 27-11 | ✓ **VERIFIED** | Read in full: explicitly states "27-11 regression check (verified, no regression)" with line-level citations matching this pass's independent re-trace. The review's one NEW Critical finding (CourtTenure rows omitted from merge/delete FK bookkeeping in `api/services/admin_people.py`) is unrelated to 27-11's scope and pre-dates this phase's tenure-editing UI (the underlying `CourtTenure` rows and FK constraint were introduced by Phase 22's migration, not Phase 27) — see Anti-Patterns below for scope assessment. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| Person-id-change reset `$effect` execution | Svelte reactivity scheduler settling (no infinite rerun) | `nextKey` write-only pattern (local `resetKey` counter, single trailing write) | ✓ **WIRED (fixed)** | Previously the effect read AND wrote the same `$state` variable (`nextKey`) synchronously within its own run — the literal condition Svelte's `effect_update_depth_exceeded` error names. Now `nextKey` is only ever written inside this effect, never read, matching the codebase's established write-only reset-effect convention (e.g. `admin/pipeline/[job_id]/+page.svelte:78`, confirmed unchanged). This breaks the self-referential dependency that caused the loop. |
| Bench/Advocate toggle → Save Person | Tenure/birthdate preservation on `is_justice=false` | Always-present hidden `tenures`/`birthdate` inputs (CR-01, 27-10) | ✓ WIRED (unchanged, re-confirmed) | Not touched by 27-11's diff — re-verified still outside `{#if isJustice}` at lines 499-500. |
| Merge redirect → component reuse | `tenureRows` state correctness for the new (target) person | Person-id-change `$effect` re-derives `tenureRows`/`nextKey` (CR-02, 27-10) | ✓ WIRED (unchanged, re-confirmed) | The effect still reads `data.person.tenures` (line 134) and reassigns `tenureRows`/`nextKey` on every person-id change (line 126 dependency), and now does so without looping. The CR-02 behavior itself (what gets reset, and when) is unchanged by 27-11 — only *how* the intermediate `_key` counter is computed changed. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `[id]/+page.svelte` person-id-change effect → `tenureRows`/`nextKey` | `data.person.tenures` | Re-derived fresh on every person-id change, now via a non-reactive intermediate counter | Yes — unchanged from pass 4 (27-11 changed only the counter mechanism, not the data source or the values produced) | ✓ FLOWING (unchanged) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `npm run check` (svelte-check) across the whole app | `cd app && npm run check` | `COMPLETED 797 FILES 0 ERRORS 16 WARNINGS 10 FILES_WITH_PROBLEMS` — identical baseline | ✓ PASS (no regression) |
| Self-referential `nextKey` read+write is eliminated | `grep -n 'nextKey = 1;\|nextKey = resetKey;\|let resetKey = 1;\|resetKey++\|nextKey++'` on `[id]/+page.svelte` | `nextKey = 1;`→0, `nextKey = resetKey;`→1, `let resetKey = 1;`→1, `resetKey++`→1, `nextKey++`→2 (both outside `$effect`) | ✓ PASS (matches 27-11-PLAN.md's exact acceptance gates) |
| CR-01 hidden inputs remain outside `{#if isJustice}` | `grep -n 'name="birthdate"\|name="tenures"\|{#if isJustice}\|transition:slide'` | `birthdate` line 499, `tenures` line 500, `{#if isJustice}` line 502, `transition:slide` line 503 (count 1) | ✓ PASS (no regression from 27-11) |
| Git commit trace for the 27-11 fix | `git show --stat 9651e27c` / `bbd792fc` | Both present with diffs matching stated scope (1 file / 3 ins / 2 del; summary-only doc commit) | ✓ PASS |
| No debt markers introduced | `grep -n "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER" -i` on `[id]/+page.svelte` | Only HTML `placeholder="Coming soon"` attributes (D-19 deferred-field UI, pre-existing, not code debt) | ✓ PASS (no blocker) |
| No unit/component/e2e test exists for the effect-loop, toggle-then-save, or merge-then-save behavior | `find app -iname "*.test.*" -o -iname "*.spec.*"` (excluding node_modules) | Empty result — no test files exist anywhere in `app/` | ✗ CONFIRMS GAP IN AUTOMATED COVERAGE (routed to human verification — this is why Truth 4 and the effect-loop fix cannot be marked fully VERIFIED by this pass alone) |

### Probe Execution

No `scripts/*/tests/probe-*.sh` probes exist in this project and none are referenced by Phase 27's plans/summaries/success criteria. Step 7c: SKIPPED (no probes declared or discovered).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| PDIR-01 | 27-04 | Page title "People" | ✓ SATISFIED | Unchanged, confirmed. |
| PDIR-02 | 27-02, 27-04 | Bench/Advocate tab toggle | ✓ SATISFIED | Unchanged, confirmed. |
| PDIR-03 | 27-02, 27-04, 27-07 | Bench columns: name, tenure coverage, tenure gap, completeness | ✓ SATISFIED | Unchanged, confirmed. |
| PDIR-04 | 27-02, 27-04, 27-07 | Advocate columns: name, argument count, completeness | ✓ SATISFIED | Unchanged, confirmed. |
| PDIR-05 | 27-02, 27-04 | Reworked per D-04 (click-to-filter pills replace toggle) | ~ REWORKED (per REQUIREMENTS.md, intentional) | Unchanged. |
| PDIR-06 | 27-02, 27-04 | "Justices with tenure gaps" filter, Bench-only | ✓ SATISFIED | Unchanged, confirmed. |
| PDIR-07 | 27-03, 27-04, 27-06 | "Create person" button, works before any argument exists | ✓ SATISFIED | Unchanged, confirmed. |
| PEDIT-01 | 27-05, 27-08 | First/middle/last/suffix name fields, same structure Bench/Advocate | ✓ SATISFIED | Unchanged, confirmed. |
| PEDIT-02 | 27-01, 27-03, 27-05 | Optional birthdate field | ✓ SATISFIED | Field works; CR-01 fix (structural) means the value is no longer silently deleted when the Bench/Advocate toggle is off at save time; behavioral round-trip pending human confirmation (see Truth 4). |
| PEDIT-03 | 27-05 | No prefix/rank field on person record | ✓ SATISFIED | Unchanged, confirmed. |
| PEDIT-04 | — | Superseded (D-10) | ✓ Correctly marked Superseded | Unchanged. |
| PEDIT-05 | 27-05 | "Upload photo" button label | ✓ SATISFIED | Unchanged, confirmed. |
| PEDIT-06 | 27-05 | Justice Details card, collapsed by default | ✓ SATISFIED | Unchanged, confirmed. |
| PEDIT-07 | 27-05, 27-06, 27-10, 27-11 | "Is Justice" toggle opens card with animation; unchecking hides fields but does not delete tenure or appointment data | ✓ **STRUCTURALLY SATISFIED** — behavior pending human confirmation | Animation/hide mechanism works; CR-01/CR-02 data-preservation code paths correctly wired (27-10); the 27-11 fix additionally removes the infinite-loop regression that blocked the live UAT retest of this exact requirement from even being attempted. REQUIREMENTS.md marks this row `[x] Complete` — accurate as a structural statement; the underlying behavioral round-trip has not yet been exercised live (see Human Verification). |
| PEDIT-08 | — | Superseded (D-10) | ✓ Correctly marked Superseded | Unchanged. |
| PEDIT-09 | 27-01, 27-03, 27-05, 27-09 | Tenure rows: Seat, Appointed by, Appointing president's party, Start date, End date | ✓ SATISFIED | Unchanged, confirmed. |
| PEDIT-10 | Phase 22 | Schema move: `appointed_by`/`appointing_president_party` to `court_tenures` | ✓ SATISFIED | Unchanged. |
| PEDIT-11 | 27-05, 27-06 | Merge card, unchanged | ✓ SATISFIED | Merge mechanism itself unchanged by 27-11 (out of scope, single-file diff confined to the effect). A separate, pre-existing latent defect (CourtTenure rows not accounted for in merge/delete FK bookkeeping — 27-REVIEW.md Critical finding) predates Phase 27 (the `CourtTenure` table and its FK constraint were introduced by Phase 22) and is not a regression from this phase's work — see Anti-Patterns for scope assessment; recommended for backlog capture, not a blocker of this requirement's "unchanged" claim. |
| PEDIT-12 | 27-06 | Delete card, unchanged | ✓ SATISFIED | Same scope note as PEDIT-11 above. |

**Orphaned requirements check:** All requirement IDs the phase task lists (PDIR-01..07, PEDIT-01,02,03,05,06,07,09,10,11,12; PEDIT-04/08 superseded) are claimed by at least one plan's `requirements:` frontmatter (27-01 through 27-11). No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `api/services/admin_people.py` | 522-636 | `CourtTenure` rows omitted from `get_merge_preview`/`merge_people`/`delete_person_if_orphan` — merging or deleting a Bench person with tenure rows raises an unhandled `IntegrityError` (27-REVIEW.md Critical finding) | ⚠️ Warning — real defect, but **out of this phase's declared scope** | This bug predates Phase 27: `CourtTenure` and its FK constraint were introduced by Phase 22's migration, and the merge/delete service functions were never updated for it in either Phase 22 or Phase 27 (PEDIT-11/PEDIT-12 explicitly scope those cards as "unchanged" — no plan in this phase touched `merge_people`/`delete_person_if_orphan`/`get_merge_preview`). Phase 27's ROADMAP Success Criteria and requirements do not mention merge/delete FK integrity for tenure rows. Recommend capturing as a standalone backlog item (999.x) rather than a Phase 27 gap-closure plan — it is real, plausible (any Justice with tenure data will hit it on merge/delete), and worth fixing soon, but is not something Phase 27 committed to deliver. Not treated as a blocker for this verification. |
| `app/src/routes/admin/people/[id]/+page.svelte:153-172` | fetchMergePreview / reset effect | Race condition (27-REVIEW.md WR-08): an in-flight merge-preview fetch is not cancelled on person-id-change, so a stale preview can briefly render after a redirect | ⚠️ Warning — minor, out of 27-11's scope | Pre-existing pattern (not introduced or touched by 27-11); noted in 27-REVIEW.md as a new finding from a broader review pass, not a Phase 27 must-have. |
| `api/schemas/admin_people.py` | 164, 174 | `TODO(D-10): orphaned by Phase 27 — person-level roles removed; safe to delete once confirmed.` | ⚠️ Warning (carried forward, not a blocker) | Unchanged since pass 3/4 — confirmed dead code, cosmetic technical debt, not a phase-goal blocker. |
| `api/services/admin_people.py` | 439-445 | Full-name auto-derivation silently overwrites a manually-typed "Full name" (27-REVIEW.md WR-06) | ⚠️ Warning (carried forward, pre-existing, not introduced by 27-10/27-11) | Not part of CR-01/CR-02/27-11 scope; already tracked as an open backlog item per ROADMAP.md line 486. |
| `app/src/routes/admin/people/[id]/+page.svelte` | — | Zero automated regression coverage for the effect-loop fix, toggle-then-save, or merge-then-save paths (27-REVIEW.md WR-07) | ⚠️ Warning | Direct cause of this pass's `human_needed` status — see Human Verification. Not a debt-marker comment, does not trigger the debt-marker gate. |

No `TBD`/`FIXME`/`XXX` debt markers found in the file modified by plan 27-11 (`app/src/routes/admin/people/[id]/+page.svelte`) — confirmed via targeted grep (the only "PLACEHOLDER"-adjacent matches are HTML `placeholder="Coming soon"` attributes on the intentionally-disabled D-19 fields, not code debt).

### Human Verification Required

The following items need a live browser session to confirm. None indicate a known defect — they are the behavioral proof this static-analysis pass cannot provide, and they are now unblocked by the 27-11 fix.

1. **Smoke test: the effect_update_depth_exceeded loop is actually gone (new, primary reason to re-attempt UAT now)**
   **Test:** Open `/admin/people/{id}` for a Justice with >=1 tenure row and watch the console/network tab for a few seconds.
   **Expected:** No repeated "updated at" effect-rerun spam, no thrown `effect_update_depth_exceeded`, and normal click-to-navigation responsiveness (not the previously-reported 3-5s lag).
   **Why human:** Exactly the runtime behavior static analysis cannot observe — the debug session's own diagnosis was code-reading-only and explicitly flagged this as a blind spot.

2. **CR-01 data-preservation round-trip (UAT Test 1 — blocked by the now-fixed loop, not yet cleanly re-attempted)**
   **Test:** Open an existing Justice with tenure rows and a birthdate. Click "Advocate." Click "Save Person." Reload the page.
   **Expected:** Tenure rows and birthdate are unchanged after reload — not wiped.
   **Why human:** State-transition/data-integrity invariant; requires the live SvelteKit form submission → FastAPI PATCH → Postgres write → reload round-trip. No automated test exercises this path.

3. **CR-02 data-preservation round-trip (UAT Test 2 — blocked by the now-fixed loop, not yet attempted)**
   **Test:** Merge person A into person B (this redirects to `/admin/people/{B}`). On that page, click "Save Person" without making further edits. Reload.
   **Expected:** B's tenure rows after reload are B's own (not A's stale pre-merge `tenureRows` array).
   **Why human:** Same class of invariant as item 2, across a soft-navigation redirect. No automated test exercises this path.

4. **Bench/Advocate slide-reveal animation re-check (UAT Test 3 — blocked, not yet attempted)**
   **Test:** Toggle Bench↔Advocate on `/admin/people/{id}` and observe the transition.
   **Expected:** Slide transition still animates smoothly (not fade/snap); DESIGN-SYSTEM.md token compliance; in-progress tenure edits still preserved across a Bench→Advocate→Bench toggle.
   **Why human:** Animation fidelity is not type-checkable.

5. **Column spacing visual re-check (UAT Test 4, 27-07 fix carried forward — blocked, not yet attempted)**
   **Test:** On `/admin/people`, view both the Bench tab and Advocate tab middle columns.
   **Expected:** Clear horizontal gutter between the two middle columns on each tab.
   **Why human:** Visual gutter perception cannot be assessed by grep/svelte-check.

6. **President's Party dropdown round-trip (UAT Test 5, 27-09 fix carried forward — blocked, not yet attempted)**
   **Test:** Select a party from the dropdown, save, reload; separately confirm a legacy out-of-list value still displays selected.
   **Expected:** Selection persists; legacy values preserved.
   **Why human:** Full click-through round-trip cannot be exercised by static checks alone.

7. **Create-person name-parts persistence, full click-through (UAT Test 6, 27-08 fix carried forward — blocked, not yet attempted)**
   **Test:** On `/admin/people/new`, fill in Full Name and all four name-part fields, submit, reopen the created person.
   **Expected:** All four name-part fields display the submitted values.
   **Why human:** Automated coverage proves each layer independently but not the full browser click-through flow.

### Gaps Summary

**No FAILED truths, artifacts, or key links in this pass.** The blocking regression that stopped the 4th UAT retest cold — `effect_update_depth_exceeded` on `/admin/people/[id]` — is confirmed structurally fixed by independent re-trace of the current codebase (not merely trusting 27-11-SUMMARY.md's or 27-REVIEW.md's narratives):

- **Root cause (confirmed):** The person-id-change reset `$effect` computed `tenureRows[i]._key` via `nextKey++` — reading AND writing the same `$state` variable (`nextKey`) synchronously within the effect's own execution — which Svelte 5 tracks as a self-referential dependency, causing an infinite rerun loop.
- **Fix (confirmed):** `nextKey`'s intermediate reads/increments now happen on a plain local `resetKey` counter (not `$state`); `nextKey` is written exactly once, after the loop, restoring the codebase's established write-only reset-effect convention. Grep gates from 27-11-PLAN.md's own acceptance criteria all pass exactly as specified.
- **No regression:** CR-01 (always-present hidden `birthdate`/`tenures` inputs) and CR-02 (tenure/nextKey re-derivation on person-id change, minus the buggy counter) both remain intact and unmodified in substance — 27-11's diff touches only the counter mechanism (3 insertions, 2 deletions, one file).
- `svelte-check` remains at the unchanged 0-errors/16-warnings baseline.

**Why this pass is `human_needed` rather than `passed`:** The 27-11 fix removes the *practical blocker* that prevented the 4th UAT retest from being attempted — it does not itself constitute the live-browser proof that Truth 4/PEDIT-07's data-preservation invariant holds, nor does it prove (from static analysis alone) that the reactivity scheduler now settles in an actual browser. Both are state-transition/runtime invariants with zero automated test coverage anywhere in `app/` (confirmed via `find`). This is the same class of gap flagged at pass 3/4 and in 27-REVIEW.md's WR-07 — not a new problem, and not one 27-11 was scoped to solve (27-11-PLAN.md explicitly deferred "re-attempting the CR-01/CR-02 behavioral round-trips as automated tasks" to the next UAT retest).

**Separately (not blocking):** 27-REVIEW.md's re-verification of 27-11 surfaced one new Critical finding — `CourtTenure` rows are omitted from the merge/delete FK bookkeeping in `api/services/admin_people.py`, which can raise an unhandled `IntegrityError` when merging/deleting a Bench person with tenure rows. This predates Phase 27 (the `CourtTenure` table and FK constraint were introduced by Phase 22), and no Phase 27 plan touched the merge/delete service functions (PEDIT-11/PEDIT-12 are explicitly scoped as "unchanged"). It is a real, plausible defect worth fixing soon, but it falls outside Phase 27's declared Success Criteria and requirements — recommend capturing it as a standalone backlog item rather than blocking this phase's gap-closure loop on it.

**Recommendation:** Re-attempt the 4th UAT retest now that the blocking loop is fixed. Start with the smoke test (Human Verification item 1) to confirm the page is usable, then proceed through UAT Tests 1-6 (items 2-7) in order. If all pass, Phase 27 can be considered fully closed without a 6th verification pass; if any fail, route the specific failure back through gap-closure planning as before.

---

*Verified: 2026-07-09T19:00:00Z*
*Verifier: Claude (gsd-verifier)*
