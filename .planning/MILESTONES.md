# Milestones

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
