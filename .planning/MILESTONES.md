# Milestones

## v1.5 Admin Screens Cleanup (Shipped: 2026-07-12)

**Phases completed:** 10 phases, 55 plans, 110 tasks

**Key accomplishments:**

- Migration 0012 adds `unpublished` to the `argument_status` PG enum, creates the `argument_status_log` audit table, and backfills one row per argument using its current status — with matching ORM changes and schema test registration.
- Alembic migration 0013 adds `argument_participants.title` and moves appointment columns from `people` to `court_tenures`, with simultaneous ORM/schema/service/frontend cleanup eliminating every person-level `appointing_president` reference.
- TDD implementation of `_parse_toc_titles` + `extract_toc_data` in cover_extractor.py, and `_update_participant_titles` wired into parse.py via a single shared PDF open (D-12).
- Expanded ParseStats with bench/advocate/total speaker counts and cover_metadata fields; added question_number to MetadataUpdate and ArgumentDetail; wired get_job and update_argument_metadata service functions to populate and persist these fields.
- Reusable `ArgumentDetailsCard.svelte` with docket pill input, free-text question number, argued date, always-visible extracted hints, and action-prop-driven form — built in Svelte 5 Runes exclusively.
- Wired ArgumentDetailsCard into /admin/pipeline/[job_id] with saveJobMetadata action, savedValues/hints from load(), expanded parse stat card (8 fields, N/A fallbacks), and removal of the ingest Source file row.
- Closed all five Phase 23 UAT failures: removed two orphaned UI cards, fixed silent docket-clear bug via empty-string sentinel, froze question_number hint to null, and promoted docket instruction from placeholder to always-visible static label.
- Client-side max-count guard prevents a second docket pill from being added, making the server CR-02 rejection unreachable from normal UI interaction.
- 1. [Rule 1 - Bug] Corrupted em-dash in CR-02 comment blocked Edit match
- Admin jobs listing now returns the full pipeline run history newest-first, with incomplete filtering preserved.
- Extracted a standalone `DocketPillInput.svelte` Svelte 5 Runes component from `ArgumentDetailsCard.svelte`'s inline pill logic, ready for reuse on both the job detail page (Plan 03) and the New Run form (Plan 04).
- Refactored ArgumentDetailsCard.svelte to delegate docket pill add/remove/render logic to the shared DocketPillInput component, replacing ~90 lines of inline pill markup and state with a single keyed component instance.
- Typed FastAPI/Pydantic contract for run readiness, failed-step recovery, job-scoped mini create-person, and a new resolve-row side/title mutation that allows BENCH — all guarded by argument ownership derived from job_id.
- Typed FastAPI/Pydantic `ResolveRow` shape and job-scoped `GET /api/admin/jobs/{job_id}/resolve-rows` endpoint that returns every participant on a job's argument — including unresolved rows — with backend-derived tenure-based bench role, an explicit "Missing tenure" state, and advocate title/hint data.
- SvelteKit `+page.server.ts` load/action bridge for the Phase 25 job detail page — new readiness, failed-recovery, and resolve-row HTTP fetches feeding a computed `readonlyMode`, plus a `saveResolveRow` action and extended `addPerson`/`saveJobMetadata` actions — including two router endpoints (`GET .../readiness`, `GET .../failed-recovery`) that Plan 25-01 had built the service layer for but never exposed over HTTP.
- Four new Svelte 5 components (RunStatusCard, ResolveCard, FailedStepGuidance, CreatePersonPopover) plus a full `+page.svelte` recomposition that turns `/admin/pipeline/[id]` into a sibling-card operator workflow — run status first, resolve fully restructured with locked columns and side-first gating, failed recovery contextual to its step card, and Danger Zone unchanged and last.
- Rewrote publish/unpublish/delete/slug-freeze/list guards to key on Argument.status (not published_at), and started writing the ArgumentStatusLog audit trail on every transition.
- New `list_argument_speakers` service helper backing `ArgumentDetail.status_log` and `ArgumentDetail.speakers` (unified bench+advocate rows with utterance counts), plus a writable advocate `title` on the existing participant-update endpoint.
- Arguments list gains a three-state (Draft/Published/Unpublished) badge, a Created column, and status-driven row actions; RunStatusCard gains a neutral-grey "Archived" badge override for already-created pipeline runs.
- Rebuilt the `/admin/arguments/[id]` edit page around the three-state lifecycle: Status card with Created/Published dates and in-card Publish/Unpublish, a new timestamped Status history card, a unified Speakers section replacing the old Advocate Roles card and tenure-gap banners, and a Draft-only delete gate.
- Tightened delete_argument to a single positive DRAFT-only status gate and added an authoritative backend + explicit UI guard preventing an unresolved advocate's side from being silently persisted.
- Closed Phase 26 UAT gap (Test 18) by adding `is_archived` to `AdminJobResponse` via a `list_jobs()` outerjoin on `Argument`, and rendering the same grey "Archived" badge on `/admin/pipeline` that RunStatusCard already shows on the detail page.
- New Alembic migration 0016 adds people.birthdate; admin_people schemas gain per-tenure appointment fields, drop person-level Role, and add a two-field PersonCreateRequest
- `list_people`/`_missing_fields` now drive Bench/Advocate tabs, click-to-filter-by-missing-field, and per-tab columns (tenure coverage/gap, distinct argument count) with zero person-level Role and zero N+1 tenure queries
- `get_person_detail`/`update_person`/`_replace_tenures` now carry birthdate + per-tenure appointment data with zero person-level Role, and a new `POST /people` exposes a general `create_person` behind the standard admin-auth boundary
- `/admin/people/` is now a tabbed "People" directory (Bench default, Advocate via `?tab=`) with click-to-filter missing-field pills, a Bench-only tenure-gaps toggle, and a "Create person" entry point — all driven by Plan 27-02/27-03's `is_justice`/`missing`/`tenure_gaps` query-param contract
- `/admin/people/[id]` rebuilt into Identity/Photo/Biography/Person Type cards with a Bench/Advocate segmented toggle that slide-reveals Birth Date, disabled Death Date, and bordered Tenure Period sub-cards carrying free-text appointment fields — the Role field and its inline-creation machinery are gone entirely
- `/admin/people/new` — a new static route reusing the `/admin/people/[id]` editor's Identity/Person Type card structure, with a three-state (unselected) Bench/Advocate toggle, D-08 minimum validation, and a create action that POSTs to the general `POST /api/admin/people` endpoint before redirecting into the freshly-created person's editor
- Fixed zero-horizontal-padding defect on all four middle columns (Tenure coverage, Tenure gap, Argument count, Missing fields) in the /admin/people list table, restoring the codebase's 8px gutter convention.
- Closed UAT Gap 3 — PersonCreateRequest, create_person, and the SvelteKit create action now carry first_name/middle_name/last_name/name_suffix end-to-end, matching the [id] editor's save behavior.
- Converted the tenure sub-card's President's Party free-text input to a curated `<select>` (six historical US parties + blank + legacy-value fallback), reversing D-16 for that field only while leaving Appointing President free-text.
- Relocated the hidden birthdate/tenures save-form inputs outside the Bench/Advocate toggle's conditional, and completed the person-id-change reset effect to also re-derive tenureRows/nextKey — closing the two BLOCKER data-loss defects (CR-01, CR-02) that failed Phase 27's third verification pass.
- Replaced a self-referential `nextKey` $state read+write inside the person-id-change reset `$effect` with a write-only pattern using a local non-reactive counter, eliminating the infinite-loop regression introduced by the 27-10 CR-02 fix.
- Seven read-only COUNT/MAX/LIMIT aggregation service functions across three admin service files, plus a new Pydantic schema module and DB-gated test suite proving their I/O contracts against the corpus-scale (~7,800 row) dev database.
- Seven thin, resource-scoped GET routes on the existing `/api/admin` router exposing Plan 01's aggregation service functions, each literal route registered before its `{id}`-parameterized sibling and proven via a DB-gated test suite to resolve 200 (not 422).
- Rewrote `/admin/` from a placeholder into an at-a-glance operator dashboard: a new shared `StatCard.svelte` component, a sequential degrade-gracefully `load()` fetching all seven Plan 02 endpoints, and a `+page.svelte` rendering Needs Attention first, four neutral stat cards, then a visually-distinct Web Traffic placeholder — all from DESIGN-SYSTEM.md tokens with no mockup pass.
- External services require manual configuration.
- Three tested pure-Python modules -- streaming JSONL loader, typo-tolerant curated-vocabulary stage-direction detector, and a positive apolitical allowlist extractor -- that Plan 05's ConvoKit importer will orchestrate.
- A new `import-justices` CLI command upgrades the 13 pre-existing seed_aliases.py Person rows in place (is_justice=True + court_tenures) and creates the remaining historical justices, with idempotent check-before-insert dedup and auto dual-tenure handling for elevated justices.
- New `import-convokit` term-batched CLI command that idempotently scaffolds draft Case/Argument/CaseArgument/PipelineRun rows and resolves bench/advocate speakers into Person/ArgumentParticipant rows, entirely from conversations.json/cases.jsonl/speakers.json with a provably apolitical field allowlist.
- Streams ConvoKit utterances.jsonl one term at a time (never the full 900MB file) into Utterance rows with `\n` boundaries preserved verbatim, splits curated-vocabulary stage-direction markers (including inline mid-turn ones) into their own rows via the existing `detect_stage_direction` helper, and prints a per-term/rollup summary of created/skipped/matched/flagged/errored counts.
- Static /attributions page (Oyez.org/ConvoKit/SCDB credits + CC BY-NC 4.0 callout), a server-gated per-argument attribution note, TopNav entry point, and README credit — clearing the D-26 gate before any corpus-imported argument can go live
- ArgumentMetadataResponse and CaseItem now accept argued_date=None without a pydantic ValidationError, closing the BLOCKER gap where GET /arguments/{id}/utterances 500'd for historical corpus rows lacking a parseable transcript date.
- `pipeline/commands/import_convokit.py`'s single per-argument `PipelineRun` now writes `step="parse"` instead of `step="ingest"`, and a new end-to-end test proves `get_argument_with_utterances` now returns the actual, non-empty, correctly-attributed `Utterance` rows for a corpus-imported argument — closing the gap 29-07-PLAN.md's own regression test explicitly left open.
- Per-docket `question_number` derivation aligned with the DB's real `(source_docket, question_number)` UNIQUE constraint, plus a distinct `docket_question_conflict` counter and explicit `IntegrityError` safety net, so reargued cases and PDF-ingest-overlap dockets import instead of being silently dropped into `conversations_errored`.
- Corpus-imported arguments now start at `status=PIPELINE` (not `DRAFT`) and are paired with a HIT-shaped `PAUSED`/`RESOLVE` `AdminJob`, making the existing resolve→approve→publish workflow reachable for the ~7,800 historical corpus arguments for the first time.
- Derived `source: Literal["pdf","corpus"]` field on `AdminJobResponse`, computed at read time in both `list_jobs()` and `get_job()` via a duplication-safe `exists()` subquery on `PipelineRun.strategy == "convokit_import"` — no schema change.
- Quiet neutral "PDF"/"Corpus" provenance tag added to the /admin/pipeline/ list table, positioned between Status and Created, using only pre-existing color tokens.
- Term-1955 corpus batch (163 arguments) wiped via a scoped FK-safe transaction and re-imported through the 30-01-patched path, landing at status=PIPELINE with paired paused/resolve AdminJobs — closing the D-02 stored-data gap that left the batch permanently unpublishable and unreviewable.
- GET /api/admin/arguments now accepts an allow-list-guarded `?status=` query param that narrows results to a single status end-to-end, with a new segmented filter control, active-filter indicator, and filtered empty-state on the `/admin/arguments` list page (DASH-02).
- `/admin/arguments/[id]` now renders the shared `ArgumentDetailsCard.svelte` component as a true second consumer, with the old hand-rolled docket/date form reduced to a small "Case" identity card whose `?/save` action no longer touches `argued_date` (AEDIT-04).
- Migration 0019 makes arguments.question_number nullable (parity with argued_date); admin router now catches IntegrityError as a 409 instead of leaking a 500; CaseItem/ArgumentMetadataResponse schemas accept None

