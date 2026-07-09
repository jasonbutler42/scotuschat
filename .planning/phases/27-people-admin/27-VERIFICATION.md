---
phase: 27-people-admin
verified: 2026-07-09T11:20:00Z
status: human_needed
score: 5/5 roadmap success criteria verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: "4/5 roadmap success criteria verified (1 failed)"
  gaps_closed:
    - "Each tenure row in the editor contains Seat, Appointed by, Appointing president's party, Start date, and End date (ROADMAP Success Criterion 5 / REQUIREMENTS.md PEDIT-09)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Click-to-filter pill round-trip in a live browser"
    expected: "URL updates to `?tab={tab}&missing={field}`; table shows only matching rows; clicking again returns to the unfiltered `?tab={tab}` view."
    why_human: "Static grep/build checks confirm the onclick/goto() wiring and the allow-listed server-side filter, but not the actual rendered click-through experience."
  - test: "Bench/Advocate slide-reveal animation and visual token compliance"
    expected: "Content grows/shrinks via a slide transition (not a fade or instant snap); colors/spacing match .planning/codebase/DESIGN-SYSTEM.md tokens; switching Advocate→Bench→Advocate preserves any in-progress tenure edits (now including the restored Seat input)."
    why_human: "Animation behavior and visual fidelity cannot be confirmed by npm run check/npm run build alone."
  - test: "Photo/Merge/Delete gating on the create route"
    expected: "Clean layout with only Identity and Person Type cards, no dangling whitespace or broken card boundaries."
    why_human: "Layout/spacing correctness under card removal is a visual judgment, not a type-check-able property."
---

# Phase 27: People Admin Verification Report

**Phase Goal:** The people list is split into Bench and Advocate tabs with columns appropriate to each, a "Create person" button works before any argument exists, and the person editor consolidates all Justice-specific fields into a collapsible Justice Details card with appointment data now stored per tenure row

**Verified:** 2026-07-09T11:20:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (fix commit `34bad2c8`)

> This is the second phase-level verification pass for Phase 27. The initial pass (2026-07-09T06:04:45Z) found exactly one gap: ROADMAP Success Criterion 5 / REQUIREMENTS.md PEDIT-09 requires each tenure row to display Seat, Appointed by, Appointing president's party, Start date, and End date, but the shipped editor had no Seat input anywhere (data round-tripped correctly server-side; only the UI template omitted it). The user was asked whether this was an intentional deviation (per D-18's mockup-derived field list) or an oversight, and confirmed it was an oversight. Commit `34bad2c8` ("fix(27): restore Seat field to the tenure period editor (PEDIT-09 gap)") adds the missing input. This re-verification focuses full three-level scrutiny on that fix and does a regression sanity check on everything else.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria — the non-negotiable contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | People list titled "People", has Bench/Advocate tabs; Bench columns include tenure coverage + gap indicator; Advocate columns include argument count | ✓ VERIFIED (regression check — unchanged) | No files under `app/src/routes/admin/people/+page.*` were touched by commit `34bad2c8`; re-confirmed `<h1>People</h1>`, tab toggle, and per-tab columns still present in `app/src/routes/admin/people/+page.svelte`. |
| 2 | Click-to-filter missing-field pills work per tab; "Justices with tenure gaps" filter present and functional on Bench tab only | ✓ VERIFIED (regression check — unchanged) | Same file untouched by the fix commit; pill/filter code unchanged from initial pass. Live browser click-through still not exercised — see Human Verification. |
| 3 | "Create person" button navigates to a blank person editor — operator can create a Justice before any argument is uploaded | ✓ VERIFIED (regression check — unchanged) | `app/src/routes/admin/people/new/+page.server.ts`/`+page.svelte` untouched by the fix commit; route ordering and create action unchanged. |
| 4 | Justice Details card is collapsed by default; checking "Is Justice" opens it with animation; unchecking hides fields without deleting tenure/appointment data | ✓ VERIFIED (regression check — mechanism changed from checkbox to toggle per D-13, unchanged this pass) | The fix commit only inserted a new `<div>`/`<label>`/`<input>` block inside the existing `{#if isJustice}<div transition:slide>` wrapper (lines 459-628) — the wrapper, its `transition:slide`, and the `tenureRows` $state mutators (`addTenureRow`/`removeTenureRow`) are byte-for-byte unchanged outside the new block. Confirmed by reading the full diff (19 insertions / 4 deletions, entirely additive except for a removed comment). |
| 5 | Each tenure row in the editor contains Seat, Appointed by, Appointing president's party, Start date, and End date — data reads correctly from the migrated `court_tenures` columns | ✓ VERIFIED | **Gap closed.** `app/src/routes/admin/people/[id]/+page.svelte` lines 506-523 now render a "Seat" `<label>`/`<input id="tenure-seat-{row._key}">` as the first field inside each Tenure Period sub-card, `bind:value={row.seat}` — the exact same `TenureRow.seat` field that was already declared in the `TenureRow` interface (line 14) and already populated from `data.person.tenures[].seat` (line 48). Confirmed live-data path end-to-end: `+page.server.ts`'s `save` action (lines 161-166) already mapped `seat` into the PATCH body pre-fix and is unchanged — so the previously-orphaned render gap is now closed with zero backend/schema changes needed, exactly as the initial report predicted. All five fields — Seat, Start Date, End Date, Appointing President, President's Party — are now present in the rendered template (Reason Left remains intentionally disabled per D-19, unrelated to this gap). |

