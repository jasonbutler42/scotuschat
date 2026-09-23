---
phase: 49-review-model
plan: 07
subsystem: ui
tags: [svelte, admin, copy, source-contract-tests]

requires:
  - phase: 49-review-model (plan 05)
    provides: "/admin/review queue screen and its source-contract test module"
  - phase: 49-review-model (plan 03)
    provides: "/admin/help page and its source-contract test module"
provides:
  - "argumentEditLabel(item) helper on the review page, branching on the identical admin_job_id !== null condition as argumentEditHref, closing the destination-naming label gap (G-49-4a)"
  - "Domain-noun ('participant') operator copy on both /admin/review and /admin/help, replacing the internal rollup noun 'constituent' (G-49-4b)"
  - "Subject-verb agreement in the review-queue attention-count line at exactly one (G-49-5b)"
  - "A per-line source gate on the review page and a whole-file source gate on the help page that fail if the internal rollup noun reappears in rendered copy"
affects: [49-08, 49-09, admin-review-ui, admin-help-ui]

actuals:
  tokens: 2977
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Label helper parity: a text-label helper (argumentEditLabel) is written alongside a destination helper (argumentEditHref) and both branch on the identical condition, with a source-text test asserting the parity so the two cannot drift independently."
    - "Per-line vocabulary gate vs. whole-file vocabulary gate: when a page still uses an internal identifier as a wire code or property accessor (review page: no_constituents, item.constituents), the source gate must exempt those forms line-by-line; when a page has no such internal usage (help page), a whole-file lowercase substring check is sufficient and simpler."

key-files:
  created: []
  modified:
    - app/src/routes/admin/review/+page.svelte
    - app/src/routes/admin/help/+page.svelte
    - api/tests/test_phase49_review_ui_contract.py
    - api/tests/test_phase49_cleanup_contract.py
    - .planning/phases/49-review-model/49-UAT.md

key-decisions:
  - "Rename stopped at operator-facing copy only — no_constituents (wire code), ReviewQueueConstituent (admin-only schema symbol asserted by the D-34 leak-ban security guard), and the constituents response field are all byte-identical to before this plan."
  - "Chose 'Edit pipeline run' / 'Edit argument' over the UI-SPEC's 'Resolve speaker' — the operator's own phrasing, completed to name the destination noun, since both destinations are whole pages rather than a single resolvable action."
  - "Zero-one-many copy for attentionCountText copies the dashboard StatCard's shape verbatim ('1 participant needs review' / '{N} participants need review') rather than inventing a third shape."

patterns-established:
  - "Destination-label-parity test: assert both the label helper's existence AND that the same branch condition string count equals 2 (one per helper), rather than asserting only that labels are present."

requirements-completed: [REVIEW-01, REVIEW-03, REVIEW-04]

coverage:
  - id: D1
    description: "Review-queue row action link is labelled with a destination-naming action verb (Edit pipeline run / Edit argument) that branches on the identical admin_job_id !== null condition as its href (G-49-4a)"
    requirement: "REVIEW-01"
    verification:
      - kind: unit
        ref: "api/tests/test_phase49_review_ui_contract.py#test_action_link_label_branches_on_the_same_condition_as_the_href"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_review_ui_contract.py#test_four_action_labels_present_verbatim"
        status: pass
    human_judgment: true
    rationale: "The passing tests are source-TEXT assertions — they prove the helper exists, is wired into the anchor, and shares the href's branch condition. They do not prove the rendered anchor shows the correct label for a real admin_job_id vs. argument-only row in a live browser; that is a rendering claim this plan's automated suite cannot make (see 'Structural vs behavioural closure' below)."
  - id: D2
    description: "Internal rollup noun 'constituent' removed from all operator-facing copy on /admin/review and /admin/help, replaced with the domain noun 'participant' / 'speaker attributions and utterances' (G-49-4b)"
    requirement: "REVIEW-03"
    verification:
      - kind: unit
        ref: "api/tests/test_phase49_review_ui_contract.py#test_review_page_rendered_copy_uses_the_domain_noun"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_help_page_rendered_copy_uses_the_domain_noun"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_help_page_trust_tier_paragraph_names_speaker_attributions"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_help_page_states_the_no_blockers_case_accurately"
        status: pass
    human_judgment: true
    rationale: "These are source-TEXT gates (per-line on the review page, whole-file on the help page) — they prove the string is absent from source, not that a human reading the rendered page perceives correct, natural-sounding prose. The plan's own module docstrings say the same (a $state proxy trap already let 28 green source-contract tests pass against a fully broken button in Phase 48 plan 48-10)."
  - id: D3
    description: "Review-queue attention-count line agrees in number: singular subject/verb at exactly one, plural subject/verb otherwise, matching the dashboard's Review-queue StatCard shape (G-49-5b)"
    requirement: "REVIEW-04"
    verification:
      - kind: unit
        ref: "api/tests/test_phase49_review_ui_contract.py#test_backstop_E1_attention_count_keys_singular_plural_on_strict_equality_one"
        status: pass
    human_judgment: true
    rationale: "Source-text assertion proving the exact singular/plural literals and the strict === 1 keying are present in source; it does not render the component to prove a live 1-row queue actually shows '1 participant needs review' in the browser."
  - id: D4
    description: "Wire code no_constituents, schema symbol ReviewQueueConstituent, and the constituents response field are unchanged"
    verification:
      - kind: unit
        ref: "api/tests/test_trust_public_leak_ban.py (full module)"
        status: pass
      - kind: other
        ref: "git diff --stat 690d51e20..HEAD -- api/schemas/ api/services/ alembic/ (empty)"
        status: pass
    human_judgment: false