---

## v1.4 Admin Completeness (Shipped: 2026-07-02)

**Phases completed:** 4 phases (18–21), 13 plans
**Timeline:** 2026-06-29 → 2026-07-02 (3 days)
**Files changed:** 94 | **Net lines:** +11,903 / -330
**Closeout type:** verified_closeout (10/10 requirements shipped; 2 stale todos closed at milestone)

**Key accomplishments:**

- `is_justice` boolean migration (0010) with tenure-based backfill; people editor conditionally renders bench-only sections (Role, Court Tenure, Appointment) based on `is_justice`; Justice badge in directory listing (PEOPLE-05/06/07)
- Duplicate argument prevention — DB UNIQUE constraint on `(source_docket, question_number)` via migration 0011; preflight UI check before pipeline run start with duplicate warning banner (PIPE-25)
- Argument metadata prefill — `cover_extractor` extracts docket from PDF cover; `cover_metadata` JSONB written at parse; job detail Argument Metadata card with auto-populated fields operator can override (PIPE-26)
- Live pipeline status — unconditional 1s `$effect`/`invalidateAll()` polling on list page; detail-page step card polling human-verified live (PIPE-23/24)
- Argument delete with FK-ordered cascade (Utterance → PipelineRun → ArgumentParticipant → CaseArgument → NULL AdminJob.argument_id → Argument); published guard returns 409; two-step inline confirm UI (ADMIN-01)
- Pipeline run delete — `delete_job` removes admin_job row only; argument and its utterances survive; two-step confirm UI with redirect to /admin/pipeline (ADMIN-02)
- Unified admin nav — `AdminSubNav` component + `TopNav variant=public` in admin layout; dead `variant=admin` TopNav branch removed; NAV-02 gap closed via Plan 21-04 (NAV-02)

