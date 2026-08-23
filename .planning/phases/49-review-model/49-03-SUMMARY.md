---
phase: 49-review-model
plan: 03
subsystem: ui
tags: [sveltekit, svelte5, admin-ui, trust-tier, review-state, source-contract]

requires:
  - phase: 49-review-model plan 01
    provides: "review_state PG enum (4 permanent values) shared with argument_participants"
  - phase: 49-review-model plan 02
    provides: "Migration 0029 fold — people.review_state/provenance_metadata replace the legacy Phase 38 fields outright; the admin vocabulary this plan's Help page documents is now in its final, post-fold shape"

provides:
  - "CreatePersonPopover accepts initialSide (defaults ADVOCATE, no behavior change at any existing call site); side state and resetForm() initialize from it instead of a hardcoded literal"
  - "ResolveCard passes initialSide from the row's own Bench/Advocate toggle at the CreatePersonPopover call site, and handlePersonCreated sets s.comboQuery = enriched.full_name so the Resolved As box visibly shows the new person"
  - "Argument detail Status card relabels the resolve-pipeline-completion timestamp 'Resolved' instead of 'Created' (Argument has no creation timestamp column)"
  - "/admin/help — static, server-data-free operator reference documenting the four lifecycle statuses, the four trust tiers (with derive_tier's seven ordered rules transcribed from api/domain/trust.py), the four post-0029 review_state values and their two transition rules (D-24/D-25), and publish_argument's two ordered gates — linked from AdminSubNav"
  - "api/tests/test_phase49_cleanup_contract.py: 20 source-contract tests across three independently-selectable groups (popover/status_card/help_page)"

affects: [49-04-authority-ladder, 49-05-review-ui, 49-06]

actuals:
  tokens: 7839
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "A prop-initialized $state (let x = $state(initialProp)) is the established pattern for 'initial value the operator can still change' — CreatePersonPopover's `initialSide` follows the same shape svelte-check already accepts elsewhere in this codebase (ChatBubble, DocketPillInput), including the same benign state_referenced_locally warning"
    - "Static source-contract test modules (no DB, no node subprocess) remain this codebase's substitute for a Svelte component test runner; named-group `-k` selection is achieved purely through test-name prefixes matching the group name, not pytest marks"

key-files:
  created:
    - app/src/routes/admin/help/+page.svelte
    - api/tests/test_phase49_cleanup_contract.py
  modified:
    - app/src/lib/components/CreatePersonPopover.svelte
    - app/src/lib/components/ResolveCard.svelte
    - app/src/routes/admin/arguments/[id]/+page.svelte
    - app/src/lib/components/AdminSubNav.svelte

key-decisions:
  - "Status-card label fix took option 1 (relabel to 'Resolved', no schema change) per the plan's own pre-made decision — Argument has no created_at column, and the Status History list on the same card already carries the accurate birth record since plan 48-05."
  - "review_state badge on the Help page sized like the 14px status badge (not the 12px passive tier badge) since review_state is a primary, operator-actionable row-state axis in the UI-SPEC's own screen contract, not a passive info badge like trust tier. This is the Help page's own presentational choice — plan 49-05 owns the real queue screen's badge and is free to render it differently."
  - "Added flex-wrap: wrap to the Help page's badge+description rows (not specified in the plan's action text) to satisfy the plan's own 375px-width human-check requirement, matching the existing codebase convention for baseline-aligned badge+text flex rows."

requirements-completed: [REVIEW-01]

