---
phase: 49
slug: review-model
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-21
validated: 2026-08-23
---

# Phase 49 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `49-RESEARCH.md` § Validation Architecture; audited against shipped code 2026-08-23.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`.venv/bin/pytest`, verified present) |
| **Config file** | `pytest.ini` at repo root, with the isolation-critical `conftest.py` beside it |
| **Quick run command** | `./.venv/bin/python -m pytest api/tests/test_<module>.py -x` |
| **Full suite command** | `./.venv/bin/python -m pytest` |
| **Full-suite result at phase close** | 1414 passed / 5 xfailed / 0 failed (49-06 §6 gate) |
| **Phase 49 module total** | 210 tests across 8 modules, all green (re-run at audit, 2026-08-23) |

**Invocation-shape caution (CLAUDE.md, Phase 45 D-03):** the `TEST_DATABASE_URL` redirect lives in the
repo-root `conftest.py`. Never invoke a subset of tests in a way that bypasses it. The regression guard is
`tests/test_pytest_isolation_invocation_shapes.py`.

**Known runtime cost (not a defect):** the `api/tests` suite runtime roughly tripled (342s → ~550-820s)
because the autouse `_sweep_orphaned_value_discrepancies` fixture in `api/tests/conftest.py` performs a DB
round-trip after each test. Flagged in `49-VERIFICATION.md` for a future look.

---

## Sampling Rate

- **After every task commit:** the relevant new/extended test file only, fail-fast (`-x`)
- **After every plan wave:** `./.venv/bin/python -m pytest api/tests -q`
- **Before `/gsd-verify-work`:** full suite green (`./.venv/bin/python -m pytest`) **plus** D-32's one live
  browser walkthrough of an authority conflict (operator edits a corpus value, a second writer disagrees)
- **Max feedback latency:** single-file quick run — target < 60s (the six fast modules run in 54s combined)

**Why the browser walkthrough is non-negotiable:** three of Phase 48's defects were found by operator
browser testing and none by the 1209-test suite. Automated green is necessary, not sufficient.

**Outcome this phase:** D-32's walkthrough was executed at the data/API layer (`49-EVIDENCE.md` §5) and
found a real, phase-central defect the whole suite had missed — `_argument_attention_predicate` lacked an
open-discrepancy inclusion leg, so a recorded discrepancy was invisible in the queue. Fixed in-plan (49-06)
and now pinned by `test_discrepancy_alone_includes_argument_and_lists_constituent`. The browser-visual half
of that walkthrough remains outstanding (Manual-Only item 7).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 49-01 T2 | 49-01 | 1 | REVIEW-01 | — | N/A | integration | `./.venv/bin/python -m pytest api/tests/test_review_state_schema.py -x` | ✓ 6 tests | ✅ green |
| 49-03 T1-T3 | 49-03 | 2 | REVIEW-01 | — | N/A | static/structural | `./.venv/bin/python -m pytest api/tests/test_phase49_cleanup_contract.py -x` | ✓ 20 tests | ✅ green |
| 49-04 T1-T2 | 49-04 | 3 | REVIEW-02 | T-49-authority | Equal-or-higher-authority disagreement records a discrepancy, never overwrites | unit + integration | `./.venv/bin/python -m pytest api/tests/test_authority_matrix.py -x` | ✓ 70 tests | ✅ green |
| 49-02 T2 | 49-02 | 2 | REVIEW-02 | T-49-authority | Re-import preserves operator review_state and operator-edited name parts | integration | `./.venv/bin/python -m pytest pipeline/tests/test_import_justices_csv.py pipeline/tests/test_import_convokit_core.py -x` | ✓ 75 tests | ✅ green |
| 49-01 T1 / 49-05 T1 | 49-01, 49-05 | 1, 4 | REVIEW-03 | T-49-idor | Queue query scoped by admin auth; no cross-argument leakage | integration | `./.venv/bin/python -m pytest api/tests/test_admin_review_service.py -x` | ✓ 30 tests | ✅ green |
| 49-05 T2-T3 | 49-05 | 4 | REVIEW-03 | — | N/A | static/structural | `./.venv/bin/python -m pytest api/tests/test_phase49_review_ui_contract.py -x` | ✓ 14 tests | ✅ green |
| 49-04 T3 | 49-04 | 3 | REVIEW-04 | T-49-idor, T-49-massassign | Scoped-SELECT-then-UPDATE; Pydantic allow-list body | integration | `./.venv/bin/python -m pytest api/tests/test_admin_review_service.py::test_patch_confirm_advances_review_state_and_recomputes_tier -x` | ✓ | ✅ green |
| 49-02 T3 | 49-02 | 2 | REVIEW-05 | — | N/A | static/structural (AST) | `./.venv/bin/python -m pytest api/tests/test_legacy_review_mechanism_removed.py -x` | ✓ 2 tests | ✅ green |
| 49-04 T3 | 49-04 | 3 | D-34 | T-49-leak | `review_state`/`source`/`method`/discrepancy fields never reach a public response | structural | `./.venv/bin/python -m pytest api/tests/test_trust_public_leak_ban.py -x` | ✓ 59 tests (BANNED_KEYS 1→7) | ✅ green |
| 49-06 T1 | 49-06 | 5 | D-33 | — | Dev route mounted only when `settings.environment == development` | integration | `./.venv/bin/python -m pytest api/tests/test_admin_dev_unresolved_fixture.py -x` | ✓ 9 tests | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Audit correction (2026-08-23):** the pre-execution draft of this table named
`api/tests/test_admin_review_service.py::test_resolve_recomputes_trust` for REVIEW-04. That node id was
never created — running it errors with `not found: ... test_resolve_recomputes_trust`. The behavior it was
meant to pin *is* covered, by `test_patch_confirm_advances_review_state_and_recomputes_tier`, which the
table now names. This was the only executable defect the audit found.

