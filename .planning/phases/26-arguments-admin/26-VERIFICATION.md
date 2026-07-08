---
phase: 26-arguments-admin
verified: 2026-07-08T12:00:00Z
status: gaps_found
score: 15/17 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "Delete is blocked (returns False) whenever status is PUBLISHED or UNPUBLISHED; allowed only for DRAFT"
    status: failed
    reason: "delete_argument's gate only checks `argument.status in (PUBLISHED, UNPUBLISHED)`. It does NOT block PIPELINE-status arguments, so a direct DELETE call against an argument that is still mid-pipeline (with a job possibly PAUSED at RESOLVE, referencing it via AdminJob.argument_id) succeeds — the argument, its participants, utterances, and pipeline runs are deleted and AdminJob.argument_id is NULLed, permanently stranding the job. This is a regression against this phase's own stated must-have text ('allowed only for DRAFT') and against the 26-04 plan's explicit objective ('a delete gate that keys on Draft only'). Confirmed independently by reading api/services/admin_arguments.py:650-652; not merely a code-review claim taken on faith. No test exists for the PIPELINE case (test_delete_argument_returns_false_for_unpublished exists; no equivalent test_delete_argument_returns_false_for_pipeline)."
    artifacts:
      - path: "api/services/admin_arguments.py"
        issue: "delete_argument gate (line 651): `if argument.status in (ArgumentStatusEnum.PUBLISHED, ArgumentStatusEnum.UNPUBLISHED): return False` — PIPELINE is not in the blocked tuple, so it falls through to the delete cascade returning True."
    missing:
      - "Change the gate to `if argument.status != ArgumentStatusEnum.DRAFT: return False` (or explicitly add PIPELINE to the blocked tuple) so only DRAFT arguments can be deleted, matching the plan's own must-have text and objective."
      - "Add a regression test asserting delete_argument returns False for a PIPELINE-status argument, and that DELETE /api/admin/arguments/{id} returns 409 for a PIPELINE-status argument."
  - truth: "Unified Speakers section: advocate rows get a role dropdown, title input, utterance count, and inline Save that persists accurate state"
    status: failed
    reason: "The advocate role <select> in app/src/routes/admin/arguments/[id]/+page.svelte only renders PETITIONER/RESPONDENT/AMICUS <option>s (confirmed at lines 457-459). SideEnum includes UNKNOWN (the default side value written at parse time for every unresolved advocate participant, per api/models/models.py:39/313) and legacy ADVOCATE. When speaker.side is UNKNOWN, none of the three `selected={...}` expressions evaluates true, so per standard HTML <select> behavior the browser silently defaults the control to the first listed option (PETITIONER). If an operator opens the Speakers card to fill in only a Title for an unresolved advocate and clicks Save, the form submits side=PETITIONER, and update_participant_side (api/services/admin_arguments.py:535, guard only rejects side==BENCH — UNKNOWN passes through) writes it, silently reclassifying an unresolved advocate as 'Petitioner's Counsel' with no confirmation or warning. This is a real, confirmed data-accuracy defect in the 'inline Save' behavior this section is required to provide, and it runs against CLAUDE.md's hard constraint that every speaker gets identical, non-inferred treatment. Note: this was a deliberate instruction in 26-04-PLAN.md Task 3 ('drop the UNKNOWN/\"Counsel\" option per AEDIT-06') — the executor followed the plan faithfully; the defect originates in the plan's own design decision, not an execution deviation. It also technically satisfies the plan's literal must-have wording ('a role dropdown (PETITIONER/RESPONDENT/AMICUS)'), but fails the functional intent of a safe, non-destructive inline-save experience."
    artifacts:
      - path: "app/src/routes/admin/arguments/[id]/+page.svelte"
        issue: "Lines 443-460: <select name=\"side\"> has no option/handling for SideEnum.UNKNOWN (or legacy ADVOCATE); browser default-selects PETITIONER when no option matches, and the form has no guard preventing that default from being submitted."
    missing:
      - "Add an explicit disabled placeholder option (e.g. `<option value=\"UNKNOWN\" selected={speaker.side === 'UNKNOWN'} disabled>Unresolved — choose a role</option>`) so the control visually reflects true unresolved state."
      - "Either disable the Save button while side remains UNKNOWN, or have the backend reject/ignore an UNKNOWN submission so an accidental Save cannot silently reassign an unresolved advocate's side."