**Score:** 5/5 roadmap Success Criteria verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/src/routes/admin/people/[id]/+page.svelte` | Tenure Period sub-card renders Seat/Start/End/Appointed-by/Party inputs, each `bind:value` to the corresponding `TenureRow` field | ✓ VERIFIED (previously ⚠️ VERIFIED with 1 field gap) | Seat input added at lines 506-523, `id="tenure-seat-{row._key}"`, `bind:value={row.seat}`, styled consistent with the other four tenure-row inputs (same background/border/padding/font tokens). No other part of the file changed except the removal of a now-stale explanatory comment about `seat` being deliberately unrendered. |
| `app/src/routes/admin/people/[id]/+page.server.ts` | `save` action maps `row.seat` into the PATCH `tenures` payload | ✓ VERIFIED (unchanged, confirmed still correct) | Lines 161-166: `tenures = tenuresParsed.map(({ seat, start_date, end_date, appointed_by, appointing_president_party }) => ({ seat, ... }))` — `seat` was already included before the fix and required no change. File has zero diff from the initial pass. |
| `app/src/routes/admin/people/new/+page.svelte` | Tenure UI not rendered at all pre-save (unchanged scope) | ✓ VERIFIED (unchanged, not part of this gap) | Confirmed unchanged — the create route still renders no tenure fields of any kind (D-08: Birth Date/Tenure Periods "intentionally omitted on the create route" since they need a person id to attach to). This was correctly identified in the initial pass as inherited, not an independent instance of the Seat gap, and remains true after the fix. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| Tenure sub-card inputs | `PATCH /people/{id}` `tenures` array | Hidden JSON `tenures` input → `save` action → `_replace_tenures` | ✓ WIRED (previously ⚠️ PARTIAL) | All five tenure-row fields — including the newly-rendered Seat input — now round-trip: `bind:value={row.seat}` mutates the same `TenureRow[]` `$state` array serialized into the hidden `tenures` JSON input (line 626, unchanged), which the `save` action's existing (unchanged) mapping forwards to FastAPI's `_replace_tenures`, previously confirmed live against person id 8's real `seat: "Captain"` row. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `[id]/+page.svelte` tenure sub-cards | `data.person.tenures` → `row.seat` | `get_person_detail()` live DB query | Yes — person id 8's `seat: "Captain"` is now rendered as the input's initial value (`row.seat` seeded from `t.seat ?? ''` at load, line 48, unchanged) and is editable/re-savable through the new input | ✓ FLOWING (previously ✓ FLOWING but unrendered — now fully closed) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `npm run check` (svelte-check) on the fixed file | `cd app && npm run check` | 0 errors, 16 pre-existing unrelated warnings — identical count/content to the initial pass's baseline (same warning lines, including the two pre-existing `state_referenced_locally` warnings on `[id]/+page.svelte` lines 28/29/39, untouched by this fix) | ✓ PASS (no regression) |
| Diff scope check | `git show --stat 34bad2c8` | `1 file changed, 19 insertions(+), 4 deletions(-)` — only `app/src/routes/admin/people/[id]/+page.svelte` touched; no backend/schema/migration files changed | ✓ PASS (confirms the initial report's prediction that this was a UI-only fix) |
| Working-tree scope check (no untracked scope creep in the phase's admin/people routes) | `git log --oneline -5 -- app/src/routes/admin/people` + `git status --short` | `34bad2c8` is the only new commit since the initial verification touching this path; no uncommitted changes to any phase-27 route file | ✓ PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` probes exist in this project and none are referenced by Phase 27's plans/summaries/success criteria. Step 7c: SKIPPED (no probes declared or discovered) — unchanged from initial pass.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| PEDIT-09 | 27-01, 27-03, 27-05 | Tenure rows contain Seat, Appointed by, Appointing president's party, Start date, End date | ✓ SATISFIED (previously ✗ BLOCKED) | Seat field now rendered and wired end-to-end; REQUIREMENTS.md's PEDIT-09 row ("Complete") is now accurate without needing a supersession/rework annotation, since the shipped behavior now matches the locked wording exactly rather than deviating from it. |

