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
  status: failed
  reason: "User reported: Yes, I can see what you describe and it works as indicated, however, there's no option to choose bench or advocate. If a speaker is unverified, then I would expect their bench side to be editable"
  severity: major
  test: 3
  artifacts: []  # Filled by diagnosis
  missing: []    # Filled by diagnosis

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
  status: failed
  reason: |
    Found 2026-08-24 by live browser verification (Playwright MCP), AFTER 49-08 closed G-49-5a's
    three causes. Those three ARE genuinely fixed and were confirmed working in the same session:
    both queue tables and the status segment group scroll inside their own containers
    (312px containers with scrollWidth 529 and 690), and the dashboard grid reflows to
    `140px 140px` / 2 columns at 375px while still rendering 5 tracks at 136.797px / 1 row at
    1280px — matching 49-08's predicted arithmetic to the pixel.
    A FOURTH, previously unknown cause remains. `app/src/lib/components/AdminSubNav.svelte:11`
    is `display: flex` with NO `flex-wrap` and NO `overflow-x`, holding five nav links plus a
    `<form style="margin-left: auto;">` (`:32`) wrapping the Log out button. At a 375px viewport
    (360px client width after the scrollbar) the row needs ~423px, so the logout form's right
    edge lands at 423px and the Log out button is pushed off-screen entirely.
    Measured: document.scrollWidth 423 vs clientWidth 360 on BOTH /admin and /admin/review.
    document.scrollWidth equals the logout form's right edge exactly — the tables (right 714)
    and status group (right 553) extend further but contribute nothing to page scroll, proving
    they are contained and the sub-nav is the sole remaining cause.
    This component renders on EVERY admin page, so no admin page currently satisfies the
    49-05 UI-SPEC no-horizontal-scroll must_have, regardless of that page's own containment.
  severity: minor
  test: 5
  discovered_by: live browser verification (not source inspection — three structural gates were green)
  artifacts:
    - path: "app/src/lib/components/AdminSubNav.svelte"
      issue: ":11 display:flex with no flex-wrap and no overflow-x; :32 form has margin-left:auto and cannot shrink"
  missing:
    - "Containment for the sub-nav row at narrow widths — same idiom 49-08 used for the status segment group (outer min-width:0 + overflow-x:auto, inner width:max-content), or flex-wrap if the wrapped appearance is acceptable for a nav (unlike the segmented control, these are separate links with no shared border geometry, so wrapping is visually fine here)"
    - "A regression assertion that measures page scrollWidth vs clientWidth rather than grepping for a declaration — three source-text gates passed while the page still scrolled"

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
