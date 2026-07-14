# SCOTUS Chat

## What This Is

A website that displays Supreme Court oral arguments as a chat-style interface — formatted like a group conversation between the Justices and whoever is arguing before the Court. An offline operator-only pipeline ingests transcript PDFs, parses utterances via LLM, and resolves raw speaker labels to named people records. An operator admin web interface drives the full pipeline from the browser — uploading PDFs, monitoring step progress, reviewing speaker aliases, and editing people metadata — without touching the CLI. The goal is accessibility: making dense legal transcripts easy to follow for anyone who wants to understand who said what, without editorial framing or political commentary.

## Core Value

Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.

## Current State

**v1.5 Admin Screens Cleanup — SHIPPED 2026-07-12.** All 7 admin screens (`/admin/`, `/admin/pipeline/`, `/admin/pipeline/[id]`, `/admin/arguments/`, `/admin/arguments/[id]`, `/admin/people/`, `/admin/people/[id]`) audited and refined: three-state argument lifecycle with status log, shared Argument Details component, redesigned pipeline list/detail pages, People admin with Bench/Advocate tabs and per-tenure appointment data, and a real dashboard. Also absorbed an out-of-band addition mid-milestone: bulk historical corpus import (~7,800 arguments, 1955–2019, from Cornell ConvoKit) routed through the same resolve/publish workflow as PDF ingest. Full details: `.planning/milestones/v1.5-ROADMAP.md`, `.planning/milestones/v1.5-REQUIREMENTS.md`.

**v1.6 Backlog Cleanup — 4/10 phases complete.** Phases 31, 32, 33, and 40 are verified. Phase 40 adds a clean-checkout local-stack guide for PostgreSQL, FastAPI, and SvelteKit, including a disposable Windows portable-PostgreSQL walkthrough with real admin-session validation.

## Current Milestone: v1.6 Backlog Cleanup

**Goal:** Close out the 10 promoted backlog phases (31–40) — data-integrity fixes, small operator UX improvements, and two open design questions — before starting anything new.

**Target features:**
- Phase 31: Audit stale DB-gated test fixtures + fix real data leakage into shared dev DB (escalated risk)
- Phase 32: Fix CourtTenure FK bookkeeping gap in merge/delete person paths
- Phase 33: `update_argument_metadata` unique-constraint guard (409 instead of 500)
- Phase 34: Blank case_name/docket_number validation (prevents slug/dedup corruption)
- Phase 35: `rerun_job` never spawns ingest for locally-uploaded jobs
- Phase 36: Click-to-copy design pattern for extracted values
- Phase 37: Tenure Seat — Chief/Associate toggle vs. numbered seats (design decision during discuss-phase)
- Phase 38: Full Name vs. name-parts rethink (design decision during discuss-phase)
- Phase 39: Bench popover — additional context data for Justices
- Phase 40: README — how to start the local stack

Deployment (DEPLOY-01, DEPLOY-03) and the remaining 999.x backlog (999.2–999.8) are explicitly out of scope for this milestone.

## Requirements

### Validated

