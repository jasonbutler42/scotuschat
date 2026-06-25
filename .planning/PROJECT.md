# SCOTUS Chat

## What This Is

A website that displays Supreme Court oral arguments as a chat-style interface — formatted like a group conversation between the Justices and whoever is arguing before the Court. An offline operator-only pipeline ingests transcript PDFs, parses utterances via LLM, and resolves raw speaker labels to named people records. An operator admin web interface drives the full pipeline from the browser — uploading PDFs, monitoring step progress, reviewing speaker aliases, and editing people metadata — without touching the CLI. The goal is accessibility: making dense legal transcripts easy to follow for anyone who wants to understand who said what, without editorial framing or political commentary.

## Core Value

Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.

## Current Milestone: v1.3 Speaker Accuracy + Pipeline Confidence

**Goal:** Fix speaker role accuracy on the live popover, make the ingestion pipeline reliable enough to process large volumes of older transcripts, and give the operator enough visibility to trust the process.

**Target features:**
- Speaker role accuracy — Justices show tenure-derived role at argument date; advocates have per-argument roles (ROLE-01–03)
- Parser improvements — extract case metadata and advocate sides from transcript PDF at parse time (PARSE-01–02)
- Pipeline UI polish — stage stat cards, pre-populated argument fields, source PDF access (PIPE-21–22)

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

### Active

- [ ] Speaker role accuracy — Justice tenure date-range lookup for popover role; per-argument advocate roles stored and editable (ROLE-01, ROLE-02, ROLE-03)
- [ ] Parser improvements — parse step extracts case name, docket, argued date, and advocate side from transcript PDF (PARSE-01, PARSE-02)
- [ ] Pipeline UI polish — stage stat cards; source PDF accessible from job detail; pre-populated argument fields (PIPE-21, PIPE-22)
- [ ] Application deployed to Digital Ocean App Platform (SvelteKit + FastAPI as separate services, managed Postgres) (DEPLOY-01, v1.4)
- [ ] Continuous deployment from GitHub main branch (DEPLOY-03, v1.4)

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

- Shipped v1.0 with ~4,895 LOC across TypeScript, Svelte, and Python (Phase 1–4)
- Shipped v1.1 with ~52,872 total LOC (120 files changed, 23,277 insertions; 155 commits from Phase 5–8; 4 days 2026-06-15 → 2026-06-18)
- Tech stack confirmed: SvelteKit 2.x + Svelte 5 Runes (frontend), FastAPI 0.115+ + Pydantic v2 (API), PostgreSQL 16 + SQLAlchemy 2.0 async + Alembic (database), Python 3.12 + pdfplumber + Anthropic SDK + instructor + tenacity (pipeline)
- Admin interface: stateless HMAC session cookie, DO Spaces PDF storage (boto3), fire-and-poll job state, people directory + edit form
- One hand-picked case (Obergefell v. Hodges) ingested and verified end-to-end; `arguments.resolved_at` gate controls public visibility
- No photo URLs populated yet — avatar initials fallback in use throughout
- Repo is public on GitHub
- Hosting: Digital Ocean App Platform + managed Postgres (owner has existing account; DEPLOY-01/03 are v1.2 work)
- PgBouncer transaction mode constraint fully addressed: `statement_cache_size=0` in `connect_args` (not top-level engine kwarg)
- Known deployment blockers: `BODY_SIZE_LIMIT=10M`, `ORIGIN`/`PROTOCOL_HEADER`/`HOST_HEADER` env vars, `admin.scotuschat.com` DNS entry

## Constraints

- **Tech stack**: SvelteKit (frontend), FastAPI/Python (backend + pipeline), PostgreSQL (database) — decided and not up for revision
- **Hosting**: Digital Ocean App Platform + managed Postgres — owner has existing account
- **Framing**: Apolitical and non-editorial is a hard constraint — every speaker gets identical schema, depth, and treatment
- **Schema forward-compatibility**: Architectural decisions must not block future features (citation resolution, cross-case queries, topic tagging) even when those features aren't being built
- **Pipeline is offline only**: Ingest/parse/resolve/enrich are CLI scripts — never HTTP endpoints or user-facing features
- **Raw PDFs are immutable**: Never modify source files after ingest; all derived data can be regenerated
- **Alembic is sole DDL authority**: Never call `Base.metadata.create_all` anywhere

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
| `argument_participants.side` BENCH/ADVOCATE binary (Phase 1) | Simple classification sufficient at MVP; advocate sub-roles deferred | ⚠️ Revisit — Phase 15 expands to per-argument roles for correct popover display |
| `Person.role_id` as popover role source (Phase 14) | Expedient at build time; person's primary role used as fallback | ⚠️ Revisit — Phase 15 replaces with tenure date-range lookup for Justices |

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
*Last updated: 2026-06-25 after v1.3 milestone start*
