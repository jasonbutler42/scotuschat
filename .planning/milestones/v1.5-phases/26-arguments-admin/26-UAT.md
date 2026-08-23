---
status: complete
phase: 26-arguments-admin
source: [26-01-SUMMARY.md, 26-02-SUMMARY.md, 26-03-SUMMARY.md, 26-04-SUMMARY.md, 26-05-SUMMARY.md, 26-06-SUMMARY.md]
started: 2026-07-08T17:21:23Z
updated: 2026-07-08T19:35:00Z
---

## Current Test

[testing complete]

## Tests

### 1. [auto] publish/re-publish writes correct status + one log row
expected: publish_argument sets status=PUBLISHED, stamps published_at, and writes one PUBLISHED ArgumentStatusLog row; re-publish from UNPUBLISHED succeeds
result: pass
source: automated
coverage_id: D1

### 2. [auto] unpublish preserves published_at + writes log row
expected: unpublish_argument sets status=UNPUBLISHED, leaves published_at intact, writes one UNPUBLISHED log row
result: pass
source: automated
coverage_id: D2

### 3. [auto] approve_job writes Created log row
expected: approve_job writes a DRAFT ("Created") ArgumentStatusLog row alongside its existing status=DRAFT update
result: pass
source: automated
coverage_id: D3

### 4. [auto] list_arguments includes all three post-pipeline states
expected: list_arguments includes DRAFT, PUBLISHED, and UNPUBLISHED rows; excludes only PIPELINE
result: pass
source: automated
coverage_id: D4

### 5. [auto] delete_argument gate + 409 copy
expected: delete_argument returns False for PUBLISHED/UNPUBLISHED, True for DRAFT; DELETE route returns 409 with updated copy for UNPUBLISHED
result: pass
source: automated
coverage_id: D5

### 6. [auto] slug freeze for PUBLISHED/UNPUBLISHED
expected: update_argument freezes the slug (re-derives only while DRAFT) for both PUBLISHED and UNPUBLISHED arguments
result: pass
source: automated
coverage_id: D6

### 7. Confirm Plan 26-01 auto-covered deliverables
expected: |
  Plan 26-01 (argument lifecycle rewrite) deliverables were all auto-verified by passing tests:
  - publish_argument sets status=PUBLISHED, stamps published_at, writes one PUBLISHED log row; re-publish from UNPUBLISHED succeeds
  - unpublish_argument sets status=UNPUBLISHED, leaves published_at intact, writes one UNPUBLISHED log row
  - approve_job writes a DRAFT ("Created") log row
  - list_arguments includes DRAFT, PUBLISHED, and UNPUBLISHED rows (excludes only PIPELINE)
  - delete_argument returns False for PUBLISHED/UNPUBLISHED, True for DRAFT; DELETE route returns 409 for UNPUBLISHED
  - update_argument freezes the slug for PUBLISHED/UNPUBLISHED arguments
  No manual test needed — confirm you have no reason to doubt this automated coverage.
result: pass

### 8. [auto] list_argument_speakers returns unified rows with utterance counts
expected: list_argument_speakers returns one row per ArgumentParticipant with a correct utterance_count computed via a single grouped query (no N+1)
result: pass
source: automated
coverage_id: D1

### 9. [auto] Bench rows carry tenure-derived role or missing-tenure flag
expected: Bench rows carry bench_role/argument_role when a CourtTenure covers argued_date, or missing_tenure=True + person_edit_href when none does
result: pass
source: automated
coverage_id: D2

### 10. [auto] Advocate rows carry role + title + hint
expected: Advocate rows carry argument_role from ADVOCATE_LABEL_MAP and title/title_hint from ArgumentParticipant.title
result: pass
source: automated
coverage_id: D3

### 11. [auto] get_argument_detail returns status_log + speakers
expected: get_argument_detail returns status_log (oldest-first ArgumentStatusLog rows) and speakers (full list_argument_speakers output)
result: pass
source: automated
coverage_id: D4

### 12. [auto] update_participant_side persists title conditionally
expected: update_participant_side persists title only when provided (leaves it unchanged when omitted) and still rejects side==BENCH
result: pass
source: automated
coverage_id: D5

### 13. [auto] PATCH participants route persists title
expected: PATCH /arguments/{id}/participants/{id} accepts {side, title}, persists both, and returns the persisted title
result: pass
source: automated
coverage_id: D6

### 14. Confirm Plan 26-02 auto-covered deliverables
expected: |
  Plan 26-02 (speakers + status log data contract) deliverables were all auto-verified by passing tests:
  - list_argument_speakers returns one row per participant with correct utterance counts (no N+1)
  - Bench rows carry tenure-derived role, or missing_tenure + person_edit_href
  - Advocate rows carry role + title + title_hint
  - get_argument_detail returns status_log (oldest-first) and speakers
  - update_participant_side persists title only when provided; still rejects BENCH
  - PATCH participants route accepts and returns {side, title}
  No manual test needed — confirm you have no reason to doubt this automated coverage.
