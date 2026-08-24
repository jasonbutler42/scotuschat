---
phase: 49-review-model
verified: 2026-08-23T18:00:00Z
status: gaps_found
score: 5/5 roadmap success criteria verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:

    - "Resolving a review item (confirm or edit) advances its review_state and recomputes the affected argument's trust (ROADMAP SC4 / REVIEW-04) — the 'create new person' branch of the resolve flow (create_person_for_job) now advances review_state to OPERATOR_EDITED and closes its own open value_discrepancy rows, matching its sibling writers."
  gaps_remaining: []
  regressions: []
human_verification:

  - test: "Toggle a Resolve-card row to Bench, open 'Create new bench person,' confirm Bench is pre-selected in the popover; close and reopen without toggling again; repeat on an Advocate row."
    expected: "The popover's radio pre-selection always matches the row's CURRENT side at the moment it opens."
    why_human: "Known, code-confirmed defect (WR-01, 49-REVIEW.md), left unfixed by explicit human scope decision (Criticals only this pass) — CreatePersonPopover.svelte initializes `side = $state(initialSide)` once at mount and only resyncs on close (resetForm), not on open or on a later prop change. Needs a human to confirm the visual/interactive symptom and to decide whether to fix it in this phase or defer."

  - test: "Full /admin/review screen walkthrough: tab switching; filter composition surviving back-button; expand/collapse including zero-constituent blockers fallback; Confirm/Confirm-as-unattributable/Re-flag acting on the correct row; five StatCards in one row; no horizontal scroll at 375px."
    expected: "Matches 49-05's UI-SPEC/must_haves exactly."
    why_human: "Browser-only visual/interactive verification; this sandbox cannot authenticate to /admin/** (denied .env read for ADMIN_USERNAME/ADMIN_PASSWORD/SESSION_SECRET), consistent with 49-EVIDENCE.md §9 item 4. NOT TICKED by 49-08: the no-horizontal-scroll-at-375px sub-item is now STRUCTURALLY fixed (G-49-5a, source-contract tests green — three overflow-x: auto containers plus an auto-fit grid track floor with an executable track-fit arithmetic gate), but the same credential gap blocked 49-08 from running this browser pass, so the item stays open pending a visual look."

  - test: "26-UAT Test 26 (Speakers card 'Unresolved — choose a role' placeholder + disabled Save) and 14-UAT Test 8 (non-interactive avatar for an unresolved utterance), on the seeded live data state."
    expected: "Placeholder/disabled-Save render for 26-UAT; plain non-clickable avatar circle for 14-UAT (second precondition: the fixture must also be published, which the seeder deliberately does not do)."
    why_human: "Data/API layer confirmed by source trace and live query in 49-EVIDENCE.md §2/§3; the actual browser rendering was never observed, for the same credential reason."

  - test: "D-32's authority-conflict walkthrough's Discrepancy badge — actual visual rendering on /admin/review."
    expected: "A visible 'Discrepancy' badge on the flagged constituent, matching 49-05's E6 spec."
    why_human: "Fully verified end-to-end at the data/API layer (49-EVIDENCE.md §5); the badge's own rendering was never observed in a browser."

  - test: "The Dev Tools 'Seed unresolved speaker' button and its success line on /admin."
    expected: "Clicking the button calls the seeder and displays a success line naming the Complexity fixture and 'uncertain'."
    why_human: "Backend and form action fully tested; the button's own rendering/behavior was never observed in a browser."
---

