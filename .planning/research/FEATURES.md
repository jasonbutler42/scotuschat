# Feature Research

**Domain:** Admin tooling + public content site — SCOTUS oral argument viewer (v1.2 polish)
**Researched:** 2026-06-18
**Confidence:** HIGH

## Context

This is a subsequent milestone. v1.0 shipped the public chat view; v1.1 shipped the admin pipeline runner and people editor. v1.2 adds six feature clusters to complete the admin tooling and enrich the public experience before deployment. The features below are analyzed in terms of expected behaviors, UX patterns, and data considerations for this specific codebase — not greenfield design.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features the operator expects to work correctly. Missing or broken = the admin panel feels unfinished.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Unified top navigation | Every admin tool has a single consistent nav; toggling between admin and public by URL feels broken without it | LOW | SvelteKit root `+layout.svelte` already exists. Pattern: root layout renders nav that reads `page.url.pathname` to conditionally show admin vs. public links. Auth state check via `$page.data.user` or `locals.user`. No new routes. |
| Argument metadata editing (pre-resolve) | Pipeline produces a title from the PDF filename; operators must correct it before the argument goes public | MEDIUM | Gate is `resolved_at IS NULL` — form must be disabled once resolved. Fields: `case_name` on `cases` table, `docket_number`, `argued_date` on `arguments`. Multi-case (consolidated dockets) complicates: editing the lead case name may not propagate to joined dockets. Scope: edit only the primary case row's name and the argument date/docket for now. |
| Ingestion flow polish (progress, typeahead, incomplete toggle) | Fire-and-poll status display already exists but has known gaps in progress indicators | MEDIUM | Three sub-items: (1) fix step progress indicators to reflect actual polling state accurately, (2) typeahead for URL input (autocomplete from past supremecourt.gov URLs stored in admin_jobs), (3) "incomplete" toggle in jobs list to filter to paused/failed/needs_review jobs. All within existing `/admin/pipeline` route. |
| Structured name fields | Legal names have suffix (Jr., III) and middle names; a single `full_name` field makes display logic fragile and prevents proper sorting | MEDIUM | Alembic migration required. New columns on `people`: `first_name`, `last_name`, `middle_name` (nullable), `name_suffix` (nullable). Keep `full_name` as the stored display name — do not make it computed/generated in the DB, derive it in the service layer on save. Existing data migration: parse existing `full_name` strings via simple heuristic (split on space, last token = last name). Flag records that fail the heuristic for manual review. |
| Appointing president + party field | Factual data point on Justice records; required by the speaker popover feature | LOW | Two new columns on `people`: `appointing_president` (VARCHAR), `appointing_party` (VARCHAR — "Republican"/"Democrat"). Not computed; operator-entered. Aligns with apolitical constraint: factual attribution, not commentary. Only meaningful for Justices but schema stores on all people (nullable). Alembic migration required alongside structured name columns. |
| People delete (orphaned records) | Resolve step creates stub person records that may never be linked; no delete path exists today | LOW | Must guard: block delete if any `utterances.person_id` or `argument_participants.person_id` references the row. Show referencing count before confirming. Hard delete only when counts = 0. Cascade: also delete `court_tenures`, `case_appearances`, `speaker_alias` rows for that person. |

### Differentiators (Competitive Advantage)

