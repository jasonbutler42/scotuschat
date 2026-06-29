# Phase 1: Foundation + Proof of Concept - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 delivers the full project scaffold end-to-end: PostgreSQL schema + Alembic migrations, ingest + parse pipeline CLI commands, a minimal FastAPI endpoint, and a minimal SvelteKit chat view — all wired together so an operator can take a real SCOTUS transcript PDF to a rendered two-sided chat in a browser. The hand-picked case is Obergefell v. Hodges (Q1 session, argued 2015-04-28).

**Note:** A parse prompt spike (`/gsd:spike`) must be completed before Phase 1 planning begins. The spike produces the validated `ParsedUtterance` schema, a working prompt template, and a failure taxonomy. Phase 1 planning is blocked on spike output.

</domain>

<decisions>
## Implementation Decisions

### Parse Prompt Spike (pre-Phase 1)
- **D-01:** Run a dedicated `/gsd:spike` session before Phase 1 planning. Phase 1 planning is blocked until the spike delivers its three outputs.
- **D-02:** Spike deliverables: (1) validated `ParsedUtterance` Pydantic schema, (2) working prompt template for `claude-haiku-4-5-20251001`, (3) failure taxonomy classifying transient vs. structural LLM failures (to ground PIPE-06 retry logic).
- **D-03:** Spike test PDFs: Obergefell v. Hodges Q1 session + 2–3 other recent cases for variety.
- **D-04:** Target model for parse step: `claude-haiku-4-5-20251001`. Spike validates that Haiku is accurate enough; if not, escalate to Sonnet in the spike findings.
- **D-05:** Feed strategy: full transcript text per session as one LLM call (no chunking). The spike should confirm Q1 session fits within Haiku's context window (~40–50k tokens expected).

### Dev Environment Setup
- **D-06:** No Docker. Native per-user install — no admin rights required on Windows. PostgreSQL portable ZIP, Python per-user installer (python.org), Node.js per-user installer (nodejs.org).
- **D-07:** A single dev startup script (PowerShell `.ps1` or `Makefile` target) starts all three services: Postgres, FastAPI (uvicorn), SvelteKit (`vite dev`).
- **D-08:** Postgres data directory lives inside the repo at `/data/pgdata`, gitignored. Easy to nuke and recreate; self-contained per clone.

### Side Assignment
- **D-09:** The parse step outputs a `side` field on every utterance: enum `BENCH | ADVOCATE | UNKNOWN`. The LLM assigns side at parse time based on the raw speaker label (e.g., "JUSTICE KAGAN" → BENCH, "MR. CLEMENT" → ADVOCATE, stage directions → UNKNOWN).
- **D-10:** `side` is stored in the DB from Phase 1 forward. Phase 2 speaker resolution confirms/corrects it but does not introduce the field.

### Hand-Picked PoC Case
- **D-11:** Obergefell v. Hodges, Q1 session only (docket 14-556 consolidated, argued 2015-04-28). Q1 covers the question of whether the 14th Amendment requires states to license same-sex marriages.
- **D-12:** This case exercises INFRA-02 (consolidated dockets) because Obergefell was consolidated across four docket numbers (14-556, 14-562, 14-571, 14-574).
- **D-13:** Q2 session is deferred — not part of Phase 1 PoC.

### Structured LLM Output
- **D-14:** Use `instructor` library (already declared in the project stack) wrapping the Anthropic SDK. Auto-validates LLM responses against the `ParsedUtterance` Pydantic model; retries on schema mismatch. Do not use raw tool use or prompt-only JSON mode.

### Pipeline CLI Design
- **D-15:** Invoke as a Python package: `python -m pipeline ingest --url ...` and `python -m pipeline parse --run-id ...`. No install step required beyond `pip install -r requirements.txt` in the venv.
- **D-16:** CLI flag design for ingest and parse is left to the planner (user preference: "you decide").

### SvelteKit Route Structure
- **D-17:** Use the final URL structure from day one: `/cases/[slug]/arguments/[id]`. Phase 1 hard-codes navigation to the Obergefell argument; Phase 3 wires up the case list. No route refactor needed later.

### FastAPI Scaffolding Depth
- **D-18:** Scaffold the full `routers/ / services/ / schemas/` directory structure in Phase 1 with the single Phase 1 endpoint (`GET /arguments/{id}/utterances`) wired as the first example. Phase 2–3 endpoints slot in without restructuring.

### Claude's Discretion
- CLI flags for `python -m pipeline ingest` and `python -m pipeline parse` (design them for ergonomics and the actual data the ingest step needs).
- `instructor` retry configuration (number of retries, backoff — use `tenacity` per the declared stack).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Definition
- `.planning/PROJECT.md` — Core value, constraints, key decisions, out-of-scope items
- `.planning/REQUIREMENTS.md` — All v1 requirements; Phase 1 covers INFRA-01, INFRA-02, INFRA-03, PIPE-01–06, PIPE-10–11, API-01, UI-01–03
- `.planning/ROADMAP.md` — Phase 1 goal, success criteria, and dependency ordering

### Hard Constraints (CLAUDE.md)
- `CLAUDE.md` — Apolitical framing, Alembic-only DDL, `asyncpg` `statement_cache_size=0`, pipeline offline-only, raw PDFs immutable, all FastAPI calls through `+page.server.ts`

### External Docs (no local files yet — researcher should locate)
- Official SCOTUS transcript PDF for Obergefell v. Hodges, Q1 session (supremecourt.gov or oyez.org)
- `instructor` library docs — structured output with Anthropic SDK
- `pdfplumber` docs — PDF text extraction
- Alembic migration docs — async SQLAlchemy 2.0 patterns
- Digital Ocean PgBouncer / asyncpg `statement_cache_size=0` requirement

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — project is a blank slate. No existing components, hooks, or utilities.

### Established Patterns
- None yet — Phase 1 establishes all baseline patterns that subsequent phases will follow.

### Integration Points
- Phase 1 establishes the integration contract between pipeline → DB → FastAPI → SvelteKit that all future phases depend on.
- FastAPI router/service/schema structure laid down in Phase 1 is the pattern Phase 2–3 must follow.
- `side` field on utterances is the Phase 1 ↔ Phase 2 handoff point for speaker resolution.

</code_context>

<specifics>
## Specific Ideas

- **Project origin:** Obergefell v. Hodges is what started this project — it is the inspiration case, not just a random test case.
- **asyncpg constraint:** `statement_cache_size=0` must be in the initial engine config (Phase 1 sets this up; it must not be retrofitted in Phase 4/DEPLOY). See CLAUDE.md.
- **Alembic constraint:** `Base.metadata.create_all` must never appear anywhere in the codebase. Alembic is the sole DDL authority. See CLAUDE.md.
- **Apolitical framing:** Every speaker (Justice or advocate) gets identical schema, depth, and treatment. No derived insight, summaries, sentiment, or statistics. This applies to the chat UI rendering in Phase 1.

</specifics>

<deferred>
## Deferred Ideas

- Obergefell Q2 session — not part of Phase 1 PoC; load after Phase 1 is validated.
- Additional cases beyond Obergefell — pipeline can ingest them post-Phase 1.
- Docker Compose setup — deferred; user cannot install Docker without admin rights. May revisit if dev machine changes.

</deferred>

---

*Phase: 1-Foundation + Proof of Concept*
*Context gathered: 2026-06-11*