---

## Wave 0 Requirements

- [x] `api/tests/test_review_state_schema.py` — REVIEW-01 (enum presence + all four values on both `people`
      and `argument_participants`; `test_people_review_state_shares_udt_with_argument_participants` proves
      the shared UDT after the 0029 fold)
- [x] `api/tests/test_authority_matrix.py` — REVIEW-02 (`test_matrix_exercises_every_combination` holds the
      exhaustiveness D-32 demanded; the OPERATOR/OPERATOR carve-out is pinned by
      `test_operator_over_operator_accepts_and_records`)
- [x] `api/tests/test_admin_review_service.py` — REVIEW-03 / REVIEW-04 (queue query with tier × review_state
      × status filters, the full confirm / confirm_unattributable / reflag action set, trust recompute)
- [x] `api/tests/test_legacy_review_mechanism_removed.py` — REVIEW-05 (AST-based, non-vacuous structural
      proof, with docstring-node and `downgrade()`-subtree exemptions)
- [x] Extend `api/tests/test_trust_public_leak_ban.py` — D-34 (BANNED_KEYS widened 1 → 7, iterated per
      reachable public model, plus an AST import ban on `api.domain.authority` / `api.schemas.admin_review`)
- [x] **Dev-only fixture mechanism for the unresolved-speaker case (D-33)** — delivered by 49-06 as
      `api/services/admin_dev.py::seed_unresolved_speaker_fixture` + `POST /api/admin/dev/seed-unresolved-speaker`,
      mounted only in development. **RESEARCH Pitfall 4's premise was false** — a live corpus path *can*
      produce an unresolved speaker (argument 1788 had 11 `person_id IS NULL` rows from a job parked
      pre-resolve). The seeder's justification is its own standalone value as a deterministic, repeatable
      fixture, not the disproven premise. See `49-EVIDENCE.md` §1.

*Framework install: none needed — pytest and all fixtures already existed project-wide.*

---

## Manual-Only Verifications

All eight items below are browser-visual. None was worked around: this sandbox's permission policy denies
reading `.env` (`ADMIN_USERNAME` / `ADMIN_PASSWORD` / `SESSION_SECRET`), so no authenticated `/admin/**`
browser session was reachable by any plan in this phase. All are recorded in `.planning/WINDOWS.md` as
`kind: unrun-verify` so they surface at ship time. Source: `49-EVIDENCE.md` §9.