deferred: []
human_verification:
  - test: "Visually confirm the three arguments-list badge colors (Draft violet #a78bfa, Published green #4ade80, Unpublished orange #fb923c) render with sufficient contrast and are visually distinct side by side"
    expected: "Three clearly distinguishable badge colors, each with a text label"
    why_human: "Color rendering and contrast are visual concerns; svelte-check and grep confirm the hex values are present in code but not how they look together in the browser (per 26-03-SUMMARY.md D1/D2/D3 human_judgment notes)"
  - test: "Open a pipeline job detail page for a run whose argument has already been created and confirm the RunStatusCard shows the grey 'Archived' badge instead of the job-status badge"
    expected: "Archived badge (#cbd5e1) overrides the jobStatus-driven badge for an already_created run"
    why_human: "Requires a live backend + a run in the already_created readiness state to observe (per 26-03-SUMMARY.md D4)"
  - test: "Load the argument edit page for a live argument in each of the three lifecycle states (Draft, Published, Unpublished) and visually confirm: Status card + Status history layout, Publish/Unpublish button placement inside the Status card, and Speakers table column alignment for mixed bench/advocate rows"
    expected: "Layout renders as specified in the UI-SPEC; no visual misalignment"
    why_human: "svelte-check and grep verify markup/logic correctness but not actual browser layout/rendering (per 26-04-SUMMARY.md D6); also surfaces WR-01 from the code review — the advocate row's <td colspan=\"3\"> spans only 3 of the 4 remaining logical columns (Title/Utterances/Action all collapsed together), which will visibly misalign column borders against 5-column bench rows when both appear in the same table."
---

# Phase 26: Arguments Admin Verification Report

