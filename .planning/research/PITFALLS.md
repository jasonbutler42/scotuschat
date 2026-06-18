# Pitfalls Research

**Domain:** LLM-based legal transcript parsing pipeline + SCOTUS oral argument chat interface + operator admin web interface
**Researched:** 2026-06-18 (v1.2 additions); 2026-06-15 (v1.1); 2026-06-11 (v1.0)
**Scope:** v1.2 additions — people merge (atomic FK transfer), image upload to DO Spaces, structured name migration, speaker popover (SSR vs. client fetch), argument metadata editing with resolved_at gate, appointing president/party fields, unified navigation, ingestion flow polish; v1.1 (preserved below); v1.0 (preserved below)
**Confidence:** HIGH — derived from direct inspection of the existing codebase (models, services, routes) and domain-specific knowledge of the feature areas involved

---

## Critical Pitfalls — v1.2 Feature Additions

Mistakes specific to adding people merge, image upload, name migration, speaker popover, metadata editing, and navigation unification to the existing system.

---

### Pitfall W1: People Merge Leaves Orphaned FK Rows Because Transfer Is Not Atomic

**What goes wrong:**
Merge logic transfers utterances (by updating `utterances.person_id`), aliases (`speaker_alias.person_id`), appearances (`case_appearances.person_id`), and argument_participants (`argument_participants.person_id`) from the source person to the target person, then deletes the source person. If any single FK update succeeds but a later one fails, the source person is partially drained. If the DELETE then runs, the source is gone but some rows still pointed to it are now orphaned (FK constraint will prevent this — which means the delete raises an IntegrityError, leaving the source person alive but with a partially inconsistent state). Re-running the merge with a partially-transferred source produces duplicate rows in the target.

**Why it happens:**
Each table update is written as a separate `await db.execute(update(...))` call. Without wrapping the entire sequence in one transaction, a network timeout, process kill, or exception between updates leaves the DB in a split state. SQLAlchemy async sessions have an open transaction by default (autocommit=False), but if each step is followed by an intermediate `await db.commit()`, the atomicity guarantee is lost.

**How to avoid:**
- Execute all FK-updating statements (`utterances`, `speaker_alias`, `case_appearances`, `argument_participants`) within a **single transaction** — one `await db.commit()` at the very end, after all updates succeed.
- Wrap the entire merge in a `try/except` that calls `await db.rollback()` on any exception before re-raising.
- Only issue the `DELETE FROM people WHERE id = source_id` after all FK rows have been transferred in the same transaction.
- Add a pre-merge check: verify the source person exists and is not the same as the target. Verify the target person exists.
- Write a post-merge assertion (separate read transaction) that confirms `COUNT(*) = 0` for all FK tables where `person_id = source_id`.
- Guard re-runs: if the source person no longer exists, return a 404 rather than treating it as a success — the merge already ran.

**Warning signs:**
Multiple sequential `await db.commit()` calls inside the merge function; merge endpoint has no explicit rollback on error; no transaction wrapper around the full transfer sequence.

**Phase to address:** People admin phase (merge feature).

---

### Pitfall W2: Partial Transfer — Some FK Tables Missed During Merge

**What goes wrong:**
The merge implementation updates `utterances.person_id` and `speaker_alias.person_id` but omits `case_appearances.person_id` and `argument_participants.person_id`. The source person can then be deleted (no FK violations remain from the tables that were updated), but `case_appearances` and `argument_participants` rows still point to the now-deleted source person — violating FK constraints and causing query errors or missing participant data in the UI.

**Why it happens:**
There are four FK tables pointing to `people.id`: `utterances`, `speaker_alias`, `case_appearances`, `argument_participants`. Developers discover the first two because they are most visible (resolving shows aliases and utterances). The other two are less prominent and easy to overlook when writing the transfer.

**How to avoid:**
- Enumerate all FK relationships from `people.id` before writing any merge code. Grep the models file for `ForeignKey("people.id")` — currently four tables.
- Write the transfer as an ordered list with a comment for each table, checked off: `[ ] utterances`, `[ ] speaker_alias`, `[ ] case_appearances`, `[ ] argument_participants`.
- Add a test: create two persons, insert one row each in all four FK tables for the source person, run merge, verify all four FK tables have zero rows for source_id and at least one for target_id.
- After the migration adding new name/president fields, check if any new FK tables reference `people.id` — if so, add them to the merge transfer list immediately.

**Warning signs:**
Merge tests only check `utterances` and `speaker_alias`; no test asserts the source person can be deleted without FK violation after merge.

**Phase to address:** People admin phase (merge feature).

---

### Pitfall W3: Image Upload Stores URL Before Confirming Spaces Write Success

**What goes wrong:**
Upload handler calls `upload_image_to_spaces(file_bytes, key)` and then immediately writes the returned URL to `people.photo_url` in the DB. If the Spaces upload raises a `ClientError` (network error, invalid credentials, bucket not found) but the exception is caught and swallowed, the DB row is updated to a URL that points to a file that does not exist. The avatar shows a broken image icon in the UI instead of the initials fallback.

