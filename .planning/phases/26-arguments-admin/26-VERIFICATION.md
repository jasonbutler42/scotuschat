---
phase: 26-arguments-admin
verified: 2026-07-08T18:00:00Z
status: human_needed
score: 17/17 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 15/17
  gaps_closed:
    - "Delete is blocked (returns False) whenever status is PUBLISHED or UNPUBLISHED; allowed only for DRAFT"
    - "Unified Speakers section: advocate rows get a role dropdown, title input, utterance count, and inline Save that persists accurate state"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Visually confirm the three arguments-list badge colors (Draft violet #a78bfa, Published green #4ade80, Unpublished orange #fb923c) render with sufficient contrast and are visually distinct side by side"
    expected: "Three clearly distinguishable badge colors, each with a text label"
    why_human: "Color rendering and contrast are visual concerns; grep confirms the hex values are present in code but not how they look together in the browser (carried forward from prior verification — unaffected by 26-05)"
  - test: "Open a pipeline job detail page for a run whose argument has already been created and confirm the RunStatusCard shows the grey 'Archived' badge instead of the job-status badge"
    expected: "Archived badge (#cbd5e1) overrides the jobStatus-driven badge for an already_created run"
    why_human: "Requires a live backend + a run in the already_created readiness state to observe (carried forward from prior verification — unaffected by 26-05)"
  - test: "Load the argument edit page for a live argument in each of the three lifecycle states (Draft, Published, Unpublished), and additionally for an argument with at least one unresolved (UNKNOWN-side) advocate. Visually confirm: Status card + Status history layout, Publish/Unpublish button placement inside the Status card, Speakers table column alignment for mixed bench/advocate rows, the advocate row's new 'Unresolved — choose a role' placeholder renders selected for an unresolved advocate, and the Save button is visibly disabled (dimmed, not-allowed cursor) for that row until a real role is chosen"
    expected: "Layout renders as specified in the UI-SPEC; no visual misalignment; the Unresolved state and disabled Save are visually unambiguous to an operator"
    why_human: "svelte-check and grep verify markup/logic correctness but not actual browser layout/rendering or the disabled-button visual treatment. Also surfaces WR-01 from the code review (still unresolved, confirmed present at +page.svelte:443) — the advocate row's <td colspan=\"3\"> spans only 3 of the 4 remaining logical columns, which will visibly misalign column borders against 5-column bench rows when both appear in the same table."
---

# Phase 26: Arguments Admin Verification Report

**Phase Goal:** The arguments admin screens accurately represent the three-state argument lifecycle (Draft / Published / Unpublished), the arguments list excludes pipeline-only rows, and the argument edit page has a status log, a unified Argument Details card, and a speakers section replacing the old advocate roles card
**Verified:** 2026-07-08T18:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap-closure plan 26-05

## Goal Achievement

This is a fresh, independent re-verification against the CURRENT codebase (not a re-statement of 26-05-SUMMARY.md's or 26-REVIEW.md's claims). Both files were consulted for context only; every finding below was re-derived by reading the actual source and by executing the actual regression tests and type-checker in this session.

### Gap 1 re-verification: delete_argument DRAFT-only gate (was FAILED, previously allowed deleting PIPELINE-status arguments)

**Direct code read** — `api/services/admin_arguments.py:669-670`:
```python
if argument.status != ArgumentStatusEnum.DRAFT:
    return False
```
This is a single positive condition keyed on `DRAFT`. It rejects PIPELINE, PUBLISHED, and UNPUBLISHED alike — the previously-confirmed hole (PIPELINE falling through to the delete cascade) is closed. The docstring above the gate (lines 636-660) was also updated to explicitly document that PIPELINE is blocked because an active `AdminJob` may still reference it.

**Regression tests** — read and executed fresh in this session (not taken on faith from the SUMMARY):
- `test_delete_argument_gate_keys_on_draft` (structural, always-runs, no DB) — ran it directly: **PASSED**. It asserts the gate references `ArgumentStatusEnum.DRAFT` and explicitly asserts the OLD `"PUBLISHED, ArgumentStatusEnum.UNPUBLISHED"` enumerated-tuple pattern is NOT present, which would catch a regression to the old (broken) gate.
- `test_delete_argument_returns_false_for_pipeline` (service, DB-guarded) and `test_delete_argument_returns_409_for_pipeline` (route, DB-guarded) exist and read correctly (create a PIPELINE-status argument, assert `False`/409). This environment has no live Postgres reachable (confirmed: even with `DATABASE_URL` exported, `api.core.database.AsyncSessionLocal` is `None` because the engine is only created inside the FastAPI `lifespan`, not at import — the exact same limitation that already applied to the pre-existing sibling test `test_delete_argument_returns_false_for_unpublished` before this phase). These tests report `skipped` here, matching the project's own documented pre-existing test pattern; this is not a new environment gap introduced by 26-05.
- Router (`api/routers/admin.py:970-978`) unchanged — still maps `False` → 409 with the (deliberately unchanged, per plan) "Only drafts can be removed" detail string, which remains accurate for PIPELINE.

**Verdict: ✓ VERIFIED.** Gap 1 is closed.

### Gap 2 re-verification: unresolved-advocate silent misclassification (was FAILED)

**Backend guard** — direct code read, `api/services/admin_arguments.py:542-547`:
```python
if side == SideEnum.BENCH:
    raise ValueError("BENCH cannot be set via participant side update")
if side in (SideEnum.UNKNOWN, SideEnum.ADVOCATE):
    raise ValueError(
        "An advocate's side must be resolved to Petitioner, Respondent, or Amicus"
    )
```
Placed before the DB `SELECT`, mirroring the existing BENCH guard. `test_update_participant_side_rejects_unresolved_side` (always-runs, no DB) — ran it directly in this session: **PASSED**. It calls `update_participant_side` with `SideEnum.UNKNOWN` and `SideEnum.ADVOCATE` and asserts `ValueError` in both cases.

**Frontend** — direct code read, `app/src/routes/admin/arguments/[id]/+page.svelte`:
- `VALID_SIDES = new Set(['PETITIONER', 'RESPONDENT', 'AMICUS'])` (line 67) and `speakerSideById` `$state<Record<number,string>>` (lines 68-73) seeded from `data.argument.speakers`, collapsing any side not in `VALID_SIDES` (i.e. `UNKNOWN` or legacy `ADVOCATE`) to the sentinel `'UNKNOWN'`.
- The `<select name="side">` (lines 458-477) now has a leading `<option value="UNKNOWN">Unresolved — choose a role</option>` and is driven by `bind:value={speakerSideById[speaker.participant_id]}` — no more reliance on per-option `selected={...}` (which was the root cause of the original silent-default-to-PETITIONER bug).
- The Save `<button>` (line 514) is `disabled={savingSpeakerId === speaker.participant_id || speakerSideById[speaker.participant_id] === 'UNKNOWN'}`, with matching `cursor`/`opacity` styling (lines 524-525) so the disabled state is visually distinguishable.
- `cd app && npm run check` — ran fresh in this session: **0 ERRORS** (793 files, 18 warnings — all pre-existing/unrelated to phase 26 files, e.g. `state_referenced_locally` hints in other components).

**Verdict: ✓ VERIFIED.** Gap 2 is closed. An unresolved advocate's side can no longer be silently written by an accidental Save — the UI makes the state explicit and blocks Save, and the backend independently rejects the value even if a submission were forced through.

**One non-blocking follow-on observed (not a gap against this phase's must-haves):** `speakerSideById` is seeded once at component setup and is not reset via an `$effect` keyed on `data.argument.id` the way the file's own `deleteConfirming`/`deleteSubmitting` state is (WR-07 in 26-REVIEW.md). If the SvelteKit `[id]` component instance were reused across a client-side navigation between two different argument edit pages, a stale seed could theoretically let the disabled-check miss a genuinely-unresolved row for the *new* page's data. This does **not** reopen the safety gap: the backend guard above rejects an `UNKNOWN`/`ADVOCATE` submission unconditionally regardless of what the client's `disabled` state computed, so no silent misclassification is possible even in that edge case — the worst outcome is a confusing "Save failed" 422 instead of a disabled button. This is recorded as a warning-level finding, not a truth failure.

### Observable Truths (full re-check, all 17 from the original must-haves list)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Publish/unpublish/re-publish set the correct `Argument.status` and each writes exactly one matching `ArgumentStatusLog` row | ✓ VERIFIED | `api/services/admin_arguments.py:490-503` (publish), `:592-611` (unpublish) — re-read fresh, unchanged from prior verification, not touched by 26-05 |
| 2 | `approve_job` writes one DRAFT ("Created") `ArgumentStatusLog` row alongside its existing status update | ✓ VERIFIED | `api/services/admin_jobs.py:511` — confirmed present, unchanged |
| 3 | The arguments list query returns DRAFT, PUBLISHED, and UNPUBLISHED rows; excludes only PIPELINE | ✓ VERIFIED | `api/services/admin_arguments.py:70-82` — confirmed present, unchanged |
| 4 | Delete is blocked (returns False) whenever status is PUBLISHED, UNPUBLISHED, **or PIPELINE**; allowed only for DRAFT | ✓ VERIFIED (was FAILED) | `api/services/admin_arguments.py:669-670` — `if argument.status != ArgumentStatusEnum.DRAFT: return False`. Structural regression test executed and passed this session |
| 5 | Slug is frozen (not re-derived) whenever `status != DRAFT` | ✓ VERIFIED | `api/services/admin_arguments.py:447` region — unchanged, not touched by 26-05 |
| 6 | Arguments list renders a distinct badge for each of Draft (violet), Published (green), and Unpublished (orange) | ✓ VERIFIED | `app/src/routes/admin/arguments/+page.svelte:18-25` — hex values confirmed present |
| 7 | Arguments list has a "Created" column between "Argued" and the row-actions column | ✓ VERIFIED | Confirmed unchanged (not touched by 26-05) |
| 8 | Each list row's action is status-driven: Draft and Unpublished show Publish; Published shows Unpublish | ✓ VERIFIED | Confirmed unchanged |
| 9 | The pipeline run status card shows an "Archived" badge (neutral grey) when the run's argument has already been created | ✓ VERIFIED | `app/src/lib/components/RunStatusCard.svelte:47,50` — confirmed unchanged |
| 10 | `GET /api/admin/arguments/{id}` returns a `status_log` array, one `{status, created_at}` entry per transition, oldest first | ✓ VERIFIED | Confirmed unchanged (not touched by 26-05) |
| 11 | `GET /api/admin/arguments/{id}` returns a `speakers` array covering ALL participants (bench + advocate) with a per-participant utterance count | ✓ VERIFIED | Confirmed unchanged |
| 12 | `PATCH /participants/{id}` accepts and persists an optional `title` alongside `side` for advocate rows | ✓ VERIFIED | Confirmed unchanged; title-write logic (lines 559-575) untouched by the new guard, which sits above it |
| 13 | Edit page Status card shows the current three-state badge, a "Created {date}" line, and a "Published {date}" line when set | ✓ VERIFIED | Confirmed unchanged |
| 14 | A "Status history" section lists every `status_log` entry as `{badge} — {date, time}`, oldest first, first DRAFT entry labelled "Created" | ✓ VERIFIED | Confirmed unchanged |
| 15 | Publish shows for Draft and Unpublished; Unpublish shows for Published; button lives with the Status card, not floating | ✓ VERIFIED | Confirmed unchanged |
| 16 | Unified Speakers section: advocate rows get a role dropdown, title input, utterance count, and inline Save that **persists accurate, non-destructive state**; bench rows show tenure-derived role or "Missing tenure" + Edit person, with utterance count | ✓ VERIFIED (was FAILED) | `+page.svelte:458-530` — explicit "Unresolved" placeholder, `bind:value`, Save disabled while unresolved, backend guard rejects UNKNOWN/ADVOCATE. Bench branch (lines 533+) confirmed unchanged |
| 17 | Delete is enabled only for Draft arguments (client); Published and Unpublished show the disabled button with the updated tooltip | ✓ VERIFIED | `app/src/routes/admin/arguments/[id]/+page.server.ts:77` — `can_delete = argument.status === 'draft'`, unchanged; now correctly backed end-to-end by the fixed server-side gate |

**Score:** 17/17 truths verified (both previously-failed truths now closed; no regressions found in the 15 previously-passing truths)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/services/admin_arguments.py` | DRAFT-only delete gate; UNKNOWN/ADVOCATE-rejecting `update_participant_side` guard | ✓ VERIFIED | Both re-read directly this session at their current line numbers |
| `api/tests/test_admin_arguments_service.py` | `test_delete_argument_gate_keys_on_draft`, `test_delete_argument_returns_false_for_pipeline`, `test_update_participant_side_rejects_unresolved_side` | ✓ VERIFIED | All three present; the two always-run tests executed and passed fresh this session |
| `api/tests/test_admin_arguments_routes.py` | `test_delete_argument_returns_409_for_pipeline` | ✓ VERIFIED (exists; DB-guarded, cannot execute against a live DB in this environment) | Present at line 243, correctly structured, mirrors the passing UNPUBLISHED sibling |
| `app/src/routes/admin/arguments/[id]/+page.svelte` | `speakerSideById` state, "Unresolved" placeholder option, Save-disable | ✓ VERIFIED | Confirmed at lines 67-73, 460, 473, 514, 524-525 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `delete_argument` | `Argument.status` | single positive `== DRAFT` gate | ✓ WIRED | Fixed; regression test executed and passed |
| `update_participant_side` | `SideEnum.UNKNOWN`/`ADVOCATE` rejection | pre-SELECT `ValueError` guard → router 422 | ✓ WIRED | Confirmed; regression test executed and passed |
| Advocate `<select>`/Save button | `speakerSideById` client state | `bind:value` + `disabled` expression | ✓ WIRED | Confirmed; `npm run check` 0 errors |
| (all other Phase 26 links from the original verification) | — | — | ✓ WIRED | Unaffected by 26-05; spot-checked for regressions (list filter, badges, RunStatusCard, status_log/speakers query, Status card/history rendering) — all confirmed present and unchanged |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| ALIST-02 | 26-01, 26-03 | List shows only Draft/Published/Unpublished; pipeline excluded | ✓ SATISFIED | Confirmed unchanged |
| ALIST-03 | 26-03 | Distinct badges for all three statuses | ✓ SATISFIED | Confirmed unchanged |
| ALIST-04 | 26-03 | "Created" column added | ✓ SATISFIED | Confirmed unchanged |
| AEDIT-01 | 26-02, 26-04 | Status card: badge, created date, published date | ✓ SATISFIED | Confirmed unchanged |
| AEDIT-02 (UI surface) | 26-01, 26-02, 26-04 | Full status log with timestamps for every transition | ✓ SATISFIED | Confirmed unchanged |
| AEDIT-05 | 26-02, 26-04 | Speakers section replaces Advocate Roles card + tenure gap warnings | ✓ SATISFIED | Confirmed unchanged |
| AEDIT-06 | 26-02, 26-04, 26-05 | Advocate role dropdown + title field + inline save | ✓ SATISFIED (was PARTIAL) | Dropdown/title/inline-save present and now safe: explicit Unresolved state, disabled Save, authoritative backend rejection |
| AEDIT-07 | 26-02, 26-04 | Bench speakers: tenure-derived role; Missing tenure + edit link | ✓ SATISFIED | Confirmed unchanged |
| AEDIT-08 | 26-01, 26-04 | Publish/Unpublish/re-Publish transitions | ✓ SATISFIED | Confirmed unchanged |
| AEDIT-09 | 26-01, 26-04, 26-05 | Danger Zone delete gate | ✓ SATISFIED (was NOT FULLY SATISFIED) | Backend gate now blocks PIPELINE in addition to PUBLISHED/UNPUBLISHED |

No orphaned requirements. All 10 IDs from the phase's declared requirement list (ALIST-02/03/04, AEDIT-01/02/05/06/07/08/09) are declared across the five plans (26-01 through 26-05) and match REQUIREMENTS.md's Phase 26 assignments. AEDIT-03/AEDIT-04 remain correctly attributed to Phase 23 and out of this phase's scope.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/src/routes/admin/arguments/[id]/+page.svelte` | 443 | `colspan="3"` on a cell holding content for 4 logical columns (WR-01, carried forward, unresolved) | ⚠️ Warning | Visual column misalignment between advocate and bench rows when both appear in the same table; non-blocking, cosmetic; not touched by 26-05 |
| `app/src/routes/admin/arguments/[id]/+page.svelte` | 67-73 | `speakerSideById` seeded once, not reset on route-param reuse (WR-07, new in 26-REVIEW.md) | ⚠️ Warning | Theoretical stale-seed edge case on back/forward navigation between two argument edit pages within the same component instance; does not reopen the data-safety gap because the backend guard is unconditional — worst case is a confusing failed-Save instead of silent misclassification |

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in any file modified by 26-05.

Out of scope for this phase's must-haves (noted for completeness, not treated as gaps here): 26-REVIEW.md's CR-01 (rerun_job local-disk ingest gap) and CR-02 (blank case_name/docket_number persistence) are real findings but map to pipeline-run/argument-metadata-edit behavior that is not part of this phase's stated goal, success criteria, or requirement IDs (ALIST-02/03/04, AEDIT-01/02/05/06/07/08/09). They are pre-existing/unrelated to the lifecycle-badges/status-log/speakers-section goal this phase targets and should be tracked separately (e.g., backlog or a future phase), not folded into Phase 26's gap set.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `test_delete_argument_gate_keys_on_draft` (always-run, DRAFT-only gate) | `.venv/Scripts/python.exe -m pytest api/tests/test_admin_arguments_service.py::test_delete_argument_gate_keys_on_draft -v` | `PASSED` | ✓ PASS |
| `test_update_participant_side_rejects_unresolved_side` (always-run, UNKNOWN/ADVOCATE guard) | `.venv/Scripts/python.exe -m pytest api/tests/test_admin_arguments_service.py::test_update_participant_side_rejects_unresolved_side -v` | `PASSED` | ✓ PASS |
| Full scoped backend test suite (regression check) | `.venv/Scripts/python.exe -m pytest api/tests/test_admin_arguments_service.py api/tests/test_admin_arguments_routes.py api/tests/test_admin_jobs_service.py -q` | `27 passed, 27 skipped` (DB-guarded tests skip; no live Postgres reachable in this environment — pre-existing, documented limitation) | ✓ PASS |
| Frontend type/markup check | `cd app && npm run check` | `793 FILES 0 ERRORS 18 WARNINGS` (warnings pre-existing/unrelated) | ✓ PASS |
| DB-guarded PIPELINE delete tests (attempted live run) | Exported `DATABASE_URL` and re-ran; confirmed `api.core.database.AsyncSessionLocal` is `None` outside the FastAPI lifespan (engine created only at app startup, not import) | Same limitation affects the pre-existing sibling UNPUBLISHED test — not a new gap | ? SKIP (environment) |

### Human Verification Required

See frontmatter `human_verification` — three items: badge-color visual contrast, the RunStatusCard Archived-badge live check (both carried forward, unaffected by 26-05), and full-page layout/column-alignment confirmation across all three lifecycle states — this third item is expanded from the prior verification to also require visually confirming the new "Unresolved — choose a role" placeholder and disabled-Save treatment on an argument with an unresolved advocate.

### Gaps Summary

Both previously-confirmed gaps are closed, independently re-verified in this session by direct code reading and by executing (not merely citing) the relevant regression tests and the frontend type-checker:

1. **Backend delete gate.** `delete_argument` now rejects any non-DRAFT status (`if argument.status != ArgumentStatusEnum.DRAFT: return False`), closing the PIPELINE hole. Confirmed at `api/services/admin_arguments.py:669-670`; `test_delete_argument_gate_keys_on_draft` executed and passed.
2. **Advocate role dropdown.** The `<select>` now has an explicit "Unresolved — choose a role" option bound via `speakerSideById`, Save is disabled while unresolved, and the backend `update_participant_side` guard unconditionally rejects `UNKNOWN`/`ADVOCATE` sides regardless of what the client sends. Confirmed at `+page.svelte:67-73,458-530` and `admin_arguments.py:542-547`; `test_update_participant_side_rejects_unresolved_side` executed and passed.

No regressions were found in any of the 15 previously-passing truths — none of the files those truths depend on were touched by 26-05 outside the two targeted fixes, and spot-checks confirm they remain intact.

The phase does not reach a clean `passed` status only because three human-verification items (visual badge contrast, live Archived-badge check, and full-page layout/placeholder-rendering confirmation) remain open — these are pre-existing items from the original verification that no automated check can resolve, expanded to also cover the new Unresolved-advocate UI treatment introduced by this gap-closure. There are no outstanding code-level gaps against this phase's must-haves.

---

_Verified: 2026-07-08T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