result: pass

### 15. Arguments list — three-state badges
expected: On /admin/arguments, Draft arguments show a violet badge, Published arguments show a green badge, and Unpublished arguments show a distinct orange badge.
result: pass

### 16. Arguments list — Created column
expected: The arguments list table has a "Created" column between "Argued" and the row-actions column, showing the resolved_at date (or "—" if none).
result: pass

### 17. Arguments list — status-driven row actions
expected: Row actions are status-driven — Draft and Unpublished arguments show a "Publish" action; Published arguments show an "Unpublish" action.
result: pass

### 18. Pipeline job detail — Archived badge
expected: On a pipeline job detail page whose argument has already been created, RunStatusCard shows a neutral-grey "Archived" badge instead of the normal job-status badge.
result: issue
reported: "pass for the details page but I was expecting the same badge to be present on the pipeline list and it's not there"
severity: major

### 19. [auto] Status card shows badge + Created/Published dates
expected: Status card shows the three-state badge, a "Created {date}" line (relabeled from "Resolved"), and a "Published {date}" line when set
result: pass
source: automated
coverage_id: D1

### 20. [auto] Status history card lists status_log entries oldest-first
expected: Status history card lists every status_log entry oldest-first as {badge} — {date, time}, with the first draft entry labelled "Created" and a degraded fallback message
result: pass
source: automated
coverage_id: D2

### 21. [auto] Publish/Unpublish live inside Status card
expected: Publish button shows for Draft and Unpublished arguments; Unpublish shows for Published; both live inside the Status card, not floating between Speakers and Danger Zone
result: pass
source: automated
coverage_id: D3

### 22. [auto] Unified Speakers section fields
expected: Unified Speakers section — advocate rows get a three-option role select (no UNKNOWN), a title input with an Extracted hint, an utterance count, and inline Save; bench rows show tenure-derived role or Missing tenure + Edit person, each with an utterance count
result: pass
source: automated
coverage_id: D4

### 23. [auto] Draft-only delete gate + tooltip copy
expected: Delete is enabled only for Draft arguments; Published and Unpublished show the disabled button with the updated tooltip copy
result: pass
source: automated
coverage_id: D5

### 24. Argument edit page — full render across all three lifecycle states
expected: Opening the argument edit page (/admin/arguments/[id]) for an argument in each of the three states (draft, published, unpublished) renders correctly — Status card shows badge + Created/Published dates + Publish/Unpublish button; Status history card lists status_log entries oldest-first; Speakers table shows advocate rows (role select, title, Extracted hint, utterance count, Save) and bench rows (tenure-derived role or Missing tenure + Edit person link, utterance count); Delete is disabled unless status is Draft.
result: pass

### 25. [auto] delete_argument rejects PIPELINE-status arguments
expected: delete_argument rejects PIPELINE-status arguments server-side (DRAFT-only gate), matching the router's 409 and the client's can_delete gate
result: pass
source: automated
coverage_id: D1

### 26. Unresolved advocate side — explicit placeholder + Save disabled
expected: On the argument edit page, an advocate row whose side is UNKNOWN/unresolved shows an explicit "Unresolved — choose a role" placeholder in the role select, and the Save button for that row is disabled until a real role is chosen.
result: blocked
reason: "Resolve/Speakers table is scheduled for rework per project/.planning/seeds/SEED-001-rework-resolve-table-requirements.md — not worth testing ahead of that rework"
waived_at: 2026-08-18
waived_by: "operator — instructed to skip the outstanding human UAT items and prepare for Phase 48"
waiver_reason: "NOT VERIFIED — deliberately not run, not a pass. The original skip reason turned out to be mistaken: the rework it deferred to (SEED-001 → Phase 44) landed on the pipeline job page's Resolve card, not on this argument-editor Speakers card, so the deferral never resolved itself. The 2026-08-18 audit confirmed the code is present and correct-looking — the placeholder at `admin/arguments/[id]/+page.svelte:497` and the Save gate on `speakerSideById[...] === 'UNKNOWN'` at :544 — but no human has exercised it in a browser. Phase 49 (Review Model) touches participant review state and is the natural place to verify it."
phase_49_06_update: |
  2026-08-23 (Phase 49 plan 49-06): the blocking precondition this test actually needed — a real
  argument with an advocate participant whose `side` is UNKNOWN — did not exist anywhere in the
  corpus until now, closing the loop this test has been waiting on since 2026-08-18.
  `api.services.admin_dev.seed_unresolved_speaker_fixture` (D-33a) makes it reachable on demand.
  Run once against the live dev database (not synthetic — conversation 15169, "Baltimore & Ohio
  Railroad Company v. United States", argument id 1784), it selected participant 3500 (Lloyd N.
  Cutler), whose `side` was ALREADY SideEnum.UNKNOWN in the real corpus data (a residual
  pre-Resolve-rework state, not something this seeder invented), and nulled its `person_id`.
  Confirmed by direct query immediately afterward: participant 3500 now reads
  side=UNKNOWN, person_id=NULL, review_state=needs_review, and the argument appears on
  `GET /api/admin/review/arguments` with exactly that constituent. A second call confirmed
  idempotence (`already_seeded: true`, same participant id, no second row touched).
  **This is a data-layer observation only** — a direct query and an in-process API call, not a
  browser. The visual claim this test actually makes (the placeholder text renders, the Save
  button is genuinely disabled) has NOT been observed: this sandbox's permission policy denies
  reading `.env` (where ADMIN_USERNAME/ADMIN_PASSWORD/SESSION_SECRET live), so no authenticated
  `/admin/**` browser session was reachable by this executor, and no workaround was attempted.
  **STILL NOT VERIFIED — do not read this note as a pass.** A human must run `Reset to Fixture`
  then `Seed unresolved speaker` from `/admin` (or confirm the state above is already live),
  open `/admin/arguments/1784`, confirm the placeholder and Save-gate render exactly as expected,
  and flip this `result` to `pass` or `issue` based on what they actually see.
