---
status: diagnosed
phase: 27-people-admin
source: [27-VERIFICATION.md]
started: 2026-07-09T11:25:00Z
updated: 2026-07-09T12:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Click-to-filter pill round-trip in a live browser
expected: URL updates to ?tab={tab}&missing={field}; table shows only matching rows; clicking again (or "Clear filter") returns to the unfiltered ?tab={tab} view.
result: issue
reported: "functional pass but the table spacing between argument count and missing fields is too tight"
severity: cosmetic

### 2. Bench/Advocate slide-reveal animation and visual token compliance
expected: On /admin/people/new and /admin/people/{id}, toggling Bench↔Advocate grows/shrinks the Person Type card's Birth Date/Death Date/Tenure Periods section (including the restored Seat field) via a slide transition (not a fade or instant snap); colors/spacing match .planning/codebase/DESIGN-SYSTEM.md tokens; switching Advocate→Bench→Advocate preserves any in-progress tenure edits, including a partially-typed Seat value.
result: issue
reported: "The animation works perfectly and preserves previous tenure entries. Seat and President's Party should both be dropdowns, though."
severity: minor

### 3. Photo/Merge/Delete gating on the create route
expected: Loading /admin/people/new shows a clean layout with only Identity and Person Type cards — no dangling whitespace or broken card boundaries where Photo, Biography, Merge, or Delete would normally sit.
result: pass

## Summary

total: 3
passed: 1
issues: 2
pending: 0
skipped: 0
blocked: 0

Note: Test 3 itself passed (Photo/Merge/Delete gating confirmed clean). The
tester found an additional, unrelated bug on the same page while testing it —
recorded below as a third Gaps entry (tagged to test 3 for provenance) without
changing test 3's own pass result.

## Gaps

- truth: "The Advocate-tab table's Argument count and Missing fields columns have adequate spacing between them"
  status: failed
  reason: "User reported: functional pass but the table spacing between argument count and missing fields is too tight"
  severity: cosmetic
  test: 1
  root_cause: "Both th/td pairs for these two middle columns use padding:0 horizontally (the codebase's edge-column convention) instead of the middle-column gutter convention (e.g. padding: 8px 8px, as used in admin/arguments/+page.svelte). Opposing text-align (right vs left) on facing columns pushes both flush against the same 0px-padded shared boundary, making them visually merge. The Bench tab has the identical latent defect on Tenure coverage/Tenure gap but it's invisible there since both are left-aligned."
  artifacts:
    - path: "app/src/routes/admin/people/+page.svelte"
      issue: "Argument count / Missing fields th+td pairs (~lines 224-308) use padding: 8px 0 / 12px 0 instead of a horizontal gutter"
  missing:
    - "Add horizontal padding (e.g. 8px) to the Argument count and Missing fields th/td pairs, matching admin/arguments/+page.svelte's middle-column convention"
    - "While there: same fix for Bench tab's Tenure coverage/Tenure gap columns for consistency (not visibly broken today, but same latent defect)"
  debug_session: ".planning/debug/people-list-argument-count-spacing.md"

