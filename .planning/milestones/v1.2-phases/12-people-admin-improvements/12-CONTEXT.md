# Phase 12: People Admin Improvements - Context

**Gathered:** 2026-06-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 12 delivers three new admin operations on the person edit page (`/admin/people/[id]`):

1. **Profile photo management** — replaces the standalone `photo_url` text input with a combined upload/URL widget (PADM-01). Dual-path storage: Spaces if configured, local `data/uploads/people/` fallback.
2. **Delete orphaned record** — "Delete person" button on the edit page, enabled only when the person has no utterances, aliases, or appearances (PADM-02).
3. **Merge duplicate people** — "Merge into another person" section on the edit page; operator picks a target, sees an inline count preview (utterances / aliases / appearances), then confirms (PADM-03, PADM-04). Atomic transfer of all 4 FK tables; source deleted; redirect to target edit page.

Out of scope: image crop UI, DO Spaces ACL configuration, photo format decision (deferred), bulk operations, post-publish speaker attribution editing.

</domain>

<decisions>
## Implementation Decisions

### Photo Management (PADM-01)

- **D-01:** Photo upload follows the PDF dual-path pattern: if DO Spaces is configured (`do_spaces_bucket` is set), upload to Spaces and store the full public URL in `people.photo_url`. If Spaces is not configured (local dev), save to `data/uploads/people/` and serve via a FastAPI `StaticFiles` mount or a dedicated serve endpoint; `photo_url` stores the accessible path.
- **D-02:** The "Bio & Photo" section on `/admin/people/[id]` replaces the standalone `photo_url` text input with a **combined widget**: "Upload file" tab and "Enter URL" tab. Shows a preview of the current photo (if `photo_url` is set) above the tabs.
- **D-03:** If both a file and a URL are submitted, file upload takes precedence. URL-only submit (Enter URL tab) updates `photo_url` directly without touching Spaces.

### Delete (PADM-02)

- **D-04:** Delete is only surfaced from the person edit page. No delete action in the directory listing.
- **D-05:** "Delete person" button at the bottom of `/admin/people/[id]`. **Enabled only** when the person has no rows in any of the 4 FK tables (utterances, speaker_alias, case_appearances, argument_participants). Rendered as disabled with a tooltip when the person cannot be deleted.
- **D-06:** The API endpoint checks orphan status server-side before deleting — not reliant on the client-side disabled state (prevents bypass).
- **D-07:** After successful delete, redirect to `/admin/people`.

### Merge (PADM-03, PADM-04)