| # | Behavior | Requirement | Why Manual | Test Instructions |
|---|----------|-------------|------------|-------------------|
| 1 | Confirm-vs-"Resolve speaker" conditional rendering on `/admin/review` | REVIEW-03, REVIEW-04 | Conditional render correctness by eye; not re-verified live since the tracer feedback-gate fix | Open `/admin/review`; confirm Confirm shows only on `person_id != null && review_state == needs_review` rows, and the Resolve-speaker deep link only on unresolved rows |
| 2 | `CreatePersonPopover` Bench/Advocate side inheritance | REVIEW-01 | Popover open/close state and the Resolved-As box are UI affordances the source-contract tests can only assert structurally | Toggle a row to Bench, open "Create new bench person", confirm Bench pre-selected; close/reopen; create a person; confirm the Resolved-As box shows the name. Repeat on an Advocate row |
| 3 | `/admin/help` visual + apolitical read-through | REVIEW-01, REVIEW-05 | Badge color rendering, 375px reflow, and apolitical-language judgement are human calls | Load `/admin/help`; check badge colors, no horizontal scroll at 375px, no ranking/comparison language by eye |
| 4 | Full `/admin/review` seven-item walkthrough | REVIEW-03, REVIEW-04 | Exactly the class of defect the 1209-test suite missed three times in Phase 48 | Tab switching; filter composition surviving a back-button press plus the active-filter indicator; expand/collapse including the zero-constituent blockers fallback; Confirm / Confirm-as-unattributable / Re-flag acting on the right row with D-26 stay-visible behavior; all five dashboard StatCards even in one row; the StatCard singular/zero-state link text; no horizontal scroll at 375px |
| 5 | 26-UAT Test 26 — Speakers card "Unresolved — choose a role" placeholder + disabled Save | REVIEW-01 | Reclassified `waived` → `blocked`; the data state is now reachable via the seeder, but visual confirmation still needs a human | Seed the unresolved speaker, open the Complexity fixture's argument edit page, confirm the placeholder and the disabled Save button |
| 6 | 14-UAT Test 8 — non-interactive avatar for an unresolved utterance | REVIEW-01 | Requires BOTH the seeded state AND a deliberate publish step the seeder does not perform | Seed, then publish the Complexity fixture, then view its public chat page |
| 7 | D-32 authority-conflict walkthrough — **visual half only** | REVIEW-02, REVIEW-04 | Data/API layer fully verified in `49-EVIDENCE.md` §5 (and found a real defect); only the Discrepancy badge's rendering was never observed | Run the §5a script, then open `/admin/review` and confirm the Discrepancy badge and the incoming-vs-existing detail render on the affected constituent |
| 8 | "Seed unresolved speaker" Dev Tools button + success line | D-33 | Backend and form action fully tested; the button's own rendering/behavior never observed | Open `/admin`, click the button, confirm the success line |

**Recommended single-sitting order** (from `49-EVIDENCE.md` §9): (a) `/admin` → Reset to Fixture → Seed
unresolved speaker — closes item 8 and sets up 5/7 in one motion; (b) the Complexity fixture's argument edit
page — item 5; (c) `/admin/review` — items 1, 4, 7; (d) the `CreatePersonPopover` / `/admin/help` flows —
items 2, 3; (e) publish the Complexity fixture and view its public page — item 6 (this leaves a fixture in a
modified state until the next reset).

**Retired manual item (2026-08-23):** the pre-execution draft listed "review-queue filter combinations
render correctly" as manual partly because RESEARCH Pitfall 3 found the dashboard grid hardcoded to
`repeat(4, 1fr)` at `app/src/routes/admin/+page.svelte:240`. Plan 49-05 widened it to `repeat(5, 1fr)` and
the layout contract is now automated by
`test_phase49_review_ui_contract.py::test_dashboard_has_five_column_grid_and_five_statcards`. The residual
human-eye portion of that item is folded into Manual-Only item 4.

---

