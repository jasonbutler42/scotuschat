---
status: complete
phase: 49-review-model
source: 49-01-SUMMARY.md, 49-02-SUMMARY.md, 49-03-SUMMARY.md, 49-04-SUMMARY.md, 49-05-SUMMARY.md, 49-06-SUMMARY.md
started: 2026-08-24T00:38:02Z
updated: 2026-08-24T14:06:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running API/dev server. Start the stack from scratch. `alembic upgrade head` applies migrations 0028 and 0029 without error, api/main.py boots with no startup exception, and a primary query returns live data (GET /api/admin/review/stats returns counts; the admin dashboard loads).
result: pass
injected: cold-start (3 new alembic migrations + api/main.py touched this phase)

### 2. Dev Tools — Seed unresolved speaker button
expected: On /admin, click "Reset to Fixture", then click "Seed unresolved speaker". The button renders in Dev Tools and its success line appears. This also sets up tests 3 and 5.
result: pass
evidence_ref: 49-EVIDENCE.md §9 item 8 (order step a)

### 3. Speakers card — unresolved placeholder (26-UAT Test 26)
expected: Open the Complexity fixture's argument edit page. The Speakers card shows the "Unresolved — choose a role" placeholder and the Save button is disabled.
result: issue
reported: "Yes, I can see what you describe and it works as indicated, however, there's no option to choose bench or advocate. If a speaker is unverified, then I would expect their bench side to be editable"
severity: major
evidence_ref: 49-EVIDENCE.md §9 item 5 (order step b)
coverage_id: 49-06 D3

### 4. /admin/review — Confirm vs "Resolve speaker" link conditional
expected: On /admin/review, an unresolved constituent renders a "Resolve speaker" link pointing at /admin/pipeline/{admin_job_id} (falling back to /admin/arguments/{id}), not a Confirm button. A needs_review constituent with a person renders Confirm.
result: issue
reported: "Edit correctly links to the pipeline run for that argument but I'd prefer if it was action verb as an established pattern in most places. So something like \"Edit pipeline\" makes sense since it takes you to the pipeline run for it, but maybe \"Edit draft\" since that's the state it's in. Also: when did we start calling something \"constituent\"?"
severity: minor
note: |
  Conditional itself VERIFIED from operator screenshot + code: no plain Confirm on a
  person_id-IS-NULL row (+page.svelte:507 guard), "Confirm as unattributable" present
  (:514), link destination correct (argumentEditHref :215-219 -> /admin/pipeline/{admin_job_id}),
  operator confirmed the destination by following it. The defects are in the copy, not the logic.
evidence_ref: 49-EVIDENCE.md §9 item 1 (order step c)
coverage_id: 49-01 D6