Features that make the public viewer meaningfully better than reading raw PDFs.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Speaker popover card (bench only) | Clicking a Justice's avatar reveals who they are, when they served, and who appointed them — zero friction for non-legal readers | MEDIUM | Trigger: click on avatar in `ChatBubble`. Scope: bench side only (`side === 'BENCH'`). Content: photo (if available), full name, role, tenure dates, appointing president + party. Pattern: `@floating-ui/dom` for positioning — autoPlacement middleware handles viewport edges. Dismiss: click outside, Escape key, or second click on same avatar. No hover — touch devices need click. A11y: `popover` role or `dialog` role, focus trap on open, return focus on close. Data gap: `GET /people/{id}` currently returns only `id`, `full_name`, `role_name`; needs tenure + appointing fields added. |
| Image upload to DO Spaces | Operators currently paste URLs; uploading actual photos keeps them in the admin without leaving the page | MEDIUM | Recommended pattern: server-side relay via SvelteKit form action — receives multipart, streams to Spaces via boto3 (simpler than presigned URLs for internal admin; `api/services/spaces.py` already exists). UX: file input + image preview via `URL.createObjectURL` on file select, accept=".jpg,.jpeg,.png,.webp", max 5MB client-side validation, upload executes on form submit (not on file select — avoids orphaned Spaces objects from abandoned edits). `BODY_SIZE_LIMIT=10M` env var required on DO App Platform (already a known deployment requirement). Store resulting Spaces public URL in `photo_url`. |
| People merge (utterance transfer) | Resolve step may create duplicate person records under slightly different labels; merge transfers all utterances then deletes the source | HIGH | Highest-complexity feature in the milestone. Data transfer scope: `utterances.person_id`, `argument_participants.person_id`, `case_appearances.person_id`, `speaker_alias.person_id` — all UPDATE from source_id to target_id in a single DB transaction. Then DELETE source person row. Alias conflict: if both source and target have an alias for the same `normalized_label`, drop the source's conflicting alias before transferring the rest. UX pattern: (1) select source person (the duplicate), (2) select target person (canonical), (3) preview screen shows transfer counts, (4) confirm with irreversibility warning, (5) redirect to target record after success. New endpoint: `POST /api/admin/people/{source_id}/merge-into/{target_id}`. |

### Anti-Features (Commonly Requested, Often Problematic)

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Hover popover for speaker card | Hover feels natural on desktop | Touch devices have no hover state; hover over dense text content triggers accidental popovers while reading | Click-to-open popover — intentional trigger, works on touch + desktop, simpler focus management |
| Image crop in upload flow | Uploaded photos may not be square | Canvas-based crop UI is complex to implement cross-browser, adds JS payload, is not blocking for v1.2 | Upload as-is; use CSS `object-fit: cover` on avatar circles for non-square images; crop deferred to v1.3 |
| Field-level merge control (choose per-field which record wins) | Source may have better bio or more complete tenure data | Adds comparison UI with per-field radio buttons; multiplies implementation complexity 3-4x | Target-wins merge; operator manually edits target record fields after merge if needed |
| Metadata editing after resolve | Operator realizes title/date is wrong after the argument is published | Post-resolve edits are unexpected to users with bookmarks; no undo path exists | Gate editing to `resolved_at IS NULL` strictly; if post-resolve correction is needed, operator resets `resolved_at` to null via direct DB access (not a v1.2 UI feature) |
| AI-suggested appointing president | Automatically populate from Justice name | Violates apolitical hard constraint — LLM-derived political data is editorial even when factually correct | Operator manually enters from an authoritative source (oyez.org); one-time data entry per Justice (~9 active, ~20 retired) |
| Bulk people import via CSV | Seems efficient for populating Justice records | Adds CSV parsing, column mapping, validation, partial-failure handling; for ~9 active Justices this is over-engineering | Single-record edit form is adequate; import deferred to v2+ |

---

## Feature Dependencies

```
People data model migration (structured names + appointing fields)
    └──required before──> Speaker popover card (needs appointing_president/party columns populated)
    └──required before──> People admin edit form changes (new fields in schema + form)
    └──independent of──> Image upload (photo_url already exists)

Speaker popover card
    └──requires──> Extended GET /people/{id} response (tenure + appointing fields)
    └──requires──> People data model migration

People merge
    └──requires──> People directory (already shipped — needed for source/target selection)
    └──conflict risk──> People delete (after merge, source is deleted; delete endpoint logic overlaps)

People delete
    └──requires──> Referencing-count check (utterances + argument_participants counts)
    └──independent of──> People merge (can be built separately)

Image upload
    └──requires──> DO Spaces service (already exists: api/services/spaces.py)
    └──enhances──> Speaker popover card (popover only shows photo if photo_url is populated)

Argument metadata editing
    └──requires──> resolved_at IS NULL gate logic (already on arguments table)
    └──independent of all people features

Unified navigation
    └──independent of all other v1.2 features
    └──prerequisite for──> acceptable admin UX at launch perception
```