**Why it happens:**
The existing `upload_pdf_to_spaces` function in `api/services/spaces.py` returns only the key, not the full URL, and has no error handling beyond a raw boto3 call. Image upload adds a new code path where the URL is derived from the key and stored in the DB. Developers write the DB update optimistically before verifying the upload succeeded.

**How to avoid:**
- Structure the upload handler as: (1) validate file, (2) upload to Spaces, (3) only if upload succeeds (no exception), write URL to DB. Never write the URL first.
- Let boto3 `ClientError` propagate to the route handler, which returns a 500 to the client. The DB is not touched on upload failure.
- Add explicit error handling for the most common Spaces failures: `NoCredentialsError`, `ClientError` with `code='NoSuchBucket'`, `ClientError` with `code='AccessDenied'`. Return a meaningful operator error message for each.
- Test the failure path: mock a Spaces `ClientError` and verify `people.photo_url` remains unchanged.

**Warning signs:**
`people.photo_url` is written inside the same `try` block as the Spaces upload call; no test for Spaces upload failure.

**Phase to address:** People admin phase (image upload).

---

### Pitfall W4: Image Upload Accepts Non-Image Files — No Content Validation

**What goes wrong:**
Image upload handler trusts the browser-supplied `Content-Type` (e.g., `image/jpeg`). An operator accidentally uploads a PDF or a `.js` file renamed to `.jpg`. The file is stored in Spaces and the URL is written to `photo_url`. When the browser requests the URL, either the image fails to render (PDF) or a JS file is served from the Spaces bucket with the wrong content type — a stored XSS vector if the bucket has permissive content-type behavior.

**Why it happens:**
The existing PDF upload code in `spaces.py` validates with magic bytes for PDF (`%PDF-`). The image upload feature is added as a separate code path and the developer forgets to apply the same pattern.