### 5. /admin/review — full screen walkthrough (7 items)
expected: On /admin/review — (1) Arguments|People tab switching works; (2) filter composition survives a back-button press and the active-filter indicator shows; (3) expand/collapse toggles live, including the zero-constituent blockers fallback; (4) Confirm / Confirm-as-unattributable / Re-flag act on the correct row and the row stays visible with its new badge (D-26); (5) all five dashboard StatCards sit evenly in one row; (6) the StatCard's singular and zero-state link text read correctly; (7) no horizontal scroll at 375px.
result: issue
reported: "Let's just say that I like the review tab! 1: pass; 2: pass; 3: pass; 4: pass; 5: pass; 6: not sure where to see this; 7: fail. small screens cause horizontal scrolling."
severity: minor
note: |
  Sub-item breakdown (operator-reported, then 49-08 update below):
    (1) tab switching ........................ pass
    (2) filter composition survives back ..... pass
    (3) expand/collapse + blockers fallback .. pass
    (4) Confirm / unattributable / Re-flag ... pass
    (5) five StatCards evenly in one row ..... pass (49-08: still pass — re-verified as an
        executable arithmetic gate, `_tracks_that_fit(812, 120, 32) == 5`; not traded away
        for sub-item 7's fix)
    (6) StatCard singular + zero-state text .. STILL NOT OBSERVED (needs queue total==1 and ==0;
        operator's queue had 2+. Site: admin/+page.svelte:338-358. 49-08 could not drive this
        state either — no browser access, see missing[] above)
    (7) no horizontal scroll at 375px ........ STRUCTURALLY FIXED by 49-08 (three overflow-x:
        auto containers + auto-fit grid track floor), NOT YET VISUALLY RE-CONFIRMED — the
        browser pass is blocked by the same credential-access gap as sub-item 6. Do not read
        this as "pass" until an operator has looked at 375px.
evidence_ref: 49-EVIDENCE.md §9 item 4 (order step c)
coverage_id: 49-05 D4, 49-05 D5

### 6. Discrepancy badge — authority-conflict visual rendering
expected: On /admin/review, the Discrepancy badge for the seeded authority-conflict row renders with correct color and placement, and clicking it reveals both values with their provenance. (Data/API layer already verified end-to-end by script.)
result: pass
note: |
  Scenario had to be constructed — no Dev Tools button exists for it (admin_dev.py has only
  reset-to-fixture and seed-unresolved-speaker). 49-EVIDENCE.md section 5a's script hardcodes
  argument 1793 / participant 3586, which reset_to_fixture reassigns, so a self-discovering
  variant was used instead (scratchpad/seed_discrepancy.py; needs
  PYTHONPATH=<repo root> for a file-based run, unlike the transcript's stdin invocation).
  Verified live via GET /api/admin/review/arguments before the operator looked:
    Baltimore & Ohio Railroad Company v. United States, docket 642, attention 2
      participant 3663 | person_id None | UNKNOWN    | needs_review    | discrepancy False
      participant 3662 | person_id 1834 | PETITIONER | operator_edited | discrepancy True
        descriptor | existing 'Lead counsel for petitioner (operator edit)' (corpus/direct)
                   | incoming 'Counsel of record (corpus re-import)'       (corpus/direct)
  REJECT_AND_RECORD fired for the RIGHT reason: authority_rank (api/domain/authority.py:103)
  resolves review_state=operator_edited to OPERATOR before ever reading source/method (D-22 —
  an operator edit deliberately does NOT rewrite stored source/method), so OPERATOR strictly
  outranked the incoming CORPUS write. NOT the equal-authority-rejects tiebreak.
  UNREPORTED OBSERVATION (not an operator finding, promote to a gap only if wanted): because
  stored source/method is intentionally left alone, both sides of the discrepancy line print
  (corpus/direct), so the rendering never conveys that the surviving value won on OPERATOR
  authority. Display-only; the data and the decision are both correct.
evidence_ref: 49-EVIDENCE.md §9 item 7 (order step c)
coverage_id: 49-06 D4

### 7. CreatePersonPopover — Bench/Advocate side inheritance
expected: Toggle a row to Bench, open "Create new bench person" — Bench is pre-selected. Close and reopen — still Bench (reset returns to the inherited side, not a hardcoded default). Create a person — the Resolved As box shows the new person's full name. Repeat on an Advocate row.
result: pass
note: |
  Operator observed correct behavior on every leg they exercised — recorded as pass on that basis.
  DOES NOT CLOSE WR-01. The defective code shape 49-REVIEW.md/49-VERIFICATION.md describe is still
  present verbatim in app/src/lib/components/CreatePersonPopover.svelte:
    :48  let side = $state<'BENCH'|'ADVOCATE'>(initialSide)   <- captured once at mount
    :59  side = initialSide                                    <- only inside resetForm()
    :67  if (!next) resetForm()                                <- resync on CLOSE only
    (no $effect tracking initialSide)
  Why the pass is consistent with the defect still existing: resetForm() runs on close and re-reads
  initialSide at that moment, so both 'toggle row -> open' and 'close -> toggle -> open' render the
  correct side. The stale value is only reachable when the row's side changes WHILE the popover is
  already open, which a normal walkthrough does not hit.
  ACTION: do NOT tick 49-VERIFICATION.md human_verification item 1 on the strength of this pass.
  WR-01 remains open by explicit scope decision (Criticals only this pass); the fix-vs-defer call
  it asks for is still outstanding.
evidence_ref: 49-EVIDENCE.md §9 item 2 (order step d)
coverage_id: 49-03 D1, 49-03 D2

### 8. /admin/help — visual and apolitical read-through
expected: /admin/help is reachable from AdminSubNav and documents the four lifecycle statuses, four trust tiers (derive_tier's seven rules), four review_state values (D-24/D-25 transitions), and publish_argument's two ordered gates. Badge colors render correctly, no horizontal scroll at 375px, and no speaker ranking or comparison language by eye.
result: pass
evidence_ref: 49-EVIDENCE.md §9 item 3 (order step d)
coverage_id: 49-03 D4

### 9. Public chat page — non-interactive unresolved avatar (14-UAT Test 8)
expected: Publish the Complexity fixture, then open its public chat page. The avatar for the unresolved utterance is non-interactive. Note: leaves a fixture in a modified state until the next reset.
result: pass
reported: "the functionality passes but there's a styling issue as seen in the screenshot. Notice the alignment issue for Lloyd N. Cutler. The same thing happens on an utterance. We have an upcoming phase that will build a design system that should address one-off strangeness like this so I leave it up to you if it should be fixed now or later."
note: |
  Functionality (the non-interactive avatar itself) PASSES — operator confirmed.
  Operator reported an alignment defect alongside it and delegated the fix-now-vs-defer call.
  DIAGNOSIS (not glyph-related, not pre-existing drift): a padding asymmetry between the two
  branches of the interactive/non-interactive avatar split THIS PHASE introduced.
    resolved   (person_id != null) -> <button style="...padding:6px..."> wrapping a 32px circle
                                      => 44x44 layout footprint
    unresolved (person_id == null) -> bare <div>, no wrapper, no padding
                                      => 32x32 layout footprint
  Both live in a `display:flex; align-items:center; gap:8px` row, so the unresolved avatar is
  12px narrower; its circle shifts ~6px and drags the following name text with it. Lloyd N.
  Cutler is the ONLY affected row because he is the seeded unresolved speaker — every other
  advocate is resolved and therefore button-wrapped. Reproduces on the utterance bubble because
  ChatBubble.svelte carries the identical branch.
  Classified as a PHASE 49 REGRESSION, not design-system debt: the non-interactive branch was
  added by this phase for the very behavior this test checks (14-UAT Test 8 / 49-06 D3).
  FIXED IN SESSION (3 sites, one property each — margin:6px on the bare-div branch so it
  occupies the same 44px footprint as the button, leaving the 32px circle untouched):
    app/src/routes/cases/[slug]/arguments/[id]/+page.svelte:218  (bench, #94a3b8)
    app/src/routes/cases/[slug]/arguments/[id]/+page.svelte:252  (advocates, #93c5fd)
    app/src/lib/components/ChatBubble.svelte:80
  Chose margin over padding deliberately: padding on a border-radius:50% box would have grown
  the visible circle to 44px; margin preserves the 32px circle and only corrects the footprint.
  Distinguished from WR-01 (deferred): WR-01 needs a behavioral decision, this needed none.
  NEEDS OPERATOR RE-CONFIRMATION in the browser — the fix is verified by test suite + geometry
  reasoning, not yet by eye.
evidence_ref: 49-EVIDENCE.md §9 item 6 (order step e)
coverage_id: 49-06 D3

### 10. Participant editability interim state (decision confirmation — not a browser check)
expected: Confirm the widened editability reading is what you intended: every unpublished lifecycle state (candidate/draft/unpublished) is editable and only PUBLISHED is read-only. The frontend readonlyMode split that 49-04 and 49-05 both deferred was closed in 49-06 (resolveCardReadonly / metadataReadonly), so this is no longer an interim state.
result: pass
note: |
  Operator ratified the widened reading verbatim: every unpublished lifecycle state
  (candidate / draft / unpublished) is editable, and ONLY PUBLISHED is read-only.
  This closes 49-04 D3's open scope question. Not a browser check — a decision confirmation.
  The frontend readonlyMode split 49-04 and 49-05 both deferred was closed in 49-06
  (resolveCardReadonly / metadataReadonly), so this is shipped behavior, not an interim state.
coverage_id: 49-04 D3

### 11. review_state PG enum (4 permanent values) + argument_participants.review_state/source/method columns, migration 0028
expected: review_state PG enum (4 permanent values) + argument_participants.review_state/source/method columns, migration 0028
result: pass
source: automated
coverage_id: 49-01 D1

### 12. _load_constituents feeds derive_tier real per-participant (source, method, review_state) values instead of contributing nothing (D-18)
expected: _load_constituents feeds derive_tier real per-participant (source, method, review_state) values instead of contributing nothing (D-18)
result: pass
source: automated
coverage_id: 49-01 D2

### 13. GET /api/admin/review/arguments (D-05 OR-composed inclusion query, one row per argument) and PATCH /api/admin/review/participants/{id} confirm action
expected: GET /api/admin/review/arguments (D-05 OR-composed inclusion query, one row per argument) and PATCH /api/admin/review/participants/{id} confirm action
result: pass
source: automated
coverage_id: 49-01 D3

### 14. Tracer feedback gate defect 1 fix — deterministic constituent ordering (side, id) so a confirmed row never moves in the list
expected: Tracer feedback gate defect 1 fix — deterministic constituent ordering (side, id) so a confirmed row never moves in the list
result: pass
source: automated
coverage_id: 49-01 D4

### 15. Tracer feedback gate defect 2a fix — Confirm rendered only for needs_review constituents; backend rejects (422) a confirm on a person_id-IS-NULL participant
expected: Tracer feedback gate defect 2a fix — Confirm rendered only for needs_review constituents; backend rejects (422) a confirm on a person_id-IS-NULL participant
result: pass
source: automated
coverage_id: 49-01 D5

### 16. Migration 0029: people.review_state + people.provenance_metadata replace the two Phase 38 columns outright; one deterministic legacy mapping (name_needs_review=true -> needs_review), a straight envelope carry, clean-reverse downgrade
expected: Migration 0029: people.review_state + people.provenance_metadata replace the two Phase 38 columns outright; one deterministic legacy mapping (name_needs_review=true -> needs_review), a straight envelope carry, clean-reverse downgrade
result: pass
source: automated
coverage_id: 49-02 D1

### 17. REVIEW-05: no parallel mechanism survives — neither legacy Person field appears anywhere outside migration history, migration-specific tests, or downgrade() bodies, proven by an AST-based structural sweep (not convention)
expected: REVIEW-05: no parallel mechanism survives — neither legacy Person field appears anywhere outside migration history, migration-specific tests, or downgrade() bodies, proven by an AST-based structural sweep (not convention)
result: pass
source: automated
coverage_id: 49-02 D2

### 18. Every consumer moves with the schema: admin_people schemas/service, 4 SvelteKit files, 2 pipeline import commands, the drift-report script, and every existing test module — no broken repo mid-fold
expected: Every consumer moves with the schema: admin_people schemas/service, 4 SvelteKit files, 2 pipeline import commands, the drift-report script, and every existing test module — no broken repo mid-fold
result: pass
source: automated
coverage_id: 49-02 D3

### 19. An authoritative name edit sets review_state=operator_edited (D-11) and leaves provenance_metadata byte-identical (D-12); an importer's confident write sets UNREVIEWED, never an operator state (D-08/D-11/D-24)
expected: An authoritative name edit sets review_state=operator_edited (D-11) and leaves provenance_metadata byte-identical (D-12); an importer's confident write sets UNREVIEWED, never an operator state (D-08/D-11/D-24)
result: pass
source: automated
coverage_id: 49-02 D4

### 20. Argument Status card's resolve-pipeline-completion timestamp is labelled 'Resolved', not 'Created'
expected: Argument Status card's resolve-pipeline-completion timestamp is labelled 'Resolved', not 'Created'
result: pass
source: automated
coverage_id: 49-03 D3

### 21. api/domain/authority.py: the pure write-acceptance authority ladder (AuthorityRank, WriteDecision, authority_rank, decide_write) with a fail-closed UNKNOWN rung and an equal-authority-rejects boundary, exhaustively matrix-tested (50 rank x rank x differs cases + a count guard + named behavior tests)
expected: api/domain/authority.py: the pure write-acceptance authority ladder (AuthorityRank, WriteDecision, authority_rank, decide_write) with a fail-closed UNKNOWN rung and an equal-authority-rejects boundary, exhaustively matrix-tested (50 rank x rank x differs cases + a count guard + named behavior tests)
result: pass
source: automated
coverage_id: 49-04 D1

### 22. The ONE authority-gated writer (apply_participant_value_change/apply_person_value_change/record_value_discrepancy/close_open_discrepancies) — update_participant_side, update_resolve_row_for_job, and update_person all delegate their value writes through it; no second, ungated write path to those columns survives
expected: The ONE authority-gated writer (apply_participant_value_change/apply_person_value_change/record_value_discrepancy/close_open_discrepancies) — update_participant_side, update_resolve_row_for_job, and update_person all delegate their value writes through it; no second, ungated write path to those columns survives
result: pass
source: automated
coverage_id: 49-04 D2

### 23. Fixes the pre-existing test_admin_jobs_service.py regression (WINDOWS.md #11, now marked fixed): resolve_job and update_resolve_row_for_job backfill ArgumentParticipant.source/.method from the job's parse-step ImportRun when never stamped, so a freshly-resolved corpus participant reads TRUSTED instead of floor-UNCERTAIN
expected: Fixes the pre-existing test_admin_jobs_service.py regression (WINDOWS.md #11, now marked fixed): resolve_job and update_resolve_row_for_job backfill ArgumentParticipant.source/.method from the job's parse-step ImportRun when never stamped, so a freshly-resolved corpus participant reads TRUSTED instead of floor-UNCERTAIN
result: pass
source: automated
coverage_id: 49-04 D4

### 24. D-17: confirm_unattributable on a person_id-IS-NULL participant lifts the trust floor to VERIFIED; an ordinary confirm on the same row is rejected with a distinct tagged error and never lifts the floor as a side effect; reflag is the only backward transition (never to unreviewed); a resolve action closes multiple open discrepancies with one shared resolved_at
expected: D-17: confirm_unattributable on a person_id-IS-NULL participant lifts the trust floor to VERIFIED; an ordinary confirm on the same row is rejected with a distinct tagged error and never lifts the floor as a side effect; reflag is the only backward transition (never to unreviewed); a resolve action closes multiple open discrepancies with one shared resolved_at
result: pass
source: automated
coverage_id: 49-04 D5

### 25. D-34: the public-leak ban covers trust_tier, review_state, source, method, incoming_value, existing_value, and resolved_at across the full public model graph (7x case growth), an AST scan additionally bans importing api.domain.authority/api.schemas.admin_review from public schemas, and the false-green guard is extended to prove ReviewQueueConstituent (admin-only) DOES carry review_state
expected: D-34: the public-leak ban covers trust_tier, review_state, source, method, incoming_value, existing_value, and resolved_at across the full public model graph (7x case growth), an AST scan additionally bans importing api.domain.authority/api.schemas.admin_review from public schemas, and the false-green guard is extended to prove ReviewQueueConstituent (admin-only) DOES carry review_state
result: pass
source: automated
coverage_id: 49-04 D6

### 26. list_review_queue_arguments/list_review_queue_people gain status × tier × review_state filters with an unrecognised-value-applies-no-filter allow-list convention, and the full D-03 deterministic sort (published-degraded first, tier rank, argued_date ASC NULLS LAST, Argument.id ASC tie-break — never created_at, which does not exist on Argument)
expected: list_review_queue_arguments/list_review_queue_people gain status × tier × review_state filters with an unrecognised-value-applies-no-filter allow-list convention, and the full D-03 deterministic sort (published-degraded first, tier rank, argued_date ASC NULLS LAST, Argument.id ASC tie-break — never created_at, which does not exist on Argument)
result: pass
source: automated
coverage_id: 49-05 D1

### 27. get_review_queue_stats + GET /api/admin/review/stats: dedicated COUNT queries sharing the exact inclusion predicates the list queries use, never materializing the unbounded list
expected: get_review_queue_stats + GET /api/admin/review/stats: dedicated COUNT queries sharing the exact inclusion predicates the list queries use, never materializing the unbounded list
result: pass
source: automated
coverage_id: 49-05 D2

### 28. Each argument item carries a real summarize_tier_blockers breakdown, so a zero-flagged-constituent degraded row has something real to show in the expanded panel (49-05 <planner_decisions> E5 empty)
expected: Each argument item carries a real summarize_tier_blockers breakdown, so a zero-flagged-constituent degraded row has something real to show in the expanded panel
result: pass
source: automated
coverage_id: 49-05 D3

### 29. seed_unresolved_speaker_fixture produces a NULL-person_id ArgumentParticipant row on the real Complexity fixture, idempotently, with the trust tier recomputed, and the endpoint is genuinely absent (404, not 403) outside development
expected: seed_unresolved_speaker_fixture produces a NULL-person_id ArgumentParticipant row on the real Complexity fixture, idempotently, with the trust tier recomputed, and the endpoint is genuinely absent (404, not 403) outside development
result: pass
source: automated
coverage_id: 49-06 D1

### 30. The seeder reproduces the EXACT states 26-UAT Test 26 (side=UNKNOWN) and 14-UAT Test 8 (Utterance.person_id IS NULL) need — not just an unresolved participant row
expected: The seeder reproduces the EXACT states 26-UAT Test 26 (side=UNKNOWN) and 14-UAT Test 8 (Utterance.person_id IS NULL) need — not just an unresolved participant row
result: pass
source: automated
coverage_id: 49-06 D2

### 31. _argument_attention_predicate gains a fourth leg (open participant discrepancy) — before this fix, an operator-edited, already-resolved participant with an open discrepancy (exactly D-32's own scenario) was invisible in the review queue, satisfying none of the original three legs
expected: _argument_attention_predicate gains a fourth leg (open participant discrepancy) — before this fix, an operator-edited, already-resolved participant with an open discrepancy was invisible in the review queue
result: pass
source: automated
coverage_id: 49-06 D5

### 32. readonlyMode split into resolveCardReadonly (status===published, matching 49-04's widened backend guard) and metadataReadonly (unchanged) — closes the item 49-04 and 49-05 both flagged and deferred
expected: readonlyMode split into resolveCardReadonly (status===published, matching 49-04's widened backend guard) and metadataReadonly (unchanged)
result: pass
source: automated
coverage_id: 49-06 D6

### 33. Full suite green, no new skips, versus the 1403-test baseline this plan inherited from 49-05
expected: Full suite green, no new skips, versus the 1403-test baseline this plan inherited from 49-05
result: pass
source: automated
coverage_id: 49-06 D7

### 34. Requirement-to-evidence traceability (REVIEW-01..05, D-34, all four T-49-* threat refs) plus the D-32 transcript, the corrected Pitfall 4 premise, and every outstanding human-verification item across the phase consolidated into one list
expected: Requirement-to-evidence traceability (REVIEW-01..05, D-34, all four T-49-* threat refs) plus the D-32 transcript, the corrected Pitfall 4 premise, and every outstanding human-verification item across the phase consolidated into one list
result: pass
source: automated
coverage_id: 49-06 D8

## Summary

total: 34
passed: 31
issues: 3
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-49-3
  truth: "An unresolved/unverified speaker's bench-vs-advocate classification is operator-editable from the Speakers card on the argument edit page"
  status: resolved
  resolved_by: 49-10
  resolved_at: 2026-08-24
  reason: "User reported: Yes, I can see what you describe and it works as indicated, however, there's no option to choose bench or advocate. If a speaker is unverified, then I would expect their bench side to be editable. Closed by convergence (D-35, \"Converge both surfaces\"): the Speakers card now reaches every stored side value including BENCH, gated by a boundary-crossing confirm, with one row template so bench and advocate rows share identical affordance depth. D-35 superseded the three-option checkpoint (deep-link/port-control/defer) 49-09 originally raised for this gap rather than answering any one of them."
  severity: major
  test: 3
  artifacts:
    - "app/src/lib/participantSide.ts — the shared bucket rule, label map, specific-advocate-role helper, and boundary-crossing predicate both cards import"
    - "app/src/routes/admin/arguments/[id]/+page.svelte — one converged Speakers row template (bench/advocate branch removed), the five-value side control, the boundary-crossing two-step confirm, and the three-state bench companion (tenure role / missing tenure / no person linked)"
    - "app/src/routes/admin/arguments/[id]/+page.server.ts — updateParticipantSide action omits descriptor when the row's committed side was BENCH (RESOLVE-13 round-trip guard)"
    - "api/services/admin_arguments.py::update_participant_side — accepts BENCH under RESOLVE-13's descriptor rule; T-15-02-BENCH retired as satisfied"
    - "api/schemas/admin_arguments.py, api/routers/admin.py (two docstrings), api/services/admin_jobs.py — the four citation sites recording T-15-02-BENCH's retirement"
  missing: []

- gap_id: G-49-4a
  truth: "The review-queue constituent action link is labelled with an action verb naming where it goes, matching the established label pattern elsewhere in admin"
  status: resolved
  resolved_by: 49-07
  resolved_at: 2026-08-24
  reason: "User reported: link reads a bare \"Edit\"; wants an action verb. Destination is correct (operator followed it to the pipeline run). app/src/routes/admin/review/+page.svelte:527 hardcodes \"Edit\" unconditionally, while argumentEditHref (:215-219) branches between /admin/pipeline/{admin_job_id} and /admin/arguments/{id} — so one static label cannot be accurate for both branches. 49-05 UI-SPEC called this link \"Resolve speaker\"; neither label was implemented."
  severity: minor
  test: 4
  artifacts:
    - "app/src/routes/admin/review/+page.svelte — new argumentEditLabel(item) helper, branching on the identical admin_job_id !== null condition as argumentEditHref; the row action anchor now renders {argumentEditLabel(item)} instead of the literal \"Edit\""
    - "api/tests/test_phase49_review_ui_contract.py::test_action_link_label_branches_on_the_same_condition_as_the_href — source-text parity assertion (not a rendering assertion)"
  missing: []

- gap_id: G-49-4b
  truth: "Operator-facing copy names a speaker with the domain noun (participant), not the internal rollup adjective 'constituent', and agrees in number"
  status: resolved
  resolved_by: 49-07
  resolved_at: 2026-08-24
  reason: "Found during test 4. 'constituent' was never chosen as a user-facing term: it entered as an ADJECTIVE in .planning/notes/provenance-and-trust-model.md:143 ('constituent utterances and attributions'), was nominalized into a noun by 48-CONTEXT.md:15 (:114 cites that sentence as its source), then hardened into ReviewQueueConstituent (api/schemas/admin_review.py) and leaked into operator copy. The domain noun is participant (argument_participants / ArgumentParticipant / participant_id in the same markup). User asked: 'When did we start calling something constituent?'  Separately, review/+page.svelte:182 pluralizes the noun but not the verb, so a single-item row renders the ungrammatical '1 constituent need review' (visible in the operator's screenshot). Scoped to operator-facing COPY ONLY per 49-07-PLAN.md <planner_decisions>: the wire code no_constituents, the ReviewQueueConstituent schema symbol, and the constituents response field are unchanged (they are a wire code and an admin-only API/security-guard symbol, never shown to an operator)."
  severity: minor
  test: 4
  user_visible_sites:
    - "app/src/routes/admin/review/+page.svelte:182 (N constituents need review + subject-verb disagreement)"
    - "app/src/routes/admin/review/+page.svelte:544 (No flagged constituents...)"
    - "app/src/routes/admin/help/+page.svelte:181-182, 323"
  artifacts:
    - "app/src/routes/admin/review/+page.svelte:182 -> attentionCountText now renders '1 participant needs review' / '{N} participants need review'"
    - "app/src/routes/admin/review/+page.svelte:544 -> 'No flagged participants — this argument is queued because:'"
    - "app/src/routes/admin/help/+page.svelte:181 -> 'across every one of its speaker attributions'"
    - "app/src/routes/admin/help/+page.svelte:182 -> 'An argument with no utterances and no participants at all reads uncertain'"
    - "app/src/routes/admin/help/+page.svelte:323 -> 'the argument's current participants and utterances'"
    - "api/tests/test_phase49_review_ui_contract.py::test_review_page_rendered_copy_uses_the_domain_noun — per-line source gate, exempts the wire code and property accessors"
    - "api/tests/test_phase49_cleanup_contract.py::test_help_page_rendered_copy_uses_the_domain_noun — whole-file source gate (help page has no wire code / accessors using the noun)"
  missing:
    - "no_constituents (api/services/trust.py), ReviewQueueConstituent (api/schemas/admin_review.py), and the constituents response field are deliberately NOT renamed — see 49-07-PLAN.md prohibitions"

- gap_id: G-49-5a
  truth: "No horizontal scroll at 375px on the review queue and the admin dashboard (49-05 UI-SPEC must_have)"
  status: resolved
  resolved_by: 49-08
  resolved_at: 2026-08-24
  reason: "User reported: small screens cause horizontal scrolling. THREE independent causes, not two — the third found during 49-08 planning, not in the original UAT diagnosis. (a) app/src/routes/admin/review/+page.svelte contained ZERO overflow declarations: both queue tables were bare `width: 100%; border-collapse: collapse` with no overflow-x:auto wrapper, and 12 `white-space: nowrap` cells pinned a hard minimum width, so the page body — not the table — scrolled. (b) app/src/routes/admin/+page.svelte hardcoded `grid-template-columns: repeat(5, 1fr); gap: 32px` with no minmax/auto-fit and no media query; at 375px the four gaps alone consumed 128px, leaving ~49px per card. (c) (found by 49-08 planning, not the original diagnosis) the status segmented control (All/Candidate/Draft/Published/Unpublished) had `display: flex; gap: 0` with five 44px-min-height buttons, no flex-wrap and no min-width: 0, so its own ~480px minimum overflowed the page's 327px inner width independently of the tables. Fixing (a) and (b) alone would have left the page still scrolling."
  severity: minor
  test: 5
  artifacts:
    - "app/src/routes/admin/review/+page.svelte — each of the two queue tables and the status segment group wrapped in its own `<div style=\"overflow-x: auto;\">` (the status group additionally gets `min-width: 0` on the outer wrapper and `width: max-content` on the inner button group); nowrap cells, columns, and the no-truncation rule (49-UI-SPEC E1/E2) are untouched"
    - "app/src/routes/admin/+page.svelte — `grid-template-columns` changed from `repeat(5, 1fr)` to `repeat(auto-fit, minmax(120px, 1fr))`; five tracks still fill the 812px desktop content width at the same 136.8px per-card width as before (UAT sub-item 5 preserved exactly), and the grid reflows to two tracks at a 375px viewport"
    - "api/tests/test_phase49_review_ui_contract.py — three new containment assertions (both tables + status group wrapped, min-width:0/width:max-content present, no truncation/media-query introduced) and an executable `_tracks_that_fit` arithmetic gate proving both UAT sub-item 5 and sub-item 7 hold simultaneously at the real desktop and 375px geometries"
  missing:
    - "Visual/browser re-confirmation at 375px and at desktop width — NOT OBSERVED. This sandbox has been denied .env access for ADMIN_USERNAME/ADMIN_PASSWORD/SESSION_SECRET throughout Phase 49 (49-EVIDENCE.md §9 item 4), so 49-08 could not authenticate to /admin/** to run the browser pass. This gap's closure is STRUCTURAL (source-contract tests green) only; it is not yet VISUALLY closed. See 49-VERIFICATION.md human_verification item 2."

- gap_id: G-49-5b
  truth: "Zero-one-many count copy agrees in number everywhere it appears"
  status: resolved
  resolved_by: 49-07
  resolved_at: 2026-08-24
  reason: "Found while explaining test 5 sub-item 6. admin/+page.svelte:353-355 (Review queue StatCard) gets it RIGHT — '1 item needs review'. app/src/routes/admin/review/+page.svelte:182 attentionCountText gets it WRONG — pluralizes the noun but not the verb, rendering '1 constituent need review'. Same zero-one-many concept, two implementations, one defective. Overlaps G-49-4b (same line, terminology); fixed together."
  severity: cosmetic
  test: 5
  artifacts:
    - "app/src/routes/admin/review/+page.svelte:181-183 -> attentionCountText(n) now returns '1 participant needs review' at n === 1 (singular subject, singular verb) and '${n} participants need review' otherwise (plural subject, plural verb) — the identical shape admin/+page.svelte's Review-queue StatCard already used"
    - "api/tests/test_phase49_review_ui_contract.py::test_backstop_E1_attention_count_keys_singular_plural_on_strict_equality_one — rewritten to assert the exact singular/plural literals rather than the old ungrammatical substring"
  missing: []

## Deferred Follow-Ups

- test: 5
  idea: "The review tab should become the basis for a future Phase that folds the existing People, Arguments, and Pipeline Runner screens into one screen with filtering."
  raised_by: operator
  deferred_at: 2026-08-24
  note: "Future-work idea, NOT a Phase 49 gap — deliberately not appended to ## Gaps and must not spawn a fix plan. Candidate for /gsd-capture -> ROADMAP backlog."

- gap_id: G-49-9a
  truth: "An unresolved (non-interactive) avatar occupies the same layout footprint as a resolved (button-wrapped) one, so rows stay aligned"
  status: resolved
  reason: "User reported: alignment issue for Lloyd N. Cutler, reproducing on the utterance bubble too. Root cause: the resolved branch wraps the 32px circle in a <button style=padding:6px> (44x44 footprint) while the unresolved branch renders a bare 32x32 div — a 12px width difference inside a flex row with align-items:center, shifting the circle ~6px and the name with it. Phase 49 regression: the non-interactive branch was introduced by this phase for 14-UAT Test 8 / 49-06 D3."
  severity: cosmetic
  test: 9
  resolved_by: in-session fix during UAT (operator delegated the fix-now-vs-defer decision)
  resolved_at: 2026-08-24
  artifacts:
    - path: "app/src/routes/cases/[slug]/arguments/[id]/+page.svelte"
      issue: "bare-div avatar branch (bench :218, advocates :252) lacked the button branch's 6px footprint"
    - path: "app/src/lib/components/ChatBubble.svelte"
      issue: "same bare-div branch at :80"
  missing:
    - "margin:6px on each bare-div branch (margin, not padding — padding on a border-radius:50% box would grow the visible circle from 32px to 44px)"
    - "Operator re-confirmation by eye; the fix is verified by geometry reasoning and the test suite, not visually"
  reconfirmation_attempt:
    attempted_by: 49-08
    attempted_at: 2026-08-24
    result: "NOT ATTEMPTED IN BROWSER — 49-08 confirmed by grep that all three fix sites still carry the margin fix (arguments/[id]/+page.svelte: `margin:6px` x2 — no space, differs from the plan's `margin: 6px` grep pattern but is the same declaration; ChatBubble.svelte: `margin: 6px` x1), but could not open a browser session (same .env credential gap as G-49-5a). No verified_at added; status remains resolved (code-level) with the visual re-confirmation still outstanding, unchanged from the prior UAT session."

- gap_id: G-49-5c
  truth: "No horizontal page scroll at 375px on ANY admin page — including the shared AdminSubNav, which renders on all of them"
  status: resolved
  resolved_by: 49-12
  resolved_at: 2026-08-24
  reason: |
    Found 2026-08-24 by live browser verification (Playwright MCP), AFTER 49-08 closed G-49-5a's
    three causes. Those three ARE genuinely fixed and were confirmed working in the same session:
    both queue tables and the status segment group scroll inside their own containers
    (312px containers with scrollWidth 529 and 690), and the dashboard grid reflows to
    `140px 140px` / 2 columns at 375px while still rendering 5 tracks at 136.797px / 1 row at
    1280px — matching 49-08's predicted arithmetic to the pixel.
    A FOURTH, previously unknown cause remained. `app/src/lib/components/AdminSubNav.svelte:11`
    was `display: flex` with NO `flex-wrap` and NO `overflow-x`, holding five nav links plus a
    `<form style="margin-left: auto;">` (`:32`) wrapping the Log out button. At a 375px viewport
    the row needed ~423px, so the logout form's right edge landed at 423px and the Log out
    button was pushed off-screen entirely.
    Measured (operator, 2026-08-24): document.scrollWidth 423 vs clientWidth 360 on BOTH /admin
    and /admin/review. document.scrollWidth equalled the logout form's right edge exactly — the
    tables (right 714) and status group (right 553) extended further but contributed nothing to
    page scroll, proving they were contained and the sub-nav was the sole remaining cause.
    RESOLVED by 49-12 (2026-08-24, session continued into 2026-08-25): 49-08's three causes were
    NOT re-fixed and were re-confirmed working by the same live measurement pass that found this
    gap in the first place — this plan added only a fourth cause's fix. `AdminSubNav.svelte` gained
    `flex-wrap: wrap` on its `<nav>` inline style (D-49-12-a); `margin-left: auto` on the logout
    form stays (D-49-12-b), so Log out lands flush right on whichever line it wraps to. Re-measured
    live (headless chromium, same authenticated profile): scrollWidth == clientWidth == 375 on
    /admin, /admin/review, /admin/pipeline, /admin/help post-fix, having been measured 423 vs 375
    on those same routes pre-fix. 1280px sub-nav geometry unchanged before/after (navHeight 69,
    logout right 1256).
    The regression gate 49-08 lacked (a page-scroll measurement, not a declaration grep) is now a
    computed chrome-set sweep in api/tests/test_phase49_nav_narrow_viewport_contract.py: it
    discovered TopNav.svelte as a second, previously-unreported zero-slack near-miss (not a cause
    of page scroll, but `display:flex` with no escape) and failed naming it before any fix was
    applied. TopNav also received `flex-wrap: wrap` (D-49-12-c) — brought into compliance by sweep
    MEMBERSHIP, not because it was observed causing scroll.
  severity: minor
  test: 5
  discovered_by: live browser verification (not source inspection — three structural gates were green)
  artifacts:
    - path: "app/src/lib/components/AdminSubNav.svelte"
      issue: "RESOLVED — `flex-wrap: wrap` added to the `<nav>` inline style (one declaration; nothing else changed)"
    - path: "app/src/lib/components/TopNav.svelte"
      issue: "Brought into sweep compliance — `flex-wrap: wrap` added; TopNav was never a cause of page scroll (zero pixels of slack at 375px, not overflowing)"
    - path: "api/tests/test_phase49_nav_narrow_viewport_contract.py"
      issue: "NEW module: a computed chrome-set walker (transitively-imported +layout.svelte components, union first-tag <nav> components) so a fifth undiscovered offender is swept in by construction; a whitespace-insensitive display:flex/escape detector; a non-degeneracy guard that fails (not passes vacuously) if the walker's discovered set collapses; and a permanent regression fixture proving the detector flags the exact historical pre-fix AdminSubNav declaration set. Every assertion in it is source-text-only — see the module's own docstring — the behavioural claim is closed by the live measurement recorded below, never by this module going green."
  missing:
    - "`/admin/arguments` and `/admin/people` each still overflow at 375px (scrollWidth 680 and 403 respectively vs clientWidth 375) due to an UNWRAPPED <table> on each page — a separate, pre-existing cause, out of scope for this plan (files_modified does not include either page). /admin/people's overflow was newly VISIBLE only after this plan's fix removed the larger sub-nav overflow that had been masking it (both were previously pegged at 423/375 by the sub-nav alone). Recorded as a new finding, not fixed here — a candidate for a future plan or `/gsd-review-backlog`."
    - "The 49-12-SUMMARY.md authenticated browser measurements were taken via a direct node + playwright-core script against a copy of the persistent `.playwright-profile` (cookies only, no credential read/typed/echoed), not via the Playwright MCP tool call the plan anticipated — the configured MCP server process already held the live profile's singleton lock at execution time. Same executable, same authenticated session, same numbers; documented for transparency, not treated as a shortfall of the truth this gap required."

## Live Browser Verification — 2026-08-24

First authenticated browser pass of the phase. Playwright MCP + a per-user rootless browser
runtime (NSS libs and fonts extracted to ~/.local, no sudo, no system change); operator logged
in once into a persistent profile so no credential ever entered the assistant's context.
Every item below was MEASURED in a real browser, not inferred from source.

OBSERVED PASS:
- UAT sub-item 5 — five StatCards, ONE row at 1280px: grid inner width 812px, tracks
  5 x 136.797px, gap 32px, distinct row-tops = 1. Matches 49-08's predicted arithmetic to the
  pixel; no regression from the auto-fit change.
- G-49-5a cause (b) — at 375px the dashboard grid reflows to `140px 140px` (2 columns, 3 rows).
- G-49-5a causes (a) and (c) — on /admin/review both queue tables AND the status segment group
  scroll inside their own containers: 312px containers with scrollWidth 529 and 690. The table's
  right edge reaches 714px and the segment group's 553px, yet document.scrollWidth is only 423px,
  proving both are contained and contribute nothing to page scroll.
- G-49-4b — the word "constituent" is ABSENT from rendered operator copy (/admin/review, expanded
  row). The rewritten blockers fallback renders live: "No flagged participants — this argument is
  queued because:".
- G-49-9a — avatar alignment FIXED, confirmed at the pixel. On the public chat page's Advocates
  sidebar the button-wrapped avatars (HT, EB, HJ, LK, GM, RG) sit at left=647; the bare-div
  non-interactive avatar (LC) also sits at left=647 with margin:6px. Same in the chat body:
  interactive and non-interactive both at left=534. This closes the item that had been verified
  by geometry and test suite but never by sight.
- 49-09 published lock, VISIBLE and correct on published argument 1801: all 8 side selects
  disabled, all 8 descriptor inputs disabled, all 8 per-row Save buttons disabled, plus the copy
  "This argument is published, so participant data is read-only. Unpublish it first to edit roles
  or descriptors."

OBSERVED FAIL:
- G-49-5c (NEW, recorded above) — the page STILL scrolls horizontally at 375px on every admin
  page. AdminSubNav.svelte is the sole remaining cause. Three source-text gates were green while
  the page scrolled; only a live measurement caught it.

CONFIRMED-AS-EXPECTED (not a defect — this is 49-11's target):
- D-35a half-locked state, now visible rather than theoretical. On the same published argument
  1801, `case_name`, `docket_number` and `argued_date` inputs are all ENABLED and both
  "Save changes" and "Save Argument Details" are active, while the Speakers card is locked.
  Exactly the state 49-11 exists to close, and exactly what the planner predicted when it
  declined to reverse the `readonly is always false here` decision silently.

STILL NOT OBSERVABLE (data-state dependent, NOT assumed):
- G-49-4a — the "Edit pipeline run" / "Edit argument" labels. Requires a queue row with at least
  one flagged constituent; the current dev data has attention_count 0 on both rows, so the
  expanded panel shows the blockers fallback instead of constituent action rows.
- Discrepancy badge placement and its #fb7185 colour. Requires the D-32 authority-conflict state,
  which the dev database no longer holds.
- UAT sub-item 5.6 — StatCard singular and zero-state copy. Requires the review queue at exactly
  1 and at 0; it currently reads 40.
These three need a re-seed (Reset to Fixture -> Seed unresolved speaker -> the D-32 script) and
are deliberately left unobserved rather than marked passed.

### Re-seeded verification round — 2026-08-24 (second live pass)

Operator authorised a re-seed. Reset to Fixture (via the Dev Tools button, including its
"Confirm reset" gate) -> Seed unresolved speaker -> the D-32 authority-conflict script.
Fixtures re-imported as arguments 1805-1808; seeder reported
`Argument #1805 — "Lloyd N. Cutler" — trust tier: uncertain`.

NOW OBSERVED PASS — the three items the previous pass could not reach:

- G-49-4a — the destination-naming label renders and points correctly:
  BOTH action links read "Edit pipeline run" and resolve to `/admin/pipeline/1164`, i.e. the
  `admin_job_id !== null` branch of argumentEditHref. The operator's original complaint (a bare
  "Edit" that did not say where it went) is closed.
- UAT test 6 — Discrepancy badge, fully verified visually and computationally:
  computed colour `rgb(251, 113, 133)` = #fb7185 exactly, border the same, 12px, background
  `rgb(15, 17, 23)` = #0f1117 — the informational badge tier from 49-UI-SPEC:79/:97.
  Placement confirmed LAST in the identity row: ["Howard J. Trienens", "(Advocate)", "Edited",
  "Discrepancy"]. The provenance line renders directly beneath with no click, as D-15 requires:
  `descriptor: existing "Lead counsel for petitioner (operator edit)" (corpus/direct) — incoming
  "Counsel of record (corpus re-import)" (corpus/direct)`.
- UAT sub-item 5.6 — all THREE zero-one-many branches of the Review-queue StatCard observed by
  driving the real queue count down (people confirmed in bulk; 1808's single null-speaker
  utterance resolved; then 1805's four attention legs cleared):
    total 40 -> "40 items need review ->"   (link)
    total 1  -> "1 item needs review ->"    (link; singular noun AND singular verb)
    total 0  -> "No items need review"      (PLAIN TEXT, no link — verified hasLink === false)
  The zero state correctly refuses to advertise work that does not exist (E8).

ALSO RE-CONFIRMED in the same view: "2 participants need review" in the Needs-attention column —
the exact line that used to render the ungrammatical "1 constituent need review", now carrying
both the domain noun (G-49-4b) and correct subject-verb agreement (G-49-5b); and UAT test 4's
conditional (an unresolved constituent shows "Confirm as unattributable" and NO plain Confirm,
while the operator_edited row shows "Re-flag for review").

DEV DATA NOTE: reaching totals of 1 and 0 required draining the queue artificially (bulk
person confirmation, utterance attribution, discrepancy closure). That state is NOT
representative and was restored by a second Reset to Fixture + Seed unresolved speaker
immediately afterward.

### 49-10 human-checks — RUN IN BROWSER by the orchestrator, 2026-08-24

49-10's executor had no browser tool and logged three `<human-check>` items as unrun. Two of the
three are now OBSERVED (the third, Task 1's Resolve-card pipeline-page regression walk, is not).

OBSERVED PASS:
- Convergence, on draft argument 1810: EVERY speaker row renders the full five-option control
  [UNKNOWN, BENCH, PETITIONER, RESPONDENT, AMICUS] — measured `everyRowOffersBench: true` across
  all 5 rows. Bench-side people (Earl Warren, Felix Frankfurter, Stanley Reed) now carry the SAME
  select rather than the bare em-dash that made G-49-3's asymmetry. CLAUDE.md's apolitical
  constraint — identical affordance depth for every speaker — is satisfied by observation, not
  by assertion.
- Cross-boundary confirm (RESOLVE-09), verified INTERACTIVELY: selecting BENCH on an advocate row
  changes that row's Save button to "Move to Bench". The operator cannot cross the boundary
  without seeing that they are.
- Descriptor protection (RESOLVE-13), verified INTERACTIVELY: the descriptor input becomes
  `disabled: true` the instant BENCH is selected, and a hidden `committed_side="UNKNOWN"` input is
  present for the server to read. That is the both-ends fix for the round trip that would
  otherwise have submitted '' and clobbered a preserved bench descriptor.
- 49-09's published lock SURVIVED the convergence (49-10's single largest regression risk), on
  published argument 1811: 7 side selects all disabled, all descriptors disabled, all Saves
  disabled, lock line intact — while BENCH remains in the option set.

The last point is the clearest demonstration of D-35 in the product: published 1811 and draft 1810
render the IDENTICAL five-option interface, and the only difference between them is enabled vs
disabled, decided solely by publish status. That is the operator's doctrine, verbatim, on screen.

STILL NOT OBSERVED:
- 49-10 Task 1's Resolve-card regression walk on the pipeline page (`/admin/pipeline/{job}`).
  The shared-module extraction changed ResolveCard's imports; this walk confirms the batch resolve
  form still behaves. Not run in this pass.

### 49-10 Task 1 Resolve-card regression walk — RUN IN BROWSER, 2026-08-25

The third and last of 49-10's unrun `<human-check>` items. Run on the paused job that owns the
Complexity fixture (`/admin/pipeline/1168`, argument 1809), which is the only surface with a live
Resolve card. This is the check that matters for 49-10's shared-module extraction, because
`SIDE_LABEL` and `sideBucket` were moved OUT of ResolveCard.svelte into
`app/src/lib/participantSide.ts` and this component now imports them.

OBSERVED PASS:
- The Resolve card renders intact: 34 Bench/Advocate segmented toggles (17 participant rows x 2)
  with correct `aria-pressed` state (Advocate pressed=true / Bench pressed=false on advocate rows),
  9 candidate picker selects, 0 elements with role="alert", 0 console errors.
- All four SIDE_LABEL values render from the shared module: "Bench", "Petitioner's Counsel",
  "Respondent's Counsel", "Amicus Curiae". This is the extraction verified behaviourally — the
  labels now come from participantSide.ts and still render identically.

PRE-EXISTING OBSERVATION, not a 49-10 regression and NOT a gap:
- The page emits 17 identical Svelte warnings: `binding_property_non_reactive`, one per
  participant row. Traced to `ResolveCard.svelte:1314`, `bind:this={formRefs[row.participant_id]}`
  — a bind into a plain object property, so `formRefs` is not a `$state` proxy and writes into it
  are not reactive. PROVEN pre-existing rather than introduced: 49-10's diff over ResolveCard
  (574903cb5~1..a89adcd62) touches ZERO `bind:` lines, and the pre-49-10 file carried the same
  single binding.
  Recorded rather than ignored because it is the same SHAPE as this project's documented
  false-green incident (a non-reactive Svelte binding under 28 green source-contract tests, plan
  48-10). Here it is probably benign — the refs are used imperatively with flushSync before
  submit, where non-reactivity is the intent — but a future contributor who starts reading
  `formRefs` reactively would get a silent stale value. Candidate for the design-system phase or
  a cleanup plan; deliberately not fixed here, as it is outside every open gap.

All three of 49-10's human-checks are now observed. None remain outstanding for that plan.

### Third live pass — 2026-08-24 (49-12, narrow-viewport chrome)

Closes G-49-5c. Method note: the authenticated measurements below were taken via a direct
`node` + `playwright-core` script against a COPY of the persistent `.playwright-profile`
(cookies only — no credential was ever read, typed, or echoed), because the Playwright MCP
server process configured in `.mcp.json` already held the live profile's singleton lock at
execution time. Same chromium binary, same authenticated session, same numbers as the operator's
own 423/360 reading above would have produced.

MEASURED (real headless-chromium browser, not inferred from source):

- Six admin routes at 375px, before the AdminSubNav fix: `/admin` 423/375, `/admin/review`
  423/375, `/admin/arguments` 680/375, `/admin/people` 423/375, `/admin/pipeline` 423/375,
  `/admin/help` 423/375 (scrollWidth / clientWidth). The 423 on five of six matches the operator's
  own 423 reading exactly; `/admin/arguments` was already higher for an unrelated reason (see
  below).
- The same six routes at 375px, after `AdminSubNav.svelte` gained `flex-wrap: wrap`: `/admin`
  375/375, `/admin/review` 375/375, `/admin/arguments` 680/375 (UNCHANGED — separate cause),
  `/admin/people` 403/375 (now visible on its own — see below), `/admin/pipeline` 375/375,
  `/admin/help` 375/375.
- 1280px `/admin` sub-nav geometry, before and after the fix — IDENTICAL: navHeight 69,
  logout form left 1169.609375 / right 1256, page scrollWidth == clientWidth == 1280 both times.
- NEW FINDING, out of scope for this plan (neither page is in `files_modified`): `/admin/arguments`
  has an unwrapped `<table>` (right edge 679.95px at 375px) — an admin-jobs/arguments list table
  with no `overflow-x` container, a separate cause from AdminSubNav. `/admin/people` has the same
  shape (a people-editor `<table>`, right edge 402.94px at 375px); this one was previously MASKED
  because the sub-nav's larger 423px overflow pegged the whole page at 423 regardless. Fixing the
  sub-nav did not fix these tables and was never expected to — they are independent overflow
  sources. Both were also confirmed clean (no overflow) at 1280px via
  `app/scripts/narrow-viewport-audit.mjs` (Task 2b), which additionally named the exact offending
  `<table>`/`<thead>`/`<tr>`/`<th>`/`<tbody>` elements and their right edges for both routes.
  Neither is fixed here — recorded as a new finding, candidate for a future plan.

ASSERTED-ONLY (STRUCTURAL) — proves declarations are present in source, cannot prove the page
does not scroll:

- `api/tests/test_phase49_nav_narrow_viewport_contract.py` (new module): a chrome-set walker
  computes the set of page-chrome `.svelte` files (rather than a hand-picked list); a detector
  flags any element with `display:flex` and none of `flex-wrap`, `overflow-x`, or fixed-with-
  left/right; a non-degeneracy guard fails if the walker's discovered set shrinks below three
  members or misses AdminSubNav/TopNav/MobileNavBar. Run BEFORE the TopNav fix, the live sweep
  failed naming `TopNav.svelte:<nav>` — a component no gap report or prior assertion had ever
  named. This module going green proves the four known chrome components each carry an escape
  declaration; it does not and cannot prove the rendered page does not scroll. That claim is
  closed only by the MEASURED numbers above.

Also recorded, from planning:

- MobileNavBar was already compliant and needed no change: it is mobile-only
  (`display: none` above 768px via a `<style>` media-query rule), declares `overflow-x: auto` and
  `position: fixed` with `left: 0; right: 0` inline, so it structurally cannot widen the page.
- TopNav had exactly zero pixels of horizontal slack at 375px (planning-time measurement on the
  real `/cases` page: last child's right edge 351px + 24px padding = 375px exactly) without
  actually overflowing — it was NOT a cause of page scroll. It was brought into compliance by
  sweep MEMBERSHIP (the computed chrome set includes it by construction, via both `+layout.svelte`
  files importing it), not because it was observed causing scroll.

### D-35 / D-35a end-to-end verification — RUN IN BROWSER, 2026-08-25

After 49-11 and 49-12 landed. This is the operator's doctrine tested in both directions on real
pages, which is the only way to know it was implemented rather than merely asserted.

PUBLISHED argument 1811 — everything locked, escape hatch intact:
- `case_name`, `docket_number`, `question_number`, `argued_date` — ALL disabled.
- All 8 Save buttons — ALL disabled (both card-level and every per-speaker row).
- **`Unpublish` remains ENABLED** — the over-lock guard holds. This was 49-11's own stated worst
  failure mode: locking lifecycle operations alongside data would freeze a published argument
  permanently, with no way back. It did not happen.
- One card-agnostic notice, stated once: "This argument is published, so its data is read-only.
  Unpublish it in the Status card below to edit the case, argument details, or speakers." It names
  the way out rather than only the prohibition.

DRAFT argument 1810 — everything editable:
- All four argument-data inputs editable; both card-level Saves enabled; no lock notice rendered.
- All side selects enabled, and every one offers BENCH (49-10's convergence).
- Per-row Saves disabled ONLY on rows whose side is still UNKNOWN — verified individually: each
  disabled Save has `rowSideValue: "UNKNOWN"`, and rows already resolved to BENCH have ENABLED
  Saves. That is the PRE-EXISTING unresolved-side gate (26-UAT Test 26), not a lock leak. Checked
  explicitly rather than assumed, because "some Save is disabled on a draft" would otherwise look
  exactly like an over-lock bug.

Net: published 1811 and draft 1810 render the IDENTICAL interface. The only difference between
them is enabled vs disabled, decided solely by publish status — plus one pre-existing gate that
predates this doctrine and is orthogonal to it. That is D-35 as the operator stated it,
implemented, and observed.

Full suite after all six gap-closure plans: 1150 passed, single clean process, 0 failures.