All other requirement rows (PDIR-01..07, PEDIT-01,02,03,05,06,07,10,11,12; PEDIT-04/08 correctly Superseded per D-10) are unchanged from the initial pass — no file supporting those rows was touched by commit `34bad2c8`. See the initial verification's Requirements Coverage table for full detail; re-confirmed no orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/src/routes/admin/people/[id]/+page.svelte` | 506-509 | New comment: "Restored per phase 27 verification gap closure" | ℹ️ INFO | Explanatory comment documenting the fix, references the gap it closes — not a TBD/FIXME/XXX/TODO/HACK debt marker, does not trigger the debt-marker gate. |

All previously-found anti-patterns (`TODO(D-10)` markers referencing the tracked D-10 decision; the pre-existing dead `first_name`/`last_name` fields on `+page.server.ts`'s local `PersonListItem`; the docstring rollback-guarantee wording) are unchanged — none are in the file touched by this fix, so they are not re-scanned in detail here. No unreferenced `TBD`/`FIXME`/`XXX` markers found in the fix commit's diff.

### Human Verification Required

Unchanged from the initial pass — these three items were flagged by the plan executors (`human_judgment: true` in 27-04/27-05/27-06 SUMMARY.md coverage blocks) and are unrelated to the Seat gap. They were present at the initial verification too, but the ordered status-decision tree gave `gaps_found` (rule 1, the failed Seat truth) precedence over `human_needed` (rule 2) at that time. Now that the Seat gap is closed and no truth/artifact/link fails, these three still-open items are what determines this pass's `human_needed` status:

1. **Click-to-filter pill round-trip in a live browser**
   **Test:** On `/admin/people`, click a missing-field pill, confirm the table filters and the "Filtering by … · Clear filter" line appears; click the pill again (or "Clear filter") and confirm it resets.
   **Expected:** URL updates to `?tab={tab}&missing={field}`; table shows only matching rows; clicking again returns to the unfiltered `?tab={tab}` view.
   **Why human:** Static grep/build checks confirm the `onclick`/`goto()` wiring and the allow-listed server-side filter, but not the actual rendered click-through experience.

2. **Bench/Advocate slide-reveal animation and visual token compliance**
   **Test:** On `/admin/people/new` and `/admin/people/{id}`, toggle Bench↔Advocate and observe the Person Type card's Birth Date/Death Date/Tenure Periods section — now including the restored Seat field.
   **Expected:** Content grows/shrinks via a slide transition (not a fade or instant snap); colors/spacing match `.planning/codebase/DESIGN-SYSTEM.md` tokens; switching Advocate→Bench→Advocate preserves any in-progress tenure edits, including a partially-typed Seat value.
   **Why human:** Animation behavior and visual fidelity cannot be confirmed by `npm run check`/`npm run build` alone.

3. **Photo/Merge/Delete gating on the create route**
   **Test:** Load `/admin/people/new` and confirm there is no visual gap where the Photo, Biography, Merge, or Delete cards would normally sit.
   **Expected:** Clean layout with only Identity and Person Type cards, no dangling whitespace or broken card boundaries.
   **Why human:** Layout/spacing correctness under card removal is a visual judgment, not a type-check-able property.

### Gaps Summary

**The one gap from the initial verification is closed.** Commit `34bad2c8` adds a Seat text input to the Tenure Period sub-card in `app/src/routes/admin/people/[id]/+page.svelte`, positioned first (matching PEDIT-09's locked field order), bound via `bind:value={row.seat}` to the pre-existing `TenureRow.seat` state that already flowed correctly through load, save-payload mapping, and backend persistence. This was confirmed to be an oversight (not an intentional D-18 deviation) and the fix required no backend, schema, or migration changes — exactly as the initial report's suggested remediation predicted. Requirements coverage for PEDIT-09 is now ✓ SATISFIED without needing a REQUIREMENTS.md amendment, since the shipped behavior now matches the locked wording rather than diverging from it.

Regression check confirms the fix is scoped exactly as claimed: `git show --stat` shows only the one file changed (19 insertions, 4 deletions, entirely additive plus one removed stale comment); `npm run check` reports the identical 0-errors/16-warnings baseline as the initial pass; no other phase-27 route file has any uncommitted or newly-committed change since the initial verification.

**Overall status is `human_needed`, not `passed`**, because three pre-existing, unrelated human-verification items (live browser pill-filter round-trip, slide animation/visual-token fidelity, and create-route layout gating) remain open from the initial pass and were never resolved — they were simply masked by the higher-precedence `gaps_found` status in the first report. Per the status decision tree, any non-empty human-verification list routes the phase to `human_needed` once no gaps remain. None of these three items are new or introduced by the Seat fix.

---

*Verified: 2026-07-09T11:20:00Z*
*Verifier: Claude (gsd-verifier)*