> **REOPENED 2026-08-24 — status changed `passed` -> `gaps_found`.** The 5/5 score above
> reflects the 2026-08-23 automated/code verification and remains accurate for what it
> measured. It was superseded by the human UAT session completed 2026-08-24
> (`49-UAT.md`, 31 passed / 3 issues / 0 pending), which found **4 open gaps** that the
> code-level pass could not see because they are operator-facing defects:
>
> | Gap | Severity | Summary |
> |-----|----------|---------|
> | `G-49-3`  | major    | No bench<->advocate control on the Speakers card; `is_bench` arrives derived and is not operator-correctable |
> | `G-49-4a` | minor    | Review-queue action link reads a bare "Edit"; one static label cannot cover both `argumentEditHref` branches |
> | `G-49-4b` | minor    | "constituent" leaked from an internal adjective into operator copy; plus `1 constituent need review` agreement bug |
> | `G-49-5a` | minor    | Horizontal scroll at 375px from two independent causes; UAT sub-items 5 and 7 are in direct tension |
>
> One further gap, `G-49-9a` (unresolved-avatar footprint asymmetry), was found and
> **fixed in-session** (commit `690d51e20`) and is already closed.
>
> Also still open from the original pass, unchanged by the UAT: **WR-01**. UAT test 7
> passed, but only because the common interaction path masks the stale-`$state` bug —
> `CreatePersonPopover.svelte:48` still captures `initialSide` once at mount. Do not tick
> `human_verification` item 1 below on the strength of that pass.
>
> UAT sub-item 5.6 (StatCard singular/zero-state copy) was never observed — it needs the
> review queue at exactly 1 and at 0 — and is recorded as NOT OBSERVED, not as a pass.

# Phase 49: Review Model Verification Report

**Phase Goal:** Operator gets a real review workflow over the candidate pool — a unified `review_state` + provenance record replacing the legacy `name_needs_review` mechanism, an authority ladder governing re-import overwrites, and an operator review queue that lists, filters, and lets the operator resolve attention-worthy items with trust recomputed on resolution.

**Verified:** 2026-08-23
**Status:** passed
**Re-verification:** Yes — after gap closure (commit `6c7a0f7cb`)

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Operator-editable rows carry a four-state `review_state` | VERIFIED (regression check — unchanged since prior pass) | `ReviewState` enum (api/models/models.py:92-101); no commits touched `alembic/versions/` since the prior verification (`git log 113c87276..HEAD -- alembic/versions/` empty). |
| 2 | A re-import disagreeing with an equal-or-higher-authority value records a discrepancy instead of silently overwriting | VERIFIED (re-confirmed against live source) | `decide_write` (api/domain/authority.py:181-184): `if incoming_rank == existing_rank == AuthorityRank.OPERATOR: return ACCEPT_AND_RECORD`; every other equal-rank pair, including CORPUS/CORPUS, falls through to `REJECT_AND_RECORD`. `pytest api/tests/test_authority_matrix.py -q` -> 70 passed (this run). |
| 3 | Operator can open a review queue listing everything needing review, filterable by trust tier and review state | VERIFIED (regression check — unchanged since prior pass) | `app/src/routes/admin/review/+page.svelte` — still 621 lines, no commits since the prior verification touched it. |
| 4 | Resolving a review item (confirm or edit) advances its `review_state` and recomputes the affected argument's trust | **VERIFIED (gap closed)** | Commit `6c7a0f7cb` adds, inside the existing `if participant is not None and body.side is not None:` guard in `create_person_for_job` (api/services/admin_jobs.py:1164-1180), after both `apply_participant_value_change` calls and before `recompute_argument_tier`: an `UPDATE ... SET review_state = OPERATOR_EDITED` scoped to `(id, argument_id)`, then `close_open_discrepancies(db, target_type="argument_participant", target_id=participant.id)`. Confirmed only one `await db.commit()` exists in the function (line 1191, after `recompute_argument_tier`) — no second commit was introduced. Live-run regression test `test_create_person_for_job_closes_discrepancies_and_advances_review_state` (api/tests/test_admin_jobs_phase25.py:639-757) re-fetches the participant from a **fresh** `AsyncSessionLocal()` session (not the function's return value, which only carries the created `Person`) and asserts `review_state == ReviewState.OPERATOR_EDITED` and zero open `ValueDiscrepancy` rows for that participant. Ran independently: `1 passed in 2.67s`. |
| 5 | The legacy `name_needs_review`/`name_extraction_metadata` mechanism is folded into the unified record, no parallel mechanism remains | VERIFIED (regression check — unchanged since prior pass) | `test_legacy_review_mechanism_removed.py` re-run as part of the targeted suite below: 2 passed. |