---

## v1.3 Speaker Accuracy + Pipeline Confidence (Shipped: 2026-06-29)

**Phases completed:** 3 phases (15–17), 9 plans
**Timeline:** 2026-06-25 → 2026-06-29 (5 days)
**Commits:** 84 | **Files changed:** 73 | **Net lines:** +11,791 / -177
**Closeout type:** override_closeout (1 acknowledged item — Phase 11 human_needed verification, v1.2 carry-over)

**Key accomplishments:**

- Tenure-aware speaker popover — Justices now show the role they held at the argument's argued_date via `_tenure_role_name()` date-range lookup; D-14 fallback to most-recent tenure; advocates show per-argument side (PETITIONER/RESPONDENT/AMICUS) via ADVOCATE_LABEL_MAP (ROLE-01, ROLE-02)
- Per-argument advocate role editor — IDOR-guarded PATCH `/api/admin/arguments/{id}/participants/{pid}` with advocate role dropdowns on both argument edit page and pipeline job detail UI; each save is isolated per argument (ROLE-03)
- Argument status lifecycle — new argument_status enum (pipeline/draft/published) via Alembic migration 0008 + ArgumentStatusEnum ORM; approve action transitions pipeline→draft and unlocks public visibility gate
- Cover-page metadata extraction — `cover_extractor.py` extracts argued_date and case_name from PDF transcript via regex; parse step writes both to DB after dry-run gate without blocking parse on extraction failure (PARSE-01)
- TOC advocate side detection — `_update_participant_sides()` maps ESQ. name pairs from transcript TOC to PETITIONER/RESPONDENT/AMICUS and seeds argument_participants.side after step 7b (PARSE-02)
- Pipeline UI polish — Ingest source filename (migration 0009), Parse stat cards (utterance count, speaker count, extracted metadata), same-origin SvelteKit PDF proxy keeping ADMIN_TOKEN server-side throughout (PIPE-21, PIPE-22)