### Dependency Notes

- **People data model migration must ship before speaker popover card.** The popover needs `appointing_president` and `appointing_party` to exist in the DB and be returned by the API.
- **Image upload is independent of structured names.** `photo_url` already exists. Upload is a UI/API enhancement to the existing edit form, no schema change required.
- **People merge is the riskiest feature and should ship last** in the people admin cluster, after delete and image upload are verified stable.
- **Unified navigation is the lowest complexity, highest perceived polish feature.** Build first — it makes every subsequent admin feature feel properly finished.

---

## MVP Definition

### Launch With (v1.2)

All six feature clusters are required for the milestone goal: admin tooling and public experience sufficient for deployment.

- [x] Unified top navigation — prerequisite for "done" perception
- [x] Ingestion flow polish — existing gaps block smooth operator use
- [x] Argument metadata editing — no path exists today to correct pipeline-derived titles
- [x] People data model (structured names + appointing president/party) — unblocks popover; enables proper name display
- [x] People admin improvements (image upload + delete + merge) — completes people management workflow
- [x] Speaker popover card — primary public-facing differentiator for this milestone

### Add After Validation (v1.3)

- [ ] Image crop in upload flow — CSS `object-fit` covers most cases in v1.2
- [ ] Post-resolve metadata editing with explicit reset action — needs UX design for "unresolved" flow
- [ ] Bulk people import — only relevant when corpus exceeds ~50 people

### Future Consideration (v2+)

- [ ] Automated enrichment from Oyez/FJC API — manual editor ships in v1.1; automation deferred
- [ ] Speaker statistics across arguments — apolitical constraint makes this high-risk
- [ ] Public speaker profile pages — architecturally supported; defer until public demand is clear

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Unified navigation | HIGH | LOW | P1 |
| Ingestion flow polish | HIGH | MEDIUM | P1 |
| Argument metadata editing | HIGH | MEDIUM | P1 |
| People data model migration | HIGH (unblocks popover) | MEDIUM | P1 |
| Appointing president/party fields | HIGH (popover content) | LOW | P1 |
| People delete | MEDIUM | LOW | P1 |
| Image upload | MEDIUM | MEDIUM | P1 |
| Speaker popover card | HIGH | MEDIUM | P1 |
| People merge | MEDIUM | HIGH | P1 |
| Image crop | LOW | HIGH | P3 |

**Priority key:**
- P1: Required for v1.2 milestone
- P2: Should add, not blocking deployment
- P3: Nice to have, future milestone

---

## Existing API Gaps to Close

| Gap | Required By | Current State | Action Needed |
|-----|-------------|---------------|---------------|
| `GET /people/{id}` returns only `id, full_name, role_name` | Speaker popover card | Missing tenure, appointing_president, appointing_party | Extend `PersonResponse` schema after data model migration |
| No argument metadata PATCH endpoint | Argument metadata editing | Does not exist | `PATCH /api/admin/arguments/{id}` + service method |
| No photo upload endpoint | Image upload | Does not exist | `POST /api/admin/people/{id}/upload-photo` multipart handler |
| No merge endpoint | People merge | Does not exist | `POST /api/admin/people/{source_id}/merge-into/{target_id}` |
| No people delete endpoint | People delete | Does not exist | `DELETE /api/admin/people/{id}` with referencing-count guard |
| `PersonUpdate` schema lacks new fields | Structured names + appointing | Has only `full_name, role_id, bio_text, photo_url, tenures` | Add `first_name, last_name, middle_name, name_suffix, appointing_president, appointing_party` post-migration |

---

## Behavioral Specifications

### Speaker Popover Card

