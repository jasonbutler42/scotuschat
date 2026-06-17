---
status: diagnosed
phase: 07-pipeline-runner
source: 07-01-SUMMARY.md, 07-02-SUMMARY.md, 07-03-SUMMARY.md, 07-04-SUMMARY.md, 07-05-SUMMARY.md
started: 2026-06-16T00:00:00Z
updated: 2026-06-17T00:00:00Z
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
expected: Clicking Confirm on a row marks that speaker match as accepted (visual indicator updates). Clicking Correct opens a dropdown populated with candidate names from that row only. Selecting a candidate from the dropdown marks it as corrected. Once ALL rows are dispositioned, the "Continue Resolve" button appears.
result: issue
reported: "1. There are no rows that have 'confirm' as an action. Could be that they resolved automatically? If so, I would expect to still see them in the interface with a status of 'automatically matched' or something but there should always be the option to override that match. 2. As expected, there are several speakers needing to be matched with a 'Correct' action button. 3. Clicking 'Correct' bring up a list of existing people to choose from or give me the option to create a new speaker. 4. If I select an existing speaker, I get a new status of 'Corrected' followed by who I selected. However, there's no way to change the selection so if I chose the wrong one, I'm stuck. 5. Once all rows are corrected, the 'Continue Resolve' button shows up correctly. Two changes needed: 1. Make the dropdown a typeahead field. 2. Allow for changing the person after a selection is made."
severity: major

### 11. Add new person inline
expected: In the Correct dropdown, selecting "— Add new person —" reveals a small form with Full Name and Role fields. Submitting it creates the person and auto-selects them in that row's dropdown, dismissing the form. The new person is now available as a candidate in that row.
result: issue
reported: "When I select 'Add new person' I get the small form with the two fields. When I enter a name and role and hit save, the button briefly changes to indicate the person was saved then immediately goes back to 'Save person' with no other visible changes: the small form does NOT go away and the interface does not automatically select the newly created person. If I refresh the screen, I can reset the Resolve process so that no selections have been made. After a refresh, the dropdowns look the same as before--the newly created person does not show up in the dropdown."
severity: major

### 12. Continue Resolve submits and restarts polling
expected: After all rows are dispositioned, clicking Continue Resolve submits the matches. The button text changes to "Submitting…" and becomes disabled. The page then transitions the Resolve step from PAUSED back to RUNNING (or COMPLETED if no further issues), and polling resumes to show the updated state.
result: issue
reported: "The button text changes to 'Submitting...' but does not disable itself. The status indicator in the top right corner of the Resolve card does not change; it still says 'Needs Review' with a pause icon."
severity: major

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
passed: 9
issues: 3
pending: 0
skipped: 1
blocked: 1

## Gaps

- truth: "Discrepancy table shows ALL speaker aliases — auto-matched rows visible with 'Confirmed' status and an override option; unmatched rows show Confirm/Correct actions. After selecting a correction, the user can change their selection."
  status: failed
  reason: "User reported: No rows with Confirm action visible (auto-matched rows not shown with override option). After selecting a person via Correct, there is no way to change the selection. Dropdown should be a typeahead field."
  severity: major
  test: 10
  root_cause: "Two sub-problems: (A) resolve.py only appends to discrepancies on alias MISS — HIT rows are silently auto-resolved and never written to the discrepancies JSONB column, so auto_match_id is always None and the Svelte Confirm branch never renders. (B) In handleSelectPerson(), once disposition is set to 'corrected' the action column renders nothing — no Change/Override button exists to reopen the dropdown."
  artifacts:
    - path: "pipeline/commands/resolve.py"
      issue: "Lines 204–256: HIT branch never appends to discrepancies list; only MISSes do. auto_match_id, auto_match_name, auto_match_role fields exist in schema but are never populated."
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.svelte"
      issue: "Lines 534–575: action column renders nothing once disposition is set; no re-open path (Change/Override button missing)"
  missing:
    - "resolve.py: HIT rows need to be added to discrepancies list with auto_match_id/name/role populated and auto_resolved: True flag"
    - "+page.svelte: after disposition === 'corrected' or 'confirmed', render an Override/Change button that resets disposition=null and correcting=true"
    - "(Enhancement) Replace <select> dropdown with typeahead/combobox component"
  debug_session: ""

- truth: "Selecting 'Add new person' in Correct dropdown creates the person, auto-selects them in that row, dismisses the inline form, and makes the new person immediately visible in the dropdown."
  status: failed
  reason: "User reported: Form does not dismiss after save; button reverts to 'Save person' with no selection made. After page refresh, newly created person does not appear in the dropdown at all."
  severity: major
  test: 11
  root_cause: "Two sub-problems: (A) handleAddPerson() calls fetch('?/addPerson') and parses the response as plain JSON, but SvelteKit form actions return an action envelope {type, status, data} — person resolves to undefined, so the if(person) branch is skipped, s.addingPerson stays true, and the form never dismisses. (B) Candidates are snapshotted at pipeline run time in JSONB; newly created people added after the run are not in that snapshot and s.extraCandidates is in-memory client state lost on refresh."
  artifacts:
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.svelte"
      issue: "Lines 235–256: fetch('?/addPerson') response parsing misreads SvelteKit action envelope; person resolves to undefined"
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.server.ts"
      issue: "Lines 68–98: addPerson action returns {personCreated: true, person} which SvelteKit wraps in its envelope"
    - path: "api/schemas/admin_jobs.py"
      issue: "Lines 55–62: PersonResponse omits role_name so returned person can't populate role in dropdown"
    - path: "pipeline/commands/resolve.py"
      issue: "Lines 184–244: candidates list snapshotted at pipeline run time; newly added people invisible after page refresh"
  missing:
    - "Use SvelteKit's applyAction/enhance helpers (or a dedicated fetch endpoint) instead of raw fetch for addPerson so the response envelope is parsed correctly"
    - "PersonResponse needs role_name: Optional[str] field joined from Role table"
    - "addPerson server action or load function needs to update JSONB candidates so new people appear after refresh"
  debug_session: ""

- truth: "Clicking Continue Resolve disables the button (shows 'Submitting…'), and the Resolve step transitions from PAUSED/Needs Review to RUNNING or COMPLETED with polling resuming."
  status: failed
  reason: "User reported: Button text changes to 'Submitting...' but does not disable. Resolve card status stays 'Needs Review' with pause icon — never transitions."
  severity: major
  test: 12
  root_cause: "Two sub-problems: (A) Continue Resolve form uses native POST without use:enhance — continueSubmitting=true fires but native form navigation destroys the component before Svelte can re-render the disabled attribute. (B) resolve action returns fail(422) on error but the component has no form prop binding or error display — failures are invisible. The polling $effect treats 'paused' as terminal so polling never restarts; without use:enhance + invalidateAll(), the load function does not re-run after the action, leaving the UI stuck at paused state."
  artifacts:
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.svelte"
      issue: "Lines 587–610: form uses native POST without use:enhance; onclick sets continueSubmitting but native navigation destroys component before next render; no form prop binding for error display. Line 39: polling $effect treats 'paused' as terminal."
    - path: "app/src/routes/admin/pipeline/[job_id]/+page.server.ts"
      issue: "Lines 30–61: resolve action returns fail(422) on error but component never reads form.error"
  missing:
    - "Add use:enhance to Continue Resolve form so: (a) button disabled takes effect before navigation; (b) form.error is accessible; (c) invalidateAll() is called after success to restart polling"
    - "Add error display block reading form?.error from resolve action result"
    - "Polling $effect should restart after successful resolve action (use:enhance + invalidateAll handles this)"
  debug_session: ""