**Phase Goal:** The arguments admin screens accurately represent the three-state argument lifecycle (Draft / Published / Unpublished), the arguments list excludes pipeline-only rows, and the argument edit page has a status log, a unified Argument Details card, and a speakers section replacing the old advocate roles card
**Verified:** 2026-07-08T12:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Publish/unpublish/re-publish set the correct `Argument.status` and each writes exactly one matching `ArgumentStatusLog` row | ✓ VERIFIED | `api/services/admin_arguments.py:467-600` — `publish_argument` guard checks `status == PUBLISHED` (allows re-publish from UNPUBLISHED); `unpublish_argument` guard checks `status != PUBLISHED`; both call `db.add(ArgumentStatusLog(...))` before commit. Read directly, not from SUMMARY claim. |
| 2 | `approve_job` writes one DRAFT ("Created") `ArgumentStatusLog` row alongside its existing status update | ✓ VERIFIED | `api/services/admin_jobs.py:502-511` — `db.add(ArgumentStatusLog(argument_id=job.argument_id, status=DRAFT))` present in the same transaction as the status=DRAFT update, before commit. |
| 3 | The arguments list query returns DRAFT, PUBLISHED, and UNPUBLISHED rows; excludes only PIPELINE | ✓ VERIFIED | `api/services/admin_arguments.py:75-81` — `.where(Argument.status.in_([DRAFT, PUBLISHED, UNPUBLISHED]))`. |
| 4 | Delete is blocked (returns False) whenever status is PUBLISHED or UNPUBLISHED; **allowed only for DRAFT** | ✗ FAILED | `api/services/admin_arguments.py:650-652` — gate is `if argument.status in (PUBLISHED, UNPUBLISHED): return False`. PIPELINE is not blocked — a PIPELINE-status argument can still be deleted, contradicting "allowed only for DRAFT." See Gaps below. |
| 5 | Slug is frozen (not re-derived) whenever `status != DRAFT` | ✓ VERIFIED | `api/services/admin_arguments.py:447` — `if argument.status == ArgumentStatusEnum.DRAFT:` gates slug re-derivation; else-branch leaves slug untouched. |
| 6 | Arguments list renders a distinct badge for each of Draft (violet), Published (green), and Unpublished (orange) | ✓ VERIFIED | `app/src/routes/admin/arguments/+page.svelte:18-35` — `badgeStyle`/`badgeLabel` have three branches with the exact hex values (`#a78bfa`, `#4ade80`, `#fb923c`). |
| 7 | Arguments list has a "Created" column between "Argued" and the row-actions column | ✓ VERIFIED | `app/src/routes/admin/arguments/+page.svelte:126,188` — header "Created" cell renders `formatDate(arg.resolved_at)` guarded by `arg.resolved_at`. |
| 8 | Each list row's action is status-driven: Draft and Unpublished show Publish; Published shows Unpublish | ✓ VERIFIED | `app/src/routes/admin/arguments/+page.svelte:197,216` — `{#if arg.status === 'draft' || arg.status === 'unpublished'}` (Publish) / `{:else if arg.status === 'published'}` (Unpublish). |
| 9 | The pipeline run status card shows an "Archived" badge (neutral grey) when the run's argument has already been created | ✓ VERIFIED | `app/src/lib/components/RunStatusCard.svelte:44-50` — `badgeColor`/`badgeLabel` `$derived` check `readiness?.state === 'already_created'` first, resolving to `#cbd5e1` / `'Archived'`. |
| 10 | `GET /api/admin/arguments/{id}` returns a `status_log` array, one `{status, created_at}` entry per transition, oldest first | ✓ VERIFIED | `api/services/admin_arguments.py:329-336,362` — `select(ArgumentStatusLog)...order_by(created_at.asc(), id.asc())`, returned as `"status_log"`. `api/schemas/admin_arguments.py:53,199` defines `StatusLogEntry` and `ArgumentDetail.status_log`. |
| 11 | `GET /api/admin/arguments/{id}` returns a `speakers` array covering ALL participants (bench + advocate) with a per-participant utterance count | ✓ VERIFIED | `api/services/admin_arguments.py:101-218` — `list_argument_speakers` builds one row per `ArgumentParticipant`, bench and advocate branches, utterance counts via one grouped query (`group_by(Utterance.person_id)`, no N+1); wired into `get_argument_detail` at line 342/363. |
| 12 | `PATCH /participants/{id}` accepts and persists an optional `title` alongside `side` for advocate rows | ✓ VERIFIED | `api/services/admin_arguments.py:506-551` — `update_participant_side(..., title=...)` writes `title` only when non-None; `api/routers/admin.py:1135-1136` passes `body.title` through. |
| 13 | Edit page Status card shows the current three-state badge, a "Created {date}" line, and a "Published {date}" line when set | ✓ VERIFIED | `app/src/routes/admin/arguments/[id]/+page.svelte:266-286` — badge span, `Created {formatDate(resolved_at)}` (guarded), `Published {formatDate(published_at)}` (guarded). |
| 14 | A "Status history" section lists every `status_log` entry as `{badge} — {date, time}`, oldest first, first DRAFT entry labelled "Created" | ✓ VERIFIED | `app/src/routes/admin/arguments/[id]/+page.svelte:360-389` — iterates `data.argument.status_log`, special-cases `index === 0 && entry.status === 'draft'` → "Created"; degraded fallback text present. |
| 15 | Publish shows for Draft and Unpublished; Unpublish shows for Published; button lives with the Status card, not floating | ✓ VERIFIED | `app/src/routes/admin/arguments/[id]/+page.svelte:292-357` — Publish/Unpublish forms rendered directly inside the same card div as the Status badge/dates (lines 258-358 form one continuous card), status-driven branches confirmed. |
| 16 | Unified Speakers section: advocate rows get a role dropdown, title input with "Extracted:" hint, utterance count, and an inline Save that **persists accurate, non-destructive state**; bench rows show tenure-derived role or "Missing tenure" + Edit person, with utterance count | ✗ FAILED | Structural rendering is correct (bench branch at lines 516-530 correctly shows `missing_tenure`/`bench_role`/Edit-person-link/utterance count). But the advocate `<select>` (lines 443-460) omits `SideEnum.UNKNOWN`, so saving an unresolved advocate's row silently reassigns `side=PETITIONER`. See Gaps below. |
| 17 | Delete is enabled only for Draft arguments (client); Published and Unpublished show the disabled button with the updated tooltip | ✓ VERIFIED (client-side only) | `app/src/routes/admin/arguments/[id]/+page.server.ts:77` — `can_delete = argument.status === 'draft'`; tooltip copy confirmed at `+page.svelte:632`. Client-side gate is correct; the corresponding **backend** gate gap is captured in Truth #4 — client disabled-state alone is defense-in-depth, not the authoritative guard (project's own stated convention). |