- truth: "Bench/Advocate slide-reveal animation and visual token compliance"
  status: failed
  reason: >
    User reported: "The animation works perfectly and preserves previous
    tenure entries. Seat and President's Party should both be dropdowns,
    though." Follow-up from user after diagnosis: "the President's party
    should be a dropdown as I indicated but because the Seat is just two
    options for [justices] (Associate or Chief) then let's use the toggle
    component that we use for advocate/bench. If that's too far out of
    scope then we can defer it."
  root_cause: >
    Two different histories bundled in one report. (1) appointing_president_party
    free-text is an explicit, locked decision — 27-CONTEXT.md D-16 states
    verbatim "not dropdowns, not a curated president lookup," cited directly
    in TenureRow's docstring. The user has now explicitly asked to reverse
    D-16 for this one field. (2) seat free-text was never decided either
    way — D-18's mockup-derived field list simply omitted Seat entirely
    (27-05-SUMMARY.md flags this), and when Phase 27 verification caught the
    omission (PEDIT-09 gap) and the operator confirmed it was an oversight,
    the field was restored (commit 34bad2c8) as plain text by pattern-matching
    sibling fields — its *input type* was never litigated. Real historical
    data (CourtTenure.seat) includes specific numbered seats like "Associate
    Justice Seat 3", not just a Chief/Associate binary — collapsing to a
    2-option toggle per the user's request is a real data-model
    simplification with reconciliation implications for existing rows, not
    a pure UI swap.
  severity: minor
  test: 2
  artifacts:
    - path: "app/src/routes/admin/people/[id]/+page.svelte"
      issue: "President's Party rendered as type=\"text\" input (~line 564+); needs to become a dropdown/select"
    - path: "api/schemas/admin_people.py"
      issue: "TenureRow.appointing_president_party typed Optional[str] with no enum constraint; D-16 docstring reference needs updating to reflect the reversal"
    - path: ".planning/phases/27-people-admin/27-CONTEXT.md"
      issue: "D-16 needs an explicit amendment note recording that appointing_president_party (only) was reversed from free-text to a dropdown, post-ship, per operator request during UAT"
  missing:
    - "President's Party: convert to a dropdown/select populated with a sensible historical US political party list (derive from any existing appointing_president_party values already in the DB plus standard historical parties); keep appointed_by (president name) as free-text — D-16 is unchanged for that field"
    - "Seat-as-toggle: DEFERRED to backlog per user's own offered exit (\"if too far out of scope, we can defer it\") — real data-reconciliation scope (existing numbered-seat values vs a 2-option toggle) makes this a poor fit for a same-day gap-closure fix. Captured as backlog Phase 999.16."
  debug_session: ".planning/debug/tenure-seat-party-dropdown-request.md"

- truth: "Creating a person with both Full Name and first/last/middle/suffix name-part fields filled in persists all of them, matching the [id] editor's save behavior"
  status: failed
  reason: >
    User reported (found during test 3, unrelated to that test's own pass):
    "What is a real bug is that if I enter something into full name AND into
    the component parts it only saves the full name and discards the
    components. That only happens on person creation; it saves properly on
    saving an existing person."
  severity: major
  test: 3
  root_cause: "The create form renders First/Middle/Last/Suffix as live, named inputs alongside Full Name inside the same <form>, but the create action only ever reads full_name and is_justice from FormData — confirmed at three layers: the SvelteKit create action never calls formData.get() for the four name-part keys; PersonCreateRequest declares only full_name/is_justice; create_person's service docstring explicitly states name-part fields are left at column defaults (None). The [id] editor's save action is the working reference — it reads and forwards all four fields correctly. D-08 (27-CONTEXT.md) names only tenure/bio/photo/birthdate as deferred on create — it never mentions structured name parts, so this is an implementation gap in Plan 27-06 (and the corresponding 27-01/27-03 schema/service work), not a deliberate scope decision — a sibling defect to the already-flagged WR-03 (birthdate/tenures), just never caught for name parts specifically."
  artifacts:
    - path: "app/src/routes/admin/people/new/+page.server.ts"
      issue: "create action (lines ~56-95) never reads first_name/middle_name/last_name/name_suffix from FormData"
    - path: "api/schemas/admin_people.py"
      issue: "PersonCreateRequest (lines ~132-146) has no first_name/middle_name/last_name/name_suffix fields"
    - path: "api/services/admin_people.py"
      issue: "create_person (lines ~461-486) never sets name-part fields on the new Person row"
  missing:
    - "Add Optional[str]=None first_name/middle_name/last_name/name_suffix fields to PersonCreateRequest"
    - "create_person: set these fields on the new Person row when supplied"
    - "new/+page.server.ts's create action: read/trim/null-coerce the four FormData fields and include them in the POST body, mirroring [id]'s save action"
  debug_session: ".planning/debug/create-person-discards-name-parts.md"