- Appears anchored to the clicked avatar, positioned above or below based on viewport space (Floating UI `autoPlacement` middleware)
- Width: 260–320px; never clips outside viewport on mobile
- Content sections: photo thumbnail (with initials fallback), name + role label, tenure date range formatted as "YYYY–present" or "YYYY–YYYY", appointing president + party in a neutral factual line
- One popover visible at a time — opening a second closes the first
- Dismissed by: clicking outside, pressing Escape, or clicking the same avatar again
- No action buttons needed for v1.2 (read-only)
- A11y: ARIA `dialog` role, focus trap when open, focus returns to avatar button on close
- Implementation entry point: `ChatBubble.svelte` — add click handler on the avatar `<div>`, convert it to a `<button>`, render popover via `{#if showPopover}` with `@floating-ui/dom` for position computation

### Record Merge Workflow

1. Operator selects "Merge" from a person's row in the people directory
2. Second screen: search field to select target (canonical) person
3. Preview screen: counts of rows to transfer — "N utterances, M participants, K aliases, J appearances"
4. Confirm button with warning: "This cannot be undone. [Source name] will be permanently deleted."
5. Atomic DB transaction: UPDATE all FK references, DELETE source row
6. On success: redirect to target person's edit page; success flash message
7. On conflict (alias collision): silently drop conflicting source aliases, proceed with non-conflicting ones
8. No partial commits — if transaction fails, show error, no data changed

### Argument Metadata Editing

- Form renders only when `resolved_at IS NULL`; if resolved, show read-only display with note: "Locked — argument is published. Editing requires reopening the pipeline."
- Editable fields: `argued_date`, lead case `case_name`, lead case `docket_number`
- For consolidated arguments: display all linked cases but only allow editing the lead case's name; secondary docket numbers shown as read-only
- Save validates: date format, docket number matches `##-####` pattern
- No publish/unpublish toggle in this form — `resolved_at` is set only by the resolve pipeline step

### Image Upload

- File input accepts `.jpg`, `.jpeg`, `.png`, `.webp` only
- Client-side validation before submit: reject files > 5MB with an inline error message
- `URL.createObjectURL` renders preview in a small image element (48×48px) immediately after file selection
- Upload executes as part of the main save form submission (not a separate async upload on file-select)
- Server streams file bytes to DO Spaces via boto3 `put_object`; returns the public Spaces URL
- Updates `photo_url` field in the person record and re-renders the preview with the saved URL
- Error states: file type rejected (client), file too large (client), upload failed (server) — all surface inline below the file input

---

## Sources

- [Floating UI — positioning library](https://floating-ui.com/)
- [floating-ui-svelte examples](https://floating-ui-svelte.vercel.app/examples/popovers)
- [Shadcn Hover Card pattern](https://ui.shadcn.com/docs/components/radix/hover-card)
- [CiviCRM deduping and merging workflow](https://docs.civicrm.org/user/en/latest/common-workflows/deduping-and-merging/)
- [Talend Cloud Data Stewardship — merging tasks](https://help.qlik.com/talend/en-US/data-stewardship-user-guide/Cloud/handling-merging-tasks-to-deduplicate-records)
- [Image upload UX patterns — uxpatterns.dev](https://uxpatterns.dev/patterns/media/image-upload)
- [Uploadcare file uploader UX best practices](https://uploadcare.com/blog/file-uploader-ux-best-practices/)
- [FastAPI + presigned URL upload pattern](https://medium.com/@sanmugamsanjai98/secure-file-uploads-made-simple-mastering-s3-presigned-urls-with-react-and-fastapi-258a8f874e97)
- [boto3 presigned URLs reference](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html)
- [DatoCMS draft/published system](https://www.datocms.com/docs/general-concepts/draft-published)
- [Craft CMS publish vs save UX discussion](https://github.com/craftcms/cms/issues/7543)
- [Adobe XDM person name data type](https://experienceleague.adobe.com/en/docs/project-aim-demo/xdm/data-types/person-name)
- [SvelteKit advanced layouts — joyofcode](https://joyofcode.xyz/sveltekit-advanced-layouts)

---
*Feature research for: SCOTUS Chat v1.2 — admin tooling and public experience polish*
*Researched: 2026-06-18*