blocking_reason_now: "authenticated /admin/** browser session unavailable to the automated executor (this sandbox denies reading .env for admin credentials) — no longer a missing-state blocker"

### 27. Pipeline list page — Archived badge (retest of Test 18 gap fix)
expected: |
  On /admin/pipeline (list page), open a job whose linked argument has already been created
  (left PIPELINE status) and confirm the row's status badge reads the grey "Archived" badge
  (#cbd5e1), visually matching the same run's detail-page RunStatusCard exactly.
result: pass

## Summary

total: 27
passed: 25
issues: 0
pending: 0
skipped: 0
blocked: 1
waived: 0
audit_note: "2026-08-18 audit + operator waiver. Test 26 skipped → waived: NOT verified, deliberately not run. Its original deferral pointed at a rework that landed elsewhere (Phase 44's Resolve card, not this Speakers card); code confirmed present but never exercised in a browser. Phase 49 is the natural place to verify."
phase_49_06_note: "2026-08-23 (plan 49-06): Test 26's original blocking reason (no state to test) is resolved — see the test's own phase_49_06_update. Reclassified waived -> blocked (blocked on authenticated-browser access in this sandbox, not on a missing state) rather than waived (an operator's deliberate skip) or pass (unobserved). A human must complete the browser check before this can become pass/issue."

## Gaps

- truth: "RunStatusCard shows a neutral-grey Archived badge when the run's argument has already been created"
  status: resolved
  reason: "User reported: pass for the details page but I was expecting the same badge to be present on the pipeline list and it's not there"
  severity: major
  test: 18
  root_cause: "The pipeline list page (app/src/routes/admin/pipeline/+page.svelte) has no Archived-badge branch, and more fundamentally its backing list endpoint never computes or returns the signal needed: list_jobs() in api/services/admin_jobs.py runs a plain select(AdminJob) with no join to Argument, and AdminJobResponse (api/schemas/admin_jobs.py) has no field indicating the linked argument's status. The detail page instead calls a separate per-job GET /api/admin/jobs/{job_id}/readiness endpoint (get_job_readiness() in admin_jobs.py, api/routers/admin.py ~line 393) which has no list/batch equivalent. This is a missing data field, not a missing render branch."
  artifacts:
    - path: "api/schemas/admin_jobs.py"
      issue: "AdminJobResponse has no field indicating whether the linked argument has already been created (left PIPELINE status)"
    - path: "api/services/admin_jobs.py"
      issue: "list_jobs() (~lines 212-235) does a plain select(AdminJob) with no outerjoin to Argument and no readiness/archived computation"
    - path: "app/src/routes/admin/pipeline/+page.svelte"
      issue: "badgeStyle()/badgeLabel() (~lines 108-141) only branch on job.status/job.current_step; no Archived override like RunStatusCard.svelte has"
  missing:
    - "Add argument_status (or is_archived) field to AdminJobResponse"
    - "Outerjoin Argument in list_jobs() and populate the new field (already-created when Argument.status != PIPELINE), mirroring the existing parse_stats injection pattern"
    - "Extend the list page's badge logic to render the grey Archived badge when the new field indicates the argument is already created, mirroring RunStatusCard.svelte's readiness.state === 'already_created' override (lines 44-50)"
  debug_session: ""
  resolution: "Closed by gap-closure plan 26-06 — is_archived added to AdminJobResponse, populated via outerjoin in list_jobs(), consumed by the list page's badge logic. Code-level fix independently confirmed by 26-REVIEW.md and 26-VERIFICATION.md re-derivation. Visual parity retest tracked as Test 27, pending."
