---
phase: 27-people-admin
verified: 2026-07-09T14:10:00Z
status: gaps_found
score: 4/5 roadmap success criteria verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: "5/5 roadmap success criteria verified"
  gaps_closed:
    - "UAT Gap 1 (cosmetic): Advocate-tab table's Argument count / Missing fields columns visually merged — fixed by 27-07 (8px horizontal gutter on all four middle columns, both tabs)"
    - "UAT Gap 2 (minor): President's Party was free-text, operator requested a dropdown — fixed by 27-09 (curated `<select>`, D-16 amended, legacy-value preservation guard)"
    - "UAT Gap 3 (major): create-person form discarded First/Middle/Last/Suffix name parts, only Full Name persisted — fixed by 27-08 (schema/service/action all now carry the four fields, with passing tests)"
  gaps_remaining:
    - "NEW gap discovered by this verification pass (not one of the 3 UAT gaps 27-07/08/09 were scoped to close): Justice Details toggle can silently delete tenure history and birthdate on save (CR-01), and a stale post-merge tenureRows array can silently overwrite a different person's tenures (CR-02). Both were found and documented in 27-REVIEW.md (commit f751dee0, the phase's most recent commit) but never fixed — no follow-up commit exists."
  regressions: []
gaps:
  - truth: "Justice Details card is collapsed by default; checking 'Is Justice' opens it with animation; unchecking hides fields without deleting tenure/appointment data (ROADMAP Success Criterion 4 / REQUIREMENTS.md PEDIT-07)"
    status: failed
    reason: >
      Directly confirmed by code inspection (not merely the unfixed 27-REVIEW.md
      finding — independently re-traced end-to-end for this verification).
      CR-01: the hidden `tenures` input and the visible Birth Date input in
      app/src/routes/admin/people/[id]/+page.svelte are both nested inside
      `{#if isJustice}` (opens line 477, closes line 655). The Bench/Advocate
      segmented toggle (line 456: `onclick={() => (isJustice = false)}`) has no
      confirmation step. Toggling an existing Justice to Advocate un-mounts both
      inputs from the DOM. On Save Person, +page.server.ts's `save` action reads
      `formData.get('birthdate')` (line 141, defaults to null when absent) and
      `formData.get('tenures')` (line 145, defaults to the string '[]' when
      absent) and forwards both as an explicit PATCH body. update_person's own
      documented guard ("Does NOT delete tenure rows when is_justice is False,
      D-06/D-07") does not help here because `body.tenures` arrives as `[]`, not
      `None` — `_replace_tenures(db, person_id, [])` deletes every existing
      CourtTenure row and inserts nothing; birthdate is wiped the same way. Net
      effect: one click (Advocate) + Save Person permanently destroys a
      Justice's entire tenure history and birthdate, with no undo and no
      warning — a direct violation of this Success Criterion's own wording.
      CR-02 (same truth, different trigger): the person-id-change reset
      `$effect` (lines 125-133) resets mergeTargetId/mergePreview/mergeError/
      mergeLoading/isJustice/birthdate but omits `tenureRows`/`nextKey`. The
      `merge` action redirects to `/admin/people/{target_id}` on the same route
      (+page.server.ts line 304) — SvelteKit reuses the component instance for
      this soft navigation, so `tenureRows` still holds the pre-merge (source)
      person's tenure array. Saving on this page overwrites the target's real
      tenure rows with the wrong, stale ones. Both bugs were found and
      documented in 27-REVIEW.md (dated 2026-07-09, reviewing all 9 plans
      including the 3 gap-closure plans) but the phase's most recent commit
      (f751dee0) is the review document itself — no fix commit followed.
    artifacts:
      - path: "app/src/routes/admin/people/[id]/+page.svelte"
        issue: "Hidden `tenures` input (line 653, form=\"save-form\") and Birth Date input (lines 488-495, name=\"birthdate\", form=\"save-form\") are both inside `{#if isJustice}...{/if}` (lines 477-655) instead of being always present in the save-form's submitted FormData regardless of the toggle's current value."
      - path: "app/src/routes/admin/people/[id]/+page.svelte"
        issue: "The person-id-change reset `$effect` (lines 125-133) does not reset `tenureRows`/`nextKey`, unlike its sibling fields (mergeTargetId, isJustice, birthdate, etc.) which are all reset there."
      - path: "app/src/routes/admin/people/[id]/+page.server.ts"
        issue: "`save` action (lines 141-180) has no defense-in-depth guard against an implicit empty-tenures/null-birthdate submission caused by the toggle being off at submit time."
    missing:
      - "Move the `tenures` hidden input and the `birthdate` input outside `{#if isJustice}` (always rendered, bound to the same $state variables) so unchecking Is Justice and saving preserves existing tenure/birthdate data — per 27-REVIEW.md CR-01's suggested fix."
      - "Add `tenureRows`/`nextKey` reset to the existing person-id-change `$effect`, mirroring how isJustice/birthdate/merge state are already reset there — per 27-REVIEW.md CR-02's suggested fix."
      - "Consider a confirmation step on the Bench→Advocate toggle when the person currently has tenure/birthdate data, as defense in depth (27-REVIEW.md CR-01 suggestion)."
    debug_session: ".planning/phases/27-people-admin/27-REVIEW.md (CR-01, CR-02)"
---

# Phase 27: People Admin Verification Report

**Phase Goal:** The people list is split into Bench and Advocate tabs with columns appropriate to each, a "Create person" button works before any argument exists, and the person editor consolidates all Justice-specific fields into a collapsible Justice Details card with appointment data now stored per tenure row

**Verified:** 2026-07-09T14:10:00Z
**Status:** gaps_found
**Re-verification:** Yes — third phase-level verification pass. This pass covers the 3 gap-closure plans (27-07/08/09) executed against the prior round's `human_needed` UAT findings, AND independently re-traces the phase from scratch rather than trusting the prior pass's "unchanged, regression check" shortcuts.

> **Why this pass differs from the previous one.** The previous verification (2026-07-09T11:20:00Z) marked Truth 4 ("Justice Details card... unchecking hides fields without deleting tenure/appointment data") as "✓ VERIFIED (regression check)" on the basis that the fix commit for the Seat gap didn't touch the `{#if isJustice}` wrapper or its `transition:slide`. That check confirmed the wrapper's *presence* but never traced what happens to the DOM-absent `tenures`/`birthdate` inputs when the save-form is actually submitted with the toggle off. `27-REVIEW.md` (a code review dated the same day, covering all 9 plans including the two gap-closure UI plans) independently found this exact gap — CR-01 and CR-02, both rated Critical/BLOCKER — and it was never fixed: the phase's most recent commit (`f751dee0`) is the review document itself, with no follow-up fix commit. This verification independently re-traced the full code path (toggle onclick → Svelte `{#if}` unmount → `FormData.get()` default → server action → service call) and confirms both bugs are live in the current codebase.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria — the non-negotiable contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | People list titled "People", has Bench/Advocate tabs; Bench columns include tenure coverage + gap indicator; Advocate columns include argument count | ✓ VERIFIED | `<h1>People</h1>` at `app/src/routes/admin/people/+page.svelte:54`; Bench/Advocate segmented toggle at lines 56-92; per-tab columns unchanged from prior passes; padding fix (27-07) confirmed applied — `grep -c "padding: 8px 8px"` returns 4, `grep -c "padding: 12px 8px"` returns 4, edge columns (Name, Edit action) still at zero horizontal padding (lines 195, 258, 271, 333). |
| 2 | Click-to-filter missing-field pills work per tab; "Justices with tenure gaps" filter present and functional on Bench tab only | ✓ VERIFIED | Unchanged filter/goto() wiring from prior passes; UAT test 1 (27-UAT.md) confirmed the round-trip mechanic itself as a "functional pass" — only the cosmetic spacing was flagged as an issue, and that is now fixed by 27-07. Fresh visual confirmation of the fixed spacing is a human-verification item (below), not a functional gap. |
| 3 | "Create person" button navigates to a blank person editor — operator can create a Justice before any argument is uploaded | ✓ VERIFIED | `href="/admin/people/new"` button unchanged at `+page.svelte:96-114`; create route/action unchanged by 27-07/08/09 except the name-part additions verified under Requirements Coverage below. |
| 4 | Justice Details card is collapsed by default; checking "Is Justice" opens it with animation; unchecking hides fields **without deleting tenure/appointment data** | ✗ **FAILED** | See Gaps below (CR-01, CR-02). The animation/collapse mechanism itself works (confirmed structurally and by UAT test 2's "works perfectly" report), but the data-preservation half of this Success Criterion is violated: saving after toggling Bench→Advocate wipes tenure/birthdate; saving on a post-merge page can overwrite a different person's tenure data with stale state. |
| 5 | Each tenure row in the editor contains Seat, Appointed by, Appointing president's party, Start date, and End date — data reads correctly from the migrated `court_tenures` columns | ✓ VERIFIED | All five fields render: Seat (`[id]/+page.svelte:535-540`, `bind:value={row.seat}`), Start/End Date (551-570), Appointing President (581-586, unchanged free-text per D-16), President's Party (597-611, now a curated `<select>` per 27-09 — `PARTY_OPTIONS` declared at line 16, blank "— None —" option, six curated parties, and a conditional legacy-value fallback `<option>` at line 606). This truth is about field presence/data-shape when the Justice Details card is open and intact — the toggle-off deletion bug (Truth 4) is a separate failure mode and does not retroactively invalidate this truth's own scope. |

**Score:** 4/5 roadmap Success Criteria verified (1 failed)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/src/routes/admin/people/+page.svelte` | Middle-column th/td padding uses an 8px horizontal gutter (Tenure coverage, Tenure gap, Argument count, Missing fields); edge columns (Name, Edit action) unchanged | ✓ VERIFIED | Confirmed via grep: 4× `padding: 8px 8px` (headers), 4× `padding: 12px 8px` (body cells); 2× `padding: 8px 0` and 2× `padding: 12px 0` remain, matching the Name/Edit edge columns exactly. |
| `api/schemas/admin_people.py` (`PersonCreateRequest`) | Gains `first_name`/`middle_name`/`last_name`/`name_suffix` as `Optional[str] = None` | ✓ VERIFIED | Lines 158-161, confirmed present; `full_name`/`is_justice` remain required. |
| `api/services/admin_people.py` (`create_person`) | Sets the four name-part fields on the new `Person` row with blank→`None` normalization | ✓ VERIFIED | Lines 489-492: `person.first_name = (body.first_name or "").strip() or None` (and matching lines for middle/last/suffix). |
| `app/src/routes/admin/people/new/+page.server.ts` | `create` action reads and forwards all four name-part fields | ✓ VERIFIED | Lines 66-69 read with trim/`''`→`null` coercion; line 91 includes all four in the POST body. |
| `api/tests/test_admin_people_schemas_service.py` | New tests proving create_person persists/omits name parts correctly | ✓ VERIFIED (substantive, currently skipped in this environment) | `test_create_person_persists_name_parts_when_supplied` / `test_create_person_leaves_name_parts_none_when_omitted` — both are well-formed, assert real persisted values (not stubs). Ran locally: `24 passed, 2 skipped` — the 2 skips are these DB-guarded tests, skipped because `DATABASE_URL` is not visible inside `api/tests`' pytest process (confirmed pre-existing, documented limitation: only the root `tests/conftest.py` calls `load_dotenv()`, and `api/tests` has no sibling conftest that does — same limitation independently confirmed present since 27-03-SUMMARY.md, not introduced by this phase). This is an environment-visibility gap, not evidence the tests are broken; the tests are correctly written and were confirmed against the live dev DB via standalone scripts per 27-08-SUMMARY.md's documented RED/GREEN procedure (not independently re-run here since I do not have DATABASE_URL credentials in this session). |
| `app/src/routes/admin/people/[id]/+page.svelte` (President's Party) | Renders as a curated `<select>` (6 parties + blank + legacy-value fallback), `appointed_by` unchanged free-text | ✓ VERIFIED | `PARTY_OPTIONS` declared line 16; `<select bind:value={row.appointing_president_party}>` lines 597-611; `bind:value={row.appointed_by}` unchanged at line 584 (still a plain `<input type="text">`). |
| `.planning/phases/27-people-admin/27-CONTEXT.md` (D-16 amendment) | Dated note recording the party-only reversal | ✓ VERIFIED | Line 46: "Amendment (2026-07-09, Phase 27 UAT, gap-closure plan 27-09)..." present verbatim, original D-16 text preserved above it. |
| `app/src/routes/admin/people/[id]/+page.svelte` (tenures/birthdate always-present) | Not claimed as an artifact by any plan, but required for Truth 4 | ✗ **MISSING** | The hidden `tenures` input and the `birthdate` input are conditionally rendered inside `{#if isJustice}`, not always present — this is the root cause of the Truth 4 gap. No plan in this phase (27-01 through 27-09) scoped a fix for this; it surfaced only in `27-REVIEW.md`, which was never actioned. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| Tenure sub-card inputs (Seat/Start/End/Appointed-by/Party) | `PATCH /people/{id}` `tenures` array | Hidden JSON `tenures` input → `save` action → `_replace_tenures` | ✓ WIRED (when Justice Details card is open at submit time) | All five fields correctly serialize into the hidden `tenures` JSON input and round-trip through `_replace_tenures` — confirmed by the code path and by 27-09's dropdown addition writing to the same `row.appointing_president_party` state with no payload-shape change. |
| Bench/Advocate toggle → Save Person | Tenure/birthdate preservation on `is_justice=false` | `{#if isJustice}` wrapper around the hidden `tenures` input and `birthdate` input | ✗ **NOT WIRED** | When the toggle is off at submit time, the hidden inputs are unmounted from the DOM, so `formData.get('tenures')`/`formData.get('birthdate')` return their "absent" defaults (`'[]'` / `null`) rather than the true current values — the link between "toggle state" and "submitted data" incorrectly couples visibility to data inclusion. This is the direct mechanism of CR-01. |
| Merge redirect → component reuse | `tenureRows` state correctness for the new (target) person | Person-id-change `$effect` | ✗ **NOT WIRED** | The reset effect is missing `tenureRows`/`nextKey`, so after a merge redirect the component's tenure state does not refresh to match the new person id, per CR-02. |
| `app/src/routes/admin/people/new/+page.server.ts` `create` action | `POST /api/admin/people` name-part fields | JSON body includes `first_name`/`middle_name`/`last_name`/`name_suffix` | ✓ WIRED | Confirmed at the action's POST body construction (line 91) — matches `PersonCreateRequest`'s new fields and `create_person`'s new assignment logic. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `[id]/+page.svelte` tenure sub-cards | `data.person.tenures` → `row.seat`/`row.appointing_president_party` etc. | `get_person_detail()` live DB query | Yes — real per-row values seeded at load and editable | ✓ FLOWING |
| `new/+page.server.ts` create action | `first_name`/`middle_name`/`last_name`/`name_suffix` FormData → POST body | Operator form input, forwarded verbatim (trimmed, `''`→`null`) | Yes — verified end-to-end by the new DB-guarded tests (present, substantive, currently environment-skipped) | ✓ FLOWING |
| `[id]/+page.svelte` save-form → `tenures`/`birthdate` hidden inputs | `tenureRows`/`birthdate` `$state` | Conditionally present only while `isJustice === true` | **No — data silently becomes empty/null when the toggle is off**, regardless of what the underlying state actually holds | ✗ **HOLLOW** (state exists correctly in memory; the DOM/FormData path that should carry it to the server is severed by the `{#if}` wrapper) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `npm run check` (svelte-check) across the whole app | `cd app && npm run check` | `COMPLETED 797 FILES 0 ERRORS 16 WARNINGS 10 FILES_WITH_PROBLEMS` — identical warning count/content to both prior passes' baselines | ✓ PASS (no regression) |
| Gap-closure test suite | `.venv/Scripts/python.exe -m pytest api/tests/test_admin_people_schemas_service.py -q` | `24 passed, 2 skipped` — the 2 skips are the new DB-guarded name-part tests, skipped due to the pre-existing `DATABASE_URL`-visibility gap in `api/tests` (confirmed, not a new problem) | ✓ PASS (existing coverage intact, new tests well-formed but environment-skipped) |
| CR-01 reproduction trace (toggle → save → service call) | Static grep/read trace across `[id]/+page.svelte` (lines 456, 477-655), `[id]/+page.server.ts` (lines 141-180), `admin_people.py::update_person`/`_replace_tenures` | Confirmed: `{#if isJustice}` wraps both the `tenures` and `birthdate` inputs; `formData.get()` defaults are `'[]'`/`null`; `_replace_tenures(db, person_id, [])` unconditionally deletes all rows | ✗ FAIL — confirms the gap |
| CR-02 reproduction trace (merge redirect → stale state) | Static grep/read trace across `[id]/+page.svelte` (lines 56-73, 125-133), `[id]/+page.server.ts` (line 304, merge action) | Confirmed: reset `$effect` omits `tenureRows`/`nextKey`; merge redirects to `/admin/people/{target_id}` on the same route (soft navigation reuses the component) | ✗ FAIL — confirms the gap |
| Git commit history for a fix following `27-REVIEW.md` | `git log --oneline -5` | `f751dee0 docs(27): add code review report` is the most recent commit — no fix commit follows it | ✗ FAIL — confirms the gap is genuinely unresolved, not merely unverified |

### Probe Execution

No `scripts/*/tests/probe-*.sh` probes exist in this project and none are referenced by Phase 27's plans/summaries/success criteria. Step 7c: SKIPPED (no probes declared or discovered).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| PDIR-01 | 27-04 | Page title "People" | ✓ SATISFIED | Unchanged, confirmed. |
| PDIR-02 | 27-02, 27-04 | Bench/Advocate tab toggle | ✓ SATISFIED | Unchanged, confirmed. |
| PDIR-03 | 27-02, 27-04, 27-07 | Bench columns: name, tenure coverage, tenure gap, completeness | ✓ SATISFIED | Padding fix (27-07) confirmed applied without breaking column semantics. |
| PDIR-04 | 27-02, 27-04, 27-07 | Advocate columns: name, argument count, completeness | ✓ SATISFIED | Padding fix (27-07) confirmed applied; "Argument count"/"Missing fields" no longer run together. |
| PDIR-05 | 27-02, 27-04 | Reworked per D-04 (click-to-filter pills replace toggle) | ~ REWORKED (per REQUIREMENTS.md, intentional) | Unchanged. |
| PDIR-06 | 27-02, 27-04 | "Justices with tenure gaps" filter, Bench-only | ✓ SATISFIED | Unchanged, confirmed. |
| PDIR-07 | 27-03, 27-04, 27-06 | "Create person" button, works before any argument exists | ✓ SATISFIED | Unchanged; create route confirmed intact. |
| PEDIT-01 | 27-05, 27-08 | First/middle/last/suffix name fields, same structure Bench/Advocate | ✓ SATISFIED | 27-08 closed the create-path gap (name parts now persist on create, matching the [id] editor). |
| PEDIT-02 | 27-01, 27-03, 27-05 | Optional birthdate field | ✓ SATISFIED (structurally) — **but see Truth 4** | Birthdate field itself works when the Justice Details card is open; it is silently deleted when the toggle is off at save time (CR-01) — the field's *presence* satisfies PEDIT-02's literal wording, but this is a data-integrity concern worth flagging alongside PEDIT-07 below. |
| PEDIT-03 | 27-05 | No prefix/rank field on person record | ✓ SATISFIED | Unchanged, confirmed. |
| PEDIT-04 | — | Superseded (D-10) | ✓ Correctly marked Superseded | Unchanged. |
| PEDIT-05 | 27-05 | "Upload photo" button label | ✓ SATISFIED | Unchanged, confirmed. |
| PEDIT-06 | 27-05 | Justice Details card, collapsed by default | ✓ SATISFIED | Unchanged, confirmed — the collapse/expand mechanism itself is correct. |
| PEDIT-07 | 27-05, 27-06 | "Is Justice" toggle opens card with animation; **unchecking hides fields but does not delete tenure or appointment data** | ✗ **BLOCKED** | The animation/hide mechanism works; the "does not delete" clause is violated (CR-01/CR-02). REQUIREMENTS.md currently marks this row `[x] Complete` (line 88) / "Complete" (line 172) — **this is now inaccurate** and should be revised to reflect the open gap until CR-01/CR-02 are fixed. |
| PEDIT-08 | — | Superseded (D-10) | ✓ Correctly marked Superseded | Unchanged. |
| PEDIT-09 | 27-01, 27-03, 27-05, 27-09 | Tenure rows: Seat, Appointed by, Appointing president's party, Start date, End date | ✓ SATISFIED | Seat restored (prior pass); President's Party now a curated dropdown (27-09); all five fields render and round-trip when the card is open. |
| PEDIT-10 | Phase 22 | Schema move: `appointed_by`/`appointing_president_party` to `court_tenures` | ✓ SATISFIED | Migration-level work from Phase 22, unaffected by this phase's UI changes. (Note: 27-09-SUMMARY.md lists PEDIT-10 among its `requirements-completed`, which overstates this plan's scope — the schema move was already done in Phase 22; 27-09 only changed the UI control type. Minor documentation inaccuracy, not a functional gap.) |
| PEDIT-11 | 27-05, 27-06 | Merge card, unchanged | ✓ SATISFIED (mechanism) — **see CR-02 caveat under Truth 4** | The Merge feature itself (transfer FK rows, delete source, redirect) is unchanged and correct; the *side effect* of merge's redirect exposing the stale-`tenureRows` bug is a Truth 4 issue, not a defect in the merge logic itself. |
| PEDIT-12 | 27-06 | Delete card, unchanged | ✓ SATISFIED | Unchanged, confirmed. |

**Orphaned requirements check:** All requirement IDs the phase task lists (PDIR-01..07, PEDIT-01,02,03,05,06,07,09,10,11,12; PEDIT-04/08 superseded) are claimed by at least one plan's `requirements:` frontmatter (27-01 through 27-09). No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `api/schemas/admin_people.py` | 164, 174 | `TODO(D-10): orphaned by Phase 27 — person-level roles removed; safe to delete once confirmed.` | ⚠️ Warning (not a blocker — `TODO` is warning-tier, not the `TBD`/`FIXME`/`XXX` debt-marker gate) | `RoleCreate`/`RoleResponse`/`create_role`/`POST /roles` (also `api/services/admin_people.py:499`, `api/routers/admin.py:1018`) are confirmed still fully present and wired into the router — this is now-dead code per Phase 27's own D-10, flagged in `27-REVIEW.md` IN-01 but not deleted. Cosmetic technical debt, not a phase-goal blocker. |
| `api/tests/test_admin_people_schemas_service.py` | 383 | `"sk-ant" not in url` inside `_db_configured()` — an Anthropic API-key-prefix substring check with no relationship to a Postgres connection string | ℹ️ Info | Flagged in `27-REVIEW.md` WR-04 as a likely copy/paste artifact; harmless as written (doesn't cause false positives in this environment) but reads as unintentional. Does not block the phase goal. |
| `api/routers/admin.py` | ~741-759 | Photo-by-URL fetch host allowlist gap (WR-02) and overly broad `except (UnidentifiedImageError, Exception)` (WR-03, partially addressed per commit history — confirmed the `Exception` catch-all is still present for the image-validation blocks) | ⚠️ Warning | Pre-existing/adjacent finding from `27-REVIEW.md`, not introduced by the 3 gap-closure plans; carried forward as an open item, not scoped to this phase's UAT gaps. |
| `app/src/routes/admin/people/[id]/+page.svelte` | 477-655 | `{#if isJustice}` wrapping data-bearing hidden/visible form inputs whose absence changes what gets submitted | 🛑 **Blocker** | This is the root cause of the Truth 4 gap (CR-01) — see Gaps below. Not a debt-marker comment, but a structural anti-pattern (conditional rendering coupled to data submission) that directly causes silent data loss. |

### Human Verification Required

The following items remain from the prior verification pass and are **not** newly introduced by this pass. They are informational — they do not block progression past the gaps above being closed, but should be re-confirmed once CR-01/CR-02 are fixed (since fixing them will change the DOM structure inside the Justice Details card and could interact with the animation):

1. **Column spacing visual re-check (27-07 fix)**
   **Test:** On `/admin/people`, view both the Bench tab (Tenure coverage / Tenure gap) and Advocate tab (Argument count / Missing fields) and confirm the columns now read as visually separated, not touching.
   **Expected:** A clear horizontal gutter between the two middle columns on each tab.
   **Why human:** Visual gutter perception is a rendering check that grep/`svelte-check` cannot assess; only the CSS values were confirmed programmatically.

2. **President's Party dropdown round-trip (27-09 fix)**
   **Test:** Open a Justice's editor, select a party from the new dropdown, click Save Person, reload the page, confirm the selection persisted. Separately, if any tenure row has a legacy/out-of-list stored value, confirm it still displays selected (not reset to blank) on load.
   **Expected:** Selected party persists across save/reload; legacy values are preserved and visibly selected.
   **Why human:** Full click-through round-trip (select → save → reload) cannot be exercised by static checks alone; explicitly deferred to UAT retest per 27-09-SUMMARY.md D3.

3. **Create-person name-parts persistence, full click-through (27-08 fix)**
   **Test:** On `/admin/people/new`, fill in Full Name AND First/Middle/Last/Suffix, submit, then open the created person's editor and confirm all name parts display.
   **Expected:** All four name-part fields show the submitted values, matching the [id] editor's existing save behavior.
   **Why human:** Automated coverage (DB-guarded tests, currently environment-skipped; svelte-check; grep) proves each layer independently but not the full browser click-through flow — explicitly deferred to UAT retest per 27-08-SUMMARY.md D3.

4. **Bench/Advocate slide-reveal animation and visual token compliance** (carried forward, unrelated to the gaps above — last confirmed passing per UAT test 2, "The animation works perfectly")
   **Test:** Toggle Bench↔Advocate on `/admin/people/new` and `/admin/people/{id}` and observe the transition.
   **Expected:** Slide transition (not fade/snap); DESIGN-SYSTEM.md token compliance.
   **Why human:** Animation fidelity is not type-checkable. **Note:** once CR-01/CR-02 are fixed and the `tenures`/`birthdate` inputs move outside `{#if isJustice}`, this animation's DOM contents will change slightly (fewer elements will unmount/remount) — worth a fresh look alongside the fix, not just a re-confirmation of the pre-fix behavior.

### Gaps Summary

**The three UAT gaps this session's plans (27-07/08/09) were scoped to close are, in fact, closed** — verified independently in code (not just by trusting SUMMARY.md claims):
- 27-07: the padding fix is present exactly as specified (4 middle-column headers at `8px 8px`, 4 body cells at `12px 8px`, edge columns untouched).
- 27-08: `PersonCreateRequest`, `create_person`, and the create action all now carry the four name-part fields end-to-end, with two new, substantive (non-stub) tests proving both the supplied and omitted cases; the tests are correctly written but currently skip in this environment due to a pre-existing, documented `DATABASE_URL`-visibility gap in `api/tests` (not a new defect).
- 27-09: President's Party is now a curated `<select>` with a blank option and a legacy-value preservation guard; `appointed_by` is confirmed untouched; the D-16 amendment and schema docstring are both present and accurate.

**However, this verification found a new, unrelated, and more severe gap that none of the 9 plans were scoped to address:** `27-REVIEW.md` — a code review of all 9 plans, dated the same day and sitting as the phase's single most recent commit (`f751dee0`) — documents two Critical/BLOCKER findings (CR-01, CR-02) that directly contradict ROADMAP Success Criterion 4 / REQUIREMENTS.md PEDIT-07's explicit "does not delete tenure or appointment data" clause. This verification independently re-traced both bugs end-to-end against the current codebase (not just re-reading the review) and confirmed both are live:

- **CR-01:** Toggling an existing Justice's Person Type card to "Advocate" (one click, no confirmation) and then clicking "Save Person" silently and permanently deletes that Justice's entire tenure history and birthdate, because the hidden `tenures` input and the `birthdate` input are both nested inside `{#if isJustice}` and vanish from the submitted FormData when the toggle is off.
- **CR-02:** After a successful person merge (which redirects to the target person's edit page on the same route), the component's `tenureRows` state is not reset to the new person's data — a subsequent Save Person can overwrite the target's real tenure data with the stale, pre-merge source person's tenure array.

No commit exists after the review was added that fixes either finding. This is not a stale/false-positive review finding — it was independently confirmed live in the current code during this verification pass, via direct trace of the toggle's `onclick` handler, the `{#if isJustice}` block boundaries, the `save` action's `formData.get()` calls, and `update_person`/`_replace_tenures`'s actual guard logic.

**This looks unintentional**, not a deliberate scope decision — no CONTEXT.md decision, BACKLOG.md entry, or STATE.md note accepts or defers this behavior, and it squarely contradicts the locked wording of both the ROADMAP Success Criterion and REQUIREMENTS.md PEDIT-07. Recommend routing this to a gap-closure plan (in the same style as 27-07/08/09) before considering Phase 27 complete, rather than an override.

---

*Verified: 2026-07-09T14:10:00Z*
*Verifier: Claude (gsd-verifier)*