**Score:** 5/5 roadmap success criteria verified.

### Gap Closure — Independent Re-Verification

The task explicitly asked not to take the commit-message/summary narrative on trust. Each of the four required checks was independently re-run against the live code:

| Check | Result | Evidence |
|---|---|---|
| (a) `create_person_for_job` advances `review_state` and closes discrepancies, inside the correct guard, with no second `db.commit()` | CONFIRMED | Diff (`git show 6c7a0f7cb -- api/services/admin_jobs.py`) inserts the `UPDATE ArgumentParticipant SET review_state=...` + `close_open_discrepancies(...)` block directly after the second `apply_participant_value_change` call and directly before the pre-existing `recompute_argument_tier(db, job.argument_id)` comment/call — all still inside the single `if participant is not None and body.side is not None:` block. Counted `db.commit()` occurrences inside the function body: exactly 1 (unchanged from before the fix). |
| (b) No ungated `update(ArgumentParticipant)` / `update(Person)` write to value columns has reappeared | CONFIRMED | `grep -n "update(ArgumentParticipant)\|update(Person)" api/services/*.py` returns 9 call sites total. Read every one: two are the gate functions themselves (`apply_participant_value_change` at admin_review.py:200, `apply_person_value_change` at admin_review.py:264 — these ARE the gate, writing `{field: incoming_value}` only after `decide_write` authorizes it); the remaining seven write only `review_state`, `status`, `source`/`method` provenance backfill (guarded by `source IS NULL`), or (in the dev-only seeder, environment-gated) an intentional `person_id=None` reset for test-fixture purposes. No raw value-column write bypassing `apply_participant_value_change`/`apply_person_value_change` exists anywhere. |
| (c) CORPUS-vs-CORPUS differing writes still `REJECT_AND_RECORD`; OPERATOR/OPERATOR is the only equal-rank exception | CONFIRMED | `api/domain/authority.py:179-184` — `if incoming_rank == existing_rank == AuthorityRank.OPERATOR: return ACCEPT_AND_RECORD`; the next line is the unconditional `return REJECT_AND_RECORD` fallthrough for every other equal-rank pair. `test_authority_matrix.py` (70 passed, this run) includes the CORPUS/CORPUS-keyed cases. |
| (d) `api/domain/authority.py` still pure; `api/domain/trust.py` unchanged since Phase 48 | CONFIRMED | `grep -n "^import\|^from" api/domain/authority.py` -> only `from __future__ import annotations` and `import enum`. `git log --oneline -- api/domain/trust.py` -> most recent commit is still `f9bcbed90` (Phase 48-09); nothing in Phase 49 (including the gap-closure commit) touched it. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `alembic/versions/0028_review_state_and_discrepancy.py` | review_state enum, participant columns, value_discrepancy table | VERIFIED | Unchanged since prior pass; no commits since. |
| `alembic/versions/0029_person_review_state_fold.py` | people column swap-with-carry | VERIFIED | Unchanged since prior pass; no commits since. |
| `api/domain/authority.py` | Pure authority ladder | VERIFIED | Re-confirmed pure (imports only `enum`/`__future__`); OPERATOR/OPERATOR carve-out re-confirmed as sole equal-rank exception. |
| `api/services/admin_review.py` | Queue queries, gated writer, discrepancy record/close, four resolve actions | VERIFIED | Unchanged in this fix; re-run as part of the targeted suite (30 passed within the 268-test run below). |
| `api/services/admin_jobs.py` | Gated writers, including `create_person_for_job` now at review-resolution parity with its siblings | **VERIFIED (gap closed)** | See Gap Closure table above. |
| `app/src/routes/admin/review/+page.svelte` | Full queue screen | VERIFIED | Unchanged since prior pass (still 621 lines, no commits touching it). |
| `app/src/routes/admin/help/+page.svelte` | Operator documentation | VERIFIED | Unchanged since prior pass. |
| `api/services/admin_dev.py` (`seed_unresolved_speaker_fixture`) | Dev-only seeder | VERIFIED | Unchanged; still environment-gated to development. |
| `api/tests/test_admin_jobs_phase25.py` | Regression coverage for the gap closure | VERIFIED | New test `test_create_person_for_job_closes_discrepancies_and_advances_review_state` present, reads persisted state from a fresh session, ran independently and passed. |
| `.planning/phases/49-review-model/49-EVIDENCE.md` | Requirement-to-evidence record | VERIFIED (present) | |

