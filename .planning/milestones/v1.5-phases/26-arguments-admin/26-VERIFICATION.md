---
phase: 26-arguments-admin
verified: 2026-07-08T19:15:00Z
status: passed
score: 17/17 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 17/17
  gaps_closed:

    - "Delete is blocked (returns False) whenever status is PIPELINE, PUBLISHED, or UNPUBLISHED; allowed only for DRAFT (carried forward from 26-05, re-confirmed)"
    - "Unified Speakers section: advocate rows get a role dropdown, title input, utterance count, and inline Save that persists accurate state, with an explicit Unresolved placeholder and disabled Save (carried forward from 26-05, re-confirmed)"
    - "UAT Test 18: pipeline list page (/admin/pipeline) now shows the neutral-grey Archived badge for runs whose linked argument has already left PIPELINE status, matching the detail page's RunStatusCard (closed by gap-closure plan 26-06)"
  gaps_remaining: []
  regressions: []
human_verification:

  - test: "On /admin/pipeline (list page), open a job whose linked argument has already been created (left PIPELINE status) and confirm the row's status badge reads the grey 'Archived' badge (#cbd5e1), matching the same run's detail-page RunStatusCard exactly"
    expected: "Grey Archived badge on the list row, visually identical in color/label to the detail page's badge for the same run"
    why_human: "This is UAT Test 18's own retest — the original gap was reported by a human as a visual absence, and the closure (26-06) is a rendering/styling change that only a rendered browser view can confirm; wiring (is_archived field → outerjoin → badge override) is independently confirmed via code and passing tests, but visual parity across the two pages still requires a live look, per 26-06-SUMMARY.md's own D2 rationale (human_judgment: true)."
---

# Phase 26: Arguments Admin Verification Report

**Phase Goal:** The arguments admin screens accurately represent the three-state argument lifecycle (Draft / Published / Unpublished), the arguments list excludes pipeline-only rows, and the argument edit page has a status log, a unified Argument Details card, and a speakers section replacing the old advocate roles card
**Verified:** 2026-07-08T19:15:00Z
**Status:** human_needed
**Re-verification:** Yes — fresh full re-verification covering gap-closure plans 26-05 (delete gate + advocate guard) and 26-06 (pipeline list Archived badge), plus scope triage of 3 new 26-REVIEW.md critical findings

This is a fresh, independent re-derivation against the CURRENT codebase. 26-05-SUMMARY.md, 26-06-SUMMARY.md, 26-REVIEW.md, and the prior VERIFICATION.md were consulted for context/pointers only — every finding below was re-derived this session by directly reading source, running `git log`/`git blame` for provenance, executing the actual regression tests, and running the frontend type-checker fresh.

## Goal Achievement

### Gap 1 re-confirmation: delete_argument DRAFT-only gate

**Direct code read** — `api/services/admin_arguments.py:669-670`:

```python
if argument.status != ArgumentStatusEnum.DRAFT:
    return False
```

Single positive condition keyed on `DRAFT`; rejects PIPELINE, PUBLISHED, and UNPUBLISHED alike. Docstring (lines 636-660) explicitly documents PIPELINE is blocked because an active `AdminJob` may still reference it.

**Verdict: ✓ VERIFIED.** Unchanged since 26-05; confirmed present at the current line numbers.

### Gap 2 re-confirmation: unresolved-advocate side guard

**Backend** — `api/services/admin_arguments.py:542-547`:

```python
if side == SideEnum.BENCH:
    raise ValueError("BENCH cannot be set via participant side update")
if side in (SideEnum.UNKNOWN, SideEnum.ADVOCATE):
    raise ValueError(
        "An advocate's side must be resolved to Petitioner, Respondent, or Amicus"
    )
```

**Frontend** — `app/src/routes/admin/arguments/[id]/+page.svelte`: `VALID_SIDES` set (line 67), `speakerSideById` state seeded collapsing anything not in the set to `'UNKNOWN'` (lines 68-73), `<option value="UNKNOWN">Unresolved — choose a role</option>` (line 473) driven by `bind:value` (line 460), Save `disabled` expression includes `speakerSideById[...] === 'UNKNOWN'` (line 514) with matching cursor/opacity styling (524-525).