**How to avoid:**
- Check magic bytes for allowed image formats. JPEG: first 3 bytes `FF D8 FF`. PNG: first 8 bytes `89 50 4E 47 0D 0A 1A 0A`. WebP: bytes 0–3 `52 49 46 46` and bytes 8–11 `57 45 42 50`.
- Enforce a maximum file size for images (e.g., 5MB) — Justice headshots do not exceed this; a larger upload is likely an error.
- Restrict accepted file extensions at the UI level (accept="image/jpeg,image/png,image/webp") as a UX gate, not a security gate.
- Upload images to a `/people-images/` key prefix in Spaces, separate from `/pdfs/`. This makes it easy to apply different bucket policies to each prefix.
- Set `ContentType` explicitly when uploading (e.g., `image/jpeg` derived from magic bytes, not from the client's claim).

**Warning signs:**
Image upload handler passes `file.content_type` directly to `ExtraArgs={"ContentType": file.content_type}` without magic byte verification; no maximum file size enforced.

**Phase to address:** People admin phase (image upload).

---

### Pitfall W5: Structured Name Migration Corrupts full_name for Names With Non-Standard Formats

**What goes wrong:**
Migration splits `full_name` into `first_name`, `last_name`, `middle_name`, `name_suffix` using a naive split (e.g., `parts = full_name.split()`). This fails for:
- Names with titles: "Chief Justice John G. Roberts Jr." → `first_name = "Chief"`, `last_name = "Jr."`.
- Hyphenated last names: "Sandra Day O'Connor" → incorrect split.
- Single-name entries: "GENERAL PRELOGAR" (role-prefixed raw label that was incorrectly resolved to a person) → no recognizable structure.
- Names with suffixes: "Thurgood Marshall Jr." → suffix ends up in `last_name`.
- All-caps names from older resolution paths: "ANTONIN SCALIA" → capitalization preserved raw, display derivation must normalize.

Because the migration runs on production data that was manually entered, every existing `full_name` value must be audited, not assumed to follow a consistent pattern.

**Why it happens:**
Name splitting is a classic "looks easy, is hard" problem. The existing `people` table has a small number of rows (fewer than 30 after v1.1), making it tempting to write a generic splitter and call it done. But each name was entered by a human during v1.1 people editing and may reflect free-form input.

**How to avoid:**
- Do not auto-split names with code. Instead, write the migration as a data-only migration that adds the new columns as `nullable=True` with no default transformation. Let the admin fill in structured name fields via the edit form.
- If auto-population is desired for speed, write a Python script (not an Alembic data migration) that outputs a CSV of `id, full_name, proposed_first, proposed_last, ...` for operator review before any writes happen.
- Display name derivation (`first_name + (middle_name or '') + last_name + (suffix or '')`) must have a fallback to `full_name` when any of the structured fields are null — this is the safe default since structured fields will be null initially.
- The `speaker_alias` resolution and `resolve.py` step match against `full_name` or alias labels, not against `first_name`/`last_name`. Do not change the resolution matching logic to use structured fields — it would break existing aliases.

**Warning signs:**
Alembic migration includes a `UPDATE people SET first_name = split_part(full_name, ' ', 1)` statement; `full_name` column is dropped or made non-nullable after migration; display name derivation has no fallback to `full_name`.

**Phase to address:** People data model phase (structured name fields).

---

### Pitfall W6: Structured Name Columns Added Without Keeping full_name as the Resolution Anchor

**What goes wrong:**
After adding `first_name`/`last_name` columns, a developer changes the people directory listing or the speaker resolution logic to display/match against `first_name + ' ' + last_name`. Existing `speaker_alias` entries reference people by `person_id`, so alias lookups are unaffected. But any code that searches for people by name (e.g., the typeahead in discrepancy review, admin people search) now returns no results for people whose structured name fields are still null (the majority, immediately after migration). The operator cannot find people to merge or correct in the review flow.

**Why it happens:**
New fields feel more "correct" and developers migrate display logic to use them before all rows are populated.

**How to avoid:**
- Keep `full_name` as the primary display and search column throughout v1.2. Structured name fields are additive enrichment only.
- In all queries that filter by name (typeahead, people directory search), use `full_name` as the search target. Only use structured fields for display purposes once all rows are confirmed populated.
- Add a comment in the service layer: "full_name is the resolution anchor — do not replace with first_name/last_name in search queries until all rows are populated."

**Warning signs:**
`WHERE lower(first_name) LIKE ...` in any service query; typeahead returns fewer results after the migration than before.

**Phase to address:** People data model phase.

---

### Pitfall W7: Speaker Popover Fetches Person Data Client-Side, Breaking SSR and Creating CORS Exposure

**What goes wrong:**
Speaker popover is implemented with a `fetch('/api/people/{id}')` call triggered from a Svelte `$effect` when the popover opens. This works in the browser. On server-side rendering, `$effect` does not run, so the popover data is never populated — SSR renders the popover trigger with no content. More critically, the fetch URL uses `PUBLIC_FASTAPI_BASE_URL` to reach FastAPI directly from the browser. This exposes the FastAPI origin to the public internet, requires CORS to be enabled on `/people/{id}`, and contradicts the project constraint that `FASTAPI_BASE_URL` must be a server-only env var (`$env/static/private`).

**Why it happens:**
Client-side fetching for interactive popover data feels natural in a Svelte component. The FastAPI `/people/{id}` endpoint already exists. Developers reach for it directly without checking the env var constraint.

**How to avoid:**
- Popover person data must be loaded server-side, in the `+page.server.ts` load function for the argument page. Pass it as part of the page `data` prop: a `Map<personId, PersonDetail>` keyed by the person IDs in the argument's participant roster.
- The popover component receives pre-loaded person data as a prop, not fetched on open.
- There is no need for a new API endpoint for the popover — the existing `GET /people/{id}` call happens server-side in the load function, using `FASTAPI_BASE_URL` from `$env/static/private`.
- The popover shows/hides purely based on UI state (`$state` boolean), not on data availability.
- Cost of pre-loading: the argument page's load already fetches utterances; adding a handful of person detail fetches (one per participant, typically 5–15 per argument) adds minimal latency via parallel `Promise.all()`.

**Warning signs:**
`PUBLIC_FASTAPI_BASE_URL` referenced in any `.svelte` file or client-side TypeScript; `fetch('/api/people/...')` in a `$effect`; `onMount` used to populate popover content.

**Phase to address:** Speaker popover phase.

---

### Pitfall W8: Speaker Popover Accessibility Broken — Not Keyboard Navigable or Screen-Reader Announced

**What goes wrong:**
Popover is implemented as a `<div>` that appears on `click` of an avatar image. Tab navigation skips the avatar (not focusable). Screen readers do not announce the popover content because it appears in the DOM dynamically without ARIA live region or focus management. The popover has no close mechanism via keyboard (Escape key not handled). This violates WCAG 2.1 AA requirements already met in v1.0/v1.1 (A11Y-01 through A11Y-04).

**Why it happens:**
Popovers are a UI pattern where accessibility is easy to overlook because the visual result looks complete. The trigger avatar is an `<img>` or `<span>` — not natively focusable or keyboard-interactable.

**How to avoid:**
- Wrap the avatar trigger in a `<button>` element (not `<div>` or `<span>`). Buttons are natively keyboard-focusable and receive Enter/Space key events.
- Apply `aria-haspopup="dialog"` and `aria-expanded={isOpen}` to the trigger button.
- When the popover opens, move focus to the popover container (use Svelte's `action` or `bind:this` + `element.focus()`) and trap focus inside.
- Close on `Escape` key press and on click outside. Return focus to the trigger button when closing.
- Apply `role="dialog"` and `aria-label="[Person name] profile"` to the popover container.
- This is not a "nice to have" — it is required by the existing WCAG constraint.

**Warning signs:**
Avatar trigger is a bare `<img>` or `<span>`; no `role="dialog"` on the popover; no Escape key handler; no focus management on open/close.

**Phase to address:** Speaker popover phase.

---

### Pitfall W9: Argument Metadata Edit Allows Publishing (resolved_at Gate) Before Metadata Is Complete

**What goes wrong:**
Argument metadata editing adds the ability to set `title`, `docket`, and `date`. The edit form also exposes a "Publish" button that sets `resolved_at`. If validation does not enforce that title, docket, and date are all populated before `resolved_at` can be set, an operator accidentally publishes an argument with a placeholder title (e.g., the synthetic `job-{job_id}` docket assigned during ingest). This causes the case list to display incomplete or wrong information to public users — violating the resolved_at gate's intent.

**Why it happens:**
The gate is designed as a visibility control. Developers implement the edit form and the publish action as separate operations and forget to add cross-field validation that checks all required metadata is present before allowing publish.

**How to avoid:**
- The FastAPI endpoint that sets `resolved_at` (or the SvelteKit form action) must validate that `arguments.title` (or the lead case name), `argued_date`, and at least one associated case with a valid docket number are all non-null and non-empty before setting `resolved_at = NOW()`.
- The "Publish" button in the UI must be disabled (not just hidden) until required metadata is present. But server-side validation is the real gate — the UI state is UX, not security.
- Define "valid docket" explicitly: must not match the pattern `^job-\d+$` (the synthetic placeholder assigned during ingest).
- Return a clear validation error to the operator: "Cannot publish: docket number is a placeholder. Set a real docket before publishing."

**Warning signs:**
`resolved_at` can be set via a form submission that does not first check `docket_number NOT LIKE 'job-%'`; no server-side validation before writing `resolved_at`; publish button is hidden but not disabled.

**Phase to address:** Argument metadata editing phase.

---

### Pitfall W10: Argument Metadata Editing Changes Fields That Are Immutable Post-Resolve

**What goes wrong:**
After `resolved_at` is set (argument is public), an operator edits the argued date or lead case name. This is allowed by the edit form with no warning. The change is reflected immediately on the public case list and argument page. Downstream: share URLs that users have bookmarked show a different case name than when they bookmarked the page. If `slug` is derived from case name, changing the case name without re-deriving the slug breaks existing URLs.

**Why it happens:**
The edit form does not distinguish between fields that are "pre-publish safe to edit" and fields that are "immutable after publish." Without an explicit classification, all fields are editable at all times.

**How to avoid:**
- Classify fields by mutability: `argued_date`, `case_name`, `docket_number` are editable before `resolved_at` only (or require explicit "I know what I'm doing" confirmation after publish). `title`/display metadata corrections are acceptable after publish since the case is publicly known by its official name.
- In the edit form, render post-publish fields as read-only (disabled inputs) once `resolved_at IS NOT NULL`, with a note: "Argument is published. To change this field, contact the operator."
- `slug` must never change after the argument is public — it is the URL identity. If case name changes, only update the display name, not the slug.
- FastAPI edit endpoint should enforce field-level immutability: if `resolved_at IS NOT NULL`, reject writes to `argued_date` and `docket_number` with a 409 Conflict.

**Warning signs:**
Edit endpoint accepts all fields regardless of `resolved_at` status; no read-only rendering in the form for published arguments; slug re-derivation on case name update.

**Phase to address:** Argument metadata editing phase.

---

### Pitfall W11: Unified Navigation Duplicates Auth Logic Between Root Layout and Admin Layout

**What goes wrong:**
Root layout (`/routes/+layout.svelte`) renders a top nav for all routes. Admin layout (`/routes/admin/+layout.svelte`) also renders a nav. When unified navigation is added to the root layout, both layouts render a nav — resulting in two nav bars on admin pages. Alternatively, removing the admin layout's nav while keeping its other logic causes the auth check or logout form to be placed in the wrong layout, breaking the separation between public and admin UI.

**Why it happens:**
The existing codebase uses `{#if !page.url.pathname.startsWith('/admin')}` in the root layout to suppress the public nav for admin routes, and the admin layout renders its own nav. Adding unified navigation to the root layout requires careful coordination of these two guards.

**How to avoid:**
- Decide upfront: is the unified nav a single component rendered from the root layout with conditional content, or are there two separate nav components (public/admin) rendered by their respective layouts?
- The cleanest approach given the existing structure: root layout renders one `<Nav>` component that takes a `variant` prop ("public" | "admin" | "none") derived from `page.url.pathname`. Admin layout removes its own nav and relies on the root. The `{#if !page.url.pathname.startsWith('/admin')}` guard in the root layout is replaced by the `<Nav variant={...}>` conditional rendering.
- Auth-dependent nav items (logout button, admin links) must remain in a component that only runs in admin context — do not put session checks in the root layout's server load if the root layout also serves unauthenticated public routes.
- Verify: public `/cases` page has no logout button. Admin `/admin/pipeline` page has no "Cases" public link. `/admin/login` page has no nav at all.

**Warning signs:**
Two `<header>` elements visible in the admin UI; root layout `+layout.server.ts` performs session checks that apply to all routes including public pages.

**Phase to address:** Unified navigation phase.

---

### Pitfall W12: Polling Race Condition — Stale Job State Shown After Browser Back Navigation

**What goes wrong:**
Operator starts a pipeline run, watches it complete, navigates away to the people editor, then presses Back. SvelteKit's back navigation may use the cached page data snapshot from when the page was first loaded (status="running"). The polling `$effect` checks `TERMINAL.has(data.job.status)` and, since the cached status is "running", starts polling again — triggering unnecessary `invalidateAll()` calls. Alternatively, if the back navigation restores the page with `status="completed"`, the `$effect` correctly skips polling, but a fresh data load would show the correct "completed" UI. The issue is that SvelteKit's navigation cache can restore stale data.

**Why it happens:**
SvelteKit's `invalidateAll()` inside a polling `$effect` causes the page data to refresh. But `$effect` only re-runs when its reactive dependencies change. If the back navigation restores stale `data.job.status = "running"` from cache, the effect re-registers the interval — potentially re-polling a job that finished hours ago.

**How to avoid:**
- Add `export const config = { isr: false };` or ensure no aggressive caching headers on the job detail page's `+page.server.ts` so back navigation triggers a fresh load.
- In the polling `$effect`, add a guard: if `data.job.status === 'completed'` (regardless of how the page was loaded), clear the interval immediately and do not start one.
- The existing terminal set already includes `'completed'` — verify it is checked before `setInterval` is called, not just as a condition to clear on the next interval tick.
- Explicitly call `invalidateAll()` once on page mount (via a `$effect` with no dependencies or a one-time flag) to force a fresh data load regardless of navigation type.

**Warning signs:**
Polling interval starts on back navigation to a completed job; `data.job.status` reads stale "running" on back; multiple simultaneous polling intervals visible in DevTools Network tab.

**Phase to address:** Ingestion flow polish phase.

---

### Pitfall W13: Ingestion Progress Indicator Shows Stale State When Polling Misses a Step Transition

**What goes wrong:**
Fire-and-poll pattern: client polls every 2.5 seconds via `invalidateAll()`. The server advances job state atomically on each poll (see `get_or_advance_job` in `admin_jobs.py`). If the client polls at T=0 (status=running, step=parse) and the step transitions to resolve at T=1.2s, the next poll at T=2.5s correctly shows step=resolve. However, if the server advances the step but the DB write is not yet visible to the SvelteKit server process's connection (read-after-write lag under PgBouncer transaction mode), the poll returns the old step. The progress indicator flickers or appears stuck, then jumps.

**Why it happens:**
PgBouncer transaction mode means each query gets a fresh connection from the pool. A `COMMIT` on connection A does not guarantee the next query on connection B immediately sees the committed data (dirty read window). The project already addresses this with `statement_cache_size=0` for prepared statements, but transaction-mode read-after-write lag is a separate concern.

**How to avoid:**
- The progress indicator must tolerate receiving the same status for multiple consecutive polls without treating it as an error. Show a "step in progress" state, not a "step stuck" state, until terminal.
- Use monotonically increasing data (e.g., a `progress_sequence` integer that increments on each step advance) to detect real changes versus identical polls.
- Add a minimum "spinner visible" duration: even if the status transitions quickly, show the in-progress indicator for at least 1 poll cycle to prevent the UI from blinking through states too fast to read.
- Do not derive "stuck" status from the number of identical poll results — the DB under PgBouncer may return the same status for 2–3 polls before the write is visible.

**Warning signs:**
UI shows "error" or "stuck" after 3 consecutive polls with the same status; progress jumps from step 1 to step 3 skipping step 2 in the UI display.

**Phase to address:** Ingestion flow polish phase.

---

### Pitfall W14: Appointing President/Party Fields Carry Editorial Risk If Not Treated as Factual Metadata

**What goes wrong:**
Appointing president and party are factual historical data for Supreme Court Justices (e.g., "George W. Bush / Republican"). If the UI labels these fields in a way that implies partisanship or political evaluation — or if data entry is inconsistent (sometimes "Republican", sometimes "GOP", sometimes "R") — the fields become editable political commentary rather than neutral attribution. This directly violates the apolitical framing constraint.

**Why it happens:**
The fields are factual and seem unambiguous, so developers enter them ad-hoc without a controlled vocabulary. Inconsistency accumulates as more Justices are added. Display of party affiliation next to spoken words implies an editorial framing.

**How to avoid:**
- Define a controlled vocabulary for `appointing_party` before writing any UI: use official party names only ("Democratic", "Republican", "Whig", "Federalist" for historical appointments). Do not use abbreviations, popular names, or slang.
- `appointing_president` is a free-text field but should be entered as the full official name (e.g., "George W. Bush", not "Bush 43" or "GWB").
- In the speaker popover (the only public-facing display of this data), show "Appointed by [president]" as a factual attribution. Do not show party affiliation in the public popover — it is not needed for understanding the oral argument and carries political interpretation risk.
- Party affiliation is admin-only metadata — useful for operator research, not for public display.
- Add a note in the admin form: "Use the Justice's official appointing president and party. Do not editorialize."

**Warning signs:**
`appointing_party` is a free-text field with no controlled vocabulary; party affiliation is displayed in the public speaker popover; different capitalizations or abbreviations for the same party in the people table.

**Phase to address:** People data model phase (appointing president/party fields).

---

### Pitfall W15: Image URL Stored as Spaces Key vs. Full Public URL — Inconsistent Derivation

**What goes wrong:**
The existing `photo_url` field on `people` stores a raw URL string (as entered by the operator in v1.1 people editor). After adding DO Spaces image upload, some rows will have `photo_url = "https://space-bucket.nyc3.digitaloceanspaces.com/people-images/123.jpg"` (full URL) while others have `photo_url = "https://some-external-url.com/photo.jpg"` (external URL, entered manually). If the image serving logic later changes (e.g., the bucket region changes or CDN is added), only the Spaces-uploaded images need updating, but the code cannot distinguish them from external URLs without parsing the domain.

**Why it happens:**
The upload service returns a full URL and the code stores it directly. Manual entries also store full URLs. The field type does not distinguish origin.

**How to avoid:**
- Store only the Spaces `key` (e.g., `people-images/123.jpg`) for Spaces-uploaded images, not the full URL. Derive the public URL at read time from `settings.do_spaces_endpoint + '/' + settings.do_spaces_bucket + '/' + key`. This makes bucket migration a config change, not a data migration.
- Keep a separate `photo_source` enum column: `"spaces"` | `"external"` | `"manual"`. The API returns the derived URL for `"spaces"` and the raw value for others.
- Alternatively, accept that `photo_url` is always a full URL and document the DO Spaces URL pattern so future migration can identify and update them via SQL (`UPDATE people SET photo_url = ... WHERE photo_url LIKE '%digitaloceanspaces.com%'`).
- If simplicity is preferred: store the full URL in `photo_url` as today, but namespace Spaces keys so they are identifiable: `people-images/{person_id}/{uuid}.jpg`.

**Warning signs:**
`people.photo_url` stores mixed formats with no `photo_source` discriminator; the codebase derives the Spaces URL in multiple places rather than one central helper.

**Phase to address:** People admin phase (image upload).

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Auto-split `full_name` into first/last in migration | Saves operator data-entry time | Corrupts names with titles, suffixes, hyphenations; hard to recover | Never — leave structured fields null, fill manually |
| Merge without full FK table enumeration | Faster to write | Leaves orphaned rows in omitted FK tables; source person delete raises IntegrityError | Never |
| Show party affiliation in public speaker popover | More information = more useful | Violates apolitical framing constraint; politically interpretable | Never for this project |
| Client-side fetch for popover data | Simple reactive code | Exposes FASTAPI_BASE_URL; requires CORS; SSR renders empty popover | Never — use server-side load |
| Store full Spaces URL instead of key in photo_url | One step simpler | Bucket/region/CDN changes require data migration | Acceptable if URL pattern is documented and searchable |
| Allow resolved_at to be set without metadata validation | Simplifies publish action | Publishes arguments with placeholder dockets; violates gate intent | Never |
| Disable inputs on published arguments (UI only, no server guard) | Faster to implement | Server still accepts writes; direct API call can modify post-publish fields | Never — server-side field-level guard required |

---

## Integration Gotchas

Common mistakes when connecting new v1.2 features to the existing system.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| boto3 image upload | Reusing `upload_pdf_to_spaces` verbatim without adding image-specific validation | Write a separate `upload_image_to_spaces` that adds magic byte check, size limit, and content-type enforcement |
| SvelteKit popover → FastAPI `/people/{id}` | Calling from browser via `PUBLIC_FASTAPI_BASE_URL` | Call from `+page.server.ts` load function using `FASTAPI_BASE_URL` (private); pass pre-loaded data as prop |
| Merge endpoint → FK tables | Running UPDATE statements on each FK table in separate transactions | One transaction; all FK updates; DELETE source at end; single commit |
| Root layout unified nav → admin auth | Adding session check to root layout server load | Root layout has no session check; `hooks.server.ts` remains the sole auth checkpoint |
| Name migration → speaker alias | Changing `full_name` values during migration breaks no aliases (aliases key on `person_id`) | Safe — but changing the text value in `full_name` does affect any display or search that uses it; leave `full_name` unchanged |
| Argument metadata edit → slug | Updating `case_name` triggers slug re-derivation | Slug must never change post-publish; update display name only, not slug |
| Progress polling → PgBouncer | Read-after-write seeing stale status under transaction-mode pool | Add tolerance for identical consecutive poll results; do not treat as stuck |

---

## Security Mistakes

v1.2-specific security issues.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Accepting non-image files in image upload | Stored XSS via script files served from Spaces bucket | Magic byte validation server-side; set Content-Type from verified format, not client claim |
| Spaces credentials in SvelteKit service | Secret keys exposed in client bundle or environment | All boto3 calls in FastAPI service only; SvelteKit proxies file bytes, never holds Spaces credentials |
| Merge endpoint accessible without admin auth | Any authenticated admin can delete people records | Merge endpoint is admin-only; verify X-Admin-Token dependency is on the router, not just on read endpoints |
| IDOR in merge: source_id from user input | Admin merges person 1 into person 2 when they meant person 3 | Show confirmation dialog with both person names before executing merge; merge is irreversible |
| Public speaker popover exposing bio/appointment data | Not a security risk per se, but a data exposure choice | Bio and appointment data are intentionally public-facing in the popover; confirm this is the intended scope before implementing |

---

## "Looks Done But Isn't" Checklist

- [ ] **People merge:** After merge, source person ID returns 404 from `GET /people/{id}` AND all four FK tables (utterances, speaker_alias, case_appearances, argument_participants) have zero rows for source_id
- [ ] **People merge (rollback):** When merge is interrupted mid-transfer, DB is unchanged (all-or-nothing) — verify by killing the process between FK table updates
- [ ] **Image upload:** After upload, `people.photo_url` is set AND the URL returns a 200 with the correct image (not a 404 or wrong content type)
- [ ] **Image upload (failure):** When Spaces upload raises ClientError, `people.photo_url` is unchanged and the operator sees a clear error message
- [ ] **Image validation:** Upload a PNG file renamed to `.jpg` — verify it is accepted (magic bytes match). Upload an HTML file renamed to `.jpg` — verify it is rejected.
- [ ] **Structured name migration:** After running migration, all existing people still appear correctly in the admin directory (no null display names); `full_name` is unchanged
- [ ] **Display name fallback:** A person with null `first_name`/`last_name` but populated `full_name` displays correctly in admin, public case list, and speaker popover
- [ ] **Speaker popover (SSR):** Hard-refreshing an argument page at `/cases/.../arguments/...` shows popover trigger avatars; opening a popover immediately shows content without a loading flash (data pre-loaded server-side)
- [ ] **Speaker popover (accessibility):** Tab to an avatar, press Enter — popover opens. Press Escape — popover closes. Focus returns to avatar button.
- [ ] **Argument metadata gate:** Attempt to set `resolved_at` via the publish action on an argument with `docket_number LIKE 'job-%'` — verify 422 is returned
- [ ] **Post-publish field immutability:** After `resolved_at` is set, attempt to submit the edit form changing `argued_date` — verify the server rejects it
- [ ] **Unified nav:** Public `/cases` page has no logout button. Admin pages have no "Cases" public nav link. `/admin/login` page has no nav at all.
- [ ] **Polling after back navigation:** Complete a pipeline job, navigate away, press Back — verify polling does not restart on the completed job

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Partial merge (FK tables inconsistently transferred) | MEDIUM | Identify which FK tables were partially updated via SQL audit; manually update remaining rows to target person_id; delete source person |
| Spaces URL written but file missing | LOW | Re-upload image via admin form; or set `photo_url = NULL` to restore initials fallback |
| Corrupted full_name from auto-split migration | HIGH | Restore from backup; or manually correct each person row via admin edit form |
| Published argument with placeholder docket | LOW | Set `resolved_at = NULL` via direct SQL (admin-only action); correct docket via edit form; re-publish |
| Unified nav double-render | LOW | Fix layout guard logic; redeploy |
| Polling stuck in loop on completed job | LOW | Page refresh resolves; fix polling terminal check in code |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| W1: Non-atomic merge | People admin (merge) | Interrupt merge mid-run → DB unchanged |
| W2: Partial FK transfer | People admin (merge) | Check all 4 FK tables after merge → 0 rows for source |
| W3: URL stored before upload confirms | People admin (image upload) | Mock Spaces error → photo_url unchanged |
| W4: Non-image file accepted | People admin (image upload) | Upload HTML as .jpg → rejected at magic bytes |
| W5: full_name corrupted by auto-split | People data model (name migration) | All existing people display correctly after migration |
| W6: Structured fields replace full_name in search | People data model (name migration) | Typeahead finds all existing people after migration |
| W7: Client-side popover fetch exposes FASTAPI_BASE_URL | Speaker popover | No `PUBLIC_FASTAPI_BASE_URL` in .svelte files; SSR renders popover content |
| W8: Popover not keyboard navigable | Speaker popover | Tab to avatar → Enter opens → Escape closes → focus returns |
| W9: resolved_at set before metadata complete | Argument metadata editing | Publish with placeholder docket → 422 |
| W10: Post-publish field mutation | Argument metadata editing | Edit argued_date after publish → server rejects |
| W11: Double nav from layout collision | Unified navigation | Admin pages show exactly one nav bar |
| W12: Polling restarts on back navigation | Ingestion flow polish | Back to completed job → no new polling interval |
| W13: Progress indicator stuck under PgBouncer lag | Ingestion flow polish | Multiple identical poll results → spinner, not error |
| W14: Appointing party as free-text editorial | People data model | Controlled vocabulary enforced; no party in public popover |
| W15: Inconsistent photo_url format | People admin (image upload) | Spaces-uploaded images distinguishable from external URLs |

---

## Critical Pitfalls — v1.1 Admin Interface (Preserved)

The full v1.1 pitfalls (V1–V15 covering auth, pipeline jobs, subprocess buffering, file uploads) are preserved below for reference. These are addressed in the existing codebase; new v1.2 phases should not re-introduce them.

---

### Pitfall V1: Infinite Redirect Loop When Login Page Is Not Excluded from Auth Guard

**What goes wrong:** `hooks.server.ts` redirects any unauthenticated request to `/admin/login`. If the guard does not explicitly exclude `/admin/login` itself, the login page request is unauthenticated → gets redirected to `/admin/login` → which is also unauthenticated → redirect → infinite 302 loop. The browser shows ERR_TOO_MANY_REDIRECTS.

**Why it happens:** Auth guards are written as "if not authenticated, redirect to login" without thinking about what happens when the redirect destination is itself guarded.

**How to avoid:** In `hooks.server.ts`, check `event.url.pathname` and return early for the login page before applying the auth check.

**Phase to address:** Auth foundation phase (first admin work).

---

### Pitfall V2: Session Cookie Missing HttpOnly or SameSite Attributes

**What goes wrong:** Session cookie is set without `httpOnly: true`, making it accessible via `document.cookie`. Any XSS vulnerability can exfiltrate the session token.

**How to avoid:** Always set session cookies with at minimum: `httpOnly: true`, `sameSite: 'lax'`, `path: '/'`, `secure: true`.

**Phase to address:** Auth foundation phase.

---

### Pitfall V3: Credentials Compared with == Instead of Timing-Safe Equality

**What goes wrong:** Username and password compared with `===` string equality — a timing attack can enumerate valid usernames.

**How to avoid:** Use `crypto.timingSafeEqual()` on Buffer representations of both strings.

**Phase to address:** Auth foundation phase.

---

### Pitfall V7: ORIGIN Environment Variable Not Set in Production — CSRF Errors at Login

**What goes wrong:** `adapter-node` requires `ORIGIN` to be set in production. Missing it causes every form submission to return a 403 CSRF error.

**How to avoid:** Set `ORIGIN=https://admin.scotuschat.com` in Digital Ocean App Platform env vars for the SvelteKit service. Also set `PROTOCOL_HEADER` and `HOST_HEADER`.

**Phase to address:** Deployment phase.

---

### Pitfall V10: BODY_SIZE_LIMIT Blocks PDF Uploads Silently at Default 512KB

**What goes wrong:** Uploads above 512KB fail with HTTP 413. SCOTUS transcript PDFs range from 200KB to 2MB.

**How to avoid:** Set `BODY_SIZE_LIMIT=10M` as an environment variable.

**Phase to address:** File upload phase.

---

### Pitfall V11: PDF MIME Type Not Validated Server-Side

**What goes wrong:** Upload handler trusts browser-supplied `Content-Type`. A non-PDF file named `.pdf` passes the check.

**How to avoid:** Check magic bytes (`%PDF-`). First 5 bytes must match.

**Phase to address:** File upload phase.

---

### Pitfall V14: Resumable Jobs Track Step Progress in Application Memory

**What goes wrong:** In-memory job state is lost on server restart (DO App Platform container cycling).

**How to avoid:** All resumable state lives in the DB. SvelteKit polls a DB-backed status endpoint.

**Phase to address:** Pipeline runner phase.

---

### Pitfall V15: Running Pipeline Step Directly in HTTP Request Handler

**What goes wrong:** Blocking `await subprocess.run()` in a server action ties the HTTP connection to the pipeline step duration (2–10 min for LLM parse). Browser and proxy timeouts kill the request.

**How to avoid:** Fire-and-forget: spawn subprocess, return immediately with `{ job_id }`, client polls status.

**Phase to address:** Pipeline runner phase.

---

## Critical Pitfalls — v1.0 Pipeline and Parsing (Preserved)

---

### Pitfall C1: Retrying Structural LLM Failures Treats Them as Transient

**What goes wrong:** Naive retry logic catches every LLM failure and resubmits the same prompt. Structural failures produce the same bad output on every retry.

**How to avoid:** Classify failures before retrying. HTTP 429/503 → retry. HTTP 400/422 / JSON parse error → stop. Never retry more than 2 times.

**Phase to address:** Pipeline Steps (Parse, Resolve).

---

### Pitfall C4: Speaker Resolution Fails on Surname-Only and Role-Only Labels

**What goes wrong:** Simple string matching fails for labels like "MR. BOPP", "GENERAL PRELOGAR", "CHIEF JUSTICE".

**How to avoid:** Use case metadata as resolution context. Maintain `speaker_alias` table. Below-confidence matches → `needs_review`.

**Phase to address:** Pipeline Step 3 (Resolve).

---

## Sources

**v1.2 research (2026-06-18):**
- Direct codebase inspection: `api/models/models.py` (FK table enumeration), `api/services/admin_people.py` (transaction patterns), `api/services/spaces.py` (boto3 upload), `app/src/routes/admin/+layout.svelte` and `/routes/+layout.svelte` (nav structure), `app/src/routes/admin/pipeline/[job_id]/+page.svelte` (polling pattern), `app/src/hooks.server.ts` (auth guard), `.planning/STATE.md` (v1.1 decisions log), `.planning/PROJECT.md` (constraints and key decisions)
- SQLAlchemy async transaction patterns — SQLAlchemy 2.0 docs
- SvelteKit layout hierarchy and server load functions — official docs
- WCAG 2.1 dialog/popover accessibility requirements — W3C
- DigitalOcean Spaces boto3 integration — DO documentation
- PostgreSQL FK constraint behavior under concurrent transactions

**v1.1 research (2026-06-15):**
- Protected Routes in SvelteKit — gebna.gg
- Session cookies in SvelteKit — Lucia Auth
- Node servers (adapter-node) — SvelteKit Official Docs

**v1.0 research (2026-06-11):**
- LLMs for Structured Data Extraction from PDFs — Unstract
- pdfplumber — GitHub

---
*Pitfalls research for: SCOTUS Chat v1.2 feature additions (people merge, image upload, name migration, speaker popover, metadata editing, unified nav, ingestion polish)*
*v1.2 researched: 2026-06-18*
*v1.1 researched: 2026-06-15*
*v1.0 researched: 2026-06-11*
