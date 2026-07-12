# Phase 26: Arguments Admin - Context

**Gathered:** 2026-07-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Rebuild the arguments admin screens (`/admin/arguments/` and `/admin/arguments/[id]`) around the three-state argument lifecycle (Draft / Published / Unpublished) introduced by Phase 22's schema work. This phase delivers:

1. Arguments list filtered to Draft/Published/Unpublished only (pipeline-status arguments stay on the pipeline job detail page), with distinct status badges and a "Created" column.
2. An argument edit page Status card (current badge, created date, published date) plus a full status log showing every timestamped transition.
3. A Speakers section replacing the old "Advocate Roles" card and tenure-gap-warning banners — all participants listed with utterance counts; advocates get an editable role + title; bench rows show tenure-derived role or "Missing tenure" + edit link.
4. Functional Publish / Unpublish / re-Publish transitions (Draft → Published, Published → Unpublished, Unpublished → Published).
5. Danger Zone delete, updated to gate on the new three-state model instead of the legacy `published_at` null-check.

Folded into this phase's scope (see Folded Todos below): the pipeline run "Archived" status badge on `/admin/pipeline/[id]`'s `RunStatusCard`, even though it touches a different status field (`AdminJob`/run status, not `Argument.status`).

This phase does not touch People Admin (Phase 27) or the Dashboard (Phase 28).

</domain>

<decisions>
## Implementation Decisions

### Publish / Unpublish UX
- **D-01:** Unpublish stays one-click, no confirmation step — matches today's Publish behavior. No Danger-Zone-style two-step confirm for this action.
- **D-02:** On re-Publish (Unpublished → Published), the Status card's "Published" field shows only the current/latest `published_at` timestamp (simple re-stamp, matching existing `publish_argument` behavior). The full status log is the source of complete history, including any original first-publish date — no separate "first published" column or field is needed.

### Delete Gate
- **D-03:** Delete is blocked whenever `Argument.status` is `PUBLISHED` or `UNPUBLISHED` — only `DRAFT` (never published) can be deleted. This replaces the current `published_at IS NOT NULL` check in `admin_arguments.delete_argument` and the corresponding frontend disabled-state logic, since an Unpublished argument was once public and should keep its data/audit trail rather than become deletable again once `published_at` is cleared.

