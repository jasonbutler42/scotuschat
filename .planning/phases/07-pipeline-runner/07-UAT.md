---
status: diagnosed
phase: 07-pipeline-runner
source: 07-01-SUMMARY.md, 07-02-SUMMARY.md, 07-03-SUMMARY.md, 07-04-SUMMARY.md, 07-05-SUMMARY.md, 07-06-SUMMARY.md
started: 2026-06-16T00:00:00Z
updated: 2026-06-17T03:00:00Z
---

## Current Test

<!-- OVERWRITE each test - shows where we are -->

[testing complete]

## Tests

### 1. Pipeline Runner nav link is active
expected: Navigate to any /admin/* page. The sidebar/nav shows "Pipeline Runner" as a clickable link (not greyed-out text). Clicking it takes you to /admin/pipeline.
result: pass

### 2. /admin/pipeline page loads with URL mode by default
expected: Navigating to /admin/pipeline shows the "New Run" form in URL mode by default. The URL input field is visible; no file picker is shown. A "Start Run" button is present but disabled when the input is empty.
result: pass

### 3. Toggle to file upload mode
expected: Clicking the "Upload PDF" / file toggle button switches the form so the URL input disappears and a file picker appears. The toggle button reflects the active mode (aria-pressed state). Clicking back to URL mode restores the URL input.
result: pass

### 4. Recent Runs history table
expected: The /admin/pipeline page shows a "Recent Runs" table below the New Run form. If no jobs exist yet, an empty-state message is shown. If jobs exist, each row shows the job id, status badge (with correct color per status), and relevant info.
result: pass

### 5. Start a run via URL mode
expected: Enter a supremecourt.gov PDF URL in the URL input (e.g. https://www.supremecourt.gov/oral_arguments/argument_audio/2023/22-1036.pdf) and click Start Run. The page redirects to /admin/pipeline/{id}. The new run appears in the Recent Runs table on returning to /admin/pipeline.
result: pass

### 6. SSRF guard rejects non-supremecourt.gov URLs
expected: Enter a URL that is NOT from supremecourt.gov (e.g. https://example.com/file.pdf) and click Start Run. The form shows an error (e.g. "Could not start the run") without creating a job or redirecting.
result: pass

### 7. /admin/pipeline/[job_id] live step cards
expected: Opening /admin/pipeline/{id} for an active job shows three step cards: Ingest, Parse, Resolve. The current running step shows a spinner and "Running" badge. The page auto-refreshes every ~2.5 seconds without any manual action — status badges update as the pipeline progresses.
result: pass

### 8. Polling stops on terminal state
expected: Once a job reaches "completed", "failed", or "paused" state, the page stops auto-refreshing (no more 2.5s network requests). The final state is displayed statically.
result: pass

### 9. Discrepancy review table appears on PAUSED resolve step
expected: When the Resolve step is PAUSED (speaker aliases could not be auto-resolved), the Resolve step card expands to show a discrepancy table. Each row lists a raw speaker label, the auto-matched candidate name (if any), and Confirm / Correct buttons. The "Continue Resolve" button is NOT yet visible.
result: pass

### 10. Confirm and Correct disposition in discrepancy table
expected: Clicking Confirm on a row marks that speaker match as accepted (visual indicator updates). Clicking Correct opens a typeahead input backed by a datalist — typing filters candidates; selecting one marks it corrected. Auto-matched HIT rows appear with Confirm button and an Override button that resets the row. Once ALL rows are dispositioned, the "Continue Resolve" button appears.
result: issue
reported: "Two problems: (1) UX wrong — want a single Change button; auto-matched rows should be assumed correct without needing an explicit Confirm click. (2) Typeahead for auto-matched HIT rows only shows Add New Person — no existing people listed — so there is no way to correct a wrong auto-match. (Ginsberg/Ginsburg two-entry behavior is acceptable.)"
severity: major

### 11. Add new person inline
expected: In the Correct typeahead, selecting "— Add new person —" reveals a small form with Full Name and Role fields. Submitting it creates the person, dismisses the form, and auto-selects them in that row. The new person is available for the duration of the session (note: does not persist after hard refresh, by design — resetting the page resets all row selections).
result: issue
reported: "Save Person button changes to Saving... then nothing else happens. Form stays visible, no selection is made. After page refresh the new person was not saved and does not appear in the dropdown."
severity: major

### 12. Continue Resolve submits and restarts polling
expected: After all rows are dispositioned, clicking Continue Resolve: button immediately shows "Submitting…" with disabled attribute (before network request fires); on success the Resolve card transitions away from "Needs Review" and polling resumes; on failure an error message appears below the form and button re-enables.
result: pass
note: Success path confirmed. Failure path not testable without manufacturing a server error — acceptable skip.

### 13. Failed-state error panel
expected: For a job where a step failed, /admin/pipeline/{id} shows "This run failed." followed by the verbatim error message in monospace text. There is no Retry button — only a "Start a new run" link back to /admin/pipeline.
result: skipped

### 14. Pipeline CLI --job-id flag (ingest)
expected: Running `python -m pipeline ingest --help` in a terminal shows both `--job-id` and `--spaces-key` flags listed. Running `python -m pipeline parse --help` and `python -m pipeline resolve --help` each show `--job-id`.
result: blocked
blocked_by: other
reason: "ModuleNotFoundError: No module named 'sqlalchemy' — venv not activated in test terminal."

## Summary

total: 14
passed: 10
issues: 2
pending: 0
skipped: 1
blocked: 1

## Gaps

- truth: "Auto-matched HIT rows need only a single Change button — no explicit Confirm step. Clicking Change opens a typeahead listing ALL existing people (not just Add New Person) so a wrong auto-match can be corrected."
  status: failed
  reason: "User reported: UX has Confirm+Override instead of single Change button; typeahead for HIT rows only shows Add New Person — can't correct a wrong auto-match."
  severity: major
  test: 10
  root_cause: |
    Two separate causes. (1) Button UX: rowStates init in +page.svelte ignores auto_resolved — all rows start with disposition: null, so HIT rows fall into the same Confirm+Correct rendering branch as MISS rows. auto_resolved field is never read in the template (lines 71-89, 553-618). (2) Empty typeahead: resolve.py line 243 explicitly writes candidates: [] for HIT rows ('HIT rows need no candidates'). No separate people list is loaded in +page.server.ts load(). getRowCandidates() only returns row.candidates + extraCandidates, both empty for HIT rows.
  artifacts:
    - path: "pipeline/commands/resolve.py"
      issue: "Line 243 writes candidates: [] for HIT rows — full people list omitted intentionally but incorrectly"
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.svelte"
      issue: "rowStates init (lines 71-89) ignores auto_resolved; Column 3 rendering (lines 553-618) has no HIT-specific branch"
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.server.ts"
      issue: "load() fetches only the job row — no people list loaded for typeahead"
  missing:
    - "Initialize HIT rows with disposition: 'confirmed' in rowStates; render single Change button for auto_resolved===true rows"
    - "Populate candidates for HIT rows in resolve.py (same as MISS rows) OR load all people in +page.server.ts and pass to getRowCandidates()"
  debug_session: ".planning/debug/discrepancy-ux-typeahead.md"

- truth: "Selecting 'Add new person' creates the person server-side, dismisses the inline form, and auto-selects them in that row."
  status: failed
  reason: "User reported: Save Person button flashes Saving... then nothing — form stays visible, no selection made. Person not persisted after page refresh."
  severity: major
  test: 11
  root_cause: |
    handleAddPerson uses a raw fetch with two compounding bugs that prevent the success branch from executing. (1) Missing Accept: application/json header — SvelteKit's is_action_json_request() gates the JSON action path on this header, not on x-sveltekit-action. Without it, SvelteKit returns an HTML redirect response; calling res.json() on HTML either throws (caught silently) or returns malformed data. (2) Uses res.json() instead of deserialize(await res.text()) — SvelteKit serializes action return values via devalue.stringify(), not plain JSON. After res.json(), envelope.data is a raw devalue string; accessing envelope.data.person yields undefined, so the state-update branch never runs and the form stays visible.
  artifacts:
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.svelte"
      issue: "handleAddPerson (lines 236-243): missing Accept: application/json header; uses res.json() instead of deserialize(await res.text()) from $app/forms"
  missing:
    - "Add Accept: application/json to fetch headers in handleAddPerson"
    - "Replace res.json() with deserialize(await res.text()) importing deserialize from $app/forms"
    - "Preferred: replace raw fetch entirely with use:enhance on a <form> element — handles both headers and devalue deserialization idiomatically"
  debug_session: ".planning/debug/add-person-silent-fail.md"

- truth: "Cases only appear in /cases/ after resolve is complete with real case metadata (docket number, argued date, title)."
  status: failed
  reason: "User reported: newly ingested arguments appear in /cases/ before resolution with placeholder titles like 'Pending review (job 3)' and metadata like 'No. job-3 · Argued June 17, 2026 · Question 1'."
  severity: major
  test: 0
  root_cause: |
    Two cooperating defects. (1) ingest.py creates Case/Argument/CaseArgument rows at ingest time with synthetic placeholder values (case_name='Pending review (job N)', docket_number='job-N', argued_date=today()) and commits them. The CaseArgument is_lead=True row is also created at this point, immediately satisfying the API query's only filter. (2) The Case and Argument models have no visibility/status column (no resolved_at, is_published, or status field) — confirmed across all three Alembic migrations. get_cases() in api/services/cases.py queries all Cases with a lead CaseArgument with no resolve-completion filter. Resolve never updates case metadata or sets any visibility flag.
  artifacts:
    - path: "pipeline/commands/ingest.py"
      issue: "Creates Case/Argument/CaseArgument rows with placeholder metadata at ingest time, before parse or resolve"
    - path: "api/services/cases.py"
      issue: "get_cases() has no resolve-completion filter; no column exists to add one without a migration"
    - path: "api/models/models.py"
      issue: "Case and Argument models have no resolved_at, is_published, or status column"
    - path: "pipeline/commands/resolve.py"
      issue: "Resolve never updates case metadata or sets a visibility flag after completion"
  missing:
    - "Add resolved_at TIMESTAMPTZ nullable column to arguments table via new Alembic migration"
    - "Set arguments.resolved_at = now() in resolve.py when job reaches COMPLETED state"
    - "Add WHERE arguments.resolved_at IS NOT NULL filter to get_cases() in api/services/cases.py"
    - "Update case metadata (case_name, docket_number, argued_date) from resolved data in resolve.py"
  debug_session: ".planning/debug/cases-premature-visibility.md"

