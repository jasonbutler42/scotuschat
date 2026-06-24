---
status: diagnosed
phase: 12-people-admin-improvements
source: 12-01-SUMMARY.md, 12-02-SUMMARY.md, 12-03-SUMMARY.md, 12-04-SUMMARY.md
started: 2026-06-24T00:00:00Z
updated: 2026-06-24T00:00:00Z
---

## Current Test

[testing complete]

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
  root_cause: "The save form's submit button is the last element inside <form action=\"?/save\">. The Bio & Photo card is a sibling form placed after the save form closes (line 536 of +page.svelte), so it always renders below Save Changes. HTML disallows nested forms so Bio & Photo cannot be inside the save form. Fix: add id=\"save-form\" to the save form, move the Save Changes button outside the form after the Bio & Photo card, and associate it via <button type=\"submit\" form=\"save-form\">."
  artifacts:
    - path: "app/src/routes/admin/people/[id]/+page.svelte"
      issue: "Save Changes button is inside the save form (line 527-533); Bio & Photo card starts at line 536 after </form>"
  missing:
    - "Add id=\"save-form\" to the save form element"
    - "Remove Save Changes button from inside the form"
    - "Re-add Save Changes button after the Bio & Photo card with form=\"save-form\" attribute"
  debug_session: ""

- truth: "Bio text can be saved independently of photo — editing bio and submitting persists on reload, whether or not a photo is selected"
  status: failed
  reason: "User reported: If I enter a bio and hit Save photo but haven't selected a photo, I get an error about not having selected a photo. If I use Save Changes it appears to save but on refresh the bio is gone. Bio save should not be tied to the photograph."
  severity: major
  test: 4
  root_cause: "The photo action in +page.server.ts always POSTs to FastAPI /photo even when outForm is empty (no file, no URL). FastAPI returns 422 when the FormData has neither field. Fix: after the best-effort bio PATCH, check if outForm has any entries; if empty, skip the FastAPI call and redirect(303) immediately."
  artifacts:
    - path: "app/src/routes/admin/people/[id]/+page.server.ts"
      issue: "photo action (line ~287): outForm may be empty if no file/URL provided; still calls FastAPI which returns 422"
  missing:
    - "In photo action: after best-effort bio PATCH, if outForm is empty (no photo_file, no photo_url), skip FastAPI call and redirect(303, ...) directly"
  debug_session: ""

- truth: "Merge preview counts reload correctly each time a different target person is selected"
  status: failed
  reason: "User reported: Preview counts show up but can't confirm accuracy. Only works once — selecting a second target person after the first gives 'Could not load counts. Try again.' error."
  severity: major
  test: 5
  root_cause: "onchange fires fetchMergePreview(mergeTargetId) reading mergeTargetId from $state closure. In Svelte 5 Runes, bind:value and onchange both react to the same DOM change event — the $state update may not have flushed when onchange reads it, causing the second call to pass the stale previous target_id. Fix: read the value directly from the event: onchange={(e) => fetchMergePreview((e.target as HTMLSelectElement).value)}. Also add Cache-Control: no-store to the proxy response."
  artifacts:
    - path: "app/src/routes/admin/people/[id]/+page.svelte"
      issue: "line 678: onchange={() => fetchMergePreview(mergeTargetId)} reads $state variable which may be stale at event fire time"
    - path: "app/src/routes/admin/people/[id]/merge-preview/+server.ts"
      issue: "No Cache-Control header on json() response"
  missing:
    - "Change onchange to read from event.target.value instead of $state variable"
    - "Add Cache-Control: no-store header to the json() response in +server.ts"
  debug_session: ""

- truth: "After merge executes and redirects to the target person's page, all client state resets as if navigated there directly — no stale picker selection or preview counts carried over"
  status: failed
  reason: "User reported: Merge redirects to the target person's page but the page still has the previously selected target still open in the merge picker. It should reset as if you navigated to the target person directly."
  severity: major
  test: 6
  root_cause: "SvelteKit soft-navigates between /admin/people/[id] pages with different [id] params, reusing the component instance. Svelte 5 $state variables (mergeTargetId, mergePreview, mergeError, mergeLoading) are initialized once at mount and never reset on soft navigation. Fix: add a $effect that tracks data.person.id and resets all merge $state variables when it changes."
  artifacts:
    - path: "app/src/routes/admin/people/[id]/+page.svelte"
      issue: "$state merge variables not reset on SvelteKit soft navigation to different person"
  missing:
    - "Add $effect(() => { data.person.id; mergeTargetId = ''; mergePreview = null; mergeError = null; mergeLoading = false; })"
  debug_session: ""

- truth: "A person with only aliases (no utterances, appearances, or argument participants) can be deleted — aliases should cascade-delete or be excluded from the orphan block check"
  status: failed
  reason: "User reported: Person with 0 utterances, 1 alias, 0 appearances, 0 argument participants cannot be deleted. Aliases should not block deletion."
  severity: major
  test: 8
  root_cause: "delete_person_if_orphan checks all 4 FK tables including SpeakerAlias. Any alias > 0 returns False (caller -> 409). Aliases are name variants intrinsic to the person and should be deleted with them. Fix: (1) in delete_person_if_orphan, delete all SpeakerAlias rows before the orphan check, then check only Utterance/CaseAppearance/ArgumentParticipant; (2) in +page.server.ts load, exclude aliases from the can_delete condition and delete_block_count."
  artifacts:
    - path: "api/services/admin_people.py"
      issue: "delete_person_if_orphan (line ~380): SpeakerAlias included in orphan check"
    - path: "app/src/routes/admin/people/[id]/+page.server.ts"
      issue: "can_delete check (line ~124): aliases === 0 required; delete_block_count includes aliases"
  missing:
    - "In delete_person_if_orphan: delete SpeakerAlias rows first, then check only Utterance/CaseAppearance/ArgumentParticipant"
    - "In +page.server.ts load: remove aliases from can_delete condition and delete_block_count"
  debug_session: ""

- truth: "Submitting a photo URL should fetch the image from that URL and save it locally on the server, not store an external URL reference"
  status: failed
  reason: "User reported: works visually, but requirement is that the URL path should fetch the image and save it to the local server — not store an external URL reference. Everything should be self-contained locally at this stage."
  severity: major
  test: 3
  root_cause: "In admin.py upload_person_photo (line 435-436): photo_url path calls people_service.update_photo_url() which stores the URL string directly. Fix: when photo_url is provided, fetch the image bytes from the URL (httpx/urllib), validate with Pillow (same two-gate check as file upload), then call upload_photo() to save via existing dual-path local/Spaces logic."
  artifacts:
    - path: "api/routers/admin.py"
      issue: "upload_person_photo (line 435-436): photo_url path calls update_photo_url() which stores external URL as-is"
    - path: "api/services/admin_people.py"
      issue: "update_photo_url (line ~399): stores URL string directly, no fetch/download"
  missing:
    - "In upload_person_photo router: fetch image bytes from photo_url, validate with Pillow, call upload_photo() instead of update_photo_url()"
  debug_session: ""