## Security Domain (ASVS L1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | `/admin/review` inherits the existing router-level `verify_admin_token` dependency |
| V3 Session Management | No | No change to session handling |
| V4 Access Control | **Yes** | Scoped-SELECT-then-UPDATE (WHERE both parent id AND child id match), per `update_participant_side` at `api/services/admin_arguments.py:725-727` |
| V5 Input Validation | **Yes** | Pydantic allow-list-only-writable-fields, per `ParticipantSideUpdate` at `api/schemas/admin_arguments.py:44-55` |
| V6 Cryptography | No | Not implicated |

| Threat Ref | Pattern | STRIDE | Mitigation | Verified By |
|---|---|---|---|---|
| T-49-leak | Public disclosure of operator-only trust/review data | Information Disclosure | BANNED_KEYS widened 1 → 7 + AST import ban (D-34) | `test_trust_public_leak_ban.py` (59) |
| T-49-idor | IDOR on cross-argument / cross-person writes | Tampering | Scoped-SELECT-then-UPDATE | `test_admin_review_service.py` (30) |
| T-49-massassign | Mass assignment via overly permissive PATCH body | Tampering | Pydantic schema exposing only intended writable fields | `test_admin_review_service.py` (30) |
| T-49-authority | Re-import silently overwriting human-confirmed work | Tampering | Authority-ladder gate + discrepancy record; "operator work is sacred" | `test_authority_matrix.py` (70) + pipeline rerun guards |

Full threat verification: `49-SECURITY.md`.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s for quick runs (six fast modules: 54s combined)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-08-23 — all five requirements (REVIEW-01…REVIEW-05) plus D-33 and D-34 carry
green automated verification. The eight Manual-Only items are browser-visual confirmations of already
automated behavior, not uncovered requirements, and are tracked as `unrun-verify` in `WINDOWS.md`.

---

## Validation Audit 2026-08-23

| Metric | Count |
|--------|-------|
| Requirements audited | 5 (+ D-33, D-34) |
| COVERED | 7 |
| PARTIAL | 0 |
| MISSING | 0 |
| Gaps found | 7 (all documentation; 1 executable) |
| Resolved | 7 |
| Escalated | 0 |
| Tests generated | 0 (none needed — every requirement already had green coverage) |

**Gaps found and closed:**

1. **REVIEW-04's automated command was unrunnable** — named `test_resolve_recomputes_trust`, a node id that
   was never created. Repointed to `test_patch_confirm_advances_review_state_and_recomputes_tier`. *This was
   the only defect that would have failed if executed.*
2. Per-task map was never updated post-execution — every Task ID `TBD`, every status `⬜ pending`, every
   `File Exists` `❌ W0`, despite all files shipping green. Filled from the six SUMMARY files.
3. Three shipped test modules were absent from the map entirely: `test_phase49_cleanup_contract.py` (20),
   `test_phase49_review_ui_contract.py` (14), `test_admin_dev_unresolved_fixture.py` (9). Added.
4. REVIEW-02's pipeline-boundary coverage (`test_rerun_preserves_operator_review_state`,
   `test_matched_person_with_operator_edited_parts_never_overwritten`) was unmapped — the domain matrix
   alone does not prove a *re-import* respects the ladder. Added as its own row.
5. Wave 0 checklist was entirely unchecked, including the D-33 fixture mechanism delivered by 49-06.
   Checked off, with RESEARCH Pitfall 4's disproven premise noted inline.
6. Manual-Only row 2 was stale — it cited the `repeat(4, 1fr)` StatCard grid that 49-05 fixed and automated.
   Retired, with the residual human-eye portion folded into item 4.
7. The eight real outstanding browser-visual items from `49-EVIDENCE.md` §9 were not represented in the
   Manual-Only table. Imported with instructions and the recommended single-sitting order.

**Verification method:** all eight Phase 49 modules re-run at audit time —
`171 passed in 53.66s` (six fast modules) and `39 passed in 22.61s` (review service + dev fixture),
210 tests, 0 failures. The stale REVIEW-04 node id was confirmed unrunnable by direct invocation.
