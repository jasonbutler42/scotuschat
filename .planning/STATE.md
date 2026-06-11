# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-11)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** Phase 1 — Foundation + Proof of Concept

## Current Position

Phase: 1 of 4 (Foundation + Proof of Concept)
Plan: 1 of 5 in current phase (01-01 complete — project scaffold)
Status: Executing
Last activity: 2026-06-11 — Plan 01-01 executed: Python scaffold + SvelteKit scaffold complete

Progress: [█░░░░░░░░░] 10%

## Performance Metrics

**Velocity:**
- Total plans completed: 1
- Average duration: 45 min
- Total execution time: 0.75 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-proof-of-concept | 1 | 45 min | 45 min |

**Recent Trend:**
- Last 5 plans: 01-01 (45 min)
- Trend: Baseline established

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

Last session: 2026-06-11
Stopped at: Phase 1, Plan 01 complete — project scaffold (Python requirements, SvelteKit app, route structure, stub components, dev startup script). Ready to execute Plan 02 (Alembic schema migrations).
Resume file: None
