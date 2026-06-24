---
status: complete
phase: 12-people-admin-improvements
source: 12-01-SUMMARY.md, 12-02-SUMMARY.md, 12-03-SUMMARY.md, 12-04-SUMMARY.md
started: 2026-06-24T00:00:00Z
updated: 2026-06-24T00:00:00Z
---

## Current Test

number: 8
name: Delete — eligible person (no associated records)
expected: |
  [testing complete]
awaiting: complete

## Tests

### 1. Bio & Photo unified card layout
expected: Open the edit page for any person in /admin/people. A card labelled "Bio & Photo" appears with a bio textarea at the top, followed by a photo preview/widget below it. This is a single card — bio and photo are not separated by other sections (Court Tenure, Appointment, etc.).
result: issue
reported: "bio and phot are together in one card but it's still below the 'Save Changes' button"
severity: major

### 2. Photo upload via file
expected: On the Bio & Photo card, an "Upload" tab is active by default. Selecting an image file (JPEG/PNG/WEBP) and clicking Save/submit on that form updates the person's photo. The new photo appears in the preview. The page stays on the same person's edit page after the redirect.
result: pass

### 3. Photo URL entry
expected: Clicking the "URL" tab on the photo widget shows a text input. Entering a valid image URL and submitting updates the photo. The preview reflects the new URL.
result: issue
reported: "works visually, but requirement is that the URL path should fetch the image and save it to the local server — not store an external URL reference. Everything should be self-contained locally at this stage."
severity: major

### 4. Bio text saved via Bio & Photo form
expected: Edit the bio textarea in the Bio & Photo card and click its submit button. Reloading the page shows the updated bio text. (Bio is saved through the photo action, not the main Save Changes button.)
result: issue
reported: "If I enter a bio and hit Save photo but haven't selected a photo, I get an error about not having selected a photo. If I use Save Changes it appears to save but on refresh the bio is gone. Bio save should not be tied to the photograph."
severity: major

### 5. Merge preview counts appear on picker change
expected: Scroll to the Merge section. Selecting a target person from the dropdown triggers a fetch and displays a preview panel showing exact integer counts for: utterances, aliases, appearances, and argument participants that will be transferred from this person to the target.
result: issue
reported: "Preview counts show up but can't confirm accuracy. Only works once — selecting a second target person after the first gives 'Could not load counts. Try again.' error."
severity: major

### 6. Merge execution
expected: With a target person selected and preview counts shown, clicking Confirm (or equivalent) executes the merge. The browser redirects to the target person's edit page. The original (source) person no longer appears when browsing /admin/people.
result: issue
reported: "Merge redirects to the target person's page but the page still has the previously selected target still open in the merge picker. It should reset as if you navigated to the target person directly."
severity: major

### 7. Delete — ineligible person (has associated records)
expected: For a person who has utterances, aliases, or other associated records, the Delete section shows a disabled/grayed-out delete button with cursor: not-allowed. A tooltip or message explains that deletion is blocked because the person has associated records.
result: pass

### 8. Delete — eligible person (no associated records)
expected: For a person with no associated records, the Delete section shows an active delete button (red border styling). Clicking it deletes the person and redirects to /admin/people. The deleted person no longer appears in the list.
result: issue
reported: "Person with 0 utterances, 1 alias, 0 appearances, 0 argument participants cannot be deleted. Aliases should not block deletion."
severity: major

## Summary

total: 8
passed: 2
issues: 6
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Bio & Photo card appears as a unified section positioned above the Save Changes button"
  status: failed
  reason: "User reported: bio and phot are together in one card but it's still below the 'Save Changes' button"
  severity: major
  test: 1
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Bio text can be saved independently of photo — editing bio and submitting persists on reload, whether or not a photo is selected"
  status: failed
  reason: "User reported: If I enter a bio and hit Save photo but haven't selected a photo, I get an error about not having selected a photo. If I use Save Changes it appears to save but on refresh the bio is gone. Bio save should not be tied to the photograph."
  severity: major
  test: 4
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "After merge executes and redirects to the target person's page, all client state resets as if navigated there directly — no stale picker selection or preview counts carried over"
  status: failed
  reason: "User reported: Merge redirects to the target person's page but the page still has the previously selected target still open in the merge picker. It should reset as if you navigated to the target person directly."
  severity: major
  test: 6
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Merge preview counts reload correctly each time a different target person is selected"
  status: failed
  reason: "User reported: Preview counts show up but can't confirm accuracy. Only works once — selecting a second target person after the first gives 'Could not load counts. Try again.' error."
  severity: major
  test: 5
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "A person with only aliases (no utterances, appearances, or argument participants) can be deleted — aliases should cascade-delete or be excluded from the orphan block check"
  status: failed
  reason: "User reported: Person with 0 utterances, 1 alias, 0 appearances, 0 argument participants cannot be deleted. Aliases should not block deletion."
  severity: major
  test: 8
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Submitting a photo URL should fetch the image from that URL and save it locally on the server, not store an external URL reference"
  status: failed
  reason: "User reported: works visually, but requirement is that the URL path should fetch the image and save it to the local server — not store an external URL reference. Everything should be self-contained locally at this stage."
  severity: major
  test: 3
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
