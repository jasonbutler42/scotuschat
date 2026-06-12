# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-11)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** Phase 3 — Full UI (UI-SPEC approved)

## Current Position

Phase: 3 of 4 (Full UI)
Plan: 0 of TBD in current phase (not yet planned)
Status: Phase 3 UI-SPEC approved — Ready to plan Phase 3
Last activity: 2026-06-12 — UI design contract (03-UI-SPEC.md) created and verified (6/6 dimensions passed, 1 revision to collapse typography scale from 5 → 4 sizes).

Progress: [███████░░░] 75%

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: 40 min
- Total execution time: 2 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-proof-of-concept | 5 | 215 min | 43 min |
| 02-speaker-resolution | 4 | — | — |

**Recent Trend:**
- Last 5 plans: 01-01 (45 min), 01-02 (35 min), 01-03 (45 min), 01-04 (45 min), 01-05 (45 min)
- Trend: Stable ~43 min/plan

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: Schema (INFRA-01, INFRA-02) must come first — all pipeline and API work depends on it
- Roadmap: Parse step (PIPE-03–06) ships in Phase 1 alongside minimal FastAPI + minimal SvelteKit to prove concept end-to-end
- Roadmap: Resolve step (PIPE-07–09) deferred to Phase 2 — depends on utterances from Parse
- Roadmap: PIPE-08 (speaker_alias seed) is a Phase 2 prerequisite; must be in place before PIPE-07 runs
- Roadmap: A11Y requirements (A11Y-01–04) held for Phase 4 after full UI surface exists
- 01-01: Svelte 5 Runes exclusively — $props() not export let; no $: reactive blocks
- 01-01: FASTAPI_BASE_URL imported from $env/static/private only — never PUBLIC_ prefix (T-01-01 threat mitigation)
- 01-01: Route /cases/[slug]/arguments/[id] created from day one to avoid Phase 3 refactor (D-17)
- 01-01: Identical bubble backgrounds for bench and advocate (apolitical framing — position-only side differentiation)
- 01-01: adapter-node installed for Digital Ocean App Platform SSR support
- 01-02: Citations table deferred — 10 tables only in initial schema; schema supports citations FK (resolved_case_id) but table not created until needed
- 01-02: Hand-written migration (not autogenerate) — explicit FK dependency order control; prevents Pitfall 2 (empty migrations)
- 01-02: SideEnum uppercase (BENCH/ADVOCATE/UNKNOWN), PipelineRunStatus lowercase (pending/running/etc.) — matches raw speaker label conventions and status field idioms respectively
- 01-02: test_no_create_all_in_codebase searches production dirs only (api/, alembic/, pipeline/) — test files excluded to avoid false positives
- 01-03: SSRF validation as standalone _validate_url() function — synchronous, no DB, enables unit tests without async setup
- 01-03: Lazy engine creation in get_engine() — DATABASE_URL not required at import time, only at coroutine execution time
- 01-03: PipelineRunStatus.COMPLETED set directly for ingest (synchronous op) — pending→running→completed state machine used by parse step (Plan 04)
- 01-03: parse.py stub created in Plan 03 to satisfy __main__.py import — full implementation in Plan 04
- 01-04: Two-variable section hint design (pending_section_hint + current_section_hint) prevents cascade (Pitfall 3)
- 01-04: F04 fix — ON\s+BEHALF\s+OF added to TOC_SECTION_RE (handles Obergefell "ON BEHALF OF" header variant)
- 01-04: assign_side() deterministic rule-based (BENCH_RE/ADVOCATE_RE) — resolves D-09 Open Question #3
- 01-04: LLM pass falls back to rule-based output on failure — resilience over hard-fail for Phase 1 PoC
- 01-04: AsyncAnthropic(max_retries=0) + tenacity outer retry — prevents triple-retry on transient errors (Pitfall 4)
- 01-05: statement_cache_size=0 in connect_args dict (asyncpg connection args) — not top-level engine kwarg; top-level silently has no effect under PgBouncer Transaction mode
- 01-05: expire_on_commit=False on async_sessionmaker — prevents MissingGreenlet on ORM attribute access after commit in async context
- 01-05: Lifespan context manager (not @app.on_event) — @app.on_event deprecated in FastAPI 0.93+
- 01-05: Service returns dict, router creates Pydantic response — clean ORM/schema separation
- 01-05: service uses MAX(pipeline_runs.id) WHERE step='parse' AND status='completed' — not MAX(utterances.pipeline_run_id), to avoid surfacing partial writes from crashed runs (CR-04 fix)
- 01-05: formatDate appends T00:00:00 before new Date() — forces local-date parsing, avoids UTC midnight roll-back west of UTC

### Pending Todos

None yet.

### Blockers/Concerns

- Research recommends spiking LLM parse prompt design (2–4 hours, 3–5 real PDFs) before finalizing ParsedUtterance schema — worth doing before Phase 1 planning
- `speaker_alias` seed data completeness should be sourced from FJC and walkerdb/supreme_court_transcripts before Phase 2 planning
- asyncpg requires `statement_cache_size=0` when behind DO PgBouncer Transaction mode — must be in initial engine config (Phase 1)

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-06-12
Stopped at: Phase 3 UI-SPEC approved. UI design contract at .planning/phases/03-full-ui/03-UI-SPEC.md. Ready to plan Phase 3.
Resume file: .planning/phases/03-full-ui/03-UI-SPEC.md