### Speakers Section
- **D-04:** Do not reuse ResolveCard's full interaction model (auto-match, discrepancies, create-person popover, side-gating). Instead, extend the **current** arguments/[id] page's existing "Advocate Roles" card pattern: per-row `<select>` + explicit Save button + `use:enhance` (inline save, no full page reload, no navigation).
- **D-05:** Extend that existing pattern with: a Title `<input>` per advocate row, a per-participant utterance count column, and read-only bench rows (tenure-derived role via the same date-window logic as Phase 25's `_bench_role_and_missing_tenure`, or "Missing tenure" + edit-person link when no tenure covers `argued_date`).
- **D-06:** Advocate title fields show the extracted TOC hint (same "Extracted: X" pattern as Phase 23/25) when the current value differs from or is unset relative to `ArgumentParticipant.title` as originally written by parse-time TOC extraction.
- **D-07:** This section replaces the current "Advocate Roles" card AND the `tenure_gap_warnings` banner block entirely — one unified Speakers section covers what those two disjoint UI pieces did separately today.

### Status Log Writes
- **D-08:** Phase 26 adds the ArgumentStatusLog write for the "Created" transition, which is currently missing entirely (only pre-Phase-22 arguments have a "Created" row, from the one-time migration backfill). Without this, every argument created going forward has an empty/incomplete status log, breaking the log display this phase adds. The write goes into `admin_jobs.approve_job` (the PIPELINE → DRAFT transition), even though that function lives in a file `admin_jobs.py` Phase 25 owns.
- **D-09:** Phase 26 also adds the ArgumentStatusLog writes for Publish, Unpublish, and re-Publish, at the corresponding points in `admin_arguments.publish_argument` / `unpublish_argument`.
- **D-10 (Claude's discretion):** Whether the four log-write call sites (`approve_job`, `publish_argument`, `unpublish_argument`, and re-Publish) share one small helper function or each write their own inline insert is left to the planner, based on what fits the existing `admin_jobs.py` / `admin_arguments.py` module boundaries best.

### Claude's Discretion
- Exact placement/naming of the shared status-log-write helper (or inline duplication), per D-10.
- Visual treatment details for the Speakers section (spacing, column order) beyond what D-04/D-05 lock in.

### Folded Todos
- **Add Archived pipeline run status** (`.planning/todos/pending/2026-07-07-add-archived-pipeline-run-status.md`) — Surfaced during Phase 25 UAT. Once a pipeline run's argument has been created, `RunStatusCard.svelte`'s `already_created` state currently reuses a generic badge; the user wants a distinct grey/neutral "Archived" badge specifically for runs whose linked argument now exists (permanently read-only), separate from `completed` (pipeline-processing-outcome). Touches `app/src/lib/components/RunStatusCard.svelte` and `api/services/admin_jobs.py` (`get_job_readiness` / `RunReadiness`). This is a different status field (`AdminJob`/run readiness state) than `Argument.status`, which is the rest of this phase's focus — the user explicitly chose to fold it in anyway rather than leave it pending.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope and Requirements
- `.planning/ROADMAP.md` — Phase 26 goal, success criteria, and phase boundary (§ "Phase 26: Arguments Admin").
- `.planning/REQUIREMENTS.md` — ALIST-02, ALIST-03, ALIST-04, AEDIT-01, AEDIT-05, AEDIT-06, AEDIT-07, AEDIT-08, AEDIT-09 (this phase's requirements); ALIST-01, AEDIT-02, AEDIT-03, AEDIT-04 (already delivered by Phases 22/23 — read for the schema/component contracts this phase builds on).

### Prior Decisions
- `.planning/phases/22-schema-foundations/22-CONTEXT.md` — Defines the `unpublished` enum value, `argument_status_log` table schema (id, argument_id, status, created_at — no previous_status/notes/triggered_by), and the `argument_participants.title` column this phase edits.
- `.planning/phases/25-pipeline-job-detail-page/25-CONTEXT.md` — Locks the `_bench_role_and_missing_tenure` tenure-role computation this phase's Speakers section reuses, and the read-only-after-argument-created model for the pipeline job detail page (relevant to the folded Archived-status todo).
- `.planning/phases/23-shared-argument-details-component/23-CONTEXT.md` — Locks `ArgumentDetailsCard` behavior (unaffected by this phase, but shares the same edit page).
- `.planning/todos/pending/2026-07-07-add-archived-pipeline-run-status.md` — Folded-todo source (see Decisions § Folded Todos).

### Existing Arguments Admin UI (Phase 26's main edit targets)
- `app/src/routes/admin/arguments/+page.svelte` — List page; current two-state (draft/published) badge logic and publish/unpublish row actions to be replaced with three-state logic.
- `app/src/routes/admin/arguments/+page.server.ts` — List page load/actions.
- `app/src/routes/admin/arguments/[id]/+page.svelte` — Edit page; contains the current Status card (Card 2), Advocate Roles card (Card 3, D-04's reuse target), tenure-gap-warning banners (D-07's removal target), Publish/Unpublish buttons, and Danger Zone delete gate (D-03's update target).
- `app/src/routes/admin/arguments/[id]/+page.server.ts` — Edit page load/actions.

### Backend/API
- `api/services/admin_arguments.py` — `list_arguments` (D-02 status filter currently missing UNPUBLISHED — bug to fix), `publish_argument`/`unpublish_argument` (D-08/D-09 log-write targets, currently only touch `published_at` not `status`), `delete_argument` (D-03's gate to update), `update_argument` (slug-freeze logic currently keyed on `published_at IS NULL` — must also freeze for UNPUBLISHED per ALIST-01's "slug locked" definition), `update_participant_side`.
- `api/services/admin_jobs.py` — `approve_job` (D-08's "Created" log-write target, PIPELINE → DRAFT transition), `get_job_readiness` (folded-todo target).
- `api/services/admin_people.py` — `_bench_role_and_missing_tenure` (lines ~564–584) and `list_resolve_rows_for_job` (lines ~587+) — direct analog for the Speakers section's bench-row tenure computation (D-05).
- `api/models/models.py` — `Argument.status` (`ArgumentStatusEnum`: PIPELINE/DRAFT/PUBLISHED/UNPUBLISHED), `ArgumentStatusLog`, `ArgumentParticipant.title`, `CourtTenure`.
- `api/routers/admin.py` — `/arguments`, `/arguments/{id}`, `/arguments/{id}/publish`, `/arguments/{id}/unpublish`, `/arguments/{id}/participants/{participant_id}` routes.

### Reusable Frontend Component
- `app/src/lib/components/ResolveCard.svelte` — NOT reused per D-04, but read for the utterance-count and tenure-role rendering conventions if useful as a secondary reference.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The current "Advocate Roles" card in `arguments/[id]/+page.svelte` (lines ~275–366) is the direct template for the new Speakers section per D-04 — same per-row `<select>` + Save button + `use:enhance` mechanism, just extended with Title input and utterance count.
- `admin_people._bench_role_and_missing_tenure` (no fallback to most-recent tenure, unlike the public speaker popover's `_tenure_role_name`) is the exact function to reuse for bench-row role display (D-05) — it already returns `(bench_role, missing_tenure)` from a date-window check against `argued_date`.
- `admin_people.list_resolve_rows_for_job` shows the query pattern for pre-fetching tenures for multiple bench participants in one query (avoids N+1) — same shape needed for the Speakers section's bench rows.
- `admin_jobs.get_job_detail`'s per-job utterance-count query (lines ~140–147, scoped by `pipeline_run_id`) is NOT directly reusable — Speakers needs a per-participant count via `Utterance.argument_id` + `Utterance.person_id` (see `speakers.get_argument_speakers` for the `Utterance.person_id`/`argument_id` linking pattern), not a per-job aggregate.

### Established Patterns
- Svelte 5 Runes only: `$props`, `$state`, `$derived`, `$effect`; no legacy `export let` or `$:` blocks.
- Admin UI uses inline dark-theme CSS with card backgrounds `#1e293b`, borders `#334155`, primary text `#e2e8f0`, muted text `#94a3b8`.
- SvelteKit form actions + `use:enhance` is the established inline-save pattern (no full page reload).
- Every SQLAlchemy `update()`/`delete()` statement uses `.execution_options(synchronize_session=False)` (project-wide critical guard).
- Dates parsed with `datetime.date.fromisoformat()`; malformed input raises `ValueError` → router maps to 422.

### Integration Points — Bugs/Gaps Found During Scouting (not user decisions — planner must address)
- `admin_arguments.list_arguments` filters `Argument.status.in_([DRAFT, PUBLISHED])` — **excludes UNPUBLISHED**, contradicting ALIST-02's requirement that the list show all three states. Must add `ArgumentStatusEnum.UNPUBLISHED` to this filter.
- `admin_arguments.publish_argument`/`unpublish_argument` only touch `published_at`, never `Argument.status` — must be updated to also write `status = PUBLISHED`/`UNPUBLISHED` (and handle re-Publish from UNPUBLISHED, which the current `unpublish_argument`'s "already not published" guard doesn't anticipate).
- `admin_arguments.update_argument`'s slug-freeze check (`if argument.published_at is None: re-derive slug`) will incorrectly UN-freeze the slug once an argument is unpublished (since `published_at` goes back to NULL) — contradicts ALIST-01's "Unpublished ... slug locked". Must key slug-freeze on `status != DRAFT` instead.
- `admin_arguments.delete_argument`'s gate (`if argument.published_at is not None: return False`) has the same problem relative to D-03 — must key on `status in (PUBLISHED, UNPUBLISHED)` instead.
- No `ArgumentStatusLog` row is ever written outside the one-time Phase 22 migration backfill — see D-08/D-09.
- The frontend list/edit page badge helpers (`badgeStyle`/`badgeLabel` in both `+page.svelte` files) only handle `published`/`draft`/fallback-to-pipeline — need an `unpublished` branch (distinct color per ALIST-03).
- `Argument` has no `created_at` column; `resolved_at` (stamped at PIPELINE → DRAFT transition in `approve_job`) is the established "created" timestamp — same value the Phase 22 migration backfill used (`COALESCE(resolved_at, CURRENT_TIMESTAMP)`). Reuse `resolved_at` for ALIST-04's "Created" column rather than adding a new column.

</code_context>

<specifics>
## Specific Ideas

- The Speakers section is explicitly NOT a re-skin of ResolveCard — it should feel like the simpler, already-settled-argument context it lives in, extending the existing Advocate Roles card rather than importing Resolve's pause/discrepancy/auto-match complexity.
- "Extracted: X" hint styling/copy should match Phase 23/25's established extracted-hint convention wherever it already appears in the codebase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope (the one adjacent-scope item, the Archived pipeline run status todo, was explicitly folded in rather than deferred; see Decisions § Folded Todos).

</deferred>

---

*Phase: 26-Arguments Admin*
*Context gathered: 2026-07-07*