coverage:
  - id: D1
    description: "Create-person popover inherits the row's current Bench/Advocate side as its initial selection (operator can still change it), and reset returns to that inherited side rather than a hardcoded default"
    requirement: "REVIEW-01"
    verification:
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_popover_declares_initial_side_prop_in_interface"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_popover_side_state_initializes_from_initial_side"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_popover_reset_form_reassigns_initial_side_not_a_hardcoded_literal"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_popover_resolve_card_passes_initial_side_from_the_row_side"
        status: pass
    human_judgment: true
    rationale: "Source-contract tests prove the prop is wired end-to-end, but the plan's own acceptance criteria explicitly reject a green source-contract test as evidence for this exact class of bug (a $state proxy trap let 28 green tests pass against a fully broken button in plan 48-10). This executor could not complete the browser walkthrough: authenticating to /admin/** requires ADMIN_USERNAME/ADMIN_PASSWORD (or SESSION_SECRET to forge a cookie) from .env, and this sandbox's permission policy denied reading .env when attempted. Confirmed instead via full source read of the diff (state initialization, resetForm, the ResolveCard call site) and a clean svelte-check (0 errors) plus a clean dev-server hot-reload with no runtime error. A human must complete the Task 1 browser walkthrough before this item is considered UAT-complete."
  - id: D2
    description: "After creating a person from the Resolve card, the Resolved As search box shows the new person's full name"
    requirement: "REVIEW-01"
    verification:
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_popover_resolve_card_sets_combo_query_on_person_created"
        status: pass
    human_judgment: true
    rationale: "Same class of gap as D1 — this is exactly the kind of runtime-state assertion a source-contract test cannot prove and the plan explicitly calls out. Not confirmed in a live browser for the same credential-access reason as D1."
  - id: D3
    description: "Argument Status card's resolve-pipeline-completion timestamp is labelled 'Resolved', not 'Created'"
    requirement: "REVIEW-01"
    verification:
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_status_card_labels_resolved_at_as_resolved"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_status_card_no_longer_calls_resolved_at_created"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_status_card_published_label_treatment_unchanged"
        status: pass
      - kind: other
        ref: "npm --prefix app run check (svelte-check, 0 errors)"
        status: pass
    human_judgment: false
  - id: D4
    description: "/admin/help documents the four lifecycle statuses, four trust tiers (with derive_tier's seven rules), four review_state values (with D-24/D-25 transition rules), and publish_argument's two ordered gates, reachable from AdminSubNav, with no speaker ranking/comparison language"
    requirement: "REVIEW-01"
    verification:
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_help_page_documents_all_four_lifecycle_statuses"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_help_page_documents_all_four_trust_tiers"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_help_page_documents_all_four_review_states"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_help_page_documents_both_publish_gates"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_subnav_links_to_help_page"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase49_cleanup_contract.py#test_help_page_contains_no_speaker_ranking_or_comparison_language"
        status: pass
      - kind: other
        ref: "curl http://localhost:5173/admin/help (unauthenticated) -> 302 to /admin/login, no 500; dev-server hot-reload picked up the new route with no runtime error"
        status: pass
    human_judgment: true
    rationale: "The plan's <human-check> also requires visual confirmation (badge colors render correctly, no horizontal scroll at 375px, apolitical read-through by a human eye) that a static source-contract test and an unauthenticated SSR redirect cannot substitute for. Not confirmed live for the same credential-access reason as D1/D2 — a human should load /admin/help and the popover flow once before UAT sign-off."

duration: 25min
completed: 2026-08-23
status: complete
---

# Phase 49 Plan 03: Cleanup Pass — Popover Side/Selection, Status Card Label, Admin Help Page Summary

**Three independent folded todos closed: CreatePersonPopover now inherits the row's Bench/Advocate side and visibly selects the newly created person, the argument Status card stops mislabelling the resolve timestamp as a creation date, and a new `/admin/help` page documents the post-migration-0029 three-axis admin vocabulary (status x trust tier x review state) plus both publish gates, with 20 source-contract tests locking all three.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 3
- **Files modified:** 6 (2 created, 4 modified)
- **Commits:** 4

## Accomplishments