- **D-08:** Merge is initiated from the source person's edit page. A "Merge into another person" section appears at the bottom of `/admin/people/[id]`.
- **D-09:** The operator picks a target person from a picker (searchable dropdown or list of all people — Claude's discretion on picker style). After selecting a target, the page shows an inline confirmation section:
  - Heading: "Merging [source name] into [target name]"
  - Transfer counts: N utterances, N aliases, N appearances
  - "Confirm merge" button
- **D-10:** Merge executes atomically in a single DB transaction — transfer all 4 FK tables (utterances → `person_id`, speaker_alias → `person_id`, case_appearances → `person_id`, argument_participants → `person_id`) then delete the source person. No commit between steps.
- **D-11:** After successful merge, redirect to `/admin/people/[target_id]` (the target's edit page). The source no longer exists.

### Claude's Discretion

- Target-picker UI for merge (searchable `<select>` vs. a list rendered inline)
- Disabled delete button tooltip wording (e.g., "This person has N utterances and cannot be deleted")
- Whether the merge section is always visible on the edit page or revealed by clicking a "Merge this person" expand button
- Photo preview styling in the combined upload widget
- Whether the count preview is fetched eagerly on target selection or only shown after a "Check counts" step

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Scope
- `.planning/REQUIREMENTS.md` §People Admin — PADM-01, PADM-02, PADM-03, PADM-04 (4 requirements this phase closes)
- `.planning/ROADMAP.md` §Phase 12 — Goal and 5 success criteria (must all be TRUE)
- `.planning/PROJECT.md` §Key Constraints — Alembic sole DDL authority; `Base.metadata.create_all` is forbidden

### Database & ORM
- `api/models/models.py` — `Person`, `Utterance` (person_id FK), `SpeakerAlias` (person_id FK), `CaseAppearance` (person_id FK), `ArgumentParticipant` (person_id FK); confirm FK column names before writing merge UPDATE statements
- Current most-recent migration: `alembic/versions/0007_add_published_at_to_arguments.py` (from Phase 11) — any new migration (e.g., for StaticFiles serving) chains from this

### API & Service Layer
- `api/services/admin_people.py` — `update_person()`, `get_person_detail()`, `list_people()` patterns; new service functions (`upload_photo`, `get_merge_counts`, `merge_people`, `delete_person_if_orphan`) follow the same async/dict-return pattern
- `api/services/spaces.py` — `get_spaces_client()` + `upload_pdf_to_spaces()`; `upload_photo_to_spaces()` mirrors this exactly; check `api/core/config.py` for the Spaces settings fields
- `api/schemas/admin_people.py` — `PersonUpdate`, `PersonDetail`; new schemas for merge request (`MergeRequest`) and delete response go here
- `api/routers/admin.py` — existing admin router; new endpoints: `POST /api/admin/people/{id}/photo`, `DELETE /api/admin/people/{id}`, `GET /api/admin/people/{id}/merge-preview?target_id=N`, `POST /api/admin/people/{id}/merge`

### SvelteKit Admin UI
- `app/src/routes/admin/people/[id]/+page.svelte` — existing edit form; Phase 12 restructures Bio & Photo section and appends merge/delete sections at the bottom
- `app/src/routes/admin/people/[id]/+page.server.ts` — existing load + save actions; new `photo`, `merge`, `delete` form actions added
- `app/src/routes/admin/people/+page.svelte` — directory listing reference (no changes expected)
- `app/src/routes/admin/people/+page.server.ts` — directory load (no changes expected)

### Prior Phase Foundation (MUST READ)
- `.planning/phases/09-people-data-model-migration/09-CONTEXT.md` — edit form section structure, dark theme tokens, SvelteKit form-action patterns, `use:enhance` mandatory
- `.planning/phases/11-argument-metadata-editing/11-CONTEXT.md` — patterns for multi-action form pages; how edit + publish actions coexist on one page
- `.planning/STATE.md` — accumulated context; blockers section includes DO Spaces ACL note and photo_url format note (both deferred but referenced here for awareness)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `api/services/spaces.py` `get_spaces_client()` / `upload_pdf_to_spaces()` — mirror directly for `upload_photo_to_spaces(key, image_bytes, content_type)`
- `api/services/admin_people.py` `update_person()` — the PATCH pattern (fetch by id → mutate → commit → return detail); merge and delete follow the same fetch-guard structure
- Phase 7 local fallback path: `data/uploads/{job.id}.pdf` → photo mirror: `data/uploads/people/{person_id}.{ext}`
- Admin dark theme tokens: `#0f1117` bg, `#1e293b` card, `#334155` border, `#94a3b8` body text, `#93c5fd` accent blue — all new UI sections must match

### Established Patterns
- **SvelteKit form actions + `use:enhance`**: all admin form submissions use progressive enhancement — mandatory
- **Multiple named actions**: `export const actions = { save: ..., photo: ..., merge: ..., delete: ... }` in `+page.server.ts` (same page, multiple actions) — see Phase 11 edit page for multi-action example
- **Server-only env vars**: `FASTAPI_BASE_URL` from `$env/static/private` — never `PUBLIC_`
- **FastAPI router → service → schema layering**: router calls service, service returns dicts, router wraps with Pydantic
- **`.execution_options(synchronize_session=False)`**: every UPDATE/DELETE statement in service layer must include this (established in admin_jobs.py)

### Integration Points
- `api/models/models.py` — verify FK column names on the 4 transfer tables before writing merge logic (utterances.person_id, speaker_alias.person_id, case_appearances.person_id, argument_participants.person_id)
- `api/core/config.py` — `do_spaces_bucket` presence check gates the Spaces vs local upload path (D-01)
- `app/src/routes/admin/people/[id]/+page.svelte` — Bio & Photo section restructured; bottom of page gains two new action sections (Merge, Delete)
- `data/uploads/people/` — new subdirectory for local photo storage fallback; must be created on demand (mkdir -p pattern)

</code_context>

<specifics>
## Specific Ideas

- **Merge count fetch**: `GET /api/admin/people/{source_id}/merge-preview?target_id={N}` returns `{utterances: N, aliases: N, appearances: N, argument_participants: N}`. Fetch this when the operator selects a target — before showing the "Confirm merge" button. The inline preview reads: "Merging [source] into [target] will transfer: N utterances, N aliases, N appearances."
- **Pillow for image validation**: `Pillow >=11.0` (from Phase 9 research) — validate file is a real image and get dimensions before uploading. Reject non-image uploads with a 422. Optional: cap max dimensions (e.g., 2000px) to avoid storing huge originals.
- **Atomic merge transaction**: use `async with db.begin()` wrapping all 4 UPDATE statements + DELETE. If any step fails the whole transaction rolls back — no partial-merge state.
- **Orphan check for delete**: `SELECT COUNT(*) FROM utterances WHERE person_id=?` + same for alias/appearances/participants — if any count > 0, return 409 Conflict from the API; the frontend also disables the button upfront.

</specifics>

<deferred>
## Deferred Ideas

- **DO Spaces ACL setup** — enable bucket-level public access for the `people/` prefix; needed before production deployment but not a Phase 12 code blocker. Noted in STATE.md blockers.
- **Image crop UI** — explicitly out of scope per REQUIREMENTS.md; `object-fit: cover` handles display
- **photo_url format decision** — the dual-path approach (D-01) resolves this naturally per environment; no explicit schema migration needed
- **Bulk merge or bulk delete** — single-record operations sufficient for v1.2

</deferred>

---

*Phase: 12-people-admin-improvements*
*Context gathered: 2026-06-23*