---

# Phase 49 Plan 07: Review-queue and help-page copy gap closure Summary

**Destination-naming action label (`Edit pipeline run` / `Edit argument`), domain-noun rewrite (`participant` for the internal `constituent` rollup noun), and singular/plural subject-verb agreement — all on `/admin/review` and `/admin/help`, with schema/wire code left byte-identical.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-08-24T00:00:00Z (approx, per orchestrator handoff)
- **Completed:** 2026-08-24
- **Tasks:** 2
- **Files modified:** 5 (4 in `files_modified`, plus `49-UAT.md` per the plan's `<output>` instruction)

## Accomplishments

- Task 1: `app/src/routes/admin/review/+page.svelte` gained `argumentEditLabel(item)`, branching on the identical `admin_job_id !== null` condition as `argumentEditHref`; the row action anchor now renders `{argumentEditLabel(item)}` instead of a static `Edit`. `attentionCountText` now returns `1 participant needs review` at `n === 1` and `${n} participants need review` otherwise. The zero-flagged-row fallback now reads "No flagged participants". A new per-line source gate (`test_review_page_rendered_copy_uses_the_domain_noun`) fails if the internal rollup noun reappears in rendered copy, while still permitting `no_constituents`, `item.constituents`, `as constituent`, and `constituent.<field>`.
- Task 2: `app/src/routes/admin/help/+page.svelte`'s Trust-tiers paragraph now says "speaker attributions" (matching phrasing already used one sentence earlier) instead of "constituent attributions", states the no-blockers case as "no utterances and no participants" (matching what `api/services/trust.py:151` actually tests — both empty, not just one), and the publish-gate closing paragraph now names "participants and utterances" instead of "constituents". A new whole-file source gate (`test_help_page_rendered_copy_uses_the_domain_noun`) fails if the rollup noun reappears anywhere in help-page prose.

## Task Commits

1. **Task 1: Review-queue copy — destination-naming action label, domain noun, and subject-verb agreement** - `a96466b0b` (fix)
2. **Task 2: Help-page copy and the help-page vocabulary gate** - `5d03be308` (fix)

**Plan metadata:** `8662c42af` (docs: mark G-49-4a/4b/5b resolved in 49-UAT.md)

_Note: This plan used `tdd="true"` per-task (RED assertions written and observed failing before source edits), not the plan-level RED/GREEN/REFACTOR commit-gate sequence — both tasks' test-then-source edits landed in one commit per task, matching the plan's own `<action>` step numbering (test file edited and run red BEFORE the page file, both staged together at task completion). See "RED-phase verification" below for the per-assertion evidence the plan required in place of separate RED/GREEN commits._

## Files Created/Modified

- `app/src/routes/admin/review/+page.svelte` - `argumentEditLabel` helper added; `attentionCountText` and the zero-flagged-row fallback rewritten to the domain noun with subject-verb agreement; row action anchor now interpolates the label helper
- `app/src/routes/admin/help/+page.svelte` - Trust-tiers paragraph and publish-gate closing paragraph rewritten to the domain noun; no-blockers case now states both required conditions
- `api/tests/test_phase49_review_ui_contract.py` - `test_four_action_labels_present_verbatim` rewritten (5 labels incl. both edit-label branches); `test_backstop_E1_...` rewritten to assert the exact singular/plural literals; two new tests added (`test_action_link_label_branches_on_the_same_condition_as_the_href`, `test_review_page_rendered_copy_uses_the_domain_noun`)
- `api/tests/test_phase49_cleanup_contract.py` - three new tests added to the existing help-page block (`test_help_page_rendered_copy_uses_the_domain_noun`, `test_help_page_trust_tier_paragraph_names_speaker_attributions`, `test_help_page_states_the_no_blockers_case_accurately`)
- `.planning/phases/49-review-model/49-UAT.md` - `G-49-4a`, `G-49-4b`, `G-49-5b` marked `status: resolved` with `resolved_by: 49-07`, `resolved_at: 2026-08-24`, and populated `artifacts`/`missing` lists

## RED-phase verification (per the plan's mandatory-RED requirement)

All four Task 1 assertions and all three Task 2 assertions were observed to FAIL before the corresponding source file was touched. Quoted failure messages below are copied verbatim from the actual pytest run (not reconstructed from memory):

**Task 1 — `api/tests/test_phase49_review_ui_contract.py`:**

1. `test_four_action_labels_present_verbatim` — RED:
   `AssertionError: missing action label 'Edit pipeline run'`
2. `test_backstop_E1_attention_count_keys_singular_plural_on_strict_equality_one` — RED:
   `assert '1 participant needs review' in REVIEW_SOURCE` failed (old source still read `${n} constituent${n === 1 ? '' : 's'} need review`)
3. `test_action_link_label_branches_on_the_same_condition_as_the_href` — RED:
   `AssertionError: assert 'function argumentEditLabel' in REVIEW_SOURCE` (helper did not exist yet)
4. `test_review_page_rendered_copy_uses_the_domain_noun` — RED:
   `AssertionError: line 182 renders the internal rollup noun as operator copy: "\t\treturn \`\${n} constituent\${n === 1 ? '' : 's'} need review\`;"` — the gate correctly caught the exact pre-existing offending line and quoted it with its line number, confirming the gate is real and not vacuously green.

After the page edit, all four passed GREEN, along with the 12 pre-existing tests in the module (16 passed total).

**Task 2 — `api/tests/test_phase49_cleanup_contract.py`:**

1. `test_help_page_rendered_copy_uses_the_domain_noun` — RED:
   `AssertionError: assert 'constituent' not in source` — quoted context showed "...ne of its constituent attributions. an argument with no / constituents at all reads..."
2. `test_help_page_trust_tier_paragraph_names_speaker_attributions` — RED:
   `assert 'speaker attributions' in source` failed against the unmodified page source.
3. `test_help_page_states_the_no_blockers_case_accurately` — RED:
   `assert 'no utterances and no participants' in source` failed against the unmodified page source.

After the page edit, all three passed GREEN on the first attempt except for one self-correction: my first edit wrapped "no utterances and no\n\t\t\t\tparticipants" across a line break in the `.svelte` template, so the literal newline broke the contiguous substring match the test required (`assert 'no utterances and no participants' in source` failed even after the wording change, because "no" and "participants" were separated by `\n\t\t\t\t` rather than a space). I re-wrapped the paragraph so the full phrase "no utterances and no participants" sits on one line, then reran and confirmed GREEN. This was a Rule 1 (auto-fix bug) self-correction within Task 2, not a deviation from the plan's intent — the final rendered text matches the plan's specified wording exactly.

Final combined run: 39 passed (16 from the review module + 23 from the cleanup module, cleanup module count includes the 3 new tests plus pre-existing ones).

## Full-suite verification

`./.venv/bin/python -m pytest api/tests -q` observed: **1089 passed, 12 warnings in 306.54s**, against the stated 1084-passed baseline (commit `690d51e20`) — exactly `+5` (2 net-new tests in Task 1's module + 3 net-new tests in Task 2's module; the two rewritten tests in Task 1's module did not change the total count). No failures, no new skips.

`npm --prefix app run check` observed: **0 ERRORS, 37 WARNINGS, 11 FILES_WITH_PROBLEMS, 812 FILES** both before and after the change (same pre-existing warning list — `DocketPillInput.svelte`, `ArgumentDetailsCard.svelte`, `ChatBubble.svelte`, `CreatePersonPopover.svelte`, `ResolveCard.svelte`, `SpeakerPopover.svelte`, admin route files — none introduced by this plan).

## Structural vs. behavioural closure

Every assertion added or rewritten in this plan is a **source-text** contract, per the modules' own docstrings and per the plan's explicit warning. These tests prove:
- the exact strings/literals are present in the `.svelte` source, and
- (Task 1's per-line gate) that no *other* line renders the internal rollup noun as prose.

They do **not** prove:
- that a real browser renders `argumentEditLabel(item)` correctly for a live row with `admin_job_id !== null` vs. `null`,
- that the singular/plural attention-count line reads naturally when a real query returns exactly 1 flagged participant,
- that the help-page prose reads naturally to an operator.

No `npm`/Playwright/browser-driven check was run against these pages in this plan (none was in the plan's `<verify>` block). This is consistent with the sibling module's own documented precedent (Phase 48 plan 48-10: 28 green source-contract tests passed against a fully broken button) — I am stating this explicitly rather than implying behavioral verification occurred. A human browser walkthrough of `/admin/review` and `/admin/help` would be needed to close the behavioral gap; this plan closes the UAT gap IDs (G-49-4a, G-49-4b, G-49-5b) at the structural/copy level the plan scoped for.

## Decisions Made

- Stopped the rename at operator-facing copy: `no_constituents` (wire code, `api/services/trust.py:152`), `ReviewQueueConstituent` (admin-only schema symbol, `api/tests/test_trust_public_leak_ban.py`'s D-34 false-green guard), and the `constituents` response field are all confirmed byte-identical — verified via `test_trust_public_leak_ban.py` passing unchanged and `git diff --stat` showing zero touched files under `api/schemas/`, `api/services/`, `alembic/`.
- Chose "Edit pipeline run" / "Edit argument" over 49-UI-SPEC.md's "Resolve speaker" per the plan's `<planner_decisions>` — the operator's own phrasing, and both destinations are whole pages rather than a single resolvable action.
- No new architectural decisions were required; both tasks were pure copy/test edits within existing files.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Line-wrap in help-page "no utterances and no participants" sentence broke the contiguous-substring test**
- **Found during:** Task 2, first pass at editing `app/src/routes/admin/help/+page.svelte`
- **Issue:** My first edit placed a template line break between "no" and "utterances", so the literal newline (rather than a space) separated words the test asserted as one contiguous substring (`"no utterances and no participants"`). The test still failed after the wording change.
- **Fix:** Re-wrapped the paragraph so the entire phrase sits on a single source line, preserving the exact same rendered text (HTML whitespace-collapses regardless of source line wrapping) and the "— the maximal-risk case, not a free pass" clause verbatim.
- **Files modified:** `app/src/routes/admin/help/+page.svelte`
- **Verification:** Re-ran `test_help_page_states_the_no_blockers_case_accurately`, confirmed GREEN.
- **Committed in:** `5d03be308` (part of Task 2 commit — caught before the task commit was made, not a separate fix commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — self-corrected before committing, no separate commit needed)
**Impact on plan:** No scope creep. The correction is invisible in rendered output; it only affects source line-wrapping.

## Issues Encountered

None beyond the one self-corrected line-wrap issue documented above.

## What I could NOT verify

- No browser/Playwright verification of either page's rendered output was performed (not in this plan's `<verify>` block; see "Structural vs. behavioural closure" above).
- I did not independently re-derive or re-run the 1084-baseline count myself before this plan started — I took the orchestrator-supplied baseline at face value and compared my own observed 1089 against it. The arithmetic checks out (+5 exactly matches the net-new test count), which is corroborating but not independent proof the stated baseline was itself accurate.

## Next Phase Readiness

- `app/src/routes/admin/review/+page.svelte` and `api/tests/test_phase49_review_ui_contract.py` are released for 49-08 (wave 2), which is documented to re-edit both files.
- No files owned by 49-08 or 49-09 (`app/src/routes/admin/+page.svelte`, `app/src/lib/components/CreatePersonPopover.svelte`, `app/src/routes/admin/arguments/[id]/+page.svelte`, `api/tests/test_phase49_participant_side_contract.py`) were touched by this plan.
- G-49-4a, G-49-4b, G-49-5b are closed in `49-UAT.md`. G-49-3 (design-risk gap) remains open for 49-09; G-49-5a (horizontal scroll) remains open, unrelated to this plan's scope.

---
*Phase: 49-review-model*
*Completed: 2026-08-24*

## Self-Check: PASSED

All 6 claimed files found on disk. All 3 claimed commit hashes (`a96466b0b`, `5d03be308`, `8662c42af`) found in `git log --oneline --all`.