### Key Link Verification

| From | To | Via | Status |
|---|---|---|---|
| `api/services/trust.py` | `api/domain/trust.py` | `_load_constituents` -> `derive_tier(source.value, method.value, review_state.value)` | WIRED |
| `api/services/admin_arguments.py::update_participant_side` | `api/services/admin_review.py` | `apply_participant_value_change` + `close_open_discrepancies` | WIRED |
| `api/services/admin_jobs.py::update_resolve_row_for_job` | `api/services/admin_review.py` | `apply_participant_value_change` + `close_open_discrepancies` | WIRED |
| `api/services/admin_jobs.py::resolve_job` | `api/services/admin_review.py` | `apply_participant_value_change` (CORPUS provenance) | WIRED |
| `api/services/admin_jobs.py::create_person_for_job` | `api/services/admin_review.py` | `apply_participant_value_change` (gated write) **followed by** `review_state=OPERATOR_EDITED` UPDATE and `close_open_discrepancies` (gap closed by `6c7a0f7cb`) | **WIRED** — write is gated AND the resolve-completion contract (D-15) is now honored, matching its three sibling writers exactly. |
| `app/src/lib/components/AdminSubNav.svelte` | `app/src/routes/admin/review/+page.svelte` | `/admin/review` link | WIRED |
| `app/src/routes/admin/review/+page.svelte` | argument edit page | `argumentEditHref(item)` on the "Edit" action | WIRED — this path no longer terminates in a stuck row; the participant it resolves via "create new person" now leaves the queue on the next load, since `review_state` advances and its discrepancies close. |

### Requirements Coverage

| Requirement | Status | Evidence |
|---|---|---|
| REVIEW-01 | SATISFIED | `review_state` enum + columns on both tables; unchanged since prior pass, `test_review_state_schema.py` re-run in the targeted suite. |
| REVIEW-02 | SATISFIED | Authority ladder + discrepancy recording; `test_authority_matrix.py` re-run independently, 70 passed. |
| REVIEW-03 | SATISFIED | Queue screen exists, filterable, deterministic ordering; unchanged since prior pass. |
| REVIEW-04 | **SATISFIED (gap closed)** | The queue's resolve actions and the "Edit" -> "create new person" resolve path both now advance `review_state` and close discrepancies. Regression test proves the previously-broken path from a fresh DB session. |
| REVIEW-05 | SATISFIED | Migration 0029 + `test_legacy_review_mechanism_removed.py` re-run, 2 passed. |

No orphaned requirements — union of `requirements:` across the six 49-0X-PLAN.md files still exactly matches REQUIREMENTS.md's Phase 49 rows (unchanged since prior pass).

### Anti-Patterns Found

