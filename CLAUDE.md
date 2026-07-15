# SCOTUS Chat — Project Guide

## Project

A read-only website that displays Supreme Court oral arguments as a chat-style interface. The pipeline is an offline operator-only CLI tool. The website is never interactive for end users.

See `.planning/PROJECT.md` for full context.

## GSD Workflow

This project uses the Get Shit Done (GSD) workflow. Always follow the phase-gate process:

```
/gsd:discuss-phase N   → gather context and clarify approach
/gsd:plan-phase N      → create an executable plan
/gsd:execute-phase N   → implement the plan
/gsd:verify-work N     → verify phase goal was achieved
```

**Current state:** See `.planning/STATE.md`
**Roadmap:** See `.planning/ROADMAP.md`
**Requirements:** See `.planning/REQUIREMENTS.md`

## Key Constraints

- **Apolitical framing is a hard constraint.** Every speaker (Justice or advocate) gets identical schema, depth, and treatment. No derived insight, summaries, sentiment, or statistics.
- **Pipeline is offline only.** Ingest/parse/resolve are CLI scripts. Never expose pipeline steps as HTTP endpoints or user-facing features.
- **Raw PDFs are immutable.** Never modify source files after ingest. All derived data can be regenerated.
- **Alembic is the sole DDL authority.** Never call `Base.metadata.create_all` anywhere.
- **asyncpg requires `statement_cache_size=0`** when behind Digital Ocean PgBouncer (Transaction mode). This must be in the initial engine config.

## Stack

| Layer | Choice |
|-------|--------|
| Frontend | SvelteKit 2.x / Svelte 5 (Runes — no legacy stores) |
| Backend | FastAPI 0.115+ with Pydantic v2 |
| Database | PostgreSQL 16, SQLAlchemy 2.0 async, Alembic migrations |
| Pipeline | Python 3.12, pdfplumber, Anthropic SDK, instructor, tenacity |
| Hosting (v2) | Digital Ocean App Platform |

## Repository Structure

```
/app        — SvelteKit frontend
/api        — FastAPI backend
/pipeline   — Preprocessing scripts (ingest, parse, resolve, enrich, extract)
/data       — Raw ingested PDF files (immutable)
```

## Spike Findings

- **Spike findings for scotuschat** (PDF extraction patterns, ParsedUtterance schema, parse state machine, failure taxonomy, LLM prompt template) → `Skill("spike-findings-scotuschat")`

## Architecture Rules

1. FastAPI is read-only — the pipeline writes directly to PostgreSQL; the API never triggers pipeline steps
2. All FastAPI calls from SvelteKit go through `+page.server.ts` server load functions — `FASTAPI_BASE_URL` is a server-only env var, never `PUBLIC_`
3. Re-running a pipeline step produces new rows under a new `pipeline_run_id` — prior rows are not deleted until the new run is promoted
4. An extracted field with an operator-editable destination uses `CopyableExtractedValue` by default unless its phase explicitly opts out; a read-only extracted value without an operator-editable destination remains plain.