**Verdict: ✓ VERIFIED.** Unchanged since 26-05; confirmed present at the current line numbers.

### New gap-closure (26-06) re-derivation: pipeline list Archived badge (UAT Test 18)

UAT Test 18 found: RunStatusCard on the pipeline job detail page correctly shows a grey "Archived" badge for an `already_created` run, but the equivalent badge was missing on the pipeline list page (`/admin/pipeline`). Root cause per the gap report: `list_jobs()` did a plain `select(AdminJob)` with no join to `Argument`, and `AdminJobResponse` had no field signaling the linked argument's status.

**Schema** — `api/schemas/admin_jobs.py:65`: `is_archived: bool = False` confirmed present on `AdminJobResponse`.

**Service** — `api/services/admin_jobs.py`:

- `list_jobs()` (lines ~218-255): query is `select(AdminJob, Argument.status).outerjoin(Argument, AdminJob.argument_id == Argument.id)`. Existing `incomplete` filter and `order_by(AdminJob.created_at.desc())` preserved. Per-row: `job.__dict__["is_archived"] = (arg_status is not None and arg_status != ArgumentStatusEnum.PIPELINE)`, with `job.__dict__.setdefault("parse_stats", None)` retained so serialization does not raise.
- `get_job()` (line 143): `job.__dict__.setdefault("is_archived", False)` confirmed present, guarding the single-job detail path (which derives its own Archived signal from the separate `RunReadiness` endpoint, not this field) from an `AttributeError` on serialization.

**Frontend** — `app/src/routes/admin/pipeline/+page.svelte`:

- `badgeStyle(status, isArchived = false)` (line 110): when `isArchived`, returns the fixed grey style using `#cbd5e1` for both border and text — the exact same hex as `RunStatusCard.svelte:47` (`already_created` override).
- `badgeLabel(status, currentStep, isArchived = false)` (line 129): returns `'Archived'` when `isArchived`, short-circuiting the compound step/status label.
- Call sites (lines 638-639): `badgeStyle(job.status, job.is_archived)` / `badgeLabel(job.status, job.current_step, job.is_archived)` — `job.is_archived` flows directly from the load function's `data.jobs`, which is the `AdminJobResponse` list returned by the now-outerjoined `list_jobs()`.

**Key link verified end-to-end:** `list_jobs()` outerjoin → `AdminJobResponse.is_archived` → `+page.svelte` badge override — WIRED, all three hops confirmed by direct code read, no gaps.

**Verdict: ✓ VERIFIED** (wiring and logic). Visual rendering parity across the two pages is deferred to human verification (see frontmatter) — this matches 26-06-SUMMARY.md's own stated rationale (coverage D2, `human_judgment: true`) and is not a gap; it is the same class of visual-confirmation item already open for the arguments-list badges since the original verification.

**Scope note:** This truth traces to requirement **PLIST-05**, which `REQUIREMENTS.md` attributes to **Phase 24**, not Phase 26 (`.planning/REQUIREMENTS.md:122` — `PLIST-05 | Phase 24 | Complete`). The gap was discovered and closed during Phase 26's UAT/gap-closure cycle (plan 26-06), but it is not one of Phase 26's own declared requirement IDs (ALIST-02/03/04, AEDIT-01/02/05/06/07/08/09) and is not part of the phase's 5 stated ROADMAP success criteria. It is verified here for completeness (work performed inside this phase's execution window) but is tracked separately under Phase 24 and does not count toward, or subtract from, Phase 26's own must-have score below. No orphaned requirement: PLIST-05 is legitimately owned and already marked Complete at Phase 24.