None. The gap-closure diff (`api/services/admin_jobs.py` lines 1156-1180, `api/tests/test_admin_jobs_phase25.py` lines 639-757) scanned for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` — no matches. The inline comment referencing `49-VERIFICATION.md` cites the closed gap for context, not an open debt marker.

### Behavioral Spot-Checks / Targeted Test Runs

| Check | Command | Result |
|---|---|---|
| Regression test for the closed gap, run in isolation | `pytest api/tests/test_admin_jobs_phase25.py::test_create_person_for_job_closes_discrepancies_and_advances_review_state -q` | 1 passed in 2.67s |
| Combined review/jobs/legacy/leak-ban/dev-fixture/UI-contract/authority suite | `pytest api/tests/test_authority_matrix.py api/tests/test_admin_review_service.py api/tests/test_admin_jobs_phase25.py api/tests/test_admin_jobs_service.py api/tests/test_phase44_argument_role_roundtrip.py api/tests/test_review_state_schema.py api/tests/test_legacy_review_mechanism_removed.py api/tests/test_trust_public_leak_ban.py api/tests/test_admin_dev_unresolved_fixture.py api/tests/test_phase49_cleanup_contract.py api/tests/test_phase49_review_ui_contract.py -q` | 268 passed in 100.45s |

Full-suite run (1421 passed, 5 xfailed, 0 failed), `python3 -m compileall -q pipeline api scripts tests alembic` (exit 0), and `npm run check` (0 errors, 37 warnings) were already run by the orchestrator per the task's `<current_state>`; not re-run here in full, per the "run the full suite at most once" constraint — the targeted runs above are the net-new evidence for this re-verification pass and cover every file touched by the gap-closure commit plus every sibling writer for regression safety.

### Prohibitions Checked

| Statement | Status |
|---|---|
| No public response model declares `review_state`/`source`/`method`/discrepancy fields (D-34) | VERIFIED — `test_trust_public_leak_ban.py` re-run in the targeted suite, included in the 268 passed. |
| No aggregation of discrepancies/review states/tiers into per-person/per-role statistics or rankings | VERIFIED by source read — the gap-closure diff adds no aggregation of any kind. |
| No bulk-confirm control on the review queue (D-24) | VERIFIED — no change to the review queue screen in this fix. |
| `provenance_metadata` never cleared/rewritten as a side effect of a review action | VERIFIED by source read of the gap-closure diff — the added UPDATE touches only `review_state`; `provenance_metadata` is not referenced. |

## Gaps Summary

None. The single outstanding gap from the prior verification pass — `create_person_for_job` gating its `person_id`/`side` writes correctly but never advancing `review_state` past `UNREVIEWED` or closing the `value_discrepancy` rows those writes opened — is closed by commit `6c7a0f7cb`. The fix was independently re-derived from the diff (not the commit message) and confirmed to sit inside the correct existing guard block, introduce no second `db.commit()`, and be covered by a regression test that re-fetches persisted state from a fresh database session rather than trusting the function's return value. All four sibling writers (`update_participant_side`, `update_resolve_row_for_job`, `resolve_job`'s gated match-writes, and now `create_person_for_job`) carry the same gate-then-resolve pattern, and no ungated value-column write exists anywhere in the codebase. The authority ladder's OPERATOR/OPERATOR carve-out remains the sole equal-rank exception, and the two `api/domain/*` pure modules remain untouched/pure. The phase goal — a unified review workflow where every path that resolves an attention-worthy item actually clears it from the queue and advances trust — is now genuinely achieved.

The eight browser-only verification items (49-EVIDENCE.md §9) and the known WR-01 Svelte prop-capture bug remain open, exactly as disclosed, and are carried forward here as `human_verification` rather than gaps — none of them reflect missing work, and per the task's own framing they would not on their own drive a `gaps_found` verdict.

**Known cost, not a gap:** the `api/tests` suite runtime has roughly tripled (342s -> ~550-820s) because the `autouse` `_sweep_orphaned_value_discrepancies` fixture in `api/tests/conftest.py` performs a DB round-trip after each of 1083 tests. Behavior is correct; this is a real cost worth a future look, not a defect blocking this phase.

**Note for Phase 50 planning:** `49-RESEARCH.md` Pitfall 4's original false premise ("no live corpus path can produce an unresolved speaker") was never edited in that document itself. The correction lives in `49-EVIDENCE.md`, `WINDOWS.md`, `STATE.md`, and the seeder docstring — but a reader who goes straight to `49-RESEARCH.md` still meets the uncorrected claim. This verifier takes no position on whether that is adequate; it is flagged here for a human decision during Phase 50 planning, not treated as a Phase 49 gap (the research doc is a point-in-time artifact, and the correction is recorded elsewhere in the same phase's own trail).

---

_Verified: 2026-08-23_
_Verifier: Claude (gsd-verifier)_