- **CreatePersonPopover** accepts a new `initialSide?: 'BENCH' | 'ADVOCATE'` prop (default `'ADVOCATE'`, so every existing call site is unaffected); the `side` `$state` rune and `resetForm()` both now initialize from it instead of a hardcoded `'ADVOCATE'` literal. `resolvedSide()` (the Bench/`defaultAdvocateSide` mapping) is untouched — a deliberately separate concern.
- **ResolveCard** passes `initialSide={side === 'BENCH' ? 'BENCH' : 'ADVOCATE'}` at the `CreatePersonPopover` call site, reusing the same `side` value `triggerLabel`/`defaultAdvocateSide` already read, so all three stay consistent by construction. `handlePersonCreated` now sets `s.comboQuery = enriched.full_name` right after `s.personId = enriched.id`, mirroring the existing-person pick path — the Resolved As box now visibly shows the new person instead of staying blank/stale.
- **Argument detail Status card**: the `resolved_at` date row now reads "Resolved" instead of "Created" — `Argument` has no creation-timestamp column, and this value is when the resolve pipeline step completed. The comment above it now states the resolved position (relabel, no schema change) rather than deferring the fix, and cites the folded todo by filename. The Published-label treatment from plan 48-10 is untouched.
- **`/admin/help`** (new route, linked from `AdminSubNav` after "People Editor"): a static, server-data-free operator reference in the existing admin idiom (inline styles only, no component library). Four cards: Lifecycle statuses (candidate/draft/published/unpublished, noting `pipeline`'s migration-0027 retirement), Trust tiers (verified/trusted/provisional/uncertain, with `derive_tier`'s seven ordered rules transcribed verbatim from `api/domain/trust.py` and the zero-constituent floor rule), Review states (unreviewed/needs_review/operator_confirmed/operator_edited with the UI-SPEC's badge colors, and the two easy-to-miss transition rules — D-25's no-return-to-unreviewed and D-24's no-bulk-confirm), and Publish gates (the non-overridable resolve-completeness gate and the overridable, never-sticky trust gate, in evaluation order). Every speaker role is described identically; the page contains no ranking, scoring, or comparative language, and no real Justice/advocate name.
- **`api/tests/test_phase49_cleanup_contract.py`** (new, 20 tests): three independently `-k`-selectable groups matching this plan's three tasks — `popover` (8 tests), `status_card` (3 tests), `help_page` (9 tests) — with a module docstring restating the memory-note caveat that these are source-text assertions, not behavioral proof.

## Task Commits

Each task was committed atomically, plus one follow-up robustness fix and the todo close-out:

1. **Task 1 — popover side inheritance + post-create selection:** `7a623012f` (feat)
2. **Task 2 — Status card label fix:** `091786013` (fix)
3. **Task 3 — Admin Help page + subnav link + test module:** `f6ce277c9` (feat)
4. **Follow-up — 375px badge-row wrap fix + move the three closed todos to `todos/completed/`:** `321a62b4a` (fix)

## Files Created/Modified

- `app/src/lib/components/CreatePersonPopover.svelte` — `initialSide` prop, `side` state initializer, `resetForm()`
- `app/src/lib/components/ResolveCard.svelte` — `initialSide` passed at the call site; `s.comboQuery` set in `handlePersonCreated`
- `app/src/routes/admin/arguments/[id]/+page.svelte` — Status card `resolved_at` row relabelled "Resolved"; comment rewritten
- `app/src/routes/admin/help/+page.svelte` — new operator reference page (328 lines)
- `app/src/lib/components/AdminSubNav.svelte` — new "Help" link
- `api/tests/test_phase49_cleanup_contract.py` — new, 20 tests across 3 groups

## Decisions Made

- Status-card label took option 1 (relabel, no schema change) — pre-decided in the plan's `<planner_decisions>`, executed as written.
- review_state badge on the Help page sized like the 14px status badge rather than the 12px passive tier badge (review_state is a primary, operator-actionable axis per the UI-SPEC's own screen contract) — this page's own presentational choice; plan 49-05's real queue screen owns the final formula.
- Added `flex-wrap: wrap` to the Help page's badge rows (not in the plan's action text) to satisfy the plan's own 375px human-check requirement, matching the existing codebase convention.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Help page badge+description rows would not wrap on a narrow viewport**
- **Found during:** Task 3, pre-emptively while preparing for the plan's own 375px `<human-check>` requirement
- **Issue:** The plan's action text specified the row layout (`display: flex; align-items: baseline; gap: 12px;`) but did not mention `flex-wrap`, and the plan's own human-check explicitly requires "no horizontal scroll" at 375px.
- **Fix:** Added `flex-wrap: wrap` to all 12 badge+description rows, matching the established codebase convention for this exact row shape (e.g. `admin/people/[id]/+page.svelte:375`, `admin/people/new/+page.svelte:112`).
- **Files modified:** `app/src/routes/admin/help/+page.svelte`
- **Verification:** `npm --prefix app run check` clean; visual confirmation deferred to the human browser pass (see Known Stubs / Next Phase Readiness below).
- **Committed in:** `321a62b4a`

**2. [Rule 3 - Blocking, tooling gap] Requirements traceability table's annotated "Pending (shared with ...)" cell blocked `requirements mark-complete`**
- **Found during:** close-out, `update_requirements` step
- **Issue:** `gsd-tools query requirements.mark-complete REVIEW-01` returned `not_found` even though `requirements.ready-ids` correctly reported REVIEW-01 as ready. The traceability row's Status cell read `Pending (shared with 49-02/49-03; not all declaring plans complete)` — a previous plan's annotation — and `mark-complete`'s row-update regex requires an exact `Pending` (or `Gaps Found`) match, not a prefix.
- **Fix:** Rewrote the cell to plain `Pending` (the annotation's information — which plans it was shared with — was already stale now that 49-03 is the last declaring plan), then re-ran `mark-complete`, which flipped both the checkbox and the traceability row cleanly.
- **Files modified:** `.planning/REQUIREMENTS.md`
- **Verification:** `requirements.mark-complete REVIEW-01` returned `write_set_complete: true`; `grep -n "REVIEW-01" .planning/REQUIREMENTS.md` shows `[x]` and `Complete`.
- **Committed in:** included in the final metadata commit for this plan.

---

**Total deviations:** 2 (1 Rule 2 missing-critical, 1 Rule 3 blocking/tooling)
**Impact on plan:** Both are small, bounded, in-scope fixes. No architectural changes, no scope creep.

## Issues Encountered

**Could not complete the plan's `<human-check>` browser walkthroughs.** Both Task 1 (popover side inheritance/selection) and Task 3 (Help page visual/apolitical read-through) require an authenticated `/admin/**` session. This sandbox's permission policy denied a `cat .env` read attempted for a different reason earlier in this session, and authenticating requires `ADMIN_USERNAME`/`ADMIN_PASSWORD` (or forging a session cookie with `SESSION_SECRET`) — all of which live in `.env`/`app/.env`. Consistent with this org's credential-handling posture, this executor did not attempt to work around that denial (e.g. via a different file-reading tool). Instead:

- Read the exact diff for both popover changes line-by-line and confirmed the logic against the plan's stated behavior.
- Ran `npm --prefix app run check` — 0 errors (one new benign `state_referenced_locally` warning on `initialSide`, the same class already present 36 times elsewhere in this codebase for prop-initialized `$state`).
- Ran the full pytest suite (1252 passed, 5 xfailed, 2 failed — both are the pre-existing, out-of-scope `test_admin_jobs_service.py` failures named in this plan's environment notes; no new failures).
- Started both dev servers and confirmed via the reload logs that neither crashed picking up the new route/changes, and confirmed `/admin/help` returns a clean `302` (session-gated, no `500`) rather than a server error.

**A human operator should complete both `<human-check>` walkthroughs before this plan is considered UAT-complete** — this is recorded as `human_judgment: true` on coverage items D1, D2, and D4 above, not silently marked done. This mirrors the precedent already set in `49-01-SUMMARY.md`'s own unresolved live-browser recheck item.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three folded todos are closed at the code level; pending files moved to `.planning/todos/completed/`.
- **Open item for a human:** walk through the Task 1 popover flow (toggle a row to Bench, open "Create new bench person", confirm Bench is pre-selected, close/reopen, create a person, confirm Resolved As shows the name; repeat on an Advocate row) and the Task 3 Help page visual/apolitical read-through at `/admin/help` (badge colors, 375px width, no ranking language) — both are blocked on this environment lacking authenticated browser access, not on any known defect.
- REVIEW-01 is now `Complete` in `.planning/REQUIREMENTS.md` — it was the last of this phase's three declaring plans (49-01/49-02/49-03) to finish.
- Plan 49-04 (authority ladder) and 49-05 (review UI) are unaffected by this plan's scope — no shared files.

## Self-Check: PASSED

- `app/src/routes/admin/help/+page.svelte`, `api/tests/test_phase49_cleanup_contract.py` — confirmed present via `git show`/`git log --stat`.
- Commits `7a623012f`, `091786013`, `f6ce277c9`, `321a62b4a` all found in `git log --oneline --grep="49-03"`.
- `./.venv/bin/python -m pytest api/tests/test_phase49_cleanup_contract.py -v` → 20 passed; `-k popover` → 8 passed; `-k status_card` → 3 passed; `-k help_page` → 9 passed (8+3+9=20, no overlap/gap).
- `./.venv/bin/python -m pytest -q` (full suite) → 1252 passed, 5 xfailed, 2 failed (both pre-existing, named, out-of-scope).
- `npm --prefix app run check` → 0 errors, 37 warnings (36 pre-existing + 1 new benign `state_referenced_locally` on `initialSide`).
- `grep -c 'class=' app/src/routes/admin/help/+page.svelte` → 0.
- All 12 required vocabulary labels confirmed present in the Help page source.

---
*Phase: 49-review-model*
*Completed: 2026-08-23*