### Observable Truths (Phase 26's own 17 must-haves, freshly re-derived)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Publish/unpublish/re-publish set the correct `Argument.status` and each writes exactly one matching `ArgumentStatusLog` row | ✓ VERIFIED | `api/services/admin_arguments.py:467-503` (publish: guard is `status == PUBLISHED` reject, so DRAFT and UNPUBLISHED can both publish — re-publish works), `:578-611` (unpublish: guard is `status != PUBLISHED` reject) — read fresh this session |
| 2 | `approve_job` writes one DRAFT ("Created") `ArgumentStatusLog` row alongside its existing status update | ✓ VERIFIED | `api/services/admin_jobs.py:487-531` — read fresh this session, `db.add(ArgumentStatusLog(..., status=ArgumentStatusEnum.DRAFT))` confirmed at line 531 |
| 3 | The arguments list query returns DRAFT, PUBLISHED, and UNPUBLISHED rows; excludes only PIPELINE | ✓ VERIFIED | `api/services/admin_arguments.py:60-83` — `.where(Argument.status.in_([DRAFT, PUBLISHED, UNPUBLISHED]))` — read fresh this session |
| 4 | Delete is blocked (returns False) whenever status is PUBLISHED, UNPUBLISHED, or PIPELINE; allowed only for DRAFT | ✓ VERIFIED | `api/services/admin_arguments.py:669-670` — re-confirmed this session; structural regression test executed and passed |
| 5 | Slug is frozen (not re-derived) whenever `status != DRAFT` | ✓ VERIFIED | `api/services/admin_arguments.py` update_argument region — confirmed unchanged, not touched by 26-05/26-06 |
| 6 | Arguments list renders a distinct badge for each of Draft (violet), Published (green), and Unpublished (orange) | ✓ VERIFIED | `app/src/routes/admin/arguments/+page.svelte:18-25` — hex values `#a78bfa`/`#4ade80`/`#fb923c` re-confirmed this session |
| 7 | Arguments list has a "Created" column between "Argued" and the row-actions column, showing resolved_at | ✓ VERIFIED | `app/src/routes/admin/arguments/+page.svelte:126,188` — `>Created</th>` header and `{arg.resolved_at ? formatDate(...) : '—'}` cell re-confirmed this session |
| 8 | Each list row's action is status-driven: Draft and Unpublished show Publish; Published shows Unpublish | ✓ VERIFIED | Confirmed unchanged, not touched by 26-05/26-06 |
| 9 | The pipeline run status card (detail page) shows an "Archived" badge (neutral grey) when the run's argument has already been created | ✓ VERIFIED | `app/src/lib/components/RunStatusCard.svelte:44-50` re-confirmed this session — `#cbd5e1`/"Archived" override on `readiness?.state === 'already_created'` |
| 10 | `GET /api/admin/arguments/{id}` returns a `status_log` array, one `{status, created_at}` entry per transition, oldest first | ✓ VERIFIED | `api/services/admin_arguments.py:329-336,362` re-confirmed this session |
| 11 | `GET /api/admin/arguments/{id}` returns a `speakers` array covering ALL participants (bench + advocate) with a per-participant utterance count | ✓ VERIFIED | `api/services/admin_arguments.py:101,339-342,363` re-confirmed this session |
| 12 | `PATCH /participants/{id}` accepts and persists an optional `title` alongside `side` for advocate rows | ✓ VERIFIED | Confirmed unchanged, not touched by 26-05/26-06; title-write logic sits below the new guard added in 26-05 |
| 13 | Edit page Status card shows the current three-state badge, a "Created {date}" line, and a "Published {date}" line when set | ✓ VERIFIED | `app/src/routes/admin/arguments/[id]/+page.svelte:293,299` re-confirmed this session |
| 14 | A "Status history" section lists every `status_log` entry as `{badge} — {date, time}`, oldest first, first DRAFT entry labelled "Created" | ✓ VERIFIED | `app/src/routes/admin/arguments/[id]/+page.svelte:375-402` re-confirmed this session |
| 15 | Publish shows for Draft and Unpublished; Unpublish shows for Published; button lives with the Status card, not floating | ✓ VERIFIED | `app/src/routes/admin/arguments/[id]/+page.svelte:307-369` re-confirmed this session |
| 16 | Unified Speakers section: advocate rows get a role dropdown, title input, utterance count, and inline Save that persists accurate, non-destructive state; bench rows show tenure-derived role or "Missing tenure" + Edit person, with utterance count | ✓ VERIFIED | `+page.svelte:425-530` re-confirmed this session — Unresolved placeholder, `bind:value`, Save disabled while unresolved, backend guard rejects UNKNOWN/ADVOCATE unconditionally |
| 17 | Delete is enabled only for Draft arguments (client); Published and Unpublished show the disabled button with the updated tooltip | ✓ VERIFIED | `app/src/routes/admin/arguments/[id]/+page.server.ts:77` — `can_delete = argument.status === 'draft'`, re-confirmed this session |