**Score:** 15/17 truths verified (2 failed — both are backend/functional-safety defects, not missing UI surface)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/services/admin_arguments.py` | Status-keyed publish/unpublish/delete/slug guards; `list_argument_speakers` helper | ✓ VERIFIED (with the delete-gate defect noted above) | All guards present and correctly keyed on `Argument.status` except the delete gate's PIPELINE omission |
| `api/services/admin_jobs.py` | `approve_job` writes DRAFT log row | ✓ VERIFIED | Confirmed inline |
| `api/routers/admin.py` | 409 copy update; `title` passthrough on participant PATCH | ✓ VERIFIED | Both confirmed |
| `api/schemas/admin_arguments.py` | `StatusLogEntry`, `SpeakerRow`, `ArgumentDetail.status_log`/`speakers`, `ParticipantSideUpdate.title` | ✓ VERIFIED | All fields present |
| `app/src/routes/admin/arguments/+page.svelte` | Three-state badge, Created column, status-driven actions | ✓ VERIFIED | Confirmed |
| `app/src/lib/components/RunStatusCard.svelte` | Archived badge override | ✓ VERIFIED | Confirmed |
| `app/src/routes/admin/arguments/[id]/+page.server.ts` | `SpeakerRow`/`status_log` types, `can_delete === 'draft'`, title-aware save, delete copy | ✓ VERIFIED | Confirmed |
| `app/src/routes/admin/arguments/[id]/+page.svelte` | Status card + history, Speakers section, Danger Zone copy | ⚠️ VERIFIED WITH DEFECT | Structurally present and wired; advocate role select has the UNKNOWN-handling gap (Truth #16) and a `colspan` structural warning (WR-01, non-blocking) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `publish_argument`/`unpublish_argument` | `Argument.status` + `ArgumentStatusLog` | inline `db.add()` in same transaction | ✓ WIRED | Confirmed at both call sites |
| `approve_job` | `ArgumentStatusLog` DRAFT row | inline `db.add()` before commit | ✓ WIRED | Confirmed |
| `delete_argument` / `update_argument` slug-freeze | `Argument.status` | status-keyed conditionals | ⚠️ PARTIAL | Slug-freeze correctly keys on status; delete gate keys on status but the condition is incomplete (misses PIPELINE) |
| `get_argument_detail` | `list_argument_speakers` + `ArgumentStatusLog` query | function call + query, merged into return dict | ✓ WIRED | Confirmed at `admin_arguments.py:329-363` |
| `list_argument_speakers` | Utterance counts | single grouped query (`group_by(Utterance.person_id)`) | ✓ WIRED | No N+1 confirmed |
| Edit page `+page.svelte` | `status_log`/`speakers` from `load()` | direct template binding (`data.argument.status_log`, `data.argument.speakers`) | ✓ WIRED | Confirmed |
| Advocate Speakers row form | `?/updateParticipantSide` action → PATCH `/participants/{id}` | `use:enhance` form → fetch → backend | ⚠️ WIRED BUT UNSAFE | The wiring itself works; the data it submits can be wrong for UNKNOWN-side rows (Truth #16) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| ALIST-02 | 26-01, 26-03 | List shows only Draft/Published/Unpublished; pipeline excluded | ✓ SATISFIED | `list_arguments` filter + status-driven row actions confirmed |
| ALIST-03 | 26-03 | Distinct badges for all three statuses | ✓ SATISFIED | Three hex-coded badges confirmed |
| ALIST-04 | 26-03 | "Created" column added | ✓ SATISFIED | Column confirmed |
| AEDIT-01 | 26-02, 26-04 | Status card: badge, created date, published date | ✓ SATISFIED | Confirmed in edit page Status card |
| AEDIT-02 | 26-01, 26-02, 26-04 | Full status log with timestamps for every transition | ✓ SATISFIED | `status_log` + Status history section confirmed end-to-end |
| AEDIT-05 | 26-02, 26-04 | Speakers section replaces Advocate Roles card + tenure gap warnings | ✓ SATISFIED | Old card/banner text confirmed absent (`grep` for "Advocate Roles" / "falls outside all recorded tenures" returns nothing); unified Speakers table present |
| AEDIT-06 | 26-02, 26-04 | Advocate role dropdown + title field + inline save | ⚠️ SATISFIED WITH DEFECT | Dropdown/title/inline-save all present and wired, but see Truth #16 — the dropdown's incomplete option set makes the "inline save" unsafe for unresolved advocates |
| AEDIT-07 | 26-02, 26-04 | Bench speakers: tenure-derived role; Missing tenure + edit link | ✓ SATISFIED | Confirmed |
| AEDIT-08 | 26-01, 26-04 | Publish/Unpublish/re-Publish transitions | ✓ SATISFIED | Confirmed at both backend and UI layers |
| AEDIT-09 | 26-01, 26-04 | Danger Zone delete gate | ✗ NOT FULLY SATISFIED | Client-side gate correct; backend gate does not block PIPELINE-status deletion (Truth #4) |

No orphaned requirements found — all IDs declared across the four plans (ALIST-02/03/04, AEDIT-01/02/05/06/07/08/09) match the task's requirement list and REQUIREMENTS.md's Phase 26 assignments. AEDIT-03/AEDIT-04 ("Argument Details card") are correctly attributed to Phase 23 in REQUIREMENTS.md and are not claimed by any Phase 26 plan; the pre-existing "Argument Details" card (Card 1) in `arguments/[id]/+page.svelte` was not touched by Phase 26 and remains present, satisfying that clause of the stated phase goal by inheritance rather than by this phase's own work.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `api/services/admin_arguments.py` | 651 | Incomplete status-gate condition | 🛑 Blocker | Allows deleting PIPELINE-status arguments, contradicting the phase's own "Draft-only delete gate" objective |
| `app/src/routes/admin/arguments/[id]/+page.svelte` | 443-460 | Missing enum-value handling in `<select>` causing silent default-selection | 🛑 Blocker | Data-accuracy defect — can silently misclassify an unresolved advocate on save |
| `app/src/routes/admin/arguments/[id]/+page.svelte` | 428 | `colspan="3"` on a cell holding content for 4 logical columns | ⚠️ Warning | Visual column misalignment between advocate and bench rows (non-blocking; cosmetic) |

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in any file modified by this phase.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Scoped backend test suite for phase 26 files | `.venv/Scripts/python.exe -m pytest api/tests/test_admin_arguments_service.py api/tests/test_admin_arguments_routes.py api/tests/test_admin_jobs_service.py -q` | `25 passed, 25 skipped` (DB-guarded tests skip; `DATABASE_URL` not configured in this environment — matches project's documented, pre-existing test pattern, confirmed via `deferred-items.md`) | ✓ PASS |
| Frontend type/markup check | `cd app && npm run check` | `793 FILES 0 ERRORS 17 WARNINGS` (warnings are pre-existing, unrelated to phase 26 files) | ✓ PASS |
| Delete gate correctly rejects PIPELINE-status argument | No existing test | Not covered — confirmed by direct code read, not by a passing/failing test | ✗ FAIL (no test exists to catch the confirmed defect) |

### Human Verification Required

See frontmatter `human_verification` — three items covering badge-color visual contrast, the RunStatusCard Archived-badge live check, and full-page layout/column-alignment confirmation across all three lifecycle states (this also surfaces the WR-01 `colspan` warning visually).

### Gaps Summary

Two confirmed, independently-verified defects block a clean pass, both matching this phase's own explicitly declared must-haves rather than being out-of-scope nice-to-haves:

1. **Backend delete gate does not enforce "Draft-only."** `delete_argument` blocks PUBLISHED and UNPUBLISHED but not PIPELINE, so a still-in-progress argument (one an `AdminJob` may still be actively referencing, possibly paused at RESOLVE awaiting an operator) can be deleted via a direct API call, permanently stranding that job. This directly contradicts 26-01-PLAN.md's must-have text ("allowed only for DRAFT") and 26-04-PLAN.md's explicit objective ("a delete gate that keys on Draft only"). The client-side `can_delete` gate is correct, but per this project's own stated convention elsewhere in the same files, the backend must independently enforce the invariant — it does not.

2. **Advocate role dropdown omits `SideEnum.UNKNOWN`, causing silent data corruption on save.** Every freshly-parsed, not-yet-resolved advocate participant defaults to `side=UNKNOWN`. Because the `<select>` only offers PETITIONER/RESPONDENT/AMICUS, the browser silently defaults to PETITIONER when none of the three matches, and clicking Save (e.g., to save only a Title) writes that default — reclassifying an unresolved advocate as "Petitioner's Counsel" with no warning. This was a deliberate instruction in the plan itself (to drop the UNKNOWN option), so it is a planning-level defect the executor implemented faithfully — but it is a real, confirmed functional bug that undermines the safety of the "inline Save" feature and runs against the project's CLAUDE.md constraint that every speaker receive identical, non-inferred treatment.

Both were independently confirmed by direct code inspection (not accepted from the code-review report at face value): `api/services/admin_arguments.py:650-652` for gap 1, and `app/src/routes/admin/arguments/[id]/+page.svelte:443-460` plus `api/models/models.py:36-42/313` (SideEnum default) for gap 2.

All other must-haves across the four plans — the publish/unpublish/re-publish lifecycle and its audit log, the three-state list badges and Created column, the status-driven row/edit-page actions, the Archived run-status badge, the status_log/speakers API contract, and the Status card/history/Speakers-section UI — were independently verified present, substantive, and correctly wired.

---

_Verified: 2026-07-08T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