---

## v1.2 Pre-Launch Polish (Shipped: 2026-06-25)

**Phases completed:** 6 phases (9–14), 21 plans
**Timeline:** 2026-06-18 → 2026-06-25 (7 days)

**Key accomplishments:**

- Structured people schema — Alembic migration 0006 adds six nullable name-part and appointing president columns to `people`; `_derive_full_name` preserves `full_name` as resolution anchor; edit form extended with name-parts grid and Appointment section (PEOP-01, PEOP-02)
- Unified navigation — shared `TopNav.svelte` (variant prop) wired to both root and admin layouts; single component, no duplicate markup; admin auth guard stays in layout (NAV-01)
- Argument metadata editing — migration 0007 adds `published_at` to arguments; public visibility gate swapped from `resolved_at` to `published_at`; admin edit page with case title/docket/date + read-only after publish; `ArgumentUpdate` allow-list prevents mass-assignment (ARG-01, ARG-02)
- People admin tooling — photo upload to DO Spaces or URL, orphan-safe delete returning 409 when FK rows exist, merge transferring all 4 FK tables in single `db.begin()` transaction with preview count (PADM-01–04)
- Ingestion flow polish — `lastKnownStep` $state fallback for null-transition step badges (PIPE-18); custom Svelte 5 Runes combobox replacing native datalist (PIPE-19); incomplete filter toggle with empty state (PIPE-20)
- Speaker popover card — `SpeakerPopoverEntry` schema + `get_argument_speakers` service (no N+1 lazy loads); bits-ui ^2.18.1 for Svelte 5-native headless popover; `appointing_president_party` excluded at schema level (apolitical constraint) (PUB-01–03)