**Score:** 17/17 truths verified. No regressions found relative to the previous verification; both previously-closed gaps remain closed under independent re-derivation.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/services/admin_arguments.py` | DRAFT-only delete gate; UNKNOWN/ADVOCATE-rejecting `update_participant_side` guard; list/detail/publish/unpublish logic | ✓ VERIFIED | All re-read directly this session at current line numbers |
| `api/services/admin_jobs.py` | `approve_job` Created-log write; `list_jobs()` outerjoin + `is_archived`; `get_job()` `is_archived` default | ✓ VERIFIED | Confirmed this session |
| `api/schemas/admin_jobs.py` | `AdminJobResponse.is_archived: bool = False` | ✓ VERIFIED | Confirmed at line 65 |
| `app/src/routes/admin/arguments/+page.svelte` | Three-state badges, Created column, status-driven actions | ✓ VERIFIED | Confirmed this session |
| `app/src/routes/admin/arguments/[id]/+page.svelte` | Status card, Status history, unified Speakers section, Unresolved-guard UI | ✓ VERIFIED | Confirmed this session |
| `app/src/routes/admin/arguments/[id]/+page.server.ts` | `can_delete` gate, updated delete-error copy | ✓ VERIFIED | Confirmed this session |
| `app/src/routes/admin/pipeline/+page.svelte` | `badgeStyle`/`badgeLabel` `isArchived` parameter, call sites pass `job.is_archived` | ✓ VERIFIED | Confirmed this session |
| `app/src/lib/components/RunStatusCard.svelte` | `already_created` → grey Archived badge (detail page) | ✓ VERIFIED | Confirmed this session, unchanged |
| `api/tests/test_admin_arguments_service.py`, `test_admin_arguments_routes.py`, `test_admin_jobs_list.py` | Regression coverage for both gap-closures | ✓ VERIFIED | Executed fresh this session, see Behavioral Spot-Checks |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `delete_argument` | `Argument.status` | single positive `== DRAFT` gate | ✓ WIRED | Re-confirmed |
| `update_participant_side` | `SideEnum.UNKNOWN`/`ADVOCATE` rejection | pre-SELECT `ValueError` guard → router 422 | ✓ WIRED | Re-confirmed |
| Advocate `<select>`/Save button | `speakerSideById` client state | `bind:value` + `disabled` expression | ✓ WIRED | Re-confirmed; `npm run check` / `svelte-check` 0 errors |
| `list_jobs()` outerjoin | `AdminJobResponse.is_archived` | `select(AdminJob, Argument.status).outerjoin(...)` → per-row `job.__dict__["is_archived"]` | ✓ WIRED | New this session (26-06); traced end-to-end |
| `AdminJobResponse.is_archived` | `/admin/pipeline` badge | `data.jobs` → `badgeStyle(job.status, job.is_archived)` / `badgeLabel(...)` | ✓ WIRED | New this session (26-06); traced end-to-end |
| (all other Phase 26 links) | — | — | ✓ WIRED | Spot-checked for regressions; unaffected by 26-05/26-06 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| ALIST-02 | 26-01, 26-03 | List shows only Draft/Published/Unpublished; pipeline excluded | ✓ SATISFIED | Confirmed fresh |
| ALIST-03 | 26-03 | Distinct badges for all three statuses | ✓ SATISFIED | Confirmed fresh |
| ALIST-04 | 26-03 | "Created" column added | ✓ SATISFIED | Confirmed fresh |
| AEDIT-01 | 26-02, 26-04 | Status card: badge, created date, published date | ✓ SATISFIED | Confirmed fresh |
| AEDIT-02 (UI surface) | 26-01, 26-02, 26-04 | Full status log with timestamps for every transition | ✓ SATISFIED | Confirmed fresh. Note: `REQUIREMENTS.md` attributes the base AEDIT-02 (table + migration) to Phase 22; Phase 26 is correctly scoped to the UI-surface rendering of that data, which is what was verified here |
| AEDIT-05 | 26-02, 26-04 | Speakers section replaces Advocate Roles card + tenure gap warnings | ✓ SATISFIED | Confirmed fresh |
| AEDIT-06 | 26-02, 26-04, 26-05 | Advocate role dropdown + title field + inline save | ✓ SATISFIED | Dropdown/title/inline-save present and safe: explicit Unresolved state, disabled Save, authoritative backend rejection |
| AEDIT-07 | 26-02, 26-04 | Bench speakers: tenure-derived role; Missing tenure + edit link | ✓ SATISFIED | Confirmed fresh |
| AEDIT-08 | 26-01, 26-04 | Publish/Unpublish/re-Publish transitions | ✓ SATISFIED | Confirmed fresh — publish guard rejects only already-PUBLISHED (allows DRAFT and UNPUBLISHED to publish); unpublish guard rejects non-PUBLISHED |
| AEDIT-09 | 26-01, 26-04, 26-05 | Danger Zone delete gate | ✓ SATISFIED | Backend gate blocks PIPELINE, PUBLISHED, and UNPUBLISHED; only DRAFT deletable |

**Not a Phase 26 requirement (informational only):** PLIST-05 (pipeline list status badges) is owned by Phase 24 per `REQUIREMENTS.md` and is already marked Complete there. Phase 26's gap-closure plan 26-06 extended that existing badge system to add the Archived override on the list page — verified above as correctly wired — but it is not counted against Phase 26's own requirement list and is not an orphan (it has a clear home at Phase 24).

No orphaned requirements against Phase 26's own declared set. All 10 IDs (ALIST-02/03/04, AEDIT-01/02/05/06/07/08/09) are declared across the plans and match `REQUIREMENTS.md`'s Phase 26 assignments. AEDIT-03/AEDIT-04 remain correctly attributed to Phase 23 and out of this phase's scope.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/src/routes/admin/arguments/[id]/+page.svelte` | 443 | `colspan="3"` on a cell holding content for 4 logical columns (WR-01, carried forward, unresolved) | ⚠️ Warning | Visual column misalignment between advocate and bench rows when both appear in the same table; non-blocking, cosmetic |
| `app/src/routes/admin/arguments/[id]/+page.svelte` | 67-73 | `speakerSideById` seeded once, not reset via `$effect` on `data.argument.id` reuse (WR-07) | ⚠️ Warning | Theoretical stale-seed edge case on client-side navigation between two argument edit pages within the same component instance. Backend guard (T-26-14) is unconditional, so the worst outcome is a confusing failed-Save 422, not silent misclassification — does not reopen the data-safety gap |
| `api/services/admin_jobs.py` (`approve_job`), `api/services/admin_arguments.py` (`publish_argument`, `unpublish_argument`) | — | Check-then-act status transitions without a status predicate in the `UPDATE ... WHERE` clause (WR-08, introduced in 26-01) | ⚠️ Warning | Two concurrent requests against the same argument could each pass the Python-level status check before either commits, theoretically double-writing an `ArgumentStatusLog` row. This is a real defect introduced by Phase 26's own new code, but it requires concurrent requests against a single-operator admin tool to trigger — it does not affect the phase's stated success criteria (each transition, run singly, is fully functional and writes exactly one log row, as confirmed by both the always-run structural tests and this session's fresh read). Recommend tracking as a follow-up hardening item rather than a phase-26 blocker |

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in any file modified by 26-05 or 26-06.

**Scope triage of 26-REVIEW.md's 3 Critical findings (fresh git-blame provenance check, this session):**

| Finding | Introduced in | Confirmed via | Phase 26 scope? |
|---|---|---|---|
| CR-01: `rerun_job` never spawns ingest for locally-uploaded jobs | Pre-existing (rerun/local-upload machinery predates and is untouched by Phase 26; `admin.py`/`admin_jobs.py` rerun logic is a Phase 24-era pipeline-run concern) | Code path not touched by any 26-01..26-06 commit (`git log` on the affected functions shows no Phase 26 commits) | **Out of scope.** Real defect, but pre-existing and unrelated to the lifecycle-badges/status-log/speakers goal. Track separately. |
| CR-02: Blank `case_name`/`docket_number` accepted, corrupting slug/dedup key | `ArgumentUpdate` schema: `f95f3ab8 feat(11-02)` (Phase 11). `?/save` action's `.trim()`-without-`required` logic: `b938ad6d feat(11-03)` (Phase 11). `MetadataUpdate`/`update_argument_metadata`'s identical gap: `a9cbf218 feat(19-03)` (Phase 19) | `git log -S` on `class ArgumentUpdate`, `async def update_argument(`, and the `?/save` action; confirmed 26-04's only touch to `+page.server.ts` was `can_delete`/title-related, not the case_name/docket_number trim block (diff inspected directly) | **Out of scope.** Both the schema gap and the untrimmed-`required` UI gap predate Phase 26 by multiple phases and were not modified by any Phase 26 plan. None of Phase 26's success criteria or requirement IDs (ALIST-02/03/04, AEDIT-01/02/05/06/07/08/09) call for input validation on blank metadata values. Real defect; recommend a backlog item, not a Phase 26 gap. |
| CR-03: `update_argument_metadata` has no guard against the `(source_docket, question_number)` unique constraint | `a9cbf218 feat(19-03)` (Phase 19), when `update_argument_metadata` was first introduced | `git log -S "async def update_argument_metadata"` shows a single introducing commit, Phase 19; no Phase 26 commit touches this function | **Out of scope.** Predates Phase 26 by 7 phases; Phase 26 never modifies `update_argument_metadata`. Not required by any Phase 26 success criterion. Real defect; recommend a backlog item, not a Phase 26 gap. |

This mirrors the prior verification's treatment of CR-01 and extends the same provenance-based reasoning to the two new Criticals — all three predate Phase 26's own code changes and are not required by its must-haves, so none are treated as Phase 26 gaps. They should be tracked as separate backlog items given their severity (both CR-02 and CR-03 are real, unhandled failure modes worth fixing soon).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full targeted backend regression (delete gate, advocate guard, is_archived) | `.venv/Scripts/python.exe -m pytest api/tests/test_admin_jobs_list.py api/tests/test_admin_arguments_service.py api/tests/test_admin_arguments_routes.py -q` | `26 passed, 33 skipped` | ✓ PASS |
| Frontend type/markup check (post-26-06) | `cd app && npx svelte-check --tsconfig ./tsconfig.json` | `793 FILES 0 ERRORS 18 WARNINGS` (warnings pre-existing/unrelated, confirmed identical set to prior run) | ✓ PASS |
| DB-guarded `is_archived` tests (`test_list_jobs_is_archived_*`) and DB-guarded delete/participant tests | Included in the run above | Skipped — no live Postgres reachable in this environment; documented pre-existing limitation (`.planning/phases/26-arguments-admin/deferred-items.md`), confirmed via sibling-test comparison to not be a new regression | ? SKIP (environment, pre-existing) |

Full unfiltered workspace test suite was not re-run in this session — `deferred-items.md` already documents (with disposable-worktree and sibling-test comparisons across every plan in this phase, including 26-06) that the project's known pytest collection-order corruption produces false failures/errors when `api/tests`, `tests`, and `pipeline/tests` are collected together, and that this is pre-existing and unrelated to Phase 26's logic. The scoped run above is the correct evidence signal per the project's own established pattern and this session's own execution.

### Human Verification Required

See frontmatter `human_verification` — one item: the UAT Test 18 retest, confirming the pipeline list page's Archived badge visually matches the detail page's for the same run now that 26-06's wiring is in place.

**Correction to this section (orchestrator cross-check against 26-UAT.md, post-verification):** the first draft of this report carried forward three additional human-verification items from the original (pre-UAT) verification pass — arguments-list badge-color contrast, the RunStatusCard Archived-badge check on the pipeline detail page, and full-page layout/column-alignment/Unresolved-state confirmation across the three lifecycle states. All three were already exercised and passed during the completed human UAT run recorded in `26-UAT.md`: Test 15 ("Arguments list — three-state badges", `result: pass`), Test 18's detail-page portion ("Pipeline job detail — Archived badge", `result: issue` — but the reported issue was specifically that the *list* page lacked the badge; the detail-page badge itself was explicitly confirmed working: "pass for the details page"), and Test 24 ("Argument edit page — full render across all three lifecycle states", `result: pass`). The one exception is the Unresolved-advocate visual check (would-be Test 26 coverage), which UAT explicitly marked `result: skipped` with reason "Resolve/Speakers table is scheduled for rework per SEED-001-rework-resolve-table-requirements.md — not worth testing ahead of that rework" — a deliberate, already-made deferral decision, not an open Phase 26 gap. Re-asking for all four would duplicate work already completed and re-litigate an explicit deferral. Only the Test 18 list-page retest is genuinely new and unconfirmed.

### Gaps Summary

No outstanding gaps against Phase 26's own must-haves. Both previously-confirmed gaps (delete gate, advocate-side guard) remain closed under independent re-derivation this session, and the newly-closed UAT gap (Test 18, pipeline list Archived badge) is fully wired end-to-end per direct code inspection and passing tests — its remaining open item is a visual-parity confirmation, the same category of human-only check already open for the arguments-list badges since the original verification.

The three new Critical findings in the refreshed 26-REVIEW.md (CR-01 rerun/local-upload, CR-02 blank metadata validation, CR-03 unique-constraint collision) were each traced via `git log -S`/`git blame` to commits from Phase 11, Phase 19, or earlier — all predate Phase 26's own code changes, none are touched by any Phase 26 plan, and none are required by Phase 26's stated success criteria or requirement IDs. They are real, worth-fixing defects but are correctly out of scope for this phase's gate; recommend tracking them as backlog items for a future phase rather than reopening Phase 26.

WR-08 (non-atomic status transitions, introduced in 26-01) is a genuine Phase-26-introduced defect, but it is a concurrency edge case that does not affect the phase's functional success criteria under normal single-operator usage (each transition, exercised singly, is confirmed correct by the always-run structural tests and by fresh code reading). It is recorded as a warning-level anti-pattern for follow-up, not a blocker.

The phase does not reach a clean `passed` status only because one human-verification item remains open — the visual parity retest of UAT Test 18 on the pipeline list page (see correction note above: the three other visual items originally carried forward from the pre-UAT verification pass are already discharged by the completed `26-UAT.md` run, and the Unresolved-advocate visual check is a deliberate, separately-tracked deferral, not an open item). This is not a code-level gap; it is a visual/live-render confirmation that no automated check in this environment can resolve.

---

## Acknowledged Gaps

Recorded 2026-07-08 when advancing Phase 26 past the automated `phase uat-passed` predicate, which flags raw per-test `result:` fields with no concept of a later retest or a documented skip reason. Both items below are resolved/accepted at the human-judgment level; the predicate's blocker list is a known false positive against this phase's actual state.

- **26-UAT.md Test 18** (`result: issue`) — original gap: pipeline list page missing the Archived badge. Root-caused and fixed by gap-closure plan 26-06; fix independently confirmed by 26-REVIEW.md and this VERIFICATION.md's fresh re-derivation (see "New gap-closure (26-06) re-derivation" above). Visual parity retested as **Test 27, `result: pass`**. Test 18's own result line is left unchanged as the historical record of the original UAT finding; Test 27 is the authoritative outcome.
- **26-UAT.md Test 26** (`result: skipped`) — deliberate deferral, not an open defect. Reason recorded on the test: "Resolve/Speakers table is scheduled for rework per `.planning/seeds/SEED-001-rework-resolve-table-requirements.md` — not worth testing ahead of that rework."

Accepted by: jason.butler@offenpetro.com (via `/gsd-verify-work 26`, force-advance option).

---

_Verified: 2026-07-08T19:15:00Z_
_Verifier: Claude (gsd-verifier)_