- ✓ Full PostgreSQL schema (10 tables) via Alembic migrations — v1.0 (INFRA-01)
- ✓ Schema handles consolidated arguments with multiple docket numbers — v1.0 (INFRA-02)
- ✓ Development environment runs fully locally — v1.0 (INFRA-03)
- ✓ Ingest step: download PDF, create case/argument/pipeline_run records — v1.0 (PIPE-01)
- ✓ Raw PDFs immutable after ingest — v1.0 (PIPE-02)
- ✓ Parse step: pdfplumber + LLM extracts utterances, writes with person_id=null — v1.0 (PIPE-03)
- ✓ Parse records pipeline_run_id and strategy on each utterance row — v1.0 (PIPE-04)
- ✓ Parse correctly classifies stage directions — v1.0 (PIPE-05)
- ✓ Parse classifies LLM failures as transient vs. structural; max 2 retries — v1.0 (PIPE-06)
- ✓ Resolve step: matches raw speaker labels to people records via alias table — v1.0 (PIPE-07)
- ✓ speaker_alias table seeded for role-only and surname-only labels — v1.0 (PIPE-08)
- ✓ Resolve gates low-confidence matches as needs_review; never auto-commits ambiguous matches — v1.0 (PIPE-09)
- ✓ pipeline_run status machine enforced: pending → running → completed | failed | needs_review — v1.0 (PIPE-10)
- ✓ Re-running any step produces new rows linked to new pipeline_run_id — v1.0 (PIPE-11)
- ✓ GET /arguments/{id}/utterances — returns ordered utterances with speaker attribution — v1.0 (API-01)
- ✓ GET /cases — returns list of available cases with basic metadata — v1.0 (API-02)
- ✓ GET /people/{id} — returns person record (name, role) — v1.0 (API-03)
- ✓ Two-sided chat UI: bench left, advocates right — v1.0 (UI-01)
- ✓ Each utterance shows speaker name and role label — v1.0 (UI-02)
- ✓ Stage directions render as distinct visual component — v1.0 (UI-03)
- ✓ Argument header with case name, docket, date, and speaker roster — v1.0 (UI-04)
- ✓ Speaker avatars with styled initials fallback — v1.0 (UI-05)
- ✓ Arguments at stable shareable URLs, SSR on hard refresh — v1.0 (UI-06)
- ✓ Case list lets user browse and navigate to any argument — v1.0 (UI-07)
- ✓ Section navigation rail with scroll-spy — v1.0 (UI-08)
- ✓ All UI passes WCAG 2.1 AA color contrast (4.5:1) — v1.0 (A11Y-01)
- ✓ Fully keyboard navigable — v1.0 (A11Y-02)
- ✓ Speaker side differentiation by layout position only — v1.0 (A11Y-03)
- ✓ Focus managed correctly for interactive elements — v1.0 (A11Y-04)
- ✓ Operator can log in at `/admin/login` with username+password (env vars); invalid credentials show an error — v1.1 (AUTH-01)
- ✓ All `/admin/*` routes redirect unauthenticated requests to `/admin/login` before content renders — v1.1 (AUTH-02)
- ✓ Operator can log out and session is invalidated immediately — v1.1 (AUTH-03)
- ✓ Operator can start a new pipeline run by entering a supremecourt.gov PDF URL — v1.1 (PIPE-12)
- ✓ Operator can start a new pipeline run by uploading a local PDF file — v1.1 (PIPE-13)
- ✓ Running pipeline displays step status (Ingest / Parse / Resolve) and auto-advances when each step completes without discrepancies — v1.1 (PIPE-14)
- ✓ Pipeline pauses after resolve when discrepancies exist and displays them for operator review before continuing — v1.1 (PIPE-15)
- ✓ Operator can confirm or correct speaker alias matches during resolve review; confirmed matches saved to alias table — v1.1 (PIPE-16)
- ✓ Pipeline job state persisted to DB; operator can close the browser and resume an in-progress run — v1.1 (PIPE-17)
- ✓ Operator can view all people in a directory listing — v1.1 (PEOPLE-01)
- ✓ Operator can filter the directory to show only people with one or more missing metadata fields — v1.1 (PEOPLE-02)
- ✓ Operator can edit a person's name, role, bio text, photo URL, and tenure dates — v1.1 (PEOPLE-03)
- ✓ After a pipeline run, operator can review resolved participants and fill in missing metadata inline — v1.1 (PEOPLE-04)
- ✓ Structured name parts (first/last/middle/suffix) and appointing president on person records — v1.2 (PEOP-01, PEOP-02)
- ✓ Unified top navigation shared by admin and public pages — v1.2 (NAV-01)
- ✓ Argument metadata editing (case title, docket, date) before publish; read-only after — v1.2 (ARG-01, ARG-02)
- ✓ Photo upload/URL, orphan delete, and merge for people admin — v1.2 (PADM-01–04)
- ✓ Pipeline step badge accuracy, alias typeahead, incomplete filter toggle — v1.2 (PIPE-18–20)
- ✓ Speaker popover card on argument page — v1.2 (PUB-01–03)
- ✓ Justice role in popover determined by tenure date-range lookup at argument date — v1.3 (ROLE-01)
- ✓ Per-argument advocate roles stored and displayed (petitioner/respondent/amicus) — v1.3 (ROLE-02)
- ✓ Operator can edit advocate role per argument without affecting other arguments — v1.3 (ROLE-03)
- ✓ Parse step extracts case name and argued date from transcript PDF cover page — v1.3 (PARSE-01)
- ✓ Parse step detects advocate sides from TOC and seeds argument_participants.side — v1.3 (PARSE-02)
- ✓ Pipeline stage stat cards (Ingest: source filename; Parse: utterance/speaker counts + metadata) — v1.3 (PIPE-21)
- ✓ Operator can access source PDF from pipeline job detail page — v1.3 (PIPE-22)
- ✓ `is_justice` boolean + Alembic migration + backfill; people editor conditionally shows bench-only sections; operator can toggle flag — v1.4 (PEOPLE-05, PEOPLE-06, PEOPLE-07)
- ✓ Duplicate argument prevention: DB UNIQUE constraint + preflight UI warning before run start — v1.4 (PIPE-25)
- ✓ Argument metadata pre-populated from cover extraction; operator can override before publish — v1.4 (PIPE-26)
- ✓ Pipeline list page and job detail page update status live without manual reload — v1.4 (PIPE-23, PIPE-24)
- ✓ Argument delete from admin UI (confirmation + published guard) — v1.4 (ADMIN-01)
- ✓ Pipeline run delete from admin UI (confirmation; argument survives) — v1.4 (ADMIN-02)
- ✓ Admin nav unified with public nav: AdminSubNav + TopNav variant=public in admin layout — v1.4 (NAV-02)
- ✓ Pipeline list page: free-text question number, shared docket pill input, full runs table, incomplete toggle, compound status badges — v1.5 (PLIST-01–05)
- ✓ Pipeline job detail page: run status card (not-ready/ready/already-created), restructured resolve card with locked columns and side-first gating, step-specific failed guidance, job-scoped mini create-person popover, no floating action buttons — v1.5 (PJOB-01–23)
- ✓ Arguments admin: three-state (Draft/Published/Unpublished) list badges + Created column, edit page Status card with full status log, unified Speakers section (advocates: role/title/inline save; bench: tenure-derived role or Missing-tenure guard), Draft-only delete gate — v1.5 (ALIST-02/03/04, AEDIT-01/02/05/06/07/08/09)
- ✓ People admin: Bench/Advocate tabs with per-tab columns and click-to-filter missing-field pills, tenure-gaps filter, "Create person" button before any argument exists; person editor consolidates Justice-specific fields into a collapsible Justice Details card with per-tenure appointment data (birthdate, seat, appointed-by, president's party dropdown, start/end date) — v1.5 (PDIR-01/02/03/04/06/07, PEDIT-01/02/03/05/06/07/09/11/12); PDIR-05 reworked (D-04), PEDIT-04/PEDIT-08 superseded (D-10, argument-level role replaces person-level Role field)
- ✓ Bulk historical corpus import: `import-justices` + `import-convokit` CLI subcommands bulk-seed ~7,800 historical oral arguments (1955–2019) from the Cornell ConvoKit dataset directly into cases/arguments/utterances/people/court_tenures, bypassing PDF download and LLM parsing; per-docket `question_number` dedup aligned to the DB's real uniqueness constraint (gap-closure CR-01), stage-direction row-splitting, apolitical field stripping, Attributions/License page — v1.5 (CORPUS-01–11), validated in Phase 29
- ✓ Corpus import resolve workflow: corpus-imported arguments now land at `status=PIPELINE` paired with a PAUSED/RESOLVE `AdminJob` (previously stuck permanently at `status=DRAFT`, unpublishable) — reuses the existing PDF-ingest resolve/approve/publish machinery unchanged; `source: "pdf"|"corpus"` tag on the Pipeline list distinguishes job origin; the pre-existing term-1955 batch (163 arguments, imported before this feature existed) was brought into the corrected state via a scoped wipe-and-rerun operator runbook (no committed migration) — v1.5 (PJOB-01/02/14/15/18/19/20/21, reused family), validated in Phase 30
- ✓ `/admin/arguments/[id]` reuses the shared `ArgumentDetailsCard` component instead of a hand-rolled duplicate form (Case card + ArgumentDetailsCard card, `saveArgumentDetails` action reusing `PATCH /metadata`); dashboard Draft/Published/Unpublished status CTAs actually filter `/admin/arguments` via a threaded `?status=` param + segmented control + active-filter indicator; `arguments.question_number` migrated nullable (migration 0019, parity with `argued_date`), closing a UAT-found gap where blanking it threw an unhandled 500 instead of persisting NULL — v1.5 (AEDIT-04, DASH-02), gap-closure Phase 30.1, milestone-audit-found
- ✓ Dedicated `scotus_test` Postgres DB + session-boundary auto-reset isolates the full pytest suite from the shared dev DB; a `pytest_sessionfinish` hook fails any run that changes shared-dev-DB `Person`/`Argument` row counts, closing the gap where production service functions that commit internally (`create_person_for_job`, `publish_argument`, `run_import_convokit`) could leak synthetic rows past a test's own rollback; ~28 previously-stale DB-gated fixtures across `pipeline/tests`/`api/tests` repaired against the current schema; one-time reviewed cleanup script removed 81 already-leaked rows (25 duplicate `Person`, 56 orphaned `Argument`) from the shared dev DB under explicit operator authorization — v1.6 (TEST-01, TEST-02), validated in Phase 31
- ✓ Clean-checkout local-stack README covers PostgreSQL, FastAPI, and SvelteKit end to end with split private environment contracts, cross-platform commands, safe troubleshooting, optional integrations, and a verified Windows portable-PostgreSQL admin-session walkthrough — v1.6 (DOCS-01), validated in Phase 40

### Active

- [ ] Application deployed to Digital Ocean App Platform (SvelteKit + FastAPI as separate services, managed Postgres) (DEPLOY-01)
- [ ] Continuous deployment from GitHub main branch (DEPLOY-03)

### Out of Scope

- Automated enrich pipeline step (Oyez/FJC API) — manual people editor shipped in v1.1 serves this use case; automated enrichment remains deferred (ENRICH-01/02/03)
- Citation pipeline step — not in scope for v1.1; schema already supports it (CITE-01/02)
- Audio playback — Oyez owns the distribution relationship; link to Oyez instead
- AI-generated case summaries — violates apolitical framing constraint; hard no
- Cross-case justice statistics — politically interpretable; contradicts non-editorial principle
- Topic / subject tagging — non-partisan framing requires careful thought; explicitly deferred
- Pre-2000 transcript parsing — different format requires separate strategy; pipeline modularity accommodates later
- User accounts or public contributions — read-only product by design
- Monetization — not a driving goal; not excluded for future milestones
- Real-time argument streaming — arguments are historical documents; no live ingestion use case
- Citation resolution (linking raw text to case records) — schema supports it; deferred post-v2

## Context

- Shipped v1.5 — 362 files changed (91 code files: +17,308 / -2,473 lines), 10 phases (22–30, 30.1), 55 plans, 10 days (2026-07-02 → 2026-07-12). Includes the historical corpus import (Phase 29/30), which was scoped in mid-milestone and is not part of the original v1.5 requirement set.
- Shipped v1.4 — 94 files changed, +11,903 / -330 lines (Phases 18–21, 3 days 2026-06-29 → 2026-07-02)
- Shipped v1.0–v1.4 cumulatively; tech stack finalized: SvelteKit 2.x + Svelte 5 Runes (frontend), FastAPI 0.115+ + Pydantic v2 (API), PostgreSQL 16 + SQLAlchemy 2.0 async + Alembic (database), Python 3.12 + pdfplumber + Anthropic SDK + instructor + tenacity (pipeline)
- Alembic migrations through 0011: schema includes argument_status enum (pipeline/draft/published), SideEnum (PETITIONER/RESPONDENT/AMICUS), original_filename on admin_jobs, is_justice on people, source_docket + cover_metadata JSONB + argued_date nullable on arguments, UNIQUE(source_docket, question_number)
- Admin interface: full operator self-service — HMAC auth, DO Spaces PDFs, pipeline runner with live status polling, full people admin (photo/merge/delete/is_justice), argument editing + delete, pipeline run delete, speaker role assignment, duplicate preflight, metadata prefill, unified nav
- Parser auto-extracts case metadata, advocate sides, and docket from PDF; operator reviews pre-populated fields in admin UI
- Repo is public on GitHub
- Hosting: Digital Ocean App Platform + managed Postgres — deployment is next milestone (DEPLOY-01, DEPLOY-03)
- Known deployment blockers: `BODY_SIZE_LIMIT=10M`, `ORIGIN`/`PROTOCOL_HEADER`/`HOST_HEADER` env vars, `admin.scotuschat.com` DNS entry

## Constraints

- **Tech stack**: SvelteKit (frontend), FastAPI/Python (backend + pipeline), PostgreSQL (database) — decided and not up for revision
- **Hosting**: Digital Ocean App Platform + managed Postgres — owner has existing account
- **Framing**: Apolitical and non-editorial is a hard constraint — every speaker gets identical schema, depth, and treatment
- **Schema forward-compatibility**: Architectural decisions must not block future features (citation resolution, cross-case queries, topic tagging) even when those features aren't being built
- **Pipeline is offline only**: Ingest/parse/resolve/enrich are CLI scripts — never HTTP endpoints or user-facing features
- **Raw PDFs are immutable**: Never modify source files after ingest; all derived data can be regenerated
- **Alembic is sole DDL authority**: Never call `Base.metadata.create_all` anywhere
- **Oyez-sourced content is CC BY-NC 4.0 (NonCommercial)**: Confirmed 2026-07-09 during Phase 29 (Historical Corpus Import) discussion — Oyez.org's oral-argument transcripts/audio (the source for ~7,800 historical arguments imported via the Cornell ConvoKit corpus) are licensed Creative Commons Attribution-NonCommercial 4.0. This creates real tension with "Monetization — not a driving goal; not excluded for future milestones" (Out of Scope, below): any future monetization strategy must account for the fact that a large share of the site's content is NonCommercial-licensed and requires attribution. Not a lawyer's determination — flagged here so it isn't silently baked in before a monetization decision is ever made. SCDB (vote/outcome data) is not implicated — that data is excluded entirely per the apolitical framing constraint, not imported.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SvelteKit for frontend | Clean syntax for content-focused UI, handles routing + SSR in one framework, owner has experience | ✓ Good — SSR, routing, and component model worked well throughout all 4 phases |
| FastAPI (Python) for backend | Pipeline uses Python for LLM calls and PDF processing; keeps server-side in one language | ✓ Good — clean service/router separation; Pydantic v2 worked well |
| PostgreSQL on Digital Ocean | Relational model fits entity/relationship structure; native integration with App Platform | ✓ Good — schema handles all cases including consolidated dockets |
| Utterances belong to arguments, not cases | Supports re-arguments (same case, multiple argument events) without schema contortion | ✓ Good — correct for Obergefell Q1/Q2 pattern |
| Capture citations now, resolve later | Avoids blocking parse step on resolution; citations stored as raw text strings | ✓ Good — schema ready; citation resolution deferred to post-v2 |
| Pipeline is offline | Transcript processing is not a live-request operation; keeps app server simple | ✓ Good — clean separation; API is purely read-only |
| Raw PDFs are immutable | Transcripts are historical documents; all derived data can be regenerated from source | ✓ Good — idempotent re-runs work correctly via pipeline_run_id |
| Re-running a step produces new rows linked to new pipeline_run_id | Old rows preserved until new run is promoted; supports safe re-processing and auditing | ✓ Good — max(pipeline_run_id) filter in service layer enforces this cleanly |
| Alembic hand-written migrations (not autogenerate) | Explicit FK dependency order control; prevents empty migration pitfall | ✓ Good — both migrations (0001 initial, 0002 speaker_alias) correct on first run |
| `statement_cache_size=0` in asyncpg `connect_args` (not top-level) | Top-level kwarg silently has no effect under PgBouncer Transaction mode; must go in connect_args dict | ✓ Good — critical for Digital Ocean PgBouncer; discovered during Phase 1 |
| Svelte 5 Runes exclusively ($props, $state, $derived, $effect) | Avoids mixing two reactivity models; `export let` and `$:` blocks prohibited | ✓ Good — consistent throughout; no store/rune conflicts |
| FASTAPI_BASE_URL from `$env/static/private` only | Server-only env var; never PUBLIC_ prefix; keeps API URL off the browser | ✓ Good — enforced by test suite; no PUBLIC_ env vars introduced |
| Route `/cases/[slug]/arguments/[id]` from day one | Avoids Phase 3 refactor; stable shareable URL structure from first commit | ✓ Good — SSR worked correctly on hard refresh without changes |
| Roster derived client-side from utterances via `$derived.by()` | No new API endpoint; avoids N+1 requests | ✓ Good — clean; no extra round-trips |
| max(pipeline_run_id) filter in service layer | Always shows most-recent parse run; prevents surfacing partial writes from crashed runs | ✓ Good — correct for PIPE-11 no-delete policy |
| Identical treatment for all speakers (color, schema, depth) | Hard apolitical framing constraint — position-only differentiation | ✓ Good — `#475569` eliminated in Phase 4; bench and advocate roster columns both `#94a3b8` |
| Stateless HMAC session cookie (node:crypto, no library) | No auth library, no DB-backed session store; DO restarts stateless; individual sessions non-revocable without rotating SECRET | ✓ Good — minimal surface area; `hooks.server.ts` is sole auth checkpoint |
| Fire-and-poll for pipeline status (Phase 7) | Subprocess spawned immediately, HTTP returns `{job_id}`, client polls every 2.5s; never await subprocess completion in request handler | ✓ Good — clean separation; prevents request timeouts on long-running steps |
| DigitalOcean Spaces (boto3) for PDF persistence (Phase 7) | DO App Platform container filesystem is ephemeral; Spaces provides durable object storage | ✓ Good — PDFs survive deploys and restarts |
| `arguments.resolved_at` visibility gate (Phase 7) | Cases only appear in `/cases/` after `resolved_at IS NOT NULL`; prevents placeholder titles ("Pending review") from surfacing publicly; metadata fabrication at resolve time forbidden by apolitical constraint | ✓ Good — Phase 8 (People Editor) provides real metadata editing |
| ArgumentParticipant seeding in parse Step 7b (Phase 8) | resolve.py Step 5 ran UPDATE against rows that never existed; fix seeds one row per unique speaker label (person_id=NULL) during parse Step 7b; select-before-insert guards re-runs | ✓ Good — participants section renders on completed job detail pages after any new run |
| People editor uses SvelteKit form actions + use:enhance throughout (Phase 8) | Consistent with existing admin UI patterns; AddNewPersonForm uses raw fetch for role creation (needs JSON response inspection) | ✓ Good — clean server validation via FastAPI Pydantic models |
| `bits-ui ^2.18.1` for speaker popover (Phase 14) | Only Svelte 5-native headless popover after `@skeletonlabs/floating-ui-svelte` archived Oct 2025 | ✓ Good — customAnchor prop + plain buttons pattern worked correctly |
| `argument_participants.side` BENCH/ADVOCATE binary (Phase 1) | Simple classification sufficient at MVP; advocate sub-roles deferred | ✓ Resolved — Phase 15 expanded SideEnum to PETITIONER/RESPONDENT/AMICUS; ADVOCATE backfilled to UNKNOWN |
| `Person.role_id` as popover role source (Phase 14) | Expedient at build time; person's primary role used as fallback | ✓ Resolved — Phase 15 replaced with `_tenure_role_name()` tenure date-range lookup for Justices; ADVOCATE_LABEL_MAP for advocates |
| Migration 0008 commits Alembic transaction before ALTER TYPE ADD VALUE (Phase 15) | PG forbids ADD VALUE inside a transaction block; `op.execute("COMMIT")` placed first in upgrade() | ✓ Good — pattern established for future PG enum expansions |
| SideEnum.ADVOCATE retained as legacy value (Phase 15) | PG cannot drop enum values; ADVOCATE→UNKNOWN backfill in migration; code should never produce ADVOCATE going forward | ✓ Good — backward-compatible; UI never displays ADVOCATE label |
| _tenure_role_name uses datetime.date objects not strings (Phase 15) | Avoids lexicographic sort bugs on ISO strings with None values; D-14 fallback to most-recent tenure when argued_date outside all windows | ✓ Good — 16 unit tests pass covering boundary cases |
| cover_extractor.py is a new module (not extending extractor.py) (Phase 16) | Separates cover-page concern; pdfplumber I/O runs before async DB session (Pitfall 1 guard) | ✓ Good — 21 unit tests; fail-safe returns {} on any exception |
| `ParseStats` assembled from scalar COUNT results, no `from_attributes` (Phase 17) | ORM object has no `parse_stats` attribute; injected via `job.__dict__` before `model_validate` reads the ORM row | ✓ Good — avoids constructing `AdminJobResponse` manually in every route |
| PDF proxy uses `redirect:'manual'` to pass Spaces 302 to browser (Phase 17) | Token stays server-side; pre-signed URL goes directly to the browser without transiting SvelteKit memory | ✓ Good — open-redirect threat mitigated by sourcing Location from FastAPI (server-controlled) |
| Same-origin SvelteKit proxy at `/admin/pipeline/{id}/pdf` (Phase 17) | Browser has no direct FastAPI route; ADMIN_TOKEN must stay server-side (Architecture Rule 2) | ✓ Good — enforced via `$env/static/private` only |
| `formatDate()` declared at script level, not inside `{#if}` block (Phase 17) | `{@const}` inside `{#if}` is scoped to that block; script-level function accessible from `{#each STEP_ORDER}` loop | ✓ Good — pitfall documented for future Svelte date helpers |
| `is_justice BOOLEAN NOT NULL DEFAULT FALSE` backfill from court_tenures only (Phase 18) | Backfill from tenure records is conservative and correct; avoids false-positive Justice classification | ✓ Good — migration 0010 clean; all 3 PEOPLE requirements verified |
| `(source_docket, question_number)` UNIQUE on arguments (Phase 19) | Natural dedup key for SCOTUS arguments; pre-real-docket synthetic values (`job-{id}`) safely pass through because they're unique per-job | ✓ Good — IntegrityError deduplication in ingest; preflight UI check layered on top |
| `cover_metadata` JSONB written unconditionally at parse; nullable fields auto-populated conditionally (Phase 19) | Separates extraction (always) from promotion (only when still null) — allows re-run without overwriting manual corrections | ✓ Good — D-09 pattern; saveMetadata action lets operator persist changes from UI |
| Unconditional list-page polling instead of `data.jobs.some(running)` guard (Phase 20) | Guard created deadlock — if no jobs were running on load, a run started from another tab would never wake the effect | ✓ Good — `invalidateAll()` is cheap; unconditional polling solves multi-tab visibility |
| `delete_argument` returns `bool \| None`: True=deleted, False=published (409), None=not found (404) (Phase 21) | Tri-state distinguishes "refused because published" from "not found"; router maps cleanly without catching exceptions | ✓ Good — can_delete flag in load function prevents UI-level 409s for most cases |
| FK cascade order: Utterance → PipelineRun → ArgumentParticipant → CaseArgument → NULL AdminJob.argument_id → Argument (Phase 21) | NULL AdminJob before deletion avoids FK violation on admin_jobs.argument_id; order mirrors logical dependency chain | ✓ Good — Pitfall 1/2 mitigated; all cascade paths tested in test_admin_arguments_service.py |
| `AdminSubNav` component + `TopNav variant=public` in admin layout (Phase 21) | Two-row admin nav: shared public TopNav + admin-only tab row; no markup duplication; dead `variant=admin` branch removed | ✓ Good — NAV-02 gap closed via Plan 21-04; root layout guard kept to prevent double-render |
| `update_resolve_row_for_job` is a new job-scoped mutation, not a reuse of `admin_arguments.update_participant_side` (Phase 25) | The existing endpoint rejects `BENCH` by design; reusing it would weaken an existing security guard | ✓ Good — clean separation; `title` forced null server-side whenever `side == BENCH` |
| Resolve card's paused-only interactive surface gated behind a single `isPaused` flag (Phase 25) | Person re-matching/create and Continue Resolve only make sense while the pipeline resolve step has left a job `PAUSED`; reuses the existing `?/resolve` batch action unchanged | ✓ Good — confirmed via UAT retest against a genuinely paused job; the two initial "missing trigger" UAT reports traced to testing against a non-paused (already-completed) job, not a code defect |
| `readonlyMode` computed once in `+page.server.ts` `load()` from `argument.status !== 'pipeline'` (Phase 25) | Single source of truth so `RunStatusCard`/`ResolveCard`/`ArgumentDetailsCard` all read the same boolean rather than re-deriving it independently | ✓ Good — no drift observed across the three components |
| `_bench_role_and_missing_tenure` has no fallback to the most-recent tenure, unlike `speakers._tenure_role_name`'s D-14 fallback (Phase 25) | Operator-facing Resolve card needs an explicit "Missing tenure" state + edit-person link rather than silently guessing a bench role | ✓ Good — kept intentionally distinct from the public speaker popover's fallback behavior |
| Person-level Role field dropped; role captured per-argument only (D-10, Phase 27) | Phase 26 already made role an `argument_participants` concern; a person-level Role field was redundant and could drift from the per-argument source of truth | ✓ Good — PEDIT-04/PEDIT-08 formally superseded; simplifies the Bench Details card |
| Appointment data (seat, appointed-by, president's party, dates) moved to per-tenure rows, not per-person (D-16, Phase 27) | A Justice can have multiple tenures (e.g., elevated to Chief); person-level appointment fields couldn't represent that | ✓ Good — `court_tenures` carries the appointment fields; migration 0016 + schema/service/UI updated together (Plans 27-01/02/03/05) |
| Click-to-filter missing-field pills replace the "Incomplete only" toggle (D-04, Phase 27) | Per-tab missing-field breakdown is more actionable than one binary toggle | ✓ Good — PDIR-05 reworked; pills scoped per Bench/Advocate tab |
| Write-only `$state` reassignment pattern for effect-driven resets (Phase 27, Plan 27-11) | A person-id-change reset `$effect` that both reads and writes the same `$state` variable inside its own body creates a self-referential dependency Svelte 5 reschedules forever (`effect_update_depth_exceeded`) | ✓ Good — fixed by computing all intermediate values in a local plain variable and writing the `$state` variable exactly once, after the loop; matches the codebase's existing write-only reset convention (e.g. `admin/pipeline/[job_id]/+page.svelte:78`) — document this pattern before introducing any new effect that rebuilds a keyed list on reset |
| CR-01/CR-02 data-preservation fixes keep data-carrying inputs always-present (not conditionally rendered) (Phase 27, Plan 27-10) | Conditionally-rendered form inputs (e.g. inside `{#if isJustice}`) don't submit when hidden, silently wiping tenure/birthdate data on an accidental toggle-then-save or a merge-redirect-then-save | ✓ Good — hidden inputs stay in the DOM outside the conditional block so `use:enhance` always submits the real values; independently re-verified intact through two further gap-closure rounds (27-11, code review, phase verification) |
| Corpus importer's `question_number` derived per-docket via `select(func.max(...))`, not hardcoded to 1 (CR-01, Phase 29, Plan 29-09) | The real DB uniqueness constraint is `(source_docket, question_number)`, but the importer originally deduped only on `oyez_transcript_id` and hardcoded `question_number=1` — reargued cases and dockets already ingested by the PDF pipeline collided at flush and were silently folded into the generic error counter | ✓ Good — derivation aligns the write path with the DB's real contract; a distinct `docket_question_conflict` counter + `IntegrityError` safety net catches any residual collision without silent data loss; independently re-verified via direct code read and live test execution during phase verification |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-14 after Phase 40 (README local-stack setup) completed — 4 of 10 v1.6 backlog phases are verified; 6 remain.*