---

## v1.1 Operator Admin Interface (Shipped: 2026-06-18)

**Phases completed:** 4 phases (5–8), 19 plans, 33 tasks
**Timeline:** 2026-06-15 → 2026-06-18 (4 days)
**Commits:** 155 (v1.0 → v1.1) | **Files changed:** 120 | **Net lines:** +23,277 / -1,410

**Key accomplishments:**

- Operator admin area secured end-to-end — HMAC stateless session cookie (`node:crypto`), `hooks.server.ts` sole auth checkpoint, dark-theme login page with constant-time credential validation, logout action, AUTH-01/02/03 all verified
- FastAPI admin router at `/api/admin` with router-level `X-Admin-Token` dependency, admin_jobs service layer (Pydantic schemas, atomic step-advance guards, boto3 DO Spaces upload, detached subprocess spawn)
- Three pipeline commands (ingest, parse, resolve) made job-aware via `--job-id`: each writes RUNNING/COMPLETED/FAILED to admin_jobs; resolve replaces terminal prompts with discrepancy JSONB + PAUSED state
- Pipeline Runner UI — two-mode start page (URL/file upload), live step cards polling every 2.5s, auto-advance on clean resolve, pauses for discrepancy review; fire-and-poll pattern survives browser close (PIPE-17)
- Discrepancy review workflow — HIT rows pre-confirmed with single Change button, MISS rows with Correct/Override; people-backed typeahead (full roster via server-loaded data); inline add-new-person via `use:enhance` for reliable devalue deserialization
- `arguments.resolved_at` visibility gate — cases hidden from `/cases/` until resolve completes; no placeholder metadata leaks publicly (Alembic migration 0004)
- People directory at `/admin/people` — filterable by incomplete metadata, edit form with bio text / photo URL / tenure dates / role create (Alembic migration 0005); per-argument participant review after pipeline run

---

## v1.0 MVP (Shipped: 2026-06-15)

**Phases completed:** 4 phases (1–4), 15 plans, 76 commits
**Timeline:** 2026-06-11 → 2026-06-15 (4 days)
**Lines of code:** ~4,895 (TypeScript + Svelte + Python) across 146 files

**Key accomplishments:**

- SvelteKit 2 + Svelte 5 Runes scaffold with adapter-node, final route `/cases/[slug]/arguments/[id]` from day one, stub ChatBubble/StageDirection components, Python dependencies, pytest config, PowerShell dev startup script
- 10-table PostgreSQL schema via hand-written Alembic migration — people/roles/tenures/cases/arguments/case_arguments/appearances/participants/pipeline_runs/utterances — supporting M:M consolidated dockets and idempotent re-runs via `pipeline_run_id`
- Async pipeline CLI: `ingest` (SSRF-validated PDF download, immutable storage) + `parse` (pdfplumber extraction, rule-based state machine, instructor/tenacity LLM corrective pass)
- Speaker resolution: `speaker_alias` table + `resolve` step + `GET /people/{id}` API; ChatBubble displays resolved names with role labels and raw-label fallback
- FastAPI `GET /arguments/{id}/utterances` with PgBouncer-safe async engine (`statement_cache_size=0` in `connect_args`), max-pipeline-run-id filtering, and full chat layout in SvelteKit
- Full browseable UI: SSR case list, slug routing with 307 redirect, CSS Grid argument layout, avatar initials circles, SectionRail scroll-spy
- WCAG 2.1 AA accessibility: global focus ring, ARIA article semantics, HTML5 landmarks on all pages, MobileNavBar for narrow viewports; `#475569` eliminated from entire `app/src/` tree

**Known deferred items at close:** 4 (see STATE.md Deferred Items — stale verification status markers; human UAT completed per commits)

---
